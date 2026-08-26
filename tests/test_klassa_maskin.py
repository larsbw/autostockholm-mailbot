"""Tester för src/klassa_maskin.py.

All indata är påhittad. Spärren `klassning-maskinmail` har fyra lager plus ett
UNDANTAG, och undantaget är det farligaste att tappa: utan det klassas
webbformulärets notiser som maskinmail och det mest värdefulla kundmaterialet
kastas.
"""

from __future__ import annotations

from src import klassa_maskin, urval

KUND = "kund@exempel.se"
BREVLADA = urval.BREVLADA


def meddelande(*, huvuden: dict, etiketter=("INBOX",)):
    return {
        "labelIds": list(etiketter),
        "payload": {"headers": [{"name": n, "value": v}
                                for n, v in huvuden.items()]},
    }


def kundmail(**extra):
    huvuden = {"From": f"Namn <{KUND}>", "To": BREVLADA, "Subject": "Fråga"}
    huvuden.update(extra)
    return meddelande(huvuden=huvuden)


# --- lager för lager ---------------------------------------------------------


def test_vanligt_kundmail_ar_inte_maskinmail():
    """Negativkontroll: spärren SLÄPPER IGENOM en människa."""
    assert klassa_maskin.skal_maskinmail(kundmail()) == ""


def test_lager_list_unsubscribe():
    skal = klassa_maskin.skal_maskinmail(kundmail(**{"List-Unsubscribe": "<x>"}))

    assert skal.startswith("huvud:")


def test_lager_auto_submitted():
    assert klassa_maskin.skal_maskinmail(
        kundmail(**{"Auto-Submitted": "auto-generated"})
    ).startswith("huvud:")


def test_lager_x_auto_response_suppress():
    assert klassa_maskin.skal_maskinmail(
        kundmail(**{"X-Auto-Response-Suppress": "All"})
    ).startswith("huvud:")


def test_lager_precedence_bulk():
    assert klassa_maskin.skal_maskinmail(
        kundmail(Precedence="bulk")
    ).startswith("precedence:")


def test_precedence_normal_ar_inte_maskinmail():
    """`Precedence: normal` betyder inte utskick och får inte fälla."""
    assert klassa_maskin.skal_maskinmail(kundmail(Precedence="normal")) == ""


def test_lager_noreply_avsandare():
    for lokal in ("noreply", "no-reply", "donotreply", "do_not_reply",
                  "bounces", "mailer-daemon", "nyhetsbrev"):
        med = kundmail(**{"From": f"Avs <{lokal}@nagon.se>"})

        assert klassa_maskin.skal_maskinmail(med).startswith("avsändare:"), lokal


def test_avsandare_som_bara_borjar_pa_no_ar_inte_noreply():
    """`nora@` och `notarie@` är människor. Mönstret är förankrat."""
    for lokal in ("nora", "notarie", "norea"):
        med = kundmail(**{"From": f"Namn <{lokal}@nagon.se>"})

        assert klassa_maskin.skal_maskinmail(med) == "", lokal


def test_lager_doman_ur_konfigurationen():
    med = kundmail(**{"From": "Utskick <info@utskickaren.se>"})

    assert klassa_maskin.skal_maskinmail(med, {"utskickaren.se"}).startswith(
        "domän:"
    )


def test_doman_utanfor_listan_faller_inte():
    med = kundmail(**{"From": f"Namn <{KUND}>"})

    assert klassa_maskin.skal_maskinmail(med, {"utskickaren.se"}) == ""


# --- undantaget --------------------------------------------------------------


