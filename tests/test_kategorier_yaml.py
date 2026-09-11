"""Tester för config/kategorier.yaml, fas 4:s grind.

Filen är sändväg: den avgör OM ett mail får gå ut automatiskt. Ett stavfel i ett
kategorinamn tar tyst bort kategorin ur sin hink, och en kategori som faller ur
`aldrig` hamnar i standardhinken utan att någon märker det.

Testerna prövar filen mot taxonomin och mot de etiketter korpusen faktiskt bär,
inte mot en kopia av listan.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from src import kategorisera, ometikettera

ROT = Path(__file__).resolve().parent.parent
HINKFIL = ROT / "config" / "kategorier.yaml"
TAXONOMIFIL = ROT / "data" / "taxonomi.json"

HINKAR = ("auto", "utkast", "aldrig")


@pytest.fixture
def hinkar() -> dict:
    return yaml.safe_load(HINKFIL.read_text(encoding="utf-8"))


def giltiga_etiketter() -> set[str]:
    """Taxonomin plus de etiketter som sätts utanför den.

    `inget kundärende`, `oklart` och `fel` kommer ur den fria klassningen och
    `utanför listan` ur pass 2. De står inte i taxonomin men är etiketter en
    text faktiskt kan bära, och därför namn som får stå i en hink.
    """
    taxonomi = set(json.loads(TAXONOMIFIL.read_text(encoding="utf-8")))
    return taxonomi | set(kategorisera.EJ_KUNDARENDE) | {ometikettera.UTANFOR}


def test_filen_finns_och_parsar(hinkar):
    assert isinstance(hinkar, dict)


def test_standardhinken_ar_utkast(hinkar):
    """En kategori ingen tagit ställning till får ALDRIG hamna i auto."""
    assert hinkar["standardhink"] == "utkast"


def test_standardhinken_ar_en_giltig_hink(hinkar):
    assert hinkar["standardhink"] in HINKAR


def test_auto_ar_TOM(hinkar):
    """Ramverksregel 2: ingen kategori flyttas till auto av kod.

    **`auto` ÄR TOM SEDAN SKIVA 38, på Lars beslut.** `fråga om
    a-traktorkonvertering` stod här tills skiva 37 mätte att klassificeraren gav
    samma tråd den kategorin i en körning och grannkategorin `boka
    a-traktorkonvertering` i en annan. Grannen stod i `utkast`, alltså hängde
    gränsen för om ett mail får gå ut på en skillnad klassificeraren inte kan
    göra. Se `docs/beslutslogg.md` #81.

    **RADEN ÄR TRIPWIREN FÖR RAMVERKSREGEL 2.** Blir den röd har någon lagt en
    kategori i `auto`, och det får bara ske på Lars uttryckliga beslut efter
    skuggläget. Att den är röd är alltså inte ett fel i sig; det är en fråga om
    vem som gjorde ändringen och varför.
    """
    assert hinkar["auto"] == [], (
        "en kategori står i auto. Ramverksregel 2: bara Lars uttryckliga "
        "beslut får flytta dit, och #81 säger att det ska vila på skuggläget."
    )


def test_a_traktorfragan_hamnar_i_UTKAST(hinkar):
    """Att kategorin FÖLL UR auto räcker inte. Den ska hamna rätt.

    Kategorin står inte i någon hink, alltså faller den till `standardhink`.
    Raden binder att standardhinken är `utkast` och inte något annat, eftersom
    hela flytten är meningslös om standardhinken en dag blir `auto`.
    """
    assert hinkar["standardhink"] == "utkast"
    assert "fråga om a-traktorkonvertering" not in hinkar["auto"]
    assert "fråga om a-traktorkonvertering" not in hinkar["aldrig"]


def test_varje_namn_ar_en_verklig_etikett(hinkar):
    """Ett stavfel gör att kategorin tyst faller till standardhinken."""
    giltiga = giltiga_etiketter()
    for hink in ("auto", "aldrig"):
        for namn in hinkar[hink]:
            assert namn in giltiga, f"{hink}: {namn!r} är ingen etikett"


def test_ingen_kategori_star_i_tva_hinkar(hinkar):
    """En kategori i både auto och aldrig hade gjort utfallet beroende av
    läsordningen i den kod som senare tolkar filen."""
    assert not set(hinkar["auto"]) & set(hinkar["aldrig"])


def test_de_nio_aldrig_kategorierna_star_kvar(hinkar):
    """Lars diktamen i skiva 17, ordagrant. Faller en av dem ur listan hamnar
    den i standardhinken `utkast` och blir därmed ett utkast en människa kan
    råka skicka."""
    for namn in ("bestrida faktura", "reklamera utfört arbete",
                 "godkänna offert", "begära dokument",
                 "ansöka om praktikplats", "ge feedback",
                 "inget kundärende", "oklart", "utanför listan"):
        assert namn in hinkar["aldrig"], namn


def test_prisfragan_star_inte_i_auto(hinkar):
    """`fråga om pris a-traktorkonvertering` står inte i `auto`.

    Kategorin är KVALIFICERAD för `auto` och hindras enbart av att
    `config/priser.json` saknas, se `docs/beslutslogg.md` #30. Den flyttas
    ändå inte automatiskt när filen fylls: flytten kräver ett nytt uttryckligt
    beslut av Lars.

    Testet binder alltså var kategorin står i dag, och det ska falla den dag
    någon flyttar den. Att det faller är poängen: flytten ska vara ett beslut
    och inte en följdverkan.
    """
    assert "fråga om pris a-traktorkonvertering" not in hinkar["auto"]


def test_filen_bar_ingen_utkastlista(hinkar):
    """`utkast` är standardhinken och räknas inte upp.

    En uppräkning hade blivit föråldrad av varje ny kategori, och den som läste
    den hade trott att en kategori utanför listan saknar hink.
    """
    assert "utkast" not in hinkar
