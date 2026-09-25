"""`scripts/driftlarm.py`: ETT DRIFTLARM när en körning misslyckats. SKICKAR
ALDRIG. Uppdrag 2026-09-25 DEL 2.

**INGET TEST HÄR RÖR NÄTET.** `gmailutkast.skriv_tjanst` monkeypatchas eller
görs att kasta, precis som `tests/test_gmailutkast.py` gör för `respond.py`
och `serva.py`.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

from src import gmailutkast, vy
from tests.test_gmailutkast import FejkRa

ROT = Path(__file__).resolve().parent.parent
DRIFTLARM = ROT / "scripts" / "driftlarm.py"


def _ladda():
    """`scripts/driftlarm.py` som modul, samma mönster som
    `tests/test_respond.py::_ladda`."""
    spec = importlib.util.spec_from_file_location(
        "driftlarm_under_test", DRIFTLARM)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


driftlarm = _ladda()

TID = "2026-09-25T12:00:00+00:00"


def test_tid_och_exitkod_KRAVS():
    """SPÄRR: ett larm utan tid eller exitkod är ingen giltig anrop."""
    with pytest.raises(SystemExit):
        driftlarm.main([])
    with pytest.raises(SystemExit):
        driftlarm.main(["--tid", TID])


def test_utan_skrivtjanst_ger_1_och_skriver_INGEN_traceback(monkeypatch,
                                                            capsys):
    """Saknad `token-skriv.json` ska fällas som ett diagnostiskt FEL, inte
    som ett okänt kastat undantag."""
    def kraschar(**_kwargs):
        raise FileNotFoundError("token-skriv.json saknas")
    monkeypatch.setattr(driftlarm.gmailutkast, "skriv_tjanst", kraschar)

    kod = driftlarm.main(["--tid", TID, "--exitkod", "1", "--fel", "boom"])

    assert kod == 1
    assert "FEL" in capsys.readouterr().out


def test_ett_lyckat_larm_ger_0_och_skriver_INGENTING_till_disk(
        monkeypatch, capsys, tmp_path):
    """§6, och drifttarmets egen docstring: filen skriver ingenting till
    disk. Throttlingen är anroparens ansvar."""
    ra = FejkRa(tradsvar=lambda kw: "ny-fristaende-trad")
    monkeypatch.setattr(driftlarm.gmailutkast, "skriv_tjanst",
                        lambda **_kwargs: gmailutkast.Utkastjanst(ra))
    monkeypatch.chdir(tmp_path)

    kod = driftlarm.main(["--tid", TID, "--exitkod", "1", "--fel", "boom"])

    assert kod == 0
    ut = capsys.readouterr().out
    assert "DRIFTLARM skapat" in ut
    assert "m-1" in ut
    assert "INTE skickat" in ut
    assert [namn for namn, _ in ra.logg] == ["create"]
    assert not list(tmp_path.rglob("*")), "filen skrev något till disk"


def test_ett_MISSLYCKAT_larm_ger_1(monkeypatch, capsys):
    """Ett fel EFTER att tjänsten byggts (nätverksfel, kvottak) ska också ge
    ett diagnostiskt FEL, inte ett okänt kastat undantag."""
    class _KraschandeTjanst:
        def users(self):
            raise RuntimeError("nätverksfel")

    monkeypatch.setattr(driftlarm.gmailutkast, "skriv_tjanst",
                        lambda **_kwargs: _KraschandeTjanst())

    kod = driftlarm.main(["--tid", TID, "--exitkod", "1", "--fel", "boom"])

    assert kod == 1
    assert "FEL" in capsys.readouterr().out


def test_KOR_sandvagssparren_FORE_tjansten_byggs(monkeypatch):
    """Samma mönster som `test_serva_KOR_sparren_vid_start`: en onamngiven
    Gmail-modul i grafen ska fällas vid uppstart, INNAN något Gmail-anrop
    görs."""
    anrop = []

    def fall(*a, **k):
        anrop.append((a, k))
        raise vy.Sandvagsfel("prov")
    monkeypatch.setattr(driftlarm.vy, "krav_pa_sandvagsfrihet", fall)

    def kraschar_om_anropad(**_kwargs):
        raise AssertionError("tjänsten byggdes trots att spärren fällde")
    monkeypatch.setattr(driftlarm.gmailutkast, "skriv_tjanst",
                        kraschar_om_anropad)

    with pytest.raises(vy.Sandvagsfel):
        driftlarm.main(["--tid", TID, "--exitkod", "1", "--fel", "boom"])

    assert anrop == [(("scripts.driftlarm",), {"tillatna": vy.UNDANTAGBARA})]


def test_driftlarm_KLARAR_den_riktiga_sparren():
    """NEGATIVKONTROLL, oberoende av testerna ovan: den verkliga
    `krav_pa_sandvagsfrihet` ska släppa igenom modulens egen graf."""
    vy.krav_pa_sandvagsfrihet("scripts.driftlarm", tillatna=vy.UNDANTAGBARA)
