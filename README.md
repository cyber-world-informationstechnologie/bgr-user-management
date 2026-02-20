# bgr-user-management

Automatisiertes Benutzer-Onboarding für Binder Grösswang (BGR). Ursprünglich als Power Automate + Power Automate Desktop Flow umgesetzt, wurde der Prozess wegen Unzuverlässigkeit nach Python migriert.

Das Skript läuft direkt auf dem Exchange-Server und erstellt vollautomatisch neue Benutzerkonten in Active Directory, legt Exchange-Postfächer an, setzt AD-Attribute, weist Gruppen zu, erstellt Profilordner und versendet eine Zusammenfassungs-E-Mail.

---

## Was macht das Skript?

Der Ablauf besteht aus vier Hauptschritten:

### 1. Neue Mitarbeiter aus LOGA laden
Das Skript ruft die **LOGA HR-Schnittstelle** (P&I Scout API) auf und erhält eine Liste aller bevorstehenden Eintritte. Die Daten kommen als JSON-Array, wobei jeder Eintrag 20 Felder enthält (Personalnummer, Name, Titel, Kürzel, Zimmer, Team, Stellenbezeichnung, usw.).

### 2. Prüfen, ob der Benutzer bereits existiert
Für jeden Benutzer wird per PowerShell im Active Directory geprüft, ob ein Konto mit dem Kürzel (SamAccountName) bereits vorhanden ist.

- **Neuer Benutzer** → Vollständige Provisionierung (Postfach + Attribute + Gruppen + Profilordner)
- **Bereits vorhandener Benutzer** → **Abgleich (Reconcile):** Die Postfach-Erstellung wird übersprungen, aber AD-Attribute, Gruppen und Profilordner werden erneut gesetzt. Dadurch werden fehlende oder fehlerhafte Werte automatisch korrigiert. Alle Operationen sind idempotent — ein wiederholter Lauf auf einem vollständig provisionierten Benutzer ist sicher und ändert nichts Ungewolltes.

### 3. Benutzer anlegen (außer Reinigungskräfte)
Für neue Benutzer, die **nicht** die Stelle „Mitarbeiter*in Reinigung" haben, werden folgende Schritte ausgeführt:

- **Remote-Mailbox erstellen** — Über `New-RemoteMailbox` wird auf dem Exchange-Server ein AD-Konto erstellt, das auf ein Cloud-Postfach in Exchange Online geroutet wird (via `RemoteRoutingAddress` auf `*.mail.onmicrosoft.com`). Das Konto wird in die korrekte Organisationseinheit (OU) einsortiert, die sich aus der Stellenbezeichnung ergibt (z.B. Partner → `OU=Partner-in`, Sekretariat → `OU=Sekretariat`).

