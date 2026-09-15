"""OAuth-desktopflöde mot Gmail för info@autostockholm.se.

TVÅ SCOPELISTOR OCH TVÅ TOKEN. `SCOPES` är miningens och fas 7:s, låst till
gmail.modify och gmail.send. `LASSCOPES` är skugglägets, gmail.readonly och
ingenting annat. Ett nytt scope är ett §10-stopp och läggs aldrig till av kod;
`LASSCOPES` tillkom på Lars uttryckliga beslut i skiva 48.

*Här stod att scopelistan är låst till gmail.modify och gmail.send, i singular.
Det blev falskt av samma skiva som skrev den andra listan.*

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

# SKUGGLÄGETS SCOPE. Lars §10-beslut i skiva 48.
#
# **DET HÄR ÄR DET ENDA LAGRET GOOGLE UPPRÄTTHÅLLER.** De andra tre ligger i vår
# kod och kan brytas av en rad; det här vägrar på serversidan. Lars ordagranna
# skäl: sändförmågan ska inte finnas, inte vara bortbyggd.
#
# AVLÄST 2026-09-15 ur
# https://developers.google.com/workspace/gmail/api/auth/scopes :
#
#   gmail.readonly  "View your email messages and settings."   restricted
#   gmail.modify    "Read, compose, and send emails from your Gmail account.
#                    This scope does not allow immediate, permanent deletion of
#                    threads and messages, bypassing the trash."   restricted
#   gmail.send      "Send email on your behalf."   sensitive
#
# **`gmail.modify` TILLÅTER ALLTSÅ SÄNDNING**, och det är hela skälet att det
# inte räcker att utelämna `gmail.send`. Det nuvarande tokenet bär TVÅ av
# varandra oberoende vägar ut, och läsatokenet tar bort båda.
LASSCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
]

ROT = Path(__file__).resolve().parent.parent
CLIENT_SECRET = ROT / "client_secret.json"
TOKEN = ROT / "token.json"

# SKILD FIL, INTE SAMMA. Två auktoriseringar med olika scope kan inte dela
# token: `_las_token` prövar `has_scopes` mot det filen bär, och en skrivning
# hade skrivit över den andra. Filen är gitignorerad på samma villkor som
# `token.json`.
LASTOKEN = ROT / "token-las.json"


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
        # KOMMANDOT I MEDDELANDET MÅSTE MATCHA SCOPET SOM BEGÄRDES. Raden bar
        # `--auktorisera` utan `--las` oavsett vilken token som saknades, alltså
        # anvisade den läsvägens användare att auktorisera om med gmail.modify
        # och gmail.send. Ett felmeddelande som leder till fel scope är värre än
        # inget felmeddelande.
        flagga = " --las" if token_sokvag == LASTOKEN else ""
        raise AuthFel(
            f"Ingen giltig eller förnybar token i {token_sokvag.name}. "
            "Auktorisering kräver webbläsare och är ett §10-stopp: kör "
            f"`.venv/bin/python -m src.auth{flagga} --auktorisera` efter Lars "
            "beslut."
        )

    if not client_secret.exists():
        raise AuthFel(f"Hittar inte {client_secret.name} i repots rot.")

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secret), scopes)
    cred = flow.run_local_server(port=0)
    _skriv_token(cred, token_sokvag)
    return cred


class Sandformaga(Exception):
    """Credentialen bär ett scope som kan skicka mail."""


def krav_pa_bara_lasning(cred: Credentials) -> None:
    """Kastar om credentialen bär något annat scope än `LASSCOPES`.

    **PRÖVNINGEN ÄR EN TILLÅTNINGSLISTA OCH INTE EN FÖRBUDSLISTA, och det är
    avsiktligt.** En förbudslista hade krävt att vi vet vilka av Gmails scope som
    kan skicka, och den kunskapen är en avläsning som åldras: `gmail.modify` och
    `gmail.send` är de två jag läst 2026-09-15, men listan är inte uttömmande
    prövad och ett scope vi inte känner till hade sluppit igenom. En exakt
    likhet mot `LASSCOPES` behöver ingen sådan kunskap.

    **DEN HÄR RADEN ÄR INTE GARANTIN, den är larmet.** `cred.scopes` kommer ur
    vår egen tokenfil och säger vad Google BEVILJADE enligt filen, inte vad
    Google faktiskt kommer att acceptera. Garantin är serversidans: ett
    `messages.send` med ett readonly-token avvisas av Google oavsett vad filen
    påstår. Kontrollen finns för att ett fel ska synas här, vid uppstart, i
    stället för som ett 403 mitt i en körning.
    """
    beviljade = set(cred.scopes or [])
    if beviljade != set(LASSCOPES):
        raise Sandformaga(
            f"credentialen bär {sorted(beviljade)}, inte {sorted(LASSCOPES)}. "
            "Skuggläget läser med ett token som inte kan skicka. Kör "
            "`.venv/bin/python -m src.auth --las --auktorisera`."
        )


def hamta_las_credentials(
    *,
    tillat_webblasare: bool = False,
    token_sokvag: Path = LASTOKEN,
    client_secret: Path = CLIENT_SECRET,
) -> Credentials:
    """Credentials som BARA kan läsa. Skugglägets enda väg till Gmail.

    **`scopes` ÄR INGEN PARAMETER HÄR, och det är hela poängen.**
    `hamta_credentials` tar scopelistan som argument, alltså kan en anropare be
    om vad som helst. Den här funktionen kan inte ombes om något annat än
    `LASSCOPES`, och prövar dessutom utfallet: pekar någon `token_sokvag` mot
    `token.json` faller `krav_pa_bara_lasning` i stället för att ge en
    sändförmögen credential till en läsväg.
    """
    cred = hamta_credentials(
        tillat_webblasare=tillat_webblasare,
        token_sokvag=token_sokvag,
        client_secret=client_secret,
        scopes=LASSCOPES,
    )
    krav_pa_bara_lasning(cred)
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
    tolk.add_argument(
        "--las",
        action="store_true",
        help="skuggläget: gmail.readonly mot token-las.json, i stället för "
             "gmail.modify och gmail.send mot token.json",
    )
    arg = tolk.parse_args(argv)

    token = LASTOKEN if arg.las else TOKEN
    print(_status(token))
    print(f"client_secret.json: {'finns' if CLIENT_SECRET.exists() else 'saknas'}")
    print("begär scopes: " + " ".join(LASSCOPES if arg.las else SCOPES))

    try:
        if arg.las:
            cred = hamta_las_credentials(tillat_webblasare=arg.auktorisera)
        else:
            cred = hamta_credentials(tillat_webblasare=arg.auktorisera)
    except (AuthFel, Sandformaga) as fel:
        print(f"FEL: {fel}")
        return 1

    print(f"giltig: {cred.valid}")
    print("scopes: " + " ".join(sorted(cred.scopes or [])))
    print(_status(token))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
