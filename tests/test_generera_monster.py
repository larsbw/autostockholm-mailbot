"""REGRESSIONSTABELLEN för generatorns spärrmönster. SÄNDVÄG.

**VARFÖR FILEN FINNS.** Skiva 31 ändrade `TROSKELTAL` och `FORFATTNINGSORD` i
två av sina tre granskningsvarv, och BÅDA gångerna införde rättelsen ett nytt
fel i motsatt riktning:

  varv 1  ordgräns i båda ändar missade `Kravet`  ->  tog bort ordgränsen HELT
  varv 2  ingen ordgräns fällde `lager`, `underlag`  ->  tappade `regler`

*Här stod att skiva 31 ändrade fem mönster i tre varv. `git diff 086cd93
4956c35 -- src/generera.py` visar att varv 3 ändrade ENBART en kommentar, och
commit-meddelandet säger det själv: "INGEN regex rörd". Fällt av
§7-granskningen av skiva 32, varv 1.*

Lars ordning i skiva 32: **en tabell över varje form som någon lydelse någonsin
fångat, körd i sin helhet efter varje ändring. Ett mönster som fångar en ny form
men tappar en gammal är inte en rättelse.**

Tabellen är därför HISTORISK och inte en lista över vad dagens mönster råkar
klara. Varje rad bär den skiva och det varv den kommer ur, så att nästa läsare
ser att raden är en gammal fångst och inte ett hittepå.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext (§6). Inget test här rör nätet.
"""

from __future__ import annotations

import re

import pytest

from src import generera
from src.fordonsuppslag import Uppslag, Utfall
from src.generera import Forfragan, Sparrfalld

# GRÄNSBILEN. Släpvagnsvikten är exakt 1000, alltså HAR talet en källa och
# talspärren fäller INTE först. Utan det prövar tröskelraderna fel spärr, vilket
# hände i skiva 31 varv 1 innan någon märkte det.
GRANSBIL = Forfragan(
    text="x",
    kategori="fråga om a-traktorkonvertering",
    utfall=Utfall.GRONT,
    uppslag=Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1000, draganordning=True),
)

# Ett vanligt uppslag, för fordonsfakta som får nämnas.
MED_UPPSLAG = Forfragan(
    text="x",
    kategori="fråga om a-traktorkonvertering",
    utfall=Utfall.GRONT,
    uppslag=Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1500, draganordning=True),
)

UTAN_UPPSLAG = Forfragan(
    text="x",
    kategori="fråga om a-traktorkonvertering",
    utfall=Utfall.OKLART,
    uppslag=None,
)


# ---------------------------------------------------------------- TRÖSKELN
#
# Varje form någon lydelse av `TROSKELTAL` och `FORFATTNINGSORD` har fångat.
# Kolumnen "ur" säger var raden kommer ifrån.

