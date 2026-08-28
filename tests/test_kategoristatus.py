"""Tester för scripts/kategoristatus.py.

Statusraden är §12:s krav och läses som belagd. Ett fel här ger en rad som ser
maskinproducerad ut och är fel, vilket är sämre än det hål §12 lät stå.

FIXTURERNA ÅTERANVÄNDER VERKLIGA KATEGORINAMN, med avsikt: `bestrida faktura`,
`boka service` och `inget kundärende` finns i taxonomin respektive i
`EJ_KUNDARENDE`, och miningdatumet är repots faktiska sista körning. Ett test
som bara känner påhittade namn hade missat att skriptet läser dem ur filer med
just den formen. `boka tvätt` är påhittat och står för det som INTE finns.
Ingen kundtext förekommer.

TYNGDPUNKTEN LIGGER PÅ ATT RADEN INTE PRODUCERAS när en källa saknas. Det är
påståendet om att något INTE sker, och det är det §7.1 kräver fällning av.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROT = Path(__file__).resolve().parent.parent


def las_skript():
    spec = importlib.util.spec_from_file_location(
        "kategoristatus", ROT / "scripts" / "kategoristatus.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


status = las_skript()


HINKAR = {"standardhink": "utkast",
          "auto": ["boka tvätt"],
          "aldrig": ["bestrida faktura", "inget kundärende"]}


def skriv_hinkar(sokvag: Path, **avvikelser) -> Path:
    import yaml
    data = {**HINKAR, **avvikelser}
    sokvag.write_text(yaml.safe_dump(data, allow_unicode=True),
                      encoding="utf-8")
    return sokvag


def skriv_etiketter(sokvag: Path, *poster: tuple[str, str]) -> Path:
    sokvag.write_text(
        "".join(json.dumps({"text": f"t{i}", "kalla": kalla, "etikett": e},
                           ensure_ascii=False) + "\n"
                for i, (e, kalla) in enumerate(poster)),
        encoding="utf-8")
    return sokvag


def skriv_taxonomi(sokvag: Path, *namn: str) -> Path:
    sokvag.write_text(json.dumps(list(namn), ensure_ascii=False),
                      encoding="utf-8")
    return sokvag


def skriv_mining(sokvag: Path, *datum: str) -> Path:
    rader = ["# Mining-logg", "",
             "| Datum | Query | Trådar | Anrop | Kvotenheter | Status |",
             "| --- | --- | --- | --- | --- | --- |"]
    rader += [f"| {d} | `q` | 1 | 1 | 10 | fullständig |" for d in datum]
    sokvag.write_text("\n".join(rader) + "\n", encoding="utf-8")
    return sokvag


# --- hinkarna ----------------------------------------------------------------


def test_auto_och_aldrig_lases_ur_filen():
    assert status.hink_for("boka tvätt", HINKAR) == "auto"
    assert status.hink_for("bestrida faktura", HINKAR) == "aldrig"


def test_okand_kategori_faller_till_standardhinken():
    """RAMVERKSREGEL 1. En kategori ingen tagit ställning till får aldrig
    hamna i `auto`."""
    assert status.hink_for("något helt nytt", HINKAR) == "utkast"


def test_kategori_i_tva_hinkar_larmar():
    """Gränsfall. Vakten mot dubbelt medlemskap ligger i
    `tests/test_kategorier_yaml.py`; faller den ska utfallet bli synligt här
    i stället för att avgöras av ordningen i koden."""
    with pytest.raises(status.Saknas):
        status.hink_for("x", {"standardhink": "utkast",
                              "auto": ["x"], "aldrig": ["x"]})


def test_tomma_hinklistor_ger_standardhinken():
    """Nollfall: filen bär hinkarna men de är tomma."""
    assert status.hink_for("vad som helst",
                           {"standardhink": "utkast",
                            "auto": None, "aldrig": None}) == "utkast"


def test_saknad_standardhink_ar_ett_stopp(tmp_path):
    fil = tmp_path / "h.yaml"
    fil.write_text("auto: []\n", encoding="utf-8")

    with pytest.raises(status.Saknas):
        status.las_hinkar(fil)


def test_okand_standardhink_ar_ett_stopp(tmp_path):
    with pytest.raises(status.Saknas):
        status.las_hinkar(skriv_hinkar(tmp_path / "h.yaml",
                                       standardhink="soptunnan"))


def test_standardhink_auto_ar_ett_stopp(tmp_path):
    """RAMVERKSREGEL 1, gränsfallet.

    `auto` är en giltig hink men en otillåten STANDARDhink: en kategori ingen
    tagit ställning till hade då blivit sändbar av att någon lade till den i
    taxonomin. Att den inte får vara standard är hela poängen med att `utkast`
    är det.
    """
    with pytest.raises(status.Saknas):
        status.las_hinkar(skriv_hinkar(tmp_path / "h.yaml",
                                       standardhink="auto"))


# --- antalen -----------------------------------------------------------------


def test_antalen_delas_pa_kalla(tmp_path):
    fil = skriv_etiketter(tmp_path / "e.jsonl",
                          ("boka tvätt", "med svar"),
                          ("boka tvätt", "utan svar"),
                          ("boka tvätt", "utan svar"))

    assert status.las_antal(fil)["boka tvätt"] == {
        "totalt": 3, "med_svar": 1, "utan_svar": 2}


def test_tom_etikettfil_ger_inga_antal(tmp_path):
    """Nollfall: filen finns men är tom."""
    fil = tmp_path / "e.jsonl"
    fil.write_text("", encoding="utf-8")

    assert status.las_antal(fil) == {}


# --- senaste mining ----------------------------------------------------------


def test_senaste_mining_tar_SISTA_raden_inte_storsta(tmp_path):
    """Raden skrivs in sist i tabellen, i kronologisk ordning. En sortering
    hade tyst rättat en logg i oordning, och den oordningen är i så fall det
    som ska synas."""
    fil = skriv_mining(tmp_path / "m.md",
                       "2026-08-26 16:42 UTC", "2026-01-01 09:00 UTC")

    assert status.senaste_mining(fil)[0] == "2026-01-01 09:00 UTC"


def test_senaste_mining_bar_med_statusen(tmp_path):
    """Statusen följer med, den läses inte bort."""
    fil = skriv_mining(tmp_path / "m.md", "2026-08-26 16:42 UTC")

    assert status.senaste_mining(fil)[1] == "fullständig"


def test_avbruten_korning_varnas(tmp_path, capsys):
    """GRÄNSFALLET. `src/mine.py` loggar även en körning som faller, och
    `AVBRUTEN` betyder att `data/tradar.jsonl` INTE uppdaterades.

    En statusrad som redovisar datumet utan statusen hade påstått färskt
    material där det bara fanns förbrukad kvot.
    """
    fil = tmp_path / "m.md"
    fil.write_text(
        "| Datum | Query | Trådar | Anrop | Kvotenheter | Status |\n"
        "| --- | --- | --- | --- | --- | --- |\n"
        "| 2026-08-26 16:42 UTC | `q` | 1 | 1 | 10 | AVBRUTEN |\n",
        encoding="utf-8")

    rader = status.statusrader({"standardhink": "utkast"}, {}, [],
                               status.senaste_mining(fil))

    text = "\n".join(rader)
    assert "AVBRUTEN" in text
    assert "VARNING" in text
    assert "uppdaterades inte" in text


def test_tabellhuvudet_raknas_inte_som_korning(tmp_path):
    """Gränsfall: en logg utan körningar bär ändå huvud och avgränsare."""
    with pytest.raises(status.Saknas):
        status.senaste_mining(skriv_mining(tmp_path / "m.md"))


# --- unionen av kategorier ---------------------------------------------------


def test_kategori_utan_texter_forsvinner_inte():
    """En taxonomikategori med noll texter ska SYNAS, inte utelämnas."""
    alla = status.alla_kategorier({}, ["boka tvätt", "boka service"], HINKAR)

    assert alla == ["bestrida faktura", "boka service", "boka tvätt",
                    "inget kundärende"]


def test_etikett_utanfor_taxonomin_kommer_med():
    """`inget kundärende`, `oklart` och `utanför listan` står inte i
    taxonomin men är etiketter en text kan bära."""
    alla = status.alla_kategorier({"oklart": {"totalt": 1}}, [], HINKAR)

    assert "oklart" in alla


def test_hinknamngiven_kategori_utan_texter_kommer_med():
    """En hink som namnger något som inte finns någonstans är ett fynd."""
    assert "bestrida faktura" in status.alla_kategorier({}, [], HINKAR)


# --- statusraden i sin helhet ------------------------------------------------


@pytest.fixture
def kallor(tmp_path):
    return {
        "hinkar": skriv_hinkar(tmp_path / "h.yaml"),
        "etiketter": skriv_etiketter(tmp_path / "e.jsonl",
                                     ("boka tvätt", "med svar"),
                                     ("bestrida faktura", "utan svar")),
        "taxonomi": skriv_taxonomi(tmp_path / "t.json", "boka tvätt",
                                   "bestrida faktura", "boka service"),
        "mining": skriv_mining(tmp_path / "m.md", "2026-08-26 16:42 UTC"),
    }


def argument(kallor: dict) -> list[str]:
    return [f"--{namn}={sokvag}" for namn, sokvag in kallor.items()]


def test_statusraden_produceras(kallor, capsys):
    assert status.main(argument(kallor)) == 0

    ut = capsys.readouterr().out
    assert "=== KATEGORISTATUS" in ut
    assert "2026-08-26 16:42 UTC" in ut
    assert "Texter i underlaget: 2" in ut


def test_hinkarnas_summor_stammer(kallor, capsys):
    status.main(argument(kallor))

    ut = capsys.readouterr().out
    assert "| auto | 1 | 1 | 1 | 0 |" in ut
    assert "| aldrig | 2 | 1 | 0 | 1 |" in ut
    assert "| utkast | 1 | 0 | 0 | 0 |" in ut


def test_statusraden_namnger_sina_kallor(kallor, capsys):
    """HÄRKOMSTEN. Utan den vore en rad producerad ur godtyckliga filer
    teckenidentisk med en producerad ur repot, och §12:s krav på att raden inte
    ska gå att skriva för hand hade gått att kringgå med en omväg."""
    status.main(argument(kallor))

    ut = capsys.readouterr().out
    assert "Källor:" in ut
    for sokvag in kallor.values():
        assert sokvag.name in ut


def test_kategori_utan_texter_namnges(kallor, capsys):
    status.main(argument(kallor))

    ut = capsys.readouterr().out
    assert "KATEGORIER UTAN TEXTER" in ut
    assert "boka service" in ut


# --- DET SOM INTE FÅR SKE ----------------------------------------------------


@pytest.mark.parametrize("saknad",
                         ["hinkar", "etiketter", "taxonomi", "mining"])
def test_saknad_kalla_ger_ingen_statusrad(kallor, capsys, saknad):
    """KÄRNAN. En halv statusrad ser komplett ut och är värre än ett hål.

    §12 lät hålet stå hellre än att någon skrev raden för hand.
    Skriptet ska följa samma regel: säg vilken fil som saknas, producera
    ingen tabell, och avsluta med exit 1.
    """
    kallor[saknad].unlink()

    kod = status.main(argument(kallor))

    ut = capsys.readouterr().out
    assert kod == 1
    assert "STATUSRADEN KAN INTE PRODUCERAS" in ut
    assert "=== KATEGORISTATUS" not in ut
    assert "| Hink |" not in ut


def test_saknad_kalla_namnger_filen(kallor, capsys):
    """Hålet ska vara NAMNGIVET, inte bara konstaterat.

    "En källa saknas" duger inte: nästa läsare ska veta vilken.
    """
    saknad = kallor["mining"]
    saknad.unlink()

    status.main(argument(kallor))

    assert saknad.name in capsys.readouterr().out


def test_katalog_i_stallet_for_fil_ger_hal_inte_traceback(tmp_path):
    """En källa som FINNS men inte går att läsa är samma hål som en som saknas.

    Utan vakten gav en katalog `IsADirectoryError` som traceback, alltså precis
    det utfall skriptet finns för att undvika.
    """
    with pytest.raises(status.Saknas):
        status.las_text(tmp_path)


def test_trasig_yaml_ger_hal(tmp_path):
    fil = tmp_path / "h.yaml"
    fil.write_text("standardhink: [olukt\n", encoding="utf-8")

    with pytest.raises(status.Saknas):
        status.las_hinkar(fil)


def test_yaml_av_fel_typ_ger_hal(tmp_path):
    """Gränsfall: filen är giltig YAML men en LISTA, inte en tabell."""
    fil = tmp_path / "h.yaml"
    fil.write_text("- boka tvätt\n", encoding="utf-8")

    with pytest.raises(status.Saknas):
        status.las_hinkar(fil)


def test_trasig_jsonl_ger_hal_med_radnummer(tmp_path):
    """Radnumret, ALDRIG radens innehåll: raderna bär kundtext (§6)."""
    fil = tmp_path / "e.jsonl"
    fil.write_text('{"text": "t", "kalla": "utan svar", "etikett": "x"}\n'
                   "inte json\n", encoding="utf-8")

    with pytest.raises(status.Saknas) as fel:
        status.las_antal(fil)

    assert "rad 2" in str(fel.value)
    assert "inte json" not in str(fel.value)


def test_jsonl_post_utan_etikett_ger_hal(tmp_path):
    """Nollfall: posten finns men saknar det fält räkningen vilar på."""
    fil = tmp_path / "e.jsonl"
    fil.write_text('{"text": "t", "kalla": "utan svar"}\n', encoding="utf-8")

    with pytest.raises(status.Saknas):
        status.las_antal(fil)


def test_taxonomi_av_fel_typ_ger_hal(tmp_path):
    fil = tmp_path / "t.json"
    fil.write_text('{"boka tvätt": 1}', encoding="utf-8")

    with pytest.raises(status.Saknas):
        status.las_taxonomi(fil)


def test_sokvag_utanfor_repot_kraschar_inte(tmp_path):
    """GRÄNSFALLET som `namnge` finns för.

    `Path.relative_to` kastar `ValueError` för en sökväg utanför repot, och
    varje `--hinkar` som pekar någon annanstans går den vägen. Utan vakten föll
    felhanteringen med ett traceback i stället för att skriva ut vilken fil som
    saknades, alltså precis i det läge skriptet finns för.
    """
    utanfor = tmp_path / "finns-inte.yaml"

    with pytest.raises(status.Saknas) as fel:
        status.las_hinkar(utanfor)

    assert str(utanfor) in str(fel.value)


def test_dubbel_hinkmedlemskap_ger_ingen_statusrad(kallor, capsys):
    """Ett motstridigt hinkbeslut får inte tolkas till något. Det ska stoppa."""
    skriv_hinkar(kallor["hinkar"], auto=["bestrida faktura"])

    kod = status.main(argument(kallor))

    assert kod == 1
    assert "=== KATEGORISTATUS" not in capsys.readouterr().out
