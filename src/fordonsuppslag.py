"""Slår upp de fordonsfakta som gatar en a-traktorombyggnad, och utvärderar dem.

TRE FÄLT BÄR §42: **tjänstevikt**, **släpvagnsvikt** och **draganordning**.
Beslut av Lars i skiva 13, se `docs/beslutslogg.md` #25.

**SEDAN SKIVA 55 GATAR TVÅ FÄLT TILL, och de kommer ur en annan föreskrift.**
Lars order, se `docs/beslutslogg.md` #121:

  `kaross`         `Ombyggd Bil` betyder att fordonet REDAN är ombyggt. Då är
                   utfallet RÖTT, och skälet är ett annat än §42:s.
  `fyrhjulsdrift`  tillsammans med tjänstevikten avgör den om §39:s
                   barlastflakskrav gäller fordonet.

*Här stod att "drivning, karosserikod och barlastflak ingår INTE i bedömningen"
och att allt annat uppslaget kan visa är merförsäljning. Det var Lars beslut i
skiva 13 och är upphävt av hans beslut i skiva 55: två av de fält meningen
uteslöt är nu gatande. `docs/roadmap.md` fas 4.5 bär samma mening och rättas
där.*

**`totalvikt`, `arsmodell` och `status` LÄSES MEN GATAR INGENTING.** De bärs av
`Uppslag` och visas i vyns härkomstrad, så att Lars ser vad registret sade.
De når ALDRIG prompten: varje tal i prompten blir ett citerbart tal, och de tre
svarar inte på någon fråga kunden ställt.

**ETT FÄLT LARS BAD OM FINNS INTE PÅ SIDAN.** Briefen säger `fordonsslag`, med
värdet `Traktor`. Mätt 2026-09-15 över tio sparade fordonssidor bär sidan 62
etiketter, och ingen av dem heter `Typ` eller `Fordonsslag`; ingen av de 62 bär
värdet `Traktor`. Det signalen faktiskt heter på den öppna sidan är
`Kaross: Ombyggd Bil`, alltså briefens ANDRA led. Se `docs/beslutslogg.md` #121.

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

Spärren `fordonsfakta-ur-uppslag` är utspridd över FEM funktioner: `_kontrollera`
prövar svarets form, `_krav_pa_gatande_falt` prövar att ett UTELÄMNAT gatande
fält är belagt som frånvarande i registret, `_krav_pa_vikt` prövar de två
vikterna, `Uppslag.__post_init__` prövar draganordningen och anropar viktkravet,
och `slag_upp` stoppar ett saknat registreringsnummer. Den som ska fälla den
enligt §7.1 måste fälla i alla fem; en prövning som bara rör `_kontrollera` når
inte värdelagren och ger ett inkonklusivt verdikt som ser konklusivt ut.

**ETT GATANDE FÄLT FÅR SEDAN SKIVA 55 VARA `None`, OCH BARA PÅ ETT SÄTT.**
Hämtningen måste säga att SIDAN inte bär fältet, alltså `saknas på sidan` ur
`biluppgifter.Faltstatus`, som i sin tur vilar på `_sidan_bar_inte_faltet`:s två
lager. Ett fält som stod på sidan och inte gick att läsa, `tolkas ej`, fäller
hela uppslaget precis som förut. Skillnaden är hela skiva 55 DEL B punkt 3: ett
uppslag som LYCKADES men där registret saknar en uppgift är inte ett uppslag som
föll, och kunden ska inte få veta att vi inte kunnat slå upp bilen.

**DET GER INGEN RÄTT ATT PÅSTÅ FRÅNVARO FÖR KUNDEN.** Skiva 41:s VÄG TRE står
oförändrad: `generera.Forfragan.franvaro_far_pastas` sätts bara av ett AVLÄST
`Draganordning: Nej`, och `src/kedja.py` är fortfarande det enda stället som
sätter den. Se `docs/beslutslogg.md` #93 och #121.

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

# VVFS 2003:19 4 kap 39 § första stycket, citerad ordagrant i `docs/roadmap.md`
# fas 4.5. Paragrafen inleds *"Om A-traktorn har en tjänstevikt av HÖGST 2 000
# kg, och MINDRE ÄN 60 % av tjänstevikten vilar på drivhjulen"*.
#
# **TALET ÄR SAMMA 2 000 SOM §42:s, OCH DE BETYDER MOTSATTA SAKER.** I §42 är
# 2 000 kg en NEDRE gräns som gör fordonet lämpligt; i §39 är det en ÖVRE gräns
# som drar in fordonet under barlastflakskravet. Konstanten står därför för sig,
# med eget namn, i stället för att `TROSKEL_TJANSTEVIKT_KG` återanvänds: en läsare
# som ser samma namn på båda ställena drar fel slutsats om riktningen, och
# `docs/roadmap.md` bär redan en rättelse av precis den förväxlingen.
TAK_BARLASTFLAK_TJANSTEVIKT_KG = 2000

# VÄRDET `biluppgifter.Faltstatus.SAKNAS_PA_SIDAN` BÄR, skrivet som en sträng här
# och INTE importerat.
#
# `src/biluppgifter.py` importerar inte den här modulen och tvärtom: modulen är
# nätverksfri och ska gå att pröva utan att en socket finns, vilket
# `src/biluppgifter.py`:s eget huvud anger som skälet till att den ligger för sig.
# Samma val som `kedja.A_TRAKTORKATEGORIER` och `vy._INTETSKAL` gör, och det binds
# på samma sätt: `test_frovarobeviset_matchar_biluppgifters_faltstatus` fäller om
# de två glider isär.
REGISTRET_SAKNAR_FALTET = "saknas på sidan"

# NYCKELN HÄMTNINGEN LÄGGER SIN STATUSKARTA UNDER. Samma val och samma bindning
# som `REGISTRET_SAKNAR_FALTET` ovan; `src/biluppgifter.py` äger skrivandet och
# den här modulen läsandet.
#
# **UNDERSTRECKET ÄR KONTRAKTET.** `_kontrollera` tolererar okända nycklar, och en
# metanyckel utan understreck hade riskerat att läsas som ett fordonsfält av
# nästa läsare. Samma skäl som `biluppgifter.META_DRAGVIKT` bär.
META_FALTSTATUS = "_faltstatus"

# NYCKELN OCH VÄRDET FÖR DRAGVIKTSLÄGET, samma val och samma bindning som ovan.
# `biluppgifter.Dragviktslage.REGISTRET_SAKNAR` är det enda av fyra lägen som
# säger att INGEN av sidans fyra släpviktsformer finns.
META_DRAGVIKT = "_dragviktslage"
REGISTRET_SAKNAR_DRAGVIKT = "registret saknar uppgiften"

# KAROSSVÄRDET SOM BETYDER ATT FORDONET REDAN ÄR OMBYGGT. Lars order i skiva 55.
#
# **AVLÄST OCH INTE ANTAGET.** Mätt 2026-09-15 över tio sparade fordonssidor:
# `Kaross` står på 10/10, och värdet `Ombyggd Bil` på 4 av dem. På precis de fyra
# saknar sidan dessutom både `Släpvagnsvikt` och `Draganordning`, alltså är det
# de ombyggda fordonen som bär det tunnaste registerutdraget.
#
# **JÄMFÖRELSEN ÄR SKIFTLÄGESOKÄNSLIG OCH ANNARS EXAKT.** Sidan skriver `Ombyggd
# Bil` i värdet och `Ombyggd BIL` inuti `Modell` och `Originalnamn TS`; en
# delsträngsjämförelse mot hela sidan hade alltså träffat fält vi inte läser.
# Här jämförs bara `Kaross` egna värde, och bara mot hela strängen.
KAROSS_REDAN_OMBYGGD = "ombyggd bil"


class UppslagMisslyckades(Exception):
    """Uppslaget gav inget som får användas i ett svar.

    Bärs som undantag och inte som ett returvärde, därför att ett misslyckat
    uppslag ALDRIG får förväxlas med ett lyckat. Ett returnerat `None` som
    någon glömmer pröva blir tyst; det här blir högljutt.

    **UNDANTAGET BÄR DRAGVIKTSLÄGET, och bara för härkomstradens skull.**
    Skillnaden mellan lägena finns PRECIS i de fall uppslaget misslyckas, och
    bärs den inte här kan vyn bara säga ATT något gick fel, aldrig VAD.

    *Stycket sade "UNDANTAGET BÄR SIDANS FÄLTSTATUSAR" och att informationen är
    den DEL B:s spärr behöver. Båda leden blev falska av VÄG TRE i skiva 41:
    `faltstatus` är borttaget, och ingen spärr läser något härifrån. Falskheten
    stod tre rader från den not som beskriver borttagningen. Fällt av
    §7-granskningen av skiva 41, varv 1.*

    `dragviktslage` är `None` när hämtningen inte lämnade något, alltså för varje
    annan hämtare än `biluppgifter_hamtning`.

    **DET ANVÄNDS BARA AV HÄRKOMSTRADEN I VYN, aldrig av en spärr.** Skiva 40
    lät det också avgöra vilka frånvaropåståenden som var tillåtna. Skiva 41 tog
    bort den vägen på Lars beslut: ett misslyckat uppslag ger aldrig rätt att
    påstå frånvaro, hur väl vi än tror oss veta varför det misslyckades. Se
    `docs/beslutslogg.md` #93.

    *Undantaget bar också `faltstatus`, som var den andra halvan av samma väg.
    Den blev oanvänd av VÄG TRE och är borttagen i stället för kvarlämnad: en
    oanvänd rörledning i sändvägen är något nästa skiva kan koppla tillbaka till
    en rättighet utan att någon märker det.*
    """

    def __init__(self, skal: str, *,
                 dragviktslage: str | None = None) -> None:
        super().__init__(skal)
        self.skal = skal
        self.dragviktslage = dragviktslage


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

    **`arsmodell` PRÖVAS INTE ALLS, och det ska stå här.** Fältet gatar
    ingenting, når aldrig prompten och läses av ingen gren, alltså hade en
    typkontroll varit ett lager som inget test kan fälla. §7.1 kallar det
    vakuöst. Blir fältet en dag en del av en bedömning ska kontrollen skrivas
    samtidigt.

    Spärren `fordonsfakta-ur-uppslag` vaktar hämtningens svar, inte anroparens
    fantasi. Luckorna är registrerade i `docs/sparrar.md` under samma namn.
    """

    # **TJÄNSTEVIKTEN ÄR OFÖRÄNDRAT OBLIGATORISK.** Den står på 10/10 sparade
    # sidor och på 6/6 i skiva 40:s stickprov, alltså är dess frånvaro nästan
    # säkert vår läsning och inte registret. Se `_krav_pa_tjanstevikt`.
    tjanstevikt_kg: int

    # **`None` BETYDER ATT REGISTRET INTE BÄR UPPGIFTEN, aldrig att vi inte kunde
    # läsa den.** Skillnaden vaktas av `_krav_pa_slapvagnsvikt` och
    # `_krav_pa_draganordning`, som kräver belägg ur hämtningen innan ett
    # utelämnat fält blir `None`. Se modulhuvudet.
    slapvagnsvikt_kg: int | None
    draganordning: bool | None

    # SKIVA 55 DEL A. `kaross` och `fyrhjulsdrift` GATAR, se `utvardera` och
    # `kraver_barlastflak`. De tre sista gatar ingenting och når aldrig prompten.
    #
    # **FÖRVALET ÄR `None` FÖR ALLA FEM, alltså oförändrat beteende för varje
    # anropare som inte känner dem.** Samma val som `Forfragan.uppslag_gjordes`
    # och `regnr_i_mailet` gjorde, och av samma skäl: ett tillkommande fält får
    # inte tyst ändra vad en befintlig anropare får ut.
    kaross: str | None = None
    fyrhjulsdrift: bool | None = None
    totalvikt_kg: int | None = None
    arsmodell: tuple[int, int] | None = None
    status: str | None = None

    def __post_init__(self) -> None:
        # Lokala namn, så att varje villkor ryms på EN rad. Ett villkor som
        # bryts över flera rader går inte att neutralisera enligt §7.1 utan att
        # filen blir syntaktiskt trasig, och då ger prövningen FEL i stället för
        # RÖD.
        drag = self.draganordning
        fyrhjul = self.fyrhjulsdrift

        # **`None` SLIPPER FÖRBI VÄRDEKRAVEN, och det är hela skillnaden mot
        # före skiva 55.** Invarianten är inte längre "varje fält bär ett
        # giltigt värde" utan "varje fält som BÄR ett värde bär ett giltigt".
        # Att fältet över huvud taget får vara tomt avgörs en nivå upp, av
        # `_krav_pa_gatande_falt`, och bara mot ett belägg ur hämtningen.
        _krav_pa_vikt(self.tjanstevikt_kg, "tjanstevikt_kg")

        if self.slapvagnsvikt_kg is not None:
            _krav_pa_vikt(self.slapvagnsvikt_kg, "slapvagnsvikt_kg")

        if self.totalvikt_kg is not None:
            _krav_pa_vikt(self.totalvikt_kg, "totalvikt_kg")

        if drag is not None and not isinstance(drag, bool):
            raise UppslagMisslyckades("draganordning är inte ja eller nej")

        if fyrhjul is not None and not isinstance(fyrhjul, bool):
            raise UppslagMisslyckades("fyrhjulsdrift är inte ja eller nej")

        # TEXTFÄLTEN. Ett tal eller ett objekt här hade nått `ar_redan_ombyggd`
        # och kastat `AttributeError` mitt i en bedömning i stället för att fällas
        # som ett trasigt uppslag.
        if self.kaross is not None and not isinstance(self.kaross, str):
            raise UppslagMisslyckades("kaross är inte text")

        if self.status is not None and not isinstance(self.status, str):
            raise UppslagMisslyckades("status är inte text")


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


