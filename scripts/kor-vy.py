#!/usr/bin/env python3
"""Startar utkastvyn på localhost.

    .venv/bin/python scripts/kor-vy.py

**LOKALT OCH INGET ANNAT.** Skiva 27 bygger vyn för att den ska gå att se och
rätta innan den exponeras. Ingen Railway, ingen inloggning, ingen port utåt:
`src.vy.starta` binder uttryckligen `127.0.0.1`, alltså tar servern inte emot
något från nätet. Hosting och auth är en egen skiva, se `docs/beslutslogg.md`
#38.

Sändvägsspärren körs av `starta` innan servern binder porten. Kastar den, startar
vyn inte, och det är avsikten: en vy som kan skicka mail ska inte gå att köra.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import vy  # noqa: E402


def main(argv: list[str]) -> int:
    port = int(argv[0]) if argv else 8765

    fall = vy.las_fall()
    if not fall:
        print("Inga a-traktorfall i data/ometiketterade.jsonl. Kör mining först.")
        return 1

    server = vy.starta(port, fall)

    # Antalet är AVLÄST ur listan, inte påstått. Fördelningen mellan de två
    # populationerna avgör vilka utfall som går att täcka.
    med_svar = sum(1 for f in fall if f.kalla == "med svar")
    print(f"fall: {len(fall)}, varav med svar {med_svar}")
    print(f"vyn kör på http://127.0.0.1:{port}/referens/0")
    print("avsluta med ctrl-c")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
