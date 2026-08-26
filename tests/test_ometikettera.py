"""Tester för src/ometikettera.py.

Ingen riktig API-nyckel och inget nätverk. Klienten är fejkad, och alla texter
är påhittade.
"""

from __future__ import annotations

import json

import pytest

from src import kategorisera, ometikettera
from tests.test_kategorisera import FejkKlient


def _post(etikett, kalla="med svar", text="text"):
    return {"text": text, "kalla": kalla, "etikett": etikett}


# --- urvalet -----------------------------------------------------------------


def test_inget_kundarende_och_oklart_etiketteras_inte_om():
    """Lars beslut i skiva 9. De är inte kundärenden, och en kundkategori på
    dem hade gjort korpusen större än den är."""
    poster = [_post("boka service"), _post("inget kundärende"),
              _post("oklart"), _post("fel")]

    kvar = ometikettera.akta_kundarenden(poster)

    assert [p["etikett"] for p in kvar] == ["boka service"]


def test_etikettraderna_bar_antal_och_storst_forst():
    """Pass 1 ska se hur tungt varje etikett väger. Utan antalen kan modellen
    inte skilja en kategori med tretton texter från en med en."""
    poster = [_post("boka rekond"), _post("boka rekond"), _post("boka tid")]

    rader = ometikettera.etikettrader(poster)

    assert rader == ["boka rekond (2)", "boka tid (1)"]


# --- pass 1: taxonomin -------------------------------------------------------


def test_taxonomin_avdubblas_och_behaller_ordningen():
    lista = ometikettera.las_taxonomi("boka service\nboka tid\nboka service\n")

    assert lista == ["boka service", "boka tid", "övrigt"]


def test_ovrigt_laggs_till_om_modellen_glomde_den():
    """Utan `övrigt` har pass 2 ingen tillåten utväg, och en text som inte
    passar trycks in i närmaste fel kategori."""
    lista = ometikettera.las_taxonomi("boka service\n")

    assert lista[-1] == "övrigt"


def test_ovrigt_dubbleras_inte_om_modellen_kom_ihag_den():
    lista = ometikettera.las_taxonomi("boka service\növrigt\n")

    assert lista.count("övrigt") == 1


def test_rad_som_inte_ar_en_kategori_slapps():
    """En förklarande mening normaliseras till `oklart` och är ingen kategori.
    Utan filtret hamnar modellens brödtext i taxonomin."""
    lang = ("här kommer listan över de kategorier som jag har slagit ihop "
            "efter att ha läst igenom hela materialet noggrant")

    lista = ometikettera.las_taxonomi(f"{lang}\nboka service\n")

    assert lista == ["boka service", "övrigt"]


def test_pass1_ar_ETT_anrop():
    """Ett anrop, hela listan. Blir det ett per etikett är konsolideringen
    meningslös: modellen ser då inte vilka namn som ska slås ihop."""
    klient = FejkKlient(["boka service\nboka tid"])

    ometikettera.konsolidera(klient, ["boka service (2)", "boka tid (1)"])

    assert len(klient.anrop) == 1


def test_pass1_far_se_alla_etiketter():
    klient = FejkKlient(["boka service"])

    ometikettera.konsolidera(klient, ["boka rekond (13)", "boka tid (2)"])

    skickat = klient.anrop[0]["messages"][0]["content"]
    assert "boka rekond (13)" in skickat
    assert "boka tid (2)" in skickat


# --- pass 2: enum ------------------------------------------------------------


def test_taxonomin_star_i_systemprompten():
    system = ometikettera.bygg_system_pass2(["boka service", "övrigt"])

    assert "- boka service" in system
    assert "- övrigt" in system


def test_svar_i_taxonomin_slapps_igenom():
    klient = FejkKlient(["boka service"])
    taxonomi = ["boka service", "övrigt"]

    namn = ometikettera.ometikettera_en(
        klient, "Hej", taxonomi, ometikettera.bygg_system_pass2(taxonomi)
    )

    assert namn == "boka service"


