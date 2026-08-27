"""Tester för src/fordonsuppslag.py.

Spärren `fordonsfakta-ur-uppslag` står i docs/sparrar.md och ligger i FYRA
funktioner: `_kontrollera` prövar formen, `_krav_pa_vikt` prövar de två vikterna,
`Uppslag.__post_init__` prövar draganordningen, och `slag_upp` stoppar ett saknat
registreringsnummer. Varje lager har ett eget test här, eftersom ett fällt lager
syns som ett rött test medan ett SAKNAT lager inte syns alls.

Spärren `dragkrokbesked-har-harkomst` ligger i `utvardera`, `DragkrokBesked` och
`BeskedKalla` och har sina egna test längst ned. Typkontrollen i `utvardera` är
dess viktigaste lager.

**FORMLAGREN ÄR HELT REDUNDANTA MED VARANDRA, och testerna är skrivna efter det.**
En rå JSON-sträng, en lista och `None` fälls av alla tre. **Varje lagertest
asserar därför mot `fel.value.skal`**, inte bara mot att något kastades: utan det
blir testet grönt när ett enskilt lager fälls, och §7.1:s prövning pekar då ut
ett äkta spärrtest som vakuöst.

**VIKTLAGREN DELAS av `tjanstevikt_kg` och `slapvagnsvikt_kg` genom
`_krav_pa_vikt`.** En fällning där fäller båda fälten samtidigt. Skälet bär
fältnamnet, så testerna kan ändå skilja dem åt.

Tröskeln prövas vid EXAKT gränsvärdet, ett kilo under och ett kilo över (§4).

**FIXTURERNAS TJÄNSTEVIKT LIGGER MEDVETET UNDER `TROSKEL_TJANSTEVIKT_KG`**, så
att släpvagnsvikten är det som avgör i de test som prövar den. §42:s två villkor
är förenade med ELLER, och en tung fixtur hade gjort varje sådant test grönt av
fel skäl.

All indata är påhittad. Registreringsnumren är påhittade i den meningen att de
inte är hämtade ur kundmaterialet; om någon av strängarna råkar motsvara ett
verkligt fordon är inte undersökt och saknar betydelse här (§6).
"""

from __future__ import annotations

from types import MappingProxyType, SimpleNamespace

import pytest

from src import fordonsuppslag
from src.fordonsuppslag import (
    BeskedKalla,
    DragkrokBesked,
    Uppslag,
    UppslagMisslyckades,
    Utfall,
)

TROSKEL = fordonsuppslag.TROSKEL_SLAPVAGNSVIKT_KG
TROSKEL_TJANST = fordonsuppslag.TROSKEL_TJANSTEVIKT_KG

# Under tjänstevikttröskeln, så att släpvagnsvikten avgör. Se filhuvudet.
LATT = 1500

HELT_SVAR = {
    "tjanstevikt_kg": LATT,
    "slapvagnsvikt_kg": 1400,
    "draganordning": True,
}

KUNDBESKED = DragkrokBesked(saknas=True, kalla=BeskedKalla.KUNDSVAR)


def hamtning(svar):
    """Hämtning som alltid ger `svar`, oavsett nummer."""
    def hamta(_regnr):
        return svar
    return hamta


def svar_med(**andringar):
    """`HELT_SVAR` med enskilda fält utbytta."""
    return dict(HELT_SVAR, **andringar)


# --- negativkontroll: spärren SLÄPPER IGENOM när den ska ---------------------


def test_fullstandigt_svar_slapps_igenom():
    """Negativkontroll enligt §7.1. En spärr som alltid fäller är ett stopp och
    inte en spärr: utan det här testet vore ett `raise` överst i `_kontrollera`
    lika grönt som den riktiga implementationen."""
    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(HELT_SVAR))

    assert uppslag == Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=True
    )


