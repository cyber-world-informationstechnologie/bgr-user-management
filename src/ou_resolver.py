"""Resolve Active Directory Organizational Unit from LOGA position."""

from src.models import OnboardingUser

_OU_BASE = "OU=BGUser,DC=BGR,DC=AT"

_POSITION_TO_OU: dict[str, str] = {
    "Partner*in": f"OU=Partner-in,{_OU_BASE}",
    "Anwalt/Anwältin selbstständig": f"OU=Anwalt-Anwältin - selbständig,{_OU_BASE}",
    "Europäische*r Rechtsanwalt/Rechtsanwältin": f"OU=Anwalt-Anwältin - selbständig,{_OU_BASE}",
    "Counsel": f"OU=Counsel,{_OU_BASE}",
    "Of Counsel": f"OU=Counsel,{_OU_BASE}",
    "Rechtsanwaltsanwärter*in": f"OU=Rechtsanwaltsanwärter-in,{_OU_BASE}",
    "Juristische*r Mitarbeiter*in": f"OU=Juristische-r Mitarbeiter-in,{_OU_BASE}",
    "Juristische*r Praktikant*in": f"OU=Juristische-r Praktikant-in,{_OU_BASE}",
    "Juristische*r Ferialpraktikant*in": f"OU=Ferialpraktikant-in,{_OU_BASE}",
    "NJ-Praktikant*in": f"OU=NJ-Praktikant-in,{_OU_BASE}",
    "Assistent*in": f"OU=Sekretariat,{_OU_BASE}",
    "Backoffice Assistent*in": f"OU=Sekretariat,{_OU_BASE}",
    "Assistent*in - Reisestelle": f"OU=Sekretariat,{_OU_BASE}",
    "MP Assistent*in": f"OU=MP Assistent-in,{_OU_BASE}",
    "Mitarbeiter*in KOM": f"OU=Mitarbeiter-in KOM,{_OU_BASE}",
    "Mitarbeiter*in IT": f"OU=Mitarbeiter-in IT,{_OU_BASE}",
    "Mitarbeiter*in HR": f"OU=Mitarbeiter-in HR,{_OU_BASE}",
    "Mitarbeiter*in OM": f"OU=Mitarbeiter-in OM,{_OU_BASE}",
    "Mitarbeiter*in Reinigung": f"OU=Reinigung,{_OU_BASE}",
    "Mitarbeiter*in Bibliothek": f"OU=Mitarbeiter-in Bibliothek,{_OU_BASE}",
    "Leiter*in HR": f"OU=Leiterin HR,{_OU_BASE}",
    "Leiter*in IT": f"OU=Leiter-in IT,{_OU_BASE}",
    "Leiter*in KOM": f"OU=Leiter-in KOM,{_OU_BASE}",
    "Leiter*in FIN": f"OU=Leiter-in Finanzen,{_OU_BASE}",
    "Leiter*in Rezeption": f"OU=Leiter-in Rezeption,{_OU_BASE}",
    "Leiter*in Reinigung": f"OU=Reinigung,{_OU_BASE}",
    "Rezeptionist*in": f"OU=Rezeption,{_OU_BASE}",
    "Buchhalter*in": f"OU=Buchhalter-in,{_OU_BASE}",
    "Honorarverrechner*in": f"OU=Honorarverrechner-in,{_OU_BASE}",
    "Haustechniker*in": f"OU=Haustechniker-in,{_OU_BASE}",
    "Trademark Paralegal": f"OU=Trademark Paralegal,{_OU_BASE}",
    "CommonUser": f"OU=CommonUser,{_OU_BASE}",
    "noJobtitle": f"OU=noJobtitle,{_OU_BASE}",
}

_DEFAULT_OU = f"OU=noJobtitle,{_OU_BASE}"


def resolve_ou(user: OnboardingUser) -> str:
    """Return the AD OU distinguished name for the user's position."""
    return _POSITION_TO_OU.get(user.position, _DEFAULT_OU)
