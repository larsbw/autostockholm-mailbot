"""Dagens inkommande mail ur info@autostockholm.se. LÄSER, SKICKAR ALDRIG.

**DEN HÄR MODULEN ÄR DEN ENDA I SKUGGLÄGETS VÄG SOM RÖR EN BREVLÅDA**, och den
är utpekad med namn i `src/vy.py::GMAILBARANDE_MODULER`. En fjärde modul som
börjar importera `googleapiclient` fäller `krav_pa_sandvagsfrihet` tills Lars
skriver in den där.

FYRA LAGER, OCH BARA DET FÖRSTA ÄR GOOGLES
------------------------------------------

Lars beslut i skiva 48, se `docs/beslutslogg.md` #113. Hans ordagranna skäl:
lager 2 till 4 kan brytas av en rad i vår kod, lager 1 kan det inte, för då
vägrar Google på serversidan. Vinsten är att sändförmågan inte finns, inte att
den är bortbyggd.

  1  SCOPET        `src/auth.py::LASSCOPES`, gmail.readonly och inget annat.
                   Ett `messages.send` avvisas av Google oavsett vad vår kod
                   gör. **DET ENDA LAGRET SOM INTE ÄR VÅRT.**
  2  TJÄNSTEN      `Lastjanst` nedan. Bara `threads().list/get` och
                   `messages().list/get` går igenom; allt annat kastar
                   `Sandforsok`. Den råa tjänsten lämnar aldrig `las_tjanst`.
  3  IMPORTLAGRET  `GMAILBARANDE_MODULER`, tre namngivna moduler.
  4  KÄLLTEXTEN    `FORBJUDET_MONSTER` över hela grafen, OFÖRÄNDRAT. Den här
                   modulen bär inget sändanrop, och `src/mine.py` och
                   `src/auth.py` gör det inte heller: uppmätt i skiva 48.

Lager 2 till 4 fångar ett misstag vid uppstart i stället för som ett 403 mitt i
en körning. Det är hela deras uppgift, och de påstås inte göra mer.

DAGSGRÄNSEN DRAS AV OSS, INTE AV GMAILS FRÅGA
---------------------------------------------

`after:` och `newer_than:` slogs upp 2026-09-15 i
https://support.google.com/mail/answer/7190 . **Sidan säger varken om `after:`
är inklusiv eller vilken tidszon den mäter i.** Ett urval som vilade på det hade
vilat på en gissning, vilket §1 förbjuder för just Gmail.

Gmail-frågan är därför bara ett GROVT NÄT som håller kvoten nere, och den exakta
dagsgränsen dras här, mot `internalDate`, som är millisekunder sedan epok och
inte tolkningsbar. Dygnet är Europe/Stockholms, eftersom det är det dygn Lars
menar när han säger dagens mail.

SPAM OCH PAPPERSKORG SÅLLAS I VÅR KOD av samma skäl:
`users.threads.list`:s `includeSpamTrash` saknar dokumenterat förval på
https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.threads/list
(avläst 2026-09-15). Etiketterna står i meddelandet och går att pröva.

§6. Modulen returnerar trådar med kundtext och adresser, och `dagens_tradar`
SKRIVER dem till den `utfil` anroparen anger: `mine.mina` är hämtningen, och den
skriver till fil som sin form. Sökvägen har därför inget förval, och
`scripts/respond.py` lägger den under `data/`, som är gitignorerad. Ingenting av
det modulen returnerar skrivs ut av `scripts/respond.py`.

*Här stod att modulen SKRIVER ingenting till disk. Det var falskt redan när det
skrevs: `dagens_tradar` går via `mine.mina`, vars hela kontrakt är en fil.*

SKÖRDEN ÄR ARBETSMATERIAL FÖR EN KÖRNING
----------------------------------------

Lars beslut i skiva 54, DEL A. Skörden skrivs över vid varje körning, och den
bär bara de fält kedjan läser. Gallringen är `gallra_trad` och `mine.mina` lägger
den på FÖRE skrivningen, alltså når det som faller aldrig disken.

*Här stod "råa trådar". Det slutade vara sant med gallringen.*
"""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from src import auth, extract, klassa_maskin, mine, urval

