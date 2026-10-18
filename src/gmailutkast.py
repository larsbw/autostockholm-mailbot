"""Ett granskat svar som ett UTKAST i Gmail, i kundens tråd. SKICKAR ALDRIG.

Lars §10-beslut i skiva 68: utkastet skapas när Lars trycker på knappen i vyn.
Lars beslut i skiva 69: den dagliga körningen skapar det också, UTAN att någon
läst texten (`scripts/respond.py --gmailutkast`). Spärrarna är då enda skyddet.
Matte öppnar Gmail och trycker skicka.

*Här stod "aldrig av den dagliga körningen". Sant till och med skiva 68.*

FYRA LAGER, OCH DET FÖRSTA FINNS INTE
-------------------------------------

  1  SCOPET        FALLER. `src/auth.py::SKRIVSCOPES` är gmail.compose, och
                   Google säger om det *"Manage drafts and send emails."* Inget
                   scope ger utkast utan sändförmåga. Credentialen i
                   `token-skriv.json` KAN skicka, och det är Googles gräns och
                   inte vår.
  2  TJÄNSTEN      `Utkastjanst` nedan. Bara `users().drafts().create` och,
                   sedan uppdraget 2026-09-25 DEL 1, `users().drafts().delete`
                   går igenom; allt annat kastar `Sandforsok`, också
                   `drafts().send` och `messages().send`.
  3  IMPORTLAGRET  `src/vy.py::GMAILBARANDE_MODULER` namnger modulen. Vyns och
                   kedjans graf når den aldrig: vyn får funktionen INJICERAD av
                   `scripts/serva.py` och importerar ingenting härifrån. Sedan
                   skiva 69 importerar `scripts/respond.py` den.
  4  KÄLLTEXTEN    `FORBJUDET_MONSTER` fäller också `drafts().send`.

**MED LAGER 1 BORTA ÄR LAGER 2 TILL 4 ALLT SOM STÅR EMELLAN**, och de ligger i
vår kod och kan brytas av en rad. Den som bygger en tjänst direkt ur
`auth.bygg_tjanst` med den här credentialen kan skicka. Det kan också den som
når den råa tjänsten genom attributet `_ra`, till exempel
`drafts()._ra.send(...)`: det mönstret fångas inte av lager 4. Samma form som
`inkorg.Lastjanst`.

§6. Modulen tar emot kundens adress och utkastets text och skickar dem till
Gmail. Den skriver ingenting till disk och ingenting till stdout.
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from email.message import EmailMessage

from src import auth

ANVANDARE = "me"

# SKIVA 81, Lars beslut. Mottagaren för LARMUTKASTET, alltid, en
# modulkonstant och aldrig ett argument: se `bygg_larmmeddelande`.
LARMADRESS = "info@autostockholm.se"

# `drafts().create` och `drafts().delete`. UPPDRAG 2026-09-25 DEL 1:
# `delete` tillkom för regnrfiltret, som tar bort ett obesickat utkast i en
# äldre tråd när en nyare förfrågan om samma bil ersätter det. Fortfarande
# INGET SOM SKICKAR: ett borttaget utkast är ett utkast mindre, inte ett
# mail ut.
TILLATNA_ANROP = frozenset({("drafts", "create"), ("drafts", "delete")})

# Ett svar som redan bär ett svarsprefix får inget till. Gmail kräver att
# ämnesraderna matchar, och `Re: Re:` är ingen tråd någon vill läsa.
SVARSPREFIX = re.compile(r"^\s*(?:re|sv)\s*:", re.IGNORECASE)


class Sandforsok(Exception):
    """Något försökte nå en Gmail-resurs som inte är `drafts().create`."""


class EjUtkastbar(Exception):
    """Posten får inte bli ett Gmail-utkast."""


class _Drafts:
    def __init__(self, ra):
        self._ra = ra

    def __getattr__(self, metod: str):
        if ("drafts", metod) not in TILLATNA_ANROP:
            raise Sandforsok(
                f"users().drafts().{metod}() är stängd. Utkastvägen skapar "
                "utkast och gör ingenting annat."
            )
        return getattr(self._ra, metod)


class _Users:
    def __init__(self, ra):
        self._ra = ra

    def drafts(self):
        return _Drafts(self._ra.drafts())

    def __getattr__(self, namn: str):
        # `drafts` är en riktig metod ovan och når aldrig hit. `messages`,
        # `threads`, `settings` och allt annat gör det.
        raise Sandforsok(
            f"users().{namn}() är stängd. Tillåtet: users().drafts().create()."
        )


class Utkastjanst:
    """Gmail-tjänsten med bara `drafts().create` öppet. LAGER 2.

    Spegelvänd mot `src/inkorg.py::Lastjanst`. **DEN HÄR KLASSEN ÄR NU DET
    STARKASTE LAGRET**, eftersom credentialen bakom den kan skicka.
    """

    def __init__(self, ra):
        self._ra = ra

    def users(self):
        return _Users(self._ra.users())


def skriv_tjanst(*, tillat_webblasare: bool = False) -> Utkastjanst:
    """En tjänst som bara kan skapa utkast. Den råa tjänsten lämnar aldrig
    funktionen, samma form som `inkorg.las_tjanst`."""
    cred = auth.hamta_skriv_credentials(tillat_webblasare=tillat_webblasare)
    return Utkastjanst(auth.bygg_tjanst(cred))


def krav_pa_utkastbar(post) -> None:
    """Kastar om posten inte får bli ett Gmail-utkast. DEL C.

    En post får det bara om den bär ett utkast som passerat samtliga spärrar
    och en fullständig svarsväg. `post` är en `vy.Granskningsfall`; modulen
    importerar inte vyn.
    """
    if post.inget_svar:
        raise EjUtkastbar("posten har inget svar")
    if post.sparr:
        raise EjUtkastbar(f"posten är spärrad av {post.sparr}")
    if not post.forslag.strip():
        raise EjUtkastbar("posten bär inget utkast")
    vag = post.svarsvag
    if vag is None:
        raise EjUtkastbar("posten bär ingen svarsväg till en Gmail-tråd")
    for falt in ("trad_id", "meddelande_id", "mottagare", "amne"):
        if not getattr(vag, falt).strip():
            raise EjUtkastbar(f"svarsvägen saknar {falt}")
    if "@" not in vag.mottagare:
        raise EjUtkastbar("mottagaren är ingen adress")


def svarsamne(amne: str) -> str:
    """`Re: ` plus kundens ämne, utan att lägga ett andra prefix."""
    amne = amne.strip()
    return amne if SVARSPREFIX.match(amne) else f"Re: {amne}"


def bygg_meddelande(post) -> dict:
    """`drafts.create`-kroppen: ett svar i kundens tråd.

    AVLÄST 2026-09-16 ur
    https://developers.google.com/workspace/gmail/api/guides/threads : ett
    utkast hamnar i en tråd när `threadId` står på meddelandet, när
    `References` och `In-Reply-To` följer RFC 2822, och när `Subject` matchar.

    **`References` BÄR BARA KUNDMEDDELANDETS `Message-ID`.** RFC 2822 vill ha
    förälderns egen `References` först, men skörden gallrar bort det huvudets
    värde (`inkorg.HUVUDEN_UTAN_VARDE`; före skiva 69 föll hela huvudet). För ett första kundmail, som saknar
    `References`, är formen exakt.

    `From` sätts inte. Gmail använder då kontots egen adress, alltså den
    brevlåda `token-skriv.json` auktoriserades för.
    """
    vag = post.svarsvag
    brev = EmailMessage()
    brev["To"] = vag.mottagare
    brev["Subject"] = svarsamne(vag.amne)
    brev["In-Reply-To"] = vag.meddelande_id
    brev["References"] = vag.meddelande_id
    brev.set_content(post.forslag)
    raa = base64.urlsafe_b64encode(brev.as_bytes()).decode("ascii")
    return {"message": {"raw": raa, "threadId": vag.trad_id}}


def bygg_larmmeddelande(*, regnr: str, kundnamn: str, kundepost: str,
                        datum: str, sparr: str,
                        forsok: list[tuple[str, str]],
                        tradsokvag: str) -> dict:
    """Ett LARMUTKAST när ett ärende spärrats på ALLA genereringsförsök.
    Skiva 81, Lars beslut.

    **MOTTAGAREN ÄR `LARMADRESS`, ALLTID.** Det är en modulkonstant, inte ett
    argument: funktionen tar bara TEXTSTRÄNGAR och en lista av (skäl, sats)
    som brödtext, aldrig ett `Fall`, en `Svarsvag`, en `Arende` eller något
    annat som BÄR en adress eller ett tråd-id. Den kan alltså inte råka rikta
    utkastet mot kunden, eftersom inget kundriktat värde ens kan nå in i
    anropet. `tests/test_gmailutkast.py` binder att `to`-huvudet blir
    `LARMADRESS` oavsett vad `kundepost`, `kundnamn` eller `tradsokvag` bär.

    **INGEN `threadId`, till skillnad från `bygg_meddelande`.** Meddelandet är
    fristående med flit: `skapa_larmutkast` skapar ett NYTT Gmail-meddelande
    och kan därför aldrig landa i kundens tråd, eftersom ingen tråd begärs.

    `forsok` är en lista `(skal, sats)`, ett par per genereringsförsök, äldst
    först — se `kedja.Kedjeutfall.tidigare_forsok` och `.skal`/`.sats`.

    `sparr` är spärrens NAMN (`Kedjeutfall.sparr`, t.ex.
    `genererat-tal-har-kalla`), samma sträng `docs/sparrar.md` katalogiserar
    posten under. §7-granskningsfynd: utan den kunde brödtexten bara peka på
    skälet och satsen, inte på VILKEN spärr det var, fast varje annan yta i
    systemet (terminalen, `logg/beslut.jsonl`) redan namnger den.
    """
    brev = EmailMessage()
    brev["To"] = LARMADRESS
    brev["Subject"] = f"MANUELLT SVAR KRÄVS: {regnr}"
    forsoksrader = "\n\n".join(
        f'Försök {i}:\n  Skäl: {skal}\n  Mening: "{sats}"'
        for i, (skal, sats) in enumerate(forsok, start=1)
    )
    kropp = (
        f"Kund: {kundnamn} <{kundepost}>\n"
        f"Datum: {datum}\n"
        f"Registreringsnummer: {regnr}\n"
        f"Spärr: {sparr}\n\n"
        f"Spärrat på samtliga {len(forsok)} försök:\n\n"
        f"{forsoksrader}\n\n"
        f"Kundens tråd: {tradsokvag}\n"
    )
    brev.set_content(kropp)
    raa = base64.urlsafe_b64encode(brev.as_bytes()).decode("ascii")
    return {"message": {"raw": raa}}


@dataclass(frozen=True)
class UtkastResultat:
    """Vad `skapa_utkast` returnerar. UPPDRAG 2026-09-25 DEL 1.

    **TVÅ OLIKA GMAIL-ID, och det är hela skälet klassen finns.**
    `meddelande_id` är meddelandets, oförändrat sedan skiva 68 och det enda
    som fanns innan: det skrivs i loggen och skrivs ut till terminalen.
    `utkast_id` är UTKASTETS eget id, alltså `drafts().create`-svarets egen
    `id`-nyckel och inte `message.id`. `drafts().delete` tar det förra, inte
    det senare; att blanda ihop dem ger ett `HttpError` mot fel resurs.
    """

    meddelande_id: str
    utkast_id: str


def skapa_utkast(tjanst: Utkastjanst, post) -> UtkastResultat:
    """Skapar utkastet och returnerar dess två Gmail-id, se `UtkastResultat`.

    **TRÅDEN PRÖVAS I SVARET.** Hamnar utkastet i en annan tråd än den begärda,
    till exempel för att token auktoriserades för fel konto, kastar funktionen
    med utkastets id, så att det går att hitta och ta bort.
    """
    krav_pa_utkastbar(post)
    svar = tjanst.users().drafts().create(
        userId=ANVANDARE, body=bygg_meddelande(post)
    ).execute()
    meddelande = svar.get("message") or {}
    if meddelande.get("threadId") != post.svarsvag.trad_id:
        raise EjUtkastbar(
            f"utkastet {svar.get('id')!r} hamnade i tråd "
            f"{meddelande.get('threadId')!r}, inte i kundens. Ta bort det i "
            "Gmail och kontrollera att token-skriv.json gäller "
            "info@autostockholm.se."
        )
    return UtkastResultat(meddelande_id=meddelande["id"], utkast_id=svar["id"])


def skapa_larmutkast(tjanst: Utkastjanst, **kwargs) -> UtkastResultat:
    """Skapar larmutkastet. Skiva 81. Samma tjänst och samma lager som
    `skapa_utkast`: `TILLATNA_ANROP` skiljer inte på de två, för `drafts()`
    bryr sig aldrig om VILKET meddelande som skapas.

    **INGEN TRÅDKONTROLL**, till skillnad från `skapa_utkast`. Det finns ingen
    begärd tråd att jämföra svaret mot: `bygg_larmmeddelande` sätter aldrig
    `threadId`, med flit.

    `kwargs` går rakt till `bygg_larmmeddelande`, oförändrade.
    """
    svar = tjanst.users().drafts().create(
        userId=ANVANDARE, body=bygg_larmmeddelande(**kwargs)
    ).execute()
    meddelande = svar.get("message") or {}
    return UtkastResultat(meddelande_id=meddelande.get("id", ""),
                          utkast_id=svar["id"])


def ta_bort_utkast(tjanst: Utkastjanst, utkast_id: str) -> None:
    """Tar bort ETT obesickat utkast. UPPDRAG 2026-09-25 DEL 1.

    `utkast_id` är UTKASTETS id, inte meddelandets, se `UtkastResultat`.

    AVLÄST 2026-09-25 ur
    https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.drafts/delete
    : ett lyckat anrop ger ett TOMT svar, alltså ingen kvittens att verifiera
    mot, till skillnad från `skapa_utkast`. Sidan säger INGET om vad ett
    utkast som redan är borta (skickat av Matte, eller borttaget för hand i
    Gmail) ger för fel eller statuskod. Ett antagande om 404 här hade varit
    en gissning §1 förbjuder. Funktionen kastar därför vidare vad anropet än
    ger; anroparen avgör om ett fel för ett redan-borta utkast ska tystas.
    """
    tjanst.users().drafts().delete(userId=ANVANDARE, id=utkast_id).execute()


def utkastskapare(*, tjanst: Utkastjanst | None = None):
    """Funktionen vyn får injicerad. Tjänsten byggs vid första trycket.

    Vyn kör utan `token-skriv.json`, och då fälls först knapptrycket och inte
    uppstarten.
    """
    cache: list[Utkastjanst] = [] if tjanst is None else [tjanst]

    def skapa(post) -> UtkastResultat:
        if not cache:
            cache.append(skriv_tjanst())
        return skapa_utkast(cache[0], post)

    return skapa


def larmutkastskapare(*, tjanst: Utkastjanst | None = None):
    """Motsvarigheten till `utkastskapare`, för larmutkastet. Skiva 81.

    Samma cache-mönster: en tjänst byggs vid FÖRSTA larmet, inte vid
    uppstarten, av samma skäl `utkastskapare`s docstring ger.
    """
    cache: list[Utkastjanst] = [] if tjanst is None else [tjanst]

    def larma(**kwargs) -> UtkastResultat:
        if not cache:
            cache.append(skriv_tjanst())
        return skapa_larmutkast(cache[0], **kwargs)

    return larma
