"""Tester för src/kategorisera.py.

Ingen riktig API-nyckel och inget nätverk. Klienten är fejkad, och alla texter
är påhittade.
"""

from __future__ import annotations

import json

from src import kategorisera


class FejkBlock:
    def __init__(self, text):
        self.type = "text"
        self.text = text


class FejkForbrukning:
    def __init__(self, in_tokens=100, ut_tokens=5):
        self.input_tokens = in_tokens
        self.output_tokens = ut_tokens


class FejkSvar:
    def __init__(self, text, forbrukning=None):
        self.content = [FejkBlock(text)]
        self.usage = FejkForbrukning() if forbrukning is None else forbrukning


class FejkKlient:
    """Svarar med en förbestämd sekvens och sparar varje anrop."""

    def __init__(self, svar, fel_pa=()):
        self._svar = list(svar)
        self._fel_pa = set(fel_pa)
        self.anrop = []
        self.messages = self

    def create(self, **kw):
        nummer = len(self.anrop)
        self.anrop.append(kw)
        if nummer in self._fel_pa:
            raise RuntimeError("API-fel")
        return FejkSvar(self._svar[nummer % len(self._svar)])


# --- nyckeln -----------------------------------------------------------------


def test_miljon_gar_fore_envfilen(tmp_path, monkeypatch):
    envfil = tmp_path / ".env"
    envfil.write_text("ANTHROPIC_API_KEY=ur-filen\n", encoding="utf-8")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "ur-miljon")

    assert kategorisera.las_api_nyckel(envfil) == "ur-miljon"