def _sidan_saknar_faltet(svar: Mapping, nyckel: str) -> bool:
    """Säger hämtningen att SIDAN inte bär fältet?

    **DE TVÅ LAGREN FÅNGAR OLIKA SAKER**, och en §7.1-prövning ska fälla dem var
    för sig:

      `isinstance`-lagret  en hämtare som inte bär någon statuskarta alls, och en
                           som bär något annat än en mappning. Varje hämtare
                           utom `biluppgifter_hamtning` är i det läget, `tests/`
                           och `manuell_hamtning` inräknade, och för dem gäller
                           beteendet från före skiva 55.
      likhetslagret        en hämtare som säger `tolkas ej`, alltså att fältet
                           STOD på sidan och att VÅR läsning föll.

    **`tolkas ej` FÄLLER FORTFARANDE HELA UPPSLAGET.** Ett fält vi inte kunde
    läsa säger ingenting om bilen, och skiva 24 och 39 band beteendet: `Ja Kula`
    i `Draganordning` ger `None` ur `_ja_nej` med avsikt, och ärendet blir ett
    utkast utan bedömning. Att behandla det som *"registret bär ingen uppgift"*
    hade bytt ut ett eget fel mot en egenskap hos registret, vilket är precis det
    `biluppgifter.dragviktslage` ordnar sin prövningsordning för att undvika.
    """
    statusar = svar.get(META_FALTSTATUS)

    if not isinstance(statusar, Mapping):
        return False

    return statusar.get(nyckel) == REGISTRET_SAKNAR_FALTET


