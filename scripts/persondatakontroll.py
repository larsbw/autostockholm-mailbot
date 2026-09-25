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

# Sökvägar vars innehåll kontrolleras.
#
# `mallar/` är den TYNGSTA posten och saknades i första versionen: §11 säger att
# mallarna byggs ur `data/par.jsonl`, alltså ur RÅ kundtext. Det är projektets
# största persondatarisk, och den var oskyddad.
#
# `config/` bär material härlett ur kundpost. `CLAUDE.md` ligger i roten, är
# spårad, och innehåller redan en adress.
#
# `scripts/` tillkom i skiva 16. Skiva 15 lade två mätskript där som läser
# kundpost och skriver antal ur den, och de var därmed oskyddade: en utskrift
# som råkar bära ett värde i stället för en räkning hade passerat. En spärr som
# inte täcker en katalog är en lucka oavsett vad som råkar ligga där.
#
# `src/` och `tests/` kontrolleras fortfarande INTE. De bär mönster och
# testfixturer som ser ut som persondata och som är påhittade. Skillnaden mot
# `scripts/` är inte att det ena är kod och det andra inte, utan att skripten
# under `scripts/` läser skarp kundpost och skriver utdata ur den.
BEVAKADE = ("docs/", "mallar/", "config/", "scripts/", "CLAUDE.md")

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
# utskrivet. Undantaget gäller exakt strängen, inte mönstret, och en DEL av en
# post godtas bara när hela posten står i samma rad. Se `_tillaten`.
TILLATNA = {
    # Brevlådan själv står i CLAUDE.md §0 och är företagets, inte en persons.
    "info@autostockholm.se",
    # Verkstadens eget växelnummer, av SAMMA klass som brevlådan ovan: det är
    # publicerat på autostockholm.se och tillhör företaget, inte en person.
    # Lars §10-beslut i skiva 44 skrev in det i `config/fakta.json`, som är en
    # bevakad katalog, och spärren fällde commit:en. Undantaget rör orsaken:
    # numret ÄR ett telefonnummer, och det är inte persondata.
    #
    # **UNDANTAGET TYSTAR INTE VAKTENS EGET BEVIS.** Skiva 33:s lärdom nedan är
    # att ett undantag aldrig får göra spärren blind för den sträng dess eget
    # test använder som kanariefågel. `test_telefonnummer_falls` använder en
    # annan sträng, alltså står beviset kvar.
    "076-860 38 15",
    # VERKSTADENS EGEN POSTADRESS, av samma klass som brevlådan och växelnumret
    # ovan: den är publicerad på autostockholm.se och tillhör företaget, inte en
    # person. Lars §10-beslut i skiva 58 DEL A skrev in den i
    # `config/fakta.json`, som är en bevakad katalog, och spärren fällde
    # commit:en precis som den gjorde för numret i skiva 44.
    #
    # **UNDANTAGET RÖR ORSAKEN och skriver inte om texten.** Skriptets eget
    # stoppmeddelande föreskriver den här åtgärden och förbjuder den andra:
    # adressen ÄR en gatuadress och ett postnummer, och den är inte persondata.
    #
    # **EN POST OCH INTE TVÅ, och det ledet är fällt fram av §7-granskningen av
    # skiva 58.** Två mönster träffar var sin DEL av värdet: `gatuadress` tar
    # gatudelen, `postnummer` de fem siffrorna utan orten. En första lydelse la
    # de två delsträngarna här var för sig, och då var de undantagna ÖVERALLT:
    # en KUNDS postnummer med samma siffror hade passerat vakten tyst, vilket är
    # precis den invändning `postnummer`-mönstrets egen kommentar reser. Posten
    # är därför HELA adressen, och `_tillaten` godtar en del av den bara när hela
    # värdet står i samma rad.
    #
    # **UNDANTAGET TYSTAR INTE VAKTENS EGET BEVIS.** `test_gatuadress_falls` och
    # `test_postnummer_med_ort_falls` använder andra strängar, alltså står båda
    # kanariefåglarna kvar.
    "Surbrunnsgatan 42, 113 48 Stockholm",
    # RUFFS REGELKOD FÖR EN FÖR BRED EXCEPT, inget registreringsnummer. Koden
    # har tre bokstäver och tre siffror och beskrivs här i stället för att
    # skrivas ut, som skiva 33 föreskriver. Lars beslut i skiva 69: spärren
    # fällde noqa-kommentaren i `scripts/respond.py`. Samma kommentar står orörd
    # på HEAD i fem filer under `src/`, som inte är bevakad.
    #
    # **POSTEN ÄR HELA KOMMENTAREN och inte koden ensam.** `_tillaten` godtar
    # då koden bara på en rad som bär hela kommentaren, samma snäva form som
    # adressen ovan. Ett nummer med den formen i en kundtext fälls fortfarande.
    "# noqa: BLE001",
    # Exempeladresser i regler och mallar.
    "noreply@example.com",
    "kund@exempel.se",
    # EN SÄKERHETSKOPIAS FILNAMN PÅ PRODUKTIONSVOLYMEN, skiva 81. Namnet är
    # källfilen plus en UTC-tidsstämpel, `YYYYMMDD-HHMM`, och den formen råkar
    # ha exakt personnummer-mönstrets form (sex siffror, ett skiljetecken,
    # fyra siffror). Det är en filsökväg, inte en persons identitetsnummer.
    #
    # **UNDANTAGET RÖR ORSAKEN och skriver inte om texten**, av samma skäl
    # skriptets eget stoppmeddelande föreskriver: `docs/beslutslogg.md` #139
    # namnger filen så att den går att hitta på volymen igen.
    #
    # **HELA FILNAMNET OCH INTE BARA TIDSSTÄMPELN**, samma snäva form som
    # postadressen ovan: `_tillaten` godtar tidsstämpeln bara när hela
    # `par.jsonl.bak-20260925-1100` står i samma rad. En kunds personnummer
    # med råkat SAMMA tolv siffror, utan filnamnet omkring, fälls fortfarande.
    #
    # **UNDANTAGET TYSTAR INTE VAKTENS EGET BEVIS.** `test_personnummer_falls`
    # använder en annan sträng, alltså står kanariefågeln kvar.
    "par.jsonl.bak-20260925-1100",
}

