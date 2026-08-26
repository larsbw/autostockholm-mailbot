"""Tester för maskeringen i scripts/tradstruktur.py.

Ingen riktig data rörs. Samtliga indata är påhittade, och testerna prövar de
former som en granskning bröt maskeringen med (CLAUDE.md §6).

Påståendet varje test bär är att persondata INTE syns i utdatan, alltså den sort
§7.1 kräver att man prövar genom att fälla raden och se sviten bli röd.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "tradstruktur", ROT / "scripts" / "tradstruktur.py"
)
tradstruktur = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(tradstruktur)


def test_citerat_visningsnamn_med_komma_lacker_inte_efternamnet():
    """Outlooks standardform. En rå split på komma bryter den i två poster,
    varav den första saknar vinkelparenteser och passerade omaskerad."""
    rad = '"Efternamnsson, Förnamn" <fornamn@exempel.se>'

    ut = tradstruktur.maska_adressrad(rad)

    assert "Efternamnsson" not in ut
    assert "Förnamn" not in ut
    assert "fornamn" not in ut


def test_adressrad_utan_vinkelparenteser_returneras_aldrig_oforandrad():
    rad = "Förnamn Efternamnsson"

    ut = tradstruktur.maska_adressrad(rad)

    assert ut != rad
    assert "Efternamnsson" not in ut


def test_flera_mottagare_maskeras_var_for_sig():
    rad = "Anna Andersson <anna@ett.se>, Bo Berg <bo@tva.se>"

    ut = tradstruktur.maska_adressrad(rad)

    assert "Andersson" not in ut
    assert "Berg" not in ut
    assert "anna" not in ut
    assert ut.count("<") == 2


def test_verp_adress_lacker_inte_den_inkodade_adressen():
    """Lokaldelen kodar in en annan adress efter ett likhetstecken. Utan `=` i
    teckenklassen börjar matchningen efter det och lämnar resten i klartext."""
    rad = "<bounces+12-kalle=kundens-doman.se@sg.example.net>"

    ut = tradstruktur.maska_adressrad(rad)

    assert "kalle" not in ut
    assert "kundens-doman" not in ut


def test_telefonnummer_maskeras_i_bada_formaten():
    assert "123" not in tradstruktur.maska("ring 070-123 45 67")
    assert "123" not in tradstruktur.maska("ring +46 (0)8-123 45 67")


def test_regnummer_maskeras_oavsett_skiftlage():
    assert "[REGNR]" in tradstruktur.maska("bilen ABC123 står kvar")
    assert "[REGNR]" in tradstruktur.maska("bilen ABC 12D står kvar")
    assert "[REGNR]" in tradstruktur.maska("bilen abc12d står kvar")


def test_tom_adressrad_ger_ingen_krasch():
    assert tradstruktur.maska_adressrad("") == "[MASKERAD, 0 tecken]"


KUND = "kund@exempel.se"
BREVLADA = tradstruktur.BREVLADA


def meddelande(*, etiketter, huvuden, mottagare=KUND, mimetyp=None, amne=""):
    # Uppslagningen är skiftlägesokänslig, eftersom avsändare varierar mellan
    # `To` och `to` och hjälparen annars ger tomma mottagare för det gemena
    # fallet.
    varden = {"to": mottagare, "subject": amne}
    nyttolast = {
        "headers": [
            {"name": n, "value": varden.get(n.lower(), "")} for n in huvuden
        ]
    }
    if mimetyp:
        nyttolast["mimeType"] = mimetyp
    return {"labelIds": list(etiketter), "payload": nyttolast}


SVARSHUVUDEN = ["Content-Type", "Date", "From", "In-Reply-To", "MIME-Version",
                "Message-ID", "References", "Subject", "To"]
GMAIL_SVAR = {"etiketter": ["SENT"], "huvuden": SVARSHUVUDEN}
LEVERANS = ["Received", "Return-Path", "Delivered-To", "Received-SPF"]


def test_svar_skrivet_i_gmail_kanns_igen():
    assert tradstruktur.ar_gmail_svar(meddelande(**GMAIL_SVAR))


def test_meddelande_bara_till_brevladan_raknas_inte_som_svar():
    fwd = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                     mottagare=BREVLADA)

    assert not tradstruktur.ar_gmail_svar(fwd)


def test_vidarebefordran_raknas_inte_som_svar():
    """Bär In-Reply-To och References precis som ett svar, och saknar
    leveranshuvuden. Huvudena skiljer den inte från ett svar; prefixet gör det.
    Beslutslogg #5 utesluter kategorin."""
    for amne in ("Fwd: Offert", "VB: Offert", "fw: offert", "  FWD:  Offert"):
        fwd = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, amne=amne)

        assert not tradstruktur.ar_gmail_svar(fwd), amne


