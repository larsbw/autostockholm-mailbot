#!/usr/bin/env python3
"""Letar osynliga tecken i repots filer eller i en diffs adderade rader.

VARFÖR SKRIPTET FINNS. Skiva 26:s granskare kunde inte belägga frånvaron av
osynliga tecken: repot saknade ett committat skript för kontrollen, och §9
tillåter inte granskaren att skriva ett på en bash-rad. Kontrollen kördes därför
av den som skrev texten, alltså av fel part. Ett committat skript flyttar den
till granskaren.

VAD SOM LETAS EFTER, tre grupper:

  Cf   formateringstecken. Bär ingen bredd och syns inte. Hit hör mjukt
       bindestreck, nollbreddstecken och riktningsmarkörer.
  Cc   styrtecken. TAB och radbrytning är undantagna, se `TILLATNA`.
  De femton NAMNGIVNA kodpunkterna i `NAMNGIVNA`. De ligger utanför Cf och Cc
       men är lika osynliga i en diff, och hårt blanksteg är den av dem som
       faktiskt har uppstått i det här repot: skiva 23 skrev in ett U+00A0 i en
       docstring genom att en escape blev ett literalt tecken.

**RADENS INNEHÅLL SKRIVS ALDRIG UT.** Bara fil, rad, kolumn, kodpunkt och namn.
Skälet är §6: skriptet ska kunna riktas mot `data/`, där kundtext bor, utan att
en rapport eller ett terminalutdrag börjar bära persondata. Ett verktyg som är
osäkert att köra mot halva repot blir inte kört.

ANVÄNDNING, literala rader enligt §9:

    .venv/bin/python scripts/osynliga-tecken.py --diff
    .venv/bin/python scripts/osynliga-tecken.py --stagat
    .venv/bin/python scripts/osynliga-tecken.py src/vy.py tests/test_vy.py

Avslutskod 0 betyder inga fynd, 1 betyder minst ett fynd, 2 betyder att
anropet inte gick att tolka.
"""

from __future__ import annotations

import subprocess
import sys
import unicodedata
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent

# TECKEN SOM FÅR VARA STYRTECKEN. TAB och radbrytning bär mening i källkod och i
# markdown. Vagnretur gör det INTE i det här repot och rapporteras som fynd:
# den är lika osynlig som resten och är en äkta avvikelse när den dyker upp.
TILLATNA = frozenset({"\t", "\n"})

# DE FEMTON NAMNGIVNA KODPUNKTERNA. Listan är den som kördes i skiva 26:s
# egenkontroll, återfunnen ordagrant ur den körningen och inte ur ett minne av
# den. Antalet skrivs inte ut i löptext här: `--lista` skriver ut den, och
# `test_femton_namngivna_kodpunkter` mäter längden.
NAMNGIVNA = frozenset({
    0x00A0,  # NO-BREAK SPACE
    0x00AD,  # SOFT HYPHEN
    0x200B,  # ZERO WIDTH SPACE
    0x200C,  # ZERO WIDTH NON-JOINER
    0x200D,  # ZERO WIDTH JOINER
    0x200E,  # LEFT-TO-RIGHT MARK
    0x200F,  # RIGHT-TO-LEFT MARK
    0x2007,  # FIGURE SPACE
    0x2009,  # THIN SPACE
    0x2028,  # LINE SEPARATOR
    0x2029,  # PARAGRAPH SEPARATOR
    0x202F,  # NARROW NO-BREAK SPACE
    0x2060,  # WORD JOINER
    0x3000,  # IDEOGRAPHIC SPACE
    0xFEFF,  # ZERO WIDTH NO-BREAK SPACE
})


def ar_osynligt(tecken: str) -> bool:
    """Sant när tecknet är ett av dem kontrollen letar efter.

    **PARENTESERNA ÄR INTE KOSMETISKA.** Skiva 26:s engångskörning skrev
    `a in b or kategori in c and t != tab`, vilket Python läser som
    `a or (b and c)`. Undantaget för TAB gällde alltså bara den ena grenen.
    Här är undantaget utbrutet först och gäller båda.
    """
    if tecken in TILLATNA:
        return False
    return ord(tecken) in NAMNGIVNA or unicodedata.category(tecken) in ("Cf", "Cc")


def namnge(tecken: str) -> str:
    """Unicodes namn på tecknet, eller dess kategori när namn saknas.

    Styrtecken under U+0020 har inget Unicode-namn alls, och `unicodedata.name`
    kastar `ValueError` för dem. Ett fynd utan namn är fortfarande ett fynd.
    """
    try:
        return unicodedata.name(tecken)
    except ValueError:
        return f"utan namn, kategori {unicodedata.category(tecken)}"


