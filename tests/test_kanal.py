"""Tester för src/kanal.py och för kontexten i klassificeringen.

Ingen riktig API-nyckel och inget nätverk. Klienten är fejkad, och alla texter,
ämnesrader och adresser är påhittade.

KÄRNAN I FILEN är negativkontrollen: kanalen får vara en bekräftande signal och
aldrig ensam grund. Det prövas genom att låta modellen svara med en kategori som
går emot kanalen och kontrollera att svaret står kvar orört. Går den prövningen
inte igenom har koden en kanal-till-kategori-koppling, vilket är förbjudet.
"""

from __future__ import annotations

import base64
import json

from src import kanal, kategorisera, ometikettera
from tests.test_kategorisera import FejkKlient


def meddelande(amne: str, kropp: str = "Hej") -> dict:
    """Ett meddelande i Gmail-API:ts form, med kroppen base64url-kodad."""
    data = base64.urlsafe_b64encode(kropp.encode("utf-8")).decode("ascii")
    return {
        "labelIds": ["INBOX"],
        "payload": {
            "headers": [{"name": "Subject", "value": amne},
                        {"name": "From", "value": "kund@exempel.se"}],
            "mimeType": "text/plain",
            "body": {"data": data},
        },
    }


FORMULARAMNE = "Ny offertförfrågan A-traktor"


# --- kanalen -----------------------------------------------------------------


def test_formularets_amnesrad_kanns_igen():
    assert kanal.ar_webbformular(meddelande(FORMULARAMNE))


def test_prövningen_ar_skiftlagesokanslig():
    """Ämnesraden sätts av formuläret, men skiftläget är inget att lita på."""
    assert kanal.ar_webbformular(meddelande("NY OFFERTFÖRFRÅGAN A-TRAKTOR"))
    assert kanal.ar_webbformular(meddelande("ny offertförfrågan a-traktor"))


def test_vanligt_kundmail_har_ingen_kanal():
    """NOLLFALLET. `None` betyder VET INTE och aldrig en påhittad kanal."""
    assert kanal.namnge(meddelande("Fråga om pris")) is None


def test_tom_amnesrad_ger_ingen_kanal():
    """Nollfall: mailet utan ämnesrad."""
    assert kanal.namnge(meddelande("")) is None


def test_saknad_amnesrad_kraschar_inte():
    """Kantfall: huvudet finns inte alls."""
    utan = {"payload": {"headers": [], "body": {"data": ""}}}
    assert kanal.amnesrad(utan) == ""
    assert kanal.namnge(utan) is None


def test_mimekodad_amnesrad_avkodas():
    """En kodad ämnesrad ser ut som `=?UTF-8?B?...?=` i råhuvudet.

    Utan avkodning missas varje ämnesrad med svenska tecken, alltså precis
    formulärets.
    """
    kodad = base64.b64encode(FORMULARAMNE.encode("utf-8")).decode("ascii")
    m = meddelande(f"=?UTF-8?B?{kodad}?=")
    assert kanal.amnesrad(m) == FORMULARAMNE
    assert kanal.ar_webbformular(m)


def test_trasig_mimekodning_ger_ravardet_inte_ett_undantag(monkeypatch):
    """Docstringens löfte: en trasig ämnesrad kostar inte klassificeringen.

    Faller avkodningen ska råvärdet komma tillbaka. Utan det hade ett enda
    felformat huvud tagit ner hela körningen mot brevlådan.
    """
    def faller(_):
        raise ValueError("trasig kodning")

    monkeypatch.setattr(kanal, "decode_header", faller)

    assert kanal.amnesrad(meddelande("Fråga om pris")) == "Fråga om pris"
    assert kanal.namnge(meddelande("Fråga om pris")) is None


def test_formularet_namnges_med_vad_det_ar():
    """Namnet ska säga att formuläret gäller a-traktor.

    Det är den upplysning klassificeraren saknade. Ett namn som bara sade
    `webbformulär` hade inte tillfört något.
    """
    assert "a-traktor" in kanal.namnge(meddelande(FORMULARAMNE)).lower()


# --- kontexten i användarmeddelandet -----------------------------------------


def test_utan_kontext_ar_meddelandet_oforandrat():
    """Ingen kontext ⇒ ANVÄNDARMEDDELANDET är oförändrat.

    Anropet i sin helhet är det inte: systemprompten bär `KONTEXTREGEL` även
    när blocket saknas, se `test_kontextregeln_laggs_till_aven_utan_kontext`.
    """
    assert kategorisera.bygg_anvandarmeddelande("Hej") == "Hej"


