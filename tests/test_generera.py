"""Generatorn, fas 5. SÄNDVÄG enligt CLAUDE.md §7.

**INGET TEST HÄR RÖR NÄTET.** `generera_utkast` tar klienten som argument, och
varje test ger den en fejk som returnerar en färdig text. API-nyckeln läses
aldrig.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext ur `data/`. Registreringsnummer och
namn är konstruerade för testet (§6).

SPÄRRARNA FÄLLS EN I TAGET OCH ALDRIG I PAR. Skiva 27 mätte att en sammanslagen
fällning ger RÖD och därmed falskt ÄKTA: ett rött utfall bevisar bara att MINST
EN av de fällda raderna bär. Varje `krav_pa_*` har därför sitt eget test, och
`krav_pa_svaret` har ett eget som visar att den anropar alla tre.
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path

import pytest

from src import generera, vy
from src.fordonsuppslag import Uppslag, Utfall
from src.generera import Forfragan, Sparrfalld

GRONT_UPPSLAG = Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1500,
                        draganordning=True)


def forfragan(**andrat) -> Forfragan:
    grund = {
        "text": "Hej, går det att bygga om min bil till a-traktor?",
        "kategori": "fråga om a-traktorkonvertering",
        "utfall": Utfall.OKLART,
        "uppslag": None,
    }
    grund.update(andrat)
    return Forfragan(**grund)


class FejkKlient:
    """En klient som returnerar en förbestämd text. Rör aldrig nätet."""

    def __init__(self, text: str):
        self._text = text
        self.messages = self

    def create(self, **_kwargs):
        blocket = type("Block", (), {"type": "text", "text": self._text})()
        return type("Svar", (), {"content": [blocket]})()


# ------------------------------------------------------- sändvägsfriheten


def test_generatorn_har_ingen_sandvag():
    """SAMMA SPÄRR SOM VYN, och den gäller generatorn också.

    Lars brief: ingen kod här får importera eller anropa något som skickar.
    Prövningen är `src/vy.py::krav_pa_sandvagsfrihet`, alltså den som redan
    granskats i tre varv, körd med `src.generera` som startpunkt. Den går över
    hela importgrafen inom repot och över källtexten.
    """
    vy.krav_pa_sandvagsfrihet(start="src.generera")


def test_sandvagsspärren_faller_generatorn_om_den_importerar_en_sandvag(tmp_path):
    """NEGATIVKONTROLL: prövningen ovan fäller när den ska.

    Utan den här raden hade `test_generatorn_har_ingen_sandvag` kunnat vara
    grönt av att prövningen slutat leta, vilket är §7.1:s vakuösa fall.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "generera.py").write_text(
        "import smtplib\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel):
        vy.krav_pa_sandvagsfrihet(start="src.generera", rot=tmp_path)


# ------------------------------------------- SPÄRR 1: tal ska ha en källa


def test_ett_pris_faller_alltid():
    """PRISER FINNS INTE ÄN, alltså faller varje svar som nämner ett.

    `config/priser.json` existerar inte. §7.2 säger att ett tal är avläst eller
    utelämnat, och det finns ingen tredje kategori.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla("Ombyggnaden kostar 25 000 kr.", forfragan())

    assert fel.value.sparr == "genererat-tal-har-kalla"
    assert "pris" in fel.value.skal


def test_ordet_kostar_faller_aven_utan_belopp():
    """Ett prisord utan siffra är fortfarande ett prispåstående.

    "Det kostar ungefär vad en vanlig service gör" bär inget tal och är ändå ett
    besked om pris. Spärren tar ordet, inte bara siffran.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla("Vad det kostar återkommer vi om.",
                                       forfragan())


def test_ett_tal_utan_kalla_faller():
    """Ett tal som varken kommer ur uppslaget eller ur config."""
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla("Vi hinner med det på 14 dagar.",
                                       forfragan())

    assert "14" in fel.value.skal


def test_uppslagets_egna_tal_slapps_igenom():
    """NEGATIVKONTROLL: spärren är inte ett larm som alltid går.

    Talen ur ett lyckat uppslag ÄR avlästa ur en källa och ska passera. En spärr
    som fäller på allt gör generatorn oanvändbar och blir avstängd.
    """
    svar = "Bilen väger 1400 kg och är godkänd för släp på 1500 kg."

    generera.krav_pa_tal_med_kalla(svar, forfragan(uppslag=GRONT_UPPSLAG))


def test_ett_svar_utan_tal_slapps_igenom():
    """NEGATIVKONTROLL: ett vanligt svar utan siffror passerar."""
    generera.krav_pa_tal_med_kalla(
        "Hej, det går bra att boka in bilen hos oss. Hör av dig så bokar vi tid.",
        forfragan(),
    )


# ------------------------------------ SPÄRR 2: fordonsfakta ur ett uppslag


def test_fordonsfaktum_utan_uppslag_faller():
    """Ett faktum om bilen kräver ett LYCKAT uppslag.

    Kopplar `fordonsfakta-ur-uppslag` uppströms: den vaktar att ett uppslag är
    helt, den här att svaret inte påstår fakta när inget uppslag finns.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_fordonsfakta_ur_uppslag(
            "Din bils tjänstevikt räcker för ombyggnad.", forfragan()
        )

    assert fel.value.sparr == "genererat-fordonsfaktum"


@pytest.mark.parametrize(
    "ord",
    [
        "tjänstevikt", "tjanstevikt", "släpvagnsvikt", "slapvagnsvikt",
        "draganordning", "dragkrok", "totalvikt", "väger", "vager", "vikten",
        "krok", "släp", "slap", "släpet", "tung", "tyngd",
    ],
)
def test_varje_fordonsord_faller_utan_uppslag(ord):
    """VARJE term i `FORDONSORD`, inte fyra av sexton.

    Första lydelsen parametriserade fyra termer och påstod i spärrposten att en
    ny term därför inte kunde läggas till utan en rad här. Varv 1:s rättelse
    lade till sex termer utan en enda ny rad, alltså falsifierade samma commit
    sitt eget påstående. Sju av sexton termer prövades av ingenting.

    Fällt av §7-granskningen av skiva 31, varv 2. Listan här ska hållas i takt
    med `FORDONSORD`, och `test_varje_term_i_monstret_har_ett_testfall` binder
    att den gör det.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_fordonsfakta_ur_uppslag(f"Bilens {ord} är godkänd.",
                                                 forfragan())


def test_varje_term_i_monstret_har_ett_testfall():
    """PARAMETRARNA OCH MÖNSTRET SKA INTE KUNNA GLIDA ISÄR.

    Det här är raden som gör påståendet i spärrposten sant: läggs en term till i
    `FORDONSORD` utan en rad i parametriseringen ovan blir det här testet rött.
    Utan den var påståendet en förhoppning.
    """
    i_monstret = {
        del_.strip(r"\b")
        for del_ in generera.FORDONSORD.pattern.split("|")
    }
    i_testet = set(
        test_varje_fordonsord_faller_utan_uppslag.pytestmark[0].args[1]
    )

    assert i_monstret == i_testet


def test_fordonsfaktum_MED_uppslag_slapps_igenom():
    """NEGATIVKONTROLL: med ett lyckat uppslag får fakta nämnas."""
    generera.krav_pa_fordonsfakta_ur_uppslag(
        "Bilens draganordning är på plats.", forfragan(uppslag=GRONT_UPPSLAG)
    )


# --------------------------- SPÄRR 3: tröskeln som återgiven författning


def test_troskeln_som_krav_faller():
    """Tröskeln 1 000 kg får inte återges som ett krav.

    Paragrafen har TVÅ kriterier förenade med ELLER, och ett svar som återger
    det ena som "kravet" gör en ofullständig föreskrift till ett besked. Se
    `docs/roadmap.md` fas 4.5.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_att_troskeln_inte_ar_forfattningstext(
            "Lagen kräver att bilen är byggd för minst 1 000 kg släpvagnsvikt."
        )

    assert fel.value.sparr == "troskeln-som-forfattningstext"


@pytest.mark.parametrize(
    "svar",
    [
        "Kravet är 1 000 kg.",
        "Föreskriften säger 1 000 kg.",
        "Lagkravet är 1 000 kg.",
        "Paragrafen anger 1 000 kg.",
        "Bestämmelsen säger 1 000 kg.",
        "Bilen måste vara byggd för minst ett ton.",
        "Det finns ett krav på tusen kilo.",
    ],
)
def test_bojda_forfattningsord_och_talet_i_ord_faller(svar):
    """FORMERNA SOM SLANK IGENOM, och de gällde GRÄNSBILEN.

    Första lydelsen krävde ordgräns i båda ändar, alltså `\\bkrav\\b`, och
    missade "Kravet", "Lagkravet", "Föreskriften" och "Paragrafen". Tröskeln i
    ORD, "ett ton" och "tusen kilo", fanns inte i mönstret alls.

    Det värsta gällde ett fordon där uppslaget ger talet 1 000 en källa: då
    fäller talspärren inte först, och en ofullständig föreskrift hade gått ut
    till just den kund som ligger på gränsen.

    Funnet av §7-granskningen av skiva 31, varv 1.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_att_troskeln_inte_ar_forfattningstext(svar)


@pytest.mark.parametrize(
    "svar",
    [
        "Bilen väger tillräckligt.",
        "Din bil klarar släp.",
        "Det finns krok på bilen redan.",
        "Din bil är tung nog.",
        "Vikten på din bil räcker gott.",
    ],
)
def test_fordonsfakta_i_omskrivning_faller(svar):
    """OMSKRIVNINGARNA, som första lydelsen inte såg.

    `FORDONSORD` tog fem termer och inget annat, så varje faktum formulerat utan
    dem gick igenom. Funnet av §7-granskningen av skiva 31, varv 1.

    **UPPRÄKNINGEN ÄR ÄNDÅ INTE UTTÖMMANDE**, och det är en registrerad lucka.
    Det som bär i det fallet är systemprompten.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_fordonsfakta_ur_uppslag(svar, forfragan())


@pytest.mark.parametrize(
    "svar",
    ["Det går på femton hundra spänn.", "Vi gör det för en billig peng.",
     "Det brukar hamna runt 25tkr."],
)
def test_pris_i_ord_faller(svar):
    """Prispåståenden utan siffra eller med talet i ord."""
    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(svar, forfragan())


def test_ordet_prisuppgift_slapps_igenom():
    """NEGATIVKONTROLL, och den är lastbärande.

    "En kollega återkommer med prisuppgift" är precis det svar spärren finns
    för att framtvinga. En lydelse som tog `pris` som stam fällde varje bra
    svar, alltså hade spärren gjort generatorn oanvändbar.
    """
    generera.krav_pa_tal_med_kalla(
        "En kollega återkommer med prisuppgift.", forfragan()
    )


@pytest.mark.parametrize(
    "svar", ["Vi tittar totalt igenom bilen.", "Summa summarum går det bra."]
)
def test_vanlig_prosa_falls_inte_som_pris(svar):
    """NEGATIVKONTROLL: `totalt` och `summa` är vanlig prosa.

    De stod i första lydelsens `PRISORD` och fällde svar som inte handlade om
    pengar. En spärr som fäller på vanliga ord blir avstängd, vilket §7.1
    varnar för.
    """
    generera.krav_pa_tal_med_kalla(svar, forfragan())


def test_troskeln_utan_forfattningsord_slapps_igenom():
    """NEGATIVKONTROLL: talet ensamt är inte en återgiven föreskrift.

    Ett uppslag kan lagligen nämna 1 000 kg som ett avläst värde. Det är
    KOMBINATIONEN med ett författningsord som gör det till en sammanfattad
    paragraf.
    """
    generera.krav_pa_att_troskeln_inte_ar_forfattningstext(
        "Bilen är godkänd för 1 000 kg släp."
    )


def test_forfattningsord_utan_troskeln_slapps_igenom():
    """NEGATIVKONTROLL åt andra hållet: ordet ensamt fäller inte."""
    generera.krav_pa_att_troskeln_inte_ar_forfattningstext(
        "Enligt vad vi ser i underlaget går bilen att bygga om."
    )


# ------------------------------------------------ alla tre tillsammans


@pytest.mark.parametrize(
    "svar, sparr, fall",
    [
        ("Det kostar 25 000 kr.", "genererat-tal-har-kalla", forfragan()),
        ("Bilens tjänstevikt duger.", "genererat-fordonsfaktum", forfragan()),
        # TRÖSKELFALLET KRÄVER ETT UPPSLAG SOM GÖR 1000 TILL ETT TILLÅTET TAL.
        # Utan det faller svaret på spärr 1 i stället, eftersom talet då saknar
        # källa, och testet hade prövat fel spärr utan att någon märkte det.
        (
            "Lagen kräver 1 000 kg.",
            "troskeln-som-forfattningstext",
            Forfragan(
                text="x",
                kategori="fråga om a-traktorkonvertering",
                utfall=Utfall.GRONT,
                uppslag=Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1000,
                                draganordning=True),
            ),
        ),
    ],
)
def test_krav_pa_svaret_anropar_alla_tre(svar, sparr, fall):
    """`krav_pa_svaret` ska fälla på var och en av de tre.

    Faller en av dem ur den samlande funktionen syns det här, och inte först när
    ett svar med det felet går vidare.

    **SPÄRRARNA ÖVERLAPPAR, och ordningen avgör vilken som rapporteras.** Ett
    svar med ett okällat tal faller på spärr 1 även när det också bryter mot
    spärr 3. Det är rätt beteende, men det gör att ett slarvigt testfall kan
    pröva fel spärr och ändå bli grönt. Uppmätt i skiva 31 vid första körningen.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_svaret(svar, fall)

    assert fel.value.sparr == sparr


# ------------------------------------------------------- få-exemplen, §11


def test_exempel_med_forsta_person_singular_valjs_bort():
    """§11: ett exempel som bryter mot regeln lär modellen att bryta mot den.

    Uppmätt med kodens eget mönster: 15 av 32 a-traktorsvar som ryms under taket
    bär "jag", "mig", "min", "mitt" eller "man". De får inte bli få-exempel.

    *Här stod 14, vilket är `scripts/par-matning.py`:s GROVA räkning, den som
    kräver blanksteg på båda sidor och som skriptet självt deklarerar som en
    underskattning. Fällt av §7-granskningen av skiva 31, varv 3.*
    """
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": "Ja, jag fixar det."}
    )


