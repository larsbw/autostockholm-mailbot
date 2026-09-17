"""DRIFTEN: sökvägar, inloggning, bindning och det dagliga schemat. Skiva 53.

`docs/beslutslogg.md` #37 och #38, samt #119 som bygger dem.

**INGEN KUNDTEXT (§6).** Varje adress och varje nyckel här är påhittad.
**INGET TEST RÖR NÄTET.** Tokenutbytet tar sin öppnare som argument.
"""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import inloggning, sokvagar, vy

ROT = Path(__file__).resolve().parent.parent


def konfiguration(**andrat) -> inloggning.Konfiguration:
    grund = {
        "klient_id": "123456789012-exempel.apps.googleusercontent.com",
        "klient_hemlighet": "PAHITTAD-HEMLIGHET",
        "omdirigering": "https://mailagent.dasher.se/atervand",
        "sessionsnyckel": b"x" * 40,
    }
    grund.update(andrat)
    return inloggning.Konfiguration(**grund)


def anspraken(**andrat) -> dict:
    grund = {
        "iss": "https://accounts.google.com",
        "aud": konfiguration().klient_id,
        "exp": time.time() + 600,
        "hd": "autostockholm.se",
        "email_verified": True,
        "email": "info@autostockholm.se",
    }
    grund.update(andrat)
    return grund


# ------------------------------------------------------------- SÖKVÄGARNA


def test_forvalen_ar_REPOTS_EGNA_alltsa_oforandrat_lokalt(monkeypatch):
    """SPÄRR: en omläggning av sökvägar får inte ändra något utan att någon ber om det.

    Villkoret för att skiva 53 fick göra omläggningen alls: utan miljövariabler
    pekar allt precis där det pekade före skivan.
    """
    for namn in ("MAILBOT_DATA", "MAILBOT_LOGG", "MAILBOT_HEMLIGHETER"):
        monkeypatch.delenv(namn, raising=False)

    assert sokvagar._ur_miljon("MAILBOT_DATA", ROT / "data") == ROT / "data"
    assert sokvagar._ur_miljon("MAILBOT_LOGG", ROT / "logg") == ROT / "logg"
    assert sokvagar._ur_miljon("MAILBOT_HEMLIGHETER", ROT) == ROT


def test_ett_TOMT_varde_raknas_som_OSATT(monkeypatch):
    """SPÄRR: `MAILBOT_DATA=` i en Railway-panel får inte bli arbetskatalogen.

    Utan raden blir en tom ruta `Path("")`, alltså `.`, och boten skriver
    kundtext till containerns arbetskatalog. Det försvinner vid nästa deploy och
    hamnar dessutom utanför volymen, vilket är precis vad #38 binder mot.
    """
    monkeypatch.setenv("MAILBOT_DATA", "   ")

    assert sokvagar._ur_miljon("MAILBOT_DATA", ROT / "data") == ROT / "data"


def test_miljovariabeln_STYR_nar_den_ar_satt(monkeypatch):
    """NEGATIVKONTROLL till de två raderna ovan.

    Utan den vore "returnera alltid förvalet" en grön lösning, och då hade
    volymen aldrig använts.
    """
    monkeypatch.setenv("MAILBOT_DATA", "/volym/data")

    assert sokvagar._ur_miljon("MAILBOT_DATA", ROT / "data") == Path("/volym/data")


def test_hemligheterna_har_en_EGEN_variabel_skild_fran_data(monkeypatch):
    """SPÄRR: credentials och kundtext ska gå att lägga på var sitt ställe.

    §6 och #38:s öppna punkt ur #20: de två är olika slags hemligheter med olika
    konsekvenser om de läcker. En gemensam variabel hade gjort det omöjligt att
    ge dem olika rättigheter.
    """
    monkeypatch.setenv("MAILBOT_DATA", "/volym/data")
    monkeypatch.setenv("MAILBOT_HEMLIGHETER", "/volym/hemligheter")

    assert sokvagar._ur_miljon("MAILBOT_DATA", ROT / "data") != \
        sokvagar._ur_miljon("MAILBOT_HEMLIGHETER", ROT)


@pytest.mark.parametrize("namn, mal", [
    ("MAILBOT_DATA", "src"),
    ("MAILBOT_DATA", "config"),
    ("MAILBOT_DATA", "docs"),
    ("MAILBOT_DATA", "logg"),
    ("MAILBOT_LOGG", "src"),
    ("MAILBOT_LOGG", "data"),
    ("MAILBOT_LOGG", "tests"),
    ("MAILBOT_HEMLIGHETER", "src"),
    ("MAILBOT_HEMLIGHETER", "data"),
])
def test_en_katalogvariabel_far_INTE_peka_in_i_repot(namn, mal, monkeypatch):
    """SPÄRR: en miljövariabel får inte kunna skriva kundtext till en SPÅRAD katalog.

    **DEN HÄR LUCKAN ÖPPNADES AV SKIVAN SJÄLV.** Före den hårdkodade
    `vy.krav_pa_skrivbar_sokvag` `data/` och `logg/` under repots rot, alltså var
    en skrivning till `src/` omöjlig oavsett konfiguration. När katalogerna blev
    flyttbara blev de flyttbara också TILLBAKA IN i repot: uppmätt släppte
    spärren igenom en skrivning till `src/` med `MAILBOT_LOGG` pekad dit.

    **DET ÄR DEN TYSTASTE FORMEN AV §6-LÄCKA.** Filen hamnar i git i stället för
    hos Railway, alltså på ett ställe där den inte går att ta bort i efterhand.

    `logg` för `MAILBOT_DATA` och `data` för `MAILBOT_LOGG` står med: de är
    gitignorerade, men de är fel katalog, och två variabler som pekar på samma
    ställe är ett driftfel värt att fälla.
    """
    monkeypatch.setenv(namn, str(ROT / mal))

    with pytest.raises(sokvagar.Sokvagsfel) as fel:
        sokvagar._ur_miljon(namn, ROT / "data")

    assert namn in str(fel.value)
    assert mal in str(fel.value)


