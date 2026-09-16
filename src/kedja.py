"""KEDJAN: inkommande mail till utkast i vyn. SÄNDVÄG.

Fram till skiva 34 fanns delarna var för sig och ingenting anropade något annat.
`slag_upp` anropades bara ur tester, och vyns granskningsläge hade ingen rutt.
Den här modulen är sömmen, och den är AVSIKTLIGT tunn: den fattar inga beslut
som någon av delarna redan fattar, den bara för vidare.

**INGEN SÄNDNING. VÄGEN SLUTAR I VYN.** Modulen har ingen väg till en brevlåda,
och `vy.krav_pa_sandvagsfrihet("src.kedja")` prövar hela kedjan, inte bara den
här filen: den vandrar importgrafen och läser källtexten i varje modul den når.

Ordningen är:

    mail -> klassificering -> GRIND: a-traktor? -> uppslag
         -> GRIND: redan ombyggd? -> generering -> spärrar -> utkast

**KEDJAN SKRIVER SVAR PÅ A-TRAKTOR OCH PÅ INGENTING ANNAT.** Lars beslut i
skiva 51 DEL B. En kategori utanför `A_TRAKTORKATEGORIER` blir `INGET SVAR`
utan att generatorn anropas. Klassningen görs ändå och kategorin loggas, så att
materialet finns den dag fas 6 tar nästa kategori. Sedan skiva 61 når posten
inte vyn: anroparna sparar bara poster med ett utkast eller en spärr.

*Skivan mätte vad grinden kostar. Med de pass-2-etiketter som finns att mäta
mot i `data/ometiketterade.jsonl` skriver kedjan i dag ett utkast för 133
ärenden som grinden nu tystar; talen per material står i `docs/beslutslogg.md`
#117. Utkasten var inte efterfrågade av någon: ingen kategori står i `auto`,
alltså kunde inget av dem gå ut, och var och en kostade ett modellanrop.*

**`kor` LOGGAR INTE SJÄLV, och skissen framställde det som om den gjorde det.**
Loggningen är ett eget anrop, `logga_beslut` eller `logga_kallfel`, och det görs
av anroparen. Skälet är att `kor` ska gå att köra i ett test utan att röra
disken. Anroparens ansvar är att en rad skrivs för VARJE utfall, källfelet
inräknat. Fällt av §7-granskningen av skiva 34, varv 2.

**TRE UTFALL, och `INGET SVAR` är det tredje.** `kor` returnerar en
`Kedjeutfall` som bär antingen ett utkast, en fälld spärr, eller `inget_svar`.
Det sista har sedan skiva 63 TRE skäl, och `inget_svar_skal` säger vilket:
hinken `aldrig`, en kategori grinden inte släpper fram, eller ett fordon
registret säger redan är ombyggt. I alla tre fallen anropas generatorn
inte alls.

*Här stod att HINKEN AVGÖR INGENTING HÄR, och att ett utkast produceras för
varje kategori också de i `aldrig`, med motiveringen att skuggläget annars inte
kan mäta vad som HADE gått ut. Lars beslut i skiva 49 vänder den avvägningen för
hinken `aldrig`, och skälet är att den mätningen inte finns: ramverksregel 1
säger att INGENTING i `aldrig` någonsin får gå ut, alltså är svaret på "vad hade
gått ut" känt utan att ett anrop görs. Vad det kostade var ett modellanrop per
ärende i `aldrig` och en vy full av utkast som aldrig kan gå ut. Skuggläget ser
posten ändå: kategorin och hinken loggas och visas som förut.* *Visas gäller
inte sedan skiva 61: posten loggas men sparas inte till vyn.*

**HINKEN AVGÖR FORTFARANDE INGENTING OM SÄNDNING här.** Ramverksregel 1 gäller
sändvägen, och den här modulen har ingen. `aldrig` stoppar GENERERINGEN, inte en
sändning, och `auto` och `utkast` går samma väg som förut.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable

from src import biluppgifter, fordonsuppslag, generera, ometikettera, sokvagar
from src.fordonsuppslag import UppslagMisslyckades, Uppslag, Utfall
from src.generera import Forfragan, Sparrfalld
from src.vy import Fall, Granskningsfall, krav_pa_skrivbar_sokvag

ROT = Path(__file__).resolve().parent.parent

# KATALOGERNA UR `src/sokvagar.py`, skiva 53. Se den modulens huvud.
BESLUTSLOGG = sokvagar.LOGG / "beslut.jsonl"
TAXONOMIFIL = sokvagar.DATA / "taxonomi.json"

# KATEGORIERNA SOM GATAS AV FORDONSUPPSLAGET, ur `docs/roadmap.md` fas 4.5.
# Samma tre som `vy.A_TRAKTORETIKETTER`, och de står här som en egen tupel
# eftersom en import av vyns konstant hade gjort kedjan beroende av vyns
# rendering. `test_kedjans_a_traktorkategorier_matchar_vyns` binder att de två
# inte glider isär.
A_TRAKTORKATEGORIER = (
    "fråga om a-traktorkonvertering",
    "boka a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# SKÄLEN TILL `INGET SVAR`. Strängarna står här och inte som literaler
# på användningsstället, eftersom de skrivs på två ställen i `kor`: i
# `Steg.detalj`, som går till `logg/beslut.jsonl`, och i
# `Kedjeutfall.inget_svar_skal`, som gick till vyn. Går de isär säger loggen och
# sidan olika saker om samma post. Sedan skiva 61 sparar ingen körning en post
# utan svar till vyn, men äldre sparade filer bär fältet och vyn visar det.
#
# **VYN BÄR SAMMA STRÄNGAR SKRIVNA EN GÅNG TILL**, som nycklar i `vy._INTETSKAL`.
# `src/vy.py` kan inte importera härifrån: importen går åt andra hållet. Samma
# val som `A_TRAKTORETIKETTER`, och `test_vyns_INGET_SVAR_skal_matchar_kedjans`
# fäller om de två uppräkningarna glider isär.
#
# **DE ÄR VÅRA EGNA FASTA STRÄNGAR och bär ingenting ur ett modellsvar.** Det
# är villkoret för att de får nå `data/granskningsfall.jsonl` och vyn. Jämför
# `Sparrfalld.skal`, som byggs av text lyft ordagrant ur utkastet och därför
# aldrig loggas och renderas genom `maskera.maska_sparrskal`. Den lämnar sedan
# skiva 57 DEL 0 ETT tal omaskerat, det spärren namnger som skäl, och maskerar
# allt annat i strängen.
SKAL_ALDRIG = "hinken aldrig"
SKAL_OGATAD = "ingen a-traktorkategori"
# SKIVA 63 DEL A, Lars beslut. Ett fordon registret säger redan är ombyggt
# behöver inget svar, oavsett vem som byggt om det.
SKAL_REDAN_OMBYGGD = "redan ombyggd"

# ÄLDRE ÄN SÅ FÅR SVARET EFTERSLÄPSRADEN. Skiva 61 DEL B, Lars tal.
EFTERSLAP = timedelta(days=7)


def ar_efterslapande(tidsstampel: str, nu: datetime) -> bool:
    """Är mailet ÄLDRE än `EFTERSLAP`, räknat från `nu`? Exakt sju dagar är nej.

    `tidsstampel` är `urval.tidsstampel`:s ISO-sträng. **TOM STRÄNG GER NEJ**:
    utan en känd ålder ska svaret inte ursäkta ett dröjsmål. En sträng utan
    tidszon läses som UTC, samma zon som `urval.tidsstampel` skriver.
    """
    if not tidsstampel:
        return False

    mottaget = datetime.fromisoformat(tidsstampel)
    if mottaget.tzinfo is None:
        mottaget = mottaget.replace(tzinfo=timezone.utc)

    return nu - mottaget > EFTERSLAP


class Kallfel(Exception):
    """Uppslagskällan svarade inte alls.

    **SKILD FRÅN `UppslagMisslyckades` MED FLIT.** `slag_upp`:s docstring skriver
    ut varför: en källa som är nere är inte samma sak som ett fordon utan
    uppgifter, och att översätta det ena till det andra gör ett driftavbrott
    osynligt. Kedjan stannar på den här, och genererar inget alls.

    **`sort` ÄR DET ENDA SOM FÅR LOGGAS, och det är en §6-rättelse.** Undantaget
    byggs av `except Exception` runt ANROPARENS hämtfunktion, alltså inte av
    strängar `src/fordonsuppslag.py` äger. En `ConnectionError` från requests
    lyder *"HTTPSConnectionPool(host=biluppgifter.se, ...): Max retries exceeded
    with url: /fordon/ABC123"*, alltså bär den ett REGISTRERINGSNUMMER, som §6
    namnger som persondata och förbjuder i `logg/`.

    Meddelandet finns kvar i undantaget för den som står vid terminalen, där det
    inte persisteras. `sort` är typnamnet och inget annat, och det är vad
    `logga_kallfel` skriver. Fällt av §7-granskningen av skiva 34, varv 3.
    """

    def __init__(self, sort: str, detalj: str = ""):
        self.sort = sort
        super().__init__(f"{sort}: {detalj}" if detalj else sort)


@dataclass(frozen=True)
class Arende:
    """Ett inkommande mail, med det kedjan behöver och inget mer.

    **INGEN AVSÄNDARADRESS.** §6: loggar bär hashade avsändare. Fältet heter
    `avsandare_hash` för att en adress inte ska kunna smyga in genom att någon
    fyller ett fält som heter `avsandare`.
    """

    text: str
    amne: str = ""
    kanal: str | None = None
    regnr: str | None = None
    avsandare_hash: str = ""
    tidsstampel: str = ""
    # SKIVA 61. Sant när tråden redan bär ett svar från oss, och då blir det
    # ingen eftersläpsrad. Sedan skiva 62 är `tidsstampel` trådens SENASTE
    # kundmail i `scripts/respond.py`, Lars beslut. Flaggan står kvar: ett svar
    # från oss i tråden stänger fallet oavsett vilket mail som daterar.
    besvarad: bool = False


@dataclass(frozen=True)
class Steg:
    """Ett steg i kedjan, som det gick.

    `utfall` är kort och maskinläsbart, `detalj` är för en människa.
    """

    namn: str
    utfall: str
    detalj: str = ""

    # SKIVA 40 DEL A. Uppslagssteget bär VILKET läge som gäller, inte bara att
    # något misslyckades. `None` för varje steg som inte är ett uppslag.
    #
    # **DET ANVÄNDS BARA AV HÄRKOMSTRADEN.** Skiva 40 lät det också styra vilka
    # frånvaropåståenden som var tillåtna; skiva 41 tog bort den vägen, se
    # `docs/beslutslogg.md` #93.
    dragviktslage: str | None = None


@dataclass(frozen=True)
class Kedjeutfall:
    """Vad kedjan kom fram till. Bär ALDRIG ett skickat mail.

    **TRE UTFALL.** `kor` sätter exakt ett av dem:

      UTKAST      `utkast` är en text. Spärrarna passerade.
      SPÄRRAD     `sparr` bär spärrens namn. Ett svar skrevs och fälldes.
      INGET SVAR  `inget_svar` är sant och `inget_svar_skal` säger varför.
                  Generatorn anropades ALDRIG.

    **DE TVÅ SISTA ÄR INTE SAMMA SAK, och det är hela skälet att det tredje
    finns.** En spärr säger att modellen skrev något den inte fick skriva, alltså
    att något gick fel. Ett ärende i `aldrig` är inte ett fel: hinken säger att
    svaret aldrig får gå ut, alltså finns ingen anledning att skriva det. Att
    bygga utfallet som en spärr hade kostat ett modellanrop per sådant ärende och
    sedan fyllt `per_sparr` i skugglägets summering med en rad som inte är ett
    fynd. Lars beslut i skiva 49.

    Garantin om exakt ett är `kor`:s och inte typens, av samma skäl som
    `till_granskningsfall` skriver ut om `utkast` och `sparr`: en direkt
    konstruerad `Kedjeutfall` kan bära vad som helst.
    """

    kategori: str
    hink: str
    uppslag: Uppslag | None = None
    utfall: Utfall | None = None
    utkast: str | None = None
    sparr: str | None = None
    # SKIVA 49 DEL B. Sant när generatorn hoppades över. Ett eget fält och inte
    # en spärrsträng, se klassens docstring.
    inget_svar: bool = False
    # SKIVA 51 DEL B. VILKET skäl. `SKAL_ALDRIG`, `SKAL_OGATAD` eller, sedan
    # skiva 63, `SKAL_REDAN_OMBYGGD`. Tom när `inget_svar` är falskt.
    #
    # **ETT EGET FÄLT OCH INTE `skal`.** `skal` bär `Sparrfalld.skal`, som är
    # byggt av strängar lyfta ordagrant ur modellens svar och därför kan bära
    # ett telefonnummer eller ett registreringsnummer. Det fältet loggas aldrig
    # och renderas genom `maskera.maska_sparrskal`, som sedan skiva 57 DEL 0
    # lämnar ETT tal omaskerat: det spärren namnger som skäl. Den här bär en av
    # modulens `SKAL_*`-strängar, och det är skillnaden som gör att den
    # får gå till vyn rå.
    inget_svar_skal: str = ""
    skal: str = ""
    # SKIVA 56 DEL 0. Satsen `skal` handlar om, alltså den text spärren prövade.
    # För två av spärrarna är den bearbetad och inte en ordagrann delsträng ur
    # svaret, se `generera.Sparrfalld`. Bär samma sorts text som `skal` och
    # lyder under samma villkor: maskeras innan den når en skärm, loggas aldrig.
    sats: str = ""
    steg: tuple[Steg, ...] = field(default_factory=tuple)

    @property
    def blev_utkast(self) -> bool:
        return self.utkast is not None


def _uppslagssteg(
    arende: Arende,
    hamta: Callable[[str], dict | None],
) -> tuple[Uppslag | None, Utfall | None, Steg]:
    """Uppslaget, och vad som hände.

    **TVÅ SORTERS MISSLYCKANDE, och de leder olika vägar.** Ett fordon utan
    uppgifter ger `uppslag=None` och kedjan fortsätter: generatorn har ett eget
    läge för det, och svaret säger att vi inte kunnat slå upp bilen. En källa som
    KASTAR något annat blir `Kallfel` och stoppar kedjan, eftersom vi då inte vet
    om bilen duger eller inte.
    """
    try:
        uppslag = fordonsuppslag.slag_upp(arende.regnr, hamta=hamta)
    except UppslagMisslyckades as fel:
        # **STEGET SÄGER VILKET UTFALL DET ÄR, inte bara att något misslyckades.**
        # Lars order i skiva 40. Härkomstraden i vyn sade MISSLYCKADES för tre
        # lägen som betyder olika saker, och femton skarpa uppslag PER KÖRNING
        # gav noll gröna och noll röda utan att det gick att se varför.
        #
        # *Kvalifikatorn "per körning" saknades här. `docs/beslutslogg.md` #78
        # bär en kursiv not om exakt den utelämningen, och den återinfördes i
        # den här kommentaren. Fällt av §7-granskningen av skiva 40, varv 1 och
        # varv 2.*
        # **ETT MISSLYCKAT UPPSLAG GER ALDRIG RÄTT ATT PÅSTÅ FRÅNVARO.**
        # Lars beslut i skiva 41, VÄG TRE på lucka 50. Steget bär läget för
        # HÄRKOMSTRADENS skull och för ingenting annat.
        return None, None, Steg("uppslag", "misslyckades", str(fel),
                                dragviktslage=fel.dragviktslage)
    except Exception as fel:  # noqa: BLE001
        raise Kallfel(type(fel).__name__, str(fel)) from fel

    utfall = fordonsuppslag.utvardera(uppslag)
    return uppslag, utfall, Steg("uppslag", "lyckades", _lyckadetalj(uppslag,
                                                                    utfall))


# DE TRE GATANDE FÄLTEN, med de namn härkomstraden skriver ut.
#
# **NAMNEN ÄR KUNDVÄNLIGA OCH INTE NYCKLARNA.** Raden läses av Lars i vyn
# bredvid ett utkast, inte av kod, och `slapvagnsvikt_kg` säger honom inget som
# `släpvagnsvikt` inte säger bättre.
_GATANDE_FALT = {
    "tjanstevikt_kg": "tjänstevikt",
    "slapvagnsvikt_kg": "släpvagnsvikt",
    "draganordning": "draganordning",
}


def _lyckadetalj(uppslag: Uppslag, utfall: Utfall) -> str:
    """Utfallet, och vilka gatande fält registret INTE bar. Skiva 55 DEL A.

    **ETT LYCKAT UPPSLAG KAN NUMERA SAKNA FÄLT, och utan den här raden syns det
    inte.** Före skiva 55 var `lyckades` liktydigt med att alla tre fälten var
    avlästa, alltså räckte utfallet som detalj. Nu ger ett fordon utan
    dragviktsuppgift i registret ett LYCKAT uppslag med tom släpvagnsvikt, och
    ett OKLART utan förklaring ser i vyn ut som en
    bot som inte kan bestämma sig.

    **DET ÄR EN UPPGIFT TILL LARS OCH ALDRIG TILL KUNDEN.** Strängen går till
    `logg/beslut.jsonl` och till härkomstraden. Vad boten får SKRIVA styrs av
    `generera.Forfragan.franvaro_far_pastas`, som är oförändrad sedan skiva 41.

    **INGA VÄRDEN, BARA FÄLTNAMN.** Raden bär inga vikter: `logg/beslut.jsonl`
    är gitignorerad, men en detaljsträng som växer med fordonsdata är en
    persondataväg som ingen bett om. §6.
    """
    saknade = [ord_ for nyckel, ord_ in _GATANDE_FALT.items()
               if getattr(uppslag, nyckel) is None]

    if not saknade:
        return utfall.value

    return f"{utfall.value}, registret bar ingen {' och ingen '.join(saknade)}"


def kor(
    arende: Arende,
    *,
    klient,
    hamta: Callable[[str], dict | None],
    hinkar: dict,
    taxonomi: list[str],
    exempel: list[dict] | None = None,
    nu: datetime | None = None,
) -> Kedjeutfall:
    """Hela vägen för ETT ärende. Returnerar aldrig ett skickat mail.

    `nu` är KÖRNINGENS tidpunkt, och ärendets ålder räknas från den. Skiva 61.
    `None` betyder att åldern inte prövas, alltså blir det aldrig någon
    eftersläpsrad, och en tråd vi redan svarat i får den aldrig heller.
    `scripts/respond.py` skickar alltid ett värde:
    `test_CLI_satter_KORNINGENS_tidpunkt_och_inget_annat` binder att `_kor`
    sätter klockan, och `test_slingan_skickar_KORNINGENS_tidpunkt` att
    `kor_alla` lämnar den vidare.

    `klient`, `hamta` och `taxonomi` har inga förval. Den som anropar väljer
    modell, källa och kategorilista medvetet, vilket är samma skäl `slag_upp`
    anger för sitt eget `hamta`: en tyst standardkälla i en sändvägsmodul är
    precis det §10 finns för att hindra.

    **KLASSNINGEN ÄR PASS 2, och det ledet är fällt fram av kedjans egen
    provkörning.** Första lydelsen anropade `kategorisera.kategorisera_en` med
    dess förvalda systemprompt, alltså PASS 1, som uttryckligen säger *"Använd
    INGEN lista. Hitta det namn som passar texten."* Följden var att varje
    a-traktormail fick en påhittad etikett som `offert på a-traktorombyggnad`
    eller `konvertera till elbil`, och eftersom ingen av dem står i taxonomin
    **utlöstes fordonsuppslagets grind aldrig**. Tio av tio ärenden hoppade över
    uppslaget.

    Pass 1 är upptäcktspasset som BYGGER taxonomin. Pass 2 är det som väljer ur
    den, och bara pass 2 ger ett namn som `config/kategorier.yaml` kan hinka.
    """
    steg: list[Steg] = []

    kategori = ometikettera.ometikettera_en(
        klient,
        arende.text,
        taxonomi,
        ometikettera.bygg_system_pass2(taxonomi),
        amne=arende.amne,
        kanal=arende.kanal,
    )
    hink = _hink_for(kategori, hinkar)
    steg.append(Steg("klassificering", kategori, f"hink {hink}"))

    # **HINKEN `aldrig` GER INGET SVAR, OCH GENERATORN ANROPAS INTE.** Lars
    # beslut i skiva 49 DEL B. Raden står FÖRE uppslagssteget, alltså sparar den
    # både modellanropet och en möjlig begäran mot biluppgifter.se.
    #
    # Ingen av kategorierna i `aldrig` står i `A_TRAKTORKATEGORIER` i dag, så
    # uppslaget hade hoppats över ändå. Ordningen är ändå den här, eftersom den
    # inte ska bero på att de två listorna aldrig överlappar.
    #
    # *Stycket ovan gäller UPPSLAGET och skrevs i skiva 49, när nästa steg var
    # generering för alla kategorier. Sedan skiva 51 följer en andra grind
    # nedanför den här, och ordningen mellan de TVÅ grindarna avgör något helt
    # annat: vilket skäl som redovisas. Det står vid grinden.*
    if hink == "aldrig":
        steg.append(Steg("generering", "hoppades över", SKAL_ALDRIG))
        return Kedjeutfall(
            kategori=kategori, hink=hink, inget_svar=True,
            inget_svar_skal=SKAL_ALDRIG, steg=tuple(steg),
        )

    # **GRINDEN. KEDJAN SVARAR BARA PÅ A-TRAKTOR.** Lars beslut i skiva 51
    # DEL B. Allt annat är material för en fas som inte är påbörjad, och ett
    # utkast ingen bett om kostar ett modellanrop och en post i vyn som ingen
    # kan skicka: `auto` är tom, alltså kunde inget av de utkasten gå ut ändå.
    #
    # **RADEN STÅR EFTER `aldrig` OCH INTE FÖRE, och ordningen avgör något.**
    # Varje kategori i `aldrig` är i dag också ogatad, alltså träffar båda
    # villkoren samma ärende, och det som står först bestämmer vilket skäl som
    # redovisas i loggen, i summeringen och i vyn.
    #
    # Hinken går först därför att den är ramverksregel 1:s gräns och står kvar
    # när grinden vidgas: en kategori som Lars flyttar ur `aldrig` byter skäl,
    # medan en som ligger kvar där ska redovisas som `aldrig` också den dag fas 6
    # släpper fram den. `test_de_TVA_skalen_till_INGET_SVAR_HALLS_ISAR` fäller om
    # grenarna byter plats.
    #
    # Ordningen avgör alltså vilket skäl som redovisas, aldrig om svaret skrivs:
    # båda vägarna slutar i `INGET SVAR` och ingen av dem anropar generatorn.
    #
    # **KLASSNINGEN GÖRS ÄNDÅ**, och det är hela skillnaden mot att sålla bort
    # posten. Kategorin står i `logg/beslut.jsonl`, så att fas 6 har materialet
    # när nästa kategori tas. I vyn står den inte sedan skiva 61.
    if kategori not in A_TRAKTORKATEGORIER:
        steg.append(Steg("generering", "hoppades över", SKAL_OGATAD))
        return Kedjeutfall(
            kategori=kategori, hink=hink, inget_svar=True,
            inget_svar_skal=SKAL_OGATAD, steg=tuple(steg),
        )

    # HÄRIFRÅN ÄR KATEGORIN EN AV DE TRE, och grinden ovan är enda vägen förbi.
    # Grenen för en ogatad kategori är struken med den: den var oåtkomlig i samma
    # stund grinden byggdes, och en oåtkomlig gren går inte att fälla (§7.1).
    franvaro_far_pastas: frozenset[str] = frozenset()

    uppslag, utfall, uppslagssteg = _uppslagssteg(arende, hamta)
    steg.append(uppslagssteg)

    # **REDAN OMBYGGD GER INGET SVAR, OCH GENERATORN ANROPAS INTE.** Lars
    # beslut i skiva 63 DEL A: ett sådant ärende behöver inget svar, oavsett om
    # vi eller någon annan byggt om bilen. Samma väg som hinken `aldrig`.
    #
    # **BARA DET SKÄLET.** RÖTT av att fordonet inte duger som dragfordon går
    # vidare till generatorn: den kunden ska få ett svar. Prövningen är samma
    # funktion som gör utfallet RÖTT, `fordonsuppslag.utvardera` regel 1.
    if utfall is Utfall.ROTT and fordonsuppslag.ar_redan_ombyggd(uppslag):
        steg.append(Steg("generering", "hoppades över", SKAL_REDAN_OMBYGGD))
        return Kedjeutfall(
            kategori=kategori, hink=hink, uppslag=uppslag, utfall=utfall,
            inget_svar=True, inget_svar_skal=SKAL_REDAN_OMBYGGD,
            steg=tuple(steg),
        )

    # **ETT AVLÄST `Nej` ÄR DEN ENDA VÄGEN IN I MÄNGDEN.** Lars beslut i
    # skiva 41, VÄG TRE på lucka 50, se `docs/beslutslogg.md` #93.
    #
    # Ett fordon vars sida säger `Draganordning: Nej` har bevisligen ingen
    # registrerad draganordning: vi har LÄST ett värde som säger det. Att
    # spärra meningen *"bilen saknar registrerad draganordning"* hade
    # blockerat ett SANT besked, och det är den formulering promptens
    # regel 12 ber om.
    #
    # **EN FRÅNVARO ÄR ALDRIG ETT BELÄGG.** Skiva 40 lät ett saknat fält ge
    # samma rätt, med motiveringen att sidan bara renderar fält som har ett
    # värde. Det är sant om SIDAN och osant om vår läsning av den: ett mjukt
    # bindestreck i `Släpvagnsvikt` räcker för att fältet ska se saknat ut,
    # och det kräver ingen markupändring alls. Lucka 50 bär mätningen.
    if uppslag is not None and uppslag.draganordning is False:
        franvaro_far_pastas = frozenset({"draganordning"})

    forfragan = Forfragan(
        text=arende.text,
        kategori=kategori,
        utfall=utfall,
        uppslag=uppslag,
        # SANT UTAN VILLKOR SEDAN SKIVA 51: grinden ovan släpper bara fram de
        # tre kategorier uppslaget görs för. `uppslag_gjordes=False` når
        # generatorn bara via en direkt konstruerad `Forfragan`, alltså ur ett
        # test och inte ur kedjan.
        uppslag_gjordes=True,
        # SKIVA 46 DEL B. **SAMMA UTTRYCK SOM FÄLLER UPPSLAGET.**
        # `fordonsuppslag.slag_upp` kastar "registreringsnummer saknas" när just
        # `normalisera_regnr` ger tomt, alltså är det här villkoret inte en egen
        # tolkning av vad ett nummer är. Ett andra skrivsätt hade kunnat gå isär
        # med det första, och då hade prompten fått ett annat besked än spärren.
        regnr_i_mailet=bool(fordonsuppslag.normalisera_regnr(arende.regnr)),
        # SKIVA 41. Mängden kommer ur ett AVLÄST VÄRDE och ingenting annat.
        # Hoppades uppslaget över, eller misslyckades det, är den tom.
        franvaro_far_pastas=franvaro_far_pastas,
        efterslap=(nu is not None and not arende.besvarad
                   and ar_efterslapande(arende.tidsstampel, nu)),
    )

    try:
        utkast = generera.generera_utkast(klient, forfragan, exempel=exempel)
    except Sparrfalld as fel:
        steg.append(Steg("spärrar", "fälld", fel.sparr))
        return Kedjeutfall(
            kategori=kategori, hink=hink, uppslag=uppslag, utfall=utfall,
            sparr=fel.sparr, skal=fel.skal, sats=fel.sats, steg=tuple(steg),
        )

    # INGEN RÄKNING HÄR. Strängen `alla tre` stod här och skrevs in i
    # `logg/beslut.jsonl`, alltså blev ett räknat tal en falsk uppgift i
    # skugglägets eget underlag i samma stund en fjärde spärr tillkom. §7.2
    # förbjuder processräkningar av precis det skälet.
    steg.append(Steg("spärrar", "passerade"))
    steg.append(Steg("utkast", "skapat", f"{len(utkast)} tecken"))

    return Kedjeutfall(
        kategori=kategori, hink=hink, uppslag=uppslag, utfall=utfall,
        utkast=utkast, steg=tuple(steg),
    )


def _hink_for(etikett: str, hinkar: dict) -> str:
    """Kategorins hink, med standardhinken som förval.

    **EN KATEGORI I TVÅ HINKAR LARMAR, den väljs aldrig tyst.** Formen är lånad
    från `scripts/kategoristatus.py::hink_for`, som gör detsamma med
    motiveringen *"bättre att utfallet blev synligt än tyst"*. Första lydelsen
    här valde `auto` före `aldrig`, alltså valde en SÄNDVÄGSMODUL den mest
    tillåtande hinken tyst, medan ett mätverktyg larmade. Fällt av
    §7-granskningen av skiva 34, varv 1.

    `tests/test_kategorier_yaml.py` gör läget omöjligt i dag. Skulle den vakten
    falla ska det synas här och inte tolkas till kategorins fördel.
    """
    i_auto = etikett in (hinkar.get("auto") or [])
    i_aldrig = etikett in (hinkar.get("aldrig") or [])

    if i_auto and i_aldrig:
        raise ValueError(
            f"kategorin {etikett!r} står i BÅDE auto och aldrig i "
            "config/kategorier.yaml. Kedjan väljer inte åt Lars."
        )
    if i_auto:
        return "auto"
    if i_aldrig:
        return "aldrig"
    return hinkar.get("standardhink", "utkast")


# VAD HÄRKOMSTRADEN SÄGER OM VARJE DRAGVIKTSLÄGE. Skiva 40 DEL A.
#
# **`LAST` STÅR INTE HÄR**, eftersom ett läst fält inte ger ett misslyckat
# uppslag: den vägen når aldrig hit. `TOLKAS_EJ` är det enda av de tre som är
# VÅRT fel, och raden säger det rakt ut i stället för att kalla allt
# MISSLYCKADES.
_DRAGVIKTSTEXT = {
    biluppgifter.Dragviktslage.REGISTRET_SAKNAR.value:
        "REGISTRET BÄR INGEN DRAGVIKTSUPPGIFT för fordonet. Det är ett faktum "
        "om bilen och inte ett fel hos oss.",
    biluppgifter.Dragviktslage.ANNAN_FORM.value:
        "registret bär en dragviktsuppgift i en FORM VI INTE KAN BEDÖMA MOT, "
        "alltså obromsad vikt eller körkortsbehörighet men ingen bromsad "
        "släpvagnsvikt. Vi kan varken ge besked eller säga att uppgiften "
        "saknas.",
    biluppgifter.Dragviktslage.TOLKAS_EJ.value:
        "fältet STOD PÅ SIDAN och gick inte att läsa. Det är vårt fel och "
        "ingenting om bilen.",
}


def uppslagskalla(arende: Arende, utfall: Kedjeutfall, *, skarp: bool) -> str:
    """Vad som FAKTISKT hände med uppslaget för DEN HÄR posten.

    **RADEN LÄSES BREDVID ETT UTKAST SOM KAN INNEHÅLLA VIKTER**, och skillnaden
    mellan en avläst tjänstevikt och en konstruerad är inte synlig i texten.
    Skiva 35 satte en varning på hela vyn; den sade varken vilken post den gällde
    eller om uppslaget lyckats. Lars invändning i skiva 36 var att en post
    spärrades i stället för att slås upp, alltså är det just den skillnaden som
    ska stå här.

    `skarp` kommer från anroparen och inte från utfallet, eftersom utfallet ser
    likadant ut oavsett källa. Det är hela poängen med raden.
    """
    # **EN POST UTAN SVAR HAR INGEN HÄRKOMSTRAD ATT VISA.** Raden finns för att
    # säga vad vikterna i ett utkast är värda, och det finns inget utkast. Den
    # generella grenen nedan hade sagt *"Inget uppslag gjordes: kategorin gatar
    # det inte"*, vilket är sant men läses som ett besked om ett svar som
    # aldrig skrevs. Skiva 49.
    if utfall.inget_svar:
        return ""

    kalla = "biluppgifter.se" if skarp else "FIXTUR, konstruerad ur regnr"

    steg = {s.namn: s for s in utfall.steg}.get("uppslag")
    # **DEN HÄR GRENEN ÄR VILANDE SEDAN SKIVA 51 och nås inte ur `kor`.**
    # Grinden gör `INGET SVAR` av varje ogatad kategori, och grenen ovan
    # returnerar tomt för dem. Kvar går den att nå ur en direkt konstruerad
    # `Kedjeutfall`, alltså ur ett test. Den står kvar som funktionens kontrakt
    # för den indatan och är inte ett påstående om en väg kedjan tar.
    if steg is None or steg.utfall == "hoppades över":
        return "Inget uppslag gjordes: kategorin gatar det inte."

    if steg.utfall == "misslyckades":
        # SAMMA UTTRYCK SOM `Forfragan.regnr_i_mailet` OCH SOM `slag_upp`.
        # Raden sade tidigare `not arende.regnr`, alltså hade ett nummer som
        # bara bär blanktecken gett härkomstraden MISSLYCKADES medan prompten
        # sedan skiva 46 säger att mailet inte bär något nummer. Granskaren läser
        # de två bredvid varandra, och de ska inte kunna säga olika saker.
        if not fordonsuppslag.normalisera_regnr(arende.regnr):
            return (
                "Inget uppslag: MAILET BÄR INGET REGISTRERINGSNUMMER. "
                "Vikter i utkastet nedan saknar källa."
            )

        # **RADEN SÄGER VILKET LÄGE DET ÄR, inte bara att något misslyckades.**
        # Lars order i skiva 40. Tre lägen såg likadana ut här, och två av dem
        # är inte fel: att registret inte bär uppgiften är ett faktum om bilen,
        # inte om vår kod.
        lage = _DRAGVIKTSTEXT.get(steg.dragviktslage)
        if lage:
            return f"Uppslag mot {kalla}: {lage} Vikter i utkastet saknar källa."

        return (
            f"Uppslag mot {kalla} MISSLYCKADES ({steg.detalj}). "
            "Vikter i utkastet nedan saknar källa."
        )

    return f"Uppslag mot {kalla}: {steg.utfall}, utfall {steg.detalj}."


def till_granskningsfall(arende: Arende, utfall: Kedjeutfall,
                         *, skarp: bool) -> Granskningsfall:
    """Kedjans utfall som ett fall vyn kan visa. **VÄGENS SLUTPUNKT.**

    Utan den här funktionen slutade vägen i en `Kedjeutfall` som ingen kunde
    läsa: rutten `/granskning/N` fanns men hade ingen producent, alltså
    renderade den alltid *"Inga förslag"*. Fällt av §7-granskningen av skiva 34,
    varv 1.

    **HÖGST ETT AV `forslag` OCH `sparr` SÄTTS, och det är en egenskap hos
    `kor` och inte hos den här funktionen.** `kor`:s två normalvägar sätter
    antingen `utkast` eller `sparr`, aldrig båda.

    **INGETDERA VAR MÖJLIGT tills `tomt-svar` byggdes:** ett modellsvar som är
    tomt efter `.strip()` passerade varje spärr, och då blev `blev_utkast` sant
    medan `forslag` var tomt. Spärren stänger den vägen, se
    `docs/beslutslogg.md` #64. HÖGST och inte EXAKT står kvar ändå, eftersom
    garantin är `kor`:s och inte den här funktionens: en direkt konstruerad
    `Kedjeutfall` kan bära vad som helst.

    *Här stod att EXAKT ett av dem sätts, och sedan att `src/vy.py` skrivits om
    medan producentsidan stod kvar. Båda leden var fel: det var VYN som stod kvar
    med EXAKT, och meningen om att ett tomt svar passerar var i presens efter att
    samma varv hade byggt spärren som stoppar det. Fällt av §7-granskningen av
    skiva 34, varv 2 och varv 3.*

    Vad som däremot håller: en post med `sparr` satt får inget textfält av
    `rendera_granskning`, alltså går ett fällt förslag inte att omdöma.

    **`skarp` HAR INGET FÖRVAL, och det är samma skäl som `kor`:s `hamta`.** Ett
    förval hade PÅSTÅTT riktig fordonsdata för den som glömmer argumentet, alltså
    hade härkomstraden ljugit i den farliga riktningen: *"Uppslag mot
    biluppgifter.se"* ovanför vikter konstruerade ur ett registreringsnummer.
    Utan förval kastar Python i stället, och det syns. Fällt av §7-granskningen
    av skiva 36, varv 1.
    """
    return Granskningsfall(
        fall=Fall(
            etikett=utfall.kategori,
            kalla="kedjan",
            text=arende.text,
            tidsstampel=arende.tidsstampel,
            avsandare_hash=arende.avsandare_hash,
        ),
        forslag=utfall.utkast or "",
        sparr=utfall.sparr or "",
        inget_svar=utfall.inget_svar,
        # `inget_svar_skal` bär en av modulens FASTA `SKAL_*`-strängar och går rakt
        # in på sidan. `sparrskal` och `sparrsats` bär text lyft ur modellens
        # svar och MASKERAS av `vy.rendera_granskning` innan de renderas.
        #
        # *Här stod att bara `inget_svar_skal` får nå disken och sidan. Det var
        # sant till skiva 56, där Lars beslutade att spärrskälet ska synas i
        # vyn, maskerat: utan det såg Lars ATT ett svar fälldes men aldrig VAD
        # som fällde, och skiva 55:s `talet 113` gick inte att spåra.*
        inget_svar_skal=utfall.inget_svar_skal,
        # **RÅ HÄR, MASKERAD I VYN.** `data/granskningsfall.jsonl` är
        # gitignorerad och bär redan rå kundtext och råa utkast, alltså är det
        # inte filen som är gränsen. Gränsen är skärmen, och den ligger i
        # `vy.rendera_granskning`, som maskerar varje väg in: kedjans,
        # den sparade filens, och en direkt konstruerad post.
        sparrskal=utfall.skal,
        sparrsats=utfall.sats,
        uppslagskalla=uppslagskalla(arende, utfall, skarp=skarp),
    )


# ------------------------------------------------------------------ DEL C


def logga_beslut(
    arende: Arende,
    utfall: Kedjeutfall,
    *,
    loggfil: Path = BESLUTSLOGG,
) -> dict:
    """En rad per ärende som passerat kedjan. APPEND-ONLY, §0 ramverksregel 4.

    **DET HÄR ÄR UNDERLAGET FÖR SKUGGLÄGET**, och `docs/roadmap.md` säger att
    det ska finnas INNAN skuggläget börjar. Raden bär det Lars namngav i skiva
    34: kategorin, uppslagets utfall, vilka spärrar som fällde, och om det blev
    ett utkast eller föll ur.

    **§6: INGEN PERSONDATA, och det ledet är fällt fram.** Raden bär
    `avsandare_hash` och aldrig en adress, och den bär ALDRIG utkastets text.
    Utkastet innehåller kundens namn och bilmodell, och en logg som bär det blir
    en persondatafil som lever kvar.

    **`skal` LOGGAS INTE, och det är skälet till att fältet saknas.** Första
    lydelsen skrev `Sparrfalld.skal`, som byggs av strängar lyfta ORDAGRANT ur
    modellens svar. Skriver boten ut ett telefonnummer lyder skälet *"talet …
    kommer varken ur uppslaget eller ur config"* med numret inbakat, och
    `genererat-fordonsfaktum` bär på samma sätt ett ord ur utkastet. Det hade
    redan hänt i den befintliga loggen när granskningen mätte den. Fällt av
    §7-granskningen av skiva 34, varv 1.

    Det maskinläsbara som skuggläget behöver är VILKEN spärr som fällde, och det
    står i `sparr`. Detaljen hör hemma där utkastet läses, alltså i vyn.

    **FILEN ÖPPNAS BARA I `a`-LÄGE.** Ramverksregel 4 är obrytbar, och
    `test_beslutsloggen_ar_APPEND_ONLY` binder att en andra skrivning inte
    raderar den första.
    """
    krav_pa_skrivbar_sokvag(loggfil)

    post = {
        "skrivet": datetime.now(timezone.utc).isoformat(),
        "avsandare_hash": arende.avsandare_hash,
        "tidsstampel": arende.tidsstampel,
        "kategori": utfall.kategori,
        "hink": utfall.hink,
        "uppslag": utfall.utfall.value if utfall.utfall is not None else None,
        "sparr": utfall.sparr,
        "blev_utkast": utfall.blev_utkast,
        # SKIVA 49. **UTAN FÄLTET GÅR DE TVÅ ICKE-UTKASTEN INTE ATT SKILJA ÅT I
        # LOGGEN.** `blev_utkast: false` med `sparr: null` betydde förut ingenting
        # alls, och betyder nu antingen ett källfel eller ett INGET SVAR.
        # Skuggläget ska kunna räkna maskinmailen för sig.
        "inget_svar": utfall.inget_svar,
        "utkast_tecken": len(utfall.utkast) if utfall.utkast else 0,
        "steg": [{"namn": s.namn, "utfall": s.utfall, "detalj": s.detalj}
                 for s in utfall.steg],
    }

    return _skriv(post, loggfil)


def logga_kallfel(
    arende: Arende,
    fel: Kallfel,
    *,
    loggfil: Path = BESLUTSLOGG,
) -> dict:
    """En rad för ett ärende som STOPPADES av ett källfel.

    **ETT DRIFTAVBROTT SOM INTE LOGGAS SER UT SOM ETT ÄRENDE SOM ALDRIG KOM
    IN.** `kor` kastar `Kallfel` och anroparen hoppade vidare, alltså lämnade
    ett nere-liggande biluppgifter.se INGEN rad alls. Skuggläget ska kunna mäta
    hur ofta källan svek, och den skillnaden är exakt vad `Kallfel` byggdes för
    att bevara: ett felläst fält är inte ett saknat fordon.

    Fällt av §7-granskningen av skiva 34, varv 2, som också fällde att modulens
    flödesskiss påstod en rad *oavsett utfall* medan just det här utfallet inte
    fick någon.

    `fel` bär ett undantagsnamn och ett meddelande ur `src/fordonsuppslag.py`,
    alltså fasta strängar och fältnamn. Ingen kundtext, se `logga_beslut`.
    """
    krav_pa_skrivbar_sokvag(loggfil)

    return _skriv(
        {
            "skrivet": datetime.now(timezone.utc).isoformat(),
            "avsandare_hash": arende.avsandare_hash,
            "tidsstampel": arende.tidsstampel,
            "kategori": None,
            "hink": None,
            "uppslag": None,
            "sparr": None,
            "blev_utkast": False,
            # FALSKT OCH INTE UTELÄMNAT: ett källfel är inte ett INGET SVAR.
            # Kedjan hann aldrig fram till hinken, och en saknad nyckel hade
            # tvingat den som räknar loggen att gissa vilket av de två det var.
            "inget_svar": False,
            "utkast_tecken": 0,
            # `fel.sort` OCH ALDRIG `str(fel)`: meddelandet byggs av anroparens
            # hämtfunktion och bär ett registreringsnummer när requests kastar.
            # Se `Kallfel`.
            "steg": [{"namn": "källa", "utfall": "stoppade kedjan",
                      "detalj": fel.sort}],
        },
        loggfil,
    )


def _skriv(post: dict, loggfil: Path) -> dict:
    """APPEND-ONLY. `a`-läget är ramverksregel 4 och står bara här."""
    loggfil.parent.mkdir(parents=True, exist_ok=True)
    with loggfil.open("a", encoding="utf-8") as fil:
        fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    return post
