"""Tester för src/maskera.py och src/cluster.py.

All indata är påhittad. Testerna om maskering bär påståendet att persondata
INTE syns i utdatan, alltså den sort §7.1 kräver att man prövar genom att fälla
raden och se sviten bli röd.
"""

from __future__ import annotations

import json

import pytest

from src import cluster, maskera


# --- maskering av fritext ----------------------------------------------------


def test_epostadress_maskeras_i_fritext():
    ut = maskera.maska_fritext("hör av er till nagon@exempel.se tack")

    assert "nagon@exempel.se" not in ut
    assert "[EPOST]" in ut


def test_telefonnummer_maskeras_i_fritext():
    ut = maskera.maska_fritext("ring mig på 070-123 45 67")

    assert "123" not in ut
    assert "[SIFFROR]" in ut


def test_regnummer_maskeras_i_fritext():
    for regnr in ("ABC123", "ABC 12D", "abc12d"):
        ut = maskera.maska_fritext(f"bilen {regnr} behöver besiktigas")

        assert regnr not in ut, regnr
        assert "[REGNR]" in ut


def test_bar_doman_maskeras_i_fritext():
    """En domän utan protokoll matchas varken av EPOST eller URL, och kan vara
    ett efternamn. Utan det här mönstret överlevde en sådan som kategorinamn i
    en committad fil."""
    ut = maskera.maska_fritext("se efternamnsson.se för mer")

    assert "efternamnsson" not in ut
    assert "[DOMÄN]" in ut


def test_lank_maskeras_i_fritext():
    ut = maskera.maska_fritext("se https://exempel.se/sida?id=4 för mer")

    assert "exempel.se" not in ut
    assert "[LÄNK]" in ut


def test_namn_mitt_i_mening_maskeras():
    """Svenskan versaliserar inte vanliga substantiv, så ett versalt ord mitt i
    en mening är oftast ett egennamn."""
    ut = maskera.maska_fritext("jag heter Annika och undrar en sak")

    assert "Annika" not in ut
    assert "[NAMN]" in ut


def test_ord_vid_meningsstart_maskeras_ocksa():
    """Positionsundantaget är BORTTAGET. Det lät `Kund: Förnamn` och varje
    radbörjan i ett signaturblock passera, vilket gav persondata i en committad
    fil. Att `Bilen` nu maskeras är priset, och modulens doktrin är att
    övermaskering är ofarlig medan undermaskering är en §6-överträdelse."""
    ut = maskera.maska_fritext("Hej. Bilen behöver besiktigas.")

    assert ut == "Hej. [NAMN] behöver besiktigas."


def test_vanliga_versala_ord_maskeras_inte():
    ut = maskera.maska_fritext("det passar bra på Tisdag tycker Jag")

    assert "[NAMN]" not in ut


def test_tom_text_kraschar_inte():
    assert maskera.maska_fritext("") == ""


# --- adressrader -------------------------------------------------------------


def test_citerat_visningsnamn_med_komma_lacker_inte_efternamnet():
    ut = maskera.maska_adressrad('"Efternamnsson, Förnamn" <f@exempel.se>')

    assert "Efternamnsson" not in ut
    assert "Förnamn" not in ut


def test_oigenkannlig_adressrad_maskeras_helt():
    ut = maskera.maska_adressrad("Förnamn Efternamnsson")

    assert "Efternamnsson" not in ut
    assert "Förnamn" not in ut
    assert ut.startswith("[MASKERAD")


def test_verp_adress_lacker_inte_den_inkodade_adressen():
    """Återställd ur den borttagna test_tradstruktur.py. Vaktar `=` i EPOST:s
    teckenklass. En studsadress kodar in kundens adress efter ett
    likhetstecken, och utan `=` börjar matchningen efter det."""
    ut = maskera.maska_adressrad(
        "<bounces+12-kalle=kundens-doman.se@sg.example.net>"
    )

    assert "kalle" not in ut
    assert "kundens-doman" not in ut


def test_flera_mottagare_maskeras_var_for_sig():
    """Återställd. Vaktar sammanfogningsgrenen i maska_adressrad."""
    ut = maskera.maska_adressrad("Anna Andersson <anna@ett.se>, "
                                 "Bo Berg <bo@tva.se>")

    assert "Andersson" not in ut
    assert "Berg" not in ut
    assert "anna" not in ut
    assert ut.count("<") == 2


def test_tom_adressrad_ger_ingen_krasch():
    """Återställd. §4:s nollfall för adressraden."""
    assert maskera.maska_adressrad("") == "[MASKERAD, 0 tecken]"


