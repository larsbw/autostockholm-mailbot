"""Urvalsregler och textutvinning ur Gmail-trådar.

Reglerna bor här och inte i ett verktyg, eftersom `src/extract.py` och
`scripts/tradstruktur.py` måste tillämpa EXAKT samma urval. Två kopior hade
drivit isär, och det var precis ett saknat villkor som gjorde talet i
beslutslogg #7 fel.

Spärren heter `urval-gmail-svar` och står i `docs/sparrar.md` med sina lager.
Kriterierna kommer ur `docs/beslutslogg.md` #5, #6 och #8.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import html
import re
from email.utils import getaddresses

# Huvuden som bara finns på post som PASSERAT INKOMMANDE LEVERANS. Ett mail som
# skrivits i Gmail och skickats därifrån har dem inte.
LEVERANSHUVUDEN = {"received", "delivered-to", "return-path", "received-spf"}

# Huvuden som ett SVAR bär, till skillnad från ett första mail.
SVARSHUVUDEN = {"in-reply-to", "references"}

MOTTAGARHUVUDEN = {"to", "cc", "bcc"}

# Brevlådan själv, ur CLAUDE.md §0.
BREVLADA = "info@autostockholm.se"

# Bara det YTTERSTA prefixet avgör. `Fwd: X` är en vidarebefordran vi skickat,
# `Re: Fwd: X` är ett svar på något som vidarebefordrats till oss.
VIDAREPREFIX = re.compile(r"^\s*(?:vb|fwd|fw)\s*:", re.IGNORECASE)


def huvuden(meddelande: dict) -> list[tuple[str, str]]:
    return [
        (h.get("name", ""), h.get("value", ""))
        for h in meddelande.get("payload", {}).get("headers", [])
    ]


def huvudnamn(meddelande: dict) -> set[str]:
    return {namn.lower() for namn, _ in huvuden(meddelande)}


def huvudvarde(meddelande: dict, sokt: str) -> str:
    """Första träffen. Huvudnamn är inte unika (beslutslogg #6), och den som
    behöver alla värden ska iterera själv."""
    for namn, varde in huvuden(meddelande):
        if namn.lower() == sokt.lower():
            return varde
    return ""


def adresser(meddelande: dict, namn: set[str]) -> set[str]:
    ut = set()
    for huvud, varde in huvuden(meddelande):
        if huvud.lower() in namn:
            for _, adress in getaddresses([varde]):
                if adress:
                    ut.add(adress.lower())
    return ut


def ar_gmail_svar(meddelande: dict) -> bool:
    """Sant för det som får bli HÖGER sida i ett par: ett svar skrivet i Gmail
    till en kund. Villkoren och deras skäl står i `docs/sparrar.md`."""
    if "SENT" not in (meddelande.get("labelIds") or []):
        return False

    namn = huvudnamn(meddelande)
    if namn & LEVERANSHUVUDEN:
        return False
    if not SVARSHUVUDEN <= namn:
        return False

    typ = meddelande.get("payload", {}).get("mimeType", "")
    if typ.startswith("multipart/report"):
        return False

    if not adresser(meddelande, MOTTAGARHUVUDEN) - {BREVLADA}:
        return False

    return not VIDAREPREFIX.match(huvudvarde(meddelande, "subject"))


# Huvuden som bara massutskick och automatik bär. Ett nyhetsbrev, en
# Google-notis eller ett ordererkännande är inte ett kundärende, och en
# klustring som inte sållar bort dem grupperar mail på avsändarens
# mallformgivning i stället för på vad kunden vill.
MASSUTSKICKSHUVUDEN = {
    "list-unsubscribe", "list-id", "list-post", "precedence",
    "auto-submitted", "x-campaign-id", "x-mailer-lid", "feedback-id",
    "x-csa-complaints", "x-report-abuse",
}


def ar_massutskick(meddelande: dict) -> bool:
    """Sant för post som är utskickad till många, eller genererad av ett system.

    Villkoret prövar HUVUDEN och inte avsändaradress: en domänlista hade
    behövt underhållas och hade blivit fel vid första nya avsändaren, medan
    `List-Unsubscribe` finns just därför att utskicket självt deklarerar vad
    det är.
    """
    namn = huvudnamn(meddelande)
    if namn & MASSUTSKICKSHUVUDEN:
        return True
    return huvudvarde(meddelande, "precedence").lower() in {"bulk", "list",
                                                            "junk"}


def ar_kundmeddelande(meddelande: dict) -> bool:
    """Sant för det som får bli VÄNSTER sida: kundens text.

    Formulärnotisen bär `SENT` men har passerat inkommande leverans, och
    innehåller kundens ärende. Att kräva frånvaro av `SENT` uteslöt hela den
    sortens par (beslutslogg #8).
    """
    if "SENT" not in (meddelande.get("labelIds") or []):
        return True
    return bool(huvudnamn(meddelande) & LEVERANSHUVUDEN)


def kundadress(meddelande: dict) -> str:
    """Kundens adress. För en formulärnotis står den i `Reply-To`, eftersom
    `From` då är brevlådan själv."""
    for huvud in ("reply-to", "from"):
        for adress in sorted(adresser(meddelande, {huvud})):
            if adress != BREVLADA:
                return adress
    return ""


def hasha(adress: str) -> str:
    """§6: adressen skrivs aldrig ut. Hashen är stabil mellan körningar, så att
    samma kund går att känna igen utan att kunna läsas."""
    return hashlib.sha256(adress.strip().lower().encode("utf-8")).hexdigest()


# --- textutvinning -----------------------------------------------------------

_TAGG = re.compile(r"<[^>]+>")
_BLOCKSLUT = re.compile(r"</(?:p|div|br|tr|li|h[1-6])\s*>", re.IGNORECASE)
_BR = re.compile(r"<br\s*/?>", re.IGNORECASE)
# style och script bär INNEHÅLL som inte är text. Tas de inte bort före
# taggborttagningen blir CSS-regler och skriptkod till "ord", och en klustring
# på sådant material grupperar mail på mallens formgivning i stället för på
# ärendet.
_EJ_TEXT = re.compile(r"<(style|script)\b.*?</\1\s*>", re.IGNORECASE | re.DOTALL)
_KOMMENTAR = re.compile(r"<!--.*?-->", re.DOTALL)

# Rader som inleder citerad historik. Gmail och Outlook, svenska och engelska.
_CITATSTART = re.compile(
    r"^\s*(?:"
    r">|"
    # Gmails citatrad: "Den 3 mars 2026 kl 10:00 skrev Namn <adress>:"
    # Kolonet står EFTER avsändaren, inte efter verbet.
    r"(?:Den|On)\s.*\b(?:skrev|wrote)\b.*:\s*$|"
    r"-{2,}\s*(?:Ursprungligt meddelande|Original Message|Forwarded message)|"
    r"(?:Från|From)\s*:\s.{0,120}$"
    r")",
    re.IGNORECASE,
)


def _platta(del_: dict) -> list[dict]:
    delar = [del_]
    for underdel in del_.get("parts", []) or []:
        delar.extend(_platta(underdel))
    return delar


def _avkoda(data: str) -> str:
    # Gmail använder base64url utan utfyllnad. `===` är alltid nog, och
    # b64decode ignorerar överskottet.
    try:
        rabyte = base64.urlsafe_b64decode(data + "===")
    except (binascii.Error, ValueError):
        return ""
    return rabyte.decode("utf-8", "replace")


def _text_ur_html(rahtml: str) -> str:
    utan_skript = _EJ_TEXT.sub(" ", rahtml)
    utan_kommentar = _KOMMENTAR.sub(" ", utan_skript)
    utan_br = _BR.sub("\n", utan_kommentar)
    utan_block = _BLOCKSLUT.sub("\n", utan_br)
    utan_taggar = _TAGG.sub("", utan_block)
    # Dubbelkodad HTML förekommer: `&amp;auml;` ger efter en avkodning den
    # bokstavliga strängen `&auml;`, vars bokstäver annars blir till ord.
    return html.unescape(html.unescape(utan_taggar))


def brodtext(meddelande: dict) -> str:
    """Meddelandets text, utan citerad historik.

    `text/plain` föredras. Saknas den används `text/html`, vilket beslutslogg #6
    säger förekommer. Saknas `parts` ligger texten direkt i `payload.body.data`,
    vilket också står i #6.
    """
    delar = _platta(meddelande.get("payload", {}))
    for typ in ("text/plain", "text/html"):
        for del_ in delar:
            if del_.get("mimeType") != typ:
                continue
            data = del_.get("body", {}).get("data")
            if not data:
                continue
            ratext = _avkoda(data)
            if typ == "text/html":
                ratext = _text_ur_html(ratext)
            return stada(ratext)
    return ""


def stada(text: str) -> str:
    """Klipper bort citerad historik och normaliserar blankrader.

    Utan det bär varje svar hela trådens tidigare text, och en mall byggd på
    det skulle återge kundens egna ord tillbaka till kunden.
    """
    rader = []
    for rad in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        if _CITATSTART.match(rad):
            break
        rader.append(rad.rstrip())

    while rader and not rader[0].strip():
        rader.pop(0)
    while rader and not rader[-1].strip():
        rader.pop()

    stadat = []
    for rad in rader:
        if not rad.strip() and stadat and not stadat[-1].strip():
            continue
        stadat.append(rad)
    return "\n".join(stadat).strip()
