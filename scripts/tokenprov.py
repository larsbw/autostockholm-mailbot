#!/usr/bin/env python3
"""Prövar att båda tokenerna går att förnya. Körs av `scripts/dagligen.py` vid start.

    .venv/bin/python scripts/tokenprov.py

Exitkod 0 när båda förnyas, 1 annars. Varje token får en rad på stdout med
Googles skäl i klartext, aldrig tokenens innehåll.

**EGEN PROCESS AV SAMMA SKÄL SOM `scripts/respond.py`.** `scripts/dagligen.py`
importerar bara stdlib och `src.sokvagar`, och förnyelsen kräver `google.auth`.

Lars beslut 2026-10-18: tokenerna dog 2026-10-12 när lösenordet byttes, och
slingan stod still i sex dygn utan att något larmade.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import auth  # noqa: E402

TOKENS = ((auth.LASTOKEN, auth.LASSCOPES), (auth.SKRIVTOKEN, auth.SKRIVSCOPES))


def main(prova=auth.prova_fornyelse) -> int:
    kod = 0
    for sokvag, scopes in TOKENS:
        try:
            prova(sokvag, scopes)
        except Exception as fel:  # noqa: BLE001
            print(f"[tokenprov] FEL {type(fel).__name__}: {fel}", flush=True)
            kod = 1
        else:
            print(f"[tokenprov] {sokvag.name}: förnyad", flush=True)
    return kod


if __name__ == "__main__":
    sys.exit(main())
