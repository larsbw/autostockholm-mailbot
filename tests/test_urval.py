"""Tester för urvalsvillkoren i src/urval.py.

Spärren heter `urval-gmail-svar` och står i docs/sparrar.md. Den har sex lager
som INTE är redundanta med varandra: varje lager vaktar en egen sorts felaktig
text. Ett fällt lager syns som ett rött test, ett SAKNAT lager syns inte alls.
Därför har varje lager ett eget test här.

All indata är påhittad.
"""

from __future__ import annotations

from src import urval

KUND = "kund@exempel.se"
BREVLADA = urval.BREVLADA

SVARSHUVUDEN = ["Content-Type", "Date", "From", "In-Reply-To", "MIME-Version",
                "Message-ID", "References", "Subject", "To"]
LEVERANS = ["Received", "Return-Path", "Delivered-To", "Received-SPF"]


def meddelande(*, etiketter, huvuden, mottagare=KUND, mimetyp=None, amne=""):
    varden = {"to": mottagare, "subject": amne}
    nyttolast = {
        "headers": [{"name": n, "value": varden.get(n.lower(), "")}
                    for n in huvuden]
    }
    if mimetyp:
        nyttolast["mimeType"] = mimetyp
    return {"labelIds": list(etiketter), "payload": nyttolast}


GMAIL_SVAR = {"etiketter": ["SENT"], "huvuden": SVARSHUVUDEN}


# --- lager för lager ---------------------------------------------------------


def test_svar_skrivet_i_gmail_kanns_igen():
    """Negativkontroll: spärren SLÄPPER IGENOM ett äkta svar."""
    assert urval.ar_gmail_svar(meddelande(**GMAIL_SVAR))


def test_lager_sent_inkommande_raknas_aldrig_som_svar():
    assert not urval.ar_gmail_svar(
        meddelande(etiketter=["INBOX"], huvuden=SVARSHUVUDEN)
    )


def test_lager_leveranshuvuden_formularnotis_raknas_inte_som_svar():
    """Bär SENT men har passerat inkommande leverans (beslutslogg #5)."""
    notis = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN + LEVERANS)

    assert not urval.ar_gmail_svar(notis)


def test_lager_svarshuvuden_forsta_utgaende_raknas_inte_som_svar():
    forsta = meddelande(
        etiketter=["SENT"],
        huvuden=["Content-Type", "Date", "From", "Message-ID", "Subject", "To"],
    )

    assert not urval.ar_gmail_svar(forsta)


def test_lager_report_leveransrapport_raknas_inte_som_svar():
    """multipart/report avsänds från brevlådan och kan bära In-Reply-To utan
    att vara skriven av någon (beslutslogg #7)."""
    studs = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                       mimetyp="multipart/report")

    assert not urval.ar_gmail_svar(studs)


def test_lager_mottagare_bara_till_brevladan_raknas_inte_som_svar():
    assert not urval.ar_gmail_svar(
        meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                   mottagare=BREVLADA)
    )


def test_lager_prefix_vidarebefordran_raknas_inte_som_svar():
    for amne in ("Fwd: Offert", "VB: Offert", "fw: offert", "  FWD:  Offert"):
        fwd = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, amne=amne)

        assert not urval.ar_gmail_svar(fwd), amne


# --- gränsfall ---------------------------------------------------------------


def test_svar_pa_vidarebefordrat_mail_raknas_som_svar():
    """`Re: Fwd: X` betyder att något vidarebefordrats TILL oss och att vi
    svarat. Bara det yttersta prefixet avgör."""
    for amne in ("Re: Fwd: Offert", "SV: VB: Offert"):
        svar = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, amne=amne)

        assert urval.ar_gmail_svar(svar), amne


def test_kopia_till_sig_sjalv_diskvalificerar_inte_svaret():
    kopia = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN,
                       mottagare=f"{KUND}, {BREVLADA}")

    assert urval.ar_gmail_svar(kopia)


def test_huvudnamnens_skiftlage_spelar_ingen_roll():
    """Avsändare varierar mellan Message-Id och Message-ID (beslutslogg #6)."""
    gement = meddelande(
        etiketter=["SENT"],
        huvuden=["content-type", "date", "from", "IN-REPLY-TO", "mime-version",
                 "message-id", "REFERENCES", "subject", "to"],
    )

    assert urval.ar_gmail_svar(gement)


def test_meddelande_utan_labelids_kraschar_inte():
    """Beslutslogg #6: äldre meddelanden saknar nyckeln helt."""
    utan = {"payload": {"headers": []}}

    assert not urval.ar_gmail_svar(utan)
    assert urval.ar_kundmeddelande(utan)


# --- kundsidan ---------------------------------------------------------------


def test_inkommande_ar_kundmeddelande():
    assert urval.ar_kundmeddelande(
        meddelande(etiketter=["INBOX"], huvuden=SVARSHUVUDEN)
    )


def test_formularnotis_ar_kundmeddelande_trots_sent():
    """Beslutslogg #8: notisen bär kundens ärende. Att kräva frånvaro av SENT
    uteslöt hela den sortens par."""
    notis = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN + LEVERANS)

    assert urval.ar_kundmeddelande(notis)


def test_gmail_svar_ar_inte_kundmeddelande():
    assert not urval.ar_kundmeddelande(meddelande(**GMAIL_SVAR))


# --- huvuduppslag ------------------------------------------------------------


def test_huvudvarde_ar_skiftlagesokansligt():
    med = meddelande(etiketter=["SENT"], huvuden=["subject"], amne="Offert")

    assert urval.huvudvarde(med, "Subject") == "Offert"


def test_huvudvarde_utan_traff_ger_tom_strang():
    assert urval.huvudvarde(meddelande(**GMAIL_SVAR), "X-Finns-Inte") == ""
