"""On-premise Active Directory & Exchange user provisioning via PowerShell.

Runs on the Exchange server — uses New-RemoteMailbox to create a remote mailbox
(cloud-hosted) with an on-premise AD account, plus native AD cmdlets via subprocess.
"""

import base64
import logging
import subprocess

from src.config import settings
from src.models import OnboardingUser

logger = logging.getLogger(__name__)

# Prefix prepended to every PowerShell script so AD cmdlets are always available.
_PS_PREAMBLE = "Import-Module ActiveDirectory -ErrorAction SilentlyContinue\n"


def _encode_command(script: str) -> str:
    """Encode a PowerShell script as base64 UTF-16LE for -EncodedCommand.

    This avoids all code-page / encoding issues with special characters
    (ö, ä, ü, ß, …) that break when passed via -Command on Windows.
    """
    return base64.b64encode(script.encode("utf-16-le")).decode("ascii")


def _escape(value: str) -> str:
    """Escape a string for safe embedding in a PowerShell single-quoted string."""
    return value.replace("'", "''")


def user_exists_in_ad(abbreviation: str) -> bool:
    """Check if a user with the given SamAccountName already exists in AD."""
    if not abbreviation:
        return False

    script = (
        _PS_PREAMBLE
        + f"if (Get-ADUser -Filter {{SamAccountName -eq '{_escape(abbreviation)}'}}) {{ 'FOUND' }} else {{ 'NOTFOUND' }}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", _encode_command(script)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    return "FOUND" in result.stdout


def _run_ps(script: str, *, description: str) -> subprocess.CompletedProcess[str]:
    """Execute a PowerShell script block and return the result.

    Automatically prepends ``Import-Module ActiveDirectory`` and uses
    ``-EncodedCommand`` (base64 UTF-16LE) to avoid code-page issues with
    special characters like ö, ä, ü.
    """
    full_script = _PS_PREAMBLE + script
    logger.debug("Running PowerShell [%s]:\n%s", description, full_script)

    if settings.dry_run:
        logger.info("[DRY RUN] Would run PowerShell [%s]:\n%s", description, full_script)
        return subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")

    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-EncodedCommand", _encode_command(full_script)],
        capture_output=True,
        text=True,
        timeout=120,
    )

    if result.returncode != 0:
        logger.error(
            "PowerShell [%s] failed (rc=%d):\nSTDOUT: %s\nSTDERR: %s",
            description,
            result.returncode,
            result.stdout,
            result.stderr,
        )
        raise RuntimeError(f"PowerShell [{description}] failed: {result.stderr}")

    logger.debug("PowerShell [%s] output: %s", description, result.stdout.strip())
    return result


def create_mailbox(user: OnboardingUser, *, ou: str) -> None:
    """Create a remote mailbox (cloud-hosted) with an on-premise AD account.

    Uses New-RemoteMailbox which creates the AD user and sets up mail-routing
    to Exchange Online via the remote routing address.
    """
    abrev_upper = user.abbreviation.upper()
    display_name = f"{user.last_name}, {user.first_name}"
    routing_address = f"{abrev_upper}@{settings.remote_routing_domain}"

    script = f"""
Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn -ErrorAction SilentlyContinue

New-RemoteMailbox `
    -Password (ConvertTo-SecureString '{settings.default_password}' -AsPlainText -Force) `
    -Name '{_escape(display_name)}' `
    -DisplayName '{_escape(display_name)}' `
    -FirstName '{_escape(user.first_name)}' `
    -LastName '{_escape(user.last_name)}' `
    -SamAccountName '{abrev_upper}' `
    -UserPrincipalName '{abrev_upper}@bgr.at' `
    -OnPremisesOrganizationalUnit '{_escape(ou)}' `
    -Initials '{abrev_upper}' `
    -PrimarySmtpAddress '{_escape(user.email)}' `
    -RemoteRoutingAddress '{routing_address}' `
    -ResetPasswordOnNextLogon $true `
    -Verbose
"""
    _run_ps(script, description=f"New-RemoteMailbox {user.email}")
    logger.info("Created remote mailbox for %s", user.email)


def set_ad_attributes(user: OnboardingUser, *, job_title: str) -> None:
    """Set AD user attributes (address, phone, title, extension attributes, manager)."""
    address = user.address

    # Build the main Set-ADUser script
    script = f"""
$userdn = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(user.abbreviation)}' }}
if (-not $userdn) {{
    Write-Error 'User {_escape(user.abbreviation)} not found in AD'
    exit 1
}}

# Extension attributes
Set-ADUser -Identity $userdn -Add @{{"extensionattribute1"='{_escape(user.title_pre)}'}}
Set-ADUser -Identity $userdn -Add @{{"extensionattribute2"='{_escape(user.title_post)}'}}
Set-ADUser -Identity $userdn -Add @{{"extensionattribute5"='{_escape(job_title)}'}}

# Standard attributes
Set-ADUser `
    -Identity $userdn `
    -Replace @{{
        l                            = '{_escape(address.city)}'
        facsimileTelephoneNumber     = '+43 (1) 534 80 - 8'
        Company                      = 'Binder Grösswang Rechtsanwälte GmbH'
        c                            = '{_escape(address.country)}'
        telephoneNumber              = '{_escape(user.phone)}'
        PostalCode                   = '{_escape(address.zip_code)}'
        StreetAddress                = '{_escape(address.street)}'
        st                           = '{_escape(address.state)}'
        Title                        = '{_escape(job_title)}'
        Description                  = '{_escape(job_title)}'
        IPPhone                      = '{_escape(user.phone)}'
    }} `
    -Verbose
"""
    _run_ps(script, description=f"Set-ADUser attributes {user.abbreviation}")

    # Set manager if team field is populated (last 3 chars = manager abbreviation)
    if user.team and len(user.team) >= 3:
        manager_abrev = user.team[-3:]
        manager_script = f"""
$userdn = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(user.abbreviation)}' }}
$managerObject = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(manager_abrev)}' }} `
    -Properties DisplayName, extensionAttribute1, extensionAttribute2

if ($managerObject) {{
    Set-ADUser -Identity $userdn -Manager $managerObject.DistinguishedName
    Set-ADUser -Identity $userdn -Add @{{"extensionattribute15"= $managerObject.DisplayName }}
    Set-ADUser -Identity $userdn -Add @{{"extensionattribute14"= ($managerObject.extensionAttribute1 + ' ' + $managerObject.DisplayName + ' ' + $managerObject.extensionAttribute2) }}
}} else {{
    Write-Warning 'Manager {_escape(manager_abrev)} not found in AD'
}}
"""
        _run_ps(manager_script, description=f"Set-ADUser manager {user.abbreviation}")

    logger.info("Set AD attributes for %s", user.abbreviation)


