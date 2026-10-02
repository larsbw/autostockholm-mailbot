#!/usr/bin/env python3
"""Mäter TypeSafe Jev mot nuvarande triageklassning. FRISTÅENDE, ENDAST MÄTNING.

Inget här är inkopplat i kedjan. Skriptet läser lokala skördar, skriver till de
gitignorerade `data/jev-test/` och `scratchpad/`, och anropar två API:er:
TypeSafe (maskerad text) och Anthropic (rå text, samma väg som `kedja.kor`).
Det rör inte Gmail och skickar ingenting.

Fem steg, ett per underkommando, i den här ordningen:

    urval      drar ett fast urval trådar och skriver uppmärkningsfilen
    maskera    skriver exakt det som skulle gå till Jev, utan nätanrop
    jev        ett anrop per mejl mot Jev, fyra frågor i samma anrop
    nuvarande  pass 2 plus kanalregeln, alltså vad kedjan säger i dag
    mat        mäter båda mot facit, alltså den av Lars ifyllda uppmärkningsfilen

**FACIT ÄR UPPMÄRKNINGSFILEN OCH INGET ANNAT.** `mat` mäter bara på de rader
där `a_traktor` är ifylld, och vägrar köra om ingen är det. `kategori` och
`matte_maste_se` är frivilliga och mäts bara där de är ifyllda. Nuvarande
klassning är en av de två som mäts och aldrig facit.

**ETT FACIT PÅ ENBART DE OENIGA RADERNA AVGÖR VEM SOM HAR RÄTT DÄR, OCH INGET
MER.** Så kördes mätningen 2026-10-02. Har Jev och nuvarande klassning samma
fel på en rad utan facit syns det inte, alltså säger kalibreringen,
routningströskeln och "missade av båda" ingenting på ett sådant facit.

**§6.** Till Jev går bara maskerad text, se `maska_for_jev`. Registreringsnummer
står kvar på Lars beslut. Uppmärkningsfilen bär rå kundtext och ligger i
`scratchpad/`, som har undantag i §6.

Jev: https://docs.typesafe.ai, avläst 2026-10-02. Modellen är låst till
`jev-1.13.0` och aldrig ett alias. Anropet går med stdlib mot
`POST /v1/systemone`; pip-paketet heter `typesafe-sdk` och används inte, eftersom
ett enda anrop inte motiverar ett nytt beroende.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import random
import re
import statistics
import sys
import time
import urllib.error
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import (kanal, kategorisera, kedja, klassa_maskin,  # noqa: E402
                 maskera, ometikettera, urval)

ROT = Path(__file__).resolve().parent.parent
UTKATALOG = ROT / "data" / "jev-test"
URVALSFIL = UTKATALOG / "urval.jsonl"
MASKERADFIL = UTKATALOG / "maskerat.jsonl"
JEVFIL = UTKATALOG / "jev-svar.jsonl"
# Samma körning med `UNDANTAG` släppta förbi maskeringen, alternativ C.
JEVFIL_UNDANTAG = UTKATALOG / "jev-svar-undantag.jsonl"
MASKERADFIL_UNDANTAG = UTKATALOG / "maskerat-undantag.jsonl"
NUVARANDEFIL = UTKATALOG / "nuvarande.jsonl"
UPPMARKNING = ROT / "scratchpad" / "Mailbot-jev-uppmarkning.csv"
HINKFIL = ROT / "config" / "kategorier.yaml"

JEV_URL = "https://api.typesafe.ai/v1/systemone"
JEV_MODELL = "jev-1.13.0"
JEV_NYCKEL = "TYPESAFE_API_KEY"
# Dollar per miljon in-tokens, avläst på docs.typesafe.ai/models 2026-10-02.
# Ut-tokens kostar ingenting enligt samma sida.
JEV_PRIS_PER_MTOK = 0.042

# Den handsatta Gmail-etiketten som följer a-traktorformuläret, se
# `docs/sparrar.md` under `gmail-etikett-som-ensam-grund`. Den används HÄR bara
# för att dra urvalet, så att svåra a-traktormejl kommer med. Den är inte facit.
A_TRAKTORETIKETT = "Label_4067421502860552187"

FRO = 20261002

# Urvalets fyra skikt: (namn, skördfil, antal).
SKIKT = (
    ("etikett-ej-formular", "etikett-atraktor-nu.jsonl", None),
    ("formular", "etikett-atraktor-nu.jsonl", 20),
    ("ovriga-senaste-skorden", "backfill-skord3.jsonl", 34),
    ("ovriga-besvarade", "tradar.jsonl", 30),
)


# ------------------------------------------------------------------- urval


def _las_jsonl(fil: Path) -> list[dict]:
    return [json.loads(rad) for rad in fil.read_text(encoding="utf-8").splitlines()
            if rad.strip()]


def _skriv_jsonl(poster: list[dict], fil: Path) -> None:
    fil.parent.mkdir(parents=True, exist_ok=True)
    fil.write_text("".join(json.dumps(p, ensure_ascii=False) + "\n" for p in poster),
                   encoding="utf-8")


def _arende(trad: dict, domaner: set[str]) -> dict | None:
    """Samma meddelande och samma tre fält som `respond.arende_ur_trad` ger
    klassningen: första kundmeddelandets text, ämnesrad och kanal."""
    if klassa_maskin.tradens_skal(trad, domaner):
        return None
    for meddelande in trad.get("messages", []) or []:
        if urval.ar_kundmeddelande(meddelande):
            text = urval.brodtext(meddelande)
            if not text.strip():
                return None
            return {"trad_id": trad["id"], "text": text,
                    "amne": kanal.amnesrad(meddelande),
                    "kanal": kanal.namnge(meddelande)}
    return None


def _bar_etiketten(trad: dict) -> bool:
    return any(A_TRAKTORETIKETT in (m.get("labelIds") or [])
               for m in trad.get("messages", []) or [])


def _besvarad(trad: dict) -> bool:
    return any(urval.ar_gmail_svar(m) for m in trad.get("messages", []) or [])


def dra_urval() -> list[dict]:
    """Ett fast urval, samma varje körning.

    URVALET ÄR SKIKTAT OCH INTE SLUMPAT UR INFLÖDET. A-traktormejlen är
    överrepresenterade med avsikt, eftersom det är dem mätningen gäller. Den
    samlade träffsäkerheten säger därför inget om produktionens inflöde; talen
    per kategori och a-traktortalen gör det.

    Skikten dras på kanal, handsatt etikett och om tråden är besvarad. Aldrig på
    nuvarande klassning, som är en av de två som mäts.
    """
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)
    slump = random.Random(FRO)
    valda: list[dict] = []
    sedda_tradar: set[str] = set()
    sedda_texter: set[str] = set()

    for skikt, filnamn, antal in SKIKT:
        kandidater = []
        for trad in _las_jsonl(ROT / "data" / filnamn):
            arende = _arende(trad, domaner)
            if arende is None:
                continue
            etikett = _bar_etiketten(trad)
            formular = arende["kanal"] is not None
            if skikt == "etikett-ej-formular" and not (etikett and not formular):
                continue
            if skikt == "formular" and not formular:
                continue
            if skikt.startswith("ovriga") and (etikett or formular):
                continue
            if skikt == "ovriga-besvarade" and not _besvarad(trad):
                continue
            kandidater.append(arende)
        kandidater.sort(key=lambda a: a["trad_id"])
        slump.shuffle(kandidater)
        tagna = 0
        for arende in kandidater:
            if antal is not None and tagna >= antal:
                break
            if (arende["trad_id"] in sedda_tradar
                    or arende["text"] in sedda_texter):
                continue
            sedda_tradar.add(arende["trad_id"])
            sedda_texter.add(arende["text"])
            valda.append({**arende, "skikt": skikt})
            tagna += 1

    # Blandas, så att uppmärkaren inte ser skikten på radnumret.
    slump.shuffle(valda)
    return [{"nr": nr, **post} for nr, post in enumerate(valda, start=1)]


def skriv_uppmarkning(poster: list[dict], fil: Path) -> None:
    """Ett mejl per rad, tre tomma kolumner. Semikolon och BOM, så att filen
    öppnas rätt i Excel och Numbers med svenska inställningar."""
    if fil.exists():
        raise SystemExit(f"{fil} finns redan och kan vara ifylld. "
                         "Flytta den först, den skrivs aldrig över.")
    fil.parent.mkdir(parents=True, exist_ok=True)
    with fil.open("w", encoding="utf-8-sig", newline="") as ut:
        skriv = csv.writer(ut, delimiter=";")
        skriv.writerow(["nr", "kategori", "a_traktor", "matte_maste_se",
                        "kanal", "amne", "text"])
        for post in poster:
            skriv.writerow([
                post["nr"], "", "", "",
                "formulär" if post["kanal"] else "",
                post["amne"],
                " ".join(post["text"][:kategorisera.MAX_TECKEN].split()),
            ])


def las_facit(fil: Path, taxonomi: list[str]) -> dict[int, dict]:
    """Den ifyllda uppmärkningsfilen. Fäller på rader som inte går att läsa som
    ett facit, i stället för att gissa.

    En rad utan `a_traktor` ingår inte i facit alls. `kategori` och
    `matte_maste_se` är frivilliga, Lars beslut: en tom cell betyder att raden
    inte ingår i just den mätningen, aldrig att svaret är nej eller `övrigt`."""
    ja_nej = {"ja": True, "j": True, "nej": False, "n": False}
    facit: dict[int, dict] = {}
    fel: list[str] = []
    with fil.open(encoding="utf-8-sig", newline="") as in_:
        for rad in csv.DictReader(in_, delimiter=";"):
            nr = int(rad["nr"])
            kategori = rad["kategori"].strip().lower()
            a_traktor = rad["a_traktor"].strip().lower()
            matte = rad["matte_maste_se"].strip().lower()
            if not a_traktor:
                continue
            if kategori and kategori not in taxonomi:
                fel.append(f"rad {nr}: kategorin {kategori!r} står inte i taxonomin")
            if a_traktor not in ja_nej:
                fel.append(f"rad {nr}: a_traktor ska vara ja eller nej")
            if matte and matte not in ja_nej:
                fel.append(f"rad {nr}: matte_maste_se ska vara ja, nej eller tom")
            facit[nr] = {"kategori": kategori or None,
                         "a_traktor": ja_nej.get(a_traktor),
                         "matte": ja_nej.get(matte) if matte else None}
    if fel:
        raise SystemExit("Uppmärkningsfilen är inte ett facit än:\n  "
                         + "\n  ".join(fel[:20])
                         + (f"\n  och {len(fel) - 20} till" if len(fel) > 20 else ""))
    if not facit:
        raise SystemExit("Uppmärkningsfilen bär ingen rad med a_traktor ifylld.")
    return facit


# ---------------------------------------------------------------- maskering

# Ord som `maskera.REGNR` tar för bokstavsdelen i ett registreringsnummer när
# de står före ett telefon- eller boxnummer. Utan listan hade `tel 070` skyddats
# som regnr och sluppit förbi sifferraden.
_EJ_REGNR = {"tel", "mob", "box", "fax", "org"}
_PLATS = "\x00{}\x00"
# Alternativ C, Lars beslut 2026-10-02. De fyra orden är versala och blir
# annars `[NAMN]`, alltså försvinner själva ärendet ur ett a-traktormejl. Inget
# av dem är persondata. Listan är Lars och utökas inte här.
UNDANTAG = re.compile(r"\b(?:EPA|Epa|Epatraktor|Traktor)\b")
_NAMNFALT = re.compile(r"^(namn:)[ \t]*(.+)$", flags=re.IGNORECASE | re.MULTILINE)


def maska_for_jev(text: str, undantag: bool = False) -> str:
    """Repots maskering, med registreringsnumren kvar.

    `maskera.maska_fritext` minus `REGNR`-steget, i samma ordning. Numren lyfts
    ut före maskeringen och sätts tillbaka efter, eftersom ett nummer skrivet
    med mellanslag annars förlorar sina bokstäver till namnmaskeringen.

    Webbformulärets `Namn:`-rad maskeras hel. Versalheuristiken hittar inte ett
    namn skrivet med gemener, och formuläret är det ställe där vi VET att raden
    bär ett namn.

    Med `undantag` lyfts också orden i `UNDANTAG` förbi namnmaskeringen.

    KÄND BEGRÄNSNING, samma som i `src/maskera.py`: ett namn med gemener i
    löpande text går inte att hitta.
    """
    text = _NAMNFALT.sub(lambda t: f"{t.group(1)} [NAMN]", text)

    lyfta: list[str] = []

    def lyft(traff: re.Match) -> str:
        lyfta.append(traff.group(0))
        return _PLATS.format(len(lyfta) - 1)

    def lyft_regnr(traff: re.Match) -> str:
        if (traff.group(0)[:3].lower() in _EJ_REGNR
                or text[traff.end():traff.end() + 1].isdigit()):
            return traff.group(0)
        return lyft(traff)

    text = maskera.REGNR.sub(lyft_regnr, text)
    if undantag:
        text = UNDANTAG.sub(lyft, text)
    for monster, plats in ((maskera.URL, " [LÄNK] "), (maskera.EPOST, " [EPOST] "),
                           (maskera.DOMAN, " [DOMÄN] "), (maskera.GATA, " [GATA] "),
                           (maskera.SIFFROR, " [SIFFROR] ")):
        text = monster.sub(plats, text)
    text = maskera._maska_namn(text)
    for index, lyft_text in enumerate(lyfta):
        text = text.replace(_PLATS.format(index), lyft_text)
    return text


def jev_state(post: dict, undantag: bool = False) -> dict:
    """Det Jev får se: samma tre upplysningar som pass 2, maskerade."""
    state = {"mejl": maska_for_jev(post["text"][:kategorisera.MAX_TECKEN],
                                   undantag)}
    if post["amne"].strip():
        state["amnesrad"] = maska_for_jev(post["amne"].strip(), undantag)
    if post["kanal"]:
        state["kanal"] = post["kanal"]
    return state


# ---------------------------------------------------------------------- Jev

# En kort engelsk beskrivning per kategori. Namnen är taxonomins egna, så att
# svaret går att hinka med `config/kategorier.yaml`; beskrivningarna är skrivna
# för det här testet och står på engelska eftersom Jev enligt TypeSafe är
# starkast där. En kategori som saknas här får `null`, vilket API:t tillåter.
BESKRIVNING = {
    "boka rekond": "Wants to book car detailing / reconditioning",
    "boka biltvätt": "Wants to book a car wash",
    "boka service": "Wants to book a regular service",
    "boka däckbyte": "Wants to book a tyre or wheel change",
    "boka bromskontroll": "Wants to book a brake check",
    "boka reparation": "Wants to book a repair or fault diagnosis",
    "boka tillbehörsmontage": "Wants to book fitting of an accessory, such as a "
                              "tow bar, when it is NOT part of an A-traktor conversion",
    "boka a-traktorkonvertering": "Wants to book a time for converting a car to "
                                  "an A-traktor (EPA-traktor)",
    "avboka bokning": "Cancels an existing booking",
    "omboka bokning": "Wants to move an existing booking",
    "fråga om a-traktorkonvertering": "Asks whether or how a car can be converted "
                                      "to an A-traktor, without mainly asking for a price",
    "fråga om pris rekond": "Asks what detailing costs",
    "fråga om pris service": "Asks what a service costs",
    "fråga om pris reparation": "Asks what a repair costs",
    "fråga om pris däck": "Asks about tyre prices",
    "fråga om pris a-traktorkonvertering": "Asks what an A-traktor conversion "
                                           "costs, or requests a quote for one",
    "fråga om pris tillbehör": "Asks what an accessory or its fitting costs",
    "fråga om däckförvaring": "Asks about tyre storage",
    "fråga om tjänst": "Asks whether the workshop offers a certain service",
    "fråga om praktisk info": "Asks about opening hours, address, drop-off or "
                              "other practical matters",
    "begära offert": "Requests a quote for work that is NOT an A-traktor conversion",
    "godkänna offert": "Accepts a quote the workshop has given",
    "begära dokument": "Asks for an invoice, receipt, certificate or other document",
    "bestrida faktura": "Disputes an invoice or a charge",
    "reklamera utfört arbete": "Complains about work the workshop has done",
    "ge feedback": "Gives praise or criticism without requesting anything",
    "ansöka om praktikplats": "Applies for an internship or a job",
    "övrigt": "None of the other options fit: advertising, automated notices, "
              "suppliers, authorities, or anything that is not a workshop customer matter",
}


def jev_fragor(taxonomi: list[str]) -> dict:
    return {
        "kategori": {
            "type": "choice",
            "instructions": "This is an incoming email, in Swedish, to an "
                            "independent car workshop in Stockholm. Which option "
                            "best describes what the sender wants?",
            "criteria": {namn: BESKRIVNING.get(namn) for namn in taxonomi},
        },
        "a_traktor": {
            "type": "noul",
            "instructions": "Is this email about converting a car into an "
                            "A-traktor (also called EPA-traktor)?",
            "criteria": {
                "true": "The sender asks about, requests a quote for, or wants "
                        "to book an A-traktor conversion, or the email came "
                        "through the A-traktor conversion web form",
                "false": "The email is about anything else, including other "
                         "work on a car that already is an A-traktor",
            },
        },
        "matte_maste_se": {
            "type": "noul",
            "instructions": "Does the workshop owner need to read and handle "
                            "this email personally?",
            "criteria": {
                "true": "A complaint, a disputed invoice, an accepted quote, a "
                        "request that needs a judgement in the workshop, or an "
                        "email whose purpose is unclear",
                "false": "A routine question that standard information can "
                         "answer, or advertising and automated notices that "
                         "need no answer",
            },
        },
        "bradska": {
            "type": "score",
            "instructions": "How urgent is this email for the workshop?",
            "criteria": ["can wait a week or more", "should be answered this week",
                         "needs an answer today"],
        },
    }


def las_jev_nyckel() -> str:
    """Miljön först, sedan `.env`. Skrivs aldrig ut (§6)."""
    nyckel = os.environ.get(JEV_NYCKEL, "").strip()
    if nyckel:
        return nyckel
    envfil = ROT / ".env"
    if envfil.exists():
        for rad in envfil.read_text(encoding="utf-8").splitlines():
            if rad.startswith(JEV_NYCKEL + "="):
                return rad[len(JEV_NYCKEL) + 1:].strip()
    raise SystemExit(f"Ingen {JEV_NYCKEL} i miljön eller i .env.")


def fraga_jev(state: dict, fragor: dict, nyckel: str) -> tuple[dict, float]:
    """Ett anrop. Returnerar svaret och svarstiden i sekunder.

    429 och 529 försöks om med växande väntan, vilket API-sidan föreskriver.
    Alla andra fel går upp: ett 401 eller 422 blir inte rätt av ett omförsök.
    """
    kropp = json.dumps({"model": JEV_MODELL, "state": state,
                        "questions": fragor}).encode("utf-8")
    for forsok in range(4):
        begaran = urllib.request.Request(
            JEV_URL, data=kropp, method="POST",
            headers={"Authorization": f"Bearer {nyckel}",
                     "Content-Type": "application/json"})
        start = time.monotonic()
        try:
            with urllib.request.urlopen(begaran, timeout=60) as svar:
                return json.load(svar), time.monotonic() - start
        except urllib.error.HTTPError as fel:
            if fel.code not in (429, 529) or forsok == 3:
                raise SystemExit(f"Jev svarade {fel.code}: "
                                 f"{fel.read().decode('utf-8', 'replace')[:500]}")
            time.sleep(2 ** forsok)
    raise AssertionError("onåbar")


# --------------------------------------------------------------- nuvarande


def nuvarande_klassning(klient, post: dict, taxonomi: list[str],
                        hinkar: dict) -> dict:
    """Pass 2 och kanalregeln, ordagrant som `kedja.kor` gör dem."""
    start = time.monotonic()
    pass2 = ometikettera.ometikettera_en(
        klient, post["text"], taxonomi, ometikettera.bygg_system_pass2(taxonomi),
        amne=post["amne"], kanal=post["kanal"])
    sekunder = time.monotonic() - start
    kategori = pass2
    if (post["kanal"] == kanal.WEBBFORMULAR
            and kategori not in kedja.A_TRAKTORKATEGORIER
            and kedja._hink_for(kategori, hinkar) != "aldrig"):
        kategori = kedja.KANALKATEGORI
    return {"nr": post["nr"], "pass2": pass2, "kategori": kategori,
            "sekunder": round(sekunder, 3)}


# --------------------------------------------------------------------- mät


def _andel(traffar: int, antal: int) -> str:
    return f"{traffar}/{antal}" + (f" ({100 * traffar / antal:.0f} %)" if antal else "")


def _per_kategori(facit: dict, gissning: dict[int, str]) -> list[str]:
    per: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for nr, f in facit.items():
        per[f["kategori"]][1] += 1
        per[f["kategori"]][0] += gissning[nr] == f["kategori"]
    return [f"| {k} | {_andel(*v)} |"
            for k, v in sorted(per.items(), key=lambda kv: -kv[1][1])]


def _a_traktorfel(facit: dict, gissning: dict[int, bool]) -> tuple[list, list]:
    missade = sorted(nr for nr, f in facit.items()
                     if f["a_traktor"] and not gissning[nr])
    falska = sorted(nr for nr, f in facit.items()
                    if not f["a_traktor"] and gissning[nr])
    return missade, falska


def _intervall(granser: tuple, varde: dict[int, float]) -> list[tuple]:
    return [(lag, hog, [nr for nr, v in varde.items() if lag <= v < hog])
            for lag, hog in zip(granser, granser[1:])]


def mat(skriv=print) -> None:
    taxonomi = json.loads(kedja.TAXONOMIFIL.read_text(encoding="utf-8"))
    import yaml
    hinkar = yaml.safe_load(HINKFIL.read_text(encoding="utf-8"))
    facit = las_facit(UPPMARKNING, taxonomi)
    # De två Jev-körningarna, sida vid sida. Den andra finns bara om
    # `jev --undantag` är körd.
    jevar = {"Jev strikt maskering": {p["nr"]: p for p in _las_jsonl(JEVFIL)}}
    if JEVFIL_UNDANTAG.exists():
        jevar["Jev med undantag"] = {p["nr"]: p
                                     for p in _las_jsonl(JEVFIL_UNDANTAG)}
    nu = {p["nr"]: p for p in _las_jsonl(NUVARANDEFIL)}
    saknas = [nr for nr in facit
              if nr not in nu or any(nr not in j for j in jevar.values())]
    if saknas:
        raise SystemExit(f"svar saknas för rad {saknas[:10]}")

    def svar(jev: dict, nr: int, fraga: str) -> dict:
        return jev[nr]["svar"]["answers"][fraga]

    antal = len(facit)
    a_antal = sum(1 for f in facit.values() if f["a_traktor"])
    skriv(f"mejl i facit: {antal}, varav a-traktor: {a_antal}")

    # KATEGORI MÄTS BARA DÄR DEN ÄR IFYLLD.
    med_kat = {nr: f for nr, f in facit.items() if f["kategori"]}
    kat = {namn: {nr: svar(j, nr, "kategori")["choice"] for nr in facit}
           for namn, j in jevar.items()}
    kat["nuvarande"] = {nr: nu[nr]["kategori"] for nr in facit}
    kat["nuvarande, bara pass 2"] = {nr: nu[nr]["pass2"] for nr in facit}
    skriv(f"\n# Kategori, mätt på de {len(med_kat)} rader där facit bär en")
    if med_kat:
        for namn, gissning in kat.items():
            ratt = sum(gissning[nr] == f["kategori"] for nr, f in med_kat.items())
            ratt_hink = sum(kedja._hink_for(gissning[nr], hinkar)
                            == kedja._hink_for(f["kategori"], hinkar)
                            for nr, f in med_kat.items())
            skriv(f"\n## {namn}: {_andel(ratt, len(med_kat))} rätt, "
                  f"rätt hink {_andel(ratt_hink, len(med_kat))}")
            skriv("| facit | rätt |\n|---|---|")
            for rad in _per_kategori(med_kat, gissning):
                skriv(rad)

    skriv("\n# A-traktor, alla rader")
    noul = {namn: {nr: svar(j, nr, "a_traktor")["noul"] for nr in facit}
            for namn, j in jevar.items()}
    a_gissning = {}
    for namn in jevar:
        a_gissning[f"{namn}, Noul minst 0,5"] = {
            nr: p >= 0.5 for nr, p in noul[namn].items()}
        a_gissning[f"{namn}, Choice gav a-traktorkategori"] = {
            nr: k in kedja.A_TRAKTORKATEGORIER for nr, k in kat[namn].items()}
    for namn in ("nuvarande", "nuvarande, bara pass 2"):
        a_gissning[namn] = {nr: k in kedja.A_TRAKTORKATEGORIER
                            for nr, k in kat[namn].items()}
    missar = {}
    for namn, gissning in a_gissning.items():
        missade, falska = _a_traktorfel(facit, gissning)
        missar[namn] = set(missade)
        skriv(f"{namn}: missade {len(missade)} {missade}, "
              f"falska {len(falska)} {falska}")
    for namn in jevar:
        bada = missar[f"{namn}, Noul minst 0,5"] & missar["nuvarande"]
        skriv(f"missade av BÅDE {namn} (Noul) och nuvarande: {sorted(bada)}")

    for namn, jev in jevar.items():
        skriv(f"\n# {namn}")
        if med_kat:
            skriv("Kalibrering, Choice: rätt kategori per konfidensintervall")
            konf = {nr: svar(jev, nr, "kategori")["confidence"] for nr in med_kat}
            for lag, hog, i in _intervall((0.0, 0.5, 0.7, 0.9, 0.99, 1.0000001),
                                          konf):
                ratt = sum(kat[namn][nr] == med_kat[nr]["kategori"] for nr in i)
                skriv(f"  {lag:.2f} till {min(hog, 1):.2f}: {_andel(ratt, len(i))}")
        skriv("Kalibrering, Noul a-traktor: andel a-traktor i facit per intervall")
        for lag, hog, i in _intervall((0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0000001),
                                      noul[namn]):
            ja = sum(1 for nr in i if facit[nr]["a_traktor"])
            skriv(f"  {lag:.1f} till {min(hog, 1):.1f}: {_andel(ja, len(i))}")

        # Trösklarna sätts på SAMMA mejl som de mäts på, alltså är andelen ett
        # tak och inget löfte om nästa hundra.
        skriv("Routning utan missade a-traktormejl")
        ja = [noul[namn][nr] for nr, f in facit.items() if f["a_traktor"]]
        nej = [noul[namn][nr] for nr, f in facit.items() if not f["a_traktor"]]
        if ja and nej:
            lag, hog = min(ja), max(nej)
            auto_nej = sum(1 for p in noul[namn].values() if p < lag)
            auto_ja = sum(1 for p in noul[namn].values() if p > hog)
            skriv(f"  lägsta Noul bland facits a-traktormejl: {lag:.3f}")
            skriv(f"  högsta Noul bland facits övriga mejl: {hog:.3f}")
            skriv(f"  under den lägsta, routas som ej a-traktor: "
                  f"{_andel(auto_nej, antal)}")
            skriv(f"  över den högsta, routas som a-traktor: "
                  f"{_andel(auto_ja, antal)}")
            skriv(f"  resten, till Matte: "
                  f"{_andel(antal - auto_nej - max(auto_ja, 0), antal)}")

        matte = {nr: f["matte"] for nr, f in facit.items()
                 if f["matte"] is not None}
        if matte:
            ratt = sum((svar(jev, nr, "matte_maste_se")["noul"] >= 0.5) == v
                       for nr, v in matte.items())
            skriv(f"Matte måste se, Noul minst 0,5: {_andel(ratt, len(matte))} "
                  "rätt, på de rader där facit bär ett svar")

        skriv("Brådska, Score avrundad, inte mätt mot facit: "
              + str(sorted(Counter(round(svar(jev, nr, "bradska")["score"])
                                   for nr in facit).items())))
        tok = [jev[nr]["svar"]["usage"]["input_tokens"] for nr in facit]
        tid = [jev[nr]["sekunder"] for nr in facit]
        skriv(f"in-tokens per mejl, medel: {statistics.mean(tok):.0f}")
        skriv(f"dollar per mejl, medel: "
              f"{statistics.mean(tok) * JEV_PRIS_PER_MTOK / 1e6:.6f}")
        skriv(f"svarstid, median {statistics.median(tid):.2f} s, "
              f"högst {max(tid):.2f} s")

    tid = [nu[nr]["sekunder"] for nr in facit]
    skriv(f"\n# nuvarande svarstid, median {statistics.median(tid):.2f} s, "
          f"högst {max(tid):.2f} s")


# -------------------------------------------------------------------- main


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    tolk.add_argument("steg", choices=("urval", "maskera", "jev", "nuvarande", "mat"))
    tolk.add_argument("--undantag", action="store_true",
                      help="släpp EPA, Epa, Epatraktor och Traktor förbi "
                           "maskeringen (stegen maskera och jev)")
    tolk.add_argument("--max-poster", type=int, default=None,
                      help="begränsa antalet mejl, för en provkörning")
    arg = tolk.parse_args(argv)

    if arg.steg == "urval":
        poster = dra_urval()
        skriv_uppmarkning(poster, UPPMARKNING)
        _skriv_jsonl(poster, URVALSFIL)
        print(f"mejl i urvalet: {len(poster)}")
        for skikt, antal in sorted(Counter(p["skikt"] for p in poster).items()):
            print(f"  {skikt}: {antal}")
        print(f"uppmärkningsfil: {UPPMARKNING}")
        return 0

    if arg.steg == "mat":
        mat()
        return 0

    poster = _las_jsonl(URVALSFIL)[:arg.max_poster]
    taxonomi = json.loads(kedja.TAXONOMIFIL.read_text(encoding="utf-8"))

    if arg.steg == "maskera":
        utfil = MASKERADFIL_UNDANTAG if arg.undantag else MASKERADFIL
        _skriv_jsonl([{"nr": p["nr"], "state": jev_state(p, arg.undantag)}
                      for p in poster], utfil)
        print(f"maskerade mejl: {len(poster)}, skrivna till {utfil}")
        return 0

    if arg.steg == "jev":
        nyckel = las_jev_nyckel()
        fragor = jev_fragor(taxonomi)
        ut = []
        for post in poster:
            svar, sekunder = fraga_jev(jev_state(post, arg.undantag), fragor,
                                       nyckel)
            ut.append({"nr": post["nr"], "sekunder": round(sekunder, 3),
                       "svar": svar})
            _skriv_jsonl(ut, JEVFIL_UNDANTAG if arg.undantag else JEVFIL)
        print(f"Jev-svar: {len(ut)}, modell {ut[0]['svar'].get('model')}")
        return 0

    import yaml
    hinkar = yaml.safe_load(HINKFIL.read_text(encoding="utf-8"))
    klient = kategorisera.bygg_klient()
    ut = []
    for post in poster:
        ut.append(nuvarande_klassning(klient, post, taxonomi, hinkar))
        _skriv_jsonl(ut, NUVARANDEFIL)
    print(f"klassade med nuvarande kedja: {len(ut)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
