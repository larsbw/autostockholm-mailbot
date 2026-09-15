"""Generatorn, fas 5. SÄNDVÄG enligt CLAUDE.md §7.

**INGET TEST HÄR RÖR NÄTET.** `generera_utkast` tar klienten som argument, och
varje test ger den en fejk som returnerar en färdig text. API-nyckeln läses
aldrig.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext ur `data/`. Registreringsnummer och
namn är konstruerade för testet (§6).

SPÄRRARNA FÄLLS EN I TAGET OCH ALDRIG I PAR. Skiva 27 mätte att en sammanslagen
fällning ger RÖD och därmed falskt ÄKTA: ett rött utfall bevisar bara att MINST
EN av de fällda raderna bär. Varje `krav_pa_*` har därför sitt eget test, och
`krav_pa_svaret` har ett eget som visar att den anropar spärrarna i sin tabell.

*Här stod "att den anropar alla tre". Tabellen bar tre rader medan
`krav_pa_svaret` anropade fem spärrar, alltså påstod meningen en fullständighet
som inte fanns. Fällt i skiva 46, som lade till en fjärde rad.*
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
from tests.sentinelpris import SENTINELPRIS, SENTINELPRIS_IHOP, SENTINELTAL

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


def test_FAKTABLOCKETS_ram_ar_bunden_ORDAGRANT():
    """Rubriken är sändvägstext, och den var obunden.

    **EN LYDELSE SOM BAD MODELLEN HITTA PÅ MER OM OSS PASSERADE HELA SVITEN.**
    Testet sökte bara efter delsträngen `Fakta om oss`, alltså band det att
    blocket FANNS och inget om vad det sade. Det är lucka 25:s hål, flyttat ett
    lager upp. Fällt av §7-granskningen av skiva 37, varv 2.

    Samma form som `test_HELA_systemprompten_ar_bunden`: en likhet fångar varje
    ändring, en delsträng fångar de ord någon råkade tänka på.
    """
    assert generera.FAKTARUBRIK == (
        "Fakta om oss, avlästa ur config/fakta.json. Utöver det som redan står "
        "i reglerna ovan får du inte påstå något om Auto Stockholm som inte "
        "står här:\n"
    )
    assert generera.FAKTAFOT == (
        "Varje TAL här återges ordagrant och ändras aldrig.\n"
    )

    # Och att blocket FAKTISKT byggs av dem, alltså att ramen inte går att
    # kringgå genom att skriva om `_faktarader`:s kropp.
    block = generera._faktarader()
    assert block.startswith(generera.FAKTARUBRIK)
    assert block.endswith(generera.FAKTAFOT)


def test_UNDERLAGETS_rubrik_ar_bunden_ORDAGRANT():
    """Underlagets FÖRSTA rad var vakuös och bar en känd falskhet.

    Den löd *"Detta är allt du vet. Allt annat får du inte påstå."* Det är
    ordagrant det led som fälldes i `FAKTARUBRIK`, och det stod kvar hundra rader
    upp i samma funktion. En lydelse som bad modellen påstå mer om oss passerade
    hela testfilen, medan grannraden `Priser: INGA` var bunden.

    Fällt av §7-granskningen av skiva 37, varv 3.
    """
    assert generera.UNDERLAGSRUBRIK == (
        "UNDERLAG. Det här är vad du vet om det HÄR ärendet. Fyll inte i något "
        "som saknas, och gissa aldrig ett värde.\n"
    )
    assert generera._underlag(forfragan()).startswith(generera.UNDERLAGSRUBRIK)

    # Och att den inte påstår sig vara allt modellen vet om OSS. Tre andra
    # källor bär påståenden om Auto Stockholm, se raden nedan.
    assert "allt du vet" not in generera.UNDERLAGSRUBRIK.lower()


def test_TRE_ANDRA_kallor_bar_pastaenden_om_oss():
    """Skälet till att ingen rubrik får säga "allt du vet om oss".

    *Raden hette `test_RUBRIKEN_pastar_inte_att_den_ar_ALLT_modellen_vet` och
    bestod av `"ENDA du vet" not in FAKTARUBRIK`. Den band frånvaron av en
    LITERAL FRAS, inte egenskapen i sitt namn: en omformulering med samma
    innebörd passerade grönt. §7.1 ger två utvägar, döp om eller gör äkta. Det
    som faktiskt skyddar är ordagrant-bindningen i testet ovan, och den här
    raden redovisar PREMISSEN den vilar på. Fällt av §7-granskningen av skiva
    37, varv 3.*

    Premissen: prompten bär påståenden om Auto Stockholm på tre ställen utöver
    `config/fakta.json`. Slutar något av dem gälla ska den här raden bli röd, så
    att rubrikernas formulering vägs om.
    """
    assert "fristående verkstad i Stockholm" in generera.SYSTEM
    assert "bygger om bilar till a-traktor" in generera.SYSTEM
    assert "liten verkstad utan en organisation" in generera.SYSTEM


def test_UNDERLAGET_bar_faktaraden(tmp_path, monkeypatch):
    """Att `_faktarader` finns räcker inte. Den ska KOPPLAS IN i underlaget.

    **DETTA ÄR SAMMA HÅL SOM SKIVAN SJÄLV NAMNGAV FÖR `uppslagskalla`**, och det
    lämnades öppet för DEL C i samma skiva: hela raden
    `rader.append(_faktarader())` gick att radera med full svit grön, alltså band
    de andra testen funktionens INNEHÅLL men aldrig att prompten får det.
    `docs/incidentlogg.md` I10. Fällt av §7-granskningen av skiva 36, varv 1.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text('{"telefon": "08-000 00 00"}', encoding="utf-8")
    monkeypatch.setattr(generera, "FAKTA", fil)

    underlag = generera._underlag(forfragan())

    assert "08-000 00 00" in underlag
    assert "Fakta om oss" in underlag


def test_UNDERLAGET_bar_bokningsbeskedet_som_REGEL_10_vilar_pa():
    """Regel 10 beordrar det regel 8 förbjuder, om beskedet inte är underlag.

    Regel 8: *"Påstå aldrig något om vad Auto Stockholm har, erbjuder eller
    innehåller utöver det som står i underlaget nedan."* Regel 10: *"svarar vi
    att det löser vi."* Att vi kan ta emot en bil är ett påstående om vad vi
    erbjuder, alltså måste det STÅ i underlaget. Fällt av §7-granskningen av
    skiva 36, varv 1.

    **BESKEDET BOR I `config/fakta.json` SEDAN SKIVA 37**, på Lars §10-beslut,
    och kommer in via `_faktarader`. Raden binder därför att FILEN bär beskedet
    och att underlaget får det ORDAGRANT. Det var lucka 43, och den är stängd.

    **FÖRBUDET MOT ATT LOVA EN TID PRÖVAS INTE HÄR LÄNGRE, och det är avsiktligt.**
    Det är en instruktion till modellen och bor i promptregel 10, bunden av
    `test_varje_regel_star_ORDAGRANT`. Att söka efter det i ett FAKTUM var vad
    som gjorde att flytten kunde försvaga spärren utan att något blev rött.

    *Här stod rubriken "RADEN BINDS ORDAGRANT" kvar efter att likheten mot
    `BOKNINGSBESKED` ersatts av delsträngskontroller. Docstringen beskrev alltså
    en bindning testet inte hade. Fällt av §7-granskningen av skiva 37, varv 1.*

    *En rad som räknade skivans delsträngsfällor stod här och är struken: en
    räkning av instanser av ett mönster i ett arbetsförlopp går inte att
    verifiera mot repot, §7.2. Fällt av §7-granskningen av skiva 37, varv 2.*
    """
    underlag = generera._underlag(forfragan())
    fakta = generera.las_fakta()

    assert "bokningar" in fakta, "config/fakta.json bär inget bokningsbesked"
    # ORDAGRANT, inte som delsträng av en omskrivning: det underlaget bär ska
    # vara filens värde tecken för tecken.
    assert f"  bokningar: {fakta['bokningar']}" in underlag


def test_UNDERLAGET_sager_ifran_nar_fakta_SAKNAS(tmp_path, monkeypatch):
    """Att tiga hade lämnat modellen att gissa om den får skriva ett nummer."""
    monkeypatch.setattr(generera, "FAKTA", tmp_path / "finns-inte.json")

    underlag = generera._underlag(forfragan())

    assert "Fakta om oss: INGA" in underlag
    assert "aldrig ett påhittat nummer" in underlag


@pytest.mark.parametrize("filnamn", ["PRISER", "FAKTA"])
def test_ett_NYCKELNAMN_ar_ALDRIG_en_talkalla(filnamn, tmp_path, monkeypatch):
    """SPÄRR: ett namn är en etikett, inte en avläsning.

    Första rättelsen filtrerade `_`-nycklar och dumpade sedan hela dicten, alltså
    gick NYCKELNAMNEN med: `{"ledtid_14_dagar": ...}` gjorde 14 till ett tal
    boten får skriva. Fällt av §7-granskningen av skiva 36, varv 2.

    **BÅDA KONFIGFILERNA PRÖVAS.** `config/priser.json` hade ingen enda rad, och
    det är den fil som mest sannolikt blir nästlad: ett prisregister per tjänst
    är den naturliga formen.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text('{"ledtid_14_dagar": "snabbt"}', encoding="utf-8")
    monkeypatch.setattr(generera, filnamn, fil)

    assert "14" not in generera._tillatna_tal(forfragan())


@pytest.mark.parametrize("filnamn", ["PRISER", "FAKTA"])
def test_en_NASTLAD_kommentar_vidgar_ALDRIG_talsparren(filnamn, tmp_path, monkeypatch):
    """SPÄRR: en kommentar en nivå ned är lika mycket en kommentar.

    Första rättelsen prövade `_`-prefixet bara på toppnivån, alltså återuppstod
    hålet ett steg ned. Fällt av §7-granskningen av skiva 36, varv 2.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"a-traktor": {"_om": "se §7.2 och §10", "pris": 25000}}', encoding="utf-8"
    )
    monkeypatch.setattr(generera, filnamn, fil)

    tillatna = generera._tillatna_tal(forfragan())

    assert "7" not in tillatna
    assert "10" not in tillatna
    # NEGATIVKONTROLL i samma rad: det nästlade VÄRDET ska fortfarande fram.
    assert "25000" in tillatna


@pytest.mark.parametrize("filnamn", ["PRISER", "FAKTA"])
def test_en_KOMMENTAR_i_en_LISTA_vidgar_ALDRIG_talsparren(filnamn, tmp_path, monkeypatch):
    """SPÄRR: listgrenen i `_varden_ur`, som var OBUNDEN.

    **`config/priser.json` BLIR MED STÖRSTA SANNOLIKHET EN LISTA** av objekt, ett
    per tjänst. Utan listgrenen faller listan igenom till `str(data)`, alltså till
    REPR:EN med varje nästlad `_`-kommentar inbakad, och hålet från varv 1 är
    tillbaka en nivå djupare.

    Grenen fungerade men ingen rad band den: fälld ensam var hela sviten grön,
    alltså vakuös enligt §7.1. Fällt av §7-granskningen av skiva 36, varv 3.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"tjanster": [{"_om": "se §7.2 och §10", "pris": 25000}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(generera, filnamn, fil)

    tillatna = generera._tillatna_tal(forfragan())

    assert "7" not in tillatna
    assert "10" not in tillatna
    assert "25000" in tillatna


def test_giltig_JSON_av_FEL_TYP_ger_INGA_fakta_i_stallet_for_krasch(tmp_path, monkeypatch):
    """En fil som inte är ett objekt på toppnivån ska inte stoppa genereringen.

    `las_konfigvarden` gjorde `data.items()` rakt av, alltså `AttributeError` på
    en lista. Den säkra riktningen är att inga fakta finns.

    *Raden hette `test_en_TRASIG_konfigfil_...`, vilket är bredare än vad den
    prövar: syntaktiskt trasig JSON kastar fortfarande, och det är avsiktligt.
    §7.1: döp om det till vad det faktiskt bevisar. Fällt av §7-granskningen av
    skiva 36, varv 3.*
    """
    fil = tmp_path / "konfig.json"
    fil.write_text('["en lista", 42]', encoding="utf-8")
    monkeypatch.setattr(generera, "FAKTA", fil)

    assert generera.las_fakta() == {}
    assert "Fakta om oss: INGA" in generera._underlag(forfragan())


def test_en_KOMMENTAR_i_konfig_vidgar_ALDRIG_talsparren(tmp_path, monkeypatch):
    """SPÄRR: §0:s ramverksregel 3. En kommentar är ingen källa.

    **DEN HÄR RADEN BÄR EN UPPMÄTT DEFEKT.** `config/fakta.json` fick i skiva 36
    två kommentarnycklar som nämner `§7.2` och `CLAUDE.md §10`. `_tillatna_tal`
    läste hela filen och plockade tal ur den, alltså blev 7 och 10 TILLÅTNA TAL:
    *"vi hör av oss inom 10 dagar"* passerade spärren och hade kunnat gå till en
    kund. Fällt av §7-granskningen av skiva 36, varv 1.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text(
        '{"_om": "se §7.2 och CLAUDE.md §10", "telefon": ""}', encoding="utf-8"
    )
    monkeypatch.setattr(generera, "FAKTA", fil)

    tillatna = generera._tillatna_tal(forfragan())

    assert "7" not in tillatna
    assert "10" not in tillatna

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla("Vi hör av oss inom 10 dagar.", forfragan())


def test_ett_IFYLLT_konfigvarde_ger_FORTFARANDE_sitt_tal(tmp_path, monkeypatch):
    """NEGATIVKONTROLL: filtret får inte stänga av källan.

    Utan raden vore "returnera alltid tomt" en grön lösning på raden ovan, och
    då hade Lars kunnat fylla filen utan att talet blev skrivbart.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text('{"_om": "kommentar", "ledtid_dagar": 14}', encoding="utf-8")
    monkeypatch.setattr(generera, "FAKTA", fil)

    assert "14" in generera._tillatna_tal(forfragan())


def test_ett_TOMT_telefonvarde_nar_ALDRIG_prompten(tmp_path):
    """SPÄRR: ett tomt värde är inte en avläsning.

    `config/fakta.json` skapades i skiva 36 med `telefon: ""`, och Lars fyller
    värdet. Fram till dess får modellen inte veta något nummer, alltså kan den
    inte skriva ett. §0:s ramverksregel 3.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text('{"_om": "kommentar", "telefon": "   "}', encoding="utf-8")

    assert generera.las_fakta(fil) == {}
    assert "INGA" in generera._faktarader(fil)
    assert "kommentar" not in generera._faktarader(fil)


