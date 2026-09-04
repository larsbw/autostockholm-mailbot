"""Utkastvyn, fas 5.5. Lokal körning, ingen inloggning, INGEN SÄNDVÄG.

Vyn är där Lars läser inkommande mail och skriver referenssvar, och där botens
förslag senare granskas med fyra omdömen. `docs/roadmap.md` fas 5.5 bär specen,
och `docs/beslutslogg.md` #39 och #40 bär besluten.

**DEN HÄR SKIVAN KÖR BARA LOKALT.** Ingen Railway, ingen inloggning. Hosting och
auth är en egen skiva, se #37 och #38. Vyn ska gå att se och rätta innan den
exponeras.

TVÅ LÄGEN.

  REFERENSLÄGE      Visar ett inkommande mail UTAN genererat förslag. Tomt fält.
                    Lars skriver, det sparas som ett par i `data/par.jsonl`.
                    ALDRIG som utgående mail.
  GRANSKNINGSLÄGE   Visar ett genererat förslag med fyra omdömen, loggade
                    åtskilt till `logg/omdomen.jsonl`. Generatorn finns inte än,
                    så läget är byggt men har inget att visa.

**VYN HAR INGEN SÄNDVÄG ALLS, och det är spärren i sin starkaste form.** Ingen
kod som vyn drar in får importera eller anropa något som skickar mail. Se
`krav_pa_sandvagsfrihet` nedan och `docs/sparrar.md` `vyn-har-ingen-sandvag`.

**§6.** Vyn visar RÅ KUNDTEXT på skärmen, eftersom det är hela poängen: Lars ska
läsa ärendet som kunden skrev det. Den får därför aldrig skriva kundtext någon
annanstans än under `data/` och `logg/`, som båda är gitignorerade. Se
`krav_pa_skrivbar_sokvag`.
"""

from __future__ import annotations

import ast
import html
import io
import json
import re
import tokenize
from dataclasses import dataclass
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import parse_qs

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PAR = ROT / "data" / "par.jsonl"
OMDOMEN = ROT / "logg" / "omdomen.jsonl"