@pytest.mark.parametrize("namn, mal", [
    ("MAILBOT_DATA", "data"),
    ("MAILBOT_LOGG", "logg"),
    ("MAILBOT_HEMLIGHETER", ""),
])
def test_det_LAGLIGA_laget_i_repot_slapps_igenom(namn, mal, monkeypatch):
    """NEGATIVKONTROLL: utan den vore "vägra allt i repot" en grön lösning.

    Då hade den lokala körningen slutat fungera, eftersom förvalen ÄR de här
    lägena. `MAILBOT_HEMLIGHETER` får peka på repotets rot: det är där
    `token.json`, `token-las.json` och `client_secret.json` ligger, alla
    gitignorerade var för sig.
    """
    monkeypatch.setenv(namn, str(ROT / mal) if mal else str(ROT))

    assert sokvagar._ur_miljon(namn, ROT / "data") == (ROT / mal if mal else ROT)


def test_en_katalog_UTANFOR_repot_provas_inte(monkeypatch):
    """Volymen är driftens sak, och regeln gäller bara repots egen gräns."""
    monkeypatch.setenv("MAILBOT_DATA", "/volym/data")

    assert sokvagar._ur_miljon("MAILBOT_DATA", ROT / "data") == Path("/volym/data")


def test_config_FLYTTAR_INTE(monkeypatch):
    """SPÄRR: `config/` är §10-grindad och ska ändras genom en deploy.

    `priser.json` och `fakta.json` bär det boten får påstå om pris och om oss.
    Gick de att peka om med en miljövariabel kunde någon byta ut dem på en
    server utan att repot såg det, och §10:s stopp vore verkningslöst.
    """
    from src import generera

    monkeypatch.setenv("MAILBOT_DATA", "/volym/data")

    assert generera.PRISER == generera.ROT / "config" / "priser.json"
    assert generera.FAKTA == generera.ROT / "config" / "fakta.json"


# --------------------------------------------------------- SKRIVSPÄRREN


def test_skrivsparren_FOLJER_MED_katalogerna(tmp_path, monkeypatch):
    """SPÄRR: spärren mäter mot katalogerna och inte mot repot. Skiva 53.

    **UTAN DEN HÄR RADEN FALLER VARJE SKRIVNING I DRIFT.** Formen var
    `relative_to(ROT)` plus ett krav på att första leden heter `data` eller
    `logg`. På volymen ligger katalogerna utanför repot helt, alltså hade varje
    skrivning kastat `Skrivfel` och boten stått still.
    """
    monkeypatch.setattr(vy, "DATAKATALOG", tmp_path / "volym" / "data")
    monkeypatch.setattr(vy, "LOGGKATALOG", tmp_path / "volym" / "logg")

    vy.krav_pa_skrivbar_sokvag(tmp_path / "volym" / "data" / "par.jsonl")
    vy.krav_pa_skrivbar_sokvag(tmp_path / "volym" / "logg" / "beslut.jsonl")


def test_skrivsparren_VAGRAR_fortfarande_utanfor_de_tva(tmp_path, monkeypatch):
    """NEGATIVKONTROLL: spärren blev inte svagare av att katalogerna kan flytta.

    Utan den här raden vore "tillåt allt" en grön lösning på raden ovan, och då
    kunde vyn skriva rå kundtext var som helst.
    """
    monkeypatch.setattr(vy, "DATAKATALOG", tmp_path / "volym" / "data")
    monkeypatch.setattr(vy, "LOGGKATALOG", tmp_path / "volym" / "logg")

    for utanfor in (tmp_path / "volym" / "annat" / "fil.jsonl",
                    tmp_path / "fil.jsonl",
                    Path("/tmp/lackt.jsonl")):
        with pytest.raises(vy.Skrivfel):
            vy.krav_pa_skrivbar_sokvag(utanfor)


def test_skrivsparren_vagrar_KATALOGEN_SJALV(tmp_path, monkeypatch):
    """En skrivfunktion ska inte skriva över en katalog, och felet ska vara vårt.

    Formen är fälld fram av §7-granskningen av skiva 27: `parts[0]` kastade
    `IndexError` i stället för `Skrivfel`, alltså slapp den som fångade
    `Skrivfel` igenom ett fel den trodde sig täcka.
    """
    monkeypatch.setattr(vy, "DATAKATALOG", tmp_path / "data")
    monkeypatch.setattr(vy, "LOGGKATALOG", tmp_path / "logg")

    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(tmp_path / "data")


# ---------------------------------------------------- BINDNING OCH INLOGGNING


def test_vyn_VAGRAR_binda_utat_utan_inloggning():
    """SKIVANS VIKTIGASTE RAD. §6.

    Fram till skiva 53 hindrades omvärlden av att `starta` band `127.0.0.1`.
    Railway kräver `0.0.0.0`, alltså måste den spärren bort. Kvar blir
    inloggningen, som är ett svagare skydd: den ligger i vår kod.

    **UTAN DEN HÄR RADEN GÅR BINDNINGEN ATT VIDGA MEDAN INLOGGNINGEN ÄR OSATT**,
    och då ligger rå kundtext öppet på internet utan att något blir rött.
    """
    with pytest.raises(vy.Oskyddad):
        vy.starta(port=0, fall=[], adress="0.0.0.0", konfiguration=None)


# FÖRVALET, alltså att `starta` utan adress binder loopback, prövas av
# `tests/test_vy.py::test_servern_binder_bara_loopback`. En rad med samma kropp
# stod här och var en ordagrann dubblett. Struken av §7-granskningen av skiva 53.


def test_vyn_FAR_binda_utat_nar_inloggningen_finns():
    """NEGATIVKONTROLL: spärren får inte göra driften omöjlig.

    Utan den vore "vägra alltid" en grön lösning på raden ovan, och då gick
    #38 inte att bygga alls.
    """
    server = vy.starta(port=0, fall=[], adress="127.0.0.1",
                       konfiguration=konfiguration())
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()

    vy.krav_pa_inloggning_utanfor_loopback("0.0.0.0", konfiguration())


# ------------------------------------------------------ ANSPRÅKEN, LED FÖR LED


