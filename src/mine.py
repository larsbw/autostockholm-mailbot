"""Hämtar alla trådar som innehåller minst ett skickat meddelande.

Hela tråden hämtas i ETT anrop med threads.get. messages.get per meddelande
används aldrig: det kostar mer kvot och ger samma innehåll.

KVOTTABELL — avläst 2026-08-26 ur
https://developers.google.com/workspace/gmail/api/reference/quota
(sidan anger "Last updated 2026-07-31 UTC" och att gränserna uppdaterades
"As of May 1, 2026"). GCP-projektet autostockholm-mailbot är skapat efter det
datumet och lyder under dessa värden:

    threads.list                            10 kvotenheter
    threads.get                             40 kvotenheter
    per minut per projekt            1 200 000 kvotenheter
    per minut per användare per projekt  6 000 kvotenheter

Boten kör mot en enda brevlåda, så per-användargränsen binder först. Pacingen
dimensioneras därför mot 6 000 enheter/minut, med en vald säkerhetsmarginal
(ANDEL_AV_KVOT) eftersom Gmail-klienter och mobiler förbrukar ur samma pott.
Marginalen är ett val, inte ett avläst värde. Se docs/beslutslogg.md #1.

FELHANTERING VID KVOTTAK. Vad koden gör: VARJE 429 behandlas som kvottak,
oavsett orsak, och ett 403 behandlas som kvottak bara när dess
error.errors[0].reason är en av dailyLimitExceeded, rateLimitExceeded eller
userRateLimitExceeded. Allt annat, 403 av behörighetsskäl inräknat, kastas
vidare och görs aldrig om.

Underlaget, avläst 2026-08-26 ur
https://developers.google.com/workspace/gmail/api/guides/handle-errors : sidans
avsnitt "403 errors" listar orsakerna dailyLimitExceeded, domainPolicy,
rateLimitExceeded och userRateLimitExceeded. domainPolicy är utelämnad ur
KVOTORSAKER därför att den inte är ett kvottak. Avsnittet "429 errors" listar
INGA maskinläsbara reason-strängar alls, bara meddelandetext, och därför tittar
koden aldrig på reason för 429. Sidan rekommenderar exponentiell backoff och att
"Start retry periods at least one second after the error."
"""

from __future__ import annotations

import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path

from googleapiclient.errors import HttpError

from src import auth

ROT = Path(__file__).resolve().parent.parent
UTFIL = ROT / "data" / "tradar.jsonl"
MININGLOGG = ROT / "docs" / "mining-log.md"

ANVANDARE = "me"
FRAGA = "in:sent"

# Vald sidstorlek för threads.list, inget avläst värde. Gmails eget tak för
# maxResults är inte uppslaget, så talet är satt lågt med avsikt.
SIDSTORLEK = 100

KOSTNAD_THREADS_LIST = 10
KOSTNAD_THREADS_GET = 40
KVOT_PER_ANVANDARE_PER_MINUT = 6000

# Vald marginal mot per-användargränsen, inget avläst värde.
ANDEL_AV_KVOT = 0.5
ENHETER_PER_MINUT = KVOT_PER_ANVANDARE_PER_MINUT * ANDEL_AV_KVOT

# BASFORDROJNING_S är avläst: sidan om felhantering säger "Start retry periods
# at least one second after the error." Takfördröjningen och antalet försök är
# däremot VAL utan mätt underlag, satta för att en mining-körning ska ge upp
# inom rimlig tid i stället för att mala mot ett kvottak som inte släpper.
BASFORDROJNING_S = 1.0
MAX_BASFORDROJNING_S = 64.0
MAX_FORSOK = 6

KVOTORSAKER = frozenset(
    {"rateLimitExceeded", "userRateLimitExceeded", "dailyLimitExceeded"}
)


class KvotfelKvarstar(Exception):
    """Kvottaket höll i sig genom samtliga försök."""


def _orsak(fel: HttpError) -> str:
    """Plockar ut Googles error.errors[0].reason ur felkroppen."""
    try:
        kropp = json.loads(fel.content.decode("utf-8"))
    except (AttributeError, ValueError, UnicodeDecodeError):
        return ""
    fellista = kropp.get("error", {}).get("errors") or [{}]
    return fellista[0].get("reason", "")


