"""Utkastvyn, fas 5.5.

TESTERNA BÄR TRE SPÄRRAR, och den viktigaste är att vyn inte har någon sändväg.
Se `docs/sparrar.md` `vyn-har-ingen-sandvag`, `referenssvar-skickas-aldrig` och
`sparrfalld-post-har-inget-textfalt`.

**FIXTURERNA BÄR INGEN KUNDTEXT.** Testerna bygger sina egna poster. Att läsa
`data/` i ett test hade gjort sviten beroende av en gitignorerad fil och satt
kundtext i en testrapport (§6).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from src import vy
from src.vy import Fall

ROT = Path(__file__).resolve().parent.parent


def ett_fall(**andrat) -> Fall:
    grund = dict(
        etikett="fråga om a-traktorkonvertering",
        kalla="med svar",
        text="Hej, vad kostar det att bygga om en Volvo till a-traktor?",
        tidsstampel="2026-01-02T03:04:05+00:00",
        avsandare_hash="0" * 64,
    )
    grund.update(andrat)
    return Fall(**grund)


# ---------------------------------------------------------------- DEL B


def test_vyn_har_ingen_sandvag():
    """SPÄRRENS HUVUDFALL. Vyn drar inte in något som kan skicka mail.

    Prövningen går över hela importgrafen inom repot, inte bara över
    `src/vy.py`, eftersom en modul vyn importerar kan importera vidare.
    """
    vy.krav_pa_sandvagsfrihet()


def test_importlagret_faller_en_modul_som_kan_skicka(tmp_path):
    """NEGATIVKONTROLL för importlagret: det fäller när det ska.

    Utan den här raden hade `krav_pa_sandvagsfrihet` kunnat sluta leta utan att
    något test blev rött, vilket är precis §7.1:s vakuösa fall.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "from googleapiclient.discovery import build\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "googleapiclient" in str(fel.value)


def test_importlagret_foljer_kedjan_ett_steg_till(tmp_path):
    """En modul som vyn importerar får inte heller ha en sändväg.

    Här importerar vyn en oskyldig modul, och DEN importerar `src.auth`.
    Prövningen ska följa kedjan; gjorde den inte det hade en indirektion räckt
    för att gömma sändvägen.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text("from src import mellan\n", encoding="utf-8")
    (tmp_path / "src" / "mellan.py").write_text("from src import auth\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "src.auth" in str(fel.value)


def test_kalltextlagret_faller_ett_anrop_utan_import(tmp_path):
    """NEGATIVKONTROLL för det andra lagret, och det är inte redundant.

    En modul kan nå en färdig Gmail-tjänst som ARGUMENT och anropa
    `messages().send` utan att importera något förbjudet. Importlagret ser
    ingenting då. Det här är fallet som skiljer de två lagren åt.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "def skicka(tjanst, brev):\n"
        "    return tjanst.users().messages().send(userId='me', body=brev)\n",
        encoding="utf-8",
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "messages().send" in str(fel.value)


def test_smtp_faller_ocksa(tmp_path):
    """Den andra vägen ut. `smtplib` behöver ingen Google-tjänst alls."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "import smtplib\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel):
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)


def test_en_ren_modul_slapps_igenom(tmp_path):
    """NEGATIVKONTROLL ÅT ANDRA HÅLLET: spärren är inte ett larm som alltid går.

    En spärr som fäller på allt är inget skydd, den är ett stopp, och den blir
    avstängd. Här importerar vyn `json` och en lokal modul, och ingenting ska
    hända.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "import json\nfrom src import urval\n", encoding="utf-8"
    )
    (tmp_path / "src" / "urval.py").write_text("import hashlib\n", encoding="utf-8")

    vy.krav_pa_sandvagsfrihet(rot=tmp_path)


def test_starta_provar_sparren_innan_servern_binds(monkeypatch):
    """Spärren körs FÖRE servern tar emot något.

    Utan den här raden hade `krav_pa_sandvagsfrihet` kunnat tas bort ur
    `starta` utan att någon rad blev röd: de andra testen anropar funktionen
    direkt.
    """
    anropad = []

    def fejk(*_, **__):
        anropad.append(True)
        raise vy.Sandvagsfel("fejkad")

    monkeypatch.setattr(vy, "krav_pa_sandvagsfrihet", fejk)

    with pytest.raises(vy.Sandvagsfel):
        vy.starta(port=0, fall=[])

    assert anropad


# ---------------------------------------------------------------- §6


def test_skrivning_utanfor_data_och_logg_kastar(tmp_path):
    """§6. Vyn visar rå kundtext och får inte skriva den var som helst."""
    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(ROT / "docs" / "lackt.jsonl")


def test_skrivning_utanfor_repot_kastar():
    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(Path("/tmp/lackt.jsonl"))