def test_ETT_GILTIGT_anspraksset_slapps_igenom():
    """NEGATIVKONTROLL till de sex raderna nedan.

    Utan den vore "neka alltid" en grön lösning, och då gick ingen in i vyn.
    """
    assert inloggning.krav_pa_anspraken(anspraken(), konfiguration()) == \
        "info@autostockholm.se"


@pytest.mark.parametrize("andrat, vad", [
    ({"iss": "https://ond.example"}, "utfärdare"),
    ({"aud": "en-annan-klient.apps.googleusercontent.com"}, "annan klient"),
    ({"exp": time.time() - 1}, "utgången"),
    ({"hd": "annanfirma.se"}, "fel organisation"),
    ({"hd": None}, "ingen organisation"),
    ({"email_verified": False}, "overifierad"),
    ({"email": "nagon@autostockholm.se"}, "fel adress i rätt organisation"),
])
def test_varje_LED_i_anspraken_faller_FOR_SIG(andrat, vad):
    """SPÄRR: sju led, sju rader. §7.1.

    Fälls två tillsammans och sviten blir röd vet man bara att minst ett bär.

    **RADEN MED EN ANNAN ADRESS PÅ DOMÄNEN ÄR DEN VIKTIGASTE.** En sådan klarar
    `hd`-kontrollen: den ligger på domänen och Googles Internal-spärr släpper
    igenom den. Bara adresskontrollen fäller den, och #37 säger att inloggningen
    sker som info@ och som ingen annan.

    **ADRESSEN ÄR PÅHITTAD OCH TILLHÖR INGEN.** §6 gäller allt som pushas, och
    att `scripts/persondatakontroll.py` inte granskar `tests/` är en egenskap hos
    hooken och inte en gräns för regeln. Lars beslut i skiva 53.
    """
    with pytest.raises(inloggning.Inloggningsfel):
        inloggning.krav_pa_anspraken(anspraken(**andrat), konfiguration())


# ------------------------------------------------------------- SESSIONEN


def test_en_session_overlever_en_tur_genom_kakan():
    """Grundfallet: skapa, läs tillbaka, samma adress."""
    kon = konfiguration()
    kaka = inloggning.skapa_session("info@autostockholm.se", kon)

    assert inloggning.las_session(kaka, kon) == "info@autostockholm.se"


def test_en_FORFALSKAD_session_avvisas():
    """SPÄRR: signaturen är det enda som gör kakan värd något.

    Utan den kan vem som helst skriva `info@autostockholm.se|9999999999|x` i en
    kaka och läsa hela materialet.
    """
    kon = konfiguration()
    akta = inloggning.skapa_session("info@autostockholm.se", kon)
    nyttolast, _, _ = akta.rpartition("|")

    assert inloggning.las_session(f"{nyttolast}|0" * 1, kon) is None
    assert inloggning.las_session(f"{nyttolast}|deadbeef", kon) is None
    assert inloggning.las_session("info@autostockholm.se|9999999999|x", kon) is None


def test_en_session_signerad_med_EN_ANNAN_NYCKEL_avvisas():
    """SPÄRR: nyckeln ska faktiskt gå in i signaturen.

    Utan det ledet är varje sessionsnyckel likvärdig, alltså skyddar den inget.
    """
    kaka = inloggning.skapa_session("info@autostockholm.se", konfiguration())

    assert inloggning.las_session(
        kaka, konfiguration(sessionsnyckel=b"y" * 40)
    ) is None


def test_en_UTGANGEN_session_avvisas():
    """SPÄRR: utgången prövas, annars gäller en kaka för alltid."""
    kon = konfiguration()
    kaka = inloggning.skapa_session(
        "info@autostockholm.se", kon, nu=time.time() - inloggning.SESSION_SEKUNDER - 10
    )

    assert inloggning.las_session(kaka, kon) is None


def test_en_session_for_EN_ANNAN_ADRESS_avvisas():
    """SPÄRR: ändras `INLOGGAD_ADRESS` ska varje gammal kaka sluta gälla.

    Kakan är signerad med vår nyckel, alltså är adressen äkta. Raden finns för
    dagen adressen ändras: utan den gäller den gamla tills den går ut.
    """
    kon = konfiguration()
    kaka = inloggning.skapa_session("nagon@autostockholm.se", kon)

    assert inloggning.las_session(kaka, kon) is None


def test_kaksatsen_bar_SAMTLIGA_skydd():
    """SPÄRR: en kaka utan de här flaggorna är en kaka som läcker.

    `HttpOnly` mot JavaScript, `Secure` mot okrypterad överföring, `SameSite`
    mot att en annan sida startar begäran.
    """
    sats = inloggning.kaksats(inloggning.KAKA_SESSION, "x", 60)

    assert "HttpOnly" in sats
    assert "Secure" in sats
    assert "SameSite=Lax" in sats


# ------------------------------------------------------------------ STATE


def test_state_maste_STAMMA():
    """SPÄRR: CSRF. Ett svar vi inte startade ska inte ge en session."""
    state = inloggning.ny_state()

    assert inloggning.state_stammer(state, state)
    assert not inloggning.state_stammer(state, inloggning.ny_state())
    assert not inloggning.state_stammer("", state)
    assert not inloggning.state_stammer(state, "")


def test_ett_GAMMALT_state_avvisas():
    """SPÄRR: ett påbörjat flöde ska inte gå att slutföra dagar senare."""
    gammal = f"abc.{int(time.time()) - inloggning.FLODE_SEKUNDER - 10}"

    assert not inloggning.state_stammer(gammal, gammal)


# ----------------------------------------------------- KONFIGURATIONEN


def test_ingen_konfiguration_ger_NONE_och_inte_ett_undantag(monkeypatch):
    """Lokalt körs vyn utan inloggning, och då ska ingenting kasta."""
    for namn in ("MAILBOT_OAUTH_KLIENT_ID", "MAILBOT_OAUTH_KLIENT_HEMLIGHET",
                 "MAILBOT_OAUTH_OMDIRIGERING", "MAILBOT_SESSIONSNYCKEL"):
        monkeypatch.delenv(namn, raising=False)

    assert inloggning.ur_miljon() is None


