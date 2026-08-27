"""Tester för src/fordonsuppslag.py.

Spärren heter `fordonsfakta-ur-uppslag` och står i docs/sparrar.md. Den ligger i
`_kontrollera`, som prövar svarets FORM, och i `Uppslag.__post_init__`, som prövar
VÄRDENA. Varje lager har ett eget test här, eftersom ett fällt lager syns som ett
rött test medan ett SAKNAT lager inte syns alls.

**LAGREN 1, 2 OCH 3 ÄR DELVIS REDUNDANTA, och testerna är skrivna efter det.**
`in` fungerar på varje container, så en lista fälls av alla tre, och en tom `dict`
fälls av både 2 och 3. Ett test som bara asserar `pytest.raises` blir därför grönt
när ett enskilt lager fälls, och en §7.1-prövning pekar då ut ett äkta spärrtest
som vakuöst. **Varje lagertest asserar därför mot `fel.value.skal`**, inte bara
mot att något kastades.

Tröskeln prövas vid EXAKT gränsvärdet, ett kilo under och ett kilo över (§4).

All indata är påhittad. Registreringsnumren är påhittade i den meningen att de
inte är hämtade ur kundmaterialet; om någon av strängarna råkar motsvara ett
verkligt fordon är inte undersökt och saknar betydelse här (§6).
"""

from __future__ import annotations

from types import MappingProxyType

import pytest

from src import fordonsuppslag
from src.fordonsuppslag import Uppslag, UppslagMisslyckades, Utfall

TROSKEL = fordonsuppslag.TROSKEL_SLAPVAGNSVIKT_KG

HELT_SVAR = {"slapvagnsvikt_kg": 1400, "draganordning": True}


def hamtning(svar):
    """Hämtning som alltid ger `svar`, oavsett nummer."""
    def hamta(_regnr):
        return svar
    return hamta


# --- negativkontroll: spärren SLÄPPER IGENOM när den ska ---------------------


def test_fullstandigt_svar_slapps_igenom():
    """Negativkontroll enligt §7.1. En spärr som alltid fäller är ett stopp och
    inte en spärr: utan det här testet vore ett `raise` överst i `_kontrollera`
    lika grönt som den riktiga implementationen."""
    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(HELT_SVAR))

    assert uppslag == Uppslag(slapvagnsvikt_kg=1400, draganordning=True)


def test_svar_med_okanda_nycklar_slapps_ocksa_igenom():
    """Andra halvan av negativkontrollen. Varje verklig datakälla bär fler fält
    än de två som gatar, och en strikthet mot dem hade fällt varje riktig källa
    vid första bytet."""
    svar = dict(HELT_SVAR, fabrikat="okänt", arsmodell=2011)

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.slapvagnsvikt_kg == 1400


def test_draganordning_nej_ar_ett_giltigt_uppslag():
    """`False` är ett SVAR och inte ett saknat värde. Ett lager som prövade
    sanningsvärdet i stället för typen hade fällt det här."""
    svar = {"slapvagnsvikt_kg": 1400, "draganordning": False}

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.draganordning is False


def test_slapvagnsvikt_noll_ar_ett_giltigt_uppslag():
    """Nollfallet. Vikten 0 är ett avläst värde och ska ge RÖTT längre fram,
    inte ett misslyckat uppslag."""
    svar = {"slapvagnsvikt_kg": 0, "draganordning": False}

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.slapvagnsvikt_kg == 0


# --- spärrens lager, ett test per lager --------------------------------------


def test_hamtning_utan_traff_ar_inte_ett_uppslag():
    """Lager 1. Det vanligaste trasiga svaret: numret finns inte i källan."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(None))

    assert "inget svar" in fel.value.skal


def test_tomt_svar_ar_inte_ett_uppslag():
    """Lager 2. En tom dict är inte ett svar, den är ett hål."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning({}))

    assert "slapvagnsvikt_kg" in fel.value.skal


def test_svar_utan_draganordning_ar_inte_ett_uppslag():
    """Lager 3. Halva svaret är inte ett svar."""
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp(
            "ABC123", hamta=hamtning({"slapvagnsvikt_kg": 1400})
        )

    assert "draganordning" in fel.value.skal


@pytest.mark.parametrize("vikt", ["1400", None, 1400.0, [1400]])
def test_vikt_som_inte_ar_heltal_ar_inte_ett_uppslag(vikt):
    """Lager 4. Inget av dessa jämförs med tröskeln utan att kasta.

    `1400.0` är med därför att en JSON-källa kommer att leverera flyttal vid
    första bytet av hämtning. Att det fälls är fail-closed och alltså rätt
    riktning, men det ska vara ett MEDVETET utfall och inte en överraskning.
    """
    svar = {"slapvagnsvikt_kg": vikt, "draganordning": True}

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "heltal" in fel.value.skal


@pytest.mark.parametrize("vikt", [True, False])
def test_vikt_som_bool_ar_inte_ett_uppslag(vikt):
    """Lager 4, det lömska fallet. `bool` ÄR en `int` i Python, så `True` hade
    annars passerat som vikten 1 och gett RÖTT, och `False` som vikten 0."""
    svar = {"slapvagnsvikt_kg": vikt, "draganordning": True}

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "heltal" in fel.value.skal