def test_svar_med_okanda_nycklar_slapps_ocksa_igenom():
    """Andra halvan av negativkontrollen. Varje verklig datakälla bär fler fält
    än de tre som gatar, och en strikthet mot dem hade fällt varje riktig källa
    vid första bytet."""
    svar = svar_med(fabrikat="okänt", arsmodell=2011)

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.slapvagnsvikt_kg == 1400


def test_draganordning_nej_ar_ett_giltigt_uppslag():
    """`False` är ett SVAR och inte ett saknat värde. Ett lager som prövade
    sanningsvärdet i stället för typen hade fällt det här."""
    uppslag = fordonsuppslag.slag_upp(
        "ABC123", hamta=hamtning(svar_med(draganordning=False))
    )

    assert uppslag.draganordning is False


@pytest.mark.parametrize("falt", ["tjanstevikt_kg", "slapvagnsvikt_kg"])
def test_vikt_noll_ar_ett_giltigt_uppslag(falt):
    """Nollfallet, för BÅDA vikterna. 0 är ett avläst värde och ska påverka
    utfallet längre fram, inte ge ett misslyckat uppslag."""
    uppslag = fordonsuppslag.slag_upp(
        "ABC123", hamta=hamtning(svar_med(**{falt: 0}))
    )

    assert getattr(uppslag, falt) == 0


# --- spärrens formlager, ett test per lager ----------------------------------


def test_hamtning_utan_traff_ar_inte_ett_uppslag():
    """Lager 1. Det vanligaste trasiga svaret: numret finns inte i källan."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(None))

    assert "inget svar" in fel.value.skal


def test_tomt_svar_ar_inte_ett_uppslag():
    """Lager 2. En tom dict är inte ett svar, den är ett hål."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning({}))

    assert "tjanstevikt_kg" in fel.value.skal


@pytest.mark.parametrize(
    "saknat, skal",
    [
        ("tjanstevikt_kg", "saknar tjanstevikt_kg"),
        ("slapvagnsvikt_kg", "saknar slapvagnsvikt_kg"),
        ("draganordning", "saknar draganordning"),
    ],
)
def test_svar_som_saknar_ett_falt_ar_inte_ett_uppslag(saknat, skal):
    """Lagren 2, 3 och 4. Ett svar med två av tre fält är inte ett svar.

    Skälet asseras per fält, så att en fällning av ETT nyckellager blir röd i
    just sin parameter och inte döljs av grannlagret.
    """
    svar = {k: v for k, v in HELT_SVAR.items() if k != saknat}

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert skal in fel.value.skal


@pytest.mark.parametrize("falt", ["tjanstevikt_kg", "slapvagnsvikt_kg"])
@pytest.mark.parametrize("vikt", ["1400", None, 1400.0, [1400]])
def test_vikt_som_inte_ar_heltal_ar_inte_ett_uppslag(falt, vikt):
    """Viktlagret, typkravet, prövat för BÅDA vikterna.

    `1400.0` är med därför att en JSON-källa kommer att leverera flyttal vid
    första bytet av hämtning. Att det fälls är fail-closed och alltså rätt
    riktning, men det ska vara ett MEDVETET utfall och inte en överraskning.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(**{falt: vikt}))
        )

    assert f"{falt} är inte ett heltal" in fel.value.skal


@pytest.mark.parametrize("falt", ["tjanstevikt_kg", "slapvagnsvikt_kg"])
@pytest.mark.parametrize("vikt", [True, False])
def test_vikt_som_bool_ar_inte_ett_uppslag(falt, vikt):
    """Viktlagret, det lömska fallet. `bool` ÄR en `int` i Python, så `True`
    hade annars passerat som vikten 1 och `False` som vikten 0."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(**{falt: vikt}))
        )

    assert f"{falt} är inte ett heltal" in fel.value.skal


