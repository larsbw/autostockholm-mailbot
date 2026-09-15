"""Tester för src/fordonsuppslag.py.

Spärren `fordonsfakta-ur-uppslag` står i docs/sparrar.md och ligger i FEM
funktioner: `_kontrollera` prövar formen, de tre `_krav_pa_*`-lagren prövar att
ett UTELÄMNAT gatande fält är belagt, `_krav_pa_vikt` prövar de två vikterna,
`Uppslag.__post_init__` prövar draganordningen, och `slag_upp` stoppar ett saknat
registreringsnummer. Varje lager har ett eget test här, eftersom ett fällt lager
syns som ett rött test medan ett SAKNAT lager inte syns alls.

*Raden sade FYRA och räknade inte beläggslagret, som kom med skiva 55.*

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

from src import biluppgifter, fordonsuppslag
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
@pytest.mark.parametrize("vikt", ["1400", 1400.0, [1400]])
def test_vikt_som_inte_ar_heltal_ar_inte_ett_uppslag(falt, vikt):
    """Viktlagret, typkravet, prövat för BÅDA vikterna.

    `1400.0` är med därför att en JSON-källa kommer att leverera flyttal vid
    första bytet av hämtning. Att det fälls är fail-closed och alltså rätt
    riktning, men det ska vara ett MEDVETET utfall och inte en överraskning.

    **`None` STÅR INTE LÄNGRE I LISTAN, och det är en avsiktlig ändring i skiva
    55.** Värdet betyder nu att registret inte bär uppgiften, alltså är det inte
    ett ogiltigt värde utan ett av fältets lägen. De två fälten skiljer sig åt
    där, så de prövas var för sig nedan i stället för i en korsprodukt som hade
    påstått samma sak om båda.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(**{falt: vikt}))
        )

    assert f"{falt} är inte ett heltal" in fel.value.skal


def test_tjanstevikt_None_ar_fortfarande_ett_ogiltigt_varde():
    """TJÄNSTEVIKTEN ÄR OFÖRÄNDRAT OBLIGATORISK I TYPEN. Skiva 55.

    **DE TRE GATANDE FÄLTEN BEHANDLAS OLIKA, och den här raden är hälften av
    beviset.** Fältet står på 10/10 sparade sidor och 6/6 i skiva 40:s
    stickprov, alltså är dess frånvaro nästan säkert vår läsning. Att lämna det
    tomt hade byggt skivans uppmjukning på det fält där den har svagast stöd.

    Fällningen sker i `Uppslag.__post_init__`, alltså i TYPEN, och gäller därmed
    också en direkt konstruktion i ett test eller i fas 5:s kod.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning(svar_med(tjanstevikt_kg=None))
        )

    assert "tjanstevikt_kg är inte ett heltal" in fel.value.skal


@pytest.mark.parametrize(
    ("falt", "varde"),
    [("slapvagnsvikt_kg", None), ("draganordning", None)],
)
def test_de_tva_valfria_falten_godtar_None_i_typen(falt, varde):
    """ANDRA HALVAN: för de två andra fälten ÄR `None` ett giltigt värde.

    **TYPEN SÄGER INGENTING OM VARFÖR FÄLTET ÄR TOMT.** Att ett utelämnat fält
    ur en HÄMTNING bara får bli `None` mot ett belägg vaktas en nivå upp, av
    `_krav_pa_slapvagnsvikt` och `_krav_pa_draganordning`, och de lagren har
    egna test. Delningen är densamma som `_kontrollera` och `__post_init__`
    alltid haft: formen prövas på ett ställe, värdena på ett annat.
    """
    argument = {"tjanstevikt_kg": 1400, "slapvagnsvikt_kg": 1400,
                "draganordning": True}
    argument[falt] = varde

    uppslag = fordonsuppslag.Uppslag(**argument)

    assert getattr(uppslag, falt) is None


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


@pytest.mark.parametrize("drag", ["nej", "ja", 0, 1])
def test_draganordning_som_inte_ar_bool_ar_inte_ett_uppslag(drag):
    """Draganordningslagret. Strängen `"nej"` är SANN i Python och hade gett
    GRÖNT, alltså motsatsen till vad källan sa.

    **`None` ÄR BORTTAGET UR LISTAN i skiva 55**, av samma skäl som i
    viktlagret: värdet betyder nu att registret inte bär uppgiften. Se
    `test_de_tva_valfria_falten_godtar_None_i_typen`.
    """
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
        ("slapvagnsvikt_kg", 1400.0, "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", True, "slapvagnsvikt_kg är inte ett heltal"),
        ("slapvagnsvikt_kg", -1, "slapvagnsvikt_kg är negativ"),
        ("draganordning", "kanske", "draganordning är inte ja eller nej"),
        ("draganordning", 1, "draganordning är inte ja eller nej"),
    ],
)
def test_uppslag_gar_inte_att_skapa_med_ogiltiga_varden(falt, varde, skal):
    """SPÄRRENS INVARIANT LIGGER I TYPEN och inte hos den som anropar rätt.

    **TVÅ RADER ÄR BORTTAGNA I SKIVA 55**, `slapvagnsvikt_kg=None` och
    `draganordning=None`. Invarianten är inte längre *"varje fält bär ett giltigt
    värde"* utan *"varje fält som BÄR ett värde bär ett giltigt"*, och de två
    fälten får sedan skivan vara tomma när registret inte bär dem.
    `tjanstevikt_kg=None` står kvar och fäller som förut.


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