TROSKEL_SKA_FALLA = [
    # skiva 31, byggd i DEL C
    ("Lagen kräver att bilen är byggd för minst 1 000 kg släpvagnsvikt.", GRANSBIL),
    # skiva 31, varv 1: böjda författningsord
    ("Kravet är 1 000 kg.", GRANSBIL),
    ("Föreskriften säger 1 000 kg.", GRANSBIL),
    ("Lagkravet är 1 000 kg.", GRANSBIL),
    ("Paragrafen anger 1 000 kg.", GRANSBIL),
    ("Bestämmelsen säger 1 000 kg.", GRANSBIL),
    ("Bilen måste vara byggd för minst ett ton.", UTAN_UPPSLAG),
    ("Det finns ett krav på tusen kilo.", UTAN_UPPSLAG),
    # skiva 31, varv 2: tröskeln ihopskriven och i ord
    ("Lagen kräver 1000kg.", GRANSBIL),
    ("Kravet är ettusen kilo.", UTAN_UPPSLAG),
    ("Kravet är tusen kg.", GRANSBIL),
    ("Lagen kräver minst 1 ton.", UTAN_UPPSLAG),
    ("Kravet är 1 000kg.", GRANSBIL),
    ("Lagen kräver 1000 kilogram.", GRANSBIL),
    ("Kravet är 1.000 kg.", GRANSBIL),
    ("Lagen kräver ETTUSEN kilo.", UTAN_UPPSLAG),
    ("Kravet är ett tusen kilo.", UTAN_UPPSLAG),
    ("Lagen kräver 1000 kilo.", GRANSBIL),
    # skiva 31, varv 3, LUCKA 27: fångades av varv 1 och tappades i varv 2
    ("Det finns regler om 1 000 kg släpvagnsvikt.", GRANSBIL),
    ("Regleringen säger 1 000 kg.", GRANSBIL),
    ("Trafikreglerna säger 1 000 kg.", GRANSBIL),
    ("Det är ett myndighetskrav på 1 000 kg.", GRANSBIL),
    # skiva 32, varv 1: FORMER SOM VARV 1:s COMMITTADE LYDELSE FÅNGADE och som
    # skivans första försök TAPPADE. `git show 927543d:src/generera.py` bar
    # `krav|kräv|lag|regel|regl|föreskrift|bestämmels|paragraf` HELT utan
    # ordgränser, alltså fångades varje sammansättning.
    #
    # Skivan namngav egenskapen rätt, "ett författningsord kan vara ANDRA ledet
    # i en sammansättning", och tillämpade den sedan på TVÅ av sju led. Det är
    # samma fel som lucka 27, en ordstam längre bort, och det är precis vad den
    # här tabellen finns för att fånga.
    ("Trafikföreskriften säger 1 000 kg.", GRANSBIL),
    ("Trafikbestämmelserna säger 1 000 kg.", GRANSBIL),
    ("Lagtexten säger 1 000 kg.", GRANSBIL),
    ("Lagarna säger 1 000 kg.", GRANSBIL),
    ("Reglementet säger 1 000 kg.", GRANSBIL),
    ("Lagparagrafen anger 1 000 kg.", GRANSBIL),
    ("Vägtrafiklagstiftningen säger 1 000 kg.", GRANSBIL),
    # skiva 32, varv 2: ISOLERANDE RADER, en per författningsterm som saknade en.
    #
    # Driftvakten, som i skiva 33 heter `test_varje_term_ar_ISOLERAD` och då
    # gällde alla fyra mönstren, mätte att TOLV av
    # tjugotvå termer inte hade någon rad där de var ensamma om att matcha.
    # Bland dem `\bkräv\w*` och `regeln\b`, alltså exakt de två som varv 2:s
    # omskrivning TAPPADE utan att sviten blev röd.
    #
    # Raderna bär därför MEDVETET inget andra författningsord. Skriv aldrig
    # "Lagen kräver ..." här: den raden isolerar ingenting.
    ("Det krävs 1 000 kg släpvagnsvikt.", GRANSBIL),
    ("Foreskriften anger 1 000 kg.", GRANSBIL),
    ("Bestammelsen anger 1 000 kg.", GRANSBIL),
    ("En regel om 1 000 kg finns.", GRANSBIL),
    ("Regeln om 1 000 kg gäller.", GRANSBIL),
    ("En lag om 1 000 kg finns.", GRANSBIL),
    ("Lagen om 1 000 kg gäller.", GRANSBIL),
    ("VVFS anger 1 000 kg.", GRANSBIL),
    ("§ anger 1 000 kg.", GRANSBIL),
    ("Bilen maste klara 1 000 kg.", GRANSBIL),
    ("Trafikverket anger 1 000 kg.", GRANSBIL),
    ("Transportstyrelsen anger 1 000 kg.", GRANSBIL),
    # skiva 33: `reglers` fick sin isolerande rad när `regler`-termens fyra
    # böjningar delades upp i egna termer. Grenen var lucka 34, alltså ett
    # lager som gick att ta bort med hela sviten grön.
    ("Dessa reglers innebörd är 1 000 kg.", GRANSBIL),
    # skiva 33, varv 1: RADER SOM UTNYTTJAR `\w*` MED OLIKA SUFFIX.
    #
    # Ett `\w*` är en gren som alternationsförbudet inte når: den kan matcha
    # tomt eller en böjning, och utan två OLIKA träffar går suffixdelen att
    # snäva bort med grön svit. Raderna nedan finns bara för att ge varje sådan
    # term en andra, annorlunda träff.
    #
    # **En prefixsammansättning duger INTE**, eftersom termen saknar
    # vänsterankare: `föreskrift\w*` träffar samma sträng i "Föreskriften" som i
    # "Trafikföreskriften". Skillnaden måste ligga i SUFFIXET.
    ("Det kräver 1 000 kg släpvagnsvikt.", GRANSBIL),
    ("Föreskrifter anger 1 000 kg.", GRANSBIL),
    ("Foreskrifter anger 1 000 kg.", GRANSBIL),
    ("Bestammelser anger 1 000 kg.", GRANSBIL),
    ("Paragrafer anger 1 000 kg.", GRANSBIL),
    ("Lagstiftning anger 1 000 kg.", GRANSBIL),
    ("Reglementen säger 1 000 kg.", GRANSBIL),
    ("Reglering anger 1 000 kg.", GRANSBIL),
    ("Lagtext anger 1 000 kg.", GRANSBIL),
    # skiva 33, varv 2: RADER MED DEN NAKNA STAMMEN.
    #
    # `föreskrift`, `foreskrift` och `paragraf` är ord på egen hand, alltså är
    # den tomma böjningen i `\w*` en gren som måste prövas. Utan de här raderna
    # gick termerna att snäva till `\w+` med hela sviten grön, och då tappades
    # just grundformen.
    ("Denna föreskrift anger 1 000 kg.", GRANSBIL),
    ("Denna foreskrift anger 1 000 kg.", GRANSBIL),
    ("Denna paragraf anger 1 000 kg.", GRANSBIL),
    # `kräv` är imperativ av `kräva`, alltså ett ord på egen hand. En tidigare
    # lydelse skärpte termen till `\w+` med motiveringen att stammen inte är ett
    # ord, och tappade då den här formen.
    ("Kräv 1 000 kg av bilen.", GRANSBIL),
    # skiva 34, LUCKA 32: HÖGERGRÄNSEN. Nio former som repots första lydelse
    # (`927543d`) fångade och som föll bort när VÄNSTERgränsen rättades. Samma
    # egenskap, andra änden av ordet.
    #
    # Raderna bär MEDVETET inget andra författningsord, så att var och en
    # isolerar sin term.
    ("Regelverket säger 1 000 kg.", GRANSBIL),
    ("Transportstyrelsens gräns är 1 000 kg.", GRANSBIL),
    ("Trafikverkets besked är 1 000 kg.", GRANSBIL),
    ("Enligt lagens ordalydelse gäller 1 000 kg.", GRANSBIL),
    ("Det är lagstadgat med 1 000 kg.", GRANSBIL),
    ("Det är inte lagligt under 1 000 kg.", GRANSBIL),
    ("Det är påkrävt med 1 000 kg.", GRANSBIL),
    ("VVFS2003 anger 1 000 kg.", GRANSBIL),
    ("Dessa reglernas innebörd är 1 000 kg.", GRANSBIL),
    # Naken stam för de två termer vars grundform ÄR ett ord. Utan dem går
    # `\w*` att snäva till `\w+` med grön svit, och då tappas just grundformen.
    ("Bilen är laglig vid 1 000 kg.", GRANSBIL),
    ("Ett regelverk anger 1 000 kg.", GRANSBIL),
    # skiva 34, varv 1: FORMER SOM LÄCKTE TROTS ATT LUCKA 32 SADES VARA STÄNGD.
    #
    # Egenskapen var namngiven rätt i tre kommentarer och tillämpad bara på de
    # nio former fyndet räknade upp. `laglig` och `lagstadga` beskrevs som
    # entydiga men skrevs med vänstergräns, och genitiven lades till för `lagen`
    # och `reglerna` men inte för `regeln` och `lagarna`.
    ("Det är olagligt att dra 1 000 kg.", GRANSBIL),
    ("Olagliga ombyggnader ger 1 000 kg.", GRANSBIL),
    ("Lagarnas innebörd är 1 000 kg.", GRANSBIL),
    ("Regelns innebörd är 1 000 kg.", GRANSBIL),
    # skiva 34, VARV 2: fyra av sex former till, alla av samma klass som varv 1
    # fällde. Stammen är andra ledet i en sammansättning, alltså måste
    # vänstergränsen falla. Vilka stammar som TÅL det är mätt med
    # `scripts/stamprov.py` och inte antaget.
    #
    # **DE TVÅ ÅTERSTÅENDE STÅR I `TROSKEL_LUCKA_39` och inte här**, eftersom de
    # inte gick att uttrycka som en term. Se noten där.
    ("Det är lagenligt vid 1 000 kg.", GRANSBIL),
    ("Lagstiftaren anger 1 000 kg.", GRANSBIL),
    ("Lagändringen anger 1 000 kg.", GRANSBIL),
    ("Lagrummet anger 1 000 kg.", GRANSBIL),
    # De NAKNA formerna. `test_en_SNAVAD_term_tappar_en_rad` fällde att
    # nollängdsdelen i varje `\w*` var oprövad, alltså gick termen att snäva
    # till `\w+` utan att någon rad slutade matcha. Alla tre är verkliga
    # svenska ordformer, så lagret ska finnas OCH prövas.
    ("Ett lagrum anger 1 000 kg.", GRANSBIL),
    ("Lagändring anger 1 000 kg.", GRANSBIL),
    ("Ombyggnaden är lagenlig vid 1 000 kg.", GRANSBIL),
    # skiva 34, LUCKA 33: MASSENHETENS BÖJNINGAR. Fem former som `kilo\w*`
    # fångade och som föll bort när enheten snävades för att inte fälla
    # `kilometer`.
    ("Kravet är tusen kilos.", UTAN_UPPSLAG),
    ("Kravet är tusen kilot.", UTAN_UPPSLAG),
    ("Kravet är tusen kilona.", UTAN_UPPSLAG),
    ("Kravet är tusen kilogrammen.", UTAN_UPPSLAG),
    ("Kravet är tusen kilogrammet.", UTAN_UPPSLAG),
    ("Kravet är tusentals kilogram.", UTAN_UPPSLAG),
    ("Kravet är tusentals kilon.", UTAN_UPPSLAG),
    ("Kravet är tusentals kg.", GRANSBIL),
    ("Kravet är 1ton.", GRANSBIL),
    # skiva 31, varv 3, LUCKA 26: enheten utskriven
    ("Kravet är tusen kilogram.", UTAN_UPPSLAG),
    ("Lagen kräver ett tusen kilogram.", UTAN_UPPSLAG),
    ("Kravet är tusen kilon.", UTAN_UPPSLAG),
    ("Kravet är tusentalet kilo.", UTAN_UPPSLAG),
    ("Lagen kräver tusentals kilo.", UTAN_UPPSLAG),
]