def test_negativ_vikt_ar_inte_ett_uppslag():
    """Lager 5. Ett negativt tal är inte en vikt, det är ett fel i källan som
    annars hade gett RÖTT och sett rimligt ut."""
    svar = {"slapvagnsvikt_kg": -1, "draganordning": True}

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "negativ" in fel.value.skal


@pytest.mark.parametrize("drag", ["nej", "ja", None, 0, 1])
def test_draganordning_som_inte_ar_bool_ar_inte_ett_uppslag(drag):
    """Lager 6. Strängen `"nej"` är SANN i Python och hade gett GRÖNT, alltså
    motsatsen till vad källan sa. `None` och heltal fälls av samma skäl."""
    svar = {"slapvagnsvikt_kg": 1400, "draganordning": drag}

    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "ja eller nej" in fel.value.skal


@pytest.mark.parametrize(
    "svar",
    [
        '{"slapvagnsvikt_kg": 1400, "draganordning": true}',
        "slapvagnsvikt_kg draganordning",
    ],
)
def test_ra_strang_ar_inte_ett_uppslag(svar):
    """STRÄNGFALLET, och det är inte konstruerat.

    En hämtning som glömt parsa svaret returnerar rå JSON. Strängen bär BÅDA
    nyckelnamnen som delsträngar, så ett naket `nyckel in svar` är sant för
    dem. Innan lagren 2 och 3 prövade mappningsobjekt var det bara lager 1 som
    stoppade det här, och en fällning av lager 1 hade släppt igenom en sträng
    som `Uppslag`-argument.

    Skälet asseras: annars kan testet inte skilja lager 1 från 2 och 3.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert "inget svar" in fel.value.skal


def test_mappningsobjekt_som_inte_ar_dict_slapps_igenom():
    """NEGATIVKONTROLL för mappningskravet. Kravet gäller `Mapping`, inte `dict`.

    En källa som returnerar en `MappingProxyType` eller en egen mappningsklass
    är ett fullgott svar, och ett `isinstance(svar, dict)` hade fällt den. Utan
    det här testet vore skärpningen av lagren 2 och 3 omöjlig att skilja från
    en förträngning till just `dict`.
    """
    svar = MappingProxyType(dict(HELT_SVAR))

    uppslag = fordonsuppslag.slag_upp("ABC123", hamta=hamtning(svar))

    assert uppslag.slapvagnsvikt_kg == 1400


def test_lista_som_svar_ar_inte_ett_uppslag():
    """En källa som returnerar en lista med träffar i stället för en post.

    ASSERTIONEN MOT `skal` ÄR INTE PYNT. En lista fälls av lager 1, 2 OCH 3,
    eftersom `in` fungerar på varje container. Utan den här assertionen förblir
    testet grönt när lager 1 fälls ensamt, och §7.1:s prövning pekar då ut ett
    äkta spärrtest som vakuöst. Uppmätt av granskaren i skiva 12.
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


# --- utvärderingen: fyra utfall ur två fält ----------------------------------


def test_troskeln_vid_exakt_gransvardet_ar_inte_rott():
    """GRÄNSVÄRDET, §4. `minst 1000` betyder att 1000 självt passerar. Ett `<=`
    i stället för `<` hade fällt exakt det här fordonet och bara det."""
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL, draganordning=True)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_ett_kilo_under_troskeln_ar_rott():
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL - 1, draganordning=True)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_ett_kilo_over_troskeln_ar_inte_rott():
    """Andra sidan av gränsvärdet, ett kilo bort och inte hundratals. Ett `>`
    i stället för `<` hade fällt det här och lämnat gränsvärdestestet grönt."""
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL + 1, draganordning=True)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_vikt_noll_ar_rott():
    """Nollfallet för utvärderingen."""
    uppslag = Uppslag(slapvagnsvikt_kg=0, draganordning=True)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_rott_vager_tyngre_an_draganordning():
    """Vikten prövas FÖRST, och det här testet vaktar ordningen mot en bil UTAN
    dragkrok, alltså det fall där ett omkastat villkor hade gett OKLART i
    stället för RÖTT. Fallet med dragkrok täcks av
    `test_ett_kilo_under_troskeln_ar_rott`."""
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL - 1, draganordning=False)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.ROTT


def test_vikt_over_troskeln_med_dragkrok_ar_gront():
    uppslag = Uppslag(slapvagnsvikt_kg=2100, draganordning=True)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.GRONT


def test_utan_dragkrok_och_utan_besked_ar_oklart():
    """FÖRVALET ÄR DET FÖRSIKTIGA. Registret kan inte skilja en omonterad
    dragkrok från en monterad men oregistrerad, så svaret frågar."""
    uppslag = Uppslag(slapvagnsvikt_kg=1400, draganordning=False)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART


