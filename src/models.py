from dataclasses import dataclass


@dataclass
class Address:
    city: str
    country: str
    state: str
    zip_code: str
    street: str


ADDRESS_VIENNA = Address(
    city="Wien", country="AT", state="Wien", zip_code="1010", street="Sterngasse 13"
)
ADDRESS_INNSBRUCK = Address(
    city="Innsbruck", country="AT", state="Tirol", zip_code="6020", street="Kaiserjägerstraße 1"
)


@dataclass
class OnboardingUser:
    """Represents a user to be onboarded, built from LOGA data.

    LOGA CSV column indices (semicolon-delimited):
        0  = Personalnummer (personnel number / PNR)
        1  = Kürzel (abbreviation)
        2  = Titel (title prefix, e.g. Mag., Dr.)
        3  = Vorname (first name)
        4  = Nachname (last name)
        5  = Titel nach dem Namen (title suffix, e.g. LL.M.)
        6  = Vertragsbeginn (contract start / begin date)
        7  = Vertragsende (contract end)
        8  = Zimmer (room)
        9  = Geburtsdatum (birth date)
        10 = Geschlecht (gender, M/W)
        11 = Handy (mobile)
        12 = E-Mail (email)
        13 = Telefon (phone)
        14 = Kostenstelle (cost center)
        15 = Stundensatz (hourly rate)
        16 = Berufsträger (professional carrier flag)
        17 = Team (team)
        18 = FTE (full-time equivalent)
        19 = Stellenbezeichnung (job title / position)
    """

    personalnummer: str
    abbreviation: str
    title_pre: str
    first_name: str
    last_name: str
    title_post: str
    begin_date: str
    end_date: str
    room: str
    birth_date: str
    geschlecht: str
    mobile: str
    email: str
    phone: str
    kostenstelle: str
    stundensatz: str
    berufstraeger: str
    team: str
    umf_besetz: str  # FTE
    position: str  # raw position from LOGA

    @classmethod
    def from_loga_row(cls, row: list[str]) -> "OnboardingUser":
        """Create an OnboardingUser from a LOGA data row (array of strings).
        
        Handles rows with 20+ fields (tolerates trailing empty fields).
        """

        def safe_get(index: int) -> str:
            if index < len(row):
                return (row[index] or "").strip()
            return ""

        return cls(
            personalnummer=safe_get(0),
            abbreviation=safe_get(1),
            title_pre=safe_get(2),
            first_name=safe_get(3),
            last_name=safe_get(4),
            title_post=safe_get(5),
            begin_date=safe_get(6),
            end_date=safe_get(7),
            room=safe_get(8),
            birth_date=safe_get(9),
            geschlecht=safe_get(10),
            mobile=safe_get(11),
            email=safe_get(12),
            phone=safe_get(13),
            kostenstelle=safe_get(14),
            stundensatz=safe_get(15),
            berufstraeger=safe_get(16),
            team=safe_get(17),
            umf_besetz=safe_get(18),
            position=safe_get(19),
        )

    @property
    def full_display_name(self) -> str:
        parts = [self.title_pre, self.first_name, self.last_name, self.title_post]
        return " ".join(p for p in parts if p)

    @property
    def is_reinigungskraft(self) -> bool:
        """Return True if the user is cleaning staff (Reinigungskraft)."""
        return self.position == "Mitarbeiter*in Reinigung"

    @property
    def address(self) -> Address:
        """Return the office address based on room location (I* = Innsbruck, else Vienna)."""
        if self.room and self.room.startswith("I"):
            return ADDRESS_INNSBRUCK
        return ADDRESS_VIENNA

    @property
    def phone_extension(self) -> str:
        """Extract the last 3 digits from the phone number as the extension (DW)."""
        digits = "".join(c for c in self.phone if c.isdigit())
        return digits[-3:] if len(digits) >= 3 else digits

@dataclass
class OffboardingUser:
    """Represents a user to be offboarded, built from LOGA data.

    Uses the same data structure as OnboardingUser, but adds exit_date
    (Letzter Arbeitstag) for offboarding operations.

    LOGA CSV column indices (semicolon-delimited):
        0  = Personalnummer (personnel number / PNR)
        1  = Kürzel (abbreviation)
        2  = Titel (title prefix, e.g. Mag., Dr.)
        3  = Vorname (first name)
        4  = Nachname (last name)
        5  = Titel nach dem Namen (title suffix, e.g. LL.M.)
        6  = Vertragsbeginn (contract start / begin date)
        7  = Vertragsende (contract end)
        8  = Zimmer (room)
        9  = Geburtsdatum (birth date)
        10 = Geschlecht (gender, M/W)
        11 = Handy (mobile)
        12 = E-Mail (email)
        13 = Telefon (phone)
        14 = Kostenstelle (cost center)
        15 = Stundensatz (hourly rate)
        16 = Berufsträger (professional carrier flag)
        17 = Team (team)
        18 = FTE (full-time equivalent)
        19 = Stellenbezeichnung (job title / position)
        20 = Letzter Arbeitstag (exit date / last work day)
        21 = Kommentar (comment, e.g. expected re-entry)
    """

    personalnummer: str
    abbreviation: str
    title_pre: str
    first_name: str
    last_name: str
    title_post: str
    begin_date: str
    end_date: str  # Contract end
    exit_date: str  # Last work date (Letzter Arbeitstag) — used for offboarding
    room: str
    birth_date: str
    geschlecht: str
    mobile: str
    email: str
    phone: str
    kostenstelle: str
    stundensatz: str
    berufstraeger: str
    team: str
    umf_besetz: str  # FTE
    position: str
    kommentar: str  # Comment (e.g. expected re-entry date)

    @classmethod
    def from_loga_row(cls, row: list[str]) -> "OffboardingUser":
        """Create an OffboardingUser from LOGA data row."""

        def safe_get(index: int) -> str:
            if index < len(row):
                return (row[index] or "").strip()
            return ""

        return cls(
            personalnummer=safe_get(0),
            abbreviation=safe_get(1),
            title_pre=safe_get(2),
            first_name=safe_get(3),
            last_name=safe_get(4),
            title_post=safe_get(5),
            begin_date=safe_get(6),
            end_date=safe_get(7),
            exit_date=safe_get(20),  # Last work date (Letzter Arbeitstag)
            room=safe_get(8),
            birth_date=safe_get(9),
            geschlecht=safe_get(10),
            mobile=safe_get(11),
            email=safe_get(12),
            phone=safe_get(13),
            kostenstelle=safe_get(14),
            stundensatz=safe_get(15),
            berufstraeger=safe_get(16),
            team=safe_get(17),
            umf_besetz=safe_get(18),
            position=safe_get(19),
            kommentar=safe_get(21),
        )

    @property
    def full_display_name(self) -> str:
        parts = [self.title_pre, self.first_name, self.last_name, self.title_post]
        return " ".join(p for p in parts if p)

    @property
    def manager_abbreviation(self) -> str | None:
        """Extract manager abbreviation from team field (last 3 chars)."""
        if self.team and len(self.team) >= 3:
            return self.team[-3:]
        return None