def test_telefonnummer_maskeras_i_bada_formaten():
    """Återställd. Det internationella formatet testades inte längre."""
    assert "123" not in maskera.maska_fritext("ring 070-123 45 67")
    assert "123" not in maskera.maska_fritext("ring +46 (0)8-123 45 67")


def test_postnummer_och_kundnummer_maskeras():
    """Fem respektive fyra siffror stod i klartext när gränsen låg på sex."""
    assert "19252" not in maskera.maska_fritext("adressen är 19252 orten")
    assert "4711" not in maskera.maska_fritext("kundnummer 4711 hos oss")


def test_gatunamn_maskeras():
    for adress in ("Surbrunnsgatan", "Storvägen", "Lilltorget"):
        ut = maskera.maska_fritext(f"vi finns på {adress} nära dig")

        assert adress not in ut, adress


def test_namn_skrivet_med_versaler_maskeras():
    """En tidigare version krävde gemen svans och släppte igenom versala namn."""
    ut = maskera.maska_fritext("hälsningar från ANDERSSON på verkstaden")

    assert "ANDERSSON" not in ut


def test_namn_vid_meningsstart_maskeras_ocksa():
    """Positionsundantaget är borttaget: `Kund: Förnamn` och signaturblockens
    radbörjan gick annars ut i klartext i en committad fil."""
    assert "Tobias" not in maskera.maska_fritext("Kund: Tobias ringde")
    assert "Annika" not in maskera.maska_fritext("Hej.\nAnnika här")


def test_regnummer_med_bindestreck_maskeras():
    assert "ABC-123" not in maskera.maska_fritext("bilen ABC-123 står kvar")


# --- klustring ---------------------------------------------------------------


def test_namn_i_korpus_hittar_egennamn_i_gemen_form():
    namn = cluster.namn_i_korpus(["jag heter Annika och bor i Solna"])

    assert "annika" in namn
    assert "solna" in namn


def test_namn_utesluts_ur_etiketten():
    """Utan detta hamnade kundernas förnamn som KATEGORINAMN i en committad
    fil, vilket är en §6-överträdelse."""
    texter = ["besiktning av traktor hos Annika besiktning traktor"]
    namn = cluster.namn_i_korpus(texter)
    vektorer = cluster.tfidf([cluster.tokenisera(texter[0], namn)])

    etikett = cluster.etikett([0], vektorer, antal_ord=5)

    assert "annika" not in etikett
    assert "besiktning" in etikett


def test_massutskick_faller_bort_ur_klustringen(tmp_path):
    obesvarade = tmp_path / "obesvarade.jsonl"
    kropp = {"data": "ZnLDpWdhIG9tIHJlc2VydmRlbA=="}
    nyhetsbrev = {"messages": [{
        "labelIds": ["INBOX"],
        "payload": {"mimeType": "text/plain", "body": kropp,
                    "headers": [{"name": "List-Unsubscribe", "value": "<x>"}]},
    }]}
    kundmail = {"messages": [{
        "labelIds": ["INBOX"],
        "payload": {"mimeType": "text/plain", "body": kropp, "headers": []},
    }]}
    rader = [json.dumps(nyhetsbrev), json.dumps(kundmail)]
    obesvarade.write_text("\n".join(rader) + "\n", encoding="utf-8")

    dokument = cluster.las_kallor(tmp_path / "finns-ej", obesvarade)

    assert len(dokument) == 1


def test_stoppord_faller_bort_vid_tokenisering():
    assert cluster.tokenisera("hej och tack för att det") == []


def test_korta_ord_faller_bort():
    assert "ab" not in cluster.tokenisera("ab abc")


def test_likhet_ar_ett_for_identiska_vektorer():
    vektorer = cluster.tfidf([["besiktning", "traktor"], ["annat", "helt"]])

    assert cluster.likhet(vektorer[0], vektorer[0]) == pytest.approx(1.0)


def test_likhet_ar_noll_utan_gemensamma_ord():
    vektorer = cluster.tfidf([["besiktning"], ["reservdel"]])

    assert cluster.likhet(vektorer[0], vektorer[1]) == 0.0


def test_likartade_texter_hamnar_i_samma_kluster():
    dokument = [
        cluster.tokenisera("besiktning av traktor pris besiktning traktor"),
        cluster.tokenisera("besiktning traktor kostnad besiktning traktor"),
        cluster.tokenisera("reservdel bakljus lampa reservdel bakljus"),
    ]
    vektorer = cluster.tfidf(dokument)

    klustren = cluster.klustra(vektorer)

    tillhorighet = {}
    for nummer, klustret in enumerate(klustren):
        for index in klustret:
            tillhorighet[index] = nummer
    assert tillhorighet[0] == tillhorighet[1]
    assert tillhorighet[2] != tillhorighet[0]