def test_utan_dragkrok_med_bekraftat_besked_ar_gult():
    """GULT nås först när kunden bekräftat att dragkrok saknas. Utan den biten
    finns ingen information som skiljer GULT från OKLART."""
    uppslag = Uppslag(slapvagnsvikt_kg=1400, draganordning=False)

    utfall = fordonsuppslag.utvardera(uppslag, dragkrok_bekraftad_saknas=True)

    assert utfall is Utfall.GULT


def test_bekraftelsen_gor_inte_ett_rott_fordon_gult():
    """Bekräftelsen får inte lyfta ett fordon över tröskeln. Vikten prövas
    först, och det här testet vaktar ordningen."""
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL - 1, draganordning=False)

    utfall = fordonsuppslag.utvardera(uppslag, dragkrok_bekraftad_saknas=True)

    assert utfall is Utfall.ROTT


def test_bekraftelsen_paverkar_inte_ett_gront_fordon():
    """Sitter dragkroken registrerad är frågan redan besvarad."""
    uppslag = Uppslag(slapvagnsvikt_kg=1400, draganordning=True)

    utfall = fordonsuppslag.utvardera(uppslag, dragkrok_bekraftad_saknas=True)

    assert utfall is Utfall.GRONT


def test_oklart_och_gult_provas_ocksa_vid_exakta_gransvardet():
    """Gränsvärdet ska gälla i ALLA grenar och inte bara i GRÖNT. Utan det här
    testet var `TROSKEL` bara prövat på vägen mot GRÖNT."""
    uppslag = Uppslag(slapvagnsvikt_kg=TROSKEL, draganordning=False)

    assert fordonsuppslag.utvardera(uppslag) is Utfall.OKLART
    assert fordonsuppslag.utvardera(
        uppslag, dragkrok_bekraftad_saknas=True
    ) is Utfall.GULT


# --- invarianten i typen, där __post_init__ körs -----------------------------


@pytest.mark.parametrize(
    "vikt, drag, skal",
    [
        ("gissning", True, "heltal"),
        (None, True, "heltal"),
        (1400.0, True, "heltal"),
        (True, True, "heltal"),
        (-1, True, "negativ"),
        (1400, "kanske", "ja eller nej"),
        (1400, None, "ja eller nej"),
        (1400, 1, "ja eller nej"),
    ],
)
def test_uppslag_gar_inte_att_skapa_med_ogiltiga_varden(vikt, drag, skal):
    """SPÄRRENS INVARIANT LIGGER I TYPEN och inte hos den som anropar rätt.

    Fyndet ur skiva 12:s granskning: `Uppslag` var en naken dataklass, så
    `Uppslag("gissning", "kanske")` gick att skapa och nådde `utvardera`. Med
    typriktiga men påhittade tal gav den ett fullt trovärdigt GRÖNT.

    `__post_init__` stänger normal konstruktion och `dataclasses.replace`. Den
    stänger INTE `object.__setattr__`, `pickle.loads`, `object.__new__` eller en
    subklass som skuggar den, och två av dem är konstruktion. Det ska inte läsas
    in i det här testet: luckan står utskriven i `docs/sparrar.md`.

    SKÄLET ASSERAS PER PARAMETER, av samma skäl som i lagertesterna: utan det
    kan ett lager fällas utan att någon parameter blir röd, eftersom ett annat
    lager fångar samma värde.
    """
    with pytest.raises(UppslagMisslyckades) as fel:
        Uppslag(slapvagnsvikt_kg=vikt, draganordning=drag)

    assert skal in fel.value.skal


def test_uppslag_med_giltiga_varden_gar_att_skapa_direkt():
    """Negativkontroll för invarianten. En vakt som fäller allt vore ett stopp
    och inte en spärr, och sviten själv bygger `Uppslag` direkt."""
    uppslag = Uppslag(slapvagnsvikt_kg=0, draganordning=False)

    assert uppslag.slapvagnsvikt_kg == 0
    assert uppslag.draganordning is False


def test_typen_hindrar_ogiltiga_varden_men_inte_pahittade():
    """DEN KVARSTÅENDE LUCKAN, utskriven som ett test så att den inte glöms.

    Spärren vaktar hämtningens SVAR, inte anroparens fantasi. Ett `Uppslag` med
    typriktiga men påhittade tal går att skapa och ger ett trovärdigt utfall.
    Det som skyddar mot det är att fas 5 hämtar sina fakta via `slag_upp`, inte
    typen. Registrerat i `docs/sparrar.md`.
    """
    pahittat = Uppslag(slapvagnsvikt_kg=1400, draganordning=True)

    assert fordonsuppslag.utvardera(pahittat) is Utfall.GRONT


# --- tröskelns härkomst ------------------------------------------------------


def test_troskeln_ar_tusen_kilo():
    """Talet är VVFS 2003:19 4 kap 42 § punkt 2, uppslagen i skiva 12. Testet
    finns för att en ändring ska kräva ett medvetet beslut: tröskeln avgör
    vilka kunder som får ett rött svar och är därmed sändväg (§10)."""
    assert fordonsuppslag.TROSKEL_SLAPVAGNSVIKT_KG == 1000
