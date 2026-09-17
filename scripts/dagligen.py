#!/usr/bin/env python3
"""DEN DAGLIGA KÖRNINGEN. Startar `respond.py --inkorg` en gång per dygn.

    .venv/bin/python scripts/dagligen.py --nu        kör en gång, direkt
    .venv/bin/python scripts/dagligen.py             slinga, kör 05:10 UTC

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

# NÄR PÅ DYGNET, i UTC. Railways scheman är UTC och det är också den här
# slingans klocka.
#
# **05:10 UTC ÄR VALT OCH INTE MÄTT, och skälet är när Lars läser.** Det är
# 07:10 svensk sommartid och 06:10 vintertid, alltså ligger utkasten i vyn när
# verkstaden öppnar. Kvarten över är medveten: hel timme är när allt annat i
# världen kör, och Anthropics API och biluppgifter.se är båda tredjeparter.
#
# **SOMMARTIDEN FLYTTAR KÖRNINGEN EN TIMME, och det är ett medvetet val.** Ett
# UTC-schema betyder att den svenska klockslaget rör sig med tidsomställningen.
# Alternativet vore en tidszonsberoende slinga, och en timmes glidning två
# gånger om året är inte värd den komplexiteten för ett utkast Lars läser när
# han kommer till jobbet.
TIMME_UTC = 5
MINUT_UTC = 10

# TAK FÖR EN KÖRNING. Utan det kan en hängd körning blockera nästa dygn i all
# oändlighet. 45 minuter är VALT.
TIMEOUT_S = 45 * 60

# SEKUNDER ETT ÄRENDE FÅR TA I TAKET NEDAN. Skiva 70, uppmätt ur
# `logg/beslut.jsonl` mellan två beslutsrader i följd: med uppslagssteg median
# 7,2 s och p99 33,4 s över 455 ärenden, utan uppslagssteg p99 34,2 s över 31.
# Uppslagssteget omfattar också ärenden där regnr saknades och ingen hämtning
# gjordes. 60 är valt över p99. Gmail-hämtningen och uppstarten ligger utanför
# budgeten; medeltiden per ärende är långt under den.
SEKUNDER_PER_ARENDE = 60

# HUR MÅNGA ÄRENDEN EN DAGLIG KÖRNING TAR. **LUCKA 86, SKIVA 70.** Här stod 20,
# valt. Med 24 timmar bakåt kommer ett ärende över taket aldrig tillbaka, så
# taket är nu det som ryms i `TIMEOUT_S`, alltså körningens egen gräns.
# Simulerat över backfillens skörd, 61 körningar: flest ärenden i en körning
# 20, median 8. Når en körning taket skriver respond ut hur många som föll och
# returnerar 1.
ANTAL = TIMEOUT_S // SEKUNDER_PER_ARENDE


def kommando(antal: int = ANTAL) -> list[str]:
    """Kommandoraden den dagliga körningen startar.

    **EGEN FUNKTION SÅ ATT DEN GÅR ATT LÄSA UR ETT TEST.** En kommandorad byggd
    inne i `kor` hade bara gått att pröva genom att faktiskt köra den.
    """
    return [sys.executable, str(ROT / "scripts" / "respond.py"),
            "--inkorg", "--gmailutkast", "--antal", str(antal)]


def _logga(post: dict) -> None:
    """Skriver en rad till körningsloggen. Aldrig kundtext (§6)."""
    KORNINGSLOGG.parent.mkdir(parents=True, exist_ok=True)
    with KORNINGSLOGG.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(post, ensure_ascii=False) + "\n")


def kor(antal: int = ANTAL, kor_process=None) -> int:
    """Kör en gång. Returnerar exitkoden.

    **FÅNGAR ALLT OCH KASTAR ALDRIG VIDARE, och det är slingans villkor.** En
    körning som kastar hade dödat slingan, och då står boten still tills någon
    märker det. Ett misslyckande ska kosta ETT dygn, inte alla följande.

    **UTDATA GÅR TILL STDOUT OCH RÄKNAS I LOGGEN, men skrivs inte dit.**
    `respond.py` skriver räknare och kategorinamn, aldrig kundtext, men den
    garantin bor i den filen. Den här filen upprepar den inte: den skickar vidare
    till stdout, där Railway fångar den, och skriver bara ANTALET rader till
    `logg/korningar.jsonl`.
    """
    kor_process = subprocess.run if kor_process is None else kor_process
    start = time.time()
    startad = datetime.now(timezone.utc).isoformat()

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
    return kod


def nasta_korning(nu: datetime) -> datetime:
    """Nästa tidpunkt schemat träffar, strikt efter `nu`."""
    mal = nu.replace(hour=TIMME_UTC, minute=MINUT_UTC, second=0, microsecond=0)
    if mal <= nu:
        mal += timedelta(days=1)
    return mal


def slinga(sov=None, nu_funktion=None, varv: int | None = None) -> None:
    """Sover till nästa körning, kör, upprepar.

    `sov` och `nu_funktion` finns för testet. `varv` begränsar antalet varv och
    är None i drift, alltså för alltid.
    """
    sov = time.sleep if sov is None else sov
    nu_funktion = (lambda: datetime.now(timezone.utc)) if nu_funktion is None \
        else nu_funktion

    print(f"[dagligen] schema {TIMME_UTC:02d}:{MINUT_UTC:02d} UTC, "
          f"logg {KORNINGSLOGG}", flush=True)

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
