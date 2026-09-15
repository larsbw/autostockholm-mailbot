"""SIGN IN WITH GOOGLE FÖR VYN. `docs/beslutslogg.md` #37, byggd i skiva 53.

Vyn visar rå kundtext. Fram till den här skivan hindrades omvärlden av EN sak:
`starta` band `127.0.0.1`, alltså tog servern inte emot något från nätet.
§7-granskningen av skiva 27 fällde att påståendet dessförinnan var ovaktat.
`test_servern_binder_bara_loopback` vaktar numera FÖRVALET och inte en absolut
spärr: bindningen går att vidga, och det är den här modulen som är villkoret.

**NÄR VYN SKA NÅS UTIFRÅN FÖRSVINNER DEN SPÄRREN, och den här modulen är det
som ersätter den.** Det är ett byte av ett starkt skydd mot ett svagare, och
därför binder `vy.starta` att bindningen INTE får vidgas utan att en inloggning
är konfigurerad. Se `vy.krav_pa_inloggning_utanfor_loopback`.

DEN HÄR MODULEN FÅR ALDRIG IMPORTERA `src.auth` ELLER `googleapiclient`
--------------------------------------------------------------------

`vy.FORBJUDNA_MODULER` bär båda, och `vy.krav_pa_sandvagsfrihet` körs utan
undantag för vyns egen graf. Inloggningen ligger i vyns graf, alltså gäller
spärren den. Det är avsiktligt: en inloggningsmodul har inget ärende till Gmail.

**KOD-FLÖDET, och inte implicit.** Implicit flöde lägger tokenet i en
fragment-del som aldrig når servern, och kräver att webbläsaren är betrodd.
Koden byts mot ett id_token på serversidan, över TLS, mot Googles
tokenslutpunkt, med vår klienthemlighet.

TRE LED SOM ALLA MÅSTE HÅLLA
----------------------------

  1  `hd`          Googles egen organisationskontroll. Skickas i begäran OCH
                   prövas i svaret. Bara det andra ledet bär: parametern i
                   begäran är en ledtrådsparameter som en angripare kan ändra.
  2  `email`       Måste vara exakt `INLOGGAD_ADRESS`. #37 säger att
                   inloggningen sker som info@autostockholm.se och som ingen
                   annan. INGEN WHITELIST, och det här är skälet: det finns
                   ingen lista, det finns en adress.
  3  `state`       CSRF. En slumpad sträng i kakan som ska komma tillbaka
                   oförändrad, annars var det inte vi som startade flödet.

**`email_verified` PRÖVAS OCKSÅ.** En Workspace-adress är alltid verifierad,
men ledet kostar en rad och tar bort ett antagande.

SCOPE: `openid email`, OCH INGENTING MER
----------------------------------------

Lars §10-beslut i skiva 53. `profile` begärs INTE: det hämtas bara för att kunna
visa ett namn, och med ett delat konto finns inget namn att visa. Vyn skriver
adressen i stället, vilket är det enda den vet och det enda den behöver veta.

Det är samma princip som `src/auth.py::LASSCOPES`: miljön får det den behöver
och inget annat.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass

from src import sokvagar

# ADRESSEN SOM FÅR LOGGA IN. #37, och den är EN.
INLOGGAD_ADRESS = "info@autostockholm.se"

# ORGANISATIONEN. Skickas som `hd` i begäran och prövas i svarets anspråk.
ORGANISATION = "autostockholm.se"

SCOPES = ["openid", "email"]

AUKTORISERINGSSLUTPUNKT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKENSLUTPUNKT = "https://oauth2.googleapis.com/token"

# GILTIGA UTFÄRDARE. Google skriver båda formerna, och båda är giltiga.
UTFARDARE = frozenset({"accounts.google.com", "https://accounts.google.com"})

# HUR LÄNGE EN SESSION GÄLLER. Åtta timmar är en arbetsdag: Lars loggar in på
# morgonen och slipper göra om det, och en glömd flik i en lånad webbläsare dör
# samma dag. Talet är VALT och inte mätt.
SESSION_SEKUNDER = 8 * 60 * 60

# Hur länge ett påbörjat inloggningsflöde får ta innan `state` anses för gammalt.
FLODE_SEKUNDER = 10 * 60

KAKA_SESSION = "mailbot_session"
KAKA_STATE = "mailbot_state"


class Inloggningsfel(Exception):
    """Inloggningen gick inte att slutföra. Aldrig ett tyst nej."""


class Konfigurationsfel(Exception):
    """Inloggningen är inte konfigurerad, alltså kan vyn inte öppnas utåt."""


@dataclass(frozen=True)
class Konfiguration:
    """Det inloggningen behöver. Byggs ur miljön, aldrig ur en fil i repot.

    **KLIENTHEMLIGHETEN KOMMER UR MILJÖN OCH INTE UR `client_secret.json`.**
    Den filen är desktopklientens, `mailbot-cli`, och #37 kräver en EGEN klient
    av typen Web application. Två klienter ska inte dela fil, av samma skäl som
    `token.json` och `token-las.json` inte delar fil.
    """

    klient_id: str
    klient_hemlighet: str
    omdirigering: str
    sessionsnyckel: bytes

    @property
    def maskerad(self) -> str:
        """Klient-id:t i en form som går att känna igen men inte återanvända.

        §6: en hemlighet skrivs aldrig ut i upplöst form. Klient-id:t är inte
        en hemlighet i OAuth:s mening, men det hör ihop med en som är det, och
        en maskerad form räcker för att se VILKEN klient som är inställd.
        """
        if len(self.klient_id) <= 12:
            return "***"
        return f"{self.klient_id[:8]}…{self.klient_id[-4:]}"


def ur_miljon() -> Konfiguration | None:
    """Konfigurationen ur miljön, eller None när inloggning inte är inställd.

    **NONE OCH INTE ETT UNDANTAG, och skillnaden är driftläget.** Lokalt körs
    vyn utan inloggning mot `127.0.0.1`, precis som före skivan, och då ska
    ingenting kasta. Det är `vy.starta` som avgör att None inte duger när
    bindningen vidgas.

    Fyra variabler, och ALLA fyra krävs. En halvt ifylld konfiguration är ett
    driftfel som ska synas vid uppstart och inte som ett 500 vid första
    inloggningsförsöket.
    """
    klient_id = (os.environ.get("MAILBOT_OAUTH_KLIENT_ID") or "").strip()
    hemlighet = (os.environ.get("MAILBOT_OAUTH_KLIENT_HEMLIGHET") or "").strip()
    omdirigering = (os.environ.get("MAILBOT_OAUTH_OMDIRIGERING") or "").strip()
    nyckel = (os.environ.get("MAILBOT_SESSIONSNYCKEL") or "").strip()

    if not any([klient_id, hemlighet, omdirigering, nyckel]):
        return None

    saknas = [
        namn
        for namn, varde in [
            ("MAILBOT_OAUTH_KLIENT_ID", klient_id),
            ("MAILBOT_OAUTH_KLIENT_HEMLIGHET", hemlighet),
            ("MAILBOT_OAUTH_OMDIRIGERING", omdirigering),
            ("MAILBOT_SESSIONSNYCKEL", nyckel),
        ]
        if not varde
    ]
    if saknas:
        raise Konfigurationsfel(
            "inloggningen är halvt konfigurerad, dessa saknas: "
            + ", ".join(saknas)
        )

    # **NYCKELN MÅSTE VARA LÅNG NOG.** En kort nyckel går att gissa, och då är
    # sessionskakan förfalskningsbar, alltså är inloggningen verkningslös. 32
    # tecken är VALT: det är längden på `secrets.token_urlsafe(24)`.
    if len(nyckel) < 32:
        raise Konfigurationsfel(
            f"MAILBOT_SESSIONSNYCKEL är {len(nyckel)} tecken, minst 32 krävs. "
            "Skapa en med: python -c \"import secrets; "
            "print(secrets.token_urlsafe(32))\""
        )

    if not omdirigering.startswith("https://"):
        # **HTTPS KRÄVS, och skälet är kakan.** Sessionskakan sätts med
        # `Secure`, alltså skickas den aldrig över en okrypterad förbindelse.
        # En omdirigering över http hade gett en inloggning som ser ut att
        # lyckas och en session som aldrig följer med.
        raise Konfigurationsfel(
            f"MAILBOT_OAUTH_OMDIRIGERING måste vara https, är {omdirigering!r}"
        )

    return Konfiguration(
        klient_id=klient_id,
        klient_hemlighet=hemlighet,
        omdirigering=omdirigering,
        sessionsnyckel=nyckel.encode("utf-8"),
    )


def _b64url_avkoda(text: str) -> bytes:
    """Base64url utan utfyllnad, som JWT skriver den."""
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def anspraken_ur(id_token: str) -> dict:
    """JWT:ns nyttolast som en dict.

    **SIGNATUREN PRÖVAS INTE HÄR, och det är en medveten avgränsning som bara
    håller i ETT läge.** Tokenet hämtas av `vaxla_kod` direkt från Googles
    tokenslutpunkt över TLS, med vår klienthemlighet. Det är den enda vägen in i
    den här funktionen, och OpenID Connect säger uttryckligen att ett token som
    tas emot så inte behöver signaturprövas: kanalen är beviset.

    **DEN DAGEN ETT id_token KOMMER NÅGON ANNAN VÄG HÅLLER DET INTE.** Ett token
    ur en omdirigering, ur en kaka eller ur en begäran är inte betrott, och då
    krävs signaturprövning mot Googles JWKS. `vaxla_kod` är därför enda
    anroparen, och `test_id_token_kommer_BARA_ur_tokenslutpunkten` binder det.
    """
    delar = id_token.split(".")
    if len(delar) != 3:
        raise Inloggningsfel("id_token har inte tre delar")
    try:
        return json.loads(_b64url_avkoda(delar[1]))
    except (ValueError, json.JSONDecodeError) as fel:
        raise Inloggningsfel(f"id_token går inte att tolka: {fel}") from None


def krav_pa_anspraken(anspraken: dict, konfiguration: Konfiguration,
                      nu: float | None = None) -> str:
    """Prövar anspråken och returnerar adressen. Kastar annars.

    **VARJE LED ÄR EN EGEN RAD, så att vart och ett går att fälla för sig**
    (§7.1). Fälls två tillsammans och sviten blir röd vet man bara att minst ett
    bär.
    """
    nu = time.time() if nu is None else nu

    if anspraken.get("iss") not in UTFARDARE:
        raise Inloggningsfel(f"fel utfärdare: {anspraken.get('iss')!r}")

    if anspraken.get("aud") != konfiguration.klient_id:
        # Tokenet är utfärdat för en ANNAN klient. Utan det här ledet duger ett
        # token från vilken Google-app som helst.
        raise Inloggningsfel("id_token är utfärdat för en annan klient")

    utgang = anspraken.get("exp")
    if not isinstance(utgang, (int, float)) or utgang <= nu:
        raise Inloggningsfel("id_token har gått ut")

    if anspraken.get("hd") != ORGANISATION:
        # LED 1 av tre. Googles `hd` i SVARET, inte parametern i begäran.
        raise Inloggningsfel(
            f"kontot tillhör inte {ORGANISATION}: hd={anspraken.get('hd')!r}"
        )

    if anspraken.get("email_verified") is not True:
        raise Inloggningsfel("adressen är inte verifierad")

    adress = (anspraken.get("email") or "").lower()
    if adress != INLOGGAD_ADRESS:
        # LED 2 av tre. #37: inloggningen sker som info@ och som ingen annan.
        raise Inloggningsfel(
            f"{adress!r} får inte logga in, bara {INLOGGAD_ADRESS}"
        )

    return adress


def auktoriseringsadress(konfiguration: Konfiguration, state: str) -> str:
    """URL:en att skicka användaren till.

    `prompt=select_account` gör att en inloggad privat Google-identitet inte
    tyst används: Lars ska kunna välja info@ även när webbläsaren redan är
    inloggad som någon annan.
    """
    falt = {
        "client_id": konfiguration.klient_id,
        "redirect_uri": konfiguration.omdirigering,
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "state": state,
        "hd": ORGANISATION,
        "prompt": "select_account",
    }
    return AUKTORISERINGSSLUTPUNKT + "?" + urllib.parse.urlencode(falt)


def vaxla_kod(kod: str, konfiguration: Konfiguration,
              oppna=None) -> dict:
    """Byter koden mot anspråken hos Google. Enda vägen till ett id_token.

    `oppna` finns för testet och är `urllib.request.urlopen` i drift. Det är en
    parameter och inte en modulnivåkrok, så att ingen annan anropare kan byta ut
    den i efterhand.
    """
    oppna = urllib.request.urlopen if oppna is None else oppna

    kropp = urllib.parse.urlencode({
        "code": kod,
        "client_id": konfiguration.klient_id,
        "client_secret": konfiguration.klient_hemlighet,
        "redirect_uri": konfiguration.omdirigering,
        "grant_type": "authorization_code",
    }).encode("utf-8")

    begaran = urllib.request.Request(
        TOKENSLUTPUNKT,
        data=kropp,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with oppna(begaran, timeout=20) as svar:
            nyttolast = json.loads(svar.read().decode("utf-8"))
    except Exception as fel:
        # §6: felet kan bära kroppen i sin text, och kroppen bär vår
        # klienthemlighet i begäran. Bara typen återges.
        raise Inloggningsfel(
            f"tokenutbytet misslyckades ({type(fel).__name__})"
        ) from None

    id_token = nyttolast.get("id_token")
    if not id_token:
        raise Inloggningsfel("svaret från Google bar inget id_token")

    return anspraken_ur(id_token)


def _signera(nyttolast: str, nyckel: bytes) -> str:
    return hmac.new(nyckel, nyttolast.encode("utf-8"), hashlib.sha256).hexdigest()


def skapa_session(adress: str, konfiguration: Konfiguration,
                  nu: float | None = None) -> str:
    """En signerad sessionssträng: adress, utgång, signatur."""
    nu = time.time() if nu is None else nu
    nyttolast = f"{adress}|{int(nu + SESSION_SEKUNDER)}"
    return f"{nyttolast}|{_signera(nyttolast, konfiguration.sessionsnyckel)}"


def las_session(kaka: str, konfiguration: Konfiguration,
                nu: float | None = None) -> str | None:
    """Adressen ur en giltig sessionskaka, annars None.

    **SIGNATUREN JÄMFÖRS MED `compare_digest`.** En vanlig `==` läcker hur många
    tecken som stämde genom hur lång tid jämförelsen tar.

    **UTGÅNGEN PRÖVAS EFTER SIGNATUREN.** Prövades den före kunde en angripare
    mäta skillnaden mellan en utgången och en osignerad kaka.
    """
    if not kaka:
        return None

    nu = time.time() if nu is None else nu
    delar = kaka.split("|")
    if len(delar) != 3:
        return None

    adress, utgang, signatur = delar
    vantad = _signera(f"{adress}|{utgang}", konfiguration.sessionsnyckel)
    if not hmac.compare_digest(signatur, vantad):
        return None

    try:
        if int(utgang) <= nu:
            return None
    except ValueError:
        return None

    # **ADRESSEN PRÖVAS EN GÅNG TILL, och det är inte överflödigt.** Kakan är
    # signerad med vår nyckel, alltså är adressen äkta. Men om `INLOGGAD_ADRESS`
    # ändras ska varje redan utfärdad kaka för den gamla adressen sluta gälla,
    # och utan den här raden gäller den tills den går ut.
    if adress != INLOGGAD_ADRESS:
        return None

    return adress


def ny_state() -> str:
    """En slumpad CSRF-sträng med sin tidsstämpel."""
    return f"{secrets.token_urlsafe(24)}.{int(time.time())}"


def state_stammer(ur_kakan: str, ur_svaret: str, nu: float | None = None) -> bool:
    """LED 3 av tre. Jämför CSRF-strängen och prövar dess ålder.

    `compare_digest` av samma skäl som i `las_session`.
    """
    if not ur_kakan or not ur_svaret:
        return False
    if not hmac.compare_digest(ur_kakan, ur_svaret):
        return False

    nu = time.time() if nu is None else nu
    _, _, stampel = ur_kakan.partition(".")
    try:
        return int(stampel) > nu - FLODE_SEKUNDER
    except ValueError:
        return False


def kaksats(namn: str, varde: str, sekunder: int) -> str:
    """En `Set-Cookie`-rad med samtliga skydd påslagna.

    `HttpOnly` gör kakan oläslig för JavaScript, `Secure` skickar den bara över
    TLS, och `SameSite=Lax` gör att den inte följer med en begäran som en annan
    sida startar. Lax och inte Strict: Strict hade gjort att kakan inte följer
    med tillbaka från Googles omdirigering.
    """
    return (
        f"{namn}={varde}; Max-Age={sekunder}; Path=/; "
        "HttpOnly; Secure; SameSite=Lax"
    )


def kaka_ur(huvud: str, namn: str) -> str:
    """Värdet för `namn` ur ett `Cookie`-huvud, eller tom sträng."""
    for bit in (huvud or "").split(";"):
        etikett, _, varde = bit.strip().partition("=")
        if etikett == namn:
            return varde
    return ""


def status() -> str:
    """En rad om inloggningens läge, för uppstartsutskriften. Aldrig en hemlighet."""
    try:
        konfiguration = ur_miljon()
    except Konfigurationsfel as fel:
        return f"inloggning: TRASIG KONFIGURATION, {fel}"
    if konfiguration is None:
        return "inloggning: AV, vyn får bara binda 127.0.0.1"
    return (
        f"inloggning: PÅ, klient {konfiguration.maskerad}, "
        f"som {INLOGGAD_ADRESS}, hemligheter i {sokvagar.HEMLIGHETER}"
    )
