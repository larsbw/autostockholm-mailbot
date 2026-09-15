"""KEDJAN från inkommande mail till utkast. SÄNDVÄG.

**INGET TEST HÄR RÖR NÄTET.** `kor` tar både klienten och hämtningen som
argument, alltså är båda utbytbara mot fejkar. Ingen rad rör en brevlåda, och
`test_kedjan_har_ingen_sandvag` prövar hela importgrafen.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext (§6).
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from src import (
    biluppgifter,
    fordonsuppslag,
    generera,
    kategorisera,
    kedja,
    ometikettera,
    vy,
)
from src.fordonsuppslag import UppslagMisslyckades, Utfall
from src.kedja import Arende, Kallfel, Kedjeutfall, Steg
from tests.sentinelpris import SENTINELPRIS_IHOP
from tests.test_vy import FejkHanterare
from tests.test_vy import peka_om_katalogerna

HINKAR = {
    "standardhink": "utkast",
    "auto": ["fråga om a-traktorkonvertering"],
    "aldrig": ["inget kundärende"],
}

# Taxonomin kedjan väljer UR. Pass 2 svarar med en av raderna eller
# `utanför listan`, aldrig med ett påhittat namn.
TAXONOMI = [
    "fråga om a-traktorkonvertering",
    "boka däckbyte",
    "inget kundärende",
]

# Ett fordon som duger: släpvagnsvikten når tröskeln och draganordning finns.
GRONT_SVAR = {
    "tjanstevikt_kg": 1450,
    "slapvagnsvikt_kg": 1500,
    "draganordning": True,
}


class FejkKlient:
    """Returnerar förbestämda svar i tur och ordning. Rör aldrig nätet.

    Kedjan gör TVÅ anrop, ett för klassificering och ett för generering, och
    fejken måste därför kunna ge olika svar. En fejk som gav samma text på båda
    hade gjort varje test till en slump.
    """

    def __init__(self, *texter: str):
        self._texter = list(texter)
        self.anrop = 0

        class Messages:
            def create(inre, **_):  # noqa: N805
                self.anrop += 1
                text = self._texter.pop(0)
                return type("Svar", (), {"content": [
                    type("Block", (), {"type": "text", "text": text})()
                ], "usage": None})()

        self.messages = Messages()


def hamta_gront(_regnr: str) -> dict:
    return dict(GRONT_SVAR)


def hamta_saknas(_regnr: str) -> None:
    return None


def hamta_kraschar(_regnr: str):
    raise ConnectionError("källan svarar inte")


def hamta_utan_draganordning(_regnr: str) -> dict:
    """Ett LYCKAT uppslag där registret säger Nej på draganordningen."""
    return {**GRONT_SVAR, "draganordning": False}


def hamta_registret_saknar_dragvikt(_regnr: str) -> dict:
    """Ingen av sidans fyra släpviktsformer finns, alltså utfall 1.

    Formen är den `biluppgifter_hamtning` lämnar: de fält som lästes, plus
    dragviktsläget under en reserverad nyckel. `slapvagnsvikt_kg` saknas, alltså
    fäller `_kontrollera` och undantaget bär läget.
    """
    return {
        "tjanstevikt_kg": GRONT_SVAR["tjanstevikt_kg"],
        "draganordning": GRONT_SVAR["draganordning"],
        biluppgifter.META_DRAGVIKT:
            biluppgifter.Dragviktslage.REGISTRET_SAKNAR.value,
    }


def hamta_dragvikt_i_annan_form(_regnr: str) -> dict:
    """Den bromsade saknas men en annan form finns, alltså utfall 4."""
    return {
        "tjanstevikt_kg": GRONT_SVAR["tjanstevikt_kg"],
        "draganordning": GRONT_SVAR["draganordning"],
        biluppgifter.META_DRAGVIKT:
            biluppgifter.Dragviktslage.ANNAN_FORM.value,
    }


def hamta_dragvikt_olasbar(_regnr: str) -> dict:
    """Fältet stod på sidan och gick inte att läsa, alltså utfall 2.

    Den tredje av de tre lägen ett misslyckat uppslag kan rapportera. Hämtaren
    saknades, och ett test som påstod sig pröva alla tre prövade två. Fällt av
    §7-granskningen av skiva 41, varv 1.
    """
    return {
        "tjanstevikt_kg": GRONT_SVAR["tjanstevikt_kg"],
        "draganordning": GRONT_SVAR["draganordning"],
        biluppgifter.META_DRAGVIKT:
            biluppgifter.Dragviktslage.TOLKAS_EJ.value,
    }


def arende(**andrat) -> Arende:
    grund = {
        "text": "Hej, går det att bygga om min bil till a-traktor?",
        "amne": "Fråga",
        "regnr": "ABC123",
        "avsandare_hash": "0" * 16,
        "tidsstampel": "2026-01-01T00:00:00+00:00",
    }
    grund.update(andrat)
    return Arende(**grund)


# ------------------------------------------------------- vägen, steg för steg


def test_hela_vagen_ger_ett_utkast():
    """Grundfallet: klassning, uppslag, generering, spärrar, utkast."""
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        "Hej, din bil går bra att bygga om. En kollega hör av sig.",
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.kategori == "fråga om a-traktorkonvertering"
    assert utfall.hink == "auto"
    assert utfall.utfall is Utfall.GRONT
    assert utfall.blev_utkast
    assert utfall.sparr is None
    assert [s.namn for s in utfall.steg] == [
        "klassificering", "uppslag", "spärrar", "utkast"
    ]


def test_en_kategori_UTANFOR_a_traktor_ger_INGET_SVAR():
    """GRINDEN. Lars beslut i skiva 51 DEL B.

    *Raden hette `test_kategori_utanfor_a_traktor_hoppar_over_uppslaget` och
    band att en sådan kategori hoppade över UPPSLAGET men gick vidare till
    generatorn. Grinden gör mer än så: den stannar före generatorn också.*

    **RADEN OM `klient.anrop` ÄR DEN SOM BÄR.** Utan den är testet grönt även om
    kedjan anropar generatorn och sedan kastar utkastet, alltså exakt den kostnad
    grinden finns för. Samma skäl som i `test_hinken_ALDRIG_...`.

    Hämtningen kraschar med flit: nås uppslaget alls är det inte överhoppat.
    Hinken är `utkast` och inte `aldrig`, alltså är det GRINDEN och ingenting
    annat som fäller den här posten.
    """
    klient = FejkKlient("boka däckbyte", "Hej, vi bokar in dig.")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.hink == "utkast"
    assert utfall.inget_svar
    assert utfall.inget_svar_skal == kedja.SKAL_OGATAD
    assert utfall.uppslag is None
    assert utfall.utfall is None
    assert utfall.utkast is None
    assert utfall.sparr is None
    # ETT ANROP, alltså klassificeringen och ingenting mer.
    assert klient.anrop == 1, "generatorn ska inte ha anropats"
    assert [s.namn for s in utfall.steg] == ["klassificering", "generering"]
    assert utfall.steg[-1] == Steg("generering", "hoppades över",
                                   kedja.SKAL_OGATAD)


def test_de_TVA_skalen_till_INGET_SVAR_HALLS_ISAR():
    """Hinken `aldrig` och grinden är olika saker, och loggen ska visa vilket.

    **UTAN DEN HÄR RADEN GÅR DE TVÅ SKÄLEN ATT SLÅ IHOP med grön svit.** Båda
    ger `inget_svar=True`, alltså skiljer inget annat fält dem åt. Skälet står i
    vyn ovanför ett mail Lars läser: en rekondbokning med texten *"kategorin står
    i hinken aldrig"* skickar honom till en rad i `config/kategorier.yaml` som
    inte finns.

    **ORDNINGEN PRÖVAS OCKSÅ, och `inget kundärende` är valt för just det.**
    Kategorin står i `aldrig` OCH är ogatad, alltså träffar båda villkoren i
    `kor` samma ärende och det som prövas först bestämmer skälet. Byter grenarna
    plats blir raden om `SKAL_ALDRIG` röd.

    *Första lydelsen lade i stället en A-TRAKTORKATEGORI i `aldrig` och påstod
    att den band ordningen. Den gör inte det: grinden släpper igenom en
    a-traktorkategori oavsett var den står, alltså faller ärendet till
    hinkgrenen i båda ordningarna och raden var grön för båda. Fällt av §7.1-
    prövningen av den här skivan.*
    """
    ogatad = kedja.kor(
        arende(), klient=FejkKlient("boka däckbyte", "onådd"),
        hamta=hamta_kraschar, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[],
    )
    i_aldrig = kedja.kor(
        arende(), klient=FejkKlient("inget kundärende", "onådd"),
        hamta=hamta_kraschar, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[],
    )

    assert "inget kundärende" not in kedja.A_TRAKTORKATEGORIER, (
        "ordningsprövningen kräver en kategori som BÅDA villkoren träffar"
    )

    assert ogatad.inget_svar and i_aldrig.inget_svar
    assert ogatad.inget_svar_skal != i_aldrig.inget_svar_skal
    assert ogatad.inget_svar_skal == kedja.SKAL_OGATAD
    assert i_aldrig.inget_svar_skal == kedja.SKAL_ALDRIG


def test_en_ogatad_kategori_far_INGEN_uppslagsbedomning():
    """Ett uppslag som aldrig gjordes får inte låta som ett misslyckat.

    **FÄLLT AV KEDJANS EGEN PROVKÖRNING i skiva 34.** En REKONDBOKNING fick
    svaret *"Vi har inte kunnat slå upp ditt fordon just nu"*, eftersom
    `utfall=None` hade en enda betydelse. Vi hade inte försökt: kategorin gatas
    inte. Kunden bad om en tid och fick besked om ett uppslag.

    Raden prövar UNDERLAGET och inte ett handskrivet svar, eftersom det är
    prompten som bär felet.
    """
    forfragan = generera.Forfragan(
        text="Hej, jag vill boka rekond.",
        kategori="boka rekond",
        utfall=None,
        uppslag=None,
        uppslag_gjordes=False,
    )

    underlag = generera._underlag(forfragan)

    assert "EJ AKTUELLT" in underlag
    assert "inte kunnat slå upp" not in underlag
    assert "ingen fordonsbedömning behövs" in underlag


def test_ett_fordon_utan_uppgifter_stoppar_INTE_kedjan():
    """`UppslagMisslyckades` är ett svar, inte ett avbrott.

    Generatorn har ett eget läge för det, och svaret säger att vi inte kunnat
    slå upp bilen. Att stoppa här hade gjort kunden svarslös.
    """
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        "Hej, vi har inte kunnat slå upp din bil. En kollega hör av sig.",
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_saknas, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.uppslag is None
    assert utfall.blev_utkast
    assert utfall.steg[1].utfall == "misslyckades"


def test_en_KRASCHAD_kalla_stoppar_kedjan():
    """En källa som är nere är inte samma sak som ett fordon utan uppgifter.

    `slag_upp`:s docstring skriver ut skillnaden, och `Kallfel` bär den vidare.
    Utan den hade ett driftavbrott sett ut som ett okänt fordon, och boten hade
    svarat som om den vetat att uppslaget gick igenom.
    """
    klient = FejkKlient("fråga om a-traktorkonvertering", "onådd")

    with pytest.raises(Kallfel):
        kedja.kor(
            arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
            taxonomi=TAXONOMI, exempel=[],
        )

    assert klient.anrop == 1, "generatorn ska inte ha anropats"


def test_ett_spärrfällt_svar_ger_INGET_utkast():
    """Spärren fäller, och kedjan bär skälet i stället för en text."""
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        f"Hej, det kostar {SENTINELPRIS_IHOP} kr.",
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.utkast is None
    assert not utfall.blev_utkast
    assert utfall.sparr == "genererat-tal-har-kalla"
    assert utfall.steg[-1] == Steg("spärrar", "fälld", "genererat-tal-har-kalla")


def test_hinken_ALDRIG_ger_INGET_SVAR_och_inget_modellanrop():
    """Lars beslut i skiva 49 DEL B. Generatorn anropas INTE.

    *Testet hette `test_hinken_stoppar_INTE_generering` och band motsatsen: att
    ett utkast produceras också för `aldrig`, eftersom skuggläget skulle mäta vad
    som HADE gått ut. Den mätningen finns inte: ramverksregel 1 säger att
    ingenting i `aldrig` någonsin får gå ut, alltså är svaret känt utan anropet.*

    **RADEN OM `klient.anrop` ÄR DEN SOM BÄR.** Utan den är testet grönt även om
    kedjan anropar generatorn och sedan kastar utkastet, vilket är precis den
    kostnad beslutet gällde: ett modellanrop per maskinmail.
    """
    klient = FejkKlient("inget kundärende", "Hej, tack för ditt meddelande.")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )

    assert utfall.hink == "aldrig"
    assert utfall.inget_svar
    assert not utfall.blev_utkast
    assert utfall.utkast is None
    assert utfall.sparr is None
    # ETT ANROP, alltså klassificeringen och ingenting mer.
    assert klient.anrop == 1, "generatorn ska inte ha anropats"
    # `hamta_kraschar` med flit: nås uppslaget alls är det inte överhoppat.
    assert [s.namn for s in utfall.steg] == ["klassificering", "generering"]
    assert utfall.steg[-1] == Steg("generering", "hoppades över", "hinken aldrig")


def test_hinken_UTKAST_genererar_fortfarande():
    """Motsatsen. Utan den här raden är testet ovan grönt även om kedjan
    slutat generera helt.

    Skuggläget står och faller med att `utkast`-hinken fortfarande producerar
    något att läsa, och skiva 49 rörde bara `aldrig`.

    *Raden använde `boka däckbyte`, som sedan skiva 51 fälls av GRINDEN och
    aldrig når generatorn. Kategorin är bytt mot en a-traktorkategori, alltså
    prövar raden nu det den alltid påstod sig pröva: att hinken `utkast` inte i
    sig stoppar genereringen. `HINKAR` lägger `fråga om a-traktorkonvertering` i
    `auto`, och därför står den här i en egen hinkuppsättning.*
    """
    hinkar = {**HINKAR, "auto": []}
    klient = FejkKlient(
        "fråga om a-traktorkonvertering", "Hej, din bil går bra att bygga om."
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=hinkar,
        taxonomi=TAXONOMI, exempel=[],
    )

    assert utfall.hink == "utkast"
    assert not utfall.inget_svar
    assert utfall.blev_utkast
    assert klient.anrop == 2


def test_INGET_SVAR_ger_varken_textfalt_eller_omdomesknappar():
    """Vyn visar posten som en egen sort. Lars order i skiva 49 DEL B.

    Renderingen prövas genom `till_granskningsfall`, alltså hela vägen från
    kedjans utfall och inte mot en handkonstruerad `Granskningsfall`. Sätter
    producenten inte flaggan blir raden röd.
    """
    klient = FejkKlient("inget kundärende", "onådd")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    post = kedja.till_granskningsfall(arende(), utfall, skarp=True)

    assert post.inget_svar
    assert post.forslag == ""
    assert post.sparr == ""

    sida = vy.rendera_granskning(
        post.fall, post.forslag, post.sparr, 0,
        uppslagskalla=post.uppslagskalla, inget_svar=post.inget_svar,
    )

    assert "INGET SVAR SKRIVS" in sida
    assert "<textarea" not in sida
    for omdome in vy.OMDOMESVARDEN:
        assert f"value='{omdome}'" not in sida


def test_INGET_SVAR_bar_INGEN_uppslagskalla():
    """Härkomstraden säger vad vikterna i ett utkast är värda, och det finns
    inget utkast.

    Den generella grenen hade sagt *"Inget uppslag gjordes: kategorin gatar det
    inte"*, vilket är sant om uppslaget och läses som ett besked om ett svar som
    aldrig skrevs.
    """
    klient = FejkKlient("inget kundärende", "onådd")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )

    assert kedja.uppslagskalla(arende(), utfall, skarp=True) == ""


def test_INGET_SVAR_star_i_loggraden(tmp_path, monkeypatch):
    """Skuggläget ska kunna räkna maskinmailen för sig.

    `blev_utkast: false` med `sparr: null` betyder annars antingen ett källfel
    eller ett INGET SVAR, och de två är olika saker.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"
    klient = FejkKlient("inget kundärende", "onådd")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    post = kedja.logga_beslut(arende(), utfall, loggfil=loggfil)

    assert post["inget_svar"] is True
    assert post["blev_utkast"] is False
    assert post["hink"] == "aldrig"

    # SAMMA FÄLTUPPSÄTTNING som de två andra utfallen, så att skuggläget läser
    # alla tre med samma kod. Samma egenskap som `logga_kallfel` prövas för.
    kallfel = kedja.logga_kallfel(arende(), Kallfel("ConnectionError"),
                                  loggfil=loggfil)
    assert sorted(post) == sorted(kallfel)


