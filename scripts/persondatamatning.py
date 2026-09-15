#!/usr/bin/env python3
"""VAD BÄR EN FIL FÖR PERSONUPPGIFTER? Mätningen bakom #119:s tabell.

    .venv/bin/python scripts/persondatamatning.py

**SKRIPTET FINNS FÖR ATT TABELLEN SKA GÅ ATT RÄKNA OM.** §7-granskningen av
skiva 53 kunde inte reproducera kolumnerna e-post, mobil och fastnät: mönstren
låg i en ogitad fil, och repots enda committade uppsättning,
`scripts/persondatakontroll.py`, bär ett enda telefonmönster och inget för
fastnät. Ett tal som bara författaren kan räkna om är i praktiken oläst (§7.2).

**MÖNSTREN HÄR ÄR INTE `persondatakontroll.py`:S, och de två har olika uppdrag.**
Hooken ska larma på det som är på väg in i git och får hellre fälla för mycket.
Den här mätningen ska BESKRIVA en fil, alltså snävt och uppdelat per form.

§6: skriptet skriver ANTAL och MASKERADE former. Ingen läsbar kundtext lämnar
det. En maskerad form är `999-999 99 99`, alltså formen utan innehållet.

**TALEN ÄR MÖNSTERTRÄFFAR OCH INTE BEKRÄFTADE UPPGIFTER.** `personnr` räknar
strängar på formen `ÅÅMMDD-NNNN`; ett ordernummer med samma form räknas med.
Siffran är en ÖVRE gräns för hur mycket av den sorten filen bär, och en
undre gräns för hur mycket som INTE syns: en adress eller ett namn fångas inte
av något mönster alls.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent

EPOST = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")

# SVENSKA MOBILNUMMER. `(?<![\d.\-T:])` och `(?![\d.\-T:])` hindrar att en
# ISO-tidsstämpel räknas: ett första mätvarv utan dem gav `logg/beslut.jsonl`
# 168 telefonnummer, samtliga falska.
MOBIL = re.compile(
    r"(?<![\d.\-T:])(?:\+46[ -]?|0)7[0236][ -]?\d{3}[ -]?\d{2}[ -]?\d{2}"
    r"(?![\d.\-T:])"
)

# FASTNÄT. Kräver en avskiljare efter riktnumret, annars fångas varje
# sjusiffrig run.
FASTNAT = re.compile(
    r"(?<![\d.\-T:])0[1-9]\d{0,2}[ -]\d{2,3}[ -]?\d{2}[ -]?\d{2}(?![\d.\-T:])"
)

# REGISTRERINGSNUMMER. VERSALER krävs, så att en hexadecimal hash inte räknas:
# `avsandare_hash` är 16 tecken och skulle annars ge träffar.
REGNR = re.compile(r"(?<![A-Za-z0-9])[A-ZÅÄÖ]{3} ?\d{2}[\dA-Z](?![A-Za-z0-9])")

# PERSONNUMMER. Kräver skiljetecken, alltså inte varje tiosiffrig run. Ett
# första varv utan det kravet gav `data/par.jsonl` 69 träffar, nästan alla
# falska.
PERSONNR = re.compile(r"(?<!\d)(?:19|20)?\d{6}[-+]\d{4}(?!\d)")

MONSTER = {
    "e-post": EPOST,
    "mobil": MOBIL,
    "fastnät": FASTNAT,
    "regnr": REGNR,
    "personnr": PERSONNR,
}

# FILERNA SOM FLYTTAR TILL RAILWAY, #119. Ordningen är tabellens.
FLYTTAR = ["par.jsonl", "ometiketterade.jsonl", "granskningsfall.jsonl",
           "taxonomi.json"]

# FILERNA SOM STANNAR PÅ LARS MASKIN. Lars beslut i skiva 53.
STANNAR = ["tradar.jsonl", "tradar_obesvarade.jsonl", "kategorisvar.jsonl"]

LOGGAR = ["beslut.jsonl", "omdomen.jsonl", "uppslag.jsonl", "korningar.jsonl"]


def maskera(traff: str) -> str:
    """Formen, aldrig innehållet. Varje siffra blir 9 och varje bokstav X."""
    return re.sub(r"[A-Za-zÅÄÖåäö]", "X", re.sub(r"\d", "9", traff))


def poster_ur(fil: Path) -> list:
    """Filens poster. En JSON-lista räknas som sina element."""
    text = fil.read_text(encoding="utf-8")
    if fil.suffix == ".json":
        data = json.loads(text)
        return data if isinstance(data, list) else [data]
    return [json.loads(r) for r in text.splitlines() if r.strip()]


def matt(fil: Path) -> dict:
    """Antal per mönster, plus en maskerad form per fält och mönster."""
    poster = poster_ur(fil)
    summa = Counter()
    per_falt = defaultdict(int)
    former = {}

    for post in poster:
        if not isinstance(post, dict):
            post = {"_": post}
        for falt, varde in post.items():
            if not isinstance(varde, str):
                varde = json.dumps(varde, ensure_ascii=False)
            for namn, monster in MONSTER.items():
                fynd = monster.findall(varde)
                if fynd:
                    summa[namn] += len(fynd)
                    per_falt[(falt, namn)] += len(fynd)
                    former.setdefault((falt, namn), maskera(fynd[0]))

    return {"byte": fil.stat().st_size, "poster": len(poster),
            "summa": summa, "per_falt": per_falt, "former": former}


def skriv_storlekar(rubrik: str, filer: list[Path]) -> int:
    """BARA BYTE OCH POSTER, inga mönster.

    **FÖR FILER SOM INTE FLYTTAR, och det är en avsiktlig avgränsning.**
    Mönstermatchning över `data/tradar_obesvarade.jsonl`, 86 MB med
    base64-kodade bilagor, tar tiotals minuter och säger ingenting som påverkar
    ett beslut: filerna stannar på Lars maskin. En tabell som visade
    mönsterkolumner här hade dessutom frestat till att skriva ut tal ingen
    faktiskt räknat.
    """
    print(f"\n### {rubrik}\n")
    print(f"| {'Fil':<30} | {'Byte':>11} |")
    print(f"| {'-' * 30} | {'-' * 11} |")
    total = 0
    for fil in filer:
        if not fil.exists():
            print(f"| {fil.name:<30} | {'SAKNAS':>11} |")
            continue
        total += fil.stat().st_size
        print(f"| {fil.name:<30} | {fil.stat().st_size:>11,} |".replace(",", " "))
    print(f"| {'SUMMA':<30} | {total:>11,} |".replace(",", " "))
    return total


def skriv_tabell(rubrik: str, filer: list[Path]) -> int:
    print(f"\n### {rubrik}\n")
    kolumner = list(MONSTER)
    print(f"| {'Fil':<30} | {'Byte':>11} | {'Poster':>6} | "
          + " | ".join(f"{k:>8}" for k in kolumner) + " |")
    print(f"| {'-' * 30} | {'-' * 11} | {'-' * 6} | "
          + " | ".join("-" * 8 for _ in kolumner) + " |")

    total = 0
    for fil in filer:
        if not fil.exists():
            print(f"| {fil.name:<30} | {'SAKNAS':>11} | {'':>6} | "
                  + " | ".join(f"{'':>8}" for _ in kolumner) + " |")
            continue
        m = matt(fil)
        total += m["byte"]
        print(f"| {fil.name:<30} | {m['byte']:>11,} | {m['poster']:>6} | ".replace(",", " ")
              + " | ".join(f"{m['summa'][k]:>8}" for k in kolumner) + " |")

    print(f"| {'SUMMA':<30} | {total:>11,} | {'':>6} | ".replace(",", " ")
          + " | ".join(f"{'':>8}" for _ in kolumner) + " |")
    return total


# HUVUDEN SOM BÄR EN IDENTITET. `Bcc` står här därför att den bär uppgifter
# mottagarna själva inte ser.
IDENTITETSHUVUDEN = ("From", "To", "CC", "Bcc", "Reply-To", "Return-Path",
                     "Delivered-To", "Subject")


def skriv_skorden(fil: Path) -> None:
    """Vad `data/inkorg-dagens.jsonl` faktiskt bär, mätt på struktur.

    Filen är Gmails råa svar. Den mäts på HUVUDEN och kroppsdelar och inte på
    mönster: base64 producerar slumpmässiga träffar som inte betyder något.
    """
    tradar = poster_ur(fil)
    meddelanden = [m for t in tradar for m in (t.get("messages") or [])]

    raknare = Counter()
    kroppar = 0

    def ga_ned(del_):
        nonlocal kroppar
        if (del_.get("body") or {}).get("data"):
            kroppar += 1
        for under in (del_.get("parts") or []):
            ga_ned(under)

    for m in meddelanden:
        nyttolast = m.get("payload") or {}
        for huvud in (nyttolast.get("headers") or []):
            if huvud.get("name") in IDENTITETSHUVUDEN:
                raknare[huvud["name"]] += 1
        if m.get("snippet"):
            raknare["snippet"] += 1
        ga_ned(nyttolast)

    print("\n### SKAPAS AV SERVERN SJÄLV\n")
    print(f"| {fil.name:<30} | {fil.stat().st_size:>11,} byte |".replace(",", " "))
    print(f"| {'trådar':<30} | {len(tradar):>11} |")
    print(f"| {'meddelanden':<30} | {len(meddelanden):>11} |")
    for namn in IDENTITETSHUVUDEN + ("snippet",):
        print(f"| {namn:<30} | {raknare[namn]:>11} |")
    print(f"| {'kroppsdelar med base64':<30} | {kroppar:>11} |")


def main(argv: list[str] | None = None) -> int:
    from src import sokvagar

    data = sokvagar.DATA
    logg = sokvagar.LOGG

    print("PERSONDATAMÄTNING. Antal och maskerade former, aldrig innehåll (§6).")
    print(f"data: {data}")
    print(f"logg: {logg}")

    flyttar = skriv_tabell("FLYTTAR TILL RAILWAY", [data / n for n in FLYTTAR])
    stannar = skriv_storlekar("STANNAR PÅ LARS MASKIN",
                              [data / n for n in STANNAR])
    skriv_tabell("LOGGARNA", [logg / n for n in LOGGAR])

    # SKÖRDEN MÄTS PÅ STRUKTUR OCH INTE PÅ MÖNSTER. Filen bär Gmails råa
    # nyttolast med base64-kodade kroppar, alltså säger ett mönsterantal över
    # den mest hur många träffar base64 råkar producera. Huvudena är det som
    # betyder något.
    skord = data / "inkorg-dagens.jsonl"
    if skord.exists():
        skriv_skorden(skord)

    if flyttar:
        print(f"\nkvot stannar/flyttar: {stannar / flyttar:.2f}")
    return 0


if __name__ == "__main__":
    sys.path.insert(0, str(ROT))
    raise SystemExit(main())
