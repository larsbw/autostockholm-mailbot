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

import json

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
    "ord", ["tjänstevikt", "släpvagnsvikt", "draganordning", "dragkrok"]
)
def test_varje_fordonsord_faller_utan_uppslag(ord):
    """Varje ord som gör svaret till ett faktapåstående om bilen.

    Parametriserat så att en ny term inte kan läggas till i mönstret utan att
    någon skriver en rad här.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_fordonsfakta_ur_uppslag(f"Bilens {ord} är godkänd.",
                                                 forfragan())


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

    Uppmätt med `scripts/par-matning.py`: 14 av 32 a-traktorsvar som ryms under
    taket bär "jag", "mig", "min" eller "mitt". De får inte bli få-exempel.
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
