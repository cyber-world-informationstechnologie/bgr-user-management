# bgr-user-management

Automatisiertes Benutzer-Onboarding und -Offboarding für Binder Grösswang (BGR). Ursprünglich als Power Automate + Power Automate Desktop Flow umgesetzt, wurde der Prozess wegen Unzuverlässigkeit nach Python migriert.

Das Skript läuft direkt auf dem Exchange-Server und erstellt vollautomatisch neue Benutzerkonten in Active Directory, legt Exchange-Postfächer an, setzt AD-Attribute, weist Gruppen zu, erstellt Profilordner und versendet eine Zusammenfassungs-E-Mail.

Beim Offboarding werden Benutzer (am Tag nach dem Austrittsdatum) automatisch deaktiviert, ihre Postfächer in Shared Mailboxes umgewandelt, E-Mail-Weiterleitungen eingerichtet und alle Gruppenzugehörigkeiten entfernt.

---

## Was macht das Skript?

Das Skript unterstützt zwei Prozesse:

### 🟢 **ONBOARDING** — Neue Mitarbeiter aufnehmen

Der Ablauf besteht aus vier Hauptschritten:

#### 1. Neue Mitarbeiter aus LOGA laden
Das Skript ruft die **LOGA HR-Schnittstelle** (P&I Scout API) auf und erhält eine Liste aller bevorstehenden Eintritte. Die Daten kommen als JSON-Array, wobei jeder Eintrag 20 Felder enthält (Personalnummer, Name, Titel, Kürzel, Zimmer, Team, Stellenbezeichnung, usw.).

#### 2. Prüfen, ob der Benutzer bereits existiert
Für jeden Benutzer wird per PowerShell im Active Directory geprüft, ob ein Konto mit dem Kürzel (SamAccountName) bereits vorhanden ist.

- **Neuer Benutzer** → Vollständige Provisionierung (Postfach + Attribute + Gruppen + Profilordner)
- **Bereits vorhandener Benutzer** → **Abgleich (Reconcile):** Die Postfach-Erstellung wird übersprungen, aber AD-Attribute, Gruppen und Profilordner werden erneut gesetzt. Dadurch werden fehlende oder fehlerhafte Werte automatisch korrigiert. Alle Operationen sind idempotent — ein wiederholter Lauf auf einem vollständig provisionierten Benutzer ist sicher.

#### 3. Benutzer anlegen (außer Reinigungskräfte)
Für neue Benutzer, die **nicht** die Stelle „Mitarbeiter*in Reinigung" haben, werden folgende Schritte ausgeführt:

- **Remote-Mailbox erstellen** — Über `New-RemoteMailbox` wird auf dem Exchange-Server ein AD-Konto erstellt, das auf ein Cloud-Postfach in Exchange Online geroutet wird (via `RemoteRoutingAddress` auf `*.mail.onmicrosoft.com`). Das Konto wird in die korrekte Organisationseinheit (OU) einsortiert, die sich aus der Stellenbezeichnung ergibt (z.B. Partner → `OU=Partner-in`, Sekretariat → `OU=Sekretariat`).

