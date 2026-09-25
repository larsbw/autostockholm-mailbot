"""Dagens inkommande mail ur info@autostockholm.se. LÄSER, SKICKAR ALDRIG.

**DEN HÄR MODULEN LÄSER BREVLÅDAN I SKUGGLÄGETS VÄG**, och den är utpekad med
namn i `src/vy.py::GMAILBARANDE_MODULER`. En onamngiven modul som börjar
importera `googleapiclient` fäller `krav_pa_sandvagsfrihet` tills Lars skriver
in den där. `src/gmailutkast.py` SKRIVER till brevlådan och ligger sedan skiva
69 också i skugglägets väg, med `respond.py --gmailutkast`.

*Här stod att den här modulen är den enda i vägen som rör en brevlåda, och att
`src/gmailutkast.py` ligger utanför den. Sant till och med skiva 68.*

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
  3  IMPORTLAGRET  `GMAILBARANDE_MODULER`, namngivna moduler.
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
gränsen dras här, mot `internalDate`, som är millisekunder sedan epok och
inte tolkningsbar. Sedan uppdraget 2026-09-25 DEL 1 är gränsen sedan SENASTE
LYCKADE KÖRNINGEN, med ett tak på sju dygn, se `fonsterstart` och
`fonstrets_granser`.

*Här stod att gränsen sedan skiva 69 är de 24 timmarna före körningen. Sant
till och med uppdraget 2026-09-25 DEL 1, som lade om `scripts/dagligen.py`
från en körning per dygn till en per timme: ett fast dygnsfönster hade då
läst om samma trådar 24 gånger om dagen.*

*Här stod innan dess att dygnet är Europe/Stockholms. Det var lucka 84.*

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

import math
from datetime import datetime, timedelta, timezone

from src import auth, extract, klassa_maskin, mine, urval

# SAMMA LISTA SOM `src/auth.py` ÄGER, inte en kopia. `scripts/respond.py` skriver
# ut vilket scope körningen har, och ska inte behöva importera `src.auth` för
# det: den modulen står i `vy.GMAILBARANDE_MODULER` och slingan gör det inte.
#
# **UPPMÄTT AV SPÄRREN.** Ett `from src import auth` i `scripts/respond.py` fällde
# `test_respond_nar_gmail_BARA_via_de_namngivna_modulerna`, alltså gjorde lager 3
# precis vad det byggdes för: en fjärde modul som drar in en Gmail-väg faller.
LASSCOPES = auth.LASSCOPES

# HUR LÅNGT BAKÅT EN KÖRNING SER SOM FÖRVAL, när ingen senaste lyckade körning
# finns att räkna från. Se `fonstrets_granser` och `fonsterstart`.
#
# **INTE LÄNGRE DEN ENDA GRÄNSEN, sedan uppdraget 2026-09-25 DEL 1.** Skiva 69
# drog fönstret som de 24 timmarna före körningen, byggt för ett schema en
# gång per dygn. Med `scripts/dagligen.py` om till en gång i timmen (samma
# uppdrag) hade ett fast dygn gjort varje körning till en 24-faldig omläsning
# av samma trådar. Fönstret dras nu i stället från `vy.senaste_lyckade`, se
# `fonsterstart`, och `FONSTER` är kvar bara som `fonstrets_granser`s eget
# förval när ingen `borjan` anges (testerna av fönstrets mekanik, och en
# `--tradar`-körning utan `--regnr-historik` som ändå vill ett värde).
FONSTER = timedelta(hours=24)

# TAK BAKÅT, uppdraget 2026-09-25 DEL 1, Lars beslut: en körning ska aldrig
# läsa längre bak än en vecka, hur länge slingan än stått still. Utan ett tak
# hade en `logg/korningar.jsonl` utan någon lyckad rad, eller en rad flera
# månader gammal, gett ett fönster som drar hem hela brevlådans historik.
MAX_FONSTER = timedelta(days=7)

# ÖVERLAPPSMARGINALEN `fonsterstart` DRAR FRÅN `senaste_lyckad`,
# §7-granskningsfynd. Se den funktionens docstring för VARFÖR: två olika
# klockor (`scripts/dagligen.py`s, före subprocessen, och `respond.py`s
# egen, efter) ska annars mötas exakt, och gör det bara så länge inget
# stör dem emellan. Talet är VALT och inte mätt: några sekunder är gott om
# marginal mot schemats egna vaknjitter (`time.sleep` returnerar aldrig
# tidigt) och för litet för att mätbart öka vad en körning ser, eftersom en
# överlappande tråd ändå bara ger ETT utkast.
SAKERHETSMARGINAL = timedelta(seconds=5)

# GROVT NÄT, inte urvalet. Nätet ska vara vidare än fönstret det tjänar, så
# att gränsen dras av `_ar_fran_dagen` och aldrig av en operator vars
# inklusivitet och tidszon inte går att läsa ut.
#
# **DEN HÄR KONSTANTEN ÄR VÄRSTA FALLET, INTE VAD VARJE KÖRNING FRÅGAR EFTER.**
# `newer_than:8d`, vidare än `MAX_FONSTER` (sju dygn). `dagens_tradar`s eget
# förval, alltså vad en anropare får UTAN att räkna ut något själv: en
# `--tradar`-skörd, ett test, eller en `--inkorg`-körning vars fönster faktiskt
# är sju dygn (ny miljö, eller en slinga som stått still länge).
#
# **`scripts/respond.py::_kallan` ANVÄNDER I STÄLLET `gmailfraga(borjan, nu)`
# FÖR VARJE VANLIG KÖRNING.** Skälet är kvoten: `mine.mina` skickar ALDRIG
# `uteslut` här (se `dagens_tradar`s docstring), alltså listar och HÄMTAR HELA
# INNEHÅLLET i varje tråd nätet snappar upp, på nytt, VARJE körning. Med
# `scripts/dagligen.py` en gång i timmen hade en konstant `newer_than:8d`
# gjort det 24 gånger om dagen för samma åtta dagars trådar, en kvotkostnad
# som inte står i proportion till det enstaka nya mail en normal timme faktiskt
# ger. `gmailfraga` krymper nätet till fönstrets egen storlek plus en dags
# marginal: en normal timme ger `newer_than:2d`, samma tal skiva 69 redan körde
# och mätte kvoten mot, och bara en körning som faktiskt behöver läsa långt
# bakåt (efter ett driftstopp) betalar det bredare nätet.
#
# *Här stod `newer_than:2d`, vidare än det tidigare fasta dygnsfönstret men
# smalare än `MAX_FONSTER`. Uppdraget 2026-09-25 DEL 1 vidgade fönstret till
# sju dygn, alltså måste KONSTANTENS värsta fall vidgas med det; samma
# uppdrag lade `gmailfraga` för att den vidgningen inte skulle betalas 24
# gånger om dagen i det vanliga fallet.*
#
# **INGET `-in:sent` SEDAN SKIVA 69.** Webbformulärets notis bär `SENT`
# (beslutslogg #8), alltså höll operatorn ute varje formulärärende. Uppmätt över
# 2026-07-16 till 2026-09-16: 33 av 432 ärenden, och 11 av de 13 obesvarade
# a-traktorärendena. Vilka meddelanden som är kundens avgör
# `tradar_fran_dagen` med `urval.ar_kundmeddelande`.
FRAGA = "newer_than:8d"

# MARGINALEN `gmailfraga` LÄGGER OVANPÅ DET UTRÄKNADE FÖNSTRET, i hela dygn.
# Samma marginal skiva 69 valde mellan sitt 24-timmarsfönster och
# `newer_than:2d`: en dags marginal ovanpå ett dygns fönster.
GMAILFRAGA_MARGINAL_DAGAR = 1

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


def fonsterstart(nu: datetime, senaste_lyckad: datetime | None) -> datetime:
    """Var fönstret ska börja: sedan `senaste_lyckad`, tak `MAX_FONSTER`.

    Uppdraget 2026-09-25 DEL 1, Lars beslut: med `scripts/dagligen.py` om till
    en gång i timmen läser en körning sedan den SENASTE LYCKADE körningen,
    inte ett fast dygn. `senaste_lyckad` kommer ur `vy.senaste_lyckade`, som
    läser `logg/korningar.jsonl` — samma fil `scripts/dagligen.py` skriver.

    **GOLVET VINNER NÄR `senaste_lyckad` SAKNAS ELLER LIGGER FÖR LÅNGT BAK.**
    Ingen loggad lyckad körning (ny miljö, eller en logg som bara bär
    misslyckanden) och en körning som stått still i mer än en vecka behandlas
    lika: fönstret dras vid `MAX_FONSTER`, aldrig längre. Utan taket hade en
    trasig slinga som lagats efter en månad läst en månad bakåt i en enda
    körning.

    Ett `senaste_lyckad` EFTER `nu` (klockor som glider, eller ett anrop med
    fel argumentordning) ger också golvet: `min` med `nu` hade behövts för att
    hindra ett negativt fönster, och att i stället falla tillbaka på golvet är
    samma säkra riktning som "ingen körning loggad".

    **`SAKERHETSMARGINAL` DRAS FRÅN `senaste_lyckad`, §7-granskningsfynd.**
    `senaste_lyckad` är `scripts/dagligen.py::kor`s EGEN klocka, läst FÖRE
    `respond.py`-subprocessen ens startas. Den körningens egen `slut`
    (`fonstrets_granser`) läses däremot INUTI subprocessen, EFTER dess
    uppstart. De två klockorna är alltså olika mätningar, och utan marginal
    kunde nästa körnings `borjan` (den första, opåverkade mätningen) hamna
    EFTER föregåendes `slut` (den andra, senare mätningen) med precis
    schemats egna vaknjitter, ett glapp inget fönster täcker. Marginalen kan
    bara ge en KORT ÖVERLAPPNING, aldrig ett glapp, och en överlappning är
    ofarlig: samma tråd i två körningar ger ändå bara ETT utkast,
    `vy.gmailutkast_finns`. Dras EFTER golvjämförelsen, inte före: annars
    hade marginalen kunnat knuffa en `senaste_lyckad` som redan låg exakt på
    golvet under det, och golvet är taket, inte ett mål att pruta på.
    """
    golv = nu - MAX_FONSTER
    if senaste_lyckad is None or senaste_lyckad < golv or senaste_lyckad > nu:
        return golv
    kandidat = senaste_lyckad - SAKERHETSMARGINAL
    return kandidat if kandidat > golv else golv


def gmailfraga(borjan: datetime, nu: datetime) -> str:
    """Gmail-frågans grovt nät, rätt stort för DEN HÄR körningens fönster.
    Uppdraget 2026-09-25 DEL 1. Se `FRAGA`s docstring för VARFÖR: `FRAGA`
    ensam, konstant `newer_than:8d`, hade kostat samma kvot 24 gånger om
    dagen för en normal timmes fönster.

    **AVRUNDAT UPPÅT TILL HELA DYGN, PLUS `GMAILFRAGA_MARGINAL_DAGAR`.**
    `newer_than:` tar bara hela dygn (Gmails egen syntax, ingen timupplösning),
    och avrundning NEDÅT hade kunnat göra nätet SMALARE än fönstret för ett
    fönster som inte går jämnt upp i dygn, till exempel tre och en halv
    timme. Marginalen ovanpå är densamma skiva 69 lade mellan sitt
    24-timmarsfönster och `newer_than:2d`.

    **ALDRIG SMALARE ÄN EN DAG**, `newer_than:1d`: ett fönster kortare än ett
    dygn (den vanliga timkörningen) ska ändå ha samma marginal som skiva 69
    mätte, inte ett ännu smalare nät ingen mätning täcker.

    Ett `borjan` EFTER `nu` (bara möjligt vid ett felaktigt anrop, se
    `fonsterstart`) ger noll sekunder och alltså `newer_than:1d`, aldrig ett
    negativt tal.
    """
    sekunder = max((nu - borjan).total_seconds(), 0.0)
    hela_dagar = math.ceil(sekunder / (24 * 60 * 60))
    dagar = max(hela_dagar, 1) + GMAILFRAGA_MARGINAL_DAGAR
    return f"newer_than:{dagar}d"


def fonstrets_granser(
    nu: datetime | None = None, *, borjan: datetime | None = None,
) -> tuple[int, int]:
    """(början, slut) för fönstret som slutar vid `nu`, i millisekunder.

    **`borjan` ÄR FÖRVALET `FONSTER` FÖRE `nu` OM DEN UTELÄMNAS.** Det förvalet
    är kvar för att fönstrets mekanik, avrundningen och gränsernas
    inklusivitet, ska gå att pröva utan en logg att räkna `borjan` ur.
    `scripts/respond.py::_kallan` skickar alltid ett uträknat `borjan`, ur
    `fonsterstart`.

    **LUCKA 84, LARS BESLUT I SKIVA 69.** Här stod dygnet i Europe/Stockholm.
    Körningen gick 05:10 UTC, alltså såg den bara dygnets första timmar, och
    ett mail som kom efter körningen låg utanför nästa dags dygn. Simulerat
    över backfillens skörd, en körning 05:10 UTC per dag i 61 dagar: 483 av
    519 kundmail i ärendetrådar hamnade aldrig i något fönster. Med 24 timmar
    bakåt: 0.

    **SLUTET AVRUNDAS NEDÅT TILL HEL MINUT**, så att två körningar i följd
    möter varandra utan glapp när den ena `borjan` är den andras `slut`.
    `nu` ska vara körningens start. En körning som startar en minut senare än
    föregående `slut` lämnar en minuts glapp, och en som startar tidigare en
    minuts överlapp.

    Samma enhet som `internalDate`. Slutet är EXKLUSIVT, så ett mail som kommer
    i körningens minut tas av nästa körning.

    `nu` slås upp vid anropet och inte i signaturen, av samma skäl som
    `src/vy.py::_rot` anger.
    """
    nu = datetime.now(timezone.utc) if nu is None else nu
    slut = nu.replace(second=0, microsecond=0)
    start = (slut - FONSTER) if borjan is None else borjan
    return int(start.timestamp() * 1000), int(slut.timestamp() * 1000)


def _ar_fran_dagen(meddelande: dict, granser: tuple[int, int]) -> bool:
    """Kom meddelandet in inom `granser`? Namnet är från dygnsgränsens tid.

    Ett meddelande utan `internalDate` räknas INTE som inkommet i fönstret. Att gissa åt
    andra hållet hade tagit in varje odaterat mail i varje körning.
    """
    ra = meddelande.get("internalDate")
    if not ra:
        return False
    borjan, slut = granser
    return borjan <= int(ra) < slut


def tradar_fran_dagen(tradar, *, granser) -> list[dict]:
    """Trådarna med minst ett INKOMMANDE meddelande inom `granser`.

    Namnet är från den tid gränsen var ett dygn. Sedan skiva 69 är den
    `fonstrets_granser`.

    **KRITERIET LIGGER PÅ ETT INKOMMANDE MEDDELANDE och inte på tråden.** En
    tråd vars enda dagsfärska meddelande är vårt eget svar är inget nytt ärende,
    och skulle annars besvaras en gång till varje dag vi svarar i den.

    **INKOMMANDE ÄR `urval.ar_kundmeddelande`, SKIVA 69.** Här stod att `SENT`
    saknas, och det fällde webbformulärets notis, som bär `SENT` men har
    passerat inkommande leverans. Samma kriterium som `arende_ur_trad` väljer
    kundmailet med.

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
        if any(_ar_fran_dagen(m, granser) and urval.ar_kundmeddelande(m)
               for m in meddelanden):
            ut.append(trad)
    return ut


