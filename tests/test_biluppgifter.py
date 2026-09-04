"""Tester för src/biluppgifter.py.

Spärren `fordonsfakta-ur-sida` ligger i FYRA lager, och varje lager har egna
test här:

1. **Exakt etikettmatchning** i `_las_falt`. `Släpvagnsvikt` är ett prefix till
   `Släpvagnsvikt obromsad`, och de två raderna ligger intill varandra på
   sidan. Lagret vaktar att rätt rad läses.
2. **Tvetydighetskontrollen** i `_las_falt`. En etikett som förekommer flera
   gånger kastar i stället för att den första träffen tas.
3. **Canonical-ankaret** i `_galler_fordonet`. Sidan svarar 200 med SÖKSIDAN på
   ett okänt nummer, så statuskoden kan inte avgöra om fordonet finns.
4. **De strikta värdeparsningarna** i `_tal` och `_ja_nej`, sedan skiva 22 också
   `_krav_pa_rimlighet`. Ett värde som inte är en ren vikt eller ett rent ja/nej
   utelämnas, och ett värde utanför rimligt intervall kastar.

**SIDAN PARSAS SEDAN SKIVA 22**, se `docs/beslutslogg.md` #32. Lagren ligger kvar
men vilar på `_Faltlasare` i stället för på tre regexuttryck. Det som stod här om
`MONSTER` och `ETIKETTSPAN` beskrev kod som inte finns längre.

**LAGER 1 OCH 2 BÄR INTE LÄNGRE VARANDRAS FÖRSVAR.** Med regexen tände lager 2
när lager 1:s exakthet föll, eftersom en prefixmatchning gav två träffar. Lager 2
räknar nu etikettNODER, och en fällning av likhetsjämförelsen i lager 1 rör inte
räkningen. Talen står i `docs/sparrar.md`.

**ATT ASSERA PÅ VÄRDET RÄCKTE INTE, och det är prövat och inte antaget.**
`test_slapvagnsvikt_ar_den_bromsade` asserar på 2 400 och inte på att något
kastades. Det gjorde det ändå inte fällbart för sig under den gamla koden: fälldes
BÅDA lagren samtidigt togs första träffen, och den råkar vara den bromsade vikten
eftersom den raden står först på sidan i dag. Testet förblev alltså GRÖNT vid
dubbelfällningen.

Det som löste det är `test_slapvagnsvikt_ar_den_bromsade_aven_i_omvand_radordning`
nedan, vars fixtur lägger den obromsade raden först. Det testet behövs fortfarande:
det vaktar att utfallet inte beror på källans radordning, vilket är ett krav på
avläsningen och inte på hur den är implementerad.

**INGET TEST HÄR RÖR NÄTET.** `biluppgifter_hamtning` tar `oppna`, och alla test
injicerar den. Ett test som slår mot biluppgifter.se hade gjort svitens utfall
beroende av en tredje parts drift och av deras klientfiltrering.

Talen i fixturerna är påhittade utom där något annat sägs. `SIDA_AVLAST` bär
ÅTTA värden som är AVLÄSTA ur ett verkligt svar 2026-09-02, och alla åtta är
uppräknade i kommentaren där, eftersom prefixfällan bara går att pröva mot
sidans verkliga radordning. Samma kommentar anger också i vilket avseende
ordningen INTE är källans.

All indata är påhittad i den meningen att den inte är hämtad ur kundmaterialet
(§6). Registreringsnumren är konstruerade för testet.
"""

from __future__ import annotations

import http.client
import json
import urllib.error
from pathlib import Path

import pytest

from src import biluppgifter, fordonsuppslag
from src.biluppgifter import (
    EXAKT_ETIKETT,
    Hamtningsfel,
    _galler_fordonet,
    _hamta_sidan,
    _ja_nej,
    _las_falt,
    _lasaren,
    _tal,
    biluppgifter_hamtning,
)
from src.fordonsuppslag import UppslagMisslyckades, Utfall

REGNR = "ABC12X"


@pytest.fixture(autouse=True)
def logg_i_tmp(tmp_path, monkeypatch):
    """INGEN TESTKÖRNING SKRIVER I REPOTS `logg/`.

    `biluppgifter_hamtning` loggar varje misslyckat uppslag, och den här filen
    bär hundratals uppslag som misslyckas med flit. Utan omdirigeringen hade
    varje svitkörning fyllt `logg/uppslag.jsonl` med fixturnummer, alltså gjort
    en driftlogg oläsbar med data som aldrig rörde en kund.

    Fixturen är `autouse` därför att kravet gäller varje test i filen, och en
    fixtur man måste komma ihåg att begära är en fixtur någon glömmer.
    """
    monkeypatch.setattr(biluppgifter, "LOGGFIL", tmp_path / "uppslag.jsonl")


def rad(etikett: str, varde: str) -> str:
    """En fältrad i sidans form: etikett följd av värde i nästa span."""
    return (
        f'\t\t\t<li>\n'
        f'\t\t\t\t<span class="label">{etikett}</span>\n'
        f'\t\t\t\t<span class="value">{varde}</span>\n'
        f'\t\t\t</li>\n'
    )


def sida(*, regnr: str | None = REGNR, rader: str = "") -> str:
    """En minimal fordonssida.

    `regnr=None` ger en sida UTAN registreringsnummer i canonical, alltså det
    söksidan svarar med när numret inte finns.
    """
    slut = f"{regnr.lower()}/" if regnr else ""
    return (
        "<html><head>"
        f'<link rel="canonical" href="https://biluppgifter.se/fordon/{slut}"/>'
        "</head><body>\n"
        f'<ul class="list top-30">\n{rader}</ul>\n'
        "</body></html>"
    )


# ALLA ÅTTA VÄRDENA ÄR AVLÄSTA ur ett verkligt svar 2026-09-02, inget är
# påhittat: Tjänstevikt 2 140 kg, Totalvikt 2 750 kg, Lastvikt 610 kg,
# Släpvagnsvikt 2 400 kg, Släpvagnsvikt obromsad 750 kg, Släp totalvikt (B)
# Max 750 kg (Teoretisk), Släp totalvikt (B+) Max 1500 kg (Teoretisk),
# Draganordning Nej. Här stod tidigare DE TRE VÄRDENA och räknade sedan fyra.
#
# RADORDNINGEN ÄR KÄLLANS FÖR SJU AV ÅTTA, INTE FÖR ALLA. På den avlästa sidan
# står ETIKETTERNA i ordningen Draganordning (index 36), därefter Tjänstevikt
# (42), Totalvikt (43), Lastvikt (44), Släpvagnsvikt (45), Släpvagnsvikt obromsad
# (46), Släp totalvikt (B) (47) och Släp totalvikt (B+) (48). BASEN ÄR LABEL-SPAN
# OCH INTE LABEL/VALUE-PAR, och det är skillnad: sidan bär 62 label-span men 54
# par, och på parbasen är indexen i stället 28, 34, 35, 36, 37, 38, 39, 40.
# Glappet beror på par vars värde bär nästlad markup, avläst för `Chassinr / VIN`
# vars value-span öppnar ett `<a hx-get=...>` så att `([^<]*)` inte matchar. Den
# relativa ordningen och angränsningen håller på BÅDA baserna, och det är den enda
# egenskap bevisföringen nedan vilar på. Här ligger Draganordning
# SIST i stället för först.
#
# Fixturens bevisvärde är ändå oskadat: den mutationskritiska angränsningen
# Släpvagnsvikt → Släpvagnsvikt obromsad är källans egen, och den obromsade
# raden ligger direkt EFTER den bromsade precis som på sidan. Draganordnings
# plats spelar ingen roll för prefixfällan, eftersom ingen annan etikett i
# registret är ett prefix till den. Här stod tidigare att radordningen är
# sidans egen utan förbehåll; det var för brett.
SIDA_AVLAST = sida(
    rader=(
        rad("Tjänstevikt", "2140 kg")
        + rad("Totalvikt", "2750 kg")
        + rad("Lastvikt", "610 kg")
        + rad("Släpvagnsvikt", "2400 kg")
        + rad("Släpvagnsvikt obromsad", "750 kg")
        + rad("Släp totalvikt (B)", "Max 750 kg (Teoretisk)")
        + rad("Släp totalvikt (B+)", "Max 1500 kg (Teoretisk)")
        + rad("Draganordning", "Nej")
    )
)

HELA_RADER = (
    rad("Tjänstevikt", "1500 kg")
    + rad("Släpvagnsvikt", "1400 kg")
    + rad("Draganordning", "Ja")
)


def svarar(kropp: str, status: int = 200):
    """Injicerad hämtning som alltid ger `status` och `kropp`."""

    def oppna(_regnr: str) -> tuple[int, str]:
        return status, kropp

    return oppna


# ---------------------------------------------------------------- lager 1


def test_slapvagnsvikt_ar_den_bromsade():
    """LAGER 1. `Släpvagnsvikt`, inte `Släpvagnsvikt obromsad`.

    ASSERAR PÅ VÄRDET och inte på ett undantag, därför att lager 2 fäller en
    prefixmatchning åt lager 1. **Det gör inte det här testet fällbart för sig**,
    se filhuvudet och testet nedan: vid dubbelfällning är det GRÖNT, eftersom
    första träffen råkar bli den rätta i den här fixturens radordning.

    750 mot 2 400 är inte kosmetik: tröskeln är 1 000, så den obromsade vikten
    faller UNDER och den bromsade ÖVER. **Men defekten byter inte utfall på det
    här fordonet**, och här stod tidigare att den gör det på varje fordon där
    tjänstevikten inte räcker. Det är inte producerbart. Tre villkor måste hålla
    samtidigt: att källan skriver den obromsade raden först, att tjänstevikten
    inte redan räcker, och att den bromsade vikten når över tröskeln medan den
    obromsade faller under. Det tredje håller på det avlästa fordonet. **De två
    andra gör det inte.** Källan skriver den BROMSADE raden först, och
    tjänstevikten 2 140 kg ligger redan över tröskeln 2 000 kg. Eftersom
    `ar_lamplig_som_dragfordon` prövar tjänstevikten först och returnerar `True`
    direkt, läses släpvagnsvikten aldrig för det här fordonet. Spärren finns för
    att inte behöva lita på någotdera.
    """
    assert _las_falt(SIDA_AVLAST)["slapvagnsvikt_kg"] == 2400


def test_slapvagnsvikt_ar_den_bromsade_aven_i_omvand_radordning():
    """LAGER 1. Samma sak när den OBROMSADE raden ligger först.

    **DETTA TEST FINNS FÖR ATT DET FÖRRA INTE RÄCKTE.** §7.1-prövningen fällde
    lager 1 och lager 2 samtidigt, och `test_slapvagnsvikt_ar_den_bromsade`
    förblev då GRÖNT. Skälet: med en prefixmatchning ger `re.findall` två
    träffar, och `traffar[0]` råkar bli den bromsade vikten bara därför att den
    står först på sidan i dag. Testet vaktade alltså dokumentordningen och inte
    spärren, alltså vakuöst i §7.1:s mening.

    Här ligger den obromsade raden först. En prefixmatchning ger då 750 och
    testet blir rött, oberoende av vilken ordning källan råkar välja.
    """
    omvand = sida(
        rader=(
            rad("Släpvagnsvikt obromsad", "750 kg")
            + rad("Släpvagnsvikt", "2400 kg")
        )
    )

    assert _las_falt(omvand)["slapvagnsvikt_kg"] == 2400


def test_alla_tre_falten_lases_ur_ett_avlast_svar():
    """LAGER 1. De tre gatande fälten, och inga andra rader, ur sidans form."""
    assert _las_falt(SIDA_AVLAST) == {
        "tjanstevikt_kg": 2140,
        "slapvagnsvikt_kg": 2400,
        "draganordning": False,
    }


def test_etikett_med_annat_suffix_ger_inte_falt():
    """LAGER 1. En etikett som bara BÖRJAR likadant är inte fältet."""
    bara_obromsad = sida(rader=rad("Släpvagnsvikt obromsad", "750 kg"))

    assert "slapvagnsvikt_kg" not in _las_falt(bara_obromsad)


# ---------------------------------------------------------------- lager 2


def test_dubblerad_etikett_kastar():
    """LAGER 2. Tvetydighet kastar i stället för att första träffen tas."""
    dubbel = sida(
        rader=rad("Tjänstevikt", "1500 kg") + rad("Tjänstevikt", "1900 kg")
    )

    with pytest.raises(Hamtningsfel) as fel:
        _las_falt(dubbel)

    assert "förekommer 2 gånger" in str(fel.value)
    assert "Tjänstevikt" in str(fel.value)


# ---------------------------------------------------------------- lager 3


def test_canonical_utan_nummer_ar_inte_fordonet():
    """LAGER 3. Söksidans canonical bär inget nummer.

    AVLÄST 2026-09-02: ett okänt nummer ger HTTP 200 och söksidan, vars
    canonical är `.../fordon/` utan nummer. Statuskoden kan alltså inte avgöra
    om fordonet finns.
    """
    assert _galler_fordonet(sida(regnr=None), REGNR) is False


