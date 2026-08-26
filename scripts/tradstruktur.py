"""Skriver ut STRUKTUREN på en tråd ur data/tradar.jsonl, med persondata maskerad.

Finns för att `data/tradar.jsonl` bär namn, adresser, telefonnummer och
registreringsnummer (CLAUDE.md §6), och strukturen ändå måste kunna redovisas i
en rapport. Skriptet skriver aldrig ut brödtext: bara fältnamn, nästling,
storlekar, och maskerade huvudvärden.

Maskeringen är avsiktligt trubbig. Att maska för mycket är ofarligt, att maska
för lite är en §6-överträdelse.

    .venv/bin/python scripts/tradstruktur.py --index 0
"""

from __future__ import annotations

import argparse
import json
import re
from email.utils import getaddresses
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
INFIL = ROT / "data" / "tradar.jsonl"

# Huvuden vars värde kan bära persondata och därför alltid maskeras.
KANSLIGA_HUVUDEN = {
    "from", "to", "cc", "bcc", "reply-to", "delivered-to", "return-path",
    "x-original-sender", "sender",
}

# Ämnesraden maskeras HELT, inte mönstervis. Den bär regnummer, kundnamn och
# fritext, och en delvis maskering släppte igenom en identifierare vid första
# körningen mot brevlådan.
#
# Maskeringen kostar något, och det ska stå utskrivet: svarsprefixet `Re:`,
# `Sv:` eller `Fwd:` är STRUKTUR och inte persondata, och det är just vad
# extract.py behöver för att skilja ett första mail från ett svar. Prefixet
# redovisas därför separat nedan, resten maskeras.
HELMASKADE_HUVUDEN = {"subject"}

SVARSPREFIX = re.compile(r"^\s*((?:re|sv|ang|vb|fwd|fw)\s*:\s*)+", re.IGNORECASE)

# Vidarebefordringsprefix, svenska och engelska. En vidarebefordran bär
# In-Reply-To och References precis som ett svar, och går inte att skilja från
# ett svar på huvudena. Prefixet är det enda signalementet.
#
# Bara det YTTERSTA prefixet avgör. `Fwd: X` är en vidarebefordran vi skickat,
# medan `Re: Fwd: X` är ett SVAR på något som vidarebefordrats till oss. Att
# tillåta re- och sv-prefix före fwd hade uteslutit den andra sorten, som är
# äkta svar.
VIDAREPREFIX = re.compile(r"^\s*(?:vb|fwd|fw)\s*:", re.IGNORECASE)

# Huvuden som bara finns på post som PASSERAT INKOMMANDE LEVERANS. Ett mail som
# skrivits i Gmail och skickats därifrån har dem inte. De skiljer alltså ett
# skrivet svar från en formulärnotis som bär SENT men kommit utifrån.
LEVERANSHUVUDEN = {"received", "delivered-to", "return-path", "received-spf"}

# Huvuden som ett SVAR bär, till skillnad från ett första mail.
SVARSHUVUDEN = {"in-reply-to", "references"}

MOTTAGARHUVUDEN = {"to", "cc", "bcc"}

# Brevlådan själv, ur CLAUDE.md §0. Ett mail vars enda mottagare är den här
# adressen går inte till någon kund.
BREVLADA = "info@autostockholm.se"


def _adresser(meddelande: dict, huvudnamn: set[str]) -> set[str]:
    ut = set()
    for namn, varde in _huvuden(meddelande):
        if namn.lower() in huvudnamn:
            for _, adress in getaddresses([varde]):
                if adress:
                    ut.add(adress.lower())
    return ut


