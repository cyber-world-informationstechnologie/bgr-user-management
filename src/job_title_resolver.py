"""Resolve gendered job title from the generic LOGA position string."""

from src.models import OnboardingUser

# Mapping: LOGA position -> (male title, female title)
# If only one string, the title is gender-neutral.
_GENDERED_TITLES: dict[str, tuple[str, str] | str] = {
    "Partner*in": ("Partner", "Partnerin"),
    "Anwalt/Anwältin selbstständig": ("Selbstständiger Anwalt", "Selbstständige Anwältin"),
    "Europäische*r Rechtsanwalt/Rechtsanwältin": (
        "Europäischer Rechtsanwalt",
        "Europäische Rechtsanwältin",
    ),
    "Counsel": "Counsel",
    "Of Counsel": "Of Counsel",
    "Rechtsanwaltsanwärter*in": ("Rechtsanwaltsanwärter", "Rechtsanwaltsanwärterin"),
    "Juristische*r Mitarbeiter*in": ("Juristischer Mitarbeiter", "Juristische Mitarbeiterin"),
    "Juristische*r Praktikant*in": ("Juristischer Praktikant", "Juristische Praktikantin"),
    "Juristische*r Ferialpraktikant*in": (
        "Juristischer Ferialpraktikant",
        "Juristische Ferialpraktikantin",
    ),
    "NJ-Praktikant*in": ("NJ-Praktikant", "NJ-Praktikantin"),
    "Assistent*in": ("Assistent", "Assistentin"),
    "Backoffice Assistent*in": ("Backoffice Assistent", "Backoffice Assistentin"),
    "Assistent*in - Reisestelle": ("Assistent - Reisestelle", "Assistentin - Reisestelle"),
    "MP Assistent*in": ("MP Assistent", "MP Assistentin"),
    "Mitarbeiter*in KOM": ("Mitarbeiter KOM", "Mitarbeiterin KOM"),
    "Mitarbeiter*in IT": ("Mitarbeiter IT", "Mitarbeiterin IT"),
    "Mitarbeiter*in HR": ("Mitarbeiter HR", "Mitarbeiterin HR"),
    "Mitarbeiter*in OM": ("Mitarbeiter OM", "Mitarbeiterin OM"),
    "Mitarbeiter*in Reinigung": ("Mitarbeiter Reinigung", "Mitarbeiterin Reinigung"),
    "Mitarbeiter*in Bibliothek": ("Mitarbeiter Bibliothek", "Mitarbeiterin Bibliothek"),
    "Leiter*in HR": ("Leiter HR", "Leiterin HR"),
    "Leiter*in IT": ("Leiter IT", "Leiterin IT"),
    "Leiter*in KOM": ("Leiter KOM", "Leiterin KOM"),
    "Leiter*in FIN": ("Leiter FIN", "Leiterin FIN"),
    "Leiter*in Rezeption": ("Leiter Rezeption", "Leiterin Rezeption"),
    "Leiter*in Reinigung": ("Leiter Reinigung", "Leiterin Reinigung"),
    "Rezeptionist*in": ("Rezeptionist", "Rezeptionistin"),
    "Buchhalter*in": ("Buchhalter", "Buchhalterin"),
    "Honorarverrechner*in": ("Honorarverrechner", "Honorarrechnerin"),
    "Haustechniker*in": ("Haustechniker", "Haustechnikerin"),
    "Trademark Paralegal": "Trademark Paralegal",
}

# English position mapping (used for international contexts)
_ENGLISH_TITLES: dict[str, str] = {
    "Partner*in": "Partner",
    "Counsel": "Counsel",
    "Anwalt/Anwältin selbstständig": "Attorney at Law",
    "Rechtsanwaltsanwärter*in": "Associate",
    "Juristische*r Mitarbeiter*in": "Legal Assistant",
    "Trademark Paralegal": "Trademark Paralegal",
}


def resolve_job_title(user: OnboardingUser) -> str:
    """Resolve the gendered job title for the given user."""
    entry = _GENDERED_TITLES.get(user.position)
    if entry is None:
        return "Unknown"
    if isinstance(entry, str):
        return entry
    male, female = entry
    return male if user.gender == "M" else female


def resolve_job_title_en(user: OnboardingUser) -> str:
    """Resolve the English job title for the given user."""
    return _ENGLISH_TITLES.get(user.position, "Unknown")