TROSKEL_SKA_PASSERA = [
    # skiva 31, DEL C: talet ensamt är ett avläst värde, inte en föreskrift
    ("Bilen är godkänd för 1 000 kg släp.", GRANSBIL),
    # skiva 31, varv 2: önskade svar som varv 1:s lydelse fällde
    ("Bilen är godkänd för 1 000 kg släp, och vi har delarna på lager.", GRANSBIL),
    ("Enligt uppslaget är bilen godkänd för 1 000 kg släpvagnsvikt.", GRANSBIL),
    ("Vi har lagt in bilen för 1 000 kg.", GRANSBIL),
    ("Bilen klarar 1 000 kg enligt uppgifterna du gav oss.", GRANSBIL),
    # skiva 31, varv 3: vanliga ord som inte får ge träff
    ("Vi har lagom med tid för 1 000 kg.", GRANSBIL),
    ("Underlaget visar 1 000 kg.", GRANSBIL),
    ("Vi ser regelbundet bilar på 1 000 kg.", GRANSBIL),
    # skiva 32, varv 1: VERKSTADSORD SOM DELAR STAM MED ETT FÖRFATTNINGSORD.
    #
    # `regler` utan vänsterordgräns fällde *"dragkroken är reglerbar"*, alltså
    # en ny falsk positiv som skivans FÖRSTA lydelse införde. Verbet `reglera`
    # och substantivet `regler` delar sträng, och verbet är ett vanligt
    # verkstadsord: termostaten reglerar, tomgången regleras.
    #
    # `lagar` är samma fälla för `lag`: en verkstad LAGAR bilar. Därför fångas
    # bara `lagarna`, aldrig `lagar`.
    ("Dragkroken är reglerbar och bilen klarar 1 000 kg.", GRANSBIL),
    ("Termostaten reglerar temperaturen, och bilen klarar 1 000 kg.", GRANSBIL),
    ("Tomgången regleras när vi lastar 1 000 kg.", GRANSBIL),
    ("Vi reglerade ventilspelet på bilen som drar 1 000 kg.", GRANSBIL),
    ("Vi lagar bilen som är godkänd för 1 000 kg.", GRANSBIL),
    ("Vi har lagat en bil för 1 000 kg i veckan.", GRANSBIL),
    # skiva 32, varv 2: FALSKA POSITIVA SOM VARV 1:s RÄTTELSE INFÖRDE.
    #
    # `regler(?!a|bar)\w*` fångade `reglerventilen` och `reglerskruven`, alltså
    # sammansättningar där `regler` är FÖRSTA ledet. `kilo\w*` fångade
    # `kilometer`, alltså en längdenhet i en spärr som gäller vikt.
    ("Reglerventilen sitter på bilen som klarar 1 000 kg.", GRANSBIL),
    ("Reglerskruven är justerad på bilen som drar 1 000 kg.", GRANSBIL),
    ("Bilen har gått tusentals kilometer och klarar 1 000 kg.", GRANSBIL),
]


