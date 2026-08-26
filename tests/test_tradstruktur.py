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


def meddelande(*, etiketter, huvuden):
    return {
        "labelIds": list(etiketter),
        "payload": {"headers": [{"name": n, "value": ""} for n in huvuden]},
    }


GMAIL_SVAR = {
    "etiketter": ["SENT"],
    "huvuden": ["Content-Type", "Date", "From", "In-Reply-To", "MIME-Version",
                "Message-ID", "References", "Subject", "To"],
}


def test_svar_skrivet_i_gmail_kanns_igen():
    assert tradstruktur.ar_gmail_svar(meddelande(**GMAIL_SVAR))


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
