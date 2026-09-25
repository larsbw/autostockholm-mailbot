"""SKUGGLÄGETS SLINGA. Sändväg i den mening §7 avser: den bygger det ärende
klassificeringen, fordonsuppslaget och generatorn arbetar på.

**INGET TEST HÄR RÖR NÄTET.** `kor_alla` tar klienten och hämtningen som
argument, alltså är båda utbytbara mot fejkar, och trådarna är dictar skrivna
för hand.

**ALL INDATA ÄR PÅHITTAD.** Ingen kundtext, inga riktiga adresser (§6).
"""

from __future__ import annotations

import base64
import importlib.util
import json
import re
import sys
from datetime import timedelta
from pathlib import Path

import pytest

from src import gmailutkast, generera, inkorg, kedja, klassa_maskin, vy
from src.kedja import Arende, Kedjeutfall, Steg
from tests.fejk import FejkGmail
from tests.test_kedja import (NU, FejkKlient, HINKAR, PromptSpion, TAXONOMI,
                              hamta_gront)
from tests.test_vy import peka_om_katalogerna

ROT = Path(__file__).resolve().parent.parent
RESPOND = ROT / "scripts" / "respond.py"


def _ladda():
    """`scripts/respond.py` som modul.

    Skriptet ligger i `scripts/` och inte i `src/`, eftersom varje annan
    ingång i repot gör det. Namnet är importerbart, till skillnad från
    `kedja-prov.py`, och laddas här via sin sökväg så att testet inte behöver
    en kopia av `scripts/` på `sys.path`.
    """
    spec = importlib.util.spec_from_file_location("respond_under_test", RESPOND)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = modul
    spec.loader.exec_module(modul)
    return modul


respond = _ladda()


# --------------------------------------------------------------- material


def _kropp(text: str) -> dict:
    return {"mimeType": "text/plain",
            "body": {"data": base64.urlsafe_b64encode(
                text.encode("utf-8")).decode("ascii").rstrip("=")}}


def meddelande(text: str, *, huvuden=None, sent=False,
               internal="1757900000000") -> dict:
    """Ett Gmail-meddelande med det urvalsmodulen läser och inget mer."""
    alla = {"From": "kund@exempel.invalid", "To": "info@autostockholm.se",
            "Subject": "Fråga"}
    alla.update(huvuden or {})
    return {
        "labelIds": ["SENT"] if sent else ["INBOX"],
        "internalDate": internal,
        "payload": {
            "mimeType": "text/plain",
            "headers": [{"name": n, "value": v} for n, v in alla.items()],
            **_kropp(text),
        },
    }


def trad(*meddelanden, trad_id="t1") -> dict:
    return {"id": trad_id, "messages": list(meddelanden)}


@pytest.fixture(autouse=True)
def _tom_forbudslista():
    """`las_forbjudna` är cachad per sökväg och läser den riktiga filen."""
    klassa_maskin.las_forbjudna.cache_clear()
    yield
    klassa_maskin.las_forbjudna.cache_clear()


