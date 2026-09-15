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


# --- förbudslistan -----------------------------------------------------------


def test_forbjuden_doman_klassas_aldrig_som_maskin():
    """En förmedlad offertförfrågan är en KUND, och en domän som råkar skicka
    den maskinellt är fortfarande en kund. Beslut av Lars, skiva 8."""
    aldrig = frozenset({"bokadirekt.se", "autobutler.se"})
    undantag = frozenset({"support.autobutler.se"})

    assert klassa_maskin.ar_forbjuden("bokadirekt.se", aldrig, undantag)
    assert klassa_maskin.ar_forbjuden("autobutler.se", aldrig, undantag)


def test_subdoman_arver_skyddet():
    aldrig = frozenset({"bokadirekt.se"})

    assert klassa_maskin.ar_forbjuden(
        "transactional.bokadirekt.se", aldrig, frozenset()
    )


def test_undantaget_ar_mer_specifikt_och_provas_forst():
    """`support.autobutler.se` är en supportkanal, `autobutler.se` en
    kundkanal. Undantaget måste slå igenom subdomänregeln."""
    aldrig = frozenset({"autobutler.se"})
    undantag = frozenset({"support.autobutler.se"})

    assert not klassa_maskin.ar_forbjuden(
        "support.autobutler.se", aldrig, undantag
    )
    assert klassa_maskin.ar_forbjuden("autobutler.se", aldrig, undantag)


def test_liknande_doman_skyddas_inte_av_misstag():
    """`inte-bokadirekt.se` slutar på samma bokstäver men är en annan domän."""
    aldrig = frozenset({"bokadirekt.se"})

    assert not klassa_maskin.ar_forbjuden(
        "inte-bokadirekt.se", aldrig, frozenset()
    )


def test_tom_doman_ar_inte_forbjuden():
    """Fallet är verkligt, inte hypotetiskt: `las_forbjudna` bygger mängden med
    `d.strip().lower()`, så en YAML-post `- ""` lägger in tomma strängen i
    `aldrig`. Utan raden som fäller tom domän hade DÅ varje avsändare vars
    `From` saknar tolkbar domän blivit skyddad, och maskinklassningen hade
    slutat klassa.

    Den tidigare lydelsen skickade `aldrig={"x.se"}` och kunde därför inte bli
    röd: tomma strängen fanns ändå inte i mängden. §7-granskningen av skiva 8
    mätte upp det, och `docs/sparrar.md` bär fyndet."""
    assert not klassa_maskin.ar_forbjuden("", frozenset({""}), frozenset())


def test_forbudslistan_gar_fore_maskinhuvuden(tmp_path, monkeypatch):
    """Listan går FÖRE allt annat: även ett mail med List-Unsubscribe från en
    förbjuden domän är en kund."""
    fil = tmp_path / "forbjudna.yaml"
    fil.write_text("aldrig_maskin:\n  - bokadirekt.se\nundantag: []\n",
                   encoding="utf-8")
    monkeypatch.setattr(klassa_maskin, "FORBJUDNAFIL", fil)
    klassa_maskin.las_forbjudna.cache_clear()

    med = kundmail(**{"From": "Bokning <noreply@bokadirekt.se>",
                      "List-Unsubscribe": "<x>"})

    try:
        assert klassa_maskin.skal_maskinmail(med) == ""
    finally:
        klassa_maskin.las_forbjudna.cache_clear()


def test_harledningen_foreslar_aldrig_en_forbjuden_doman(tmp_path, monkeypatch):
    import json

    forbjudna = tmp_path / "forbjudna.yaml"
    forbjudna.write_text("aldrig_maskin:\n  - bokadirekt.se\nundantag: []\n",
                         encoding="utf-8")
    monkeypatch.setattr(klassa_maskin, "FORBJUDNAFIL", forbjudna)
    klassa_maskin.las_forbjudna.cache_clear()

    skord = tmp_path / "tradar.jsonl"
    tradar = [
        {"messages": [kundmail(**{"From": "A <a@bokadirekt.se>",
                                  "List-Unsubscribe": "<x>"})]},
        {"messages": [kundmail(**{"From": "B <b@utskickaren.se>",
                                  "List-Unsubscribe": "<x>"})]},
    ]
    skord.write_text("\n".join(json.dumps(t) for t in tradar) + "\n",
                     encoding="utf-8")

    try:
        assert klassa_maskin.harled_domaner([skord]) == ["utskickaren.se"]
    finally:
        klassa_maskin.las_forbjudna.cache_clear()


def test_den_riktiga_forbudslistan_bar_lars_beslut():
    """Filen är committad och dess innehåll är ett beslut, inte en härledning."""
    aldrig, undantag = klassa_maskin.las_forbjudna()

    assert {"bokadirekt.se", "autobutler.se", "hittabilverkstad.nu",
            "verkstadsdeal.se", "verkstadsoffert.se",
            "googlemail.com"} <= set(aldrig)
    assert "support.autobutler.se" in undantag


