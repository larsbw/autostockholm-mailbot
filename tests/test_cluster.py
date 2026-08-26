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


def test_ord_vid_meningsstart_maskeras_inte():
    ut = maskera.maska_fritext("Hej. Bilen behöver besiktigas.")

    assert ut == "Hej. Bilen behöver besiktigas."


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
    assert ut.startswith("[MASKERAD")


# --- klustring ---------------------------------------------------------------


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
