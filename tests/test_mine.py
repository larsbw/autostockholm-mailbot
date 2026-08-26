"""Tester för src/mine.py mot en fejkad Gmail-tjänst.

Ingen brevlåda rörs. Påståenden som säger att något INTE sker (fler sidor hämtas
inte, messages.get används aldrig, ett behörighetsfel görs aldrig om) är de som
prövas enligt CLAUDE.md §7.1.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest
from googleapiclient.errors import HttpError

from src import mine
from tests import fejk


def trad(id_, antal_meddelanden=1):
    return {
        "id": id_,
        "historyId": "17",
        "messages": [
            {"id": f"{id_}-m{n}", "labelIds": ["SENT"]}
            for n in range(antal_meddelanden)
        ],
    }


def snabb_pacer():
    """Pacer som räknar rätt men aldrig sover på riktigt."""
    return mine.Kvotpacer(sov=lambda _: None)


def tva_sidor():
    return {
        None: {
            "threads": [{"id": "t1"}, {"id": "t2"}],
            "nextPageToken": "sida2",
        },
        "sida2": {"threads": [{"id": "t3"}]},
    }


def tre_tradar():
    return {"t1": trad("t1"), "t2": trad("t2", 3), "t3": trad("t3", 2)}


def kor(gmail, tmp_path, **kw):
    utfil = tmp_path / "tradar.jsonl"
    forbrukning = mine.mina(
        gmail, utfil=utfil, pacer=snabb_pacer(), sov=lambda _: None, **kw
    )
    return utfil, forbrukning


def rader(utfil):
    text = utfil.read_text(encoding="utf-8")
    return [json.loads(rad) for rad in text.splitlines() if rad]


def test_alla_tradar_over_flera_sidor_hamtas(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    utfil, forbrukning = kor(gmail, tmp_path)

    assert rader(utfil) == [trad("t1"), trad("t2", 3), trad("t3", 2)]
    assert forbrukning.tradar == 3


def test_fragan_hamtar_tradar_med_minst_ett_skickat_meddelande(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    kor(gmail, tmp_path)

    assert gmail.list_anrop[0]["q"] == "in:sent"
    assert mine.FRAGA == "in:sent"


def test_hela_traden_hamtas_i_ett_anrop_och_messages_get_anvands_aldrig(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    kor(gmail, tmp_path)

    assert [anrop["id"] for anrop in gmail.get_anrop] == ["t1", "t2", "t3"]
    assert gmail.messages_anrop == []


def test_max_threads_stoppar_innan_nasta_sida_hamtas(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    utfil, forbrukning = kor(gmail, tmp_path, max_tradar=2)

    assert len(gmail.list_anrop) == 1
    assert [anrop["id"] for anrop in gmail.get_anrop] == ["t1", "t2"]
    assert len(rader(utfil)) == 2
    assert forbrukning.tradar == 2


def test_max_threads_lika_med_totalen_hamtar_allt(tmp_path):
    sidor = {None: {"threads": [{"id": "t1"}, {"id": "t2"}, {"id": "t3"}]}}
    gmail = fejk.FejkGmail(sidor, tre_tradar())

    utfil, _ = kor(gmail, tmp_path, max_tradar=3)

    assert len(gmail.list_anrop) == 1
    assert len(rader(utfil)) == 3


def test_max_threads_noll_ger_inga_anrop_alls(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    utfil, forbrukning = kor(gmail, tmp_path, max_tradar=0)

    assert gmail.list_anrop == []
    assert gmail.get_anrop == []
    assert not utfil.exists()
    assert forbrukning.enheter == 0


def test_max_threads_noll_raderar_inte_foregaende_skord(tmp_path):
    utfil = tmp_path / "tradar.jsonl"
    utfil.write_text('{"id": "tidigare-skord"}\n', encoding="utf-8")
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    mine.mina(
        gmail, utfil=utfil, max_tradar=0, pacer=snabb_pacer(),
        sov=lambda _: None,
    )

    assert rader(utfil) == [{"id": "tidigare-skord"}]
    assert not (tmp_path / "tradar.jsonl.delvis").exists()


def test_tom_brevlada_ger_tom_utfil(tmp_path):
    gmail = fejk.FejkGmail({None: {}}, {})

    utfil, forbrukning = kor(gmail, tmp_path)

    assert gmail.get_anrop == []
    assert rader(utfil) == []
    assert forbrukning.enheter == mine.KOSTNAD_THREADS_LIST


def test_trad_utan_meddelanden_skrivs_anda(tmp_path):
    tom = {"id": "t1", "historyId": "17", "messages": []}
    gmail = fejk.FejkGmail({None: {"threads": [{"id": "t1"}]}}, {"t1": tom})

    utfil, _ = kor(gmail, tmp_path)

    assert rader(utfil) == [tom]


# --- kvot och pacing ---------------------------------------------------------


def test_kvottabellens_varden_ar_de_avlasta():
    assert mine.KOSTNAD_THREADS_LIST == 10
    assert mine.KOSTNAD_THREADS_GET == 40
    assert mine.KVOT_PER_ANVANDARE_PER_MINUT == 6000


def test_pacingen_dimensioneras_mot_anvandarkvoten():
    assert mine.ENHETER_PER_MINUT == 3000
    tradar_per_minut = mine.ENHETER_PER_MINUT / mine.KOSTNAD_THREADS_GET
    assert tradar_per_minut == 75


def test_atgangen_kvot_raknas_ur_tabellen(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    _, forbrukning = kor(gmail, tmp_path)

    assert forbrukning.anrop == 5
    assert forbrukning.enheter == (
        2 * mine.KOSTNAD_THREADS_LIST + 3 * mine.KOSTNAD_THREADS_GET
    )


def test_pacern_sprider_ut_anropen_efter_kostnad():
    sov = fejk.Sovlogg()
    pacer = mine.Kvotpacer(enheter_per_minut=3000, sov=sov, klocka=fejk.Klocka(sov))

    pacer.vanta(mine.KOSTNAD_THREADS_GET)
    pacer.vanta(mine.KOSTNAD_THREADS_GET)

    assert sov.sovtider == [pytest.approx(0.8)]


def test_forsta_anropet_vantar_inte():
    sov = fejk.Sovlogg()
    pacer = mine.Kvotpacer(enheter_per_minut=3000, sov=sov, klocka=fejk.Klocka(sov))

    pacer.vanta(mine.KOSTNAD_THREADS_LIST)

    assert sov.sovtider == []


def test_nollkostnad_ger_ingen_vantan():
    sov = fejk.Sovlogg()
    pacer = mine.Kvotpacer(enheter_per_minut=3000, sov=sov, klocka=fejk.Klocka(sov))

    pacer.vanta(0)
    pacer.vanta(0)

    assert sov.sovtider == []


# --- backoff -----------------------------------------------------------------


def test_ar_kvotfel_kanner_igen_de_dokumenterade_fallen():
    assert mine.ar_kvotfel(fejk.httpfel(429, "userRateLimitExceeded"))
    assert mine.ar_kvotfel(fejk.httpfel(429, "rateLimitExceeded"))
    assert mine.ar_kvotfel(fejk.httpfel(403, "rateLimitExceeded"))
    assert mine.ar_kvotfel(fejk.httpfel(403, "dailyLimitExceeded"))
    assert mine.ar_kvotfel(fejk.httpfel(403, "userRateLimitExceeded"))


def test_ar_kvotfel_slapper_igenom_det_som_inte_ar_kvottak():
    assert not mine.ar_kvotfel(fejk.httpfel(403, "insufficientPermissions"))
    assert not mine.ar_kvotfel(fejk.httpfel(404, "notFound"))
    assert not mine.ar_kvotfel(fejk.httpfel(500, "backendError"))
    assert not mine.ar_kvotfel(ValueError("inte ett httpfel"))


def test_fordrojningen_ar_exponentiell_och_har_en_sekund_som_golv():
    assert mine.fordrojning(0, lambda: 0.0) == 1.0
    assert mine.fordrojning(1, lambda: 0.0) == 2.0
    assert mine.fordrojning(2, lambda: 0.0) == 4.0


def test_jittern_laggs_ovanpa_basen():
    assert mine.fordrojning(0, lambda: 1.0) == 2.0
    assert mine.fordrojning(0, lambda: 0.5) == 1.5


def test_429_gor_om_anropet_med_vaxande_fordrojning(tmp_path):
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.kvotfel(), fejk.kvotfel()]},
    )
    sov = fejk.Sovlogg()
    utfil = tmp_path / "tradar.jsonl"

    forbrukning = mine.mina(
        gmail, utfil=utfil, pacer=snabb_pacer(), sov=sov, slumpa=lambda: 0.5
    )

    assert sov.sovtider == [1.5, 3.0]
    assert len(gmail.get_anrop) == 3
    assert rader(utfil) == [trad("t1")]
    assert forbrukning.enheter == (
        mine.KOSTNAD_THREADS_LIST + 3 * mine.KOSTNAD_THREADS_GET
    )


def test_behorighetsfel_gors_aldrig_om(tmp_path):
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.behorighetsfel()]},
    )
    sov = fejk.Sovlogg()

    with pytest.raises(HttpError):
        mine.mina(
            gmail,
            utfil=tmp_path / "tradar.jsonl",
            pacer=snabb_pacer(),
            sov=sov,
            slumpa=lambda: 0.5,
        )

    assert len(gmail.get_anrop) == 1
    assert sov.sovtider == []


def test_kvottak_som_kvarstar_ger_upp_efter_max_forsok(tmp_path):
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.kvotfel() for _ in range(mine.MAX_FORSOK)]},
    )
    sov = fejk.Sovlogg()

    with pytest.raises(mine.KvotfelKvarstar):
        mine.mina(
            gmail,
            utfil=tmp_path / "tradar.jsonl",
            pacer=snabb_pacer(),
            sov=sov,
            slumpa=lambda: 0.0,
        )

    assert len(gmail.get_anrop) == mine.MAX_FORSOK
    assert len(sov.sovtider) == mine.MAX_FORSOK - 1


def test_fallda_anrop_kostar_kvot(tmp_path):
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.kvotfel() for _ in range(mine.MAX_FORSOK)]},
    )
    forbrukning = mine.Forbrukning()

    with pytest.raises(mine.KvotfelKvarstar):
        mine.mina(
            gmail,
            utfil=tmp_path / "tradar.jsonl",
            pacer=snabb_pacer(),
            forbrukning=forbrukning,
            sov=lambda _: None,
            slumpa=lambda: 0.0,
        )

    assert forbrukning.enheter == (
        mine.KOSTNAD_THREADS_LIST + mine.MAX_FORSOK * mine.KOSTNAD_THREADS_GET
    )


# --- mining-logg -------------------------------------------------------------


RUBRIKRAD = "| Datum | Query | Trådar | Anrop | Kvotenheter | Status |\n"
STAMPEL = datetime(2026, 8, 26, 9, 5, tzinfo=timezone.utc)


def test_mining_loggen_appendas_utan_att_rora_befintligt(tmp_path):
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")
    forbrukning = mine.Forbrukning()
    forbrukning.tradar = 3
    forbrukning.anrop = 5
    forbrukning.enheter = 140
    forbrukning.fullstandig = True

    rad = mine.logga_korning(forbrukning, logg=logg, nu=STAMPEL)

    text = logg.read_text(encoding="utf-8")
    assert text.startswith(RUBRIKRAD)
    assert rad in text
    assert "2026-08-26 09:05 UTC" in rad
    assert "`in:sent`" in rad
    assert "| 3 | 5 | 140 | fullständig |" in rad


def test_avbruten_korning_loggas_som_avbruten(tmp_path):
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")
    forbrukning = mine.Forbrukning()
    forbrukning.tradar = 1
    forbrukning.anrop = 7
    forbrukning.enheter = 250

    rad = mine.logga_korning(forbrukning, logg=logg, nu=STAMPEL)

    assert "| 1 | 7 | 250 | AVBRUTEN |" in rad


# --- avbrott lämnar utfilen orörd --------------------------------------------


def test_avbruten_hamtning_ror_inte_utfilen(tmp_path):
    utfil = tmp_path / "tradar.jsonl"
    utfil.write_text('{"id": "gammal"}\n', encoding="utf-8")
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}, {"id": "t2"}]}},
        {"t1": trad("t1"), "t2": trad("t2")},
        get_fel={"t2": [fejk.behorighetsfel()]},
    )

    with pytest.raises(HttpError):
        mine.mina(
            gmail, utfil=utfil, pacer=snabb_pacer(), sov=lambda _: None
        )

    assert rader(utfil) == [{"id": "gammal"}]
    assert (tmp_path / "tradar.jsonl.delvis").exists()


def test_fullstandig_flagga_satts_forst_nar_allt_ar_hamtat(tmp_path):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())

    _, forbrukning = kor(gmail, tmp_path)

    assert forbrukning.fullstandig is True


# --- CLI ---------------------------------------------------------------------


def test_main_skickar_max_threads_vidare(tmp_path, monkeypatch):
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")

    monkeypatch.setattr(mine.auth, "hamta_credentials", lambda **kw: "fejk-cred")
    monkeypatch.setattr(mine.auth, "bygg_tjanst", lambda cred: gmail)
    monkeypatch.setattr(mine, "UTFIL", tmp_path / "tradar.jsonl")
    monkeypatch.setattr(mine, "MININGLOGG", logg)
    monkeypatch.setattr(mine.time, "sleep", lambda _: None)

    utfall = mine.main(["--max-threads", "1"])

    assert utfall == 0
    assert [anrop["id"] for anrop in gmail.get_anrop] == ["t1"]
    assert len(rader(tmp_path / "tradar.jsonl")) == 1
    assert "| 1 | 2 | 50 | fullständig |" in logg.read_text(encoding="utf-8")


def test_pacerns_sovfunktion_gar_att_byta_ut_utifran(tmp_path, monkeypatch):
    """main() tar ingen sov-parameter, så sviten kan bara hålla den vaken
    genom att byta ut mine.time.sleep. Slås den upp som defaultvärde i stället
    för vid anropet når utbytet aldrig fram, och sviten sover på riktigt utan
    att någon märker det."""
    gmail = fejk.FejkGmail(tva_sidor(), tre_tradar())
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")
    sov = fejk.Sovlogg()

    monkeypatch.setattr(mine.auth, "hamta_credentials", lambda **kw: "fejk-cred")
    monkeypatch.setattr(mine.auth, "bygg_tjanst", lambda cred: gmail)
    monkeypatch.setattr(mine, "UTFIL", tmp_path / "tradar.jsonl")
    monkeypatch.setattr(mine, "MININGLOGG", logg)
    monkeypatch.setattr(mine.time, "sleep", sov)

    mine.main([])

    assert sov.sovtider, "mine.time.sleep byttes ut men anropades aldrig"
    assert all(vantan > 0 for vantan in sov.sovtider)


def test_main_auktoriserar_aldrig_pa_egen_hand(tmp_path, monkeypatch):
    gmail = fejk.FejkGmail({None: {}}, {})
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")
    argument = []

    def fejk_hamta(**kw):
        argument.append(kw)
        return "fejk-cred"

    monkeypatch.setattr(mine.auth, "hamta_credentials", fejk_hamta)
    monkeypatch.setattr(mine.auth, "bygg_tjanst", lambda cred: gmail)
    monkeypatch.setattr(mine, "UTFIL", tmp_path / "tradar.jsonl")
    monkeypatch.setattr(mine, "MININGLOGG", logg)
    monkeypatch.setattr(mine.time, "sleep", lambda _: None)

    mine.main([])

    assert argument == [{"tillat_webblasare": False}]


def test_main_loggar_kvoten_aven_nar_korningen_faller(tmp_path, monkeypatch):
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.behorighetsfel()]},
    )
    logg = tmp_path / "mining-log.md"
    logg.write_text(RUBRIKRAD, encoding="utf-8")

    monkeypatch.setattr(mine.auth, "hamta_credentials", lambda **kw: "fejk-cred")
    monkeypatch.setattr(mine.auth, "bygg_tjanst", lambda cred: gmail)
    monkeypatch.setattr(mine, "UTFIL", tmp_path / "tradar.jsonl")
    monkeypatch.setattr(mine, "MININGLOGG", logg)
    monkeypatch.setattr(mine.time, "sleep", lambda _: None)

    with pytest.raises(HttpError):
        mine.main([])

    text = logg.read_text(encoding="utf-8")
    assert "AVBRUTEN" in text
    assert f"| 0 | 2 | {mine.KOSTNAD_THREADS_LIST + mine.KOSTNAD_THREADS_GET} |" in text


def test_loggfel_maskerar_inte_felet_fran_hamtningen(tmp_path, monkeypatch):
    """Faller både hämtningen och loggskrivningen är det hämtningens fel
    operatören behöver se. Loggfelet rapporteras vid sidan av."""
    gmail = fejk.FejkGmail(
        {None: {"threads": [{"id": "t1"}]}},
        {"t1": trad("t1")},
        get_fel={"t1": [fejk.behorighetsfel()]},
    )

    def trasig_logg(forbrukning, **kw):
        raise OSError("mining-log går inte att skriva")

    monkeypatch.setattr(mine.auth, "hamta_credentials", lambda **kw: "fejk-cred")
    monkeypatch.setattr(mine.auth, "bygg_tjanst", lambda cred: gmail)
    monkeypatch.setattr(mine, "UTFIL", tmp_path / "tradar.jsonl")
    monkeypatch.setattr(mine, "logga_korning", trasig_logg)
    monkeypatch.setattr(mine.time, "sleep", lambda _: None)

    with pytest.raises(HttpError):
        mine.main([])