def test_en_HALVT_ifylld_konfiguration_KASTAR(monkeypatch):
    """SPÄRR: ett driftfel ska synas vid uppstart, inte vid första inloggningen.

    Utan raden startar vyn, binder utåt eftersom en konfiguration "finns", och
    faller först när någon försöker logga in. Då står kundtexten redan öppet.
    """
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_ID", "x")
    for namn in ("MAILBOT_OAUTH_KLIENT_HEMLIGHET",
                 "MAILBOT_OAUTH_OMDIRIGERING", "MAILBOT_SESSIONSNYCKEL"):
        monkeypatch.delenv(namn, raising=False)

    with pytest.raises(inloggning.Konfigurationsfel):
        inloggning.ur_miljon()


def test_EN_ENDA_saknad_variabel_namnges(monkeypatch):
    """SPÄRR: isolerar `saknas`-ledet, som var REDUNDANT med de andra två.

    **FÄLLD ENSAM VAR SVITEN GRÖN, och det var ett fynd.** Raden ovan lämnar
    tre variabler tomma, alltså fångar `len(nyckel) < 32` den ändå om
    `saknas`-ledet kopplas ur. En fällning som passerar därför att en granne
    råkar täcka samma fall mäter ingenting (§7.1).

    Här är ALLT giltigt utom klienthemligheten, som är tom. Bara `saknas`-ledet
    kan fälla det, och felet ska NAMNGE variabeln: en drifttext som säger att
    något saknas utan att säga vad tvingar Lars att gissa.
    """
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_ID", "x")
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_HEMLIGHET", "")
    monkeypatch.setenv("MAILBOT_OAUTH_OMDIRIGERING", "https://x.se/atervand")
    monkeypatch.setenv("MAILBOT_SESSIONSNYCKEL", "z" * 40)

    with pytest.raises(inloggning.Konfigurationsfel) as fel:
        inloggning.ur_miljon()

    assert "MAILBOT_OAUTH_KLIENT_HEMLIGHET" in str(fel.value)
    assert "MAILBOT_SESSIONSNYCKEL" not in str(fel.value)


def test_en_KORT_sessionsnyckel_KASTAR(monkeypatch):
    """SPÄRR: en gissningsbar nyckel gör sessionskakan förfalskningsbar."""
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_ID", "x")
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_HEMLIGHET", "y")
    monkeypatch.setenv("MAILBOT_OAUTH_OMDIRIGERING", "https://x.se/atervand")
    monkeypatch.setenv("MAILBOT_SESSIONSNYCKEL", "kort")

    with pytest.raises(inloggning.Konfigurationsfel):
        inloggning.ur_miljon()


def test_en_omdirigering_over_HTTP_KASTAR(monkeypatch):
    """SPÄRR: sessionskakan är `Secure` och följer aldrig med över http.

    Utan raden får Lars en inloggning som ser ut att lyckas och en session som
    aldrig kommer tillbaka.
    """
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_ID", "x")
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_HEMLIGHET", "y")
    monkeypatch.setenv("MAILBOT_OAUTH_OMDIRIGERING", "http://x.se/atervand")
    monkeypatch.setenv("MAILBOT_SESSIONSNYCKEL", "z" * 40)

    with pytest.raises(inloggning.Konfigurationsfel):
        inloggning.ur_miljon()


def test_statusraden_skriver_ALDRIG_hemligheten(monkeypatch):
    """§6: en hemlighet skrivs aldrig ut i upplöst form."""
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_ID", "123456789012-abc.apps.googleusercontent.com")
    monkeypatch.setenv("MAILBOT_OAUTH_KLIENT_HEMLIGHET", "HEMLIG-STRANG-XYZ")
    monkeypatch.setenv("MAILBOT_OAUTH_OMDIRIGERING", "https://x.se/atervand")
    monkeypatch.setenv("MAILBOT_SESSIONSNYCKEL", "z" * 40)

    rad = inloggning.status()

    assert "HEMLIG-STRANG-XYZ" not in rad
    assert "z" * 40 not in rad
    assert "apps.googleusercontent.com" not in rad


# ------------------------------------------------------- SCOPE OCH ADRESS


def test_scopen_ar_EXAKT_de_TVA_Lars_beslutat():
    """§10-STOPP: ett nytt scope läggs aldrig till av kod.

    Lars beslut i skiva 53: `openid` och `email`, inte `profile`. Samma princip
    som `src/auth.py::LASSCOPES`: miljön får det den behöver och inget annat.
    """
    assert inloggning.SCOPES == ["openid", "email"]


def test_auktoriseringsadressen_bar_hd_och_ratt_scope():
    """`hd` skickas i begäran OCH prövas i svaret. Det andra ledet är det som bär."""
    url = inloggning.auktoriseringsadress(konfiguration(), "ETT-STATE")

    assert "hd=autostockholm.se" in url
    assert "scope=openid+email" in url
    assert "state=ETT-STATE" in url
    assert "response_type=code" in url
    assert "profile" not in url


# ------------------------------------------------- id_token KOMMER EN VÄG


def _jwt(nyttolast: dict) -> str:
    kropp = base64.urlsafe_b64encode(
        json.dumps(nyttolast).encode("utf-8")
    ).decode("utf-8").rstrip("=")
    return f"huvud.{kropp}.signatur"


def test_id_token_kommer_BARA_ur_tokenslutpunkten():
    """SPÄRR: `anspraken_ur` prövar ingen signatur, alltså måste källan vara EN.

    Tokenet hämtas av `vaxla_kod` direkt från Google över TLS med vår
    klienthemlighet, och OpenID Connect säger att ett token som tas emot så inte
    behöver signaturprövas: kanalen är beviset.

    **DEN DAGEN NÅGON ANNAN ANROPAR `anspraken_ur` HÅLLER DET INTE.** Raden
    läser källtexten och fäller om en andra anropare tillkommer.
    """
    kalla = (ROT / "src" / "inloggning.py").read_text(encoding="utf-8")

    anropare = [
        rad.strip() for rad in kalla.splitlines()
        if "anspraken_ur(" in rad and not rad.strip().startswith(("def ", "#", "*", "`"))
    ]

    assert len(anropare) == 1, (
        f"`anspraken_ur` anropas på {len(anropare)} ställen: {anropare}. "
        "Funktionen prövar ingen signatur och är betrodd ENBART därför att "
        "`vaxla_kod` hämtar tokenet direkt från Google över TLS. En andra "
        "anropare kräver signaturprövning mot Googles JWKS."
    )