@pytest.mark.parametrize("falt", ["tjanstevikt_kg", "slapvagnsvikt_kg"])
def test_negativ_vikt_ar_inte_ett_uppslag(falt):
    """Viktlagret, teckenkravet. Ett negativt tal är inte en vikt, det är ett
    fel i källan som annars hade gett ett utfall och sett rimligt ut."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(**{falt: -1}))
        )

    assert f"{falt} är negativ" in fel.value.skal


@pytest.mark.parametrize("drag", ["nej", "ja", None, 0, 1])
def test_draganordning_som_inte_ar_bool_ar_inte_ett_uppslag(drag):
    """Draganordningslagret. Strängen `"nej"` är SANN i Python och hade gett
    GRÖNT, alltså motsatsen till vad källan sa."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(draganordning=drag))
        )

    assert "ja eller nej" in fel.value.skal


@pytest.mark.parametrize(
    "svar",
    [
        '{"tjanstevikt_kg": 1500, "slapvagnsvikt_kg": 1400,'
        ' "draganordning": true}',
        "tjanstevikt_kg slapvagnsvikt_kg draganordning",
    ],
)
def test_ra_strang_ar_inte_ett_uppslag(svar):
    """STRÄNGFALLET, och det är inte konstruerat.

    En hämtning som glömt parsa svaret returnerar rå JSON. Strängen bär ALLA
    nyckelnamnen som delsträngar, så ett naket `nyckel in svar` är sant för dem.
    Innan nyckellagren prövade mappningsobjekt var det bara lager 1 som stoppade
    det här.

    Skälet asseras: annars kan testet inte skilja lager 1 från nyckellagren.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "inget svar" in fel.value.skal


def test_mappningsobjekt_som_inte_ar_dict_slapps_igenom():
    """NEGATIVKONTROLL för mappningskravet. Kravet gäller `Mapping`, inte `dict`.

    En källa som returnerar en `MappingProxyType` eller en egen mappningsklass
    är ett fullgott svar, och ett `isinstance(svar, dict)` hade fällt den. Utan
    det här testet vore skärpningen av nyckellagren omöjlig att skilja från en
    förträngning till just `dict`.
    """
    svar = MappingProxyType(dict(HELT_SVAR))

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.slapvagnsvikt_kg == 1400


def test_lista_som_svar_ar_inte_ett_uppslag():
    """En källa som returnerar en lista med träffar i stället för en post.

    ASSERTIONEN MOT `skal` ÄR INTE PYNT. En lista fälls av samtliga formlager.
    Utan den här assertionen förblir testet grönt när lager 1 fälls ensamt, och
    §7.1:s prövning pekar då ut ett äkta spärrtest som vakuöst. Uppmätt av
    granskaren i skiva 12.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning([HELT_SVAR]))

    assert "inget svar" in fel.value.skal


# --- registreringsnumret -----------------------------------------------------