def _krav_pa_tjanstevikt(svar: Mapping, meta: dict) -> None:
    """SPÄRRLAGER: tjänstevikten är ALDRIG valfri.

    **DE TRE GATANDE FÄLTEN BEHANDLAS OLIKA SEDAN SKIVA 55, och skillnaden är
    mätt och inte vald av symmetri.** Avläst 2026-09-15 över tio sparade
    fordonssidor, och i skiva 40 över sex andra:

      `Tjänstevikt`     10/10 och 6/6. Inget fordon i något stickprov saknar den.
      `Släpvagnsvikt`   5/10 och 4/6.
      `Draganordning`   6/10 och 5/6.

    **DÄRFÖR ÄR EN SAKNAD TJÄNSTEVIKT NÄSTAN SÄKERT VÅRT FEL.** De två andra
    saknas på var tredje till var annan verklig sida, alltså är deras frånvaro
    ett normalläge i registret. Tjänsteviktens är det inte, och att kalla den
    ett registerfaktum vore att bygga skiva 55:s uppmjukning på det fält där den
    har svagast stöd.

    **DET ÄR OCKSÅ VARFÖR `Uppslag.tjanstevikt_kg` INTE ÄR VALFRI I TYPEN.**
    Invarianten är oförändrad sedan skiva 12 för just det fältet, och
    `_krav_pa_vikt` prövar den ovillkorligt.
    """
    if not _bar_nyckel(svar, "tjanstevikt_kg"):
        raise UppslagMisslyckades("svaret saknar tjanstevikt_kg", **meta)