def ar_gmail_svar(meddelande: dict) -> bool:
    """Sant för den sort som hör hemma som HÖGER sida i ett par enligt
    docs/beslutslogg.md #5 och #8: ett svar skrivet i Gmail till en kund.

    Villkoren, alla nödvändiga:

    - `SENT` i labelIds, alltså utgående.
    - INGA leveranshuvuden. Formulärnotiser bär `SENT` men har passerat
      inkommande leverans och bär därför `Received` och `Return-Path`.
    - Både `In-Reply-To` och `References`, alltså ett svar i en tråd och inte
      ett första utgående mail.
    - INTE `multipart/report`. Leveransrapporter och studsar avsänds från
      brevlådan och kan bära `In-Reply-To` utan att vara skrivna av någon.
    - MINST EN MOTTAGARE SOM INTE ÄR BREVLÅDAN.
    - INGET VIDAREBEFORDRINGSPREFIX i ämnesraden. En vidarebefordran bär
      `In-Reply-To` och `References` precis som ett svar och uppfyllde alla
      tidigare villkor, trots att #5 uttryckligen utesluter den. Prefixet är det
      enda signalementet: huvudena skiljer dem inte åt. Villkoret är därför
      språkberoende och täcker svenska och engelska, vilket är en känd
      begränsning och inte en förbisedd.
    """
    if "SENT" not in (meddelande.get("labelIds") or []):
        return False

    namn = {namn.lower() for namn, _ in _huvuden(meddelande)}
    if namn & LEVERANSHUVUDEN:
        return False
    if not SVARSHUVUDEN <= namn:
        return False

    typ = meddelande.get("payload", {}).get("mimeType", "")
    if typ.startswith("multipart/report"):
        return False

    mottagare = _adresser(meddelande, MOTTAGARHUVUDEN)
    if not mottagare - {BREVLADA}:
        return False

    for namn_, varde in _huvuden(meddelande):
        if namn_.lower() == "subject" and VIDAREPREFIX.match(varde):
            return False
    return True


def ar_kundmeddelande(meddelande: dict) -> bool:
    """Sant för det som kan utgöra VÄNSTER sida i ett par, alltså kundens text.

    Två sorter räknas, och den andra är lätt att missa:

    - Meddelanden utan `SENT`, alltså vanlig inkommande post.
    - Formulärnotiser, som bär `SENT` MEN har passerat inkommande leverans.
      De innehåller kundens ärende och har kunden i `Reply-To`. #5 säger att de
      inte får bli SVAR, och det stämmer. Men de är kundens meddelande, och en
      tråd där notisen är kundsidan och ett Gmail-skrivet svar är vår sida är
      ett fullgott par. Att kräva ett meddelande utan `SENT` uteslöt dem.
    """
    if "SENT" not in (meddelande.get("labelIds") or []):
        return True
    namn = {namn.lower() for namn, _ in _huvuden(meddelande)}
    return bool(namn & LEVERANSHUVUDEN)

