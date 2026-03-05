<#
.SYNOPSIS
    Audits and optionally fixes NTFS permissions on user profile folders.

.DESCRIPTION
    Each sub-folder under RootFolder is expected to match an AD SamAccountName.
    The correct ACL is:
        - DOMAIN\<SamAccountName>   FullControl  (owner + explicit ACE)
        - DOMAIN\Domain Admins      FullControl
        - BUILTIN\Administrators    FullControl
        - NT AUTHORITY\SYSTEM        FullControl
        - CREATOR OWNER              FullControl  (accepted, not required)
    All other ACEs are considered faulty and will be reported.
    Comparisons use SIDs to avoid locale issues (German vs English names).

    Use -Fix to apply corrections.  Add -WhatIf to preview changes without writing.
    Folders that do not match an AD SamAccountName are skipped.

.PARAMETER RootFolder
    Path that contains one sub-folder per user (default: E:\Daten\Profile).

.PARAMETER DomainName
    NetBIOS domain name used to build DOMAIN\user identities (default: BGR).

.PARAMETER Fix
    Actually repair permissions.  Without this flag the script only reports.

.PARAMETER ExtraOnly
    Only report folders with EXTRA (unexpected) ACEs or wrong owners.
    MISSING permissions are ignored in this mode.

.PARAMETER RemoveExtra
    Only remove EXTRA (unexpected) ACEs. Does not change the owner or add
    missing permissions. Combine with -WhatIf for a dry-run.

.PARAMETER AddMissing
    Only add MISSING required ACEs. Does not change the owner or remove
    extra permissions. Combine with -WhatIf for a dry-run.

.PARAMETER DisableInheritance
    Disable ACL inheritance on folders that have it enabled. Inherited ACEs
    are removed (not copied as explicit). Existing explicit ACEs are kept.
    Combine with -WhatIf for a dry-run.

.PARAMETER WhatIf
    When combined with -Fix, shows what would be changed without writing ACLs.

.EXAMPLE
    # Audit only — no changes
    .\Fix-ProfilePermissions.ps1

.EXAMPLE
    # Show only extra permissions and wrong owners
    .\Fix-ProfilePermissions.ps1 -ExtraOnly

.EXAMPLE
    # Disable inheritance on all profile folders
    .\Fix-ProfilePermissions.ps1 -DisableInheritance

.EXAMPLE
    # Add only missing permissions (no owner change, no extra removal)
    .\Fix-ProfilePermissions.ps1 -AddMissing

.EXAMPLE
    # Remove only extra permissions (no owner change, no missing fix)
    .\Fix-ProfilePermissions.ps1 -RemoveExtra

.EXAMPLE
    # Dry-run — show what Fix would do
    .\Fix-ProfilePermissions.ps1 -Fix -WhatIf

.EXAMPLE
    # Apply fixes
    .\Fix-ProfilePermissions.ps1 -Fix
#>
[CmdletBinding()]
param(
    [string]$RootFolder = "E:\Daten\Profile",
    [string]$DomainName = "BGR",
    [switch]$Fix,
    [switch]$ExtraOnly,
    [switch]$RemoveExtra,
    [switch]$AddMissing,
    [switch]$DisableInheritance,
    [switch]$WhatIf
)

# ── Constants ────────────────────────────────────────────────────────────────
$rights       = [System.Security.AccessControl.FileSystemRights]::FullControl
$inheritFlags = [System.Security.AccessControl.InheritanceFlags]"ContainerInherit, ObjectInherit"
$propFlags    = [System.Security.AccessControl.PropagationFlags]::None
$ruleType     = [System.Security.AccessControl.AccessControlType]::Allow

