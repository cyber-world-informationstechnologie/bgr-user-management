"""Resolve AD group memberships for a user based on base groups, room, OU, and position."""

from src.models import OnboardingUser

BASE_GROUPS: list[str] = [
    "acc.Office365BusinessPremium",
    "acc.M365Exchange",
    "WorksiteLicencedUSers",
    "Alle",
    "acc.BGR-AI-Plattform",
    "WorkSiteUsers",
]

# OU fragment -> group name
_OU_TO_GROUP: dict[str, str] = {
    "OU=Abendsekretariat,": "OU_ASEKR",
    "OU=Angestellte-r Anwalt-Anwältin,": "OU_ANWALTA",
    "OU=Anwalt-Anwältin - selbständig,": "OU_ANWALTS",
    "OU=Betriebsarzt,": "OU_ARZT",
    "OU=Buchhalter-in,": "OU_BUHA",
    "OU=Counsel,": "OU_COU",
    "OU=Ferialpraktikant-in,": "OU_FP",
    "OU=Haustechniker-in,": "OU_HAUS",
    "OU=Honorarverrechner-in,": "OU_HON",
    "OU=Juristische-r Mitarbeiter-in,": "OU_JURM",
    "OU=Juristische-r Praktikant-in,": "OU_JP",
    "OU=Juristische-r Praktikant-in - geringfügig,": "OU_JPG",
    "OU=Leiter-in Finanzen,": "OU_LEIT_FIN",
    "OU=Leiterin HR,": "OU_LEIT_HR",
    "OU=Leiter-in IT,": "OU_001",
    "OU=Leiter-in KOM,": "OU_PR",
    "OU=Leiter-in Rezeption,": "OU_LEIT_REZ",
    "OU=Mitarbeiter-in Bibliothek,": "OU_MA_BIBLIO",
    "OU=Mitarbeiter-in Controlling,": "OU_CONTR",
    "OU=Mitarbeiter-in Finanzen,": "OU_FIN",
    "OU=Mitarbeiter-in HR,": "OU_HR",
    "OU=Mitarbeiter-in IT,": "OU_EDV",
    "OU=Mitarbeiter-in KOM,": "OU_MPR",
    "OU=Mitarbeiter-in OM,": "OU_OM",
    "OU=MP Assistent-in,": "OU_MPA",
    "OU=NJ-Praktikant-in,": "OU_NJP",
    "OU=NJ-Praktikant-in geringfügig,": "OU_NJPG",
    "OU=Partner-in,": "OU_PARTNER",
    "OU=Projektmanager-in,": "OU_PM",
    "OU=Rechtsanwaltsanwärter-in,": "OU_RAA",
    "OU=Reinigung,": "OU_REI",
    "OU=Rezeption,": "OU_REZ",
    "OU=Sekretariat,": "OU_SEKR",
    "OU=Trademark Paralegal,": "OU_TRAD",
}

# ---------------------------------------------------------------------------
# Position + location → distribution/security groups
#
# Each entry maps a LOGA position to either:
#   - a list of groups (applied regardless of location)
#   - a dict with "all" (always), "wien" (Vienna only), "ibk" (Innsbruck only)
# ---------------------------------------------------------------------------
_POSITION_GROUPS: dict[str, list[str] | dict[str, list[str]]] = {
    # --- Juristen und juristische Mitarbeiter ---
    "Rechtsanwaltsanwärter-in": {
        "wien": ["Konzipienten-Wien"],
        "ibk": ["Konzipienten-Innsbruck"],
    },
    "Anwalt/Anwältin - selbständig": {
        "wien": ["Anwaelte-Wien"],
        "ibk": ["Anwaelte-Innsbruck"],
    },
    "Counsel": {
        "all": ["Counsel", "Counsel-HR"],
        "wien": ["Anwaelte-Wien"],
        "ibk": ["Anwaelte-Innsbruck"],
    },
    "Partner-in": {
        "wien": ["Partner-Wien"],
        "ibk": ["Partner-Innsbruck"],
    },
    "Juristische-r Ferialpraktikant-in": ["Praktikanten"],
    "Juristische-r Praktikant-in": ["Praktikanten"],
    "Juristische-r Praktikant-in - geringfügig": ["Praktikanten"],
    "Juristische Mitarbeiter*in": ["Juristische Mitarbeiter"],
    "Trademark Paralegal": {
        "ibk": ["TMParalegal-Innsbruck"],
    },
    # --- Leiter ---
    "Leiter-in IT": {
        "all": ["Ausschussleiter"],
        "wien": ["IT-Team"],
    },
    "Leiter-in KOM": {
        "all": ["Ausschussleiter"],
        "wien": ["KOM-Team"],
    },
    "Leiterin-in HR": {
        "all": ["Ausschussleiter"],
        "wien": ["HR-Team"],
    },
    "Leiter-in Finanzen": ["BUHA", "HOVE", "Ausschussleiter"],
    "Leiter-in Rezeption": ["Rezeption intern", "Rezeption"],
    # --- Mitarbeiter ---
    "Mitarbeiter-in IT": {
        "wien": ["IT-Team"],
    },
    "Mitarbeiter-in HR": {
        "wien": ["HR-Team"],
    },
    "MP Assistent-in": {
        "wien": ["OM-Team"],
    },
    "Mitarbeiter-in Bibliothek": {
        "wien": ["Bibliothek"],
    },
    "Mitarbeiter-in KOM": {
        "wien": ["kommunikation"],
    },
    "Sekretariat": {
        "wien": ["Sekretariat-Wien"],
        "ibk": ["Sekretariat-Innsbruck"],
    },
    "Rezeption": {
        "wien": ["Rezeption intern", "Rezeption"],
    },
    "Buchhalter-in": {
        "wien": ["BUHA"],
    },
    "Honorarverrechner-in": {
        "wien": ["HOVE"],
    },
}


def _is_innsbruck(user: OnboardingUser) -> bool:
    """Return True if the user's room indicates the Innsbruck office."""
    return bool(user.room and user.room.startswith("I"))


def _resolve_position_groups(user: OnboardingUser) -> list[str]:
    """Return distribution/security groups based on position and location."""
    mapping = _POSITION_GROUPS.get(user.position)
    if mapping is None:
        return []

    # Simple list → applies to all locations
    if isinstance(mapping, list):
        return list(mapping)

    groups: list[str] = []
    groups.extend(mapping.get("all", []))
    if _is_innsbruck(user):
        groups.extend(mapping.get("ibk", []))
    else:
        groups.extend(mapping.get("wien", []))
    return groups


def resolve_groups(user: OnboardingUser, ou: str) -> list[str]:
    """Return the complete list of AD groups the user should be added to.

    Combines:
    1. Base groups (every user)
    2. Floor/location group based on room number
    3. OU-specific group
    4. Position + location distribution groups
    """
    groups = list(BASE_GROUPS)

    # Room-based group: Innsbruck rooms start with "I", Vienna rooms use floor prefix
    if user.room:
        if user.room.startswith("I"):
            groups.append("IBK_1OG")
        else:
            floor = user.room[0]
            groups.append(f"VIE_{floor}OG")

    # OU-based group
    if ou:
        for ou_fragment, group_name in _OU_TO_GROUP.items():
            if ou_fragment in ou:
                groups.append(group_name)
                break

    # Position + location distribution groups
    groups.extend(_resolve_position_groups(user))

    # De-duplicate while preserving order
    seen: set[str] = set()
    unique: list[str] = []
    for g in groups:
        if g not in seen:
            seen.add(g)
            unique.append(g)

    return unique