def test_ett_IFYLLT_telefonvarde_nar_prompten_ORDAGRANT(tmp_path):
    """NEGATIVKONTROLL: fylls filen ska värdet fram, oförändrat.

    Utan raden vore "returnera alltid tomt" en grön lösning, och Lars skulle
    fylla filen utan verkan.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text('{"telefon": "08-000 00 00"}', encoding="utf-8")

    rader = generera._faktarader(fil)
    assert "08-000 00 00" in rader
    assert "INGA" not in rader


# VAD LARS HAR BESLUTAT ATT `config/fakta.json` BÄR. Samma form och samma skäl
# som `PRISER_SOM_LARS_BESLUTAT`.
#
# **BÅDA VÄRDENA BINDS ORDAGRANT, och det andra ledet är nytt.** Vakten band
# förut `telefon == ""` plus nyckelmängden, alltså INTE vad `bokningar`
# innehåller. Det var LUCKA 57:s gatningsfynd: uppmätt gav ett årtal i
# `bokningar`, *"vi har funnits sedan 1995 och tar emot bokningar löpande"*, HELT
# GRÖN SVIT. Ett tal kunde alltså skrivas in i den här filen och bli en citerbar
# källa i ett utgående mail utan att en enda rad gick röd. Med hela innehållet
# bundet är det ledet stängt.
FAKTA_SOM_LARS_BESLUTAT = {
    "bokningar": "vi tar emot bokningar löpande och kommer överens om tid "
                 "med kunden",
    "telefon": "076-860 38 15",
}


def test_faktafilen_i_repot_bar_EXAKT_det_Lars_BESLUTAT():
    """Binder att jag inte ändrat filen åt Lars.

    §10 gör `config/fakta.json` till ett uttryckligt stopp. Skiva 36 skapade
    filen på Lars order och skiva 44 fyllde `telefon` på hans beslut. Raden blir
    röd den dag någon rör ett värde, och då ska den dagen vara Lars val.

    *Raden hette `..._har_TOM_telefon` och band `telefon == ""`. Det ledet gick
    röd av Lars egen fyllning, alltså vaktade det hans beslut på precis det sätt
    det skulle. Det är UPPDATERAT och inte upplöst.*
    """
    data = json.loads(generera.FAKTA.read_text(encoding="utf-8"))
    poster = {n: v for n, v in data.items() if not n.startswith("_")}

    # **HELA INNEHÅLLET BINDS, inte bara `telefon`.** HEAD band
    # `las_fakta() == {}`, alltså att ingen post med värde fanns alls. Skiva 37
    # bytte det mot en kontroll av enbart `telefon`, och då gick en NY post in
    # med grön svit. Filen är ett §10-stopp: varje post ska kräva ett medvetet
    # beslut, och den här raden är tripwiren. Fällt av §7-granskningen av
    # skiva 37, varv 2.
    assert poster == FAKTA_SOM_LARS_BESLUTAT, (
        "config/fakta.json har fått, tappat eller ändrat en post. Filen är ett "
        "§10-stopp: ändra tabellen här bara när Lars har beslutat ändringen."
    )

    # Och att numret FAKTISKT når prompten, ordagrant. RADEN prövas, inte
    # strängen: rubriken innehåller ordet "telefonnummer", så en
    # delsträngskontroll hade varit grön av fel skäl.
    rader = [r.strip() for r in generera._faktarader().splitlines()]
    assert f"telefon: {FAKTA_SOM_LARS_BESLUTAT['telefon']}" in rader


# --- SKIVA 41 DEL A: config/priser.json --------------------------------------


# VAD LARS HAR BESLUTAT ATT `config/priser.json` BÄR. Avläst ur filen efter hans
# §10-beslut i skiva 44; värdena kommer ur autostockholm.se/prislista.
#
# **HELA INNEHÅLLET BINDS, inte bara nyckelmängden och inte bara att en post är
# ifylld.** Vakten band förut `set(poster) == PRISNYCKLAR` plus att varje värde
# var TOMT. Det andra ledet gick inte att behålla när Lars fyllde filen, och att
# lösa upp det till "posterna är ifyllda" hade gjort tripwiren svagare än den var:
# ett ÄNDRAT belopp är lika mycket en §10-ändring som ett infört, och en sådan
# ändring hade då passerat med grön svit.
#
# Raden går alltså röd på tre former: en ny post, en borttagen post, och ett
# ändrat värde. Alla tre kräver Lars beslut, och den som har hans beslut ändrar
# tabellen här i samma svep.
PRISER_SOM_LARS_BESLUTAT = {
    # `inklusive moms` ÄR LARS §10-BESLUT I SKIVA 44. Boten skrev det ändå, i
    # två av fem lästa utkast, utan att någon källa bar det: formuleringen står
    # i prisfilens kommentar `_formen`, som filtreras bort ur prompten, alltså
    # kom den ur få-exemplen eller ur modellen. Åtgärden är att göra påståendet
    # SANT OCH KÄLLBELAGT i stället för att fälla det i efterhand.
    "a_traktorkonvertering":
        "från 20 000 till 25 000 kr inklusive moms, och priset gäller arbetet "
        "och de delar som ingår i grundpaketet",
    "rekond":
        "Premium rekond 3 500 kr, Guldtvätt 1 500 kr, glasförsegling 1 000 kr, "
        "sanering av djurhår 500 kr, fälgbehandling 500 kr, invändig tvätt "
        "800 kr, utvändig tvätt 900 kr, keramisk lackförsegling från 4 500 kr",
    "reparation":
        "diagnostik och felsökning från 1 250 kr, bromsbelägg fram 2 500 till "
        "4 500 kr, bromsskivor och belägg fram 5 000 till 7 000 kr, "
        "kamremsbyte 12 000 till 20 000 kr, kopplingsbyte 8 000 till "
        "15 000 kr, stötdämparbyte 3 000 till 6 000 kr, hjulinställning "
        "1 000 till 1 500 kr",
    "service":
        "stor service 4 650 kr, mellan service 3 950 kr, liten service "
        "2 850 kr, oljebyte från 1 500 kr, efterkontroll besiktning från "
        "300 kr, motortvätt 500 kr",
    "dack":
        "däckhotell med skifte 1 695 kr per säsong, däckskifte 600 kr, "
        "punktering 600 kr, däckomläggning med balansering 2 400 kr för 13 "
        "till 16 tum, 3 000 kr för 17 till 18 tum, 3 600 kr för 19 till 21 tum",
    # TOM MED FLIT, och det är Lars beslut. Auto Stockholm säljer tillbehör,
    # men prislistan bär inget fast pris för dem, och §0:s ramverksregel 3 säger
    # att ett pris som inte står i filen aldrig får skrivas. Posten står kvar
    # tom i stället för att tas bort, så att den dag den fylls är ett beslut och
    # inte ett tillägg.
    "tillbehor": "",
}

PRISNYCKLAR = set(PRISER_SOM_LARS_BESLUTAT)


def test_prisfilen_i_repot_bar_EXAKT_det_Lars_BESLUTAT():
    """§10-VAKTEN FÖR PRISFILEN, byggd som den för `config/fakta.json`.

    Filen skapades i skiva 41 på Lars §10-beslut och FYLLDES av honom i skiva
    44. Att ändra den är hans beslut och inte mitt, och den här raden blir röd
    den dag någon rör den.

    **HELA INNEHÅLLET BINDS, inte bara att filen har rätt nycklar.** Skiva 37
    visade att en vakt som bara prövar ETT fält går att kringgå: en ny post gick
    in med grön svit. Skälet att värdena binds ORDAGRANT står vid
    `PRISER_SOM_LARS_BESLUTAT`: ett ändrat belopp är lika mycket en §10-ändring
    som ett infört.

    *Raden hette `..._har_BARA_TOMMA_varden` och band `all(v == "")`. Det ledet
    gick röd av Lars egen fyllning, alltså vaktade det hans beslut på precis det
    sätt det skulle. Det är UPPDATERAT och inte upplöst.*
    """
    data = json.loads(generera.PRISER.read_text(encoding="utf-8"))
    poster = {n: v for n, v in data.items() if not n.startswith("_")}

    assert poster == PRISER_SOM_LARS_BESLUTAT, (
        "config/priser.json har fått, tappat eller ändrat en post. Filen är ett "
        "§10-stopp: ändra tabellen här bara när Lars har beslutat ändringen."
    )

    # `tillbehor` ÄR TOM OCH SKA FÖRBLI TOM tills Lars säger annat. Ledet står
    # för sig, så att den dag posten fylls säger felmeddelandet vad som hände i
    # stället för att bara visa två olika dictar.
    assert poster["tillbehor"] == "", (
        "tillbehor har fått ett pris. Lars beslut i skiva 44 var att den står "
        "tom, eftersom prislistan inte bär något fast tillbehörspris."
    )

    # OCH ATT DET TOMMA VÄRDET FAKTISKT UTELÄMNAS, alltså aldrig når prompten
    # och aldrig blir en källa. De fyllda posterna ska däremot nå hela vägen.
    assert generera.las_priser() == {
        n: v for n, v in PRISER_SOM_LARS_BESLUTAT.items() if v
    }

    rader = generera._prisrader()
    assert rader != generera.INGA_PRISER
    assert "tillbehor" not in rader


def _med_priser(monkeypatch, poster: dict) -> None:
    """Låtsas att `config/priser.json` bär `poster`. Rör aldrig filen.

    §10 gör filen till ett stopp, alltså får ett test inte skriva i den. Den
    här hjälparen byter ut den RÅA läsningen, `las_konfig`, och inte
    `las_priser`.

    **SKÄLET ÄR ATT FILEN HAR TVÅ LÄSARE MED OLIKA KRAV**, och det är avsiktligt:
    `las_konfigvarden` ger prompten namn och värde i par, `_varden_ur` ger
    talspärren varje värde var det än ligger. Båda går via `las_konfig`. En
    hjälpare som bara patchade `las_priser` hade gett prisgrenen en fylld fil
    och talspärren en tom, alltså ett test som inte liknar något verkligt läge.
    Uppmätt under bygget: `test_ett_AVLAST_pris_slapps_igenom...` föll på att
    25000 inte fanns bland de tillåtna talen.
    """
    riktig = generera.las_konfig

    def las(fil):
        return dict(poster) if fil == generera.PRISER else riktig(fil)

    monkeypatch.setattr(generera, "las_konfig", las)


def test_ett_pris_FALLER_nar_prisfilen_ar_tom(monkeypatch):
    """DAGENS LÄGE, och det är oförändrat sedan före skiva 41.

    Filen finns men bär inga priser, alltså har boten ingen prisuppgift och
    varje prisord fäller.
    """
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla("Det kostar 25 000 kr.", forfragan())

    assert fel.value.sparr == "genererat-tal-har-kalla"
    assert "kommer inte ur config/priser.json" in fel.value.skal


def test_ett_AVLAST_pris_slapps_igenom_nar_Lars_fyllt_filen(monkeypatch):
    """**DEN DAG LARS FYLLER EN POST MÅSTE PROMPTENS EGET SVAR PASSERA.**

    `_prisrader` skriver in priset och ber modellen återge det ordagrant. Den
    ovillkorliga prisgrenen hade fällt varje svar som gjorde det, alltså hade
    prompten beställt en mening spärren fäller. Det är §9.1:s motsägelse, och
    den fångades av §7-granskningen av skiva 41, varv 1.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    generera.krav_pa_tal_med_kalla(
        "Konverteringen kostar 25 000 kr.", forfragan())


def test_ett_PAHITTAT_pris_faller_aven_nar_filen_ar_fylld(monkeypatch):
    """SPÄRREN ÄR INTE BORTTAGEN, den vilar på vad filen BÄR.

    Ett annat tal än det avlästa har ingen källa och fälls av loopen längre ned.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(
            "Konverteringen kostar 30 000 kr.", forfragan())


@pytest.mark.parametrize(
    "svar",
    [
        # UPPSLAGETS VIKTER ÄR INGEN PRISKÄLLA. Alla fyra passerade en första
        # lydelse, där prisordet föll igenom till den ALLMÄNNA talloopen så
        # snart filen bar något. Uppmätt av §7-granskningen av skiva 41, varv 2.
        "Ombyggnaden kostar 1400 kr.",
        "Det blir 1500 kr.",
        "Det blir 1400tkr.",
        # `ALLTID_TILLATNA_TAL` ÄR HELLER INGEN PRISKÄLLA.
        "Vi tar 3 kr.",
        # ETT PRISORD UTAN TAL I SIN EGEN SATS. Den gamla lydelsen prövade
        # `_tal_i` över HELA svaret, alltså räckte en tvåa var som helst.
        "Det kostar en del, vi hör av oss inom 2 dagar.",
        "Det kostar en del.",
    ],
)
def test_ett_PRIS_utan_PRISKALLA_faller_aven_nar_filen_ar_fylld(monkeypatch,
                                                                svar):
    """**ETT PRIS PRÖVAS MOT PRISKÄLLAN, inte mot alla tillåtna tal.**

    `_tillatna_tal` bär uppslagets vikter och `ALLTID_TILLATNA_TAL`. Lät man
    prisordet falla igenom dit blev fordonets TJÄNSTEVIKT ett tillåtet pris, och
    `Det blir 1400tkr` är 1,4 miljoner kronor.

    Fixturen bär ett uppslag med tjänstevikt 1400 och släpvagnsvikt 1500, alltså
    är de två första raderna tal som FINNS i den allmänna mängden.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            svar, forfragan(uppslag=GRONT_UPPSLAG))

    assert fel.value.sparr == "genererat-tal-har-kalla"


def test_ett_PRISORD_I_EN_ANNAN_SATS_hamtar_ingen_kalla(monkeypatch):
    """PRÖVNINGEN SKER PER SATS, precis som frånvarospärrens.

    Ett pris i en sats får inte hämta sin källa ur ett tal i en annan.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    generera.krav_pa_tal_med_kalla(
        "Konverteringen kostar 25 000 kr. Vi hör av oss.", forfragan())

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(
            "Vikten är 25 000. Det kostar en del.", forfragan())


def test_ett_PRISORD_UTAN_TAL_faller_aven_nar_filen_ar_fylld(monkeypatch):
    """*"Det kostar en del"* är ett prispåstående utan avläsbar källa.

    Utan den här grenen hade en fylld prisfil gjort varje vagt prisord tillåtet,
    alltså hade filen köpt fri passage åt meningar som inte nämner något pris.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla("Det kostar en del.", forfragan())

    assert "utan att ange ett tal" in fel.value.skal


# --- SKIVA 44, LARS VÄG TVÅ: TELEFONNUMRET I EN PRISSATS --------------------