def ar_kvotfel(fel: BaseException) -> bool:
    """Sant bara för de statuskoder och orsaker Google dokumenterar som
    kvottak. Ett 403 av behörighetsskäl ska falla igenom, inte göras om."""
    status = getattr(getattr(fel, "resp", None), "status", None)
    if status == 429:
        return True
    if status != 403:
        return False
    return _orsak(fel) in KVOTORSAKER


def fordrojning(forsok: int, slumpa=random.random) -> float:
    """Exponentiell backoff med jitter. Jittern läggs ovanpå basen i stället
    för att skala ned den, så att första omförsöket aldrig hamnar under den
    sekund Google anger som golv."""
    bas = min(BASFORDROJNING_S * (2**forsok), MAX_BASFORDROJNING_S)
    return bas + slumpa() * bas


class Kvotpacer:
    """Sprider ut anropen jämnt så att förbrukningen håller sig under
    ENHETER_PER_MINUT. Ingen skur tillåts: varje anrop reserverar sin egen
    kostnad framåt i tiden."""

    def __init__(self, enheter_per_minut=ENHETER_PER_MINUT, sov=time.sleep,
                 klocka=time.monotonic):
        self._enheter_per_sekund = enheter_per_minut / 60.0
        self._sov = sov
        self._klocka = klocka
        self._nasta_tidigast: float | None = None

    def vanta(self, kostnad: int) -> None:
        nu = self._klocka()
        if self._nasta_tidigast is not None and nu < self._nasta_tidigast:
            self._sov(self._nasta_tidigast - nu)
            nu = self._nasta_tidigast
        self._nasta_tidigast = nu + kostnad / self._enheter_per_sekund


class Forbrukning:
    """Räknar faktiskt åtgången kvot, inklusive anrop som fällts av kvottaket."""

    def __init__(self) -> None:
        self.enheter = 0
        self.anrop = 0
        self.tradar = 0
        self.fullstandig = False

    def lagg_till(self, kostnad: int) -> None:
        self.enheter += kostnad
        self.anrop += 1


def _utfor(bygg_anrop, *, kostnad, pacer, forbrukning, sov=time.sleep,
           slumpa=random.random):
    """Kör ett Gmail-anrop med pacing före och backoff vid kvottak."""
    senaste = None
    for forsok in range(MAX_FORSOK):
        pacer.vanta(kostnad)
        forbrukning.lagg_till(kostnad)
        try:
            return bygg_anrop().execute()
        except HttpError as fel:
            if not ar_kvotfel(fel):
                raise
            senaste = fel
            if forsok == MAX_FORSOK - 1:
                break
            sov(fordrojning(forsok, slumpa))
    raise KvotfelKvarstar(
        f"Kvottaket kvarstod efter {MAX_FORSOK} försök."
    ) from senaste


def lista_trad_id(tjanst, *, pacer, forbrukning, max_tradar=None, sov=time.sleep,
                  slumpa=random.random) -> list[str]:
    """Tråd-ID för trådar med minst ett skickat meddelande."""
    if max_tradar is not None and max_tradar <= 0:
        return []

    idn: list[str] = []
    sidtoken = None
    while True:
        svar = _utfor(
            lambda: tjanst.users().threads().list(
                userId=ANVANDARE,
                q=FRAGA,
                maxResults=SIDSTORLEK,
                pageToken=sidtoken,
            ),
            kostnad=KOSTNAD_THREADS_LIST,
            pacer=pacer,
            forbrukning=forbrukning,
            sov=sov,
            slumpa=slumpa,
        )
        for trad in svar.get("threads") or []:
            idn.append(trad["id"])
            if max_tradar is not None and len(idn) >= max_tradar:
                return idn
        sidtoken = svar.get("nextPageToken")
        if not sidtoken:
            return idn


