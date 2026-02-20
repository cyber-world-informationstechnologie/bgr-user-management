#!/usr/bin/env python3
"""Test CSV parsing with multi-line rows."""

from src.models import OffboardingUser

# Test data (with multi-line rows)
csv_data = """Kürzel;Titel;Vorname;Nachname;Titel nach dem Namen;Vertragsbeginn;Vertragsende;Zimmer;Geburtsdatum;Handy;E-Mail;Telefon;Kostenstelle;Stundensatz;Berufsträger;Team;FTE;Stellenbezeichnung;Letzter Arbeitstag
SHO;Mag.;Sung-Hyek;Hong;;05.12.2022;28.02.2026;609/1;06.09.1996;+43 664 80 534 449;hong@bindergroesswang.at;+43 1 534 80 449;210024;;Ja;Partner*in FKH;1,00000;Rechtsanwaltsanwärter*in;13.02.2026
C38;;Anna;Zierler;;01.02.2026;28.02.2026;614/1;29.01.2004;;zierler@bindergroesswang.at;+43 1 534 80 343;240062
;;Nein;Partner*in CWI;1,00000;Juristische*r Ferialpraktikant*in;25.02.2026"""

# Simulate the multi-line parsing
lines = csv_data.strip().split('\n')
header = lines[0].split(';')
print(f"Header has {len(header)} columns")
print(f"Header: {header}\n")

# Use the same logic as in _parse_csv_response (updated version)
rows = []
current_row = []
expected_cols = len(header)

for line_idx, line in enumerate(lines[1:], start=2):
    parts = line.split(';')
    
    print(f"Line {line_idx}: {len(parts)} fields, starts with '{parts[0]}'")
    
    # Check if this line starts a new record (non-empty Kürzel/abbreviation)
    is_new_record = parts and parts[0].strip() != ""
    
    if is_new_record and current_row:
        # Save current row and start new
        rows.append(current_row)
        current_row = parts
        print(f"  -> Saved row, started new one")
    elif is_new_record:
        # New record with no current row
        current_row = parts
        print(f"  -> Created new row")
    else:
        # Continuation
        if current_row:
            current_row.extend(parts)
            print(f"  -> Appended to row (now {len(current_row)} fields)")
        else:
            current_row = parts

if current_row:
    rows.append(current_row)
    print(f"Final row: {len(current_row)} fields")

print(f"\nTotal rows parsed: {len(rows)}")

# Test instantiation
for i, row in enumerate(rows):
    print(f"\nRow {i+1}: {len(row)} fields")
    # Normalize
    normalized = row[:expected_cols] if len(row) > expected_cols else row + [''] * (expected_cols - len(row))
    
    try:
        user = OffboardingUser.from_loga_row(normalized)
        print(f"  ✓ {user.full_display_name} ({user.email})")
        print(f"    Exit date: {user.exit_date}")
        print(f"    Abbreviation: {user.abbreviation}")
    except Exception as e:
        print(f"  ✗ Error: {e}")

