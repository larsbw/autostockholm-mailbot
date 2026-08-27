"""Slår upp de fordonsfakta som gatar en a-traktorombyggnad, och utvärderar dem.

TVÅ FÄLT GATAR OMBYGGNADEN: **släpvagnsvikt** och **draganordning**. Beslut av
Lars i skiva 12, se `docs/beslutslogg.md` #24. Tjänstevikt, drivning,
karosserikod och barlastflak ingår INTE i bedömningen. Allt annat uppslaget
skulle kunna visa är merförsäljning, inte gating.

TRÖSKELN 1000 KG ÄR ETT FÖRFATTNINGSKRAV. VVFS 2003:19 4 kap 42 § punkt 2:
"ursprungsfordonet är konstruerat för en släpvagnsvikt av minst 1 000 kg".
Föreskriften är uppslagen i skiva 12 och citeras i `docs/roadmap.md` fas 4.5.
Modulen kallade talet för verkstadens praxis fram till dess, vilket var falskt.

**ÖPPEN PUNKT, BLOCKERANDE: §42 HAR TVÅ KRITERIER OCH DEN HÄR KODEN PRÖVAR ETT.**
Villkoren är förenade med *eller*: ett fordon är lämpligt som dragfordon om
tjänstevikten är minst 2 000 kg ELLER om släpvagnsvikten är minst 1 000 kg.
`utvardera` prövar bara det senare, så **ett fordon med tjänstevikt 2 100 kg och
släpvagnsvikt 800 kg får RÖTT trots att föreskriften säger att det duger.**

Att rätta det kräver tjänstevikt som ett tredje fält, alltså just det fält som
ströks ur bedömningen på premissen att §42 var tyst. Vilka fält som gatar är Lars
beslut, se `docs/beslutslogg.md` #24, och ingen mall får skrivas innan punkten är
avgjord.

REGELUTVÄRDERINGEN ÄR DETERMINISTISK KOD, INTE EN MODELL. `utvardera` är boolesk
logik på två fält. Ingen modell avgör om ett fordon kan byggas om; modellen får
formulera svaret, aldrig fatta beslutet.

HÄMTNINGEN LIGGER BAKOM GRÄNSSNITTET som en utbytbar implementation. `slag_upp`
tar en `hamta`-funktion, och `manuell_hamtning` är den som finns nu. Datakällan
är inte avgjord (beslutslogg #23), så ett byte ska vara ett byte av EN funktion
och inte en omskrivning av modulen.

Spärren `fordonsfakta-ur-uppslag` ligger i TVÅ funktioner: `_kontrollera` prövar
svarets FORM, `Uppslag.__post_init__` prövar VÄRDENA. Den som ska fälla den
enligt §7.1 måste fälla i båda; en prövning som bara rör `_kontrollera` når tre
av sex lager och ger ett inkonklusivt verdikt som ser konklusivt ut. Registrerad
i `docs/sparrar.md`.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Callable

# VVFS 2003:19 4 kap 42 § punkt 2, uppslagen i skiva 12. Se modulens huvud.
# Ändras det här talet ändras vilka kunder som får ett rött svar, så det är
# sändväg och inte en konstant bland andra.
TROSKEL_SLAPVAGNSVIKT_KG = 1000


class UppslagMisslyckades(Exception):
    """Uppslaget gav inget som får användas i ett svar.

    Bärs som undantag och inte som ett returvärde, därför att ett misslyckat
    uppslag ALDRIG får förväxlas med ett lyckat. Ett returnerat `None` som
    någon glömmer pröva blir tyst; det här blir högljutt.
    """

    def __init__(self, skal: str) -> None:
        super().__init__(skal)
        self.skal = skal


@dataclass(frozen=True)
class Uppslag:
    """Ett LYCKAT uppslag, och därmed den enda källan till fordonsfakta i ett svar.

    INVARIANTEN LIGGER I TYPEN, inte hos den som råkar anropa rätt.
    `__post_init__` kastar, så **normal konstruktion och `dataclasses.replace`**
    kan inte ge en instans med en vikt som inte är ett icke-negativt heltal eller
    en draganordning som inte är `True`/`False`. Det gäller också en direkt
    konstruktion i ett test eller i fas 5:s kod.

    **VAD TYPEN INTE SKYDDAR MOT, och det ska stå här. Två saker.**

    För det första hindrar den ogiltiga VÄRDEN, inte påhittade. `Uppslag(1400,
    True)` går att skriva utan att någon källa har svarat, och blir då ett fullt
    trovärdigt GRÖNT.

    För det andra gäller invarianten bara där `__post_init__` faktiskt körs.
    `object.__setattr__` går förbi `frozen` på en färdig instans, och
    `pickle.loads`, `object.__new__` och en subklass som skuggar `__post_init__`
    kommer förbi på var sitt sätt. **Två av dem är konstruktion**, subklassen och
    `pickle`, så ordet "konstruktionsvägarna är stängda" vore fel och används
    inte. Uppmätt i skiva 12: `object.__setattr__(u, "slapvagnsvikt_kg", -5)` ger
    ett tyst RÖTT.

    Det hårdnas medvetet INTE mot, på beslut av Lars: boten möter ingen fientlig
    indata och skyddet är inte tänkt att vara det. Men påståendet får inte
    formuleras som om varje väg vore stängd.

    Spärren `fordonsfakta-ur-uppslag` vaktar hämtningens svar, inte anroparens
    fantasi. Luckorna är registrerade i `docs/sparrar.md` under samma namn.
    """

    slapvagnsvikt_kg: int
    draganordning: bool

    def __post_init__(self) -> None:
        # Lokala namn, så att varje villkor ryms på EN rad. Ett villkor som
        # bryts över flera rader går inte att neutralisera enligt §7.1 utan att
        # filen blir syntaktiskt trasig, och då ger prövningen FEL i stället för
        # RÖD.
        vikt = self.slapvagnsvikt_kg
        drag = self.draganordning

        # `bool` är en subklass till `int` i Python, så True hade annars passerat
        # som vikten 1 och gett RÖTT på ett fordon vi inte vet något om.
        if isinstance(vikt, bool) or not isinstance(vikt, int):
            raise UppslagMisslyckades("slapvagnsvikt_kg är inte ett heltal")

        if vikt < 0:
            raise UppslagMisslyckades("slapvagnsvikt_kg är negativ")

        if not isinstance(drag, bool):
            raise UppslagMisslyckades("draganordning är inte ja eller nej")


class Utfall(str, Enum):
    """De fyra utfallen ur `docs/roadmap.md` fas 4.5.

    `SAKNAR_REGNR` och `UPPSLAG_MISSLYCKADES` står inte här: de är TILLSTÅND och
    inte utfall, de bärs av `UppslagMisslyckades`, och båda leder till utkast.
    """

    GRONT = "gront"
    GULT = "gult"
    OKLART = "oklart"
    ROTT = "rott"


def normalisera_regnr(regnr: str | None) -> str:
    """Versaler utan blanksteg eller bindestreck. Tom sträng om inget finns."""
    if not regnr:
        return ""
    return "".join(regnr.split()).replace("-", "").upper()


def manuell_hamtning(
    tabell: dict[str, dict],
) -> Callable[[str], dict | None]:
    """Hämtningen som finns NU: värdena matas in för hand.

    Finns för att datakällan inte är vald (beslutslogg #23) och fasen ändå ska
    gå att bygga och pröva. Nycklarna normaliseras, så att uppslaget inte beror
    på hur numret råkade skrivas.
    """
    normaliserad = {normalisera_regnr(k): v for k, v in tabell.items()}

    def hamta(regnr: str) -> dict | None:
        return normaliserad.get(regnr)

    return hamta


def _bar_nyckel(svar: object, nyckel: str) -> bool:
    """Sant bara för ett MAPPNINGSOBJEKT som bär nyckeln.

    Finns för att `nyckel in svar` ensamt är sant för varje container som råkar
    innehålla strängen. En rå JSON-sträng bär båda nyckelnamnen som delsträngar
    och hade passerat lagren 2 och 3 utan den här kontrollen.
    """
    return isinstance(svar, Mapping) and nyckel in svar


def _kontrollera(svar: object) -> Uppslag:
    """SPÄRREN `fordonsfakta-ur-uppslag`. Släpper bara igenom ett fullständigt svar.

    Varje villkor nedan är ett eget lager och fäller för sig. Ett tomt eller
    oväntat svar från hämtningen är INTE ett giltigt uppslag: det kastar, och
    anropet faller till utkast.

    OKÄNDA NYCKLAR TOLERERAS med avsikt. Varje verklig datakälla levererar fler
    fält än de två som gatar, och en strikthet mot dem hade fällt varje riktig
    källa vid första bytet. Det spärren vaktar är att de två fält som ANVÄNDS
    finns och är rimliga, inte att svaret är precis så stort som vi väntade oss.

    ARBETSDELNINGEN MOT `Uppslag.__post_init__`: här prövas svarets FORM, alltså
    att det är ett mappningsobjekt och att båda nycklarna finns. VÄRDENA prövas
    av typen själv. Delningen finns för att invarianten ska gälla också en direkt
    konstruktion som aldrig passerar den här funktionen.

    **LAGREN 2 OCH 3 PRÖVAR MAPPNINGSOBJEKT, INTE `in`.** Ett naket `in` fungerar
    på varje container, och en RÅ JSON-STRÄNG bär båda nyckelnamnen som
    delsträngar. Med `in` ensamt hade lagren 2 och 3 alltså släppt igenom
    `'{"slapvagnsvikt_kg": 1400, ...}'`, vilket är precis vad en hämtning som
    glömt parsa svaret returnerar. Det är inte ett hypotetiskt fall: det är
    normalfelet vid det första bytet av `hamta`.

    Följden är att lagren 1, 2 och 3 nu fäller SAMMA sak, alltså är helt
    redundanta. Det gör dem inte överflödiga, men det gör att ett lagertest
    måste assera SKÄLET för att gå att fälla för sig. Registrerat i
    `docs/sparrar.md`.
    """
    if not isinstance(svar, Mapping):
        raise UppslagMisslyckades("hämtningen gav inget svar")

    if not _bar_nyckel(svar, "slapvagnsvikt_kg"):
        raise UppslagMisslyckades("svaret saknar slapvagnsvikt_kg")

    if not _bar_nyckel(svar, "draganordning"):
        raise UppslagMisslyckades("svaret saknar draganordning")

    return Uppslag(
        slapvagnsvikt_kg=svar["slapvagnsvikt_kg"],
        draganordning=svar["draganordning"],
    )


def slag_upp(
    regnr: str | None,
    *,
    hamta: Callable[[str], dict | None],
) -> Uppslag:
    """Slår upp ett registreringsnummer. Kastar `UppslagMisslyckades` annars.

    `hamta` är hämtningen, alltså den utbytbara delen. Den har inget förval:
    den som anropar ska välja källa medvetet, och en tyst standardkälla i en
    sändvägsmodul är precis det §10 finns för att hindra.

    KONTRAKTET FÖR `hamta`, utskrivet därför att sömmen ska bytas:

    - Den får returnera källans svar som en `dict`, eller `None` när fordonet
      inte finns. Båda hanteras här.
    - **Den får kasta, och ett sådant undantag fångas INTE utan når anroparen.**
      Det är avsiktligt. En källa som är nere är inte samma sak som ett fordon
      utan uppgifter, och att översätta det ena till det andra hade gjort ett
      driftavbrott osynligt. Ett obehandlat undantag stoppar dessutom mailet,
      vilket är rätt riktning: inget skickas på fakta vi inte har.
    - **Anroparen i fas 5 måste därför hantera BÅDE `UppslagMisslyckades` och
      källans egna undantag.** Spärren täcker svaret, inte tystnaden.
    """
    normalt = normalisera_regnr(regnr)
    if not normalt:
        raise UppslagMisslyckades("registreringsnummer saknas")

    return _kontrollera(hamta(normalt))


def utvardera(
    uppslag: Uppslag,
    *,
    dragkrok_bekraftad_saknas: bool = False,
) -> Utfall:
    """Fyra utfall ur två fält. Boolesk logik, ingen modell.

    `dragkrok_bekraftad_saknas` bär det enda som registret inte kan veta: om
    kunden bekräftat att det inte sitter någon dragkrok på bilen. Utan den
    bekräftelsen är fallet OKLART och svaret frågar, eftersom en omonterad
    dragkrok och en monterad men oregistrerad ser likadana ut i registret.

    FÖRVALET ÄR DET FÖRSIKTIGA. Utan besked blir utfallet OKLART, alltså en
    fråga till kunden, aldrig ett påstående om att dragkrok saknas.

    **BESLUT AV LARS i skiva 12.** Briefen listade GULT och OKLART med identiska
    registervillkor, vilket en deterministisk funktion inte kan honorera. Att
    skillnaden är ett besked från kunden föreslogs av agenten och antogs som
    beslut. Se `docs/beslutslogg.md` #24. Förvalet OKLART står fast.

    **BITEN BÄR INGEN HÄRKOMST, till skillnad från fordonsfakta.** Vikten och
    draganordningen måste passera spärren `fordonsfakta-ur-uppslag`; det här är
    en naken `bool` som vilken anropare som helst kan sätta, inklusive en modell.
    En felaktigt satt `True` flyttar kunden från "vi frågar" till "vi offererar".
    Luckan är registrerad i `docs/sparrar.md`.
    """
    if uppslag.slapvagnsvikt_kg < TROSKEL_SLAPVAGNSVIKT_KG:
        return Utfall.ROTT

    if uppslag.draganordning:
        return Utfall.GRONT

    if dragkrok_bekraftad_saknas:
        return Utfall.GULT

    return Utfall.OKLART