# `=` ingår i lokaldelen: VERP- och bounce-adresser kodar in en ANNAN adress
# där, som `bounces+12-kalle=exempel.se@sg.net`. Utan `=` börjar matchningen
# efter likhetstecknet och lämnar den inkodade adressen i klartext.
EPOST = re.compile(r"[A-Za-z0-9._%+=-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
REGNR = re.compile(r"\b[A-ZÅÄÖa-zåäö]{3}\s?\d{2}[A-ZÅÄÖa-zåäö0-9]\b")
SIFFROR = re.compile(r"\d[\d\s()+-]{4,}\d")


def _maska_epost(traff: re.Match) -> str:
    adress = traff.group(0)
    lokal, _, doman = adress.partition("@")
    delar = doman.rsplit(".", 1)
    return f"{lokal[:1]}***@{delar[0][:1]}***.{delar[1]}"


def maska(text: str) -> str:
    """Ordningen spelar roll: adresser först, de innehåller både bokstäver
    och siffror som annars fångas av de senare mönstren."""
    text = EPOST.sub(_maska_epost, text)
    text = REGNR.sub("[REGNR]", text)
    text = SIFFROR.sub("[SIFFROR]", text)
    return text


def _initialer(visningsnamn: str) -> str:
    rensat = visningsnamn.strip().strip('"').strip()
    if not rensat:
        return ""
    return ".".join(ord_[:1].upper() for ord_ in rensat.split() if ord_) + "."


def maska_adressrad(varde: str) -> str:
    """Maskerar BÅDE adressen och visningsnamnet.

    Att bara maska adressen räcker inte: `Förnamn Efternamn <a@b.se>` lämnar
    kundens namn i klartext, vilket är en §6-överträdelse.

    Uppdelningen görs med `email.utils.getaddresses` och ALDRIG genom att
    splitta på komma. Ett citerat visningsnamn av formen
    `"Efternamn, Förnamn" <adress>` innehåller ett komma, och en rå splittning
    bryter det i två poster varav den första saknar vinkelparenteser och
    passerar omaskerad. Den formen är Outlooks standard, och brevlådan tar emot
    O365-post.

    Känns formen inte igen maskeras HELA värdet. Ingen gren får returnera
    indata oförändrad: det som inte går att tolka är också det som inte går att
    garantera är ofarligt.
    """
    poster = []
    for visningsnamn, adress in getaddresses([varde]):
        if not adress:
            continue
        initialer = _initialer(visningsnamn)
        poster.append(f"{initialer} <{maska(adress)}>".strip())

    if not poster:
        return f"[MASKERAD, {len(varde)} tecken]"
    return ", ".join(poster)


def _huvuden(meddelande: dict) -> list[tuple[str, str]]:
    return [
        (h.get("name", ""), h.get("value", ""))
        for h in meddelande.get("payload", {}).get("headers", [])
    ]


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
        varde = trad[nyckel]
        if nyckel == "messages":
            print(f"  {nyckel}: lista, {len(meddelanden)} meddelanden")
        else:
            print(f"  {nyckel}: {type(varde).__name__}")

    print("")
    print("=== MEDDELANDEN ===")
    for nummer, meddelande in enumerate(meddelanden):
        etiketter = meddelande.get("labelIds", []) or []
        utgaende = "SENT" in etiketter
        print(f"\n-- meddelande[{nummer}] --")
        print(f"  fält: {sorted(meddelande.keys())}")
        print(f"  labelIds: {etiketter}")
        print(f"  UTGÅENDE (SENT i labelIds): {utgaende}")
        print(f"  internalDate: {meddelande.get('internalDate')}")
        print(f"  sizeEstimate: {meddelande.get('sizeEstimate')}")

        huvuden = _huvuden(meddelande)
        print(f"  antal huvuden: {len(huvuden)}")
        for namn, varde in huvuden:
            if namn.lower() in HELMASKADE_HUVUDEN:
                traff = SVARSPREFIX.match(varde)
                prefix = traff.group(0).strip() if traff else "inget"
                print(
                    f"    {namn}: [MASKERAD, {len(varde)} tecken] "
                    f"svarsprefix={prefix!r}"
                )
            elif namn.lower() in KANSLIGA_HUVUDEN:
                print(f"    {namn}: {maska_adressrad(varde)}")
        namngivna = sorted({namn for namn, _ in huvuden})
        print(f"  huvudnamn: {namngivna}")

        nyttolast = meddelande.get("payload", {})
        print(f"  payload-fält: {sorted(nyttolast.keys())}")
        print("  MIME-träd:")
        for rad in _deltrad(nyttolast, 2):
            print(rad)


def summera(tradar: list[dict]) -> None:
    """Aggregat över hela filen. Inga värden, bara räkningar, så att utdatan
    kan läggas i en rapport utan §6-risk."""
    antal_meddelanden = []
    tradar_med_sent = 0
    tradar_bara_sent = 0
    meddelanden_totalt = 0
    sent_totalt = 0
    mimetyper: dict[str, int] = {}
    med_bilaga = 0
    saknar_textdel = 0

    for trad in tradar:
        meddelanden = trad.get("messages", []) or []
        antal_meddelanden.append(len(meddelanden))
        meddelanden_totalt += len(meddelanden)
        sent_i_trad = 0
        for meddelande in meddelanden:
            etiketter = meddelande.get("labelIds", []) or []
            if "SENT" in etiketter:
                sent_i_trad += 1
            nyttolast = meddelande.get("payload", {})
            typ = nyttolast.get("mimeType", "saknas")
            mimetyper[typ] = mimetyper.get(typ, 0) + 1
            platt = _platta(nyttolast)
            if any(d.get("body", {}).get("attachmentId") for d in platt):
                med_bilaga += 1
            if not any(
                d.get("mimeType") in ("text/plain", "text/html") for d in platt
            ):
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

    langst = max(range(len(antal_meddelanden)), key=lambda i: antal_meddelanden[i])
    print(f"  index för längsta tråden: {langst}")


def _platta(del_: dict) -> list[dict]:
    delar = [del_]
    for underdel in del_.get("parts", []) or []:
        delar.extend(_platta(underdel))
    return delar


def rakna_svar(tradar: list[dict]) -> None:
    """Räknar underlaget för mallarna. Detta är måttet som avgör om projektet
    har något att bygga på, se docs/beslutslogg.md #5."""
    tradar_med_svar = 0
    svar_totalt = 0
    tradar_med_svar_och_kundmail = 0
    tradar_utan_svar = 0

    for trad in tradar:
        meddelanden = trad.get("messages", []) or []
        svar = [m for m in meddelanden if ar_gmail_svar(m)]
        har_kundtext = any(ar_kundmeddelande(m) for m in meddelanden)

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
    """Visar urvalsverdikten per meddelande, med mottagarna maskerade. Finns
    för att kunna se VARFÖR ett meddelande räknas eller inte, utan att läsa
    data/tradar.jsonl direkt."""
    for nummer, meddelande in enumerate(trad.get("messages", []) or []):
        namn = {n.lower() for n, _ in _huvuden(meddelande)}
        mottagare = _adresser(meddelande, MOTTAGARHUVUDEN)
        print(f"-- meddelande[{nummer}] --")
        print(f"  SENT: {'SENT' in (meddelande.get('labelIds') or [])}")
        print(f"  leveranshuvuden: {sorted(namn & LEVERANSHUVUDEN)}")
        print(f"  svarshuvuden kompletta: {SVARSHUVUDEN <= namn}")
        print(f"  payload.mimeType: {meddelande.get('payload', {}).get('mimeType')}")
        print(f"  mottagare: {sorted(maska(a) for a in mottagare)}")
        print(f"  mottagare utanför brevlådan: "
              f"{sorted(maska(a) for a in mottagare - {BREVLADA})}")
        print(f"  ar_gmail_svar: {ar_gmail_svar(meddelande)}")
        print(f"  ar_kundmeddelande: {ar_kundmeddelande(meddelande)}")


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--fil", type=Path, default=INFIL)
    tolk.add_argument("--index", type=int, default=0)
    tolk.add_argument("--summering", action="store_true")
    tolk.add_argument("--svarsrakning", action="store_true")
    tolk.add_argument("--kontrollera", action="store_true")
    arg = tolk.parse_args(argv)

    rader = arg.fil.read_text(encoding="utf-8").splitlines()

    if arg.kontrollera:
        if not 0 <= arg.index < len(rader):
            print(f"index {arg.index} finns inte, filen har {len(rader)} rader")
            return 2
        kontrollera(json.loads(rader[arg.index]))
        return 0

    if arg.svarsrakning:
        rakna_svar([json.loads(rad) for rad in rader if rad])
        return 0

    if arg.summering:
        summera([json.loads(rad) for rad in rader if rad])
        return 0

    if not 0 <= arg.index < len(rader):
        print(f"index {arg.index} finns inte, filen har {len(rader)} rader")
        return 2

    redovisa(json.loads(rader[arg.index]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
