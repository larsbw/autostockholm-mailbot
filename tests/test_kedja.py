"""KEDJAN från inkommande mail till utkast. SÄNDVÄG.

**INGET TEST HÄR RÖR NÄTET.** `kor` tar både klienten och hämtningen som
argument, alltså är båda utbytbara mot fejkar. Ingen rad rör en brevlåda, och
`test_kedjan_har_ingen_sandvag` prövar hela importgrafen.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext (§6).
"""

from __future__ import annotations

import json

import pytest

from src import generera, kategorisera, kedja, ometikettera, vy
from src.fordonsuppslag import UppslagMisslyckades, Utfall
from src.kedja import Arende, Kallfel, Kedjeutfall, Steg
from tests.test_vy import FejkHanterare

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


def test_kategori_utanfor_a_traktor_hoppar_over_uppslaget():
    """Uppslaget gatar bara a-traktor, `docs/roadmap.md` fas 4.5.

    Hämtningen kraschar med flit: nås den alls är steget inte överhoppat.
    """
    klient = FejkKlient("boka däckbyte", "Hej, vi bokar in dig.")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_kraschar, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.hink == "utkast"
    assert utfall.uppslag is None
    assert utfall.utfall is None
    assert utfall.steg[1] == Steg("uppslag", "hoppades över",
                                  "kategorin gatas inte")


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
        "Hej, det kostar 25000 kr.",
    )

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.utkast is None
    assert not utfall.blev_utkast
    assert utfall.sparr == "genererat-tal-har-kalla"
    assert utfall.steg[-1] == Steg("spärrar", "fälld", "genererat-tal-har-kalla")


def test_hinken_stoppar_INTE_generering():
    """Ramverksregel 1 gäller SÄNDNING, och kedjan skickar ingenting.

    En kategori i `aldrig` ska ändå ge ett utkast, eftersom skuggläget mäter vad
    som HADE gått ut. Att låta hinken stoppa här hade dolt just det.
    """
    klient = FejkKlient("inget kundärende", "Hej, tack för ditt meddelande.")

    utfall = kedja.kor(
        arende(), klient=klient, hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[]
    )

    assert utfall.hink == "aldrig"
    assert utfall.blev_utkast


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
    granskningsfall = kedja.till_granskningsfall(ar, utfall)

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
        "fråga om a-traktorkonvertering", "Hej, det kostar 25000 kr."
    )
    ar = arende()

    utfall = kedja.kor(
        ar, klient=klient, hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[],
    )
    granskningsfall = kedja.till_granskningsfall(ar, utfall)

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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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


def test_ett_KALLFEL_lamnar_ocksa_en_rad(tmp_path, monkeypatch):
    """Ett driftavbrott som inte loggas ser ut som ett ärende som aldrig kom in.

    `kor` kastar `Kallfel` och anroparen hoppade vidare, alltså lämnade ett
    nere-liggande biluppgifter.se INGEN rad alls. Skuggläget ska kunna mäta hur
    ofta källan svek, och den skillnaden är vad `Kallfel` byggdes för att
    bevara. Fällt av §7-granskningen av skiva 34, varv 2.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    monkeypatch.setattr(vy, "ROT", tmp_path)
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
    """`krav_pa_skrivbar_sokvag` gäller även den här loggen."""
    with pytest.raises(vy.Skrivfel):
        kedja.logga_beslut(
            arende(),
            Kedjeutfall(kategori="x", hink="utkast"),
            loggfil=kedja.ROT / "src" / "smugglad.jsonl",
        )