def _med_konfig(monkeypatch, priser: dict, fakta: dict) -> None:
    """Låtsas att BÅDA §10-filerna bär `priser` respektive `fakta`.

    **BÅDA PATCHAS, och det är LUCKA 58:s föreskrivna form.** Tre äldre
    spärrtest patchar EN konfigfil och låter den andra vara den riktiga, medan
    `_tillatna_tal` läser båda. Ett sådant test går rött av en laglig post i den
    opatchade filen, alltså av Lars beslut i stället för av en defekt.

    Byter ut den RÅA läsningen, `las_konfig`, av samma skäl som `_med_priser`:
    filen har två läsare med olika krav och båda går den vägen.
    """
    riktig = generera.las_konfig

    def las(fil):
        if fil == generera.PRISER:
            return dict(priser)
        if fil == generera.FAKTA:
            return dict(fakta)
        return riktig(fil)

    monkeypatch.setattr(generera, "las_konfig", las)


def test_telefonnumret_ORDAGRANT_ar_en_kalla_i_en_prissats(monkeypatch):
    """LARS VÄG TVÅ I SKIVA 44. Prompten beordrar formen, spärren fällde den.

    Regel 14 säger att ett svar som nämner ett pris ska följa det med
    telefonnumret. Prisgrenen kräver att varje tal i en prissats kommer ur
    `config/priser.json`, och numrets siffergrupper gör det inte, alltså fälldes
    ett svar som var korrekt för kunden. FYRA av tjugo körda mail spärrades på
    just den formen.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    generera.krav_pa_tal_med_kalla(
        "Ombyggnaden kostar 25 000 kr, ring oss på 076-860 38 15.",
        forfragan(),
    )


def test_ett_OMSKRIVET_telefonnummer_faller_FORTFARANDE_i_en_prissats(monkeypatch):
    """LEDET SOM GÖR `ORDAGRANT` LASTBÄRANDE, och utan det är väg två en sänkt
    tröskel.

    Samma siffror, annan skrivform. Det är inte det värde `config/fakta.json`
    bär, alltså är det ingen avläsning. Utan den här raden vore "dra alltid bort
    numrets siffergrupper" en grön lösning, och då hade villkoret slutat pröva
    satsen alls.

    **SKRIVFORMEN ÄR VALD SÅ ATT DEN GER IDENTISK TALMÄNGD, och det ledet är
    fällt fram.** En första lydelse bytte bindestrecket mot ett BLANKSTEG. Då gav
    `_tal_i` tokenet `076860` i stället för `076` och `860`, eftersom
    `TAL_I_TEXT` tar en blankstegsavskiljare följd av exakt tre siffror som en
    del av talet. Raden gick alltså röd av att talmängden BLEV EN ANNAN, inte av
    att strängen inte matchade, och en fällning av `telefon in sats` till
    `telefon` gav GRÖN svit. Uppmätt med `scripts/sparr-prova.sh`.

    `076-860-38-15` ger exakt samma talmängd som värdet i config. Det enda som
    skiljer är strängen, alltså är det bara `in`-prövningen som kan fälla den.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Ombyggnaden kostar 25 000 kr, ring oss på 076-860-38-15.",
            forfragan(),
        )

    assert "076" in fel.value.skal


def test_telefonnumret_ENSAMT_ar_INGET_prisbesked(monkeypatch):
    """INVARIANTEN STÅR KVAR: en prissats måste bära minst ett tal ur priskällan.

    **DÄRFÖR DRAS NUMRETS TAL BORT I STÄLLET FÖR ATT LÄGGAS TILL.** Ett tillägg
    hade gjort den här meningen till ett godkänt prisbesked utan belopp, alltså
    tagit bort den gren som fäller ett prisord utan tal. Skillnaden mellan de två
    lydelserna syns bara här.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Ring oss på 076-860 38 15 för pris.", forfragan())

    assert "utan att ange ett tal" in fel.value.skal


def test_en_TOM_telefonpost_ger_INGEN_ratt_i_en_prissats(monkeypatch):
    """Ett tomt värde är ingen avläsning, och undantaget vilar på värdet.

    Utan den här raden hade en fällning som läser nyckeln i stället för värdet
    varit grön, och då hade siffergrupperna släppts igenom av att posten FANNS.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": ""})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Ombyggnaden kostar 25 000 kr, ring oss på 076-860 38 15.",
            forfragan(),
        )

    assert "076" in fel.value.skal


def test_prisblockets_ram_star_ORDAGRANT():
    """SÄNDVÄGSTEXT SOM VAR OBUNDEN, och kommentaren påstod motsatsen.

    **`FAKTARUBRIK` OCH `FAKTAFOT` BINDS ORDAGRANT SEDAN SKIVA 37**, efter att
    en lydelse som bad modellen hitta på mer om oss passerade hela sviten.
    Prisblockets ram fick samma kommentar och ingen bindning: en lydelse som bad
    modellen UPPSKATTA ett pris gav grön svit. Fällt av §7-granskningen av
    skiva 41, varv 1.
    """
    assert generera.PRISRUBRIK == (
        "Priser, avlästa ur config/priser.json. Du har inga andra priser, och "
        "du uppskattar aldrig ett pris som inte står här:\n"
    )
    # HELHETSKRAVET ÄR LARS BESLUT I SKIVA 44, och det kom ur ett läst utkast:
    # boten skrev *"startar från 20 000 kr"* om en post vars värde är
    # `från 20 000 till 25 000 kr ...`. Varje tal hade en källa, alltså fällde
    # ingen spärr, men kunden läser ett annat prisbesked än filen bär. Foten är
    # det som bär, och därför binds den ORDAGRANT här.
    assert generera.PRISFOT == (
        "Varje pris här återges ORDAGRANT och ändras aldrig, och det återges i "
        "SIN HELHET eller inte alls. Är priset ett intervall skriver du båda "
        "gränserna. Plocka aldrig ut en del av en prisrad, och gör aldrig om "
        "ett pris till ett ungefärligt.\n"
    )
    assert generera.INGA_PRISER == (
        "Priser: INGA. Du har inga prisuppgifter alls."
    )


def test_prisblocket_bar_ramen_nar_filen_ar_fylld(monkeypatch):
    """Och att ramen FAKTISKT används, inte bara att konstanterna finns."""
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    block = generera._prisrader()
    assert block.startswith(generera.PRISRUBRIK)
    assert block.endswith(generera.PRISFOT)
    assert "  a_traktorkonvertering: 25 000 kr" in block


def test_prisfilens_KOMMENTARER_blir_ALDRIG_tillatna_tal():
    """SKIVA 36:s HÅL, prövat på den nya filen INNAN den fylls.

    **`config/fakta.json` BLEV VÄGEN RUNT KRAVET PÅ KÄLLA.** Två
    kommentarnycklar nämnde `§7.2` och `§10`, och därmed blev 7 och 10 tillåtna
    tal i ett utgående mail: *"vi hör av oss inom 10 dagar"* passerade spärren,
    uppmätt i skiva 36. Det bryter §0:s ramverksregel 3, som är obrytbar.

    **PRISFILENS KOMMENTARER BÄR MED FLIT ETT PRISFORMAT TAL.** `_formen`
    innehåller exemplet `25 000 kr`, alltså är den här raden inte teoretisk: utan
    filtret hade boten fått skriva just det talet som ett pris.

    Raden prövar BÅDA leden: att inget tal som BARA står i en kommentar når
    `_tillatna_tal`, och att kommentarerna faktiskt bär ett prisformat tal. Utan
    det andra ledet vore testet grönt även om kommentarerna togs bort, alltså
    vakuöst.

    **URVALET UTESLUTER TAL SOM HAR EN ANNAN KÄLLA, och det är skiva 43:s
    ändring.** Raden jämförde tidigare HELA filens tal mot `_tillatna_tal`. Den
    mängden rymmer `25000` ur `_formen`, som samtidigt är ett fullt rimligt pris,
    alltså gick raden röd den dag Lars fyllde filen med just det beloppet trots
    att filtret fungerade precis som det ska. Den prövar nu differensen: tal som
    står i en kommentar men saknar varje LAGLIG källa. Ett tal som fått en sådan
    är inte längre ett läckage.

    **DE LAGLIGA KÄLLORNA ÄR `_tillatna_tal`:s EGNA, alla fyra.**
    `ALLTID_TILLATNA_TAL`, uppslagets två vikter, och VÄRDENA i `config/priser.json`
    OCH `config/fakta.json`. Fixturen ger inget uppslag, och raden binder det, så
    att vikterna inte tyst börjar bära differensen.

    *Skiva 43:s FÖRSTA lydelse prövade STRÄNGIDENTITET och kallade det "strikt
    starkare". Den var strikt SVAGARE: en `_varden_ur` utan kommentarfilter
    släpper varje kommentartal vidare till `_tillatna_tal` medan ingen
    kommentarsträng behöver vara identisk med en post i utdatalistan. Den
    fällningen gav GRÖNT. Motiveringen var dessutom falsk: `_tillatna_tal` hämtar
    inte sina tal enbart ur `_varden_ur`. Fällt av §7-granskningen av skiva 43,
    varv 1.*

    *ANDRA LYDELSEN DROG BARA BORT VÄRDENA I PRISFILEN och
    `ALLTID_TILLATNA_TAL`, alltså inte `config/fakta.json` och inte uppslagets
    vikter. Uppmätt: en fullt laglig ledtid i faktafilen, `vi hör av oss inom 14
    dagar`, gjorde raden RÖD, eftersom `14` också ligger i datumet i prisfilens
    `_nycklarna`. Det är exakt den defektklass skivan byggdes för att ta bort,
    flyttad från `priser.json` till `fakta.json`. Fällt av §7-granskningen av
    skiva 43, varv 2.*
    """
    kommentarernas_tal = set()
    lagliga_tal = set(generera.ALLTID_TILLATNA_TAL)
    for fil in (generera.PRISER, generera.FAKTA):
        rat = json.loads(fil.read_text(encoding="utf-8"))
        for namn, varde in rat.items():
            if not str(namn).startswith("_"):
                lagliga_tal |= generera._tal_i(str(varde))
            elif fil == generera.PRISER:
                kommentarernas_tal |= generera._tal_i(str(varde))

    # LEDET SOM GÖR RADEN ICKE-VAKUÖS: kommentarerna bär faktiskt ett prisformat
    # tal, alltså finns det något att läcka. Ledet läser BARA kommentarerna och
    # påverkas därför inte av att Lars fyller en post.
    assert "25000" in kommentarernas_tal, (
        "kommentaren tappade sitt prisformade tal, och då prövar raden inget"
    )

    # UPPSLAGETS VIKTER ÄR OCKSÅ EN LAGLIG KÄLLA. Fixturen ger inget uppslag, och
    # raden binder det i stället för att subtrahera en mängd som är tom.
    fall = forfragan()
    assert fall.uppslag is None, (
        "fixturen har fått ett uppslag, och då måste dess vikter dras bort ur "
        "de lagliga talen innan differensen beräknas"
    )

    # LEDET SOM ÄR SPÄRREN: ett tal som bara en kommentar bär har ingen källa.
    utan_annan_kalla = kommentarernas_tal - lagliga_tal
    assert utan_annan_kalla, (
        "varje kommentartal har en annan källa, och då prövar raden inget"
    )

    tillatna = generera._tillatna_tal(fall)
    for tal in sorted(utan_annan_kalla):
        assert tal not in tillatna, f"{tal} kom in via en kommentarnyckel"


# --- SKIVA 43 DEL A: KORPUSENS SENTINELTAL -----------------------------------


def test_SENTINELTALET_ar_samma_i_varje_skrivform():
    """`tests/sentinelpris.py`:s centrala påstående, bundet.

    Modulen säger att båda skrivformerna ger samma token ur `_tal_i`, och det är
    hela grunden för att korpusen kan blanda dem fritt: en fylld prisfil ska
    antingen göra alla sentinelrader gröna eller ingen. Påståendet var OBUNDET
    när modulen skrevs. Fällt av §7-granskningen av skiva 43, varv 1.
    """
    assert generera._tal_i(f"Det kostar {SENTINELPRIS} kr.") == {SENTINELTAL}
    assert generera._tal_i(f"Vi tar {SENTINELPRIS_IHOP}kr.") == {SENTINELTAL}
    assert generera._tal_i(f"Det blir {SENTINELPRIS_IHOP}tkr.") == {SENTINELTAL}


# --- SKIVA 42 DEL 0: LUCKA 53, PLATT FIL -------------------------------------


def test_bada_konfigfilerna_i_repot_ar_PLATTA():
    """LARS BESLUT I SKIVA 42, LUCKA 53: platt fil, ingen nästling.

    **VAD NÄSTLINGEN KOSTAR.** `las_konfigvarden` filtrerade `_`-nycklar bara på
    toppnivån och körde sedan `str(v)` på vad som helst. En nästlad post
    renderade därför hela sin repr i prompten, med varje inre kommentar inbakad,
    under rubriken *"Priser, avlästa ur config/priser.json"* och över foten
    *"Varje pris här återges ordagrant"*. Det är lucka 53, uppmätt av
    §7-granskningen av skiva 41, varv 2.

    Den här raden är TRIPWIREN för filerna i repot. Koden bär sitt eget skydd,
    prövat av `test_ett_NASTLAT_varde_nar_ALDRIG_prompten`; den här raden går röd
    den dag någon nästlar en post, så att nästlingen blir ett medvetet val och
    inte en tyst form.
    """
    for fil in (generera.PRISER, generera.FAKTA):
        data = json.loads(fil.read_text(encoding="utf-8"))
        for namn, varde in data.items():
            assert isinstance(varde, str), (
                f"{fil.name}: posten {namn!r} är nästlad. Filen ska vara PLATT, "
                "Lars beslut i skiva 42. En nästlad struktur renderar sina "
                "interna kommentarer i prompten."
            )