def granska(text: str, fil: str) -> list[tuple[str, int, int, str, str]]:
    """Fynden i en text, som `(fil, rad, kolumn, kodpunkt, namn)`.

    Rad och kolumn räknas från 1. Radens innehåll ingår ALDRIG i returvärdet:
    det är det som gör utdatan säker att klistra in i en rapport.
    """
    fynd = []
    for radnummer, rad in enumerate(text.split("\n"), start=1):
        for kolumn, tecken in enumerate(rad, start=1):
            if ar_osynligt(tecken):
                fynd.append(
                    (fil, radnummer, kolumn, f"U+{ord(tecken):04X}", namnge(tecken))
                )
    return fynd


def adderade_rader(stagat: bool, rot: Path | None = None) -> list[tuple[str, str]]:
    """Diffens adderade rader som `(fil, rad)`.

    Radnumret som `granska` sedan sätter är numret INOM den samlade texten per
    fil, inte filens eget radnummer. Det är avsiktligt: en diff har inga stabila
    radnummer, och fyndet ska hittas med kodpunkten och inte med raden.

    **`--diff` TAR MED OSPÅRADE FILER, och det ledet är hela skillnaden mellan
    ett svar och ett falskt GRÖN.** `git diff HEAD` ser inte en fil som ännu
    inte är `git add`:ad. Första körningen av det här skriptet skrev noll fynd
    för skiva 27 medan skivans fyra nya filer var ospårade, alltså noll fynd
    över noll filer. En ospårad fil är i sin helhet adderad och läses därför i
    sin helhet.

    `--stagat` tar INTE med dem. Det som inte är stagat ingår inte i committen,
    och frågan `--stagat` besvarar är vad committen bär.
    """
    rot = ROT if rot is None else rot
    kommando = ["git", "diff", "--unified=0"]
    kommando.append("--cached" if stagat else "HEAD")

    korning = subprocess.run(
        kommando, capture_output=True, text=True, cwd=rot, check=True
    )

    rader: list[tuple[str, str]] = []
    fil = "okänd fil"
    for rad in korning.stdout.split("\n"):
        if rad.startswith("+++ b/"):
            fil = rad[len("+++ b/"):]
        elif rad.startswith("+") and not rad.startswith("+++"):
            rader.append((fil, rad[1:]))

    if not stagat:
        rader.extend(_osparade_rader(rot))

    return rader


def _osparade_rader(rot: Path) -> list[tuple[str, str]]:
    """Varje rad i varje ospårad fil som inte är gitignorerad.

    `--exclude-standard` gör att `data/` och `logg/` hålls utanför, alltså att
    kontrollen av en diff aldrig råkar läsa kundtext. Vill man granska dem pekar
    man ut dem med sökväg, och då skriver skriptet ändå aldrig ut raderna.
    """
    korning = subprocess.run(
        ["git", "ls-files", "--others", "--exclude-standard"],
        capture_output=True,
        text=True,
        cwd=rot,
        check=True,
    )

    rader: list[tuple[str, str]] = []
    for namn in korning.stdout.split("\n"):
        if not namn:
            continue
        try:
            text = (rot / namn).read_text(encoding="utf-8", newline="")
        except (UnicodeDecodeError, OSError):
            # En binärfil bär inga osynliga TEXTtecken. Att hoppa över den är
            # inte att tiga om den: `main` räknar bara filer den faktiskt läst.
            continue
        rader.extend((namn, rad) for rad in text.split("\n"))
    return rader


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2

    if argv[0] == "--lista":
        for kodpunkt in sorted(NAMNGIVNA):
            print(f"U+{kodpunkt:04X}  {namnge(chr(kodpunkt))}")
        print(f"namngivna kodpunkter: {len(NAMNGIVNA)}")
        print("plus varje tecken i kategorierna Cf och Cc utom TAB och radbrytning")
        return 0

    fynd: list[tuple[str, int, int, str, str]] = []

    if argv[0] in ("--diff", "--stagat"):
        per_fil: dict[str, list[str]] = {}
        for fil, rad in adderade_rader(argv[0] == "--stagat"):
            per_fil.setdefault(fil, []).append(rad)
        for fil, rader in sorted(per_fil.items()):
            fynd.extend(granska("\n".join(rader), fil))
        vad = f"adderade rader i {argv[0]}"
        antal_filer = len(per_fil)
    else:
        for sokvag in argv:
            fil = Path(sokvag)
            if not fil.exists():
                print(f"finns inte: {sokvag}")
                return 2
            # `newline=""` stänger av översättningen av radslut, så en vagnretur
            # syns i stället för att tyst bli en radbrytning.
            fynd.extend(
                granska(fil.read_text(encoding="utf-8", newline=""), sokvag)
            )
        vad = "angivna filer"
        antal_filer = len(argv)

    for fil, rad, kolumn, kodpunkt, namn in fynd:
        print(f"{fil}:{rad}:{kolumn}  {kodpunkt}  {namn}")

    # ANTALET GRANSKADE FILER SKRIVS ALLTID UT, bredvid antalet fynd. Noll fynd
    # över noll filer och noll fynd över fyra filer är helt olika besked, och den
    # första formen är ett falskt GRÖN som inget i utdatan annars avslöjar.
    print(f"osynliga tecken i {vad}: {len(fynd)} fynd över {antal_filer} filer")
    return 1 if fynd else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
