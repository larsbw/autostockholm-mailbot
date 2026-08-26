"""Skriver ut STRUKTUREN på en tråd, med persondata maskerad.

Finns för att trådfilerna bär namn, adresser, telefonnummer och
registreringsnummer (CLAUDE.md §6), och strukturen ändå måste kunna redovisas i
en rapport. Skriptet skriver aldrig ut brödtext eller snippet: bara fältnamn,
nästling, storlekar, och maskerade huvudvärden.

URVAL OCH MASKERING BOR I `src/`, inte här. Skriptet hade tidigare egna kopior
av båda. Två kopior driver isär, och ett saknat villkor i den ena kopian var
precis vad som gjorde talet i beslutslogg #7 fel.

    .venv/bin/python scripts/tradstruktur.py --index 0
    .venv/bin/python scripts/tradstruktur.py --summering
    .venv/bin/python scripts/tradstruktur.py --svarsrakning
    .venv/bin/python scripts/tradstruktur.py --kontrollera --index 41
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import maskera, urval  # noqa: E402

INFIL = ROT / "data" / "tradar.jsonl"

# Huvuden vars värde kan bära persondata och därför alltid maskeras.
KANSLIGA_HUVUDEN = {
    "from", "to", "cc", "bcc", "reply-to", "delivered-to", "return-path",
    "x-original-sender", "sender",
}

# Ämnesraden maskeras HELT, inte mönstervis. En delvis maskering släppte igenom
# en identifierare vid första körningen mot brevlådan. Svarsprefixet redovisas
# separat, eftersom det är struktur och inte persondata.
HELMASKADE_HUVUDEN = {"subject"}

SVARSPREFIX = re.compile(r"^\s*((?:re|sv|ang|vb|fwd|fw)\s*:\s*)+", re.IGNORECASE)


def _deltrad(del_: dict, niva: int = 0) -> list[str]:
    """MIME-trädet, utan innehåll. Bara typ, storlek och filnamnets existens."""
    indrag = "  " * niva
    kropp = del_.get("body", {})
    rader = [
        f"{indrag}- mimeType={del_.get('mimeType')} "
        f"size={kropp.get('size')} "
        f"data={'ja' if kropp.get('data') else 'nej'} "
        f"attachmentId={'ja' if kropp.get('attachmentId') else 'nej'} "
        f"filename={'ja' if del_.get('filename') else 'nej'}"
    ]
    for underdel in del_.get("parts", []) or []:
        rader.extend(_deltrad(underdel, niva + 1))
    return rader


def redovisa(trad: dict) -> None:
    meddelanden = trad.get("messages", []) or []

    print("=== TRÅDNIVÅ ===")
    for nyckel in trad:
        if nyckel == "messages":
            print(f"  {nyckel}: lista, {len(meddelanden)} meddelanden")
        else:
            print(f"  {nyckel}: {type(trad[nyckel]).__name__}")

    print("")
    print("=== MEDDELANDEN ===")
    for nummer, meddelande in enumerate(meddelanden):
        etiketter = meddelande.get("labelIds", []) or []
        print(f"\n-- meddelande[{nummer}] --")
        print(f"  fält: {sorted(meddelande.keys())}")
        print(f"  labelIds: {etiketter}")
        print(f"  UTGÅENDE (SENT i labelIds): {'SENT' in etiketter}")
        print(f"  internalDate: {meddelande.get('internalDate')}")
        print(f"  sizeEstimate: {meddelande.get('sizeEstimate')}")

        huvuden = urval.huvuden(meddelande)
        print(f"  antal huvuden: {len(huvuden)}")
        for namn, varde in huvuden:
            if namn.lower() in HELMASKADE_HUVUDEN:
                traff = SVARSPREFIX.match(varde)
                prefix = traff.group(0).strip() if traff else "inget"
                print(f"    {namn}: [MASKERAD, {len(varde)} tecken] "
                      f"svarsprefix={prefix!r}")
            elif namn.lower() in KANSLIGA_HUVUDEN:
                print(f"    {namn}: {maskera.maska_adressrad(varde)}")
        print(f"  huvudnamn: {sorted({namn for namn, _ in huvuden})}")

        nyttolast = meddelande.get("payload", {})
        print(f"  payload-fält: {sorted(nyttolast.keys())}")
        print("  MIME-träd:")
        for rad in _deltrad(nyttolast, 2):
            print(rad)


def _platta(del_: dict) -> list[dict]:
    delar = [del_]
    for underdel in del_.get("parts", []) or []:
        delar.extend(_platta(underdel))
    return delar


def summera(tradar: list[dict]) -> None:
    antal_meddelanden = []
    meddelanden_totalt = 0
    sent_totalt = 0
    tradar_med_sent = 0
    tradar_bara_sent = 0
    mimetyper: dict[str, int] = {}
    med_bilaga = 0
    saknar_textdel = 0

    for trad in tradar:
        meddelanden = trad.get("messages", []) or []
        antal_meddelanden.append(len(meddelanden))
        meddelanden_totalt += len(meddelanden)
        sent_i_trad = 0
        for meddelande in meddelanden:
            if "SENT" in (meddelande.get("labelIds") or []):
                sent_i_trad += 1
            nyttolast = meddelande.get("payload", {})
            typ = nyttolast.get("mimeType", "saknas")
            mimetyper[typ] = mimetyper.get(typ, 0) + 1
            platt = _platta(nyttolast)
            if any(d.get("body", {}).get("attachmentId") for d in platt):
                med_bilaga += 1
            if not any(d.get("mimeType") in ("text/plain", "text/html")
                       for d in platt):
                saknar_textdel += 1
        sent_totalt += sent_i_trad
        if sent_i_trad:
            tradar_med_sent += 1
        if sent_i_trad == len(meddelanden):
            tradar_bara_sent += 1

    print("=== SUMMERING ===")
    print(f"  trådar: {len(tradar)}")
    print(f"  meddelanden totalt: {meddelanden_totalt}")
    print(f"  meddelanden med SENT: {sent_totalt}")
    print(f"  trådar med minst ett SENT: {tradar_med_sent}")
    print(f"  trådar där ALLA meddelanden är SENT: {tradar_bara_sent}")
    print(f"  minsta antal meddelanden i en tråd: {min(antal_meddelanden)}")
    print(f"  största antal meddelanden i en tråd: {max(antal_meddelanden)}")
    print(f"  meddelanden med bilaga: {med_bilaga}")
    print(f"  meddelanden utan text/plain eller text/html: {saknar_textdel}")
    print("  payload.mimeType, antal per typ:")
    for typ in sorted(mimetyper):
        print(f"    {typ}: {mimetyper[typ]}")

    fordelning: dict[int, int] = {}
    for antal in antal_meddelanden:
        fordelning[antal] = fordelning.get(antal, 0) + 1
    print("  trådlängd, antal trådar per längd:")
    for langd in sorted(fordelning):
        print(f"    {langd} meddelanden: {fordelning[langd]} trådar")

    langst = max(range(len(antal_meddelanden)),
                 key=lambda i: antal_meddelanden[i])
    print(f"  index för längsta tråden: {langst}")


def rakna_svar(tradar: list[dict]) -> None:
    """Räknar underlaget för mallarna, se docs/beslutslogg.md #8."""
    tradar_med_svar = 0
    svar_totalt = 0
    tradar_med_svar_och_kundmail = 0
    tradar_utan_svar = 0

    for trad in tradar:
        meddelanden = trad.get("messages", []) or []
        svar = [m for m in meddelanden if urval.ar_gmail_svar(m)]
        har_kundtext = any(urval.ar_kundmeddelande(m) for m in meddelanden)

        svar_totalt += len(svar)
        if svar:
            tradar_med_svar += 1
            if har_kundtext:
                tradar_med_svar_och_kundmail += 1
        else:
            tradar_utan_svar += 1

    print("=== UNDERLAG FÖR MALLARNA ===")
    print(f"  trådar totalt: {len(tradar)}")
    print("")
    print(f"  TRÅDAR MED SVAR OCH KUNDTEXT ATT PARA IHOP: "
          f"{tradar_med_svar_och_kundmail}")
    print("")
    print(f"  trådar med minst ett svar skrivet i Gmail: {tradar_med_svar}")
    print(f"  sådana svar totalt: {svar_totalt}")
    print(f"  trådar utan något skrivet svar: {tradar_utan_svar}")


