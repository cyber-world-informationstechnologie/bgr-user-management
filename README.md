# bgr-user-management

Automated user onboarding for BGR — migrated from Power Automate to Python.

## What it does

1. Fetches upcoming new employees from the **LOGA HR system** (P&I Scout API)
2. Checks each user against **Microsoft Entra ID** (Azure AD) via Graph API
3. For users that don't exist yet (skipping cleaning staff):
   - Creates a local **Exchange mailbox** + AD account (runs on the Exchange server)
   - Sets AD attributes (address, phone, title, manager, extension attributes)
   - Assigns AD groups (base groups + location + OU-based + team group)
   - Creates the **profile folder** on the DFS share with proper ACLs
4. Sends a **summary email** listing all onboarded users

## Prerequisites

- **Runs on the Exchange server** (uses `New-Mailbox` directly, not `New-RemoteMailbox`)
- Active Directory PowerShell module (`RSAT-AD-PowerShell`)
- Exchange Management Shell / snap-in
- Python 3.11+

## Setup

```bash
# Install dependencies
pip install -e .

# Copy and fill in environment variables
cp .env.example .env
```

### Required Entra ID App Registration permissions

- `User.Read.All` (existence check only)
- `Mail.Send`

## Usage

```bash
# Dry run (default) — logs what would happen without making changes
python main.py

# Production run
# Set DRY_RUN=false in .env, then:
python main.py
```

## Project structure

```
src/
  config.py              Settings from .env
  models.py              OnboardingUser data model
  loga_client.py         LOGA HR API client
  graph_client.py        Graph API (email + user existence check only)
  ad_client.py           On-premise AD/Exchange provisioning via PowerShell
  job_title_resolver.py  Gender-aware job title mapping
  ou_resolver.py         Position → AD OU mapping
  group_resolver.py      AD group membership resolution
  email_builder.py       HTML summary email builder
  onboarding.py          Main orchestration
main.py                  Entry point
```