- **AD-Attribute setzen** — Adresse, Telefon, Titel, Firma, IP-Telefon, Fax-Nummer, Title-Prefix/Suffix als Extension Attributes. Die Adresse wird automatisch anhand des Zimmers bestimmt (Zimmer beginnt mit „I" → Innsbruck, sonst Wien).

- **Manager setzen** — Die letzten 3 Zeichen des Team-Feldes ergeben das Kürzel des Vorgesetzten. Daraus wird der Manager in AD gesetzt und zusätzlich in Extension Attributes 14 und 15 gespeichert.

- **AD-Gruppen zuweisen** — Jeder Benutzer bekommt:
  - **Basisgruppen** (alle Benutzer): `acc.Office365BusinessPremium`, `acc.M365Exchange`, `WorksiteLicencedUSers`, `Alle`, `acc.BGR-AI-Plattform`, `WorkSiteUsers`
  - **Standortgruppe** basierend auf dem Zimmer: z.B. `VIE_3OG` (3. OG Wien) oder `IBK_1OG` (Innsbruck)
  - **OU-Gruppe** basierend auf der Organisationseinheit: z.B. `OU_PARTNER`, `OU_SEKR`, `OU_RAA`
  - **Verteilergruppen** basierend auf Stellenbezeichnung + Standort (siehe Tabelle unten)
  - **Team-Gruppe** im Format `Team-<Manager-Kürzel>`

- **Profilordner erstellen** — Auf `\\bgr\dfs\Profile\<Kürzel>` wird ein Ordner erstellt. Der Benutzer wird als Besitzer gesetzt und erhält Vollzugriff, ebenso die Administratoren-Gruppe.

#### 4. Zusammenfassungs-E-Mail senden
Am Ende wird eine HTML-E-Mail mit einer Tabelle aller verarbeiteten Benutzer versendet (Eintritt, Name, E-Mail, Kürzel, Telefon, Zimmer, Team, Stellenbezeichnung, Geburtsdatum, Kostenstelle, Berufsträger, Stundensatz, FTE). Der Versand erfolgt per direktem SMTP über den gewhitelisteten Connector — keine Authentifizierung notwendig.

##### Verteilergruppen nach Stellenbezeichnung

Die folgende Tabelle zeigt, welche zusätzlichen Verteilergruppen je nach Position und Standort zugewiesen werden. Standort wird automatisch aus dem Zimmer abgeleitet (beginnt mit „I" → Innsbruck, sonst Wien).

**Juristen und juristische Mitarbeiter:**

| Stellenbezeichnung | Wien | Innsbruck | Beide Standorte |
|---|---|---|---|
| Rechtsanwaltsanwärter-in | Konzipienten-Wien | Konzipienten-Innsbruck | |
| Anwalt/Anwältin - selbständig | Anwaelte-Wien | Anwaelte-Innsbruck | |
| Counsel | Anwaelte-Wien | Anwaelte-Innsbruck | Counsel, Counsel-HR |
| Partner-in | Partner-Wien | Partner-Innsbruck | |
| Juristische-r Ferialpraktikant-in | | | Praktikanten |
| Juristische-r Praktikant-in | | | Praktikanten |
| Juristische-r Praktikant-in - geringfügig | | | Praktikanten |
| Juristische Mitarbeiter\*in | | | Juristische Mitarbeiter |
| Trademark Paralegal | | TMParalegal-Innsbruck | |

**Leiter:**

| Stellenbezeichnung | Wien | Innsbruck | Beide Standorte |
|---|---|---|---|
| Leiter-in IT | IT-Team | | Ausschussleiter |
| Leiter-in KOM | KOM-Team | | Ausschussleiter |
| Leiterin-in HR | HR-Team | | Ausschussleiter |
| Leiter-in Finanzen | | | BUHA, HOVE, Ausschussleiter |
| Leiter-in Rezeption | | | Rezeption intern, Rezeption |

**Mitarbeiter:**

| Stellenbezeichnung | Wien | Innsbruck | Beide Standorte |
|---|---|---|---|
| Mitarbeiter-in IT | IT-Team | | |
| Mitarbeiter-in HR | HR-Team | | |
| MP Assistent-in | OM-Team | | |
| Mitarbeiter-in Bibliothek | Bibliothek | | |
| Mitarbeiter-in KOM | kommunikation | | |
| Sekretariat | Sekretariat-Wien | Sekretariat-Innsbruck | |
| Rezeption | Rezeption intern, Rezeption | | |
| Buchhalter-in | BUHA | | |
| Honorarverrechner-in | HOVE | | |

---

### 🔴 **OFFBOARDING** — Mitarbeiter entfernen

Das Offboarding läuft **am Tag nach dem Austrittsdatum** (Letzter Arbeitstag) automatisch ab:

#### Phase 1: Informationen von P&I
- ✅ Austrittsdatum ("Letzter Arbeitstag") wird aus LOGA-System geladen
- ✅ Offboarding-Benachrichtigungsemail wird versendet, sobald die Person in der P&I-Auswertung aufscheint

#### Phase 2: Exchange-Maßnahmen (nächster Tag nach Austrittsdatum)

- **Umwandlung zu Shared Mailbox**: Das persönliche Postfach wird in eine Shared Mailbox konvertiert, damit das Team darauf zugreifen kann
- **E-Mail-Weiterleitung**: Automatische Weiterleitung der E-Mails an den Vorgesetzten wird eingerichtet
- **Zustellungskopie**: E-Mails werden weiterhin auch im ursprünglichen Postfach zugestellt
- **Abwesenheitsnotiz**: Automatisch-Antwort (Out-of-Office) wird gesetzt mit:
  - Vorlage aus Marketing
  - Kein Enddatum (bleibt permanent aktiv)
- **Verteilerlisten**: Benutzer wird aus allen E-Mail-Gruppen entfernt

#### Phase 3: Active Directory-Maßnahmen

- **Konto deaktivieren**: Das AD-Benutzerkonto wird deaktiviert (disabled)
- **In "Disabled Users" verschieben**: Das Konto wird in die OU `OU=Disabled Users,DC=bgr,DC=at` verschoben
- **Gruppenmitgliedschaften entfernen**: Der Benutzer wird aus sämtlichen Gruppen entfernt, mit Ausnahme von `Domain Users` (da dies nicht deaktivierbar ist)

#### Phase 4: Benachrichtigungen
- ✅ Zusammenfassungs-E-Mail mit allen verarbeiteten Austritten wird an Stakeholder versendet

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
# LOGA HR System — den base64-kodierten Job-File-Content eintragen
LOGA_ONBOARDING_JOB_FILE_CONTENT=<Wert von Markus erfragen>
LOGA_OFFBOARDING_JOB_FILE_CONTENT=<Wert von Markus erfragen>

# Restliche Werte sind bereits korrekt vorausgefüllt.
# Zum Testen DRY_RUN=true lassen (Standard).
```

**Umgebungsvariablen — nach Prozesstyp organisiert:**

| Variable | Beschreibung | Prozess |
|---|---|---|
| **LOGA HR System** | | |
| `LOGA_API_URL` | URL der LOGA Scout Report API (vorausgefüllt) | - |
| `LOGA_ONBOARDING_JOB_FILE_CONTENT` | Base64-kodierter Schlüssel für LOGA Onboarding-Report (neue Mitarbeiter) — **vertraulich!** | Onboarding |
| `LOGA_OFFBOARDING_JOB_FILE_CONTENT` | Base64-kodierter Schlüssel für LOGA Offboarding-Report (ausscheidende Mitarbeiter) — **vertraulich!** | Offboarding |
| **SMTP (E-Mail-Versand)** | | |
| `SMTP_HOST` | SMTP-Server (vorausgefüllt: `bindergroesswang-at.mail.protection.outlook.com`) | - |
| `SMTP_PORT` | SMTP-Port (vorausgefüllt: 25) | - |
| **Onboarding-Benachrichtigungen** | | |
| `ONBOARDING_NOTIFICATION_EMAIL_TO` | Empfänger der Zusammenfassungs-E-Mail | Onboarding |
| `ONBOARDING_NOTIFICATION_EMAIL_BCC` | BCC-Empfänger, kommagetrennt (optional) | Onboarding |
| `ONBOARDING_NOTIFICATION_EMAIL_FROM` | Absender-Adresse | Onboarding |
| **Offboarding-Benachrichtigungen** | | |
| `OFFBOARDING_NOTIFICATION_EMAIL_TO` | Empfänger der Zusammenfassungs-E-Mail | Offboarding |
| `OFFBOARDING_NOTIFICATION_EMAIL_BCC` | BCC-Empfänger, kommagetrennt (optional) | Offboarding |
| `OFFBOARDING_NOTIFICATION_EMAIL_FROM` | Absender-Adresse | Offboarding |
| **Fehlerbenachrichtigungen** | | |
| `ERROR_NOTIFICATION_EMAIL` | Empfänger bei kritischen Fehlern | - |
| **Offboarding-Konfiguration** | | |
| `OFFBOARDING_ABSENCE_NOTICE` | Text der Auto-Reply-Abwesenheitsnotiz | Offboarding |
| `OFFBOARDING_DISABLED_USERS_OU` | AD OU für deaktivierte Benutzer (z.B. `OU=Disabled Users,DC=bgr,DC=at`) | Offboarding |
| **AD und Profil** | | |
| `PROFILE_BASE_PATH` | UNC-Pfad zum Profilordner-Share (z.B. `\\bgr\dfs\Profile`) | Onboarding |
| `DEFAULT_PASSWORD` | Standardpasswort für neue Postfächer | Onboarding |
| `REMOTE_ROUTING_DOMAIN` | Remote-Routing-Domain für Exchange Online (z.B. `bindergroesswang-at.mail.onmicrosoft.com`) | Onboarding |
| **Testmodus** | | |
| `DRY_RUN` | `true` = nur loggen, nichts ändern; `false` = produktiv ausführen | - |

### 5. Testlauf (Dry Run)

```powershell
.\.venv\Scripts\python.exe main.py onboarding
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

Für **Onboarding**:
```powershell
.\.venv\Scripts\python.exe main.py onboarding
```

Für **Offboarding**:
```powershell
.\.venv\Scripts\python.exe main.py offboarding
```

---

## Als geplante Tasks einrichten (Task Scheduler)

Es empfiehlt sich, sowohl das Onboarding als auch das Offboarding als geplante Tasks zu konfigurieren:

### Option 1: Verwendung der vorgefertigten .bat-Dateien (einfach)

Das Projekt enthält zwei vorgefertigte `.bat`-Dateien, die automatisch:
- Das Virtual Environment aktivieren
- Die `.env`-Datei prüfen
- Das Logging-Verzeichnis erstellen
- Den Python-Prozess aufrufen

#### Onboarding — täglich um 06:00
| Feld | Wert |
|---|---|
| **Programm** | `C:\Tasks\User-Management\run-onboarding.bat` |
| **Working Directory** | `C:\Tasks\User-Management` |
| **Trigger** | Täglich, 06:00 |
| **Run as** | Service-Account mit AD/Exchange-Berechtigungen |

#### Offboarding — täglich um 08:00
| Feld | Wert |
|---|---|
| **Programm** | `C:\Tasks\User-Management\run-offboarding.bat` |
| **Working Directory** | `C:\Tasks\User-Management` |
| **Trigger** | Täglich, 08:00 |
| **Run as** | Service-Account mit AD/Exchange-Berechtigungen |

### Option 2: Direkter Python-Aufruf (fortgeschritten)

Falls Sie den Python-Prozess direkt aufrufen möchten:

| Feld | Wert |
|---|---|
| **Programm** | `C:\Tasks\User-Management\.venv\Scripts\python.exe` |
| **Argumente** | `main.py onboarding` (oder `offboarding`) |
| **Working Directory** | `C:\Tasks\User-Management` |

---

## Logging

Das System schreibt Logs automatisch in das Verzeichnis `logs/`:

```
logs/
  onboarding_20260220_060000.log    ← Onboarding
  offboarding_20260220_080000.log   ← Offboarding
  ...
```

### Log-Details

**Jede Log-Datei enthält:**
- ✅ Auf der Konsole: `INFO` und höher (Warning, Error)
- ✅ In der Datei: `DEBUG` und höher (alles)
- 🕐 Zeitstempel im Format `YYYY-MM-DD HH:MM:SS`
- 🏷️ Level, Logger-Name, Nachricht

### Log-Beispiel

```
2026-02-20 06:00:00 [INFO] bgr-user-management: ================================================================================
2026-02-20 06:00:00 [INFO] bgr-user-management: BGR User Management — ONBOARDING Process Started
2026-02-20 06:00:00 [INFO] bgr-user-management: Log file: logs/onboarding_20260220_060000.log
2026-02-20 06:00:00 [INFO] bgr-user-management: ================================================================================
2026-02-20 06:00:05 [INFO] src.loga_client: Fetching new users from LOGA API…
2026-02-20 06:00:10 [INFO] src.loga_client: LOGA returned 5 user rows
...
2026-02-20 06:00:30 [INFO] bgr-user-management: Process completed successfully
```

### Log-Dateien aufräumen

Nach einiger Zeit sollten alte Log-Dateien gelöscht werden. Sie können ein weiteres Scheduled-Task erstellen:

```powershell
# PowerShell-Script zum Löschen von Logs älter als 90 Tage
$logDir = "C:\Tasks\User-Management\logs"
$daysToKeep = 90
$cutoffDate = (Get-Date).AddDays(-$daysToKeep)

Get-ChildItem -Path $logDir -Filter "*.log" | Where-Object {
    $_.LastWriteTime -lt $cutoffDate
} | Remove-Item -Force

Write-Output "Cleaned up logs older than $daysToKeep days"
```

---

## Scheduled Tasks erstellen

Nachdem das Projekt eingerichtet ist, können Sie die geplanten Tasks einrichten. Es gibt zwei Wege:

### Methode 1: Task Scheduler GUI (einfach)

**Onboarding erstellen:**
1. Öffnen Sie **Task Scheduler** (Startmenü → Taskplaner)
2. Klicken Sie auf **Create Basic Task...**
3. **Name:** `BGR Onboarding` | **Description:** `Daily user onboarding`
4. **Trigger:** Daily | **6:00:00 AM** | **Recur every 1 day**
5. **Action:** Start a program
   - **Program/script:** `C:\Tasks\User-Management\run-onboarding.bat`
   - **Start in:** `C:\Tasks\User-Management`
6. **Conditions:**
   - ✅ Break down Idle conditions (Enabled)
   - ✅ Start the task only if the computer is on AC power
7. **Settings:**
   - ✅ Allow task to be run on demand
   - ✅ If the task fails, restart every 1 minute (max. 3 times)
   - ✅ Stop the task if it runs longer than 1 hour
8. **Finish**

**Offboarding erstellen:**
Gleich wie Onboarding, aber:
- **Name:** `BGR Offboarding`
- **Program/script:** `C:\Tasks\User-Management\run-offboarding.bat`
- **Trigger:** Daily, **8:00:00 AM** (nach Onboarding!)

### Methode 2: Via PowerShell (Skript)

```powershell
$taskPath = "C:\Tasks\User-Management"
$batOnboarding = "$taskPath\run-onboarding.bat"
$batOffboarding = "$taskPath\run-offboarding.bat"

# Onboarding Task erstellen
$action = New-ScheduledTaskAction -Execute $batOnboarding -WorkingDirectory $taskPath
$trigger = New-ScheduledTaskTrigger -Daily -At 6:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings `
    -TaskName "BGR Onboarding" -Description "Daily user onboarding from LOGA" -AsJob

Write-Host "✅ Onboarding Task erstellt"

# Offboarding Task erstellen
$action = New-ScheduledTaskAction -Execute $batOffboarding -WorkingDirectory $taskPath
$trigger = New-ScheduledTaskTrigger -Daily -At 8:00am
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -ExecutionTimeLimit (New-TimeSpan -Hours 1)

Register-ScheduledTask -Action $action -Trigger $trigger -Settings $settings `
    -TaskName "BGR Offboarding" -Description "Daily user offboarding after exit date" -AsJob

Write-Host "✅ Offboarding Task erstellt"
```

> **Wichtig:** Die Service-Account muss AD/Exchange-Berechtigungen haben. Prüfen Sie die Task-Eigenschaften und setzen Sie die richtige **Run as**-Benutzer.

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
  models.py              OnboardingUser & OffboardingUser Datenmodelle
  loga_client.py         LOGA HR API Client (holt neue/ausscheidende Mitarbeiter)
  ad_client.py           AD/Exchange-Provisionierung & -Deprovisioning via PowerShell
  smtp_client.py         E-Mail-Versand via SMTP (gewhitelisteter Connector, ohne Auth)
  job_title_resolver.py  Geschlechtsspezifische Stellenbezeichnung (Onboarding)
  ou_resolver.py         Stellenbezeichnung → AD Organisationseinheit (Onboarding)
  group_resolver.py      Ermittlung der AD-Gruppenmitgliedschaften (Onboarding)
  email_builder.py       HTML-Zusammenfassungstabellen (Onboarding & Offboarding)
  onboarding.py          Onboarding-Ablauf (Orchestrierung)
  offboarding.py         Offboarding-Ablauf (Orchestrierung) 
main.py                  Einstiegspunkt (python main.py [onboarding|offboarding])
run-onboarding.bat       Batch-Script für geplantes Onboarding-Task
run-offboarding.bat      Batch-Script für geplantes Offboarding-Task
.env.example             Vorlage für die Konfiguration
.env                     Tatsächliche Konfiguration (nicht im Git!)
.gitignore               Git-Ausschlüsse (logs/, .env, etc.)
pyproject.toml           Python-Projektdefinition und Abhängigkeiten
logs/                    Automatisch erstellte Log-Dateien (nicht im Git)
```

---

## Fehlerbehebung

| Problem | Lösung |
|---|---|
| `ModuleNotFoundError: No module named 'src'` | Sicherstellen, dass `pip install -e .` im venv ausgeführt wurde |
| `PowerShell-Fehler: Get-ADUser not recognized` | AD PowerShell-Modul installieren: `Install-WindowsFeature RSAT-AD-PowerShell` |
| `New-RemoteMailbox not recognized` | Exchange Snap-In nicht verfügbar — Skript muss auf dem Exchange-Server laufen |
| `SMTP connection refused` | Server-IP nicht auf dem Connector gewhitelistet, oder Port 25 blockiert |
| `LOGA API gibt leere Daten zurück` | `LOGA_ONBOARDING_JOB_FILE_CONTENT` oder `LOGA_OFFBOARDING_JOB_FILE_CONTENT` in `.env` prüfen |
| Benutzer wird übersprungen obwohl er neu ist | AD-Kürzel (SamAccountName) existiert bereits — manuell im AD prüfen |
| Nach Fehler erneut ausführen: Postfach existiert schon | Das ist normal — das Skript erkennt den Benutzer als „vorhanden" und führt nur den Abgleich durch (Attribute, Gruppen, Profilordner) |
| `git pull` schlägt fehl mit „unrelated histories" | `git fetch origin` dann `git reset --hard origin/main` — danach ist das lokale Repo synchron |
