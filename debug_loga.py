"""Fetch and verify LOGA data parsing against the real API."""
import logging
import os

from dotenv import load_dotenv

load_dotenv()
logging.basicConfig(level=logging.DEBUG)

from src.loga_client import fetch_new_users, fetch_exiting_users
from src.email_builder import OffboardingEmailRow, build_offboarding_email

print("=== OFFBOARDING ===")
exiting = fetch_exiting_users()
print(f"\nParsed {len(exiting)} offboarding users:")
email_rows = []
for u in exiting:
    print(f"\n  {u.full_display_name}")
    print(f"    Abbreviation: {u.abbreviation}, Email: {u.email}")
    print(f"    Room: {u.room}, Phone: {u.phone}, Birth: {u.birth_date}")
    print(f"    Team: {u.team}, Kostenstelle: {u.kostenstelle}")
    print(f"    Berufsträger: {u.berufstraeger}, FTE: {u.umf_besetz}")
    print(f"    Begin: {u.begin_date}, End: {u.end_date}, Exit: {u.exit_date}")
    print(f"    Position: {u.position}, Kommentar: {u.kommentar}")

    email_rows.append(OffboardingEmailRow(
        exit_date=u.exit_date,
        end_date=u.end_date,
        full_name=u.full_display_name,
        email=u.email,
        abbreviation=u.abbreviation,
        phone=u.phone,
        room=u.room,
        team=u.team,
        birth_date=u.birth_date,
        kostenstelle=u.kostenstelle,
        berufstraeger=u.berufstraeger,
        fte=u.umf_besetz,
        kommentar=u.kommentar,
    ))

print("\n=== EMAIL HTML ===")
html = build_offboarding_email(email_rows)
print(html)

print("\n=== ONBOARDING ===")
new = fetch_new_users()
print(f"\nParsed {len(new)} onboarding users:")
for u in new:
    print(f"\n  {u.full_display_name}")
    print(f"    PNR: {u.personalnummer}, Abbreviation: {u.abbreviation}")
    print(f"    Email: {u.email}, Phone: {u.phone}")
    print(f"    Room: {u.room}, Birth: {u.birth_date}, Gender: {u.geschlecht}")
    print(f"    Team: {u.team}, Kostenstelle: {u.kostenstelle}")
    print(f"    Berufsträger: {u.berufstraeger}, FTE: {u.umf_besetz}")
    print(f"    Position: {u.position}, Stundensatz: {u.stundensatz}")