def kontrollera(trad: dict) -> None:
    """Urvalsverdikten per meddelande, med mottagarna maskerade. Finns för att
    kunna se VARFÖR ett meddelande räknas eller inte."""
    for nummer, meddelande in enumerate(trad.get("messages", []) or []):
        namn = urval.huvudnamn(meddelande)
        mottagare = urval.adresser(meddelande, urval.MOTTAGARHUVUDEN)
        print(f"-- meddelande[{nummer}] --")
        print(f"  SENT: {'SENT' in (meddelande.get('labelIds') or [])}")
        print(f"  leveranshuvuden: {sorted(namn & urval.LEVERANSHUVUDEN)}")
        print(f"  svarshuvuden kompletta: {urval.SVARSHUVUDEN <= namn}")
        print(f"  payload.mimeType: "
              f"{meddelande.get('payload', {}).get('mimeType')}")
        print(f"  mottagare: {sorted(maskera.maska(a) for a in mottagare)}")
        print(f"  mottagare utanför brevlådan: "
              f"{sorted(maskera.maska(a) for a in mottagare - {urval.BREVLADA})}")
        print(f"  ar_gmail_svar: {urval.ar_gmail_svar(meddelande)}")
        print(f"  ar_kundmeddelande: {urval.ar_kundmeddelande(meddelande)}")


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--fil", type=Path, default=INFIL)
    tolk.add_argument("--index", type=int, default=0)
    tolk.add_argument("--summering", action="store_true")
    tolk.add_argument("--svarsrakning", action="store_true")
    tolk.add_argument("--kontrollera", action="store_true")
    arg = tolk.parse_args(argv)

    rader = arg.fil.read_text(encoding="utf-8").splitlines()

    if arg.svarsrakning:
        rakna_svar([json.loads(rad) for rad in rader if rad])
        return 0

    if arg.summering:
        summera([json.loads(rad) for rad in rader if rad])
        return 0

    if not 0 <= arg.index < len(rader):
        print(f"index {arg.index} finns inte, filen har {len(rader)} rader")
        return 2

    trad = json.loads(rader[arg.index])
    if arg.kontrollera:
        kontrollera(trad)
    else:
        redovisa(trad)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