def test_formularnotis_klassas_som_manniska_trots_maskinhuvuden():
    """Notisen är maskinSKICKAD men människoSKRIVEN. Utan undantaget föll 288
    av 555 besvarade trådar som maskinmail."""
    notis = meddelande(huvuden={
        "From": f"Auto Stockholm <{BREVLADA}>",
        "To": BREVLADA,
        "Reply-To": f"Kund <{KUND}>",
        "X-Msg-EID": "abc123",
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(notis) == ""


def test_nyhetsbrev_med_reply_to_till_sig_sjalvt_ar_fortfarande_maskinmail():
    """Undantaget får inte vara så brett att varje utskick slipper igenom."""
    brev = meddelande(huvuden={
        "From": "Utskick <info@utskickaren.se>",
        "Reply-To": "Utskick <info@utskickaren.se>",
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(brev).startswith("huvud:")


def test_nyhetsbrev_fran_subdoman_ar_inte_relay():
    """Jämförelsen sker på ORGANISATIONSDOMÄN. Med exakt strängmatchning såg
    `From: news@news.exempel.se` med `Reply-To: kundservice@exempel.se` ut som
    ett relä och slapp igenom alla fyra lager."""
    brev = meddelande(huvuden={
        "From": "Nyheter <news@news.exempel.se>",
        "Reply-To": "Kundservice <kundservice@exempel.se>",
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(brev).startswith("huvud:")


def test_organisationsdoman_slar_ihop_subdomaner():
    assert (klassa_maskin.organisationsdoman("a@news.exempel.se")
            == klassa_maskin.organisationsdoman("b@exempel.se"))
    assert (klassa_maskin.organisationsdoman("a@mail.exempel.co.uk")
            == "exempel.co.uk")
    assert (klassa_maskin.organisationsdoman("a@exempel.se")
            != klassa_maskin.organisationsdoman("b@annat.se"))


def test_reply_to_pa_avsandarens_egen_doman_ar_inte_relay():
    brev = meddelande(huvuden={
        "From": "Utskick <noreply@utskickaren.se>",
        "Reply-To": "Support <support@utskickaren.se>",
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(brev).startswith("huvud:")


def test_reply_to_till_brevladan_ar_inte_relay():
    brev = meddelande(huvuden={
        "From": "Utskick <info@utskickaren.se>",
        "Reply-To": BREVLADA,
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(brev).startswith("huvud:")


# --- trådnivå ----------------------------------------------------------------


def test_tradens_skal_ser_forsta_inkommande_och_inte_vart_svar():
    """Vårt eget svar är aldrig maskinmail och får inte dra tråden åt fel håll."""
    vart_svar = {"labelIds": ["SENT"], "payload": {"headers": [
        {"name": "In-Reply-To", "value": "x"},
        {"name": "References", "value": "x"},
        {"name": "To", "value": KUND},
        {"name": "From", "value": BREVLADA},
        {"name": "Subject", "value": "Re: Fråga"},
    ]}}
    trad = {"messages": [kundmail(**{"List-Unsubscribe": "<x>"}), vart_svar]}

    assert klassa_maskin.tradens_skal(trad).startswith("huvud:")


def test_trad_utan_kundmeddelande_ger_tomt_skal():
    assert klassa_maskin.tradens_skal({"messages": []}) == ""


# --- domänhärledning ---------------------------------------------------------


def test_doman_harleds_bara_nar_all_post_darifran_ar_deklarerad(tmp_path):
    """En domän som också skickat ett odeklarerat mail lämnas utanför: den kan
    bära både utskick och en människa, och att klassa den som maskin hade
    kastat kundens post."""
    import json

    fil = tmp_path / "tradar.jsonl"
    tradar = [
        {"messages": [kundmail(**{"From": "A <a@bara-utskick.se>",
                                  "List-Unsubscribe": "<x>"})]},
        {"messages": [kundmail(**{"From": "B <b@blandad.se>",
                                  "List-Unsubscribe": "<x>"})]},
        {"messages": [kundmail(**{"From": "C <c@blandad.se>"})]},
    ]
    fil.write_text("\n".join(json.dumps(t) for t in tradar) + "\n",
                   encoding="utf-8")

    domaner = klassa_maskin.harled_domaner([fil])

    assert domaner == ["bara-utskick.se"]


def test_domanfilen_bar_bara_domaner_aldrig_adresser(tmp_path):
    """§6: en domän är inte persondata, men en lokaldel kan vara det."""
    fil = tmp_path / "maskindomaner.yaml"

    klassa_maskin.skriv_domaner(["utskickaren.se"], fil)

    text = fil.read_text(encoding="utf-8")
    assert "utskickaren.se" in text
    assert "@" not in text.split("maskindomaner:")[1]


def test_las_domaner_utan_fil_ger_tom_mangd(tmp_path):
    assert klassa_maskin.las_domaner(tmp_path / "finns-ej") == set()