# TRÖSKELFORMER SOM NUMERA FÄLLS AV EN ANNAN SPÄRR.
#
# `krav_pa_svaret` prövar talspärren FÖRST, och `TAL_I_ORD` fäller varje tal
# skrivet i ord. Formerna nedan når därför aldrig tröskelspärren. Att de faller
# är oförändrat; VEM som fäller dem är det inte.
#
# **RADERNA STÅR HÄR I STÄLLET FÖR ATT TIGAS IHJÄL.** Ett test som bara
# asserterar `Sparrfalld` säger inte vilken spärr det prövar, och en rad som
# tyst byter spärr slutar vakta det den påstår sig vakta utan att bli röd. Det
# är fyndet `docs/sparrar.md` beskriver under ORDNINGEN AVGÖR VILKEN SPÄRR SOM
# RAPPORTERAS, återinfört av skiva 32 och funnet av dess granskning, varv 1.
# Exakt de fyra formerna bär ett RÄKNEORD före `tusen`, alltså `ett`. `tusen
# kilo` och `tusentals kilo` saknar multiplikator och passerar `TAL_I_ORD`, så
# de når tröskelspärren. Uppdelningen är AVLÄST ur en körning och inte gissad:
# en första lydelse här gissade fel, och sviten fällde de rader som gissats fel.
FALLER_PA_TALSPARREN = {
    "Kravet är ettusen kilo.",
    "Lagen kräver ETTUSEN kilo.",
    "Kravet är ett tusen kilo.",
    "Lagen kräver ett tusen kilogram.",
    # `VVFS2003` bär ett ÅRTAL, och årtalet har ingen källa. Talspärren fäller
    # därför raden innan tröskelspärren nås, och raden ska säga det.
    #
    # **RADEN BINDER INTE `\w*` PÅ `vvfs`, och det ska inte påstås.** Eftersom
    # talspärren fäller oavsett vad `FORFATTNINGSORD` innehåller går termen att
    # snäva tillbaka till `\bvvfs\b` med hela sviten grön, mätt. Det är en
    # instans av lucka 38: vakterna når termer och optionalitet, inte
    # ordgränser. Fällt av §7-granskningen av skiva 34, varv 1.
    "VVFS2003 anger 1 000 kg.",
}


@pytest.mark.parametrize("svar, fall", TROSKEL_SKA_FALLA)
def test_troskelformer_som_ska_falla(svar, fall):
    """Varje form någon lydelse har fångat ska fortsätta falla.

    Prövar också VILKEN spärr som fäller, så att en rad inte tyst byter vaktare.
    """
    with pytest.raises(Sparrfalld) as fangad:
        generera.krav_pa_svaret(svar, fall)

    vantad = (
        "genererat-tal-har-kalla"
        if svar in FALLER_PA_TALSPARREN
        else "troskeln-som-forfattningstext"
    )
    assert fangad.value.sparr == vantad, (
        f"{svar!r} fälldes av {fangad.value.sparr}, inte av {vantad}"
    )


# LUCKA 39: sammansättningar med `lag`, i BÅDA leden. En ÖPPEN och MÄTT lucka,
# inte en glömd. Skiva 34:s DEL A säger att en form som inte går att uttrycka
# som en term i termtupeln lämnas öppen och mätt, och att inget särfall byggs.
#
# **`lag` ÄR GENUINT TVETYDIGT I BÅDA RIKTNINGARNA.** `lagen\b` utan
# vänstergräns fäller `uppslagen`, `förslagen`, `avslagen`, `beslagen` och
# `utslagen`, och `uppslagen` är vad kedjan GÖR. `\blag\w*` utan högergräns
# fäller `lagar`, `lager`, `lagt` och `lagning`. Varje lydelse som når klassen
# når också verkstadens egna ord.
#
# **UPPRÄKNINGEN NEDAN ÄR DE MÄTTA FORMERNA, ALDRIG GRÄNSEN.** Att lista dem är
# vad som gör luckan synlig, inte vad som definierar den. Se `docs/sparrar.md`.
#
# **RADERNA ÄR `xfail(strict=True)` OCH INTE STRUKNA.** Det är samma val som
# lucka 24:s rad ovan: en struken rad är en glömd lucka, medan en strikt xfail
# blir RÖD den dag någon stänger luckan och därmed tvingar fram att noten skrivs
# om. En kommentar hade inte gjort det.
#
# *Här stod två former och att klassen är sammansättningar vars ANDRA led är
# `lagen`. Klassen bär minst fyra former i FÖRSTA ledet och två böjningsformer
# till. Fällt av §7-granskningen av skiva 34, varv 3.*
TROSKEL_LUCKA_39 = [
    pytest.param(
        svar,
        GRANSBIL,
        marks=pytest.mark.xfail(strict=True, reason=f"lucka 39, {klass}"),
    )
    for svar, klass in [
        ("Vägtrafiklagen anger 1 000 kg.", "lag som andra led"),
        ("Trafiklagen anger 1 000 kg.", "lag som andra led"),
        ("Fordonslagen anger 1 000 kg.", "lag som andra led"),
        ("Körkortslagen anger 1 000 kg.", "lag som andra led"),
        ("Lagboken anger 1 000 kg.", "lag som första led"),
        ("Lagförslaget anger 1 000 kg.", "lag som första led"),
        ("Lagrådet anger 1 000 kg.", "lag som första led"),
        ("Lagsamlingen anger 1 000 kg.", "lag som första led"),
        ("Det är reglerat till 1 000 kg.", "böjning utanför vitlistan"),
        ("Det är ett måsten med 1 000 kg.", "böjning utanför vitlistan"),
    ]
]


@pytest.mark.parametrize("svar, fall", TROSKEL_LUCKA_39)
def test_lucka_39_ar_OPPEN_och_MATT(svar, fall):
    """Formen SKA falla och gör det inte. Luckan är mätt, inte glömd."""
    with pytest.raises(Sparrfalld):
        generera.krav_pa_svaret(svar, fall)


@pytest.mark.parametrize("svar, fall", TROSKEL_SKA_PASSERA)
def test_troskelformer_som_ska_passera(svar, fall):
    """En spärr som fäller önskade svar blir avstängd, §7.1."""
    generera.krav_pa_svaret(svar, fall)


# ------------------------------------------------------------------- PRIS

