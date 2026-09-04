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


def snippets(tradar: list[dict]) -> list[str]:
    """Varje icke-tomt `snippet` i de obesvarade trådarna.

    **`snippet` ÄR ETT EXTRAHERAT TEXTFÄLT, och det ledet är rättat.** Skiva 27
    påstod först att `data/tradar_obesvarade.jsonl` saknar ett sådant fält och
    att brödtexten bara finns base64-kodad i `payload`. Det är falskt: Gmail
    lägger ett eget klartextutdrag i `snippet`.

    **PÅ MEDDELANDET, INTE PÅ TRÅDEN**, vilket är varför den här funktionen
    loopar över `messages`. De 1604 trådarna bär 1755 meddelanden, vart och ett
    med fältet, och fem har det tomt. Noll trådar bär fältet på sin toppnivå.

    *Här stod att fältet finns "på var och en av de 1604 trådarna". Talet var
    rätt för meddelandena och fel för trådarna. Att 1750 icke-tomma `snippet`
    är fler än 1604 trådar är i sig ett bevis för det. Fällt av
    §7-granskningen av skiva 28.*

    Fältet är däremot TRUNKERAT, alltså är det ingen nyckel för en exakt
    jämförelse. Skillnaden mellan "det finns inget fält" och "fältet är
    trunkerat" är hela skälet till att mätningen nedan görs i stället för
    påstås.
    """
    texter = []
    for trad in tradar:
        for meddelande in trad.get("messages") or []:
            utdrag = (meddelande.get("snippet") or "").strip()
            if utdrag:
                texter.append(utdrag)
    return texter


def _normalisera(text: str) -> str:
    """Slår ihop allt blanksteg till enkla mellanslag.

    `snippet` normaliserar radbrytningar till mellanslag medan den etiketterade
    texten behåller sina. Utan det här ledet mäter jämförelsen radbrytningar och
    inte innehåll.
    """
    return " ".join(text.split())


def main() -> int:
    etiketterade = las_jsonl(OMETIKETTERADE)
    par = las_jsonl(PAR)
    obesvarade = las_jsonl(OBESVARADE)

    if not etiketterade:
        print(f"saknas eller tom: {OMETIKETTERADE}")
        return 1

    partexter = {post["inkommande_text"] for post in par}
    utdrag = [_normalisera(s) for s in snippets(obesvarade)]

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

    # KOPPLINGEN GÖRS, den påstås inte. Två former, båda mot `snippet`:
    # exakt likhet, och `snippet` som inledning på den etiketterade texten.
    # Den andra formen finns därför att `snippet` är TRUNKERAT och en exakt
    # jämförelse därför bara kan lyckas för de allra kortaste mailen.
    exakt = 0
    som_inledning = 0
    for post in a_utan:
        text = _normalisera(post["text"])
        if text in utdrag:
            exakt += 1
        elif any(text.startswith(s) for s in utdrag if s):
            som_inledning += 1

    print("")
    print("=== KOPPLING a-traktor utan svar -> tradar_obesvarade")
    print(f"trådar i tradar_obesvarade.jsonl:     {len(obesvarade)}")
    print(f"icke-tomma snippet i dem:             {len(utdrag)}")
    print(f"a-traktorrader utan svar:             {len(a_utan)}")
    print(f"varav kopplade på exakt snippet:      {exakt}")
    print(f"varav kopplade på snippet som inledning: {som_inledning}")
    print("")
    print("`snippet` är Gmails klartextutdrag och sitter på MEDDELANDET, men")
    print("det är TRUNKERAT. Talen ovan säger hur mycket det räcker till. Det är")
    print("skälet till att `las_fall` lämnar hash och tidsstämpel TOMMA för de")
    print("obesvarade i stället för att hitta på dem (§7.2).")

    return 0


if __name__ == "__main__":
    sys.exit(main())
