"""Tester för scripts/generator-matning.py::spar_per_sparr.

VARFÖR FILEN FINNS. Skiva 57 DEL A: skriptet skrev `Sparrfalld.skal` OMASKERAT
både till terminalen och till sin utfil i `scratchpad/`. Utfilen är det som gör
raden värd ett test: en fil lever kvar, och skiva 53 visade att en fil i en
gitignorerad katalog ändå kan hamna fel.

Ingen riktig API-nyckel, inget nätverk, ingen skriven fil. `spar_per_sparr` tar
en färdig text och kör spärrarna på den.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from src.generera import Forfragan

ROT = Path(__file__).resolve().parent.parent


def las_skript():
    """Laddar skriptet, vars filnamn bär bindestreck och inte går att importera."""
    spec = importlib.util.spec_from_file_location(
        "generator_matning", ROT / "scripts" / "generator-matning.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


@pytest.fixture
def skript():
    return las_skript()


def test_skalet_ar_maskerat_innan_det_nar_utfilen(skript):
    """§6. Fältet går till `scratchpad/`, alltså till en fil som lever kvar.

    **TRÖSKELSPÄRREN ÄR DEN GREN SOM GÅR ATT MÄTA, och det är ingen slump.**
    Uppmätt över `SATS_PER_SPARR`: maskeringen är IDENTITET för nio av dess tio
    skäl. De skälen bär inga versala ord och inga siffergrupper alls, utom det
    tal `maska_sparrskal` uttryckligen undantar. Tröskelspärren är den enda vars
    skäl bär ett tal maskeringen rör: `1 000` står i en fast sträng och inte
    efter ordet `talet`.

    *Här stod att `SATS_PER_SPARR` är "varje spärr och gren". Den täcker tio av
    tolv skälgrenar i `src/generera.py` och saknar prisgrenen och `tomt-svar`.
    Slutsatsen står kvar: §7-granskningen av skiva 57 körde de två utelämnade
    grenarna för sig, och maskeringen är identitet också för dem.*

    Raden binder därför den av de två maskeringsraderna som går att binda. Den
    andra, i loopen över talspärren och fordonsfaktumspärren, är vakuös i dag:
    ingen indata skiljer maskerad från omaskerad utdata där.
    """
    fallda = skript.spar_per_sparr(
        "Hej. Lagen kräver 1 000 kg för en a-traktor.",
        Forfragan(text="hej", kategori="fråga om a-traktorkonvertering",
                  utfall=None),
    )

    troskeln = [f for f in fallda
                if f["sparr"] == "troskeln-som-forfattningstext"]
    assert troskeln, "indatan ska fälla tröskelspärren, annars mäter raden inget"
    assert "1 000" not in troskeln[0]["skal"]
    assert "[SIFFROR]" in troskeln[0]["skal"]