PRIS_SKA_FALLA = [
    ("Ombyggnaden kostar 25 000 kr.", UTAN_UPPSLAG),
    ("Vad det kostar återkommer vi om.", UTAN_UPPSLAG),
    ("Det blir 25 000:- rakt av.", UTAN_UPPSLAG),
    ("Vi kan ge dig en offert.", UTAN_UPPSLAG),
    # skiva 31, varv 1
    ("Det går på femton hundra spänn.", UTAN_UPPSLAG),
    ("Vi gör det för en billig peng.", UTAN_UPPSLAG),
    ("Det brukar hamna runt 25tkr.", UTAN_UPPSLAG),
    # skiva 31, varv 2: talet ihopskrivet med enheten
    ("Vi tar 25000kr för jobbet.", UTAN_UPPSLAG),
    ("Det blir 1500kr, betala på plats.", UTAN_UPPSLAG),
    # skiva 32, varv 1: PRISORDEN UTAN SIFFRA INTILL.
    #
    # `tkr` och `spänn` hade bara rader där ett tal stod bredvid, alltså bar
    # `TAL_I_TEXT` respektive `TAL_I_ORD` fällningen och prisorden var
    # SKUGGADE: `\btkr\b|\d\s*tkr` gick att radera med hela sviten grön, mätt.
    # Ett lager som ingen rad prövar ensamt är ett otestat lager.
    # Fällt av §7-granskningen av skiva 32, varv 1.
    ("Vi tar några tkr för jobbet.", UTAN_UPPSLAG),
    ("Vi tar några spänn för det.", UTAN_UPPSLAG),
    # skiva 33: ISOLERANDE RADER, en per pristerm som saknade en.
    #
    # Driftvakten mätte att tretton av nitton prisord inte hade någon rad där de
    # var ensamma om att matcha. `kr` är mönstrets centralaste term och var
    # skuggad av `kostar` och av `TAL_I_TEXT` i varje rad som bar den. Det var
    # lucka 31.
    #
    # Raderna bär därför MEDVETET inget andra prisord och ingen siffra.
    ("Vi tar några kr.", UTAN_UPPSLAG),
    ("Vi tar några kronor.", UTAN_UPPSLAG),
    ("Vi tar några sek.", UTAN_UPPSLAG),
    ("Det tillkommer en kostnad.", UTAN_UPPSLAG),
    ("Vi tar kostnaden.", UTAN_UPPSLAG),
    ("Vi sätter ett pris.", UTAN_UPPSLAG),
    ("Vi tar priset.", UTAN_UPPSLAG),
    ("Vi har olika priser.", UTAN_UPPSLAG),
    ("Det tillkommer en avgift.", UTAN_UPPSLAG),
    ("Vi tar nagra spann.", UTAN_UPPSLAG),
    ("Vi tar pengar.", UTAN_UPPSLAG),
    ("Det är inkl. moms.", UTAN_UPPSLAG),
    ("Det är exkl. moms.", UTAN_UPPSLAG),
    # skiva 33, varv 1: RADER SOM UTNYTTJAR DEN VALFRIA DELEN OLIKA.
    #
    # `\binkl\.?\s*moms\b` gick att snäva till `\binkl\.\s*moms\b` med grön
    # svit, alltså var punktens valfrihet ett otestat lager. Samma för `\d\s*tkr`,
    # där den enda raden bar "25tkr".
    ("Det är inkl moms.", UTAN_UPPSLAG),
    ("Det är exkl moms.", UTAN_UPPSLAG),
    # `\s*` tillåter noll blanksteg, och den grenen prövas av raderna nedan.
    # Vakten snävar inte `\s*` själv, se dess kommentar, alltså är de här
    # raderna det enda som gör `inkl.moms` prövad.
    ("Det är inkl.moms.", UTAN_UPPSLAG),
    ("Det är exkl.moms.", UTAN_UPPSLAG),
    ("Det blir 9tkr.", UTAN_UPPSLAG),
    # skiva 33, varv 1: RADEN SOM GÖR `\d\s*tkr` LASTBÄRANDE.
    #
    # Varje annan tkr-rad bär en siffra UTAN källa, alltså fälls den av
    # `TAL_I_TEXT` även om prisordet tas bort. Med GRÄNSBILEN har 1400 en källa,
    # så prisordet är det enda som kan fälla. Utan raden gick `\d\s*tkr` att
    # radera med hela sviten grön.
    ("Det blir 1400tkr.", GRANSBIL),
]

PRIS_SKA_PASSERA = [
    # skiva 31, varv 1: den lydelse som fällde varje BRA svar
    ("En kollega återkommer med prisuppgift.", UTAN_UPPSLAG),
    ("Vi tittar totalt igenom bilen.", UTAN_UPPSLAG),
    ("Summa summarum går det bra.", UTAN_UPPSLAG),
    ("Hör av dig så bokar vi tid.", UTAN_UPPSLAG),
]


@pytest.mark.parametrize("svar, fall", PRIS_SKA_FALLA)
def test_prisformer_som_ska_falla(svar, fall):
    with pytest.raises(Sparrfalld):
        generera.krav_pa_svaret(svar, fall)


@pytest.mark.parametrize("svar, fall", PRIS_SKA_PASSERA)
def test_prisformer_som_ska_passera(svar, fall):
    generera.krav_pa_svaret(svar, fall)


# -------------------------------------------------------------------- TAL

TAL_SKA_FALLA = [
    ("Vi hinner med det på 14 dagar.", UTAN_UPPSLAG),
    ("Nio av tio bilar går bra, cirka 90 procent.", UTAN_UPPSLAG),
    # skiva 32, LUCKA 24: talet helt i ord, utan siffra och utan prisord
    ("Ombyggnaden går på tjugofemtusen.", UTAN_UPPSLAG),
    ("Det landar på femtusen.", UTAN_UPPSLAG),
    ("Vi tar tjugofem tusen för jobbet.", UTAN_UPPSLAG),
    ("Det går på femhundra.", UTAN_UPPSLAG),
    ("Vi tar sex hundra.", UTAN_UPPSLAG),
    ("Det blir tvåtusen.", UTAN_UPPSLAG),
    ("Priset är ETTUSEN.", UTAN_UPPSLAG),
    # skiva 32, LUCKA 24 KVARSTÅENDE ÅT ANDRA HÅLLET. Ett räkneord utan
    # multiplikand är en ledtid och inte ett pris, och `TAL_I_ORD` kräver
    # `tusen` eller `hundra` efter räkneordet. "Det tar 14 dagar" fälls på
    # SIFFRAN; samma påstående i ord gör det inte.
    #
    # Raden är xfail(strict=True) och inte struken, därför att en lucka som
    # bara är namngiven är osynlig medan en som är MÄTT syns. Rättas mönstret
    # blir raden röd och tvingar bort märkningen.
    pytest.param(
        "Det tar fjorton dagar.",
        UTAN_UPPSLAG,
        marks=pytest.mark.xfail(strict=True, reason="lucka 24, räkneord utan multiplikand"),
    ),
]

