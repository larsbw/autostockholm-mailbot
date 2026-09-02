"""Tester för src/biluppgifter.py.

Spärren `fordonsfakta-ur-sida` ligger i FYRA lager, och varje lager har egna
test här:

1. **Exakt etikettmatchning** i `MONSTER` och `_las_falt`. `Släpvagnsvikt` är ett
   prefix till `Släpvagnsvikt obromsad`, och de två raderna ligger intill
   varandra på sidan. Lagret vaktar att rätt rad läses.
2. **Tvetydighetskontrollen** i `_las_falt`. En etikett som förekommer flera
   gånger kastar i stället för att den första träffen tas.
3. **Canonical-ankaret** i `_galler_fordonet`. Sidan svarar 200 med SÖKSIDAN på
   ett okänt nummer, så statuskoden kan inte avgöra om fordonet finns.
4. **De strikta värdeparsningarna** i `_tal` och `_ja_nej`. Ett värde som inte är
   en ren vikt eller ett rent ja/nej utelämnas i stället för att tolkas.

**LAGER 1 OCH 2 BÄR VARANDRAS FÖRSVAR, och det ändrar hur lager 1 ska prövas.**
Görs etikettmatchningen till ett prefix får `re.findall` TVÅ träffar på
`Släpvagnsvikt`, och då kastar lager 2. En §7.1-prövning som bara fäller lager 1
ser alltså rött ut av fel skäl: undantaget kommer från det andra lagret.

**ATT ASSERA PÅ VÄRDET RÄCKTE INTE, och det är prövat och inte antaget.**
`test_slapvagnsvikt_ar_den_bromsade` asserar på 2 400 och inte på att något
kastades. Det gjorde det ändå inte fällbart för sig: fälls BÅDA lagren samtidigt
tas första träffen, och den råkar vara den bromsade vikten eftersom den raden
står först på sidan i dag. Testet förblev alltså GRÖNT vid dubbelfällningen.

Det som löste det är `test_slapvagnsvikt_ar_den_bromsade_aven_i_omvand_radordning`
nedan, vars fixtur lägger den obromsade raden först. Redundansen och prövningens
tal står i `docs/sparrar.md`.

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

import urllib.error

import pytest

from src import fordonsuppslag
from src.biluppgifter import (
    Hamtningsfel,
    _galler_fordonet,
    _hamta_sidan,
    _ja_nej,
    _las_falt,
    _tal,
    biluppgifter_hamtning,
)
from src.fordonsuppslag import UppslagMisslyckades, Utfall

REGNR = "ABC12X"


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
    r"""LAGER 4. `.strip()` FÖRE MATCHNINGEN ÄR ETT VILLKOR, INTE STÄDNING.

    Testet finns därför att `_tal` INTE bär någon tomkontroll efter `re.sub`.
    Den grenen togs bort som bevisat onåbar, och beviset vilar på TVÅ ting:
    kvantifikatorn `+` i mönstret, OCH att `.strip()` körs på argumentet före
    matchningen. `+` stod utskrivet i modulens docstring. `.strip()` gjorde det
    inte, och det är det här testet som spikar den.

    Tas `.strip()` bort matchar `([\d\s\u00a0]+)kg` mot ` kg` med grupp 1 lika
    med ett blanksteg, `re.sub` tömmer gruppen, och `int("")` kastar
    `ValueError` i stället för att ge `None`. Uppmätt på alla fyra värdena: MED
    `.strip()` blir utfallet `None`, UTAN blir det
    `ValueError: invalid literal for int() with base 10: ''`.

    ASSERAR PÅ `None` OCH INTE PÅ ETT UNDANTAG, därför att ett värde som bara
    bär blanktecken är ett SAKNAT fält och inte en strukturändring. Ett kastat
    undantag hade tagit hela uppslaget med sig.
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
