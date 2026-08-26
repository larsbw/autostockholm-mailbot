"""Vägrar en commit som för in persondata i ett spårat dokument.

SKÄLET, och det är mätt och inte befarat: skiva 5 och skiva 6 hade båda
persondata nära en commit, och båda gångerna fångades det av en granskning.
I skiva 6 nådde det ända in i en commit och togs bort först efteråt. **En
granskare tittar ibland. En spärr biter varje gång.**

Kontrollen läser det som ligger i INDEXET, alltså det som faktiskt är på väg in
i committen, och inte arbetsträdet. Att läsa arbetsträdet hade missat en
`git add` följd av en redigering.

    scripts/persondatakontroll.py            # kontrollerar indexet
    scripts/persondatakontroll.py --alla     # kontrollerar allt spårat

Installeras som git-hook med:

    scripts/installera-hook.sh
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent

# Kataloger vars innehåll kontrolleras. Kod kontrolleras inte: den innehåller
# mönster och testfixturer som ser ut som persondata och som är påhittade.
BEVAKADE = ("docs/",)

MONSTER: list[tuple[str, re.Pattern]] = [
    ("mailadress", re.compile(r"[A-Za-z0-9._%+=-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    # Gränsen är en negativ lookbehind och INTE `\b`: `\b` före ett plustecken
    # matchar aldrig, eftersom `+` inte är ett ordtecken. Mönstret missade
    # därför hela det internationella formatet.
    ("telefonnummer", re.compile(r"(?<![\d\w])(?:\+46|0)[\s-]?7[\d\s-]{8,}\d")),
    ("registreringsnummer", re.compile(r"\b[A-ZÅÄÖ]{3}[\s-]?\d{2}[A-ZÅÄÖ0-9]\b")),
    # Postnummer kräver en ORT efter sig. Ett bart femsiffrigt tal är oftast
    # ett mätvärde: kvotåtgången i `docs/mining-log.md` larmade som postnummer
    # vid första körningen. Att i stället lägga just de talen i TILLATNA hade
    # varit sämre, eftersom det hade släppt igenom ett framtida RIKTIGT
    # postnummer som råkar ha samma siffror.
    ("postnummer", re.compile(
        r"\b\d{3}\s?\d{2}\b(?=\s+[A-ZÅÄÖ][A-ZÅÄÖa-zåäö]+)")),
    ("gatuadress", re.compile(
        r"\b[A-ZÅÄÖ][a-zåäö]{2,}(?:gatan|vägen|gränd|torget|backen|stigen)"
        r"\s+\d+\b")),
    ("personnummer", re.compile(r"\b(?:19|20)?\d{6}[\s-]?\d{4}\b")),
]

# Undantag. Varje post är en RAD som får innehålla en träff, med skälet
# utskrivet. Undantaget gäller exakt strängen, inte mönstret.
TILLATNA = {
    # Brevlådan själv står i CLAUDE.md §0 och är företagets, inte en persons.
    "info@autostockholm.se",
    # Exempeladresser i regler och mallar.
    "noreply@example.com",
    "kund@exempel.se",
}


def _kor(argument: list[str]) -> str:
    return subprocess.run(
        argument, cwd=ROT, capture_output=True, text=True, check=True
    ).stdout


def stagade_filer() -> list[str]:
    ut = _kor(["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR"])
    return [rad for rad in ut.splitlines() if rad]


def sparade_filer() -> list[str]:
    return [rad for rad in _kor(["git", "ls-files"]).splitlines() if rad]


def _innehall_ur_indexet(sokvag: str) -> str:
    return _kor(["git", "show", f":{sokvag}"])


def _innehall_ur_tradet(sokvag: str) -> str:
    return (ROT / sokvag).read_text(encoding="utf-8", errors="replace")


def bevakad(sokvag: str) -> bool:
    return any(sokvag.startswith(katalog) for katalog in BEVAKADE)


def _tillaten(traff: str) -> bool:
    return traff.strip() in TILLATNA


def granska(text: str, sokvag: str) -> list[tuple[int, str, str]]:
    """Träffar som (radnummer, sort, träffen).

    Träffen returneras för att kunna maskeras i utskriften. Den skrivs ALDRIG
    ut i klartext: ett skript som larmar om persondata får inte självt skriva
    ut den i en terminallogg.
    """
    fynd = []
    for nummer, rad in enumerate(text.splitlines(), start=1):
        for sort, monster in MONSTER:
            for traff in monster.finditer(rad):
                if not _tillaten(traff.group(0)):
                    fynd.append((nummer, sort, traff.group(0)))
    return fynd


def _maska(traff: str) -> str:
    if len(traff) <= 4:
        return "*" * len(traff)
    return f"{traff[:2]}{'*' * (len(traff) - 4)}{traff[-2:]}"


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--alla", action="store_true",
                      help="kontrollera allt spårat i stället för indexet")
    arg = tolk.parse_args(argv)

    if arg.alla:
        filer = [f for f in sparade_filer() if bevakad(f)]
        las = _innehall_ur_tradet
        vad = "spårade filer"
    else:
        filer = [f for f in stagade_filer() if bevakad(f)]
        las = _innehall_ur_indexet
        vad = "stagade filer"

    if not filer:
        print(f"persondatakontroll: inga {vad} under {', '.join(BEVAKADE)}")
        return 0

    totalt = 0
    for sokvag in filer:
        for nummer, sort, traff in granska(las(sokvag), sokvag):
            if totalt == 0:
                print("PERSONDATAKONTROLL: STOPP", file=sys.stderr)
                print("", file=sys.stderr)
            print(f"  {sokvag}:{nummer}  {sort}: {_maska(traff)}",
                  file=sys.stderr)
            totalt += 1

    if totalt:
        print("", file=sys.stderr)
        print("CLAUDE.md §6: persondata förekommer aldrig i dokument som", file=sys.stderr)
        print("pushas. Träffarna är maskerade ovan med avsikt.", file=sys.stderr)
        print("", file=sys.stderr)
        print("Är en träff ett falskt larm, lägg strängen i TILLATNA i", file=sys.stderr)
        print("scripts/persondatakontroll.py MED SKÄLET UTSKRIVET.", file=sys.stderr)
        print("Skriv aldrig om texten tills spärren släpper igenom den:", file=sys.stderr)
        print("det är §9.1:s förbjudna åtgärd, i dokumentform.", file=sys.stderr)
        return 1

    print(f"persondatakontroll: {len(filer)} {vad} granskade, inga fynd")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