def test_bokadirekts_transaktionella_subdoman_ar_INTE_undantagen():
    """Undantaget lades in i skiva 50 och drogs tillbaka samma skiva.

    Subdomänen är inte bokadirekts transaktionella halva utan den som bär de
    FÖRMEDLADE FÖRFRÅGNINGARNA, alltså precis vad förbudslistan finns för.
    Avläst i `data/tradar_obesvarade.jsonl`: 60 trådar därifrån, 35 med fältet
    `Registreringsnummer`, medan `bokadirekt.se` har 19 och noll med fältet.

    Testet fäller om posten förs in igen utan att de talen prövats om."""
    aldrig, undantag = klassa_maskin.las_forbjudna()

    assert "transactional.bokadirekt.se" not in undantag
    assert klassa_maskin.ar_forbjuden(
        "transactional.bokadirekt.se", aldrig, undantag
    )


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


def test_den_riktiga_domanlistan_bar_lars_beslut():
    """Lars §10-beslut, skiva 50. Filen stod tom dessförinnan.

    De tre domänerna i den andra prövningen stod i SAMMA avläsning ur dagens
    post och fördes medvetet inte över: `gmail.com` och `google.com` är
    konsument- respektive Googles egen domän, och `melias.se` bär mänsklig
    post."""
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)

    assert {"mekonomen.se", "hedbergsbilskrot.se", "sunmaskin.se",
            "ekvallautoteknik.se", "email.tele2.se",
            "epostsystem.se"} <= domaner
    assert not ({"gmail.com", "google.com", "melias.se"} & domaner)


def test_bildelsbasen_ar_INTE_en_maskindoman():
    """DOMÄNEN STOD I LISTAN OCH ÄR STRUKEN, Lars §10-beslut, skiva 50.

    Över de tre materialen bär `bildelsbasen.se` 49 trådar, och 32 av dem hade
    flyttat in i maskinmail. EN av de 32, i `data/tradar.jsonl`, har ett
    mänskligt svar från verkstaden: sju meddelanden, varav två svar från oss på
    tillsammans 69 ord, inga maskinhuvuden och ingen `Reply-To`. Den räddas
    alltså inte av `relayar_manniska`, och raden gjorde den sortens tråd tyst.
    De sex domäner som står kvar bär noll sådana trådar.

    Testet fäller om raden förs tillbaka utan ett nytt §10-beslut."""
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)

    assert "bildelsbasen.se" not in domaner


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


def test_formularnotisen_overlever_att_dess_doman_star_i_maskindomaner():
    """DOMÄNLAGRET ÄR SIST OCH NÅR ALDRIG EN FORMULÄRNOTIS.

    Skiva 50 fyllde `config/maskindomaner.yaml` för första gången. Notisen
    skickas från VÅR EGEN domän, och skulle någon dag en domän som bär
    formulärpost föras in i listan får det inte fälla notisen: `relayar_manniska`
    prövas FÖRE domänlagret och räddar den.

    Prövningen är på den beslutande ordningen och inte på att vår egen domän
    råkar stå utanför listan i dag. Utan ordningen hade den ena posten i
    konfigurationen kunnat stänga den kanal som aldrig får brytas."""
    egen = BREVLADA.partition("@")[2]
    notis = meddelande(huvuden={
        "From": f"Auto Stockholm <{BREVLADA}>",
        "To": BREVLADA,
        "Reply-To": f"Kund <{KUND}>",
        "X-Msg-EID": "abc123",
    })

    assert klassa_maskin.skal_maskinmail(notis, {egen}) == ""


def test_undantagen_doman_som_relayar_en_manniska_ar_fortfarande_manniska():
    """ETT UNDANTAG TAR BORT SKYDDET, INTE MER.

    `relayar_manniska` prövas EFTER förbudslistan och FÖRE huvudlagret, alltså
    bär den fortfarande en förmedlad förfrågan från en undantagen domän.

    Avsändaren är den riktiga filens enda undantag, `support.autobutler.se`."""
    forfragan = meddelande(huvuden={
        "From": "Support <noreply@support.autobutler.se>",
        "To": BREVLADA,
        "Reply-To": f"Kund <{KUND}>",
        "List-Unsubscribe": "<x>",
    })
    # Negativkontroll: utan reläet fäller huvudlagret samma avsändare, alltså
    # är det reläet och inte något annat som bär den första prövningen.
    utan_rela = meddelande(huvuden={
        "From": "Support <noreply@support.autobutler.se>",
        "To": BREVLADA,
        "List-Unsubscribe": "<x>",
    })

    assert klassa_maskin.skal_maskinmail(forfragan) == ""
    assert klassa_maskin.skal_maskinmail(utan_rela).startswith("huvud:")


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