TAL_SKA_PASSERA = [
    # Talen ur ett lyckat uppslag ÄR avlästa
    ("Bilen väger 1400 kg och klarar 1500 kg.", MED_UPPSLAG),
    # skiva 31, varv 2, LUCKA 22: två avlästa vikter över komma
    ("Vikterna är 1400, 1500 kg.", MED_UPPSLAG),
    # skiva 31, varv 3, LUCKA 22 kvarstående: samma över blanksteg
    ("Vikterna är 1400 1500 kg.", MED_UPPSLAG),
    ("Hej, hör av dig så bokar vi tid.", UTAN_UPPSLAG),
    # skiva 32, LUCKA 24: VAGA MÄNGDORD ÄR TILLÅTNA enligt §7.2 och får inte
    # fällas av talordsmönstret. Raderna binder den gränsen.
    ("Vi har hjälpt hundratals kunder med det här.", UTAN_UPPSLAG),
    ("Det rör sig om tusentals bilar i landet.", UTAN_UPPSLAG),
    ("Bilar från sextiotalet är en annan femma.", UTAN_UPPSLAG),
    ("Vi har en hundraåring i verkstaden.", UTAN_UPPSLAG),
    ("Vi bokar in dig så snart vi kan.", UTAN_UPPSLAG),
]


@pytest.mark.parametrize("svar, fall", TAL_SKA_FALLA)
def test_talformer_som_ska_falla(svar, fall):
    with pytest.raises(Sparrfalld):
        generera.krav_pa_svaret(svar, fall)


@pytest.mark.parametrize("svar, fall", TAL_SKA_PASSERA)
def test_talformer_som_ska_passera(svar, fall):
    generera.krav_pa_svaret(svar, fall)


# ---------------------------------------------------------- FORDONSFAKTA

FORDONSFAKTA_SKA_FALLA = [
    ("Bilens tjänstevikt räcker för ombyggnad.", UTAN_UPPSLAG),
    ("Din bils släpvagnsvikt är godkänd.", UTAN_UPPSLAG),
    ("Bilens draganordning är på plats.", UTAN_UPPSLAG),
    # skiva 31, varv 1: omskrivningarna
    ("Bilen väger tillräckligt.", UTAN_UPPSLAG),
    ("Din bil klarar släp.", UTAN_UPPSLAG),
    ("Det finns krok på bilen redan.", UTAN_UPPSLAG),
    ("Din bil är tung nog.", UTAN_UPPSLAG),
    ("Vikten på din bil räcker gott.", UTAN_UPPSLAG),
    # skiva 33: ISOLERANDE RADER, en per fordonsterm som saknade en.
    #
    # `test_varje_term_i_monstret_har_ett_testfall` band att varje term HAR ett
    # testfall, men inte att något testfall prövar den ENSAM. Åtta av sexton
    # termer var skuggade av en annan term i samma rad.
    ("Bilens tjanstevikt racker.", UTAN_UPPSLAG),
    ("Bilens slapvagnsvikt ar godkand.", UTAN_UPPSLAG),
    ("Bilens dragkrok sitter kvar.", UTAN_UPPSLAG),
    ("Bilens totalvikt är hög.", UTAN_UPPSLAG),
    ("Bilen vager tillrackligt.", UTAN_UPPSLAG),
    ("Din bil klarar slap.", UTAN_UPPSLAG),
    ("Släpet är monterat.", UTAN_UPPSLAG),
    ("Bilens tyngd räcker.", UTAN_UPPSLAG),
]

FORDONSFAKTA_SKA_PASSERA = [
    ("Bilens draganordning är på plats.", MED_UPPSLAG),
    ("Bilen väger 1400 kg.", MED_UPPSLAG),
    # skiva 31, varv 3, LUCKA 28: önskade svar som mönstret FÄLLER i dag.
    #
    # **RADERNA ÄR ÖPPNA MED FLIT.** Lars ordning i skiva 32 DEL D är att lucka
    # 28:s frekvens MÄTS innan `FORDONSORD` ändras. `strict=True` gör märkningen
    # självupphävande: den dag mönstret rättas blir raden röd igen och tvingar
    # bort märkningen. En grön svit döljer alltså inte hålet, den daterar det.
    pytest.param(
        "Vikten av att boka i tid är stor.",
        UTAN_UPPSLAG,
        marks=pytest.mark.xfail(strict=True, reason="lucka 28, mäts i DEL D"),
    ),
    pytest.param(
        "Vi återkommer om släp när vi sett bilen.",
        UTAN_UPPSLAG,
        marks=pytest.mark.xfail(strict=True, reason="lucka 28, mäts i DEL D"),
    ),
    pytest.param(
        "Vi har en tung period just nu.",
        UTAN_UPPSLAG,
        marks=pytest.mark.xfail(strict=True, reason="lucka 28, mäts i DEL D"),
    ),
]


@pytest.mark.parametrize("svar, fall", FORDONSFAKTA_SKA_FALLA)
def test_fordonsfaktaformer_som_ska_falla(svar, fall):
    with pytest.raises(Sparrfalld):
        generera.krav_pa_svaret(svar, fall)


@pytest.mark.parametrize("svar, fall", FORDONSFAKTA_SKA_PASSERA)
def test_fordonsfaktaformer_som_ska_passera(svar, fall):
    generera.krav_pa_svaret(svar, fall)