def test_canonical_for_annat_fordon_ar_inte_fordonet():
    """LAGER 3. Ett svar om ett ANNAT nummer är inte fakta om vårt."""
    assert _galler_fordonet(sida(regnr="XYZ99Z"), REGNR) is False


def test_canonical_saknas_helt_ar_inte_fordonet():
    """LAGER 3. Utan canonical är förvalet att fordonet inte finns."""
    assert _galler_fordonet("<html><body>tomt</body></html>", REGNR) is False


def test_canonical_jamfors_skiftlagesokansligt():
    """LAGER 3. Sidan skriver gemener, `slag_upp` normaliserar till versaler.

    Samma versalfälla gav 46 av 78 i stället för 77 av 78 vid regnr-avläsningen,
    se `docs/beslutslogg.md` #28.
    """
    assert _galler_fordonet(sida(regnr=REGNR.lower()), REGNR.upper()) is True


def test_okant_nummer_ger_none_och_faller_till_utkast():
    """LAGER 3, hela vägen. `None` från hämtningen fälls av spärren i uppslaget."""
    hamta = biluppgifter_hamtning(oppna=svarar(sida(regnr=None)))

    assert hamta(REGNR) is None

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(REGNR, hamta=hamta)

    assert fel.value.skal == "hämtningen gav inget svar"


# ---------------------------------------------------------------- lager 4


@pytest.mark.parametrize(
    "varde",
    [
        "Max 750 kg (Teoretisk)",  # sidans egen lydelse på Släp totalvikt-raderna
        "okänt",
        "",
        "kg",
        "1.5 kg",  # punkt är decimalpunkt i svensk sifferskrivning, inte avskiljare
        "2140",  # utan enhet
    ],
)
def test_varde_som_inte_ar_ren_vikt_ger_none(varde):
    """LAGER 4. Ett tal plockas aldrig ur en sträng som bär annat.

    `Max 750 kg (Teoretisk)` är sidans verkliga lydelse på två rader. Ett mönster
    som tar första talet ur en sträng hade gjort den till vikten 750.
    """
    assert _tal(varde) is None


@pytest.mark.parametrize(
    ("varde", "vantat"),
    [("2140 kg", 2140), ("2 140 kg", 2140), ("2\u00a0140 kg", 2140), ("0 kg", 0)],
)
def test_ren_vikt_lases_med_tusenavskiljare(varde, vantat):
    """LAGER 4. Blanksteg och hårt blanksteg är avskiljare, punkt är det inte."""
    assert _tal(varde) == vantat


@pytest.mark.parametrize("varde", [" kg", "  kg", "\u00a0kg", "\t kg"])
def test_bara_blanktecken_fore_enheten_ger_none(varde):
    r"""LAGER 4. Ett värde som bara bär blanktecken är ett SAKNAT fält.

    ASSERAR PÅ `None` OCH INTE PÅ ETT UNDANTAG, därför att ett tomt värde är ett
    saknat fält och inte en strukturändring. Ett kastat undantag hade tagit hela
    uppslaget med sig.

    **TESTET SPIKADE FÖRR `.strip()`, OCH GÖR DET INTE LÄNGRE.** Mot det gamla
    mönstret `([\d\s\u00a0]+)kg` matchade `' kg'` utan strip med grupp 1 lika
    med ett blanksteg, `re.sub` tömde gruppen och `int("")` kastade
    `ValueError`. Med det skärpta mönstret kan grupp 1 inte bära enbart
    blanktecken, så utfallet är `None` med eller utan strip, och fällningen av
    `.strip()` blev GRÖN. Uppmätt i skiva 21:s andra granskningsvarv, som fällde
    testet som vakuöst i §7.1:s mening.

    **Namnet beskriver därför nu vad testet faktiskt bevisar**, inte vad det en
    gång vaktade. `.strip()` binds i stället av
    `test_varde_med_omgivande_blanktecken_lases`, och den fällningen är RÖD.
    """
    assert _tal(varde) is None
@pytest.mark.parametrize(
    ("varde", "vantat"), [("Ja", True), ("Nej", False), ("ja", True), ("NEJ", False)]
)
def test_ja_och_nej_lases(varde, vantat):
    """LAGER 4. Sidan skriver `Ja` och `Nej`."""
    assert _ja_nej(varde) is vantat


@pytest.mark.parametrize("varde", ["Okänd", "", "Ja tack", "1", "true"])
def test_annat_an_ja_eller_nej_ger_none(varde):
    """LAGER 4. Ett tredje värde betyder VET INTE, aldrig `Nej`.

    Ett `Okänd` som tolkades som `Nej` hade gett ett svar som PÅSTÅR att dragkrok
    saknas, vilket är precis det påstående `utvardera`:s förval OKLART finns för
    att undvika.
    """
    assert _ja_nej(varde) is None


def test_otolkbart_varde_utelamnar_nyckeln_och_spparren_faller():
    """LAGER 4, hela vägen. Ett otolkbart värde blir ett saknat fält."""
    trasig = sida(
        rader=(
            rad("Tjänstevikt", "1500 kg")
            + rad("Släpvagnsvikt", "okänt")
            + rad("Draganordning", "Ja")
        )
    )

    assert "slapvagnsvikt_kg" not in _las_falt(trasig)

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(trasig))
        )

    assert fel.value.skal == "svaret saknar slapvagnsvikt_kg"


# ------------------------------------------------- saknade fält och statusar


@pytest.mark.parametrize(
    ("bortplockad", "skal"),
    [
        ("Tjänstevikt", "svaret saknar tjanstevikt_kg"),
        ("Släpvagnsvikt", "svaret saknar slapvagnsvikt_kg"),
        ("Draganordning", "svaret saknar draganordning"),
    ],
)
def test_saknat_falt_faller_med_sitt_eget_skal(bortplockad, skal):
    """Varje saknat fält ska fällas av spärren i uppslaget, med rätt skäl.

    Asserar på SKÄLET och inte bara på att något kastades: de tre nyckellagren i
    `_kontrollera` är helt redundanta med Mapping-lagret, och utan skälet blir
    testet grönt när ett enskilt lager fälls.
    """
    rader = "".join(
        r
        for e, r in [
            ("Tjänstevikt", rad("Tjänstevikt", "1500 kg")),
            ("Släpvagnsvikt", rad("Släpvagnsvikt", "1400 kg")),
            ("Draganordning", rad("Draganordning", "Ja")),
        ]
        if e != bortplockad
    )

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sida(rader=rader)))
        )

    assert fel.value.skal == skal


def test_fyrahundrafyra_ger_none():
    """404 är ett giltigt svar från källan, inte ett driftfel.

    Grenen står kvar som skydd men utlöses i praktiken inte: sidan svarar 200
    med söksidan på ett okänt nummer, se lager 3.
    """
    assert biluppgifter_hamtning(oppna=svarar("", status=404))(REGNR) is None


@pytest.mark.parametrize("status", [301, 403, 429, 500, 503])
def test_annan_status_kastar_hamtningsfel(status):
    """En källa som inte svarar 200 är TYSTNAD, inte tomhet."""
    with pytest.raises(Hamtningsfel) as fel:
        biluppgifter_hamtning(oppna=svarar("", status=status))(REGNR)

    assert str(status) in str(fel.value)


def test_hamtningsfel_fangas_inte_av_slag_upp():
    """`slag_upp`:s kontrakt: hämtningens egna undantag når anroparen.

    Att översätta ett driftavbrott till `fordonet finns inte` hade gjort avbrottet
    osynligt. Fas 5:s anropare måste hantera BÅDA undantagen.
    """
    with pytest.raises(Hamtningsfel):
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar("", status=503))
        )


# ------------------------------------------------------------- hela kedjan


def test_avlast_fordon_ger_oklart():
    """Hela kedjan på det avlästa svaret.

    Tjänstevikten 2 140 kg passerar tröskeln 2 000, så fordonet är lämpligt som
    dragfordon. Draganordning saknas i registret och inget kundbesked finns, så
    utfallet är OKLART, alltså en fråga till kunden och inte ett påstående.
    """
    uppslag = fordonsuppslag.slag_upp(
        REGNR, hamta=biluppgifter_hamtning(oppna=svarar(SIDA_AVLAST))
    )

    assert uppslag.tjanstevikt_kg == 2140
    assert uppslag.slapvagnsvikt_kg == 2400
    assert uppslag.draganordning is False
    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART


def test_normaliserat_nummer_slar_igenom_till_canonical():
    """`slag_upp` normaliserar numret, och ankaret ska hålla för det.

    `abc 12-x` blir `ABC12X`, och sidan skriver `abc12x` i sin canonical.
    """
    uppslag = fordonsuppslag.slag_upp(
        "abc 12-x",
        hamta=biluppgifter_hamtning(oppna=svarar(sida(rader=HELA_RADER))),
    )

    assert uppslag.slapvagnsvikt_kg == 1400


def test_tomt_nummer_nar_aldrig_hamtningen():
    """Ett saknat nummer stoppas av `slag_upp` innan källan anropas."""

    def oppna(_regnr):
        raise AssertionError("hämtningen anropades trots tomt nummer")

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("", hamta=biluppgifter_hamtning(oppna=oppna))

    assert fel.value.skal == "registreringsnummer saknas"


# ------------------------------------------------------ nätverkslagret, utan nät


def test_natverksfel_blir_hamtningsfel(monkeypatch):
    """En URLError ur `urlopen` ska bli `Hamtningsfel`, aldrig nå anroparen rå."""

    def urlopen(*_a, **_k):
        raise urllib.error.URLError("namnet gick inte att slå upp")

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    with pytest.raises(Hamtningsfel) as fel:
        _hamta_sidan(REGNR)

    assert "gick inte att nå" in str(fel.value)


def test_httperror_404_blir_status_och_inte_undantag(monkeypatch):
    """En HTTP 404 ur `urlopen` översätts till status 404, inte till ett fel."""

    def urlopen(*_a, **_k):
        raise urllib.error.HTTPError(
            "https://biluppgifter.se/fordon/ABC12X/", 404, "Not Found", {}, None
        )

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    assert _hamta_sidan(REGNR) == (404, "")


def test_httperror_500_blir_hamtningsfel(monkeypatch):
    """En HTTP 500 ur `urlopen` blir `Hamtningsfel` med statusen i skälet."""

    def urlopen(*_a, **_k):
        raise urllib.error.HTTPError(
            "https://biluppgifter.se/fordon/ABC12X/", 500, "Server Error", {}, None
        )

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    with pytest.raises(Hamtningsfel) as fel:
        _hamta_sidan(REGNR)

    assert "500" in str(fel.value)


# ------------------------------------------------------ omförsöket, skiva 29


class _svar:
    """Ett lyckat `urlopen`-svar. Kontexthanterare, som det riktiga."""

    def __init__(self, kropp: str, status: int = 200):
        self.status = status
        self._kropp = kropp

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def read(self) -> bytes:
        return self._kropp.encode("utf-8")


def test_ett_omforsok_vid_natverksfel(monkeypatch):
    """Ett övergående nätverksfel ska inte fälla uppslaget.

    Första anropet faller, det andra lyckas, och hämtningen returnerar sidan.
    """
    anrop = []

    def urlopen(*_a, **_k):
        anrop.append(1)
        if len(anrop) == 1:
            raise urllib.error.URLError("tillfälligt")
        return _svar("<html></html>")

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    assert _hamta_sidan(REGNR) == (200, "<html></html>")
    assert len(anrop) == 2


def test_omforsoket_ar_ETT_och_ingen_loop(monkeypatch):
    """PÅSTÅENDET ÄR ATT DET INTE LOOPAR. Två fel ska ge upp, inte fortsätta.

    En loop mot en källa som inte svarar är skillnaden mellan ett uppslag som
    faller och en bot som hamrar. Räknaren är det som binder ordet ETT.
    """
    anrop = []

    def urlopen(*_a, **_k):
        anrop.append(1)
        raise urllib.error.URLError("nere")

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    with pytest.raises(Hamtningsfel):
        _hamta_sidan(REGNR)

    assert len(anrop) == 2


def test_en_statuskod_forsoks_ALDRIG_om(monkeypatch):
    """En statuskod är källans SVAR, inte tystnad, och ska inte frågas igen.

    Ett 403 blir inte 200 av ett omförsök. Villkoret som bär det är att
    `_hamta_sidan` fångar de RÅA nätverksundantagen och inte `Hamtningsfel`,
    som `_ett_forsok` kastar för båda sorterna.
    """
    anrop = []

    def urlopen(*_a, **_k):
        anrop.append(1)
        raise urllib.error.HTTPError(
            "https://biluppgifter.se/fordon/ABC12X/", 403, "Forbidden", {}, None
        )

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    with pytest.raises(Hamtningsfel):
        _hamta_sidan(REGNR)

    assert len(anrop) == 1


def test_avbruten_kropp_ar_ett_natverksfel_och_forsoks_om(monkeypatch):
    """`IncompleteRead` är VARKEN `OSError` ELLER `URLError`, mätt.

    En kropp som klipps mitt i är ett övergående nätverksfel, men den undantags-
    typen ligger utanför båda de arv `_hamta_sidan` fångade. Följden var tre på
    en gång: inget omförsök, ingen `Hamtningsfel`, och ingen loggrad, alltså ett
    uppslag som föll rått rakt igenom.

    Funnet av §7-granskningen av skiva 29, varv 1.
    """
    anrop = []

    def urlopen(*_a, **_k):
        anrop.append(1)
        if len(anrop) == 1:
            raise http.client.IncompleteRead(b"halv")
        return _svar("<html></html>")

    monkeypatch.setattr("src.biluppgifter.urllib.request.urlopen", urlopen)

    assert _hamta_sidan(REGNR) == (200, "<html></html>")
    assert len(anrop) == 2


