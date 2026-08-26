"""Tester för scripts/persondatakontroll.py.

All indata är påhittad. Testerna bär påståendet att spärren FÄLLER, alltså den
sort §7.1 kräver att man prövar genom att fälla raden och se sviten bli röd.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "persondatakontroll", ROT / "scripts" / "persondatakontroll.py"
)
kontroll = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(kontroll)


def sorter(text: str) -> set[str]:
    return {sort for _, sort, _ in kontroll.granska(text, "docs/x.md")}


def test_mailadress_falls():
    assert "mailadress" in sorter("hör av dig till namn@nagon.se tack")


def test_telefonnummer_falls():
    assert "telefonnummer" in sorter("ring 070-123 45 67")
    assert "telefonnummer" in sorter("ring +46 70 123 45 67")


def test_registreringsnummer_falls():
    for regnr in ("ABC123", "ABC 12D", "ABC-123"):
        assert "registreringsnummer" in sorter(f"bilen {regnr} står"), regnr


def test_postnummer_med_ort_falls():
    assert "postnummer" in sorter("adressen är 192 52 Sollentuna")
    assert "postnummer" in sorter("adressen är 19252 SOLLENTUNA")


def test_bart_femsiffrigt_tal_falls_inte():
    """Kvotåtgången i mining-loggen är inte ett postnummer. Att i stället
    undanta just de talen hade släppt igenom framtida riktiga postnummer."""
    rad = "| 2026-08-26 14:32 UTC | `in:sent` | 555 | 561 | 22260 | klar |"

    assert "postnummer" not in sorter(rad)


def test_gatuadress_falls():
    assert "gatuadress" in sorter("vi finns på Storgatan 14 i stan")


def test_personnummer_falls():
    assert "personnummer" in sorter("personnummer 19900101-1234")


def test_brevladan_ar_undantagen():
    """Företagets egen adress står i CLAUDE.md §0 och är inte persondata."""
    assert sorter("skriv till info@autostockholm.se") == set()


def test_ren_text_ger_inga_fynd():
    assert sorter("Kategorin bär 33 ärenden med svar.") == set()


def test_radnumret_pekar_ratt():
    text = "rad ett\nrad två\nnamn@nagon.se\n"

    fynd = kontroll.granska(text, "docs/x.md")

    assert fynd[0][0] == 3


def test_traffen_skrivs_aldrig_i_klartext():
    """Ett skript som larmar om persondata får inte självt skriva ut den."""
    maskerat = kontroll._maska("namn@nagon.se")

    assert "namn@nagon" not in maskerat
    assert maskerat.startswith("na")
    assert maskerat.endswith("se")


def test_kort_straeng_maskeras_helt():
    assert kontroll._maska("abcd") == "****"


def test_kod_bevakas_inte():
    """Kod innehåller mönster och testfixturer som ser ut som persondata."""
    assert not kontroll.bevakad("src/maskera.py")
    assert not kontroll.bevakad("tests/test_extract.py")


def test_mallar_config_och_claude_md_bevakas():
    """`mallar/` är den tyngsta posten: §11 säger att mallarna byggs ur rå
    kundtext. Den saknades i första versionen."""
    for sokvag in ("docs/kategorier-forslag.md", "mallar/offert.txt",
                   "config/maskindomaner.yaml", "CLAUDE.md"):
        assert kontroll.bevakad(sokvag), sokvag


def test_ombruten_mailadress_falls():
    """Dokumenten är hårdbrutna vid omkring åttio tecken. En adress som bryts
    mitt i syns inte på någon rad för sig."""
    text = "kontakta gärna fornamn.efternamn@\nnagon.se om du undrar"

    fynd = kontroll.granska(text, "docs/x.md")

    assert any("mailadress" in sort for _, sort, _ in fynd)


def test_ombrutet_telefonnummer_falls():
    text = "ring 070-123 45\n67 på förmiddagen"

    fynd = kontroll.granska(text, "docs/x.md")

    assert any("telefonnummer" in sort for _, sort, _ in fynd)


def test_ombruten_traff_markeras_som_sadan():
    text = "skriv till fornamn@\nnagon.se"

    fynd = kontroll.granska(text, "docs/x.md")

    assert any("över radslut" in sort for _, sort, _ in fynd)


def test_hopfogningen_skapar_inga_falska_traffar():
    """Två oskyldiga rader får inte bilda persondata när de fogas ihop."""
    text = "kategorin bär 33 ärenden\nmed svar i materialet"

    assert kontroll.granska(text, "docs/x.md") == []