# --------------------------------------------------------------- GALLRINGEN


# HUVUDEN VARS VÄRDE KEDJAN LÄSER. De står här som en egen lista
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
#
# **`message-id` TILLKOM I SKIVA 68.** Gmail-utkastet svarar på kundens
# meddelande med `In-Reply-To`, och värdet läses av `urval.meddelande_id`. Det
# är en identifierare som avsändarens server satt, inte kundtext.
HUVUDEN_MED_VARDE = frozenset({"from", "reply-to", "subject", "precedence",
                               "message-id"})

# SKIVA 69 DEL A. `urval.ar_gmail_svar` kräver en mottagare utöver brevlådan,
# och utan värdena var `Arende.besvarad` alltid falskt i inkorgskörningen.
# Uppmätt mot `data/tradar.jsonl`: 0 besvarade trådar efter gallringen, 139
# före, 139 med `to` och `cc` tillbaka.
#
# **BARA PÅ VÅRA EGNA MEDDELANDEN**, alltså där `urval.ar_kundmeddelande` säger
# nej. Det är de enda `ar_gmail_svar` prövar. På ett kundmail kan `Cc` vara en
# tredje persons adress, och där faller huvudena som förut.
#
# **`bcc` STÅR INTE HÄR**, Lars beslut i skiva 54. Ett svar som når kunden
# bara via `Bcc` ger därför en besvarad tråd som ser obesvarad ut.
MOTTAGARE_MED_VARDE = frozenset({"to", "cc"})

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
#
# **`urval.SVARSHUVUDEN` TILLKOM I SKIVA 69 DEL A.** `ar_gmail_svar` prövar
# `In-Reply-To` och `References` på förekomst. Värdet är ett Message-ID och
# läses inte.
HUVUDEN_UTAN_VARDE = frozenset(
    urval.LEVERANSHUVUDEN | klassa_maskin.MASKINHUVUDEN | urval.SVARSHUVUDEN
) - HUVUDEN_MED_VARDE