# Well-known SIDs (locale-independent)
# Using SIDs avoids issues with German vs English display names:
#   NT AUTHORITY\SYSTEM       = NT-AUTORITÄT\SYSTEM
#   BUILTIN\Administrators   = VORDEFINIERT\Administratoren
#   CREATOR OWNER             = ERSTELLER-BESITZER
#   Domain Admins             = Domänen-Admins
$script:SID_SYSTEM        = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')           # NT AUTHORITY\SYSTEM
$script:SID_ADMINISTRATORS = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-32-544')      # BUILTIN\Administrators
$script:SID_CREATOR_OWNER = New-Object System.Security.Principal.SecurityIdentifier('S-1-3-0')            # CREATOR OWNER

# Required SIDs: every one of these must have a FullControl ACE
$script:RequiredWellKnownSIDs = @(
    $script:SID_SYSTEM,
    $script:SID_ADMINISTRATORS
)

# Allowed SIDs: accepted if present, but not flagged when missing
$script:AllowedWellKnownSIDs = @(
    $script:SID_CREATOR_OWNER
)

# All accepted SIDs combined (for EXTRA detection)
$script:AllWellKnownSIDs = $script:RequiredWellKnownSIDs + $script:AllowedWellKnownSIDs

function Get-IdentitySID([System.Security.Principal.IdentityReference]$identity) {
    # Translate a display-name identity reference to its SID for locale-safe comparison
    try {
        return $identity.Translate([System.Security.Principal.SecurityIdentifier])
    } catch {
        return $null
    }
}

function New-FsRule([string]$Identity) {
    return New-Object System.Security.AccessControl.FileSystemAccessRule(
        $Identity, $rights, $inheritFlags, $propFlags, $ruleType
    )
}

function New-FsRuleFromSID([System.Security.Principal.SecurityIdentifier]$SID) {
    return New-Object System.Security.AccessControl.FileSystemAccessRule(
        $SID, $rights, $inheritFlags, $propFlags, $ruleType
    )
}

# ── Validation ───────────────────────────────────────────────────────────────
Import-Module ActiveDirectory -ErrorAction Stop

if (-not (Test-Path $RootFolder)) {
    Write-Error "Root folder '$RootFolder' does not exist."
    exit 1
}

# ── Counters ─────────────────────────────────────────────────────────────────
$totalFolders   = 0
$okFolders      = 0
$faultyFolders  = 0
$fixedFolders   = 0
$failedFolders  = 0
$skippedFolders = 0

