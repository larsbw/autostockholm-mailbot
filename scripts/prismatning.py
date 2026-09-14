#!/usr/bin/env python3
"""Vad kostar prissatsregeln i överblockering? Skiva 42, Lars mätorder.

    .venv/bin/python scripts/prismatning.py

**FRÅGAN LARS STÄLLDE.** Lucka 54 stängs genom att angränsande satspar fogas
samman när ett prisord spänner över skarven. Varje hopfogning gör en sats större,
och prisgrenen kräver att VARJE tal i en prissats kommer ur `config/priser.json`.
Fler tal i samma sats betyder alltså fler fällningar. Ordern: mät
överblockeringen efter ändringen, och säg det om den blir värre än fem falska
fällningar av hundra.

**VAD SOM RÄKNAS SOM EN FALSK FÄLLNING.** En sats som bär ett prisord och minst
ett tal som INTE sitter ihop med ett valutaord. En sådan sats faller även när
priset i den är korrekt avläst ur `config/priser.json`, eftersom det andra talet
inte kommer därifrån. Det är lucka 55:s form, och `docs/sparrar.md` bär de två
uppmätta exemplen.

Satser utan tal alls räknas INTE som falska fällningar: *"Det kostar en del"* är
ett prisbesked utan avläsbar källa, och att det faller är spärrens syfte.

**INGEN SIMULERAD PRISFIL, och det är avsiktligt.** Måttet är en EGENSKAP hos
texten, inte ett utfall mot en påhittad prislista. Ett tal som ligger i en
prissats utan att bära ett valutaord faller oavsett vilka priser Lars fyller i,
alltså behöver mätningen inte gissa hans siffror. §7.2: vet du inte, skriv inte.

**DELTAT MOT FÖRE ÄNDRINGEN MÄTS I SAMMA KÖRNING.** Den gamla uppdelningen
byggs om här, ur `_meningar` plus reserven, så att hopfogningens FAKTISKA
påverkan går att läsa och inte bara resoneras fram.

**§6: INGEN KUNDTEXT SKRIVS UT.** Skripten läser `data/par.jsonl` och
`data/granskningsfall.jsonl`, som båda bär text i klartext. Utdatan består av
antal och andelar. Ingen sats, ingen mening och inget fragment skrivs ut.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generera  # noqa: E402
from src.generera import PRISORD  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
PAR = ROT / "data" / "par.jsonl"
FALLFIL = ROT / "data" / "granskningsfall.jsonl"

# Samma tre etiketter som `src/vy.py::A_TRAKTORETIKETTER` och
# `scripts/prov_stod.py`.
A_TRAKTOR = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# ETT TAL SOM SITTER IHOP MED ETT VALUTAORD, alltså ett tal som ÄR ett pris.
#
# **MÖNSTRET ÄR MÄTVERKTYGETS EGET OCH INGEN SPÄRR.** Spärren i `src/generera.py`
# skiljer inte prispengar från andra tal, och det är just den egenskapen som
# mäts här. Skulle mönstret missa en form räknas det talet som ett icke-pristal,
# alltså drar mätningen åt att RAPPORTERA FLER falska fällningar än det finns.
# Det är den riktning ett mätfel ska luta åt när talet ska jämföras mot en gräns.
PRISTAL = re.compile(
    r"\d[\d\s.]*\s*(?:kr\b|kronor\b|sek\b|tkr\b|:-)",
    flags=re.IGNORECASE,
)


def _gamla_prissatser(svar: str) -> list[str]:
    """Uppdelningen FÖRE skiva 42, ordagrant som den stod i `a11b6c1`.

    Byggd här och inte importerad, eftersom den inte finns kvar i `src/`. Den är
    det enda sättet att mäta vad hopfogningen faktiskt ändrade.
    """
    satser = [s for s in generera._meningar(svar) if PRISORD.search(s)]
    if not satser and PRISORD.search(svar):
        return [svar]
    return satser


def _hopfogningen_lopte(svar: str) -> bool:
    """Fogade kedjefogningen faktiskt ihop två meningar i den här texten?

    **DET ÄR INTE SAMMA SAK SOM ATT UPPDELNINGEN ÄNDRADES.** `nya != gamla` är
    falskt också när hopfogningen löpte men gamla vägens RESERV gav samma
    resultat, vilket den gjorde för varje text som bara bar EN prissats. En
    slutsats om att hopfogningen inte löpte gick alltså inte att dra ur det
    måttet. Fällt av §7-granskningen av skiva 42, varv 1.
    """
    delar = generera._delat_pa_mening(svar)
    return len(delar) > 1 and any(
        generera._prisord_over_skarven(delar[i], delar[i + 1])
        for i in range(len(delar) - 1)
    )


def _icke_pristal(sats: str) -> set[str]:
    """Talen i satsen som INTE sitter ihop med ett valutaord."""
    alla = generera._tal_i(sats)
    priser: set[str] = set()
    for traff in PRISTAL.finditer(sats):
        priser |= generera._tal_i(traff.group(0))
    return alla - priser


def _matt(texter: list[str]) -> dict:
    """Räknar texterna, satserna och de falska fällningarna."""
    matt = {
        "texter": len(texter),
        "texter_med_prisord": 0,
        "texter_med_falsk_fallning": 0,
        "prissatser": 0,
        "prissatser_utan_tal": 0,
        "prissatser_med_bara_pristal": 0,
        "prissatser_med_ovrigt_tal": 0,
        "texter_dar_hopfogningen_lopte": 0,
        "texter_som_bytte_uppdelning": 0,
        "texter_som_bytte_till_falsk_fallning": 0,
    }

    for text in texter:
        nya = generera._prissatser(text)
        gamla = _gamla_prissatser(text)

        if PRISORD.search(text):
            matt["texter_med_prisord"] += 1
        if _hopfogningen_lopte(text):
            matt["texter_dar_hopfogningen_lopte"] += 1
        if nya != gamla:
            matt["texter_som_bytte_uppdelning"] += 1

        falsk_nu = False
        for sats in nya:
            matt["prissatser"] += 1
            if not generera._tal_i(sats):
                matt["prissatser_utan_tal"] += 1
            elif _icke_pristal(sats):
                matt["prissatser_med_ovrigt_tal"] += 1
                falsk_nu = True
            else:
                matt["prissatser_med_bara_pristal"] += 1

        falsk_forr = any(
            generera._tal_i(s) and _icke_pristal(s) for s in gamla
        )
        if falsk_nu:
            matt["texter_med_falsk_fallning"] += 1
            if not falsk_forr:
                matt["texter_som_bytte_till_falsk_fallning"] += 1

    return matt


def _per_hundra(antal: int, av: int) -> str:
    if not av:
        return "ingen nämnare"
    return f"{antal * 100 / av:.1f} av hundra"


def _skriv(rubrik: str, kalla: str, matt: dict) -> None:
    print(f"\n{rubrik}")
    print(f"  källa: {kalla}")
    print(f"  texter: {matt['texter']}")
    print(f"  texter som bär ett prisord: {matt['texter_med_prisord']}")
    print(f"  prissatser totalt: {matt['prissatser']}")
    print(f"    utan tal alls: {matt['prissatser_utan_tal']}")
    print(f"    bara pristal: {matt['prissatser_med_bara_pristal']}")
    print(f"    MED ETT ÖVRIGT TAL: {matt['prissatser_med_ovrigt_tal']}")
    print("")
    print("  FALSKA FÄLLNINGAR, alltså texter med minst en prissats som bär ett")
    print("  tal utan valutaord. De faller även med priset korrekt avläst:")
    falska = matt["texter_med_falsk_fallning"]
    print(f"    antal: {falska}")
    print(f"    av alla texter: {_per_hundra(falska, matt['texter'])}")
    print(f"    av texter med prisord: "
          f"{_per_hundra(falska, matt['texter_med_prisord'])}")
    print("")
    print("  HOPFOGNINGENS EGET BIDRAG, skiva 42:")
    print(f"    texter där hopfogningen LÖPTE: "
          f"{matt['texter_dar_hopfogningen_lopte']}")
    print(f"    texter vars uppdelning ändrades: "
          f"{matt['texter_som_bytte_uppdelning']}")
    print(f"    texter som BLEV en falsk fällning av ändringen: "
          f"{matt['texter_som_bytte_till_falsk_fallning']}")


def _las_jsonl(sokvag: Path) -> list[dict]:
    if not sokvag.exists():
        return []
    return [json.loads(r)
            for r in sokvag.read_text(encoding="utf-8").splitlines() if r.strip()]


def main() -> int:
    par = _las_jsonl(PAR)
    if not par:
        print(f"saknas: {PAR.relative_to(ROT)}")
        return 1

    utgaende = [(p.get("utgaende_text") or "").strip() for p in par]
    utgaende = [t for t in utgaende if t]

    print("PRISSATSREGELNS ÖVERBLOCKERING, mätt i skiva 42")
    print("")
    print("En falsk fällning är en text med minst en prissats som bär ett tal")
    print("utan valutaord. En sådan sats faller av prisgrenen även när priset i")
    print("den står ordagrant i config/priser.json, eftersom det ANDRA talet")
    print("inte kommer därifrån. Det är lucka 55:s form.")

    _skriv("ALLA UTGÅENDE SVAR I UNDERLAGET",
           f"{PAR.relative_to(ROT)}, fältet utgaende_text", _matt(utgaende))

    etiketter = {}
    for post in _las_jsonl(ROT / "data" / "ometiketterade.jsonl"):
        etiketter[(post.get("text") or "").strip()] = post.get("etikett")

    a_traktor = [
        (p.get("utgaende_text") or "").strip()
        for p in par
        if etiketter.get((p.get("inkommande_text") or "").strip()) in A_TRAKTOR
    ]
    a_traktor = [t for t in a_traktor if t]
    if a_traktor:
        _skriv("BARA A-TRAKTORSVAREN, alltså den kategori som är live",
               f"{PAR.relative_to(ROT)} filtrerad på etikett", _matt(a_traktor))

    fall = _las_jsonl(FALLFIL)
    forslag = [(p.get("forslag") or "").strip() for p in fall]
    forslag = [t for t in forslag if t]
    if forslag:
        _skriv("BOTENS EGNA UTKAST ur den sparade körningen",
               f"{FALLFIL.relative_to(ROT)}, fältet forslag", _matt(forslag))
    else:
        print(f"\ninga utkast i {FALLFIL.relative_to(ROT)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