def test_kontextregeln_laggs_till_aven_utan_kontext():
    """KONTEXTREGEL finns i systemprompten också när blocket saknas.

    Regeln läggs till ovillkorligt. Två olika systemprompter hade gjort
    klassningen beroende av om kontexten råkade gå att fastställa, och det är
    en skillnad ingen skulle se i utfallet.
    """
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(klient, "Hej")

    assert kategorisera.KONTEXTREGEL in klient.anrop[0]["system"][0]["text"]


def test_systemprompten_ar_identisk_med_och_utan_kontext():
    """Jämförelsen som namnet på testet ovan inte gör."""
    utan = FejkKlient(["boka tid"])
    med = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(utan, "Hej")
    kategorisera.kategorisera_en(med, "Hej", amne=FORMULARAMNE,
                                 kanal=kanal.WEBBFORMULAR)

    assert utan.anrop[0]["system"] == med.anrop[0]["system"]


def test_kontextblocket_bar_kanal_och_amne():
    ut = kategorisera.bygg_anvandarmeddelande(
        "Vill boka", amne="Ny offertförfrågan A-traktor",
        kanal=kanal.WEBBFORMULAR)

    assert kategorisera.KONTEXT_START in ut
    assert kategorisera.KONTEXT_SLUT in ut
    assert kanal.WEBBFORMULAR in ut
    assert "Ny offertförfrågan A-traktor" in ut
    assert ut.endswith("Vill boka")


def test_trunkeringen_galler_texten_inte_summan():
    """GRÄNSVÄRDET. Ett långt kontextblock får inte äta av kundens ord.

    Kontexten läggs till EFTER trunkeringen, så texten behåller hela sitt tak
    oavsett hur lång ämnesraden är.
    """
    lang = "x" * (kategorisera.MAX_TECKEN + 500)
    ut = kategorisera.bygg_anvandarmeddelande(
        lang, amne="a" * 400, kanal=kanal.WEBBFORMULAR)

    assert ut.count("x") == kategorisera.MAX_TECKEN


def test_bara_amne_utan_kanal_ger_kontext():
    ut = kategorisera.bygg_anvandarmeddelande("Hej", amne="Fråga om pris")
    assert "Fråga om pris" in ut
    assert "Kanal:" not in ut


def test_tomt_amne_ger_ingen_amnesrad_i_blocket():
    """Nollfall: ämnesraden finns men är tom."""
    ut = kategorisera.bygg_anvandarmeddelande(
        "Hej", amne="   ", kanal=kanal.WEBBFORMULAR)
    assert "Ämnesrad:" not in ut
    assert kanal.WEBBFORMULAR in ut


def test_systemprompten_bar_kontextregeln():
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(klient, "Hej", kanal=kanal.WEBBFORMULAR)

    system = klient.anrop[0]["system"][0]["text"]
    assert "BEKRÄFTANDE SIGNAL" in system
    assert "aldrig ensam avgöra" in system
    assert "följ TEXTEN" in system


def test_kontexten_nar_fram_till_anropet():
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(
        klient, "Hej", amne=FORMULARAMNE, kanal=kanal.WEBBFORMULAR)

    skickat = klient.anrop[0]["messages"][0]["content"]
    assert kanal.WEBBFORMULAR in skickat
    assert FORMULARAMNE in skickat


def test_kategorisera_alla_skickar_postens_kontext():
    klient = FejkKlient(["boka tid"])
    poster = [{"text": "Hej", "kalla": "utan svar",
               "amne": FORMULARAMNE, "kanal": kanal.WEBBFORMULAR}]

    kategorisera.kategorisera_alla(klient, poster, sov=lambda _: None)

    assert kanal.WEBBFORMULAR in klient.anrop[0]["messages"][0]["content"]


def test_post_utan_kontextnycklar_fungerar():
    """Bakåtkompatibilitet: en post från före skiva 17 saknar nycklarna."""
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_alla(klient, [{"text": "Hej", "kalla": "utan svar"}],
                                   sov=lambda _: None)

    assert klient.anrop[0]["messages"][0]["content"] == "Hej"


# --- kontext_per_text: den besvarade sidans kanal -----------------------------
#
# `data/par.jsonl` bär ingen ämnesrad, så kontexten slås upp ur trådfilen på
# TEXTEN. Funktionen styr därmed vilken kanal varje besvarad kundtext får, och
# den var helt otestad när skiva 17 först lämnades till granskning.


