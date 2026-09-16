"""Ett granskat svar som ett UTKAST i Gmail, i kundens tråd. SKICKAR ALDRIG.

Lars §10-beslut i skiva 68. Utkastet skapas när Lars trycker på knappen i vyn,
aldrig av den dagliga körningen. Matte öppnar Gmail, läser och trycker skicka.

FYRA LAGER, OCH DET FÖRSTA FINNS INTE
-------------------------------------

  1  SCOPET        FALLER. `src/auth.py::SKRIVSCOPES` är gmail.compose, och
                   Google säger om det *"Manage drafts and send emails."* Inget
                   scope ger utkast utan sändförmåga. Credentialen i
                   `token-skriv.json` KAN skicka, och det är Googles gräns och
                   inte vår.
  2  TJÄNSTEN      `Utkastjanst` nedan. Bara `users().drafts().create` går
                   igenom; allt annat kastar `Sandforsok`, också
                   `drafts().send` och `messages().send`.
  3  IMPORTLAGRET  `src/vy.py::GMAILBARANDE_MODULER` namnger modulen. Vyns och
                   kedjans graf når den aldrig: vyn får funktionen INJICERAD av
                   `scripts/serva.py` och importerar ingenting härifrån.
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
from email.message import EmailMessage

from src import auth

ANVANDARE = "me"

# `drafts().create` och inget annat.
TILLATNA_ANROP = frozenset({("drafts", "create")})

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
    förälderns egen `References` först, men skörden gallrar bort det huvudet
    (`inkorg.HUVUDEN_SOM_LASES`). För ett första kundmail, som saknar
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


def skapa_utkast(tjanst: Utkastjanst, post) -> str:
    """Skapar utkastet och returnerar Gmails meddelande-id.

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
    return meddelande["id"]


def utkastskapare(*, tjanst: Utkastjanst | None = None):
    """Funktionen vyn får injicerad. Tjänsten byggs vid första trycket.

    Vyn kör utan `token-skriv.json`, och då fälls först knapptrycket och inte
    uppstarten.
    """
    cache: list[Utkastjanst] = [] if tjanst is None else [tjanst]

    def skapa(post) -> str:
        if not cache:
            cache.append(skriv_tjanst())
        return skapa_utkast(cache[0], post)

    return skapa
