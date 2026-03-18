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
    """Represents a user to be onboarded, built from LOGA JSON data.

    Fields are mapped from P&I LOGA Scout report ``fieldTitle`` values.
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
    def from_loga_row(cls, row: dict[str, str]) -> "OnboardingUser":
        """Create an OnboardingUser from a LOGA data row (header-keyed dict).

        Handles P&I JSON column names including duplicates — the second
        ``Kostenstelle`` (renamed to ``Kostenstelle#2`` by the client) is
        actually the Team/Partner field, and ``Umfang d.Besetz`` maps to FTE.
        """
        def g(*names: str) -> str:
            for n in names:
                v = row.get(n, "")
                if v:
                    return v
            return ""

        return cls(
            personalnummer=g("Personalnummer"),
            abbreviation=g("Kürzel"),
            title_pre=g("Titel"),
            first_name=g("Vorname"),
            last_name=g("Nachname"),
            title_post=g("Titel nach dem Namen"),
            begin_date=g("Vertragsbeginn"),
            end_date=g("Vertragsende"),
            room=g("Zimmer"),
            birth_date=g("Geburtsdatum"),
            geschlecht=g("Geschlecht"),
            mobile=g("Handy"),
            email=g("E-Mail"),
            phone=g("Telefon"),
            kostenstelle=g("Kostenstelle"),
            stundensatz=g("Stundensatz"),
            berufstraeger=g("Berufsträger"),
            team=g("Team", "Kostenstelle#2"),
            umf_besetz=g("FTE", "Umfang d.Besetz"),
            position=g("Stellenbezeichnung", "Stellenart"),
        )

    @property
    def full_display_name(self) -> str:
        parts = [self.title_pre, self.first_name, self.last_name, self.title_post]
        return " ".join(p for p in parts if p)

    @property
    def gender(self) -> str:
        """Alias for geschlecht (M/W)."""
        return self.geschlecht

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
    """Represents a user to be offboarded, built from LOGA JSON data.

    Uses the same data structure as OnboardingUser, but adds exit_date
    (Letzter Arbeitstag) and kommentar for offboarding operations.
    Fields are mapped from P&I LOGA Scout report ``fieldTitle`` values.
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
    def from_loga_row(cls, row: dict[str, str]) -> "OffboardingUser":
        """Create an OffboardingUser from a LOGA data row (header-keyed dict)."""
        def g(*names: str) -> str:
            for n in names:
                v = row.get(n, "")
                if v:
                    return v
            return ""

        return cls(
            personalnummer=g("Personalnummer"),
            abbreviation=g("Kürzel"),
            title_pre=g("Titel"),
            first_name=g("Vorname"),
            last_name=g("Nachname"),
            title_post=g("Titel nach dem Namen"),
            begin_date=g("Vertragsbeginn"),
            end_date=g("Vertragsende"),
            exit_date=g("Letzter Arbeitstag"),
            room=g("Zimmer"),
            birth_date=g("Geburtsdatum"),
            geschlecht=g("Geschlecht"),
            mobile=g("Handy"),
            email=g("E-Mail"),
            phone=g("Telefon"),
            kostenstelle=g("Kostenstelle"),
            stundensatz=g("Stundensatz"),
            berufstraeger=g("Berufsträger"),
            team=g("Team"),
            umf_besetz=g("FTE"),
            position=g("Stellenbezeichnung"),
            kommentar=g("Kommentar"),
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