def trad(*meddelanden: dict) -> str:
    return json.dumps({"messages": list(meddelanden)}, ensure_ascii=False)


def skriv_tradfil(sokvag, *rader: str):
    sokvag.write_text("\n".join(rader) + "\n", encoding="utf-8")
    return sokvag


def test_kontext_per_text_ger_kanal_och_amne(tmp_path):
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande(FORMULARAMNE, "Vill bygga om")))

    ut = kategorisera.kontext_per_text(fil)

    assert ut["Vill bygga om"] == {"amne": FORMULARAMNE,
                                   "kanal": kanal.WEBBFORMULAR}


def test_kontext_per_text_ger_none_som_kanal_for_vanligt_mail(tmp_path):
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande("Fråga om pris", "Vad kostar det")))

    assert kategorisera.kontext_per_text(fil)["Vad kostar det"]["kanal"] is None


def test_kontext_per_text_indexerar_varje_kundmeddelande(tmp_path):
    """INTE bara trådens första.

    `src/extract.py::par_ur_trad` parar ett svar med `senaste_kund`, alltså med
    kundmeddelandet närmast före svaret. En par-text kan därför komma från
    vilken position som helst i tråden.
    """
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande(FORMULARAMNE, "Först"),
                             meddelande(FORMULARAMNE, "Sedan")))

    ut = kategorisera.kontext_per_text(fil)

    assert "Först" in ut
    assert "Sedan" in ut


def test_motstridig_kontext_ger_ingen_kontext_alls(tmp_path):
    """VET INTE är svaret, aldrig en gissning.

    Samma text i två trådar med olika ämnesrad. Utan den här vakten hade texten
    fått den ena trådens kanal, och vilken hade avgjorts av läsordningen.
    """
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande(FORMULARAMNE, "Samma text")),
                        trad(meddelande("Fråga om pris", "Samma text")))

    assert "Samma text" not in kategorisera.kontext_per_text(fil)


def test_kollision_mellan_olika_positioner_upptacks(tmp_path):
    """GRÄNSVÄRDET som ett förstameddelande-index hade missat.

    Texten ligger på position två i den ena tråden och position ett i den
    andra. Ett index byggt på enbart förstameddelanden hade inte sett
    konflikten och gett texten den andra trådens kanal.
    """
    fil = skriv_tradfil(
        tmp_path / "t.jsonl",
        trad(meddelande(FORMULARAMNE, "Inledning"),
             meddelande(FORMULARAMNE, "Samma text")),
        trad(meddelande("Fråga om pris", "Samma text")))

    assert "Samma text" not in kategorisera.kontext_per_text(fil)


def test_samma_text_med_samma_kontext_ar_ingen_konflikt(tmp_path):
    """Två trådar med identisk ämnesrad ska INTE avväpna kontexten."""
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande(FORMULARAMNE, "Samma text")),
                        trad(meddelande(FORMULARAMNE, "Samma text")))

    assert kategorisera.kontext_per_text(fil)["Samma text"]["kanal"] \
        == kanal.WEBBFORMULAR


def test_kontext_per_text_pa_fil_som_inte_finns(tmp_path):
    """Nollfall: filen saknas."""
    assert kategorisera.kontext_per_text(tmp_path / "finns-inte.jsonl") == {}


def test_kontext_per_text_pa_tom_fil(tmp_path):
    """Nollfall: filen finns men är tom."""
    tom = tmp_path / "tom.jsonl"
    tom.write_text("", encoding="utf-8")

    assert kategorisera.kontext_per_text(tom) == {}


def test_meddelande_utan_brodtext_hoppas_over(tmp_path):
    """Nollfall: kundmeddelandet saknar text.

    Den tomma strängen får aldrig bli en nyckel: den hade matchat varje post
    vars text extraherats till tomt och spridit en godtycklig kanal.
    """
    fil = skriv_tradfil(tmp_path / "t.jsonl",
                        trad(meddelande(FORMULARAMNE, ""),
                             meddelande(FORMULARAMNE, "Har text")))

    ut = kategorisera.kontext_per_text(fil)

    assert "" not in ut
    assert "Har text" in ut


# --- ANROPAREN: att kontexten faktiskt når posterna --------------------------
#
# `kontext_per_text` kan vara aldrig så rätt om ingen kopplar in den.
# Granskningen av skiva 17 visade att BÅDA grenarna i
# `texter_att_kategorisera` gick att strippa på sin kontext utan att ett enda
# test föll. Testerna nedan binder inkopplingen, inte uppslagningen.


