"""Maskering av persondata i fritext (CLAUDE.md §6).

Modulen finns för att `docs/kategorier-forslag.md` COMMITTAS och innehåller
citat ur kundmail. §6 säger att namn, adresser, registreringsnummer och
telefonnummer aldrig förekommer i dokument i `docs/`.

Maskeringen är avsiktligt trubbig. Att maska för mycket kostar läsbarhet, att
maska för lite är en överträdelse.

**KÄND BEGRÄNSNING, och den ska läsas innan något citat committas.** Namn i
löpande text går inte att hitta säkert. Heuristiken här utnyttjar att svenskan
INTE versaliserar vanliga substantiv: ett versalt ord mitt i en mening är därför
oftast ett egennamn. Det fångar `Anna` och `Volvo`, men inte ett namn skrivet
med gemener, och inte ett namn först i en mening. Citat ur kundmail ska därför
hållas korta och läsas av en människa före publicering.
"""

from __future__ import annotations

import re
from email.utils import getaddresses

EPOST = re.compile(r"[A-Za-z0-9._%+=-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
# Bar domän utan protokoll, som `melias.se`. Varken EPOST eller URL fångar den,
# och en domän kan vara ett efternamn eller ett företagsnamn. Utan det här
# mönstret överlevde en sådan domän som KATEGORINAMN i en committad fil.
DOMAN = re.compile(
    r"\b[a-zåäö0-9][a-zåäö0-9-]*\.(?:se|com|net|org|nu|eu|dk|no|fi|de|co\.uk)\b",
    re.IGNORECASE,
)
REGNR = re.compile(r"\b[A-ZÅÄÖa-zåäö]{3}[\s-]?\d{2}[A-ZÅÄÖa-zåäö0-9]\b")
# Fyra siffror räcker. Postnummer är fem och kundnummer ofta fyra, och båda
# stod i klartext när gränsen låg på sex.
SIFFROR = re.compile(r"\d[\d\s()+-]{2,}\d")
# Gatunamn. Svenska gatunamn slutar på ett litet antal efterled, och adressen
# är persondata även utan husnummer.
GATA = re.compile(
    r"\b[A-ZÅÄÖa-zåäö]{2,}(?:gatan|gatans|vägen|vägens|gränd|gränden|torget"
    r"|plan|backen|stigen|allén|kajen)\b",
    re.IGNORECASE,
)
# Versalt ord. Svansen tillåter versaler, så att namn skrivna med versaler
# fångas: en tidigare version krävde gemen svans och släppte igenom dem.
VERSALT_ORD = re.compile(r"\b[A-ZÅÄÖ][A-ZÅÄÖa-zåäöéèüøæëüó]+\b")

# Ord som är versala av grammatiska skäl och inte är egennamn. Listan är kort
# med avsikt: den ska bara innehålla ord som ALDRIG är ett namn.
EJ_NAMN = {
    "Hej", "Hejsan", "Tack", "Vänliga", "Mvh", "Med", "Hälsningar", "Bästa",
    "Jag", "Vi", "Du", "Ni", "Det", "Den", "Har", "Kan", "Skulle", "Vill",
    "Undrar", "Finns", "Ska", "Måndag", "Tisdag", "Onsdag", "Torsdag",
    "Fredag", "Lördag", "Söndag", "Januari", "Februari", "Mars", "April",
    "Maj", "Juni", "Juli", "Augusti", "September", "Oktober", "November",
    "December", "Hur", "Vad", "När", "Var", "Om", "Och", "Men", "Så",
}

# Platshållarna är själva versala och skulle annars maskeras en gång till,
# så att `[LÄNK]` blev `[[NAMN]]`.
PLATSHALLARE = {"LÄNK", "EPOST", "DOMÄN", "GATA", "REGNR", "SIFFROR", "NAMN",
                "MASKERAD"}
EJ_NAMN |= PLATSHALLARE

def maska_identifierare(text: str) -> str:
    """Maskerar allt UTOM namn, och lämnar skiftläget orört.

    Finns för namnräkningen i `src/cluster.py`, som avgör om ett ord är ett
    egennamn genom att jämföra hur ofta det skrivs versalt mot gement. Räknas
    den på råtexten röstar ordets förekomster inuti e-postadresser och länkar,
    som alltid är gemena, ned ordet under tröskeln. Så slapp ett kundförnamn
    igenom som kategorinamn i en committad fil.
    """
    text = URL.sub(" [LÄNK] ", text)
    text = EPOST.sub(" [EPOST] ", text)
    text = DOMAN.sub(" [DOMÄN] ", text)
    text = GATA.sub(" [GATA] ", text)
    text = REGNR.sub(" [REGNR] ", text)
    return SIFFROR.sub(" [SIFFROR] ", text)


def maska_fritext(text: str) -> str:
    """Maskerar persondata i löpande text.

    Ordningen spelar roll: adresser och URL:er först, eftersom de innehåller
    både bokstäver och siffror som annars fångas av de senare mönstren.
    """
    return _maska_namn(maska_identifierare(text))


def _maska_namn(text: str) -> str:
    """Maskerar VARJE versalt ord som inte står i EJ_NAMN.

    POSITIONSUNDANTAGET ÄR BORTTAGET. En tidigare version lät ett versalt ord
    passera när det stod först i en mening, och räknade både radbörjan och
    tecknet efter ett kolon som meningsstart. Följden var att `Kund: Förnamn`
    och varje namn i ett signaturblock gick ut i klartext i en committad fil.

    Att maska för mycket kostar läsbarhet, att maska för lite är en
    §6-överträdelse. Därför maskeras även ord som råkar inleda en mening.
    """
    ut = []
    forra_slutet = 0
    for traff in VERSALT_ORD.finditer(text):
        ut.append(text[forra_slutet:traff.start()])
        ord_ = traff.group(0)
        ut.append(ord_ if ord_ in EJ_NAMN else "[NAMN]")
        forra_slutet = traff.end()
    ut.append(text[forra_slutet:])
    return "".join(ut)


def namnkandidater(text: str) -> set[str]:
    """Ord som troligen är egennamn, i gemen form.

    Används för att hålla namn borta ur maskinproducerade ETIKETTER, där de
    annars hamnar i klartext i en committad fil. Etiketter byggs av gemena
    tokens, så versalheuristiken kan inte tillämpas på dem: den körs på texten
    och resultatet förs vidare som en uteslutningslista.
    """
    return {
        traff.group(0).lower()
        for traff in VERSALT_ORD.finditer(text)
        if traff.group(0) not in EJ_NAMN
    }


def _initialer(visningsnamn: str) -> str:
    rensat = visningsnamn.strip().strip('"').strip()
    if not rensat:
        return ""
    return ".".join(ord_[:1].upper() for ord_ in rensat.split() if ord_) + "."


def _maska_epost(traff: re.Match) -> str:
    adress = traff.group(0)
    lokal, _, doman = adress.partition("@")
    delar = doman.rsplit(".", 1)
    return f"{lokal[:1]}***@{delar[0][:1]}***.{delar[1]}"


def maska(text: str) -> str:
    """Maskering för HUVUDVÄRDEN, där adressens form är informationen."""
    text = EPOST.sub(_maska_epost, text)
    text = REGNR.sub("[REGNR]", text)
    text = SIFFROR.sub("[SIFFROR]", text)
    return text


def maska_adressrad(varde: str) -> str:
    """Maskerar både adress och visningsnamn.

    Uppdelningen görs med `email.utils.getaddresses` och ALDRIG genom att
    splitta på komma: ett citerat visningsnamn av formen
    `"Efternamn, Förnamn" <adress>` innehåller ett komma, och en rå splittning
    lämnar efternamnet omaskerat. Känns formen inte igen maskeras hela värdet.
    """
    poster = []
    for visningsnamn, adress in getaddresses([varde]):
        # `getaddresses` returnerar första ORDET som adress när värdet inte är
        # en adressrad alls: "Förnamn Efternamnsson" ger adressen "Förnamn".
        # Utan kravet på snabel-a släpptes förnamnet ut i klartext, och
        # reservmaskeringen nedan utlöstes aldrig eftersom listan blev icke-tom.
        if "@" not in adress:
            continue
        poster.append(f"{_initialer(visningsnamn)} <{maska(adress)}>".strip())

    if not poster:
        return f"[MASKERAD, {len(varde)} tecken]"
    return ", ".join(poster)
