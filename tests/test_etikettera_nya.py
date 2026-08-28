"""Tester för scripts/etikettera-nya.py::nya_texter.

VARFÖR FILEN FINNS. Skiva 17 lade kontexten i posterna som den enda
sanktionerade körvägen bygger, och den raden gick inte att nå: torrkörningen
filtrerar bort varje kandidat som redan är etiketterad, alltså alla, och
`ut.append(...)` exekverades aldrig. En sändvägsändring på den enda körbara
vägen levererades utan verifiering. Se `docs/beslutslogg.md` #29.

Ingen riktig API-nyckel, inget nätverk, ingen skriven datafil. Alla texter,
ämnesrader och adresser är påhittade.
"""

from __future__ import annotations

import base64
import importlib.util
import json
from pathlib import Path

import pytest

from src import kanal

ROT = Path(__file__).resolve().parent.parent


def las_skript():
    """Laddar skriptet, vars filnamn bär bindestreck och inte går att importera."""
    spec = importlib.util.spec_from_file_location(
        "etikettera_nya", ROT / "scripts" / "etikettera-nya.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture
def skript():
    return las_skript()


def meddelande(amne: str, kropp: str) -> dict:
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


def tradfil(sokvag: Path, *meddelanden: dict) -> Path:
    rader = [json.dumps({"messages": [m]}, ensure_ascii=False)
             for m in meddelanden]
    sokvag.write_text("\n".join(rader) + "\n", encoding="utf-8")
    return sokvag


@pytest.fixture
def bygg(skript, tmp_path, monkeypatch):
    """Kör `nya_texter` mot en påhittad trådfil och en tom etikettfil."""
    def kor(*meddelanden: dict, redan: list[str] = ()):
        monkeypatch.setattr(
            skript, "BESVARADE", tradfil(tmp_path / "t.jsonl", *meddelanden))
        kat = tmp_path / "k.jsonl"
        kat.write_text(
            "".join(json.dumps({"text": t, "kalla": "utan svar",
                                "etikett": "oklart"}, ensure_ascii=False) + "\n"
                    for t in redan),
            encoding="utf-8")
        monkeypatch.setattr(skript, "KATEGORISVAR", kat)
        return skript.nya_texter()
    return kor


FORMULARAMNE = "Ny offertförfrågan A-traktor"


def test_posten_bar_kontexten(bygg):
    """KÄRNAN. Utan `amne` och `kanal` levererar den enda körbara vägen
    ingenting av skiva 17:s fix."""
    poster = bygg(meddelande(FORMULARAMNE, "Vill bygga om"))

    assert poster == [{"text": "Vill bygga om", "kalla": "utan svar",
                       "amne": FORMULARAMNE, "kanal": kanal.WEBBFORMULAR}]


def test_vanligt_mail_far_ingen_kanal(bygg):
    """Nollfall: kanalen går inte att fastställa, och då är svaret None."""
    poster = bygg(meddelande("Fråga om pris", "Vad kostar det"))

    assert poster[0]["kanal"] is None
    assert poster[0]["amne"] == "Fråga om pris"


def test_kallan_ar_alltid_utan_svar(bygg):
    """Kolumnen `Med svar` kan inte ändras av en tilläggskörning.

    Varje ny post bär `utan svar`, och det är den strukturella halvan av det
    skydd `kor()` sedan kontrollerar aritmetiskt.
    """
    poster = bygg(meddelande(FORMULARAMNE, "En"),
                  meddelande("Fråga om pris", "Två"))

    assert [p["kalla"] for p in poster] == ["utan svar", "utan svar"]


def test_redan_etiketterad_text_hoppas_over(bygg):
    """IDEMPOTENSEN. Nyckeln är `text`, och de nya nycklarna får inte bryta den."""
    poster = bygg(meddelande(FORMULARAMNE, "Vill bygga om"),
                  redan=["Vill bygga om"])

    assert poster == []


def test_dubblett_i_materialet_ger_en_post(bygg):
    """Samma text i två trådar ska bara etiketteras en gång."""
    poster = bygg(meddelande(FORMULARAMNE, "Samma"),
                  meddelande(FORMULARAMNE, "Samma"))

    assert len(poster) == 1


def test_tom_brodtext_ger_ingen_post(bygg):
    """Nollfall: meddelandet utan brödtext."""
    assert bygg(meddelande(FORMULARAMNE, "")) == []


def test_tom_tradfil_ger_inga_poster(bygg):
    """Nollfall: skörden är tom."""
    assert bygg() == []