def _krav_pa_slapvagnsvikt(svar: Mapping, meta: dict) -> None:
    """SPÄRRLAGER: släpvagnsvikten får utelämnas bara mot TVÅ oberoende belägg.

    **ETT BELÄGG RÄCKER INTE, OCH DET ÄR SVITEN SOM VISADE DET.** Första
    lydelsen av skiva 55 krävde bara `saknas på sidan`, och då blev
    `test_omdopt_etikett_faller_till_utkast` grön på fel sätt: en sida som döper
    om `Släpvagnsvikt` till `Släpvikt max` bär inte etikettexten, ankarna står
    kvar, och läsningens fel såg ut som ett registerfaktum. Det är exakt den
    klass skiva 41:s VÄG TRE varnar för, ordagrant *"ett mjukt bindestreck i
    `Släpvagnsvikt` räcker för att fältet ska se saknat ut"*.

    **ANDRA BELÄGGET ÄR DRAGVIKTSLÄGET, och det är en ANNAN mätning.**
    `biluppgifter.dragviktslage` säger `registret saknar uppgiften` bara när
    INGEN av sidans FYRA släpviktsformer finns: den bromsade, den obromsade och
    de två körkortsraderna. En omdöpt etikett rör en av dem, alltså står de
    övriga tre kvar och läget blir `ANNAN_FORM`, som fäller här.

    **DE TVÅ ÄR DÄRMED INTE REDUNDANTA.** Statuslagret fäller en hämtare utan
    statuskarta och en som säger `tolkas ej`; dragviktslägets lager fäller den
    omdöpta etiketten. En §7.1-prövning som fäller bara det ena får ett
    inkonklusivt utfall.

    **FALLET DET SLÄPPER IGENOM** är fordonet i Lars körning vars sida saknar
    samtliga fyra släpviktsformer. Läget blir `registret saknar uppgiften`, och
    uppslaget lyckas med `slapvagnsvikt_kg` tom.
    """
    if _bar_nyckel(svar, "slapvagnsvikt_kg"):
        return

    if not _sidan_saknar_faltet(svar, "slapvagnsvikt_kg"):
        raise UppslagMisslyckades("svaret saknar slapvagnsvikt_kg", **meta)

    if svar.get(META_DRAGVIKT) != REGISTRET_SAKNAR_DRAGVIKT:
        raise UppslagMisslyckades("svaret saknar slapvagnsvikt_kg", **meta)


