"""Klassar om BESVARAD mot OBESVARAD på rätt kriterium, utan ny mining.

MININGEN ANVÄNDE `in:sent`, alltså Gmail-etiketten SENT, som ensam grund för
uppdelningen. En tråd hamnade i `data/tradar.jsonl` om den innehöll ett SKICKAT
meddelande. För varje kanal där brevlådan själv är avsändare, framför allt
webbformuläret, är det något helt annat än att någon svarat.

RÄTT KRITERIUM är `src/urval.py::ar_gmail_svar`: en tråd är BESVARAD om den bär
ett mänskligt skrivet svar. Beslut av Lars i skiva 15, se `docs/beslutslogg.md`.

Skriptet läser BÅDA skördarna, klassar om varje tråd, och redovisar hur talen
flyttar. Ingen mining sker och ingen fil skrivs.

§6: skriptet skriver ENBART antal och avsändardomäner. Ingen kundtext, inga
adresser, inga namn. Domäner som bara förekommer enstaka gånger slås ihop,
eftersom en personlig domän kan identifiera en person.

    .venv/bin/python scripts/besvarad-omklassning.py
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from email.header import decode_header, make_header
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import klassa_maskin, urval  # noqa: E402

BESVARADE = ROT / "data" / "tradar.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"
PAR = ROT / "data" / "par.jsonl"

# En domän måste förekomma minst så här många gånger för att skrivas ut.
# Under gränsen slås den ihop, eftersom en personlig domän kan identifiera en
# person (§6).
MINSTA_DOMAN = 3


def meddelanden(trad: dict) -> list[dict]:
    if isinstance(trad.get("messages"), list):
        return trad["messages"]
    return [trad]


def har_gmail_svar(trad: dict) -> bool:
    """RÄTT KRITERIUM för besvarad: ett mänskligt skrivet svar i tråden."""
    return any(urval.ar_gmail_svar(m) for m in meddelanden(trad))


def ar_formular(meddelande: dict) -> bool:
    """Webbformulärets notis, igenkänd på ämnesraden.

    Samma predikat som `scripts/formular-matning.py`: ämnesraden innehåller
    `offertförfrågan a-traktor`, skiftlägesokänsligt. Avsändardomänen duger
    INTE, eftersom den egna domänen också bär annan maskinell trafik.
    """
    ra = urval.huvudvarde(meddelande, "subject")
    try:
        rubrik = str(make_header(decode_header(ra)))
    except Exception:
        rubrik = ra
    return "offertförfrågan a-traktor" in rubrik.lower()


def forsta_kundmeddelande(trad: dict) -> dict | None:
    for m in meddelanden(trad):
        if urval.ar_kundmeddelande(m):
            return m
    return None


def las(sokvag: Path):
    if not sokvag.exists():
        return
    with sokvag.open(encoding="utf-8") as fil:
        for rad in fil:
            rad = rad.strip()
            if rad:
                yield json.loads(rad)


def sammanslagen(rakning: Counter) -> dict:
    """Domäner under gränsen slås ihop till en rad (§6)."""
    ut, smulor, smulantal = {}, 0, 0
    for doman, antal in rakning.most_common():
        if antal >= MINSTA_DOMAN:
            ut[doman] = antal
        else:
            smulor += antal
            smulantal += 1
    if smulor:
        ut[f"<{smulantal} domäner med färre än {MINSTA_DOMAN} träffar>"] = smulor
    return ut


def kor(besvarade: Path, obesvarade: Path) -> int:
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)

    # Fyra fack: skörd × rätt klassning.
    fack = Counter()
    # Trådar som miningen kallade besvarade men som saknar svar.
    flyttar_doman = Counter()
    flyttar_kund = 0
    flyttar_maskin = 0
    # Trådar bland de flyttande som är webbformulärets notis. Mätt på
    # ÄMNESRADEN, inte på domänen: den egna domänen bär också annan trafik.
    flyttar_formular = 0
    # Kontroll åt andra hållet.
    obesvarad_med_svar = 0

    for trad in las(besvarade):
        svar = har_gmail_svar(trad)
        fack["besvarad-skörd, har svar" if svar
             else "besvarad-skörd, SAKNAR svar"] += 1
        if svar:
            continue
        m0 = forsta_kundmeddelande(trad)
        if m0 is None:
            fack["   varav utan kundmeddelande"] += 1
            continue
        if klassa_maskin.tradens_skal(trad, domaner):
            flyttar_maskin += 1
            continue
        flyttar_kund += 1
        flyttar_formular += ar_formular(m0)
        flyttar_doman[klassa_maskin.avsandardoman(m0) or "<ingen>"] += 1

    for trad in las(obesvarade):
        if har_gmail_svar(trad):
            obesvarad_med_svar += 1
        fack["obesvarad-skörd"] += 1

    par_rader = sum(1 for _ in las(PAR))
    par_texter = {p.get("inkommande_text", "") for p in las(PAR)}

    # FAST ORDNING, inte sorterad: delposten ska stå UNDER sin huvudpost.
    # Sorterad utskrift lade den överst, som syskon till facken, och inbjöd
    # till att läsa den som en egen kategori.
    print("=== SKÖRDARNA MOT RÄTT KRITERIUM")
    print(f"  besvarad-skörd, har svar           "
          f"{fack['besvarad-skörd, har svar']}")
    print(f"  besvarad-skörd, SAKNAR svar        "
          f"{fack['besvarad-skörd, SAKNAR svar']}")
    print(f"    därav utan kundmeddelande        "
          f"{fack['   varav utan kundmeddelande']}")
    print(f"  obesvarad-skörd                    {fack['obesvarad-skörd']}")
    print(f"  obesvarad-skörd som ÄNDÅ bär svar: {obesvarad_med_svar}")
    print()

    print("=== TRÅDAR SOM FLYTTAR FRÅN BESVARAD TILL OBESVARAD")
    print(f"  totalt utan svar i besvarad-skörden: "
          f"{fack['besvarad-skörd, SAKNAR svar']}")
    print(f"    varav utan kundmeddelande alls:   "
          f"{fack['   varav utan kundmeddelande']}")
    print(f"    varav maskinmail:                 {flyttar_maskin}")
    print(f"    varav KUNDÄRENDEN som flyttar:    {flyttar_kund}")
    print(f"      därav webbformulärets notis:    {flyttar_formular}")
    print()

    print("=== KANALER SOM BÄR FELET, per avsändardomän")
    for doman, antal in sammanslagen(flyttar_doman).items():
        print(f"  {doman:44} {antal}")
    print()

    print("=== PAR-SIDAN, oförändrad")
    print(f"  rader i par.jsonl:        {par_rader}")
    print(f"  unika kundtexter:         {len(par_texter)}")
    print("  par.jsonl bygger på ar_gmail_svar via src/extract.py och")
    print("  påverkas alltså INTE av felet. Talet med svar står kvar.")
    print()

    # Varför saknar de flyttande kundärendena ett svar, och hur många NYA
    # texter bidrar de med?
    skal = Counter()
    nya = set()
    # Hur många av de nya texterna som kommer ur webbformuläret. Räknas när
    # texten läggs till första gången, alltså per UNIK text och inte per tråd.
    nya_formular = 0
    text_i_formular: set[str] = set()
    text_i_ovrigt: set[str] = set()
    # Samma texter som `nya`, men OAVDUBBLADE, så prefixkontrollen nedan kan
    # jämföra avdubbling på hela strängen mot avdubbling på ett prefix.
    rana: list[str] = []
    for trad in las(besvarade):
        if har_gmail_svar(trad):
            continue
        m0 = forsta_kundmeddelande(trad)
        if m0 is None or klassa_maskin.tradens_skal(trad, domaner):
            continue
        text = urval.brodtext(m0)
        if text and text not in par_texter:
            if text not in nya and ar_formular(m0):
                nya_formular += 1
            # Om en och samma text bärs av BÅDE en formulärtråd och en
            # icke-formulärtråd blir räkningen ovan ordningsberoende. Det
            # mäts i stället för att antas.
            (text_i_formular if ar_formular(m0) else text_i_ovrigt).add(text)
            nya.add(text)
            rana.append(text)
        for m in meddelanden(trad):
            namn = urval.huvudnamn(m)
            if "SENT" not in (m.get("labelIds") or []):
                skal["meddelandet är inte skickat av oss"] += 1
            elif namn & urval.LEVERANSHUVUDEN:
                skal["skickat, men bär leveranshuvud"] += 1
            elif not urval.SVARSHUVUDEN <= namn:
                skal["skickat, men saknar svarshuvud"] += 1
            elif not urval.adresser(m, urval.MOTTAGARHUVUDEN) - {urval.BREVLADA}:
                skal["skickat, men ingen mottagare utanför brevlådan"] += 1
            elif urval.VIDAREPREFIX.match(urval.huvudvarde(m, "subject")):
                skal["skickat, men vidarebefordran"] += 1
            else:
                skal["<oklart>"] += 1

    print(f"=== VARFÖR DE {flyttar_kund} SAKNAR SVAR, per meddelande i tråden")
    for k, v in skal.most_common():
        print(f"  {k:48} {v}")
    print()
    # Den OBESVARADE kolumnen, byggd med samma urval som
    # `src/kategorisera.py` rad 95-109: icke-maskin, första kundmeddelandet.
    ob_texter: set[str] = set()
    for trad in las(obesvarade):
        if klassa_maskin.tradens_skal(trad, domaner):
            continue
        for meddelande in meddelanden(trad):
            if not urval.ar_kundmeddelande(meddelande):
                continue
            text = urval.brodtext(meddelande)
            if text:
                ob_texter.add(text)
            break

    print("=== VAD DE TILLFÖR KORPUSEN")
    print(f"  nya unika kundtexter, mätt mot par.jsonl:  {len(nya)}")
    print(f"  texter i den OBESVARADE kolumnen:          {len(ob_texter)}")
    print(f"  av de nya som ÄNDÅ finns där:              {len(nya & ob_texter)}")
    print(f"  alltså nya i BÅDA kolumnerna:              {len(nya - ob_texter)}")
    print(f"  av de nya som kommer ur webbformuläret:    {nya_formular}")
    print(f"  texter som bärs av BÅDE formulär och annat: "
          f"{len(text_i_formular & text_i_ovrigt)}")
    print("    Är den noll är talet ovan oberoende av läsordningen.")
    print()

    # PREFIXKOLLISION: en jämförelse på de första tecknen slår ihop två texter
    # som delar ingress men skiljer sig längre ned. Skriptet jämför HELA
    # strängen; talet nedan visar vad en prefixgenväg hade gett.
    print("=== PREFIXKONTROLL")
    print(f"  texter bakom de nya:        {len(rana)}")
    print(f"  unika på hela strängen:     {len(set(rana))}")
    print(f"  unika på 400 teckens prefix: {len({t[:400] for t in rana})}")
    return 0


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--besvarade", type=Path, default=BESVARADE)
    tolk.add_argument("--obesvarade", type=Path, default=OBESVARADE)
    arg = tolk.parse_args(argv)
    return kor(arg.besvarade, arg.obesvarade)


if __name__ == "__main__":
    raise SystemExit(main())