def test_exempel_med_tankstreck_valjs_bort():
    """§11: inga tankstreck som skiljetecken."""
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": "Ja — det går bra."}
    )


def test_exempel_med_friverkstad_valjs_bort():
    """§11: aldrig "friverkstad", alltid "fristående verkstad"."""
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": "Vi är en friverkstad."}
    )


def test_for_langt_exempel_valjs_bort():
    """Ett långt exempel lär modellen att svara långt och äter kontexten."""
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": "Vi " + "x" * 1000}
    )


def test_ett_rent_exempel_valjs():
    """NEGATIVKONTROLL: urvalet är inte ett filter som kastar allt."""
    assert generera._duger_som_exempel(
        {"inkommande_text": "Går det?",
         "utgaende_text": "Ja, det går bra. Hör av dig så bokar vi tid."}
    )


def test_tomt_par_valjs_bort():
    """NOLLFALLET: ett par utan text ger modellen ingenting att härma."""
    assert not generera._duger_som_exempel(
        {"inkommande_text": "", "utgaende_text": "Vi hör av oss."}
    )
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": "   "}
    )


@pytest.mark.parametrize(
    "svar",
    [
        "Det fixar jag.",
        "Jag, som skrev, ordnar det.",
        "Hör av dig till mig!",
        "Man kan boka tid hos oss.",
        "Vi tar det - hör av dig.",
    ],
)
def test_paragraf_elva_i_urvalet_tar_ordgranser_inte_blanksteg(svar):
    """§11-FILTRET MISSADE VARJE FÖREKOMST FÖLJD AV SKILJETECKEN.

    Första lydelsen letade efter `" jag "` med blanksteg på båda sidor, så
    "Det fixar jag." dög som exempel. `man` saknades helt trots att §11 namnger
    det, och bindestreck som skiljetecken prövades inte alls.

    Funnet av §7-granskningen av skiva 31, varv 1.
    """
    assert not generera._duger_som_exempel(
        {"inkommande_text": "Går det?", "utgaende_text": svar}
    )