def test_klassningen_skickar_PASS_2_s_SYSTEMPROMPT():
    """Vilken systemprompt som går ut, inte bara vad filtret gör med svaret.

    **DEN HÄR RADEN ÄR SKIVANS HUVUDRÄTTELSE, och den var OBUNDEN.** Bytet från
    pass 1 till pass 2 gick att återställa med hela sviten grön, eftersom
    fejkklienten svarar likadant oavsett prompt. `test_..._binds_av_taxonomin`
    nedan prövar bara `ometikettera_en`:s filter, alltså påstod dess namn mer än
    testet gjorde. Fällt av §7-granskningen av skiva 34, varv 1.

    Raden fångar systemprompten och kräver att den bär taxonomins rader och
    förbudet mot egna namn, alltså det pass 1 uttryckligen INTE gör.
    """
    sedda: list[str] = []

    class Spion(FejkKlient):
        def __init__(self):
            super().__init__("fråga om a-traktorkonvertering", "Hej.")
            yttre = self

            class Messages:
                def create(inre, **falt):  # noqa: N805
                    sedda.append(falt["system"])
                    yttre.anrop += 1
                    text = yttre._texter.pop(0)
                    return type("Svar", (), {"content": [
                        type("Block", (), {"type": "text", "text": text})()
                    ], "usage": None})()

            self.messages = Messages()

    kedja.kor(
        arende(), klient=Spion(), hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )

    # **HELA PROMPTEN, ORDAGRANT, och inte de fraser någon råkade räkna upp.**
    # Första lydelsen prövade tre fraser plus taxonomins rader. Den gick att
    # passera med en handskriven sträng som bar just de tre och saknade
    # *"Svara med EXAKT en av raderna ovan, ordagrant"* och hela
    # `utanför listan`-utgången. Det är samma defekt som `test_HELA_
    # systemprompten_ar_bunden` finns för på generatorns sida, alltså fanns
    # egenskapen redan i repot och tillämpades bara på den ena prompten.
    # Fällt av §7-granskningen av skiva 34, varv 2.
    #
    # `kategorisera_en` lägger prompten i ett cache-block och FOGAR PÅ sitt
    # kontextstycke, alltså är det som går ut inte enbart `bygg_system_pass2`.
    # Raden binder därför prefixet ordagrant och kräver att resten är exakt det
    # kontextstycke `kategorisera` äger. Ingen fras är utelämnad.
    utgaende = sedda[0][0]["text"]
    forvantat = ometikettera.bygg_system_pass2(TAXONOMI)

    assert utgaende.startswith(forvantat)
    assert utgaende[len(forvantat):] == kategorisera.KONTEXTREGEL