def test_envfilen_anvands_nar_miljon_saknas(tmp_path, monkeypatch):
    """En export i en interaktiv terminal når inte ett skal som startas om per
    anrop. `.env` fungerar i båda fallen och är gitignorerad."""
    envfil = tmp_path / ".env"
    envfil.write_text("# kommentar\nANTHROPIC_API_KEY=\"ur-filen\"\n",
                      encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kategorisera.las_api_nyckel(envfil) == "ur-filen"


def test_saknad_nyckel_ger_tom_strang(tmp_path, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kategorisera.las_api_nyckel(tmp_path / "finns-ej") == ""


def test_bar_nyckel_utan_namn_lases_inte(tmp_path, monkeypatch):
    """Toleransen är BORTTAGEN på Lars beslut. §1: en oklarhet lyfts, inte
    tystas. En tolerant parser döljer att formatet var fel, och nästa läsare
    vet då inte vilken form som gäller."""
    envfil = tmp_path / ".env"
    envfil.write_text("sk-ant-pahittad-nyckel\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kategorisera.las_api_nyckel(envfil) == ""


def test_export_prefix_lases_inte(tmp_path, monkeypatch):
    """Formen är `ANTHROPIC_API_KEY=värde`, och inget annat."""
    envfil = tmp_path / ".env"
    envfil.write_text("export ANTHROPIC_API_KEY=sk-ant-x\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kategorisera.las_api_nyckel(envfil) == ""


def test_annan_variabel_i_envfilen_plockas_inte(tmp_path, monkeypatch):
    envfil = tmp_path / ".env"
    envfil.write_text("ANNAN_NYCKEL=fel\n", encoding="utf-8")
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

    assert kategorisera.las_api_nyckel(envfil) == ""


# --- normalisering -----------------------------------------------------------


def test_kort_etikett_slapps_igenom():
    assert kategorisera.normalisera("boka besiktningstid") == "boka besiktningstid"


def test_versaler_och_skiljetecken_normaliseras():
    assert kategorisera.normalisera(' "Boka Tid." ') == "boka tid"


def test_lang_forklaring_blir_oklart():
    """Utan det blir modellens förklaring en egen kategori, och listan fylls
    av engångsposter som ser ut som kategorier."""
    lang = ("kunden verkar vilja boka en tid men skriver också om ett annat "
            "ärende som gör det svårt att avgöra vad som avses")

    assert kategorisera.normalisera(lang) == "oklart"


def test_tomt_svar_blir_oklart():
    assert kategorisera.normalisera("") == "oklart"


def test_etikett_med_siffror_blir_oklart():
    assert kategorisera.normalisera("ärende 12345") == "oklart"


def test_inget_kundarende_slapps_igenom():
    assert kategorisera.normalisera("inget kundärende") == "inget kundärende"


# --- anropet -----------------------------------------------------------------


def test_modellen_far_ingen_kategorilista():
    """Kategorierna ska falla ut ur datan. En lista hade gjort utfallet till
    en avprickning mot mina gissningar."""
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(klient, "Hej, vill boka tid")

    system = klient.anrop[0]["system"]
    assert "lista" in system.lower()
    assert "INGEN lista" in system


def test_texten_kortas_innan_den_skickas():
    klient = FejkKlient(["boka tid"])
    lang = "x" * 5000

    kategorisera.kategorisera_en(klient, lang)

    skickat = klient.anrop[0]["messages"][0]["content"]
    assert len(skickat) == kategorisera.MAX_TECKEN


def test_modellen_ar_den_som_begarts():
    klient = FejkKlient(["boka tid"])

    kategorisera.kategorisera_en(klient, "text", modell="claude-sonnet-4-6")

    assert klient.anrop[0]["model"] == "claude-sonnet-4-6"


def test_ett_anrop_per_text():
    """En text i taget, inte i batch: ett fel ska kosta en text, och ett svar
    ska gå att spåra till sin fråga."""
    klient = FejkKlient(["boka tid"])
    poster = [{"text": f"text {i}", "kalla": "med svar"} for i in range(4)]

    kategorisera.kategorisera_alla(klient, poster, sov=lambda _: None)

    assert len(klient.anrop) == 4


def test_fel_pa_en_text_stoppar_inte_resten():
    klient = FejkKlient(["boka tid"], fel_pa={1})
    poster = [{"text": f"text {i}", "kalla": "med svar"} for i in range(3)]

    ut = kategorisera.kategorisera_alla(klient, poster, sov=lambda _: None)

    assert [p["etikett"] for p in ut] == ["boka tid", "fel", "boka tid"]


# --- tokenåtgång -------------------------------------------------------------


def test_atgangen_summeras_over_anropen():
    klient = FejkKlient(["boka tid"])
    atgang = kategorisera.Tokenatgang()
    poster = [{"text": f"text {i}", "kalla": "med svar"} for i in range(3)]

    kategorisera.kategorisera_alla(klient, poster, atgang=atgang,
                                   sov=lambda _: None)

    assert atgang.anrop == 3
    assert atgang.in_tokens == 300
    assert atgang.ut_tokens == 15


def test_svar_utan_usage_faller_inte_korningen():
    """En utebliven mätning får inte kosta en klassificering."""
    klient = FejkKlient(["boka tid"])
    klient._svar = ["boka tid"]
    atgang = kategorisera.Tokenatgang()

    kategorisera.kategorisera_en(klient, "text", atgang=atgang)
    atgang.lagg_till(None)

    assert atgang.anrop == 2
    assert atgang.in_tokens == 100


def test_redovisningen_ar_tom_utan_anrop():
    assert kategorisera.Tokenatgang().redovisa() == ["  inga anrop"]


def test_medelvardet_raknas_per_anrop():
    atgang = kategorisera.Tokenatgang()
    atgang.lagg_till(FejkForbrukning(200, 10))
    atgang.lagg_till(FejkForbrukning(100, 4))

    rader = "\n".join(atgang.redovisa())

    assert "in-tokens totalt: 300" in rader
    assert "in-tokens per anrop, medel: 150.0" in rader


# --- sammanställning ---------------------------------------------------------


def test_antal_per_kalla_raknas_var_for_sig():
    poster = [
        {"text": "a", "kalla": "med svar", "etikett": "boka tid"},
        {"text": "b", "kalla": "utan svar", "etikett": "boka tid"},
        {"text": "c", "kalla": "utan svar", "etikett": "fråga om pris"},
    ]

    sammanstallning = kategorisera.sammanstall(poster)

    assert sammanstallning[0] == {
        "etikett": "boka tid", "antal": 2, "med_svar": 1, "utan_svar": 1,
        "exempel": ["a", "b"],
    }


def test_hogst_tre_exempel_per_kategori():
    poster = [{"text": str(i), "kalla": "med svar", "etikett": "boka tid"}
              for i in range(9)]

    assert len(kategorisera.sammanstall(poster)[0]["exempel"]) == 3


# --- rapporten ---------------------------------------------------------------


def test_rapporten_foreslar_ingen_hink(tmp_path):
    utfil = tmp_path / "kategorier-forslag.md"
    sammanstallning = [{"etikett": "boka tid", "antal": 9, "med_svar": 5,
                        "utan_svar": 4, "exempel": []}]

    kategorisera.skriv_rapport(sammanstallning, utfil, 9, "claude-sonnet-4-6")

    text = utfil.read_text(encoding="utf-8")
    assert "INGEN HINKTILLDELNING FÖRESLÅS" in text
    assert "boka tid" in text


def test_rapporten_bar_inga_citat(tmp_path):
    """§6: citat ur kundmail hör inte hemma i docs/."""
    utfil = tmp_path / "kategorier-forslag.md"
    sammanstallning = [{"etikett": "boka tid", "antal": 1, "med_svar": 1,
                        "utan_svar": 0, "exempel": ["Hej jag heter Annika"]}]

    kategorisera.skriv_rapport(sammanstallning, utfil, 1, "claude-sonnet-4-6")

    text = utfil.read_text(encoding="utf-8")
    assert "Annika" not in text
    assert "> " not in text


def test_exempelfilen_maskerar(tmp_path):
    utfil = tmp_path / "exempel.md"
    sammanstallning = [{"etikett": "boka tid", "antal": 1, "med_svar": 1,
                        "utan_svar": 0,
                        "exempel": ["jag heter Annika och bilen är ABC123"]}]

    kategorisera.skriv_exempel(sammanstallning, utfil)

    text = utfil.read_text(encoding="utf-8")
    assert "Annika" not in text
    assert "ABC123" not in text
    assert "INNEHÅLLER PERSONDATA" in text


# --- urvalet -----------------------------------------------------------------


def test_kallorna_varvas_sa_att_varje_prefix_ar_blandat():
    """Utan varvningen låg alla besvarade först, och en provkörning på tjugo
    poster blev blind för de obesvarade, som är tre gånger fler."""
    poster = ([{"text": f"m{i}", "kalla": "med svar"} for i in range(3)]
              + [{"text": f"u{i}", "kalla": "utan svar"} for i in range(3)])

    varvat = kategorisera.varva(poster)

    assert [p["kalla"] for p in varvat[:4]] == [
        "med svar", "utan svar", "med svar", "utan svar"
    ]


def test_varvningen_tappar_ingen_post_nar_kallorna_ar_olika_stora():
    poster = ([{"text": "m", "kalla": "med svar"}]
              + [{"text": f"u{i}", "kalla": "utan svar"} for i in range(4)])

    varvat = kategorisera.varva(poster)

    assert len(varvat) == 5
    assert sum(1 for p in varvat if p["kalla"] == "med svar") == 1


def test_maskinmail_kommer_inte_med(tmp_path):
    """Trådarna måste ha OLIKA brödtext, och testet måste kontrollera VILKEN
    post som överlever.

    En tidigare version gav båda trådarna samma text. Avdubbleringen ensam gav
    då `len(poster) == 1`, och testet förblev grönt med maskinfiltret helt
    avstängt: posten som överlevde var maskinmailet.
    """
    import base64

    obesvarade = tmp_path / "obesvarade.jsonl"

    def trad(huvuden, text):
        kodad = base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")
        return {"messages": [{
            "labelIds": ["INBOX"],
            "payload": {"mimeType": "text/plain", "body": {"data": kodad},
                        "headers": [{"name": n, "value": v}
                                    for n, v in huvuden.items()]},
        }]}

    rader = [
        json.dumps(trad({"From": "A <a@x.se>", "List-Unsubscribe": "<x>"},
                        "nyhetsbrev om verktyg")),
        json.dumps(trad({"From": "B <b@y.se>"}, "fråga om reservdel")),
    ]
    obesvarade.write_text("\n".join(rader) + "\n", encoding="utf-8")

    poster = kategorisera.texter_att_kategorisera(
        tmp_path / "finns-ej", tmp_path / "finns-ej-2", obesvarade, set()
    )

    assert [p["text"] for p in poster] == ["fråga om reservdel"]
    assert poster[0]["kalla"] == "utan svar"
