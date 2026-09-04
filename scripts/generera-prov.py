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

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import kategorisera, maskera  # noqa: E402
from src.fordonsuppslag import Uppslag, Utfall  # noqa: E402
from src.generera import Forfragan, Sparrfalld, generera_utkast, las_exempel  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"

A_TRAKTOR = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# **HÄR STOD EN MODULGLOBAL `EXEMPEL_I_PROMPTEN`, och den var en fälla.** Den
# fylldes bara i `main`, alltså gav ett anrop av `maska_svaret` utanför `main`
# en TOM lista och därmed exakt den §6-läcka varv 1 fällde, tyst och utan att
# något test märkte det. Det är formen `docs/incidentlogg.md` I1 handlar om.
#
# Exemplen skickas nu som ARGUMENT. En anropare som glömmer dem får ett fel av
# Python i stället för en tyst omaskerad rad.

# DE FEM LÄGENA. Uppslagen är KONSTRUERADE, inte avlästa: skiva 31 kopplar inte
# in hämtningen. Det står i utdatan vid varje fall.
LAGEN = [
    ("grönt", Utfall.GRONT,
     Uppslag(tjanstevikt_kg=1450, slapvagnsvikt_kg=1500, draganordning=True)),
    ("gult", Utfall.GULT,
     Uppslag(tjanstevikt_kg=1450, slapvagnsvikt_kg=1500, draganordning=False)),
    ("oklart", Utfall.OKLART, None),
    ("rött", Utfall.ROTT,
     Uppslag(tjanstevikt_kg=980, slapvagnsvikt_kg=600, draganordning=False)),
    ("uppslaget misslyckades", None, None),
]


def maska_svaret(svar: str, kundens_mail: str, exempel: list[dict]) -> str:
    """Botens svar med identifierare och namn maskerade.

    Namnen hämtas ur kundens mail OCH ur få-exemplen, eftersom prompten matar in
    sex verkliga par i klartext och modellen därför har andra kunders namn i
    kontexten. Genitiv och bestämd form maskeras med.

    *Här stod att namnen hämtas "ur kundens eget mail, inte ur svaret" och att
    kundens persondata "inte kan stå i svaret utan att ha stått i mailet". Båda
    leden var falska, och kommentaren i funktionskroppen skrev ut det medan
    docstringen ovanför stod kvar. Fällt av §7-granskningen av skiva 31, varv 2.*
    """
    ut = maskera.maska_identifierare(svar)

    # KANDIDATERNA HÄMTAS UR KUNDENS MAIL **OCH UR FÅ-EXEMPLEN**.
    #
    # Motiveringen "kundens persondata kan inte stå i svaret utan att ha stått i
    # mailet" var FALSK: prompten matar in sex verkliga par i klartext, alltså
    # har modellen ANDRA kunders namn i kontexten och ett demonstrerat mönster
    # att inleda med ett namn. Ett namn ur ett få-exempel hade gått ut omaskerat.
    # Fällt av §7-granskningen av skiva 31.
    #
    # `EJ_NAMN` i `src/maskera.py` skyddar verkstadens egna ord; Matte och Auto
    # Stockholm står i klartext i CLAUDE.md och maskeras inte här heller.
    kallor = [kundens_mail] + [
        p["inkommande_text"] + " " + p["utgaende_text"] for p in exempel
    ]
    kandidater = set()
    for kalla in kallor:
        kandidater.update(maskera.namnkandidater(kalla))

    kandidater = sorted(kandidater, key=len, reverse=True)
    if not kandidater:
        return ut

    # ETT SVEP, INTE ETT PER NAMN. Formulärets etikett "Namn:" gör ordet "namn"
    # till en kandidat, och en ersättning i taget lät den sedan matcha INUTI sin
    # egen platshållare: `Hej [NAMN],` blev `Hej [[NAMN]],`. En alternation kan
    # inte träffa text den själv nyss skrivit.
    #
    # **GENITIV OCH BESTÄMD FORM MÅSTE MED.** Ordgränsen i högerändan lät
    # `Sigrids bil` och `Bengts bil` gå ut OMASKERADE, och genitiv är den
    # naturligaste formen i just den mening en verkstad skriver. Fällt av
    # §7-granskningen av skiva 31, varv 2.
    monster = re.compile(
        r"\b(" + "|".join(re.escape(k) for k in kandidater) + r")(s|en|et|ens)?\b",
        flags=re.IGNORECASE,
    )
    return monster.sub("[NAMN]", ut)


def las_forfragningar(antal: int) -> list[dict]:
    """De kortaste a-traktormailen, så att utskriften går att läsa."""
    rader = [
        json.loads(r)
        for r in OMETIKETTERADE.read_text(encoding="utf-8").splitlines()
        if r
    ]
    a_traktor = [p for p in rader if p["etikett"] in A_TRAKTOR and p["text"].strip()]
    a_traktor.sort(key=lambda p: len(p["text"]))
    # Hoppar över de allra kortaste, som ofta är fragment utan fråga.
    return a_traktor[5 : 5 + antal]


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
