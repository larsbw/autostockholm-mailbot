"""Utkastvyn, fas 5.5.

TESTERNA BÄR TRE SPÄRRAR, och den viktigaste är att vyn inte har någon sändväg.
Se `docs/sparrar.md`: `vyn-har-ingen-sandvag`, `spärrfälld-post-utan-textfalt`
och `vyn-skriver-bara-till-data-och-logg`.

*Här stod två namn som inte finns i något dokument, `referenssvar-skickas-aldrig`
och `sparrfalld-post-har-inget-textfalt`. Fällt av §7-granskningen av skiva 27,
varv 1. Varför de kom att stå här går inte att läsa ur repot, eftersom filen och
spärrposterna skapades i samma commit, och skälet skrivs därför inte ut.*

**FIXTURERNA BÄR INGEN KUNDTEXT.** Testerna bygger sina egna poster. Att läsa
`data/` i ett test hade gjort sviten beroende av en gitignorerad fil och satt
kundtext i en testrapport (§6).
"""

from __future__ import annotations

import dataclasses
import inspect
import io
import json
import re
from contextlib import redirect_stderr
from pathlib import Path

import pytest

from src import vy
from src.vy import Fall

ROT = Path(__file__).resolve().parent.parent


def ett_fall(**andrat) -> Fall:
    grund = dict(
        etikett="fråga om a-traktorkonvertering",
        kalla="med svar",
        text="Hej, vad kostar det att bygga om en Volvo till a-traktor?",
        tidsstampel="2026-01-02T03:04:05+00:00",
        avsandare_hash="0" * 64,
    )
    grund.update(andrat)
    return Fall(**grund)


# ---------------------------------------------------------------- DEL B


def test_vyn_har_ingen_sandvag():
    """SPÄRRENS HUVUDFALL. Vyn drar inte in något som kan skicka mail.

    Prövningen går över hela importgrafen inom repot, inte bara över
    `src/vy.py`, eftersom en modul vyn importerar kan importera vidare.
    """
    vy.krav_pa_sandvagsfrihet()


