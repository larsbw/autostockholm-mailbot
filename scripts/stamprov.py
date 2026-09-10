r"""Mäter om en stam går att sätta UTAN vänstergräns i en termtupel.

Skiva 34, varv 3. Lucka 32 har sagts vara stängd två gånger, båda gångerna
genom att de former ett fynd RÄKNADE UPP lades till som termer. Varv 2 mätte
upp sex former till. Det här skriptet finns för att svaret ska bli MÄTT i
stället för resonerat: för varje stam ställs frågan om en gränslös lydelse
fäller något ord som faktiskt förekommer i verkstadens egen text.

Korpusen är `data/par.jsonl`, alltså Matte och Lars faktiska svar, plus varje
rad i testfilernas versala list- och tupelkonstanter. **Det inkluderar
`TROSKEL_SKA_FALLA`, alltså rader som SKA fällas**, och en träff där är inget
larm. Utdatan skriver därför ut varifrån varje träff kommer, så att läsaren kan
skilja dem åt.

**UTFALLET `OBELAGD` ÄR INTE SAMMA SAK SOM SÄKER**, och det ledet har redan
missbrukats: skiva 34 varv 3 citerade det här skriptet som belägg för att
`lagrum\w*` fäller `slagrum` och att `lagen\b` fäller `uppslagen`. Skriptet sade
OBELAGD för båda. Korpusen bär inte de orden, alltså kan den inte belägga något
om dem. Riskordsprövningen nedan finns för att fylla just det hålet, och dess
lista är HANDSKRIVEN och därmed lika ofullständig som den som skrev den.

*Här stod "plus varje rad i testfilernas 'ska passera'-uppsättningar", vilket var
falskt om `_korpus`, som tar varje versal konstant. Fällt av §7-granskningen av
skiva 34, varv 3.*

§9: anropas literalt, ingen skalexpansion.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

PARFIL = ROT / "data" / "par.jsonl"

# Stammar som prövas. Varje rad är den lydelse som ÖVERVÄGS, alltså utan
# vänstergräns, och den form som motiverade att den övervägs.
#
# **VARJE STAM SOM FAKTISKT TAPPADE SIN VÄNSTERGRÄNS I SKIVA 34 STÅR HÄR.**
# Första lydelsen prövade fem av dem och utelämnade `kräv`, `laglig`,
# `lagstadga`, `regelverk`, `trafikverket`, `transportstyrelsen` och `vvfs`,
# alltså gällde påståendet "tillämpningen är mätt" en delmängd av det som
# ändrades. Fällt av §7-granskningen av skiva 34, varv 3.
KANDIDATER = (
    (r"lagenlig\w*", "lagenligt"),
    (r"lagstift\w+", "Lagstiftaren"),
    (r"lagändring\w*", "Lagändringen"),
    (r"lagrum\w*", "Lagrummet"),
    (r"kräv\w*", "påkrävt, gränsen släppt i skiva 34"),
    (r"laglig\w*", "olagligt, olagliga"),
    (r"lagstadga\w+", "lagstadgat"),
    (r"regelverk\w*", "Regelverket"),
    (r"trafikverket\w*", "Trafikverkets"),
    (r"transportstyrelsen\w*", "Transportstyrelsens"),
    (r"vvfs\w*", "VVFS-beteckningar"),
    (r"lagen\b", "Vägtrafiklagen, Trafiklagen"),
    (r"lag\w*", "hela stammen, som kontroll"),
)

# Ord som prövas mot varje kandidat OAVSETT korpusen. Handskriven och därmed
# ofullständig, men den fångar det korpusen är för liten för att bära.
RISKORD = (
    "lagar", "lagat", "lagning", "lager", "lagret", "underlag", "underlaget",
    "uppslag", "uppslaget", "uppslagen", "förslagen", "avslagen", "beslagen",
    "utslagen", "anlagt", "lagom", "slagrum", "påkrävt", "kravet", "krävs",
    "reglerventilen", "reglerbar", "belägen", "verkstaden", "besiktning",
)


def _korpus() -> list[tuple[str, str]]:
    """Varje textstycke i materialet, med sin härkomst."""
    stycken: list[tuple[str, str]] = []

    if PARFIL.exists():
        for nr, rad in enumerate(PARFIL.read_text(encoding="utf-8").splitlines(), 1):
            if not rad.strip():
                continue
            par = json.loads(rad)
            for falt in ("fraga", "svar"):
                if par.get(falt):
                    stycken.append((par[falt], f"par.jsonl:{nr}:{falt}"))

    from tests import test_generera_monster as tgm

    for namn in dir(tgm):
        if not namn.isupper():
            continue
        varde = getattr(tgm, namn)
        if not isinstance(varde, (list, tuple)):
            continue
        for post in varde:
            text = post[0] if isinstance(post, (list, tuple)) and post else post
            if isinstance(text, str):
                stycken.append((text, f"test_generera_monster.{namn}"))

    return stycken


def main() -> int:
    korpus = _korpus()
    print(f"korpus: {len(korpus)} stycken")
    print()

    for lydelse, motiv in KANDIDATER:
        monster = re.compile(lydelse, re.IGNORECASE)
        med_grans = re.compile(r"\b" + lydelse, re.IGNORECASE)

        # Ett ord är ett FYND bara om den gränslösa lydelsen tar det OCH den
        # gränsade inte gör det. Annars är ordet inte en följd av att gränsen
        # tas bort.
        fynd: dict[str, str] = {}
        for text, varifran in korpus:
            for traff in monster.finditer(text):
                helt = re.search(
                    r"[\wåäöÅÄÖ]*" + re.escape(traff.group(0)) + r"[\wåäöÅÄÖ]*",
                    text[max(0, traff.start() - 30):],
                    re.IGNORECASE,
                )
                helord = helt.group(0) if helt else traff.group(0)
                if med_grans.search(helord):
                    continue
                fynd.setdefault(helord.lower(), varifran)

        # Riskorden prövas separat, eftersom korpusen är för liten för att bära
        # dem. Ett riskord som fälls är ett LARM oavsett vad korpusen säger.
        riskfynd = [o for o in RISKORD
                    if monster.search(o) and not med_grans.search(o)]

        if fynd:
            print(f"  {lydelse:<22} KORPUS: fäller {len(fynd)} ord  ({motiv})")
            for ord_, varifran in sorted(fynd.items())[:8]:
                print(f"      {ord_}   {varifran}")
        else:
            print(f"  {lydelse:<22} KORPUS: OBELAGD  ({motiv})")

        if riskfynd:
            print(f"      RISKORD: {', '.join(riskfynd)}")

    print()
    print("OBELAGD betyder att korpusen inte bär ett motexempel, inte att")
    print("lydelsen är säker. RISKORD-listan är handskriven och fyller det")
    print("hålet bara så långt den som skrev den tänkte. Verdiktet sätts av")
    print("den som läser, aldrig här.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