def test_user_agent_namnger_oss_och_ar_ingen_forkladnad():
    """Beslut av Lars i skiva 29: ingen webbläsarförklädnad.

    Strängen ska namnge Auto Stockholm och en kontaktväg, så att den som läser
    sina serverloggar ser vem som frågar och kan höra av sig.
    """
    assert "AutoStockholm" in biluppgifter.UA
    assert "autostockholm.se" in biluppgifter.UA

    for forkladnad in ("Mozilla", "AppleWebKit", "Chrome", "Safari", "Gecko"):
        assert forkladnad not in biluppgifter.UA


# ------------------------------------------------------ loggen, skiva 29


def _loggrader() -> list[dict]:
    """Raderna i den omdirigerade loggfilen, eller tom lista om den inte finns."""
    if not biluppgifter.LOGGFIL.exists():
        return []
    return [
        json.loads(r)
        for r in biluppgifter.LOGGFIL.read_text(encoding="utf-8").splitlines()
        if r
    ]


def test_falt_som_saknas_loggas_som_markupandring():
    """**DET HÄR ÄR SKÄLET TILL ATT LOGGEN FINNS.**

    Sidan svarar 200, gäller rätt fordon, och går att parsa, men bär inte
    fälten. Det är vad en markupändring ser ut som. Utan loggraden syns den bara
    i att a-traktorsvaren tyst börjar hamna i `utkast`, alltså som försiktighet
    i stället för som ett fel.
    """
    utan_falt = sida(rader="")

    biluppgifter_hamtning(oppna=svarar(utan_falt))(REGNR)

    rader = _loggrader()
    assert [r["skal"] for r in rader] == ["falt_saknas"]
    assert rader[0]["saknade"] == sorted(EXAKT_ETIKETT)
    assert rader[0]["regnr"] == REGNR
    assert rader[0]["tidsstampel"]


def test_ett_fullstandigt_uppslag_loggar_INGENTING():
    """NEGATIVKONTROLL: loggen är inte ett larm som alltid går.

    En logg som skriver en rad per uppslag går inte att räkna misslyckanden ur,
    och då är den tillbaka till att vara osynlig.
    """
    biluppgifter_hamtning(oppna=svarar(sida(rader=HELA_RADER)))(REGNR)

    assert _loggrader() == []


@pytest.mark.parametrize(
    "oppna, skal",
    [
        (lambda _r: (_ for _ in ()).throw(Hamtningsfel("nere")), "natverksfel"),
        (lambda _r: (503, ""), "statuskod"),
        (lambda _r: (404, ""), "okant_fordon"),
    ],
)
def test_varje_misslyckad_vag_loggas_med_sitt_skal(oppna, skal):
    """Varje väg som inte ger fält ska gå att skilja från de andra i loggen.

    Skälen är grova med flit: de ska gå att räkna per dygn. En plötslig topp i
    `okant_fordon` betyder att canonical-ankaret slutat känna igen sidan, och en
    i `statuskod` att källan börjat avvisa oss.
    """
    hamta = biluppgifter_hamtning(oppna=oppna)
    try:
        hamta(REGNR)
    except Hamtningsfel:
        pass

    assert [r["skal"] for r in _loggrader()] == [skal]


def test_tvetydigt_canonical_ankare_loggas_och_kastas_vidare():
    """Lager 3:s TVETYDIGHETSKAST, som inte loggades alls.

    Två canonical-ankare betyder att sidan inte går att knyta till ett fordon.
    `_galler_fordonet` kastar då, och det kastet låg UTANFÖR loggens ram: ett
    uppslag misslyckades och skrev ingen rad. Det är precis den sortens
    källändring loggen byggdes för.

    Funnet av §7-granskningen av skiva 29, varv 1.
    """
    tvetydig = sida(regnr=REGNR).replace(
        "</head>",
        '<link rel="canonical" href="https://biluppgifter.se/fordon/XYZ99Z/">'
        "</head>",
    )

    with pytest.raises(Hamtningsfel):
        biluppgifter_hamtning(oppna=svarar(tvetydig))(REGNR)

    assert [r["skal"] for r in _loggrader()] == ["fel_vid_lasning"]


def test_en_otolkbar_sida_loggas_som_fel_vid_lasning():
    """`_las_falt`:s kast ska också bära en loggrad.

    Skälet `fel_vid_lasning` räknas upp i `docs/beslutslogg.md` #44, och var
    det enda av de sex som inget test rörde: loggraden gick att RADERA med hela
    sviten grön. Funnet av §7-granskningen av skiva 29, varv 1 som vakuöst.
    """
    otolkbar = sida(rader=rad("Släpvagnsvikt", "2400 kg <b>2500</b> kg"))

    with pytest.raises(Hamtningsfel):
        biluppgifter_hamtning(oppna=svarar(otolkbar))(REGNR)

    assert [r["skal"] for r in _loggrader()] == ["fel_vid_lasning"]


def test_fel_fordon_loggas_som_eget_skal():
    """Canonical-ankaret fäller, och det ska synas som något annat än 404."""
    biluppgifter_hamtning(oppna=svarar(sida(regnr="XYZ99Z")))(REGNR)

    assert [r["skal"] for r in _loggrader()] == ["fel_fordon"]


def test_loggningen_hindrar_aldrig_ett_uppslag(monkeypatch):
    """En full disk får inte fälla ett uppslag.

    Loggen är en observation, inte en spärr. Kastade skrivningen vidare hade en
    diskfull maskin gjort varje a-traktorsvar till ett utkast, alltså hade
    övervakningen blivit den sak som fäller.

    **FALLET MÅSTE VARA ETT SOM FAKTISKT LOGGAR.** Första lydelsen använde ett
    fullständigt uppslag, som med flit loggar INGENTING, så `OSError` inträffade
    aldrig och testet var vakuöst. Här saknas ett fält, alltså skrivs en rad, och
    det är skrivningen som vägrar.
    """
    def vagra(*_a, **_k):
        raise OSError("ingen plats kvar")

    monkeypatch.setattr(Path, "mkdir", vagra)

    utan_ett_falt = sida(rader=rad("Släpvagnsvikt", "2400 kg"))
    falt = biluppgifter_hamtning(oppna=svarar(utan_ett_falt))(REGNR)

    assert falt["slapvagnsvikt_kg"] == 2400


# ============================================================================
# SIDÄNDRINGAR: att uppslaget FALLER när källan ändrar sig, och inte gissar
# ============================================================================
#
# De elva mutationsfällningarna i `docs/sparrar.md` visar att lagren biter mot
# ändringar i KODEN. De visar inte att modulen faller rätt när SIDAN ändras, och
# det är det som faktiskt kommer att hända: biluppgifter.se ändrar sin markup
# utan att fråga oss.
#
# **KRAVET ÄR ENSIDIGT.** Ett fall får aldrig returnera ett värde som ser
# giltigt ut. Att falla till utkast är rätt utfall; att svara med ett tal vi
# inte kan stå för är en sändvägsdefekt.
#
# Sidorna nedan byggs ur `sida()` och `rad()`, alltså ur samma fixtur som resten
# av filen, och ligger därför i repot. Skiva 19:s överlämning bar fixturer i
# `/tmp`, och en fixtur utanför repot gör testet obeständigt.


def utfallet_av(kropp: str) -> str:
    """Kör hela vägen och ger skälet till att ärendet föll till utkast.

    **Misslyckas testet om ett värde kommer ut.** Det är hela poängen: den här
    hjälparen får aldrig kunna returnera något som liknar ett uppslag, så ett
    fall som börjar svara med fakta blir rött i stället för tyst grönt.
    """
    hamta = biluppgifter_hamtning(oppna=svarar(kropp))
    try:
        uppslag = fordonsuppslag.slag_upp(REGNR, hamta=hamta)
    except UppslagMisslyckades as fel:
        return fel.skal
    raise AssertionError(
        f"sidändringen gav ett uppslag i stället för att falla: {uppslag!r}"
    )


def sida_med(tjanstevikt="2140 kg", slapvagnsvikt="2400 kg", draganordning="Nej",
             *, etiketter=None, extra="", regnr=REGNR) -> str:
    """Den avlästa sidans fältblock, med ett led utbytt.

    Den obromsade raden följer alltid med den bromsade, eftersom det är den
    angränsningen prefixfällan handlar om.
    """
    namn = {"tj": "Tjänstevikt", "sl": "Släpvagnsvikt", "dr": "Draganordning"}
    namn.update(etiketter or {})

    rader = ""
    if tjanstevikt is not None:
        rader += rad(namn["tj"], tjanstevikt)
    if slapvagnsvikt is not None:
        rader += rad(namn["sl"], slapvagnsvikt) + rad("Släpvagnsvikt obromsad",
                                                      "750 kg")
    if draganordning is not None:
        rader += rad(namn["dr"], draganordning)
    return sida(regnr=regnr, rader=rader + extra)


def test_baslinjen_ger_ett_uppslag():
    """NOLLFALLET FÖR HELA AVSNITTET.

    Utan den här är varje test nedan värdelöst: om `sida_med()` inte längre
    bygger en läsbar sida faller allt till utkast av fel skäl, och samtliga
    test blir gröna utan att pröva något.
    """
    uppslag = fordonsuppslag.slag_upp(
        REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sida_med()))
    )

    assert uppslag.tjanstevikt_kg == 2140
    assert uppslag.slapvagnsvikt_kg == 2400
    assert uppslag.draganordning is False


# --- 1 till 3: etiketten omdöpt ---------------------------------------------


@pytest.mark.parametrize(
    ("led", "nytt_namn", "skal"),
    [
        ("sl", "Släpvikt max", "svaret saknar slapvagnsvikt_kg"),
        ("dr", "Dragkrok", "svaret saknar draganordning"),
        ("tj", "Egenvikt", "svaret saknar tjanstevikt_kg"),
    ],
)
def test_omdopt_etikett_faller_till_utkast(led, nytt_namn, skal):
    """FALL 1, 2 OCH 3. En omdöpt etikett ger noll träffar, inte fel träff.

    Asserar på SKÄLET och inte bara på att något kastades: utan det blir testet
    grönt även när ett annat fält är det som saknas.
    """
    assert utfallet_av(sida_med(etiketter={led: nytt_namn})) == skal


def test_omdopning_till_ett_prefix_faller_ocksa():
    """GRÄNSFALLET i fall 1. Den nya etiketten BÖRJAR med den gamla.

    `Släpvagnsvikt bromsad` innehåller `Släpvagnsvikt` som prefix. Lager 1
    kräver `</span>` direkt efter etiketten, så träffen uteblir. Vore
    matchningen ett prefix hade den här sidan i stället gett två träffar.
    """
    assert utfallet_av(
        sida_med(etiketter={"sl": "Släpvagnsvikt bromsad"})
    ) == "svaret saknar slapvagnsvikt_kg"


def test_entitetskodad_etikett_LASES():
    """Källan börjar skriva `Sl&auml;pvagnsvikt` i stället för `Släpvagnsvikt`.

    **TESTET ÄR VÄNT I SKIVA 22, och det är en avsiktlig beteendeändring.**
    Regexavläsningen jämförde byte för byte och lät därför en entitetskodning
    se ut som en omdöpning. Parsern avkodar entiteter i texten, så noden bär
    `Släpvagnsvikt` och läses som den etikett den är.

    **Skälet är att en entitetskodning INTE är en omdöpning.** Briefens fall 1
    handlar om att källan byter NAMN på fältet, och då ska uppslaget falla. Här
    står samma namn skrivet på ett annat sätt i samma teckenuppsättning, vilket
    är källans val av kodning och inte en semantisk ändring. Att falla på det
    hade varit att falla på något ofarligt, och en spärr som fäller på det
    ofarliga blir avstängd.

    Riktningen är prövad: `test_omdopt_etikett_faller_till_utkast` bevakar att
    en verklig omdöpning fortfarande faller.
    """
    sidan = sida_med(slapvagnsvikt=None, extra=rad("Sl&auml;pvagnsvikt", "2400 kg"))

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


# --- 4: värdet i annat format -----------------------------------------------


