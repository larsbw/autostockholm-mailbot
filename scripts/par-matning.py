#!/usr/bin/env python3
"""Mäter hur många a-traktorpar som går att använda som få-exempel i prompten.

    .venv/bin/python scripts/par-matning.py

VARFÖR SKRIPTET FINNS. Skiva 31 DEL B säger: mät hur många par som FAKTISKT går
att använda, och säg det i stället för att tvinga in dem. §9 kräver att en
räkning som bär ett styrdokuments påstående ligger i ett committat skript, och
§7.2 att talet är avläst ur en körning.

**INGEN KUNDTEXT SKRIVS UT.** Bara antal, längder och kvartiler. Filerna bär
kundtext, och utdatan är avsedd att klistras in i en rapport (§6).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generera  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PAR = ROT / "data" / "par.jsonl"

# Samma tre etiketter som `src/vy.py::A_TRAKTORETIKETTER`.
A_TRAKTOR = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# TAK FÖR ETT FÅ-EXEMPEL. Ett par som är längre än så äter promptens utrymme och
# lär modellen att svara långt. Talet är ett VAL och inte en mätning; det står
# här för att gå att ändra på ett ställe.
MAX_TECKEN_SVAR = 900


def las_jsonl(sokvag: Path) -> list[dict]:
    if not sokvag.exists():
        return []
    return [json.loads(r) for r in sokvag.read_text(encoding="utf-8").splitlines() if r]


def kvartiler(tal: list[int]) -> tuple[int, int, int]:
    """Median och ytterkvartiler, utan numpy och utan interpolation."""
    if not tal:
        return (0, 0, 0)
    s = sorted(tal)
    return (s[len(s) // 4], s[len(s) // 2], s[(3 * len(s)) // 4])


def main() -> int:
    etiketterade = las_jsonl(OMETIKETTERADE)
    par = las_jsonl(PAR)

    if not etiketterade or not par:
        print("saknas: data/ometiketterade.jsonl eller data/par.jsonl")
        return 1

    # Kundtexten är nyckeln, samma koppling som `src/vy.py::_par_karta`.
    partext = {p["inkommande_text"]: p for p in par}

    a_med_svar = [
        p
        for p in etiketterade
        if p["etikett"] in A_TRAKTOR and p.get("kalla") == "med svar"
    ]
    kopplade = [partext[p["text"]] for p in a_med_svar if p["text"] in partext]

    print("=== A-TRAKTORPAR SOM UNDERLAG FÖR FÅ-EXEMPEL")
    print(f"a-traktorrader med svar:              {len(a_med_svar)}")
    print(f"varav kopplade till par.jsonl:        {len(kopplade)}")

    if not kopplade:
        print("inga par att mäta")
        return 0

    in_langd = [len(p["inkommande_text"]) for p in kopplade]
    ut_langd = [len(p["utgaende_text"]) for p in kopplade]

    print("")
    print("Längder i tecken, som q1 / median / q3:")
    print("  inkommande:  %d / %d / %d" % kvartiler(in_langd))
    print("  utgående:    %d / %d / %d" % kvartiler(ut_langd))
    print(f"  längsta utgående: {max(ut_langd)}")
    print(f"  kortaste utgående: {min(ut_langd)}")

    # ANVÄNDBARA SOM EXEMPEL. Ett par duger när båda leden har innehåll och
    # svaret ryms under taket. Ett tomt led ger modellen ingenting att härma.
    anvandbara = [
        p
        for p in kopplade
        if p["inkommande_text"].strip()
        and p["utgaende_text"].strip()
        and len(p["utgaende_text"]) <= MAX_TECKEN_SVAR
    ]

    # SLUTTALET KOMMER UR MODULENS EGEN PREDIKAT, inte ur en kopia här.
    #
    # Skriptet räknade först med sina egna kriterier, och de var lösare än
    # `src/generera.py`. Då mäter skriptet en annan population än koden använder,
    # vilket är precis det fel §7-granskningen av skiva 31 fällde på ett annat
    # ställe. Talet nedan är därför per definition det koden skulle välja bland.
    duger_i_koden = [p for p in kopplade if generera._duger_som_exempel(p)]

    print("")
    print(f"tak för ett få-exempels svar:         {MAX_TECKEN_SVAR} tecken")
    print(f"par som ryms under taket:             {len(anvandbara)}")
    print(f"par som faller på längden:            {len(kopplade) - len(anvandbara)}")

    # §11-KONTROLL PÅ EXEMPLEN SJÄLVA. Ett få-exempel som bryter mot regeln lär
    # modellen att bryta mot den. Det här är skälet att mäta och inte anta.
    tankstreck = [p for p in anvandbara if "—" in p["utgaende_text"]]
    friverkstad = [
        p for p in anvandbara if "friverkstad" in p["utgaende_text"].lower()
    ]
    jag = [
        p
        for p in anvandbara
        if any(
            f" {ord} " in f" {p['utgaende_text'].lower()} "
            for ord in ("jag", "mig", "min", "mitt")
        )
    ]

    print("")
    print("=== §11 PÅ EXEMPLEN SJÄLVA")
    print(f"bär tankstreck:                       {len(tankstreck)}")
    print(f"bär ordet friverkstad:                {len(friverkstad)}")
    print(f"bär första person singular:           {len(jag)}")

    print("")
    print("Räkningarna ovan är GROVA och underskattar: de kräver blanksteg på")
    print("båda sidor om pronomenet och missar 'jag.' med skiljetecken.")
    print("")
    print(f"PAR SOM `generera._duger_som_exempel` SLÄPPER IGENOM: {len(duger_i_koden)}")
    print("Det är talet som gäller, eftersom det är kodens eget kriterium.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
