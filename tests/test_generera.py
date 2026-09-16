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

from src import fordonsuppslag, generera, vy
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


def test_ett_NYCKELNAMN_ar_ALDRIG_en_talkalla(tmp_path, monkeypatch):
    """SPÄRR: ett namn är en etikett, inte en avläsning.

    Första rättelsen filtrerade `_`-nycklar och dumpade sedan hela dicten, alltså
    gick NYCKELNAMNEN med: `{"ledtid_14_dagar": ...}` gjorde 14 till ett tal
    boten får skriva. Fällt av §7-granskningen av skiva 36, varv 2.

    **NAMNET STÅR ORDAGRANT I SATSEN, och det ledet är skiva 58:s.** Raden
    hävdade förut `"14" not in _tillatna_tal(...)`. Faktafilens tal går inte in i
    den mängden längre, alltså hade påståendet blivit sant oavsett vad
    `_varden_ur` släpper igenom, och fällningen hade mätt ingenting (§7.1).
    Prövningen sker nu där källbegreppet faktiskt avgörs: satsen bär nyckelnamnet
    ORDAGRANT, alltså skulle ett nyckelnamn som räknades som källa dra bort 14 ur
    satsens tal och meningen passera.

    *Raden var parametriserad över BÅDA konfigfilerna och `[PRISER]`-fallet är
    struket. Skiva 52 tog prisfilen ur `_varden_ur`:s väg: `priser_for` slår upp
    ärendets kategori i `PRISNYCKEL_FOR_KATEGORI` och returnerar `.values()`,
    alltså kan ett nyckelnamn inte nå talspärren oavsett filtrering, och ingen
    indata kan skilja en filtrerad läsning från en ofiltrerad. Fallet var vakuöst
    sedan dess. Prisfilens egen form binds i stället av
    `test_ett_NASTLAT_PRIS_nar_ALDRIG_talsparren` nedan.*

    **BÅDA §10-FILERNA PATCHAS, LUCKA 58:s föreskrivna form.** Läser raden den
    RIKTIGA prisfilen går den röd den dag Lars fyller en post vars belopp är 14,
    alltså av hans beslut i stället för av en defekt.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text('{"ledtid_14_dagar": "snabbt"}', encoding="utf-8")
    monkeypatch.setattr(generera, "FAKTA", fil)
    _med_priser(monkeypatch, {})

    # SATSEN BÄR INGET ANNAT TAL ÄN NAMNETS EGET, och det ledet är fällt fram.
    # En första lydelse skrev *"Vi hör av oss inom 14 dagar, se
    # ledtid_14_dagar."*, alltså ett `14` UTANFÖR namnet. Det talet faller
    # oavsett filtrering, eftersom strykningen bara tar namnets egen förekomst,
    # och raden gick då GRÖN när filtret fälldes. Uppmätt med
    # `scripts/sparr-prova.sh` under §7-granskningen av skiva 58.
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Vi läser ledtid_14_dagar i filen.", forfragan())

    assert "talet 14" in fel.value.skal, fel.value.skal


def test_en_NASTLAD_kommentar_vidgar_ALDRIG_talsparren(tmp_path, monkeypatch):
    """SPÄRR: en kommentar en nivå ned är lika mycket en kommentar.

    Första rättelsen prövade `_`-prefixet bara på toppnivån, alltså återuppstod
    hålet ett steg ned. Fällt av §7-granskningen av skiva 36, varv 2.

    *Raden prövade tidigare BÅDA konfigfilerna. `config/priser.json` gick ur
    `_varden_ur`:s väg i skiva 52 och prövas nu av
    `test_ett_NASTLAT_PRIS_nar_ALDRIG_talsparren` nedan, som binder ett STARKARE
    krav på just den filen.*

    **KOMMENTAREN STÅR ORDAGRANT I SATSEN, och det ledet är skiva 58:s.** Raden
    hävdade förut `"7" not in _tillatna_tal(...)`, och den mängden bär inte
    faktafilens tal längre: påståendet hade blivit sant oavsett filtrering, alltså
    vakuöst (§7.1). Står kommentaren ordagrant i meningen blir skillnaden mätbar
    igen: en kommentar som räknades som källa hade STRUKITS ur satsen, och då
    finns inget tal kvar att pröva.

    **SATSEN BÄR INGET ANNAT TAL ÄN KOMMENTARENS EGNA, och det ledet är fällt
    fram.** En första lydelse skrev en påhittad ledtid framför kommentaren. Det
    talet står UTANFÖR kommentarens förekomst, alltså faller det oavsett
    filtrering, och raden gick GRÖN när filtret fälldes. Uppmätt med
    `scripts/sparr-prova.sh` under §7-granskningen av skiva 58.

    **PRISFILEN PATCHAS OCKSÅ, och det är LUCKA 58:s föreskrivna form.** Utan det
    är den riktiga filens `25 000` ett tillåtet tal via `priser_for`, och
    negativkontrollen nedan hade varit grön av fel skäl.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"a-traktor": {"_om": "se §7.2 och §10", "pris": 25000}}', encoding="utf-8"
    )
    monkeypatch.setattr(generera, "FAKTA", fil)
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Vi skriver se §7.2 och §10 i dokumentationen.", forfragan())

    assert "talet 10" in fel.value.skal, fel.value.skal

    # NEGATIVKONTROLL i samma rad: det nästlade VÄRDET ska fortfarande fram, och
    # sedan skiva 58 gör det det ORDAGRANT i den sats där värdet står.
    generera.krav_pa_tal_med_kalla("Vi har byggt om 25000 bilar.", forfragan())


def test_en_KOMMENTAR_i_en_LISTA_vidgar_ALDRIG_talsparren(tmp_path, monkeypatch):
    """SPÄRR: listgrenen i `_varden_ur`, som var OBUNDEN.

    Utan listgrenen faller listan igenom till `str(data)`, alltså till REPR:EN
    med varje nästlad `_`-kommentar inbakad, och hålet från varv 1 är tillbaka
    en nivå djupare.

    Grenen fungerade men ingen rad band den: fälld ensam var hela sviten grön,
    alltså vakuös enligt §7.1. Fällt av §7-granskningen av skiva 36, varv 3.

    *Raden prövade tidigare båda filerna, och docstringen sade att
    `config/priser.json` med största sannolikhet BLIR en lista av objekt. Lucka
    53 avgjorde motsatsen i skiva 42: filen ska vara platt. Prisfilen gick
    dessutom ur `_varden_ur`:s väg i skiva 52. Kvar är `config/fakta.json`, som
    är den fil vägen faktiskt går igenom.*

    **PRÖVNINGEN GÅR VIA SPÄRREN SEDAN SKIVA 58**, av samma skäl som raden
    ovanför: faktafilens tal når inte `_tillatna_tal` längre, alltså mäter ett
    påstående om den mängden ingenting. Satsen bär inget annat tal än
    kommentarens egna, av samma skäl som raden ovanför skriver ut.
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"tjanster": [{"_om": "se §7.2 och §10", "pris": 25000}]}',
        encoding="utf-8",
    )
    monkeypatch.setattr(generera, "FAKTA", fil)
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Vi skriver se §7.2 och §10 i dokumentationen.", forfragan())

    assert "talet 10" in fel.value.skal, fel.value.skal

    generera.krav_pa_tal_med_kalla("Vi har byggt om 25000 bilar.", forfragan())


@pytest.mark.parametrize(
    "innehall",
    [
        '{"a_traktorkonvertering": {"_om": "se §7.2", "pris": 25000}}',
        '{"a_traktorkonvertering": [{"_om": "se §10", "pris": 25000}]}',
    ],
    ids=["nastlad-dict", "nastlad-lista"],
)
def test_ett_NASTLAT_PRIS_nar_ALDRIG_talsparren(innehall, tmp_path, monkeypatch):
    """SPÄRR: prisfilen går via `las_konfigvarden`, som SLÄPPER ett nästlat värde.

    **STARKARE KRAV ÄN `_varden_ur` BAR, och det är skiva 52:s biverkan.**
    `_tillatna_tal` läste tidigare prisfilen med `_varden_ur`, som går NED genom
    strukturen: kommentarerna filtrerades men det nästlade priset 25000 blev ett
    tillåtet tal. Nu går filen via `priser_for`, alltså `las_konfigvarden`, som
    utelämnar ett nästlat värde HELT.

    Skillnaden är noll för dagens platta fil och är registrerad som lucka 53. Den
    binds här ändå: en sändvägsspärr ska inte kunna vidgas av att filen får fel
    form, och utan den här raden går ändringen att backa med grön svit.

    Både dict- och listformen prövas, alltså båda grenarna `_varden_ur` hade gått
    ned i.
    """
    fil = tmp_path / "priser.json"
    fil.write_text(innehall, encoding="utf-8")
    monkeypatch.setattr(generera, "PRISER", fil)

    tillatna = generera._tillatna_tal(
        forfragan(kategori="fråga om pris a-traktorkonvertering")
    )

    assert "7" not in tillatna
    assert "10" not in tillatna
    assert "25000" not in tillatna


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

    **KOMMENTAREN STÅR ORDAGRANT I DEN ANDRA MENINGEN, och det ledet är skiva
    58:s.** Den första meningen faller på 10 oavsett filtrering, alltså band den
    ingenting efter väg B. Den andra gör skillnaden mätbar: dess ENDA tal är
    kommentarens egna, alltså hade en kommentar som räknades som källa strukits
    ur satsen och lämnat inget att pröva. Ett tal utanför kommentarens förekomst
    hade fallit oavsett filtrering och gjort raden grön när filtret fälldes.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text(
        '{"_om": "se §7.2 och CLAUDE.md §10", "telefon": ""}', encoding="utf-8"
    )
    monkeypatch.setattr(generera, "FAKTA", fil)
    # BÅDA §10-FILERNA PATCHAS, lucka 58: annars går raden röd den dag Lars
    # fyller en prispost vars belopp är 7 eller 10.
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld):
        generera.krav_pa_tal_med_kalla("Vi hör av oss inom 10 dagar.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Vi skriver se §7.2 och CLAUDE.md §10 i dokumentationen.",
            forfragan())

    assert "talet 10" in fel.value.skal, fel.value.skal


def test_ett_IFYLLT_konfigvarde_ger_FORTFARANDE_sitt_tal(tmp_path, monkeypatch):
    """NEGATIVKONTROLL: filtret får inte stänga av källan.

    Utan raden vore "returnera alltid tomt" en grön lösning på raden ovan, och
    då hade Lars kunnat fylla filen utan att talet blev skrivbart.

    **SEDAN SKIVA 58 ÄR VILLKORET ATT VÄRDET STÅR ORDAGRANT I SATSEN**, och båda
    leden prövas: meningen som bär värdet passerar, meningen som bär ett annat
    tal faller. Raden hävdade förut `"14" in _tillatna_tal(...)`, alltså att
    talet var skrivbart var som helst i svaret. Det är precis den globala rätten
    väg B tar bort.

    **ETT VÄRDE SOM ÄR ENBART ETT TAL ÄR EN KÄLLA VAR SOM HELST DÄR TALET STÅR**,
    eftersom värdet och talet då är samma sträng. Det är LUCKA 74 och gäller
    ingen post `config/fakta.json` bär i dag.
    """
    fil = tmp_path / "fakta.json"
    fil.write_text('{"_om": "kommentar", "ledtid_dagar": 14}', encoding="utf-8")
    monkeypatch.setattr(generera, "FAKTA", fil)
    # BÅDA §10-FILERNA PATCHAS, lucka 58: annars går raden röd den dag Lars
    # fyller en prispost vars belopp är 15.
    _med_priser(monkeypatch, {})

    generera.krav_pa_tal_med_kalla("Vi hör av oss inom 14 dagar.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla("Vi hör av oss inom 15 dagar.", forfragan())

    assert "talet 15" in fel.value.skal, fel.value.skal


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
# **`adress` TILLKOM PÅ LARS §10-BESLUT I SKIVA 58 DEL A.** Skälet står i
# skiva 57:s körning: modellen skriver av Mattes signaturblock ur ett få-exempel,
# och utan en adress i config fällde talspärren postnumret. Fällningen var en
# falsk positiv i sak, och den formen återkommer eftersom exemplen bär
# signaturen.
#
# **VÄRDET SKRIVS I DEN FORM ETT MAIL SKA BÄRA DET**, och det är väg B:s krav:
# siffergrupperna är en källa bara i den sats där HELA strängen står tecken för
# tecken. En omskriven adress matchar inte och fälls.
FAKTA_SOM_LARS_BESLUTAT = {
    "adress": "Surbrunnsgatan 42, 113 48 Stockholm",
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
    # **UPPDATERAD PÅ LARS §10-BESLUT I SKIVA 47.** Den förra lydelsen sade att
    # priset gällde *"de delar som ingår i grundpaketet"* utan att säga VILKA,
    # och det var precis den luckan `atagande-om-priset` byggdes mot: boten
    # kunde inte veta om dragkroken låg i paketet. Nu räknar källan upp de sju
    # delarna.
    #
    # **POSTEN SÄGER BARA VAD SOM INGÅR, aldrig vad som inte gör det, och det
    # är Lars beslut.** En första lydelse bar meningen *"Dragkrok ingår inte
    # och offereras separat."* `dragkrok` står i `FORDONSTERMER` och i
    # `FRANVAROFAKTA["draganordning"]`, alltså läste `genererat-fordonsfaktum`
    # och `pastaende-om-franvaro` prisraden som ett påstående om KUNDENS bil.
    #
    # Uppmätt med den lydelsen inlagd och ordagrant återgiven: raden föll i
    # var och en av de tre grenar där `uppslag is None`, samtliga på
    # `genererat-fordonsfaktum`. I det LYCKADE läget föll den på
    # `pastaende-om-franvaro` när frånvaron inte var belagd och när
    # `draganordning=True`, och passerade bara när registret sade att
    # draganordning saknas OCH frånvaron var belagd. Regel 15 beordrar att
    # priset alltid skrivs, så följden var ett STOPPTECKEN enligt §9.1 på den
    # kategori boten finns för, alltså lucka 52:s defektform.
    #
    # Lars skäl: prisposten citeras ordagrant och i sin helhet när den skrivs,
    # och regel 15 gör att den skrivs i varje a-traktorsvar där kunden frågar
    # om en ombyggnad och priset står i underlaget. Ett negativt påstående om
    # en komponent hör inte hemma i en mening kunden läser varje gång. Att
    # dragkrok inte ingår bärs i stället av systempromptens regel 16, som ett
    # FÖRBUD och inte som ett påstående.
    #
    # **UPPRÄKNINGEN STÅR SOM EN EGEN SATS MED EGET SUBJEKT, och det är Lars
    # §10-beslut efter en uppmätt fältkörning.** En mellanlydelse sade
    # *"… för grundombyggnaden, och i priset ingår hastighetsbegränsning, …"*.
    # Mätt med `generera_ratext` mot tio fall: prisraden återgavs ORDAGRANT i
    # NOLL av tio, och `ingår` stod kvar efter strykningen i TIO av tio. Varje
    # gång skrev modellen *"och i DET ingår"* där källan sade *"och i PRISET
    # ingår"*, och flyttade `för grundombyggnaden` till subjektet. De tjugo gav
    # 20 spärrade och noll utkast.
    #
    # **MODELLEN PLOCKADE INTE, den citerade allt och bytte två bindeord.**
    # Varje siffra och var och en av de sju delarna återgavs korrekt. Det
    # motargument som restes mot att i stället vidga undantaget gällde
    # PLOCKFORMEN, alltså att `PRISFOT` förbjuder att en del av en prisrad
    # citeras. Det argumentet höll inte mot det som faktiskt inträffade, och
    # Lars ursprungliga premiss, att källan är en uppräkning och att ett svar
    # sällan citerar hela ordagrant, var den riktiga.
    #
    # Åtgärden rör därför KÄLLAN och ingen spärr: en uppräkning med eget
    # subjekt ger modellen inget bindeord att byta ut, och ett värde som inte
    # bär ordet `ingår` kan inte producera det felet.
    #
    # **VÄRDET BÄR INGEN PUNKT, och det ledet är lastbärande.** En lydelse som
    # skilde de två satserna med PUNKT i stället för komma prövades och
    # förkastades: `genererat-tal-har-kalla` prövar per sats, alltså klöv
    # punkten värdet i två, och svansen efter prisraden hamnade i
    # UPPRÄKNINGENS sats. Den bär inget PRISORD och är därmed ingen prismening,
    # så talet prövades aldrig mot config. Mätt: med punkten i värdet passerade
    # `Ombyggnaden kostar <värdet>, ring oss på 076-860-38-15.`, alltså ett
    # telefonnummer som INTE är det `config/fakta.json` bär. Utan punkten faller
    # samma sträng på `genererat-tal-har-kalla`. Isolerat med samma ord och
    # samma uppräkning i båda lydelserna.
    #
    # Att ett tal UTANFÖR en prismening inte prövas alls är klassen bakom
    # instansen, och den står kvar som LUCKA 65 i `docs/sparrar.md`. Kommat
    # lagar det här värdet, inte nästa.
    #
    # Sajtens stavfel skrivs INTE in: `PRISFOT` kräver ordagrann återgivning,
    # alltså hade ett stavfel i filen blivit ett stavfel i varje kundmail. Lars
    # rättar sajten separat. Pluspaketets pris står utanför grundombyggnaden
    # och därmed utanför posten; beloppet skrivs inte här, eftersom ett pris
    # som boten får nämna hör hemma i `config/priser.json` och ingen annanstans.
    "a_traktorkonvertering":
        "från 20 000 till 25 000 kr inklusive moms för grundombyggnaden, och "
        "grundombyggnaden omfattar hastighetsbegränsning, barlastflak, "
        "förstängning, belysning, LGF-skylt, dokumentation och besiktning",
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

    rader = generera._prisrader("fråga om pris a-traktorkonvertering")
    assert rader != generera.INGA_PRISER
    assert "tillbehor" not in rader


def _med_priser(monkeypatch, poster: dict) -> None:
    """Låtsas att `config/priser.json` bär `poster`. Rör aldrig filen.

    §10 gör filen till ett stopp, alltså får ett test inte skriva i den. Den
    här hjälparen byter ut den RÅA läsningen, `las_konfig`, och inte
    `las_priser`.

    **SKÄLET ÄR ATT PRISFILEN LÄSES PÅ FLERA STÄLLEN, alla via `las_konfig`.**
    En hjälpare som bara patchade `las_priser` hade lämnat någon av dem vid den
    riktiga filen, alltså gett ett test som inte liknar något verkligt läge.
    Uppmätt under bygget: `test_ett_AVLAST_pris_slapps_igenom...` föll på att
    25000 inte fanns bland de tillåtna talen.

    *Här stod att skälet är att filen har TVÅ LÄSARE MED OLIKA KRAV,
    `las_konfigvarden` för prompten och `_varden_ur` för talspärren. Sant fram
    till skiva 52, som tog prisfilen ur `_varden_ur`:s väg: enda kvarvarande
    anropet är `_varden_ur(las_konfig(FAKTA))`. Prisfilen har sedan dess EN
    läsare, `las_konfigvarden` via `priser_for`. Hjälparen fungerar oförändrat,
    men skälet var falskt. Fällt av §7-granskningen av skiva 52.*
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


