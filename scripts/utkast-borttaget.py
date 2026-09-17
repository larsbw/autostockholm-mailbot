#!/usr/bin/env python3
"""Loggar att ett Gmail-utkast är borttaget, efter att läsvägen bekräftat det.

    .venv/bin/python scripts/utkast-borttaget.py <gmail-id> [<gmail-id> ...]

Skiva 75. `vy.gmailutkast_finns` spärrar en tråd för nya utkast så länge
trådens senaste rad i `logg/omdomen.jsonl` inte är `borttaget`. Den raden
skrivs bara här, och bara när tråden i Gmail har meddelanden men varken bär
utkastet, något annat utkast eller ett eget utgående meddelande. Allt annat
vägras.

**SÄKERHETEN VILAR PÅ ATT `threads.get` VISAR UTKAST MED ETIKETTEN `DRAFT`.**
Det är iakttaget i backfillens skörd, se `urval.ar_kundmeddelande`, och inte
uppslaget i Googles dokumentation.

Läser med `token-las.json` genom `inkorg.Lastjanst`. Skriver ingen kundtext,
bara Gmails id och utfallet.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import inkorg, mine, urval, vy  # noqa: E402


def senaste_skapat(gmail_id: str, omdomesfil: Path) -> dict | None:
    """Raden `skapat` för utkastet, eller None."""
    funnen = None
    for rad in omdomesfil.read_text(encoding="utf-8").splitlines():
        try:
            post = json.loads(rad)
        except ValueError:
            continue
        if (isinstance(post, dict)
                and post.get("omdome") == vy.OMDOME_GMAILUTKAST
                and post.get("utfall") == "skapat"
                and post.get("gmail_id") == gmail_id):
            funnen = post
    return funnen


def markera(gmail_id: str, tjanst, omdomesfil: Path) -> str:
    """Utfallet i ord. Skriver raden bara när allt stämmer."""
    post = senaste_skapat(gmail_id, omdomesfil)
    if post is None:
        return "VÄGRAT: inget skapat utkast med det id:t i loggen"
    trad_id = post["trad_id"]
    if not vy.gmailutkast_finns(trad_id, omdomesfil):
        return "VÄGRAT: tråden är redan markerad"
    trad = mine.hamta_trad(tjanst, trad_id, pacer=mine.Kvotpacer(),
                           forbrukning=mine.Forbrukning())
    meddelanden = trad.get("messages") or []
    # En tråd med en `skapat`-rad bär minst kundens meddelande. Ett tomt svar
    # är inget belägg för något. Fällt av §7-granskningen av skiva 75.
    if not meddelanden:
        return "VÄGRAT: Gmail gav inga meddelanden för tråden"
    if any(m.get("id") == gmail_id for m in meddelanden):
        return "VÄGRAT: utkastet finns kvar i Gmail"
    if any("DRAFT" in (m.get("labelIds") or []) for m in meddelanden):
        return "VÄGRAT: tråden bär ett annat utkast"
    # ETT SKICKAT SVAR ÄR INTE ETT BORTTAGET UTKAST. Har tråden ett eget
    # utgående meddelande kan utkastet ha skickats, eller någon ha svarat för
    # hand. Då ska tråden förbli stängd. Fällt av §7-granskningen av skiva 75.
    if any(not urval.ar_kundmeddelande(m)
           and "DRAFT" not in (m.get("labelIds") or []) for m in meddelanden):
        return "VÄGRAT: tråden bär ett eget utgående meddelande"
    fall = vy.Fall(etikett=post.get("etikett", ""), kalla="gmailutkast",
                   text="", tidsstampel=post.get("tidsstampel", ""),
                   avsandare_hash=post.get("avsandare_hash", ""))
    vy.spara_gmailutkast(fall, trad_id, vy.BORTTAGET, gmail_id,
                         omdomesfil=omdomesfil)
    return "markerat borttaget"


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    tjanst = inkorg.las_tjanst()
    fel = 0
    for gmail_id in argv:
        utfall = markera(gmail_id, tjanst, vy.OMDOMEN)
        fel += utfall.startswith("VÄGRAT")
        print(f"{gmail_id}: {utfall}")
    return 1 if fel else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