@pytest.mark.parametrize(
    "filnamn, renderare",
    [("PRISER", "_prisrader"), ("FAKTA", "_faktarader")],
)
def test_ett_NASTLAT_varde_nar_ALDRIG_prompten(filnamn, renderare, tmp_path,
                                               monkeypatch):
    """SPÄRR: koden släpper inte igenom nästlingen, oavsett vad filen bär.

    **VÄRDET I EXEMPLET ÄR VÅRT INKÖPSPRIS**, alltså precis det som inte får bli
    ett citerbart pris. Talets halva var redan stängd av `_varden_ur`, som
    hindrar att 9000 blir ett tillåtet tal. TEXTENS halva var öppen: ingenting
    hindrade att raden stod i prompten.

    **NEGATIVKONTROLLEN LIGGER I SAMMA RAD.** Utan den vore "returnera alltid
    tomt" en grön lösning, och då hade filtret tagit Lars priser med sig.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"nastlad": {"_internt": "kostar oss 9 000 kr", "pris": "25 000 kr"},'
        ' "platt": "1 500 kr"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(generera, filnamn, fil)

    block = getattr(generera, renderare)()

    assert "_internt" not in block, block
    assert "kostar oss" not in block, block
    assert "9 000" not in block, block
    assert "1 500 kr" in block, block


# --- SKIVA 42 DEL 0: LUCKA 54, SATSPAR FOGAS SAMMAN --------------------------


def test_prisfrasen_fogas_ihop_over_meningsgransen():
    """ENHETEN: `_prissatser` lagar det `_meningar` klöv.

    `inkl. moms` klyvs av förkortningspunkten, och ingendera halvan matchar
    `PRISORD`. Utan hopfogningen finns ingen prissats alls att pröva här.
    """
    assert generera._prissatser("Vi hör av oss. Det är inkl. moms.") == [
        "Det är inkl. moms."
    ]


@pytest.mark.parametrize(
    "svar",
    [
        # DE TRE SOM MÄTTES UPP I SKIVA 41 VARV 3, ordagrant ur
        # `docs/sparrar.md`:s post för lucka 54. Alla tre PASSERADE då.
        "Konverteringen kostar 25 000 kr. Dragkroken blir 1400 extra inkl. moms.",
        "Konverteringen kostar 25 000 kr. Tillägget är 3 extra exkl. moms.",
        "Konverteringen kostar 25 000 kr. Tillägget är 2 inkl. moms.",
        # OCH FORMEN SOM SKILJER DE TVÅ TÄNKBARA EGENSKAPERNA ÅT. Här bär den
        # FÖRSTA halvan ett eget giltigt prisord, alltså hade ett villkor av
        # formen "ingendera halvan bär ett prisord" låtit paret vara, och
        # `moms 1400.` hade aldrig prövats av prisgrenen.
        "Det kostar 25 000 kr exkl. moms 1400.",
        # OCH FORMEN SOM KRÄVER ATT HOPFOGNINGEN GÅR I KEDJA. Mittendelen bär
        # slutet av en prisfras OCH början av nästa. En PARVIS regel som hoppar
        # två steg efter en hopfogning prövar aldrig den andra skarven, och då
        # blir `moms 1400.` föräldralös och når aldrig prisgrenen. Uppmätt av
        # §7-granskningen av skiva 42, varv 1: texten PASSERADE.
        "Det kostar 25 000 kr exkl. moms är inkl. moms 1400.",
    ],
)
def test_en_SONDERKLYVD_prissats_provas_av_PRISGRENEN(monkeypatch, svar):
    """LUCKA 54 STÄNGD. Lars beslut i skiva 42: foga samman satspar.

    Reserven i `_prissatser` fångade klyvningen BARA när ingen sats alls bar ett
    prisord. Bar en annan mening ett giltigt prisord blev urvalet icke-tomt,
    reserven löpte aldrig, och den klyvda satsen föll ned i den ALLMÄNNA
    talloopen, vars mängd bär uppslagets vikter och `ALLTID_TILLATNA_TAL`.

    Fixturen bär ett uppslag med tjänstevikt 1400 och släpvagnsvikt 1500, alltså
    är `1400` ett tal som FINNS i den allmänna mängden. Det är hela defekten:
    fordonets tjänstevikt blev ett citerbart pris.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(svar, forfragan(uppslag=GRONT_UPPSLAG))

    assert fel.value.sparr == "genererat-tal-har-kalla"


def test_en_SATSBROTT_SKARV_fogas_ALDRIG_ihop(monkeypatch):
    """HOPFOGNINGEN FÅR ALDRIG TILLVERKA EN PRISFRAS SOM INTE STÅR I SVARET.

    `_delat_pa_satsbrott` KASTAR sin avskiljare. Fogades en sådan skarv ihop med
    ett blanksteg blev *"Vi tar det exkl, men moms är inräknad 1400."* till
    `exkl moms`, och då fälldes en AVLÄST tjänstevikt med motiveringen att den
    står i en prismening. Texten bär inget prisord alls.

    En hopfogning över en MENINGSSKARV normaliserar i stället bara blanktecken,
    och kan varken skapa eller förstöra en pristerm, eftersom varje flerordsterm
    tar godtyckligt många blanktecken med `\\s*`. *Här stod att meningsdelningen
    "tar bort BARA blanktecken, alltså går den att ångra". Delningen tar ett
    eller flera och hopfogningen skarvar med ett, alltså är det en normalisering
    och ingen ångring. Fällt av §7-granskningen av skiva 42, varv 2.*

    Uppmätt av §7-granskningen av skiva 42, varv 1. Skyddet är ordningen i
    `_prissatser`: meningar, hopfogning, sedan `SATSBROTT`.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})
    svar = "Vi tar det exkl, men moms är inräknad 1400."

    # LEDET SOM GÖR RADEN ICKE-VAKUÖS: texten bär FAKTISKT inget prisord.
    assert not generera.PRISORD.search(svar), svar

    assert generera._prissatser(svar) == []
    generera.krav_pa_tal_med_kalla(svar, forfragan(uppslag=GRONT_UPPSLAG))


def test_ett_AVLAST_pris_MED_momsangivelse_slapps_igenom(monkeypatch):
    """NEGATIVKONTROLL: hopfogningen får inte göra prisgrenen till ett larm.

    Står hela prisfrasen i `config/priser.json` ska svaret som återger den
    ordagrant passera. En spärr som fäller det prompten beställer är §9.1:s
    motsägelse, och den blir avstängd.
    """
    _med_priser(monkeypatch,
                {"a_traktorkonvertering": "25 000 kr inkl. moms"})

    generera.krav_pa_tal_med_kalla(
        "Konverteringen kostar 25 000 kr inkl. moms.",
        forfragan(uppslag=GRONT_UPPSLAG))


@pytest.mark.parametrize(
    "svar",
    [
        "Din bil väger 1400 kg, och konverteringen kostar 25 000 kr.",
        "Konverteringen kostar 25 000 kr och tar 2 veckor.",
    ],
)
def test_LUCKA_55_overblockeringen_STAR_KVAR_och_ar_beslutad(monkeypatch, svar):
    """LUCKA 55 ÄR INTE STÄNGD, och den här raden binder att den inte är det.

    `, och ` är struket ur `SATSBROTT`, alltså prövas en samordnad mening som EN
    prissats, och prisgrenen kräver att VARJE tal i en prissats kommer ur
    `config/priser.json`. Båda raderna nedan är SANNA meningar som ändå faller:
    den första på en avläst vikt ur uppslaget, den andra på en ledtid.

    **LARS BESLUT I SKIVA 42, ordagrant hans skäl:** överblockering kostar Lars
    fem sekunders läsning, underblockering kostar ett felaktigt prisbesked till
    en kund. Utfallet blir `utkast`, och Lars läser varje utkast.

    Raden står här för att kostnaden ska vara SYNLIG och inte glömd. Den dag
    lucka 55 stängs blir den röd, och då ska det vara ett beslut.
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(svar, forfragan(uppslag=GRONT_UPPSLAG))


@pytest.mark.parametrize("svar", ["", "   ", "\n\n", "\t \n"])
def test_ett_TOMT_svar_ar_INGET_utkast(svar):
    """SPÄRR: de tre andra spärrarna SÖKER EFTER SAKER och släpper det tomma.

    Följden var att ett tomt modellsvar blev ett godkänt utkast utan spärr:
    `blev_utkast` sant och `forslag` tomt. I vyn blev det ett tomt textfält som
    gick att omdöma, och ett `forbattra` hade skrivit ett par med tom förlaga
    till `data/par.jsonl`, som generatorn läser som få-exempel.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_svaret(svar, forfragan())

    assert fel.value.sparr == "tomt-svar"


def test_ett_pris_UTAN_KALLA_faller_mot_repots_egen_prisfil():
    """Ett pris som filen inte bär faller, läst mot den RIKTIGA filen.

    §7.2 säger att ett tal är avläst eller utelämnat, och det finns ingen tredje
    kategori.

    **RADEN LÄSER DEN RIKTIGA FILEN**, till skillnad från raderna ovan som
    patchar läsningen. Den prövar vägen fil, `las_konfig`, `las_priser`,
    prisgrenen. *Här stod att den prövar `_varden_ur`. Den vägen är en ANNAN:
    prisgrenen hämtar sina tal ur `las_priser` och kastar innan `_tillatna_tal`
    alls nås. En fällning som kopplar bort `_varden_ur` ur `_tillatna_tal` låter
    den här raden vara GRÖN. Fällt av §7-granskningen av skiva 43, varv 1.*

    *Testet hette `test_ett_pris_faller_alltid` och sade att
    `config/priser.json` existerar inte. Filen skapades av skiva 41, och ordet
    ALLTID var fel redan då: en fällning av filens första post gav `DID NOT
    RAISE`. Fällt av §7-granskningen av skiva 41, varv 1 och varv 2.*

    *Och sedan hette det `..._med_repots_egen_TOMMA_prisfil`, med en docstring som
    sade att raden SKA bli röd den dag någon fyller en post. Det var en andra
    §10-tripwire i förklädnad: den gick röd av Lars beslut utan att vakta det.
    Raden bär nu `SENTINELPRIS`, alltså ett tal Lars aldrig kan fylla, och prövar
    det den heter. Lars beslut i skiva 43, se `docs/beslutslogg.md` #103.*

    *Noten sade först att den här raden "gjorde att elva vakter gick röda". Ett
    enskilt test kan på sin höjd göra sig självt rött; de övriga gick röda av
    korpusens exempeltal. Fällt av §7-granskningen av skiva 43, varv 1.*
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            f"Ombyggnaden kostar {SENTINELPRIS} kr.", forfragan())

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


# ---------------- LUCKA 30 ÄR ÖPPEN, och kundens text är INGEN källa
#
# Skiva 33 fick i uppdrag att låta `_tillatna_tal` läsa `forfragan.text`, så att
# `V50` slutar fällas som ett påhittat tal. **Tre lydelser byggdes och alla tre
# återställdes**, eftersom var och en lät ett PRIS eller en LEDTID ur kundens
# text nå ut. Det bryter mot §0:s ramverksregel 3, som är obrytbar. Historien
# står i `docs/beslutslogg.md` #56.
#
# Raderna nedan är därför tvådelade: en som asserterar den ÖPPNA luckan, så att
# den syns och blir röd den dag den stängs, och flera som binder att kundens text
# aldrig gör ett tal tillåtet. De senare är regressionsvakter mot de tre
# lydelserna, inte kontroller av en funktion som finns.


@pytest.mark.parametrize(
    "svar",
    ["Din V50 går bra att bygga om.",
     "Din A5 går bra att bygga om.",
     "Bilen ABC156 går bra att bygga om."],
)
def test_en_BETECKNING_faller_FORTFARANDE(svar):
    """LUCKA 30 ÄR ÖPPEN, och den här raden är dess mätning.

    En modellbeteckning fälls som ett påhittat tal. Fem av elva fällningar i
    skiva 32:s mätning över 100 svar var av den här formen.

    **RADEN ASSERTERAR DEFEKTEN, inte önskeläget**, och det är avsiktligt: en
    lucka som är mätt är synlig, och den dag någon stänger luckan blir raden röd
    och tvingar fram sin egen borttagning. Skiva 33 försökte stänga den i tre
    lydelser och återställde alla tre, se `docs/beslutslogg.md` #56.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(svar, forfragan(text="Hej!"))


@pytest.mark.parametrize(
    "kundtext, svar",
    [
        # Varv 2:s fynd: bokstäver FÖRE siffran gjorde en kvantitet till en
        # beteckning, alltså räckte det att kunden nämnde beloppet.
        (f"Jag har fått pris ca{SENTINELPRIS_IHOP} hos en annan verkstad.",
         f"Vi gör det för {SENTINELPRIS_IHOP}."),
        (f"Jag har fått pris SEK{SENTINELPRIS_IHOP} av en annan.",
         f"Det landar på {SENTINELPRIS_IHOP} hos oss."),
        # *Raden bar `123456`, som är osannolikt men inte omöjligt som pris och
        # gick röd när en post fylldes med `123456 kr`. Formen, ett tal ur en
        # länk, är oförändrad. Fällt av §7-granskningen av skiva 43, varv 2.*
        (f"Se annonsen blocket.se/annons{SENTINELPRIS_IHOP}",
         f"Det blir {SENTINELPRIS_IHOP}."),
        # Varv 2:s fynd om lucka 36: kundens beteckning fick bli en ledtid.
        ("Jag har en A5, går den att bygga om?", "Vi hinner på 5 dagar."),
        ("Min bil är en V70.", "Vi hinner på 70 dagar."),
    ],
)
def test_kundens_tal_gor_ALDRIG_ett_svarstal_tillatet(kundtext, svar):
    """§0:s ramverksregel 3: att kunden nämnt ett tal gör det inte till en källa.

    Varje rad här passerade i någon av skiva 33:s två första lydelser. De två
    första leden är ett PRIS, det tredje ett godtyckligt tal ur en länk, och de
    två sista en LEDTID byggd på kundens modellbeteckning.
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(svar, forfragan(text=kundtext))


def test_ett_PRIS_ur_kundens_text_faller():
    """§0:s ramverksregel 3 är OBRYTBAR: priser läses ur källa eller utelämnas.

    **DET HÄR ÄR HÅLET SOM SKIVA 33 SJÄLV INFÖRDE OCH SOM GRANSKNINGEN FÄLLDE.**
    Första lydelsen tog varje tal ur `forfragan.text`, alltså kunde boten skriva
    ett pris som vårt eget så snart kunden hade nämnt talet, utan att något
    prisord behövdes. Att kunden har fått en offert av NÅGON ANNAN gör inte
    beloppet till vårt.
    """
    kundens = forfragan(
        text=f"Jag har fått offert på {SENTINELPRIS_IHOP} kr någon annanstans.")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(
            f"Vi gör det för {SENTINELPRIS_IHOP}.", kundens)


def test_en_LEDTID_ur_kundens_text_faller():
    """Samma regel, andra ledet: ledtider läses ur källa eller utelämnas."""
    kundens = forfragan(text="Kan ni fixa det på 14 dagar?")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla("Vi hinner med det på 14 dagar.", kundens)


def test_kundens_VIKT_faller():
    """En vikt kunden uppgett är ett obelagt påstående om bilen.

    Bilens vikter kommer ur UPPSLAGET. Att kunden skrivit en siffra gör den inte
    avläst, och ett svar som återger den låter som en bekräftelse.
    """
    kundens = forfragan(text="Min bil väger 1450 kg.")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla("Din bil väger 1450 kg.", kundens)