def test_spärren_lamnar_SATSEN_talet_stod_i(monkeypatch):
    """SKIVA 56 DEL 0, Lars beslut: skälet ska gå att spåra till en mening.

    Skiva 55:s enda spärrade post lyder *"talet 113 kommer varken ur uppslaget
    eller ur config"*, och var 113 kom ifrån gick inte att avgöra: texten som
    fälldes sparades ingenstans. `Sparrfalld.sats` bär den nu.

    **TALET I RADEN ÄR SENTINELVÄRDET OCH INTE LÄNGRE `113`. Lars beslut i skiva
    58 DEL A, samma precedens som skiva 43.** `113` är de tre första siffrorna i
    verkstadens postnummer, som samma skiva skrev in i `config/fakta.json`. Ett
    exempeltal ur samma domän som en §10-fil är en tripwire i förklädnad, precis
    som `25 000 kr` var innan prisfilen fylldes: korpusen ska byta exempeltal,
    inte verkligheten.

    **INGEN RAD VAR RÖD AV ADRESSEN, och bytet görs ändå.** Väg B håller
    adressens siffergrupper utanför den globala mängden, alltså föll `113` i den
    här raden lika hårt efter DEL A som före. Det som byts är risken: skulle den
    globala vägen någon gång öppnas igen blir kollisionen omedelbar, och då står
    två gröna rader mellan Lars beslut och en tyst regression.
    """
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            f"Hej. Vi har byggt om {SENTINELPRIS_IHOP} bilar.", forfragan())

    assert SENTINELTAL in fel.value.skal
    assert fel.value.sats == f"Vi har byggt om {SENTINELPRIS_IHOP} bilar."


def test_satsen_hittas_aven_for_ett_GRUPPERAT_tal(monkeypatch):
    """`_tal_i` normaliserar bort avskiljaren, satsen skriver ut den.

    Spärren namnger `20000` medan svaret skriver `20 000`, alltså skulle en
    delsträngssökning på det normaliserade talet inte träffa någon sats alls, och
    varje fällning på ett grupperat tal bli utan sats.

    *Raden sade att `_satsen_med_talet` finns för den här egenskapens skull, och
    att den går röd om hjälparen byts mot `_satsen_med`. Hjälparen är borttagen i
    skiva 58: slutkontrollen går per sats, alltså är satsen redan känd när
    fällningen sker och behöver inte sökas upp. EGENSKAPEN står kvar och binds
    här; det som föll bort är en implementation, inte ett krav.*
    """
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Hej. Vi har byggt om 20 000 bilar.", forfragan())

    assert fel.value.sats == "Vi har byggt om 20 000 bilar."


# EN INDATA PER SPÄRR SOM `krav_pa_svaret` KÖR, med den sats som ska följa med.
#
# **§7.1. UTAN DEN HÄR TABELLEN ÄR NIO AV TIO SATSER OBUNDNA.** Uppmätt av
# §7-granskningen av skiva 56 med `scripts/sparr-prova.sh`: satt till `""` på
# nio av fällningsställena gick hela sviten GRÖN, alltså kunde fem av spärrarna
# tappa sin sats utan att något larmade, och vyn hade fallit tillbaka till att
# säga ATT något fälldes utan att säga VAD. Bara talloopen, prisgrenens andra
# fällning och `tomt-svar` var bundna.
#
# Uppslaget som gatar barlastflaket är FYRHJULSDRIVET, alltså faller §39:s andra
# led och `kraver_barlastflak` svarar `False`.
FYRHJULSDRIVET = Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=1500,
                         draganordning=True, fyrhjulsdrift=True)

# ETT LYCKAT UPPSLAG MED HÅL, skiva 55: släpvagnsvikten är utelämnad mot belägg.
UTAN_SLAPVAGNSVIKT = Uppslag(tjanstevikt_kg=1400, slapvagnsvikt_kg=None,
                             draganordning=True)

SATS_PER_SPARR = (
    (
        "genererat-tal-har-kalla, prisord utan belopp",
        "Hej. Hör av dig så skickar vi en offert.",
        {},
        "Hör av dig så skickar vi en offert.",
    ),
    (
        "genererat-tal-har-kalla, talord",
        "Hej. Vi har byggt om tjugofemtusen bilar.",
        {},
        "Vi har byggt om tjugofemtusen bilar.",
    ),
    # TALET ÄR SENTINELVÄRDET OCH INTE `113`, skiva 58 DEL A. Skälet står i
    # `test_spärren_lamnar_SATSEN_talet_stod_i` ovan: `113` ligger i verkstadens
    # postnummer, som samma skiva skrev in i `config/fakta.json`.
    (
        "genererat-tal-har-kalla, tal utan källa",
        f"Hej. Vi har byggt om {SENTINELPRIS_IHOP} bilar.",
        {},
        f"Vi har byggt om {SENTINELPRIS_IHOP} bilar.",
    ),
    (
        "genererat-fordonsfaktum",
        "Hej. Bilens tjänstevikt räcker gott.",
        {},
        "Bilens tjänstevikt räcker gott.",
    ),
    # ANDRA GRENEN AV SAMMA SPÄRR: uppslaget lyckades men bär inte det fält
    # termen påstår något om. Skiva 55 gjorde den grenen möjlig genom att låta
    # ett uppslag lyckas med hål. Uppmätt av §7-granskningen av skiva 56: utan
    # den här raden går just den fällningens sats att nolla med grön svit.
    (
        "genererat-fordonsfaktum, fältet saknas i uppslaget",
        "Hej. Bilens släpvagnsvikt räcker gott.",
        {"uppslag": UTAN_SLAPVAGNSVIKT, "utfall": Utfall.OKLART},
        "Bilens släpvagnsvikt räcker gott.",
    ),
    (
        "pastaende-om-franvaro",
        "Hej. Bilen saknar dragvikt i registret.",
        {"uppslag": GRONT_UPPSLAG, "utfall": Utfall.GRONT},
        "Bilen saknar dragvikt i registret.",
    ),
    (
        "barlastflak-galler-fordonet",
        "Hej. I bygget monterar vi barlastflak.",
        {"uppslag": FYRHJULSDRIVET, "utfall": Utfall.GRONT},
        "I bygget monterar vi barlastflak.",
    ),
    # TRÖSKELN SKRIVS `ett ton` OCH INTE `1 000 kg`, och det är inte en
    # smaksak: `krav_pa_tal_med_kalla` körs FÖRE och fäller varje siffra utan
    # källa, alltså hade siffran gjort raden till en andra mätning av talspärren
    # med den här spärrens etikett. Formen `ett ton` står i `TROSKELTERMER` och
    # bär ingen siffra.
    (
        "troskeln-som-forfattningstext",
        "Hej. Lagen kräver ett ton för en a-traktor.",
        {},
        "Lagen kräver ett ton för en a-traktor.",
    ),
    # ÅTAGANDET SÄGS OM `bygget` OCH INTE OM `priset`, av samma skäl: `priset`
    # är ett PRISORD, alltså gör det satsen till en prissats och talspärren
    # fäller den först.
    (
        "atagande-om-priset",
        "Hej. I bygget ingår lackering.",
        {},
        "I bygget ingår lackering.",
    ),
    # ANDRA GRENEN: ett FORDONSORD i samma sats fäller alltid. Uppslaget är
    # grönt, alltså är draganordningen avläst och `genererat-fordonsfaktum`
    # släpper igenom meningen; utan det uppslaget hade den spärren fällt först
    # och den här grenens sats varit obunden. Uppmätt av §7-granskningen av
    # skiva 56.
    (
        "atagande-om-priset, fordonsord i satsen",
        "Hej. I bygget ingår dragkrok.",
        {"uppslag": GRONT_UPPSLAG, "utfall": Utfall.GRONT},
        "I bygget ingår dragkrok.",
    ),
)


@pytest.mark.parametrize(
    "namn,svar,andrat,vantad",
    SATS_PER_SPARR,
    ids=[rad[0] for rad in SATS_PER_SPARR],
)
def test_VARJE_sparr_lamnar_satsen_som_fallde(namn, svar, andrat, vantad,
                                              monkeypatch):
    """SKIVA 56 DEL 0: en spärrad post ska säga VAD som fällde och VAR.

    Raden går röd om en enda av fällningarna slutar sätta sin sats, vilket är
    hela poängen: en tappad sats syns ingen annanstans än i vyn, och den läses
    av Lars och inte av sviten.

    **PRISFILEN ÄR TOM I MÄTNINGEN**, alltså bidrar den med noll tillåtna tal.
    Det är samma val som `test_ett_pris_FALLER_nar_prisfilen_ar_tom` gör, och
    det håller raderna oberoende av vad Lars fyllt.
    """
    _med_priser(monkeypatch, {})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_svaret(svar, forfragan(**andrat))

    # SPÄRREN PRÖVAS OCKSÅ, och raden är inte kosmetisk: faller indatan på en
    # ANNAN spärr än den avsedda mäter fallet inte det etiketten säger, och den
    # avsedda fällningens sats blir obunden igen. Namnet står före kommat i
    # etiketten, eftersom flera rader prövar olika grenar av samma spärr.
    assert fel.value.sparr == namn.split(",")[0], (
        f"{namn} föll på {fel.value.sparr} i stället"
    )
    assert fel.value.sats == vantad, (
        f"{namn} fällde men lämnade satsen {fel.value.sats!r}"
    )