@pytest.mark.parametrize(
    ("varde", "vantat"),
    [
        # DE TVA FORSTA SER IDENTISKA UT OCH AR DET INTE. Den forsta bar
        # ett vanligt blanksteg, U+0020; den andra ett HART, U+00A0.
        # Skillnaden ar osynlig i kallan, och det ar hela skalet till den
        # har kommentaren: sidan anvander det harda som tusenavskiljare,
        # och ett monster som bara tal det vanliga hade tappat varje tal
        # over tusen. Samma osynliga tecken bar en notering i
        # `docs/sparrar.md`, av samma skal.
        ("1 200 kg", 1200),
        ("1 200 kg", 1200),
        ("1200 kg", 1200),
        ("2&nbsp;400 kg", 2400),
    ],
)
def test_format_som_sidan_faktiskt_anvander_lases(varde, vantat):
    """FALL 4, den halva som ska LYCKAS.

    **UPPDELNINGEN ÄR INTE LÄNGRE EN ÖPPEN PUNKT.** Skiva 21 avgjorde själv att
    briefens krav inte kunde gälla källans eget format och lyfte frågan. Lars
    besked i skiva 22 är att `1 200 kg` med hårt blanksteg SKA läsas, och att
    kravet gäller att `750 2400 kg` aldrig blir 7502400. Docstringen bar
    tidigare skivans egen tolkning; nu bär den beslutet.

    En modul som föll på källans egen tusenavskiljare hade inte kunnat slå upp
    något alls. Entiteten är med därför att sidan skriver sitt hårda blanksteg
    så, och parsern avkodar entiteter i noden innan värdet tolkas.
    """
    uppslag = fordonsuppslag.slag_upp(
        REGNR,
        hamta=biluppgifter_hamtning(oppna=svarar(sida_med(slapvagnsvikt=varde))),
    )

    assert uppslag.slapvagnsvikt_kg == vantat


@pytest.mark.parametrize(
    "varde",
    [
        "1200",
        "1,2 ton",
        "1.2 ton",
        "1200 lbs",
        "ca 1200 kg",
        "1200 kg (Teoretisk)",
        "-1200 kg",
        "1 200",
    ],
)
def test_okant_vardeformat_faller_till_utkast(varde):
    """FALL 4, den halva som ska FALLA.

    Inget av formaten får tolkas. `1200` utan enhet är det farligaste: talet är
    rätt och bara enheten saknas, så en tolerant parser hade gett ett värde som
    ser giltigt ut. `1,2 ton` är det näst farligaste, eftersom en parser som
    plockar första talet ur strängen hade gett 1 kg.
    """
    assert utfallet_av(
        sida_med(slapvagnsvikt=varde)
    ) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize("varde", ["Okänd", "Ja tack", "", "1", "-"])
def test_okant_draganordningsvarde_faller_till_utkast(varde):
    """FALL 4 för draganordningen, som inte är ett tal.

    Ett `Okänd` som tolkades som `Nej` hade gett ett svar som PÅSTÅR att
    dragkrok saknas. Det är just det påstående förvalet OKLART finns för.
    """
    assert utfallet_av(
        sida_med(draganordning=varde)
    ) == "svaret saknar draganordning"


# --- 5: fältet helt borttaget -----------------------------------------------


@pytest.mark.parametrize(
    ("led", "skal"),
    [
        ("slapvagnsvikt", "svaret saknar slapvagnsvikt_kg"),
        ("tjanstevikt", "svaret saknar tjanstevikt_kg"),
        ("draganordning", "svaret saknar draganordning"),
    ],
)
def test_borttaget_falt_faller_till_utkast(led, skal):
    """FALL 5. Ett fält som försvinner ur sidan ger ett saknat fält."""
    assert utfallet_av(sida_med(**{led: None})) == skal


# --- 6: två träffar på samma etikett ----------------------------------------


@pytest.mark.parametrize(
    "etikett", ["Släpvagnsvikt", "Tjänstevikt", "Draganordning"]
)
def test_dubblerad_etikett_kastar_i_stallet_for_att_valja(etikett):
    """FALL 6. Tvetydigheten kastar, den löses aldrig genom att ta första.

    **Utfallet är `Hamtningsfel` och inte utkast**, och skillnaden är avsiktlig:
    `slag_upp` fångar inte hämtningens egna undantag. Se
    `test_dubblettens_undantag_nar_anroparen` för vad det innebär.
    """
    varde = "Ja" if etikett == "Draganordning" else "9999 kg"

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(
                oppna=svarar(sida_med(extra=rad(etikett, varde)))
            ),
        )

    assert "tvetydigt" in str(fel.value)
    assert etikett in str(fel.value)


def test_dubblettens_undantag_nar_anroparen():
    """Att dubbletten inte tyst blir ett värde är det som prövas här.

    `Hamtningsfel` passerar `slag_upp` orört, så ärendet faller INTE till utkast
    via `UppslagMisslyckades` utan når anroparen som ett undantag. Fas 5 måste
    hantera båda, se `src/fordonsuppslag.py`. Det testet bevakar är att inget
    värde kommer ut, inte vilken av de två vägarna som tas.
    """
    hamta = biluppgifter_hamtning(
        oppna=svarar(sida_med(extra=rad("Släpvagnsvikt", "9999 kg")))
    )

    with pytest.raises(Hamtningsfel):
        fordonsuppslag.slag_upp(REGNR, hamta=hamta)


# --- 7 och 8: canonical-ankaret ---------------------------------------------


def test_canonical_for_annat_fordon_faller_till_utkast():
    """FALL 7. Sidan gäller ett annat fordon än det vi frågade om.

    Det är lager 3:s hela uppgift: ett välformat tal ur FEL bils sida passerar
    varje annan kontroll, eftersom det är ett välformat tal.
    """
    assert utfallet_av(
        sida_med(regnr="XYZ99Z")
    ) == "hämtningen gav inget svar"


def test_canonical_saknas_faller_till_utkast():
    """FALL 8. Utan ankare går svaret inte att knyta till numret.

    Förvalet är försiktigt: en sida vi inte kan knyta till numret får inte bli
    fordonsfakta om numret, även om den bär fält som ser rätt ut.
    """
    utan = sida_med().replace(
        f'<link rel="canonical" href="https://biluppgifter.se/fordon/'
        f'{REGNR.lower()}/"/>',
        "",
    )

    assert 'rel="canonical"' not in utan
    assert utfallet_av(utan) == "hämtningen gav inget svar"


def test_canonical_utan_nummer_faller_till_utkast():
    """FALL 8, varianten källan faktiskt svarar med på ett okänt nummer."""
    assert utfallet_av(sida_med(regnr=None)) == "hämtningen gav inget svar"


# --- 9: felsida med status 200 ----------------------------------------------


def test_felsida_utan_ankare_faller_till_utkast():
    """FALL 9. Källan svarar 200 med något annat än en fordonssida.

    Statuskoden duger inte som `finns fordonet`: söksidan kommer med 200.
    """
    assert utfallet_av(
        sida(regnr=None, rader="<h1>Ett fel inträffade</h1>")
    ) == "hämtningen gav inget svar"


def test_felsida_med_ratt_ankare_men_utan_falt_faller_till_utkast():
    """FALL 9, det svårare fallet: ankaret stämmer men innehållet är borta.

    Här passerar lager 3, och det är lager 1 och 4 som håller genom att inget
    fält går att läsa. Ett tomt fältblock får aldrig bli ett tomt uppslag som
    ser komplett ut.
    """
    assert utfallet_av(
        sida(regnr=REGNR, rader="<h1>Ett fel inträffade</h1>")
    ) == "svaret saknar tjanstevikt_kg"


def test_felsida_med_ratt_ankare_och_ett_enda_falt_faller_till_utkast():
    """FALL 9, det svåraste: ankaret stämmer och ETT fält går att läsa.

    Ett partiellt svar är det farligaste av felsidefallen, eftersom det ser ut
    som ett fungerande uppslag ända fram till spärren i `_kontrollera`.
    """
    assert utfallet_av(
        sida(regnr=REGNR, rader=rad("Tjänstevikt", "2140 kg"))
    ) == "svaret saknar slapvagnsvikt_kg"


# --- 10: tom eller trunkerad sida -------------------------------------------


@pytest.mark.parametrize("kropp", ["", "   \n  ", "<html>", "<!DOCTYPE html>"])
def test_tom_sida_faller_till_utkast(kropp):
    """FALL 10, tomhetens nollfall. Ingen kropp, inget ankare, inget svar."""
    assert utfallet_av(kropp) == "hämtningen gav inget svar"


def test_trunkerad_efter_ankaret_faller_till_utkast():
    """FALL 10. Svaret bröts av innan fältblocket hann komma.

    Ankaret finns, så lager 3 passerar, och det är avsiktligt: en trunkering
    ska falla på att fälten saknas och inte på att den råkar sakna ankare.
    """
    hel = sida_med()
    trunkerad = hel[: hel.find("<body>") + len("<body>")]

    assert 'rel="canonical"' in trunkerad
    assert utfallet_av(trunkerad) == "svaret saknar tjanstevikt_kg"


def test_trunkerad_mitt_i_ett_varde_faller_till_utkast():
    """FALL 10, gränsvärdet. Snittet går INUTI det värde som ska läsas.

    Värdespannen saknar sin avslutande tagg, så noden stängs aldrig och inget
    par bildas. Ett halvt tal får aldrig bli ett helt. *Här stod att mönstret
    inte matchar; det beskrev regexen som togs bort i skiva 22, och utfallet är
    detsamma av en annan anledning.*
    """
    hel = sida_med()
    trunkerad = hel[: hel.find("2400 kg") + len("2400")]

    assert "2400" in trunkerad
    assert utfallet_av(trunkerad) == "svaret saknar slapvagnsvikt_kg"


def test_trunkerad_mitt_i_en_etikett_faller_till_utkast():
    """FALL 10, andra gränsvärdet. Snittet går INUTI etiketten."""
    hel = sida_med()
    trunkerad = hel[: hel.find("Släpvagnsvikt") + len("Släpvagn")]

    assert utfallet_av(trunkerad) == "svaret saknar slapvagnsvikt_kg"


# --- markupändringar som listan inte namnger men källan kan göra ------------


@pytest.mark.parametrize(
    ("beskrivning", "block"),
    [
        (
            "etikettspannen får ett attribut",
            '<span class="label" data-id="7">Släpvagnsvikt</span>\n'
            '<span class="value">2400 kg</span>\n',
        ),
        (
            "klassen får ett ord till",
            '<span class="label bold">Släpvagnsvikt</span>\n'
            '<span class="value">2400 kg</span>\n',
        ),
        (
            "något skjuts in mellan etikett och värde",
            '<span class="label">Släpvagnsvikt</span>\n<i class="ikon"></i>\n'
            '<span class="value">2400 kg</span>\n',
        ),
        (
            "etiketten står i ett annat element än span",
            '<div class="label">Släpvagnsvikt</div>\n'
            '<div class="value">2400 kg</div>\n',
        ),
    ],
)
def test_markupandring_lases_av_parsern(beskrivning, block):
    """Ändringar källan kan göra utan att röra fältets NAMN eller VÄRDE.

    **TESTET VÄNDES I SKIVA 22 och SMALNADES I SKIVA 24.** Regexavläsningen
    beskrev sidans markup, så varje avvikelse gav ett saknat fält även när
    ändringen var rent kosmetisk. Parsern läser NODERNA, så ett attribut, ett
    klassord till eller ett annat elementnamn ändrar ingenting.

    **De två fall som gällde markup INUTI VÄRDET är flyttade härifrån.** Lars
    beslut i skiva 24 är att ett värde som bär ett element inte är ett tal och
    ska KASTA, se `test_varde_med_element_kastar`. Det är en avsiktlig
    inskränkning av skiva 22:s uppmjukning, och skälet är lucka 11: samma
    konkatenering som gjorde `2400 <abbr>kg</abbr>` läsbar gjorde
    `750<sup>1</sup> kg` till 7501.

    **Uppmjukningen står kvar där den är ofarlig.** Ett attribut eller ett annat
    elementnamn kan inte ändra ett TAL. Ett element inuti värdet kan.

    Det farliga i de gamla utfallen var inte att de föll, utan att SAMMA
    okänslighet för markup gjorde att en DUBBLERAD etikett inte upptäcktes. Det
    var skiva 21:s sändvägsdefekt 1.

    Beskrivningen bärs som parameter så att ett rött utfall namnger VILKEN
    ändring som slutade läsas.
    """
    sidan = sida_med(slapvagnsvikt=None, extra=block)

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


def test_markupandring_utan_etikettklassen_faller():
    """Byter källan `class="label"` mot något annat är fältet borta.

    Det är den enda markupändringen som faller till UTKAST, och den ska göra det:
    klassnamnet är hur parsern VET att noden är en etikett. *Här stod "den enda av
    de sex", vilket blev falskt av skiva 24: uppsättningen är nu fyra som läses,
    två som kastar och den här som faller.*
    Utan den finns inget fältblock att läsa, och att gissa utifrån position
    vore att bygga tillbaka den sortens antagande skiva 22 tog bort.
    """
    block = (
        '<span class="field-label">Släpvagnsvikt</span>\n'
        '<span class="value">2400 kg</span>\n'
    )

    assert utfallet_av(
        sida_med(slapvagnsvikt=None, extra=block)
    ) == "svaret saknar slapvagnsvikt_kg"


# --- de två sändvägsdefekter granskningen av skiva 21 hittade ---------------
#
# Båda låg INOM briefens tio kategorier, och båda returnerade ett värde där
# spärren skulle ha fällt. Testen nedan skrevs EFTER rättelsen och skulle ha
# fångat dem: fälls rättelsen blir de röda, se `docs/sparrar.md`.


