"""Slår upp de fordonsfakta som gatar en a-traktorombyggnad, och utvärderar dem.

TRE FÄLT GATAR OMBYGGNADEN: **tjänstevikt**, **släpvagnsvikt** och
**draganordning**. Beslut av Lars i skiva 13, se `docs/beslutslogg.md` #25.
Drivning, karosserikod och barlastflak ingår INTE i bedömningen. Allt annat
uppslaget skulle kunna visa är merförsäljning, inte gating.

GATINGEN FÖLJER VVFS 2003:19 4 kap 42 §, som citeras ORDAGRANT i
`docs/roadmap.md` fas 4.5. Andra stycket ger två ALTERNATIVA kriterier för
lämplighet som dragfordon, förenade med **eller**: tjänstevikt minst 2 000 kg
eller släpvagnsvikt minst 1 000 kg. Ovanpå det kräver första stycket
kopplingsanordning.

**RÖTT KRÄVER ATT BÅDA LÄMPLIGHETSVILLKOREN FALLER.** Ett fordon med tjänstevikt
2 100 kg och släpvagnsvikt 800 kg är GRÖNT eller GULT beroende på draganordning,
aldrig RÖTT. Skiva 12 prövade bara släpvagnsvikten och skeppade den defekten;
`test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott` finns för att den inte ska
kunna återkomma tyst.

Tjänstevikt ströks ur bedömningen i skiva 12 på premissen att §42 saknar tal.
Premissen kom ur briefen och motbevisades av föreskriftens text.

REGELUTVÄRDERINGEN ÄR DETERMINISTISK KOD, INTE EN MODELL. `utvardera` är boolesk
logik på tre fält. Ingen modell avgör om ett fordon kan byggas om; modellen får
formulera svaret, aldrig fatta beslutet.

HÄMTNINGEN LIGGER BAKOM GRÄNSSNITTET som en utbytbar implementation. `slag_upp`
tar en `hamta`-funktion, och `manuell_hamtning` är den som finns nu. Datakällan
är inte avgjord (beslutslogg #23), så ett byte ska vara ett byte av EN funktion
och inte en omskrivning av modulen.

Spärren `fordonsfakta-ur-uppslag` är utspridd över FYRA funktioner: `_kontrollera`
prövar svarets form, `_krav_pa_vikt` prövar de två vikterna,
`Uppslag.__post_init__` prövar draganordningen och anropar viktkravet, och
`slag_upp` stoppar ett saknat registreringsnummer. Den som ska fälla den enligt
§7.1 måste fälla i alla fyra; en prövning som bara rör `_kontrollera` når inte
värdelagren och ger ett inkonklusivt verdikt som ser konklusivt ut.

Spärren `dragkrokbesked-har-harkomst` ligger i `DragkrokBesked`, i `BeskedKalla`
och i `utvardera`. **Typkontrollen i `utvardera` är dess viktigaste lager**: utan
den räcker vilket objekt som helst med ett `.saknas`-attribut.

Båda är registrerade i `docs/sparrar.md`, med villkoren som text.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Callable

# VVFS 2003:19 4 kap 42 § andra stycket, uppslagen i skiva 12 och citerad
# ordagrant i `docs/roadmap.md` fas 4.5. De två talen är ALTERNATIVA kriterier,
# förenade med ELLER. Ändras något av dem ändras vilka kunder som får ett rött
# svar, så de är sändväg och inte konstanter bland andra.
TROSKEL_TJANSTEVIKT_KG = 2000
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


def _krav_pa_vikt(varde: object, falt: str) -> None:
    """Kastar om `varde` inte är en avläsbar vikt i hela kilo.

    Delas av `tjanstevikt_kg` och `slapvagnsvikt_kg`. **En fällning av en rad
    här fäller alltså BÅDA fälten samtidigt**, och det är avsiktligt: kravet är
    identiskt och två kopior hade drivit isär. Skälet bär fältnamnet, så ett
    test kan skilja fälten åt trots delad implementation.
    """
    # `bool` är en subklass till `int` i Python, så True hade annars passerat
    # som vikten 1 och gett ett utfall på ett fordon vi inte vet något om.
    if isinstance(varde, bool) or not isinstance(varde, int):
        raise UppslagMisslyckades(f"{falt} är inte ett heltal")

    if varde < 0:
        raise UppslagMisslyckades(f"{falt} är negativ")


@dataclass(frozen=True)
class Uppslag:
    """Ett LYCKAT uppslag, och därmed den enda källan till fordonsfakta i ett svar.

    INVARIANTEN LIGGER I TYPEN, inte hos den som råkar anropa rätt.
    `__post_init__` kastar, så **normal konstruktion och `dataclasses.replace`**
    kan inte ge en instans med en vikt som inte är ett icke-negativt heltal eller
    en draganordning som inte är `True`/`False`. Det gäller också en direkt
    konstruktion i ett test eller i fas 5:s kod.

    **VAD TYPEN INTE SKYDDAR MOT, och det ska stå här. Två saker.**

    För det första hindrar den ogiltiga VÄRDEN, inte påhittade.
    `Uppslag(1500, 1400, True)` går att skriva utan att någon källa har svarat,
    och blir då ett fullt trovärdigt GRÖNT.

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

    tjanstevikt_kg: int
    slapvagnsvikt_kg: int
    draganordning: bool

    def __post_init__(self) -> None:
        # Lokala namn, så att varje villkor ryms på EN rad. Ett villkor som
        # bryts över flera rader går inte att neutralisera enligt §7.1 utan att
        # filen blir syntaktiskt trasig, och då ger prövningen FEL i stället för
        # RÖD.
        drag = self.draganordning

        _krav_pa_vikt(self.tjanstevikt_kg, "tjanstevikt_kg")
        _krav_pa_vikt(self.slapvagnsvikt_kg, "slapvagnsvikt_kg")

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


