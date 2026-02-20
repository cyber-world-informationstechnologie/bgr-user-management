"""Build the HTML summary email for onboarded and offboarded users."""

from dataclasses import dataclass


@dataclass
class EmailRow:
    begin: str
    full_name: str
    email: str
    abbreviation: str
    phone: str
    room: str
    team: str
    job_title_resolved: str
    birth_date: str
    kostenstelle: str
    berufstraeger: str
    stundensatz: str
    fte: str


@dataclass
class OffboardingEmailRow:
    exit_date: str
    full_name: str
    email: str
    abbreviation: str
    phone: str
    room: str
    team: str
    birth_date: str
    kostenstelle: str


_ONBOARDING_TABLE_HEADER = """\
<table style="border-collapse: collapse; width: 100%; max-width: 900px;">
<thead>
  <tr>
    <th style="padding: 8px; border: 1px solid #ddd;">Eintritt</th>
    <th style="padding: 8px; white-space: nowrap; border: 1px solid #ddd;">Titel und Name</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Email</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Kürzel</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Telefon</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Zimmer</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Team</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Stellenbezeichnung</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Geburtsdatum</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Kostenstelle</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Berufsträger</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Stundensatz</th>
    <th style="padding: 8px; border: 1px solid #ddd;">FTE</th>
  </tr>
</thead>
<tbody>
"""

_ONBOARDING_ROW_TEMPLATE = """\
<tr>
  <td style="padding: 8px; border: 1px solid #ddd;"><strong>{begin}</strong></td>
  <td style="padding: 8px; border: 1px solid #ddd; white-space: nowrap;">{full_name}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{email}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{abbreviation}</td>
  <td style="padding: 8px; border: 1px solid #ddd; white-space: nowrap;">{phone}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{room}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{team}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{job_title_resolved}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{birth_date}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{kostenstelle}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{berufstraeger}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{stundensatz}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{fte}</td>
</tr>
"""

_OFFBOARDING_TABLE_HEADER = """\
<table style="border-collapse: collapse; width: 100%; max-width: 900px;">
<thead>
  <tr>
    <th style="padding: 8px; border: 1px solid #ddd;">Austrittsdatum</th>
    <th style="padding: 8px; white-space: nowrap; border: 1px solid #ddd;">Titel und Name</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Email</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Kürzel</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Telefon</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Zimmer</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Team</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Geburtsdatum</th>
    <th style="padding: 8px; border: 1px solid #ddd;">Kostenstelle</th>
  </tr>
</thead>
<tbody>
"""

_OFFBOARDING_ROW_TEMPLATE = """\
<tr>
  <td style="padding: 8px; border: 1px solid #ddd;"><strong>{exit_date}</strong></td>
  <td style="padding: 8px; border: 1px solid #ddd; white-space: nowrap;">{full_name}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{email}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{abbreviation}</td>
  <td style="padding: 8px; border: 1px solid #ddd; white-space: nowrap;">{phone}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{room}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{team}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{birth_date}</td>
  <td style="padding: 8px; border: 1px solid #ddd;">{kostenstelle}</td>
</tr>
"""

_TABLE_FOOTER = """\
</tbody>
</table>
"""


def build_onboarding_email(rows: list[EmailRow]) -> str:
    """Build the full onboarding summary HTML email body.

    Returns empty string if no rows are provided.
    """
    if not rows:
        return ""

    html = "<h2><span style='font-size: 12px;'>Bevorstehende Eintritte:</span></h2>\n"
    html += _ONBOARDING_TABLE_HEADER

    for row in rows:
        html += _ONBOARDING_ROW_TEMPLATE.format(
            begin=row.begin,
            full_name=row.full_name,
            email=row.email,
            abbreviation=row.abbreviation,
            phone=row.phone,
            room=row.room,
            team=row.team,
            job_title_resolved=row.job_title_resolved,
            birth_date=row.birth_date,
            kostenstelle=row.kostenstelle,
            berufstraeger=row.berufstraeger,
            stundensatz=row.stundensatz,
            fte=row.fte,
        )

    html += _TABLE_FOOTER
    return html


def build_offboarding_email(rows: list[OffboardingEmailRow]) -> str:
    """Build the full offboarding summary HTML email body.

    Returns empty string if no rows are provided.
    """
    if not rows:
        return ""

    html = "<h2><span style='font-size: 12px;'>Durchgeführte Austritte:</span></h2>\n"
    html += _OFFBOARDING_TABLE_HEADER

    for row in rows:
        html += _OFFBOARDING_ROW_TEMPLATE.format(
            exit_date=row.exit_date,
            full_name=row.full_name,
            email=row.email,
            abbreviation=row.abbreviation,
            phone=row.phone,
            room=row.room,
            team=row.team,
            birth_date=row.birth_date,
            kostenstelle=row.kostenstelle,
        )

    html += _TABLE_FOOTER
    return html