# ------------------------------------------------------- DRIFTVAKTEN
#
# **VARFÖR DEN FINNS.** Mönstren har rättats om och om igen, och varje gång har
# rättelsen tappat eller fällt något den inte skulle. Senast skrevs
# `FORFATTNINGSORD` om i ett svep och TAPPADE `kräv` och `regeln`, och tabellen
# ovan blev ändå grön: varje rad som bar "kräver" bar också "Lagen", som fälldes
# av ett annat led.
#
# **EN REGRESSIONSTABELL HINDRAR ATT EN KÄND FORM TAPPAS. EN ISOLERINGSVAKT
# HINDRAR ATT EN OKÄND FORM TAPPAS.** Det är hela skillnaden, och det är skälet
# att båda finns. Tabellen var grön av fel skäl, alltså bevisade den ingenting
# om just de termer som försvann.
#
# Vakten kräver ISOLERING: för varje term ska det finnas en rad där just den
# termen är den ENDA som matchar.
#
# **ISOLERING RÄCKER INTE, och det ledet är fällt fram.** En rad kan vara
# isolerad för sin term och ändå falla på ett HELT ANNAT lager, alltså är termen
# oprövad medan vakten är grön. `\d\s*tkr` var det: varje tkr-rad bar en siffra
# utan källa, så `TAL_I_TEXT` fällde raden och prisordet var skuggat.
# `test_varje_term_BAR_en_fallning` prövar därför att minst en rad slutar fällas
# AV TERMENS EGEN SPÄRR när termen tas bort. Fällt av §7-granskningen av skiva
# 33, varv 1.
#
# **DET ÄR RADEN SOM FÄLLER, INTE VAKTEN, och den skillnaden ska ingen behöva
# gissa sig till.** Testerna är parametriserade över tupeln, alltså FÖRSVINNER en
# raderad terms egna vakter tillsammans med termen. Skyddet mot en tappad term
# utövas av tabellraden, och vakternas uppgift är att garantera att en sådan rad
# finns OCH att den fäller av rätt skäl. Utan isoleringskravet fanns ingen sådan
# rad för tolv av tjugotvå författningstermer, och det var precis så `kräv` kunde
# försvinna.
#
# **ETT UNDANTAG SOM ÄR MÄTT:** `\bettusen\b` i `TROSKELTERMER` går att radera
# med hela sviten grön, eftersom `TAL_I_ORD` fäller de raderna först i
# `krav_pa_svaret`. Termen är lastbärande för sin EGEN spärr, vilket
# `test_varje_term_BAR_en_fallning` visar, men oåtkomlig via kedjan. Enligt §7.1
# är det lagrat försvar och alltså inkonklusivt, inte vakuöst.
#
# **VAKTEN GÄLLER ALTERNATIV OCH INTE BARA TERMER, och det är skiva 33:s
# tillägg.** Lucka 34 var att en gren INUTI en term inte nåddes:
# `regler(?:na|ing\w*|s)?\b` gick att förkorta till `regler(?:na|ing\w*)?\b` med
# hela sviten grön. Lösningen är strukturell i stället för att vakten görs
# smartare: **en term får inte innehålla alternation.** Då ÄR termnivå och
# alternativnivå samma nivå, och `test_ingen_term_gommer_en_alternation` binder
# det. En vakt som måste tolka reguljära uttryck hade själv blivit en sak att
# hålla korrekt.
#
# Beslut av Lars i skiva 33, se `docs/beslutslogg.md` #55.

MONSTER_OCH_TABELL = {
    "PRISTERMER": (generera.PRISTERMER, "PRIS_SKA_FALLA"),
    "TROSKELTERMER": (generera.TROSKELTERMER, "TROSKEL_SKA_FALLA"),
    "FORFATTNINGSTERMER": (generera.FORFATTNINGSTERMER, "TROSKEL_SKA_FALLA"),
    "FORDONSTERMER": (generera.FORDONSTERMER, "FORDONSFAKTA_SKA_FALLA"),
}

TABELLER = {
    "PRIS_SKA_FALLA": PRIS_SKA_FALLA,
    "TROSKEL_SKA_FALLA": TROSKEL_SKA_FALLA,
    "FORDONSFAKTA_SKA_FALLA": FORDONSFAKTA_SKA_FALLA,
}

ALLA_TERMER = [
    (monster, term)
    for monster, (termer, _) in MONSTER_OCH_TABELL.items()
    for term in termer
]


# VILKEN SPÄRR VARJE MÖNSTER TILLHÖR, och hur den anropas.
#
# Behövs för `test_varje_term_BAR_en_fallning`, som prövar att en rads fällning
# faktiskt BEROR på termen. Isolering inom tupeln räcker inte: en rad kan vara
# isolerad för sin term och ändå falla på ett helt annat lager.
SPARR_FOR_MONSTER = {
    "PRISTERMER": ("PRISORD", "krav_pa_tal_med_kalla"),
    "TROSKELTERMER": ("TROSKELTAL", "krav_pa_att_troskeln_inte_ar_forfattningstext"),
    "FORFATTNINGSTERMER": (
        "FORFATTNINGSORD",
        "krav_pa_att_troskeln_inte_ar_forfattningstext",
    ),
    "FORDONSTERMER": ("FORDONSORD", "krav_pa_fordonsfakta_ur_uppslag"),
}


def _faller(sparrnamn: str, svar: str, fall) -> bool:
    """Om den namngivna spärren fäller svaret."""
    sparr = getattr(generera, sparrnamn)
    try:
        if sparrnamn == "krav_pa_att_troskeln_inte_ar_forfattningstext":
            sparr(svar)
        else:
            sparr(svar, fall)
    except Sparrfalld:
        return True
    return False


def _tabellrader(tabellnamn: str) -> list[tuple]:
    """Raderna som (svar, förfrågan), oavsett tupel eller `pytest.param`."""
    return [getattr(rad, "values", rad) for rad in TABELLER[tabellnamn]]


def _radtexter(tabellnamn: str) -> list[str]:
    """Svarstexterna i en tabell, oavsett om raden är en tupel eller en param."""
    texter = []
    for rad in TABELLER[tabellnamn]:
        # `pytest.param` bär sina värden i `.values`; en vanlig rad är en tupel.
        varden = getattr(rad, "values", rad)
        texter.append(varden[0])
    return texter


@pytest.mark.parametrize("monster", sorted(MONSTER_OCH_TABELL))
def test_ingen_term_gommer_en_alternation(monster):
    """En term får inte innehålla `|` eller en grupp.

    **DET HÄR ÄR VAD SOM GÖR ISOLERINGSVAKTEN FULLSTÄNDIG.** En gren inuti en
    term är ett lager som vakten inte når, eftersom vakten prövar termer. Med
    förbudet är varje alternativ en egen term och alltså isolerat var för sig.
    """
    termer, _ = MONSTER_OCH_TABELL[monster]
    for term in termer:
        assert "|" not in term, f"{monster}: {term!r} bär en alternation"
        assert "(" not in term, f"{monster}: {term!r} bär en grupp"