@pytest.mark.parametrize(
    "svar",
    [
        # Enheten EFTER siffran gör det till en kvantitet, inte en beteckning.
        # Det var skiva 31:s värsta hål och får inte återkomma.
        f"Vi tar {SENTINELPRIS_IHOP}kr för jobbet.",
        # *Raden bar `1000kg`. Talet är också ett fullt rimligt pris, och raden
        # gick röd när en post i `config/priser.json` fylldes med `1 000 kr`.
        # Formen, enheten ihopskriven med siffran, är oförändrad. Fällt av
        # §7-granskningen av skiva 43, varv 1.*
        f"Bilen klarar {SENTINELPRIS_IHOP}kg.",
        # Fler än tre siffror är ingen modellbeteckning.
        f"Vi gör det för ca{SENTINELPRIS_IHOP}.",
        # Ett fristående tal är alltid en kvantitet.
        # *Raden bar `55`, som är ett fullt rimligt pris för en post under `dack`
        # eller `tillbehor`, och gick röd när en post fylldes med `55 kr`.
        # Formen, ett fristående tal utan enhet, är oförändrad. Fällt av
        # §7-granskningen av skiva 43, varv 2.*
        f"Tillsammans blir det {SENTINELPRIS_IHOP}.",
        # *Raden bar `15 dagar`. Talet gick röd när Lars fyllde
        # `config/fakta.json` med verkstadens telefonnummer, `076-860 38 15`,
        # vars sista grupp `_tal_i` normaliserar till just `15`. Formen, ett tal
        # följt av sin enhet som eget ord, är oförändrad. Det är LUCKA 58:s
        # föreskrivna åtgärd för den här raden, och lucka 57:s mätning
        # *"ETT TELEFONNUMMER UTLÖSER DEN INTE"* är därmed falsifierad: den mätte
        # ett nummer vars siffergrupper råkade sakna korpusens tal.
        f"Vi hinner på {SENTINELPRIS_IHOP} dagar.",
    ],
)
def test_ett_tal_UTAN_KALLA_faller_i_varje_skrivform(svar):
    """Skrivformen får aldrig göra ett tal osynligt för spärren.

    De två första raderna är skiva 31:s värsta hål: ett tal ihopskrivet med sin
    enhet gav en TOM mängd, alltså gick den vanligaste svenska skrivformen rakt
    igenom alla tre spärrarna.

    *Raden hette `test_en_KVANTITET_ar_ingen_beteckning` och prövade gränsen mot
    en beteckningsregel som skiva 33 återställde. Utan den regeln fanns ingen
    sådan gräns, och namnet påstod något testet inte längre prövade. §7.1: döp om
    det till vad det faktiskt bevisar.*
    """
    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla(svar, forfragan(text="Hej!"))


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
     f"Det brukar hamna runt {SENTINELPRIS_IHOP}tkr."],
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


# ------------------------------------------ spärrarna tillsammans
#
# *Rubriken löd "alla tre tillsammans". Tabellen nedan bär fyra rader och
# `krav_pa_svaret` anropar sex spärrar. Fällt av §7-granskningen av skiva 46.*