- **AD-Attribute setzen** — Adresse, Telefon, Titel, Firma, IP-Telefon, Fax-Nummer, Title-Prefix/Suffix als Extension Attributes. Die Adresse wird automatisch anhand des Zimmers bestimmt (Zimmer beginnt mit „I" → Innsbruck, sonst Wien).

- **Manager setzen** — Die letzten 3 Zeichen des Team-Feldes ergeben das Kürzel des Vorgesetzten. Daraus wird der Manager in AD gesetzt und zusätzlich in Extension Attributes 14 und 15 gespeichert.

- **AD-Gruppen zuweisen** — Jeder Benutzer bekommt:
  - **Basisgruppen** (alle Benutzer): `acc.Office365BusinessPremium`, `acc.M365Exchange`, `WorksiteLicencedUSers`, `Alle`, `acc.BGR-AI-Plattform`, `WorkSiteUsers`
  - **Standortgruppe** basierend auf dem Zimmer: z.B. `VIE_3OG` (3. OG Wien) oder `IBK_1OG` (Innsbruck)
  - **OU-Gruppe** basierend auf der Organisationseinheit: z.B. `OU_PARTNER`, `OU_SEKR`, `OU_RAA`
  - **Team-Gruppe** im Format `Team-<Manager-Kürzel>`

- **Profilordner erstellen** — Auf `\\bgr\dfs\Profile\<Kürzel>` wird ein Ordner erstellt. Der Benutzer wird als Besitzer gesetzt und erhält Vollzugriff, ebenso die Administratoren-Gruppe.

### 4. Zusammenfassungs-E-Mail senden
Am Ende wird eine HTML-E-Mail mit einer Tabelle aller verarbeiteten Benutzer versendet (Eintritt, Name, E-Mail, Kürzel, Telefon, Zimmer, Team, Stellenbezeichnung, Geburtsdatum, Kostenstelle, Berufsträger, Stundensatz, FTE). Der Versand erfolgt per direktem SMTP über den gewhitelisteten Connector — keine Authentifizierung notwendig.

---

## Voraussetzungen

Das Skript muss auf einer Maschine laufen, die folgende Bedingungen erfüllt:

| Voraussetzung | Details |
|---|---|
| **Exchange-Server** | Das Skript verwendet `New-RemoteMailbox` (erstellt AD-Konto + Remote-Routing zu Exchange Online). Es muss auf dem Exchange-Server selbst oder einer Maschine mit Exchange Management Shell laufen. |
| **AD PowerShell-Modul** | Muss installiert sein: `Install-WindowsFeature RSAT-AD-PowerShell` |
| **Exchange PowerShell Snap-In** | Wird im Skript automatisch geladen (`Add-PSSnapin Microsoft.Exchange.Management.PowerShell.SnapIn`) |
| **SMTP-Connector** | Die IP-Adresse des Servers muss auf dem Connector `bindergroesswang-at.mail.protection.outlook.com` gewhitelistet sein (Port 25, ohne Auth) |
| **Python 3.11+** | [python.org/downloads](https://www.python.org/downloads/) — bei der Installation „Add to PATH" ankreuzen |
| **Netzwerkzugriff** | Zugriff auf die LOGA-API (`BGR.pi-asp.de`) und den DFS-Share (`\\bgr\dfs\Profile`) |

---

## Ersteinrichtung (Schritt für Schritt)

### 1. Repository klonen

```powershell
cd C:\Tasks
git clone https://github.com/cyber-world-informationstechnologie/bgr-user-management.git User-Management
cd User-Management
```

### 2. Python Virtual Environment erstellen

Ein Virtual Environment (venv) isoliert die Python-Pakete dieses Projekts vom restlichen System. So gibt es keine Konflikte mit anderen Tools.

```powershell
python -m venv .venv
```

### 3. Abhängigkeiten installieren

```powershell
.\.venv\Scripts\Activate.ps1
pip install -e .
```

> **Was bedeutet `pip install -e .`?**
> Das liest die Datei `pyproject.toml` und installiert alle dort definierten Abhängigkeiten (`requests`, `pydantic`, `python-dotenv`, etc.) in das venv. Das `-e` steht für „editable" — Änderungen am Code werden sofort wirksam, ohne neu installieren zu müssen.

### 4. Konfiguration anlegen

```powershell
Copy-Item .env.example .env
```

Dann die Datei `.env` bearbeiten und die fehlenden Werte ausfüllen:

```dotenv
# LOGA API — den base64-kodierten Job-File-Content eintragen
LOGA_JOB_FILE_CONTENT=<Wert von Markus erfragen>

# Restliche Werte sind bereits korrekt vorausgefüllt.
# Zum Testen DRY_RUN=true lassen (Standard).
```

| Variable | Beschreibung |
|---|---|
| `LOGA_API_URL` | URL der LOGA Scout Report API (vorausgefüllt) |
| `LOGA_JOB_FILE_CONTENT` | Base64-kodierter Schlüssel für den LOGA-Report — **vertraulich, nicht ins Git committen!** |
| `SMTP_HOST` | SMTP-Server für E-Mail-Versand (vorausgefüllt) |
| `SMTP_PORT` | SMTP-Port, Standard 25 (vorausgefüllt) |
| `NOTIFICATION_EMAIL_TO` | Empfänger der Zusammenfassungs-E-Mail |
| `NOTIFICATION_EMAIL_FROM` | Absender-Adresse |
| `ERROR_NOTIFICATION_EMAIL` | Empfänger bei Fehlern |
| `PROFILE_BASE_PATH` | UNC-Pfad zum Profilordner-Share |
| `DEFAULT_PASSWORD` | Standardpasswort für neue Postfächer |
| `REMOTE_ROUTING_DOMAIN` | Remote-Routing-Domain für Exchange Online (z.B. `bindergroesswang-at.mail.onmicrosoft.com`) |
| `DRY_RUN` | `true` = nur loggen, nichts ändern; `false` = produktiv ausführen |

### 5. Testlauf (Dry Run)

```powershell
.\.venv\Scripts\python.exe main.py
```

Im Dry-Run-Modus wird nichts verändert. Das Skript loggt, was es tun würde:
- Welche Benutzer aus LOGA kommen
- Welche bereits in AD existieren
- Welche Postfächer, Attribute, Gruppen und Ordner es anlegen würde
- Welche E-Mail es senden würde

### 6. Produktivbetrieb

In der `.env` den Wert ändern:

```dotenv
DRY_RUN=false
```

Dann erneut ausführen:

```powershell
.\.venv\Scripts\python.exe main.py
```

---

## Als geplanten Task einrichten (Task Scheduler)

Damit das Skript automatisch läuft (z.B. täglich um 7:00):

| Feld | Wert |
|---|---|
| Programm | `C:\Tasks\User-Management\.venv\Scripts\python.exe` |
| Argumente | `C:\Tasks\User-Management\main.py` |
| Starten in | `C:\Tasks\User-Management` |
| Ausführen als | Ein Service-Account mit AD/Exchange-Berechtigungen |

> **Wichtig:** „Starten in" muss auf das Projektverzeichnis zeigen, weil das Skript dort die `.env`-Datei sucht.

---

## Aktualisierung nach Code-Änderungen

```powershell
cd C:\Tasks\User-Management
git pull
.\.venv\Scripts\Activate.ps1
pip install -e .
```

Falls nur Python-Dateien geändert wurden (keine neuen Abhängigkeiten), reicht `git pull` alleine — das `-e` (editable) install sorgt dafür, dass Änderungen sofort wirksam sind.

---

## Projektstruktur

```
src/
  config.py              Einstellungen aus .env (Pydantic Settings)
  models.py              OnboardingUser Datenmodell (LOGA-Felder → benannte Attribute)
  loga_client.py         LOGA HR API Client (holt neue Mitarbeiter)
  ad_client.py           AD/Exchange-Provisionierung via PowerShell (Postfach, Attribute, Gruppen, Profilordner)
  smtp_client.py         E-Mail-Versand via SMTP (gewhitelisteter Connector, ohne Auth)
  job_title_resolver.py  Geschlechtsspezifische Stellenbezeichnung (z.B. „Partner*in" → „Partner" / „Partnerin")
  ou_resolver.py         Stellenbezeichnung → AD Organisationseinheit (OU)
  group_resolver.py      Ermittlung der AD-Gruppenmitgliedschaften
  email_builder.py       HTML-Zusammenfassungstabelle für die Onboarding-E-Mail
  onboarding.py          Hauptablauf (Orchestrierung aller Schritte)
main.py                  Einstiegspunkt (python main.py)
.env.example             Vorlage für die Konfiguration
.env                     Tatsächliche Konfiguration (nicht im Git!)
pyproject.toml           Python-Projektdefinition und Abhängigkeiten
```

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Sicherstellen, dass `pip install -e .` im venv ausgeführt wurde |
| `PowerShell-Fehler: Get-ADUser not recognized` | AD PowerShell-Modul installieren: `Install-WindowsFeature RSAT-AD-PowerShell` |
| `New-RemoteMailbox not recognized` | Exchange Snap-In nicht verfügbar — Skript muss auf dem Exchange-Server laufen |
| `SMTP connection refused` | Server-IP nicht auf dem Connector gewhitelistet, oder Port 25 blockiert |
| `LOGA API gibt leere Daten zurück` | `LOGA_JOB_FILE_CONTENT` in `.env` prüfen |
| Benutzer wird übersprungen obwohl er neu ist | AD-Kürzel (SamAccountName) existiert bereits — manuell im AD prüfen |
| Nach Fehler erneut ausführen: Postfach existiert schon | Das ist normal — das Skript erkennt den Benutzer als „vorhanden" und führt nur den Abgleich durch (Attribute, Gruppen, Profilordner) |
| `git pull` schlägt fehl mit „unrelated histories" | `git fetch origin` dann `git reset --hard origin/main` — danach ist das lokale Repo synchron |