# SAMMA LISTA SOM `src/auth.py` ÄGER, inte en kopia. `scripts/respond.py` skriver
# ut vilket scope körningen har, och ska inte behöva importera `src.auth` för
# det: den modulen står i `vy.GMAILBARANDE_MODULER` och slingan gör det inte.
#
# **UPPMÄTT AV SPÄRREN.** Ett `from src import auth` i `scripts/respond.py` fällde
# `test_respond_nar_gmail_BARA_via_de_namngivna_modulerna`, alltså gjorde lager 3
# precis vad det byggdes för: en fjärde modul som drar in en Gmail-väg faller.
LASSCOPES = auth.LASSCOPES

# Dygnet som avses när Lars säger "dagens mail".
TIDSZON = ZoneInfo("Europe/Stockholm")

# GROVT NÄT, inte urvalet. `newer_than:2d` och inte `1d` med avsikt: nätet ska
# vara vidare än dagsgränsen, så att gränsen dras av `_ar_fran_dagen` och aldrig
# av en operator vars inklusivitet och tidszon inte går att läsa ut.
#
# `-in:sent` håller våra egna svar ute. Gmails `q` matchar MEDDELANDEN, och
# `threads.list` ger varje tråd med minst ett matchande meddelande, alltså kan
# en tråd med både kundmail och svar komma med. Det är avsiktligt: det är
# kundmailet vi vill ha, och `arende_ur_trad` väljer det.
FRAGA = "-in:sent newer_than:2d"

# Ett tak på hur många trådar nätet får ge. Skydd mot att en felskriven fråga
# drar hem hela brevlådan; talet är VALT och inte mätt.
MAX_TRADAR = 200


class Sandforsok(Exception):
    """Något försökte nå en Gmail-resurs som inte är en läsväg."""


# ANROPEN LÄSVÄGEN BEHÖVER, och inga andra. `src/mine.py` använder de två
# första; de två sista står här därför att en läsning av ett enskilt meddelande
# är samma sorts anrop och inte en ny förmåga.
#
# **`messages().send`, `drafts()` OCH `messages().modify` SAKNAS, och det är
# uppräkningens hela innehåll.** Att de saknas är inte en utelämning: mängden
# är en tillåtningslista, alltså faller varje namn som inte står här.
TILLATNA_ANROP = frozenset({
    ("threads", "list"),
    ("threads", "get"),
    ("messages", "list"),
    ("messages", "get"),
})

# Resurserna `users()` lämnar ut alls. `drafts` och `settings` står inte här,
# alltså kastar redan attributåtkomsten.
TILLATNA_RESURSER = frozenset({"threads", "messages"})


class _Resurs:
    """En Gmail-resurs där bara de tillåtna metoderna finns.

    `__getattr__` anropas för VARJE attribut, eftersom klassen inte har några
    egna. Ett `send` når alltså alltid kontrollen och aldrig den råa resursen.
    """

    def __init__(self, ra, namn: str):
        self._ra = ra
        self._namn = namn

    def __getattr__(self, metod: str):
        if (self._namn, metod) not in TILLATNA_ANROP:
            raise Sandforsok(
                f"users().{self._namn}().{metod}() är ingen läsväg. Skuggläget "
                f"läser, det skickar inte. Tillåtna: "
                f"{sorted(m for r, m in TILLATNA_ANROP if r == self._namn)}."
            )
        return getattr(self._ra, metod)


class _Users:
    def __init__(self, ra):
        self._ra = ra

    def threads(self):
        return _Resurs(self._ra.threads(), "threads")

    def messages(self):
        return _Resurs(self._ra.messages(), "messages")

    def __getattr__(self, namn: str):
        # `threads` och `messages` är riktiga metoder ovan, alltså når de aldrig
        # hit. Allt annat gör det: `drafts`, `settings`, `labels`.
        raise Sandforsok(
            f"users().{namn}() är ingen läsväg. Tillåtna: "
            f"{sorted(TILLATNA_RESURSER)}."
        )


