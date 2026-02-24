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
    end_date: str  # Vertragsende
    full_name: str
    email: str
    abbreviation: str
    phone: str
    room: str
    team: str
    birth_date: str
    kostenstelle: str
    berufstraeger: str
    fte: str
    kommentar: str


_CELL_STYLE = "padding: 8px; border: 1px solid #ddd; font-family: Arial, sans-serif; font-size: 10pt;"
_CELL_STYLE_NOWRAP = "padding: 8px; border: 1px solid #ddd; font-family: Arial, sans-serif; font-size: 10pt; white-space: nowrap;"

_ONBOARDING_TABLE_HEADER = f"""\
<table style="border-collapse: collapse; width: 100%; max-width: 900px; font-family: Arial, sans-serif; font-size: 10pt;">
<thead>
  <tr>
    <th style="{_CELL_STYLE}">Eintritt</th>
    <th style="{_CELL_STYLE_NOWRAP}">Titel und Name</th>
    <th style="{_CELL_STYLE}">Email</th>
    <th style="{_CELL_STYLE}">Kürzel</th>
    <th style="{_CELL_STYLE}">Telefon</th>
    <th style="{_CELL_STYLE}">Zimmer</th>
    <th style="{_CELL_STYLE}">Team</th>
    <th style="{_CELL_STYLE}">Stellenbezeichnung</th>
    <th style="{_CELL_STYLE}">Geburtsdatum</th>
    <th style="{_CELL_STYLE}">Kostenstelle</th>
    <th style="{_CELL_STYLE}">Berufsträger</th>
    <th style="{_CELL_STYLE}">Stundensatz</th>
    <th style="{_CELL_STYLE}">FTE</th>
  </tr>
</thead>
<tbody>
"""

_ONBOARDING_ROW_TEMPLATE = f"""\
<tr>
  <td style="{_CELL_STYLE}"><strong>{{begin}}</strong></td>
  <td style="{_CELL_STYLE_NOWRAP}">{{full_name}}</td>
  <td style="{_CELL_STYLE}">{{email}}</td>
  <td style="{_CELL_STYLE}">{{abbreviation}}</td>
  <td style="{_CELL_STYLE_NOWRAP}">{{phone}}</td>
  <td style="{_CELL_STYLE}">{{room}}</td>
  <td style="{_CELL_STYLE}">{{team}}</td>
  <td style="{_CELL_STYLE}">{{job_title_resolved}}</td>
  <td style="{_CELL_STYLE}">{{birth_date}}</td>
  <td style="{_CELL_STYLE}">{{kostenstelle}}</td>
  <td style="{_CELL_STYLE}">{{berufstraeger}}</td>
  <td style="{_CELL_STYLE}">{{stundensatz}}</td>
  <td style="{_CELL_STYLE}">{{fte}}</td>
</tr>
"""

_OFFBOARDING_TABLE_HEADER = f"""\
<table style="border-collapse: collapse; width: 100%; max-width: 900px; font-family: Arial, sans-serif; font-size: 10pt;">
<thead>
  <tr>
    <th style="{_CELL_STYLE}">Letzter Arbeitstag</th>
    <th style="{_CELL_STYLE}">Vertragsende</th>
    <th style="{_CELL_STYLE_NOWRAP}">Titel und Name</th>
    <th style="{_CELL_STYLE}">Email</th>
    <th style="{_CELL_STYLE}">Kürzel</th>
    <th style="{_CELL_STYLE}">Telefon</th>
    <th style="{_CELL_STYLE}">Zimmer</th>
    <th style="{_CELL_STYLE}">Team</th>
    <th style="{_CELL_STYLE}">Geburtsdatum</th>
    <th style="{_CELL_STYLE}">Kostenstelle</th>
    <th style="{_CELL_STYLE}">Berufsträger</th>
    <th style="{_CELL_STYLE}">FTE</th>
    <th style="{_CELL_STYLE}">Kommentar</th>
  </tr>
</thead>
<tbody>
"""

_OFFBOARDING_ROW_TEMPLATE = f"""\
<tr>
  <td style="{_CELL_STYLE}"><strong>{{exit_date}}</strong></td>
  <td style="{_CELL_STYLE}">{{end_date}}</td>
  <td style="{_CELL_STYLE_NOWRAP}">{{full_name}}</td>
  <td style="{_CELL_STYLE}">{{email}}</td>
  <td style="{_CELL_STYLE}">{{abbreviation}}</td>
  <td style="{_CELL_STYLE_NOWRAP}">{{phone}}</td>
  <td style="{_CELL_STYLE}">{{room}}</td>
  <td style="{_CELL_STYLE}">{{team}}</td>
  <td style="{_CELL_STYLE}">{{birth_date}}</td>
  <td style="{_CELL_STYLE}">{{kostenstelle}}</td>
  <td style="{_CELL_STYLE}">{{berufstraeger}}</td>
  <td style="{_CELL_STYLE}">{{fte}}</td>
  <td style="{_CELL_STYLE}">{{kommentar}}</td>
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
            end_date=row.end_date,
            full_name=row.full_name,
            email=row.email,
            abbreviation=row.abbreviation,
            phone=row.phone,
            room=row.room,
            team=row.team,
            birth_date=row.birth_date,
            kostenstelle=row.kostenstelle,
            berufstraeger=row.berufstraeger,
            fte=row.fte,
            kommentar=row.kommentar,
        )

    html += _TABLE_FOOTER
    return html