def test_vaxla_kod_ger_anspraken_ur_googles_svar():
    """Hela vägen genom tokenutbytet, med en påhittad öppnare. Rör inte nätet."""
    class FejkSvar:
        def __init__(self, data): self._data = data
        def read(self): return json.dumps(self._data).encode("utf-8")
        def __enter__(self): return self
        def __exit__(self, *_): return False

    def oppna(_begaran, timeout=None):
        return FejkSvar({"id_token": _jwt(anspraken())})

    ut = inloggning.vaxla_kod("EN-KOD", konfiguration(), oppna=oppna)

    assert ut["email"] == "info@autostockholm.se"


def test_ett_FEL_i_tokenutbytet_laker_ALDRIG_kroppen():
    """§6: begäran bär vår klienthemlighet, och undantaget kan bära begäran.

    Utan raden hamnar hemligheten i Railways logg första gången Google svarar
    med ett fel.
    """
    def oppna(_begaran, timeout=None):
        raise OSError("400: client_secret=PAHITTAD-HEMLIGHET är fel")

    with pytest.raises(inloggning.Inloggningsfel) as fel:
        inloggning.vaxla_kod("EN-KOD", konfiguration(), oppna=oppna)

    assert "PAHITTAD-HEMLIGHET" not in str(fel.value)


# ----------------------------------------------------- DEN DAGLIGA KÖRNINGEN


def _dagligen():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "dagligen", ROT / "scripts" / "dagligen.py"
    )
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def test_dagliga_kommandot_bar_INGEN_sandflagga():
    """SPÄRR: DEL C säger INGEN SÄNDNING, och det ska gå att läsa ur kommandot.

    `respond.py` har ingen `--send` och `test_respond_har_INGEN_send_flagga`
    fäller om en tillkommer. Den här raden är ett andra lager: även om respond
    fick en flagga ska det dagliga kommandot inte använda den.

    §10: första sändningen i en ny miljö är Lars beslut, oavsett vad som
    skickats från hans maskin.
    """
    rad = " ".join(_dagligen().kommando())

    assert "--send" not in rad
    assert "--inkorg" in rad
    # SKIVA 69, Lars beslut: utkasten skapas av den dagliga körningen.
    assert "--gmailutkast" in rad
    assert rad.endswith(f"--antal {_dagligen().ANTAL}")


def test_TAKET_ar_det_som_ryms_i_timeouten_och_tacker_det_uppmatta():
    """LUCKA 86, skiva 70. Taket kommer ur körningens egen tidsgräns, och det
    uppmätta maxet, 20 ärenden i en körning, ryms med marginal.

    Budgeten per ärende får inte sjunka under det uppmätta p99, 34,2 s. Utan
    den raden gav en budget på en sekund ett tak på 2700 och en grön svit.
    Fällt av §7-granskningen av skiva 70."""
    d = _dagligen()

    assert d.ANTAL == d.TIMEOUT_S // d.SEKUNDER_PER_ARENDE
    assert d.SEKUNDER_PER_ARENDE > 34.2
    assert d.ANTAL >= 2 * 20


def test_schemat_traffar_NASTA_dygn_nar_tiden_passerat():
    """Grundfallet i `nasta_korning`: aldrig en tidpunkt som redan varit."""
    d = _dagligen()

    efter = datetime(2026, 9, 15, 12, 0, tzinfo=timezone.utc)
    assert d.nasta_korning(efter) == datetime(2026, 9, 16, 5, 10, tzinfo=timezone.utc)

    fore = datetime(2026, 9, 15, 3, 0, tzinfo=timezone.utc)
    assert d.nasta_korning(fore) == datetime(2026, 9, 15, 5, 10, tzinfo=timezone.utc)


def test_en_MISSLYCKAD_korning_DODAR_INTE_slingan(tmp_path, monkeypatch):
    """SPÄRR: ett misslyckande ska kosta ETT dygn, inte alla följande.

    **UTAN DEN HÄR RADEN STÅR BOTEN STILL tills någon märker det.** En körning
    som kastar hade dödat slingan, och containern lever vidare eftersom vyn är
    förgrundsprocessen. Ingenting hade blivit rött och ingenting hade larmat.
    """
    d = _dagligen()
    monkeypatch.setattr(d, "KORNINGSLOGG", tmp_path / "korningar.jsonl")

    def kraschar(*_a, **_k):
        raise OSError("processen gick inte att starta")

    kod = d.kor(kor_process=kraschar)

    assert kod == 1
    rad = json.loads((tmp_path / "korningar.jsonl").read_text(encoding="utf-8"))
    assert rad["lyckades"] is False
    assert rad["exitkod"] == 1


def test_korningsloggen_skriver_ALDRIG_kundtext(tmp_path, monkeypatch):
    """§6: loggen bär räknare och utfall, aldrig det som stod i ett mail.

    Utdata SKICKAS VIDARE till stdout, där Railway fångar den, men bara ANTALET
    rader hamnar i filen.
    """
    d = _dagligen()
    monkeypatch.setattr(d, "KORNINGSLOGG", tmp_path / "korningar.jsonl")

    class Utfall:
        returncode = 0
        stdout = "KUNDTEXT-SOM-INTE-FAR-LOGGAS\nrad två\n"
        stderr = ""

    d.kor(kor_process=lambda *a, **k: Utfall())

    innehall = (tmp_path / "korningar.jsonl").read_text(encoding="utf-8")
    assert "KUNDTEXT-SOM-INTE-FAR-LOGGAS" not in innehall
    assert json.loads(innehall)["utdatarader"] == 2


