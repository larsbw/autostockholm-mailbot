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


class FejkSvar:
    def __init__(self, text):
        self.content = [FejkBlock(text)]


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


def test_maskinmail_kommer_inte_med(tmp_path):
    obesvarade = tmp_path / "obesvarade.jsonl"
    kropp = {"data": "ZnLDpWdhIG9tIHJlc2VydmRlbA=="}

    def trad(huvuden):
        return {"messages": [{
            "labelIds": ["INBOX"],
            "payload": {"mimeType": "text/plain", "body": kropp,
                        "headers": [{"name": n, "value": v}
                                    for n, v in huvuden.items()]},
        }]}

    rader = [
        json.dumps(trad({"From": "A <a@x.se>", "List-Unsubscribe": "<x>"})),
        json.dumps(trad({"From": "B <b@y.se>"})),
    ]
    obesvarade.write_text("\n".join(rader) + "\n", encoding="utf-8")

    poster = kategorisera.texter_att_kategorisera(
        tmp_path / "finns-ej", tmp_path / "finns-ej-2", obesvarade, set()
    )

    assert len(poster) == 1
    assert poster[0]["kalla"] == "utan svar"
