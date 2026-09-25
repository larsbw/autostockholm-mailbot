#!/usr/bin/env python3
"""Ett DRIFTLARM när `scripts/dagligen.py`:s körning misslyckats. SKICKAR ALDRIG.

    .venv/bin/python scripts/driftlarm.py --tid 2026-09-25T14:10:00+00:00 \\
        --exitkod 1 --fel "processen gick inte att starta"

Uppdrag 2026-09-25 DEL 2, Lars beslut: en körning av `scripts/dagligen.py` som
avslutas med fel eller en exitkod skild från noll ska ge ETT Gmail-utkast,
till info@autostockholm.se. Samma mekanism som ärendelarmet i skiva 81
(`src/gmailutkast.py::bygg_larmmeddelande`), men för DRIFTEN och inte för ett
enskilt ärende: `src/gmailutkast.py::bygg_driftlarmmeddelande`.

EGEN PROCESS, SAMMA SKÄL SOM `scripts/respond.py`
--------------------------------------------------

`scripts/dagligen.py` importerar bara stdlib och `src.sokvagar`, och den
garantin står kvar: `test_vyn_och_kedjan_nar_ALDRIG_gmailutkast
[scripts.dagligen]` binder att `src.gmailutkast` aldrig får stå i den filens
importgraf, Lars beslut i skiva 69. Den här filen är i stället en FRISTÅENDE
process, startad av `scripts/dagligen.py::_larma_vid_fel` som en subprocess,
aldrig importerad.

FYRA LAGER, SAMMA SOM `src/gmailutkast.py` GER FÖR UTKASTVÄGEN
-----------------------------------------------------------------

Se den modulens docstring. `krav_pa_sandvagsfrihet` körs här, vid `main`, av
samma skäl `scripts/respond.py::_kor` kör den: en onamngiven Gmail-modul i
grafen ska fällas vid uppstart, inte som ett 403 mitt i ett larm.

THROTTLINGEN SKÖTS AV ANROPAREN
--------------------------------

Högst ett larm var sjätte timme, Lars beslut, är `scripts/dagligen.py`:s
ansvar: den filen läser `logg/drift-larm.jsonl` INNAN den ens startar den här
processen, och skriver raden efteråt om larmet lyckades. Den här filen skapar
bara det utkast den blir ombedd om och skriver INGENTING till disk.

§6. Bara drifttext går in: tid, exitkod, `dagligen.kor`s egen sanerade sista
rad. Ingen kundtext finns i vägen hit.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import gmailutkast, vy  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    tolk.add_argument("--tid", required=True,
                      help="körningens starttid, ISO 8601")
    tolk.add_argument("--exitkod", type=int, required=True,
                      help="exitkoden den misslyckade körningen gav")
    tolk.add_argument("--fel", default="",
                      help="dagligen.kor's egen sanerade sista stderr-rad, "
                           "eller tom sträng")
    arg = tolk.parse_args(argv)

    # LAGER 3 OCH 4, före allt annat. Se `src/gmailutkast.py`s docstring.
    vy.krav_pa_sandvagsfrihet("scripts.driftlarm", tillatna=vy.UNDANTAGBARA)
    print("SPÄRR lager 3 och 4: gmail nås bara via de namngivna modulerna, "
          "och grafen bär inget sändanrop.")

    try:
        tjanst = gmailutkast.skriv_tjanst()
    except Exception as fel:  # noqa: BLE001
        print(f"FEL: kunde inte bygga skrivtjänsten ({type(fel).__name__}). "
              "Kör python -m src.auth --skriv.")
        return 1

    try:
        resultat = gmailutkast.skapa_driftlarmutkast(
            tjanst, tid=arg.tid, exitkod=arg.exitkod, fel=arg.fel)
    except Exception as fel:  # noqa: BLE001
        print(f"FEL: driftlarmet misslyckades ({type(fel).__name__})")
        return 1

    print(f"DRIFTLARM skapat, meddelande-id {resultat.meddelande_id}, "
          "INTE skickat")
    return 0


if __name__ == "__main__":
    sys.exit(main())