def test_barlastflakets_tak_kommer_ur_forfattningen():
    """§39 FÖRSTA STYCKET, citerat ordagrant i `docs/roadmap.md` fas 4.5.

    **TALET ÄR DETSAMMA SOM §42:s OCH BETYDER MOTSATSEN.** I §42 är 2 000 kg en
    NEDRE gräns som gör fordonet lämpligt som dragfordon; i §39 en ÖVRE gräns som
    drar in det under barlastflakskravet. Konstanterna står därför för sig, och
    raden finns för att en sammanslagning ska kräva ett medvetet beslut.

    `docs/roadmap.md` bär en rättelse av precis den förväxlingen: en tidigare
    lydelse skrev viktledet omvänt.
    """
    assert fordonsuppslag.TAK_BARLASTFLAK_TJANSTEVIKT_KG == 2000


# --- de två strängarna som binder modulerna ihop -----------------------------


def test_franvarobeviset_matchar_biluppgifters_faltstatus():
    """`REGISTRET_SAKNAR_FALTET` MÅSTE VARA SAMMA STRÄNG SOM HÄMTNINGEN SKRIVER.

    **DE TVÅ MODULERNA IMPORTERAR INTE VARANDRA, och det är avsiktligt.**
    `src/fordonsuppslag.py` är nätverksfri och ska gå att pröva utan att en
    socket finns, vilket `src/biluppgifter.py`:s huvud anger som skälet till att
    hämtningen ligger för sig. Priset är att strängen står på två ställen, och
    den här raden är det som gör att de inte kan glida isär.

    **GLIDER DE ISÄR FALLER VARJE UPPSLAG MED ETT SAKNAT FÄLT**, alltså tyst
    tillbaka till beteendet före skiva 55: kunden får veta att vi inte kunnat slå
    upp bilen, fast vi har gjort det. Samma bindningsform som
    `test_kedjans_a_traktorkategorier_matchar_vyns`.
    """
    assert (fordonsuppslag.REGISTRET_SAKNAR_FALTET
            == biluppgifter.Faltstatus.SAKNAS_PA_SIDAN.value)
    assert (fordonsuppslag.REGISTRET_SAKNAR_DRAGVIKT
            == biluppgifter.Dragviktslage.REGISTRET_SAKNAR.value)


def test_metanycklarna_matchar_hamtningens():
    """Samma bindning för de två nycklarna metadatan ligger under.

    En felstavad nyckel här ger ingen `KeyError`: `svar.get` svarar `None`, och
    då fäller `_krav_pa_slapvagnsvikt` varje uppslag med ett saknat fält. Felet
    blir alltså tyst och ser ut som försiktighet.
    """
    assert fordonsuppslag.META_FALTSTATUS == biluppgifter.META_FALTSTATUS
    assert fordonsuppslag.META_DRAGVIKT == biluppgifter.META_DRAGVIKT