def test_importlagret_faller_en_modul_som_kan_skicka(tmp_path):
    """NEGATIVKONTROLL för importlagret: det fäller när det ska.

    Utan den här raden hade `krav_pa_sandvagsfrihet` kunnat sluta leta utan att
    något test blev rött, vilket är precis §7.1:s vakuösa fall.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "from googleapiclient.discovery import build\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "googleapiclient" in str(fel.value)


def test_importlagret_foljer_kedjan_ett_steg_till(tmp_path):
    """En modul som vyn importerar får inte heller ha en sändväg.

    Här importerar vyn en oskyldig modul, och DEN importerar `src.auth`.
    Prövningen ska följa kedjan; gjorde den inte det hade en indirektion räckt
    för att gömma sändvägen.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text("from src import mellan\n", encoding="utf-8")
    (tmp_path / "src" / "mellan.py").write_text("from src import auth\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "src.auth" in str(fel.value)


def test_importlagret_foljer_kedjan_aven_via_paketform(tmp_path):
    """DEN ANDRA IMPORTFORMEN, och den var otestad.

    `from src import mellan` och `from src.mellan import x` drar in samma modul
    men ger olika AST. Den första behöver ledet `nod.module + "." + alias.name`,
    den andra behöver `nod.module` självt: där ÄR `nod.module` redan
    `src.mellan`, medan det sammansatta namnet blir `src.mellan.x`, som inte är
    någon fil.

    Testet ovan använder bara den första formen, alltså gick
    `namn.add(nod.module)` att RADERA HELT med hela sviten grön. Vandringen
    slutade då följa kedjan för varje import av paketform, och en modul med
    sändväg hade kunnat gömmas ett steg bort. Funnen av §7-granskningen av
    skiva 27, varv 2, som en vakuös rad i sändvägsspärren.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "from src.mellan import hjalp\n", encoding="utf-8"
    )
    (tmp_path / "src" / "mellan.py").write_text(
        "import smtplib\n\n\ndef hjalp():\n    return smtplib\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "smtplib" in str(fel.value)


def test_importlagret_ser_relativa_importer(tmp_path):
    """DEN TREDJE IMPORTFORMEN, och den var helt osynlig för spärren.

    `from . import auth` har `nod.module` lika med None, alltså tog grenen
    `elif isinstance(nod, ast.ImportFrom) and nod.module` aldrig, och
    `_lokala_importer` returnerade en TOM MÄNGD. Varken importlagret eller
    källtextlagret såg modulen, och vandringen slutade följa kedjan.

    `src/__init__.py` finns, så formen är giltig i det här repot: en enda rad
    hade räckt för att dra in `src/auth.py`, som bygger credentials med
    `gmail.send` i sitt scope.

    Funnen av §7-granskningen av skiva 27, VARV 3.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "vy.py").write_text("from . import auth\n", encoding="utf-8")
    (tmp_path / "src" / "auth.py").write_text("import smtplib\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "src.auth" in str(fel.value)


def test_relativ_import_med_modulnamn_ser_ocksa_sandvagen(tmp_path):
    """DEN FJÄRDE FORMEN, som varv 3:s rättelse lämnade öppen.

    `from .auth import bygg` har `nod.module` satt till `auth`, alltså till en
    DEL av sökvägen, och `nod.level` lika med 1. Villkoret `nod.module or
    _paket(...)` tog då modulnamnet och ignorerade nivån, så spärren fick `auth`
    i stället för `src.auth`: namnet matchade inte `FORBJUDNA_MODULER`, och
    vandringen letade efter `auth.py` i repotet i stället för `src/auth.py`.

    Samma hål som `test_importlagret_ser_relativa_importer` stängde, en
    systerform bort. Funnen av §7-granskningen av skiva 28.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "vy.py").write_text(
        "from .auth import bygg\n", encoding="utf-8"
    )
    (tmp_path / "src" / "auth.py").write_text("import smtplib\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "src.auth" in str(fel.value)


def test_vandringen_foljer_en_relativ_import_till_en_oskyldig_modul(tmp_path):
    """DET SOM ANROPET I `moduler_i_vyn` VAKTAR, och som saknade test.

    De två anropen av `_lokala_importer` skyddar OLIKA fall. Det i
    `krav_pa_sandvagsfrihet` räcker när den relativt importerade modulen SJÄLV
    bär ett förbjudet namn: då fälls den redan på namnet. Det i `moduler_i_vyn`
    är det som får VANDRINGEN att läsa modulens källa.

    Här heter modulen `mellan`, alltså ingenting förbjudet, och sändvägen ligger
    inuti den. Utan `i_modul` i `moduler_i_vyn` blir grafen bara `src.vy`,
    `src/mellan.py` läses aldrig, och båda lagren ser tomt.

    Funnen av §7-granskningen av skiva 28, som en vakuös rad: anropet gick att
    ta bort med hela sviten grön.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "vy.py").write_text("from . import mellan\n", encoding="utf-8")
    (tmp_path / "src" / "mellan.py").write_text("import smtplib\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "smtplib" in str(fel.value)


def test_relativ_import_av_en_forbjuden_modul_falls_pa_NAMNET(tmp_path):
    """DET SOM ANROPET I `krav_pa_sandvagsfrihet` VAKTAR, och bara det.

    De två anropen av `_lokala_importer` är ett lagrat försvar och bär
    varandra i de flesta fall. Här är fallet där bara det ena kan fälla:
    `src.auth` står i `FORBJUDNA_MODULER` och är förbjuden PÅ NAMNET, oavsett
    vad filen innehåller. Modulen är därför tom här.

    Vandringen läser då `src/auth.py`, hittar ingenting förbjudet i den, och
    källtextlagret tiger. Bara namnprövningen i `krav_pa_sandvagsfrihet` kan
    fälla, och den ser namnet bara om `i_modul` skickas med dit.

    Funnen av §7-granskningen av skiva 28: efter att vandringen rättats blev
    det andra anropet grönt vid fällning, alltså inkonklusivt enligt §7.1:s
    klausul om lagrat försvar. Det här testet gör utfallet konklusivt.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "vy.py").write_text("from . import auth\n", encoding="utf-8")
    (tmp_path / "src" / "auth.py").write_text("OFARLIG = 1\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "src.auth" in str(fel.value)


def test_vandringen_laser_ett_pakets_init(tmp_path):
    """`src/__init__.py` KÖRS av varje `from . import x` och lästes aldrig.

    Uppslagningen mappade modulnamnet `src` till `src.py`, som inte finns, och
    hoppade över den. En sändväg i `src/__init__.py` var därmed osynlig för
    både importlagret och källtextlagret, trots att filen körs varje gång
    paketet rörs.

    Funnen av §7-granskningen av skiva 28, varv 2, som en oregistrerad
    räckviddsinskränkning.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("import smtplib\n", encoding="utf-8")
    (tmp_path / "src" / "vy.py").write_text("from . import auth\n", encoding="utf-8")
    (tmp_path / "src" / "auth.py").write_text("OFARLIG = 1\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "smtplib" in str(fel.value)


def test_nivan_raknas_steg_for_steg_uppat(tmp_path):
    """`_paket`:s NIVÅ, som var vakuös.

    Docstringen påstår att varje extra punkt tar ett steg till uppåt, och
    `[:-niva]` gick att hårdkoda till `[:-1]` med hela sviten grön: inget test
    hade en modul djup nog för att skilja formerna åt.

    Här ligger vyn i `src/a/b/`, alltså på djup fyra, och `from .. import auth`
    ska nå `src/a/auth.py` och inte `src/a/b/auth.py`. Med `[:-1]` löses den
    till fel paket och spärren letar efter fel fil.

    Funnen av §7-granskningen av skiva 28, varv 2.
    """
    assert vy._paket("src.a.b", 2) == "src"
    assert vy._paket("src.a.b", 1) == "src.a"

    djup = tmp_path / "src" / "a" / "b"
    djup.mkdir(parents=True)
    for katalog in (tmp_path / "src", tmp_path / "src" / "a", djup):
        (katalog / "__init__.py").write_text("", encoding="utf-8")
    (djup / "vy.py").write_text("from .. import auth\n", encoding="utf-8")
    (tmp_path / "src" / "a" / "auth.py").write_text(
        "import smtplib\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(start="src.a.b.vy", rot=tmp_path)

    assert "smtplib" in str(fel.value)


def test_relativ_import_utan_kant_modul_gissar_inte():
    """NOLLFALLET: går paketet inte att bestämma hittas det inte på.

    En gissning hade gett ett modulnamn som inte finns, alltså en TYST lucka
    där spärren letar efter fel fil och hittar ingenting. Tomt är det ärliga
    svaret, och det syns i att mängden är tom i stället för fel.
    """
    assert vy._lokala_importer("from . import auth", "") == set()
    assert vy._lokala_importer("from .. import auth", "vy") == set()


def test_kalltextlagret_faller_ett_anrop_utan_import(tmp_path):
    """NEGATIVKONTROLL för det andra lagret, och det är inte redundant.

    En modul kan nå en färdig Gmail-tjänst som ARGUMENT och anropa
    `messages().send` utan att importera något förbjudet. Importlagret ser
    ingenting då. Det här är fallet som skiljer de två lagren åt.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "def skicka(tjanst, brev):\n"
        "    return tjanst.users().messages().send(userId='me', body=brev)\n",
        encoding="utf-8",
    )

    with pytest.raises(vy.Sandvagsfel) as fel:
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)

    assert "messages().send" in str(fel.value)


def test_smtp_faller_ocksa(tmp_path):
    """Den andra vägen ut. `smtplib` behöver ingen Google-tjänst alls."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "import smtplib\n", encoding="utf-8"
    )

    with pytest.raises(vy.Sandvagsfel):
        vy.krav_pa_sandvagsfrihet(rot=tmp_path)


def test_en_ren_modul_slapps_igenom(tmp_path):
    """NEGATIVKONTROLL ÅT ANDRA HÅLLET: spärren är inte ett larm som alltid går.

    En spärr som fäller på allt är inget skydd, den är ett stopp, och den blir
    avstängd. Här importerar vyn `json` och en lokal modul, och ingenting ska
    hända.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "vy.py").write_text(
        "import json\nfrom src import urval\n", encoding="utf-8"
    )
    (tmp_path / "src" / "urval.py").write_text("import hashlib\n", encoding="utf-8")

    vy.krav_pa_sandvagsfrihet(rot=tmp_path)


def test_starta_provar_sparren_innan_servern_binds(monkeypatch):
    """Spärren körs FÖRE servern tar emot något.

    Utan den här raden hade `krav_pa_sandvagsfrihet` kunnat tas bort ur
    `starta` utan att någon rad blev röd: de andra testen anropar funktionen
    direkt.
    """
    anropad = []

    def fejk(*_, **__):
        anropad.append(True)
        raise vy.Sandvagsfel("fejkad")

    monkeypatch.setattr(vy, "krav_pa_sandvagsfrihet", fejk)

    with pytest.raises(vy.Sandvagsfel):
        vy.starta(port=0, fall=[])

    assert anropad


def test_servern_loggar_inte_vad_lars_laser():
    """§6. Standardloggen skriver varje sökväg till stderr.

    Sökvägen bär ett index och ingen kundtext, men servern ska inte skriva
    något alls om vad Lars läser. Övertäckningen av `log_message` gick att
    döpa om med hela sviten grön, alltså var kommentarens §6-åberopande
    ovaktat. Funnen av §7-granskningen av skiva 27, varv 2.

    **TESTET MÄTER ATT DEN TIGER, inte att den finns.** Första lydelsen frågade
    bara om `log_message` låg i klassens `vars`, alltså att en övertäckning
    existerade. En kropp som bytte `return` mot ett `stderr.write` hade hållit
    den grön. Namnet lovade ett beteende testet inte mätte. Fällt av
    §7-granskningen av skiva 27, varv 3.
    """
    hanterare = vy.bygg_hanterare([])
    skrivet = io.StringIO()

    with redirect_stderr(skrivet):
        hanterare.log_message(None, "%s kundtext %s", "GET", "/referens/3")

    assert skrivet.getvalue() == ""


def test_servern_binder_bara_loopback():
    """SKIVANS CENTRALA §6-PÅSTÅENDE, och det var ovaktat.

    Vyn visar rå kundtext och har ingen inloggning: den byggs lokalt först,
    och `docs/beslutslogg.md` #37 och #38 lägger hosting och auth i en egen
    skiva. Då är bindningen till loopback det enda som hindrar att vem som
    helst på nätet läser kundtexten.

    `("127.0.0.1", port)` gick att byta mot `("0.0.0.0", port)` med hela sviten
    grön. Både `starta`:s docstring och `scripts/kor-vy.py` påstår att servern
    inte tar emot något från nätet, och inget test mätte det. Funnen av
    §7-granskningen av skiva 27, varv 2.

    Port 0 låter operativsystemet välja en ledig port, så testet kan inte
    krocka med en körande vy.
    """
    server = vy.starta(port=0, fall=[])
    try:
        assert server.server_address[0] == "127.0.0.1"
    finally:
        server.server_close()


# ---------------------------------------------------------------- §6


def test_skrivning_utanfor_data_och_logg_kastar(tmp_path):
    """§6. Vyn visar rå kundtext och får inte skriva den var som helst."""
    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(ROT / "docs" / "lackt.jsonl")


def test_repotet_sjalvt_kastar_skrivfel_och_inte_indexerror(tmp_path, monkeypatch):
    """GRÄNSVÄRDET: sökvägen ÄR repoteten, alltså är `relativ.parts` tom.

    Villkoret indexerade `parts[0]` och kastade `IndexError` i stället för
    `Skrivfel`. Ingen skrivväg öppnades, men en spärr ska fälla med sitt eget
    undantag: den som fångar `Skrivfel` runt en skrivning hade annars sluppit
    igenom ett fel den trodde sig täcka. §4 kräver nollfallet, och det här är
    det. Funnet av §7-granskningen av skiva 27, varv 1.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)

    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(tmp_path)


def test_skrivning_utanfor_repot_kastar():
    with pytest.raises(vy.Skrivfel):
        vy.krav_pa_skrivbar_sokvag(Path("/tmp/lackt.jsonl"))


@pytest.mark.parametrize("katalog", ["data", "logg"])
def test_de_tva_gitignorerade_katalogerna_slapps_igenom(katalog):
    """NEGATIVKONTROLL: kontrollen får inte fälla de vägar vyn faktiskt har."""
    vy.krav_pa_skrivbar_sokvag(ROT / katalog / "fil.jsonl")


def test_referenssvar_kan_inte_sparas_utanfor_data(tmp_path, monkeypatch):
    """Kontrollen sitter i SKRIVFUNKTIONEN, inte hos anroparen.

    **SÖKVÄGEN LIGGER I `tmp_path`, ALDRIG I DET RIKTIGA REPOT, och det är inte
    en detalj.** Testet påstår att skrivningen INTE sker, alltså kommer det förr
    eller senare att köras med spärren fälld: det är precis vad §7.1:s prövning
    gör. Med en riktig sökväg skrev fällningen då en fil till `docs/` på riktigt,
    och prövningen av spärren blev själv det spärren finns för att förhindra.

    Uppmätt i skiva 27: fällningen av `krav_pa_skrivbar_sokvag`:s villkor lämnade
    efter sig en `docs/x.jsonl` med två poster i arbetsträdet, upptäckt först av
    `git status` inför committen.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    (tmp_path / "docs").mkdir()

    with pytest.raises(vy.Skrivfel):
        vy.spara_referenssvar(
            ett_fall(), "ett svar", parfil=tmp_path / "docs" / "x.jsonl"
        )


def test_omdome_kan_inte_loggas_utanfor_logg(tmp_path, monkeypatch):
    """SPÄRRENS ANDRA VERKSTÄLLIGHETSPUNKT, och den var otestad.

    §6 verkställs på TVÅ ställen: `spara_referenssvar` och `spara_omdome`. Bara
    den första var vaktad. `krav_pa_skrivbar_sokvag(omdomesfil)` i
    `spara_omdome` gick att RADERA HELT med hela sviten grön, alltså var raden
    vakuös enligt §7.1 och spärren obevakad på den vägen.

    **Fällningen som dolde det var min egen.** Prövningen i skiva 27 fällde de
    två anropen TILLSAMMANS och fick RÖD, vilket bara bevisade att minst ett av
    dem var bärande. Det är samma mekanism som §7.1:s klausul om lagrat försvar,
    spegelvänd: där ger en ofullständig fällning falskt VAKUÖST, här gav en
    sammanslagen fällning falskt ÄKTA. Fällningen ska göras per rad också, och
    spärrposten redovisar nu båda.

    Funnen av §7-granskningen av skiva 27, varv 1.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    (tmp_path / "docs").mkdir()

    with pytest.raises(vy.Skrivfel):
        vy.spara_omdome(
            ett_fall(), "godkann", omdomesfil=tmp_path / "docs" / "omdomen.jsonl"
        )


# ---------------------------------------------------------------- DEL 0


def test_sparrfalld_post_visar_aldrig_textfalt():
    """DEL 0 I SKIVA 27, beslut av Lars. §9.1 väger tyngre än bekvämligheten.

    En textruta bredvid ett fällt förslag gör förbudet till ett klick, även när
    knappen heter spara och inte skicka.
    """
    sida = vy.rendera_granskning(ett_fall(), "ett förslag", sparr="fordonsfakta-ur-sida")

    assert "<textarea" not in sida
    assert "<button" not in sida
    assert "fordonsfakta-ur-sida" in sida


def test_osparrad_post_visar_textfalt():
    """NEGATIVKONTROLL: regeln gäller den spärrfällda posten och inte alla.

    Utan den här raden hade `rendera_granskning` kunnat sluta visa textfält helt
    utan att något test blev rött, och granskningsläget hade varit oanvändbart.
    """
    sida = vy.rendera_granskning(ett_fall(), "ett förslag")

    assert "<textarea" in sida
    for omdome in vy.OMDOMESVARDEN:
        assert omdome in sida


# ---------------------------------------------------------------- DEL A


def test_referenslaget_visar_tomt_falt_och_ingen_skickaknapp():
    """REFERENSLÄGET. Tomt fält, och knappen är omöjlig att förväxla.

    PÅSTÅENDET GÄLLER KNAPPARNA, inte ordet. Sidan säger med avsikt *Skickas
    aldrig* i brödtexten, alltså kan testet inte fråga om teckenföljden `Skicka`
    finns någonstans i HTML:en: den första lydelsen gjorde det och blev röd av
    den upplysning som är hela poängen med vyn.
    """
    sida = vy.rendera_referens(ett_fall(), 0, 1)

    assert "<textarea name='svar' placeholder=" in sida
    assert [k.strip() for k in re.findall(r"<button[^>]*>(.*?)</button>", sida)] == [
        "Spara som par"
    ]


# Strängen varje escapningsprövning matar in. Den är markup som syns direkt om
# den slipper igenom, och den finns som konstant för att de två testen nedan
# ska mäta samma sak.
OND = "<script>larm()</script>"

# Renderarna, anropade med ETT `Fall` och inget annat. Signaturernas övriga
# parametrar prövas av `test_varje_strangparameter_till_renderarna_escapas`.
_RENDERARE = (
    ("rendera_referens", lambda fall: vy.rendera_referens(fall, 0, 1)),
    ("rendera_granskning", lambda fall: vy.rendera_granskning(fall, "ett förslag")),
    (
        "rendera_granskning spärrad",
        lambda fall: vy.rendera_granskning(fall, "ett förslag", sparr="en spärr"),
    ),
)


def test_varje_falt_pa_fall_escapas():
    """KLASSEN, inte instansen, och den här gången på riktigt.

    **FÄLTEN HÄRLEDS UR `Fall`, inte ur en lista i testet.** Det är skillnaden
    mot föregående lydelse, som räknade upp de fält som fanns när den skrevs.
    Läggs ett fält till på `Fall` och renderas oescapat blir raden röd av att
    fältet EXISTERAR, vilket är vad "klass" betyder.

    Föregående lydelse påstod sig pröva klassen och gjorde det inte:
    §7-granskningen av skiva 28 renderade ett befintligt men ouppräknat fält
    oescapat och fick hela sviten grön. Namnet lovade ett beteende testet inte
    mätte, alltså samma defektform som `test_servern_loggar_inte_vad_lars_laser`
    bar innan den skrevs om.
    """
    for falt in dataclasses.fields(Fall):
        for namn, rendera in _RENDERARE:
            sida = rendera(ett_fall(**{falt.name: OND}))
            assert OND not in sida, f"{namn} escapar inte {falt.name}"


def test_varje_strangparameter_till_renderarna_escapas():
    """ANDRA HALVAN AV KLASSEN: renderarnas egna parametrar.

    `Fall` täcker fälten, men `forslag` och `sparr` är fria parametrar och
    kommer inte därifrån. De härleds ur `inspect.signature`, så en NY
    strängparameter som renderas oescapat blir röd av att den existerar.

    `fall`, `index` och `antal` hoppas över: det första prövas av testet ovan,
    de två andra är heltal och kan inte bära markup.
    """
    hoppa = {"fall", "index", "antal"}
    provade = []

    for renderare in (vy.rendera_referens, vy.rendera_granskning):
        parametrar = [
            namn
            for namn in inspect.signature(renderare).parameters
            if namn not in hoppa
        ]

        for namn in parametrar:
            provade.append(namn)
            argument = {"fall": ett_fall(), namn: OND}
            if renderare is vy.rendera_granskning:
                argument.setdefault("forslag", "ett förslag")
            sida = renderare(**argument)
            assert OND not in sida, f"{renderare.__name__} escapar inte {namn}"

    # Att uppräkningen inte tystnade. Blir `hoppa` någon gång för bred, eller
    # ändras signaturerna, ska testet falla i stället för att pröva noll
    # parametrar och rapportera grönt.
    assert provade == ["forslag", "sparr"]


def test_felmeddelandet_escapas_innan_det_reflekteras():
    """POST-kroppen reflekteras tillbaka i HTML, och det är den enda platsen.

    `spara_referenssvar` kastar `ValueError` med det okända utfallet inbakat,
    och `do_POST` skriver felet i sidan. Värdet kommer ur POST-kroppen, alltså
    utifrån. Utan escapning är det en väg att få egen markup renderad.

    **TESTET ANROPAR VYNS EGEN FUNKTION.** Första lydelsen byggde sidan i
    testet med `html.escape` och prövade alltså sin egen rad: den hade förblivit
    grön hur `src/vy.py` än såg ut. Felsidan är därför utbruten till
    `rendera_fel`, som går att fälla.
    """
    sida = vy.rendera_fel(ValueError("okänt utfall: '<script>larm()</script>'"))

    assert "<script>larm()</script>" not in sida
    assert "&lt;script&gt;" in sida


def test_kundtexten_escapas_aven_i_granskningslaget():
    """BÅDA RENDERARNA, inte bara den som är kopplad.

    `rendera_granskning` bygger sitt eget huvud och escapade kundtexten där
    utan att något test mätte det: `html.escape` gick att ta bort med hela
    sviten grön. Att läget saknar rutt i dag (lucka 15) gör det ofarligt nu och
    inte i fas 5, och en ovaktad escape är precis den sortens rad som överlever
    en omskrivning. Funnen av §7-granskningen av skiva 27, varv 2.
    """
    sida = vy.rendera_granskning(
        ett_fall(text="<script>larm()</script>"), "ett förslag"
    )

    assert "<script>larm()</script>" not in sida
    assert "&lt;script&gt;" in sida


def test_kundtexten_escapas_i_sidan():
    """Kundtext renderas som TEXT och aldrig som markup.

    En kund som skriver `<script>` ska synas på skärmen, inte köras i
    webbläsaren. Vyn visar rå kundtext, alltså är det här den enda platsen där
    råheten möter en tolk.
    """
    sida = vy.rendera_referens(ett_fall(text="<script>larm()</script>"), 0, 1)

    assert "<script>larm()</script>" not in sida
    assert "&lt;script&gt;" in sida


def test_referenssvar_skrivs_som_ett_par(tmp_path, monkeypatch):
    """Referenssvaret hamnar i par.jsonl med de fyra ursprungliga nycklarna."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    parfil = tmp_path / "data" / "par.jsonl"

    post = vy.spara_referenssvar(ett_fall(), "  Hej, det kostar X.  ", "gront", parfil)

    assert post["inkommande_text"] == ett_fall().text
    assert post["utgaende_text"] == "Hej, det kostar X."
    assert post["tidsstampel"] == ett_fall().tidsstampel
    assert post["avsandare_hash"] == ett_fall().avsandare_hash

    rader = parfil.read_text(encoding="utf-8").splitlines()
    assert json.loads(rader[0]) == post


def test_referenssvaret_ar_markt_som_referenssvar(tmp_path, monkeypatch):
    """#11 räknar svarsinstanser, och ett referenssvar är inte en sådan.

    Utan markören hade en senare läsare räknat referenssvaren som svar vi
    faktiskt skickat till en kund.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    post = vy.spara_referenssvar(
        ett_fall(), "ett svar", "rott", tmp_path / "data" / "par.jsonl"
    )

    assert post["kalla"] == "referenssvar"
    assert post["utfall"] == "rott"


def test_tomt_referenssvar_sparas_inte(tmp_path, monkeypatch):
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_referenssvar(ett_fall(), "   ", parfil=tmp_path / "data" / "par.jsonl")


def test_okant_utfall_avvisas(tmp_path, monkeypatch):
    """De fyra utfallen är en sluten lista, precis som i `fordonsuppslag`."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_referenssvar(
            ett_fall(), "ett svar", "kanske", tmp_path / "data" / "par.jsonl"
        )


@pytest.mark.parametrize("utfall", vy.UTFALL)
def test_de_fem_tillatna_utfallen_gar_igenom(tmp_path, monkeypatch, utfall):
    """NEGATIVKONTROLL till raden ovan, inklusive den tomma strängen.

    Tom betyder att Lars inte angett något, och det ska gå: DEL C säger att
    utfallet anges MANUELLT när det inte går att avgöra.
    """
    monkeypatch.setattr(vy, "ROT", tmp_path)
    post = vy.spara_referenssvar(
        ett_fall(), "ett svar", utfall, tmp_path / "data" / "par.jsonl"
    )
    assert post["utfall"] == utfall


# ---------------------------------------------------------------- omdömen


def test_de_fyra_omdomena_loggas_atskilt(tmp_path, monkeypatch):
    """De fyra slås aldrig ihop till godkänt och icke godkänt."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    fil = tmp_path / "logg" / "omdomen.jsonl"

    for omdome in ("godkann", "forkasta", "neka"):
        vy.spara_omdome(ett_fall(), omdome, omdomesfil=fil)

    loggade = [json.loads(r)["omdome"] for r in fil.read_text().splitlines()]
    assert loggade == ["godkann", "forkasta", "neka"]


def test_forbattra_skriver_ocksa_ett_par(tmp_path, monkeypatch):
    """`forbattra` är den enda av de fyra som tränar rösten."""
    monkeypatch.setattr(vy, "ROT", tmp_path)
    parfil = tmp_path / "data" / "par.jsonl"

    vy.spara_omdome(
        ett_fall(), "forbattra", "så här skulle det stått",
        omdomesfil=tmp_path / "logg" / "omdomen.jsonl", parfil=parfil,
    )

    post = json.loads(parfil.read_text(encoding="utf-8").splitlines()[0])
    assert post["utgaende_text"] == "så här skulle det stått"


def test_okant_omdome_avvisas(tmp_path, monkeypatch):
    monkeypatch.setattr(vy, "ROT", tmp_path)
    with pytest.raises(ValueError):
        vy.spara_omdome(ett_fall(), "kanske", omdomesfil=tmp_path / "logg" / "o.jsonl")


# ---------------------------------------------------------------- DEL C


def test_urvalet_tar_bada_populationerna(tmp_path):
    """A-traktorfall både med svar och utan, så att de fyra utfallen går att nå."""
    etikettfil = tmp_path / "ometiketterade.jsonl"
    parfil = tmp_path / "par.jsonl"
    etikettfil.write_text(
        json.dumps({"etikett": "fråga om a-traktorkonvertering",
                    "kalla": "med svar", "text": "A"}, ensure_ascii=False) + "\n"
        + json.dumps({"etikett": "boka a-traktorkonvertering",
                      "kalla": "utan svar", "text": "B"}, ensure_ascii=False) + "\n"
        + json.dumps({"etikett": "boka rekond",
                      "kalla": "med svar", "text": "C"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    parfil.write_text(
        json.dumps({"inkommande_text": "A", "utgaende_text": "svar",
                    "tidsstampel": "T", "avsandare_hash": "H"}) + "\n",
        encoding="utf-8",
    )

    fall = vy.las_fall(etikettfil, parfil)

    assert [f.text for f in fall] == ["A", "B"]
    assert fall[0].tidsstampel == "T"
    assert fall[0].avsandare_hash == "H"


def test_obesvarat_fall_far_tomma_falt_och_ingen_pahittad_hash(tmp_path):
    """HÅLET SKRIVS UT I STÄLLET FÖR ATT FYLLAS.

    Uppmätt med `scripts/par-koppling.py`: av de 9 obesvarade a-traktorfallen
    kopplas 0 på exakt `snippet` och 1 på `snippet` som inledning, mot 1604
    trådar. Gmails `snippet` sitter på MEDDELANDET och är TRUNKERAT, alltså är
    det ingen nyckel. En påhittad hash hade varit ett tal utan källa (§7.2).

    *Här stod först 1 av 9 utan reproducerbar källa, sedan att kopplingen är
    obefintlig. Det andra var falskt och var skrivet för att rätta det första.
    Fällt av §7-granskningen av skiva 27, varv 2.*
    """
    etikettfil = tmp_path / "ometiketterade.jsonl"
    etikettfil.write_text(
        json.dumps({"etikett": "boka a-traktorkonvertering",
                    "kalla": "utan svar", "text": "B"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    fall = vy.las_fall(etikettfil, tmp_path / "finns-inte.jsonl")

    assert fall[0].tidsstampel == ""
    assert fall[0].avsandare_hash == ""


def test_urvalet_ar_tomt_utan_etikettfil(tmp_path):
    assert vy.las_fall(tmp_path / "finns-inte.jsonl", tmp_path / "par.jsonl") == []