@pytest.mark.parametrize(
    ("beskrivning", "forsta_vardet", "andra_vardet"),
    [
        ("första värdet i ett element", "<b>2400 kg</b>", "750 kg"),
        ("andra värdet i ett element", "2400 kg", "<b>750 kg</b>"),
        ("första värdet i en länk", '<a href="y">2400 kg</a>', "750 kg"),
    ],
)
def test_dubblett_dar_ett_varde_bar_markup_kastar_anda(
    beskrivning, forsta_vardet, andra_vardet
):
    """SÄNDVÄGSDEFEKT UR GRANSKNINGEN AV SKIVA 21, nu stängd.

    Lager 2 räknade träffar på HELA fältblocket, vars värdegrupp `([^<]*)` inte
    matchade ett värde med nästlad markup. Låg etiketten två gånger och ETT
    värde var nästlat gav mönstret EN träff, tvetydigheten tände aldrig, och
    modulen svarade med det andra värdet som om det vore entydigt. Uppmätt före
    rättelsen: **750 kg i stället för `Hamtningsfel`**, alltså den obromsade
    vikten under tröskeln där den rätta ligger över.

    **Premissen finns på den skarpa sidan**, se fixturkommentaren vid
    `SIDA_AVLAST`: 62 label-span mot 54 par. Att glappet i sin helhet beror på
    nästlad markup är en subtraktion och inte en avläsning; det som ÄR avläst är
    ett fall, `Chassinr / VIN`, vars value-span öppnar ett element. Ett räcker:
    formen förekommer på sidan. Att `Släpvagnsvikt` inte bär den i dag är en
    avläsning av i dag.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + '<span class="label">Släpvagnsvikt</span>\n'
            f'<span class="value">{forsta_vardet}</span>\n'
            + '<span class="label">Släpvagnsvikt</span>\n'
            f'<span class="value">{andra_vardet}</span>\n'
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "tvetydigt" in str(fel.value)


@pytest.mark.parametrize(
    "varde", ["750 2400 kg", "1 2 0 0 kg", "24 00 kg", "2400 750 kg"]
)
def test_flera_tal_i_ett_varde_kastar(varde):
    """SÄNDVÄGSDEFEKT UR GRANSKNINGEN AV SKIVA 21, OCH SKIVA 23 BYTER UTFALLET.

    Mönstret var `([\\d\\s\\u00a0]+)kg`, som tillät blanktecken var som helst i
    gruppen medan `re.sub` sedan klistrade ihop allt som blev kvar. Ett värde
    med TVÅ tal blev därför ETT: uppmätt före rättelsen gav `750 2400 kg` talet
    **7502400**, ett välformat heltal långt över tröskeln.

    Fallet är realistiskt: slår källan en dag ihop den bromsade och den
    obromsade vikten i en rad ser värdet ut precis så.

    **HÄR STOD `assert _tal(varde) is None`, och testet hette
    `test_flera_tal_i_ett_varde_ger_none`.** Skiva 22 stängde defekten genom att
    utelämna fältet, vilket gav utkast. Lars beslut i skiva 23 är att det inte
    räcker: ett fält som FANNS och lästes FEL får inte se ut som ett fält som
    saknades. `None` betyder vi vet inte, och det är inte vad vi vet här.
    """
    with pytest.raises(Hamtningsfel) as fel:
        _tal(varde)

    assert "felläsning" in str(fel.value)


def test_hopklistrat_med_hart_blanksteg_kastar_ocksa():
    """Samma sak när avskiljaren är hård, alltså i källans egen teckenform.

    Numret byggs med `chr(160)` och inte med ett tecken i källtexten. Ett hårt
    blanksteg går inte att skilja från ett vanligt när någon LÄSER filen, och
    ett test vars indata inte går att läsa är ett test ingen kan underhålla.
    Samma skäl som `docs/sparrar.md` anger för sina egna escaper.
    """
    with pytest.raises(Hamtningsfel):
        _tal("750" + chr(160) + "2400 kg")


def test_vardet_som_inte_ar_viktlikt_utelamnas_i_stallet_for_att_kasta():
    """DEL A:S GRÄNS, och den viktigaste raden i skivan.

    `Max 750 kg (Teoretisk)` bär siffror OCH enheten `kg` och ligger på sidans
    `Släp totalvikt`-rader, alltså i verkligt bruk. Den är ändå inte en
    felläsning utan ett fält vi inte kan tolka, och den ska därför ge `None`.

    Utan den här raden hade kastgrenen kunnat vidgas till varje värde som
    innehåller en siffra och bokstäverna `kg`, och då hade två av sidans egna
    rader tagit hela uppslaget med sig.
    """
    assert _tal("Max 750 kg (Teoretisk)") is None
    assert _tal("ca 1200 kg") is None
    assert _tal("1200 lbs") is None


def test_saknat_falt_ger_utkast_och_fellast_falt_kastar():
    """DEL A:S NEGATIVKONTROLL, båda riktningarna mätta i samma test.

    Poängen med skivan är SKILLNADEN mellan de två, och den syns bara när båda
    körs hela vägen genom `slag_upp`. Ett test som bara mätte kastet hade varit
    grönt även om allt annat också började kasta.
    """
    saknat = sida_med(slapvagnsvikt=None)
    assert utfallet_av(saknat) == "svaret saknar slapvagnsvikt_kg"

    fellast = sida_med(slapvagnsvikt="750 2400 kg")
    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(fellast))
        )

    assert "felläsning" in str(fel.value)
    assert "750 2400 kg" in str(fel.value)


def test_kand_lucka_hopklistring_under_gransen_ser_ut_som_tusengruppering():
    """KÄND LUCKA 9, registrerad i `docs/sparrar.md` och inte stängd.

    Två hopklistrade tal som landar under den övre rimlighetsgränsen går inte
    att skilja från en tusengruppering: `1 200 kg` och `750 400 kg` har exakt
    samma form. Mönstret läser båda som ETT tal, och det är riktigt för det
    första.

    **Skyddet ligger alltså i intervallet och inte i formen.** Det är en gräns
    och inget bevis: hade produkten hamnat under 9999 hade den passerat. Testet
    mäter påståendet i stället för att låta det stå som ett resonemang, och blir
    rött den dag någon tror sig ha stängt luckan i `_tal`.
    """
    assert _tal("750 400 kg") == 750400

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(
                oppna=svarar(sida_med(slapvagnsvikt="750 400 kg"))
            ),
        )

    assert "utanför" in str(fel.value)


@pytest.mark.parametrize(
    ("varde", "vantat"),
    [
        ("750 kg", 750),
        ("2140 kg", 2140),
        ("2750 kg", 2750),
        ("610 kg", 610),
    ],
)
def test_skarpta_talmonstret_laser_fortfarande_sidans_varden(varde, vantat):
    """NOLLFALLET FÖR SKÄRPNINGEN.

    Ett strängare mönster som också slutade läsa källans egna värden vore en
    värre defekt än den det rättar.

    **De fyra talen är AVLÄSTA**, och står i den formen i `SIDA_AVLAST`: utan
    tusenavskiljare. Här stod först `2 750 kg` och `9999 kg` och kallade båda
    fixturens. `2 750` är avläst men inte i den formen, och `9999` finns inte
    bland de åtta avlästa värdena alls; det är ett tal skivan själv hittade på
    till dubblettfixturerna. Formen med avskiljare prövas av
    `test_format_som_sidan_faktiskt_anvander_lases`, som inte påstår att den är
    avläst.
    """
    assert _tal(varde) == vantat


def test_bara_den_obromsade_raden_kvar_faller_till_utkast():
    """FALL 5, gränsvärdet `sida_med` inte kan bygga.

    `sida_med(slapvagnsvikt=None)` tar bort BÅDA släpvagnsraderna, eftersom den
    obromsade följer med den bromsade. Det realistiska fall 5 är det andra:
    källan tar bort den BROMSADE raden och låter den obromsade stå kvar. Då
    finns en rad vars etikett BÖRJAR med den vi söker, och det är precis
    prefixfällans läge.

    Lager 1 jämför etikettnodens text med LIKHET, så `Släpvagnsvikt obromsad`
    är en annan etikett och fältet utelämnas. Vore jämförelsen ett prefix hade
    750 kg kommit in här. *Här stod att lager 1 kräver `</span>` direkt efter
    etiketten; det beskrev regexen som togs bort i skiva 22.*
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Släpvagnsvikt obromsad", "750 kg")
            + rad("Draganordning", "Nej")
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize(
    ("beskrivning", "url"),
    [
        ("annan sökväg på rätt domän", "https://biluppgifter.se/sok/abc12x/"),
        ("rätt sökväg på annan domän", "https://exempel.invalid/fordon/abc12x/"),
        ("relativt ankare utan domän", "/fordon/abc12x/"),
        ("okrypterat schema", "http://biluppgifter.se/fordon/abc12x/"),
        ("numret bara som suffix", "https://biluppgifter.se/fordon/xabc12x/"),
        ("www på en annan domän", "https://www.exempel.invalid/fordon/abc12x/"),
        ("värdnamn som bara börjar likadant", "https://wwwbiluppgifter.se/fordon/abc12x/"),
    ],
)
def test_ankaret_provar_hela_urlen(beskrivning, url):
    """LUCKA 6 ÄR STÄNGD i skiva 22, och testet är vänt.

    Här stod `test_ankaret_provar_bara_sista_segmentet`, som FÄSTE att
    `_galler_fordonet` jämförde `rsplit("/", 1)[-1]` och därför godtog vilken
    domän och vilken sökväg som helst så länge numret stod sist. Skiva 21:s
    granskning mätte upp följden: ett ankare på en helt annan domän med rätt
    nummer sist gav ett uppslag.

    Lars beslut i #32 är att hela URL:en jämförs. Schema, värdnamn och sökväg
    prövas, inte bara numret. **Det relativa ankaret faller med de andra**, och
    det är avsiktligt: utan värdnamn går det inte att bekräfta vilken domän
    svaret kom ifrån, och då gäller samma försiktiga förval som vid ett saknat
    ankare.

    Beskrivningen bärs som parameter så att ett rött utfall namnger VILKEN form
    som slutade falla.
    """
    assert _galler_fordonet(f'<link rel="canonical" href="{url}"/>', REGNR) is False


@pytest.mark.parametrize(
    ("beskrivning", "url"),
    [
        ("www på rätt domän", "https://www.biluppgifter.se/fordon/abc12x/"),
        ("versalt www", "https://WWW.BILUPPGIFTER.SE/fordon/ABC12X/"),
    ],
)
def test_www_ar_samma_vard(beskrivning, url):
    """DEL C I SKIVA 23: en strikthet vars fel inte gick att se.

    Skiva 22 avvisade `www.biluppgifter.se`. Riktningen var säker, men följden
    var att en dag då källan börjar skriva `www` i sin canonical faller VARJE
    uppslag till utkast, utan larm och utan rött test. Boten slutar fungera och
    ingen märker det.

    Lars beslut är att `www` godtas som samma värd.
    `test_ankaret_provar_hela_urlen` bär motsatsen och står kvar oförändrad i
    sitt påstående: varje ANNAN domän avvisas fortfarande, `www` eller inte.
    """
    assert _galler_fordonet(f'<link rel="canonical" href="{url}"/>', REGNR) is True


@pytest.mark.parametrize(
    ("beskrivning", "forsta_taggen"),
    [
        ("attribut i etikettspannen", '<span class="label" data-id="7">'),
        ("extra blanksteg i taggen", '<span  class="label">'),
        ("enkelfnuttar kring klassen", "<span class='label'>"),
    ],
)
def test_dubblett_dar_ena_etiketten_bar_attribut_kastar_anda(
    beskrivning, forsta_taggen
):
    """SÄNDVÄGSDEFEKT UR ANDRA GRANSKNINGSVARVET, nu stängd.

    Den regexbaserade räknaren var lika sträng som läsaren. Bar den ENA av två
    etikettspannar ett attribut såg räknaren en enda förekomst, läsaren en enda
    träff, och det andra värdet gick ut som om det vore entydigt. Samma klass,
    samma riktning och samma tysthet som defekten den skulle stänga.

    **DEN DÅVARANDE RÄTTELSEN VAR ATT GÖRA RÄKNAREN LÖSARE ÄN LÄSAREN.** Den
    höll för attributen här men inte för ett extra klassord eller nästlad
    markup, vilket tredje granskningsvarvet fällde. Skiva 22 löste hela klassen
    genom att parsa sidan, och testet står kvar oförändrat i sitt påstående:
    varje form av dubblett ska kasta, oavsett hur avläsningen är byggd.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + f'{forsta_taggen}Släpvagnsvikt</span>\n'
            '<span class="value">750 kg</span>\n'
            + rad("Släpvagnsvikt", "2400 kg")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "tvetydigt" in str(fel.value)


@pytest.mark.parametrize(
    "varde", ["  2400 kg  ", "\t2400 kg\n", "\n\t\t2400 kg\n\t"]
)
def test_varde_med_omgivande_blanktecken_lases(varde):
    """`.strip()` FÖRE MATCHNINGEN, och det här är testet som binder den.

    Sidans HTML är indenterad, så ett värde med omgivande blanktecken i sin
    value-span är källans normalform och inget kantfall.

    **Det här testet ersätter en vakt som slutade vakta.**
    `test_bara_blanktecken_fore_enheten_ger_none` skrevs för `.strip()` mot det
    GAMLA talmönstret, där `' kg'` utan strip gav `ValueError`. Med det skärpta
    mönstret ger `' kg'` `None` med eller utan strip, så fällningen av
    `.strip()` blev GRÖN och testet vakuöst i §7.1:s mening. Uppmätt i skiva
    21:s andra granskningsvarv.
    """
    assert _tal(varde) == 2400


def test_en_etikettspan_utan_vardepar_kastar():
    """FÖLJDEN AV ATT RÄKNAREN ÄR LÖSARE, utskriven i stället för utelämnad.

    En `class="label"`-span som bär en av de tre etiketterna men inget värdepar
    räknas också. En rubrik i den formen ger därför `Hamtningsfel` i stället för
    att sidan läses.

    Riktningen är säker, inget värde kommer ut. Men skälet säger `förekommer 2
    gånger` om något som är ETT fält och EN rubrik, och det är priset för att
    räknaren hellre överskattar. Testet fäster beteendet så att en framtida
    uppmjukning blir ett medvetet val.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Släpvagnsvikt", "2400 kg")
            + rad("Draganordning", "Nej")
            + '<h3><span class="label">Tjänstevikt</span></h3>\n'
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "Tjänstevikt" in str(fel.value)