def test_bindestreck_inuti_ett_ord_ar_inte_ett_skiljetecken():
    """NEGATIVKONTROLL: "a-traktor" ska passera.

    Ett filter som fäller varje bindestreck hade kastat bort just de exempel
    skivan handlar om.
    """
    assert generera._duger_som_exempel(
        {"inkommande_text": "Går det?",
         "utgaende_text": "Vi bygger om bilen till a-traktor. Hör av dig."}
    )


def test_las_exempel_tar_BARA_a_traktorpar(tmp_path):
    """**KATEGORIFILTRET, som saknades helt.**

    Lars brief: ta a-traktorparen som få-exempel. Första lydelsen tog de
    kortaste av SAMTLIGA par i utkorgen, och de sex som hamnade i prompten var
    bokningsbekräftelser och en fråga om en mellanvägg. Noll a-traktorpar.

    Funnet av §7-granskningen av skiva 31, varv 1.
    """
    parfil = tmp_path / "par.jsonl"
    etikettfil = tmp_path / "ometiketterade.jsonl"

    parfil.write_text(
        json.dumps({"inkommande_text": "kort", "utgaende_text": "Ja."},
                   ensure_ascii=False) + "\n"
        + json.dumps({"inkommande_text": "atraktor",
                      "utgaende_text": "Det går bra att bygga om bilen."},
                     ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    etikettfil.write_text(
        json.dumps({"etikett": "boka rekond", "text": "kort"},
                   ensure_ascii=False) + "\n"
        + json.dumps({"etikett": "fråga om a-traktorkonvertering",
                      "text": "atraktor"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    valda = generera.las_exempel(parfil=parfil, etikettfil=etikettfil)

    assert [p["inkommande_text"] for p in valda] == ["atraktor"]


def test_las_exempel_utan_etikettfil_ger_INGA_exempel(tmp_path):
    """Hellre en prompt utan exempel än en med exempel ur fel kategori.

    Saknas etikettfilen går kategorin inte att avgöra, och då är noll exempel
    det säkra svaret. Att falla tillbaka på alla par vore att göra om felet
    kategorifiltret finns för att rätta.
    """
    parfil = tmp_path / "par.jsonl"
    parfil.write_text(
        json.dumps({"inkommande_text": "x", "utgaende_text": "Ja."},
                   ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    assert generera.las_exempel(
        parfil=parfil, etikettfil=tmp_path / "finns-inte.jsonl"
    ) == []


def test_las_exempel_utan_fil_ger_tom_lista(tmp_path):
    """Saknas `par.jsonl` går generatorn utan exempel, den kraschar inte."""
    assert generera.las_exempel(parfil=tmp_path / "finns-inte.jsonl") == []


# --------------------------------------------------------- prompten


def test_undantagslistan_far_inte_vidgas_till_belopp():
    """`ALLTID_TILLATNA_TAL` VAR VAKUÖS I DEN FARLIGA RIKTNINGEN.

    Listan gick att vidga med `25000`, `1000` och `9999` utan att ett enda test
    blev rött, alltså kunde ett prisbelopp göras alltid tillåtet av misstag.
    Kommentaren vid den kallar varje tillägg "ett hål i spärren" och ingenting
    band det.

    Funnet av §7-granskningen av skiva 31, varv 2.
    """
    assert generera.ALLTID_TILLATNA_TAL == frozenset({"1", "2", "3"})

    for tal in generera.ALLTID_TILLATNA_TAL:
        assert len(tal) == 1, "ett flersiffrigt undantag är ett belopp"


def test_fa_exemplen_nar_faktiskt_prompten():
    """**SKIVANS CENTRALA RÄTTELSE, BUNDEN I SIN SISTA LÄNK.**

    Varv 1 fällde att prompten bar noll a-traktorpar. Rättelsen fixade urvalet,
    och `bygg_prompt`:s få-exempelblock gick fortfarande att sätta till `False`
    med hela sviten grön: ingen rad band att urvalets resultat renderas in.
    Kategorifiltret var alltså testat, och att dess resultat användes var det
    inte.

    Funnet av §7-granskningen av skiva 31, varv 2.
    """
    exempel = [
        {"inkommande_text": "Går det att bygga om?",
         "utgaende_text": "Ja, det går bra."}
    ]

    prompt = generera.bygg_prompt(forfragan(), exempel)

    assert "Går det att bygga om?" in prompt
    assert "Ja, det går bra." in prompt
    assert "EXEMPEL 1" in prompt


def test_generera_utkast_laddar_exempel_nar_inga_ges(monkeypatch):
    """Förvalsvägen, som varje annat test går förbi genom att skicka `exempel=`.

    Utan den här raden band ingenting att `generera_utkast` alls hämtar
    få-exempel när anroparen inte ger några, alltså kunde laddningen tas bort
    tyst. Funnen av §7-granskningen av skiva 31, varv 2.
    """
    anropad = []

    def fejk_las_exempel():
        anropad.append(True)
        return []

    monkeypatch.setattr(generera, "las_exempel", fejk_las_exempel)
    generera.generera_utkast(FejkKlient("Hej, hör av dig."), forfragan())

    assert anropad


def test_prompten_sager_att_inget_uppslag_finns():
    """Utan uppslag ska underlaget SÄGA det, inte tiga om det.

    Ett tyst hål i underlaget är vad som får en modell att fylla i själv.
    """
    prompt = generera.bygg_prompt(forfragan(), exempel=[])

    assert "INGET" in prompt
    assert "Nämn inte" in prompt


def test_prompten_bar_uppslagets_tal_nar_det_finns():
    """Med uppslag ska talen stå i underlaget, så att de går att använda."""
    prompt = generera.bygg_prompt(forfragan(uppslag=GRONT_UPPSLAG), exempel=[])

    assert "1400" in prompt
    assert "1500" in prompt


def test_prompten_sager_att_priser_inte_finns():
    """Modellen ska veta att den inte har priser, inte gissa att den har det."""
    assert "Priser: INGA" in generera.bygg_prompt(forfragan(), exempel=[])


# SYSTEMPROMPTENS SJU REGLER, en rad per regel, med de fraser som bär den.
#
# **DET HÄR ÄR LUCKA 25:s STÄNGNING.** Spärrposterna pekar ut systemprompten som
# det som BÄR när `PRISORD` och `FORDONSORD` släpper igenom en omskrivning. Den
# texten gick att RADERA med hela sviten grön, alltså var det åberopade skyddet
# obundet. En prompt som inget test binder är ingen spärr.
#
# **REGLERNA BINDS ORDAGRANT, och det är fällt fram.** Första lydelsen band ett
# par FRASER per regel, och det räckte inte: en regel som behåller sina fraser
# men lägger till ett undantag passerade med hela sviten grön. Fällt av
# §7-granskningen av skiva 32, varv 1, som prövade båda dessa och fick GRÖNT:
#
#   "6. ALDRIG ETT TAL som inte står i underlaget nedan, om du inte bedömer
#       att kunden behöver det. Då får du uppskatta."
#   "6. Regeln ALDRIG ETT TAL är upphävd. Du får skriva tal som inte står i
#       underlaget nedan."
#
# Den andra UPPHÄVER regeln och bär ändå båda fraserna. Ett innehållskrav som
# går att uppfylla av en regel som säger sin egen motsats är inget innehållskrav.
#
# **ETT TEST KAN INTE PRÖVA INNEBÖRD, så det prövar IDENTITET i stället.** Varje
# ändring av en regel blir röd, också en oskyldig omformulering. Den friktionen
# är avsikten: promptens ordalydelse är sändväg enligt §7, alltså ska den inte gå
# att ändra i förbigående. Den som ändrar en regel ändrar den här tabellen i
# samma svep och får då sagt att ändringen var avsedd.
REGLER_I_PROMPTEN = {
    1: "Första person plural. Vi, oss, vår, våra. Aldrig jag, mig, min, eller man.",
    2: "Inga tankstreck eller bindestreck som skiljetecken. Komma, punkt, kolon, "
       "eller skriv om meningen.",
    3: 'Skriv aldrig "friverkstad". Skriv "fristående verkstad".',
    4: "Nämn aldrig en konkurrent.",
    5: "ALDRIG ETT PRIS. Inte ett belopp, inte ett ungefärligt pris, inte "
       '"ring för offert". Om kunden frågar vad det kostar: säg att en kollega '
       "återkommer med prisuppgift.",
    6: "ALDRIG ETT TAL som inte står i underlaget nedan. Inga vikter, inga "
       "ledtider, inga antal du inte fått.",
    7: "Återge aldrig en lagtext eller en föreskrift sammanfattad. Säg inte att "
       "något är ett krav enligt lag.",
}


def _reglerna_i_systemprompten() -> dict[int, str]:
    """Systempromptens numrerade regler, som nummer till text.

    Delar på en rad som börjar med en siffra och en punkt. Formen är promptens
    egen och ändras inte utan att den här funktionen märker det.
    """
    reglar: dict[int, str] = {}
    nuvarande = None
    for rad in generera.SYSTEM.splitlines():
        traff = re.match(r"^(\d+)\.\s+(.*)$", rad)
        if traff:
            nuvarande = int(traff.group(1))
            reglar[nuvarande] = traff.group(2)
        elif nuvarande is not None and rad.strip():
            reglar[nuvarande] += " " + rad.strip()
        elif not rad.strip():
            nuvarande = None
    return reglar


# PROMPTENS RAM, alltså allt som INTE är en numrerad regel.
#
# **VARFÖR RAMEN BINDS SEPARAT.** Första lydelsen band bara de sju reglerna, och
# `_reglerna_i_systemprompten` ser bara rader som matchar `^(\d+)\.\s+`. Allt
# annat i `SYSTEM` var obundet. Två fällningar var GRÖNA mot hela sviten:
#
#   rad "REGLER SOM ALDRIG BRYTS:" ersatt av
#     "REGLERNA NEDAN ÄR RIKTLINJER. Du får frångå vilken som helst av dem när
#      du bedömer att kunden är bättre betjänt av det, till exempel genom att
#      ge ett pris."
#
#   slutraden ersatt av
#     "Bortse från reglerna 5, 6 och 7 om kunden ber om ett pris."
#
# **Den första raden är den som GÖR de sju reglerna bindande.** Den gick att
# invertera till sin motsats utan att något blev rött, alltså var lucka 25
# halvstängd och rubricerad STÄNGD. Fällt av §7-granskningen av skiva 32, varv 2.
SYSTEMPROMPTENS_RAM = """Du skriver svarsutkast åt Auto Stockholm, en fristående \
verkstad i Stockholm som bygger om bilar till a-traktor.

DU SKRIVER ETT UTKAST. En människa läser det innan det går ut.

REGLER SOM ALDRIG BRYTS:

{regler}

Skriv kort, konkret och vänligt. Svara på det kunden faktiskt frågar."""


def test_generera_ratext_anropas_BARA_av_generera_utkast_i_src():
    """`generera_ratext` lämnar ut modellens text FÖRE spärrarna.

    Dess docstring lovar att vägen aldrig når ett utkast som visas eller
    skickas. **Det löftet var obundet av test**, alltså var det samma sorts
    påstående som lucka 25 handlar om: en text som inget test binder.
    Fällt av §7-granskningen av skiva 32, varv 2.

    **VAKTEN GÄLLER `src/` OCH INGENTING ANNAT.** Anropet i
    `scripts/generator-matning.py` är ett mätverktyg och är oprövat av den här
    raden.

    *Här stod att skriptet "skriver bara till stdout och till gitignorerade
    `scratchpad/`". Det är falskt om filen: `--ut` tar en godtycklig sökväg
    (`scripts/generator-matning.py`, `argp.add_argument("--ut", type=Path)`), och
    skriptet skriver dit anroparen pekar. Bisatsen bar dessutom hela vaktens
    avgränsning. Fällt av §7-granskningen av skiva 32, varv 3.*
    """
    src = Path(__file__).resolve().parent.parent / "src"

    anropare: list[str] = []
    for fil in sorted(src.rglob("*.py")):
        trad = ast.parse(fil.read_text(encoding="utf-8"), filename=str(fil))
        for nod in ast.walk(trad):
            if not isinstance(nod, ast.FunctionDef):
                continue
            for inre in ast.walk(nod):
                if not isinstance(inre, ast.Call):
                    continue
                mal = inre.func
                namn = getattr(mal, "id", None) or getattr(mal, "attr", None)
                if namn == "generera_ratext":
                    anropare.append(f"{fil.name}::{nod.name}")

    assert anropare == ["generera.py::generera_utkast"], (
        f"generera_ratext anropas från {anropare} i src/. Bara "
        "generera_utkast får göra det, eftersom bara den prövar krav_pa_svaret."
    )


def test_HELA_systemprompten_ar_bunden():
    """Varje tecken i `SYSTEM`, inte bara de numrerade raderna.

    Byggs ur ramen plus `REGLER_I_PROMPTEN`, så att regeltexten står på ETT
    ställe. En ändring var som helst i prompten gör den här raden röd.
    """
    forvantad = SYSTEMPROMPTENS_RAM.format(
        regler="\n".join(
            f"{nummer}. {REGLER_I_PROMPTEN[nummer]}"
            for nummer in sorted(REGLER_I_PROMPTEN)
        )
    )
    assert generera.SYSTEM == forvantad


def test_systemprompten_bar_ALLA_sju_reglerna():
    """En raderad ELLER TILLAGD regel ska göra den här raden röd.

    Regel 6 och 7 gick att radera med hela sviten grön innan det här testet
    fanns, trots att `docs/sparrar.md` åberopar prompten som det bärande skyddet
    för lucka 20 och 23.

    *Här stod "lucka 20, 23, 24, 26 och 27". Posterna för 24, 26 och 27 åberopar
    inte prompten, och samma skiva rättade just den uppräkningen i
    `docs/sparrar.md` och skrev in den oförändrad här. Fällt av
    §7-granskningen av skiva 32, varv 1.*
    """
    assert set(_reglerna_i_systemprompten()) == set(REGLER_I_PROMPTEN)


@pytest.mark.parametrize("nummer", sorted(REGLER_I_PROMPTEN))
def test_varje_regel_star_ORDAGRANT(nummer):
    """En URVATTNAD regel ska falla lika hårt som en raderad.

    Prövar IDENTITET och inte förekomst av fraser. Skälet står vid
    `REGLER_I_PROMPTEN`: en regel som bär sina fraser och samtidigt upphäver sig
    själv passerade det tidigare testet.
    """
    assert _reglerna_i_systemprompten()[nummer] == REGLER_I_PROMPTEN[nummer]


def test_systemprompten_bar_paragraf_elva():
    """§11:s regler ska stå i systemprompten, inte bara i spärren.

    Spärren fäller efteråt. Regeln i prompten är det som gör att den inte
    behöver fälla, och båda behövs.
    """
    for regel in ("Första person plural", "friverkstad", "tankstreck",
                  "ALDRIG ETT PRIS"):
        assert regel in generera.SYSTEM


# ------------------------------------------------- generera_utkast, helt


def test_ett_rent_svar_returneras():
    """Huvudfallet: ett svar som håller alla tre spärrarna kommer ut."""
    text = "Hej, det går bra att titta på bilen. Hör av dig så bokar vi tid."

    ut = generera.generera_utkast(FejkKlient(text), forfragan(), exempel=[])

    assert ut == text


def test_ett_fallt_svar_returneras_ALDRIG():
    """**PÅSTÅENDET SOM BÄR HELA MODULEN.** En fälld text kommer inte ut.

    `generera_utkast` kastar i stället för att returnera. Anroparen får ett
    utkast eller ett skäl, aldrig något däremellan, och kan inte råka använda en
    text som inte höll.
    """
    with pytest.raises(Sparrfalld):
        generera.generera_utkast(
            FejkKlient("Det kostar 25 000 kr."), forfragan(), exempel=[]
        )


def test_generatorn_skriver_aldrig_om_ett_fallt_svar():
    """§9.1: en fälld text är ett STOPPTECKEN, inte ett formuleringsproblem.

    Det finns ingen kod i modulen som gör om ett svar och prövar igen. Testet
    binder det genom att räkna anropen: ett fällt svar ska ge ETT anrop och ett
    kast, aldrig ett andra försök med en mildare text.
    """
    anrop = []

    class Raknande(FejkKlient):
        def create(self, **kwargs):
            anrop.append(1)
            return super().create(**kwargs)

    with pytest.raises(Sparrfalld):
        generera.generera_utkast(
            Raknande("Det kostar 25 000 kr."), forfragan(), exempel=[]
        )

    assert len(anrop) == 1