@pytest.mark.parametrize("katalog", ["data", "logg"])
def test_de_tva_gitignorerade_katalogerna_slapps_igenom(katalog):
    """NEGATIVKONTROLL: kontrollen får inte fälla de vägar vyn faktiskt har."""
    vy.krav_pa_skrivbar_sokvag(ROT / katalog / "fil.jsonl")


def test_referenssvar_kan_inte_sparas_utanfor_data(tmp_path, monkeypatch):
    """Kontrollen sitter i SKRIVFUNKTIONEN, inte hos anroparen.

    **SÖKVÄGEN LIGGER I `tmp_path`, ALDRIG I DET RIKTIGA REPOT, och det är inte
    en detalj.** Testet påstår att skrivningen INTE sker, alltså kommer det förr
    eller senare att köras med spärren fälld: det är precis vad §7.1:s prövning
    gör. Med en riktig sökväg skrev fällningen då en fil till `docs/` på riktigt,
    och prövningen av spärren blev själv det spärren finns för att förhindra.

    Uppmätt i skiva 27: fällningen av `krav_pa_skrivbar_sokvag`:s villkor lämnade
    efter sig en `docs/x.jsonl` med två poster i arbetsträdet, upptäckt först av
    `git status` inför committen.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    (tmp_path / "docs").mkdir()

    with pytest.raises(vy.Skrivfel):
        vy.spara_referenssvar(
            ett_fall(), "ett svar", parfil=tmp_path / "docs" / "x.jsonl"
        )


# ---------------------------------------------------------------- DEL 0


def test_sparrfalld_post_visar_aldrig_textfalt():
    """DEL 0 I SKIVA 27, beslut av Lars. §9.1 väger tyngre än bekvämligheten.

    En textruta bredvid ett fällt förslag gör förbudet till ett klick, även när
    knappen heter spara och inte skicka.
    """
    sida = vy.rendera_granskning(ett_fall(), "ett förslag", sparr="fordonsfakta-ur-sida")

    assert "<textarea" not in sida
    assert "<button" not in sida
    assert "fordonsfakta-ur-sida" in sida


def test_osparrad_post_visar_textfalt():
    """NEGATIVKONTROLL: regeln gäller den spärrfällda posten och inte alla.

    Utan den här raden hade `rendera_granskning` kunnat sluta visa textfält helt
    utan att något test blev rött, och granskningsläget hade varit oanvändbart.
    """
    sida = vy.rendera_granskning(ett_fall(), "ett förslag")

    assert "<textarea" in sida
    for omdome in vy.OMDOMESVARDEN:
        assert omdome in sida


# ---------------------------------------------------------------- DEL A


def test_referenslaget_visar_tomt_falt_och_ingen_skickaknapp():
    """REFERENSLÄGET. Tomt fält, och knappen är omöjlig att förväxla.

    PÅSTÅENDET GÄLLER KNAPPARNA, inte ordet. Sidan säger med avsikt *Skickas
    aldrig* i brödtexten, alltså kan testet inte fråga om teckenföljden `Skicka`
    finns någonstans i HTML:en: den första lydelsen gjorde det och blev röd av
    den upplysning som är hela poängen med vyn.
    """
    sida = vy.rendera_referens(ett_fall(), 0, 1)

    assert "<textarea name='svar' placeholder=" in sida
    assert [k.strip() for k in re.findall(r"<button[^>]*>(.*?)</button>", sida)] == [
        "Spara som par"
    ]


def test_kundtexten_escapas_i_sidan():
    """Kundtext renderas som TEXT och aldrig som markup.

    En kund som skriver `<script>` ska synas på skärmen, inte köras i
    webbläsaren. Vyn visar rå kundtext, alltså är det här den enda platsen där
    råheten möter en tolk.
    """
    sida = vy.rendera_referens(ett_fall(text="<script>larm()</script>"), 0, 1)

    assert "<script>larm()</script>" not in sida
    assert "&lt;script&gt;" in sida


def test_referenssvar_skrivs_som_ett_par(tmp_path, monkeypatch):
    """Referenssvaret hamnar i par.jsonl med de fyra ursprungliga nycklarna."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    parfil = tmp_path / "data" / "par.jsonl"

    post = vy.spara_referenssvar(ett_fall(), "  Hej, det kostar X.  ", "gront", parfil)

    assert post["inkommande_text"] == ett_fall().text
    assert post["utgaende_text"] == "Hej, det kostar X."
    assert post["tidsstampel"] == ett_fall().tidsstampel
    assert post["avsandare_hash"] == ett_fall().avsandare_hash

    rader = parfil.read_text(encoding="utf-8").splitlines()
    assert json.loads(rader[0]) == post


