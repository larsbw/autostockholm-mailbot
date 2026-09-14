#!/usr/bin/env python3
"""Hur många utkast NÄMNER priset? Skiva 45, regel 15:s enda verifikation.

    .venv/bin/python scripts/prisandel.py

**REGEL 15 BÄRS AV PROMPTEN OCH INTE AV EN SPÄRR**, enligt Lars order att binda
regeln som de övriga §11-reglerna. En spärr GÅR att bygga, och `krav_pa_ett_svar`
visar att en ren utelämning kan fällas, men en fälld spärr ger Lars INGET utkast
i stället för ett utkast utan pris, alltså vore utfallet sämre än det regeln
finns för att rätta. Verifikationen är därför den här räkningen.

*Här stod att ingen spärr KAN bära regeln, med skälet att spärrarna bara fäller
det ett svar påstår. Det var falskt, och motexemplet står i `src/generera.py`.
Fällt av §7-granskningen av skiva 45.*

**VAD MÅTTET ÄR, ORDAGRANT: förekommer postens TAL i utkastet.** Talen läses ur
`config/priser.json`-posten `a_traktorkonvertering` med generatorns egen
`_tal_i`. Ändrar Lars priset följer måttet med, och §7.2 gäller: inget tal står i
den här filen.

**VAD MÅTTET INTE ÄR.** Det prövar inte att prisets ORDALYDELSE är återgiven, och
det kan inte tillskriva ett tal en post:

- *"Vi ligger på båda gränserna, men utan moms"* räknas som HELT, trots att
  konfigvärdet säger `inklusive moms`.
- Ett tal som delas med en annan prispost, till exempel `reparation`, räknas som
  en del av a-traktorintervallet.

Därför räknas ORDAGRANNHETEN separat: bär utkastet hela konfigvärdet som en
identisk delsträng är det den starka formen, och den är det `PRISFOT` beordrar.
De två talen är alltså en ÖVRE och en UNDRE gräns för efterlevnaden.

*Här hette den grova hinken `nämner priset i SIN HELHET` och docstringen grundade
kriteriet i `PRISFOT`:s helhetskrav. Etiketten lovade det ordagranna måttet och
gav det grova. Fällt av §7-granskningen av skiva 45.*

**FILEN BÄR INGEN UPPGIFT OM VILKEN PROMPT SOM SKREV TEXTERNA.**
`data/granskningsfall.jsonl` bär etikett, kundtext, utkast, spärr och
uppslagskälla, ingenting mer. Skriptet skriver därför ut promptens och prisfilens
läge NU, som ett läge och inte som körningens härkomst, och en jämförelse mot
läget före regel 15 finns inte: körningen skrev över de tidigare fallen.

**§6: INGEN KUNDTEXT OCH INGET UTKAST SKRIVS UT.** Utdatan är antal och andelar.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generera  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
FALLFIL = ROT / "data" / "granskningsfall.jsonl"

# Samma tre etiketter som `src/vy.py::A_TRAKTORETIKETTER`.
A_TRAKTOR = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

PRISNYCKEL = "a_traktorkonvertering"


def _per_hundra(antal: int, av: int) -> str:
    """Samma form som `scripts/prismatning.py`, och samma skäl: en andel utan
    nämnare är inget mått."""
    if not av:
        return "ingen nämnare"
    return f"{antal * 100 / av:.1f} av hundra"


def main() -> int:
    if not FALLFIL.exists():
        print(f"saknas: {FALLFIL.relative_to(ROT)}")
        print("Kör scripts/kedja-prov.py --kor först.")
        return 1

    priser = generera.las_priser()
    if PRISNYCKEL not in priser:
        print(f"{PRISNYCKEL} är tom i config/priser.json.")
        print("Regel 15 har då inget pris att kräva, och måttet är odefinierat.")
        return 1

    prisvarde = priser[PRISNYCKEL]
    pristal = generera._tal_i(prisvarde)

    fall = [
        json.loads(rad)
        for rad in FALLFIL.read_text(encoding="utf-8").splitlines()
        if rad.strip()
    ]
    a_traktor = [f for f in fall if f.get("etikett") in A_TRAKTOR]
    utkast = [f for f in a_traktor if not f.get("sparr")]

    ordagrant = helt = delvis = inget = 0
    for f in utkast:
        text = f.get("forslag") or ""
        talen = generera._tal_i(text)
        if prisvarde in text:
            ordagrant += 1
        if pristal <= talen:
            helt += 1
        elif pristal & talen:
            delvis += 1
        else:
            inget += 1

    print("REGEL 15:s EFTERLEVNAD, räknad ur de SPARADE granskningsfallen")
    print(f"  källa: {FALLFIL.relative_to(ROT)}")
    print("")
    print("  LÄGET NU, och filen säger inget om vilket läge som skrev texterna:")
    star = "15." in generera.SYSTEM
    print(f"    systemprompten bär en rad som börjar med 15.: "
          f"{'ja' if star else 'NEJ'}")
    # ANTALET LÄSES, det påstås inte. En hårdkodad `ja` här hade varit sann av
    # grinden ovan och ändå ett påstående utan avläsning.
    print(f"    ifyllda poster i config/priser.json: {len(priser)}")
    print("")
    print(f"  fall totalt: {len(fall)}")
    print(f"  varav a-traktor: {len(a_traktor)}")
    print(f"  varav utkast: {len(utkast)}")
    print(f"  varav spärrade: {len(a_traktor) - len(utkast)}")
    print("")
    print("  AV UTKASTEN, stark form: hela konfigvärdet som en identisk")
    print("  delsträng, alltså det PRISFOT beordrar:")
    print(f"    antal: {ordagrant}    {_per_hundra(ordagrant, len(utkast))}")
    print("")
    print("  AV UTKASTEN, grov form: förekommer postens tal:")
    print(f"    båda gränserna: {helt}    {_per_hundra(helt, len(utkast))}")
    print(f"    en del av intervallet: {delvis}")
    print(f"    inget av talen: {inget}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