# ── Main loop ────────────────────────────────────────────────────────────────
Get-ChildItem -Path $RootFolder -Directory | ForEach-Object {
    $folder     = $_.FullName
    $folderName = $_.Name
    $userId     = "$DomainName\$folderName"
    $totalFolders++

    # Skip folders that don't match an AD user
    try {
        $adUser = Get-ADUser -Filter "SamAccountName -eq '$folderName'" -ErrorAction Stop
        if (-not $adUser) {
            Write-Host "[SKIP]  $folder — no AD user '$folderName' found" -ForegroundColor DarkGray
            $skippedFolders++
            return  # next iteration in ForEach-Object
        }
    } catch {
        Write-Host "[SKIP]  $folder — could not look up AD user '$folderName': $($_.Exception.Message)" -ForegroundColor DarkGray
        $skippedFolders++
        return
    }

    try {
        $acl = Get-Acl -Path $folder

        # ── Resolve user SID ──────────────────────────────────────────
        $userSID = $adUser.SID

        # ── Check owner (by SID to handle unresolved SID strings) ────
        $currentOwner = $acl.Owner
        $ownerSID = try {
            (New-Object System.Security.Principal.NTAccount($currentOwner)).Translate(
                [System.Security.Principal.SecurityIdentifier]
            )
        } catch { $null }
        $ownerOk = ($ownerSID -and $ownerSID.Value -eq $userSID.Value)

        # ── Check inheritance ────────────────────────────────────────
        $inheritanceEnabled = -not $acl.AreAccessRulesProtected

        # ── Check ACEs (SID-based, locale-independent) ───────────────
        $aceIssues = @()

        # Build list of all accepted SIDs for this folder
        $acceptedSIDs = @($userSID.Value) + ($script:AllWellKnownSIDs | ForEach-Object { $_.Value })
        # Domain Admins — resolve the actual SID from AD
        $domainAdminsSID = $null
        try {
            $daGroup = Get-ADGroup -Filter "Name -eq 'Domain Admins'" -ErrorAction SilentlyContinue
            if (-not $daGroup) {
                $daGroup = Get-ADGroup -Filter "Name -eq 'Domänen-Admins'" -ErrorAction SilentlyContinue
            }
            if ($daGroup) {
                $domainAdminsSID = $daGroup.SID
                $acceptedSIDs += $domainAdminsSID.Value
            }
        } catch {}

        # Verify the user itself has FullControl Allow
        $userMatch = $acl.Access | Where-Object {
            $aceSID = Get-IdentitySID $_.IdentityReference
            $aceSID -and $aceSID.Value -eq $userSID.Value -and
            $_.FileSystemRights -band $rights -and
            $_.AccessControlType -eq 'Allow'
        }
        if (-not $userMatch) {
            $aceIssues += "MISSING  $userId"
        }

        # Verify each required well-known SID has FullControl Allow
        foreach ($reqSID in $script:RequiredWellKnownSIDs) {
            $displayName = $reqSID.Translate([System.Security.Principal.NTAccount]).Value
            $match = $acl.Access | Where-Object {
                $aceSID = Get-IdentitySID $_.IdentityReference
                $aceSID -and $aceSID.Value -eq $reqSID.Value -and
                $_.FileSystemRights -band $rights -and
                $_.AccessControlType -eq 'Allow'
            }
            if (-not $match) {
                $aceIssues += "MISSING  $displayName"
            }
        }

        # Verify Domain Admins is present
        if ($domainAdminsSID) {
            $daMatch = $acl.Access | Where-Object {
                $aceSID = Get-IdentitySID $_.IdentityReference
                $aceSID -and $aceSID.Value -eq $domainAdminsSID.Value -and
                $_.FileSystemRights -band $rights -and
                $_.AccessControlType -eq 'Allow'
            }
            if (-not $daMatch) {
                $aceIssues += "MISSING  Domain Admins ($($domainAdminsSID.Value))"
            }
        } else {
            $aceIssues += "MISSING  Domain Admins (could not resolve group)"
        }

        # Detect unexpected ACEs (ignore inherited ones, compare by SID)
        foreach ($ace in $acl.Access) {
            if ($ace.IsInherited) { continue }
            $aceSID = Get-IdentitySID $ace.IdentityReference
            if ($aceSID -and $aceSID.Value -notin $acceptedSIDs) {
                $aceIssues += "EXTRA    $($ace.IdentityReference.Value) ($($ace.FileSystemRights) / $($ace.AccessControlType))"
            }
        }

        # ── Filter issues when -ExtraOnly is set ────────────────────────
        if ($ExtraOnly) {
            $aceIssues = @($aceIssues | Where-Object { $_ -match '^EXTRA' })
        }

        # ── Report ───────────────────────────────────────────────────────
        $hasOwnerIssue = (-not $ownerOk) -and (-not $ExtraOnly -or $true)  # owner issues always shown
        $isFaulty = $hasOwnerIssue -or ($aceIssues.Count -gt 0) -or $inheritanceEnabled

        if ($isFaulty) {
            $faultyFolders++
            Write-Host ""
            Write-Host "[FAULT] $folder" -ForegroundColor Yellow

            if ($inheritanceEnabled) {
                Write-Host "  INHERITANCE ENABLED — parent ACEs propagate into this folder" -ForegroundColor Red
            }
            if ($hasOwnerIssue) {
                Write-Host "  Owner: $currentOwner  (expected: $userId)" -ForegroundColor Red
            }
            foreach ($issue in $aceIssues) {
                Write-Host "  $issue" -ForegroundColor Red
            }

            # ── Fix ──────────────────────────────────────────────────────
            if ($DisableInheritance -and $inheritanceEnabled) {
                try {
                    $fixAcl = Get-Acl -Path $folder
                    # Block inheritance, discard inherited ACEs
                    $fixAcl.SetAccessRuleProtection($true, $false)
                    # Remove inherited ACEs that are still in the object
                    $fixAcl.Access | Where-Object { $_.IsInherited } | ForEach-Object {
                        $fixAcl.RemoveAccessRule($_) | Out-Null
                    }
                    if ($WhatIf) {
                        Write-Host "  (WhatIf) Would disable inheritance on $folder" -ForegroundColor Cyan
                    } else {
                        Set-Acl -Path $folder -AclObject $fixAcl
                        Write-Host "  Inheritance disabled" -ForegroundColor Green
                        $fixedFolders++
                    }
                } catch {
                    Write-Warning "  Failed to disable inheritance on $folder : $($_.Exception.Message)"
                    $failedFolders++
                }
            }
            elseif ($RemoveExtra) {
                # Only remove unexpected ACEs — leave owner and missing permissions alone
                $extraAces = @()
                foreach ($ace in $acl.Access) {
                    if ($ace.IsInherited) { continue }
                    $aceSID = Get-IdentitySID $ace.IdentityReference
                    if ($aceSID -and $aceSID.Value -notin $acceptedSIDs) {
                        $extraAces += $ace
                    }
                }
                if ($extraAces.Count -gt 0) {
                    try {
                        $fixAcl = Get-Acl -Path $folder
                        foreach ($extraAce in $extraAces) {
                            $fixAcl.RemoveAccessRule($extraAce) | Out-Null
                            Write-Host "  Removing: $($extraAce.IdentityReference.Value)" -ForegroundColor Magenta
                        }
                        if ($WhatIf) {
                            Write-Host "  (WhatIf) Would remove $($extraAces.Count) extra ACE(s) on $folder" -ForegroundColor Cyan
                        } else {
                            Set-Acl -Path $folder -AclObject $fixAcl
                            Write-Host "  Removed $($extraAces.Count) extra ACE(s)" -ForegroundColor Green
                            $fixedFolders++
                        }
                    } catch {
                        Write-Warning "  Failed to remove extra ACEs on $folder : $($_.Exception.Message)"
                        $failedFolders++
                    }
                }
            }
            elseif ($AddMissing) {
                # Only add missing required ACEs — leave owner and extra permissions alone
                try {
                    $fixAcl = Get-Acl -Path $folder
                    $added = 0

                    # Check user ACE
                    $hasUser = $acl.Access | Where-Object {
                        $s = Get-IdentitySID $_.IdentityReference
                        $s -and $s.Value -eq $userSID.Value -and
                        $_.FileSystemRights -band $rights -and
                        $_.AccessControlType -eq 'Allow'
                    }
                    if (-not $hasUser) {
                        $fixAcl.AddAccessRule((New-FsRule -Identity $userId))
                        Write-Host "  Adding: $userId" -ForegroundColor Magenta
                        $added++
                    }

                    # Check required well-known SIDs
                    foreach ($reqSID in $script:RequiredWellKnownSIDs) {
                        $displayName = $reqSID.Translate([System.Security.Principal.NTAccount]).Value
                        $has = $acl.Access | Where-Object {
                            $s = Get-IdentitySID $_.IdentityReference
                            $s -and $s.Value -eq $reqSID.Value -and
                            $_.FileSystemRights -band $rights -and
                            $_.AccessControlType -eq 'Allow'
                        }
                        if (-not $has) {
                            $fixAcl.AddAccessRule((New-FsRuleFromSID -SID $reqSID))
                            Write-Host "  Adding: $displayName" -ForegroundColor Magenta
                            $added++
                        }
                    }

                    # Check Domain Admins
                    if ($domainAdminsSID) {
                        $hasDA = $acl.Access | Where-Object {
                            $s = Get-IdentitySID $_.IdentityReference
                            $s -and $s.Value -eq $domainAdminsSID.Value -and
                            $_.FileSystemRights -band $rights -and
                            $_.AccessControlType -eq 'Allow'
                        }
                        if (-not $hasDA) {
                            $fixAcl.AddAccessRule((New-FsRuleFromSID -SID $domainAdminsSID))
                            $daName = $domainAdminsSID.Translate([System.Security.Principal.NTAccount]).Value
                            Write-Host "  Adding: $daName" -ForegroundColor Magenta
                            $added++
                        }
                    }

                    if ($added -gt 0) {
                        if ($WhatIf) {
                            Write-Host "  (WhatIf) Would add $added missing ACE(s) on $folder" -ForegroundColor Cyan
                        } else {
                            Set-Acl -Path $folder -AclObject $fixAcl
                            Write-Host "  Added $added missing ACE(s)" -ForegroundColor Green
                            $fixedFolders++
                        }
                    }
                } catch {
                    Write-Warning "  Failed to add missing ACEs on $folder : $($_.Exception.Message)"
                    $failedFolders++
                }
            }
            elseif ($Fix) {
                try {
                    # Build a clean ACL: protected from inheritance, only expected ACEs
                    $newAcl = Get-Acl -Path $folder
                    $newAcl.SetAccessRuleProtection($true, $false)   # protect, don't keep inherited

                    # Remove all existing explicit ACEs
                    $newAcl.Access | ForEach-Object {
                        $newAcl.RemoveAccessRule($_) | Out-Null
                    }

                    # Add expected rules (using SIDs for locale independence)
                    $newAcl.AddAccessRule((New-FsRule -Identity $userId))
                    foreach ($reqSID in $script:RequiredWellKnownSIDs) {
                        $newAcl.AddAccessRule((New-FsRuleFromSID -SID $reqSID))
                    }

                    # Domain Admins
                    if ($domainAdminsSID) {
                        $newAcl.AddAccessRule((New-FsRuleFromSID -SID $domainAdminsSID))
                    } else {
                        Write-Warning "  Could not resolve Domain Admins group"
                    }

                    # Set owner
                    $newAcl.SetOwner($userSID)

                    if ($WhatIf) {
                        Write-Host "  (WhatIf) Would reset ACL and owner on $folder" -ForegroundColor Cyan
                    } else {
                        Set-Acl -Path $folder -AclObject $newAcl
                        Write-Host "  FIXED" -ForegroundColor Green
                        $fixedFolders++
                    }
                }
                catch {
                    Write-Warning "  Failed to fix $folder : $($_.Exception.Message)"
                    $failedFolders++
                }
            }
        } else {
            $okFolders++
            Write-Verbose "[OK]    $folder"
        }
    }
    catch {
        Write-Warning "Failed to read ACL on $folder : $($_.Exception.Message)"
        $failedFolders++
    }
}

# ── Summary ──────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "═══ Summary ═══" -ForegroundColor White
Write-Host "  Total folders : $totalFolders"
Write-Host "  Skipped       : $skippedFolders" -ForegroundColor DarkGray
Write-Host "  OK            : $okFolders"  -ForegroundColor Green
Write-Host "  Faulty        : $faultyFolders" -ForegroundColor $(if ($faultyFolders -gt 0) { "Yellow" } else { "Green" })
if ($Fix -or $RemoveExtra -or $AddMissing -or $DisableInheritance) {
    Write-Host "  Fixed         : $fixedFolders"  -ForegroundColor Green
    Write-Host "  Failed        : $failedFolders" -ForegroundColor $(if ($failedFolders -gt 0) { "Red" } else { "Green" })
    if ($WhatIf) {
        Write-Host "  (WhatIf mode — no changes were written)" -ForegroundColor Cyan
    }
} else {
    Write-Host "  Run with -Fix to repair faulty folders." -ForegroundColor Cyan
}