@pytest.mark.parametrize(
    "svar, sparr, fall",
    [
        (f"Det kostar {SENTINELPRIS} kr.", "genererat-tal-har-kalla", forfragan()),
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
        # SKIVA 46, LUCKA 59. Raden bär varken tal eller prisord, alltså kan
        # ingen annan spärr rapportera den: det är hela skälet till att klassen
        # behövde en egen.
        #
        # **RADEN SÄGER `Rekonden` OCH INTE `Dragkroken`, och det är mätt.** Den
        # utlösande meningen i ärende 19 bär ordet `dragkrok`, som är ett
        # `FORDONSORD`, alltså rapporterade `genererat-fordonsfaktum` den först
        # och raden prövade fel spärr. Just den fällan varnar docstringen nedan
        # för, och den slog till vid första körningen.
        ("Rekonden ingår i bygget.", "atagande-om-priset", forfragan()),
    ],
)
def test_krav_pa_svaret_anropar_sparrarna_i_tabellen(svar, sparr, fall):
    """`krav_pa_svaret` ska fälla på var och en av spärrarna i tabellen ovan.

    Faller en av dem ur den samlande funktionen syns det här, och inte först när
    ett svar med det felet går vidare.

    *Raden hette `test_krav_pa_svaret_anropar_alla_tre` och tabellen bar tre rader
    medan `krav_pa_svaret` anropade fem spärrar. Namnet påstod en fullständighet
    tabellen inte hade. `tomt-svar` och `pastaende-om-franvaro` står fortfarande
    utanför den här tabellen och prövas av sina egna rader. Rättat i skiva 46,
    som lade till en fjärde rad och därmed gjorde namnet ännu falskare.*

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


def test_prompten_sager_att_priser_inte_finns(monkeypatch):
    """Modellen ska veta att den inte har priser, inte gissa att den har det.

    **RADEN PRÖVAR MEKANISMEN MED EN TOM FIL, inte repots filtillstånd.** Den
    läste tidigare den riktiga filen och gick därför röd den dag Lars fyllde en
    post, trots att mekanismen fungerade: med en fylld fil SKA prompten inte säga
    `Priser: INGA`. Vad filen i repot BÄR vaktas av
    `test_prisfilen_i_repot_bar_EXAKT_det_Lars_BESLUTAT`, som är §10-tripwiren,
    och en tripwire till gör bara att fler rader går röda av samma beslut. Lars
    beslut i skiva 43, se `docs/beslutslogg.md` #103.

    *Här stod att filen i repot ÄR TOM och att den vaktas av
    `test_prisfilen_i_repot_har_BARA_TOMMA_varden`. Lars fyllde filen i skiva 44
    och vakten band om och bytte namn i samma skiva, alltså namngav raden en vakt
    som inte finns och påstod ett filtillstånd som inte gäller. Den defekten är
    exakt vad den här radens egen förklaring ovan handlar om, ett led ned.*
    """
    _med_priser(monkeypatch, {})

    assert "Priser: INGA" in generera.bygg_prompt(forfragan(), exempel=[])


def test_prompten_bar_PRISET_nar_filen_ar_fylld(monkeypatch):
    """NEGATIVKONTROLL till raden ovan, på `bygg_prompt`-nivå.

    **MEKANISMEN VAR REDAN TÄCKT, och det ska sägas.** En lydelse som alltid
    säger `Priser: INGA` fälls också av `test_prisblocket_bar_ramen_nar_filen_ar_fylld`
    och av `test_ett_NASTLAT_varde_nar_ALDRIG_prompten[PRISER-_prisrader]`, båda
    äldre än skiva 43. Den här raden lägger till att priset når hela vägen ut i
    PROMPTEN och inte bara ur `_prisrader`, vilket är det led raden ovanför
    prövar från andra hållet.

    *Här stod att negativkontrollen "saknades" och att "säg alltid Priser: INGA"
    hade varit en grön lösning. Båda leden är falska: fällningen ger tre röda
    rader, varav två fanns före skivan. Fällt av §7-granskningen av skiva 43,
    varv 1.*
    """
    _med_priser(monkeypatch, {"a_traktorkonvertering": "25 000 kr"})

    prompt = generera.bygg_prompt(forfragan(), exempel=[])

    assert "Priser: INGA" not in prompt
    assert "a_traktorkonvertering: 25 000 kr" in prompt


# SYSTEMPROMPTENS REGLER, en rad per regel, ordagrant.
#
# *Här stod "SJU REGLER" över en tabell som skiva 33 gav en åttonde post. Antalet
# står inte längre i rubriken, eftersom en rubrik som räknar sin egen omgivning
# blir falsk av nästa tillägg, §7.2. Fällt av §7-granskningen av skiva 33.*
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
    # SKIVA 36: "en kollega" är struket. Regeln var SJÄLV källan till formen
    # regel 9 nu förbjuder, alltså föreskrev prompten det Lars invände mot.
    # SKIVA 42, LUCKA 52. Förbehållet är Lars, ORDAGRANT hans lydelse: "aldrig
    # ett pris UTÖVER DET SOM STÅR I UNDERLAGET NEDAN", av samma form som
    # regel 8:s. Utan det sade regeln emot `PRISRUBRIK`, som ber modellen
    # återge priset ur `config/priser.json` ordagrant, i samma ögonblick Lars
    # fyller en post.
    #
    # **SLUTMENINGENS VILLKOR ÄR LARS SEDAN SKIVA 43.** Utan `Står inget pris i
    # underlaget` beordrar regeln i en och samma andetag både att priset FÅR
    # återges och att kunden ska få höra att vi återkommer med prisuppgift.
    # Det är samma motsägelse förbehållet stänger, ett led ned.
    #
    # *Villkoret skrevs av mig i skiva 42 och redovisades där som MITT, eftersom
    # §11 gör promptens ordalydelse till Lars. Han antog det som sitt i skiva 43,
    # se `docs/beslutslogg.md` #102. Texten är oförändrad; det som ändrats är vem
    # som står för den.*
    5: "ALDRIG ETT PRIS utöver det som står i underlaget nedan. Inte ett "
       'belopp, inte ett ungefärligt pris, inte "ring för offert". Står inget '
       "pris i underlaget och kunden frågar vad det kostar: säg att VI "
       "återkommer med prisuppgift.",
    6: "ALDRIG ETT TAL som inte står i underlaget nedan. Inga vikter, inga "
       "ledtider, inga antal du inte fått.",
    7: "Återge aldrig en lagtext eller en föreskrift sammanfattad. Säg inte att "
       "något är ett krav enligt lag.",
    # SKIVA 33, LUCKA 29. Formen mättes till 5 av 100 svar innan regeln fanns,
    # och tre av dem hänvisade till vad vår hemsida innehåller. Regeln är
    # åtgärdens ena hälft; den andra är att RÖTT-svaret nu har något verkligt
    # att erbjuda, se `_utfallstext`.
    8: "Påstå aldrig något om vad Auto Stockholm har, erbjuder eller innehåller "
       "utöver det som står i underlaget nedan. Inte vår hemsida, inte våra "
       "öppettider, inte vårt lager, inte våra tjänster.",
    # SKIVA 36, LARS TRE INVÄNDNINGAR PÅ UTKASTEN I VYN. Alla tre är RÖST och
    # inte fakta, alltså kunde ingen spärr fånga dem: ett svar som hänvisar till
    # en kollega bryter mot ingen regel om tal eller fordonsfakta.
    9: "INGA KOLLEGOR. Vi är en liten verkstad utan en organisation att hänvisa "
       'vidare till. Skriv aldrig "en kollega", "vår tekniker", "vår säljare" '
       'eller "en av våra". Det är VI som återkommer, VI som tittar på bilen, '
       "VI som hör av oss.",
    # SKIVA 37: förbudet mot att lova en tid är TILLBAKA I PROMPTEN. Det bodde i
    # `BOKNINGSBESKED` som en instruktion till modellen, och när beskedet
    # flyttades till `config/fakta.json` blev instruktionen ett FAKTUM i första
    # person under en rubrik som bad modellen skriva med egna ord. Ingen rad
    # förbjöd då längre en tidsangivelse: regel 6 fångar tal, och "i juni" är
    # inget tal. En flytt får inte försvaga en spärr.
    10: "EN BOKNINGSFÖRFRÅGAN BESVARAS MED JA. Frågar kunden om vi kan ta emot "
        "bilen en viss månad eller vecka, så svarar vi att det löser vi och ber "
        "dem höra av sig så bestämmer vi tid. Hänvisa inte vidare och be dem "
        "inte återkomma senare. LOVA ALDRIG EN TID: ingen vecka, ingen månad, "
        "inget datum och ingen ledtid. Tiden bestäms i kontakten, aldrig i det "
        "här mailet.",
    11: "FRÅGA ALDRIG EFTER UPPGIFTER SOM REDAN STÅR I MAILET. Läs mailet "
        "först. Står registreringsnumret där, fråga inte efter det. Frågan är "
        "rimlig bara när uppgiften saknas.",
    # SKIVA 40 DEL F. Två språkfel Lars läste i vyn, inga spärrfrågor.
    #
    # Regel 12 kommer ur det FÖRSTA av de två fall Lars namnger, vars svar sade
    # *"har en registrerad draganordning som anger nej"*. Den meningen beskriver
    # vår AVLÄSNING och inte bilen, och kunden läser om sin bil.
    #
    # Regel 13 kommer ur det ANDRA fallet, vars svar bad kunden bekräfta
    # dragkroken. Att fråga är RÄTT vid OKLART, men utan tillägget läser frågan
    # som ett villkor kunden ska uppfylla själv.
    #
    # *Raderna bar först de två registreringsnumren. §6 gäller allt som pushas,
    # och `persondatakontroll` bevakar inte `tests/`, alltså fångade den bara
    # motsvarande rader i `docs/`. Att spärren är tyst är inget belägg.*
    12: "SKRIV OM REGISTRET, INTE OM REGISTERFÄLTET. Säg \"bilen saknar "
        "registrerad draganordning\", aldrig \"bilen har en registrerad "
        "draganordning som anger nej\". Det andra beskriver vår avläsning i "
        "stället för bilen, och kunden läser om sin bil och inte om vår "
        "databas.",
    13: "EN SAKNAD DRAGKROK ÄR INGET HINDER. Behöver bilen en dragkrok, skriv "
        "att vi kan montera en om det behövs. Ber du kunden bekräfta om det "
        "sitter en dragkrok, så skriv i samma mening att vi kan montera en. "
        "Utan det läser frågan som ett villkor kunden måste uppfylla själv.",
    # SKIVA 44, LARS ORDER NÄR HAN FYLLDE `config/priser.json`. Skälet är hans:
    # a-traktorpriset är ett INTERVALL och sajten säger att varje bygge är
    # unikt, alltså är beloppet inte ett besked om vad den enskilda bilen
    # kostar, och kunden behöver en väg vidare i samma svep.
    #
    # **"I EN EGEN MENING" BÄR FORTFARANDE, MEN INTE AV DET SKÄL SOM STOD HÄR.**
    #
    # *Kommentaren sade att ledet är lastbärande därför att priset och numret i
    # SAMMA mening faller på prisgrenen. Det var sant när regeln skrevs och blev
    # falskt av Lars VÄG TVÅ i samma skiva, som gör telefonnumret till en källa i
    # en prissats när det står ordagrant. Skälet mättes dessutom upp som
    # otillräckligt: FYRA av tjugo körda mail spärrades på just den formen,
    # alltså lyder modellen inte ledet varje gång, och en promptregel som bara
    # skyddar mot en spärr den inte hindrar är inget skydd.*
    #
    # **DET SKÄL SOM STÅR KVAR ÄR EXAKTHETEN.** Väg två kräver att numret står
    # ORDAGRANT som i `config/fakta.json`. Ett omskrivet nummer, `076 860 38 15`
    # i stället för `076-860 38 15`, är inte det värdet och faller fortfarande i
    # en prissats. Numret i en EGEN mening håller det utanför prissatsen helt och
    # hållet, alltså är ledet ett andra lager och inte stil. Bunden av
    # `test_REGEL_14_beordrar_en_form_som_PRISSPARREN_slapper_igenom`.
    14: "NÄMNER DU ETT PRIS, SKRIV TELEFONNUMRET DIREKT EFTER I EN EGEN "
        "MENING. Priset är ett intervall och varje bygge är unikt, alltså är "
        "beloppet aldrig ett besked om vad just den här bilen kostar. Återge "
        "priset som det står i underlaget, sätt punkt, och be kunden ringa oss "
        "på numret i underlaget så tittar vi på just den bilen. Priset och "
        "numret får ALDRIG stå i samma mening.",
    # SKIVA 45, LARS §11-ORDER. Skälet är hans, ordagrant: kunden som frågar om
    # ombyggnad vill veta vad det kostar oavsett vad registret säger om just den
    # bilen.
    #
    # **REGELN KOM UR LARS LÄSNING AV UTKASTEN I VYN, och iakttagelsen är hans.**
    # Samma läge, ett lyckat uppslag utan registrerad draganordning och ett svar
    # som säger att vi behöver titta närmare på bilen, gav ett utkast MED priset
    # och ett UTAN. Skillnaden var modellens val och inget prompten styrde, och
    # det är den sortens val en regel ska ta.
    #
    # *Här stod hur MÅNGA lästa utkast som skilde sig. §7.2 förbjuder att räkna
    # instanser av ett mönster i ett arbetsförlopp: talet går inte att verifiera
    # mot repot, och de utkasten finns inte kvar. Flaggat av §7-granskningen av
    # skiva 45.*
    #
    # **VILLKORET `OCH STÅR PRISET I UNDERLAGET` ÄR LASTBÄRANDE.** Utan det säger
    # regeln emot regel 5, som förbjuder varje pris utöver underlagets och
    # beordrar beskedet att VI återkommer med prisuppgift när inget pris finns.
    # En ovillkorlig regel 15 hade i samma andetag krävt ett pris och förbjudit
    # det, i det läge `INGA_PRISER` renderas, alltså exakt lucka 52:s defektform.
    # Bundet av `test_REGEL_15_kraver_INGET_PRIS_nar_underlaget_saknar_det`.
    #
    # **REGELN BÄRS AV PROMPTEN OCH INTE AV EN SPÄRR, och det är Lars order:
    # bind regeln som de övriga.** Regel 9, 10 och 13 är byggda så, och ingen av
    # dem har något `krav_pa_*`.
    #
    # *Här stod att INGEN SPÄRR KAN BÄRA DEN, med skälet att spärrarna fäller det
    # ett svar PÅSTÅR och att ett utelämnat pris inte är en påstådd osanning. Det
    # var FALSKT, och motexemplet står i samma modul: `krav_pa_ett_svar` fäller
    # ett TOMT svar, alltså en ren utelämning. En spärr GÅR att bygga av det
    # `Forfragan` redan bär. Fällt av §7-granskningen av skiva 45.*
    #
    # **SKÄLET ATT INTE BYGGA DEN ÄR VAD EN FÄLLNING KOSTAR.** En fälld spärr ger
    # Lars INGET utkast i stället för ett utkast utan pris, alltså vore utfallet
    # sämre än det regeln finns för att rätta. Samma avvägning som lucka 29:s
    # åtgärd och som `PRISFOT`:s helhetskrav, båda promptregler av samma skäl.
    #
    # Verifikationen är därför en MÄTNING: `scripts/prisandel.py` räknar per
    # körning hur många utkast som bär prisets båda gränser.
    15: "FRÅGAR KUNDEN OM EN OMBYGGNAD TILL A-TRAKTOR OCH STÅR PRISET I "
        "UNDERLAGET, SKRIV ALLTID VAD DEN KOSTAR. Det gäller ÄVEN när du inte "
        "kan ge något besked om just den bilen. Att uppslaget är oklart, att en "
        "uppgift saknas, eller att vi behöver titta närmare på bilen är inget "
        "skäl att utelämna priset. Kunden vill veta vad en ombyggnad kostar "
        "oavsett vad registret säger om just den bilen.",
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


def _samla_anrop(nod, hemvist: str, malnamn: str, traffar: list[str]) -> None:
    """Varje anrop av `malnamn`, med namnet på det som omsluter anropet.

    **VANDRAR HELA TRÄDET, inte bara `ast.FunctionDef`.** Första lydelsen
    filtrerade på `FunctionDef` och missade därför både `ast.AsyncFunctionDef`
    och modulnivån, inklusive `lambda`. Två fällningar var GRÖNA, båda vägar som
    lämnar ut modellens text FÖRE `krav_pa_svaret`:

        ratext_utan_sparr = lambda klient, f: generera_ratext(klient, f)
        async def ratext_utan_sparr(klient, f): return generera_ratext(klient, f)

    Det var lucka 35. Fällt av §7-granskningen av skiva 32, varv 3.
    """
    for barn in ast.iter_child_nodes(nod):
        if isinstance(barn, (ast.FunctionDef, ast.AsyncFunctionDef)):
            inre_hemvist = f"{hemvist.split('::')[0]}::{barn.name}"
        elif isinstance(barn, ast.Lambda):
            inre_hemvist = f"{hemvist}::<lambda>"
        else:
            inre_hemvist = hemvist

        if isinstance(barn, ast.Call):
            mal = barn.func
            namn = getattr(mal, "id", None) or getattr(mal, "attr", None)
            if namn == malnamn:
                traffar.append(hemvist)

        _samla_anrop(barn, inre_hemvist, malnamn, traffar)


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
        _samla_anrop(trad, f"{fil.name}::<modul>", "generera_ratext", anropare)

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


def test_rott_utfall_sager_VARFOR_och_vad_kunden_kan_gora():
    """RÖTT-texten är sändväg och var obunden av test.

    **DET ÄR SAMMA FORM SOM LUCKA 25.** `_utfallstext` styr vad ett avslag säger
    till kunden, och den texten gick att tömma på både skäl och inbjudan utan
    att något blev rött. Lucka 29 uppstod i just det tomrummet.

    Raden binder de tre leden var för sig: att BÅDA lämplighetsvillkoren namnges,
    att kunden bjuds in med ett annat fordon, och att modellen inte får hänvisa
    till något annat hos oss.
    """
    text = generera._utfallstext(Utfall.ROTT)

    assert "tjänstevikten" in text
    assert "släpvagnsvikten" in text
    assert "annat fordon" in text
    assert "Hänvisa inte" in text


def test_rott_UTAN_uppslag_ber_inte_om_siffror():
    """Prompten får aldrig både förbjuda och beordra viktangivelser.

    Med `utfall=ROTT` och `uppslag=None` skriver `_underlag` att modellen inte
    vet något om bilen och inte får nämna vikter. Bad bedömningen i samma stycke
    om bilens egna siffror var varje lydigt svar dömt att fällas av
    `krav_pa_fordonsfakta_ur_uppslag`.

    Fällt av §7-granskningen av skiva 33, varv 1.
    """
    utan = generera._utfallstext(Utfall.ROTT, har_uppslag=False)

    # **INGET FORDONSORD, inte bara inga siffror.** Första rättelsen tog bort
    # siffrorna och lät orden `tjänstevikten` och `släpvagnsvikten` stå kvar.
    # Båda är `FORDONSORD`, alltså fälldes varje lydigt svar ändå.
    assert not generera.FORDONSORD.search(utan), utan
    assert "siffror ur underlaget" not in utan
    # Inbjudan ska stå kvar: det är den som ger kunden något att göra.
    assert "annat fordon" in utan


def test_underlaget_ber_ALDRIG_om_bilfakta_utan_uppslag():
    """Samma krav prövat på HELA underlagstexten, inte bara på fragmentet.

    Den här raden binder att `_underlag` skickar med `har_uppslag`. Utan den
    kunde funktionen sluta göra det med sviten grön.

    **PRÖVAR BEDÖMNINGSRADEN och inte hela texten**, eftersom förbudsraden
    ovanför den med avsikt räknar upp orden den förbjuder.
    """
    text = generera._underlag(forfragan(utfall=Utfall.ROTT, uppslag=None))

    assert "Nämn inte" in text

    bedomning = [r for r in text.splitlines() if r.startswith("Bedömning:")]
    assert len(bedomning) == 1, text
    assert not generera.FORDONSORD.search(bedomning[0]), bedomning[0]


def test_BEDOMNINGSRADEN_sjalv_passerar_spärrarna():
    """Det prompten ber om ska aldrig fällas av spärrarna.

    **PRÖVAR BEDÖMNINGSRADEN SOM TEXT, inte en handskriven konstant.** En
    tidigare lydelse skickade in ett eget lydigt svar och hette
    `test_ett_lydigt_ROTT_svar_utan_uppslag_PASSERAR`. Den var VAKUÖS: strängen
    rörde aldrig `_utfallstext`, så den förblev grön när defekten återinfördes.
    Fällt av §7-granskningen av skiva 33, varv 3.

    Nu tas texten ur prompten själv, alltså går raden röd om bedömningsraden
    börjar be om något spärrarna fäller.
    """
    forfr = forfragan(utfall=Utfall.ROTT, uppslag=None)

    bedomning = [
        r for r in generera._underlag(forfr).splitlines()
        if r.startswith("Bedömning:")
    ][0]

    generera.krav_pa_svaret(bedomning, forfr)


# --------------------- MAILET SOM ALDRIG BAR ETT NUMMER, SKIVA 46 DEL B


def test_de_TVA_RADERNA_for_saknat_regnr_star_ORDAGRANT():
    """Sändvägstext, alltså bunden som `PRISFOT` och `UNDERLAGSRUBRIK`.

    Ett test som bara söker en delsträng släpper igenom en lydelse som också
    låter modellen påstå ett misslyckat uppslag. Det är lucka 25:s form.
    """
    assert generera.SAKNAT_REGNR_UNDERLAG == (
        "Fordonsuppslag: INGET UPPSLAG GJORDES. Vi har inget "
        "registreringsnummer för det här ärendet, alltså har vi aldrig försökt "
        "slå upp bilen och ingenting har misslyckats. Nämn inte tjänstevikt, "
        "släpvagnsvikt eller draganordning."
    )
    assert generera.SAKNAT_REGNR_BEDOMNING == (
        "vi har inget registreringsnummer att gå på, alltså har vi inte bedömt "
        "bilen. Säg ALDRIG att ett uppslag misslyckats, att vi inte kunnat "
        "hitta bilen eller att vi inte kunnat slå upp den: vi har inte "
        "försökt. Skriv ingenting om bilens uppgifter. Står "
        "registreringsnumret inte i mailet: BE KUNDEN SKICKA DET så tittar vi "
        "på bilen. Står det där: läs det ur mailet och fråga inte efter det."
    )


def test_INGENDERA_raden_pastar_att_MAILET_saknar_ett_nummer():
    """Vad vi vet är att VI inte har ett nummer, inte vad mailet bär.

    **EXTRAKTIONEN ÄR SNÄVARE ÄN VERKLIGHETEN**, se LUCKA 62 i
    `docs/sparrar.md`: mönstret söker inte i ämnesraden och täcker inte varje
    skrivform. En rad som påstår att mailet saknar ett nummer blir därför falsk
    så snart extraktionen missar, och den gamla lydelsen beordrade i samma
    andetag ovillkorligt att kunden skulle skicka det. Det är precis den form
    promptens regel 11 förbjuder.

    Raden binder BÅDA leden: inget påstående om mailet, och en VILLKORAD fråga.
    """
    for rad in (generera.SAKNAT_REGNR_UNDERLAG, generera.SAKNAT_REGNR_BEDOMNING):
        assert "Mailet bär inget" not in rad
        assert "mailet bär inget" not in rad

    # Frågan efter numret ska vara villkorad av vad modellen läser i mailet.
    assert "Står registreringsnumret inte i mailet" in (
        generera.SAKNAT_REGNR_BEDOMNING
    )
    assert "fråga inte efter det" in generera.SAKNAT_REGNR_BEDOMNING


def test_de_TVA_LAGENA_utan_uppslag_ger_OLIKA_underlag():
    """LARS ORDER I DEL B: skilj de två lägena i prompten.

    **BÅDA HAR `uppslag=None` OCH `utfall=None`, alltså är de oskiljbara för
    varje led utom flaggan.** Det är precis ärende 14:s läge: kundens mail bär
    inget registreringsnummer, och svaret inleds *"Vi har inte kunnat slå upp
    bilen i registret"*. Kunden får veta att något misslyckats utan att förstå
    varför, och blir aldrig ombedd att skicka numret.
    """
    utan_nummer = generera._underlag(
        forfragan(utfall=None, regnr_i_mailet=False))
    fallet_uppslag = generera._underlag(
        forfragan(utfall=None, regnr_i_mailet=True))

    # DET FALLNA UPPSLAGET säger fortfarande att vi inte kunnat slå upp bilen.
    # Raden binder att det läget finns kvar, alltså att ändringen SKILJER dem
    # och inte bara byter text i båda.
    assert "inte kunnat slå upp bilen" in fallet_uppslag

    # DET SAKNADE NUMRET säger det ALDRIG, och ber om numret i stället, om det
    # inte står i mailet.
    #
    # **PRÖVNINGEN GÄLLER PÅSTÅENDET OCH INTE ORDET.** Båda raderna för det
    # saknade numret nämner ett misslyckande, och båda NEKAR det: *"ingenting
    # har misslyckats"* och *"Säg ALDRIG att ett uppslag misslyckats"*. En rad
    # som sökte efter ordet `misslyckats` hade därför gått röd på just den
    # formulering den finns för att framtvinga. Uppmätt vid första körningen.
    assert "inte kunnat slå upp bilen" not in utan_nummer
    assert "Fordonsuppslag: INGET." not in utan_nummer
    assert "BE KUNDEN SKICKA DET" in utan_nummer
    assert utan_nummer != fallet_uppslag


def test_ETT_LYCKAT_UPPSLAG_gar_fore_flaggan():
    """Finns ett uppslag är det uppslaget som är bedömningen.

    Kedjan kan inte ge ett lyckat uppslag utan ett nummer, men bedömningsraden
    ska säga vad som GÄLLER och inte vad en anropare lovat. Utan `uppslag is
    None` i villkoret hade en motsägande anropare fått en prompt som både bär
    bilens vikter och ber kunden skicka registreringsnumret.
    """
    text = generera._underlag(forfragan(
        utfall=Utfall.GRONT, uppslag=GRONT_UPPSLAG, regnr_i_mailet=False))

    assert generera.SAKNAT_REGNR_BEDOMNING not in text
    assert generera.SAKNAT_REGNR_UNDERLAG not in text
    assert "tjänstevikt 1400 kg" in text


def test_BEDOMNINGSRADEN_utan_regnr_passerar_sparrarna():
    """Det prompten ber om ska aldrig fällas av spärrarna. §7.1.

    Samma form som `test_BEDOMNINGSRADEN_sjalv_passerar_spärrarna`: texten tas
    ur prompten själv, alltså går raden röd om bedömningsraden börjar be om
    något spärrarna fäller.
    """
    forfr = forfragan(utfall=None, regnr_i_mailet=False)

    bedomning = [
        r for r in generera._underlag(forfr).splitlines()
        if r.startswith("Bedömning:")
    ][0]

    generera.krav_pa_svaret(bedomning, forfr)


def test_ett_svar_som_BER_OM_NUMRET_passerar_sparrarna():
    """Den form bedömningsraden beställer ska gå igenom hela vägen.

    Bedömningsraden är en instruktion. Raden ovan prövar instruktionen som text;
    den här prövar ett SVAR skrivet efter den, alltså det utfall kunden läser.
    """
    generera.krav_pa_svaret(
        "Hej! Vi hjälper gärna till med en ombyggnad. Skicka bilens "
        "registreringsnummer så tittar vi på den och hör av oss.",
        forfragan(utfall=None, regnr_i_mailet=False),
    )


def test_rott_utfall_namner_INTE_troskeln():
    """Skälet får inte bli en återgiven föreskrift.

    Texten säger att vikterna inte räcker, aldrig vilket tal som är gränsen.
    Talet står i VVFS 2003:19 och hör inte i ett kundsvar, se
    `krav_pa_att_troskeln_inte_ar_forfattningstext`.
    """
    text = generera._utfallstext(Utfall.ROTT)

    assert not generera.TROSKELTAL.search(text), text


def test_systemprompten_bar_EXAKT_reglerna_i_tabellen():
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


def test_REGEL_5_bar_SAMMA_FORBEHALL_som_regel_8():
    """LUCKA 52 STÄNGD. Lars beslut i skiva 42.

    **REGELN SADE EMOT UNDERLAGET.** Regel 5 löd *"ALDRIG ETT PRIS"* utan
    förbehåll, medan `PRISRUBRIK` samtidigt ber modellen återge priserna ur
    `config/priser.json` och `PRISFOT` att den gör det ORDAGRANT. Ingen
    motsägelse rådde medan filen var tom, eftersom `INGA_PRISER` renderades i
    stället. Den blev live i samma ögonblick Lars fyller en post.

    **SKILLNADEN MOT FAKTAFALLET VAR ATT REGEL 8 BÄR ETT FÖRBEHÅLL.** Priser
    modellerades efter fakta utan att just den skillnaden följde med.

    `test_varje_regel_star_ORDAGRANT` binder hela lydelsen och går röd vid varje
    ändring. Den här raden säger VILKET led som är lastbärande, så att en
    framtida omskrivning ser vad den tar bort.
    """
    regler = _reglerna_i_systemprompten()
    forbehall = "utöver det som står i underlaget nedan"

    assert forbehall in regler[8], "regel 8 har tappat sitt förbehåll"
    assert forbehall in regler[5], (
        "regel 5 har tappat förbehållet, alltså förbjuder prompten åter det "
        "PRISRUBRIK ber om. Lucka 52 är då återöppnad."
    )


def test_REGEL_14_beordrar_en_form_som_PRISSPARREN_slapper_igenom():
    """REGEL 14 FÅR INTE BE OM DET `krav_pa_tal_med_kalla` FÄLLER.

    **DET ÄR LUCKA 52:s DEFEKTFORM.** Regel 5 sade *"ALDRIG ETT PRIS"* medan
    `PRISRUBRIK` bad modellen återge priset ordagrant, alltså beordrade prompten
    och spärren varandras motsatser. §9.1 säger att utvägen då inte är att skriva
    om texten tills den slinker igenom, så regeln ska vara skriven mot spärren
    från början.

    **RADEN LÄSER DE RIKTIGA KONFIGFILERNA**, och det är avsiktligt: frågan är
    inte om mekanismen fungerar i allmänhet utan om regel 14 går att lyda med
    just det pris och det nummer Lars har beslutat.

    **TRE FORMER, OCH DE BINDER VAR SITT LED.** De två första är de former regel
    14 respektive Lars VÄG TVÅ i skiva 44 gör möjliga, och båda ska passera. Den
    tredje är den som bär `ORDAGRANT`: ett OMSKRIVET nummer är inte det värde
    `config/fakta.json` bär, alltså faller det i en prissats även efter väg två.

    *Raden band först att numret i SAMMA mening som priset faller, och angav det
    som regel 14:s skäl. Väg två upphävde det ledet med flit, och FYRA av tjugo
    körda mail hade spärrats på just den formen. Skälet som står kvar är det
    tredje ledet nedan.*
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    telefon = FAKTA_SOM_LARS_BESLUTAT["telefon"]

    # DEN FORM REGELN BEORDRAR: priset, punkt, numret i en egen mening.
    generera.krav_pa_svaret(
        f"Ombyggnaden kostar {pris}. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
        forfragan(),
    )

    # LARS VÄG TVÅ: numret ORDAGRANT i samma mening som priset passerar också.
    # Det är den form modellen faktiskt skrev i fyra av tjugo körda mail.
    generera.krav_pa_svaret(
        f"Ombyggnaden kostar {pris}, ring oss på {telefon}.", forfragan())

    # OCH DET LED SOM GÖR `ORDAGRANT` LASTBÄRANDE. Samma siffror, annan
    # skrivform, alltså inte det värde config bär.
    #
    # **BLANKSTEGEN BLIR BINDESTRECK OCH INTE TVÄRTOM.** Formen måste ge SAMMA
    # talmängd som värdet i config, annars faller raden på att talen ändrades och
    # inte på att strängen inte matchade. Skälet i sin helhet står i
    # `test_ett_OMSKRIVET_telefonnummer_faller_FORTFARANDE_i_en_prissats`.
    omskrivet = telefon.replace(" ", "-")
    assert omskrivet != telefon
    assert generera._tal_i(omskrivet) == generera._tal_i(telefon), (
        "skrivformen ändrade talmängden, alltså prövar raden inte ordagrannheten"
    )

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_svaret(
            f"Ombyggnaden kostar {pris}, ring oss på {omskrivet}.", forfragan())

    assert fel.value.sparr == "genererat-tal-har-kalla"


