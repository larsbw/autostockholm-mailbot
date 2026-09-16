#!/usr/bin/env python3
"""Hur ofta bär ett åtagandeord ett NEKANDE? Skiva 59 DEL A, Lars mätorder.

    .venv/bin/python scripts/polaritet-matning.py

**FRÅGAN.** Skiva 58:s enda spärrade post föll på `atagande-om-priset` med
satsen *"…det ingår inte i grundombyggnaden men vi ordnar det."* Påståendet är
SANT och önskat: dragkroken ingår inte, och kunden ska få veta det.
`krav_pa_atagande_med_kalla` prövar ordet `ingår` utan att se polariteten,
alltså fäller den nekandet lika hårt som utfästelsen.

Måttet avgör vad posten är. En enstaka form är ett utkast Lars stryker. En
återkommande form är regel 16 och spärren som står emot varandra.

**TVÅ KORPUSAR.**

1. **DE TJUGO**, `data/granskningsfall.jsonl`, alltså botens egna utkast ur
   körningen. Den spärrade posten bär inget `forslag`, bara `sparrsats`, och
   räknas på den. Det betyder att just den posten mäts på EN sats och inte på
   ett helt svar.
2. **MATTES 45**, `data/par.jsonl`, alltså svar Matte faktiskt skickat. Samma
   urval och samma kategorikoppling som `scripts/faktakalla-matning.py`.

**RÄKNINGEN GÅR GENOM SPÄRRENS EGNA DELAR.** Satsdelningen är `_meningar` efter
att prisposten strukits, ordet är `ATAGANDEORD`, nekandet är
`_NEKAT_EFTER_ATAGANDE`, och utfallet fås genom att kalla spärren. Ingen regel
skrivs av här, se skiva 58:s §7-fynd om vad en avskrift mäter.

**`_NEKAT_EFTER_ATAGANDE` LÄSER SVANSEN DIREKT EFTER ORDET**, alltså `ingår
inte` och `ingår ej`. Formen `inte ingår`, med nekandet FÖRE ordet, syns inte i
den mätningen och räknas av en egen rad här.

**DEN EGNA RADEN NÅR BARA ETT INTILLIGGANDE NEKANDE**, alltså högst ett ord
mellan nekandet och åtagandeordet. *"Det är inte så att dragkrok ingår"* räknas
som JAKANDE av den här mätningen. Ett nolltal på den raden betyder därför att
ingen INTILLIGGANDE framförställd negation finns, och inte att klassen är tom.
Raden är en MÄTNING och ingen regel: spärren bär den inte, och den friar aldrig
en sats.

**§6: MATTES SATSER SKRIVS INTE UT.** De redovisas som antal och löpnummer,
samma val som `faktakalla-matning`. Botens satser skrivs ut genom
`maskera.maska_fritext`, alltså samma maskering som körningsvyn använder.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generera, maskera  # noqa: E402
from src.generera import Forfragan, Sparrfalld  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
FALL = ROT / "data" / "granskningsfall.jsonl"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PARFIL = ROT / "data" / "par.jsonl"

# NEKANDE FÖRE ÅTAGANDEORDET. Spärren bär ingen sådan mängd, alltså är den här
# raden en MÄTNING och ingen regel: den räknar en form spärren i dag inte kan
# se, och den används aldrig till att fria en sats.
_NEKAT_FORE_ATAGANDE = generera.re.compile(
    r"\b(?:inte|ej|aldrig)\b\W+\w*$", generera.re.IGNORECASE
)


def _forfragan(kategori: str) -> Forfragan:
    """En förfrågan utan uppslag. Samma väg som `faktakalla-matning::_forfragan`."""
    return Forfragan(
        text="x",
        kategori=kategori,
        utfall=None,
        uppslag=None,
        uppslag_gjordes=True,
        regnr_i_mailet=True,
    )


def _atagandesatser(text: str, kategori: str) -> list[tuple[str, str, str, bool]]:
    """Satserna som bär ett åtagandeord, som (sats, ord, polaritet, fälls).

    Satsdelningen är spärrens egen: prisposten stryks först, sedan `_meningar`.
    Utfallet fås genom att kalla spärren på satsen, alltså inte genom att
    skriva av dess tre led.
    """
    priser = generera.priser_for(kategori)
    kvar = text
    for varde in priser.values():
        kvar = generera._UTAN_PRISVARDE(varde).sub(" ", kvar)

    ut = []
    for sats in generera._meningar(kvar):
        traff = generera.ATAGANDEORD.search(sats)
        if not traff:
            continue

        svans = sats[traff.end():]
        framfor = sats[: traff.start()]
        if generera._NEKAT_EFTER_ATAGANDE.match(svans):
            polaritet = "nekat efter ordet"
        elif _NEKAT_FORE_ATAGANDE.search(framfor):
            polaritet = "nekat före ordet"
        else:
            polaritet = "jakande"

        try:
            generera.krav_pa_atagande_med_kalla(sats, _forfragan(kategori))
        except Sparrfalld:
            faller = True
        else:
            faller = False

        ut.append((sats.strip(), traff.group(0).lower(), polaritet, faller))
    return ut


def _sammanstall(
    poster: list[tuple[int, str, str]],
) -> tuple[dict[str, int], list[tuple[int, str, str, str, bool]]]:
    """Antal per polaritet, och raderna bakom talen."""
    per_polaritet: dict[str, int] = {}
    rader = []
    for nr, text, kategori in poster:
        for sats, ord_, polaritet, faller in _atagandesatser(text, kategori):
            nyckel = f"{polaritet} FÄLLS" if faller else f"{polaritet} passerar"
            per_polaritet[nyckel] = per_polaritet.get(nyckel, 0) + 1
            rader.append((nr, sats, ord_, polaritet, faller))
    return per_polaritet, rader


def _skriv(rubrik: str, poster: list[tuple[int, str, str]], visa_satser: bool) -> None:
    per_polaritet, rader = _sammanstall(poster)
    texter_med = len({nr for nr, *_ in rader})

    print(f"\n{rubrik}")
    print(f"  texter                        {len(poster)}")
    print(f"  texter med åtagandeord        {texter_med}")
    print(f"  åtagandesatser                {len(rader)}")
    for nyckel, antal in sorted(per_polaritet.items()):
        print(f"    {nyckel:<28}{antal}")

    nekade = [r for r in rader if r[3].startswith("nekat")]
    nekade_fallda = [r for r in nekade if r[4]]
    print(f"  NEKANDE totalt                {len(nekade)}   "
          f"löpnr {sorted({r[0] for r in nekade})}")
    print(f"  NEKANDE SOM FÄLLS             {len(nekade_fallda)}   "
          f"löpnr {sorted({r[0] for r in nekade_fallda})}")

    if visa_satser:
        for nr, sats, ord_, polaritet, faller in rader:
            utfall = "FÄLLS   " if faller else "passerar"
            print(f"    {nr:>3}  {utfall}  {polaritet:<18} {ord_:<12} "
                  f"{maskera.maska_fritext(sats)}")


def de_tjugo() -> list[tuple[int, str, str]]:
    """Botens utkast ur körningen. Den spärrade posten räknas på sin sats."""
    poster = []
    for nr, rad in enumerate(FALL.read_text(encoding="utf-8").splitlines(), 1):
        if not rad.strip():
            continue
        post = json.loads(rad)
        text = (post.get("forslag") or "").strip() or (post.get("sparrsats") or "").strip()
        if text:
            poster.append((nr, text, post.get("etikett")))
    return poster


def _par(bara_a_traktor: bool) -> list[tuple[int, str, str]]:
    """Mattes skickade svar. Samma koppling som `faktakalla-matning::_mattes_texter`.

    `bara_a_traktor` ger de 45 Lars mätorder gäller. Utan den ger funktionen
    filens alla utgående svar, alltså också de kategorier som har en egen
    prispost och därmed egna åtagandesatser.
    """
    etiketter = {}
    for rad in OMETIKETTERADE.read_text(encoding="utf-8").splitlines():
        if rad:
            post = json.loads(rad)
            etiketter[post.get("text")] = post.get("etikett")

    poster = []
    for nr, rad in enumerate(PARFIL.read_text(encoding="utf-8").splitlines(), 1):
        if not rad:
            continue
        post = json.loads(rad)
        kategori = etiketter.get(post.get("inkommande_text"))
        if bara_a_traktor and kategori not in generera.A_TRAKTORETIKETTER:
            continue
        ut = (post.get("utgaende_text") or "").strip()
        if ut:
            poster.append((nr, ut, kategori or ""))
    return poster


def main() -> None:
    _skriv("DE TJUGO (data/granskningsfall.jsonl)", de_tjugo(), visa_satser=True)
    _skriv("MATTES A-TRAKTORSVAR (data/par.jsonl)", _par(True), visa_satser=False)

    # UTÖVER MÄTORDERN. Lars bad om de tjugo och de 45. Den här raden finns för
    # att de 45 kan ge NOLL nekanden utan att formen därmed är okänd i Mattes
    # röst: spärren prövar varje kategori som har en prispost, inte bara
    # a-traktorärenden.
    _skriv("MATTES SVAR, ALLA KATEGORIER (data/par.jsonl)", _par(False),
           visa_satser=False)


if __name__ == "__main__":
    main()