# --- skiva 22: parsern stänger de två öppna sändvägsdefekterna ---------------
#
# Båda fälldes av skiva 21:s TREDJE granskningsvarv, alltså efter att skivans
# egna tio fall var gröna. Båda returnerade ett värde där spärren skulle ha
# fällt. Testen nedan skrevs EFTER ombyggnaden och skulle ha fångat dem: fälls
# parsern tillbaka mot en textmatchning blir de röda, se `docs/sparrar.md`.


@pytest.mark.parametrize(
    ("beskrivning", "forsta_etiketten"),
    [
        ("klassen bär ett ord till", '<span class="label bold">Släpvagnsvikt</span>'),
        ("etiketten bär nästlad markup", '<span class="label"><b>Släpvagnsvikt</b></span>'),
        ("etiketten står i en div", '<div class="label">Släpvagnsvikt</div>'),
        ("etiketten står i en tabellcell", '<th class="label">Släpvagnsvikt</th>'),
        ("etiketten bär ett attribut", '<span class="label" data-id="7">Släpvagnsvikt</span>'),
    ],
)
def test_dubblett_dar_etiketten_bar_annan_markup_kastar(beskrivning, forsta_etiketten):
    """ÖPPEN SÄNDVÄGSDEFEKT 1 ur skiva 21, stängd i skiva 22.

    Sidan bär `Släpvagnsvikt` TVÅ gånger, 2400 kg först och 750 kg sedan. Bar
    den ena förekomsten ett extra klassord, nästlad markup runt namnet, eller
    ett annat element än `span`, såg den gamla räknaren en enda förekomst.
    Tvetydigheten tände aldrig och **750 gick ut där 2400 var rätt**, alltså
    den obromsade vikten UNDER tröskeln där den bromsade ligger över.

    Uppmätt i skiva 21 hela vägen genom `slag_upp`, inte resonerat fram.

    Parsern räknar etiketten som en NOD, så elementnamnet och de övriga
    klassorden spelar ingen roll. Riktningen är prövad per form, och
    beskrivningen bärs som parameter så att ett rött utfall namnger VILKEN.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + forsta_etiketten
            + '\n<span class="value">2400 kg</span>\n'
            + rad("Släpvagnsvikt", "750 kg")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "förekommer 2 gånger" in str(fel.value)


def test_dubblerad_draganordning_kastar_i_stallet_for_att_valja():
    """Samma defekt på det fält som avgör dragkroksbeskedet.

    En sida som säger både `Ja` och `Nej` om draganordning har inte sagt något
    vi kan skicka. Den gamla koden valde tyst den ena, och vilken avgjordes av
    vilken av etiketterna som råkade bära markup.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Släpvagnsvikt", "2400 kg")
            + '<span class="label"><b>Draganordning</b></span>\n'
              '<span class="value">Ja</span>\n'
            + rad("Draganordning", "Nej")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "Draganordning" in str(fel.value)


@pytest.mark.parametrize(
    ("beskrivning", "oppna_tagg", "stang_tagg"),
    [
        ("HTML-kommentar", "<!--", "-->"),
        ("template-element", "<template>", "</template>"),
        ("script-element", "<script>", "</script>"),
        ("style-element", "<style>", "</style>"),
    ],
)
def test_inaktivt_falt_lases_inte(beskrivning, oppna_tagg, stang_tagg):
    """ÖPPEN SÄNDVÄGSDEFEKT 2 ur skiva 21, stängd i skiva 22.

    Fältet är BORTTAGET ur sidan i briefens fall 5, men står kvar som text
    inuti något som inte är sidans data. Den gamla koden läste HTML som en
    sträng och svarade därför med det inaktiva värdet.

    **En kommentar och ett `template` är inte noder i ett parsat träd.**
    `HTMLParser` skickar kommentaren till `handle_comment` och aldrig till
    `handle_data`, och `HOPPAS_OVER` hoppar över de tre elementen. Ingen av
    dem kan alltså bidra med en etikett eller ett värde.

    `script` och `style` är med av samma skäl: en etikett i en JSON-sträng
    inuti ett `script` är text för maskinen och inte ett fält på sidan.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + oppna_tagg
            + "\n"
            + rad("Släpvagnsvikt", "750 kg")
            + stang_tagg
            + "\n"
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_etikett_och_varde_maste_vara_syskon():
    """Parsningen fick INTE bli lösare än regexen på avståndet.

    Den gamla regexen krävde att värdespannen följde direkt efter
    etikettspannen. En parser som bara letar `nästa värdenod` hade släppt det
    kravet helt, och då kunde en etikett utan värde paras ihop med ett värde
    utan etikett längre ned i dokumentet.

    Här ligger etiketten ensam i ett block som stängs, och värdet i ett annat.
    Paret vore en gissning, och fältet ska därför utelämnas. Testet finns
    eftersom risken infördes av ombyggnaden och inte av källan.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + '<div><span class="label">Släpvagnsvikt</span></div>\n'
            + '<div><span class="value">750 kg</span></div>\n'
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_varde_pa_annan_niva_paras_inte_med_etiketten():
    """Andra lagret i syskonvillkoret, och det behövde ett eget test.

    Här stängs ingen förälder mellan etiketten och värdet: båda ligger under
    `<body>`, men värdet ett steg djupare. Föräldrastängningen fångar det
    därför inte, och utan nivåjämförelsen hade paret bildats.

    **§7.1-prövningen fann att villkoret var OBUNDET.** Fällningen av
    `foralder == self._vantar_foralder` gav GRÖN, eftersom
    `test_etikett_och_varde_maste_vara_syskon` täcks av föräldrastängningen.
    Ett villkor som inget test kan fälla ser ut som försiktighet utan att vara
    det. Det här testet gör det äkta i stället för att villkoret tas bort:
    risken det vaktar är verklig, nämligen en etikett och ett värde som ligger
    långt isär under en gemensam förälder som aldrig stänger emellan.

    Värdet på sidan är den obromsade 750 kg, alltså UNDER tröskeln där den
    rätta ligger över. Riktningen är den farliga.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + '<span class="label">Släpvagnsvikt</span>\n'
            + '<div><span class="value">750 kg</span></div>\n'
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_etikett_utan_varde_i_samma_block_lases_anda():
    """Nollfallet till syskonvillkoret: något emellan får inte fälla.

    Villkoret är att etikett och värde ligger på samma nivå under samma
    förälder, INTE att de står omedelbart efter varandra. En ikon eller en rad
    markup mellan dem är en rimlig omdesign och ska inte göra fältet borta.
    """
    sidan = sida_med(
        slapvagnsvikt=None,
        extra=(
            '<span class="label">Släpvagnsvikt</span>\n'
            '<i class="ikon"></i><span class="hjalp">?</span>\n'
            '<span class="value">2400 kg</span>\n'
        ),
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


# --- skiva 22 DEL B: ankaret prövar hela URL:en och kastar på tvetydighet ----


def test_tva_canonical_ankare_kastar():
    """Lager 3 beter sig nu som lager 2 i samma läge.

    Den gamla koden tog `re.search`, alltså FÖRSTA träffen. En sida med vårt
    fordon först och ett annat sedan gav därför ett uppslag, uppmätt i
    skiva 21. Tvetydigheten var reell och besvarades med en gissning.

    Ordningen prövas i båda riktningar, eftersom det var just ordningsberoendet
    som gjorde defekten osynlig: med det andra fordonet först föll den redan.
    """
    ankare = (
        '<link rel="canonical" href="https://biluppgifter.se/fordon/abc12x/"/>'
        '<link rel="canonical" href="https://biluppgifter.se/fordon/xyz99z/"/>'
    )

    with pytest.raises(Hamtningsfel) as fel:
        _galler_fordonet(ankare, REGNR)

    assert "2 canonical-ankare" in str(fel.value)


def test_tva_ankare_kastar_aven_i_omvand_ordning():
    """Samma sida, andra ordningen. Utfallet får inte bero på den."""
    ankare = (
        '<link rel="canonical" href="https://biluppgifter.se/fordon/xyz99z/"/>'
        '<link rel="canonical" href="https://biluppgifter.se/fordon/abc12x/"/>'
    )

    with pytest.raises(Hamtningsfel):
        _galler_fordonet(ankare, REGNR)


def test_ankaret_i_kommentar_raknas_inte():
    """Ett ankare som ligger i en kommentar är inte sidans ankare.

    Nollfallet till tvetydighetskontrollen: utan det hade en bortkommenterad
    rad kunnat göra varje sida tvetydig och stängt av uppslaget helt.
    """
    sidan = sida_med()
    med_kommentar = sidan.replace(
        "<body>",
        '<body><!--<link rel="canonical" href="https://biluppgifter.se/fordon/xyz99z/"/>-->',
    )

    assert _galler_fordonet(med_kommentar, REGNR) is True


def test_ratt_ankare_slar_fortfarande_igenom():
    """Nollfallet till hela DEL B: den avlästa sidans ankare ska gälla."""
    assert _galler_fordonet(SIDA_AVLAST, REGNR) is True


# --- skiva 22 DEL C: rimlighetskontrollen, lucka 5 --------------------------


@pytest.mark.parametrize(
    ("varde", "tal"),
    [
        ("10000 kg", 10000),
        ("99999 kg", 99999),
        ("7502400 kg", 7502400),
        ("0 kg", 0),
    ],
)
def test_orimlig_vikt_kastar(varde, tal):
    """Ett värde utanför intervallet är en FEL LÄSNING, inte ett fordon.

    Beslut av Lars, `docs/beslutslogg.md` #32. Talet 7502400 är det defekten i
    skiva 21 faktiskt producerade, ur `750 2400 kg`. `_tal` är skärpt så att
    just den hopklistringen inte längre går, men kontrollen står oberoende av
    mönstrets form: nästa avläsningsfel behöver inte se ut som det förra.

    Gränserna och deras härkomst står i `_krav_pa_rimlighet`. Den övre är
    SIFFERGRÄNSEN, fyra siffror, och inte en kalibrerad personbilsgräns.
    """
    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(
                oppna=svarar(sida_med(slapvagnsvikt=varde))
            ),
        )

    assert str(tal) in str(fel.value)


@pytest.mark.parametrize("varde", ["1 kg", "9999 kg", "2400 kg"])
def test_vikt_i_intervallet_lases(varde):
    """Gränsvärdena. `1` och `9999` är intervallets ändpunkter och ska LÄSAS.

    Utan det här testet hade kontrollen kunnat skärpas till att fälla sina egna
    ändpunkter utan att någon rad blev röd.
    """
    hamta = biluppgifter_hamtning(oppna=svarar(sida_med(slapvagnsvikt=varde)))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == int(
        varde.split()[0]
    )


def test_orimlig_tjanstevikt_kastar_ocksa():
    """Kontrollen gäller BÅDA vikterna, inte bara den som bar defekten."""
    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(
                oppna=svarar(sida_med(tjanstevikt="12000 kg"))
            ),
        )

    assert "tjanstevikt_kg" in str(fel.value)


@pytest.mark.parametrize("element", ["sup", "small"])
def test_fotnot_i_etiketten_lases_som_samma_etikett(element):
    """LUCKA 7 ÄR STÄNGD I SKIVA 23, och det här testet är VÄNT.

    Här stod `test_fotnot_i_etiketten_ger_saknat_falt`, som fäste att en fotnot
    gjorde nodens text `Släpvagnsvikt1` och därmed fältet borta. Det utfallet var
    rätt riktning men fel egenskap: det var samma okänslighet som gjorde att en
    sida med BÅDE den fotnotade och en oförändrad `Släpvagnsvikt` räknade en enda
    förekomst, lät tvetydigheten tystna, och släppte ut det andra parets värde.

    Lars beslut är att uteslutningen sker strukturellt, i `FOTNOTSELEMENT`.
    Etiketten med fotnot är därmed SAMMA etikett som utan, och fältet läses.
    """
    sidan = sida_med(
        slapvagnsvikt=None,
        extra=(
            f'<span class="label">Släpvagnsvikt<{element}>1</{element}></span>\n'
            '<span class="value">2400 kg</span>\n'
        ),
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


@pytest.mark.parametrize("element", ["sup", "small"])
def test_dubblett_dar_ena_etiketten_bar_fotnot_kastar(element):
    """DEN ELFTE FORMEN AV DEFEKT 1, och den enda som stod öppen efter skiva 22.

    Sidan bär `Släpvagnsvikt` två gånger, 2400 kg i den fotnotade och 750 kg i
    den rena. Räknades bara den rena gick **750 ut där 2400 var rätt**, alltså
    den obromsade vikten UNDER tröskeln där den bromsade ligger över. Uppmätt i
    skiva 22 hela vägen genom `slag_upp`.

    Med fotnoten utesluten ur etikettens text är de två samma nod-text, och
    lager 2 räknar två.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + f'<li><span class="label">Släpvagnsvikt<{element}>1</{element}></span>\n'
            '<span class="value">2400 kg</span></li>\n'
            + rad("Släpvagnsvikt", "750 kg")
            + rad("Draganordning", "Nej")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "tvetydigt" in str(fel.value)