class Lastjanst:
    """Gmail-tjänsten med bara läsvägarna öppna. LAGER 2.

    **RÄCKER PRECIS SÅ LÅNGT `src/mine.py` STRÄCKER SIG.** Hela repot rör Gmail
    genom två anrop, `users().threads().list` och `users().threads().get`,
    uppmätt i skiva 48. Inlindningen kostar därför ingen förmåga någon använder.

    **DEN HÄR KLASSEN ÄR INTE GARANTIN.** Den som bygger en egen tjänst ur
    `auth.bygg_tjanst` går förbi den. Garantin är lager 1, scopet. Klassen finns
    för att ett misstag ska synas som ett `Sandforsok` vid anropet i stället för
    som ett 403 från Google efter en halv körning.
    """

    def __init__(self, ra):
        self._ra = ra

    def users(self):
        return _Users(self._ra.users())


def las_tjanst(*, tillat_webblasare: bool = False) -> Lastjanst:
    """En Gmail-tjänst som varken kan skicka eller ändra. Lager 1 OCH lager 2.

    **DEN RÅA TJÄNSTEN LÄMNAR ALDRIG FUNKTIONEN.** Den byggs, lindas och
    returneras inlindad i samma uttryck. Att i stället returnera båda hade gjort
    lager 2 till en artighet som anroparen kan välja bort.

    `tillat_webblasare` är False som förval: den första auktoriseringen är ett
    §10-stopp, och den körs av Lars med `python -m src.auth --las --auktorisera`.
    """
    cred = auth.hamta_las_credentials(tillat_webblasare=tillat_webblasare)
    return Lastjanst(auth.bygg_tjanst(cred))


def dygnets_granser(nu: datetime | None = None) -> tuple[int, int]:
    """(början, slut) för dygnet i Europe/Stockholm, i millisekunder sedan epok.

    Samma enhet som `internalDate`, så att jämförelsen inte går via någon
    strängformatering. Slutet är EXKLUSIVT: dygnets sista millisekund hör till
    dygnet, nästa dygns första gör det inte.

    `nu` slås upp vid anropet och inte i signaturen, av samma skäl som
    `src/vy.py::_rot` anger.
    """
    nu = datetime.now(TIDSZON) if nu is None else nu.astimezone(TIDSZON)
    borjan = nu.replace(hour=0, minute=0, second=0, microsecond=0)
    slut = borjan + timedelta(days=1)
    return int(borjan.timestamp() * 1000), int(slut.timestamp() * 1000)


def _ar_fran_dagen(meddelande: dict, granser: tuple[int, int]) -> bool:
    """Kom meddelandet in under dygnet?

    Ett meddelande utan `internalDate` räknas INTE som dagens. Att gissa åt
    andra hållet hade tagit in varje odaterat mail i varje körning.
    """
    ra = meddelande.get("internalDate")
    if not ra:
        return False
    borjan, slut = granser
    return borjan <= int(ra) < slut


def tradar_fran_dagen(tradar, *, granser) -> list[dict]:
    """Trådarna med minst ett INKOMMANDE meddelande från dygnet.

    **KRITERIET LIGGER PÅ ETT INKOMMANDE MEDDELANDE och inte på tråden.** En
    tråd vars enda dagsfärska meddelande är vårt eget svar är inget nytt ärende,
    och skulle annars besvaras en gång till varje dag vi svarar i den.

    Etiketterna `SPAM` och `TRASH` fäller tråden. `includeSpamTrash` saknar
    dokumenterat förval, se modulens inledning, alltså prövas det här i stället
    för att förutsättas.
    """
    ut = []
    for trad in tradar:
        meddelanden = trad.get("messages") or []
        if any(set(m.get("labelIds") or []) & {"SPAM", "TRASH"}
               for m in meddelanden):
            continue
        if any(_ar_fran_dagen(m, granser) and "SENT" not in (m.get("labelIds") or [])
               for m in meddelanden):
            ut.append(trad)
    return ut


# --------------------------------------------------------------- GALLRINGEN