def test_svar_pa_vidarebefordrat_mail_raknas_som_svar():
    """`Re: Fwd: X` betyder att något vidarebefordrats TILL oss och att vi
    svarat. Det är ett äkta svar, och bara det yttersta prefixet avgör."""
    for amne in ("Re: Fwd: Offert", "SV: VB: Offert"):
        svar = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, amne=amne)

        assert tradstruktur.ar_gmail_svar(svar), amne


def test_svar_med_svarsprefix_raknas_som_svar():
    for amne in ("Re: Offert", "SV: Offert", "Ang: Offert", "Offert"):
        svar = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, amne=amne)

        assert tradstruktur.ar_gmail_svar(svar), amne


def test_svar_till_bade_kund_och_brevladan_raknas_som_svar():
    """Kopia till sig själv är vanligt och får inte diskvalificera svaret."""
    kopia = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                       mottagare=f"{KUND}, {BREVLADA}")

    assert tradstruktur.ar_gmail_svar(kopia)


def test_leveransrapport_raknas_inte_som_svar():
    """multipart/report avsänds från brevlådan och kan bära In-Reply-To utan
    att vara skriven av någon (beslutslogg #7)."""
    studs = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                       mimetyp="multipart/report")

    assert not tradstruktur.ar_gmail_svar(studs)


def test_formularnotis_ar_kundmeddelande_trots_sent():
    """Notisen bär kundens ärende och har kunden i Reply-To. Att kräva ett
    meddelande UTAN SENT uteslöt hela den här sortens par."""
    notis = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN + LEVERANS)

    assert tradstruktur.ar_kundmeddelande(notis)


def test_gmail_svar_ar_inte_kundmeddelande():
    assert not tradstruktur.ar_kundmeddelande(meddelande(**GMAIL_SVAR))


def test_inkommande_ar_kundmeddelande():
    inkommande = meddelande(etiketter=["INBOX"], huvuden=SVARSHUVUDEN)

    assert tradstruktur.ar_kundmeddelande(inkommande)


def test_formularnotis_med_sent_raknas_inte_som_svar():
    """Bär SENT men har passerat inkommande leverans, alltså Received och
    Return-Path. Skulle förgifta mallarna (beslutslogg #5)."""
    notis = meddelande(
        etiketter=["SENT"],
        huvuden=GMAIL_SVAR["huvuden"] + ["Received", "Return-Path",
                                         "Delivered-To", "Received-SPF"],
    )

    assert not tradstruktur.ar_gmail_svar(notis)


def test_forsta_utgaende_mailet_utan_forlaga_raknas_inte_som_svar():
    forsta = meddelande(
        etiketter=["SENT"],
        huvuden=["Content-Type", "Date", "From", "Message-ID", "Subject", "To"],
    )

    assert not tradstruktur.ar_gmail_svar(forsta)


def test_inkommande_meddelande_raknas_aldrig_som_svar():
    inkommande = dict(GMAIL_SVAR)
    assert not tradstruktur.ar_gmail_svar(
        meddelande(etiketter=["INBOX"], huvuden=inkommande["huvuden"])
    )


def test_meddelande_utan_labelids_kraschar_inte():
    utan = {"payload": {"headers": []}}

    assert not tradstruktur.ar_gmail_svar(utan)


def test_huvudnamnens_skiftlage_spelar_ingen_roll():
    """Avsändare varierar mellan Message-Id och Message-ID, och mellan versala
    och gemena huvudnamn. Jämförelsen ska vara skiftlägesokänslig."""
    gement = meddelande(
        etiketter=["SENT"],
        huvuden=["content-type", "date", "from", "IN-REPLY-TO", "mime-version",
                 "message-id", "REFERENCES", "subject", "to"],
    )

    assert tradstruktur.ar_gmail_svar(gement)


def test_svarsprefix_kanns_igen_men_amnet_slapps_aldrig_ut():
    traff = tradstruktur.SVARSPREFIX.match("Re: Offert ABC123 till Anna")

    assert traff is not None
    assert traff.group(0).strip() == "Re:"