@pytest.fixture
def loggfil(tmp_path, monkeypatch):
    """En beslutslogg i temporärkatalogen. Ingen rad når den riktiga.

    `vy.ROT` pekas om med, eftersom `krav_pa_skrivbar_sokvag` mäter mot den och
    annars fäller varje skrivning i temporärkatalogen.

    Sökvägen skickas som ARGUMENT till `kor_alla` och pekas inte om med
    monkeypatch. `kedja.logga_beslut` binder sin egen `BESLUTSLOGG` i signaturen,
    alltså hade en ompekning av modulglobalen inte nått fram: det är
    `docs/incidentlogg.md` I1:s form, och den är skälet att `kor_alla` slår upp
    sin loggfil vid anropet.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    return tmp_path / "logg" / "beslut.jsonl"


# ------------------------------------------------------------- SPÄRREN


def test_respond_nar_gmail_BARA_via_de_namngivna_modulerna():
    """LAGER 3. Spärren är inte borta, den är avsmalnad.

    `vyn-har-ingen-sandvag` i sin ursprungliga form går inte att hålla när
    brevlådan ska läsas: `src/mine.py` importerar `googleapiclient` och
    `src.auth`. Lars §10-beslut i skiva 48 var fyra lager i stället, och det här
    är det tredje: EN utpekad väg i stället för ingen.

    `src.inkorg`, `src.mine` och `src.auth` står i `vy.GMAILBARANDE_MODULER`.
    En fjärde modul som drar in `googleapiclient` faller, se testet nedan.
    """
    vy.krav_pa_sandvagsfrihet("scripts.respond", tillatna=vy.UNDANTAGBARA)


def test_en_ONAMNGIVEN_modul_som_drar_in_googleapiclient_FALLER(tmp_path):
    """LAGER 3, och det som gör uppräkningen till en spärr och inte en dörr.

    Undantaget gäller MODULEN SOM IMPORTERAR, inte namnet som importeras. Gällde
    det namnet vore lagret borta: vilken modul som helst hade då kunnat dra in
    `googleapiclient` så snart någon annan redan gjort det.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "inkorg.py").write_text(
        "import googleapiclient\n", encoding="utf-8")
    (tmp_path / "src" / "smyg.py").write_text(
        "import googleapiclient\n", encoding="utf-8")
    (tmp_path / "src" / "start.py").write_text(
        "from src import inkorg, smyg\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel, match="src.smyg"):
        vy.krav_pa_sandvagsfrihet("src.start", rot=tmp_path,
                                  tillatna=vy.UNDANTAGBARA)


def test_smtplib_gar_ALDRIG_att_undanta():
    """LAGER 3. En tillåtningslista som kunde öppna vad som helst vore en
    avstängningsknapp med ett annat namn.

    `smtplib` är den andra vägen ut ur en Pythonprocess och har inget ärende i
    det här repot. Den står utanför `UNDANTAGBARA`, alltså kastar spärren på
    SJÄLVA FÖRSÖKET att undanta den, innan någon graf ens vandras.
    """
    assert "smtplib" not in vy.UNDANTAGBARA

    with pytest.raises(vy.Sandvagsfel, match="går inte att undanta"):
        vy.krav_pa_sandvagsfrihet("scripts.respond",
                                  tillatna=frozenset({"smtplib"}))


def test_kalltextlagret_galler_HELA_grafen_aven_en_namngiven_modul(tmp_path):
    """LAGER 4, OFÖRÄNDRAT. Undantaget rör importen, aldrig anropet.

    En modul får dra in `googleapiclient` för att läsa. Skriver den ett
    sändanrop faller den ändå, och det är hela skillnaden mellan att få nå en
    tjänst och att få skicka med den.
    """
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "inkorg.py").write_text(
        "import googleapiclient\n"
        "def ut(t):\n"
        "    return t.users().messages().send(userId='me').execute()\n",
        encoding="utf-8")
    (tmp_path / "src" / "start.py").write_text(
        "from src import inkorg\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel, match="messages\\(\\).send"):
        vy.krav_pa_sandvagsfrihet("src.start", rot=tmp_path,
                                  tillatna=vy.UNDANTAGBARA)


def test_vyns_och_kedjans_sparr_far_INGA_undantag():
    """**DE TVÅ STARKA PRÖVNINGARNA MJUKAS INTE UPP AV DEN HÄR SKIVAN.**

    Vyn ska ha INGEN väg till en brevlåda, och kedjan likaså. `tillatna` är tom
    som förval, alltså är de två anropen oförändrade; raden här binder att de
    inte tyst får ett argument.

    Prövningen läser koden och inte prosan, av samma skäl som
    `test_respond_har_INGEN_send_flagga`.
    """
    for anrop in (vy.krav_pa_sandvagsfrihet, ):
        assert anrop.__defaults__[-1] == frozenset(), (
            "krav_pa_sandvagsfrihet har fått ett förval som inte är tomt. "
            "Spärren blir då fail-open för varje anropare som inte vet att "
            "parametern finns."
        )

    # ANROPEN, INTE DEFINITIONEN. `def krav_pa_sandvagsfrihet (` bär förstås
    # `tillatna`, det är där parametern står. Ett naivt `split` fällde på den
    # egna signaturen, alltså på det raden inte handlar om.
    anropet = re.compile(r"(?<!def )krav_pa_sandvagsfrihet \(")

    for fil in ("src/vy.py", "tests/test_vy.py", "tests/test_kedja.py"):
        kod = vy._kod_utan_prosa((ROT / fil).read_text(encoding="utf-8"))
        for traff in anropet.finditer(kod):
            stycke = kod[traff.end():traff.end() + 120]
            assert "tillatna" not in stycke, (
                f"{fil} skickar `tillatna` till krav_pa_sandvagsfrihet. Vyns "
                "och kedjans prövning ska vara den starka formen: ingen väg "
                f"alls. Anropet: {stycke[:60]!r}"
            )


def test_respond_har_INGEN_send_flagga():
    """§5: sändning är aldrig del av att skeppa, och det ska synas i källtexten.

    Raden läser KODEN och inte prosan om koden, med `vy._kod_utan_prosa`, samma
    val som `test_kallan_och_flaggan_kommer_ur_SAMMA_uttryck` gör.

    *Raden läste tidigare hela filens råtext och påstod sig läsa
    argparse-uppsättningen. Den gick grön bara därför att modulens docstring
    skriver `--send` med bakåtfästen; en docstring som citerade `"--send"` med
    raka citattecken hade gjort den röd av fel skäl, och en `--send` i en
    strängvariabel hade sluppit igenom. Fällt av §7-granskningen av skiva 48.*
    """
    kod = vy._kod_utan_prosa(RESPOND.read_text(encoding="utf-8"))

    for flagga in ("--send", "--skicka"):
        assert flagga not in kod, (
            f"scripts/respond.py bär {flagga} i sin KOD. Skuggläget skickar "
            "ingenting, och en sändflagga är fas 7 och ett §10-stopp."
        )


# --------------------------------------------------- DEL A: ärenden ur trådar


def test_maskinmail_blir_inget_arende():
    """Ett nyhetsbrev är inget kundärende, och skälet följer med."""
    nyhetsbrev = trad(meddelande(
        "Veckans erbjudanden",
        huvuden={"List-Unsubscribe": "<mailto:av@exempel.invalid>"}))

    arende, skal = respond.arende_ur_trad(nyhetsbrev, set())

    assert arende is None
    assert skal.startswith("maskinmail:")


def test_arendet_byggs_ur_SAMMA_meddelande_som_maskinbedomningen():
    """En tråd får inte bedömas på ett mail och besvaras på ett annat.

    `klassa_maskin.tradens_skal` stannar på trådens FÖRSTA inkommande
    meddelande. Väljer `arende_ur_trad` ett annat, till exempel det sista, kan
    en tråd friande bedömas på kundens första mail och sedan besvaras på en
    utskicksnotis längre ned i samma tråd.

    Tråden här bär ett kundmail först och ett massutskick sedan. Ett ärende
    byggt ur det SENARE hade burit dess text.
    """
    blandad = trad(
        meddelande("Hej, jag undrar om ni kan bygga om min bil."),
        meddelande("Veckans erbjudanden",
                   huvuden={"List-Unsubscribe": "<mailto:av@exempel.invalid>"}),
    )

    arende, skal = respond.arende_ur_trad(blandad, set())

    assert skal == ""
    assert "undrar om ni kan bygga om" in arende.text
    assert "Veckans erbjudanden" not in arende.text


def test_en_trad_utan_inkommande_meddelande_sallas_med_eget_skal():
    """En tråd vi själva inlett har ingen kund att svara.

    Skälet skiljs från maskinmail med flit: det ena är post som inte är ett
    kundärende, det andra är en tråd utan kundtext. Slås de ihop i summeringen
    går det inte att se vilket som hände.
    """
    egen = trad(meddelande("Vi hörde av oss först.", sent=True,
                           huvuden={"To": "kund@exempel.invalid"}))

    arende, skal = respond.arende_ur_trad(egen, set())

    assert arende is None
    assert skal == "ingen inkommande text i tråden"


def test_tom_brodtext_sallas_med_eget_skal():
    """Ett mail vars text vi inte kunde utvinna är VÅRT problem.

    Det ska inte se ut som maskinmail i summeringen: maskinmail betyder att
    posten inte skulle besvarats, det här betyder att den skulle det och att vi
    inte fick ut texten.
    """
    tyst = trad(meddelande(""))

    arende, skal = respond.arende_ur_trad(tyst, set())

    assert arende is None
    assert skal == "tom brödtext"


def test_arendet_bar_HASH_och_aldrig_adressen():
    """§6: loggar och vyn bär hashade avsändare, aldrig en adress."""
    kundmail = trad(meddelande(
        "Hej, jag undrar över en ombyggnad.",
        huvuden={"From": "anna.andersson@exempel.invalid"}))

    arende, _ = respond.arende_ur_trad(kundmail, set())

    assert not hasattr(arende, "avsandare")
    assert arende.avsandare_hash
    assert "anna.andersson" not in arende.avsandare_hash
    assert "exempel.invalid" not in arende.avsandare_hash


def test_regnr_plockas_ur_texten_och_gatar_uppslaget():
    """Numret avgör OM och VILKET fordon som slås upp.

    Hittas inget nummer blir `regnr` None, och kedjan skriver då ut att mailet
    inte bär något. Raden binder båda riktningarna, eftersom ett mönster som
    slutar träffa ger noll uppslag utan att något larmar.
    """
    med, _ = respond.arende_ur_trad(
        trad(meddelande("Bilen har regnr ABC12X, går den att bygga om?")), set())
    utan, _ = respond.arende_ur_trad(
        trad(meddelande("Går det att bygga om en bil till a-traktor?")), set())

    assert med.regnr == "ABC12X"
    assert utan.regnr is None


def test_amnesraden_avkodas_och_kanalen_namnges():
    """Kanalen är KONTEXT åt klassningen, och den kommer ur ämnesraden.

    En MIME-kodad ämnesrad är den form svenska tecken tar i råhuvudet, och en
    prövning mot råsträngen missar varje sådan. `kanal.namnge` ger None när
    kanalen inte går att fastställa, aldrig ett påhittat namn.
    """
    from src import kanal

    kodad = "=?UTF-8?B?" + base64.b64encode(
        "Offertförfrågan A-traktor".encode("utf-8")).decode("ascii") + "?="
    formular = trad(meddelande("Registreringsnummer: ABC12X",
                               huvuden={"Subject": kodad}))
    vanligt = trad(meddelande("Hej, en fråga.", huvuden={"Subject": "Fråga"}))

    fran_formular, _ = respond.arende_ur_trad(formular, set())
    fran_vanligt, _ = respond.arende_ur_trad(vanligt, set())

    assert fran_formular.amne == "Offertförfrågan A-traktor"
    assert fran_formular.kanal == kanal.WEBBFORMULAR
    assert fran_vanligt.kanal is None


def test_tidsstampeln_kommer_ur_internalDate():
    """Ärendets tid är kundmailets, inte körningens."""
    arende, _ = respond.arende_ur_trad(
        trad(meddelande("En fråga om ombyggnad.", internal="1757900000000")),
        set())

    assert arende.tidsstampel.startswith("2025-09-15T")


def _internal(alder: timedelta) -> str:
    """`internalDate` för ett mail `alder` före `NU`, i millisekunder."""
    return str(int((NU - alder).timestamp() * 1000))


@pytest.mark.parametrize("alder, vantat", [
    (timedelta(days=7, seconds=1), True),
    (timedelta(days=7), False),
    (timedelta(days=7, seconds=-1), False),
    (timedelta(days=1), False),
])
def test_arendet_dateras_av_det_SENASTE_kundmailet(alder, vantat):
    """Skiva 62, Lars beslut. Gränsvärdet mätt åt båda håll på det SENASTE
    mailet, med ett första mail som ensamt hade gett raden."""
    forsta = meddelande("Hej, kan ni bygga om min bil?",
                        internal=_internal(timedelta(days=30)))
    andra = meddelande("Hej igen, har ni hunnit titta?",
                       internal=_internal(alder))

    arende, _ = respond.arende_ur_trad(trad(forsta, andra), set())

    assert arende.text.startswith("Hej, kan ni bygga om")
    assert arende.besvarad is False
    assert kedja.ar_efterslapande(arende.tidsstampel, NU) is vantat


def test_senast_avgors_av_internalDate_och_inte_av_ORDNINGEN():
    """Ligger det senaste mailet först i listan daterar det ändå."""
    gammalt = meddelande("Hej, kan ni bygga om min bil?",
                         internal=_internal(timedelta(days=30)))
    nytt = meddelande("Hej igen?", internal=_internal(timedelta(days=1)))

    arende, _ = respond.arende_ur_trad(trad(nytt, gammalt), set())

    assert kedja.ar_efterslapande(arende.tidsstampel, NU) is False


def test_ett_mail_UTAN_internalDate_daterar_inte():
    """Står det sist i listan väljs ändå det mail som bär en tid."""
    daterat = meddelande("Hej, kan ni bygga om min bil?",
                         internal=_internal(timedelta(days=8)))
    odaterat = meddelande("Hej igen?", internal="")

    arende, _ = respond.arende_ur_trad(trad(daterat, odaterat), set())

    assert kedja.ar_efterslapande(arende.tidsstampel, NU) is True


def test_vart_SVAR_daterar_inte_arendet():
    """Ett senare svar från oss är inget kundmail och flyttar inte dateringen."""
    fraga = meddelande("Hej, kan ni bygga om min bil?",
                       internal=_internal(timedelta(days=8)))
    svar = meddelande(
        "Hej, det kan vi.", sent=True, internal=_internal(timedelta(days=1)),
        huvuden={"From": "info@autostockholm.se",
                 "To": "kund@exempel.invalid",
                 "In-Reply-To": "<a@exempel.invalid>",
                 "References": "<a@exempel.invalid>"})

    from src import urval

    arende, _ = respond.arende_ur_trad(trad(fraga, svar), set())

    assert arende.tidsstampel == urval.tidsstampel(fraga)


def test_urval_och_extract_daterar_samma_mail_LIKA():
    """EN definition, inte två.

    `src/extract.py` bar en egen `_tidsstampel` och `scripts/respond.py`
    behövde samma konvertering. Raden binder att extract läser urvalets
    funktion: två läsare som daterar samma mail olika är inte ett fel som syns
    i något utfall.
    """
    from src import extract, urval

    assert not hasattr(extract, "_tidsstampel")
    assert "urval.tidsstampel(" in (ROT / "src" / "extract.py").read_text(
        encoding="utf-8")
    assert urval.tidsstampel({"internalDate": "1757900000000"})
    assert urval.tidsstampel({}) == ""


# -------------------------------------------------------- DEL B: slingan


def _korning(arenden, klient, loggfil, hamta=hamta_gront, rader=None):
    """Kör slingan och fångar det den SKRIVER UT.

    `rader` finns därför att stdout är den andra vägen ett undantagsmeddelande
    kan läcka ut, och den vägen vaktades av ingenting: ett `str(fel)` i
    utskriften gick grönt genom hela sviten. Fällt av §7-granskningen av
    skiva 48.
    """
    korning = respond.Korning(tradar=len(arenden))
    respond.kor_alla(
        arenden, klient=klient, hamta=hamta, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[], skarp=True, korning=korning,
        nu=NU, loggfil=loggfil,
        skriv=(lambda *_: None) if rader is None else
              (lambda rad: rader.append(str(rad))),
    )
    return korning


def _arende(text="Hej, går ABC12X att bygga om till a-traktor?", regnr="ABC12X"):
    """Ett ärende som NÅR uppslaget.

    `regnr` måste vara satt. Utan det kastar `slag_upp` "registreringsnummer
    saknas" innan hämtningen ens anropas, och ett test som tror sig pröva ett
    källfel prövar då att numret saknas.
    """
    return Arende(text=text, regnr=regnr, avsandare_hash="hash",
                  tidsstampel="2026-09-15")


SVAR = ("fråga om a-traktorkonvertering",
        "Hej!\n\nVi återkommer med besked.\n\nVänliga hälsningar\nAuto Stockholm")


def test_ETT_KALLFEL_lamnar_en_loggrad(loggfil):
    """**ETT DRIFTAVBROTT SOM INTE LOGGAS SER UT SOM ETT ÄRENDE SOM ALDRIG KOM
    IN.** `kedja.kor` loggar inte själv, alltså är raden slingans ansvar.

    §7.1: tas `logga_kallfel`-anropet bort ur `kor_alla` blir den här raden röd.
    """
    def kraschar(_regnr):
        raise ConnectionError("källan svarar inte")

    korning = _korning([_arende()], FejkKlient(SVAR[0]), loggfil,
                       hamta=kraschar)

    rader = [json.loads(r) for r in
             loggfil.read_text(encoding="utf-8").splitlines() if r]
    assert korning.kallfel == 1
    assert korning.utkast == 0
    assert len(rader) == 1
    assert rader[0]["blev_utkast"] is False
    assert rader[0]["steg"][0]["utfall"] == "stoppade kedjan"


def test_kallfelet_bar_TYPNAMNET_och_aldrig_meddelandet_VARE_SIG_i_loggen_eller_pa_skarmen(loggfil):
    """§6: ett nätverksfel från requests bär ett REGISTRERINGSNUMMER.

    `Kallfel` byggdes för att skilja typnamnet från meddelandet just därför, och
    `src/kedja.py` skriver ut skälet: en `ConnectionError` ur requests lyder
    *"HTTPSConnectionPool(host=biluppgifter.se, ...): ... /fordon/ABC123"*.

    **TVÅ VÄGAR UT, OCH BÅDA PRÖVAS HÄR.** `logg/` är gitignorerad men lever
    kvar. Skärmen gör det inte, men den läses av en människa och kan klistras in
    var som helst, och §6 håller registreringsnummer utanför allt som inte är
    `data/` eller `logg/`.

    *Raden prövade tidigare bara loggen, medan dess docstring påstod att den
    band att meddelandet inte smugglas in på annat sätt. Uppmätt: ett `str(fel)`
    i utskriften lämnade hela sviten GRÖN. Fällt av §7-granskningen av skiva 48.*
    """
    def kraschar(_regnr):
        raise ConnectionError(
            "HTTPSConnectionPool(host=biluppgifter.se): /fordon/ABC12X")

    rader = []
    _korning([_arende()], FejkKlient(SVAR[0]), loggfil, hamta=kraschar,
             rader=rader)

    ra = loggfil.read_text(encoding="utf-8")
    assert "ConnectionError" in ra
    assert "ABC12X" not in ra

    pa_skarmen = "\n".join(rader)
    assert "ConnectionError" in pa_skarmen
    assert "ABC12X" not in pa_skarmen, (
        "slingan skrev undantagets MEDDELANDE till skärmen. Det bär ett "
        "registreringsnummer när requests kastar, och §6 förbjuder det. "
        "Skriv `fel.sort`, aldrig `fel` eller `str(fel)`."
    )
    assert "biluppgifter.se" not in pa_skarmen


def test_ett_UTKAST_raknas_och_nar_vyns_fall(loggfil):
    """Vägen slutar i vyn, och fallet ska bära förslaget."""
    korning = _korning([_arende()], FejkKlient(*SVAR), loggfil)

    assert korning.utkast == 1
    assert korning.sparrade == 0
    assert korning.per_kategori["fråga om a-traktorkonvertering"] == 1
    assert korning.per_hink["auto"] == 1
    assert len(korning.granskningsfall) == 1
    assert korning.granskningsfall[0].forslag
    assert korning.granskningsfall[0].sparr == ""


def test_ett_SPARRAT_forslag_raknas_aldrig_som_utkast(loggfil):
    """En fälld spärr är ett stopptecken, inte ett utkast med en anmärkning.

    Ett svar som påstår ett tal utan källa fälls av
    `genererat-tal-har-kalla`, och posten ska då räknas som spärrad, bära
    spärrens namn i summeringen, och nå vyn UTAN förslagstext: `rendera_
    granskning` vägrar rendera ett textfält för en spärrad post.
    """
    korning = _korning(
        [_arende()],
        FejkKlient(SVAR[0], "Hej! Ombyggnaden kostar 12345 kronor.\n\nAuto "
                            "Stockholm"),
        loggfil)

    assert korning.utkast == 0
    assert korning.sparrade == 1
    assert korning.per_sparr["genererat-tal-har-kalla"] == 1
    assert korning.granskningsfall[0].sparr == "genererat-tal-har-kalla"
    assert korning.granskningsfall[0].forslag == ""


def test_INGET_SVAR_delas_upp_pa_SINA_TVA_SKAL(loggfil):
    """Summeringen ska visa hur mycket grinden står för och hur mycket hinken.

    **ETT ODELAT TAL DÖLJER FÖRDELNINGEN.** Grinden gör `INGET SVAR` av varje
    kategori som inte är a-traktor, alltså av nästan hela en körning mot
    brevlådan, och hinken `aldrig` försvinner då i massan. Skuggläget ska kunna
    räkna maskinmailen för sig, vilket är skälet fältet `inget_svar` finns.

    Raden prövar BÅDA skälen i samma körning, så att en uppdelning som råkar
    skriva samma nyckel för båda blir röd.
    """
    # BÅDA ETIKETTERNA STÅR I `TAXONOMI`. Ett namn utanför den blir
    # `utanför listan` av pass 2:s filtrering, och då prövar raden fel skäl:
    # fixturens hinkar lägger inte det namnet i `aldrig`.
    korning = respond.Korning(tradar=2)
    for etikett in ("boka däckbyte", "inget kundärende"):
        respond.kor_alla(
            [_arende()], klient=FejkKlient(etikett, "onådd"),
            hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[],
            skarp=True, korning=korning, nu=NU, loggfil=loggfil,
            skriv=lambda *_: None)

    assert korning.inget_svar == 2
    assert korning.utkast == 0
    assert korning.per_inget_svar[kedja.SKAL_OGATAD] == 1
    assert korning.per_inget_svar[kedja.SKAL_ALDRIG] == 1
    # OCH ATT DELARNA GÅR IHOP MED HELHETEN. Två räknare som inte summerar till
    # samma tal är värre än en.
    assert sum(korning.per_inget_svar.values()) == korning.inget_svar


def test_INGET_SVAR_loggas_och_raknas_men_NAR_INTE_vyn(loggfil):
    """Lars beslut i skiva 61: vyn visar bara poster med utkast eller spärr.

    Klassningen står kvar i loggen och i summeringens räknare.
    """
    korning = respond.Korning(tradar=2)
    for klient in (FejkKlient("boka däckbyte", "onådd"), FejkKlient(*SVAR)):
        respond.kor_alla(
            [_arende()], klient=klient, hamta=hamta_gront, hinkar=HINKAR,
            taxonomi=TAXONOMI, exempel=[], skarp=True, korning=korning,
            nu=NU, loggfil=loggfil, skriv=lambda *_: None)

    rader = [json.loads(r) for r in
             loggfil.read_text(encoding="utf-8").splitlines() if r]
    assert [r["inget_svar"] for r in rader] == [True, False]
    assert rader[0]["kategori"] == "boka däckbyte"
    assert korning.inget_svar == 1
    assert korning.per_kategori["boka däckbyte"] == 1

    assert len(korning.granskningsfall) == 1
    assert not korning.granskningsfall[0].inget_svar
    assert korning.granskningsfall[0].forslag


@pytest.mark.parametrize("dagar, vantat", [(8, True), (6, False)])
def test_slingan_skickar_KORNINGENS_tidpunkt(loggfil, dagar, vantat):
    """`kor_alla` lämnar `nu` vidare, så att ett gammalt ärende får raden."""
    klient = PromptSpion(*SVAR)
    tidsstampel = (NU - timedelta(days=dagar)).isoformat()

    _korning([Arende(text="Hej, går ABC12X att bygga om till a-traktor?",
                     regnr="ABC12X", tidsstampel=tidsstampel)],
             klient, loggfil)

    assert len(klient.prompter) == 2
    assert (generera.EFTERSLAPSRAD in klient.prompter[-1]) is vantat


def test_ett_SVAR_fran_oss_i_traden_markerar_arendet_besvarat():
    """Skiva 61, §7-granskningens fynd. Ett besvarat ärende får ingen ursäkt."""
    fraga = meddelande("Hej, kan ni bygga om min bil?")
    svar = meddelande(
        "Hej, det kan vi.", sent=True,
        huvuden={"From": "info@autostockholm.se",
                 "To": "kund@exempel.invalid",
                 "In-Reply-To": "<a@exempel.invalid>",
                 "References": "<a@exempel.invalid>"})

    obesvarad, _ = respond.arende_ur_trad(trad(fraga), set())
    besvarad, _ = respond.arende_ur_trad(trad(fraga, svar), set())

    assert obesvarad.besvarad is False
    assert besvarad.besvarad is True


def test_CLI_satter_KORNINGENS_tidpunkt_och_inget_annat():
    """`_kor` skickar klockan, inte ett fast datum och inte `None`."""
    kod = vy._kod_utan_prosa(RESPOND.read_text(encoding="utf-8"))
    i_kor = kod.split("def _kor")[1]

    assert "nu = datetime . now ( timezone . utc )" in i_kor


def test_argparse_kraschar_inte_nar_SKORD_ligger_utanfor_repot(
        tmp_path, monkeypatch):
    """ROT-buggen. `--skord`s hjälptext räknade `SKORD.relative_to(ROT)` rakt
    av, ett uttryck som körs redan när tolken byggs, INNAN `--help` ens tolkas.

    `SKORD` kommer ur `sokvagar.DATA`, och `src/sokvagar.py::_krav_pa_lage`
    tillåter uttryckligen att `MAILBOT_DATA` pekar var som helst UTANFÖR
    repot: den prövningen gäller bara läget när variabeln pekar IN i det.
    Satt så, vilket är precis formen en Railway-volym har, kastade
    `relative_to` ett `ValueError` för varje anrop av `main`, `--help`
    inräknat.

    Modulen laddas om HÄR, efter att `MAILBOT_DATA` satts och `sokvagar`
    laddats om, så att den nya kopians `SKORD` faktiskt binds mot en sökväg
    utanför repot. Den redan laddade `respond` överst i filen har sin `SKORD`
    bunden mot det RIKTIGA repot och skulle inte visa bristen.
    """
    utanfor_repot = tmp_path / "utanfor-repot"
    utanfor_repot.mkdir()
    monkeypatch.setenv("MAILBOT_DATA", str(utanfor_repot))

    from src import sokvagar
    import importlib
    importlib.reload(sokvagar)
    try:
        spec = importlib.util.spec_from_file_location(
            "respond_rotbugg_under_test", RESPOND)
        modul_utanfor_repot = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = modul_utanfor_repot
        spec.loader.exec_module(modul_utanfor_repot)

        assert not modul_utanfor_repot.SKORD.is_relative_to(ROT), (
            "testet mäter inte det ROT-buggen gäller: SKORD hamnade ändå "
            "inuti repot."
        )

        with pytest.raises(SystemExit) as avslut:
            modul_utanfor_repot.main(["--help"])
        assert avslut.value.code == 0
    finally:
        sys.modules.pop("respond_rotbugg_under_test", None)
        monkeypatch.delenv("MAILBOT_DATA", raising=False)
        importlib.reload(sokvagar)


def test_VARJE_arende_lamnar_exakt_en_loggrad(loggfil):
    """Skugglägets underlag räknas ur loggen, alltså ska raderna vara lika
    många som ärendena, oavsett hur de gick."""
    def vaxlar(_regnr):
        raise ConnectionError("nere")

    korning = respond.Korning(tradar=2)
    respond.kor_alla(
        [_arende()], klient=FejkKlient(*SVAR), hamta=hamta_gront,
        hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
        korning=korning, nu=NU, loggfil=loggfil, skriv=lambda *_: None)
    respond.kor_alla(
        [_arende()], klient=FejkKlient(SVAR[0]), hamta=vaxlar,
        hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
        korning=korning, nu=NU, loggfil=loggfil, skriv=lambda *_: None)

    rader = [r for r in
             loggfil.read_text(encoding="utf-8").splitlines() if r]
    assert len(rader) == 2
    assert korning.utkast == 1
    assert korning.kallfel == 1


def test_slingan_lamnar_vidare_sin_EGNA_kallflagga():
    """`skarp` styr vad härkomstraden PÅSTÅR om vikterna i utkastet.

    Ett hårdkodat `skarp=True` i `kor_alla` hade renderat *"Uppslag mot
    biluppgifter.se"* ovanför vikter som kommer från något annat. Raden läser
    källtexten, precis som `krav_pa_sandvagsfrihet` gör, och fäller om anropet
    slutar bära argumentet.
    """
    kalla = RESPOND.read_text(encoding="utf-8")

    assert "till_granskningsfall(" in kalla
    for stycke in kalla.split("till_granskningsfall(")[1:]:
        assert "skarp=skarp" in stycke[:80], (
            "kor_alla anropar till_granskningsfall utan att lämna vidare sin "
            "egen kallflagga. En literal här gör att vyn kan påstå fel källa."
        )


def test_kallan_och_flaggan_kommer_ur_SAMMA_uttryck():
    """`bygg_kalla` returnerar båda, och CLI:t sätter aldrig flaggan själv.

    Skälet är samma defektklass som raden ovan, ett steg tidigare: en literal
    `skarp=True` i `_kor` är sann i dag och blir falsk den dag en andra källa
    tillkommer, utan att något larmar.

    **KODEN PRÖVAS, INTE PROSAN OM KODEN.** `bygg_kalla`:s egen docstring
    namnger `skarp=True` för att förklara vad som är fel, och en textsökning
    över råkällan fällde därför filen på sin egen förklaring. `vy._kod_utan_
    prosa` är repots svar på exakt den fällan, och den lånas här.

    **PRÖVNINGEN ÄR AVGRÄNSAD TILL `_kor`.** Mätt: en prövning över allt efter
    `def bygg_kalla` blev röd också när `kor_alla`:s `skarp=skarp` fälldes,
    alltså vaktade de två raderna samma sak och ett grönt utfall efter att en
    av dem fällts hade inte betytt något. §7.1.
    """
    kod = vy._kod_utan_prosa(RESPOND.read_text(encoding="utf-8"))
    i_kor = kod.split("def _kor")[1]

    assert "hamta , skarp = bygg_kalla ( arg . paus_s )" in i_kor
    assert "skarp = True" not in i_kor


# ---------------------------------------------------------- summeringen


def test_summeringen_skriver_inga_TAL_den_inte_raknat():
    """§7.2: varje tal i utdatan är räknat ur körningen.

    Raden binder de fyra Lars bad om i skiva 48: hur många som hämtades, hur de
    klassificerades, hur många som blev utkast och hur många som spärrades.
    """
    korning = respond.Korning(tradar=3)
    korning.sallade.append(("t9", "maskinmail: huvud: list-id"))
    korning.per_kategori["boka däckbyte"] = 2
    korning.per_hink["utkast"] = 2
    korning.per_sparr["tomt-svar"] = 1
    korning.utkast = 1

    rader = []
    respond.summera(korning, skriv=rader.append)
    ut = "\n".join(rader)

    assert "trådar lästa            3" in ut
    assert "sållade före kedjan     1" in ut
    assert "ärenden genom kedjan    2" in ut
    assert "utkast                  1" in ut
    assert "spärrade                1" in ut
    assert "2  boka däckbyte" in ut
    assert "tomt-svar" in ut


def test_summeringen_skriver_ingen_kundtext():
    """§6: utdatan bär räknare, kategorinamn och spärrnamn. Inget annat.

    Det är skälet att modulen inte behöver någon maskering: den har ingenting
    att maskera. Den dagen ett utkast skrivs ut behövs `prov_stod.maska_svaret`,
    och den här raden fäller om det sker utan den.
    """
    korning = respond.Korning(tradar=1)
    korning.granskningsfall.append(kedja.till_granskningsfall(
        _arende("Hej, jag heter Anna och har en bil med regnr ABC12X."),
        Kedjeutfall(kategori="oklart", hink="utkast",
                    utkast="Hej Anna!\n\nVi hör av oss.",
                    steg=(Steg("klassificering", "oklart"),)),
        skarp=True))

    rader = []
    respond.summera(korning, skriv=rader.append)
    ut = "\n".join(rader)

    assert "Anna" not in ut
    assert "ABC12X" not in ut


# ------------------------------------------------- REGNRFILTRET, DEL 1


class _FejkDraftsRa:
    """Den RÅA `Utkastjanst`-tjänsten. Spelar in `create` och `delete`.

    Samma form som `tests/test_gmailutkast.py::FejkRa`, byggd lokalt i
    stället för importerad: den här filens fejkar är trådar och meddelanden,
    inte Gmail-anropslagret, och en cross-importerad fejk för EN sak hade
    knutit ihop två testfilers underhåll i onödan.
    """

    def __init__(self):
        self.logg: list[tuple[str, dict]] = []

    def users(self):
        return self

    def drafts(self):
        return self

    def create(self, **kw):
        self.logg.append(("create", kw))
        trad_id = kw["body"]["message"]["threadId"]
        svar = {"id": f"d-{trad_id}",
               "message": {"id": f"m-{trad_id}", "threadId": trad_id}}

        class Anrop:
            def execute(self_):
                return svar
        return Anrop()

    def delete(self, **kw):
        self.logg.append(("delete", kw))

        class Anrop:
            def execute(self_):
                return {}
        return Anrop()


def _regnr_gmail(aldre_trad_id: str, aldre_meddelande: dict) -> inkorg.Lastjanst:
    fejk = FejkGmail(
        sidor={None: {"threads": [{"id": aldre_trad_id}],
                      "nextPageToken": None}},
        tradar={aldre_trad_id: {"id": aldre_trad_id,
                                "messages": [aldre_meddelande]}},
    )
    return inkorg.Lastjanst(fejk)


def test_respond_injicerar_regnr_historik(tmp_path, monkeypatch):
    """UPPDRAG 2026-09-25 DEL 1, §7-granskningsfynd: `kedja._regnr_historik_
    ingen_kontroll`s docstring citerar det här namnet.

    Slutet på slutet: `kor_alla` injicerar en fungerande `regnr_historik` i
    `kedja.kor` bara genom att få en `regnr_historik_tjanst`. Beviset är att
    en ÄLDRE trådss obesickade utkast, som bara syns via en riktig Gmail-
    sökning (fejkad här), faktiskt hittas och tas bort när den nya
    förfrågan om samma bil passerar spärrarna.
    """
    peka_om_katalogerna(monkeypatch, tmp_path)
    omdomesfil = tmp_path / "logg" / "omdomen.jsonl"

    # DEN ÄLDRE TRÅDEN har redan ett obesickat bot-utkast.
    vy.spara_gmailutkast(
        vy.Fall(etikett="fråga om a-traktorkonvertering", kalla="kedjan",
               text="", tidsstampel="", avsandare_hash=""),
        "t-aldre", "skapat", "m-aldre", "d-aldre", omdomesfil=omdomesfil,
    )
    aldre_meddelande = meddelande(
        "Fråga om ABC123", internal=str(int((NU - timedelta(days=2))
                                            .timestamp() * 1000)))
    regnr_historik_tjanst = _regnr_gmail("t-aldre", aldre_meddelande)

    utkast_ra = _FejkDraftsRa()
    ta_bort_utkast_tjanst = gmailutkast.Utkastjanst(utkast_ra)
    skapa_utkast = gmailutkast.utkastskapare(tjanst=ta_bort_utkast_tjanst)

    arende = Arende(text="Hej, ny fråga om ABC123", regnr="ABC123")
    svarsvag = vy.Svarsvag(trad_id="t-eget", meddelande_id="<kund-1@x>",
                           mottagare="kund@exempel.invalid", amne="Fråga")
    korning = respond.Korning(tradar=1)

    respond.kor_alla(
        [arende],
        klient=FejkKlient("fråga om a-traktorkonvertering",
                          "Hej, vi kan bygga om den."),
        hamta=hamta_gront, hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[],
        skarp=True, korning=korning, nu=NU,
        loggfil=tmp_path / "logg" / "beslut.jsonl",
        svarsvagar=[svarsvag], skapa_utkast=skapa_utkast,
        omdomesfil=omdomesfil,
        regnr_historik_tjanst=regnr_historik_tjanst,
        ta_bort_utkast_tjanst=ta_bort_utkast_tjanst,
    )

    assert korning.gmail_skapade == 1
    assert korning.regnrfilter_borttagna == 1
    assert ("delete", {"userId": "me", "id": "d-aldre"}) in utkast_ra.logg
    rader = [json.loads(r) for r in
            omdomesfil.read_text(encoding="utf-8").splitlines()]
    assert rader[-1] == {**rader[-1], "trad_id": "t-aldre",
                         "utfall": vy.BORTTAGET, "etikett": "regnrfilter"}


def test_gmailutkast_hoppar_over_borttagning_utan_utkast_tjanst(
        tmp_path, monkeypatch):
    """Ingen `--gmailutkast` byggd `ta_bort_utkast_tjanst` finns då: den nya
    utkasttjänsten kraschar inte, den bara låter de äldre utkasten stå kvar."""
    peka_om_katalogerna(monkeypatch, tmp_path)
    rader = []
    spion_poster = []

    def spion(post):
        spion_poster.append(post)
        return gmailutkast.UtkastResultat(meddelande_id="m-1",
                                          utkast_id="d-1")

    post = kedja.till_granskningsfall(
        _arende("Hej ABC123"),
        Kedjeutfall(kategori="fråga om a-traktorkonvertering", hink="utkast",
                    utkast="Hej!\n\nVi kan bygga om den.",
                    steg=(Steg("klassificering", "x"),),
                    aldre_utkast_att_ta_bort=("t-aldre",)),
        skarp=True,
        svarsvag=vy.Svarsvag(trad_id="t-eget", meddelande_id="<kund-1@x>",
                             mottagare="kund@exempel.invalid", amne="Fråga"))
    korning = respond.Korning(tradar=1)

    respond._gmailutkast(
        post, Arende(text="Hej ABC123", regnr="ABC123"), spion,
        tmp_path / "logg" / "omdomen.jsonl", korning, rader.append,
        aldre_utkast_att_ta_bort=("t-aldre",), ta_bort_utkast_tjanst=None,
    )

    assert korning.gmail_skapade == 1
    assert korning.regnrfilter_borttagna == 0
