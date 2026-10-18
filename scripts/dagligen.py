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
läst det. Det kräver `token-skriv.json` i hemlighetskatalogen. Går den inte
att förnya faller tokenprovet vid start, se LARMET nedan, och respond körs inte.

**§10 GÄLLER FORTFARANDE.** Första sändningen i en ny miljö är Lars beslut,
oavsett vad som skickats från hans maskin. Den här filen skickar ingenting och
kan inte börja göra det utan att båda raderna ovan blir röda.

LARMET, LARS BESLUT 2026-10-18
------------------------------

Tokenerna dog 2026-10-12 när lösenordet på brevlådan byttes, och slingan stod
still i sex dygn. Driftlarmet som skulle ha sagt till var ett Gmail-utkast
skapat med `token-skriv.json`, alltså dog det av samma lösenordsbyte. Det är
borttaget. I stället:

**DÖDMANSKLOCKAN.** Efter varje körning pingas URL:en i `MAILBOT_DODMANSURL`
(healthchecks.io), `/fail` efter en misslyckad. Tjänsten larmar Lars när ingen
lyckad ping kommit på 26 timmar. Inget i den vägen rör Gmail. Är variabeln
osatt skrivs en rad om det och ingenting pingas.

**TOKENPROVET VID START.** `scripts/tokenprov.py` förnyar båda tokenerna innan
slingan sover första gången. Går det inte pingas `/fail` och processen avslutas.