def test_svar_UTANFOR_taxonomin_rattas_inte_tyst():
    """§9.1: en fälld klassning är ett stopptecken, inte ett
    formuleringsproblem. Ett svar utanför listan räknas och redovisas, det
    tvingas aldrig in i närmaste kategori."""
    klient = FejkKlient(["boka helikoptertid"])
    taxonomi = ["boka service", "övrigt"]

    namn = ometikettera.ometikettera_en(
        klient, "Hej", taxonomi, ometikettera.bygg_system_pass2(taxonomi)
    )

    assert namn == ometikettera.UTANFOR


def test_ett_anrop_per_text_i_pass2():
    klient = FejkKlient(["boka service"])
    poster = [_post("gammal", text=f"text {i}") for i in range(4)]

    ometikettera.ometikettera_alla(klient, poster, ["boka service", "övrigt"],
                                   sov=lambda _: None, skriv=lambda _: None)

    assert len(klient.anrop) == 4


def test_fel_pa_en_text_stoppar_inte_resten():
    klient = FejkKlient(["boka service"], fel_pa=[1])
    poster = [_post("gammal", text=f"text {i}") for i in range(3)]

    ut = ometikettera.ometikettera_alla(
        klient, poster, ["boka service", "övrigt"],
        sov=lambda _: None, skriv=lambda _: None
    )

    assert [p["etikett"] for p in ut] == ["boka service", "fel", "boka service"]


# --- utfallet ----------------------------------------------------------------


def test_utanfor_listan_raknas_inte_som_kundkategori():
    """Den är en mätpunkt på taxonomins täckning, inte ett ärende som ska få
    en mall."""
    sammanstallning = [
        {"etikett": "boka service", "antal": 12, "med_svar": 12,
         "utan_svar": 0},
        {"etikett": ometikettera.UTANFOR, "antal": 40, "med_svar": 40,
         "utan_svar": 0},
        {"etikett": "inget kundärende", "antal": 547, "med_svar": 52,
         "utan_svar": 495},
    ]

    akta, fa_par = ometikettera.underlag_efter_konsolidering(sammanstallning)

    assert [k["etikett"] for k in akta] == ["boka service"]
    assert fa_par == []


def test_exakt_tio_par_racker_ocksa_efter_konsolidering():
    """Gränsvärdet. Tröskeln är FÄRRE ÄN tio, så tio räcker."""
    _, fa_par = ometikettera.underlag_efter_konsolidering(
        [{"etikett": "boka service", "antal": 10, "med_svar": 10,
          "utan_svar": 0}]
    )

    assert fa_par == []


def test_nio_par_racker_inte():
    _, fa_par = ometikettera.underlag_efter_konsolidering(
        [{"etikett": "boka service", "antal": 9, "med_svar": 9,
          "utan_svar": 0}]
    )

    assert [k["etikett"] for k in fa_par] == ["boka service"]


# --- rapporten ---------------------------------------------------------------


def test_rapporten_bar_taxonomin_och_tabellen(tmp_path):
    utfil = tmp_path / "kategorier.md"
    sammanstallning = [{"etikett": "boka service", "antal": 3, "med_svar": 2,
                        "utan_svar": 1, "exempel": []}]

    ometikettera.skriv_rapport(sammanstallning, utfil, 3,
                               ["boka service", "övrigt"], "modell-x")

    text = utfil.read_text(encoding="utf-8")
    assert "- boka service" in text
    assert "| boka service | 3 | 2 | 1 |" in text
    assert "src/ometikettera.py" in text


def test_rapporten_namner_ingen_hinktilldelning(tmp_path):
    """Ramverksregel 2: ingen kategori flyttas till en hink av kod. Filen får
    inte läsas som ett förslag på hinkar."""
    utfil = tmp_path / "kategorier.md"

    ometikettera.skriv_rapport([], utfil, 0, ["övrigt"], "modell-x")

    assert "INGEN HINKTILLDELNING" in utfil.read_text(encoding="utf-8")