class BeskedKalla(str, Enum):
    """De ENDA tillåtna källorna till ett dragkroksbesked. Beslut av Lars, skiva 13.

    Uppräkningen är uttömmande, och det är hela poängen: **det finns ingen medlem
    för en modell eller för klassificeraren.** Den som vill sätta beskedet måste
    välja en av de två nedan, och båda förutsätter att en människa har sagt eller
    skrivit något.
    """

    #: Kunden har uttryckligen svarat på frågan i sitt mail.
    KUNDSVAR = "kundsvar"
    #: Lars eller Matte har matat in det för hand i utkastvyn, fas 5.5.
    UTKASTVY = "utkastvy"


@dataclass(frozen=True)
class DragkrokBesked:
    """Ett besked om dragkrok, MED sin härkomst.

    Finns därför att `utvardera` tidigare tog en naken `bool`. En sådan flyttar
    kunden från OKLART, alltså en fråga, till GULT, alltså ett svar som namnger
    ett prispåslag, och den kunde sättas av vem som helst utan att någon kunde se
    varifrån den kom.

    **VAD TYPEN GÖR:** en NORMAL konstruktion kan inte sätta beskedet utan att
    samtidigt namnge en källa ur `BeskedKalla`, och den källan går att logga och
    granska i efterhand.

    **VAD DEN INTE GÖR.** Ordet "omöjligt" står medvetet inte här. Flera vägar
    kommer förbi `__post_init__` och ger ett objekt som `utvardera` accepterar,
    bland dem en subklass som skuggar vakten, `object.__setattr__` på en färdig
    instans, `copy.deepcopy` och en `Mock` med `spec`. Den kan inte heller hindra
    en anropare som medvetet anger en tillåten men osann källa. **Listan är inte
    uttömmande**, och den står i `docs/sparrar.md` med en rad per väg.

    Skillnaden mot den nakna `bool` som fanns förut är att felet kräver avsikt i
    stället för slarv. Varje väg är namngiven i `docs/sparrar.md` under
    `dragkrokbesked-har-harkomst`, och de hårdnas inte mot: boten möter ingen
    fientlig indata.
    """

    saknas: bool
    kalla: BeskedKalla

    def __post_init__(self) -> None:
        if not isinstance(self.saknas, bool):
            raise UppslagMisslyckades("beskedet är inte ja eller nej")

        if not isinstance(self.kalla, BeskedKalla):
            raise UppslagMisslyckades("beskedet saknar en giltig källa")


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
    innehålla strängen. En rå JSON-sträng bär alla nyckelnamnen som delsträngar
    och hade passerat nyckellagren utan den här kontrollen.
    """
    return isinstance(svar, Mapping) and nyckel in svar


def _kontrollera(svar: object) -> Uppslag:
    """SPÄRREN `fordonsfakta-ur-uppslag`. Släpper bara igenom ett fullständigt svar.

    Varje villkor nedan är ett eget lager och fäller för sig. Ett tomt eller
    oväntat svar från hämtningen är INTE ett giltigt uppslag: det kastar, och
    anropet faller till utkast.

    OKÄNDA NYCKLAR TOLERERAS med avsikt. Varje verklig datakälla levererar fler
    fält än de TRE som gatar, och en strikthet mot dem hade fällt varje riktig
    källa vid första bytet. Det spärren vaktar är att de tre fält som ANVÄNDS
    finns och är rimliga, inte att svaret är precis så stort som vi väntade oss.

    ARBETSDELNINGEN MOT `Uppslag.__post_init__`: här prövas svarets FORM, alltså
    att det är ett mappningsobjekt och att alla tre nycklarna finns. VÄRDENA
    prövas av typen själv. Delningen finns för att invarianten ska gälla också en
    direkt konstruktion som aldrig passerar den här funktionen.

    **NYCKELLAGREN PRÖVAR MAPPNINGSOBJEKT, INTE `in`.** Ett naket `in` fungerar
    på varje container, och en RÅ JSON-STRÄNG bär alla nyckelnamnen som
    delsträngar. Med `in` ensamt hade nyckellagren alltså släppt igenom
    `'{"tjanstevikt_kg": 1500, ...}'`, vilket är precis vad en hämtning som
    glömt parsa svaret returnerar. Det är inte ett hypotetiskt fall: det är
    normalfelet vid det första bytet av `hamta`.

    Följden är att Mapping-lagret och nyckellagren fäller SAMMA sak, alltså är
    helt redundanta. Det gör dem inte överflödiga, men det gör att ett lagertest
    måste assera SKÄLET för att gå att fälla för sig. Registrerat i
    `docs/sparrar.md`.
    """
    if not isinstance(svar, Mapping):
        raise UppslagMisslyckades("hämtningen gav inget svar")

    if not _bar_nyckel(svar, "tjanstevikt_kg"):
        raise UppslagMisslyckades("svaret saknar tjanstevikt_kg")

    if not _bar_nyckel(svar, "slapvagnsvikt_kg"):
        raise UppslagMisslyckades("svaret saknar slapvagnsvikt_kg")

    if not _bar_nyckel(svar, "draganordning"):
        raise UppslagMisslyckades("svaret saknar draganordning")

    return Uppslag(
        tjanstevikt_kg=svar["tjanstevikt_kg"],
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


def ar_lamplig_som_dragfordon(uppslag: Uppslag) -> bool:
    """VVFS 2003:19 4 kap 42 § andra stycket, som boolesk logik.

    Paragrafen citeras ordagrant i `docs/roadmap.md` fas 4.5. Villkoren är
    **ALTERNATIVA och förenade med ELLER**: tjänstevikt minst 2 000 kg ELLER
    släpvagnsvikt minst 1 000 kg.

    **DET RÄCKER ATT ETT AV DEM UPPFYLLS.** Ett fordon med tjänstevikt 2 100 kg
    och släpvagnsvikt 800 kg ÄR lämpligt som dragfordon. Skiva 12 prövade bara
    släpvagnsvikten och gav ett sådant fordon RÖTT, vilket är den defekt som
    skeppades och som `test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott` finns
    för att hindra från att återkomma tyst.

    Villkoren står på var sin rad så att vart och ett går att fälla för sig
    enligt §7.1. Ett `or` på en rad hade gjort dem oskiljbara.

    **PARAGRAFEN BYTER SUBJEKT MELLAN PUNKTERNA, och koden gör det inte.** Punkt 1
    säger "tjänstevikten" efter inledningen "A-traktor är lämplig som dragfordon
    om", alltså rimligen A-traktorns vikt EFTER ombyggnaden. Punkt 2 byter
    uttryckligen till "ursprungsfordonet". Här prövas båda mot
    `uppslag.tjanstevikt_kg`, som kommer ur registret på kundens nuvarande bil.

    **DET SPELAR INGEN ROLL, och det är Lars besked: tjänstevikten är densamma
    före och efter ombyggnaden.** Se `docs/beslutslogg.md` #26. Är talet detsamma
    saknar frågan praktisk betydelse, och den här funktionen prövar rätt storhet.
    Punkten var blockerande för fas 4.5 fram till beskedet.

    §39:s barlastflak är den ombyggnad som skulle kunna flytta vikten, eftersom
    den tillför massa. Beskedet omfattar det. Skulle någon hitta ett fordon där
    vikterna skiljer sig är det beslutet i #26 som ska omprövas, inte den här
    funktionen.
    """
    if uppslag.tjanstevikt_kg >= TROSKEL_TJANSTEVIKT_KG:
        return True

    if uppslag.slapvagnsvikt_kg >= TROSKEL_SLAPVAGNSVIKT_KG:
        return True

    return False


def utvardera(
    uppslag: Uppslag,
    *,
    besked: DragkrokBesked | None = None,
) -> Utfall:
    """Fyra utfall ur tre fält. Boolesk logik, ingen modell.

    GATINGEN ÄR TVÅ SAKER: lämplighet som dragfordon enligt §42 andra stycket,
    och draganordning. **RÖTT kräver att BÅDA lämplighetsvillkoren faller**, inte
    bara släpvagnsvikten.

    `besked` bär det enda som registret inte kan veta: om kunden bekräftat att
    det inte sitter någon dragkrok på bilen. En omonterad dragkrok och en
    monterad men oregistrerad ser likadana ut i registret.

    FÖRVALET ÄR DET FÖRSIKTIGA. Utan besked blir utfallet OKLART, alltså en
    fråga till kunden, aldrig ett påstående om att dragkrok saknas.

    **BESLUT AV LARS i skiva 12.** Briefen listade GULT och OKLART med identiska
    registervillkor, vilket en deterministisk funktion inte kan honorera. Att
    skillnaden är ett besked från kunden föreslogs av agenten och antogs som
    beslut. Se `docs/beslutslogg.md` #24. Förvalet OKLART står fast.

    **BESKEDET BÄR SIN HÄRKOMST sedan skiva 13.** Det är inte längre en naken
    `bool` som vilken anropare som helst kan sätta, utan en `DragkrokBesked` som
    måste namnge sin källa, och källorna är uttömmande uppräknade i
    `BeskedKalla`.

    **TYPKONTROLLEN HÄR ÄR EN DEL AV SPÄRREN och inte en formalitet.** Utan den
    räckte det att skicka vilket objekt som helst med ett `.saknas`-attribut för
    att få GULT, alltså ett svar som namnger ett prispåslag, förbi hela
    härkomstkravet. Det var ett fynd i skiva 13:s granskning, och
    `test_besked_av_fel_typ_avvisas` vaktar det.

    Vad spärren gör och inte gör står i `docs/sparrar.md` under
    `dragkrokbesked-har-harkomst`.
    """
    if besked is not None and not isinstance(besked, DragkrokBesked):
        raise UppslagMisslyckades("beskedet är inte ett DragkrokBesked")

    if not ar_lamplig_som_dragfordon(uppslag):
        return Utfall.ROTT

    if uppslag.draganordning:
        return Utfall.GRONT

    if besked is not None and besked.saknas:
        return Utfall.GULT

    return Utfall.OKLART