HUVUDEN_SOM_LASES = HUVUDEN_MED_VARDE | HUVUDEN_UTAN_VARDE


def _gallra_huvuden(nyttolast: dict, *, med_mottagare: bool) -> list[dict]:
    """Huvudena kedjan läser, i den ordning de kom.

    Ordningen bevaras därför att `urval.huvudvarde` tar FÖRSTA träffen och
    huvudnamn inte är unika (beslutslogg #6). En omsortering hade kunnat byta
    vilken `Received` eller vilken `From` som gäller.

    `med_mottagare` släpper igenom `MOTTAGARE_MED_VARDE` med värde.
    """
    med_varde = HUVUDEN_MED_VARDE | (MOTTAGARE_MED_VARDE if med_mottagare
                                     else frozenset())
    ut = []
    for huvud in nyttolast.get("headers") or []:
        namn = (huvud.get("name") or "")
        if namn.lower() not in HUVUDEN_SOM_LASES | med_varde:
            continue
        varde = huvud.get("value", "") if namn.lower() in med_varde else ""
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
                     "headers": _gallra_huvuden(
                         nyttolast,
                         med_mottagare=not urval.ar_kundmeddelande(meddelande))}

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
    borjan: datetime | None = None,
    fraga: str = FRAGA,
    max_tradar: int = MAX_TRADAR,
) -> tuple[list[dict], mine.Forbrukning]:
    """Dagens inkommande trådar, och vad hämtningen kostade i kvot.

    **HÄMTNINGEN ÄR `src/mine.py`:s OCH INTE EN ANDRA VÄG TILL GMAIL.** Den bär
    kvotpacingen, backoffen mot 429 och skrivningen via en `.delvis`-fil, och en
    andra hämtare hade behövt hålla takt med den. `mine.mina` tar frågan och
    skriver trådarna till `utfil`; vi läser dem tillbaka och sållar på
    `fonstrets_granser(nu, borjan=borjan)`. `nu` ska vara körningens START, se
    `scripts/respond.py::_kor`.

    `borjan` kommer ur `fonsterstart(nu, vy.senaste_lyckade())`, uträknad av
    anroparen: den här modulen känner inte till `logg/korningar.jsonl`, som är
    `scripts/dagligen.py`:s och `src/vy.py`:s fil. Utelämnas `borjan` gäller
    `fonstrets_granser`s eget förval, `FONSTER`.

    **`uteslut` ANVÄNDS INTE HÄR.** Fönstren för två körningar i följd möts
    utan överlapp, men en tråd där kunden skrivit i båda kommer med i båda.
    Ett andra Gmail-utkast i den tråden hindras av `vy.gmailutkast_finns`, inte
    här.

    *Här stod att dubbletter hindras av dagsgränsen. Falskt sedan lucka 84.*

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
    granser = fonstrets_granser(nu, borjan=borjan)
    return tradar_fran_dagen(alla, granser=granser), forbrukning