# --- skiva 55: de två nya gatingsreglerna ------------------------------------


@pytest.mark.parametrize(
    ("kaross", "vantat"),
    [
        ("Ombyggd Bil", True),
        ("ombyggd bil", True),
        ("OMBYGGD BIL", True),
        ("  Ombyggd Bil  ", True),
        ("Halvkombi", False),
        ("Fordon Fler Ändamål", False),
        ("Stationsvagn Kombivagn", False),
        (None, False),
    ],
)
def test_ar_redan_ombyggd_prover_karossens_HELA_varde(kaross, vantat):
    """GATINGSREGEL 1. Jämförelsen är skiftlägesokänslig och annars EXAKT.

    **DELSTRÄNGSRADERNA ÄR INTE MED AV SYMMETRI.** Sidan skriver `Ombyggd Bil` i
    `Kaross` och `Ombyggd BIL` inuti `Modell` och `Originalnamn TS`, avläst över
    tio sparade sidor. En jämförelse mot hela sidan hade alltså träffat fält vi
    inte läser, och en delsträngsjämförelse mot karossvärdet hade träffat varje
    framtida värde som råkar bära orden.

    **`None` GER `False`, inte ett larm.** Att vi inte vet om bilen är ombyggd är
    inget skäl att säga nej till kunden.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=1400, slapvagnsvikt_kg=1400, draganordning=True,
        kaross=kaross,
    )

    assert fordonsuppslag.ar_redan_ombyggd(uppslag) is vantat


def test_redan_ombyggd_ger_ROTT_aven_nar_fordonet_ar_LAMPLIGT():
    """ORDNINGEN I `utvardera` ÄR LASTBÄRANDE, och raden binder den.

    **det ombyggda fordonet med tjänstevikt 2 005 kg ÄR FALLET.** Avläst tjänstevikt 2 005 kg, alltså över §42:s tröskel,
    och `Kaross: Ombyggd Bil`. Prövades lämpligheten först hade fordonet blivit
    LÄMPLIGT och därmed fått ett svar om dragkrok på en bil som redan är en
    a-traktor.

    Raden blir röd om regel 1 flyttas nedanför lämplighetsprövningen.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=2005, slapvagnsvikt_kg=None, draganordning=None,
        kaross="Ombyggd Bil",
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is True
    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


@pytest.mark.parametrize(
    ("tjanstevikt", "fyrhjulsdrift", "vantat"),
    [
        # §39 FÖRSTA LEDET FALLER: vikten är över taket.
        (2001, False, False),
        # GRÄNSVÄRDET. Paragrafen säger HÖGST 2 000 kg, alltså gäller den vid
        # jämnt 2 000. Raden blir röd om `>` blir `>=`.
        (2000, False, True),
        # §39 ANDRA LEDET FALLER: varje hjul är ett drivhjul.
        (1720, True, False),
        # BÅDA LEDEN KAN VARA UPPFYLLDA.
        (1310, False, True),
        # VI VET INTE OM DRIVNINGEN, och då säger vi ingenting.
        (1310, None, None),
        # VIKTEN ENSAM RÄCKER FÖR ETT BESKED, också utan drivningsuppgift.
        (2001, None, False),
    ],
)
def test_kraver_barlastflak(tjanstevikt, fyrhjulsdrift, vantat):
    """GATINGSREGEL 2, §39 första stycket som boolesk logik.

    **`False` ÄR ETT BESKED, `True` ÄR DET INTE.** Funktionen säger aldrig att
    ett flak KRÄVS: sextioprocentsregeln går inte att avgöra ur registret i
    allmänhet, och `True` betyder därför bara att vi inte kan utesluta kravet.
    `src/generera.py` läser bara `False`, se `_barlastrad`.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=tjanstevikt, slapvagnsvikt_kg=1400, draganordning=True,
        fyrhjulsdrift=fyrhjulsdrift,
    )

    assert fordonsuppslag.kraver_barlastflak(uppslag) is vantat


def test_okand_slapvagnsvikt_ger_OKLART_och_aldrig_ROTT():
    """SKIVA 55 DEL B PUNKT 3. **RÖTT KRÄVER ATT BÅDA TALEN ÄR AVLÄSTA.**

    **fordonet utan dragviktsuppgift ÄR FALLET.** Tjänstevikt 960 kg, ingen släpvagnsvikt i registret.
    Ett `not lamplig` hade läst okunskapen som ett NEJ och gett kunden ett avslag
    på en uppgift registret aldrig lämnat. Det är skiva 12:s defekt i ny form.

    Raden blir röd om `lamplig is False` blir `not lamplig`.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=960, slapvagnsvikt_kg=None, draganordning=False,
        kaross="Halvkombi",
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is None
    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART


def test_okand_draganordning_ger_OKLART_och_aldrig_GRONT():
    """Samma krav för det tredje fältet.

    Ett `if uppslag.draganordning:` utan `is True` hade fallit vidare till
    beskedsgrenen, och där kan ett `DragkrokBesked` ge GULT, alltså ett svar som
    namnger ett prispåslag, på ett fordon vi inte läst något om.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=1400, slapvagnsvikt_kg=1400, draganordning=None,
    )

    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART
    assert fordonsuppslag.utvardera(
        uppslag, besked=KUNDBESKED) is Utfall.OKLART


def test_okand_lamplighet_ger_OKLART_AVEN_MED_registrerad_dragkrok():
    """§7.1-FYND: raden `if lamplig is None` var OBUNDEN utan den här.

    **FÄLLNINGEN VAR GRÖN, och skälet är lömskt.** Raderas raden blir
    `return Utfall.OKLART` en oåtkomlig andra rad i föregående block, alltså
    syntaktiskt giltig, och ett fordon med okänd lämplighet faller vidare till
    draganordningsgrenen. För ett fordon UTAN dragkrok blir svaret OKLART ändå,
    och varje befintligt test förblev grönt.

    **SKILLNADEN SYNS BARA NÄR DRAGKROKEN ÄR REGISTRERAD.** Då ger fallthrough
    GRÖNT, alltså beskedet att bilen går att bygga om, utan att §42 andra stycket
    någonsin prövats mot ett avläst tal. Det är ett ja byggt på en uppgift
    registret inte lämnat.

    Raden blir röd om `if lamplig is None` tas bort eller flyttas nedanför
    draganordningsgrenen.
    """
    uppslag = Uppslag(
        tjanstevikt_kg=960, slapvagnsvikt_kg=None, draganordning=True,
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is None
    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART


def test_dragviktslaget_ensamt_ar_inget_belagg_for_ett_saknat_falt():
    """§7.1: BINDER LAGRET SOM PRÖVAR FÄLTSTATUSEN I `_krav_pa_slapvagnsvikt`.

    **DE TVÅ LAGREN ÄR REDUNDANTA FÖR `biluppgifter_hamtning`**, och det är
    ingen slump: `dragviktslage` svarar `registret saknar uppgiften` bara när
    den bromsade vikten har status `saknas på sidan`, alltså är de kopplade vid
    källan. En fällning av statuslagret ensamt ger därför GRÖN svit, vilket är
    INKONKLUSIVT och inte vakuöst.

    **DEN HÄR RADEN GÖR LAGRET FÄLLBART.** Hämtningen nedan är en ANNAN källa,
    alltså precis det sömmen finns för: den lämnar ett dragviktsläge men ingen
    statuskarta. Utan statuslagret hade dess svar blivit ett lyckat uppslag med
    släpvagnsvikten tom, på ett belägg ingen hämtare kontrollerat.
    """
    svar = {k: v for k, v in HELT_SVAR.items() if k != "slapvagnsvikt_kg"}
    svar[fordonsuppslag.META_DRAGVIKT] = (
        fordonsuppslag.REGISTRET_SAKNAR_DRAGVIKT
    )

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "saknar slapvagnsvikt_kg" in fel.value.skal
