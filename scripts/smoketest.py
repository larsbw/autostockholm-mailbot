#!/usr/bin/env python3
"""Prövar varje hemlighet mot sin riktiga tjänst med minsta möjliga anrop.

    .venv/bin/python scripts/smoketest.py

En rad per hemlighet: namn, OK, FAIL eller SKIP, och ett kort skäl. Exitkod 1
när något är FAIL, annars 0. Körs efter varje nyckelrotation och efter varje
lösenordsbyte på info@, se CLAUDE.md §10.

**HEMLIGHETERNA LÄSES MED PRODUKTIONENS EGNA FUNKTIONER**, aldrig med en kopia:
`kategorisera.las_api_nyckel`, `auth.prova_fornyelse`, `inkorg.las_tjanst`,
`gmailutkast.skriv_tjanst` och `dagligen.DODMANSVARIABEL`. Sökvägarna kommer ur
`src/sokvagar.py`, alltså `/volym/hemligheter` på Railway och repots rot lokalt.

**INGET VÄRDE SKRIVS UT, inte ens delvis.** Ett skäl är en undantagsklass, en
HTTP-status eller ett `AuthFel`, som bara bär filnamn, scope och Googles felrad.
`_rad` stryker dessutom varje känt värde ur raden innan den skrivs.

**INGENTING SKICKAS.** Skrivtokenet skapar ett utkast utan mottagare genom
`Utkastjanst`, som bara släpper igenom `drafts().create` och `drafts().delete`,
och tar bort det direkt.

**DÖDMANSKLOCKAN FÅR `/log`, INTE `/start`.** Avläst 2026-10-22 ur
healthchecks.io/docs/measuring_script_run_time: *"If a job sends a "start"
signal but does not send a "success" signal within its configured grace time,
Healthchecks.io will assume the job has failed. It will mark the job as "down"
and send out alerts."* Om `/log` säger healthchecks.io/docs/http_api: *"The
check's status will remain the same."*
"""

from __future__ import annotations

import base64
import importlib.util
import json
import os
import sys
import urllib.parse
import urllib.request
from email.message import EmailMessage
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import auth, gmailutkast, inkorg, kategorisera  # noqa: E402


