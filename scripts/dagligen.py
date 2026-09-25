#!/usr/bin/env python3
"""SLINGAN. Startar `respond.py --inkorg` en gång i timmen.

    .venv/bin/python scripts/dagligen.py --nu        kör en gång, direkt
    .venv/bin/python scripts/dagligen.py             slinga, kör var timme

**FILEN HETER FORTFARANDE `dagligen.py`.** Namnet är från skiva 69, då
schemat var en körning per dygn. Uppdraget 2026-09-25 DEL 1, Lars beslut, gick
till en gång i timmen: boten ska inte vänta till nästa morgon på ett mail som
kom klockan nio. Ett filnamnsbyte hade rört varje import och varje
sökvägsreferens (`src/sokvagar.py::KORNINGSLOGG`, `start.sh`,
`docs/beslutslogg.md`) för en ren namnfråga, och är inte del av det uppdraget.

**VARFÖR EN EGEN SLINGA OCH INTE RAILWAYS CRON.** Avläst ur docs.railway.com
2026-09-15:

  "Each service can only have a single volume attached"
  Railways cron kör en services STARTKOMMANDO på schema.
  "If you see that a previous execution of your Cron service has a status of
   Active, the execution is still running and any new executions will not be
   run."

Den sista raden avgör. En service vars startkommando är en webbserver avslutas
aldrig, alltså är den permanent Active, alltså kör cron ALDRIG på den servicen.

Vyn och den dagliga körningen delar `data/` och `logg/`. Ett volume per service
betyder att de måste dela service, och då är den servicens cron utesluten av
raden ovan. Schemat ligger därför i containern.

*Här stod att ett volume inte KAN DELAS mellan två services, som en avläsning.
Det står ingenstans i dokumentationen. Slutsatsen står kvar, premissen är bytt
mot den som faktiskt går att läsa. Fällt av §7-granskningen av skiva 53.*

**SLINGAN STARTAR RESPOND SOM EN EGEN PROCESS, och det ledet är avsiktligt.**
`scripts/respond.py` drar in `googleapiclient` genom `src/inkorg.py`. Vyn får
inte göra det: `vy.FORBJUDNA_MODULER` bär `googleapiclient` och
`vy.krav_pa_sandvagsfrihet` körs utan undantag för vyns egen graf. En slinga som
IMPORTERADE respond hade därför antingen fällt vyns spärr eller krävt att den
mjukades upp. En subprocess rör inte importgrafen alls.

Den här filen importerar inte heller respond. Den kör den.

**INGEN SÄNDNING.** `respond.py` har ingen `--send`, och
`test_respond_har_INGEN_send_flagga` fäller om en sådan tillkommer. Den här
filen lägger till ett andra led: kommandoraden byggs av `kommando` och
`test_dagliga_kommandot_bar_INGEN_sandflagga` läser den.

**UTKAST I GMAIL, SKIVA 69.** Kommandot bär `--gmailutkast`, Lars beslut: varje
ärende som passerat spärrarna blir ett utkast i kundens tråd utan att någon
läst det. Det kräver `token-skriv.json` i hemlighetskatalogen. Saknas den
kör respond utan utkast och returnerar 1.

**§10 GÄLLER FORTFARANDE.** Första sändningen i en ny miljö är Lars beslut,
oavsett vad som skickats från hans maskin. Den här filen skickar ingenting och
kan inte börja göra det utan att båda raderna ovan blir röda.

DRIFTLARMET, UPPDRAG 2026-09-25 DEL 2
--------------------------------------

Lars beslut: en körning som avslutas med fel eller en exitkod skild från noll
ska ge ETT Gmail-utkast till info@autostockholm.se, så att ett fel inte ligger
tyst i Railways logg till nästa gång någon råkar leta.

**SAMMA ISOLERING SOM RESPOND, EN EGEN PROCESS.** Den här filen importerar
fortfarande bara stdlib och `src.sokvagar`, precis som innan uppdraget:
`test_vyn_och_kedjan_nar_ALDRIG_gmailutkast[scripts.dagligen]` binder att
`src.gmailutkast` aldrig får stå i den här filens importgraf, Lars beslut i
skiva 69 (se `tests/test_gmailutkast.py`). Draftfunktionen ligger i stället i
`scripts/driftlarm.py`, en fristående process byggd på samma mönster som
`respond.py`: `krav_pa_sandvagsfrihet("scripts.driftlarm", ...)` körs där,
inte här, och den processen har sin egen `token-skriv.json`-väg genom
`src/gmailutkast.py::skriv_tjanst`.

**TAKET ÄR HÖGST ETT LARM VAR SJÄTTE TIMME**, `LARMFONSTER_S`, så att en
kvarstående störning inte fyller inkorgen med ett utkast varje timme.
`logg/drift-larm.jsonl` bär bara en tidsstämpel per skickat larm och skrivs
ENDAST av den här filen, aldrig av `scripts/driftlarm.py`, se
`src/sokvagar.py::DRIFTLARMLOGG`.

**ETT MISSLYCKAT LARM STOPPAR INGET.** `_larma_vid_fel` fångar allt av samma
skäl som `kor` gör: ett trasigt larm (saknad `token-skriv.json`, ett nätverksfel)
ska kosta det larmet, inte slingan, och skriver ingen rad i
`logg/drift-larm.jsonl` när det misslyckas, så att nästa misslyckade körning
får försöka igen.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import sokvagar  # noqa: E402

ROT = Path(__file__).resolve().parent.parent

# KÖRNINGSLOGGEN. **Inte `logg/beslut.jsonl`**, som är append-only och tillhör
# kedjans beslut (§0:s ramverksregel 4). Den här filen bär driftutfall: när en
# körning startade, hur länge den tog och hur den slutade.
#
# §6: raden bär ALDRIG kundtext. Tidsstämpel, exitkod, sekunder och antal rader
# utdata. Se `_logga`.
#
# **SÖKVÄGEN ÄR `src/sokvagar.py`:s OCH INTE DEN HÄR FILENS.** Skiva 54 DEL B gav
# loggen en andra läsare, `vy.korningsrad`, och skälet att namnet bor där står i
# den modulen.
KORNINGSLOGG = sokvagar.KORNINGSLOGG

# DRIFTLARMETS EGEN LOGG, uppdrag 2026-09-25 DEL 2. Bär bara en tidsstämpel
# per skickat larm, se `src/sokvagar.py::DRIFTLARMLOGG` för varför den är en
# egen fil och inte en rad i `KORNINGSLOGG`. Sökvägen är `src/sokvagar.py`:s
# av samma skäl som `KORNINGSLOGG` ovan.
DRIFTLARMLOGG = sokvagar.DRIFTLARMLOGG

# TOKENFILERNA RESPOND BEHÖVER, skiva 72. Namnen är `src/auth.py`:s och står
# här som text, eftersom schemat inte importerar Gmail-vägen.
# `test_schemats_tokennamn_ar_AUTHS` binder att de inte glider isär.
TOKENFILER = ("token-las.json", "token-skriv.json")

# MINUTEN VARJE TIMME SCHEMAT TRÄFFAR, i UTC. Railways scheman är UTC och det
# är också den här slingans klocka.
#
# **:10 ÄR VALT OCH INTE MÄTT.** Inte hel timme, med avsikt: hel timme är när
# allt annat i världen kör, och Anthropics API och biluppgifter.se är båda
# tredjeparter. Talet är kvar sedan skiva 69, då det också var motiverat av när
# Lars läser utkasten; det skälet föll med den dagliga klockslagningen, men
# valet av minut var aldrig knutet till den.
#
# *Här stod också `TIMME_UTC = 5`, och stycket ovan motiverade klockslaget
# 05:10 med när Lars kommer till jobbet. Uppdraget 2026-09-25 DEL 1 gick från
# en körning per dygn till en per timme, Lars beslut: ett mail ska inte
# behöva vänta till nästa morgon. `nasta_korning` träffar nu `MINUT_UTC` i
# varje timme i stället för en gång per dygn.*
MINUT_UTC = 10

# TAK FÖR EN KÖRNING. Utan det kan en hängd körning blockera nästa timme i all
# oändlighet. 45 minuter är VALT.
TIMEOUT_S = 45 * 60

# SEKUNDER ETT ÄRENDE FÅR TA I TAKET NEDAN. Skiva 70, uppmätt ur
# `logg/beslut.jsonl` mellan två beslutsrader i följd: med uppslagssteg median
# 7,2 s och p99 33,4 s över 455 ärenden, utan uppslagssteg p99 34,2 s över 31.
# Uppslagssteget omfattar också ärenden där regnr saknades och ingen hämtning
# gjordes. 60 är valt över p99. Gmail-hämtningen och uppstarten ligger utanför
# budgeten; medeltiden per ärende är långt under den.
SEKUNDER_PER_ARENDE = 60

# HUR MÅNGA ÄRENDEN EN KÖRNING TAR. **LUCKA 86, SKIVA 70.** Här stod 20, valt.
# Taket är det som ryms i `TIMEOUT_S`, alltså körningens egen gräns. Simulerat
# över backfillens skörd, 61 dagskörningar: flest ärenden i en körning 20,
# median 8. Når en körning taket skriver respond ut hur många som föll och
# returnerar 1.
#
# *Här stod att ett ärende över taket ALDRIG kommer tillbaka, sant när
# fönstret var ett fast dygn räknat från körningens egen start. Uppdraget
# 2026-09-25 DEL 1 gjorde fönstret till "sedan senaste LYCKADE körningen": en
# körning som returnerar 1 för att taket nåddes räknas inte som lyckad
# (`respond.py::_kor`s sista rad), alltså börjar nästa körnings fönster om
# vid samma punkt och tar upp det som föll igen. Ett ärende kan alltså
# komma tillbaka, i en körning som redan är sen. Det ändrar inte var taket
# ska ligga, bara vad som händer det som faller över det.*
ANTAL = TIMEOUT_S // SEKUNDER_PER_ARENDE

# DRIFTLARMETS TAK. Uppdrag 2026-09-25 DEL 2, Lars beslut: högst ett larm var
# sjätte timme, så att en kvarstående störning inte skickar ett utkast varje
# timme och fyller inkorgen. Talet är VALT och inte mätt.
LARMFONSTER_S = 6 * 60 * 60

# TAK FÖR DRIFTLARMETS EGEN PROCESS. Ett `drafts().create`-anrop, inte en
# ärendekedja: 30 s är gott om marginal och VALT, inte mätt.
LARM_TIMEOUT_S = 30


def kommando(antal: int = ANTAL) -> list[str]:
    """Kommandoraden den dagliga körningen startar.

    **EGEN FUNKTION SÅ ATT DEN GÅR ATT LÄSA UR ETT TEST.** En kommandorad byggd
    inne i `kor` hade bara gått att pröva genom att faktiskt köra den.
    """
    return [sys.executable, str(ROT / "scripts" / "respond.py"),
            "--inkorg", "--gmailutkast", "--antal", str(antal)]


def larmkommando(tid: str, exitkod: int, fel: str) -> list[str]:
    """Kommandoraden för driftlarmet. Uppdrag 2026-09-25 DEL 2.

    **EGEN FUNKTION AV SAMMA SKÄL SOM `kommando`**: så att kommandoraden går
    att läsa ur ett test utan att faktiskt starta processen.
    """
    return [sys.executable, str(ROT / "scripts" / "driftlarm.py"),
            "--tid", tid, "--exitkod", str(exitkod), "--fel", fel]


def _logga(post: dict) -> None:
    """Skriver en rad till körningsloggen. Aldrig kundtext (§6)."""
    KORNINGSLOGG.parent.mkdir(parents=True, exist_ok=True)
    with KORNINGSLOGG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(post, ensure_ascii=False) + "\n")


def _senaste_larm(fil: Path) -> datetime | None:
    """Tidsstämpeln för senast SKICKADE driftlarmet, eller None.

    Samma toleranta läsning som `vy.senaste_lyckade`: en trasig rad hoppas
    över i stället för att fälla läsningen, av samma skäl den funktionens
    docstring ger.
    """
    if not fil.exists():
        return None
    senaste = None
    for rad in fil.read_text(encoding="utf-8").splitlines():
        if not rad.strip():
            continue
        try:
            tid = datetime.fromisoformat(json.loads(rad)["tid"])
        except (ValueError, KeyError, TypeError):
            continue
        if tid.tzinfo is None:
            tid = tid.replace(tzinfo=timezone.utc)
        if senaste is None or tid > senaste:
            senaste = tid
    return senaste


def _larm_tillatet(nu: datetime, fil: Path) -> bool:
    """Sant om `LARMFONSTER_S` gått sedan senaste SKICKADE larmet."""
    senaste = _senaste_larm(fil)
    return senaste is None or (nu - senaste).total_seconds() >= LARMFONSTER_S


def _larma_vid_fel(nu: datetime, kod: int, fel: str, kor_process=None) -> None:
    """Skapar ett driftlarm om taket i `LARMFONSTER_S` tillåter det.

    `nu` är körningens EGEN starttid (`startad` i `kor`), både som larmets
    tidsstämpel och som jämförelsepunkt mot `logg/drift-larm.jsonl`: samma
    värde som redan loggas i `logg/korningar.jsonl` för samma körning.

    **FÅNGAR ALLT**, samma villkor som `kor` självt: ett trasigt larm ska
    kosta det larmet, inte slingan. Misslyckas det skrivs ingen rad i
    `DRIFTLARMLOGG`, så att nästa misslyckade körning får försöka igen.
    """
    kor_process = subprocess.run if kor_process is None else kor_process
    if not _larm_tillatet(nu, DRIFTLARMLOGG):
        print("[dagligen] driftlarm hoppas över: mindre än "
              f"{LARMFONSTER_S // 3600} timmar sedan senaste", flush=True)
        return

    try:
        utfall = kor_process(
            larmkommando(nu.isoformat(), kod, fel),
            cwd=str(ROT),
            capture_output=True,
            text=True,
            timeout=LARM_TIMEOUT_S,
        )
        lyckades = utfall.returncode == 0
    except Exception as e:  # noqa: BLE001
        print(f"[dagligen] driftlarm MISSLYCKADES {type(e).__name__}",
              flush=True)
        return

    if not lyckades:
        print(f"[dagligen] driftlarm MISSLYCKADES, exitkod "
              f"{utfall.returncode}", flush=True)
        return

    DRIFTLARMLOGG.parent.mkdir(parents=True, exist_ok=True)
    with DRIFTLARMLOGG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps({"tid": nu.isoformat()}, ensure_ascii=False)
                 + "\n")
    print("[dagligen] driftlarm skickat", flush=True)


def kor(antal: int = ANTAL, kor_process=None) -> int:
    """Kör en gång. Returnerar exitkoden.

    **FÅNGAR ALLT OCH KASTAR ALDRIG VIDARE, och det är slingans villkor.** En
    körning som kastar hade dödat slingan, och då står boten still tills någon
    märker det. Ett misslyckande ska kosta EN timme, inte alla följande.

    **UTDATA GÅR TILL STDOUT OCH RÄKNAS I LOGGEN, men skrivs inte dit.**
    `respond.py` skriver räknare och kategorinamn, aldrig kundtext, men den
    garantin bor i den filen. Den här filen upprepar den inte: den skickar vidare
    till stdout, där Railway fångar den, och skriver bara ANTALET rader till
    `logg/korningar.jsonl`.
    """
    kor_process = subprocess.run if kor_process is None else kor_process
    start = time.time()
    startad_dt = datetime.now(timezone.utc)
    startad = startad_dt.isoformat()

    try:
        utfall = kor_process(
            kommando(antal),
            cwd=str(ROT),
            capture_output=True,
            text=True,
            timeout=TIMEOUT_S,
        )
        kod = utfall.returncode
        rader = len((utfall.stdout or "").splitlines())
        fel = (utfall.stderr or "").strip()
        sys.stdout.write(utfall.stdout or "")
        if fel:
            sys.stderr.write(fel + "\n")
        # §6: SISTA raden och inte hela spåret. En traceback kan bära ett
        # filnamn ur `data/` och, i ett undantags text, en bit av det som lästes.
        # `respond.py` utfäster att den inte skriver kundtext, men den
        # utfästelsen gäller dess EGNA utskrifter och inte vad en okänd
        # biblioteksbugg lägger i ett undantag. Sista raden är typ och
        # meddelande, hela spåret står i Railways logg och inte i vår fil.
        sista = fel.splitlines()[-1] if fel else ""
    except subprocess.TimeoutExpired:
        kod, rader, sista = 124, 0, f"körningen tog över {TIMEOUT_S} s och dödades"
        sys.stderr.write(sista + "\n")
    except Exception as e:
        kod, rader, sista = 1, 0, f"{type(e).__name__}: {e}"
        sys.stderr.write(sista + "\n")

    sekunder = round(time.time() - start, 1)
    _logga({
        "startad": startad,
        "sekunder": sekunder,
        "exitkod": kod,
        "utdatarader": rader,
        "fel": sista,
        "lyckades": kod == 0,
    })
    print(f"[dagligen] exitkod {kod} efter {sekunder} s", flush=True)

    # UPPDRAG 2026-09-25 DEL 2. Efter loggningen, aldrig i stället för den:
    # körningsloggen är beviset för slingans egen hälsa oavsett om larmet
    # går fram. `nu` är körningens EGEN starttid, se `_larma_vid_fel`.
    if kod != 0:
        _larma_vid_fel(startad_dt, kod, sista, kor_process=kor_process)

    return kod


def nasta_korning(nu: datetime) -> datetime:
    """Nästa tidpunkt schemat träffar, strikt efter `nu`.

    En gång i timmen, `MINUT_UTC` minuter in i varje timme. Uppdrag 2026-09-25
    DEL 1: här stod en gång per dygn, med `mal += timedelta(days=1)`; steget
    är nu en timme.
    """
    mal = nu.replace(minute=MINUT_UTC, second=0, microsecond=0)
    if mal <= nu:
        mal += timedelta(hours=1)
    return mal


def slinga(sov=None, nu_funktion=None, varv: int | None = None) -> None:
    """Sover till nästa körning, kör, upprepar.

    `sov` och `nu_funktion` finns för testet. `varv` begränsar antalet varv och
    är None i drift, alltså för alltid.
    """
    sov = time.sleep if sov is None else sov
    nu_funktion = (lambda: datetime.now(timezone.utc)) if nu_funktion is None \
        else nu_funktion

    print(f"[dagligen] schema varje timme :{MINUT_UTC:02d} UTC, "
          f"logg {KORNINGSLOGG}", flush=True)
    # SKIVA 72. Utan vyn är det här raden som visar att körningen kan läsa och
    # skriva utkast. Bara om filen finns, aldrig innehållet.
    for namn in TOKENFILER:
        fil = sokvagar.HEMLIGHETER / namn
        print(f"[dagligen] {fil}: {'finns' if fil.is_file() else 'SAKNAS'}",
              flush=True)

    kvar = varv
    while kvar is None or kvar > 0:
        nu = nu_funktion()
        mal = nasta_korning(nu)
        sekunder = (mal - nu).total_seconds()
        print(f"[dagligen] nästa körning {mal.isoformat()}, "
              f"om {int(sekunder)} s", flush=True)
        sov(sekunder)
        kor()
        if kvar is not None:
            kvar -= 1


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    tolk.add_argument("--nu", action="store_true",
                      help="kör en gång direkt i stället för att sova till schemat")
    tolk.add_argument("--antal", type=int, default=ANTAL)
    arg = tolk.parse_args(argv)

    if arg.nu:
        return kor(arg.antal)

    slinga()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