def test_rapporten_skriver_bara_de_fyra_kolumnerna(tmp_path):
    """REGRESSIONSVAKT, inte spärrtest, och skillnaden ska stå här.

    `skriv_rapport` läser aldrig `rad['exempel']`. Testets påstående bärs alltså
    av FRÅNVARO av kod, och det finns ingen rad att fälla: den enda mutation som
    gör testet rött är ett TILLÄGG som börjar skriva ut exempel. §7-granskningen
    av skiva 9 fällde den tidigare lydelsen, som hette
    `test_rapporten_bar_inga_citat` och läste som ett spärrtest.

    Vakten är ändå värd att ha. Skulle någon lägga till ett exempelfält i
    rapporten går den röd, och §6 säger att citaten hör hemma i den
    gitignorerade exempelfilen och aldrig i `docs/`. Den spärr som faktiskt
    biter mot persondata är `scripts/persondatakontroll.py`, som vägrar
    committen, och den har egna test.
    """
    utfil = tmp_path / "kategorier.md"
    sammanstallning = [{"etikett": "boka service", "antal": 1, "med_svar": 1,
                        "utan_svar": 0,
                        "exempel": ["Hej, jag heter Kalle och bor på Storgatan"]}]

    ometikettera.skriv_rapport(sammanstallning, utfil, 1,
                               ["boka service"], "modell-x")

    text = utfil.read_text(encoding="utf-8")
    assert "Storgatan" not in text
    assert "Kalle" not in text


# --- läsningen ---------------------------------------------------------------


def test_kategorisvaren_lases_rad_for_rad(tmp_path):
    fil = tmp_path / "kategorisvar.jsonl"
    fil.write_text(
        json.dumps({"text": "a", "kalla": "med svar", "etikett": "boka tid"})
        + "\n\n"
        + json.dumps({"text": "b", "kalla": "utan svar", "etikett": "oklart"})
        + "\n",
        encoding="utf-8",
    )

    poster = ometikettera.las_kategorisvar(fil)

    assert [p["etikett"] for p in poster] == ["boka tid", "oklart"]


def test_systemprompten_i_pass2_bar_cachemarkoren():
    """DEL E. Pass 2:s systemprompt är identisk i alla anrop och är den som
    växer med taxonomin."""
    klient = FejkKlient(["boka service"])
    taxonomi = ["boka service", "övrigt"]

    ometikettera.ometikettera_en(
        klient, "Hej", taxonomi, ometikettera.bygg_system_pass2(taxonomi)
    )

    system = klient.anrop[0]["system"]
    assert system[0]["cache_control"] == {"type": "ephemeral"}
    assert "boka service" in system[0]["text"]


# --- a-traktorfiltret --------------------------------------------------------


def test_reparation_raknas_INTE_som_a_traktor():
    """`epa` är en substräng av `reparation`. Den första lydelsen använde
    `"epa" in etikett` och drog därför in `boka reparation` i a-traktortalet,
    som var skivans utfall. Prövningen går på ORD."""
    assert not ometikettera.ror_a_traktor("boka reparation")
    assert not ometikettera.ror_a_traktor("fråga om pris reparation")


def test_a_traktorkategorierna_kanns_igen():
    assert ometikettera.ror_a_traktor("boka a-traktorkonvertering")
    assert ometikettera.ror_a_traktor("fråga om a-traktorkonvertering")
    assert ometikettera.ror_a_traktor("fråga om pris a-traktorkonvertering")


def test_epa_som_eget_ord_raknas():
    """Kunderna säger både a-traktor och epa. Taxonomin kan bära endera."""
    assert ometikettera.ror_a_traktor("fråga om epa")
    assert ometikettera.ror_a_traktor("bygga om till epatraktor")