def test_etiketten_kommer_ur_texterna_och_inte_ur_en_lista():
    dokument = [cluster.tokenisera("besiktning traktor besiktning traktor")]
    vektorer = cluster.tfidf(dokument)

    etikett = cluster.etikett([0], vektorer)

    assert "besiktning" in etikett
    assert "traktor" in etikett


def test_median_hanterar_jamnt_och_udda_antal():
    assert cluster._median([1, 2, 3]) == 2
    assert cluster._median([1, 2, 3, 4]) == 2
    assert cluster._median([]) is None


def test_exempel_maskeras_och_kortas():
    lang = "jag heter Annika och min bil ABC123 " + "text " * 100

    ut = cluster._exempel(lang)

    assert "Annika" not in ut
    assert "ABC123" not in ut
    assert len(ut) < 200


# --- källorna ----------------------------------------------------------------


def test_bada_kallorna_lases_och_markeras(tmp_path):
    parfil = tmp_path / "par.jsonl"
    parfil.write_text(json.dumps({
        "inkommande_text": "fråga om besiktning",
        "utgaende_text": "svar om besiktning",
        "tidsstampel": "", "avsandare_hash": "x",
    }) + "\n", encoding="utf-8")

    obesvarade = tmp_path / "obesvarade.jsonl"
    obesvarade.write_text(json.dumps({
        "messages": [{
            "labelIds": ["INBOX"],
            "payload": {
                "mimeType": "text/plain",
                "headers": [],
                "body": {"data": "ZnLDpWdhIG9tIHJlc2VydmRlbA=="},
            },
        }],
    }) + "\n", encoding="utf-8")

    dokument = cluster.las_kallor(parfil, obesvarade)

    assert [d["kalla"] for d in dokument] == ["med svar", "utan svar"]
    assert dokument[0]["svarslangd"] == len("svar om besiktning")
    assert dokument[1]["svarslangd"] is None


def test_samma_kundtext_raknas_en_gang_i_klustringen(tmp_path):
    """Ett kundmeddelande kan vara vänster sida i flera par när vi svarat två
    gånger. Paren är äkta, men i klustringen skulle texten blåsa upp sitt
    kluster."""
    parfil = tmp_path / "par.jsonl"
    poster = [
        {"inkommande_text": "fråga om besiktning", "utgaende_text": "kort",
         "tidsstampel": "", "avsandare_hash": "x"},
        {"inkommande_text": "fråga om besiktning",
         "utgaende_text": "ett längre svar", "tidsstampel": "",
         "avsandare_hash": "x"},
    ]
    parfil.write_text("\n".join(json.dumps(p) for p in poster) + "\n",
                      encoding="utf-8")

    dokument = cluster.las_kallor(parfil, tmp_path / "finns-ej")

    assert len(dokument) == 1
    assert dokument[0]["svarslangd"] == cluster._median([4, 15])


def test_saknad_kalla_ger_inget_fel(tmp_path):
    assert cluster.las_kallor(tmp_path / "finns-ej", tmp_path / "inte-här") == []


def test_rapporten_foreslar_ingen_hink(tmp_path):
    """Ramverksregel 2: ingen kategori flyttas till en hink av kod."""
    utfil = tmp_path / "kategorier-forslag.md"
    sammanstallning = [{
        "etikett": "besiktning, traktor", "antal": 9, "med_svar": 5,
        "utan_svar": 4, "median_svarslangd": 120, "exempel": ["ett exempel"],
    }]

    cluster.skriv_rapport(sammanstallning, utfil, 9)

    text = utfil.read_text(encoding="utf-8")
    assert "INGEN HINKTILLDELNING FÖRESLÅS" in text
    assert "`auto`" in text
    for hinkrad in ("hink: auto", "hink: utkast", "hink: aldrig"):
        assert hinkrad not in text


def test_sma_kluster_redovisas_samlat_och_inte_som_kategorier(tmp_path):
    utfil = tmp_path / "kategorier-forslag.md"
    sammanstallning = [
        {"etikett": "stor", "antal": 9, "med_svar": 9, "utan_svar": 0,
         "median_svarslangd": 100, "exempel": []},
        {"etikett": "liten", "antal": 1, "med_svar": 1, "utan_svar": 0,
         "median_svarslangd": 50, "exempel": []},
    ]

    cluster.skriv_rapport(sammanstallning, utfil, 10)

    text = utfil.read_text(encoding="utf-8")
    assert "### stor" in text
    assert "### liten" not in text
    assert "spridda ärenden" in text