def test_fotnoten_gor_inte_obromsad_till_samma_etikett():
    """GRÄNSEN FÖR DEL B, och skälet till att uteslutningen är säker.

    Kravet på lösningen var att `Släpvagnsvikt` med fotnot blir samma etikett som
    utan, MEDAN `Släpvagnsvikt obromsad` förblir en annan. Uteslutningen tar bort
    fotnotens text, aldrig etikettens egen, så den andra raden är oförändrad.

    Vore den inte det hade den obromsade vikten kunnat läsas som den bromsade,
    vilket är precis den defekt `EXAKT_ETIKETT` finns för att stoppa.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + '<li><span class="label">Släpvagnsvikt obromsad<sup>1</sup></span>\n'
            '<span class="value">750 kg</span></li>\n'
            + rad("Draganordning", "Nej")
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize("element", ["sup", "small"])
def test_ord_i_fotnotselementet_ar_en_del_av_namnet(element):
    """SÄNDVÄGSDEFEKT UR GRANSKNINGEN AV SKIVA 23, nu stängd.

    Den första uteslutningen tog bort ALLT innehåll i ett `sup` eller `small`.
    Skriver källan `Släpvagnsvikt<small> obromsad</small>` blev nodens text då
    `Släpvagnsvikt`, och modulen svarade med den OBROMSADE vikten som om den vore
    den bromsade: **750 kg under tröskeln där 2400 kg är rätt.** Uppmätt hela
    vägen genom `slag_upp`.

    Markupen är inte konstruerad. Modulens egen kommentar säger att `small` bär
    en upplysning i småstil, och `obromsad` ÄR en upplysning i småstil.

    Ett fotnotselement som bär en BOKSTAV är ett ord, och ett ord i etikettnoden
    hör till fältets namn. Texten behålls, etiketten blir en annan sträng, och
    fältet faller till utkast.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + f'<li><span class="label">Släpvagnsvikt<{element}> obromsad</{element}>'
            '</span>\n<span class="value">750 kg</span></li>\n'
            + rad("Draganordning", "Nej")
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize("element", ["sup", "small"])
def test_hela_namnet_i_ett_fotnotselement_gor_inte_etiketten_osynlig(element):
    """ANDRA SÄNDVÄGSDEFEKTEN UR GRANSKNINGEN AV SKIVA 23, nu stängd.

    Står hela etikettnamnet inuti fotnotselementet blev nodens text TOM med den
    första uteslutningen. Räknaren såg då en enda förekomst av `Släpvagnsvikt`,
    tvetydigheten tände aldrig, och det andra parets 750 kg gick ut.

    **Det är lucka 7 själv, återöppnad av sin egen rättelse**, och den fällde en
    sida som skiva 22 kastade på.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + f'<li><span class="label"><{element}>Släpvagnsvikt</{element}></span>\n'
            '<span class="value">2400 kg</span></li>\n'
            + rad("Släpvagnsvikt", "750 kg")
            + rad("Draganordning", "Nej")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "tvetydigt" in str(fel.value)


@pytest.mark.parametrize("markor", ["1", "*", "†", "2)"])
def test_markorer_utan_bokstav_utesluts(markor):
    """GRÄNSEN ÅT ANDRA HÅLLET: vad som FAKTISKT räknas som en markör.

    Siffra, asterisk, kors och en siffra med parentes bär ingen bokstav och är
    därför markörer. Utan den här raden hade villkoret kunnat skärpas till att
    bara godta en ensam siffra utan att någon rad blev röd.
    """
    sidan = sida_med(
        slapvagnsvikt=None,
        extra=(
            f'<span class="label">Släpvagnsvikt<sup>{markor}</sup></span>\n'
            '<span class="value">2400 kg</span>\n'
        ),
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


@pytest.mark.parametrize(
    ("beskrivning", "varde"),
    [
        ("markör efter talet", "750<sup>1</sup> kg"),
        ("markör före talet", "<sup>1</sup>750 kg"),
        ("markör mitt i talet", "7<sup>1</sup>50 kg"),
        ("markör efter enheten", "750 kg<sup>1</sup>"),
        ("small i stället för sup", "750<small>2</small> kg"),
        ("enheten i ett element", "2400 <abbr>kg</abbr>"),
        ("hela värdet i ett element", "<b>2400 kg</b>"),
        ("tomt element i värdet", "2400 kg<br>"),
    ],
)
def test_varde_med_element_kastar(beskrivning, varde):
    """LUCKA 11 ÄR DELVIS STÄNGD I SKIVA 24. Beslut av Lars: kasta, sanera inte.

    **Den återstående vägen är lucka 12**, se `docs/sparrar.md`: en sluttagg som
    stänger ett element UNDER värdet klipper värdets text utan att flaggan sätts.
    Det här testet bär inte den vägen.

    **VAD LUCKAN VAR.** Parsern konkatenerar textnoderna i ett värde, så en
    markör inuti talet blev en siffra I talet. Uppmätt hela vägen genom
    `slag_upp`: `750<sup>1</sup> kg` gav **7501**, `<sup>1</sup>750 kg` gav
    **1750**, och `7<sup>1</sup>50 kg` gav **7150**. Alla tre ligger inom
    rimlighetsintervallet och ÖVER `TROSKEL_SLAPVAGNSVIKT_KG`, så ett fordon med
    verkliga 750 kg fick ett jakande besked på ett tal ingen källa skrivit.

    **LUCKAN INFÖRDES AV PARSERN I SKIVA 22 och var öppen i två committade
    versioner**, `8629223` och `52d0a97`. Den kom fram först när skiva 23 tittade
    på fotnotselement i ETIKETTER, alltså av en tillfällighet och inte av att
    någon letade.

    **VARFÖR KAST OCH INTE SANERING.** Att plocka bort tecken ur ett värde vore
    att ändra ett tal vi skickar vidare. En sida som skriver 750 med en fotnot
    inuti säger något vi inte kan tolka, och då är avläsningen fel. Samma regel
    som `750 2400 kg` fick i skiva 23: ett fält som fanns men lästes fel ser inte
    ut som ett fält som saknades.

    **KOSTNADEN ÄR SYNLIG, och det är hela poängen.** En fotnot i ett värde ger
    nu ett kast i stället för ett tal. Det märks. 7501 märktes inte.

    `markör efter enheten` stod tidigare för utkast och kastar nu. Utfallet är
    fortfarande att inget värde kommer ut, men skälet är ett annat och det ska
    synas.
    """
    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(oppna=svarar(sida_med(slapvagnsvikt=varde))),
        )

    assert "bär markup" in str(fel.value)


@pytest.mark.parametrize(
    ("beskrivning", "varde"),
    [
        ("HTML-kommentar", "750<!--x-->1 kg"),
        ("processing instruction", "750<?x?>1 kg"),
        ("declaration", "750<!doctype y>1 kg"),
        ("ensam sluttagg utan starttagg", "750</b>1 kg"),
        ("sluttagg för ett tomt element", "750</br>1 kg"),
        ("sluttagg för img", "750</img>1 kg"),
        ("CDATA-sektion", "750<![CDATA[x]]>1 kg"),
    ],
)
def test_varde_avdelat_av_nagot_som_inte_ar_text_kastar(beskrivning, varde):
    """SÄNDVÄGSDEFEKT UR GRANSKNINGEN AV SKIVA 24, nu stängd.

    **Spärrens första lydelse följde bara STARTTAGGAR.** De fyra formerna här
    avdelar textnoden utan att vara en tagg, och alla fyra gav `7501` på en sida
    vars verkliga släpvagnsvikt är 750 kg. Uppmätt hela vägen genom `slag_upp`,
    med tjänstevikten under tröskeln så att släpvagnsvikten avgör: **beskedet
    vändes från NEJ till JA**.

    Texten blev bit för bit densamma som `750<sup>1</sup> kg` gav, alltså samma
    defekt genom en annan dörr.

    **Den ensamma sluttaggen är den farligaste.** `_Faltlasare`:s docstring
    skriver ut som en EGENSKAP att en sluttagg utan motsvarande starttagg
    ignoreras helt. Den egenskapen är riktig för stacken och var fel för värdet,
    och det är just den sortens halvsanning som blir en spärr med hål.

    Skälet att lydelsen var för smal är mekaniskt: den beskrev en HÄNDELSE, `en
    tagg öppnas`, i stället för det den skulle vakta, `värdets text är avdelad av
    något som inte är text`.

    **DE TVÅ SLUTTAGGSFALLEN FÖR TOMMA ELEMENT KOM AV ATT RÄTTELSEN GJORDE OM
    SAMMA FEL.** Den första rättelsen lade flaggan i `handle_endtag`:s gren för en
    sluttagg utan öppen motsvarighet, men `handle_endtag` returnerar för
    `TOMMA_TAGGAR` FÖRE den grenen. `750</br>1 kg` gav därför fortfarande 7501,
    uppmätt av granskningsvarv 2 i skiva 24. *Här stod "de två sista fallen".
    Skiva 25 lade till CDATA-parametern sist och gjorde meningen falsk i samma
    commit; fällt av granskningsvarv 2 i skiva 25.* Det är samma tidiga return som `handle_starttag`:s egen
    kommentar varnar för, och rättelsen hade tillämpat insikten på den ena
    metoden och inte på den andra.

    `</br>` är inte ett hittepåfall: `_Faltlasare`:s docstring i
    `src/biluppgifter.py` bär ett ensamt `</br>` inuti ett `<template>` som en
    uppmätt sändvägsdefekt sedan skiva 22. *Här stod `docs/sparrar.md`, vilket är
    fel fil; fällt av granskningens tredje varv.*
    """
    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR,
            hamta=biluppgifter_hamtning(oppna=svarar(sida_med(slapvagnsvikt=varde))),
        )

    assert "bär markup" in str(fel.value)


@pytest.mark.parametrize(
    ("beskrivning", "block"),
    [
        (
            "sluttagg för ett element UNDER värdet",
            '<li><b><span class="label">Släpvagnsvikt</span>\n'
            '<span class="value">1500 kg</b> enligt registrering, verklig 750 kg'
            "</span></b></li>\n",
        ),
        (
            "sluttagg för li:t under värdet",
            '<li><span class="label">Släpvagnsvikt</span>\n'
            '<span class="value">1500 kg</li> verklig 750 kg</span>\n',
        ),
    ],
)
def test_varde_som_stangs_av_nagot_annat_an_sin_egen_sluttagg_kastar(beskrivning, block):
    """LUCKA 12, stängd i skiva 25. Uppmätt av granskningens tredje varv i skiva 24.

    En sluttagg som stänger ett element UNDER värdet avslutar fältet där. Värdets
    text KLIPPS vid sluttaggen och resten släpps, utan att någon vet hur mycket
    det var.

    **Utan sluttaggen faller fältet till utkast**, eftersom texten inte är en ren
    vikt. Med den blev svaret `1500 kg`, alltså **en välformad vikt som sidan
    aldrig påstått om släpvagnen**, och den ligger över tröskeln.

    **Det här fallet fångas inte av jämförelsen mellan råtext och textnoder**, och
    det ska sägas rakt ut: fältet stängs vid sluttaggen, så råtexten fram till den
    punkten ÄR lika med textnoderna. Det som saknas är utsträckningen. Villkoret
    är därför att stängningen ska vara värdets EGEN sluttagg, vilket inte är en
    femte händelse utan samma egenskap tillämpad där den inte går att mäta.
    """
    sidan = sida(rader=rad("Tjänstevikt", "1500 kg") + block + rad("Draganordning", "Ja"))

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "bär markup" in str(fel.value)


def test_entitet_i_ett_varde_ar_inte_markup():
    """GRÄNSEN FÖR EGENSKAPEN, och den viktigaste negativkontrollen i skiva 25.

    `convert_charrefs` gör `&nbsp;` till ett hårt blanksteg i textnoden, så
    råtexten och textnoden skiljer sig åt på varje entitet. Jämfördes de utan
    `unescape` hade **källans eget sifferformat kastat**, alltså varje verkligt
    svar som skriver tusenavskiljaren som entitet.

    **Testet är inte ensamt om att binda `unescape`, och det ska stå rätt.** En
    fällning som tar bort `unescape` ur jämförelsen ger `2 failed`: det här testet
    och `test_format_som_sidan_faktiskt_anvander_lases[2&nbsp;400 kg-2400]`, som
    är ÄLDRE än skivan. *Här stod att ingen rad hade blivit röd utan den här, och
    att spärren då blivit ett larm som alltid går. Båda leden var falska: en rad
    hade blivit röd ändå, och utan `unescape` faller bara värden som bär
    entiteter. Fällt av granskningsvarv 2.*

    Raden står kvar därför att den binder ledet i sitt EGET namn: går den röd vet
    nästa läsare vad som gick sönder, medan det äldre testets namn talar om
    sidans format och inte om spärren.
    """
    sidan = sida_med(slapvagnsvikt="2&nbsp;400 kg")

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


def test_rent_varde_ger_fortfarande_uppslag():
    """DEL A:S NEGATIVKONTROLL. En spärr som fäller på allt är inte en spärr.

    Utan den här raden hade kastet i `_las_falt` kunnat skärpas till att fälla
    varje värde utan att någon rad blev röd, och hela uppslaget hade slutat
    fungera på en helt vanlig sida.
    """
    hamta = biluppgifter_hamtning(oppna=svarar(SIDA_AVLAST))
    uppslag = fordonsuppslag.slag_upp(REGNR, hamta=hamta)

    assert uppslag.slapvagnsvikt_kg == 2400
    assert uppslag.tjanstevikt_kg == 2140
    assert uppslag.draganordning is False


def test_element_i_ett_falt_vi_inte_laser_ror_ingenting():
    """GRÄNSEN FÖR DEL A, och den är inte kosmetisk.

    Den skarpa sidan bär värden med nästlad markup i fält vi ALDRIG läser:
    fixturkommentaren vid `SIDA_AVLAST` namnger `Chassinr / VIN`, vars
    value-span öppnar ett `<a hx-get=...>`. Kastade spärren på varje sådant
    värde hade den fällt varje verkligt svar, och ett larm som alltid går blir
    avstängt.

    Spärren sitter därför i `_las_falt` och gäller bara de tre fält
    `EXAKT_ETIKETT` namnger.
    """
    sidan = sida_med(
        extra=(
            '<li>\n  <span class="label">Chassinr / VIN</span>\n'
            '  <span class="value"><a hx-get="/x">visa</a></span>\n</li>\n'
        )
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


def test_lucka_10_formen_finns_bland_de_avlasta_etiketterna():
    """LUCKA 10 ÄR INTE HYPOTETISK, och det här testet mäter det.

    Lucka 10: en SKILD etikett vars särskiljande led saknar bokstäver
    normaliseras in i en annan, eftersom `_behall` inte kan veta om ett
    icke-alfabetiskt led i ett `sup` eller `small` är en fotnotsmarkör eller en
    del av namnet.

    **Formen förekommer bland fixturens åtta avlästa etiketter.**
    `Släp totalvikt (B)` och `Släp totalvikt (B+)` skiljer sig bara på `+`, som
    inte är en bokstav. Skulle källan sätta plustecknet i ett `sup`, vilket är
    typografiskt naturligt, blir de två etiketterna SAMMA sträng.

    **Ingen av de två är ett fält vi läser**, så luckan når inte `EXAKT_ETIKETT`
    på dagens sida. Det är skillnaden mellan att formen finns och att den biter,
    och båda leden ska stå mätta i stället för resonerade.

    Testet blir rött den dag fixturen slutar bära paret, och då ska påståendet i
    `docs/sparrar.md` lucka 10 mätas om i stället för att ärvas.
    """
    etiketter = _lasaren(SIDA_AVLAST).etiketter

    def bara_bokstaver(text):
        return "".join(t for t in text if t.isalpha())

    par = [
        (a, b)
        for i, a in enumerate(etiketter)
        for b in etiketter[i + 1 :]
        if a != b and bara_bokstaver(a) == bara_bokstaver(b)
    ]

    assert par == [("Släp totalvikt (B)", "Släp totalvikt (B+)")]

    med_fotnot = sida(
        rader=(
            rad("Släp totalvikt (B)", "Max 750 kg (Teoretisk)")
            + rad("Släp totalvikt (B<sup>+</sup>)", "Max 1500 kg (Teoretisk)")
        )
    )

    lasta = _lasaren(med_fotnot).etiketter
    assert lasta == ["Släp totalvikt (B)", "Släp totalvikt (B)"]

    assert not set(lasta) & set(EXAKT_ETIKETT.values())


def test_prefixraknare_hade_larmat_pa_den_avlasta_sidan():
    """Belägget för att lucka 7 inte går att stänga med en prefixräknare.

    Testet mäter påståendet i stället för att låta det stå som ett resonemang i
    en docstring. Går det någon gång att stänga luckan ska DEN HÄR raden bli
    röd först, och då är påståendet omprövat i stället för ärvt.
    """
    etiketter = _lasaren(SIDA_AVLAST).etiketter
    inleds_med = [e for e in etiketter if e.startswith("Släpvagnsvikt")]

    assert inleds_med == ["Släpvagnsvikt", "Släpvagnsvikt obromsad"]


# --- de fyra sändvägsdefekter granskningen av skiva 22 hittade ---------------
#
# TRE AV FYRA INFÖRDES AV OMBYGGNADEN SJÄLV, och det ska stå här. Parsern
# stängde de defekter regexen bar, och öppnade tre nya i sin tillståndshantering.
# En omskrivning som byter metod byter också vilka fel som är möjliga, och den
# nya uppsättningen är inte mindre farlig bara för att den är ny.


@pytest.mark.parametrize("skrap", ["</br>", "</li>", "</img>", "</div></div>"])
def test_ensam_sluttagg_avslutar_inte_overhoppningen(skrap):
    """SÄNDVÄGSDEFEKT: `</br>` inuti `<template>` läckte resten av mallen.

    Överhoppningen räknade ett TAL som minskade för varje sluttagg, medan
    starttaggar för tomma element inte ökade det. En ensam sluttagg inuti
    mallen tog talet till noll medan parsern fortfarande stod inne i den, och
    resten lästes som sidans data. Uppmätt: 750 kg ut, alltså den obromsade
    vikten under tröskeln där den bromsade ligger över.

    **Det återöppnade skiva 21:s defekt 2 i ny form**, och det är skälet att
    överhoppningen nu följer TAGGNAMNET i stället för ett tal.

    `</li>` är inget kantfall: en mall som bär ett listobjekt ser ut precis så.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + "<template>\n"
            + skrap
            + rad("Släpvagnsvikt", "750 kg")
            + "</template>\n"
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_faltet_i_noscript_lases_inte():
    """SÄNDVÄGSDEFEKT: `noscript` stod inte i `HOPPAS_OVER`.

    Innehållet visas bara för en läsare utan skript, alltså är det en
    ALTERNATIV rendering och inte sidans data. Uppmätt före rättelsen: 750 kg
    ut. Riktningen efter rättelsen är den säkra: ett fält som BARA står i ett
    `noscript` ger utkast.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + "<noscript>\n"
            + rad("Släpvagnsvikt", "750 kg")
            + "</noscript>\n"
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize("klass", ["Label", "LABEL", "lAbEl"])
def test_dubblett_med_annat_skiftlage_i_klassvardet_kastar(klass):
    """SÄNDVÄGSDEFEKT: klassVÄRDET normaliserades inte, bara attributNAMNET.

    Låg etiketten två gånger och den ena bar `class="Label"` såg räknaren en
    enda förekomst, tvetydigheten tände aldrig, och det andra parets 750 kg gick
    ut där 2400 var rätt. Samma versalfälla som `docs/beslutslogg.md` #28
    beskriver i en annan modul, i en fjärde form av defekt 1.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + f'<span class="{klass}">Släpvagnsvikt</span>\n'
              '<span class="value">2400 kg</span>\n'
            + rad("Släpvagnsvikt", "750 kg")
        )
    )

    with pytest.raises(Hamtningsfel) as fel:
        fordonsuppslag.slag_upp(
            REGNR, hamta=biluppgifter_hamtning(oppna=svarar(sidan))
        )

    assert "förekommer 2 gånger" in str(fel.value)


