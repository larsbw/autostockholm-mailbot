"""Mäter webbformulärets fält, ämnesrad och etiketter i skördarna.

Skriptet bär de tal som `docs/roadmap.md` fas 4.5 skriver ut om webbformuläret,
och de tal `docs/sparrar.md` skriver ut under `gmail-etikett-som-ensam-grund`.
Det hör hemma i repot på samma grund som `scripts/regnr-matning.py`, se
`docs/incidentlogg.md` I5: en mätning som bär ett styrdokuments påstående ska gå
att räkna om.

PREDIKATEN, utskrivna så att talen går att räkna om:

- FORMULÄRTRÅD: ämnesraden på trådens första kundmeddelande innehåller
  `offertförfrågan a-traktor`, skiftlägesokänsligt.
- FÄLTETIKETT: en rad i den avkodade brödtexten som börjar med ett ord följt av
  kolon. Kroppen avkodas med `src/urval.py::brodtext`.
- REGISTRERINGSNUMMER: mönstret lånas ur `scripts/persondatakontroll.py`, alltså
  `\\b[A-ZÅÄÖ]{3}[\\s-]?\\d{2}[A-ZÅÄÖ0-9]\\b`. Det kopieras INTE hit.
- MASKINMAIL MED EGEN DOMÄN: `klassa_maskin.tradens_skal` är sann OCH
  `klassa_maskin.avsandardoman` på första kundmeddelandet är `autostockholm.se`.
  Populationen är BÅDA skördarna.

§6: skriptet skriver ENBART antal, fältetiketter och etikett-ID. Aldrig ett
registreringsnummer, ett namn, en adress eller en kundtext.

    .venv/bin/python scripts/formular-matning.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter

from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import kanal, klassa_maskin, urval  # noqa: E402

sys.path.insert(0, str(ROT / "scripts"))
import importlib  # noqa: E402

_pdk = importlib.import_module("persondatakontroll")

# Lånat, inte kopierat: samma mönster som §6-kontrollen larmar på. Det är
# VERSALKÄNSLIGT med avsikt, eftersom det ska hitta regnr i dokumenttext utan
# att larma på vanliga ord.
REGNR_STRIKT = dict(_pdk.MONSTER)["registreringsnummer"]

# Kundens egen inmatning är inte versalnormerad. Ett nummer skrivet med gemener
# är fortfarande ett registreringsnummer, så VÄRDET prövas skiftlägesokänsligt.
# Skillnaden mellan de två talen är hela poängen och skrivs ut nedan.
REGNR = re.compile(REGNR_STRIKT.pattern, re.IGNORECASE)

BESVARADE = ROT / "data" / "tradar.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"

# Kategorierna som rör a-traktor. Prövningen är på ORD och inte på substräng,
# lånad ur `src/ometikettera.py::ror_a_traktor`, eftersom `epa` är en substräng
# av `reparation` och en substrängsprövning räknade in `boka reparation`.
_ome = importlib.import_module("src.ometikettera")

EGEN_DOMAN = "autostockholm.se"
FALT = re.compile(r"^\s*([A-Za-zÅÄÖåäö][A-Za-zÅÄÖåäö \-]{1,24})\s*:", re.M)

# Själva fältraden, så att VÄRDET går att pröva skilt från resten av kroppen.
REGNR_FALT = re.compile(r"^\s*Registreringsnummer\s*[:=]\s*(.*)$",
                        re.M | re.IGNORECASE)


def meddelanden(trad: dict) -> list[dict]:
    if isinstance(trad.get("messages"), list):
        return trad["messages"]
    return [trad]


def amne(meddelande: dict) -> str:
    """Avkodad ämnesrad. Bor i `src/kanal.py` sedan skiva 17."""
    return kanal.amnesrad(meddelande)


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


def kor() -> int:
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)

    form = []
    etiketter = Counter()
    form_etiketter = Counter()
    amne_annat = Counter()
    med_kundmeddelande = Counter()
    egen_maskin = []

    for fil, sokvag in (("besvarade", BESVARADE), ("obesvarade", OBESVARADE)):
        for trad in las(sokvag):
            # PER TRÅD, och varje etikett. En tidigare version bröt efter
            # meddelandets FÖRSTA Label_-id, vilket gjorde talet till ett
            # meddelandetal och gjorde mängden distinkta etiketter till en
            # undre gräns: en etikett som aldrig låg först räknades aldrig.
            i_traden = set()
            for m in meddelanden(trad):
                for e in m.get("labelIds") or []:
                    if e.startswith("Label_"):
                        i_traden.add(e)
            for e in i_traden:
                etiketter[e] += 1

            m0 = forsta_kundmeddelande(trad)
            if m0 is None:
                continue
            med_kundmeddelande[fil] += 1
            rubrik = amne(m0)
            ar_form = kanal.ar_webbformular(m0)

            if klassa_maskin.tradens_skal(trad, domaner) \
                    and klassa_maskin.avsandardoman(m0) == EGEN_DOMAN:
                egen_maskin.append((trad, m0, rubrik))

            if ar_form:
                form.append((fil, trad, m0, rubrik))
                sedda = set()
                for m in meddelanden(trad):
                    for e in m.get("labelIds") or []:
                        if e.startswith("Label_") and e not in sedda:
                            sedda.add(e)
                            form_etiketter[e] += 1
            elif REGNR.search(rubrik):
                amne_annat[fil] += 1

    print("=== FORMULÄRTRÅDAR")
    per_fil = Counter(f for f, _, _, _ in form)
    print(f"  totalt: {len(form)}   per fil: {dict(per_fil)}")
    print(f"  trådar med kundmeddelande: {dict(med_kundmeddelande)}")
    print()

    falt = Counter()
    for _, _, m0, _ in form:
        for e in set(FALT.findall(urval.brodtext(m0))):
            falt[e.strip()] += 1
    print("=== FÄLTETIKETTER, fallande")
    for e, n in falt.most_common():
        print(f"  {e:24} {n}/{len(form)}")
    print()

    # FÄLTVÄRDET, inte en fritextsökning i kroppen. Skillnaden spelar roll:
    # en fritextsökning svarar på om ett nummer finns NÅGONSTANS i mailet,
    # medan avläsaren i fas 4.5 ska läsa värdet som står efter etiketten.
    falt_ej_tomt = falt_giltigt = falt_strikt = 0
    for _, _, m0, _ in form:
        rad = REGNR_FALT.search(urval.brodtext(m0))
        if rad is None:
            continue
        falt_ej_tomt += bool(rad.group(1).strip())
        falt_giltigt += bool(REGNR.search(rad.group(1)))
        falt_strikt += bool(REGNR_STRIKT.search(rad.group(1)))

    strikt_kropp = sum(1 for _, _, m0, _ in form
                       if REGNR_STRIKT.search(urval.brodtext(m0)))
    strikt_amne = sum(1 for _, _, _, r in form if REGNR_STRIKT.search(r))

    i_kropp = i_amne = lika = kropp_utan_amne = 0
    for _, _, m0, rubrik in form:
        tk = REGNR.search(urval.brodtext(m0))
        ta = REGNR.search(rubrik)
        i_kropp += bool(tk)
        i_amne += bool(ta)
        if tk and ta:
            lika += tk.group(0).replace(" ", "").replace("-", "") \
                == ta.group(0).replace(" ", "").replace("-", "")
        if tk and not ta:
            kropp_utan_amne += 1
    print("=== REGISTRERINGSNUMMER I FORMULÄRTRÅDARNA")
    print(f"  fältraden finns MED ICKE-TOMT värde:  {falt_ej_tomt}/{len(form)}")
    print(f"  FÄLTVÄRDET tolkas som ett regnr:      {falt_giltigt}/{len(form)}")
    print(f"  mönstret finns någonstans i kroppen:  {i_kropp}/{len(form)}")
    print(f"  värdet tolkas som regnr i ämnesraden: {i_amne}/{len(form)}")
    print(f"  båda, och identiska:                  {lika}/{len(form)}")
    print(f"  i kroppen men INTE i ämnesraden:      {kropp_utan_amne}/{len(form)}")
    print(f"  SAMMA prövning med §6:s VERSALKÄNSLIGA mönster:")
    print(f"    FÄLTVÄRDET {falt_strikt}/{len(form)}"
          f"   brödtext {strikt_kropp}/{len(form)}"
          f"   ämnesrad {strikt_amne}/{len(form)}")
    print("    Skillnaden är kundens skiftläge, inte saknade nummer.")
    print(f"    En FÄLTAVLÄSARE med det strikta mönstret tappar "
          f"{falt_giltigt - falt_strikt} av {falt_giltigt}.")
    print()
    print("=== NEGATIVKONTROLL: ämnesrad matchar mönstret utan att vara formulär")
    for fil in ("besvarade", "obesvarade"):
        print(f"  {fil:12} {amne_annat[fil]} av {med_kundmeddelande[fil]}")
    print()

    # VILKEN KATEGORI FORMULÄRTRÅDARNA FICK. Formuläret ÄR a-traktorformuläret,
    # men klassificeraren ser bara fritexten och aldrig att inskicket kom den
    # vägen. Talet nedan är hur ofta det slår fel.
    etikett_for_text = {}
    if OMETIKETTERADE.exists():
        for rad in OMETIKETTERADE.open(encoding="utf-8"):
            rad = rad.strip()
            if rad:
                post = json.loads(rad)
                etikett_for_text[post["text"]] = post["etikett"]

    print("=== FORMULÄRTRÅDARNAS KATEGORI")
    if not etikett_for_text:
        print("  data/ometiketterade.jsonl saknas, prövningen kan inte göras.")
    else:
        fick = Counter()
        for _, _, m0, _ in form:
            fick[etikett_for_text.get(urval.brodtext(m0), "<ej i korpusen>")] += 1
        i_korpus = sum(a for e, a in fick.items() if e != "<ej i korpusen>")
        traktor = sum(a for e, a in fick.items()
                      if e != "<ej i korpusen>" and _ome.ror_a_traktor(e))
        print(f"  formulärtrådar: {len(form)}   återfunna i korpusen: {i_korpus}")
        print(f"  klassade som a-traktor:     {traktor}")
        print(f"  klassade som NÅGOT ANNAT:   {i_korpus - traktor}")
        print("  fördelning, fallande:")
        for e, antal in fick.most_common():
            if e == "<ej i korpusen>":
                continue
            markor = "a-traktor" if _ome.ror_a_traktor(e) else "ANNAT"
            print(f"    {e:38} {antal:3}  {markor}")
        saknas = fick.get("<ej i korpusen>", 0)
        if saknas:
            print(f"  ej återfunna i korpusen: {saknas}")
            print("    Texten paras i `src/extract.py` och behöver inte vara")
            print("    teckenidentisk med `brodtext` på första kundmeddelandet.")
    print()

    print("=== HANDSATTA ETIKETTER I MATERIALET, fallande")
    print(f"  distinkta Label_*-id: {len(etiketter)}")
    for e, n in etiketter.most_common():
        i_form = form_etiketter.get(e, 0)
        print(f"  {e:34} {n:5}   varav formulärtrådar: {i_form}/{len(form)}")
    print()

    print("=== MASKINMAIL MED EGEN DOMÄN")
    print(f"  trådar: {len(egen_maskin)}")
    bokning = [t for t in egen_maskin if "Appointment" in t[2]]
    print(f"    varav bokningsnotiser (Appointment i ämnet): {len(bokning)}")
    print(f"    varav ÖVRIGA:                                "
          f"{len(egen_maskin) - len(bokning)}")
    # AVKODAD text, aldrig den råa filraden: brödtexten är base64url-kodad och
    # en sökning i filraden ser bara `snippet`. Se `docs/incidentlogg.md` I5.
    ord_wp = huvud = 0
    for trad, m0, _ in egen_maskin:
        if "Appointment" in amne(m0):
            continue
        text = " ".join(
            [urval.brodtext(m) for m in meddelanden(trad)]
            + [amne(m) for m in meddelanden(trad)]
        ).lower()
        ord_wp += "wordpress" in text
        huvud += any("x-msg-eid" in urval.huvudnamn(m) for m in meddelanden(trad))
    ovriga = len(egen_maskin) - len(bokning)
    print(f"    av de ÖVRIGA bär {ord_wp}/{ovriga} ordet wordpress någonstans")
    print(f"    av de ÖVRIGA bär {huvud}/{ovriga} huvudet X-Msg-EID")
    print()

    print("=== BOKNINGSNOTISERNA")
    langd = sorted(len(urval.brodtext(m)) for _, m, _ in bokning)
    ordn = sorted(len(urval.brodtext(m).split()) for _, m, _ in bokning)
    adresser = {a for _, m, _ in bokning for a in urval.adresser(m, {"from"})}
    print(f"  antal: {len(bokning)}")
    print(f"  teckenlängd: {langd}")
    print(f"  ordantal:    {ordn}")
    print(f"  distinkta avsändaradresser: {len(adresser)}")
    print(f"  bär regnr:            "
          f"{sum(1 for _, m, _ in bokning if REGNR.search(urval.brodtext(m)))}")
    print(f"  bär fältetikett:      "
          f"{sum(1 for _, m, _ in bokning if FALT.search(urval.brodtext(m)))}")
    print(f"  bär mänskligt svar:   "
          f"{sum(1 for t, _, _ in bokning if any(urval.ar_gmail_svar(m) for m in meddelanden(t)))}")
    delad = sum(1 for _, m, _ in egen_maskin
                if urval.adresser(m, {"from"}) & adresser)
    print(f"  trådar bland de {len(egen_maskin)} som delar dessa adresser: {delad}")
    return 0


if __name__ == "__main__":
    raise SystemExit(kor())