def test_par_sidan_far_sin_kontext(tmp_path):
    """Den BESVARADE grenen. Texten kommer ur `par.jsonl`, kontexten ur
    trådfilen, och utan uppslagningen bär posten ingen kanal alls."""
    parfil = tmp_path / "par.jsonl"
    parfil.write_text(
        json.dumps({"inkommande_text": "Vill bygga om"}, ensure_ascii=False)
        + "\n", encoding="utf-8")
    besvarade = skriv_tradfil(tmp_path / "b.jsonl",
                              trad(meddelande(FORMULARAMNE, "Vill bygga om")))

    poster = kategorisera.texter_att_kategorisera(
        parfil, besvarade, tmp_path / "finns-ej", set())

    assert poster[0]["kalla"] == "med svar"
    assert poster[0]["kanal"] == kanal.WEBBFORMULAR
    assert poster[0]["amne"] == FORMULARAMNE


def test_obesvarade_sidan_far_sin_kontext(tmp_path):
    """Den OBESVARADE grenen. Här finns meddelandet i handen, så kontexten
    tas direkt ur det och inte via uppslagningen."""
    obesvarade = skriv_tradfil(tmp_path / "o.jsonl",
                               trad(meddelande(FORMULARAMNE, "Vill boka")))

    poster = kategorisera.texter_att_kategorisera(
        tmp_path / "finns-ej", tmp_path / "finns-ej-2", obesvarade, set())

    assert poster[0]["kalla"] == "utan svar"
    assert poster[0]["kanal"] == kanal.WEBBFORMULAR
    assert poster[0]["amne"] == FORMULARAMNE


def test_par_text_utan_traff_i_traden_far_ingen_kontext(tmp_path):
    """Nollfall: texten finns i `par.jsonl` men inte i trådfilen.

    Posten ska sakna kontextnycklarna helt, inte bära ett påhittat värde.
    """
    parfil = tmp_path / "par.jsonl"
    parfil.write_text(
        json.dumps({"inkommande_text": "Finns inte i tråden"},
                   ensure_ascii=False) + "\n", encoding="utf-8")

    poster = kategorisera.texter_att_kategorisera(
        parfil, skriv_tradfil(tmp_path / "b.jsonl",
                              trad(meddelande(FORMULARAMNE, "Annan text"))),
        tmp_path / "finns-ej", set())

    assert poster[0]["kalla"] == "med svar"
    assert "kanal" not in poster[0]
    assert "amne" not in poster[0]


# --- NEGATIVKONTROLLEN: kanalen är aldrig ensam grund ------------------------


def test_kanalen_overstyr_aldrig_modellens_svar():
    """LARS REGEL. En text som kom via formuläret men handlar om något annat
    ska fortfarande kunna klassas som det.

    Modellen svarar `boka biltvätt` medan kanalen är a-traktorformuläret.
    Svaret ska stå kvar orört. Faller det här testet finns det en
    kanal-till-kategori-koppling i koden, och den är förbjuden.
    """
    taxonomi = ["boka biltvätt", "boka a-traktorkonvertering", "övrigt"]
    klient = FejkKlient(["boka biltvätt"])

    namn = ometikettera.ometikettera_en(
        klient, "Vill tvätta bilen", taxonomi, "system",
        amne=FORMULARAMNE, kanal=kanal.WEBBFORMULAR)

    assert namn == "boka biltvätt"


def test_kanalen_gor_inte_ett_svar_utanfor_taxonomin_giltigt():
    """Kanalen får inte heller rädda ett svar som inte står i listan."""
    klient = FejkKlient(["boka a-traktorgrej"])

    namn = ometikettera.ometikettera_en(
        klient, "Hej", ["boka a-traktorkonvertering"], "system",
        amne=FORMULARAMNE, kanal=kanal.WEBBFORMULAR)

    assert namn == ometikettera.UTANFOR


def test_samma_svar_ger_samma_etikett_med_och_utan_kanal():
    """Kanalen ändrar prompten, aldrig efterbehandlingen av svaret."""
    taxonomi = ["boka biltvätt", "övrigt"]

    utan = ometikettera.ometikettera_en(
        FejkKlient(["boka biltvätt"]), "Hej", taxonomi, "system")
    med = ometikettera.ometikettera_en(
        FejkKlient(["boka biltvätt"]), "Hej", taxonomi, "system",
        amne=FORMULARAMNE, kanal=kanal.WEBBFORMULAR)

    assert utan == med == "boka biltvätt"
