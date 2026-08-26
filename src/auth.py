"""OAuth-desktopflöde mot Gmail för info@autostockholm.se.

Scopelistan är låst till gmail.modify och gmail.send (CLAUDE.md §0). Ett nytt
scope är ett §10-stopp och läggs aldrig till av kod.

Idempotens: en giltig token återanvänds och filen rörs INTE. En utgången token
med refresh_token förnyas utan webbläsare. Webbläsaren öppnas bara när inget av
detta går, och bara när anroparen uttryckligen tillåtit det.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.send",
]

ROT = Path(__file__).resolve().parent.parent
CLIENT_SECRET = ROT / "client_secret.json"
TOKEN = ROT / "token.json"


class AuthFel(Exception):
    """Auktorisering saknas eller går inte att förnya utan webbläsare."""


def _las_token(token_sokvag: Path, scopes: list[str]) -> Credentials | None:
    """Returnerar token från fil, eller None om den saknas, är trasig eller
    inte täcker samtliga begärda scopes."""
    if not token_sokvag.exists():
        return None
    try:
        # Utan scopes-argument: from_authorized_user_info plockar då scopelistan
        # UR filen. Skickas den in blir cred.scopes en kopia av det vi frågade
        # efter, och has_scopes nedan svarar alltid ja.
        cred = Credentials.from_authorized_user_file(str(token_sokvag))
    except (ValueError, KeyError):
        return None
    if not cred.has_scopes(scopes):
        return None
    return cred


def _skriv_token(cred: Credentials, token_sokvag: Path) -> None:
    token_sokvag.write_text(cred.to_json(), encoding="utf-8")
    token_sokvag.chmod(0o600)


def hamta_credentials(
    *,
    tillat_webblasare: bool = False,
    token_sokvag: Path = TOKEN,
    client_secret: Path = CLIENT_SECRET,
    scopes: list[str] | None = None,
) -> Credentials:
    """Hämtar giltiga credentials.

    Ordningen är: återanvänd, förnya, auktorisera. Webbläsaren är sista utvägen
    och kräver tillat_webblasare=True, eftersom första auktoriseringen i en ny
    miljö är Lars beslut (CLAUDE.md §10).
    """
    scopes = list(SCOPES if scopes is None else scopes)
    cred = _las_token(token_sokvag, scopes)

    if cred is not None and cred.valid:
        return cred

    if cred is not None and cred.refresh_token:
        try:
            cred.refresh(Request())
        except RefreshError:
            cred = None
        else:
            _skriv_token(cred, token_sokvag)
            return cred

    if not tillat_webblasare:
        raise AuthFel(
            f"Ingen giltig eller förnybar token i {token_sokvag.name}. "
            "Auktorisering kräver webbläsare och är ett §10-stopp: kör "
            "`.venv/bin/python -m src.auth --auktorisera` efter Lars beslut."
        )

    if not client_secret.exists():
        raise AuthFel(f"Hittar inte {client_secret.name} i repots rot.")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), scopes)
    cred = flow.run_local_server(port=0)
    _skriv_token(cred, token_sokvag)
    return cred


def bygg_tjanst(cred: Credentials):
    """Gmail-tjänsten. cache_discovery=False för att slippa filcache-varningen."""
    return build("gmail", "v1", credentials=cred, cache_discovery=False)


def _status(token_sokvag: Path) -> str:
    """Rapporterar existens och längd, aldrig innehåll (CLAUDE.md §6)."""
    if not token_sokvag.exists():
        return f"{token_sokvag.name}: saknas"
    return f"{token_sokvag.name}: finns, {token_sokvag.stat().st_size} byte"


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description="Auktorisering mot Gmail.")
    tolk.add_argument(
        "--auktorisera",
        action="store_true",
        help="tillåt webbläsarflödet om token saknas eller inte går att förnya",
    )
    arg = tolk.parse_args(argv)

    print(_status(TOKEN))
    print(f"client_secret.json: {'finns' if CLIENT_SECRET.exists() else 'saknas'}")

    try:
        cred = hamta_credentials(tillat_webblasare=arg.auktorisera)
    except AuthFel as fel:
        print(f"FEL: {fel}")
        return 1

    print(f"giltig: {cred.valid}")
    print("scopes: " + " ".join(sorted(cred.scopes or [])))
    print(_status(TOKEN))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
