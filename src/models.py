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

    LOGA data array indices:
        0  = PNR (personnel number)
        1  = Kürzel (abbreviation)
        2  = Title prefix (e.g. Mag., Dr.)
        3  = First name
        4  = Last name
        5  = Title suffix (e.g. LL.M.)
        6  = Begin date
        7  = End date
        8  = Room
        9  = Birth date
        10 = Gender (M / W)
        11 = Mobile
        12 = Email
        13 = Phone
        14 = Kostenstelle
        15 = Stundensatz
        16 = Berufsträger
        17 = Team
        18 = UmfBesetz (FTE)
        19 = Position / Job title
    """

    pnr: str
    abbreviation: str
    title_pre: str
    first_name: str
    last_name: str
    title_post: str
    begin_date: str
    end_date: str
    room: str
    birth_date: str
    gender: str  # "M" or "W"
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
        """Create an OnboardingUser from a LOGA data row (array of strings)."""

        def safe_get(index: int) -> str:
            if index < len(row):
                return (row[index] or "").strip()
            return ""

        return cls(
            pnr=safe_get(0),
            abbreviation=safe_get(1),
            title_pre=safe_get(2),
            first_name=safe_get(3),
            last_name=safe_get(4),
            title_post=safe_get(5),
            begin_date=safe_get(6),
            end_date=safe_get(7),
            room=safe_get(8),
            birth_date=safe_get(9),
            gender=safe_get(10),
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
    def gender_display(self) -> str:
        return "Männlich" if self.gender == "M" else "Weiblich"

    @property
    def address(self) -> Address:
        return ADDRESS_INNSBRUCK if self.room.startswith("I") else ADDRESS_VIENNA

    @property
    def full_display_name(self) -> str:
        parts = [self.title_pre, self.first_name, self.last_name, self.title_post]
        return " ".join(p for p in parts if p)

    @property
    def is_reinigungskraft(self) -> bool:
        return self.position == "Mitarbeiter*in Reinigung"

    @property
    def phone_extension(self) -> str:
        """Extract the last 3 digits from the phone number as the extension (DW)."""
        digits = "".join(c for c in self.phone if c.isdigit())
        return digits[-3:] if len(digits) >= 3 else digits