def test_REGEL_15_beordrar_en_form_som_SPARRARNA_slapper_igenom():
    """REGEL 15 FÅR INTE BE OM DET SPÄRRARNA FÄLLER, i sitt EGNA läge.

    **LÄGET ÄR DET REGELN FINNS FÖR**, alltså inte ett godtyckligt prissvar:
    ett lyckat uppslag som läst `Draganordning: Nej`, ett svar som säger det och
    att vi behöver titta närmare på bilen, OCH priset. Det är formen Lars läste
    i vyn och saknade priset i.

    Tre spärrar möts i just den texten, och därför prövas hela `krav_pa_svaret`
    och inte prisgrenen för sig: frånvaropåståendet ska bäras av
    `franvaro_far_pastas`, fordonsordet av att uppslaget lyckats, och priset av
    `config/priser.json`.

    **RADEN LÄSER DE RIKTIGA KONFIGFILERNA**, av samma skäl som regel 14:s: frågan
    är om regeln går att lyda med just det pris och det nummer Lars beslutat.
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    telefon = FAKTA_SOM_LARS_BESLUTAT["telefon"]

    forfr = forfragan(
        utfall=Utfall.GULT,
        uppslag=Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1500,
                        draganordning=False),
        franvaro_far_pastas=frozenset({"draganordning"}),
    )

    # PRISET ÅTERGES I SIN HELHET, alltså som `PRISFOT` kräver, och numret står
    # i en egen mening, alltså som regel 14 kräver.
    generera.krav_pa_svaret(
        "Vi har tittat upp bilen och ser att den saknar registrerad "
        "draganordning. Vi kan montera en om det behövs, men vi behöver titta "
        "närmare på bilen innan vi kan ge ett säkert besked. En konvertering "
        f"till A-traktor kostar {pris}. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
        forfr,
    )


# ------------------------- SPÄRR: ÅTAGANDE OM VAD PRISET TÄCKER, LUCKA 59
#
# Skiva 46 DEL A, Lars beslut: ett åtagande om vad som ingår i ett pris är samma
# klass som ett påhittat pris.


def test_PRISFILENS_EGNA_lydelser_passerar_atagandesparren():
    """SPÄRREN FÅR INTE FÄLLA DET `PRISFOT` BEORDRAR. §7.1.

    Posten för a-traktorkonverteringen bär orden *"de delar som INGÅR i
    grundpaketet"*, och `PRISFOT` kräver att ett pris återges ORDAGRANT och i
    SIN HELHET. En spärr som fäller åtagandeordet ovillkorligt hade alltså fällt
    varje svar prompten ber om, vilket är den motsägelse §9.1 finns för.

    **VÄRDENA LÄSES UR KONFIGFILEN och skrivs inte av här**, så att raden följer
    med den dag Lars ändrar en post.
    """
    varden = list(generera.las_priser().values())

    # VAKUITETSKONTROLL. Bär ingen post ett åtagandeord prövar raden ingenting,
    # och den vore då grön av fel skäl.
    barande = [v for v in varden if generera.ATAGANDEORD.search(v)]
    assert barande, (
        "ingen post i config/priser.json bär ett åtagandeord, alltså prövar "
        "raden inte undantaget den finns för"
    )

    for varde in varden:
        generera.krav_pa_atagande_med_kalla(f"En ombyggnad kostar {varde}.")


def test_ett_atagande_UTANFOR_prisfilen_faller_aven_nar_priset_citeras():
    """UNDANTAGET FÅR INTE TVÄTTA RESTEN AV SVARET. Ärende 19, i sin form.

    Utkastet återgav prisraden OCH skrev *"dragkrok ingår i bygget"* i en annan
    mening. Strykningen tar bort prisvärdet och ingenting annat, alltså står det
    andra åtagandet kvar och fäller.
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla(
            f"En ombyggnad kostar {pris}. Dragkrok ingår i bygget."
        )

    assert fel.value.sparr == "atagande-om-priset"