def test_klassningens_prompt_bar_sina_BARANDE_led():
    """Vad bindningen ovan skyddar, uttryckt så att en läsare ser det.

    Raden ovan är en likhet och säger inget om VARFÖR prompten ser ut som den
    gör. Den här säger det, och blir röd om ett bärande led försvinner ur
    `ometikettera.bygg_system_pass2` utan att någon tänkt efter.
    """
    prompt = ometikettera.bygg_system_pass2(TAXONOMI)

    assert "Välj den kategori ur listan nedan" in prompt
    assert "Svara med EXAKT en av raderna ovan, ordagrant" in prompt
    assert "Hittar du på ett eget namn är svaret fel" in prompt
    # Utgången i PROMPTEN heter `övrigt`. `ometikettera.UTANFOR` är kodsidans
    # sentinel, som filtret sätter när svaret ändå hamnar utanför listan, och
    # den står inte i prompten. Prövat mot `src/ometikettera.py:183`.
    assert f"Passar ingen kategori, svara exakt: {ometikettera.OVRIGT}" in prompt
    for kategori in TAXONOMI:
        assert kategori in prompt
    # Pass 1:s kännemärke får INTE finnas: det är den prompt bytet gällde.
    assert "Använd INGEN lista" not in prompt


def test_en_OKAND_kategori_gatar_inte_uppslaget():
    """Ett påhittat kategorinamn ska bli `utanför listan`, aldrig gata något.

    **NAMNET SA TIDIGARE `..._ar_PASS_2_och_binds_av_taxonomin`**, och det
    påstod mer än raden gör: den överlevde en fällning som satte tillbaka pass
    1:s systemprompt, alltså band den ingenting om vilket pass som körs. §7.1
    ger två utvägar, döp om eller gör äkta. Bindningen ligger i testet ovan, och
    det här är omdöpningen. Fällt av §7-granskningen av skiva 34, varv 1 och 2.

    **FÄLLT AV KEDJANS EGEN PROVKÖRNING i skiva 34.** Första lydelsen anropade
    pass 1, upptäcktspasset, vars systemprompt säger *"Använd INGEN lista"*.
    Varje a-traktormail fick då ett påhittat namn, och eftersom inget av dem
    står i taxonomin utlöstes fordonsuppslagets grind ALDRIG. Tio av tio
    ärenden hoppade över uppslaget.

    Raden prövar just det: modellen svarar med ett namn utanför listan, och
    kedjan ska då varken hinka det som en känd kategori eller slå upp något.
    """
    klient = FejkKlient("offert på a-traktorombyggnad", "Hej, vi återkommer.")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )

    assert utfall.kategori == ometikettera.UTANFOR
    # `TAXONOMI` här är en fixtur utan `utanför listan` i någon hink, alltså
    # faller den till standardhinken. I `config/kategorier.yaml` står den i
    # `aldrig`, vilket är den säkrare riktningen. Raden prövar att en OKÄND
    # kategori inte gatar uppslaget, inte vilken hink produktionen ger den.
    assert utfall.hink == HINKAR["standardhink"]
    assert utfall.steg[1].utfall == "hoppades över"