def test_en_LYCKAD_korning_loggas_som_lyckad(tmp_path, monkeypatch):
    """NEGATIVKONTROLL: utan den vore "logga alltid misslyckande" grönt."""
    d = _dagligen()
    monkeypatch.setattr(d, "KORNINGSLOGG", tmp_path / "korningar.jsonl")

    class Utfall:
        returncode = 0
        stdout = ""
        stderr = ""

    assert d.kor(kor_process=lambda *a, **k: Utfall()) == 0
    assert json.loads(
        (tmp_path / "korningar.jsonl").read_text(encoding="utf-8")
    )["lyckades"] is True


# --------------------------------------------------------- AVBILDEN, §6


@pytest.mark.parametrize("post", [
    "data/", "logg/", "token.json", "token-las.json",
    "client_secret.json", "scratchpad/", ".env",
])
def test_dockerignore_haller_persondata_OCH_credentials_ur_avbilden(post):
    """SPÄRR: `COPY . .` tar allt som inte står i `.dockerignore`.

    **EN AVBILD ÄR LIKA EXPONERAD SOM EN DISK.** Den går att ladda ner av den
    som når registret, alltså är en fil i avbilden en fil hos Railway.

    §6 och #38: kundtexten och tokenfilerna ligger på volymen och läggs dit av
    Lars en gång. Inget av det passerar genom en deploy.
    """
    rader = {
        r.strip() for r in
        (ROT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    }

    assert post in rader, f"{post} saknas i .dockerignore och följer med avbilden"


def test_gitignore_och_dockerignore_TACKER_SAMMA_kansliga_poster():
    """SPÄRR: de två listorna får inte glida isär.

    En post som står i `.gitignore` men inte i `.dockerignore` hamnar inte i
    git och ändå hos Railway, vilket är den tystaste formen av §6-läcka.

    **DEN HÄR RADEN JÄMFÖR STRÄNGAR OCH RÄCKER INTE ENSAM**, se raden nedan.
    """
    kansligt = {"data/", "logg/", "token.json", "token-las.json",
                "client_secret.json", "scratchpad/", ".env"}

    git = {r.strip() for r in
           (ROT / ".gitignore").read_text(encoding="utf-8").splitlines()}
    docker = {r.strip() for r in
              (ROT / ".dockerignore").read_text(encoding="utf-8").splitlines()}

    assert kansligt <= git, f"saknas i .gitignore: {sorted(kansligt - git)}"
    assert kansligt <= docker, f"saknas i .dockerignore: {sorted(kansligt - docker)}"


# NÄSTLADE LÄGEN SOM MÅSTE UTESLUTAS PÅ VARJE DJUP.
#
# `MAILBOT_HEMLIGHETER` finns för att credentials ska kunna ligga någon
# annanstans än i roten, alltså är en underkatalog ett LEVANDE läge och inte ett
# påhittat.
_NASTLADE = [
    "hemligheter/token.json",
    "hemligheter/token-las.json",
    "hemligheter/client_secret.json",
    "underkatalog/.env",
    "nagonstans/data/par.jsonl",
    "nagonstans/logg/beslut.jsonl",
]


@pytest.mark.parametrize("sokvag", _NASTLADE)
def test_dockerignore_utesluter_hemligheter_PA_VARJE_DJUP(sokvag):
    """SPÄRR: `.dockerignore` har INTE gitignore-semantik, och det mäts här.

    **RADEN OVAN JÄMFÖR STRÄNGAR OCH SER INTE DET HÄR.** Ett mönster utan `**/`
    matchar mot HELA den relativa sökvägen, alltså bara i byggkontextens rot.
    `.gitignore` utan snedstreck matchar på varje djup.

    Uppmätt: med bara rotformerna hamnade `hemligheter/token.json` och tre till
    i den byggda avbilden, medan `git check-ignore` ignorerade dem. Fällt av
    §7-granskningen av skiva 53.

    **RADEN MÄTER MOT MÖNSTREN och inte mot en uppräkning av rader**, alltså
    fäller den också en framtida omskrivning som råkar tappa `**/`.
    """
    import fnmatch

    monster = [
        r.strip() for r in
        (ROT / ".dockerignore").read_text(encoding="utf-8").splitlines()
        if r.strip() and not r.strip().startswith("#")
    ]

    def utesluts(vag: str) -> bool:
        for m in monster:
            m = m.rstrip("/")
            if fnmatch.fnmatch(vag, m) or fnmatch.fnmatch(vag, m + "/*"):
                return True
            # Ett katalogmönster täcker allt under sig.
            delar = vag.split("/")
            for i in range(1, len(delar)):
                if fnmatch.fnmatch("/".join(delar[:i]), m):
                    return True
        return False

    assert utesluts(sokvag), (
        f"{sokvag} utesluts inte av .dockerignore och följer med avbilden. "
        "Ett mönster utan `**/` gäller bara byggkontextens rot."
    )


# ------------------------------------------- GRINDEN PÅ RUTTERNA, GENOM VÄGEN

def _fall():
    return vy.Fall(
        etikett="fråga om pris a-traktorkonvertering",
        kalla="kedjan",
        text="PÅHITTAD KUNDTEXT SOM INTE FÅR SYNAS",
        tidsstampel="2026-01-01T00:00:00+00:00",
        avsandare_hash="0" * 16,
    )


def _granskningsfall():
    return vy.Granskningsfall(
        fall=_fall(), forslag="PÅHITTAT UTKAST SOM INTE FÅR SYNAS", sparr=""
    )


def _hanterare_med_inloggning():
    return vy.bygg_hanterare(
        [_fall()], granskning=[_granskningsfall()],
        konfiguration=konfiguration(),
    )


def _fejk(vag, kropp="", kaka=""):
    from tests.test_vy import FejkHanterare
    return FejkHanterare(_hanterare_med_inloggning(), vag, kropp, kaka=kaka)


@pytest.mark.parametrize("vag", ["/granskning/0", "/referens/0", "/"])
def test_en_OINLOGGAD_GET_nar_ALDRIG_kundtexten(vag):
    """SPÄRR: grinden på läsvägen, och den var obunden.

    **UTAN DEN HÄR RADEN GÅR `_kravs_inloggning` ATT KOPPLA UR MED GRÖN SVIT.**
    Uppmätt med `scripts/sparr-prova.sh`: `if self._kravs_inloggning():` ersatt
    med `if False:` gav 1712 gröna. Då svarar vyn med rå kundtext till vem som
    helst på internet, vilket är precis det §6 och hela skivan handlar om.

    Varje rutt prövas, alltså går grinden inte att lägga på bara en av dem.
    """
    fejk = _fejk(vag)
    fejk.get()

    assert fejk.kod == 401
    assert "PÅHITTAD KUNDTEXT SOM INTE FÅR SYNAS" not in fejk.svar
    assert "PÅHITTAT UTKAST SOM INTE FÅR SYNAS" not in fejk.svar
    assert "Logga in" in fejk.svar


def test_en_INLOGGAD_GET_slapps_igenom():
    """NEGATIVKONTROLL: utan den vore "neka alltid" en grön lösning på raden ovan."""
    kaka = (f"{inloggning.KAKA_SESSION}="
            f"{inloggning.skapa_session('info@autostockholm.se', konfiguration())}")

    fejk = _fejk("/granskning/0", kaka=kaka)
    fejk.get()

    assert fejk.kod == 200
    assert "PÅHITTAT UTKAST SOM INTE FÅR SYNAS" in fejk.svar


@pytest.mark.parametrize("vag", ["/omdome/0", "/referens/0", "/gmailutkast/0"])
def test_en_OINLOGGAD_POST_SKRIVER_INGENTING(vag, tmp_path, monkeypatch):
    """SPÄRR: grinden på SKRIVVÄGEN, och den var obunden.

    Samma fällning som raden ovan gav grön svit också här. POST-vägen skriver:
    `_omdome` till `logg/omdomen.jsonl` och referensrutten till
    `data/par.jsonl`. En oinloggad begäran ska inte kunna lägga något i en fil
    ens när den avvisas, och därför prövas inloggningen FÖRE kroppen läses.
    """
    monkeypatch.setattr(vy, "DATAKATALOG", tmp_path / "data")
    monkeypatch.setattr(vy, "LOGGKATALOG", tmp_path / "logg")

    fejk = _fejk(vag, kropp="omdome=godkann&text=PAHITTAT")
    fejk.post()

    assert fejk.kod == 401
    assert not list(tmp_path.rglob("*.jsonl")), "en oinloggad POST skrev en fil"


def test_inloggningsflodets_TVA_rutter_kraver_INGEN_session():
    """NEGATIVKONTROLL: kräver de en session går den aldrig att skaffa.

    `/logga-in` ska omdirigera till Google, `/atervand` ska pröva svaret. Båda
    utan session, och ingendera får visa kundtext.
    """
    fejk = _fejk("/logga-in")
    fejk.get()

    assert fejk.kod == 302
    plats = dict(fejk.huvuden).get("Location", "")
    assert plats.startswith(inloggning.AUKTORISERINGSSLUTPUNKT)
    assert "PÅHITTAD KUNDTEXT" not in fejk.svar


def test_atervand_UTAN_state_ger_ingen_session():
    """SPÄRR: CSRF-ledet, genom rutten och inte bara i funktionen."""
    fejk = _fejk("/atervand?code=EN-KOD&state=PAHITTAT")
    fejk.get()

    assert fejk.kod == 400
    assert not any(namn == "Set-Cookie" and inloggning.KAKA_SESSION in varde
                   for namn, varde in fejk.huvuden)


def test_inloggningssidan_bar_INGEN_uppgift_om_materialet():
    """§6: den som inte får läsa kundtexten får inte veta hur mycket som finns.

    Ett antal utkast är i sig en uppgift om brevlådan: hur mycket post
    verkstaden får, och om det finns något att granska i dag.

    **RADEN JÄMFÖR MED SIDAN BYGGD UR INGENTING.** Sidan får inte bero på
    `fall` eller `granskning` alls, och en jämförelse mot den tomma formen
    fäller varje räknare och varje etikett som smyger sig in.
    """
    fejk = _fejk("/granskning/0")
    fejk.get()

    assert fejk.svar == vy._inloggningssida()


def test_starta_LAMNAR_VIDARE_konfigurationen_till_hanteraren():
    """SPÄRR: tråden mellan `starta` och `bygg_hanterare`, och den var OBUNDEN.

    **DET HÄR ÄR SKIVANS ALLVARLIGASTE LUCKA.** `starta` prövar spärren och
    `bygg_hanterare` upprätthåller den, men ingen rad band att konfigurationen
    faktiskt når fram. Uppmätt med `scripts/sparr-prova.sh`:
    `konfiguration=konfiguration)` ersatt med `konfiguration=None)` gav 1722
    gröna.

    Med den enda raden fälld passerar `starta(adress="0.0.0.0",
    konfiguration=<giltig>)` spärren — en konfiguration FINNS — binder utåt, och
    en begäran UTAN kaka får 200 med kundtexten i kroppen. Precis det utfall
    skivan är byggd för att omöjliggöra, utan att något blir rött.

    Skälet att den var obunden: varje grindtest bygger hanteraren direkt med
    `vy.bygg_hanterare`, och det enda test som gick genom `starta` med en
    konfiguration läste bara `server_address`.

    Formen är lånad ur `test_starta_LAMNAR_VIDARE_uppslagskallan_till_hanteraren`.
    Fällt av §7-granskningen av skiva 53.
    """
    from tests.test_vy import FejkHanterare

    server = vy.starta(
        port=0,
        fall=[_fall()],
        granskning=[_granskningsfall()],
        adress="127.0.0.1",
        konfiguration=konfiguration(),
    )
    try:
        for vag in ("/granskning/0", "/referens/0"):
            fejk = FejkHanterare(server.RequestHandlerClass, vag)
            fejk.get()

            assert fejk.kod == 401, f"{vag} svarade {fejk.kod} utan session"
            assert "PÅHITTAD KUNDTEXT SOM INTE FÅR SYNAS" not in fejk.svar
            assert "PÅHITTAT UTKAST SOM INTE FÅR SYNAS" not in fejk.svar
    finally:
        server.server_close()


def test_starta_UTAN_konfiguration_slapper_igenom_som_forut():
    """NEGATIVKONTROLL: utan den vore "kräv alltid session" en grön lösning.

    Lokalt körs vyn utan inloggning mot loopback, och då ska Lars komma in.
    """
    from tests.test_vy import FejkHanterare

    server = vy.starta(port=0, fall=[_fall()], granskning=[_granskningsfall()])
    try:
        fejk = FejkHanterare(server.RequestHandlerClass, "/granskning/0")
        fejk.get()

        assert fejk.kod == 200
        assert "PÅHITTAT UTKAST SOM INTE FÅR SYNAS" in fejk.svar
    finally:
        server.server_close()


def test_slingan_skriver_de_falt_vyns_korningsrad_LASER(tmp_path, monkeypatch):
    """**SKRIVAREN OCH LÄSAREN BINDS MOT VARANDRA, inte var för sig.**

    `scripts/dagligen.py` skriver `logg/korningar.jsonl` och `src/vy.py` läser
    den. Fram till skiva 54 delade de bara SÖKVÄGEN, och den var bunden.
    Fältnamnen var det inte: `startad` fanns bara i läsarens egna fixturer.

    **UPPMÄTT AV §7-GRANSKNINGEN AV SKIVA 54:** ett byte av `"startad"` mot
    `"start"` i `dagligen._logga` lämnade hela sviten GRÖN. `senaste_lyckade`
    hade då hittat noll lyckade körningar i varje logg, och vyn hade visat
    *"INGEN LYCKAD KÖRNING ÄR LOGGAD"* för alltid medan slingan körde perfekt.

    Det är ordagrant det utfall `src/sokvagar.py` säger att raden inte får ha,
    och kommentaren där vaktade bara filnamnet.

    **RADEN KÖR SKRIVAREN OCH GER LÄSAREN RESULTATET.** Ingen fixtur emellan:
    hade testet byggt sin egen loggrad hade det prövat sig självt.
    """
    d = _dagligen()
    logg = tmp_path / "korningar.jsonl"
    monkeypatch.setattr(d, "KORNINGSLOGG", logg)

    class Utfall:
        returncode = 0
        stdout = ""
        stderr = ""

    d.kor(kor_process=lambda *a, **k: Utfall())

    tid = vy.senaste_lyckade(logg)
    assert tid is not None, (
        "vyn hittar ingen lyckad körning i det slingan just skrev. "
        "Fältnamnen i dagligen._logga och vy.senaste_lyckade har glidit isär."
    )

    nu = datetime.now(timezone.utc)
    assert (nu - tid).total_seconds() < 300
    assert "stannat" not in vy.korningsrad(logg, nu=nu)


def test_en_MISSLYCKAD_korning_ger_vyn_en_ROD_rad(tmp_path, monkeypatch):
    """NEGATIVKONTROLL till raden ovan, och den prövar samma led åt andra hållet.

    Utan den vore "returnera alltid en tid" grönt i testet ovan.
    """
    d = _dagligen()
    logg = tmp_path / "korningar.jsonl"
    monkeypatch.setattr(d, "KORNINGSLOGG", logg)

    def kraschar(*_a, **_k):
        raise OSError("processen gick inte att starta")

    d.kor(kor_process=kraschar)

    assert vy.senaste_lyckade(logg) is None
    assert "INGEN LYCKAD KÖRNING" in vy.korningsrad(
        logg, nu=datetime.now(timezone.utc))


def test_en_korning_UTAN_ARENDEN_loggas_som_LYCKAD(tmp_path, monkeypatch):
    """**ETT DYGN UTAN KUNDÄRENDEN ÄR INGEN MISSLYCKAD KÖRNING.**

    `respond._kor` returnerade 1 när urvalet gav noll ärenden. `dagligen.kor`
    skriver `"lyckades": kod == 0`, alltså loggades en lugn helg som ett
    misslyckande, och `vy.korningsrad` larmade sedan rött med texten *"minst en
    körning har uteblivit eller fallit"* över utkast som var i sin ordning.

    Skadan går åt två håll. Det första är det falska beskedet. Det andra är
    värre: raden ÄR larmet för den döda slingan, och ett larm som ropar varg
    slutar läsas innan det ropar på riktigt.

    Fällt av §7-granskningen av skiva 54. Scenariot är inte konstruerat: av den
    skörd som låg på disk gav dygnets trådar fler sållade än ärenden, och en helg
    där all inkommande post är maskinmail ger noll.
    """
    d = _dagligen()
    logg = tmp_path / "korningar.jsonl"
    monkeypatch.setattr(d, "KORNINGSLOGG", logg)

    class TomKorning:
        """Vad `respond.py` skriver och returnerar när urvalet är tomt."""
        returncode = 0
        stdout = "inga ärenden att köra.\n"
        stderr = ""

    assert d.kor(kor_process=lambda *a, **k: TomKorning()) == 0
    assert json.loads(logg.read_text(encoding="utf-8"))["lyckades"] is True
    assert "stannat" not in vy.korningsrad(
        logg, nu=datetime.now(timezone.utc))


def test_respond_returnerar_NOLL_for_ett_tomt_urval():
    """Andra halvan av raden ovan, mätt på `scripts/respond.py` självt.

    Testet ovan matar in `returncode = 0`, alltså prövar det `dagligen`:s
    tolkning och inte vad respond faktiskt returnerar. Den här raden läser
    källtexten, eftersom `_kor` inte går att anropa utan en hel körning.

    En etta här är en röd banderoll i vyn nästa lugna helg.
    """
    kalla = (ROT / "scripts" / "respond.py").read_text(encoding="utf-8")
    stycke = kalla.split('print("inga ärenden att köra.")')[1]
    forsta_retur = stycke.split("return ")[1].split("\n")[0].strip()

    assert forsta_retur == "0", (
        "respond._kor returnerar {} för ett tomt urval. dagligen loggar det "
        "som ett misslyckande och vyn larmar rött på en körning som "
        "lyckades.".format(forsta_retur)
    )