# --- etiketterna per text ----------------------------------------------------


def test_etiketterna_per_text_sparas(tmp_path):
    """Tabellen i `docs/` säger hur många par en kategori har, inte VILKA.
    Mallbygget i fas 5 behöver de senare, och utan filen kostar det 210 anrop
    att få fram dem igen."""
    utfil = tmp_path / "ometiketterade.jsonl"
    poster = [_post("boka service", text="Hej"),
              _post("övrigt", kalla="utan svar", text="Hejsan")]

    ometikettera.skriv_ometiketterade(poster, utfil)

    rader = [json.loads(r)
             for r in utfil.read_text(encoding="utf-8").splitlines() if r]
    assert [p["etikett"] for p in rader] == ["boka service", "övrigt"]
    assert rader[0]["text"] == "Hej"
    assert rader[1]["kalla"] == "utan svar"


def test_svenska_tecken_skrivs_inte_som_escape(tmp_path):
    """`ensure_ascii=False`. En fil full av \\u00e5 går inte att läsa vid
    felsökning, och nästa steg läser den här filen för hand."""
    utfil = tmp_path / "ometiketterade.jsonl"

    ometikettera.skriv_ometiketterade([_post("boka däckbyte")], utfil)

    assert "däckbyte" in utfil.read_text(encoding="utf-8")


# --- taxonomins golv och listprefix ------------------------------------------


def test_numrerad_lista_ger_anda_kategorier():
    """`SYSTEM_PASS1` förbjuder numrering, men en modell som ändå numrerar ska
    inte kosta 210 anrop. Utan avskalningen gav svaret nedan taxonomin
    `['övrigt']`, och pass 2 etiketterade hela korpusen som `övrigt`."""
    lista = ometikettera.las_taxonomi("1. boka service\n2. boka tid\n")

    assert lista == ["boka service", "boka tid", "övrigt"]


def test_punktad_lista_ger_anda_kategorier():
    lista = ometikettera.las_taxonomi("- boka service\n* boka tid\n")

    assert lista == ["boka service", "boka tid", "övrigt"]


def test_taxonomi_utan_kategorier_faller_korningen():
    """Golvet. En taxonomi som bara bär `övrigt` är ingen taxonomi, och felet
    ska kosta ETT anrop och inte tvåhundratio."""
    with pytest.raises(SystemExit) as fel:
        ometikettera.las_taxonomi("")

    assert "ingen användbar taxonomi" in str(fel.value)


def test_en_enda_riktig_kategori_racker():
    """Gränsvärdet. Golvet är två poster, och `övrigt` läggs alltid till, så en
    riktig kategori räcker."""
    assert ometikettera.las_taxonomi("boka service") == ["boka service",
                                                         "övrigt"]


# --- rapportens appendix -----------------------------------------------------


def test_rapporten_bar_ett_appendix(tmp_path):
    """§8: en ändring utan appendixpost är en ospårbar ändring. Filen är
    maskinproducerad, så appendixet skrivs av koden."""
    utfil = tmp_path / "kategorier.md"

    ometikettera.skriv_rapport([], utfil, 0, ["övrigt"], "modell-x")

    text = utfil.read_text(encoding="utf-8")
    assert "## Appendix — versionshistorik" in text
    assert "### 0.3.0" in text


def test_appendixet_behaller_de_aldre_posterna(tmp_path):
    """Skiva 9 höjde versionen och tog samtidigt bort hela historiken. Den
    återskapas genom att kopieras ur `196e60a`, aldrig ur minnet."""
    utfil = tmp_path / "kategorier.md"

    ometikettera.skriv_rapport([], utfil, 0, ["övrigt"], "modell-x")

    text = utfil.read_text(encoding="utf-8")
    assert "### 0.2.0 — 2026-08-26" in text
    assert "### 0.1.0 — 2026-08-26" in text
    assert "Se beslutslogg #9." in text