# HUVUDEN VARS VÄRDE KEDJAN LÄSER. Fyra, och de står här som en egen lista
# därför att anropen som läser dem inte går att importera: namnen skrivs i
# anropet, som `urval.huvudvarde(meddelande, "subject")`, eller i en tupel som
# en slinga går igenom, som `urval.kundadress`.
#
# *Här stod att anropen "bär namnet i anropet och inte i en mängd som går att
# importera". Det var falskt om `urval.kundadress`, som just skriver sina två
# namn i en tupel och skickar dem vidare som en variabel. Fällt av
# §7-granskningen av skiva 54.*
#
# **DEN LISTAN FÅR INTE DRIVA ISÄR FRÅN ANROPEN, och det är ett test och inte en
# god vilja som binder det.** `tests/test_inkorg.py::
# test_varje_huvud_kedjan_LASER_ETT_VARDE_ur_star_i_HUVUDEN_MED_VARDE` läser
# källtexten till kedjans moduler och fäller varje namn som läses men inte står
# här. Utan den raden hade ett nytt `huvudvarde(meddelande, "x-nytt")` gett en
# klassning som blev en annan i drift än i testsviten, tyst.
#
# **TESTET LÄSER TRE ANROPSFORMER, och en fjärde gör det RÖTT i stället för att
# hoppas över.** Första lydelsen läste två och var blind för `kundadress`:s
# slinga. Att `reply-to` och `from` ändå stod här var en slump: de skrivs som
# litteraler i `klassa_maskin`. En blind fläck som tiger är precis den felform
# stycket ovan beskriver, alltså får den inte finnas.
HUVUDEN_MED_VARDE = frozenset({"from", "reply-to", "subject", "precedence"})

# HUVUDEN VARS ENBARA FÖREKOMST KEDJAN PRÖVAR. Värdet läses aldrig, alltså
# skrivs det inte. Namnet blir kvar med ett tomt värde, eftersom det är namnet
# prövningen ställer frågan om.
#
# **`return-path` OCH `delivered-to` STÅR HÄR OCH ÄR INTE STRUKNA.**
# `urval.ar_kundmeddelande` avgör på just deras FÖREKOMST att webbformulärets
# notis, som bär `SENT`, ändå är kundens meddelande (beslutslogg #8). Stryks
# namnet blir varje sådan notis vårt eget utgående mail och tråden får inget
# svar. Deras VÄRDEN når däremot aldrig disken, och det var vad de bar.
#
# **MÄNGDERNA IMPORTERAS OCH SKRIVS INTE AV.** Ett nytt namn i
# `klassa_maskin.MASKINHUVUDEN` följer med hit av sig självt.
HUVUDEN_UTAN_VARDE = frozenset(
    urval.LEVERANSHUVUDEN | klassa_maskin.MASKINHUVUDEN
) - HUVUDEN_MED_VARDE

HUVUDEN_SOM_LASES = HUVUDEN_MED_VARDE | HUVUDEN_UTAN_VARDE


def _gallra_huvuden(nyttolast: dict) -> list[dict]:
    """Huvudena kedjan läser, i den ordning de kom.

    Ordningen bevaras därför att `urval.huvudvarde` tar FÖRSTA träffen och
    huvudnamn inte är unika (beslutslogg #6). En omsortering hade kunnat byta
    vilken `Received` eller vilken `From` som gäller.
    """
    ut = []
    for huvud in nyttolast.get("headers") or []:
        namn = (huvud.get("name") or "")
        if namn.lower() not in HUVUDEN_SOM_LASES:
            continue
        varde = huvud.get("value", "") if namn.lower() in HUVUDEN_MED_VARDE \
            else ""
        ut.append({"name": namn, "value": varde})
    return ut


