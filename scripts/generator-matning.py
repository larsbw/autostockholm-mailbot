#!/usr/bin/env python3
"""Mäter generatorns utfall över MÅNGA körningar mot samma fem lägen.

    .venv/bin/python scripts/generator-matning.py --varv 20

**VARFÖR SKRIPTET FINNS.** Skiva 32 DEL C och DEL D kräver två tal som inte går
att gissa fram:

  DEL C  hur ofta ett svar bär ett PÅSTÅENDE OM OSS som varken kommer ur
         config eller ur uppslaget. Ingen spärr fångar formen, och Lars ordning
         är uttrycklig: MÄT FÖRST, BYGG INGEN SPÄRR. Ett mönster skrivet innan
         formen är mätt är precis vad luckorna 22 till 27 kom ur.

  DEL D  hur ofta `FORDONSORD` fäller ett ÖNSKAT svar, alltså lucka 28. En spärr
         som fäller önskade svar blir kringgången, §7.1.

**SKRIPTET KLASSIFICERAR INTE, det RÄKNAR och SKRIVER UT.** Om en text bär ett
påstående om oss är en läsarbedömning, och en regex som avgör det vore just det
mönster DEL C förbjuder. Skriptet ger därför materialet maskerat, och talet sätts
av den som läser. Det som räknas maskinellt är bara vad SPÄRRARNA gjorde.

**INGEN SÄNDNING.** Skriptet går via `generera.generera_ratext`, som inte har
någon väg till en brevlåda. `src.generera` prövas mot `vyn-har-ingen-sandvag`.

**§6.** Varje text som skrivs till fil eller skärm går genom samma maskering som
`scripts/generera-prov.py` använder, alltså identifierare plus namnkandidater ur
kundens mail OCH ur få-exemplen.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import prov_stod as prov  # noqa: E402
from src import generera, kategorisera  # noqa: E402
from src.generera import Forfragan, Sparrfalld  # noqa: E402

ROT = Path(__file__).resolve().parent.parent


def spar_per_sparr(text: str, forfragan: Forfragan) -> list[dict]:
    """Vad VARJE spärr gör med texten, var för sig.

    `krav_pa_svaret` kastar på den FÖRSTA som fäller, alltså döljer den vilka
    fler som hade fällt. Lucka 28 mäts på `genererat-fordonsfaktum` ensam, och
    den skulle bli osynlig bakom talspärren i varje svar som också bär ett tal.
    """
    utfall = []
    for namn, sparr in (
        ("genererat-tal-har-kalla", generera.krav_pa_tal_med_kalla),
        ("genererat-fordonsfaktum", generera.krav_pa_fordonsfakta_ur_uppslag),
    ):
        try:
            sparr(text, forfragan)
        except Sparrfalld as fel:
            utfall.append({"sparr": namn, "skal": fel.skal})

    try:
        generera.krav_pa_att_troskeln_inte_ar_forfattningstext(text)
    except Sparrfalld as fel:
        utfall.append({"sparr": "troskeln-som-forfattningstext", "skal": fel.skal})

    return utfall


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--varv", type=int, default=20)
    argp.add_argument("--ut", type=Path, default=None)
    args = argp.parse_args()

    exempel = generera.las_exempel()
    forfragningar = prov.las_forfragningar(len(prov.LAGEN))
    klient = kategorisera.bygg_klient()

    stampel = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M")
    utfil = args.ut or ROT / "scratchpad" / f"generator-matning-{stampel}.jsonl"
    utfil.parent.mkdir(parents=True, exist_ok=True)

    print(f"få-exempel: {len(exempel)}   lägen: {len(prov.LAGEN)}   varv: {args.varv}")
    print(f"skriver: {utfil}")
    print("")

    rader = []
    raknare: Counter[str] = Counter()

    for varv in range(1, args.varv + 1):
        for post, (namn, utfall, uppslag) in zip(forfragningar, prov.LAGEN):
            forfragan = Forfragan(
                text=post["text"],
                kategori=post["etikett"],
                utfall=utfall,
                uppslag=uppslag,
            )
            ratext = generera.generera_ratext(klient, forfragan, exempel=exempel)
            fallda = spar_per_sparr(ratext, forfragan)

            raknare["svar"] += 1
            for f in fallda:
                raknare[f["sparr"]] += 1
            if not fallda:
                raknare["passerade"] += 1

            rader.append({
                "varv": varv,
                "lage": namn,
                "fallda": fallda,
                "svar_maskerat": prov.maska_svaret(ratext, post["text"], exempel),
            })

        print(f"varv {varv}: {raknare['svar']} svar, {raknare['passerade']} passerade")

    utfil.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rader) + "\n",
        encoding="utf-8",
    )

    print("")
    print("--- SPÄRRARNA, var för sig ---")
    for nyckel in sorted(raknare):
        print(f"{nyckel:34} {raknare[nyckel]}")

    print("")
    print("--- LUCKA 28: varje fällning av genererat-fordonsfaktum ---")
    for rad in rader:
        for f in rad["fallda"]:
            if f["sparr"] == "genererat-fordonsfaktum":
                print(f"varv {rad['varv']:>3} {rad['lage']:<24} {f['skal']}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