**EN MISSLYCKAD KÖRNING AVSLUTAR PROCESSEN MED SAMMA KOD**, så att Railway
markerar den som misslyckad och startar om den. Railways förval, avläst
2026-10-18 ur docs.railway.com/guides/restart-policy: *"The default is `On
Failure` with a maximum of 10 restarts."* En omstart sover till nästa
`MINUT_UTC`, alltså kostar ett misslyckande fortfarande en timme.
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
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

# DÖDMANSKLOCKANS PING-URL. Lars beslut 2026-10-18. Läses vid varje ping och
# inte när modulen laddas, så att en variabel Lars sätter i Railway gäller
# från nästa omstart utan kodändring. URL:en skrivs aldrig ut: den som har den
# kan pinga kontrollen grön.
DODMANSVARIABEL = "MAILBOT_DODMANSURL"

# TAK FÖR EN PING och för tokenprovet. VALDA, inte mätta: en ping är ett
# HTTP-anrop, tokenprovet två förnyelser mot Google.
PING_TIMEOUT_S = 10
TOKENPROV_TIMEOUT_S = 60


def kommando(antal: int = ANTAL) -> list[str]:
    """Kommandoraden den dagliga körningen startar.

    **EGEN FUNKTION SÅ ATT DEN GÅR ATT LÄSA UR ETT TEST.** En kommandorad byggd
    inne i `kor` hade bara gått att pröva genom att faktiskt köra den.
    """
    return [sys.executable, str(ROT / "scripts" / "respond.py"),
            "--inkorg", "--gmailutkast", "--antal", str(antal)]


def tokenprovkommando() -> list[str]:
    """Kommandoraden för tokenprovet, av samma skäl som `kommando`."""
    return [sys.executable, str(ROT / "scripts" / "tokenprov.py")]


def _logga(post: dict) -> None:
    """Skriver en rad till körningsloggen. Aldrig kundtext (§6)."""
    KORNINGSLOGG.parent.mkdir(parents=True, exist_ok=True)
    with KORNINGSLOGG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(post, ensure_ascii=False) + "\n")


def pinga(lyckad: bool, kropp: str = "", oppna=None) -> None:
    """Pingar dödmansklockan, `/fail` när `lyckad` är falsk. Kastar aldrig.

    §6: `kropp` hamnar hos en tredjepart. Anroparna skickar bara exitkoden
    eller tokenprovets egna rader, aldrig respond.py:s stderr.
    """
    oppna = urllib.request.urlopen if oppna is None else oppna
    url = os.environ.get(DODMANSVARIABEL, "").strip()
    if not url:
        print(f"[dagligen] dödmansklockan AV: {DODMANSVARIABEL} är inte satt, "
              "ingen ping", flush=True)
        return
    # `/fail` I SÖKVÄGEN, före en eventuell query (`?create=1`). Efter hela
    # URL:en hade det hamnat i queryn och pingat grönt. Fällt av granskningen.
    delar = urllib.parse.urlsplit(url)
    sokvag = delar.path.rstrip("/") + ("" if lyckad else "/fail")
    adress = urllib.parse.urlunsplit(delar._replace(path=sokvag))
    try:
        oppna(urllib.request.Request(adress, data=kropp.encode("utf-8")),
              timeout=PING_TIMEOUT_S).close()
    except Exception as e:  # noqa: BLE001
        # `ValueError: unknown url type` citerar hela URL:en. Fällt av
        # granskningen.
        text = str(e).replace(adress, "<URL>").replace(url, "<URL>")
        print(f"[dagligen] dödmansklockan MISSLYCKADES {type(e).__name__}: "
              f"{text}", flush=True)
        return
    print(f"[dagligen] dödmansklockan pingad ({'ok' if lyckad else 'fail'})",
          flush=True)


def prova_tokens(kor_process=None) -> int:
    """Kör `scripts/tokenprov.py` och skriver ut allt den säger. Exitkoden.

    Misslyckas provet pingas `/fail` med provets egna rader som kropp.
    """
    kor_process = subprocess.run if kor_process is None else kor_process
    try:
        utfall = kor_process(tokenprovkommando(), cwd=str(ROT),
                             capture_output=True, text=True,
                             timeout=TOKENPROV_TIMEOUT_S)
        kod = utfall.returncode
        text = ((utfall.stdout or "") + (utfall.stderr or "")).strip()
    except Exception as e:  # noqa: BLE001
        kod, text = 1, f"tokenprovet gick inte att köra: {type(e).__name__}: {e}"
    if text:
        print(text, flush=True)
    if kod != 0:
        print(f"[dagligen] tokenprovet FÖLL, exitkod {kod}", flush=True)
        pinga(False, f"tokenprovet föll vid start, exitkod {kod}\n{text}")
    return kod


def kor(antal: int = ANTAL, kor_process=None) -> int:
    """Kör en gång. Returnerar exitkoden.

    **FÅNGAR ALLT OCH KASTAR ALDRIG VIDARE.** Ett misslyckande ska loggas,
    pingas som `/fail` och komma tillbaka som en exitkod, så att `slinga` kan
    avsluta processen med den. Ett undantag hade hoppat över alla tre.

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

    # Efter loggningen, aldrig i stället för den. §6: bara exitkoden går till
    # tjänsten, inte `sista`, som är respond.py:s egen stderr.
    pinga(kod == 0, f"exitkod {kod}")

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


def slinga(sov=None, nu_funktion=None, varv: int | None = None,
           kor_process=None) -> int:
    """Prövar tokenerna, sover till nästa körning, kör, upprepar. Exitkoden.

    **RETURNERAR VID FÖRSTA FELET**, tokenprovets eller en körnings, med dess
    kod. Lars beslut 2026-10-18: Railway ska se att något gått fel. Se
    modulens docstring för vad Railway gör sedan.

    `sov`, `nu_funktion` och `kor_process` finns för testet. `varv` begränsar
    antalet varv och är None i drift, alltså för alltid.
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

    kod = prova_tokens(kor_process=kor_process)
    if kod != 0:
        return kod

    kvar = varv
    while kvar is None or kvar > 0:
        nu = nu_funktion()
        mal = nasta_korning(nu)
        sekunder = (mal - nu).total_seconds()
        print(f"[dagligen] nästa körning {mal.isoformat()}, "
              f"om {int(sekunder)} s", flush=True)
        sov(sekunder)
        kod = kor(kor_process=kor_process)
        if kod != 0:
            print(f"[dagligen] avslutar med exitkod {kod}", flush=True)
            return kod
        if kvar is not None:
            kvar -= 1
    return 0


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    tolk.add_argument("--nu", action="store_true",
                      help="kör en gång direkt i stället för att sova till schemat")
    tolk.add_argument("--antal", type=int, default=ANTAL)
    arg = tolk.parse_args(argv)

    if arg.nu:
        return kor(arg.antal)

    return slinga()


if __name__ == "__main__":
    raise SystemExit(main())