def test_en_OMSKRIVEN_prisrad_faller_i_atagandesparren():
    """`ORDAGRANT` ÄR LASTBÄRANDE, och formen är den ärende 19 skrev.

    Utkastet skrev *"och DET priset gäller arbetet och de delar som ingår i
    grundpaketet"*. Ett inskjutet ord gör strängen till något annat än det värde
    `config/priser.json` bär, alltså stryks den inte och åtagandeordet står kvar.

    **ÖVERBLOCKERINGEN ÄR DEN SÄKRA RIKTNINGEN.** Utfallet blir ett utkast Lars
    läser ändå, och en prisrad som inte är ordagrant återgiven bryter redan mot
    `PRISFOT`. Samma avvägning som lucka 55.
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    omskrivet = pris.replace("och priset gäller", "och det priset gäller")
    assert omskrivet != pris, "bytet gav samma sträng, alltså prövas ingenting"

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla(f"En ombyggnad kostar {omskrivet}.")


def test_att_KUNNA_UTFORA_ett_arbete_ar_INGET_atagande():
    """LARS SKILLNAD: kan utföra är inget prisåtagande, ingår är det.

    Båda formerna står i ärende 19, och bara den ena ska falla. En spärr som
    fällde båda hade fällt promptens regel 13, som uttryckligen ber om
    erbjudandet att montera en dragkrok.
    """
    generera.krav_pa_atagande_med_kalla("Extraljusen kopplar vi in.")
    generera.krav_pa_atagande_med_kalla("Vi kan montera en dragkrok.")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla("Dragkrok ingår i bygget.")


def test_strykningen_fogar_inte_ihop_tva_halvor_till_ett_atagandeord(monkeypatch):
    """VÄRDET BYTS MOT ETT BLANKSTEG, inte mot ingenting.

    Byttes det mot ingenting kunde strykningen foga ihop två halvor till ett
    åtagandeord som aldrig stod i svaret. Det är samma fälla
    `_prisord_over_skarven` beskriver för hopfogningen, åt andra hållet.

    **RADEN BINDER BARA DEN FORMEN, och det ledet är fällt fram.** En term som
    ligger INTILL skarven får en ny ordgräns av blanksteget och kan då matcha
    där den inte matchade förut, se raden nedan. Skillnaden är riktningen: den
    här formen vore en falsk FRIKÄNNANDE, den andra en överblockering.
    """
    monkeypatch.setattr(generera, "las_priser", lambda *a, **k: {"x": "MITTEN"})

    # Utan blanksteget blir strängen `ingår` och raden fälls.
    generera.krav_pa_atagande_med_kalla("Vi ingMITTENår med jobbet.")


def test_strykningen_KAN_tillverka_en_traff_INTILL_skarven():
    """ÖVERBLOCKERINGEN ÄR MÄTT och står i spärrens docstring.

    Blanksteget ger en term som ligger intill skarven en ny ordgräns.
    `…motortvätt 500 kringår.` bär ingen term, och efter strykningen står
    `ingår` där. Utfallet blir ett utkast Lars läser, aldrig ett släppt
    åtagande, alltså är formen ofarlig, men påståendet att strykningen inte kan
    tillverka en träff var falskt och raden hindrar att det skrivs igen.

    Fällt av §7-granskningen av skiva 46.
    """
    varde = PRISER_SOM_LARS_BESLUTAT["service"]
    text = f"Vi {varde}ingår."

    assert not generera.ATAGANDEORD.search(text), (
        "texten bär redan en term, alltså prövar raden inte skarven"
    )

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla(text)


def test_prisraden_FORST_I_EN_MENING_passerar():
    """§7.1: SPÄRREN FÅR INTE FÄLLA DET REGEL 15 BEORDRAR.

    Regel 15 säger att ett a-traktorsvar ALLTID skriver vad ombyggnaden kostar.
    En strykning som är skiftlägeskänslig fäller då varje svar som INLEDER en
    mening med prisraden: `Från 20 000 till…` är inte `från 20 000 till…`, och
    posten bär själv ordet `ingår`. Enligt §9.1 blir det ett stopptecken, alltså
    inget utkast alls på just den kategori boten finns för.

    Uppmätt av §7-granskningen av skiva 46.
    """
    varde = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    versal = varde[0].upper() + varde[1:]
    assert versal != varde

    generera.krav_pa_atagande_med_kalla(f"{versal}. Ring oss så tittar vi.")


def test_en_RADBRUTEN_prisrad_passerar():
    """Samma led, andra formen: ett radbrott inuti prisraden.

    Ett svar sätts ihop av modellen och radbryts där den vill. Ett mellanslag i
    `config/priser.json` som blir en radbrytning i svaret är samma ORD i samma
    ordning, alltså ordagrant i den mening `PRISFOT` kräver.
    """
    varde = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    radbrutet = varde.replace("och priset gäller", "och\npriset gäller", 1)
    assert radbrutet != varde

    generera.krav_pa_atagande_med_kalla(f"En ombyggnad kostar {radbrutet}.")


def test_ett_TOMT_prisvarde_tystar_INTE_sparren():
    """Ett tomt mönster matchar mellan varje tecken och stryker HELA svaret.

    `las_konfigvarden` utelämnar tomma värden, men den invarianten bor i en
    annan funktion. Raden binder att spärren inte tystnar om den ändras.
    """
    assert not generera._UTAN_PRISVARDE("").search("vad som helst ingår här")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla("Dragkroken ingår i bygget.")


def test_ett_PRISVARDE_tolkas_aldrig_som_ett_reguljart_uttryck():
    """`re.escape` på varje del. Ett värde är text, aldrig ett mönster.

    Utan den skulle en prisrad med en parentes eller ett plustecken antingen
    kasta vid kompileringen eller matcha något helt annat än sin egen text.
    """
    monster = generera._UTAN_PRISVARDE("från 1 (ett) + 2 kr")

    assert monster.search("Det kostar från 1 (ett) + 2 kr.")
    assert not monster.search("Det kostar från 1 ett 2 kr.")


def test_REGEL_15_kraver_INGET_PRIS_nar_underlaget_saknar_det(monkeypatch):
    """REGELNS VILLKOR ÄR LASTBÄRANDE, och utan det säger den emot regel 5.

    **DET ÄR LUCKA 52:s DEFEKTFORM, spegelvänd.** Där förbjöd regel 5 det
    `PRISRUBRIK` bad om. En ovillkorlig regel 15 gör tvärtom: den KRÄVER ett
    pris i varje a-traktorsvar, medan regel 5 samtidigt förbjuder varje pris
    utöver underlagets och beordrar beskedet att VI återkommer med prisuppgift.
    Med `config/priser.json` tom är de två då varandras motsatser, och §9.1 säger
    att utvägen inte är att skriva om texten efteråt.

    Raden binder VILLKORET och dess premiss: att ett tomt underlag verkligen är
    ett läge som inträffar, alltså att `INGA_PRISER` renderas och att regel 5:s
    besked är det som gäller då.
    """
    regler = _reglerna_i_systemprompten()

    assert "STÅR PRISET I UNDERLAGET" in regler[15], (
        "regel 15 har tappat sitt villkor, alltså kräver den ett pris också när "
        "underlaget saknar ett. Den säger då emot regel 5."
    )
    assert "Står inget pris i underlaget" in regler[5], (
        "regel 5 har tappat sitt besked för det tomma fallet, alltså är regel "
        "15:s villkor inte längre kopplat till något"
    )

    # OCH PREMISSEN: det tomma läget finns, och då står inget pris i underlaget.
    _med_priser(monkeypatch, {})
    assert generera._prisrader() == generera.INGA_PRISER
    assert generera.INGA_PRISER in generera._underlag(forfragan())


@pytest.mark.parametrize("har_uppslag", [True, False])
def test_REGEL_15_kraver_priset_OCKSA_VID_ROTT_och_INGEN_SPARR_faller_det(
        har_uppslag):
    """REGELNS BREDD VID RÖTT, bunden därför att den annars är TYST.

    **REGELN ÄR BREDARE ÄN DET FALL LARS NAMNGAV, och det är avsiktligt men
    oavgjort.** Ordern lyder ALLTID, med skälet att kunden vill veta vad en
    ombyggnad kostar `oavsett vad registret säger om just den bilen`, och den
    namnger fallet `även när uppslaget inte gav ett entydigt besked`. Ett RÖTT
    utfall är tvärtom ETT ENTYDIGT BESKED, alltså uttalar ordern sig inte om det.
    Regelns två villkor håller ändå: kunden frågade om en ombyggnad, och priset
    står i underlaget.

    **FÖLJDEN ÄR ETT PRIS FÄST VID EN TJÄNST VI NEKAT.** `_utfallstext(ROTT)`
    beordrar att svaret säger att bilen inte går att bygga om och bjuder kunden
    med ett annat fordon. Regel 15 plus regel 14 lägger till vad en ombyggnad
    kostar och en uppmaning att ringa. Ingen av spärrarna rör formen, vilket den
    här raden MÄTER och inte antar: båda lägena passerar `krav_pa_svaret`.

    **RADEN FINNS FÖR ATT BREDDEN SKA VARA UTSKRIVEN OCH INTE TYST.** Ett
    undantag för RÖTT är Lars beslut, se `docs/beslutslogg.md` #107. Fattar han
    det blir den här raden röd, och då ska den bli det: en inskränkning av regeln
    är en ändring av sändvägstext och inte en förbigående rättelse.

    **BÅDA LÄGENA PRÖVAS**, eftersom `_utfallstext` skiljer dem: med uppslag får
    svaret ange bilens egna siffror, utan uppslag inget om bilen alls.

    *Formen är OPRÖVAD I FÄLT. Körningen som följde beslutet bar noll RÖDA
    utfall, se rapporten för skiva 45, alltså vilar raden på konstruerad text och
    inte på ett läst utkast.*
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    telefon = FAKTA_SOM_LARS_BESLUTAT["telefon"]

    uppslag = Uppslag(tjanstevikt_kg=980, slapvagnsvikt_kg=600,
                      draganordning=False) if har_uppslag else None

    # INGEN VIKT NÄMND I SKÄLET, och det är inte för att slinka igenom en spärr.
    # `krav_pa_belagt_franvaropastaende` fäller `släpvagnsvikten räcker inte
    # till`, alltså det som `_utfallstext(ROTT)` med uppslag ber om. Det är
    # lucka 55:s klass och rör inte regel 15, så raden håller sig utanför den.
    generera.krav_pa_svaret(
        "Bilen ser inte ut att gå att bygga om. Du är välkommen att höra av dig "
        f"med ett annat fordon. En konvertering till A-traktor kostar {pris}. "
        f"Ring oss på {telefon} så tittar vi på det.",
        forfragan(utfall=Utfall.ROTT, uppslag=uppslag),
    )


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
            FejkKlient(f"Det kostar {SENTINELPRIS} kr."), forfragan(), exempel=[]
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
            Raknande(f"Det kostar {SENTINELPRIS} kr."), forfragan(), exempel=[]
        )

    assert len(anrop) == 1


# --- SKIVA 40 DEL B: påståenden om frånvaro ----------------------------------


DET_FALLDA_UTKASTET = (
    "Tyvärr går denna bil inte att bygga om till A-traktor då den saknar "
    "dragvikt."
)


def test_DET_FALLDA_UTKASTET_sparras_nar_franvaron_inte_ar_belagd():
    """SKIVA 40:s UTLÖSANDE FALL, ordagrant ur Lars körning.

    Boten gav ett negativt besked om ett fält härkomstraden i samma vy sade att
    den inte kunnat läsa. Det är §0:s ramverksregel 3 i dess andra riktning: ett
    påstående utan källa, fast om en FRÅNVARO i stället för ett tal.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_svaret(DET_FALLDA_UTKASTET, forfragan())

    assert fel.value.sparr == "pastaende-om-franvaro"


def test_DET_FALLDA_UTKASTET_slapps_igenom_nar_registret_bevisligen_saknar():
    """SPEGELVÄNT, och det är hela skälet till att DEL A byggdes först.

    Saknas uppgiften i registret är frånvaron ett FAKTUM om bilen, och då får
    boten säga det. Utan DEL A:s uppdelning hade spärren behövt välja mellan att
    blockera ett sant besked och att släppa igenom ett osant.
    """
    generera.krav_pa_svaret(
        DET_FALLDA_UTKASTET,
        forfragan(franvaro_far_pastas=frozenset({"dragvikt"})),
    )


def test_GENERERAT_FORDONSFAKTUM_fangade_INTE_det_fallda_utkastet():
    """VARFÖR EN NY SPÄRR BEHÖVDES, bevisat och inte påstått.

    Den befintliga spärren prövar VÄRDEN: ett tal eller ett citerat fordonsord.
    *"saknar dragvikt"* är varken, alltså låg hela klassen utanför dess
    räckvidd. Raden blir röd den dag någon tror att den gamla spärren räckte.
    """
    generera.krav_pa_fordonsfakta_ur_uppslag(DET_FALLDA_UTKASTET, forfragan())
    generera.krav_pa_tal_med_kalla(DET_FALLDA_UTKASTET, forfragan())


@pytest.mark.parametrize(
    "svar",
    [
        "Tyvärr saknar bilen dragvikt.",
        "Bilen saknar registrerad draganordning.",
        "Det är en bil utan dragkrok.",
        "Dragvikten saknas i registret.",
        "Vi kan tyvärr inte se någon släpvagnsvikt.",
        "Registret har ingen uppgift om draganordning.",
        "Din bil har tyvärr ingen dragvikt registrerad.",
        # FYRA BAKLÄNGESFORMER SOM SLANK IGENOM en första lydelse, där
        # `FRANVAROORD_EFTER` bara var `saknas|saknar`. Uppmätta av
        # §7-granskningen av skiva 40, varv 1. Det utlösande utkastet sade
        # `saknar dragvikt`, och en omformulering till någon av de här hade
        # passerat.
        "Dragkroken finns inte i registret.",
        "Dragvikten är inte angiven i registret.",
        "Dragvikten är okänd för denna bil.",
        "Uppgift om draganordning är inte tillgänglig.",
        # ETT ERBJUDANDE FRIAR BARA SITT EGET FAKTUM. Dragkroken går att
        # montera, dragvikten är fordonets konstruktion.
        "Vi kan montera en dragkrok, men bilen saknar dragvikt.",
        # TRE LÄCKOR SOM VARV 2 MÄTTE UPP, alla i en spärr som var en
        # UPPRÄKNING av de former varv 1 råkat hitta. Baklängesmängden är nu en
        # egenskap: varje nekande ord.
        "Dragvikten framgår inte av registret.",
        "Dragvikten står inte i registret.",
        "Dragvikten, och det är tråkigt, saknas i registret.",
        # ETT ERBJUDANDE UTAN VILLKOR FRIAR INGENTING. Det här är ett PÅSTÅENDE
        # om just den här bilen, med ett erbjudande efter. Regel 13 ber om en
        # VILLKORSSATS, och en första lydelse friade båda.
        "Din bil saknar dragkrok så det ordnar vi.",
        "Bilen saknar dragvikt men det ordnar vi.",
    ],
)
def test_varje_form_av_franvaropastaende_sparras(svar):
    """FORMERNA ÄR SPRÅKETS, inte en uppräkning av det modellen råkat skriva.

    **BÅDA RIKTNINGARNA STÅR HÄR**, `saknar dragvikt` och `dragvikten saknas`,
    eftersom en spärr som bara tog den ena hade fällts av den andra.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_belagt_franvaropastaende(svar, forfragan())
    assert fel.value.sparr == "pastaende-om-franvaro"


@pytest.mark.parametrize(
    "svar",
    [
        "Din bil har en dragvikt på 2000 kg.",
        "Dragvikten är 2000 kg, så det är inte något problem.",
        "Vi saknar just nu en tid. Dragvikten är 2000 kg.",
        "Vi behöver veta om bilen har dragkrok.",
        "Vi kan montera en dragkrok om det behövs.",
        "Vi saknar tyvärr tider den veckan.",
        "",
        # REGEL 13:s EGEN INSTRUKTION i sin naturligaste form. Prompten ber om
        # den, alltså MÅSTE den gå igenom, och en första lydelse fällde båda.
        # Uppmätt av §7-granskningen av skiva 40, varv 1.
        "Om bilen saknar dragkrok monterar vi en.",
        "Vi monterar gärna en dragkrok om du saknar en sådan.",
        # SATSBROTT. Frånvaroordet hör till tiden och inte till dragvikten.
        "Vi saknar tyvärr en ledig tid, men dragvikten är 2000 kg.",
    ],
)
def test_ett_svar_som_INTE_pastar_franvaro_slapps_igenom(svar):
    """NEGATIVKONTROLL. En spärr som fäller allt skyddar ingenting.

    **TVÅ RADER ÄR UPPMÄTTA FALSKA TRÄFFAR från bygget.** *"Dragvikten är 2000
    kg, så det är inte något problem"* fälldes av en första lydelse där
    baklängesriktningen bar hela ordmängden. *"Vi saknar just nu en tid.
    Dragvikten är 2000 kg"* prövar att spärren inte kopplar ihop två meningar.

    **DEN FEMTE RADEN ÄR DEL F:s FORMULERING.** Att vi kan montera en dragkrok
    om det behövs säger samma sak som ett frånvaropåstående utan att påstå något
    om just den här bilen, och den måste gå igenom.
    """
    generera.krav_pa_belagt_franvaropastaende(svar, forfragan())


def test_ett_belagt_dragviktspastaende_slapper_INTE_igenom_draganordning():
    """MÄNGDEN ÄR PER FAKTUM, inte en generell dispens.

    Att registret saknar dragviktsuppgift säger ingenting om draganordningen,
    och en spärr som gav fritt fram för båda hade gjort mätningen meningslös.
    """
    tillaten = forfragan(franvaro_far_pastas=frozenset({"dragvikt"}))

    generera.krav_pa_belagt_franvaropastaende("Bilen saknar dragvikt.", tillaten)
    with pytest.raises(Sparrfalld):
        generera.krav_pa_belagt_franvaropastaende(
            "Bilen saknar dragkrok.", tillaten)


def test_forvalet_ar_TOM_mangd_alltsa_inga_franvaropastaenden():
    """**TOM MÄNGD ÄR DET SÄKRA FÖRVALET.** En anropare som inte vet något om
    registrets luckor ska inte kunna låta boten påstå att en uppgift saknas.
    """
    assert forfragan().franvaro_far_pastas == frozenset()