def test_referenssvaret_ar_markt_som_referenssvar(tmp_path, monkeypatch):
    """#11 räknar svarsinstanser, och ett referenssvar är inte en sådan.

    Utan markören hade en senare läsare räknat referenssvaren som svar vi
    faktiskt skickat till en kund.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    post = vy.spara_referenssvar(
        ett_fall(), "ett svar", "rott", tmp_path / "data" / "par.jsonl"
    )

    assert post["kalla"] == "referenssvar"
    assert post["utfall"] == "rott"


def test_tomt_referenssvar_sparas_inte(tmp_path, monkeypatch):
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_referenssvar(ett_fall(), "   ", parfil=tmp_path / "data" / "par.jsonl")


def test_okant_utfall_avvisas(tmp_path, monkeypatch):
    """De fyra utfallen är en sluten lista, precis som i `fordonsuppslag`."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_referenssvar(
            ett_fall(), "ett svar", "kanske", tmp_path / "data" / "par.jsonl"
        )


@pytest.mark.parametrize("utfall", vy.UTFALL)
def test_de_fem_tillatna_utfallen_gar_igenom(tmp_path, monkeypatch, utfall):
    """NEGATIVKONTROLL till raden ovan, inklusive den tomma strängen.

    Tom betyder att Lars inte angett något, och det ska gå: DEL C säger att
    utfallet anges MANUELLT när det inte går att avgöra.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    post = vy.spara_referenssvar(
        ett_fall(), "ett svar", utfall, tmp_path / "data" / "par.jsonl"
    )
    assert post["utfall"] == utfall


# ---------------------------------------------------------------- omdömen


def test_de_fyra_omdomena_loggas_atskilt(tmp_path, monkeypatch):
    """De fyra slås aldrig ihop till godkänt och icke godkänt."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    fil = tmp_path / "logg" / "omdomen.jsonl"

    for omdome in ("godkann", "forkasta", "neka"):
        vy.spara_omdome(ett_fall(), omdome, omdomesfil=fil)

    loggade = [json.loads(r)["omdome"] for r in fil.read_text().splitlines()]
    assert loggade == ["godkann", "forkasta", "neka"]


def test_forbattra_skriver_ocksa_ett_par(tmp_path, monkeypatch):
    """`forbattra` är den enda av de fyra som tränar rösten."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    parfil = tmp_path / "data" / "par.jsonl"

    vy.spara_omdome(
        ett_fall(), "forbattra", "så här skulle det stått",
        omdomesfil=tmp_path / "logg" / "omdomen.jsonl", parfil=parfil,
    )

    post = json.loads(parfil.read_text(encoding="utf-8").splitlines()[0])
    assert post["utgaende_text"] == "så här skulle det stått"


def test_okant_omdome_avvisas(tmp_path, monkeypatch):
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_omdome(ett_fall(), "kanske", omdomesfil=tmp_path / "logg" / "o.jsonl")


# ---------------------------------------------------------------- DEL C


def test_urvalet_tar_bada_populationerna(tmp_path):
    """A-traktorfall både med svar och utan, så att de fyra utfallen går att nå."""
    etikettfil = tmp_path / "ometiketterade.jsonl"
    parfil = tmp_path / "par.jsonl"
    etikettfil.write_text(
        json.dumps({"etikett": "fråga om a-traktorkonvertering",
                    "kalla": "med svar", "text": "A"}, ensure_ascii=False) + "\n"
        + json.dumps({"etikett": "boka a-traktorkonvertering",
                      "kalla": "utan svar", "text": "B"}, ensure_ascii=False) + "\n"
        + json.dumps({"etikett": "boka rekond",
                      "kalla": "med svar", "text": "C"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    parfil.write_text(
        json.dumps({"inkommande_text": "A", "utgaende_text": "svar",
                    "tidsstampel": "T", "avsandare_hash": "H"}) + "\n",
        encoding="utf-8",
    )

    fall = vy.las_fall(etikettfil, parfil)

    assert [f.text for f in fall] == ["A", "B"]
    assert fall[0].tidsstampel == "T"
    assert fall[0].avsandare_hash == "H"


def test_obesvarat_fall_far_tomma_falt_och_ingen_pahittad_hash(tmp_path):
    """HÅLET SKRIVS UT I STÄLLET FÖR ATT FYLLAS.

    Uppmätt i skiva 27: 1 av 9 obesvarade a-traktorfall gick att koppla mot
    `data/tradar_obesvarade.jsonl`, eftersom den etiketterade texten inte är
    ordagrant `urval.brodtext` av något kundmeddelande. En påhittad hash hade
    varit ett tal utan källa (§7.2).
    """
    etikettfil = tmp_path / "ometiketterade.jsonl"
    etikettfil.write_text(
        json.dumps({"etikett": "boka a-traktorkonvertering",
                    "kalla": "utan svar", "text": "B"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    fall = vy.las_fall(etikettfil, tmp_path / "finns-inte.jsonl")

    assert fall[0].tidsstampel == ""
    assert fall[0].avsandare_hash == ""


def test_urvalet_ar_tomt_utan_etikettfil(tmp_path):
    assert vy.las_fall(tmp_path / "finns-inte.jsonl", tmp_path / "par.jsonl") == []