# **INGET REGISTRERINGSNUMMER STÅR I TILLATNA, och det är ett medvetet val.**
# Skiva 33 skrev ett påhittat regnr i `docs/sparrar.md` för att illustrera lucka
# 37, spärren fällde det, och undantaget lades först här. Det gjorde spärren
# blind för exakt den sträng `test_registreringsnummer_falls` använder som sin
# kanariefågel, alltså föll testet. Rätt åtgärd var att BESKRIVA formen i
# dokumentet i stället för att skriva ut en sträng som har den. Ett undantag som
# tystar en spärrs eget bevis är inget undantag.


def _kor(argument: list[str]) -> str:
    # `errors="replace"` matchar arbetsträdsvägen. Utan det gav en stagad
    # binärfil under en bevakad sökväg en UnicodeDecodeError med traceback i
    # stället för ett begripligt meddelande.
    return subprocess.run(
        argument, cwd=ROT, capture_output=True, check=True,
        encoding="utf-8", errors="replace",
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
    return any(sokvag == post or sokvag.startswith(post) for post in BEVAKADE)


def _tillaten(traff: str, rad: str) -> bool:
    """Är träffen undantagen, ensam eller som del av ett undantaget värde?

    **DEN ANDRA GRENEN ÄR SKIVA 58:s, och den SNÄVAR undantaget.** Verkstadens
    postadress träffas av två mönster som var för sig returnerar en DEL av
    värdet: `gatuadress` tar gatudelen, `postnummer` tar de fem siffrorna utan
    orten, som ligger i en lookahead. Lades de två delarna i `TILLATNA` var för
    sig blev de undantagna ÖVERALLT, alltså hade en KUNDS postnummer eller en
    KUNDS gatuadress med samma siffror passerat vakten tyst. Det är precis den
    invändning `postnummer`-mönstrets egen kommentar reser mot att lägga bara tal
    i `TILLATNA`.

    Undantaget gäller därför den HELA adressen, och en del av den godtas bara när
    hela värdet står i samma rad. Grenen kan bara göra vakten snävare: utan den
    hade posterna behövt vara de två delsträngarna.

    Fällt av §7-granskningen av skiva 58.
    """
    ren = traff.strip()
    if ren in TILLATNA:
        return True
    return any(ren in tillaten and tillaten in rad for tillaten in TILLATNA)


def granska(text: str, sokvag: str) -> list[tuple[int, str, str]]:
    """Träffar som (radnummer, sort, träffen).

    Träffen returneras för att kunna maskeras i utskriften. Den skrivs ALDRIG
    ut i klartext: ett skript som larmar om persondata får inte självt skriva
    ut den i en terminallogg.

    TEXTEN GRANSKAS I TVÅ PASS, rad för rad och sedan sammanfogad. Dokumenten
    här är hårdbrutna vid omkring åttio tecken, och en adress som bryts mitt i
    eller ett telefonnummer som bryts mellan grupperna syns inte i något av
    raderna var för sig. Ett radbaserat pass ensamt missade alltså normalfallet
    och inte kantfallet.
    """
    fynd = []
    for nummer, rad in enumerate(text.splitlines(), start=1):
        for sort, monster in MONSTER:
            for traff in monster.finditer(rad):
                if not _tillaten(traff.group(0), rad):
                    fynd.append((nummer, sort, traff.group(0)))

    redan = {(sort, traff) for _, sort, traff in fynd}
    hopfogad = _hopfogad(text)
    for sort, monster in MONSTER:
        for traff in monster.finditer(hopfogad):
            varde = traff.group(0)
            if (sort, varde) in redan or _tillaten(varde, hopfogad):
                continue
            fynd.append((0, f"{sort} (över radslut)", varde))

    return fynd


def _hopfogad(text: str) -> str:
    """Radslut bort, så att ombruten persondata blir synlig.

    Radslutet ersätts med ingenting och inte med ett mellanslag: en adress
    bryts utan bindestreck, och ett mellanslag hade satt tillbaka den lucka
    mönstret inte tål.
    """
    return "".join(rad.strip() for rad in text.splitlines())


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