@pytest.mark.parametrize("ostangd", ["i", "b", "span", "em", "li"])
def test_ostangd_tagg_i_foraldern_paras_inte_med_senare_varde(ostangd):
    """SÄNDVÄGSDEFEKT: föräldern jämfördes på NIVÅTAL och inte på identitet.

    En ostängd inline-tagg inuti etikettens förälder blåste upp nivån, så
    föräldrastängningen slog aldrig till, och etiketten parades med ett värde ur
    ett SENARE block. Uppmätt för fem taggnamn, alla med 750 kg ut.

    **Risken infördes av ombyggnaden**, inte av källan: den gamla regexen krävde
    att värdet följde direkt efter etiketten. Villkoret som ersatte det kravet
    måste därför tåla felformad HTML, och ett nivåtal gör inte det.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + f'<div><span class="label">Släpvagnsvikt</span><{ostangd}></div>\n'
            + '<span class="value">750 kg</span>\n'
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_sluttagg_utan_starttagg_stanger_ingenting():
    """Nollfallet till stackens namnsökning: en vilsen sluttagg får inte fälla.

    Sidan är i övrigt oförändrad. Hittas ingen öppen tagg med samma namn ska
    sluttaggen IGNORERAS, inte stänga det översta elementet på måfå. Utan det
    hade en enda felformad rad kunnat göra hela sidan oläsbar, vilket är samma
    sorts spärr-som-alltid-fäller som Lars förbjöd i briefen.
    """
    sidan = sida_med(extra="</section>\n</article>\n")

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


def test_overhoppningen_talar_nastlade_element_av_samma_namn():
    """Ett `<template>` inuti ett `<template>` får inte avsluta för tidigt.

    Djupräkningen finns kvar men följer namnet. Utan den hade den inre mallens
    sluttagg avslutat överhoppningen och den yttre mallens återstod lästs.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + "<template>\n<template>\n</template>\n"
            + rad("Släpvagnsvikt", "750 kg")
            + "</template>\n"
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


@pytest.mark.parametrize("element", ["template", "noscript", "script", "style"])
def test_overhoppningen_tar_slut_och_falten_efter_lases(element):
    """NOLLFALLET TILL ÖVERHOPPNINGEN, och utan det är den halva otestad.

    Varje test som prövar `HOPPAS_OVER` gömmer ett fält INUTI elementet och
    kräver utkast. Alla sådana förblir gröna även om överhoppningen aldrig tar
    slut och resten av dokumentet tappas, för utfallet är detsamma.

    **§7.1-PRÖVNINGEN FÄLLDE PRECIS DET.** Två villkor i `handle_endtag` och
    `handle_starttag`, de som får djupräkningen att följa taggnamnet, gick att
    fälla utan att en enda rad blev röd. Här ligger fältet EFTER elementet, så
    ett läge som skippar för mycket blir rött.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + f"<{element}>\ntrams</{element}>\n"
            + rad("Släpvagnsvikt", "2400 kg")
        )
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


@pytest.mark.parametrize(
    "innehall",
    [
        "<div>trams</div>",
        "<p>trams",
        '<span class="label">Släpvagnsvikt</span>',
        "<br>trams",
    ],
)
def test_overhoppningen_tar_slut_aven_nar_elementet_bar_markup(innehall):
    """Djupräknaren får bara räkna element med SAMMA namn som det överhoppade.

    Räknar den varje starttagg inuti mallen tar överhoppningen aldrig slut,
    eftersom bara mallens egen sluttagg räknar ned. Resten av dokumentet tappas
    då, och fältet efter blir borta.

    **§7.1-PRÖVNINGEN FÄLLDE DET SEPARAT.** Nollfallet med enbart text förblev
    grönt vid fällningen, eftersom en mall utan markup inuti aldrig får djupet
    att växa. Det är samma sorts hål som §7.1 kallar vakuöst: testet fanns, men
    ingen av dess parametrar kunde bli röd.

    Den tredje parametern är avsiktligt en ETIKETT: hade den räknats hade sidan
    dessutom sett tvetydig ut, alltså fel utfall av ett andra skäl.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + f"<template>\n{innehall}</template>\n"
            + rad("Släpvagnsvikt", "2400 kg")
        )
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400


def test_nastlad_overhoppning_tar_slut_pa_ratt_stalle():
    """Samma nollfall för den nästlade formen.

    Den inre mallens sluttagg får varken avsluta överhoppningen för tidigt,
    vilket `test_overhoppningen_talar_nastlade_element_av_samma_namn` vaktar,
    eller lämna den öppen för alltid, vilket det här testet vaktar.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Draganordning", "Nej")
            + "<template>\n<template>\ntrams</template>\n</template>\n"
            + rad("Släpvagnsvikt", "2400 kg")
        )
    )

    hamta = biluppgifter_hamtning(oppna=svarar(sidan))
    assert fordonsuppslag.slag_upp(REGNR, hamta=hamta).slapvagnsvikt_kg == 2400