def test_en_kategori_UR_taxonomin_gatar_uppslaget():
    """Motsatsen: ett namn som står i listan ska nå uppslaget.

    Utan den här raden hade `test_klassningen_ar_PASS_2...` varit grön även om
    kedjan slutat gata helt.
    """
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        "Hej, din bil går bra att bygga om.",
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )

    assert utfall.steg[1].utfall == "lyckades"
    assert utfall.utfall is Utfall.GRONT


def test_vagen_slutar_i_vyn():
    """Ett utkast ur kedjan ska gå att visa i granskningsläget.

    **RUTTEN FANNS MEN PRODUCENTEN SAKNADES.** `/granskning/N` renderade alltid
    *"Inga förslag"*, eftersom inget i repot lämnade en `Kedjeutfall` till vyn.
    Fällt av §7-granskningen av skiva 34, varv 1.
    """
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        "Hej, din bil går bra att bygga om.",
    )
    ar = arende()

    utfall = kedja.kor(
        ar, klient=klient, hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    granskningsfall = kedja.till_granskningsfall(ar, utfall, skarp=True)

    # Vägen prövas HELA vägen fram till renderad sida, och inte bara till att
    # en hanterare gick att bygga. `assert hanterare is not None` stod här och
    # bevisade ingenting: `bygg_hanterare` returnerar alltid en klass.
    hanterare = vy.bygg_hanterare([], granskning=[granskningsfall])
    fejk = FejkHanterare(hanterare, "/granskning/0")
    fejk.get()

    assert fejk.kod == 200
    assert utfall.utkast in fejk.svar

    assert granskningsfall.forslag == utfall.utkast
    assert granskningsfall.sparr == ""
    assert granskningsfall.fall.etikett == utfall.kategori
    assert granskningsfall.fall.avsandare_hash == ar.avsandare_hash


def test_ett_SPARRAT_utfall_blir_ett_sparrat_granskningsfall():
    """En fälld post bär spärren och INGET förslag.

    `rendera_granskning` vägrar rendera ett textfält när `sparr` är satt, och
    den vägran är verkningslös om konverteringen råkar sätta båda.
    """
    klient = FejkKlient(
        "fråga om a-traktorkonvertering", f"Hej, det kostar {SENTINELPRIS_IHOP} kr."
    )
    ar = arende()

    utfall = kedja.kor(
        ar, klient=klient, hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    granskningsfall = kedja.till_granskningsfall(ar, utfall, skarp=True)

    assert granskningsfall.sparr == "genererat-tal-har-kalla"
    assert granskningsfall.forslag == ""


def test_kedjan_har_ingen_sandvag():
    """SPÄRR: hela importgrafen, inte bara den här filen.

    `krav_pa_sandvagsfrihet` vandrar modulerna kedjan drar in och läser
    källtexten i var och en. Lars ordning i skiva 34: spärren gäller HELA
    kedjan.
    """
    vy.krav_pa_sandvagsfrihet("src.kedja")


def test_kedjans_a_traktorkategorier_matchar_vyns():
    """De två uppräkningarna får inte glida isär.

    Kedjan bär sin egen tupel för att inte bli beroende av vyns rendering, och
    då behövs en rad som binder att de säger samma sak.
    """
    assert set(kedja.A_TRAKTORKATEGORIER) == set(vy.A_TRAKTORETIKETTER)


def test_GENERATORNS_a_traktoretiketter_matchar_de_andra_TVA():
    """SPÄRR: det finns TRE kopior av samma tre strängar, inte två.

    `src/generera.py` bär en egen `A_TRAKTORETIKETTER` bredvid kedjans och vyns,
    och ingenting band den. Skiva 52 lät dessutom
    `test_kedjans_tre_a_traktorkategorier_bar_ALLA_prisposten` mäta
    `PRISNYCKEL_FOR_KATEGORI` mot just den obundna kopian, alltså kunde tupeln
    och kartan bytas TILLSAMMANS till en annan kategori med hela sviten grön.

    **DRIFTFÖLJDEN ÄR ATT A-TRAKTORPROMPTEN TAPPAR PRISET.** Glider generatorns
    kopia får kedjans tre kategorier ingen post i kartan, alltså `INGA_PRISER`,
    och svaren slutar citera priset — precis det den nya raden säger sig hindra.

    Fällt av §7-granskningen av skiva 52.
    """
    assert set(generera.A_TRAKTORETIKETTER) == set(vy.A_TRAKTORETIKETTER)
    assert set(generera.A_TRAKTORETIKETTER) == set(kedja.A_TRAKTORKATEGORIER)


def test_vyns_INGET_SVAR_skal_matchar_kedjans():
    """De två uppräkningarna får inte glida isär, samma skäl som raden ovan.

    `src/vy.py` kan inte importera `src/kedja.py`: importen går åt andra hållet.
    Vyns tabell bär därför strängarna skrivna en gång till, och utan den här
    raden faller varje post tyst till `_INTETSKAL_OKANT` den dag en konstant
    formuleras om. Sidan hade då sagt *"posten är sparad av en körning före
    skiva 51"* om en post som kördes i dag.
    """
    assert set(vy._INTETSKAL) == {kedja.SKAL_ALDRIG, kedja.SKAL_OGATAD}


def test_VYN_sager_vilket_av_de_tva_skalen_det_var():
    """Skälet ovanför mailet ska stämma med posten.

    **RADEN BINDER RENDERAREN, alltså att `rendera_granskning` skriver OLIKA
    meningar för de två skälen.** Visade den samma mening för båda vore den
    falsk för det ena: en rekondbokning får inget svar av GRINDEN, inte av en
    rad i `config/kategorier.yaml`, och Lars som letar efter den raden hittar
    ingen.

    *Här stod att `inget_svar_skal` GÅR ATT KOPPLA UR med grön svit utan den
    här raden. Påståendet var för brett: raden prövar renderaren och säger
    ingenting om VÄGEN dit. Fältet gick att strypa i `bygg_hanterare._granskning`
    med hela sviten grön, den här raden inräknad. Det ledet bärs sedan
    §7-granskningen av skiva 51 av `test_SKALET_nar_sidan_GENOM_RUTTEN` i
    `tests/test_vy.py`, och de två raderna vaktar alltså var sitt led.*
    """
    sidor = {}
    for skal in (kedja.SKAL_ALDRIG, kedja.SKAL_OGATAD):
        sidor[skal] = vy.rendera_granskning(
            vy.Fall(etikett="boka rekond", kalla="kedjan", text="Hej.",
                    tidsstampel="2026-01-01T00:00:00+00:00",
                    avsandare_hash="0" * 16),
            "", inget_svar=True, inget_svar_skal=skal,
        )

    assert sidor[kedja.SKAL_ALDRIG] != sidor[kedja.SKAL_OGATAD]
    assert "aldrig" in sidor[kedja.SKAL_ALDRIG]
    assert "aldrig" not in sidor[kedja.SKAL_OGATAD]
    assert "a-traktor" in sidor[kedja.SKAL_OGATAD]
    for sida in sidor.values():
        assert "INGET SVAR SKRIVS" in sida
        assert "<textarea" not in sida


def test_en_post_UTAN_skal_far_ingen_uppfunnen_forklaring():
    """En fil sparad före skiva 51 bär ingen nyckel, och gissningen vore fel.

    `_INTETSKAL_OKANT` säger att skälet inte står i posten. Att låta den falla
    till den vanligaste meningen hade gett en gammal post en förklaring ingen
    körning skrivit.
    """
    sida = vy.rendera_granskning(
        vy.Fall(etikett="boka rekond", kalla="kedjan", text="Hej.",
                    tidsstampel="2026-01-01T00:00:00+00:00",
                    avsandare_hash="0" * 16),
        "", inget_svar=True, inget_svar_skal="",
    )

    assert "INGET SVAR SKRIVS" in sida
    assert "bär inget skäl" in sida
    assert "hinken" not in sida


def test_SKALET_overlever_vagen_till_disk_och_tillbaka(tmp_path, monkeypatch):
    """Vyn läser posterna ur `data/granskningsfall.jsonl` mellan körningar.

    Utan den här raden går fältet att utelämna ur `spara_granskningsfall` med
    grön svit, och varje post som lästes tillbaka hade då renderats som en post
    utan skäl.
    """
    klient = FejkKlient("boka däckbyte", "onådd")
    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    # `krav_pa_skrivbar_sokvag` binder `data/` ELLER `logg/` UNDER REPOTS ROT,
    # alltså måste roten peka om innan filen får skrivas.
    peka_om_katalogerna(monkeypatch, tmp_path)
    fil = tmp_path / "data" / "granskningsfall.jsonl"
    fil.parent.mkdir(parents=True)

    vy.spara_granskningsfall(
        [kedja.till_granskningsfall(arende(), utfall, skarp=True)], fil=fil)
    tillbaka = vy.las_granskningsfall(fil)

    assert tillbaka[0].inget_svar
    assert tillbaka[0].inget_svar_skal == kedja.SKAL_OGATAD


def test_SPARRENS_SKAL_nar_ALDRIG_granskningsfallet():
    """§6. `Sparrfalld.skal` bär text lyft ORDAGRANT ur modellens svar.

    Skrivs ett telefonnummer ut lyder skälet *"talet ... kommer varken ur
    uppslaget eller ur config"* med numret inbakat. `Granskningsfall` skrivs till
    disk och renderas på sidan, alltså får `skal` aldrig följa med dit.
    `inget_svar_skal` får det, och skillnaden är att den bär en av kedjans egna
    två fasta strängar.

    Raden finns därför att de två fälten ligger bredvid varandra på
    `Kedjeutfall` och är ett tangenttryck isär.
    """
    klient = FejkKlient(
        "fråga om a-traktorkonvertering",
        f"Hej, det kostar {SENTINELPRIS_IHOP} kr.",
    )
    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    post = kedja.till_granskningsfall(arende(), utfall, skarp=True)

    assert utfall.skal, "spärren ska ha lämnat ett skäl att pröva mot"
    assert post.inget_svar_skal == ""
    assert utfall.skal not in dataclasses.asdict(post).values()


def test_a_traktorkategorierna_FINNS_i_taxonomin():
    """Grinden kan bara utlösas av ett namn klassningen kan svara.

    **EN TAXONOMI SOM GLIDER GER EXAKT SYMPTOMET "grinden utlöstes aldrig"**,
    vilket är felet skivans provkörning fällde. Kedjan gatar på namn ur
    `A_TRAKTORKATEGORIER`, och pass 2 kan bara svara med namn ur
    `data/taxonomi.json`. Står de isär är grinden död utan att något larmar.
    """
    # `data/` är gitignorerad, alltså finns filen bara på en maskin som kört
    # mining. Raden HOPPAS ÖVER i stället för att vara falskt grön: ett test som
    # bara går att köra på en maskin bevisar ingenting på de andra, och ett som
    # tiger om det är värre än ett som säger ifrån.
    if not kedja.TAXONOMIFIL.exists():
        pytest.skip(f"{kedja.TAXONOMIFIL} saknas, kräver en körd mining")

    taxonomi = json.loads(kedja.TAXONOMIFIL.read_text(encoding="utf-8"))

    saknade = [k for k in kedja.A_TRAKTORKATEGORIER if k not in taxonomi]
    assert not saknade, (
        f"{saknade} gatar uppslaget men finns inte i taxonomin, alltså kan "
        "klassningen aldrig svara dem och grinden utlöses aldrig."
    )


def test_en_kategori_i_TVA_hinkar_larmar():
    """SPÄRR: kedjan väljer inte åt Lars.

    `scripts/kategoristatus.py` larmar i samma läge med motiveringen att ett
    synligt utfall är bättre än ett tyst. En sändvägsmodul som i stället valde
    den mest tillåtande hinken hade gjort motsatsen.
    """
    trasiga = {"standardhink": "utkast", "auto": ["x"], "aldrig": ["x"]}

    with pytest.raises(ValueError):
        kedja._hink_for("x", trasiga)


# ------------------------------------------------------------ DEL C: loggen


def test_loggen_bar_det_lars_bad_om(tmp_path, monkeypatch):
    """Kategori, uppslagets utfall, spärrar, och om det blev ett utkast."""
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"
    utfall = Kedjeutfall(
        kategori="fråga om a-traktorkonvertering",
        hink="auto",
        utfall=Utfall.GULT,
        sparr="genererat-tal-har-kalla",
        skal="talet 14 saknar källa",
        steg=(Steg("klassificering", "fråga om a-traktorkonvertering"),),
    )

    post = kedja.logga_beslut(arende(), utfall, loggfil=loggfil)

    assert post["kategori"] == "fråga om a-traktorkonvertering"
    assert post["uppslag"] == "gult"
    assert post["sparr"] == "genererat-tal-har-kalla"
    assert post["blev_utkast"] is False
    assert post["hink"] == "auto"


def test_provskriptet_lamnar_vidare_sin_EGNA_kallflagga():
    """Skriptet ska skicka VARIABELN `skarp`, aldrig en literal.

    *Raden hette `..._vilken_kalla_det_anvande` och sammanfattades som att
    härkomsten aldrig kan påstå fel källa. Den band bara att argumentet FINNS:
    `skarp=True` hårdkodat passerade grönt, och då renderar en `--fixtur`-körning
    "Uppslag mot biluppgifter.se" ovanför konstruerade vikter. §7.1 ger två
    utvägar, döp om eller gör äkta, och den här raden gör båda. Fällt av
    §7-granskningen av skiva 36, varv 2.*

    **INGEN TESTFIL RÖR `scripts/kedja-prov.py`**, alltså band ingenting att det
    faktiskt skickar `skarp`. Ett bortglömt argument hade renderat *"Uppslag mot
    biluppgifter.se"* ovanför vikter konstruerade ur ett registreringsnummer.

    Första skyddet är att `skarp` saknar förval, alltså blir det `TypeError` i
    stället för en lögn. Den här raden är det andra: den läser KÄLLTEXTEN, precis
    som `krav_pa_sandvagsfrihet` gör, och fäller om anropet slutar bära
    argumentet. Fällt av §7-granskningen av skiva 36, varv 1.
    """
    kalla = (kedja.ROT / "scripts" / "kedja-prov.py").read_text(encoding="utf-8")

    assert "till_granskningsfall(" in kalla
    for stycke in kalla.split("till_granskningsfall(")[1:]:
        anropet = stycke.split(")")[0] + stycke.split(")")[1][:40]
        assert "skarp=skarp" in anropet, (
            "kedja-prov.py anropar till_granskningsfall utan att lämna vidare "
            f"sin egen kallflagga: {anropet.strip()!r}. En literal här gör att "
            "vyn kan påstå fel källa."
        )

    # Och att flaggan HÄRLEDS UR `--fixtur` i stället för att sättas en gång för
    # alla. Utan raden vore `skarp = True` överst i filen grönt.
    #
    # *Här stod att raden binder att flaggan "FAKTISKT följer valet av
    # hämtning". Det gör den inte: `hamta`-raden går att invertera med grön
    # svit, och då renderar en `--fixtur`-körning "Uppslag mot biluppgifter.se".
    # Två rader som båda läser `args.fixtur` är inte samma sak som en koppling
    # mellan dem. Fällt av §7-granskningen av skiva 36, varv 3.*
    assert "skarp = not args.fixtur" in kalla
    assert "bygg_fixturkalla() if args.fixtur else bygg_skarp_kalla()" in kalla


def test_till_granskningsfall_FYLLER_uppslagskallan():
    """Att funktionen finns räcker inte. Den ska KOPPLAS in.

    Utan raden gick `uppslagskalla=...` att byta mot en tom sträng i
    `till_granskningsfall` med hela sviten grön, alltså band de tre raderna nedan
    bara funktionens INNEHÅLL och inte att vyn får det. Fältet hade tyst
    försvunnit och sidan visat ingen härkomst alls.

    Uppmätt av §7.1-prövningen av skiva 36.
    """
    utfall = Kedjeutfall(
        kategori="fråga om a-traktorkonvertering", hink="auto", utkast="Hej.",
        steg=(Steg("uppslag", "lyckades", "gront"),),
    )

    skarpt = kedja.till_granskningsfall(arende(regnr="ABC123"), utfall, skarp=True)
    fixtur = kedja.till_granskningsfall(
        arende(regnr="ABC123"), utfall, skarp=False)

    assert "biluppgifter.se" in skarpt.uppslagskalla
    assert "FIXTUR" in fixtur.uppslagskalla


def test_uppslagskallan_skiljer_SKARPT_fran_FIXTUR():
    """Raden läses bredvid ett utkast som kan bära vikter.

    Skillnaden mellan en avläst tjänstevikt och en konstruerad syns inte i
    texten, alltså måste den stå bredvid den.
    """
    utfall = Kedjeutfall(
        kategori="fråga om a-traktorkonvertering", hink="auto", utkast="Hej.",
        steg=(Steg("uppslag", "lyckades", "gront"),),
    )

    assert "biluppgifter.se" in kedja.uppslagskalla(
        arende(regnr="ABC123"), utfall, skarp=True)
    assert "FIXTUR" in kedja.uppslagskalla(
        arende(regnr="ABC123"), utfall, skarp=False)


def test_uppslagskallan_skiljer_SAKNAT_REGNR_fran_MISSLYCKAT_UPPSLAG():
    """Lars invändning i skiva 36 gällde precis den här skillnaden.

    En post spärrades av `genererat-tal-har-kalla` i stället för att slås upp.
    Spärren var rätt; uppslaget uteblev. Ett mail utan registreringsnummer och
    ett uppslag som föll ser likadana ut i utkastet, och läsaren ska kunna se
    vilket det var utan att gissa.
    """
    utfall = Kedjeutfall(
        kategori="fråga om a-traktorkonvertering", hink="auto", utkast="Hej.",
        steg=(Steg("uppslag", "misslyckades", "registreringsnummer saknas"),),
    )

    utan = kedja.uppslagskalla(arende(regnr=None), utfall, skarp=True)
    med = kedja.uppslagskalla(arende(regnr="ABC123"), utfall, skarp=True)

    assert "BÄR INGET REGISTRERINGSNUMMER" in utan
    assert "MISSLYCKADES" in med
    assert utan != med


def test_uppslagskallan_sager_ifran_nar_INGET_UPPSLAG_GJORDES():
    """En kategori som inte gatas ska inte se ut som ett misslyckat uppslag.

    Samma skillnad som `_bedomning`:s tredje läge finns för, se skiva 34.
    """
    utfall = Kedjeutfall(
        kategori="boka däckbyte", hink="utkast", utkast="Hej.",
        steg=(Steg("uppslag", "hoppades över", "kategorin gatas inte"),),
    )

    text = kedja.uppslagskalla(arende(), utfall, skarp=True)

    assert "Inget uppslag gjordes" in text
    assert "MISSLYCKADES" not in text


def test_ett_KALLFEL_lamnar_ocksa_en_rad(tmp_path, monkeypatch):
    """Ett driftavbrott som inte loggas ser ut som ett ärende som aldrig kom in.

    `kor` kastar `Kallfel` och anroparen hoppade vidare, alltså lämnade ett
    nere-liggande biluppgifter.se INGEN rad alls. Skuggläget ska kunna mäta hur
    ofta källan svek, och den skillnaden är vad `Kallfel` byggdes för att
    bevara. Fällt av §7-granskningen av skiva 34, varv 2.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"

    post = kedja.logga_kallfel(
        arende(), Kallfel("TimeoutError: källan svarade inte"), loggfil=loggfil
    )

    assert post["blev_utkast"] is False
    assert post["kategori"] is None
    assert post["steg"][0]["namn"] == "källa"
    # SAMMA fältuppsättning som en vanlig rad, så att skuggläget läser båda med
    # samma kod i stället för att grena på vilken sorts rad det är.
    vanlig = kedja.logga_beslut(
        arende(), Kedjeutfall(kategori="x", hink="utkast", utkast="Hej."),
        loggfil=loggfil,
    )
    assert sorted(post) == sorted(vanlig)


def test_KALLFELSRADEN_bar_ALDRIG_undantagets_MEDDELANDE(tmp_path, monkeypatch):
    """§6: meddelandet bär ett REGISTRERINGSNUMMER när requests kastar.

    **`Kallfel` BYGGS AV ANROPARENS HÄMTFUNKTION**, inte av strängar
    `src/fordonsuppslag.py` äger. En `ConnectionError` lyder *"...Max retries
    exceeded with url: /fordon/ABC123"*. §6 namnger registreringsnummer som
    persondata och förbjuder dem i `logg/`.

    *Första lydelsen asserterade att `arende.text` saknades i loggen. Den läste
    ett fält `logga_kallfel` ALDRIG rör, alltså var den grön även med `detalj`
    satt till tom sträng: vakuös enligt §7.1. Fällt av §7-granskningen av skiva
    34, varv 3.*
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"

    fel = Kallfel(
        "ConnectionError",
        "HTTPSConnectionPool(host='biluppgifter.se'): "
        "Max retries exceeded with url: /fordon/XYZ789",
    )
    kedja.logga_kallfel(arende(), fel, loggfil=loggfil)

    innehall = loggfil.read_text(encoding="utf-8")
    assert "XYZ789" not in innehall
    assert "biluppgifter.se" not in innehall
    # Typen SKA stå kvar: utan den vet skuggläget inte att källan svek.
    assert json.loads(innehall)["steg"][0]["detalj"] == "ConnectionError"


def test_KALLFELET_bar_meddelandet_for_den_vid_TERMINALEN(tmp_path, monkeypatch):
    """Undantaget självt får bära allt. Det är loggen som är gränsen.

    Raden finns för att nästa läsare inte ska "förenkla" bort meddelandet ur
    `Kallfel` i tron att §6 kräver det. §6 gäller det som persisteras.
    """
    fel = Kallfel("ConnectionError", "Max retries exceeded with url: /fordon/X")

    assert "Max retries" in str(fel)
    assert fel.sort == "ConnectionError"


def test_loggen_bar_ALDRIG_utkastets_text(tmp_path, monkeypatch):
    """§6: utkastet bär kundens namn och bilmodell.

    En logg som bär texten blir en persondatafil som lever kvar. Raden säger att
    ett utkast blev till och hur långt det var, aldrig vad det stod i.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"
    hemligt = "Hej Sigrid, din Volvo V50 går bra att bygga om."
    utfall = Kedjeutfall(kategori="x", hink="utkast", utkast=hemligt)

    kedja.logga_beslut(arende(), utfall, loggfil=loggfil)

    innehall = loggfil.read_text(encoding="utf-8")
    assert hemligt not in innehall
    assert "Sigrid" not in innehall
    assert json.loads(innehall)["utkast_tecken"] == len(hemligt)


def test_loggen_bar_ALDRIG_SPARRENS_SKAL(tmp_path, monkeypatch):
    """§6: spärrens skäl är byggt av strängar lyfta UR modellens svar.

    **DET HÄR HADE REDAN HÄNT I DRIFT när granskningen mätte loggen.**
    `Sparrfalld.skal` lyder *"talet 0701234567 kommer varken ur uppslaget eller
    ur config"*, alltså bär den ett telefonnummer rakt ur utkastet.
    `genererat-fordonsfaktum` bär på samma sätt ett ord ur texten.

    Det maskinläsbara som skuggläget behöver är VILKEN spärr som fällde, och det
    står i `sparr`. Fällt av §7-granskningen av skiva 34, varv 1.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"
    utfall = Kedjeutfall(
        kategori="x",
        hink="utkast",
        sparr="genererat-tal-har-kalla",
        skal="talet 0701234567 kommer varken ur uppslaget eller ur config",
    )

    post = kedja.logga_beslut(arende(), utfall, loggfil=loggfil)

    assert post["sparr"] == "genererat-tal-har-kalla"
    assert "skal" not in post
    assert "0701234567" not in loggfil.read_text(encoding="utf-8")


def test_loggen_bar_ALDRIG_en_avsandaradress(tmp_path, monkeypatch):
    """§6: loggar bär hashade avsändare, aldrig adresser."""
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"
    utfall = Kedjeutfall(kategori="x", hink="utkast")

    kedja.logga_beslut(
        arende(avsandare_hash="abc123def456"), utfall, loggfil=loggfil
    )

    post = json.loads(loggfil.read_text(encoding="utf-8"))
    assert post["avsandare_hash"] == "abc123def456"
    assert "@" not in loggfil.read_text(encoding="utf-8")


def test_beslutsloggen_ar_APPEND_ONLY(tmp_path, monkeypatch):
    """§0 RAMVERKSREGEL 4, som är obrytbar.

    En andra skrivning får aldrig radera den första. Raden finns därför att en
    öppning i `w`-läge är en enda bokstavs skillnad, och den skillnaden skulle
    tysta hela underlaget för skuggläget utan att något annat test märkte det.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    loggfil = tmp_path / "logg" / "beslut.jsonl"

    kedja.logga_beslut(arende(), Kedjeutfall(kategori="ett", hink="utkast"),
                       loggfil=loggfil)
    kedja.logga_beslut(arende(), Kedjeutfall(kategori="tva", hink="utkast"),
                       loggfil=loggfil)

    rader = loggfil.read_text(encoding="utf-8").strip().splitlines()
    assert len(rader) == 2
    assert json.loads(rader[0])["kategori"] == "ett"
    assert json.loads(rader[1])["kategori"] == "tva"


def test_loggen_vagrar_skriva_utanfor_logg_och_data(tmp_path):
    """`krav_pa_skrivbar_sokvag` gäller även den här loggen.

    **MÅLET LIGGER I `tmp_path` OCH INTE I REPOT, och det ledet är fällt fram.**
    Raden pekade på `kedja.ROT / "src" / "smugglad.jsonl"`, alltså på det
    RIKTIGA repot. Så länge spärren håller skrivs ingenting, men ett negativtest
    vars enda skydd är den spärr det prövar är fel konstruerat: fälls spärren av
    en §7.1-prövning skapas filen på riktigt, i en SPÅRAD katalog, och varken
    `.gitignore`, `.dockerignore` eller `scripts/persondatakontroll.py` hindrar
    att den committas. Uppmätt: filen fanns i arbetsträdet och följde med in i
    den byggda avbilden. Fällt av §7-granskningen av skiva 53.
    """
    with pytest.raises(vy.Skrivfel):
        kedja.logga_beslut(
            arende(),
            Kedjeutfall(kategori="x", hink="utkast"),
            loggfil=tmp_path / "src" / "smugglad.jsonl",
        )


# ------------------------------------- SKIVA 40 DEL B: vad som FÅR påstås sakna


def _mangden(hamta) -> frozenset[str]:
    """Kör kedjan och ger den mängd frånvaropåståenden generatorn fick."""
    sedda: list[generera.Forfragan] = []
    klient = FejkKlient("fråga om a-traktorkonvertering", "Hej, vi hör av oss.")
    riktig = generera.generera_utkast

    def fangar(klienten, forfragan, **rest):
        sedda.append(forfragan)
        return riktig(klienten, forfragan, **rest)

    generera.generera_utkast = fangar
    try:
        kedja.kor(arende(), klient=klient, hamta=hamta, hinkar=HINKAR,
                  taxonomi=TAXONOMI, exempel=[])
    finally:
        generera.generera_utkast = riktig

    return sedda[0].franvaro_far_pastas


def _forfragan_for(arendet) -> generera.Forfragan:
    """Kör kedjan och ger den förfrågan generatorn fick."""
    sedda: list[generera.Forfragan] = []
    klient = FejkKlient("fråga om a-traktorkonvertering", "Hej, vi hör av oss.")
    riktig = generera.generera_utkast

    def fangar(klienten, forfragan, **rest):
        sedda.append(forfragan)
        return riktig(klienten, forfragan, **rest)

    generera.generera_utkast = fangar
    try:
        # `hamta_saknas` OCH INTE `hamta_kraschar`: en källa som kastar blir
        # `Kallfel` och stoppar kedjan innan generatorn nås, alltså hade
        # `sedda` varit tom för det ärende som BÄR ett nummer.
        kedja.kor(arendet, klient=klient, hamta=hamta_saknas, hinkar=HINKAR,
                  taxonomi=TAXONOMI, exempel=[])
    finally:
        generera.generera_utkast = riktig

    return sedda[0]


def test_kedjan_sager_till_generatorn_om_mailet_BAR_ETT_NUMMER():
    """SKIVA 46 DEL B. Flaggan ska komma ur ärendet och inte ur ett förval.

    Utan den här raden kunde `kor` sluta skicka `regnr_i_mailet` med hela sviten
    grön: förvalet är `True`, alltså hade ett mail utan registreringsnummer tyst
    fått tillbaka ärende 14:s besked om ett misslyckat uppslag.
    """
    assert _forfragan_for(arende(regnr=None)).regnr_i_mailet is False
    assert _forfragan_for(arende(regnr="ABC123")).regnr_i_mailet is True


def test_ETT_BLANKT_regnr_raknas_som_INGET_nummer_i_BADA_leden():
    """SAMMA UTTRYCK PÅ BÅDA STÄLLENA, och det var det inte.

    `fordonsuppslag.slag_upp` kastar *"registreringsnummer saknas"* när
    `normalisera_regnr` ger tomt, alltså är ett nummer som bara bär blanktecken
    inget nummer. `uppslagskalla` prövade `not arende.regnr`, som är FALSKT för
    en sträng med ett mellanslag, alltså hade härkomstraden sagt MISSLYCKADES
    medan prompten säger att mailet inte bär något nummer. Granskaren läser de
    två bredvid varandra.
    """
    blankt = arende(regnr="   ")

    assert _forfragan_for(blankt).regnr_i_mailet is False

    utfall = Kedjeutfall(
        kategori="fråga om a-traktorkonvertering", hink="auto", utkast="Hej.",
        steg=(Steg("uppslag", "misslyckades", "registreringsnummer saknas"),),
    )
    assert "BÄR INGET REGISTRERINGSNUMMER" in kedja.uppslagskalla(
        blankt, utfall, skarp=True)


def test_REGISTRET_SAKNAR_ger_INGEN_ratt_att_pasta_franvaro():
    """VÄG TRE, LARS BESLUT I SKIVA 41 PÅ LUCKA 50.

    **EN FRÅNVARO ÄR ALDRIG ETT BELÄGG.** Skiva 40 gav den här vägen rätten att
    säga att registret saknar dragviktsuppgift, med motiveringen att sidan bara
    renderar fält som HAR ett värde. Det är sant om sidan och osant om vår
    läsning av den: ett mjukt bindestreck i `Släpvagnsvikt` räcker för att
    fältet ska se saknat ut, och det kräver ingen markupändring alls.

    Raden band tidigare motsatsen och är vänd, inte tillagd. Se
    `docs/beslutslogg.md` #93 och LUCKA 50.
    """
    assert _mangden(hamta_registret_saknar_dragvikt) == frozenset()


def test_ett_MISSLYCKAT_uppslag_ger_ALDRIG_ratt_att_pasta_franvaro():
    """EGENSKAPEN, och inte instansen.

    **VARJE misslyckat uppslag ger en tom mängd**, oavsett vilket läge
    härkomstraden rapporterar. Raden prövar alla tre lägena tillsammans, så att
    en framtida gren som lägger tillbaka något av dem blir röd.

    *Raden påstod tre lägen och prövade två: `TOLKAS_EJ` saknade hämtare. Fällt
    av §7-granskningen av skiva 41, varv 1.*
    """
    for hamta in (hamta_registret_saknar_dragvikt, hamta_dragvikt_i_annan_form,
                  hamta_dragvikt_olasbar):
        assert _mangden(hamta) == frozenset()


def test_ANNAN_FORM_ger_INGEN_ratt_att_pasta_franvaro():
    """UTFALL 4, LARS BESLUT. Uppgiften FINNS, i en form vi inte kan bedöma mot.

    **DEN HÄR RADEN ÄR SKILLNADEN MELLAN DE TVÅ UTFALLEN**, och utan den vore
    hela DEL A:s uppdelning verkningslös i sändvägen.
    """
    assert _mangden(hamta_dragvikt_i_annan_form) == frozenset()


def test_ett_AVLAST_nej_pa_draganordningen_far_pastas():
    """DEN ANDRA VÄGEN IN I MÄNGDEN, och den går via ett LYCKAT uppslag.

    Ett fordon vars sida säger `Draganordning: Nej` har bevisligen ingen
    registrerad draganordning. Att spärra *"bilen saknar registrerad
    draganordning"* hade blockerat ett SANT besked, och det är precis den
    formulering DEL F ber om.
    """
    assert _mangden(hamta_utan_draganordning) == frozenset({"draganordning"})


def test_en_OGATAD_kategori_bygger_INGEN_forfragan_alls():
    """Grinden är starkare än den gamla raden här band.

    *Raden hette `test_ett_uppslag_som_hoppades_over_ger_TOM_mangd` och band att
    en ogatad kategori nådde generatorn med en TOM `franvaro_far_pastas`. Den
    vägen finns inte längre: grinden stannar före generatorn, alltså byggs ingen
    `Forfragan` alls. Att lämna raden som den var hade gjort den grön på en
    `IndexError` som aldrig inträffar, eller röd utan att något var fel.*

    **EGENSKAPEN SOM RADEN SKYDDADE ÄR INTE HEMLÖS.** Att ett uppslag som inte
    gav ett avläst `Nej` ger en tom mängd binds av
    `test_ett_MISSLYCKAT_uppslag_ger_ALDRIG_ratt_att_pasta_franvaro`, som prövar
    alla tre lägena.
    """
    klient = FejkKlient("boka däckbyte", "onådd")
    sedda: list[generera.Forfragan] = []
    riktig = generera.generera_utkast

    def fangar(klienten, forfragan, **rest):
        sedda.append(forfragan)
        return riktig(klienten, forfragan, **rest)

    generera.generera_utkast = fangar
    try:
        kedja.kor(arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR,
                  taxonomi=TAXONOMI, exempel=[])
    finally:
        generera.generera_utkast = riktig

    assert sedda == [], "grinden släppte fram en ogatad kategori till generatorn"


def test_A_TRAKTOR_bygger_fortfarande_en_forfragan():
    """Motsatsen. Utan den här raden är testet ovan grönt även om kedjan
    slutat bygga `Forfragan` helt, alltså slutat generera för a-traktor med."""
    klient = FejkKlient(
        "fråga om a-traktorkonvertering", "Hej, din bil går bra att bygga om."
    )
    sedda: list[generera.Forfragan] = []
    riktig = generera.generera_utkast

    def fangar(klienten, forfragan, **rest):
        sedda.append(forfragan)
        return riktig(klienten, forfragan, **rest)

    generera.generera_utkast = fangar
    try:
        kedja.kor(arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR,
                  taxonomi=TAXONOMI, exempel=[])
    finally:
        generera.generera_utkast = riktig

    assert len(sedda) == 1
    assert sedda[0].uppslag_gjordes is True


def test_harkomstraden_sager_VILKA_falt_registret_inte_bar():
    """SKIVA 55 DEL A. Ett LYCKAT uppslag kan sakna fält, och det ska synas.

    **UTAN RADEN SER ETT FORDON UTAN DRAGVIKTSUPPGIFT UT SOM EN OBESLUTSAM
    BOT.** Uppslaget lyckas,
    utfallet blir OKLART, och härkomstraden sade bara *"lyckades, utfall
    oklart"*. Skälet till att det är oklart står i registret och inte hos oss,
    och det är den skillnaden Lars ska kunna läsa i vyn.

    **INGA VÄRDEN I STRÄNGEN, bara fältnamn.** Raden blir röd om en vikt börjar
    skrivas ut: `logg/beslut.jsonl` är gitignorerad, men en detaljsträng som
    växer med fordonsdata är en persondataväg ingen bett om (§6).
    """
    uppslag = fordonsuppslag.Uppslag(
        tjanstevikt_kg=960, slapvagnsvikt_kg=None, draganordning=False,
    )

    detalj = kedja._lyckadetalj(uppslag, fordonsuppslag.Utfall.OKLART)

    assert "oklart" in detalj
    assert "släpvagnsvikt" in detalj
    assert "draganordning" not in detalj
    assert "960" not in detalj


def test_harkomstraden_sager_BARA_utfallet_nar_alla_falt_lastes():
    """NEGATIVKONTROLLEN. Ett fullständigt uppslag får ingen tilläggstext.

    Utan den här raden vore en lydelse som alltid la till en förklaring lika
    grön, och då hade varje post i vyn burit en mening om saknade fält.
    """
    uppslag = fordonsuppslag.Uppslag(
        tjanstevikt_kg=1720, slapvagnsvikt_kg=1600, draganordning=False,
    )

    assert kedja._lyckadetalj(
        uppslag, fordonsuppslag.Utfall.OKLART) == "oklart"