# **OPTIONALITET ÄR OCKSÅ EN GREN, och alternationsförbudet når den inte.**
#
# `\w*`, `?`, `*` och `+` gör en del av en term valfri, alltså bär termen två
# vägar utan att bära ett `|`. Två mätta fall, båda GRÖNA innan den här raden
# fanns:
#
#     `\binkl\.?\s*moms\b`   ->  `\binkl\.\s*moms\b`    snävade bort "inkl moms"
#     `\btusen\w*\s*kg\b`    ->  `\btusen\s*kg\b`       snävade bort "tusentals kg"
#
# Den andra är samma klass som lucka 33. Fällt av §7-granskningen av skiva 33,
# varv 1, som fällde mitt påstående att förbudet mot `|` gör termnivå och
# alternativnivå till samma nivå.
#
# **KRAVET ÄR EN FAKTISK SNÄVNING, inte två olika träffsträngar.** Första
# lydelsen krävde bara att de isolerande raderna gav minst två OLIKA strängar,
# och kommentaren påstod att det betyder "en som utnyttjar den valfria delen och
# en som inte gör det". Det ledet var falskt om koden: båda träffarna fick
# utnyttja den valfria delen. Följden var att sju `\w*`-termer gick att snäva:
#
#     `föreskrift\w*` -> `föreskrift\w+`   tappade ordet `föreskrift`, GRÖN
#     `\binkl\.?\s*moms\b` -> `\binkl\.?\smoms\b`  tappade `inkl.moms`, GRÖN
#
# Fällt av §7-granskningen av skiva 33, varv 2.
#
# Vakten SNÄVAR nu termen på riktigt, ett kvantifierare i taget, och kräver att
# minst en isolerande rad slutar matcha. Det är samma prövning en granskare gör
# för hand, gjord av sviten i stället.
#
# **`+` RÄKNAS INTE.** Det kräver minst en förekomst och går alltså inte att
# utelämna, så `\bett\s+ton\b` bär ingen gren.
#
# **`\s*` SNÄVAS INTE HELLER.** Att kräva en rad utan blanksteg där mönstret
# tillåter det skulle tvinga fram former ingen skriver, som `tusenkilo`.
# Blankstegstolerans är formatering och inte en språklig gren. `\.?` snävas
# däremot, eftersom `inkl moms` och `inkl.moms` båda är former någon skriver.
OPTIONALITET = re.compile(r"(?<!\\)[?*]")


def _snavningar(term: str) -> list[str]:
    """Termen med EN kvantifierare snävad, en variant per kvantifierare.

    `\\w*` blir `\\w+`, alltså tappas den tomma böjningen. `\\.?` blir `\\.`,
    alltså tappas formen utan tecknet. `\\s*` lämnas, se kommentaren ovan.
    """
    varianter = []
    for i, tecken in enumerate(term):
        if i == 0 or term[i - 1] == "\\":
            continue
        if tecken == "*" and term[i - 2 : i] != r"\s":
            varianter.append(term[:i] + "+" + term[i + 1 :])
        elif tecken == "?":
            varianter.append(term[:i] + term[i + 1 :])
    return varianter


@pytest.mark.parametrize("monster, term", ALLA_TERMER)
def test_en_SNAVAD_term_tappar_en_rad(monster, term):
    """Varje valfri del ska bära minst en isolerande rad."""
    if not OPTIONALITET.search(term):
        pytest.skip("termen bär ingen optionalitet")

    termer, tabellnamn = MONSTER_OCH_TABELL[monster]

    isolerande = [
        text
        for text in _radtexter(tabellnamn)
        if {t for t in termer if re.search(t, text, flags=re.IGNORECASE)} == {term}
    ]

    for snavad in _snavningar(term):
        tappade = [
            text
            for text in isolerande
            if not re.search(snavad, text, flags=re.IGNORECASE)
        ]
        assert tappade, (
            f"{monster}: {term!r} går att snäva till {snavad!r} utan att någon "
            f"isolerande rad slutar matcha. Den valfria delen är oprövad. "
            f"Isolerande rader i dag: {isolerande}"
        )


@pytest.mark.parametrize("monster, term", ALLA_TERMER)
def test_varje_term_BAR_en_fallning(monster, term, monkeypatch):
    """Det ska finnas en rad vars FÄLLNING beror på just den här termen.

    **ISOLERING INOM TUPELN RÄCKER INTE, och det är fällt fram.** En rad kan
    vara isolerad för sin term och ändå falla på ett helt annat lager. Två
    termer gick därför att radera med hela sviten grön:

        `\\d\\s*tkr`      raderna föll på `TAL_I_TEXT`, inte på prisordet
        `\\bettusen\\b`   raderna föll på `TAL_I_ORD`, inte på tröskeln

    Vakten var alltså grön medan två lager var otestade, vilket är samma
    skuggning som lucka 31 handlade om, en nivå bort. Fällt av §7-granskningen
    av skiva 33, varv 1.

    Prövningen tar bort termen ur mönstret och kräver att MINST EN rad slutar
    fällas av just den spärr termen tillhör.
    """
    termer, tabellnamn = MONSTER_OCH_TABELL[monster]
    monsternamn, sparrnamn = SPARR_FOR_MONSTER[monster]

    utan = re.compile(
        "|".join(t for t in termer if t != term), flags=re.IGNORECASE
    )

    barande = []
    for svar, fall in _tabellrader(tabellnamn):
        if not _faller(sparrnamn, svar, fall):
            continue
        monkeypatch.setattr(generera, monsternamn, utan)
        try:
            if not _faller(sparrnamn, svar, fall):
                barande.append(svar)
        finally:
            monkeypatch.undo()

    assert barande, (
        f"ingen rad i {tabellnamn} slutar fällas av {sparrnamn} när {term!r} "
        f"tas bort ur {monsternamn}. Termen är oprövad: varje rad som bär den "
        "fälls av något annat lager. Lägg till en rad där bara den här termen "
        "kan fälla."
    )


@pytest.mark.parametrize("monster, term", ALLA_TERMER)
def test_varje_term_ar_ISOLERAD(monster, term):
    """Varje term ska ha en rad där den är ENSAM om att matcha.

    Utan den här raden kan en term tas bort ur mönstret med hela sviten grön,
    så länge någon annan term råkar täcka samma testrader.
    """
    termer, tabellnamn = MONSTER_OCH_TABELL[monster]

    isolerande = [
        text
        for text in _radtexter(tabellnamn)
        if {t for t in termer if re.search(t, text, flags=re.IGNORECASE)} == {term}
    ]
    assert isolerande, (
        f"ingen rad i {tabellnamn} isolerar {term!r} ur {monster}: "
        f"lägg till en där ingen annan term ur {monster} förekommer"
    )