def _ladda(namn: str):
    """Ett skript i `scripts/` som modul. Filnamnen bär bindestreck."""
    spec = importlib.util.spec_from_file_location(
        namn.replace("-", "_"), ROT / "scripts" / f"{namn}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


dagligen = _ladda("dagligen")

TIMEOUT_S = 20

# Värden som aldrig får stå i en utskriven rad. Fylls när de läses.
_HEMLIGT: set[str] = set()


def _skal(fel: Exception) -> str:
    """Klassnamn och HTTP-status, aldrig undantagets text."""
    if isinstance(fel, auth.AuthFel):
        return str(fel)
    status = (getattr(fel, "status_code", None)
              or getattr(getattr(fel, "resp", None), "status", None)
              or getattr(fel, "code", None))
    return type(fel).__name__ + (f" HTTP {status}" if status else "")


def _rad(namn: str, utfall: str, skal: str) -> None:
    for varde in _HEMLIGT:
        if varde:
            skal = skal.replace(varde, "<dold>")
    print(f"{namn:<22} {utfall:<4} {skal}", flush=True)


def anthropic() -> tuple[str, str]:
    nyckel = kategorisera.las_api_nyckel()
    if not nyckel:
        return "FAIL", f"{kategorisera.NYCKELNAMN} saknas i miljön och i .env"
    _HEMLIGT.add(nyckel)
    svar = kategorisera.bygg_klient(nyckel).messages.create(
        model=kategorisera.MODELL, max_tokens=1,
        messages=[{"role": "user", "content": "ok"}])
    return "OK", f"{kategorisera.MODELL} svarade, {svar.usage.input_tokens} in-tokens"


def gmail_las() -> tuple[str, str]:
    # Förnyelsen först, som tokenprovet: en access-token överlever ett
    # lösenordsbyte i upp till en timme, refresh-tokenen gör det inte.
    auth.prova_fornyelse(auth.LASTOKEN, auth.LASSCOPES)
    svar = inkorg.las_tjanst().users().messages().list(
        userId="me", maxResults=1).execute()
    return "OK", f"messages.list gav {len(svar.get('messages', []))} meddelande"


def gmail_skriv() -> tuple[str, str]:
    auth.prova_fornyelse(auth.SKRIVTOKEN, auth.SKRIVSCOPES)
    tjanst = gmailutkast.skriv_tjanst()
    meddelande = EmailMessage()
    meddelande["Subject"] = "SMOKETEST"
    meddelande.set_content("Skapat och borttaget av scripts/smoketest.py.")
    raw = base64.urlsafe_b64encode(meddelande.as_bytes()).decode("ascii")
    utkast = tjanst.users().drafts().create(
        userId=gmailutkast.ANVANDARE, body={"message": {"raw": raw}}).execute()
    try:
        gmailutkast.ta_bort_utkast(tjanst, utkast["id"])
    except Exception as fel:  # noqa: BLE001
        return "FAIL", (f"utkastet skapades men gick inte att ta bort "
                        f"({_skal(fel)}), ta bort SMOKETEST i Gmail för hand")
    return "OK", "utkast SMOKETEST skapat och borttaget"


def jev() -> tuple[str, str]:
    # Jev är inte inkopplat i kedjan, bara i `scripts/jev-test.py`. Nyckeln
    # läses som där, och saknas den i miljön är det inget fel.
    jevtest = _ladda("jev-test")
    try:
        nyckel = jevtest.las_jev_nyckel()
    except SystemExit:
        return "SKIP", (f"{jevtest.JEV_NYCKEL} inte satt, Jev används bara av "
                        "scripts/jev-test.py")
    _HEMLIGT.add(nyckel)
    # GET /v1/models: autentiserat och utan modellanrop, avläst 2026-10-22 ur
    # docs.typesafe.ai/api/list-models.
    begaran = urllib.request.Request(
        "https://api.typesafe.ai/v1/models",
        headers={"Authorization": f"Bearer {nyckel}"})
    with urllib.request.urlopen(begaran, timeout=TIMEOUT_S) as svar:
        antal = len(json.load(svar).get("models", []))
    return "OK", f"/v1/models gav {antal} modeller"


def biluppgifter() -> tuple[str, str]:
    return "SKIP", "öppna fordonssidan, ingen nyckel och ingen inloggning"


def dodmansklocka() -> tuple[str, str]:
    url = os.environ.get(dagligen.DODMANSVARIABEL, "").strip()
    if not url:
        return "FAIL", f"{dagligen.DODMANSVARIABEL} är inte satt"
    _HEMLIGT.add(url)
    delar = urllib.parse.urlsplit(url)
    adress = urllib.parse.urlunsplit(
        delar._replace(path=delar.path.rstrip("/") + "/log"))
    _HEMLIGT.add(adress)
    begaran = urllib.request.Request(adress, data=b"smoketest")
    with urllib.request.urlopen(begaran, timeout=TIMEOUT_S) as svar:
        return "OK", f"/log svarade HTTP {svar.status}, status oförändrad"


PROV = (
    ("anthropic", anthropic),
    ("gmail token-las", gmail_las),
    ("gmail token-skriv", gmail_skriv),
    ("jev", jev),
    ("biluppgifter", biluppgifter),
    ("healthchecks", dodmansklocka),
)


def main() -> int:
    kod = 0
    for namn, prov in PROV:
        try:
            utfall, skal = prov()
        except Exception as fel:  # noqa: BLE001
            utfall, skal = "FAIL", _skal(fel)
        if utfall == "FAIL":
            kod = 1
        _rad(namn, utfall, skal)
    return kod


if __name__ == "__main__":
    sys.exit(main())
