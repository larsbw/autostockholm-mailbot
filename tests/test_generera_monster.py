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
    # Driftvakten `test_varje_forfattningsterm_ar_ISOLERAD` mätte att TOLV av
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


@pytest.mark.parametrize("svar, fall", TROSKEL_SKA_PASSERA)
def test_troskelformer_som_ska_passera(svar, fall):
    """En spärr som fäller önskade svar blir avstängd, §7.1."""
    generera.krav_pa_svaret(svar, fall)


# ------------------------------------------------------- DRIFTVAKTEN
#
# **VARFÖR DEN FINNS.** `FORFATTNINGSORD` har rättats om och om igen, och varje
# gång har rättelsen tappat eller fällt något den inte skulle. Senast skrevs
# hela regexen om i ett svep och TAPPADE `kräv` och `regeln`,
# och tabellen ovan blev ändå grön: varje rad som bar "kräver" bar också
# "Lagen", som fälldes av ett annat led. **Tabellen kan inte upptäcka att en
# term försvinner så länge en annan term täcker samma rad.**
#
# Vakten kräver därför ISOLERING: för varje term ska det finnas en rad där just
# den termen är den ENDA som matchar. Då gör en tappad term raden röd.
#
# Formen är lånad från `test_varje_term_i_monstret_har_ett_testfall`, som fanns
# för `FORDONSORD` men saknades här. Fällt av §7-granskningen av skiva 32,
# varv 2.


def _termer_som_matchar(text: str) -> set[str]:
    """Vilka av `FORFATTNINGSTERMER` som träffar texten."""
    return {
        term
        for term in generera.FORFATTNINGSTERMER
        if re.search(term, text, flags=re.IGNORECASE)
    }


@pytest.mark.parametrize("term", generera.FORFATTNINGSTERMER)
def test_varje_forfattningsterm_ar_ISOLERAD(term):
    """Varje term ska ha en rad där den är ENSAM om att matcha.

    Utan den här raden kan en term tas bort ur mönstret med hela sviten grön,
    så länge någon annan term råkar täcka samma testrader.
    """
    isolerande = [
        svar
        for svar, _ in TROSKEL_SKA_FALLA
        if _termer_som_matchar(svar) == {term}
    ]
    assert isolerande, (
        f"ingen rad i TROSKEL_SKA_FALLA isolerar {term!r}: "
        "lägg till en där ingen annan författningsterm förekommer"
    )


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
