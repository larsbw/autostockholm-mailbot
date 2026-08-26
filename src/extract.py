"""Bygger `data/par.jsonl` ur `data/tradar.jsonl`.

Ett par är en kunds text och det svar Matte eller Lars skrev på den. Mallarna
byggs ur dessa par enligt CLAUDE.md §11, alltså ur faktiska svar och inte från
grunden.

Urvalet ligger i `src/urval.py` och beskrivs i `docs/sparrar.md` under
`urval-gmail-svar`. Kriterierna kommer ur `docs/beslutslogg.md` #5, #6 och #8.

PARNINGEN. Inom en tråd paras varje svar med det NÄRMAST FÖREGÅENDE
kundmeddelandet. Meddelandena ligger i kronologisk ordning i tråden. Ett svar
utan föregående kundmeddelande blir inget par, och kastas hellre än att paras
med något senare: ett svar kan inte besvara text som inte fanns när det skrevs.

§6. Kundens adress hashas och skrivs aldrig ut. Brödtext från kund och från oss
finns i filen, eftersom det är själva underlaget, och `data/` är gitignorerad.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from src import urval

ROT = Path(__file__).resolve().parent.parent
INFIL = ROT / "data" / "tradar.jsonl"
UTFIL = ROT / "data" / "par.jsonl"

# Ett svar kortare än så här är en kvittens eller en hänvisning, inte ett svar
# att bygga en mall ur. Valt tal, inget uppmätt, och det redovisas som ett val.
MINSTA_TECKEN = 20


def _tidsstampel(meddelande: dict) -> str:
    """Kundmeddelandets tid, alltså när ärendet kom in. ISO 8601 i UTC.

    `internalDate` är millisekunder sedan epok, som sträng.
    """
    ra = meddelande.get("internalDate")
    if not ra:
        return ""
    return datetime.fromtimestamp(int(ra) / 1000, timezone.utc).isoformat()


def par_ur_trad(trad: dict) -> list[dict]:
    """Par ur en tråd, i kronologisk ordning."""
    par = []
    senaste_kund = None

    for meddelande in trad.get("messages", []) or []:
        if urval.ar_gmail_svar(meddelande):
            if senaste_kund is None:
                continue
            inkommande = urval.brodtext(senaste_kund)
            utgaende = urval.brodtext(meddelande)
            if len(inkommande) < MINSTA_TECKEN or len(utgaende) < MINSTA_TECKEN:
                continue
            par.append({
                "inkommande_text": inkommande,
                "utgaende_text": utgaende,
                "tidsstampel": _tidsstampel(senaste_kund),
                "avsandare_hash": urval.hasha(urval.kundadress(senaste_kund)),
            })
        elif urval.ar_kundmeddelande(meddelande):
            senaste_kund = meddelande

    return par


def extrahera(tradar, utfil: Path) -> dict:
    """Skriver par.jsonl och returnerar räknare.

    Skrivningen går via en .delvis-fil, av samma skäl som i `src/mine.py`: en
    körning som faller får inte lämna en halv fil som ser komplett ut.
    """
    utfil.parent.mkdir(parents=True, exist_ok=True)
    delvis = utfil.with_name(utfil.name + ".delvis")

    tradar_med_par = 0
    par_totalt = 0
    tradar_lasta = 0

    with delvis.open("w", encoding="utf-8") as fil:
        for trad in tradar:
            tradar_lasta += 1
            par = par_ur_trad(trad)
            if par:
                tradar_med_par += 1
                par_totalt += len(par)
            for post in par:
                fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    delvis.replace(utfil)
    return {
        "tradar_lasta": tradar_lasta,
        "tradar_med_par": tradar_med_par,
        "par_totalt": par_totalt,
    }


def las_tradar(sokvag: Path):
    for rad in sokvag.read_text(encoding="utf-8").splitlines():
        if rad:
            yield json.loads(rad)


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--infil", type=Path, default=INFIL)
    tolk.add_argument("--utfil", type=Path, default=UTFIL)
    arg = tolk.parse_args(argv)

    rakning = extrahera(las_tradar(arg.infil), arg.utfil)

    print(f"trådar lästa: {rakning['tradar_lasta']}")
    print(f"trådar med minst ett par: {rakning['tradar_med_par']}")
    print(f"par totalt: {rakning['par_totalt']}")
    print(f"utfil: {arg.utfil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
