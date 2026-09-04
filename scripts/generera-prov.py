#!/usr/bin/env python3
"""Kör generatorn mot fem verkliga a-traktormail och skriver ut svaren MASKERADE.

    .venv/bin/python scripts/generera-prov.py

**INGEN SÄNDNING.** Skriptet importerar `src.generera`, som saknar sändväg, och
skriver bara till stdout. Det finns ingen `--send` här och ingen väg till en
brevlåda.

**§6: ALLT SOM SKRIVS UT ÄR MASKERAT.** Både kundens mail och botens svar går
genom `src.maskera.maska_fritext` innan de når skärmen, eftersom utdatan är
avsedd att klistras in i en rapport. Kundtexten läses ur gitignorerade `data/`.

**`maska_fritext` OCH INTE `maska`.** Den senare maskerar adress, regnr och
siffror men INTE NAMN. Första körningen av det här skriptet använde den och
skrev tre kundnamn i klartext till skärmen. Skillnaden står i `src/maskera.py`:
bara `maska_fritext` anropar `_maska_namn`.

**BOTENS SVAR MASKERAS RIKTAT, och det är ett medvetet val.** `maska_fritext`
maskerar VARJE versalt ord, alltså också "Hej", "Vi" och varje meningsinledning,
och då går svaret inte att läsa. Skivans syfte är att Lars ska kunna läsa vad
boten skriver.

Svaret maskeras därför med identifierarna plus namnen ur kundens eget mail OCH
ur få-exemplen, hämtade med `maskera.namnkandidater`. Exemplen står i prompten i
klartext, alltså har modellen andra kunders namn i kontexten, och den kan skriva
ut ett av dem.

`Matte` och `Auto Stockholm` maskeras inte: de är verkstadens egna och står redan
i klartext i CLAUDE.md och `docs/`.

**ETT MAIL PER UTFALL om det går.** Fem förfrågningar, och utfallen sätts av
`fordonsuppslag.utvardera` när ett uppslag finns. Uppslag görs INTE här: skiva 31
bygger generatorn, inte kopplingen till hämtningen. Utfallen konstrueras därför
för att täcka grönt, gult, oklart, rött och misslyckat, och det står utskrivet i
utdatan så att ingen läser dem som avlästa.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prov_stod import LAGEN, OMETIKETTERADE, las_forfragningar, maska_svaret  # noqa: E402
from src import kategorisera, maskera  # noqa: E402
from src.generera import Forfragan, Sparrfalld, generera_utkast, las_exempel  # noqa: E402

ROT = Path(__file__).resolve().parent.parent

# **LÄGENA, MASKERINGEN OCH URVALET BOR I `scripts/prov_stod.py`.** De flyttades
# dit när `scripts/generator-matning.py` behövde exakt samma tre saker. Ett andra
# exemplar av `maska_svaret` hade varit två §6-vägar att hålla i takt.


def main() -> int:
    if not OMETIKETTERADE.exists():
        print("saknas: data/ometiketterade.jsonl")
        return 1

    exempel = las_exempel()
    print(f"få-exempel ur par.jsonl, a-traktorpar: {len(exempel)}")
    print("")

    klient = kategorisera.bygg_klient()
    forfragningar = las_forfragningar(len(LAGEN))

    for post, (namn, utfall, uppslag) in zip(forfragningar, LAGEN):
        forfragan = Forfragan(
            text=post["text"],
            kategori=post["etikett"],
            utfall=utfall,
            uppslag=uppslag,
        )

        print("=" * 72)
        print(f"LÄGE: {namn}   KATEGORI: {post['etikett']}")
        if uppslag is None:
            print("UPPSLAG: inget")
        else:
            print(
                f"UPPSLAG (konstruerat): tjänstevikt {uppslag.tjanstevikt_kg} kg, "
                f"släpvagnsvikt {uppslag.slapvagnsvikt_kg} kg, "
                f"draganordning {'ja' if uppslag.draganordning else 'nej'}"
            )
        print("")
        print("KUNDENS MAIL, maskerat:")
        print(maskera.maska_fritext(post["text"]).strip())
        print("")

        try:
            utkast = generera_utkast(klient, forfragan, exempel=exempel)
        except Sparrfalld as fel:
            print(f"SPÄRRAD av {fel.sparr}")
            print(f"skäl: {fel.skal}")
            print("")
            continue

        print("BOTENS UTKAST, maskerat:")
        print(maska_svaret(utkast, post["text"], exempel).strip())
        print("")

    return 0


if __name__ == "__main__":
    sys.exit(main())