def _krav_pa_draganordning(svar: Mapping, meta: dict) -> None:
    """SPÄRRLAGER: draganordningen får utelämnas mot ETT belägg.

    **DET FINNS INGET ANDRA BELÄGG ATT KRÄVA, och det ska stå rakt ut.**
    `Släpvagnsvikt` har tre alternativa former på sidan att mätas mot;
    `Draganordning` har ingen. En omdöpt etikett här ser alltså likadan ut som
    ett fordon utan registrerad draganordning, och skillnaden går inte att
    avgöra ur en sida. Formen står som LUCKA 71 i `docs/sparrar.md`.

    **RIKTNINGEN PÅ DET FELET ÄR DEN SÄKRA, och det är skälet att luckan lämnas
    öppen.** Ett `None` här kan aldrig ge GRÖNT: `utvardera` returnerar OKLART,
    och `krav_pa_fordonsfakta_ur_uppslag` fäller varje mening som nämner
    dragkrok. En omdöpt etikett kostar alltså ett svagare svar, aldrig ett
    falskt. Att den ändå SYNS bärs av `logga_uppslag`:s `falt_saknas`, som
    räknas per dygn.

    **ATT FÄLTET OFTA SAKNAS PÅ RIKTIGT ÄR MÄTT.** `Draganordning` står på 6 av
    10 sparade sidor, och de fyra som saknar den är precis de fyra vars `Kaross`
    är `Ombyggd Bil`. Ett fordon som redan är ombyggt bär ett tunnare
    registerutdrag, och att fälla hela uppslaget för dem hade tystat just den
    bedömning skiva 55 DEL A regel 1 finns för att göra.
    """
    if _bar_nyckel(svar, "draganordning"):
        return

    if not _sidan_saknar_faltet(svar, "draganordning"):
        raise UppslagMisslyckades("svaret saknar draganordning", **meta)


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

    # METADATAN UR HÄMTNINGEN, om den lämnade någon. Skiva 40 DEL A.
    #
    # **HÄMTAS FÖRE NYCKELLAGREN, eftersom det är DE som kastar.** Varje kast
    # nedan ska bära läget, annars kan härkomstraden bara säga att något gick
    # fel och inte vad.
    meta = {"dragviktslage": svar.get("_dragviktslage")}

    _krav_pa_tjanstevikt(svar, meta)
    _krav_pa_slapvagnsvikt(svar, meta)
    _krav_pa_draganordning(svar, meta)

    return Uppslag(
        tjanstevikt_kg=svar.get("tjanstevikt_kg"),
        slapvagnsvikt_kg=svar.get("slapvagnsvikt_kg"),
        draganordning=svar.get("draganordning"),
        kaross=svar.get("kaross"),
        fyrhjulsdrift=svar.get("fyrhjulsdrift"),
        totalvikt_kg=svar.get("totalvikt_kg"),
        arsmodell=svar.get("arsmodell"),
        status=svar.get("status"),
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


def ar_lamplig_som_dragfordon(uppslag: Uppslag) -> bool | None:
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

    **TRE UTFALL SEDAN SKIVA 55, OCH DET TREDJE ÄR `None`.** Ett fält som
    registret inte bär går inte att pröva mot sin tröskel, och då är svaret VET
    EJ och aldrig NEJ. `False` kräver alltså att BÅDA talen är avlästa och att
    båda faller.

    **RIKTNINGEN ÄR DEN ENDA SÄKRA.** Före skiva 55 kunde ett fält som saknades
    i registret inte nå hit alls: `_kontrollera` fällde hela uppslaget. Nu når
    det hit, och ett `None` som lästes som noll hade gjort varje bil utan
    dragviktsuppgift RÖTT, alltså ett nej till en kund vars bil föreskriften inte
    säger något om. Det är skiva 12:s defekt i ny form, och `ar_lamplig`:s egen
    docstring bär redan skälet till att den klassen inte får återkomma.

    **BARA SLÄPVAGNSVIKTEN KAN VARA OKÄND HÄR.** Tjänstevikten är obligatorisk i
    typen, se `_krav_pa_tjanstevikt`, alltså finns det ingen gren för den och
    ingen rad att fälla. Skulle det fältet en dag bli valfritt måste ett `None`-
    led läggas till här i samma ändring, annars läses okunskapen som noll och
    varje sådan bil blir RÖTT.
    """
    if uppslag.tjanstevikt_kg >= TROSKEL_TJANSTEVIKT_KG:
        return True

    if uppslag.slapvagnsvikt_kg is not None \
            and uppslag.slapvagnsvikt_kg >= TROSKEL_SLAPVAGNSVIKT_KG:
        return True

    if uppslag.slapvagnsvikt_kg is None:
        return None

    return False


def ar_redan_ombyggd(uppslag: Uppslag) -> bool:
    """GATINGSREGEL 1, skiva 55: fordonet är REDAN ombyggt.

    **KUNDEN BER OM EN OMBYGGNAD AV NÅGOT SOM REDAN ÄR OMBYGGT.** Lars order, se
    `docs/beslutslogg.md` #121. I hans körning fick TVÅ fordon ett erbjudande om
    grundombyggnad trots att båda står som ombyggda i registret.

    **REGELN PRÖVAR `Kaross`, OCH BRIEFENS FÖRSTA LED FINNS INTE.** Lars skrev
    *"fordonsslag Traktor, eller kaross Ombyggd Bil"*. Mätt över tio sparade
    sidor bär sidan ingen etikett `Typ` eller `Fordonsslag`, och inget av de 62
    fältens värden är `Traktor`. Andra ledet är avläst och entydigt, och det är
    det som är byggt. Se modulhuvudet.

    **MÄTNINGEN, ur samma tio sidor:** `Kaross` står på 10/10 och bär `Ombyggd
    Bil` på fyra. Regeln träffar alltså TVÅ FORDON TILL utöver de Lars namnger.

    **ETT SAKNAT ELLER OLÄSBART `Kaross` GER `False`, aldrig ett larm.** Fältet
    är inte gatande i den riktningen: att vi inte vet om bilen är ombyggd är
    inget skäl att säga nej. `Kaross` stod på samtliga tio sidor, så fallet är
    inte ett normalfall, men riktningen ska vara utskriven.
    """
    if uppslag.kaross is None:
        return False

    return uppslag.kaross.strip().lower() == KAROSS_REDAN_OMBYGGD


def kraver_barlastflak(uppslag: Uppslag) -> bool | None:
    """GATINGSREGEL 2, skiva 55: gäller §39:s barlastflakskrav det här fordonet?

    `True` betyder att båda leden i §39 första stycket kan vara uppfyllda,
    `False` att minst ett av dem bevisligen inte är det, och `None` att vi inte
    vet. Se `docs/beslutslogg.md` #121.

    **PARAGRAFEN, ORDAGRANT UR `docs/roadmap.md` fas 4.5, tryckt sida 15:**

    > **39 §** Om A-traktorn har en tjänstevikt av högst 2 000 kg, och mindre än
    > 60 % av tjänstevikten vilar på drivhjulen, skall den vara försedd med
    > barlastflak som medger tillräcklig barlast.

    **TVÅ LED, FÖRENADE MED OCH.** Faller ett av dem gäller kravet inte.

      tjänstevikt ÖVER 2 000 kg   första ledet faller. Talet är en ÖVRE gräns
                                  här och en NEDRE i §42, se
                                  `TAK_BARLASTFLAK_TJANSTEVIKT_KG`.
      fyrhjulsdrift               andra ledet faller. Är varje hjul ett drivhjul
                                  vilar 100 % av tjänstevikten på drivhjulen,
                                  alltså inte `mindre än 60 %`.

    **SEXTIOPROCENTSREGELN GÅR INTE ATT AVGÖRA UR REGISTRET I ALLMÄNHET**, och
    `docs/roadmap.md` säger det. Fyrhjulsdrift är det enda fall där den går att
    avgöra, och bara i den ena riktningen: `Ja` utesluter kravet, `Nej` säger
    ingenting om hur lasten fördelar sig mellan axlarna. Därför är `False` ett
    besked och `True` det aldrig är: den här funktionen returnerar aldrig `True`
    som ett påstående om att flak KRÄVS, utan bara som *vi kan inte utesluta
    kravet*.

    *Det är därför returvärdet inte används för att säga något till kunden.
    `src/generera.py` läser bara `False`, alltså det utfall där vi VET att
    fordonet inte behöver flak, och tystar uppräkningen då.*

    **FALLET LARS LÄSTE** är ett fordon med `Fyrhjulsdrift: Ja` och tjänstevikt
    1 720 kg. Prisradens uppräkning säger att barlastflak ingår i
    grundombyggnaden, vilket för den bilen är fel.
    """
    if uppslag.fyrhjulsdrift is True:
        return False

    if uppslag.tjanstevikt_kg > TAK_BARLASTFLAK_TJANSTEVIKT_KG:
        return False

    if uppslag.fyrhjulsdrift is None:
        return None

    return True


def utvardera(
    uppslag: Uppslag,
    *,
    besked: DragkrokBesked | None = None,
) -> Utfall:
    """Fyra utfall ur fem fält. Boolesk logik, ingen modell.

    GATINGEN ÄR TRE SAKER SEDAN SKIVA 55: att fordonet inte REDAN är ombyggt,
    lämplighet som dragfordon enligt §42 andra stycket, och draganordning.
    **RÖTT ur §42 kräver att BÅDA lämplighetsvillkoren faller**, inte bara
    släpvagnsvikten, och att båda talen är AVLÄSTA.

    **RÖTT HAR DÄRMED TVÅ SKÄL, och de får inte blandas ihop i svaret.** Ett
    fordon med `Kaross: Ombyggd Bil` är redan en a-traktor; ett fordon vars båda
    vikter faller duger inte som dragfordon. Att säga det andra om det första
    hade varit ett falskt påstående om bilen, och `src/generera.py` väljer text
    efter `ar_redan_ombyggd`.

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

    # **REGEL 1 GÅR FÖRST, OCH ORDNINGEN AVGÖR VAD KUNDEN FÅR LÄSA.** Ett redan
    # ombyggt fordon är RÖTT av ett helt annat skäl än §42:s, och skälet följer
    # med hela vägen: `generera._utfallstext` frågar `ar_redan_ombyggd` och
    # väljer text därefter. Stod raden efter lämplighetsprövningen hade det
    # ombyggda fordon som väger 2 005 kg blivit LÄMPLIGT, och därmed fått ett
    # svar om dragkrok på en bil som redan är en a-traktor.
    if ar_redan_ombyggd(uppslag):
        return Utfall.ROTT

    lamplig = ar_lamplig_som_dragfordon(uppslag)

    # **`is False` OCH INTE `not lamplig`, och det ledet är hela skiva 55 DEL B
    # punkt 3.** `None` betyder att registret inte bär talen, och ett `not` hade
    # läst den okunskapen som ett NEJ. Då blir varje bil vars sida saknar
    # `Släpvagnsvikt` RÖTT, alltså fyra av tio fordon i Lars körning, på en
    # uppgift registret aldrig lämnat.
    if lamplig is False:
        return Utfall.ROTT

    if lamplig is None:
        return Utfall.OKLART

    # HÄRIFRÅN ÄR FORDONET LÄMPLIGT SOM DRAGFORDON, alltså är §42 andra stycket
    # uppfyllt och det enda som återstår är kopplingsanordningen.
    if uppslag.draganordning is True:
        return Utfall.GRONT

    # REGISTRET SÄGER INGENTING OM DRAGANORDNINGEN. Ett `not` hade fallit vidare
    # till beskedsgrenen och därmed kunnat ge GULT, alltså ett svar som namnger
    # ett prispåslag, på ett fordon vi inte läst något om.
    if uppslag.draganordning is None:
        return Utfall.OKLART

    if besked is not None and besked.saknas:
        return Utfall.GULT

    return Utfall.OKLART