def test_ett_tomt_svar_far_INGEN_uppfunnen_sats():
    """`tomt-svar` har ingen sats att peka på, och en påhittad vore värre.

    Fältet är tomt, och vyn har ett läge för det.

    **RADEN BINDER EN DATAKLASSDEFAULT OCH INGEN RAD I KODEN**, alltså finns
    här ingenting att fälla: `krav_pa_ett_svar` skickar inget tredje argument.
    Den räknas därför inte som täckning. Den står kvar som en pinne åt andra
    hållet: skulle någon ge `Sparrfalld.sats` ett förval som är en text, eller
    låta den här spärren hitta på en sats, blir raden röd. Uppmätt av
    §7-granskningen av skiva 56.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_ett_svar("   ")

    assert fel.value.sparr == "tomt-svar"
    assert fel.value.sats == ""


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

    **BÅDA PATCHAS, och det är LUCKA 58:s föreskrivna form.** Ett spärrtest som
    patchar EN §10-fil och låter den andra vara den riktiga går rött av en laglig
    post i den opatchade filen, alltså av Lars beslut i stället för av en defekt.

    Byter ut den RÅA läsningen, `las_konfig`, av samma skäl som `_med_priser`:
    filen har två läsare med olika krav och båda går den vägen.

    *Här stod "Tre äldre spärrtest patchar EN konfigfil … medan `_tillatna_tal`
    läser båda". Båda leden är falska sedan skiva 58: `_tillatna_tal` läser inte
    `config/fakta.json` alls, och de tre raderna patchar numera båda filerna. Att
    läsa `config/fakta.json` spelar ändå roll för den här hjälparen, eftersom
    spärren läser den via `_faktakallor`. Fällt av §7-granskningen av skiva 58.*
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


# --- SKIVA 58, LARS VÄG B: ETT FAKTAVÄRDE ÄR EN KÄLLA BARA ORDAGRANT --------


@pytest.mark.parametrize(
    "svar, talet",
    [
        ("Vi hör av oss inom 15 dagar.", "15"),
        ("Ombyggnaden tar 38 dagar.", "38"),
        ("Vi har byggt om 860 bilar.", "860"),
    ],
)
def test_en_SIFFERGRUPP_ur_ett_faktavarde_faller_UTANFOR_sitt_varde(
        svar, talet, monkeypatch):
    """HÅLET VÄG B STÄNGER, och alla tre raderna passerade före skiva 58.

    `_tillatna_tal` la varje faktavärdes siffergrupper i en GLOBAL mängd, alltså
    gjorde telefonnumret `076`, `860`, `38` och `15` skrivbara i vilken mening
    som helst. Två av de tre raderna är påhittade LEDTIDER, alltså precis den
    klass hålet i skiva 36 hade: där gjorde kommentarnycklarnas `§7.2` och `§10`
    talen 7 och 10 tillåtna och *"vi hör av oss inom 10 dagar"* passerade.

    Hålet var oregistrerat och omätt tills skiva 58 DEL 0.1 mätte det.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(svar, forfragan())

    assert fel.value.sparr == "genererat-tal-har-kalla"
    assert f"talet {talet}" in fel.value.skal, fel.value.skal


def test_faktavardet_ORDAGRANT_ar_en_kalla_ocksa_UTANFOR_en_prissats(monkeypatch):
    """NEGATIVKONTROLL, och utan den är väg B bara en strypning.

    Numret ska gå att skriva. Regel 14 beordrar att ett svar som nämner ett pris
    följer det med numret, och `_faktarader` skriver in värdet i prompten just
    för att modellen ska återge det. Utan den här raden vore "faktafilen är
    aldrig en källa" en grön lösning på raden ovan.

    Meningen bär inget prisord, alltså prövas den av SLUTKONTROLLEN och inte av
    prisgrenen. Det är det led skiva 58 flyttade: ordagrannheten gällde förut
    bara prissatser.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    generera.krav_pa_tal_med_kalla(
        "Ring oss på 076-860 38 15 så bokar vi in en tid.", forfragan())


def test_ett_OMSKRIVET_faktavarde_faller_ocksa_UTANFOR_en_prissats(monkeypatch):
    """LEDET SOM GÖR `ORDAGRANT` LASTBÄRANDE i slutkontrollen.

    Samma siffror, annan skrivform, alltså inte det värde `config/fakta.json`
    bär. Utan raden vore "dra alltid bort faktafilens siffergrupper" en grön
    lösning, och då vore väg B ingen ändring alls: den globala rätten hade
    kommit tillbaka genom bakdörren.

    **SKRIVFORMEN GER IDENTISK TALMÄNGD**, av samma skäl som
    `test_ett_OMSKRIVET_telefonnummer_faller_FORTFARANDE_i_en_prissats` skriver
    ut: byts bindestrecket mot ett blanksteg blir `076 860` ETT tal, och då faller
    raden på att talmängden blev en annan i stället för på `in`-prövningen.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    omskrivet = "076-860-38-15"
    assert generera._tal_i(omskrivet) == generera._tal_i("076-860 38 15"), (
        "skrivformen ändrade talmängden, alltså prövar raden inte ordagrannheten"
    )

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            f"Ring oss på {omskrivet} så bokar vi in en tid.", forfragan())

    assert "talet 076" in fel.value.skal, fel.value.skal


def test_ett_faktavarde_i_EN_ANNAN_SATS_ar_INGEN_kalla(monkeypatch):
    """PRÖVNINGEN SKER PER SATS, också i slutkontrollen. Skiva 58.

    Numret står i första meningen och den påhittade ledtiden i andra. Ett tal ska
    inte kunna hämta sin källa ur ett värde som står någon annanstans i svaret,
    och det är samma krav prisgrenen och `krav_pa_belagt_franvaropastaende` har
    ställt sedan tidigare.

    **PER SATS RÄCKER INTE ENSAMT**, och det ledet band raden inte förut. Ett
    faktavärde i SAMMA sats som ett påhittat tal fälls av
    `test_ett_tal_UTANFOR_vardet_lanar_ALDRIG_dess_kalla` nedan, som är den rad
    §7-granskningen av skiva 58 tvingade fram.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Ring oss på 076-860 38 15. Vi hör av oss inom 15 dagar.",
            forfragan(),
        )

    assert "talet 15" in fel.value.skal, fel.value.skal
    assert fel.value.sats == "Vi hör av oss inom 15 dagar."


@pytest.mark.parametrize(
    "svar, talet",
    [
        # SAMMA SATS, rakt av: numret och en påhittad ledtid i en mening.
        ("Ring oss på 076-860 38 15 så hör vi av oss inom 15 dagar.", "15"),
        # SAMMA SATS via SIGNATUREN, och det är den form en modell faktiskt
        # skriver. `_meningar` delar vid `[.!?]` och ALDRIG vid radbrytning,
        # alltså ligger en kroppsmening utan avslutande punkt i samma sats som
        # hela signaturblocket.
        ("Vi hör av oss inom 15 dagar\n"
         "\n"
         "Med vänliga hälsningar\n"
         "Auto Stockholm\n"
         "076-860 38 15", "15"),
    ],
    ids=["samma-mening", "over-radbrytning-till-signaturen"],
)
def test_ett_tal_UTANFOR_vardet_lanar_ALDRIG_dess_kalla(svar, talet, monkeypatch):
    """SÄNDVÄGSHÅLET §7-GRANSKNINGEN AV SKIVA 58 FANN, bundet.

    **VAD SOM VAR ÖPPET.** Väg B:s första lydelse drog bort faktavärdets
    siffergrupper ur HELA satsens talmängd. Ett påhittat tal som råkade vara
    samma siffergrupp fick då källa av att värdet stod någon annanstans i samma
    sats, och satsen är stor: den sträcker sig från senaste meningsslut ned genom
    signaturblocket.

    **VAD SOM STÄNGER DET.** `_tal_utan_ordagrann_kalla` stryker värdets EGEN
    förekomst ur satsen och prövar resten. Utan den formen vore *"dra bort
    värdets tal ur satsen"* en grön lösning på varje annan rad i skivan, och
    hålet vore kvar.

    **RADEN GÅR RÖD OM STRYKNINGEN BYTS MOT EN SUBTRAKTION**, alltså mot exakt
    den lydelse granskningen fällde.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(svar, forfragan())

    assert f"talet {talet}" in fel.value.skal, fel.value.skal


def test_strykningen_FOGAR_ALDRIG_IHOP_tva_tal(monkeypatch):
    """AVSKILJAREN ÄR ETT KOMMATECKEN, och det ledet är lastbärande.

    `TAL_I_TEXT` läser `[\\s.]` följt av exakt tre siffror som en del av talet.
    Ströks värdets förekomst mot ett BLANKSTEG kunde siffrorna före och efter
    fogas ihop till ett tal som aldrig stod i svaret: `12` plus `345` blir
    `12345`, ett tal spärren sedan namnger i sitt skäl trots att kunden aldrig
    skulle läsa det.

    Raden binder att de två talen prövas var för sig. Båda saknar källa, alltså
    fäller spärren, men på det FÖRSTA av dem och inte på en hopfogning.

    **INDATAN SER KONSTRUERAD UT OCH ÄR DET, och det är inte ett val.** Värdet
    står utan blanktecken omkring sig, eftersom hopfogningen kräver att
    ersättningstecknet blir det ENDA tecknet mellan siffrorna: `[\\s.]` i
    `TAL_I_TEXT` är en teckenklass och inte `\\s+`, alltså räcker redan ett
    blanksteg på var sida för att talen ska skiljas åt. Uppmätt: med värdet
    omgivet av blanksteg ger båda ersättningarna samma talmängd, och bara den
    ihopskrivna formen skiljer dem. En rad som prövade den vanliga formen hade
    därför varit GRÖN när kommatecknet byttes mot ett blanksteg, alltså vakuös
    (§7.1). Verifierat med `scripts/sparr-prova.sh`.
    """
    _med_konfig(monkeypatch, {"a_traktorkonvertering": "25 000 kr"},
                {"telefon": "076-860 38 15"})

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Vi har 12076-860 38 15345 kvar.", forfragan())

    assert "talet 12 " in fel.value.skal + " ", fel.value.skal
    assert "12345" not in fel.value.skal, fel.value.skal


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

    block = generera._prisrader("fråga om pris a-traktorkonvertering")
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

    **DE LAGLIGA KÄLLORNA ÄR `_tillatna_tal`:s EGNA, alla tre.**
    `ALLTID_TILLATNA_TAL`, uppslagets två vikter, och VÄRDENA i
    `config/priser.json`. Fixturen ger inget uppslag, och raden binder det, så
    att vikterna inte tyst börjar bära differensen.

    *Här stod "alla fyra" och räknade in VÄRDENA i `config/fakta.json`. Väg B tog
    faktafilen ur den mängden i skiva 58: dess tal är en källa bara i den sats där
    värdet står ordagrant, alltså är de inte lagliga tal i den här meningen. Ledet
    var dessutom lastbärande åt fel håll: det drog bort ett kommentartal som
    råkade ligga i ett faktavärde, och gjorde därmed raden svagare än den skulle
    vara. Rättat i skiva 58.*

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
    # BARA PRISFILEN LÄSES, skiva 58. Faktafilens värden är en källa bara
    # ordagrant i sin egen sats, alltså varken lagliga tal eller läckage här, och
    # dess kommentarer räknades aldrig. En loop över båda filerna läste den ena
    # och kastade allt den fann. Fällt av §7-granskningen av skiva 58.
    kommentarernas_tal = set()
    lagliga_tal = set(generera.ALLTID_TILLATNA_TAL)
    for namn, varde in json.loads(
            generera.PRISER.read_text(encoding="utf-8")).items():
        if str(namn).startswith("_"):
            kommentarernas_tal |= generera._tal_i(str(varde))
        else:
            lagliga_tal |= generera._tal_i(str(varde))

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