def hamta_trad(tjanst, trad_id: str, *, pacer, forbrukning, sov=time.sleep,
               slumpa=random.random) -> dict:
    """Hela tråden i ett anrop."""
    return _utfor(
        lambda: tjanst.users().threads().get(
            userId=ANVANDARE, id=trad_id, format="full"
        ),
        kostnad=KOSTNAD_THREADS_GET,
        pacer=pacer,
        forbrukning=forbrukning,
        sov=sov,
        slumpa=slumpa,
    )


def mina(tjanst, *, utfil: Path, max_tradar=None, pacer=None, forbrukning=None,
         sov=time.sleep, slumpa=random.random) -> Forbrukning:
    """Skriver en tråd per rad till utfil och returnerar förbrukningen.

    Hämtningen skrivs till en sidofil med suffixet .delvis och flyttas på plats
    först när den är klar. En körning som avbryts lämnar därför utfilen orörd,
    och det halva resultatet ligger kvar under ett namn som inte går att läsa
    som en färdig fil.
    """
    pacer = Kvotpacer(sov=sov) if pacer is None else pacer
    forbrukning = Forbrukning() if forbrukning is None else forbrukning

    idn = lista_trad_id(
        tjanst, pacer=pacer, forbrukning=forbrukning, max_tradar=max_tradar,
        sov=sov, slumpa=slumpa,
    )

    utfil.parent.mkdir(parents=True, exist_ok=True)
    delvis = utfil.with_name(utfil.name + ".delvis")
    with delvis.open("w", encoding="utf-8") as fil:
        for trad_id in idn:
            trad = hamta_trad(
                tjanst, trad_id, pacer=pacer, forbrukning=forbrukning,
                sov=sov, slumpa=slumpa,
            )
            fil.write(json.dumps(trad, ensure_ascii=False) + "\n")
            forbrukning.tradar += 1

    delvis.replace(utfil)
    forbrukning.fullstandig = True
    return forbrukning


def logga_korning(forbrukning: Forbrukning, *, logg: Path | None = None,
                  nu=None) -> str:
    """Appendar en rad i docs/mining-log.md (CLAUDE.md §8). Inga adresser,
    inga ämnesrader, bara mätvärden.

    Anropas även när körningen fallit, eftersom kvoten är förbrukad oavsett.
    Statuskolumnen skiljer den avbrutna körningen från den färdiga.

    logg slås upp vid anropet och inte som defaultvärde: ett defaultvärde binds
    när modulen laddas, och pekade då på den riktiga loggen även när MININGLOGG
    hade bytts ut."""
    logg = MININGLOGG if logg is None else logg
    stampel = (nu or datetime.now(timezone.utc)).strftime("%Y-%m-%d %H:%M UTC")
    status = "fullständig" if forbrukning.fullstandig else "AVBRUTEN"
    rad = (
        f"| {stampel} | `{FRAGA}` | {forbrukning.tradar} | "
        f"{forbrukning.anrop} | {forbrukning.enheter} | {status} |\n"
    )
    with logg.open("a", encoding="utf-8") as fil:
        fil.write(rad)
    return rad


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(
        description="Hämtar trådar med minst ett skickat meddelande."
    )
    tolk.add_argument(
        "--max-threads",
        type=int,
        default=None,
        help="begränsa antalet trådar som hämtas",
    )
    arg = tolk.parse_args(argv)

    cred = auth.hamta_credentials(tillat_webblasare=False)
    tjanst = auth.bygg_tjanst(cred)

    # Förbrukningen skapas här och inte i mina(), så att den finns kvar att
    # logga även när mina() faller. Kvoten är åtgången oavsett utfall, och §8
    # kräver att den står i loggen innan nästa körning startas.
    forbrukning = Forbrukning()
    try:
        mina(
            tjanst,
            utfil=UTFIL,
            max_tradar=arg.max_threads,
            forbrukning=forbrukning,
        )
    finally:
        rad = logga_korning(forbrukning)
        print(f"trådar: {forbrukning.tradar}")
        print(f"anrop: {forbrukning.anrop}")
        print(f"kvotenheter: {forbrukning.enheter}")
        print(f"mining-log: {rad.strip()}")

    print(f"utfil: {UTFIL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
