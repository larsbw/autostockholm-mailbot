#!/usr/bin/env python3
"""Mäter hur väl `data/ometiketterade.jsonl` går att koppla till andra filer.

    .venv/bin/python scripts/par-koppling.py

VARFÖR SKRIPTET FINNS. `src/vy.py::las_fall` lämnar hash och tidsstämpel TOMMA
för de obesvarade fallen i stället för att hitta på dem, och skälet är en mätning
av hur många rader som faktiskt går att koppla. §7.2 kräver att ett tal är avläst
ur en körning eller en committad källa, och §9 kräver att en räkning som bär ett
styrdokuments påstående ligger i ett committat skript. Utan skriptet var talen
OPRÖVADE, vilket §7-granskningen av skiva 27 mätte upp som ett fynd.

Samma skäl som `scripts/regnr-matning.py`, och samma skäl som Lars angav i skiva
11: en mätning som bär ett påstående ska gå att räkna om.

**INGEN KUNDTEXT SKRIVS UT.** Bara antal. Filerna skriptet läser bär kundtext, och
utdatan är avsedd att klistras in i en rapport (§6).

Skriptet skriver ingenting. Det läser tre gitignorerade filer under `data/`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PAR = ROT / "data" / "par.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"

# Samma tre etiketter som `src/vy.py::A_TRAKTORETIKETTER`.
A_TRAKTOR = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)


def las_jsonl(sokvag: Path) -> list[dict]:
    if not sokvag.exists():
        return []
    poster = []
    for rad in sokvag.read_text(encoding="utf-8").splitlines():
        if rad:
            poster.append(json.loads(rad))
    return poster


def med_urval(tradar: list[dict]) -> int:
    """Antalet obesvarade trådar som bär ett extraherat `urval`-fält.

    **SVARET ÄR NOLL, och det är strukturellt.** `data/tradar_obesvarade.jsonl`
    bär RÅA Gmail-trådar: `id`, `historyId` och `messages` med `payload`, där
    brödtexten ligger base64-kodad i MIME-delarna. Något extraherat textfält
    finns inte, alltså finns det ingen nyckel att koppla på utan att köra
    extraktionen på nytt.

    Det är skälet till att `src/vy.py::las_fall` lämnar hash och tidsstämpel
    tomma för de obesvarade. Kopplingen är inte GLES, den är obefintlig i den
    här filens form.
    """
    return sum(1 for trad in tradar if trad.get("urval"))


def main() -> int:
    etiketterade = las_jsonl(OMETIKETTERADE)
    par = las_jsonl(PAR)
    obesvarade = las_jsonl(OBESVARADE)

    if not etiketterade:
        print(f"saknas eller tom: {OMETIKETTERADE}")
        return 1

    partexter = {post["inkommande_text"] for post in par}
    tradar_med_urval = med_urval(obesvarade)

    med_svar = [p for p in etiketterade if p.get("kalla") == "med svar"]
    kopplade = [p for p in med_svar if p["text"] in partexter]

    print("=== KOPPLING ometiketterade -> par")
    print(f"poster i par.jsonl:                   {len(par)}")
    print(f"unika inkommande_text i par.jsonl:    {len(partexter)}")
    print(f"rader med svar i ometiketterade:      {len(med_svar)}")
    print(f"varav kopplade till par.jsonl:        {len(kopplade)}")

    a_utan = [
        p
        for p in etiketterade
        if p.get("kalla") == "utan svar" and p["etikett"] in A_TRAKTOR
    ]

    print("")
    print("=== KOPPLING a-traktor utan svar -> tradar_obesvarade")
    print(f"trådar i tradar_obesvarade.jsonl:     {len(obesvarade)}")
    print(f"varav med ett extraherat urval-fält:  {tradar_med_urval}")
    print(f"a-traktorrader utan svar:             {len(a_utan)}")
    print("")
    print("Bär ingen tråd ett extraherat textfält finns ingen nyckel att koppla")
    print("på, och kopplingen är obefintlig snarare än gles. Det är skälet till")
    print("att `las_fall` lämnar hash och tidsstämpel TOMMA för de obesvarade i")
    print("stället för att hitta på dem (§7.2).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