def test_ett_NASTLAT_varde_nar_ALDRIG_prompten_FAKTA(tmp_path, monkeypatch):
    """SPÄRR: koden släpper inte igenom nästlingen, oavsett vad filen bär.

    **VÄRDET I EXEMPLET ÄR VÅRT INKÖPSPRIS**, alltså precis det som inte får bli
    ett citerbart pris. Talets halva var redan stängd av `_varden_ur`, som
    hindrade att 9000 blev ett tillåtet tal. TEXTENS halva var öppen: ingenting
    hindrade att raden stod i prompten.

    *Ledet stod i PRESENS och beskriver ett läge som inte gäller: sedan skiva 58
    är ett värde ur `_varden_ur` inte ett tillåtet tal alls, utan en källa bara i
    den sats där värdet står ordagrant. Samma formulering rättades i
    `las_konfigvarden` i samma skiva och lämnades kvar här. Fällt av
    §7-granskningen av skiva 58.*

    **NEGATIVKONTROLLEN LIGGER I SAMMA RAD.** Utan den vore "returnera alltid
    tomt" en grön lösning, och då hade filtret tagit Lars fakta med sig.

    *Raden prövade båda filerna med samma nycklar. Sedan skiva 52 väljer
    kategorin prispost, alltså renderar `_prisrader` bara EN post och nycklarna
    måste stå i `PRISNYCKEL_FOR_KATEGORI`. Prisfilens halva står i raden nedan.*
    """
    fil = tmp_path / "konfig.json"
    fil.write_text(
        '{"nastlad": {"_internt": "kostar oss 9 000 kr", "pris": "25 000 kr"},'
        ' "platt": "1 500 kr"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(generera, "FAKTA", fil)

    block = generera._faktarader()

    assert "_internt" not in block, block
    assert "kostar oss" not in block, block
    assert "9 000" not in block, block
    assert "1 500 kr" in block, block


def test_ett_NASTLAT_varde_nar_ALDRIG_prompten_PRISER(tmp_path, monkeypatch):
    """Samma krav på prisfilen, med kategorin som väljer posten.

    **TVÅ KATEGORIER PRÖVAS, eftersom bara EN post renderas åt gången.** Den
    nästlade posten är a-traktorns, alltså den kategori vars prompt faktiskt
    körs i dag, och `rekond` står platt som NEGATIVKONTROLL: utan den vore
    `INGA_PRISER` i varje läge en grön lösning, och då hade filtret tagit Lars
    priser med sig.
    """
    fil = tmp_path / "priser.json"
    fil.write_text(
        '{"a_traktorkonvertering": {"_internt": "kostar oss 9 000 kr",'
        ' "pris": "25 000 kr"}, "rekond": "1 500 kr"}',
        encoding="utf-8",
    )
    monkeypatch.setattr(generera, "PRISER", fil)

    nastlat = generera._prisrader("fråga om pris a-traktorkonvertering")

    assert "_internt" not in nastlat, nastlat
    assert "kostar oss" not in nastlat, nastlat
    assert "9 000" not in nastlat, nastlat
    assert nastlat == generera.INGA_PRISER, nastlat

    platt = generera._prisrader("fråga om pris rekond")

    assert "1 500 kr" in platt, platt


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
        # SKIVA 62, LUCKA 77. `två` är inget tal för talspärren, alltså kan
        # ingen annan spärr rapportera raden.
        ("Ursäkta att det dröjt i två veckor.", "drojsmalets-langd",
         forfragan()),
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
    och av `test_ett_NASTLAT_varde_nar_ALDRIG_prompten_PRISER`, båda äldre än
    skiva 43. *Den senare hette
    `test_ett_NASTLAT_varde_nar_ALDRIG_prompten[PRISER-_prisrader]` fram till
    skiva 52, som delade den parametriserade raden i en per fil. Node-id:t fanns
    inte längre, alltså namngav den här meningen en vakt som inte finns — samma
    defektklass som stycket nedan rättar. Fällt av §7-granskningen av skiva 52.*
    Den här raden lägger till att priset når hela vägen ut i
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
    # SKIVA 47, LARS §10-BESLUT. Regeln är ett RENT FÖRBUD, och den formen är
    # hans beslut efter att en första lydelse mättes upp som oföljbar.
    #
    # **EN REGEL SOM BEORDRAR ETT PÅSTÅENDE GER SPÄRRARNA NÅGOT ATT FÄLLA. EN
    # SOM BARA FÖRBJUDER GER DEM INGENTING.** Det är hela skälet till formen.
    # Första lydelsen sade *"EN DRAGKROK INGÅR INTE I GRUNDOMBYGGNADEN. Den
    # offereras separat."* och beordrade alltså modellen att skriva ordet
    # `dragkrok` tillsammans med `ingår inte`. `dragkrok` står i
    # `FORDONSTERMER` och i `FRANVAROFAKTA["draganordning"]`, så den meningen
    # är på en gång ett fordonsfaktum, ett frånvaropåstående och ett åtagande
    # utan källa. Fältkörningen av de tjugo gav 20 spärrade och NOLL utkast.
    #
    # Lydelsen nämner därför inte dragkroken som ett påstående alls. Den
    # förbjuder en form, och en förbjuden form skriver modellen inte.
    #
    # **`Den offereras separat` VAR DESSUTOM ETT PRISBESKED UTAN KÄLLA**, och
    # det är ett granskningsfynd. Regel 5 förbjuder varje pris utöver
    # underlaget och namnger *"ring för offert"* som en av formerna;
    # `config/priser.json` bär inget dragkroksvärde. Meningen PASSERADE
    # samtliga spärrar i det lyckade uppslagsläget, eftersom `PRISTERMER` bär
    # `\boffert\b` som inte matchar `offereras`. Den luckan står kvar och är
    # registrerad i `docs/sparrar.md`; den här regeln slutade bara beordra
    # formen.
    #
    # **TVÅ LAGER PÅ OLIKA FORMER, och det är Lars ordning.** Prompten HINDRAR
    # att åtagandet skrivs, `atagande-om-priset` FÅNGAR `ingår` och
    # `inkluderad` om de skrivs ändå. **`följer med` fångas INTE**, mätt: den
    # formen passerar spärren och ligger i LUCKA 61. Lagren är alltså inte
    # jämnbreda, och prompten är det bredare av dem.
    #
    # Det är inte den redundans §7.1 varnar för: den varningen gäller två
    # SPÄRRAR på samma form, som gör båda oprövbara var för sig. Här prövas
    # promptens lager av `test_varje_regel_star_ORDAGRANT` och av
    # `test_REGEL_16_beordrar_INGEN_form_som_en_SPARR_faller`, och spärrens
    # lager för sig. Vad ingen fällning kan pröva är om MODELLEN lyder texten.
    #
    # **REGEL 13 SÄGER INTE EMOT DEN.** Regel 13 beordrar formen *"vi kan
    # montera en"*, och det är precis den skillnad `atagande-om-priset` är
    # byggd på, Lars ord: kan utföra är inget prisåtagande, ingår är det.
    # Hänvisningen står i regeln så att en framtida omskrivning ser att de två
    # är avsedda att stå bredvid varandra, och den är skriven som en HÄNVISNING
    # och inte som en uppmaning att nämna dragkroken.
    16: "SKRIV ALDRIG ATT EN DRAGKROK INGÅR. Inte att den ingår i priset, i "
        "bygget eller i grundombyggnaden, och inte att den följer med eller är "
        "inkluderad. Regel 13 står oförändrad och säger vad du DÄREMOT skriver "
        "när bilen behöver en.",
    # SKIVA 55 DEL B PUNKT 1. **REGELN KOMMER UR EN MÄTNING och inte ur en
    # invändning mot språket.** Av Lars åtta spärrade ärenden mättes två orsaker,
    # och den här är den ena: boten skriver kundens egen modellbeteckning, och
    # beteckningen bär en siffra. `V70` gav `talet 70 kommer varken ur uppslaget
    # eller ur config`, `E60` gav samma sak inuti en prismening, och `X3M` gav
    # `talet 3 står i en prismening`. Kunden fick noll svar, och priset var känt
    # hela tiden.
    #
    # **DET ÄR LUCKA 30, OCH REGELN STÄNGER ORSAKEN I STÄLLET FÖR SPÄRREN.**
    # Skiva 33 försökte tre gånger lära `_tal_i` att skilja en beteckning från en
    # kvantitet och återställde alla tre: varje regel som gör en siffra intill
    # bokstäver ofarlig gör också en KVANTITET intill bokstäver ofarlig, se
    # `docs/beslutslogg.md` #56. Luckan står därför kvar öppen, och spärren är
    # orörd. Det som ändrats är att prompten inte längre ber om formen.
    #
    # **FABRIKATET FÅR SKRIVAS**, och det ledet är avsiktligt: `Volvo` och `Audi`
    # bär ingen siffra, och ett svar som inte får nämna bilen alls blir stelt.
    17: "SKRIV ALDRIG BILENS MODELLBETECKNING. Inte V70, inte E60, inte A3, "
        "inte X3M. Skriv \"bilen\", \"din bil\" eller \"er bil\". Fabrikatet "
        "får du skriva. Beteckningen bär nästan alltid en siffra, och en siffra "
        "i ett utgående mail måste ha en källa.",
    # SKIVA 55 DEL B PUNKT 1, den ANDRA mätta orsaken. Ett prisord i en mening
    # utan belopp gör meningen till en prissats som prisgrenen kräver ett
    # källbelagt tal ur, och den får inget: *"skicka gärna med
    # registreringsnumret så kan vi ge dig en mer exakt offert"* föll på
    # `svaret nämner ett pris utan att ange ett tal som går att slå upp mot
    # config/priser.json`, i tre av åtta ärenden i mätningen.
    #
    # **GRENEN ÄR INTE SÄNKT, OCH DET ÄR POÄNGEN.** Den finns mot *"det kostar en
    # del"*, alltså ett prisbesked utan belopp, och den formen ska fortfarande
    # falla. Regeln säger vilka ord modellen har i stället, och regel 5 bär redan
    # `prisuppgift`, som med flit INTE står i `PRISTERMER`.
    18: "ETT PRISORD KRÄVER ETT BELOPP I SAMMA MENING. Orden pris, priset, "
        "kostar, kostnad, offert, avgift och kronor får bara stå i en mening "
        "som också bär priset ur underlaget. Vill du säga att vi tittar närmare "
        "på bilen, skriv det utan prisord: \"hör av dig så tittar vi på just "
        "din bil\". Behöver du säga att priset beror på bilen, skriv \"vi "
        "återkommer med prisuppgift\".",
    # SKIVA 55 DEL B PUNKT 2, LARS ORDER. Tre av hans lästa utkast erbjöd en
    # dragkrok utan att säga varför den hjälper. Hans skäl, ordagrant: en
    # dragkrok hjälper inte om vikten är under tröskeln.
    #
    # **REGELN ÄR PARAD MED EN UNDERLAGSRAD och står inte ensam.**
    # `_utfallstext`:s nya OKLART-läge skriver ut att bilen duger som dragfordon
    # och ber om talet, se `_bara_dragkroken_saknas`. Utan den raden hade regeln
    # bett om en motivering modellen inte har.
    #
    # **INGEN SPÄRR BÄR DEN, och det är samma avvägning som regel 15.** En spärr
    # som krävde motiveringen hade fällt svaret, alltså gett kunden ingenting i
    # stället för ett svar utan skäl. Det är den riktning DEL B punkt 1 finns för
    # att stoppa.
    19: "NÄR DU ERBJUDER EN DRAGKROK SKA DU SÄGA VARFÖR DEN HJÄLPER. Står det i "
        "underlaget att bilen duger som dragfordon, skriv ut släpvagnsvikten ur "
        "underlaget i samma stycke. En dragkrok på en bil som inte duger "
        "hjälper inte, och ett erbjudande utan skälet läser kunden som ett "
        "villkor.",
    # SKIVA 62, LUCKA 77, LARS REGEL: raden säger ATT det dröjt, aldrig HUR
    # LÄNGE. Prompten hindrar, `drojsmalets-langd` fångar. Samma form som regel
    # 16 och `atagande-om-priset`.
    20: "SKRIV ALDRIG HUR LÄNGE DET DRÖJT. Ber du om ursäkt för att svaret "
        "dröjt, skriv att det dröjt och aldrig hur länge: inga dagar, veckor "
        "eller månader, varken i siffror eller i ord, och inte \"några "
        "veckor\" eller \"ett par dagar\". Vi vet inte hur länge mailet legat.",
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


# ETT UPPSLAG SOM GER RÖTT UR §42, alltså där BÅDA lämplighetsvillkoren faller
# och båda talen är avlästa. `Kaross` är satt och är INTE `Ombyggd Bil`, så att
# gatingsregel 1 inte tar över: utan det ledet hade raderna nedan prövat fel av
# de två röda texterna.
ROTT_UPPSLAG = Uppslag(
    tjanstevikt_kg=960, slapvagnsvikt_kg=600, draganordning=False,
    kaross="Halvkombi",
)


def test_rott_for_ett_REDAN_OMBYGGT_fordon_skyller_inte_pa_vikten():
    """SKIVA 55 DEL A GATINGSREGEL 1. RÖTT har två skäl, och de får inte blandas.

    **DEN HÄR RADEN FINNS FÖR ETT MÄTT FALL.** det ombyggda fordonet med tjänstevikt 2 005 kg bär tjänstevikt 2 005 kg,
    alltså ÖVER §42:s tröskel, och `Kaross: Ombyggd Bil`. Utfallet är RÖTT därför
    att bilen redan är ombyggd. Hade texten varit `rott_med_siffror` hade svaret
    sagt att varken tjänstevikten eller släpvagnsvikten räcker, vilket är falskt
    om just den bilen, alltså ett påhittat fordonsfaktum.

    **BÅDA RIKTNINGARNA ASSERAS.** Att rätt text väljs, och att viktskälet INTE
    står kvar i den: ett test som bara sökte den nya frasen hade varit grönt även
    om båda texterna råkade skrivas ut.
    """
    ombyggd = Uppslag(
        tjanstevikt_kg=2005, slapvagnsvikt_kg=None, draganordning=None,
        kaross="Ombyggd Bil",
    )

    assert fordonsuppslag.utvardera(ombyggd) is Utfall.ROTT

    text = generera._utfallstext(Utfall.ROTT, ombyggd)

    assert "redan" in text.lower()
    assert "tjänstevikten" not in text
    assert "släpvagnsvikten" not in text


def test_rott_utfall_sager_VARFOR_och_vad_kunden_kan_gora():
    """RÖTT-texten är sändväg och var obunden av test.

    **DET ÄR SAMMA FORM SOM LUCKA 25.** `_utfallstext` styr vad ett avslag säger
    till kunden, och den texten gick att tömma på både skäl och inbjudan utan
    att något blev rött. Lucka 29 uppstod i just det tomrummet.

    Raden binder de tre leden var för sig: att BÅDA lämplighetsvillkoren namnges,
    att kunden bjuds in med ett annat fordon, och att modellen inte får hänvisa
    till något annat hos oss.

    **UPPSLAGET SKICKAS MED SEDAN SKIVA 55**, och det är inte en formalitet:
    `_utfallstext` har numera TVÅ röda texter, och bara den här gäller ett fordon
    vars vikter faller. Den andra gäller ett fordon som redan är ombyggt och
    binds av `test_rott_for_ett_REDAN_OMBYGGT_fordon_skyller_inte_pa_vikten`.
    Uppslaget nedan har `Kaross` som inte är `Ombyggd Bil`, alltså väljs den här.
    """
    text = generera._utfallstext(Utfall.ROTT, ROTT_UPPSLAG)

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

    **ARGUMENTET ÄR UPPSLAGET SJÄLVT SEDAN SKIVA 55**, inte en `bool`. `None`
    betyder detsamma som `har_uppslag=False` gjorde.
    """
    utan = generera._utfallstext(Utfall.ROTT, None)

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


# ------------------------------------------- EFTERSLÄPSRADEN, SKIVA 61 DEL B


def test_EFTERSLAPSRADEN_star_ORDAGRANT():
    """Sändvägstext, bunden som `SAKNAT_REGNR_UNDERLAG`."""
    assert generera.EFTERSLAPSRAD == (
        "EFTERSLÄP: kundens mail har legat obesvarat en tid. INLED svaret med "
        "en kort rad i den här andan, med egna ord i samma ton som exemplen "
        "och inte ordagrant: \"Ursäkta att det dröjt, det har varit fullt upp "
        "i verkstaden. Nu har vi kapacitet igen, så hör av er om det "
        "fortfarande är aktuellt. Annars hoppas vi att det gått bra med ert "
        "projekt.\" Skriv aldrig hur länge det dröjt. Svara sedan på mailet "
        "som vanligt."
    )


def test_underlaget_bar_EFTERSLAPSRADEN_bara_nar_flaggan_ar_satt():
    med = generera._underlag(forfragan(efterslap=True))
    utan = generera._underlag(forfragan())

    assert generera.EFTERSLAPSRAD in med
    assert "EFTERSLÄP" not in utan
    assert med.replace("\n" + generera.EFTERSLAPSRAD, "") == utan


# ANDAN SOM PROMPTEN CITERAR, ur konstanten och inte avskriven.
EFTERSLAPSANDAN = generera.EFTERSLAPSRAD.split('"')[1]

# RADER I MATTES RÖST SOM PROMPTEN BER OM. Handskrivna mätprober: raden bär
# ordet kapacitet och ett nekande, alltså prövas de mot varje spärr, bland dem
# `atagande-om-priset` och `pastaende-om-franvaro`.
EFTERSLAPSPROBER = (
    EFTERSLAPSANDAN,
    "Ursäkta att det dröjt med svaret, det har varit fullt upp i verkstaden. "
    "Nu har vi kapacitet igen, så hör gärna av dig om det fortfarande är "
    "aktuellt. Annars hoppas vi att det har gått bra med ditt projekt.",
    "Förlåt att vi inte svarat förrän nu, det har varit väldigt mycket i "
    "verkstaden. Nu har vi kapacitet igen, så hör av dig om det fortfarande "
    "är aktuellt.",
    "Ber om ursäkt för det sena svaret, vi har haft fullt upp. Nu har vi "
    "kapacitet igen. Är det inte längre aktuellt hoppas vi att allt gått bra "
    "med bygget.",
    "Ursäkta dröjsmålet, det har varit fullt upp här. Nu har vi kapacitet "
    "igen, men har ni redan löst det utan oss hoppas vi att det blev bra.",
)


@pytest.mark.parametrize("rad", EFTERSLAPSPROBER)
@pytest.mark.parametrize("lage", [
    {"utfall": Utfall.GRONT, "uppslag": GRONT_UPPSLAG},
    {"utfall": Utfall.OKLART, "uppslag": None},
    {"utfall": Utfall.ROTT, "uppslag": None},
    {"utfall": None, "uppslag": None, "regnr_i_mailet": False},
    {"kategori": "boka a-traktorkonvertering"},
    {"kategori": "fråga om pris a-traktorkonvertering"},
])
def test_EFTERSLAPSRADEN_passerar_VARJE_sparr(rad, lage):
    """Det prompten ber om ska aldrig fällas. Mätt före de tjugo körs."""
    forfr = forfragan(efterslap=True, **lage)

    generera.krav_pa_svaret(rad, forfr)
    generera.krav_pa_svaret(rad + "\n\nVänliga hälsningar\nAuto Stockholm",
                            forfr)


# ------------------------------ DRÖJSMÅLETS LÄNGD, SKIVA 62 DEL B, LUCKA 77


def _hal(text: str, lucka: int = 77) -> pytest.param:
    return pytest.param(text, marks=pytest.mark.xfail(
        strict=True, reason=f"lucka {lucka}, formen fångas inte"))


# FORMERNA, MÄTTA MOT SPÄRREN. En vanlig rad fälls. En `_hal`-rad är en
# tidsangivelse spärren INTE fångar: strikt xfail, så att raden blir röd den
# dag formen börjar fångas och tabellen måste skrivas om.
DROJSMAL_SKA_FALLA = [
    # lucka 77:s två rader ur skiva 61
    "Ursäkta att det dröjt i två veckor, nu har vi kapacitet igen.",
    "Ursäkta att det dröjt i 3 veckor, nu har vi kapacitet igen.",
    # siffror
    "Förlåt att vi inte svarat på 14 dagar.",
    "Ursäkta dröjsmålet, mailet har legat i 1,5 vecka.",
    "Ursäkta att det dröjt 2-3 veckor.",
    # räkneord
    "Ursäkta att det dröjt en vecka.",
    "Ursäkta att det dröjt tre veckor.",
    "Ursäkta att vi svarar först nu, efter fjorton dagar.",
    "Beklagar att det dröjt tjugoen dagar.",
    "Ursäkta att det dröjt ett år.",
    "Ber om ursäkt för att det dröjt sex månader.",
    "Förlåt dröjsmålet på fyra timmar.",
    # vaga mängdord
    "Ursäkta att det dröjt några veckor.",
    "Ursäkta att det dröjt ett par dagar.",
    "Ursäkta att mailet legat obesvarat i flera veckor.",
    # ett ord emellan
    "Ursäkta att det dröjt två hela veckor.",
    "Ursäkta att det dröjt en halv vecka.",
    "Ursäkta att det dröjt två och en halv vecka.",
    "Ursäkta att det dröjt drygt en månad.",
    "Ursäkta att vi låtit er vänta i tre långa veckor.",
    # ursäkten och längden i var sin mening
    "Ursäkta det sena svaret. Det har gått två veckor sedan ni skrev.",
    "Ursäkta dröjsmålet. Vi har haft fullt upp i tre veckor.",
    # §7-GRANSKNINGEN AV SKIVA 62: former som passerade den första lydelsen
    "Ursäkta att det dröjt i en dryg vecka.",
    "Ursäkta att det dröjt i en knapp månad.",
    "Ursäkta att det dröjt ett antal veckor.",
    "Ursäkta att det dröjt ett flertal veckor.",
    "Ursäkta att det dröjt i veckor.",
    "Ursäkta att det dröjt i tre arbetsveckor.",
    "Ursäkta att det dröjt tio arbetsdagar.",
    "Ursäkta att det dröjt ett par arbetsdagar.",
    "Ursäkta att det dröjt i en veckas tid.",
    "Ursäkta att det dröjt i 14 dgr.",
    "Ursäkta att det dröjt i 2 mån.",
    "Ursäkta att det dröjt 2 v.",
    "Ursäkta att det dröjt i 3½ vecka.",
    "Ursäkta att det dröjt sedan förra veckan.",
    "Ursäkta att det dröjt sedan förra månaden.",
    "Ursäkta att det dröjt sedan den 3 augusti.",
    "Ursäkta att vi inte svarat sedan i juni.",
    "Tyvärr har det tagit oss tre veckor att svara.",
    "Sorry att det tog tre veckor.",
    "Hej! Vi har inte hunnit svara på två veckor.",
    "Hej! Svaret kommer två veckor för sent.",
    "Vi har varit borta i tre veckor och svarar nu.",
    "Tyvärr har ert mail blivit liggande i två veckor.",
    # FORMER SPÄRREN INTE FÅNGAR
    _hal("Ursäkta att det dröjt hela sommaren."),
    _hal("Ursäkta att det dröjt en fjortondagarsperiod."),
    _hal("Ursäkta att det dröjt tre hela långa veckor."),
    _hal("Ursäkta att det dröjt sedan midsommar."),
    _hal("Vi har haft semester i tre veckor, därav vårt svar nu."),
    # SKIVA 64, LUCKA 79: stycket med ursäkten prövas, inte hela svaret
    "Hej!\n\nVi bokar gärna in er.\n\nUrsäkta att det dröjt två veckor.",
    "Hej!\n\nUrsäkta dröjsmålet.\nDet har gått två veckor.",
    _hal("Ursäkta dröjsmålet.\n\nDet har gått två veckor sedan ni skrev.",
         lucka=79),
    "Hej!\r\n\r\nUrsäkta att det dröjt två veckor.",
]


@pytest.mark.parametrize("svar", DROJSMAL_SKA_FALLA)
def test_DROJSMALETS_LANGD_falls(svar):
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_drojsmal_utan_langd(svar)

    assert fel.value.sparr == "drojsmalets-langd"


@pytest.mark.parametrize("svar", [
    # NEGATIVKONTROLL: en ledtid utan ursäkt är inte den här spärrens sak.
    "Ombyggnaden brukar ta två veckor.",
    # NEGATIVKONTROLL: ursäkten utan längd, och Mattes hälsningar. En fri
    # ordplats före enheten fångade dem.
    "Ursäkta att det dröjt. Ha en fin dag!",
    "Ursäkta att det dröjt så länge. Trevlig helg och ha en trevlig helg!",
    "Ursäkta att det dröjt, det har varit fullt upp i veckan.",
    # SKIVA 64, LUCKA 79: bokningstiden i ett annat stycke än ursäkten.
    "Hej Anna,\n\nUrsäkta att det dröjt, det har varit fullt upp.\n\n"
    "Juni löser vi, hör av er så bestämmer vi en dag som passar.",
    "Hej Anna,\n\nUrsäkta att det dröjt.\n  \nVi bestämmer en dag som passar.",
    "Hej Anna,\r\n\r\nUrsäkta att det dröjt.\r\n\r\nVi bestämmer en dag "
    "som passar.",
])
def test_DROJSMALETS_LANGD_slapper_igenom(svar):
    generera.krav_pa_drojsmal_utan_langd(svar)


@pytest.mark.parametrize("svar", [
    "Ursäkta att det dröjt. Vi kan ta emot bilen om ett par veckor.",
    "Ursäkta att det dröjt. Besiktningen tar en dag.",
    "Det kan dröja två veckor innan delarna kommer.",
])
def test_DROJSMALETS_LANGD_faller_OCKSA_en_ledtid(svar):
    """ÖVERFÄLLNINGEN ÄR ETT VAL, fällt fram av §7-granskningen av skiva 62.

    Grinden prövar stycket med dröjsmålsordet, sedan skiva 64, och läser ett
    ord, inte en ursäkt. En längd saknar alltid källa, alltså fälls inget som
    fick gå ut."""
    with pytest.raises(Sparrfalld):
        generera.krav_pa_drojsmal_utan_langd(svar)


def test_EFTERSLAPSRADEN_forbjuder_langden():
    """Prompten hindrar, spärren fångar. Promptens lager är både regel 20 och
    underlagsraden, och den senare är bunden ordagrant ovan."""
    assert "Skriv aldrig hur länge det dröjt." in generera.EFTERSLAPSRAD
    assert "SKRIV ALDRIG HUR LÄNGE DET DRÖJT." in generera.SYSTEM


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
    text = generera._utfallstext(Utfall.ROTT, ROTT_UPPSLAG)

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


@pytest.mark.parametrize("uppslag,franvaro", [
    (None, frozenset()),
    (Uppslag(tjanstevikt_kg=980, slapvagnsvikt_kg=600, draganordning=False),
     frozenset({"draganordning"})),
    (Uppslag(tjanstevikt_kg=980, slapvagnsvikt_kg=600, draganordning=False),
     frozenset()),
    (Uppslag(tjanstevikt_kg=980, slapvagnsvikt_kg=600, draganordning=True),
     frozenset()),
])
def test_REGEL_16_beordrar_INGEN_form_som_en_SPARR_faller(uppslag, franvaro):
    """REGEL 16 FÅR INTE BE OM DET SPÄRRARNA FÄLLER. Lucka 52:s defektform.

    **RADEN FINNS DÄRFÖR ATT DEN SAKNADES, och frånvaron kostade en hel
    fältkörning.** Regel 14 och regel 15 har var sin motsvarande rad. Regel 16
    hade ingen, och dess FÖRSTA lydelse var oföljbar: den sade *"EN DRAGKROK
    INGÅR INTE I GRUNDOMBYGGNADEN. Den offereras separat."*, alltså ett PÅSTÅENDE
    som beordrade modellen att skriva ordet `dragkrok` ihop med `ingår inte`.
    Ordet står i `FORDONSTERMER` och i `FRANVAROFAKTA["draganordning"]`, så varje
    form som lydde regeln föll: `genererat-fordonsfaktum` utan uppslag,
    `pastaende-om-franvaro` med, och `atagande-om-priset` när frånvaron var
    belagd. De tjugo gav 20 spärrade och NOLL utkast.

    **DEN NYA LYDELSEN ÄR ETT RENT FÖRBUD**, och det är Lars beslut med hans
    skäl: en regel som beordrar ett påstående ger spärrarna något att fälla, en
    som bara förbjuder ger dem ingenting.

    **FYRA SVAR SOM LYDER REGELN, FYRA UPPSLAGSLÄGEN**, och ordningen är Lars:
    en ny promptregel mäts mot `krav_pa_svaret` INNAN de tjugo körs.

    Att lyda ett förbud är att låta bli, alltså är formerna här svar som inte
    säger att dragkroken ingår. Den sista bär prisraden ordagrant, eftersom
    regel 15 beordrar den i samma svar.

    **INGEN FORM BÄR ORDET `dragkrok`, och det är avsiktligt.** Regel 16 är ett
    förbud och beordrar aldrig att ordet skrivs, alltså hör en sådan form inte
    hit. Den skulle dessutom göra raden röd av FEL SKÄL: `dragkrok` är ett
    `FORDONSORD`, så varje mening som bär det faller på
    `genererat-fordonsfaktum` när uppslaget inte lyckats, oavsett vad den
    säger. Det gäller också regel 13:s egen form *"vi kan montera en"*, mätt
    mot HEAD och alltså äldre än den här skivan. Det är registrerat som LUCKA
    63 i `docs/sparrar.md` och är regel 13:s sak, inte regel 16:s.
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    telefon = FAKTA_SOM_LARS_BESLUTAT["telefon"]

    # VAKUITETSKONTROLL. Lyder formerna verkligen regeln? Bär någon av dem
    # `ingår` om dragkroken prövar raden motsatsen till det den påstår.
    former = [
        # 1. Kroken nämns inte alls, alltså förbudet lytt genom tystnad.
        "Vi behöver titta närmare på bilen innan vi kan ge ett säkert besked. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
        # 2. Ett erbjudande om ett arbete, utan något om vad priset täcker.
        "Extraljusen kopplar vi in åt er. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
        # 3. Monteringen erbjuden utan att kroken namnges.
        "Behövs det mer utrustning kan vi montera den åt er. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
        # 4. MED PRISRADEN ORDAGRANT, eftersom regel 15 beordrar den i samma
        # svar. Prisraden bär själv `ingår`, alltså prövas undantaget också.
        f"En konvertering till A-traktor kostar {pris}. "
        f"Ring oss på {telefon} så tittar vi på just den bilen.",
    ]

    # VAKUITETSKONTROLL I TVÅ LED. Lyder formerna verkligen regeln, och håller
    # de sig utanför det led som skulle göra raden röd av fel skäl?
    for svar in former:
        assert not re.search(r"dragkrok\w*\s+(?:ingår|följer|är inkluderad)",
                             svar, flags=re.IGNORECASE), (
            "formen lyder inte regel 16, alltså prövar raden fel sak"
        )
        assert not generera.FORDONSORD.search(svar), (
            "formen bär ett FORDONSORD, alltså faller den på uppslaget och "
            "inte på regel 16. Se LUCKA 63."
        )

    forfr = forfragan(utfall=Utfall.GULT, uppslag=uppslag,
                      franvaro_far_pastas=franvaro)

    for svar in former:
        generera.krav_pa_svaret(svar, forfr)


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

    **VARJE POST PRÖVAS MOT SIN EGEN KATEGORI, och det ledet är fällt fram.**
    Raden skickade `forfragan()`, alltså en a-traktorförfrågan, för SAMTLIGA
    poster. Efter skiva 52 stryks bara ärendets egen post, och raden hade därför
    gått röd den dag Lars lägger ett åtagandeord i en annan prispost: en laglig
    §10-ändring utan något fel i sändvägen, eftersom posten citerad i sitt EGET
    ärende passerar. §9.1 beskriver just det läget som det där frestelsen är att
    sänka spärren. Fällt av §7-granskningen av skiva 52.
    """
    par = [
        (nyckel, kategori, generera.las_priser()[nyckel])
        for kategori, nyckel in generera.PRISNYCKEL_FOR_KATEGORI.items()
        if nyckel in generera.las_priser()
    ]

    # VAKUITETSKONTROLL. Bär ingen post ett åtagandeord prövar raden ingenting,
    # och den vore då grön av fel skäl.
    barande = [n for n, _, v in par if generera.ATAGANDEORD.search(v)]
    assert barande, (
        "ingen post i config/priser.json bär ett åtagandeord, alltså prövar "
        "raden inte undantaget den finns för"
    )

    for _, kategori, varde in par:
        generera.krav_pa_atagande_med_kalla(
            f"En ombyggnad kostar {varde}.", forfragan(kategori=kategori)
        )


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
        , forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_en_OMSKRIVEN_prisrad_PASSERAR_nar_delarna_ar_belagda():
    """LARS §10-BESLUT I SKIVA 47: FÖREMÅLET PRÖVAS, INTE ORDET.

    **RADEN BAND FÖRUT MOTSATSEN, och den vändningen är beslutet.** Den hette
    `..._faller_i_atagandesparren` och krävde att en omskriven prisrad FÄLLER,
    med skälet att överblockering är den säkra riktningen. Uppmätt i fält var
    överblockeringen inte en kant utan regeln: trettio genereringar över tre
    lydelser gav NOLL ordagranna återgivningar, och de tjugo gav noll utkast.

    Lars skäl, ordagrant: spärren fällde på ORDET i stället för på PÅSTÅENDET.
    Ordet `ingår` är inget fel, ett obelagt föremål är det.

    Formen här är den modellen FAKTISKT skrev: uppräkningens subjekt byts mot
    ett bindeord. Varje del står kvar och är belagd i `config/priser.json`,
    alltså är påståendet sant och passerar.

    Att ett OBELAGT föremål fortfarande fäller binds av
    `test_ett_atagande_UTANFOR_prisfilen_faller_aven_nar_priset_citeras` och av
    `test_ett_atagande_om_en_OBELAGD_del_faller`.
    """
    pris = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    # BYTET ÄR DET MODELLEN FAKTISKT GJORDE, mätt i skiva 47: subjektet i
    # uppräkningens sats byts mot ett bindeord.
    omskrivet = pris.replace("och grundombyggnaden omfattar", "och den omfattar")
    assert omskrivet != pris, "bytet gav samma sträng, alltså prövas ingenting"

    # VAKUITETSKONTROLL. Strykningen får INTE vara det som friar, annars prövar
    # raden det gamla undantaget och inte det nya ledet.
    assert pris not in f"En ombyggnad kostar {omskrivet}.", (
        "den omskrivna raden bär värdet ordagrant, alltså friar strykningen "
        "den och föremålsprövningen mäts inte"
    )

    generera.krav_pa_atagande_med_kalla(f"En ombyggnad kostar {omskrivet}.", forfragan())


def test_PRÖVNINGEN_SKER_PER_SATS_och_inte_per_svar():
    """§7.1-KONTROLL FÖR `for sats in _meningar(kvar)`.

    **RADEN SAKNADES, och det var ett granskningsfynd i skiva 47.** Ledet
    lyftes fram som skivans nya i tre dokument, men ingen rad mätte det: fällt
    till `for sats in [kvar]` gick hela sviten GRÖN.

    Ett åtagandeord ska inte kunna hämta sitt BELÄGG ur en annan sats. Utan
    ledet läggs hela svaret i en påse, alltså friar `barlastflak` i den första
    meningen `lackering` i den andra.

    **`lackering` OCH INTE `dragkrok` I ANDRA MENINGEN, och det är poängen med
    provet.** Docstringens första exempel var *"…Dragkrok ingår också."*, och
    den strängen faller ÄVEN utan per-sats-ledet, på `dragkrok` som
    `FORDONSORD`. Den bevisade alltså ingenting om just den här raden. Fällt av
    §7-granskningen av skiva 47.
    """
    # VAKUITETSKONTROLL: den första satsen är belagd för sig, alltså är det
    # satsgränsen och inte något annat som fäller.
    generera.krav_pa_atagande_med_kalla("I priset ingår barlastflak.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla(
            "I priset ingår barlastflak. Lackering ingår också.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_ett_atagande_om_en_OBELAGD_del_faller():
    """FÖREMÅLSPRÖVNINGEN MÅSTE KUNNA SÄGA NEJ, annars friar den allt.

    `lackering` står inte i någon post i `config/priser.json`, alltså är
    åtagandet obelagt och faller. Utan den här raden vore "godta varje
    åtagandeord" en grön lösning.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla("Lackering ingår i priset.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_ett_NEKANDE_efter_atagandeordet_gor_INGEN_del_belagd(monkeypatch):
    """§7.1-KONTROLL FÖR `_NEKAT_EFTER_ATAGANDE`.

    **FORMEN STOD I PRISPOSTEN EN STUND.** Skiva 47:s första lydelse bar
    *"Dragkrok ingår inte och offereras separat."* Räknades den svansen som en
    uppräkning blev föremålet BELAGT av en mening som säger tvärtom, alltså
    hade spärren friat precis det åtagande den finns för att fälla.

    **SKADAN ÄR ETT FUNKTIONSORD SOM DEL, och den är uppmätt.** Utan ledet blir
    svansen efter `ingår` till delarna `inte` och `offereras separat`, och som
    BELAGD DEL friar `inte` varje sats som bär ordet. Mätt med ledet urkopplat:
    *"Vi vet inte om lackering ingår."* PASSERAR, alltså ett obelagt åtagande
    fritaget av ett nekande.

    Ordgränsat över `utgaende_text` i `data/par.jsonl`, satsdelat med
    `_meningar`, står `inte` i 56 av 1329 meningar.

    *Här stod att ordet står i VAR TREDJE mening. Talet bar ingen källa och
    stämmer inte mot korpusen: 56 av 1329 är var tjugofjärde. Fällt av
    §7-granskningen av skiva 47.*

    `lackering` och inte `dragkrok` i provet: ett `FORDONSORD` fälls av ett
    annat led, och raden ska mäta DET HÄR.
    """
    _med_priser(monkeypatch, {
        "a_traktorkonvertering":
            "1 000 kr för paketet, och paketet omfattar barlastflak. "
            "Lackering ingår inte och offereras separat",
    })

    # VAKUITETSKONTROLL: den bejakande delen är belagd, alltså fungerar
    # extraktionen i provet.
    generera.krav_pa_atagande_med_kalla("I priset ingår barlastflak.", forfragan())

    assert generera._uppraknade_delar("fråga om pris a-traktorkonvertering") == frozenset({"barlastflak"}), (
        "den nekade svansen har blivit delar, alltså friar ett funktionsord"
    )

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla("Vi vet inte om lackering ingår.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_en_MENINGSGRANS_avslutar_upprakningen(monkeypatch):
    """§7.1-KONTROLL FÖR `svans = re.split(r"[.!?]", svans)[0]`.

    Utan ledet sväljer den första meningens åtagandeord allt som står efter
    den, alltså blir innehåll ur en HELT ANNAN mening belagda delar.
    """
    _med_priser(monkeypatch, {
        "a_traktorkonvertering":
            "1 000 kr för paketet, och paketet omfattar barlastflak. "
            "Vi gör även rostskydd, lackering och mycket annat",
    })

    generera.krav_pa_atagande_med_kalla("I priset ingår barlastflak.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla("Lackering ingår i priset.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_en_FOR_KORT_del_racknas_inte(monkeypatch):
    """§7.1-KONTROLL FÖR `if len(bit) < MINSTA_DEL`.

    En kort del är oftast ett funktionsord, och den jämförs som DELSTRÄNG.
    Bleve `ab` en del friade den varje sats som råkar bära de två tecknen,
    `rabatt` bland dem, alltså hade spärren tystnat på bred front.
    """
    _med_priser(monkeypatch, {
        "a_traktorkonvertering":
            "1 000 kr för paketet, och paketet omfattar ab, barlastflak",
    })

    generera.krav_pa_atagande_med_kalla("I priset ingår barlastflak.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla("Rabatt ingår i priset.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_en_del_med_SIFFROR_racknas_inte(monkeypatch):
    """§7.1-KONTROLL FÖR `if any(t.isdigit() for t in bit)`.

    Prisvärden är fulla av tal, och en uppräkning kan bära ett belopp eller en
    tid mitt i. En sådan bit är ingen DEL utan ett pris, och som belagd del
    hade den friat en sats som citerar talet.
    """
    _med_priser(monkeypatch, {
        "a_traktorkonvertering":
            "1 000 kr för paketet, och paketet omfattar barlastflak, "
            "2 års garanti",
    })

    generera.krav_pa_atagande_med_kalla("I priset ingår barlastflak.", forfragan())

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla("2 års garanti ingår i priset.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"


def test_ett_FORDONSORD_i_satsen_faller_AVEN_med_en_belagd_del():
    """FORDONSORDSLEDET PRÖVAS FÖRST, och det är ärende 19:s form.

    *"I priset ingår barlastflak och dragkrok."* namnger en BELAGD del och en
    obelagd. Skulle barlastflaket fria satsen vore dragkroken inskriven i
    priset gratis, alltså precis det lucka 59 byggdes mot.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla(
            "I priset ingår barlastflak och dragkrok.", forfragan())

    assert fel.value.sparr == "atagande-om-priset"
    assert "dragkrok" in str(fel.value)


def test_att_KUNNA_UTFORA_ett_arbete_ar_INGET_atagande():
    """LARS SKILLNAD: kan utföra är inget prisåtagande, ingår är det.

    Båda formerna står i ärende 19, och bara den ena ska falla. En spärr som
    fällde båda hade fällt promptens regel 13, som uttryckligen ber om
    erbjudandet att montera en dragkrok.
    """
    generera.krav_pa_atagande_med_kalla("Extraljusen kopplar vi in.", forfragan())
    generera.krav_pa_atagande_med_kalla("Vi kan montera en dragkrok.", forfragan())

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla("Dragkrok ingår i bygget.", forfragan())


def test_strykningen_fogar_inte_ihop_tva_halvor_till_ett_atagandeord(monkeypatch):
    """VÄRDET BYTS MOT ETT BLANKSTEG, inte mot ingenting.

    Byttes det mot ingenting kunde strykningen foga ihop två halvor till ett
    åtagandeord som aldrig stod i svaret. Det är samma fälla
    `_prisord_over_skarven` beskriver för hopfogningen, åt andra hållet.

    **RADEN BINDER BARA DEN FORMEN, och det ledet är fällt fram.** En term som
    ligger INTILL skarven får en ny ordgräns av blanksteget och kan då matcha
    där den inte matchade förut, se raden nedan. Skillnaden är riktningen: den
    här formen vore en falsk FRIKÄNNANDE, den andra en överblockering.

    **NYCKELN MÅSTE VARA EN SOM KARTAN PEKAR PÅ, och det är skiva 52:s fälla.**
    Raden patchade `las_priser` med nyckeln `x`. Efter skiva 52 slår `priser_for`
    upp ärendets egen nyckel i den dicten, får `None` och returnerar tom dict,
    alltså ströks ingenting och raden kunde inte längre skilja `" "` från `""`.
    Fällningen `sub("", kvar)` gick grön med hela sviten. Fällt av
    §7-granskningen av skiva 52.
    """
    monkeypatch.setattr(
        generera, "las_priser",
        lambda *a, **k: {"a_traktorkonvertering": "MITTEN"},
    )

    # Utan blanksteget blir strängen `ingår` och raden fälls.
    generera.krav_pa_atagande_med_kalla("Vi ingMITTENår med jobbet.", forfragan())


def test_strykningen_KAN_tillverka_en_traff_INTILL_skarven():
    """ÖVERBLOCKERINGEN ÄR MÄTT och står i spärrens docstring.

    Blanksteget ger en term som ligger intill skarven en ny ordgräns.
    `…motortvätt 500 kringår.` bär ingen term, och efter strykningen står
    `ingår` där. Utfallet blir ett utkast Lars läser, aldrig ett släppt
    åtagande, alltså är formen ofarlig, men påståendet att strykningen inte kan
    tillverka en träff var falskt och raden hindrar att det skrivs igen.

    Fällt av §7-granskningen av skiva 46.

    *Förfrågan var en a-traktorförfrågan medan värdet är `service`:s. Sedan
    skiva 52 stryks bara ÄRENDETS EGEN prispost, alltså ströks värdet inte alls
    och skarven uppstod aldrig. Kategorin är nu den som äger värdet, så att
    raden prövar strykningen och inte kartan.*
    """
    varde = PRISER_SOM_LARS_BESLUTAT["service"]
    text = f"Vi {varde}ingår."

    assert not generera.ATAGANDEORD.search(text), (
        "texten bär redan en term, alltså prövar raden inte skarven"
    )

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla(
            text, forfragan(kategori="fråga om pris service")
        )


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

    generera.krav_pa_atagande_med_kalla(f"{versal}. Ring oss så tittar vi.", forfragan())


def test_en_RADBRUTEN_prisrad_passerar():
    """Samma led, andra formen: ett radbrott inuti prisraden.

    Ett svar sätts ihop av modellen och radbryts där den vill. Ett mellanslag i
    `config/priser.json` som blir en radbrytning i svaret är samma ORD i samma
    ordning, alltså ordagrant i den mening `PRISFOT` kräver.
    """
    varde = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]
    radbrutet = varde.replace("moms för grundombyggnaden",
                              "moms för\ngrundombyggnaden", 1)
    assert radbrutet != varde

    generera.krav_pa_atagande_med_kalla(f"En ombyggnad kostar {radbrutet}.", forfragan())


def test_ett_TOMT_prisvarde_tystar_INTE_sparren():
    """Ett tomt mönster matchar mellan varje tecken och stryker HELA svaret.

    `las_konfigvarden` utelämnar tomma värden, men den invarianten bor i en
    annan funktion. Raden binder att spärren inte tystnar om den ändras.
    """
    assert not generera._UTAN_PRISVARDE("").search("vad som helst ingår här")

    with pytest.raises(Sparrfalld):
        generera.krav_pa_atagande_med_kalla("Dragkroken ingår i bygget.", forfragan())


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
    assert generera._prisrader("fråga om pris a-traktorkonvertering") == generera.INGA_PRISER
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
        # SKIVA 64: ordgränsen står bara FÖRE, så en svans tappas inte.
        "Registret säger ingenting om dragvikten.",
        # SKIVA 64, §7-granskningen: markdown-kursiv är en ordgräns.
        "Bilen har _ingen_ dragvikt.",
        "Dragvikten är _okänd_.",
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
        # SKIVA 64, LUCKA 78. Frånvaroordet är svansen på ett vanligt ord.
        "Det är värt att ha med i beräkningen: bilen har en dragvikt på 2000 kg.",
        "Bilen har en dragvikt på 2000 kg, värt att ha med i beräkningen.",
        "Bilen har en dragvikt på 2000 kg, hej så länge.",
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


# --- SKIVA 52: KATEGORIN VÄLJER PRISPOSTEN -----------------------------------
#
# Lars beslut. `_prisrader` skrev ut HELA `config/priser.json` i varje prompt och
# `las_priser().values()` var tillåtna källor för prisspärrarna, i båda fallen
# oberoende av kategori. Ett a-traktorsvar kunde därmed skriva "en stor service
# kostar 4 650 kr" och passera varje spärr, eftersom talet står i filen.
#
# MÄTT FÖRE BYGGET: noll av botens sex utkast i `data/granskningsfall.jsonl` bär
# ett tal ur en annan kategoris prispost. Hålet var teoretiskt i det material som
# finns, och stängs ändå. Talen står i `docs/beslutslogg.md` #118.


def _prissvar(varde: str) -> str:
    """En prismening byggd ur ett HELT prisvärde, alltså citerat enligt PRISFOT."""
    return f"Hej! {varde}. Hör av dig så bokar vi in en tid."


@pytest.mark.parametrize(
    "frammande",
    [n for n in PRISER_SOM_LARS_BESLUTAT if n != "a_traktorkonvertering"
     and PRISER_SOM_LARS_BESLUTAT[n]],
)
def test_ett_tal_ur_en_ANNAN_kategoris_prispost_ar_INGEN_kalla(frammande):
    """SPÄRR: skivans hela poäng, och den fälls per främmande post.

    Varje post utom a-traktorns prövas mot en A-TRAKTORFÖRFRÅGAN. Talen står i
    `config/priser.json`, alltså passerade meningen före skiva 52, och kunden
    hade fått ett prisbesked om en tjänst ärendet inte gäller.

    **VARJE POST FÅR EN EGEN RAD.** En enda rad hade gått grön om kartan råkade
    peka rätt för just den posten.

    **SKÄLET PRÖVAS OCH INTE BARA SPÄRRNAMNET, och det ledet isolerar en av två
    REDUNDANTA rader.** `krav_pa_tal_med_kalla` prövar prissatsens tal mot
    priskällan och sedan HELA svarets tal mot `_tillatna_tal`. Båda läser
    prisfilen, och båda gick att återställa till hela filen med grön svit när de
    fälldes en i taget, alltså mätte ingen av fällningarna något (§7.1). De två
    ger OLIKA skäl. Raden här binder prissatsledet genom sitt skäl; talet utanför
    en prissats binds av `test_ett_FRAMMANDE_pristal_UTANFOR_en_prissats_faller`
    nedan. Fälls de två raderna tillsammans blir sviten röd.
    """
    svar = _prissvar(PRISER_SOM_LARS_BESLUTAT[frammande])

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            svar, forfragan(kategori="fråga om pris a-traktorkonvertering")
        )

    assert fel.value.sparr == "genererat-tal-har-kalla"
    assert "står i en prismening" in fel.value.skal, fel.value.skal


def test_ett_FRAMMANDE_pristal_UTANFOR_en_prissats_faller():
    """SPÄRR: isolerar `_tillatna_tal`, den andra av de två redundanta raderna.

    Meningen bär inget `PRISORD`, alltså är den ingen prissats och
    prissatsgrenen ser den aldrig. Kvar är slutkontrollen, som prövar VARJE tal i
    svaret mot `_tillatna_tal`. Läser den raden hela `config/priser.json` är 4650
    ett tillåtet tal i ett a-traktorsvar, och då passerar meningen.

    Talet är `service`-postens `stor service 4 650 kr`, alltså Lars egen form ur
    skiva 52:s instruktion, med prisordet borttaget så att bara den ena grenen
    kan fälla.
    """
    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_tal_med_kalla(
            "Hej! Vi har 4 650 skruvar kvar i lådan.",
            forfragan(kategori="fråga om pris a-traktorkonvertering"),
        )

    assert fel.value.sparr == "genererat-tal-har-kalla"
    assert "varken ur uppslaget eller ur config" in fel.value.skal, fel.value.skal


@pytest.mark.parametrize(
    "nyckel, kategori",
    [(n, k) for k, n in generera.PRISNYCKEL_FOR_KATEGORI.items()
     if PRISER_SOM_LARS_BESLUTAT.get(n)],
)
def test_den_EGNA_prispostens_tal_slapps_fortfarande_igenom(nyckel, kategori):
    """NEGATIVKONTROLL till raden ovan, och den är lastbärande.

    Utan den vore "ingen prispost är någonsin en källa" en grön lösning, och då
    hade boten slutat kunna skriva ut ett pris alls. Regel 15 beordrar att ett
    a-traktorsvar ALLTID skriver vad ombyggnaden kostar.

    Varje kategori i kartan prövas mot sin EGEN post.
    """
    svar = _prissvar(PRISER_SOM_LARS_BESLUTAT[nyckel])

    generera.krav_pa_tal_med_kalla(svar, forfragan(kategori=kategori))


def test_prompten_bar_BARA_arendets_egen_prispost():
    """SPÄRR: promptens halva av samma sak.

    Talspärren kan bara fälla det modellen skrivit. Att posten över huvud taget
    står i prompten är det som gör att modellen skriver den, alltså måste båda
    halvorna stängas. Jämför lucka 53: talets halva var stängd medan textens var
    öppen, och det var hålet.
    """
    block = generera._prisrader("fråga om pris a-traktorkonvertering")

    assert PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"] in block
    for namn, varde in PRISER_SOM_LARS_BESLUTAT.items():
        if namn == "a_traktorkonvertering" or not varde:
            continue
        assert namn not in block, f"{namn} står i a-traktorprompten"
        assert varde not in block, f"{namn}:s pris står i a-traktorprompten"


def test_en_kategori_UTAN_prispost_far_beskedet_att_inga_finns():
    """En kategori utanför kartan ska INTE få hela filen, och inte heller tiga.

    `INGA_PRISER` säger rakt ut att inga prisuppgifter finns, vilket är sant för
    den kategorin. Att tiga hade lämnat modellen att gissa om den får nämna ett
    pris, vilket är skälet beskedet skrivs ut i båda lägena.
    """
    assert "begära offert" not in generera.PRISNYCKEL_FOR_KATEGORI
    assert generera._prisrader("begära offert") == generera.INGA_PRISER
    assert generera.priser_for("begära offert") == {}


# KARTAN SOM LARS BESLUTAT, skiva 52. Samma form och samma skäl som
# `PRISER_SOM_LARS_BESLUTAT` ovan: vilken prispost en kategori får är Lars
# beslut, och en ändring ska kräva att tabellen här ändras i samma svep.
#
# **UTAN DEN HÄR TABELLEN BAR 8 AV KARTANS 13 RADER INGENTING.** Uppmätt med
# `scripts/sparr-prova.sh --radera N`, en rad i taget: bara raderna för
# a-traktorns tre kategorier, `fråga om pris rekond` och `fråga om pris service`
# gick röda. De övriga åtta gick att radera med hela sviten grön, och kategorin
# hade då tappat sitt pris tyst. Skälet var att
# `test_den_EGNA_prispostens_tal_slapps_fortfarande_igenom` parametriseras UR
# kartan och alltså krymper med den. Fällt av §7-granskningen av skiva 52.
#
# Riktningen är säker — en borttagen rad ger `INGA_PRISER` — men en tyst
# förlust är ingen mindre förlust.
KARTAN_SOM_LARS_BESLUTAT = {
    "fråga om pris a-traktorkonvertering": "a_traktorkonvertering",
    "fråga om a-traktorkonvertering": "a_traktorkonvertering",
    "boka a-traktorkonvertering": "a_traktorkonvertering",
    "fråga om pris rekond": "rekond",
    "boka rekond": "rekond",
    "fråga om pris service": "service",
    "boka service": "service",
    "fråga om pris reparation": "reparation",
    "boka reparation": "reparation",
    "fråga om pris däck": "dack",
    "boka däckbyte": "dack",
    "fråga om pris tillbehör": "tillbehor",
    "boka tillbehörsmontage": "tillbehor",
}


def test_prisnyckelkartan_bar_EXAKT_det_Lars_BESLUTAT():
    """§10-STOPP: varje rad i kartan binds, inte bara de fem som råkar prövas.

    Raden går röd på tre former: en ny kategori, en borttagen kategori, och en
    kategori som pekas om till en annan prispost. Alla tre är Lars beslut, och
    den som har hans beslut ändrar tabellen ovan i samma svep.

    **`boka biltvätt` OCH `boka bromskontroll` SAKNAS MED FLIT.** Posten `rekond`
    bär tvättpriser och `reparation` bär bromspriser, men att de två kategorierna
    prissätts ur just de posterna är ett antagande om verkstadens uppdelning och
    inte något `config/priser.json` säger. §10 gör den kopplingen till Lars.
    """
    assert generera.PRISNYCKEL_FOR_KATEGORI == KARTAN_SOM_LARS_BESLUTAT, (
        "§10-stopp: ändra tabellen här bara när Lars har beslutat ändringen."
    )


def test_prisnyckelkartan_pekar_bara_pa_verkliga_namn():
    """SPÄRR: kartans båda ändar ska finnas, annars tystnar en prispost tyst.

    En kategori som stavas fel faller aldrig på något: `priser_for` ger tom dict,
    prompten får `INGA_PRISER`, och kategorin tappar sitt pris utan att något
    blir rött. Samma sak åt andra hållet om en nyckel byter namn i filen.
    """
    taxonomi = json.loads(
        (generera.ROT / "data" / "taxonomi.json").read_text(encoding="utf-8")
    )
    prisnycklar = set(PRISER_SOM_LARS_BESLUTAT)

    for kategori, nyckel in generera.PRISNYCKEL_FOR_KATEGORI.items():
        assert kategori in taxonomi, (
            f"{kategori!r} står i PRISNYCKEL_FOR_KATEGORI men inte i taxonomin"
        )
        assert nyckel in prisnycklar, (
            f"{nyckel!r} står i PRISNYCKEL_FOR_KATEGORI men inte i priser.json"
        )


def test_kedjans_tre_a_traktorkategorier_bar_ALLA_prisposten():
    """SPÄRR: de tre kategorier som faktiskt får ett utkast ska kunna citera priset.

    `config/priser.json`:s `_nycklarna` säger att nycklarna är namngivna efter
    taxonomins `fråga om pris`-kategorier. En karta byggd på enbart den
    namnlikheten hade gett `boka a-traktorkonvertering` och
    `fråga om a-traktorkonvertering` ingen prispost alls, alltså tystat priset i
    två av kedjans tre kategorier.

    `generera.A_TRAKTORETIKETTER` läses härifrån och inte ur kedjan, så att
    testfilen inte drar in kedjan för tre strängar.

    *Här stod att den tupeln är bunden av
    `test_kedjans_a_traktorkategorier_matchar_vyns`. Falskt: den raden binder
    KEDJANS tupel mot VYNS, och generatorns tredje kopia band ingenting. Raden
    här mätte alltså kartan mot en uppräkning som kunde glida, och följde med i
    gliden: tupeln och kartan gick att byta tillsammans till en annan kategori
    med hela sviten grön. Kopian binds sedan §7-granskningen av skiva 52 av
    `test_GENERATORNS_a_traktoretiketter_matchar_de_andra_TVA` i
    `tests/test_kedja.py`, där alla tre modulerna redan är importerade.*
    """
    for kategori in generera.A_TRAKTORETIKETTER:
        assert generera.PRISNYCKEL_FOR_KATEGORI.get(kategori) == (
            "a_traktorkonvertering"
        ), f"{kategori!r} bär inte a-traktorns prispost"


def test_en_del_ur_en_ANNAN_kategoris_prispost_BELAGGER_INGENTING():
    """SPÄRR: åtagandespärrens halva av samma sak.

    A-traktorpostens `grundombyggnaden omfattar ... besiktning ...` räknar upp
    sju delar. Före skiva 52 lästes de oavsett kategori, alltså friade de ett
    `ingår` i ett svar om service lika gärna som i ett a-traktorsvar.

    NEGATIVKONTROLLEN står i samma rad: samma mening i ett A-TRAKTORÄRENDE ska
    fortfarande passera, annars mäter raden bara att spärren fäller allt.
    """
    svar = "I priset ingår besiktning."

    generera.krav_pa_atagande_med_kalla(
        svar, forfragan(kategori="fråga om pris a-traktorkonvertering")
    )

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla(
            svar, forfragan(kategori="fråga om pris service")
        )

    assert fel.value.sparr == "atagande-om-priset"


def test_STRYKNINGEN_ror_bara_den_EGNA_prisposten():
    """SPÄRR: isolerar strykningsraden i `krav_pa_atagande_med_kalla`.

    **ETT PRISVÄRDE SOM STRYKS TAR SITT ÅTAGANDEORD MED SIG**, och det är
    strykningens hela syfte: är prisraden ordagrant återgiven finns inget
    åtagandeord kvar att pröva. A-traktorpostens värde bär `omfattar`.

    Stryks HELA filen, som före skiva 52, försvinner alltså `omfattar` också ur
    ett SERVICESVAR som citerar a-traktorraden, och satsen passerar utan att
    någon del är belagd. Med bara den egna posten struken står ordet kvar och
    satsen faller, vilket är rätt: posten säger ingenting om vad en service
    omfattar.

    Utan den här raden går strykningen att återställa till hela filen med grön
    svit (§7.1).
    """
    a_traktorpriset = PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"]

    assert generera.ATAGANDEORD.search(a_traktorpriset), (
        "a-traktorvärdet bär inget åtagandeord, alltså prövar raden ingenting"
    )

    # EGET ÄRENDE: raden är ordagrant citerad och åtagandeordet stryks med den.
    generera.krav_pa_atagande_med_kalla(
        f"Hej! {a_traktorpriset}.",
        forfragan(kategori="fråga om pris a-traktorkonvertering"),
    )

    with pytest.raises(Sparrfalld) as fel:
        generera.krav_pa_atagande_med_kalla(
            f"Hej! {a_traktorpriset}.",
            forfragan(kategori="fråga om pris service"),
        )

    assert fel.value.sparr == "atagande-om-priset"


def test_UNDERLAGET_lamnar_vidare_arendets_kategori_till_prisblocket():
    """SPÄRR: isolerar ledet i `_underlag`, som är enda vägen in i prompten.

    `_prisrader` kan välja rätt post och ändå få fel kategori: `_underlag` är
    den som skickar den. Hårdkodas kategorin där skriver varje prompt
    a-traktorns priser, oavsett ärende, och hela skivan är verkningslös utan att
    något blir rött.

    Två kategorier prövas, alltså går ledet inte att hårdkoda till någondera.
    """
    a_traktor = generera._underlag(
        forfragan(kategori="fråga om pris a-traktorkonvertering")
    )
    rekond = generera._underlag(forfragan(kategori="fråga om pris rekond"))

    assert PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"] in a_traktor
    assert PRISER_SOM_LARS_BESLUTAT["rekond"] not in a_traktor

    assert PRISER_SOM_LARS_BESLUTAT["rekond"] in rekond
    assert PRISER_SOM_LARS_BESLUTAT["a_traktorkonvertering"] not in rekond


def test_de_SEX_utkasten_ur_skiva_51_passerar_PRISVAGEN():
    """SPÄRR: skivans verifikationskrav, mot det material som finns.

    Lars krav i skiva 52: a-traktorsvaren ska stå kvar och de sex utkasten ur
    `data/granskningsfall.jsonl` ska passera.

    **BARA DE PRISBEROENDE SPÄRRARNA PRÖVAS, och avgränsningen är en avläsning
    och inte en bekvämlighet.** `krav_pa_svaret` innehåller
    `krav_pa_fordonsfakta_ur_uppslag`, som kräver ett LYCKAT uppslag så snart
    svaret nämner ett fordonsord. Utkasten nämner dragkrok, och
    `data/granskningsfall.jsonl` bär inte uppslagets tjänstevikt och
    släpvagnsvikt: posten sparar bara `uppslagskalla`. Att hitta på en `Uppslag`
    hade gjort raden till ett prov på påhittad fordonsdata, vilket §7.2 förbjuder.
    De två spärrar skivan rör är de som prövas, och de är de enda som kan ha
    ändrat utfall.

    **FILEN ÄR GITIGNORERAD OCH BÄR KUNDTEXT.** Raden hoppas över när den saknas,
    och den läser aldrig ut något ur den: bara antal och utfall.

    **URVALET SNÄVADES I SKIVA 55, och skälet är att premissen ovan slutade
    gälla för en del av materialet.** `uppslag=None` var en SANN förfrågan för
    varje utkast så länge ett lyckat uppslag krävde alla tre fälten och varje
    sådant svar ändå nämnde dragkroken. Sedan skiva 55 ber bedömningen om
    släpvagnsvikten i klartext när bilen duger som dragfordon, och den siffran
    HAR en källa: uppslagets eget fält. Att då pröva svaret mot `uppslag=None` är
    inte en strängare prövning utan en FALSK: spärren fäller ett tal som är
    avläst, och raden blir röd av att boten gör rätt.

    Raden prövar därför bara de utkast vars härkomstrad säger att inget uppslag
    finns. För dem är `uppslag=None` det som FAKTISKT gällde, och prövningen
    mäter något. För de övriga går ingen sann förfrågan att bygga ur filen, och
    §7.2 säger att en uppgift man inte har utelämnas i stället för att gissas.
    """
    fil = generera.ROT / "data" / "granskningsfall.jsonl"
    if not fil.exists():
        pytest.skip("data/granskningsfall.jsonl saknas")

    utkast = []
    for rad in fil.read_text(encoding="utf-8").splitlines():
        if not rad.strip():
            continue
        post = json.loads(rad)
        if not (post.get("forslag") or "").strip():
            continue
        # HÄRKOMSTRADEN ÄR DET ENDA FILEN BÄR OM UPPSLAGET. Säger den
        # `lyckades` finns ett uppslag vars fält raden inte kan återskapa.
        if "lyckades" in post.get("uppslagskalla", ""):
            continue
        utkast.append(post)

    if not utkast:
        pytest.skip("inga utkast i data/granskningsfall.jsonl")

    for post in utkast:
        arende = forfragan(kategori=post["etikett"], uppslag=None,
                           regnr_i_mailet=False)
        generera.krav_pa_tal_med_kalla(post["forslag"], arende)
        generera.krav_pa_atagande_med_kalla(post["forslag"], arende)


# ------------------------------------------------- SKIVA 55: BEDÖMNINGSRADEN
#
# De fyra raderna nedan kom till efter en §7.1-prövning: `_barlastrad`:s vakt och
# `_bara_dragkroken_saknas`:s tre led var samtliga OBUNDNA, alltså gick de att
# neutralisera med hela sviten grön. De styr PROMPTTEXT och inte en fällning,
# vilket är precis varför ingen spärrtabell nådde dem.

XJZ_LIK = Uppslag(
    tjanstevikt_kg=1720, slapvagnsvikt_kg=1600, draganordning=False,
    kaross="Halvkombi", fyrhjulsdrift=True,
)


def test_bedomningen_blir_ett_JA_nar_bara_dragkroken_saknas():
    """SKIVA 55 DEL B PUNKT 2 OCH 4. det fyrhjulsdrivna fordonet i körningen skulle ha blivit ett tydligt ja.

    **DEN GAMLA TEXTEN VAR FALSK OM DEN HÄR BILEN.** `OKLART` sade *"vi kan inte
    avgöra det på uppgifterna vi har"*, medan släpvagnsvikten är avläst till
    1 600 kg och §42 andra stycket därmed uppfyllt. Det enda registret inte visar
    är en dragkrok.

    **TALET SKA BEGÄRAS, och det har en källa.** `_tillatna_tal` bär uppslagets
    släpvagnsvikt, alltså faller ett lydigt svar inte på talspärren. Raden blir
    röd om texten slutar be om siffran.
    """
    text = generera._utfallstext(Utfall.OKLART, XJZ_LIK)

    assert "släpvagnsvikten" in text
    assert "talet" in text
    assert "monterar" in text
    assert "kan inte avgöra" not in text
    # SKIVA 63 DEL B, Lars formulering för ett avläst Nej.
    assert "saknar registrerad draganordning" in text
    assert "Det enda registret inte visar" not in text


def test_NEJ_formuleringen_passerar_spärrarna():
    """Det Nej-läget ber om ska inte fällas. Skiva 63 DEL B."""
    forfr = Forfragan(
        text="x", kategori="fråga om a-traktorkonvertering",
        utfall=Utfall.OKLART, uppslag=XJZ_LIK,
        franvaro_far_pastas=frozenset({"draganordning"}),
    )

    generera.krav_pa_svaret(
        "Bilen duger som dragfordon, släpvagnsvikten är 1600 kg. Bilen saknar "
        "registrerad draganordning, så vi monterar en.", forfr)


def test_bedomningen_ber_INTE_om_siffran_nar_slapvagnsvikten_saknas():
    """FÖRSTA LEDET I `_bara_dragkroken_saknas`, bundet för sig.

    **FORDONET ÄR LÄMPLIGT PÅ TJÄNSTEVIKTEN och saknar släpvagnsvikt.** Utan det
    här ledet hade bedömningen bett modellen skriva ut en släpvagnsvikt som inte
    står i underlaget, alltså beordrat ett tal utan källa. Varje lydigt svar hade
    sedan fällts av `krav_pa_tal_med_kalla`, vilket är den garanterade falska
    fällning §7.1 varnar för.
    """
    tung = Uppslag(
        tjanstevikt_kg=2100, slapvagnsvikt_kg=None, draganordning=False,
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(tung) is True
    assert generera._bara_dragkroken_saknas(tung) is False


def test_bedomningen_blir_inget_JA_nar_fordonet_inte_ar_lampligt():
    """ANDRA LEDET, bundet för sig.

    Ett fordon vars båda tal är avlästa och faller duger INTE som dragfordon, och
    då är en dragkrok ingen lösning. Ledet är defensivt: `utvardera` ger ett
    sådant fordon RÖTT, alltså når kedjan aldrig OKLART med det. Att det ändå
    binds är §7.1:s krav, och funktionens kontrakt gäller också en direkt
    konstruerad förfrågan.
    """
    olamplig = Uppslag(
        tjanstevikt_kg=960, slapvagnsvikt_kg=600, draganordning=False,
    )

    assert fordonsuppslag.ar_lamplig_som_dragfordon(olamplig) is False
    assert generera._bara_dragkroken_saknas(olamplig) is False


def test_bedomningen_blir_inget_JA_nar_dragkroken_ar_okand():
    """TREDJE LEDET, bundet för sig.

    **ETT `None` ÄR INTE ETT `Nej`.** Vet vi ingenting om dragkroken ska svaret
    varken påstå att den saknas eller erbjuda sig att montera en: det första är
    ett obelagt frånvaropåstående, det andra ett fordonsfaktum utan avläst fält.
    Båda fälls av var sin spärr, alltså hade ledet annars beordrat ett
    STOPPTECKEN.
    """
    okand_krok = Uppslag(
        tjanstevikt_kg=1720, slapvagnsvikt_kg=1600, draganordning=None,
    )

    assert generera._bara_dragkroken_saknas(okand_krok) is False


def test_barlastraden_skrivs_BARA_for_ett_fordon_som_39_inte_galler():
    """SKIVA 55 DEL A GATINGSREGEL 2, promptens halva av den.

    **BÅDA RIKTNINGARNA ASSERAS.** Ett test som bara prövade att raden skrivs för
    det fyrhjulsdrivna fordonet i körningen hade varit grönt även om den skrevs för varje bil, alltså om varje
    a-traktorsvar tystat prisradens uppräkning utan skäl.

    **TREDJE RADEN ÄR DEN VIKTIGASTE.** Vet vi inget om drivningen säger prompten
    ingenting: en order byggd på okunskap är ett påstående om bilen.
    """
    utan_krav = generera._barlastrad(XJZ_LIK)

    assert "barlastflak" in utan_krav
    assert "BELOPPET" in utan_krav

    kan_galla = Uppslag(
        tjanstevikt_kg=1310, slapvagnsvikt_kg=1400, draganordning=False,
        fyrhjulsdrift=False,
    )
    assert generera._barlastrad(kan_galla) == ""

    okand_drivning = Uppslag(
        tjanstevikt_kg=1310, slapvagnsvikt_kg=1400, draganordning=False,
    )
    assert generera._barlastrad(okand_drivning) == ""

    assert generera._barlastrad(None) == ""


def test_underlaget_BAR_barlastraden():
    """Raden ska nå PROMPTEN, inte bara finnas som funktion.

    Utan den här kunde `_underlag` sluta anropa `_barlastrad` med sviten grön,
    och då vore hela gatingsregel 2 en död funktion med egna test.
    """
    text = generera._underlag(
        Forfragan(
            text="x", kategori="fråga om a-traktorkonvertering",
            utfall=Utfall.OKLART, uppslag=XJZ_LIK,
        )
    )

    assert "BARLASTFLAK:" in text