def gallra_meddelande(meddelande: dict) -> dict:
    """Ett meddelande med bara de fält kedjan läser.

    `id`, `threadId`, `historyId`, `sizeEstimate` och `snippet` faller.
    `snippet` är Gmails eget klartextutdrag ur kundens mail, alltså kundtext som
    ingenting i den dagliga körningen läser.

    **EN ENDA KROPPSDEL FÖLJER MED, den `urval.textdel` pekar ut.** Det är inte
    en förenkling utan vad kedjan faktiskt läser: `brodtext` tar FÖRSTA
    `text/plain` med data, och rör `text/html` bara när ingen sådan finns. Ett
    mail som bär båda bär alltså en HTML-kropp som ingenting öppnar, och den är
    en HTML-kropp som ingenting öppnar. Bilagor faller av samma skäl.

    **UPPMÄTT, och bara totalen är mätt:** en skörd om 53 trådar gick från
    3 194 225 till 643 246 byte när kroppsdelarna gallrades ned till den lästa.
    Vilken enskild post som är störst är INTE mätt och påstås inte.

    **DÄRFÖR ÄR `urval.textdel` UTBRUTEN OCH INTE HÄRMAD.** Valet av kroppsdel
    avgör vilken text kunden klassificeras och besvaras på, och det valet får
    finnas på ETT ställe.
    """
    nyttolast = meddelande.get("payload") or {}
    gallrad: dict = {"mimeType": nyttolast.get("mimeType") or "",
                     "headers": _gallra_huvuden(nyttolast)}

    text = urval.textdel(meddelande)
    if text is not None:
        kropp = {"data": text["body"]["data"]}
        if text is nyttolast:
            gallrad["body"] = kropp
        else:
            gallrad["parts"] = [{"mimeType": text.get("mimeType") or "",
                                 "body": kropp}]

    return {
        "labelIds": list(meddelande.get("labelIds") or []),
        "internalDate": meddelande.get("internalDate", ""),
        "payload": gallrad,
    }


def gallra_trad(trad: dict) -> dict:
    """En tråd med bara de fält kedjan läser. Lars beslut i skiva 54, DEL A.

    **`id` STÅR KVAR.** `scripts/respond.py` skriver det i sin sållningslista,
    och det är en ogenomskinlig Gmail-sträng som inte pekar ut en person.
    `historyId` gör ingendera och faller.
    """
    return {
        "id": trad.get("id", ""),
        "messages": [gallra_meddelande(m) for m in trad.get("messages") or []],
    }


def dagens_tradar(
    tjanst: Lastjanst,
    *,
    utfil,
    nu: datetime | None = None,
    fraga: str = FRAGA,
    max_tradar: int = MAX_TRADAR,
) -> tuple[list[dict], mine.Forbrukning]:
    """Dagens inkommande trådar, och vad hämtningen kostade i kvot.

    **HÄMTNINGEN ÄR `src/mine.py`:s OCH INTE EN ANDRA VÄG TILL GMAIL.** Den bär
    kvotpacingen, backoffen mot 429 och skrivningen via en `.delvis`-fil, och en
    andra hämtare hade behövt hålla takt med den. `mine.mina` tar frågan och
    skriver trådarna till `utfil`; vi läser dem tillbaka och sållar på dygnet.

    **`uteslut` ANVÄNDS INTE HÄR.** Skuggläget kör en gång per dag över dagens
    mail, och dubbletter hindras av dagsgränsen och inte av en uteslutningsmängd.
    Den dagen körningen ska hoppa över redan besvarade trådar är `--uteslut`
    vägen, och den tar en uteslutningsfil, inte en ändring här.

    `utfil` har inget förval. Filen bär rå kundtext och hör hemma under `data/`,
    och en tyst standardsökväg i den här modulen hade varit en §6-risk som
    ingen ser.

    **TRÅDARNA GALLRAS FÖRE SKRIVNINGEN, och det är Lars beslut i skiva 54.**
    Filen är arbetsmaterial för EN körning, inte ett arkiv, och den bär bara de
    fält kedjan läser. Vad som faller och varför står vid `gallra_trad`.

    **DET SOM RETURNERAS ÄR DÄRFÖR OCKSÅ GALLRAT**, eftersom det läses tillbaka
    ur filen. Det är avsiktligt och inte en biverkning: kördes slingan på ett
    fylligare material än det som ligger kvar att felsöka i, vore skörden inte
    längre en avbild av vad körningen såg.
    """
    forbrukning = mine.mina(
        tjanst, utfil=utfil, max_tradar=max_tradar, fraga=fraga,
        gallra=gallra_trad,
    )
    # `extract.las_tradar` OCH INGEN EGEN LÄSARE. Repot hade två identiska
    # jsonl-läsare för trådar; en tredje hade varit en till att hålla i takt.
    alla = list(extract.las_tradar(utfil))
    return tradar_fran_dagen(alla, granser=dygnets_granser(nu)), forbrukning
