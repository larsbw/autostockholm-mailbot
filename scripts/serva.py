#!/usr/bin/env python3
"""VYN SOM EN SERVER SOM NÅS UTIFRÅN. `docs/beslutslogg.md` #37 och #38.

    .venv/bin/python scripts/serva.py

Skiljer sig från `scripts/kor-vy.py` på EN punkt, och den är hela skillnaden:
den här filen binder `0.0.0.0` och kräver därför en inloggning. `kor-vy.py` är
kvar oförändrad och binder loopback, alltså är den fortfarande vägen att köra
vyn lokalt utan att konfigurera någonting.

**PORTEN KOMMER UR `PORT`**, som Railway sätter. Utan den variabeln används
8765, samma tal som resten av repot.

**BINDNINGEN OCH INLOGGNINGEN GÅR INTE ATT SKILJA ÅT.**
`vy.krav_pa_inloggning_utanfor_loopback` körs i `vy.starta` och kastar om
adressen inte är loopback medan inloggningen är osatt. Den här filen kan alltså
inte öppna vyn mot nätet genom att någon glömmer en miljövariabel.

**FALLEN LÄSES INTE HÄRIFRÅN.** `vy.starta` läser referensfallen själv, och
granskningsfallen kommer ur `vy.las_granskningsfall`, alltså ur den fil
`scripts/respond.py` skrev vid den dagliga körningen.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import inloggning, sokvagar, vy  # noqa: E402

# ADRESSEN SOM TAR EMOT FRÅN NÄTET. Railway dirigerar in trafik till containern,
# och en process som bara lyssnar på loopback nås inte.
UTATBINDNING = "0.0.0.0"  # noqa: S104


def main(argv: list[str] | None = None) -> int:
    port = int(os.environ.get("PORT") or 8765)

    try:
        konfiguration = inloggning.ur_miljon()
    except inloggning.Konfigurationsfel as fel:
        print(f"FEL: {fel}", file=sys.stderr)
        return 1

    for namn, sokvag in sokvagar.kataloger().items():
        print(f"{namn}: {sokvag}")
    print(inloggning.status())

    try:
        granskning = vy.las_granskningsfall()
    except FileNotFoundError:
        granskning = []
    print(f"granskningsfall: {len(granskning)}")

    try:
        server = vy.starta(
            port=port,
            granskning=granskning,
            adress=UTATBINDNING,
            konfiguration=konfiguration,
        )
    except vy.Oskyddad as fel:
        print(f"FEL: {fel}", file=sys.stderr)
        return 1

    # §6: adressen skrivs ut som bindning och port, aldrig som en publik URL med
    # en gissad värd. Vilken domän som pekar hit vet Railway, inte den här filen.
    print(f"vyn lyssnar på {UTATBINDNING}:{port}", flush=True)
    server.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
