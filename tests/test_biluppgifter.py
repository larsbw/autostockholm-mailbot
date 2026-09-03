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


def test_entitetskodad_etikett_faller():
    """Källan börjar skriva `Sl&auml;pvagnsvikt` i stället för `Släpvagnsvikt`.

    Etiketten avkodas ALDRIG före matchningen, bara värdet. En entitetskodad
    etikett är därför en strukturändring som ger ett saknat fält.
    """
    sidan = sida_med(slapvagnsvikt=None, extra=rad("Sl&auml;pvagnsvikt", "2400 kg"))

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


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

    `1 200 kg` är sidans egen form och måste läsas. Kravet att varje fall ska
    falla kan inte gälla det format källan använder i dag: en modul som föll på
    det hade inte kunnat slå upp något alls. Entiteten är med därför att sidan
    skriver sitt hårda blanksteg så, och `html.unescape` körs före tolkningen.
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

    Värdespannen saknar sin avslutande tagg, så mönstret matchar inte och
    fältet utelämnas. Ett halvt tal får aldrig bli ett helt.
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
            "klassnamnet byter namn",
            '<span class="field-label">Släpvagnsvikt</span>\n'
            '<span class="value">2400 kg</span>\n',
        ),
        (
            "klassen får ett ord till",
            '<span class="label bold">Släpvagnsvikt</span>\n'
            '<span class="value">2400 kg</span>\n',
        ),
        (
            "värdet får nästlad markup",
            '<span class="label">Släpvagnsvikt</span>\n'
            '<span class="value">2400 <abbr>kg</abbr></span>\n',
        ),
        (
            "värdet ligger helt i ett element",
            '<span class="label">Släpvagnsvikt</span>\n'
            '<span class="value"><b>2400 kg</b></span>\n',
        ),
        (
            "något skjuts in mellan etikett och värde",
            '<span class="label">Släpvagnsvikt</span>\n<i class="ikon"></i>\n'
            '<span class="value">2400 kg</span>\n',
        ),
    ],
)
def test_markupandring_faller_till_utkast(beskrivning, block):
    """Sex ändringar källan kan göra utan att röra en enda etikett.

    Ingen av dem finns i skivans lista, och alla sex är rimliga i en
    omdesign. Kravet är detsamma: hellre ett saknat fält än ett gissat värde.
    Beskrivningen bärs som parameter så att ett rött utfall namnger VILKEN
    ändring som slutade falla.
    """
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

    Lager 2 räknade träffar på `MONSTER`, och `MONSTER`:s värdegrupp `([^<]*)`
    matchar inte ett värde med nästlad markup. Låg etiketten två gånger och ETT
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
def test_flera_tal_i_ett_varde_ger_none(varde):
    """SÄNDVÄGSDEFEKT UR GRANSKNINGEN AV SKIVA 21, nu stängd.

    Mönstret var `([\\d\\s\\u00a0]+)kg`, som tillät blanktecken var som helst i
    gruppen medan `re.sub` sedan klistrade ihop allt som blev kvar. Ett värde
    med TVÅ tal blev därför ETT: uppmätt före rättelsen gav `750 2400 kg` talet
    **7502400**, ett välformat heltal långt över tröskeln.

    Fallet är realistiskt: slår källan en dag ihop den bromsade och den
    obromsade vikten i en rad ser värdet ut precis så.
    """
    assert _tal(varde) is None


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

    Lager 1 kräver `</span>` direkt efter etiketten, så träffen uteblir och
    fältet utelämnas. Vore matchningen ett prefix hade 750 kg kommit in här.
    """
    sidan = sida(
        rader=(
            rad("Tjänstevikt", "2140 kg")
            + rad("Släpvagnsvikt obromsad", "750 kg")
            + rad("Draganordning", "Nej")
        )
    )

    assert utfallet_av(sidan) == "svaret saknar slapvagnsvikt_kg"


def test_ankaret_provar_bara_sista_segmentet():
    """KÄND LUCKA 6, prövad och inte hypotetisk.

    `_galler_fordonet` jämför sista segmentet i `canonical` och inte hela
    sökvägen. En sida vars ankare slutar på numret passerar därför lager 3 även
    när sökvägen är en annan. Testet FÄSTER dagens beteende så att en framtida
    skärpning blir ett medvetet val och inte en tyst ändring.

    Ofarligt i dag: källans söksida svarar med `/fordon/` utan nummer, avläst
    2026-09-02. Se luckan i `docs/sparrar.md`.
    """
    assert _galler_fordonet(
        '<link rel="canonical" href="https://biluppgifter.se/sok/abc12x/"/>',
        REGNR,
    ) is True


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

    Första rättelsen lät lager 2 räkna `ETIKETTSPAN`, men den var lika sträng
    som `MONSTER`. Bar den ENA av två etikettspannar ett attribut såg räknaren
    en enda förekomst, `MONSTER` gav en enda träff, och det andra värdet gick ut
    som om det vore entydigt. Samma klass, samma riktning och samma tysthet som
    defekten den skulle stänga.

    **Räknaren är nu lösare än läsaren.** `ETIKETTSPAN` godtar attribut och
    extra blanktecken i taggen; `MONSTER` gör det inte. Båda felar åt samma
    håll: räknaren överskattar och KASTAR, läsaren underskattar och UTELÄMNAR.
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