@pytest.mark.parametrize("regnr", [None, "", "   ", "-"])
def test_saknat_regnr_ger_misslyckande(regnr):
    """Nollfallet för indata. Alla fyra normaliserar till tom sträng, och inget
    av dem får nå hämtningen."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(regnr, hamta=hamtning(HELT_SVAR))

    assert "saknas" in fel.value.skal


def test_hamtningen_anropas_inte_utan_regnr():
    """Ett saknat nummer ska stoppas FÖRE källan. Annars kostar varje tomt
    ärende ett uppslag, och mot en betald källa är det pengar."""
    anrop = []

    def hamta(regnr):
        anrop.append(regnr)
        return HELT_SVAR

    with pytest.raises(UppslagMisslyckades):
        fordonsuppslag.slag_upp("", hamta=hamta)

    assert anrop == []


@pytest.mark.parametrize("skrivet", ["abc123", "ABC 123", "abc-123", " ABC123 "])
def test_numret_normaliseras_innan_uppslag(skrivet):
    """Uppslaget får inte bero på hur kunden råkade skriva numret."""
    hamta = fordonsuppslag.manuell_hamtning({"ABC123": HELT_SVAR})

    assert fordonsuppslag.slag_upp(skrivet, hamta=hamta).draganordning is True


def test_manuell_hamtning_utan_traff_ger_misslyckande():
    hamta = fordonsuppslag.manuell_hamtning({"ABC123": HELT_SVAR})

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("XYZ789", hamta=hamta)

    assert "inget svar" in fel.value.skal


def test_manuell_hamtning_normaliserar_sina_egna_nycklar():
    """Tabellen skrivs för hand, så nyckeln kan bära blanksteg eller gemener."""
    hamta = fordonsuppslag.manuell_hamtning({"abc 123": HELT_SVAR})

    assert fordonsuppslag.slag_upp("ABC123", hamta=hamta).slapvagnsvikt_kg == 1400


# --- §42 andra stycket: två ALTERNATIVA lämplighetsvillkor -------------------


def test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott():
    """DEFEKTEN SOM SKEPPADES I SKIVA 12, och som inte får återkomma tyst.

    §42 andra stycket är ett ELLER: tjänstevikt minst 2 000 kg ELLER
    släpvagnsvikt minst 1 000 kg. Skiva 12 prövade bara släpvagnsvikten, så ett
    fordon med tjänstevikt 2 100 kg och släpvagnsvikt 800 kg fick RÖTT trots att
    föreskriften säger att det ÄR lämpligt som dragfordon.

    Med dragkrok är det GRÖNT, utan är det OKLART. Aldrig RÖTT.
    """
    tung = Uppslag(tjanstevikt_kg=2100, slapvagnsvikt_kg=800, draganordning=True)

    assert fordonsuppslag.utvardera(tung) is Utfall.GRONT

    utan_krok = Uppslag(
        tjanstevikt_kg=2100, slapvagnsvikt_kg=800, draganordning=False
    )

    assert fordonsuppslag.utvardera(utan_krok) is Utfall.OKLART


def test_rott_kraver_att_bada_lamplighetsvillkoren_faller():
    """RÖTT är konjunktionen av två NEGATIONER. Faller bara det ena villkoret
    är fordonet fortfarande lämpligt."""
    bada_faller = Uppslag(
        tjanstevikt_kg=TROSKEL_TJANST - 1,
        slapvagnsvikt_kg=TROSKEL - 1,
        draganordning=True,
    )

    assert fordonsuppslag.utvardera(bada_faller) is Utfall.ROTT


@pytest.mark.parametrize(
    "tjanstevikt, slapvagnsvikt",
    [
        (TROSKEL_TJANST, 0),
        (TROSKEL_TJANST + 1, 0),
        (0, TROSKEL),
        (0, TROSKEL + 1),
        (TROSKEL_TJANST, TROSKEL),
    ],
)
def test_ett_uppfyllt_villkor_racker_for_lamplighet(tjanstevikt, slapvagnsvikt):
    """Gränsvärdet i BÅDA villkoren, var för sig och tillsammans."""
    uppslag = Uppslag(
        tjanstevikt_kg=tjanstevikt,
        slapvagnsvikt_kg=slapvagnsvikt,
        draganordning=True,
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is True


@pytest.mark.parametrize(
    "tjanstevikt, slapvagnsvikt",
    [
        (TROSKEL_TJANST - 1, TROSKEL - 1),
        (0, 0),
    ],
)
def test_bada_villkoren_under_gransen_ar_inte_lampligt(
    tjanstevikt, slapvagnsvikt
):
    """Nollfallet och gränsvärdet, ett kilo under i båda."""
    uppslag = Uppslag(
        tjanstevikt_kg=tjanstevikt,
        slapvagnsvikt_kg=slapvagnsvikt,
        draganordning=True,
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is False


# --- utvärderingen: fyra utfall ur tre fält ----------------------------------


def test_slapvagnsvikt_vid_exakt_gransvardet_ar_inte_rott():
    """GRÄNSVÄRDET, §4. `minst 1000` betyder att 1000 självt passerar. Ett `<`
    i stället för `>=` hade fällt exakt det här fordonet och bara det."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=TROSKEL, draganordning=True
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_tjanstevikt_vid_exakt_gransvardet_ar_inte_rott():
    """GRÄNSVÄRDET för det ANDRA kriteriet, prövat genom `utvardera` och inte
    bara genom hjälpfunktionen. Släpvagnsvikten ligger under sin tröskel, så
    tjänstevikten är ensam avgörande."""
    uppslag = Uppslag(
        tjanstevikt_kg=TROSKEL_TJANST,
        slapvagnsvikt_kg=TROSKEL - 1,
        draganordning=True,
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_ett_kilo_under_bada_troskarna_ar_rott():
    """Nedre sidan av BÅDA gränsvärdena. Det finns inget sätt att pröva
    tjänsteviktströskeln nedåt utan att släpvagnsvillkoret också faller: så
    länge ETT villkor håller är fordonet lämpligt. Därför är det här ENA testet
    nedre gränsvärdet för båda, och `test_tjanstevikt_vid_exakt_gransvardet_ar_inte_rott`
    är det som isolerar tjänstevikten uppåt."""
    uppslag = Uppslag(
        tjanstevikt_kg=TROSKEL_TJANST - 1,
        slapvagnsvikt_kg=TROSKEL - 1,
        draganordning=True,
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_ett_kilo_over_slapvagnstroskeln_ar_inte_rott():
    """Andra sidan av gränsvärdet, ett kilo bort och inte hundratals."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=TROSKEL + 1, draganordning=True
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_bada_vikterna_noll_ar_rott():
    """Nollfallet för utvärderingen."""
    uppslag = Uppslag(
        tjanstevikt_kg=0, slapvagnsvikt_kg=0, draganordning=True
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_rott_vager_tyngre_an_draganordning():
    """Lämpligheten prövas FÖRST, och det här testet vaktar ordningen mot en bil
    UTAN dragkrok, alltså det fall där ett omkastat villkor hade gett OKLART i
    stället för RÖTT."""
    uppslag = Uppslag(
        tjanstevikt_kg=TROSKEL_TJANST - 1,
        slapvagnsvikt_kg=TROSKEL - 1,
        draganordning=False,
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_utan_dragkrok_och_utan_besked_ar_oklart():
    """FÖRVALET ÄR DET FÖRSIKTIGA. Registret kan inte skilja en omonterad
    dragkrok från en monterad men oregistrerad, så svaret frågar."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=False
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART


def test_utan_dragkrok_med_bekraftat_besked_ar_gult():
    """GULT nås först när kunden bekräftat att dragkrok saknas. Utan den biten
    finns ingen information som skiljer GULT från OKLART."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=False
    )

    assert fordonsuppslag.utvardera(uppslag, besked=KUNDBESKED) is Utfall.GULT


def test_besked_om_att_dragkrok_FINNS_lamnar_fallet_oklart():
    """`saknas=False` betyder att kunden säger att det SITTER en dragkrok som
    registret inte känner till. Det är varken GULT, för inget ska monteras, eller
    GRÖNT, för den är inte registrerad. Fallet är inte definierat av Lars, och
    utfallet stannar därför på det försiktiga OKLART."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=False
    )
    finns = DragkrokBesked(saknas=False, kalla=BeskedKalla.KUNDSVAR)

    assert fordonsuppslag.utvardera(uppslag, besked=finns) is Utfall.OKLART


def test_beskedet_gor_inte_ett_rott_fordon_gult():
    """Beskedet får inte lyfta ett fordon över lämplighetströskeln."""
    uppslag = Uppslag(
        tjanstevikt_kg=TROSKEL_TJANST - 1,
        slapvagnsvikt_kg=TROSKEL - 1,
        draganordning=False,
    )

    assert fordonsuppslag.utvardera(uppslag, besked=KUNDBESKED) is Utfall.ROTT


def test_beskedet_paverkar_inte_ett_gront_fordon():
    """Sitter dragkroken registrerad är frågan redan besvarad."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=True
    )

    assert fordonsuppslag.utvardera(uppslag, besked=KUNDBESKED) is Utfall.GRONT


def test_oklart_och_gult_provas_ocksa_vid_exakta_gransvardet():
    """Gränsvärdet ska gälla i ALLA grenar och inte bara i GRÖNT."""
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=TROSKEL, draganordning=False
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART
    assert fordonsuppslag.utvardera(uppslag, besked=KUNDBESKED) is Utfall.GULT


# --- invarianten i typen, där __post_init__ körs -----------------------------


@pytest.mark.parametrize(
    "falt, varde, skal",
    [
        ("tjanstevikt_kg", "gissning", "tjanstevikt_kg är inte ett heltal"),
        ("tjanstevikt_kg", None, "tjanstevikt_kg är inte ett heltal"),
        ("tjanstevikt_kg", 1500.0, "tjanstevikt_kg är inte ett heltal"),
        ("tjanstevikt_kg", True, "tjanstevikt_kg är inte ett heltal"),
        ("tjanstevikt_kg", -1, "tjanstevikt_kg är negativ"),
        ("slapvagnsvikt_kg", "gissning", "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", None, "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", 1400.0, "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", True, "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", -1, "slapvagnsvikt_kg är negativ"),
        ("draganordning", "kanske", "draganordning är inte ja eller nej"),
        ("draganordning", None, "draganordning är inte ja eller nej"),
        ("draganordning", 1, "draganordning är inte ja eller nej"),
    ],
)
def test_uppslag_gar_inte_att_skapa_med_ogiltiga_varden(falt, varde, skal):
    """SPÄRRENS INVARIANT LIGGER I TYPEN och inte hos den som anropar rätt.

    Fyndet ur skiva 12:s granskning: `Uppslag` var en naken dataklass, så
    `Uppslag("gissning", "kanske")` gick att skapa och nådde `utvardera`. Med
    typriktiga men påhittade tal gav den ett fullt trovärdigt GRÖNT.

    `__post_init__` stänger normal konstruktion och `dataclasses.replace`. Den
    stänger INTE `object.__setattr__`, `pickle.loads`, `object.__new__` eller en
    subklass som skuggar den, och två av dem är konstruktion. Det ska inte läsas
    in i det här testet: luckan står utskriven i `docs/sparrar.md`.

    SKÄLET ASSERAS PER PARAMETER, av samma skäl som i lagertesterna.
    """
    argument = dict(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=True
    )
    argument[falt] = varde

    with pytest.raises(UppslagMisslyckades) as fel:
        Uppslag(**argument)

    # HELA skälet asseras, fältnamnet inkluderat. `_krav_pa_vikt` delas av de
    # två vikterna, så utan fältnamnet kunde en parameter bli grön av att
    # GRANNENS värde fällde först.
    assert skal in fel.value.skal


def test_uppslag_med_giltiga_varden_gar_att_skapa_direkt():
    """Negativkontroll för invarianten. En vakt som fäller allt vore ett stopp
    och inte en spärr, och sviten själv bygger `Uppslag` direkt."""
    uppslag = Uppslag(
        tjanstevikt_kg=0, slapvagnsvikt_kg=0, draganordning=False
    )

    assert uppslag.tjanstevikt_kg == 0
    assert uppslag.slapvagnsvikt_kg == 0
    assert uppslag.draganordning is False


def test_typen_hindrar_ogiltiga_varden_men_inte_pahittade():
    """DEN KVARSTÅENDE LUCKAN, utskriven som ett test så att den inte glöms.

    Spärren vaktar hämtningens SVAR, inte anroparens fantasi. Ett `Uppslag` med
    typriktiga men påhittade tal går att skapa och ger ett trovärdigt utfall.
    Det som skyddar mot det är att fas 5 hämtar sina fakta via `slag_upp`, inte
    typen. Registrerat i `docs/sparrar.md`.
    """
    pahittat = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=True
    )

    assert fordonsuppslag.utvardera(pahittat) is Utfall.GRONT


# --- spärren `dragkrokbesked-har-harkomst` -----------------------------------


def test_besked_kraver_en_kalla():
    """Spärrens kärna: beskedet går inte att sätta utan att namnge sin källa.

    Före skiva 13 var det en naken `bool`, och en modell kunde sätta den utan
    att någon kunde se varifrån den kom. Nu är argumentet obligatoriskt.
    """
    with pytest.raises(TypeError):
        DragkrokBesked(saknas=True)


@pytest.mark.parametrize("kalla", ["kundsvar", "modell", None, 1, True])
def test_kallan_maste_vara_en_medlem_i_beskedkalla(kalla):
    """En sträng som RÅKAR heta rätt duger inte, och `"modell"` finns inte alls
    i uppräkningen. Det är det som gör källan granskningsbar i efterhand."""
    with pytest.raises(UppslagMisslyckades) as fel:
        DragkrokBesked(saknas=True, kalla=kalla)

    assert "giltig källa" in fel.value.skal


def test_beskedet_maste_vara_ja_eller_nej():
    with pytest.raises(UppslagMisslyckades) as fel:
        DragkrokBesked(saknas="kanske", kalla=BeskedKalla.KUNDSVAR)

    assert "ja eller nej" in fel.value.skal


@pytest.mark.parametrize("kalla", list(BeskedKalla))
def test_bada_tillatna_kallorna_gar_igenom(kalla):
    """NEGATIVKONTROLL för härkomstspärren. Båda de tillåtna källorna ska
    fungera, annars är spärren ett stopp och inte en spärr."""
    besked = DragkrokBesked(saknas=True, kalla=kalla)

    assert besked.saknas is True
    assert besked.kalla is kalla


@pytest.mark.parametrize(
    "falskt",
    [
        SimpleNamespace(saknas=True),
        SimpleNamespace(saknas=True, kalla="modell"),
        True,
        {"saknas": True},
    ],
)
def test_besked_av_fel_typ_avvisas(falskt):
    """SPÄRREN MÅSTE BINDA VID ANROPSSTÄLLET, inte bara vid konstruktionen.

    Fyndet ur skiva 13:s granskning: `utvardera` prövade bara `besked.saknas`,
    alltså en ankuppslagning. Vilket objekt som helst med det attributet gav
    GULT, alltså ett svar som namnger ett prispåslag, förbi hela härkomstkravet.
    Att `DragkrokBesked` var svår att konstruera fel spelade ingen roll när
    ingen krävde ett `DragkrokBesked`.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=LATT, slapvagnsvikt_kg=1400, draganordning=False
    )

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.utvardera(uppslag, besked=falskt)

    assert "DragkrokBesked" in fel.value.skal


def test_uppraekningen_bar_ingen_modellkalla():
    """DEN AVGÖRANDE EGENSKAPEN, som ett test så att den inte tas bort tyst.

    Spärren fungerar genom att uppräkningen är UTTÖMMANDE och saknar en medlem
    för en modell eller en klassificerare. Läggs en sådan till upphör spärren att
    betyda något, och det ska då kräva ett medvetet beslut (§10).
    """
    assert {k.value for k in BeskedKalla} == {"kundsvar", "utkastvy"}


# --- tröskarnas härkomst -----------------------------------------------------


def test_trosklarna_kommer_ur_forfattningen():
    """Talen är VVFS 2003:19 4 kap 42 § andra stycket, uppslagen i skiva 12 och
    citerad ordagrant i `docs/roadmap.md`. Testet finns för att en ändring ska
    kräva ett medvetet beslut: trösklarna avgör vilka kunder som får ett rött
    svar och är därmed sändväg (§10)."""
    assert fordonsuppslag.TROSKEL_TJANSTEVIKT_KG == 2000
    assert fordonsuppslag.TROSKEL_SLAPVAGNSVIKT_KG == 1000