# Kategorierna vyn visar. DEL C i skiva 27: Lars ska kunna välja fall som täcker
# de fyra utfallen, och a-traktor är den enda ärendetyp fas 4.5 gatar.
A_TRAKTORETIKETTER = (
    "fråga om a-traktorkonvertering",
    "boka a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# De fyra utfallen ur `src/fordonsuppslag.py`. Skrivna som strängar här och
# INTE importerade därifrån, eftersom en import av den modulen drar in
# fordonsuppslaget i vyn utan att vyn behöver det. Tom sträng betyder att Lars
# inte angett något.
UTFALL = ("", "gront", "gult", "oklart", "rott")

# De fyra omdömena ur `docs/roadmap.md` fas 5.5. De loggas ÅTSKILT och slås
# aldrig ihop till godkänt eller icke godkänt.
OMDOMESVARDEN = ("godkann", "forbattra", "forkasta", "neka")


class Sandvagsfel(Exception):
    """Vyn drar in något som kan skicka mail."""


class Skrivfel(Exception):
    """Vyn försöker skriva utanför `data/` och `logg/`."""


# ---------------------------------------------------------------- DEL B

# MODULER SOM KAN SKICKA MAIL, eller som drar in något som kan. `src/auth.py`
# bygger credentials med `gmail.send` i sitt scope, och `googleapiclient` är
# vägen till `messages().send`. `smtplib` är den andra vägen ut.
FORBJUDNA_MODULER = frozenset({
    "googleapiclient",
    "smtplib",
    "src.auth",
})

# ANROPSFORMER SOM SKICKAR. Andra lagret, och det behövs: en modul kan nå
# `googleapiclient` utan att importera namnet, till exempel genom att ta emot en
# färdig tjänst som argument. Mönstret letar i KÄLLTEXTEN.
#
# MÖNSTRET ÄR BLANKSTEGSTÅLIGT, eftersom `_kod_utan_prosa` skiljer tokens åt med
# blanksteg. Utan det ledet letade det efter en teckenföljd som aldrig uppstår
# efter tokeniseringen.
FORBJUDET_MONSTER = re.compile(
    r"messages\s*\(\s*\)\s*\.\s*send|sendmail|SMTP\s*\("
)


def _lokala_importer(kalla: str, i_modul: str) -> set[str]:
    """Modulnamnen en källfil importerar.

    `i_modul` är namnet på modulen källan KOMMER UR, och behövs för relativa
    importer, vars sökväg inte går att bestämma utan att veta var satsen står.

    **PARAMETERN HAR INGET FÖRVAL, och det är avsiktligt.** Ett förval hade
    gjort spärren FAIL-OPEN: en framtida anropare som glömmer argumentet får
    varje relativ import tyst bortkastad i stället för ett fel. Utan förval
    kastar Python i stället, och det syns. Fällt av §7-granskningen av skiva 28.

    **`from x import y` GER BÅDE `x` OCH `x.y`, och BÅDA leden behövs.** Vilket
    som bär beror på hur importen är skriven, och formerna ser likadana ut i
    källan medan de ger olika AST. Uppmätt med `ast.parse`:

      sats                          `module`     `level`   modulen som dras in
      `from src import auth`        `src`        0         `src.auth`, sammansatt
      `from src.auth import bygg`   `src.auth`   0         `src.auth`, ensamt
      `from . import auth`          `None`       1         `src.auth`, ur nivån
      `from .auth import bygg`      `auth`       1         `src.auth`, nivå + modul

    **DEN TREDJE KOLUMNEN ÄR DEN SOM AVGÖR.** `nod.module` är None bara för den
    relativa formen UTAN modulnamn; för `from .auth import bygg` är det satt,
    men bara till en DEL av sökvägen.

    *Här stod att relativa importer "bär inget paketnamn". Det är falskt för den
    fjärde raden ovan, och det var inte en prosadetalj: den premissen är skälet
    till att koden frågade efter `nod.module` i stället för efter `nod.level`,
    vilket lämnade `from .auth import bygg` osynlig för spärren. Fällt av
    §7-granskningen av skiva 28.*
    """
    namn: set[str] = set()
    for nod in ast.walk(ast.parse(kalla)):
        if isinstance(nod, ast.Import):
            namn.update(alias.name for alias in nod.names)
        elif isinstance(nod, ast.ImportFrom):
            # NIVÅN AVGÖR, INTE MODULNAMNET. `nod.level` är antalet punkter och
            # är noll för en absolut import. Är den större än noll ska paketet
            # ALLTID lösas upp mot modulens eget namn, och `nod.module` fogas på
            # när det finns.
            #
            # Att i stället fråga om `nod.module` är satt gav ett hål: för
            # `from .auth import bygg` är det satt till `auth`, alltså till en
            # DEL av sökvägen, och nivån ignorerades. Spärren fick `auth` i
            # stället för `src.auth` och såg varken namnet eller filen.
            if nod.level:
                bas = _paket(i_modul, nod.level)
                paket = f"{bas}.{nod.module}" if bas and nod.module else bas
            else:
                paket = nod.module or ""
            if not paket:
                continue
            namn.add(paket)
            namn.update(f"{paket}.{alias.name}" for alias in nod.names)
    return namn


def _paket(i_modul: str, niva: int) -> str:
    """Paketet en relativ import på `niva` punkter pekar ut.

    `from . import x` i `src.vy` har `niva` 1 och pekar på `src`. Varje extra
    punkt tar ett steg till uppåt. Är `i_modul` okänt eller nivån djupare än
    modulen ligger går paketet inte att bestämma, och då returneras tom sträng:
    en gissning här hade blivit ett modulnamn som inte finns, alltså en tyst
    lucka i stället för en synlig.
    """
    delar = i_modul.split(".")[:-niva] if i_modul else []
    return ".".join(delar)


def _kod_utan_prosa(kalla: str) -> str:
    """Källan med kommentarer och strängar borttagna.

    **SPÄRREN SKA LÄSA KOD, INTE PROSA OM KOD.** Den här modulens egen kommentar
    namnger `messages().send` för att förklara vad som är förbjudet, och en
    textsökning över råkällan fällde därför modulen på sin egen förklaring.
    Uppmätt i skiva 27, första körningen.

    Det är samma fälla som rutan överst i `docs/sparrar.md` varnar för: ett
    dokumenterat sökmönster träffade fem docstringrader i stället för spärren och
    gav ett verdikt som inte betydde något.

    Strängar tas bort tillsammans med kommentarerna. Ett sändanrop står aldrig
    inuti en strängliteral, medan en förklaring gärna gör det.
    """
    bitar = []
    for token in tokenize.generate_tokens(io.StringIO(kalla).readline):
        if token.type in (tokenize.COMMENT, tokenize.STRING):
            continue
        bitar.append(token.string)
    return " ".join(bitar)


def moduler_i_vyn(start: str = "src.vy", rot: Path | None = None) -> dict[str, str]:
    """Varje modul i repot som vyn drar in, transitivt, med sin källtext.

    Nyckeln är modulnamnet, värdet dess källa. Moduler utanför repot följs inte
    vidare, men deras NAMN prövas mot `FORBJUDNA_MODULER` av anroparen: det är
    importen av dem som är förbjuden, inte vad de i sin tur gör.

    `rot` är None som förval och slås upp vid ANROPET, inte i signaturen. Se
    `_rot`.
    """
    rot = _rot(rot)
    kvar = [start]
    sedda: dict[str, str] = {}

    while kvar:
        modul = kvar.pop()
        if modul in sedda:
            continue
        fil = rot / (modul.replace(".", "/") + ".py")
        if not fil.exists():
            continue
        kalla = fil.read_text(encoding="utf-8")
        sedda[modul] = kalla
        kvar.extend(_lokala_importer(kalla, modul))

    return sedda


def _rot(rot: Path | None) -> Path:
    """Repoteten, uppslagen VID ANROPET.

    **ETT FÖRVAL I EN SIGNATUR BINDS NÄR MODULEN LADDAS**, alltså före varje
    test som pekar om `ROT`. `docs/incidentlogg.md` I1 bär precis den defekten,
    och den här modulen skrev om den: `rot: Path = ROT` gjorde att varje
    skrivtest slog i spärren mot att skriva utanför repot, eftersom kontrollen
    mätte mot det riktiga repot medan testet skrev i sin temporärkatalog.
    """
    return ROT if rot is None else rot


def krav_pa_sandvagsfrihet(start: str = "src.vy", rot: Path | None = None) -> None:
    """Kastar när vyn drar in något som kan skicka mail.

    **SPÄRREN ÄR ATT DET INTE FINNS NÅGON VÄG, inte att vägen är stängd.** En
    knapp som inte syns, eller ett anrop bakom ett villkor, är en väg som råkar
    vara oanvänd. §9.1 säger att en fälld sändning är ett stopptecken och inte
    ett formuleringsproblem, och den regeln är lättast att hålla när koden som
    skulle kunna skicka inte finns i vyns räckvidd alls.

    TVÅ LAGER, och båda behövs:

      importlagret   `FORBJUDNA_MODULER` mot varje modulnamn vyn drar in,
                     transitivt inom repot.
      källtextlagret `FORBJUDET_MONSTER` mot varje sådan moduls källa. En modul
                     kan nå en tjänst utan att importera namnet, till exempel
                     genom att ta emot den som argument, och då är det anropet
                     som syns och inte importen.

    Prövningen körs vid `starta`, alltså innan vyn tar emot något, och den är
    ett vanligt Python-anrop som testet kan göra direkt.
    """
    kallor = moduler_i_vyn(start, _rot(rot))

    for modul, kalla in sorted(kallor.items()):
        for importerad in sorted(_lokala_importer(kalla, modul)):
            rot_namn = importerad.split(".")[0]
            if importerad in FORBJUDNA_MODULER or rot_namn in FORBJUDNA_MODULER:
                raise Sandvagsfel(
                    f"{modul} importerar {importerad}, som kan skicka mail. "
                    f"Vyn får inte ha någon sändväg alls."
                )
        traff = FORBJUDET_MONSTER.search(_kod_utan_prosa(kalla))
        if traff:
            # Blanksteg bort i MEDDELANDET, inte i mätningen. Träffen kommer ur
            # den tokeniserade texten, där `messages().send` står isärskrivet,
            # och den formen säger ingenting för den som ska hitta raden.
            hittat = re.sub(r"\s+", "", traff.group(0))
            raise Sandvagsfel(
                f"{modul} innehåller {hittat!r}, som skickar mail. "
                f"Vyn får inte ha någon sändväg alls."
            )


def krav_pa_skrivbar_sokvag(sokvag: Path, rot: Path | None = None) -> None:
    """Kastar när vyn skriver utanför `data/` och `logg/`.

    §6: vyn visar rå kundtext, och den texten får inte hamna i `docs/`, i ett
    commitmeddelande eller i en logg utanför de två gitignorerade katalogerna.
    Kontrollen ligger i SKRIVFUNKTIONEN och inte hos anroparen, eftersom en
    kontroll hos anroparen är en kontroll någon kan glömma.
    """
    try:
        relativ = sokvag.resolve().relative_to(_rot(rot).resolve())
    except ValueError:
        raise Skrivfel(f"{sokvag} ligger utanför repot") from None

    # `relativ.parts` är TOM när sökvägen ÄR repoteten, och `parts[0]` kastade då
    # `IndexError` i stället för `Skrivfel`. Ingen skrivväg öppnades, men en spärr
    # ska fälla med sitt eget undantag: den som fångar `Skrivfel` runt en
    # skrivning hade annars sluppit igenom ett fel den trodde sig täcka.
    # Funnet av §7-granskningen av skiva 27, varv 1.
    if relativ.parts[:1] != ("data",) and relativ.parts[:1] != ("logg",):
        raise Skrivfel(
            f"{relativ} ligger varken under data/ eller logg/. Vyn skriver rå "
            f"kundtext och får bara skriva till gitignorerade kataloger (§6)."
        )


# ---------------------------------------------------------------- DEL C


@dataclass(frozen=True)
class Fall:
    """Ett ärende vyn kan visa."""

    etikett: str
    kalla: str
    text: str
    tidsstampel: str
    avsandare_hash: str


def _par_karta(parfil: Path) -> dict[str, dict]:
    """Kundtext till parpost, för att hämta hash och tidsstämpel.

    Nyckeln är `inkommande_text`, som är samma sträng som `ometiketterade.jsonl`
    bär i sitt `text`-fält för raderna med svar.

    Uppmätt med `scripts/par-koppling.py`: `data/par.jsonl` bär 222 poster med
    213 UNIKA `inkommande_text`, och samtliga 213 rader med svar i
    `ometiketterade.jsonl` kopplas den vägen.

    *Här stod "samtliga 213 par". Talet var rätt men substantivet fel: 213 är
    antalet unika nycklar och antalet rader med svar, inte antalet poster i
    filen. Fällt av §7-granskningen av skiva 27, varv 1, som mätte 222.*

    Att posterna är fler än nycklarna är förväntat och hanteras av
    `setdefault`: samma kundtext kan ha besvarats mer än en gång, och kartan
    behåller den första.
    """
    if not parfil.exists():
        return {}
    karta = {}
    for rad in parfil.read_text(encoding="utf-8").splitlines():
        if rad:
            post = json.loads(rad)
            karta.setdefault(post["inkommande_text"], post)
    return karta


def las_fall(
    etikettfil: Path = OMETIKETTERADE,
    parfil: Path = PAR,
    etiketter: tuple[str, ...] = A_TRAKTORETIKETTER,
) -> list[Fall]:
    """A-traktorfallen ur den etiketterade korpusen, med svar och utan.

    **BÅDA POPULATIONERNA VISAS**, alltså både de som redan fått svar och de
    obesvarade, så att Lars kan välja fall som täcker de fyra utfallen. Vilken
    population ett fall kommer ur står i `kalla`.

    **HASH OCH TIDSSTÄMPEL SAKNAS FÖR DE OBESVARADE, och de hittas inte på.**
    Raderna med svar kopplas till `data/par.jsonl` på kundtexten och får sina
    riktiga värden. För de obesvarade räcker kopplingen inte till.

    Uppmätt med `scripts/par-koppling.py`: `data/tradar_obesvarade.jsonl` bär
    1604 trådar med 1750 icke-tomma `snippet`. Av de 9 a-traktorraderna utan
    svar kopplas 0 på exakt `snippet` och 1 på `snippet` som inledning.

    **`snippet` SITTER PÅ MEDDELANDET, inte på tråden.** De 1604 trådarna bär
    1755 meddelanden, vart och ett med fältet, och fem av dem har det tomt.
    Noll trådar bär fältet på sin egen toppnivå.

    Skälet att det ändå inte räcker är att `snippet` är Gmails eget
    klartextutdrag och TRUNKERAT. Fältet finns alltså, men det är ingen nyckel.

    Fälten lämnas därför TOMMA, och referenssvaret bär `kalla` som säger varför.
    Att skriva en påhittad hash hade varit ett tal utan källa (§7.2).

    *TRE tidigare lydelser stod här, och var och en rättade den föregående utan
    att bli sann. Den första sade 1 av 9 utan att något committat skript kunde
    räkna om det. Den andra sade att ett extraherat textfält inte finns och att
    kopplingen är OBEFINTLIG; båda leden var falska. Den tredje, skriven för att
    rätta den andra, sade att `snippet` finns på var och en av de 1604 trådarna:
    talet var rätt för meddelandena och fel för trådarna, alltså samma nivåfel
    som varv 1 fällde fem rader upp i den här filen, nu med ett exakt tal på.
    Fällt av §7-granskningen av skiva 28.*
    """
    if not etikettfil.exists():
        return []

    par = _par_karta(parfil)
    valda = set(etiketter)
    fall = []

    for rad in etikettfil.read_text(encoding="utf-8").splitlines():
        if not rad:
            continue
        post = json.loads(rad)
        if post["etikett"] not in valda:
            continue
        kalla = par.get(post["text"], {})
        fall.append(Fall(
            etikett=post["etikett"],
            kalla=post["kalla"],
            text=post["text"],
            tidsstampel=kalla.get("tidsstampel", ""),
            avsandare_hash=kalla.get("avsandare_hash", ""),
        ))

    return fall


# ---------------------------------------------------------------- skrivning


def spara_referenssvar(
    fall: Fall,
    svarstext: str,
    utfall: str = "",
    parfil: Path = PAR,
) -> dict:
    """Skriver Lars referenssvar som ett par. ALDRIG som utgående mail.

    **ETT REFERENSSVAR SKICKAS ALDRIG.** Beslut av Lars, `docs/beslutslogg.md`
    #39. Kunderna har fått svar för länge sedan eller inte alls. Den här
    funktionen skriver till `data/par.jsonl` och det finns ingen annan väg ut ur
    vyn, se `krav_pa_sandvagsfrihet`.

    **POSTEN BÄR `kalla` OCH `utfall`, och de två fälten är MITT tillägg och
    inte Lars beslut.** Skälet är att `data/par.jsonl` annars blandar ihop två
    olika saker: svar som FAKTISKT skickades till en kund, skrivna av Matte
    eller Lars i sin tid, och referenssvar som aldrig lämnat vyn. #11 säger att
    filen räknar svarsinstanser, och utan markören hade en senare läsare räknat
    referenssvaren som skickade svar.

    De fyra ursprungliga nycklarna är oförändrade, så #13:s krav att filen är RÅ
    står orört och varje befintlig läsare fortsätter fungera.
    """
    if utfall not in UTFALL:
        raise ValueError(f"okänt utfall: {utfall!r}, tillåtna är {UTFALL}")

    text = svarstext.strip()
    if not text:
        raise ValueError("ett tomt referenssvar sparas inte")

    krav_pa_skrivbar_sokvag(parfil)

    post = {
        "inkommande_text": fall.text,
        "utgaende_text": text,
        "tidsstampel": fall.tidsstampel,
        "avsandare_hash": fall.avsandare_hash,
        "kalla": "referenssvar",
        "utfall": utfall,
        "etikett": fall.etikett,
        "skrivet": datetime.now(timezone.utc).isoformat(),
    }

    parfil.parent.mkdir(parents=True, exist_ok=True)
    with parfil.open("a", encoding="utf-8") as fil:
        fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    return post


def spara_omdome(
    fall: Fall,
    omdome: str,
    redigerad_text: str = "",
    omdomesfil: Path = OMDOMEN,
    parfil: Path = PAR,
) -> dict:
    """Loggar ett av de fyra omdömena. Append-only.

    `forbattra` bär den redigerade texten och skriver DESSUTOM ett nytt par,
    enligt `docs/roadmap.md` fas 5.5: det är den enda av de fyra som tränar
    rösten.
    """
    if omdome not in OMDOMESVARDEN:
        raise ValueError(f"okänt omdöme: {omdome!r}, tillåtna är {OMDOMESVARDEN}")

    krav_pa_skrivbar_sokvag(omdomesfil)

    post = {
        "etikett": fall.etikett,
        "omdome": omdome,
        "avsandare_hash": fall.avsandare_hash,
        "tidsstampel": fall.tidsstampel,
        "skrivet": datetime.now(timezone.utc).isoformat(),
    }

    omdomesfil.parent.mkdir(parents=True, exist_ok=True)
    with omdomesfil.open("a", encoding="utf-8") as fil:
        fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    if omdome == "forbattra":
        spara_referenssvar(fall, redigerad_text, parfil=parfil)

    return post


# ---------------------------------------------------------------- rendering

SIDHUVUD = """<!doctype html>
<html lang="sv"><head><meta charset="utf-8"><title>Utkastvyn</title>
<style>
 body {{ font: 15px/1.5 -apple-system, sans-serif; margin: 2rem auto; max-width: 46rem; }}
 .mail {{ background: #f6f6f6; padding: 1rem; white-space: pre-wrap; }}
 .etikett {{ color: #555; }}
 .sparr {{ background: #fee; border-left: 4px solid #c00; padding: 1rem; }}
 textarea {{ width: 100%; height: 12rem; }}
 nav a {{ margin-right: 1rem; }}
</style></head><body>
<p><strong>Utkastvyn</strong> · lokal körning · ingen sändväg</p>
"""

SIDFOT = "</body></html>"


def rendera_referens(fall: Fall, index: int, antal: int) -> str:
    """REFERENSLÄGE: inkommande mail, tomt fält, spara som par.

    Knappen heter SPARA SOM PAR och inget annat. `docs/beslutslogg.md` #39
    kräver att den är omöjlig att förväxla med en skicka-knapp, och vyn har
    ingen skicka-knapp att förväxla den med.
    """
    return (
        SIDHUVUD.format()
        + f"<nav>{_navigering(index, antal)}</nav>"
        + f"<p class='etikett'>{html.escape(fall.etikett)}"
        + f" · {html.escape(fall.kalla)}</p>"
        + f"<div class='mail'>{html.escape(fall.text)}</div>"
        + "<h2>Referenssvar</h2>"
        + "<p>Sparas som ett par i <code>data/par.jsonl</code>."
        + " <strong>Skickas aldrig.</strong></p>"
        + f"<form method='post' action='/referens/{index}'>"
        + "<textarea name='svar' placeholder='Skriv svaret som du hade svarat.'></textarea>"
        + "<p>Utfall: " + _utfallsval() + "</p>"
        + "<p><button type='submit'>Spara som par</button></p>"
        + "</form>"
        + SIDFOT
    )


def rendera_granskning(fall: Fall, forslag: str, sparr: str = "") -> str:
    """GRANSKNINGSLÄGE: förslag med fyra omdömen.

    **EN SPÄRRFÄLLD POST VISAR ALDRIG ETT TEXTFÄLT, oavsett läge.** Beslut av
    Lars, `docs/beslutslogg.md` #40. §9.1 väger tyngre än bekvämligheten att
    kunna skriva ett referenssvar på just den posten: en textruta bredvid ett
    fällt förslag gör förbudet till ett klick, även när knappen heter spara och
    inte skicka. Behövs en referens för ett ärende vars förslag fälldes, tas en
    annan post av samma kategori.

    Vyn ska inte lära handen den rörelsen.
    """
    huvud = (
        SIDHUVUD.format()
        + f"<p class='etikett'>{html.escape(fall.etikett)}</p>"
        + f"<div class='mail'>{html.escape(fall.text)}</div>"
    )

    if sparr:
        return (
            huvud
            + "<div class='sparr'><p><strong>Spärrad av "
            + html.escape(sparr)
            + "</strong></p>"
            + "<p>Inget textfält, ingen väg vidare. Behövs ett referenssvar för"
            + " den här kategorin, ta en annan post.</p></div>"
            + SIDFOT
        )

    return (
        huvud
        + "<h2>Förslag</h2>"
        + f"<div class='mail'>{html.escape(forslag)}</div>"
        + "<form method='post' action='/omdome'>"
        + "<textarea name='redigerad'></textarea><p>"
        + "".join(
            f"<button name='omdome' value='{v}'>{v}</button> "
            for v in OMDOMESVARDEN
        )
        + "</p></form>"
        + SIDFOT
    )


def rendera_fel(fel: Exception) -> str:
    """Felsidan, med felets text ESCAPAD.

    **DEN ENDA PLATSEN DÄR DATA UR POST-KROPPEN REFLEKTERAS TILLBAKA I HTML.**
    `spara_referenssvar` bakar in det okända utfallet i sitt `ValueError`, och
    det värdet kommer utifrån. Utan escapning är det en väg att få egen markup
    renderad i vyn.

    Funktionen är UTBRUTEN ur `do_POST` för att gå att pröva. Låg den kvar
    inbakad i hanteraren kunde escapningen bara testas genom att testet
    upprepade den, vilket är ett test som inte kan bli rött. Funnet av
    §7-granskningen av skiva 27, varv 3.
    """
    return SIDHUVUD.format() + f"<p>{html.escape(str(fel))}</p>" + SIDFOT


def _utfallsval() -> str:
    return "".join(
        f"<label><input type='radio' name='utfall' value='{v}'"
        + (" checked" if v == "" else "")
        + f"> {v or 'ej angett'}</label> "
        for v in UTFALL
    )


def _navigering(index: int, antal: int) -> str:
    delar = [f"post {index + 1} av {antal}"]
    if index > 0:
        delar.append(f"<a href='/referens/{index - 1}'>föregående</a>")
    if index + 1 < antal:
        delar.append(f"<a href='/referens/{index + 1}'>nästa</a>")
    return " · ".join(delar)


# ---------------------------------------------------------------- server


def bygg_hanterare(fall: list[Fall], parfil: Path = PAR):
    """HTTP-hanteraren, med fallen inbakade.

    Servern binder till localhost i `starta`. Ingen inloggning byggs i den här
    skivan, och det är därför den inte får exponeras: vem som når porten når
    kundtexten.
    """

    class Hanterare(BaseHTTPRequestHandler):
        def _svara(self, kropp: str, kod: int = 200) -> None:
            data = kropp.encode("utf-8")
            self.send_response(kod)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:  # noqa: N802
            if not fall:
                self._svara(SIDHUVUD.format() + "<p>Inga fall.</p>" + SIDFOT)
                return
            index = _index_ur_vag(self.path, len(fall))
            self._svara(rendera_referens(fall[index], index, len(fall)))

        def do_POST(self) -> None:  # noqa: N802
            langd = int(self.headers.get("Content-Length") or 0)
            falt = parse_qs(self.rfile.read(langd).decode("utf-8"))
            index = _index_ur_vag(self.path, len(fall))
            try:
                spara_referenssvar(
                    fall[index],
                    falt.get("svar", [""])[0],
                    falt.get("utfall", [""])[0],
                    parfil=parfil,
                )
            except ValueError as fel:
                self._svara(rendera_fel(fel), 400)
                return
            nasta = min(index + 1, len(fall) - 1)
            self._svara(
                SIDHUVUD.format()
                + "<p>Sparat som par.</p>"
                + f"<p><a href='/referens/{nasta}'>nästa post</a></p>"
                + SIDFOT
            )

        def log_message(self, *_):  # noqa: D102
            # TYST. Standardloggen skriver sökvägen till stderr, och sökvägen
            # bär ett index och ingen kundtext, men servern ska inte skriva
            # något alls om vad Lars läser (§6).
            return

    return Hanterare


def _index_ur_vag(vag: str, antal: int) -> int:
    sista = vag.rstrip("/").rsplit("/", 1)[-1]
    if sista.isdigit():
        return max(0, min(int(sista), antal - 1))
    return 0


def starta(port: int = 8765, fall: list[Fall] | None = None) -> HTTPServer:
    """Startar vyn på localhost.

    **SÄNDVÄGSSPÄRREN PRÖVAS HÄR, innan servern tar emot något.** Det är den
    enda platsen som garanterat körs före första begäran.
    """
    krav_pa_sandvagsfrihet()
    fall = las_fall() if fall is None else fall
    return HTTPServer(("127.0.0.1", port), bygg_hanterare(fall))
