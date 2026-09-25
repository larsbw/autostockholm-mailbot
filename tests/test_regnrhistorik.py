"""`src/regnrhistorik.py`. UPPDRAG 2026-09-25 DEL 1.

**INGET TEST HÄR RÖR NÄTET.** `FejkGmail` (tests/fejk.py) ersätter Gmail helt.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext, inga riktiga adresser (§6).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from src import inkorg, regnrhistorik, vy
from src.kedja import RegnrLage
from tests.fejk import FejkGmail
from tests.test_respond import meddelande, trad
from tests.test_vy import peka_om_katalogerna

REGNR = "ABC123"

# `NU` ÄR KÖRNINGENS KLOCKA, samma roll som `kedja.kor`s `nu`. De andra tre
# är millisekunder sedan epok, Gmails egen form för `internalDate`, alla
# INOM `regnrhistorik.FONSTER_DAGAR` (14) från `NU` utom där testet uttryckligen
# prövar fönstrets kant.
NU = datetime(2026, 4, 20, 8, 0, tzinfo=timezone.utc)
EGEN_TID = "2026-04-18T15:44:27+00:00"
EGEN_INTERNAL = str(int(datetime.fromisoformat(EGEN_TID).timestamp() * 1000))
ALDRE_INTERNAL = str(int((NU - timedelta(days=3)).timestamp() * 1000))
NYARE_INTERNAL = str(int((NU - timedelta(hours=1)).timestamp() * 1000))
UTANFOR_FONSTRET_INTERNAL = str(
    int((NU - timedelta(days=20)).timestamp() * 1000))


def _tjanst(sidor, tradar) -> inkorg.Lastjanst:
    return inkorg.Lastjanst(FejkGmail(sidor=sidor, tradar=tradar))


def _sidor(*trad_id_lista: str) -> dict:
    return {None: {"threads": [{"id": t} for t in trad_id_lista],
                   "nextPageToken": None}}


def _kundmeddelande(regnr_i_texten: str = REGNR, internal=ALDRE_INTERNAL):
    return meddelande(f"Fråga om {regnr_i_texten}", internal=internal)


def _svarsmeddelande(internal=ALDRE_INTERNAL):
    """Ett meddelande `urval.ar_gmail_svar` säger ja till."""
    return meddelande(
        "Svar till kunden", sent=True, internal=internal,
        huvuden={"To": "kund@exempel.invalid",
                "In-Reply-To": "<kund-1@exempel.invalid>",
                "References": "<kund-1@exempel.invalid>"},
    )


def test_inga_andra_trador_ger_gront_lage():
    tjanst = _tjanst(_sidor(), {})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_egen_trad_utesluts_ur_traffarna():
    """Utan uteslutningen skulle förfrågan stoppa sig själv."""
    egen_trad = trad(_kundmeddelande(internal=EGEN_INTERNAL), trad_id="t-eget")
    tjanst = _tjanst(_sidor("t-eget"), {"t-eget": egen_trad})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_en_NYARE_trad_STOPPAR():
    annan = trad(_kundmeddelande(internal=NYARE_INTERNAL), trad_id="t-nyare")
    tjanst = _tjanst(_sidor("t-nyare"), {"t-nyare": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage.stoppa


def test_en_ALDRE_trad_UTAN_svar_eller_utkast_STOPPAR_INTE():
    annan = trad(_kundmeddelande(internal=ALDRE_INTERNAL), trad_id="t-aldre")
    tjanst = _tjanst(_sidor("t-aldre"), {"t-aldre": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_ett_RIKTIGT_SVAR_stoppar_ALLTID_oavsett_alder():
    """UPPDRAG 2026-09-25, Lars beslut (tolkning A): ett svar väger tyngre än
    ett utkast, och det gäller även om svaret är i en ÄLDRE tråd."""
    annan = trad(_kundmeddelande(internal=ALDRE_INTERNAL),
                 _svarsmeddelande(internal=ALDRE_INTERNAL), trad_id="t-svarad")
    tjanst = _tjanst(_sidor("t-svarad"), {"t-svarad": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage.stoppa


def test_ett_OBESICKAT_UTKAST_stoppar_INTE_men_samlas_for_borttagning(
        tmp_path, monkeypatch):
    """Tolkning A: kommer en nyare förfrågan går den vidare, och den äldre
    trådens utkast ska bort. `vy.gmailutkast_finns` avgör om utkastet finns."""
    peka_om_katalogerna(monkeypatch, tmp_path)
    omdomen = tmp_path / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(
        vy.Fall(etikett="fråga om a-traktorkonvertering", kalla="kedjan",
               text="", tidsstampel="", avsandare_hash=""),
        "t-har-utkast", "skapat", "m-1", "d-1", omdomesfil=omdomen,
    )
    annan = trad(_kundmeddelande(internal=ALDRE_INTERNAL),
                 trad_id="t-har-utkast")
    tjanst = _tjanst(_sidor("t-har-utkast"), {"t-har-utkast": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU,
                             omdomesfil=omdomen)

    assert lage == RegnrLage(stoppa=False,
                             aldre_utkast_trad_id=("t-har-utkast",))


def test_ett_BORTTAGET_utkast_samlas_INTE_for_borttagning_igen(
        tmp_path, monkeypatch):
    peka_om_katalogerna(monkeypatch, tmp_path)
    omdomen = tmp_path / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(
        vy.Fall(etikett="fråga om a-traktorkonvertering", kalla="kedjan",
               text="", tidsstampel="", avsandare_hash=""),
        "t-borttaget", "skapat", "m-1", "d-1", omdomesfil=omdomen,
    )
    vy.spara_gmailutkast(
        vy.Fall(etikett="regnrfilter", kalla="regnrfilter", text="",
               tidsstampel="", avsandare_hash=""),
        "t-borttaget", vy.BORTTAGET, omdomesfil=omdomen,
    )
    annan = trad(_kundmeddelande(internal=ALDRE_INTERNAL),
                 trad_id="t-borttaget")
    tjanst = _tjanst(_sidor("t-borttaget"), {"t-borttaget": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU,
                             omdomesfil=omdomen)

    assert lage == RegnrLage(stoppa=False)


def test_GMAILS_GROVA_NAT_bekraftas_LOKALT_mot_brodtexten():
    """Ett falskt positivt ur `q` (Gmails egen tokenisering) ska INTE räknas,
    se modulens docstring om grovt nät kontra exakt lokalt filter."""
    annan = trad(meddelande("Ett helt annat ärende, inget regnr här",
                            internal=NYARE_INTERNAL),
                 trad_id="t-falsk-traff")
    tjanst = _tjanst(_sidor("t-falsk-traff"), {"t-falsk-traff": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_SAMMA_tidsstampel_stoppar_inte():
    """En tråd lika gammal som den egna är inte NYARE. Skydd mot att ett mail
    med samma tidsstämpel som sig själv stoppar sig självt."""
    annan = trad(_kundmeddelande(internal=EGEN_INTERNAL), trad_id="t-samma")
    tjanst = _tjanst(_sidor("t-samma"), {"t-samma": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_UTANFOR_FONSTRET_raknas_inte_ens_med_regnr_i_texten():
    """Gmails `newer_than:` är bara det grova nätet, se modulens docstring
    och `_inom_fonstret`. En tråd Gmail råkade lämna med i det grova nätet,
    fast den ligger utanför de riktiga `dagar` dagarna, ska ändå uteslutas."""
    annan = trad(_kundmeddelande(internal=UTANFOR_FONSTRET_INTERNAL),
                 trad_id="t-for-gammal")
    tjanst = _tjanst(_sidor("t-for-gammal"), {"t-for-gammal": annan})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage == RegnrLage(stoppa=False)


def test_flera_trador_en_stoppar_racker():
    """Så fort NÅGON träff stoppar räknas ingen borttagning, oavsett vad de
    andra trådarna bär."""
    nyare = trad(_kundmeddelande(internal=NYARE_INTERNAL), trad_id="t-nyare")
    aldre = trad(_kundmeddelande(internal=ALDRE_INTERNAL), trad_id="t-aldre")
    tjanst = _tjanst(_sidor("t-nyare", "t-aldre"),
                     {"t-nyare": nyare, "t-aldre": aldre})

    lage = regnrhistorik.sok(tjanst, REGNR, "t-eget", EGEN_TID, NU)

    assert lage.stoppa
    assert lage.aldre_utkast_trad_id == ()
