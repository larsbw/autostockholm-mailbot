#!/usr/bin/env python3
"""SKUGGLÄGE: en slinga över inkommande mail. Ett utkast per ärende. INGEN SÄNDNING.

    .venv/bin/python scripts/respond.py --inkorg --antal 20
    .venv/bin/python scripts/respond.py --tradar data/tradar_obesvarade.jsonl
    .venv/bin/python scripts/respond.py --vy

`docs/roadmap.md` fas 6 namnger vad som saknades: hämtningen av inkommande mail
ur brevlådan och en slinga över dem. Den här filen är båda.

*Här stod fasens formulering som ett ordagrant citat i presens. Samma skiva
rättade fasen, alltså citerade raden en text som inte längre fanns, och
utelämnade dessutom den klausul som namngav kopplingen till `src/mine.py`.
Fällt av §7-granskningen av skiva 48.*

TVÅ KÄLLOR, OCH INGEN AV DEM ÄR FÖRVALD.

  `--inkorg`   dagens inkommande mail ur info@autostockholm.se, genom
               `src/inkorg.py`. Kräver `token-las.json`.
  `--tradar`   en skördad `tradar.jsonl`. Rör varken nät eller brevlåda.

Att ingendera är förval är samma skäl som `kedja.kor` anger för sitt `hamta`: en
tyst standardkälla i en sändvägsmodul är vad §10 finns för att hindra, och det
skälet väger tyngre när källan är en brevlåda.

**INGEN SÄNDNING, OCH INGEN `--send`.** Vägen slutar i vyn, precis som
`scripts/kedja-prov.py`. `test_respond_har_INGEN_send_flagga` läser den här
filens källtext och fäller om en sådan flagga tillkommer.

SPÄRREN ÄR INTE LÄNGRE "INGEN VÄG FINNS"
----------------------------------------

Med `--inkorg` drar den här filen in `googleapiclient`, alltså går
`vyn-har-ingen-sandvag` i sin ursprungliga form inte att hålla. Lars §10-beslut
i skiva 48 var FYRA LAGER i stället, och bara det första är Googles:

  1  SCOPET        `src/auth.py::LASSCOPES`, gmail.readonly och inget annat.
                   Sändförmågan FINNS INTE i credentialen. Det enda lagret som
                   inte kan brytas av en rad i vår kod.
  2  TJÄNSTEN      `src/inkorg.py::Lastjanst`. Bara läsvägarna går igenom.
  3  IMPORTLAGRET  `vy.GMAILBARANDE_MODULER`, tre namngivna moduler. En fjärde
                   som drar in `googleapiclient` fäller spärren.
  4  KÄLLTEXTEN    `FORBJUDET_MONSTER` över hela grafen, OFÖRÄNDRAT.

Lager 3 och 4 körs av `vy.krav_pa_sandvagsfrihet("scripts.respond", tillatna=...)`
först i `_kor`, alltså före varje läsning, varje modellanrop och varje uppslag.
Lager 1 och 2 prövas när tjänsten byggs.

**MED `--tradar` GÄLLER FORTFARANDE DEN STARKA FORMEN**: ingen tjänst byggs,
ingen credential läses, och ingen rad i den vägen rör en brevlåda.

§6. Körningen SKRIVER ALDRIG UT KUNDTEXT ELLER UTKAST. Den skriver räknare,
kategorinamn och spärrnamn. Texten läses i vyn, som är byggd för det och som
skriver den bara till gitignorerade kataloger. Det är också skälet att den här
filen inte behöver någon maskering: den har ingenting att maskera.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import yaml  # noqa: E402

from src import (biluppgifter, extract, generera, inkorg,  # noqa: E402
                 kanal, kategorisera, kedja, klassa_maskin, maskera,
                 sokvagar, urval, vy)
from src.kedja import Arende, Kallfel  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
HINKFIL = ROT / "config" / "kategorier.yaml"

# Paus mellan två skarpa uppslag mot biluppgifter.se. Talet är VALT och inte
# mätt: det finns ingen publicerad gräns att läsa. `scripts/kedja-prov.py` bär
# samma val av samma skäl, och de två är inte kopplade: byter Lars takt måste
# båda ändras. Se `docs/beslutslogg.md` #72.
PAUS_S = 1.0

# Hur många ärenden en körning tar när inget annat sägs.
#
# **FÖRVALET ÄR ETT TAK OCH INTE EN AMBITION.** Utan ett förval kostar ett
# glömt `--antal` ett modellanrop per ärende i hela filen och HÖGST ett uppslag
# mot biluppgifter.se; uppmätt mot `data/tradar_obesvarade.jsonl` blir det 665
# ärenden. Uppslaget gatas av `kedja.A_TRAKTORKATEGORIER` i `kedja.kor`, alltså
# slås bara a-traktorärendena upp.
#
# *Här stod "ett modellanrop OCH en skarp begäran per ärende", vilket räknade
# ett uppslag för varje ärende oavsett kategori. Fällt av §7-granskningen av
# skiva 48.*
# Det är samma avvägning `scripts/kedja-prov.py` gör när den kräver `--kor`: en
# dyr körning ska vara ett uttryckligt val. Talet är VALT och inte mätt, och är
# storleken på de körningar repot redan gör.
#
# `--antal 0` betyder alla, och den formen är lika uttrycklig som ett tal.
ANTAL_FORVAL = 20

# Vart `--inkorg` skriver de hämtade trådarna. **UNDER `data/`, som är
# gitignorerad**: filen bär kundtext, adresser och ämnesrader (§6). Namnet
# skiljer sig från `data/tradar.jsonl` och `data/tradar_obesvarade.jsonl`, som är
# miningens skördar: en skuggkörning får inte skriva över materialet paren och
# taxonomin vilar på.
#
# **FILEN ÄR ARBETSMATERIAL FÖR EN KÖRNING och skrivs över varje gång.** Den bär
# bara de fält kedjan läser: `src/inkorg.py::gallra_trad` gallrar före
# skrivningen, alltså når varken bilagor, `snippet` eller `Bcc`-värden disken.
# Lars beslut i skiva 54, se `docs/beslutslogg.md` #120.
#
# *Här stod "rå kundtext". Det slutade vara sant med gallringen. Texten är
# kundens, kroppen är hans base64, men tråden är inte längre Googles svar.*
SKORD = sokvagar.DATA / "inkorg-dagens.jsonl"


def bygg_kalla(paus_s: float = PAUS_S):
    """`(hämtning, skarp)`. **BÅDA UR SAMMA UTTRYCK, och det är hela poängen.**

    `skarp` styr vad härkomstraden i vyn påstår om vikterna i utkastet, och den
    får aldrig sättas på ett annat ställe än källan väljs. `kedja-prov.py` har
    två källor och en flagga, och `test_provskriptet_lamnar_vidare_sin_EGNA_
    kallflagga` finns därför att ett hårdkodat `skarp=True` renderar *"Uppslag
    mot biluppgifter.se"* ovanför vikter från en fixtur. Här finns bara en
    källa, och den här funktionen är den enda plats som behöver ändras den dag
    det blir två.

    `biluppgifter_hamtning` äger returkontraktet: `dict` när sidan gick att
    läsa, `None` när fordonet inte finns, och `Hamtningsfel` när källan inte
    svarade. Det tredje blir `Kallfel` i kedjan och stoppar ärendet.

    **PAUSEN ÄR INTE KOSMETIK.** Tjugo begäranden i följd mot en sida som inte
    är vår är något annat än en.
    """
    hamtare = biluppgifter.biluppgifter_hamtning()

    def hamta(regnr: str) -> dict | None:
        time.sleep(paus_s)
        return hamtare(regnr)

    return hamta, True


# ------------------------------------------------------- DEL A: ärenden ur trådar


def _forsta_kundmeddelandet(trad: dict) -> dict | None:
    """Trådens första INKOMMANDE meddelande, eller None.

    **SAMMA MEDDELANDE SOM MASKINBEDÖMNINGEN PRÖVAR.**
    `klassa_maskin.tradens_skal` går igenom trådens meddelanden och stannar på
    det första `urval.ar_kundmeddelande` säger ja till. Väljer den här
    funktionen ett annat meddelande bedöms en tråd på ett mail och besvaras på
    ett annat, och en tråd som friats som kund kan då svaras på en
    utskicksnotis. Kriteriet är därför ordagrant detsamma, och
    `test_arendet_byggs_ur_SAMMA_meddelande_som_maskinbedomningen` binder det.
    """
    for meddelande in trad.get("messages", []) or []:
        if urval.ar_kundmeddelande(meddelande):
            return meddelande
    return None


def _regnr_i(text: str) -> str | None:
    """Första registreringsnumret i texten, om något.

    Återanvänder `maskera.REGNR` i stället för ett eget mönster, samma val som
    `scripts/kedja-prov.py` gör och av samma skäl: ett mönster lånat från en
    maskering är för SNÄVT, och ett missat nummer ger ett misslyckat uppslag,
    vilket härkomstraden i vyn skriver ut per post.

    **ÄMNESRADEN GENOMSÖKS INTE.** Webbformuläret bär numret i BRÖDTEXTEN, och
    formuläret är den kanal vi vet något om. En kund som skriver numret bara i
    ämnesraden får inget uppslag, och vyn säger då *"MAILET BÄR INGET
    REGISTRERINGSNUMMER"*. Det är en känd begränsning och ingen mätning.

    *Här stod att formuläret är den kanal numret OFTAST kommer genom. Uppmätt
    över båda skördarna är det falskt: av ärendena med regnr i brödtexten kommer
    77 av 290 via formuläret, och i `data/tradar_obesvarade.jsonl` noll av 665
    ärenden. Meningen var motiveringen till att ämnesraden inte genomsöks, alltså
    vilade begränsningen på ett tal som inte höll. Fällt av §7-granskningen av
    skiva 48.*
    """
    traff = maskera.REGNR.search(text)
    return traff.group(0) if traff else None


def arende_ur_trad(trad: dict, domaner: set[str]) -> tuple[Arende | None, str]:
    """`(Arende, "")` för en tråd som ska besvaras, annars `(None, skäl)`.

    Skälet returneras i stället för ett sant eller falskt, av samma skäl som
    `klassa_maskin.skal_maskinmail` anger: en sållning ska gå att granska post
    för post utan att gissa vilket villkor som fällde.

    **TRE SÅLLNINGAR, och de betyder olika saker.** Maskinmail är post som inte
    är ett kundärende alls. En tråd utan inkommande meddelande är en tråd vi
    själva inlett. Tom brödtext är ett mail vars text vi inte kunde utvinna,
    alltså VÅRT problem, och det ska inte se ut som de två andra i summeringen.

    §6: `Arende` bär `avsandare_hash` och aldrig en adress. Fältnamnet är
    kedjans, och skälet står i dess docstring.
    """
    skal = klassa_maskin.tradens_skal(trad, domaner)
    if skal:
        return None, f"maskinmail: {skal}"

    meddelande = _forsta_kundmeddelandet(trad)
    if meddelande is None:
        return None, "ingen inkommande text i tråden"

    text = urval.brodtext(meddelande)
    if not text.strip():
        return None, "tom brödtext"

    return Arende(
        text=text,
        amne=kanal.amnesrad(meddelande),
        # KANALEN ÄR KONTEXT, ALDRIG GRUND. `kanal.namnge` ger None när den inte
        # går att fastställa, aldrig `e-post` som slasktratt, och kedjan lämnar
        # värdet vidare till klassningen utan att tolka det.
        kanal=kanal.namnge(meddelande),
        regnr=_regnr_i(text),
        avsandare_hash=urval.hasha(urval.kundadress(meddelande)),
        tidsstampel=urval.tidsstampel(meddelande),
        # SKIVA 61. Ett svar från oss i tråden stänger av eftersläpsraden.
        # Samma kriterium som paren byggs på, `urval.ar_gmail_svar`.
        besvarad=any(urval.ar_gmail_svar(m)
                     for m in trad.get("messages", []) or []),
    ), ""


# ----------------------------------------------------------- DEL B: slingan


@dataclass
class Korning:
    """Vad en körning gjorde. Bär räknare och fall, ALDRIG kundtext.

    `granskningsfall` bär däremot både kundtext och utkast, eftersom det ÄR
    vyns material. Det som lägger den listan under `data/` är `vy.GRANSKNINGSFALL`
    och inte spärren: `krav_pa_skrivbar_sokvag` binder `data/` ELLER `logg/`,
    alltså att skrivningen sker i en gitignorerad katalog och inget mer.

    *Här stod att spärren binder att filen hamnar under `data/`. Fällt av
    §7-granskningen av skiva 48.*

    **`sallade` BÄR TRÅD-ID OCH SKÄL, inte adressen eller ämnesraden.** Ett
    tråd-ID är en ogenomskinlig Gmail-sträng och pekar inte ut en person för
    den som läser utdatan.

    Två av de tre skälen är den här modulens egna fasta strängar. Det tredje
    byggs av `klassa_maskin.skal_maskinmail`, och det är DÄR egenskapen ska
    kontrolleras den dag den slutar hålla: den funktionen interpolerar ett
    huvudnamn ur `MASKINHUVUDEN` eller ett värde prövat mot `MASKINPRECEDENCE`,
    alltså fasta mängder och ingen kundtext.

    *Här stod att skälet är en av modulens EGNA fasta strängar, i singular om
    alla tre. Fällt av §7-granskningen av skiva 48.*
    """

    tradar: int = 0
    sallade: list[tuple[str, str]] = field(default_factory=list)
    kallfel: int = 0
    utkast: int = 0
    # SKIVA 49 DEL B. Ärenden kedjan inte skrev något svar på, oavsett vilket av
    # de två skälen. Före ändringen gick de genom generatorn och räknades i
    # `utkast`: kedjan producerade ett utkast för varje kategori, också de i
    # `aldrig`. Avläst i `logg/beslut.jsonl`, de sju raderna 2026-09-15T10:15
    # och 10:16 UTC: `blev_utkast` sant och `sparr` null i samtliga sju.
    #
    # *Här stod att talet räknar ärenden vars kategori står i hinken `aldrig`.
    # Sant i skiva 49, falskt sedan skiva 51 DEL B lade grinden: talet räknar
    # båda skälen, och `per_inget_svar` nedan är det som skiljer dem åt.*
    inget_svar: int = 0
    # SKIVA 51 DEL B. SAMMA TAL UPPDELAT PÅ DE TVÅ SKÄLEN, formen lånad från
    # `per_sparr`. Grinden gör `INGET SVAR` av varje kategori som inte är
    # a-traktor, alltså av nästan hela körningen, och ett odelat tal hade då
    # dolt hur många av dem hinken `aldrig` stod för.
    per_inget_svar: Counter = field(default_factory=Counter)
    per_kategori: Counter = field(default_factory=Counter)
    per_hink: Counter = field(default_factory=Counter)
    per_sparr: Counter = field(default_factory=Counter)
    granskningsfall: list = field(default_factory=list)

    @property
    def arenden(self) -> int:
        """Ärenden som nådde kedjan, källfelen inräknade.

        **HÄRLETT OCH INTE RÄKNAT, så att `trådar = sållade + ärenden` håller av
        konstruktion.** Ett eget räknarfält hade kunnat gå isär med de två
        andra, och en summering där leden inte går ihop är värre än ingen.

        Garantin är `_kor`:s och inte den här egenskapens: den räknar upp
        `tradar` en gång per tråd och lägger EN post i `sallade` för varje tråd
        som inte blev ett ärende. En anropare som fyller fälten själv, till
        exempel ett test, kan få egenskapen att säga något annat.
        """
        return self.tradar - len(self.sallade)

    @property
    def sparrade(self) -> int:
        return sum(self.per_sparr.values())


def kor_alla(
    arenden: list[Arende],
    *,
    klient,
    hamta,
    hinkar: dict,
    taxonomi: list[str],
    exempel: list[dict],
    skarp: bool,
    korning: Korning,
    nu: datetime,
    loggfil: Path | None = None,
    skriv=print,
) -> Korning:
    """Kedjan för varje ärende. Loggar EN rad per ärende, oavsett utfall.

    **ANROPARENS ANSVAR ÄR ATT EN RAD SKRIVS FÖR VARJE UTFALL**, källfelet
    inräknat. `src/kedja.py` säger det rakt ut: `kor` loggar inte själv, så att
    den går att köra i ett test utan att röra disken. Ett driftavbrott som inte
    lämnar en rad ser i skuggläget ut som ett ärende som aldrig kom in, och
    `test_ETT_KALLFEL_lamnar_en_loggrad` binder att det gör det.

    `skarp` lämnas VIDARE till `till_granskningsfall` och är aldrig en literal
    här. Ett hårdkodat `skarp=True` hade renderat *"Uppslag mot
    biluppgifter.se"* ovanför vikter från en annan källa, vilket är den defekt
    `test_provskriptet_lamnar_vidare_sin_EGNA_kallflagga` fäller för
    `kedja-prov.py`.

    **INGEN KUNDTEXT OCH INGET UTKAST SKRIVS UT**, se modulens §6-stycke.

    `nu` är körningens tidpunkt, EN för hela körningen, och har inget förval.
    Ärendets ålder räknas från den, se `kedja.ar_efterslapande`. Skiva 61.

    `loggfil` slås upp VID ANROPET och inte i signaturen. Ett förval i
    signaturen binds när modulen laddas, alltså före varje test som pekar om
    loggen, och `docs/incidentlogg.md` I1 bär precis den defekten. Formen är
    lånad ur `src/vy.py::_rot`.
    """
    loggfil = kedja.BESLUTSLOGG if loggfil is None else loggfil

    for nummer, arende in enumerate(arenden, start=1):
        try:
            utfall = kedja.kor(
                arende, klient=klient, hamta=hamta, hinkar=hinkar,
                taxonomi=taxonomi, exempel=exempel, nu=nu,
            )
        except Kallfel as fel:
            korning.kallfel += 1
            kedja.logga_kallfel(arende, fel, loggfil=loggfil)
            # `fel.sort` OCH ALDRIG `str(fel)`: meddelandet byggs av hämtningen
            # och bär ett registreringsnummer när requests kastar. Se `Kallfel`.
            skriv(f"{nummer:>4}  KÄLLFEL {fel.sort}, kedjan stoppad")
            continue

        kedja.logga_beslut(arende, utfall, loggfil=loggfil)
        korning.per_kategori[utfall.kategori] += 1
        korning.per_hink[utfall.hink] += 1
        # **EN POST UTAN SVAR NÅR INTE VYN, Lars beslut i skiva 61.** Vyn är en
        # granskningssida, och en post utan utkast har ingenting att granska.
        # Materialet skiva 49 ville bevara, kategori, hink och skäl per ärende,
        # står i `logg/beslut.jsonl` via raden ovan.
        if not utfall.inget_svar:
            korning.granskningsfall.append(
                kedja.till_granskningsfall(arende, utfall, skarp=skarp))

        # TRE GRENAR, EN PER UTFALL I `Kedjeutfall`. Grenen är NY och ersätter
        # ingen: före skiva 49 fanns inget tredje utfall, och ett ärende i
        # `aldrig` föll i `blev_utkast`-grenen med ett färdigt utkast.
        #
        # **SEDAN SKIVA 51 ÄR DEN HÄR GRENEN DEN BREDA.** Grinden i `kedja.kor`
        # släpper bara fram a-traktor, alltså går varje annan kategori hit.
        # `utfall.inget_svar_skal` säger vilket av de två skälen det var.
        #
        # **UTAN EN EGEN GREN HADE DEN FALLIT I `else`**, och då hade varje
        # maskinmail räknats som spärrat med `None` som spärrnamn. Det är
        # motivet till grenen och inte en beskrivning av vad koden gjorde.
        if utfall.inget_svar:
            korning.inget_svar += 1
            korning.per_inget_svar[utfall.inget_svar_skal] += 1
            skriv(f"{nummer:>4}  INGET SVAR  {utfall.kategori}  "
                  f"[{utfall.hink}]  {utfall.inget_svar_skal}")
        elif utfall.blev_utkast:
            korning.utkast += 1
            skriv(f"{nummer:>4}  UTKAST   {utfall.kategori}  [{utfall.hink}]")
        else:
            korning.per_sparr[utfall.sparr] += 1
            skriv(f"{nummer:>4}  SPÄRRAD  {utfall.kategori}  "
                  f"[{utfall.hink}]  {utfall.sparr}")

    return korning


def summera(korning: Korning, skriv=print) -> None:
    """Summeringen Lars läser. Varje tal är RÄKNAT ur körningen.

    §7.2: inga arbetsförloppstal, alltså ingenting om hur många varv eller
    rättelser något tog. Talen här är antal trådar, ärenden och utfall.

    **TVÅ AV DEM GÅR INTE ATT RÄKNA OM UR `logg/beslut.jsonl`.** En sållad tråd
    når aldrig kedjan och lämnar därför ingen loggrad, alltså finns varken
    `trådar lästa` eller `sållade före kedjan` i loggen. Uppmätt mot
    `data/tradar_obesvarade.jsonl`: 1604 trådar ger 665 loggrader, och de 939
    sållade syns ingenstans. Resten, alltså källfel, utkast, spärrade och
    fördelningen per kategori och hink, går att räkna om.

    *Här stod att talen går att räkna om ur loggen, utan förbehåll. Summeringen
    är skugglägets underlag, och meningen anvisade Lars att verifiera den mot en
    fil som saknar två av talen. Fällt av §7-granskningen av skiva 48.*
    """
    skriv("=" * 72)
    skriv("SUMMERING")
    skriv(f"  trådar lästa            {korning.tradar}")
    skriv(f"  sållade före kedjan     {len(korning.sallade)}")
    for skal, antal in sorted(Counter(s for _, s in korning.sallade).items()):
        skriv(f"      {skal:<30} {antal}")
    skriv(f"  ärenden genom kedjan    {korning.arenden}")
    skriv(f"  källfel                 {korning.kallfel}")
    skriv(f"  utkast                  {korning.utkast}")
    skriv(f"  inget svar              {korning.inget_svar}")
    for skal, antal in sorted(korning.per_inget_svar.items()):
        skriv(f"      {skal:<30} {antal}")
    skriv(f"  spärrade                {korning.sparrade}")
    for sparr, antal in sorted(korning.per_sparr.items()):
        skriv(f"      {sparr:<30} {antal}")

    skriv("\nKLASSIFICERING")
    for etikett, antal in sorted(korning.per_kategori.items(),
                                 key=lambda p: (-p[1], p[0])):
        skriv(f"  {antal:>4}  {etikett}")

    skriv("\nHINK")
    for hink, antal in sorted(korning.per_hink.items()):
        skriv(f"  {antal:>4}  {hink}")


# --------------------------------------------------------------- DEL C: CLI


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description="Skuggläge. Skickar ingenting.")
    tolk.add_argument("--inkorg", action="store_true",
                      help="dagens inkommande mail ur info@autostockholm.se. "
                           "Läser med token-las.json, som inte kan skicka.")
    tolk.add_argument("--tradar", type=Path, default=None,
                      help="jsonl med Gmail-trådar, en per rad. Rör varken nät "
                           "eller brevlåda.")
    tolk.add_argument("--skord", type=Path, default=SKORD,
                      help=f"fil hämtningen skriver trådarna till, förval "
                           f"{SKORD.relative_to(ROT)}. Skrivs över varje "
                           "körning, bär kundtext, alltså under data/.")
    tolk.add_argument("--antal", type=int, default=ANTAL_FORVAL,
                      help=f"ta högst så många ärenden, förval {ANTAL_FORVAL}. "
                           "0 betyder alla, och kostar ett modellanrop plus ett "
                           "uppslag per ärende.")
    tolk.add_argument("--vy", action="store_true",
                      help="starta vyn efteråt")
    tolk.add_argument("--port", type=int, default=8765)
    arg = tolk.parse_args(argv)

    if arg.inkorg and arg.tradar is not None:
        tolk.error("--inkorg och --tradar är två källor. Välj en.")

    if not arg.inkorg and arg.tradar is None:
        if arg.vy:
            return _bara_vyn(arg)
        tolk.error("ange --inkorg för dagens mail eller --tradar för en skörd, "
                   "eller --vy för att läsa de sparade fallen.")

    return _kor(arg)


def _bara_vyn(arg) -> int:
    """Vyn på det som redan är sparat. Inga API-anrop, ingen nättrafik."""
    fall = vy.las_granskningsfall()
    if not fall:
        print(f"inga sparade fall i {vy.GRANSKNINGSFALL.relative_to(ROT)}.")
        return 1

    print(f"{len(fall)} sparade fall, inga nya anrop.")
    _starta_vyn(arg.port, fall)
    return 0


def _starta_vyn(port: int, fall: list) -> None:
    server = vy.starta(port, fall=[], granskning=fall)
    print(f"\nvyn kör på http://127.0.0.1:{port}/granskning/0")
    print("avsluta med ctrl-c")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("")
    finally:
        server.server_close()


def _kallan(arg) -> tuple[str, list[dict]]:
    """`(vad källan var, trådarna)`. **BÅDA UR SAMMA UTTRYCK.**

    Texten skrivs ut ovanför utkasten, alltså är den ett påstående om var
    materialet kom ifrån, och den får inte kunna säga fel. Samma skäl som
    `bygg_kalla` anger för sin `skarp`, och samma skäl `kedja.uppslagskalla`
    finns för.

    **`--inkorg` BYGGER TJÄNSTEN HÄR**, alltså prövas lager 1 och 2 först när
    den vägen faktiskt väljs. En `--tradar`-körning läser ingen credential och
    rör ingen brevlåda.
    """
    if not arg.inkorg:
        return f"skörden {arg.tradar}", list(extract.las_tradar(arg.tradar))

    # LAGER 1 OCH 2. `las_tjanst` returnerar en tjänst som varken kan skicka
    # eller ändra, byggd ur en credential som bara bär gmail.readonly.
    tjanst = inkorg.las_tjanst()
    print("SPÄRR lager 1: credentialen bär "
          f"{' '.join(inkorg.LASSCOPES)} och kan inte skicka.")
    print("SPÄRR lager 2: tjänsten släpper bara igenom läsvägarna.")

    tradar, forbrukning = inkorg.dagens_tradar(tjanst, utfil=arg.skord)
    print(f"Gmail: {forbrukning.tradar} trådar hämtade, "
          f"{forbrukning.anrop} anrop, {forbrukning.enheter} kvotenheter.")
    return (f"info@autostockholm.se, dygnet i {inkorg.TIDSZON}, "
            f"fråga {inkorg.FRAGA!r}"), tradar


def _kor(arg) -> int:
    if arg.tradar is not None and not arg.tradar.exists():
        print(f"saknas: {arg.tradar}")
        return 1

    # LAGER 3 OCH 4 FÖRE VARJE LÄSNING, varje modellanrop och varje uppslag.
    # Se modulens docstring för vad de fyra lagren är. Lager 1 och 2 prövas
    # längre ned, när tjänsten byggs, eftersom `--tradar` inte bygger någon.
    vy.krav_pa_sandvagsfrihet("scripts.respond", tillatna=vy.UNDANTAGBARA)
    print("SPÄRR lager 3: gmail nås bara via "
          f"{', '.join(sorted(vy.GMAILBARANDE_MODULER))}.")
    print("SPÄRR lager 4: ingen modul i grafen bär ett sändanrop.")

    hinkar = yaml.safe_load(HINKFIL.read_text(encoding="utf-8"))
    taxonomi = json.loads(kedja.TAXONOMIFIL.read_text(encoding="utf-8"))
    exempel = generera.las_exempel()
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)

    kalltext, tradar = _kallan(arg)

    korning = Korning()
    arenden: list[Arende] = []
    for trad in tradar:
        korning.tradar += 1
        arende, skal = arende_ur_trad(trad, domaner)
        if arende is None:
            korning.sallade.append((trad.get("id", ""), skal))
            continue
        arenden.append(arende)
        if arg.antal and len(arenden) >= arg.antal:
            break

    print(f"KÄLLA: {kalltext}")
    print(f"få-exempel: {len(exempel)}   taxonomi: {len(taxonomi)} kategorier"
          f"   ärenden: {len(arenden)}")
    # KOSTNADEN SKRIVS UT FÖRE och inte efter. Talen är avlästa ur urvalet som
    # just gjordes, inte uppskattade.
    print(f"KOSTNAD: {len(arenden)} modellanrop och högst {len(arenden)} "
          f"uppslag mot biluppgifter.se, {PAUS_S} s mellan anropen.")
    print("UPPSLAGET ÄR SKARPT. INGEN SÄNDNING.\n")

    if not arenden:
        # **NOLL ÄRENDEN ÄR INGET FEL, och returkoden säger det.** Ett dygn där
        # all inkommande post var maskinmail är en körning som gjorde precis vad
        # den skulle: hämtade, sållade och fann ingenting att svara på.
        #
        # **RADEN ÄNDRADES I SKIVA 54 FRÅN `return 1`, och skälet är DEL B.**
        # `scripts/dagligen.py` skriver `"lyckades": kod == 0` i
        # `logg/korningar.jsonl`, och `vy.korningsrad` läser den flaggan. Med en
        # etta här loggades en lugn helg som ett misslyckande, och vyn larmade
        # sedan rött med texten *"minst en körning har uteblivit eller fallit"*
        # över utkast som var i sin ordning.
        #
        # Det är inte bara ett falskt besked. Raden ÄR larmet för den döda
        # slingan, och ett larm som ropar varg slutar läsas innan det ropar på
        # riktigt. Fällt av §7-granskningen av skiva 54.
        #
        # Ett verkligt fel returnerar fortfarande 1: en `--tradar` som pekar på
        # en fil som inte finns, och varje undantag som når `main`.
        print("inga ärenden att köra.")
        return 0

    hamta, skarp = bygg_kalla()
    kor_alla(
        arenden,
        klient=kategorisera.bygg_klient(),
        hamta=hamta,
        hinkar=hinkar,
        taxonomi=taxonomi,
        exempel=exempel,
        skarp=skarp,
        korning=korning,
        nu=datetime.now(timezone.utc),
    )

    print("")
    summera(korning)
    print(f"\nLoggat till {kedja.BESLUTSLOGG.relative_to(ROT)}")

    sparad = vy.spara_granskningsfall(korning.granskningsfall)
    print(f"{len(korning.granskningsfall)} fall sparade i "
          f"{sparad.relative_to(ROT)}")

    if arg.vy:
        _starta_vyn(arg.port, korning.granskningsfall)
    else:
        print("Kör med --vy för att läsa dem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