def add_to_groups(user: OnboardingUser, groups: list[str]) -> list[str]:
    """Add user to AD groups. Returns list of groups that failed."""
    failed: list[str] = []

    for group in groups:
        script = f"Add-ADGroupMember -Identity '{_escape(group)}' -Members '{_escape(user.abbreviation)}'"
        try:
            _run_ps(script, description=f"Add to group {group}")
        except RuntimeError:
            logger.warning("Failed to add %s to group %s", user.abbreviation, group)
            failed.append(group)

    # Team group: Team-<manager_sam>
    if user.team and len(user.team) >= 3:
        manager_abrev = user.team[-3:]
        team_script = f"""
$managerDn = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(manager_abrev)}' }}
if ($managerDn) {{
    $team = Get-ADUser -Identity $managerDn -Properties sAMAccountName | Select-Object -ExpandProperty sAMAccountName
    $userdn = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(user.abbreviation)}' }}
    Add-ADGroupMember -Identity ("Team-" + $team) -Members $userdn
}} else {{
    Write-Warning 'Manager {_escape(manager_abrev)} not found — cannot add to team group'
}}
"""
        try:
            _run_ps(team_script, description=f"Add to team group {user.abbreviation}")
        except RuntimeError:
            logger.warning("Failed to add %s to team group", user.abbreviation)
            failed.append(f"Team-{manager_abrev}")

    return failed


def create_profile_folder(user: OnboardingUser) -> None:
    """Create the user's profile folder on the DFS share and set ACLs."""
    folder_path = f"{settings.profile_base_path}\\{user.abbreviation}"

    script = f"""
$user = Get-ADUser -Filter {{ SamAccountName -eq '{_escape(user.abbreviation)}' }}
if (-not $user) {{
    Write-Error 'User {_escape(user.abbreviation)} not found in AD'
    exit 1
}}

$userSID = $user.SID
$userDomain = $user.DistinguishedName -replace '^.*?DC=([^,]+).*$', '$1'
$userIdentity = "$userDomain\\$($user.SamAccountName)"

$folderPath = '{folder_path}'

# Create folder if not exists
if (-not (Test-Path -Path $folderPath)) {{
    try {{
        New-Item -Path $folderPath -ItemType Directory -Force | Out-Null
        Write-Output "Created folder: $folderPath"
    }}
    catch {{
        Write-Error "Failed to create folder: $_"
        exit 1
    }}
}} else {{
    Write-Output "Folder already exists: $folderPath"
}}

# Set ACLs
try {{
    $acl = Get-Acl $folderPath

    # Remove non-system permissions
    $acl.Access | Where-Object {{
        $_.IdentityReference -notlike "NT AUTHORITY\\*" -and $_.IdentityReference -notlike "BUILTIN\\*"
    }} | ForEach-Object {{
        $acl.RemoveAccessRule($_) | Out-Null
    }}

    # Set user as owner
    $acl.SetOwner($userSID)

    # Full control for the user
    $permission = New-Object System.Security.AccessControl.FileSystemAccessRule(
        $userIdentity,
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.AddAccessRule($permission)

    # Full control for Administrators
    $adminPermission = New-Object System.Security.AccessControl.FileSystemAccessRule(
        "BUILTIN\\Administrators",
        "FullControl",
        "ContainerInherit,ObjectInherit",
        "None",
        "Allow"
    )
    $acl.AddAccessRule($adminPermission)

    Set-Acl -Path $folderPath -AclObject $acl
    Write-Output "Permissions set for: $userIdentity"
}}
catch {{
    Write-Error "Failed to set permissions: $_"
    exit 1
}}
"""
    _run_ps(script, description=f"Create profile folder {user.abbreviation}")
    logger.info("Profile folder ready for %s", user.abbreviation)


def provision_user(
    user: OnboardingUser,
    *,
    job_title: str,
    ou: str,
    groups: list[str],
) -> list[str]:
    """Full on-premise provisioning: mailbox → AD attributes → groups → profile folder.

    Returns list of groups that failed to be assigned.
    """
    create_mailbox(user, ou=ou)
    set_ad_attributes(user, job_title=job_title)
    failed_groups = add_to_groups(user, groups)
    create_profile_folder(user)
    return failed_groups
