"""Hämtningen mot biluppgifter.se, alltså den utbytbara delen av fas 4.5.

VARFÖR MODULEN ÄR EGEN. `src/fordonsuppslag.py` säger att ett byte av datakälla
ska vara ett byte av EN funktion och inte en omskrivning av modulen. Den är i
dag nätverksfri och går att testa utan att någon socket öppnas. Läggs hämtningen
in där förlorar den egenskapen för hela modulen, inklusive `utvardera` som är
ren boolesk logik. Sömmen är `Callable[[str], dict | None]`, och den bärs lika
väl av en funktion i en annan fil.

DATAKÄLLAN ÄR DEN ÖPPNA FORDONSSIDAN, inte PRO-API:t. Beslut av Lars 2026-09-02.
`docs/beslutslogg.md` #23 listade `Biluppgifter PRO API` som ett alternativ mot
API-nyckel; den öppna sidan bär samma tre gatande fält utan nyckel och utan
inloggning. Avläst på ett fordon, se posten i beslutsloggen.

**ÄGARUPPGIFTER KAN INTE FÖLJA MED.** Sidan svarar `Endast inloggade medlemmar
kan se ägarinformation` och `Logga in` på VIN. Vi loggar aldrig in, så #23:s val
att avstå ägaruppgifter blir en egenskap hos hämtningen i stället för en
disciplin någon måste upprätthålla. Det är ett skäl att föredra den här vägen,
inte bara en följd av den.

**FÄLTAVBILDNINGEN ÄR ETT BESLUT AV LARS, INTE EN LÄSNING.** Sidan bär FYRA
släpvagnsrelaterade tal: `Släpvagnsvikt`, `Släpvagnsvikt obromsad`,
`Släp totalvikt (B)` och `Släp totalvikt (B+)`. VVFS 2003:19 4 kap 42 § kräver
vad ursprungsfordonet är KONSTRUERAT för, och Lars avgör att `Släpvagnsvikt` är
det fältet. De två `Släp totalvikt`-raderna är körkortsbehörigheter och bär
dessutom ordet `Teoretisk` i värdet.

**DÄRFÖR ÄR ETIKETTMATCHNINGEN EXAKT OCH ALDRIG PREFIX.** `Släpvagnsvikt` är ett
prefix till `Släpvagnsvikt obromsad`, och de två raderna ligger direkt efter
varandra i sidans HTML. En prefixmatchning ger därför TVÅ träffar där det ska
finnas en, och vilken av dem som används avgörs av radordningen i källans HTML.

På det avlästa fordonet står den bromsade raden först, så en prefixmatchning ger
2 400 kg, alltså den RÄTTA vikten. **Den ger rätt svar av radordning och inte av
konstruktion.** Byter källan ordningen kommer 750 kg in i stället, och det är
inte ett parsningsfel som syns: 750 ligger under tröskeln 1 000 och 2 400 över,
så defekten KAN byta utfall på fordon där tjänstevikten inte redan räcker, och
göra det tyst. `EXAKT_ETIKETT` finns för att utfallet inte ska bero på den
ordningen.

INGET NYTT BEROENDE. `urllib` och `re` ur standardbiblioteket. `requirements.txt`
rörs inte.

**HÄMTNINGEN ÄR SÄNDVÄG enligt CLAUDE.md §7.** Den avgör med vilket innehåll ett
a-traktorsvar lämnar servern. Full granskning gäller, och spärren nedan är
registrerad i `docs/sparrar.md`.
"""

from __future__ import annotations

import html
import re
import urllib.error
import urllib.request
from typing import Callable

# Sidans adress. Registreringsnumret kommer normaliserat till VERSALER av
# `fordonsuppslag.slag_upp`, och sidan svarar på både gemener och versaler,
# avläst 2026-09-02. Numret URL-kodas inte: `normalisera_regnr` har redan
# strippat blanksteg och bindestreck. Ett nummer som bär något annat får alltså
# gå ut i URL:en och avvisas därefter av `canonical`-ankaret nedan, INTE av
# statuskoden: sidan svarar 200 med söksidan på ett nummer den inte känner, se
# kommentaren vid `CANONICAL`.
URL_MALL = "https://biluppgifter.se/fordon/{regnr}/"

# En webbläsares user-agent. DETTA ÄR INTE KOSMETIKA: sidan svarar 200 på en
# webbläsarklient och avvisade Perplexitys hämtare med klientfel, avläst
# 2026-09-02. Filtreringen sker alltså på klienten, och det är samtidigt den
# största driftrisken med den här vägen. Skärps filtret slutar hämtningen
# fungera, och då är PRO-API:t vägen tillbaka.
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

TIDSGRANS_S = 20

# Sömmens tre nycklar, avbildade på sidans etiketter. Vänsterledet är
# `fordonsuppslag._kontrollera`:s nycklar och får inte ändras här; högerledet är
# Lars fältval.
EXAKT_ETIKETT = {
    "tjanstevikt_kg": "Tjänstevikt",
    "slapvagnsvikt_kg": "Släpvagnsvikt",
    "draganordning": "Draganordning",
}

# Sidans fältblock är regelbundet: en etikett följd av sitt värde i nästa span.
# `\s*</span>` EFTER etiketten är det som gör matchningen exakt och inte ett
# prefix, och `[^<]*` i värdegruppen tillåter inga nästlade element: en etikett
# som plötsligt bär markup är en strukturändring och ska ge ett saknat fält,
# inte ett gissat värde.
#
# HÄR STOD ATT `(?!\s*<)` FÄLLER EN TOM ETIKETT. Uttrycket finns inte i
# mönstret. Den rättelsen var i sin tur också fel: den påstod att en tom
# söksträng ger första label/value-parets värde. UPPMÄTT ger den NOLL träffar
# mot den avlästa sidan, för med tom etikett kräver mönstret en label-span som
# bara bär blanktecken, och någon sådan finns inte där. Mot en konstruerad sida
# som HAR en sådan span ger den det TOMMA parets värde, inte det första.
# Ofarligt i dag, eftersom `EXAKT_ETIKETT` bara bär icke-tomma etiketter, men
# båda kommentarerna beskrev ett villkor de inte hade mätt.
# **Läggs en etikett till får den aldrig vara tom.**
MONSTER = (
    r'<span class="label">\s*{etikett}\s*</span>\s*'
    r'<span class="value">([^<]*)</span>'
)

# ETIKETTEN ENSAM, utan sitt värde. Lager 2 räknar FÖREKOMSTER AV ETIKETTEN och
# inte träffar på `MONSTER`, och skillnaden var en sändvägsdefekt.
#
# `MONSTER`:s värdegrupp är `([^<]*)` och matchar därför inte ett värde som bär
# nästlad markup. Låg etiketten två gånger på sidan och ETT av värdena var
# nästlat gav `MONSTER` en enda träff, tvetydighetskontrollen tände aldrig, och
# modulen svarade med det andra värdet som om det vore entydigt. Uppmätt i
# skiva 21: en sida med `Släpvagnsvikt` två gånger, det första värdet i ett
# `<b>`, gav 750 kg i stället för `Hamtningsfel`.
#
# **PREMISSEN FINNS PÅ DEN SKARPA SIDAN.** Fixturkommentaren i
# `tests/test_biluppgifter.py` mäter 62 label-span mot 54 par, och namnger
# orsaken för ett av glappen: `Chassinr / VIN`, vars value-span öppnar ett
# element. Att just `Släpvagnsvikt` inte är ett av dem i dag är en avläsning av
# i dag.
#
# **RÄKNAREN ÄR LÖSARE ÄN LÄSAREN, MEN BARA I TAGGEN.** `ETIKETTSPAN` godtar
# attribut och extra blanktecken i taggen; `MONSTER` gör det inte. I den
# dimensionen felar de åt SAMMA håll, som är det säkra:
#
#   räknaren överskattar  -> en dubblett som inte var en dubblett KASTAR
#   läsaren underskattar  -> en etikett i ändrad form UTELÄMNAS
#
# **I KLASSVÄRDET OCH I ETIKETTENS INNEHÅLL ÄR RÄKNAREN LIKA STRÄNG, OCH DÄR
# HÅLLER KONSTRUKTIONEN INTE.** Bär den ena av två förekomster `class="label
# bold"`, nästlad markup runt etikettnamnet, eller ett annat element än `span`,
# ser VARKEN räknaren eller läsaren den. `forekomster` blir 1, tvetydigheten
# tänder aldrig, och det ANDRA parets värde går ut som om sidan vore entydig.
#
# **DET ÄR EN ÖPPEN SÄNDVÄGSDEFEKT**, fälld av skiva 21:s tredje granskningsvarv
# och verifierad i egen körning: en sida med `Släpvagnsvikt` två gånger, 2400 kg
# och 750 kg, svarar 750 när den första etiketten bär ett extra klassord. Den
# obromsade vikten under tröskeln alltså, där den bromsade ligger över. Samma
# sak på `Draganordning` löser ett Ja mot ett Nej tyst.
#
# Defekten stängs i skiva 22 genom att sidan PARSAS i stället för att matchas
# som text, se `docs/beslutslogg.md`. Kommentaren står kvar tills dess, eftersom
# en känd defekt som inte står utskriven är värre än en som gör det.
#
# En räknare lika sträng som läsaren var en sändvägsdefekt: låg etiketten två
# gånger och den ENA spannen bar ett attribut såg räknaren en enda, och det
# andra värdet gick ut som om det vore entydigt. Uppmätt i skiva 21:s andra
# granskningsvarv, med `data-id="7"` på den ena och ett extra blanksteg i taggen
# på den andra.
#
# **FÖLJDEN, som ska stå utskriven:** en `class="label"`-span som bär en av våra
# tre etiketter men INGET värdepar räknas också. En sida med en rubrik i den
# formen ger därför `Hamtningsfel` i stället för att läsas. Riktningen är säker,
# inget värde kommer ut, men felskälet säger `förekommer 2 gånger` om något som
# är ett fält och en rubrik.
ETIKETTSPAN = r'<span[^>]*class=["\']label["\'][^>]*>\s*{etikett}\s*</span>'

# ANKARET SOM AVGÖR ATT SVARET GÄLLER RÄTT FORDON.
#
# **SIDAN SVARAR INTE 404 PÅ ETT OKÄNT NUMMER.** Avläst 2026-09-02: ett nummer
# utan fordon ger HTTP 200 och SÖKSIDAN, med titeln `Sök Regnr, Fordon, ...`.
# Ett statusberoende `finns fordonet` är alltså fel byggt, och 404-grenen nedan
# står kvar som ett skydd som i praktiken inte utlöses, inte som vägen.
#
# `canonical` skiljer fallen rent, avläst på tre svar 2026-09-02:
#   fordon som finns   -> .../fordon/<numret i gemener>/
#   nummer utan fordon -> .../fordon/   alltså UTAN nummer
#
# De tre nummer som avlästes står inte utskrivna här. `src/` är inte bevakat av
# `scripts/persondatakontroll.py`, men TVÅ AV DE TRE motsvarar verkliga fordon,
# och §6:s skäl gäller ändå: en läsare kan inte se att ett nummer är påhittat.
# Det tredje är påhittat och är just det som gav söksidan.
#
# Kontrollen är inte kosmetisk. Utan den läser parsern fältetiketter ur vilken
# sida källan än råkar svara med, och en söksida som en dag bär ett exempel med
# etiketten `Tjänstevikt` hade då blivit ett tal i ett kundmail. Att söksidan i
# dag bär noll `class="label"` är en avläsning av i dag, inte en garanti.
CANONICAL = r'<link[^>]+rel="canonical"[^>]+href="([^"]+)"'


class Hamtningsfel(Exception):
    """Källan svarade inte, eller svarade med något annat än en fordonssida.

    SKILD FRÅN `UppslagMisslyckades` MED AVSIKT. `slag_upp`:s kontrakt säger att
    hämtningens egna undantag INTE fångas utan når anroparen, därför att en
    källa som är nere inte är samma sak som ett fordon utan uppgifter. Att
    översätta det ena till det andra hade gjort ett driftavbrott osynligt.
    """


def _tal(varde: str) -> int | None:
    r"""Vikten i hela kilo, eller `None` när värdet inte är en ren vikt.

    STRIKT MED AVSIKT. Bara siffror, valfria tusenavskiljare och `kg`. Sidan bär
    värden som `Max 750 kg (Teoretisk)` på andra rader, och ett mönster som
    plockar första talet ur en sträng hade gjort ett sådant värde till en vikt.
    `None` gör att nyckeln utelämnas och att spärren i `_kontrollera` fäller med
    sitt eget skäl, i stället för att ett tal vi inte kan stå för når ett mail.

    Tusenavskiljaren är blanksteg eller hårt blanksteg på sidan, aldrig punkt:
    en punkt vore en decimalpunkt i svensk sifferskrivning och `1.5 kg` ska
    därför inte bli 15.

    INGEN TOMKONTROLL EFTER `re.sub`, OCH DET ÄR BEVISAT OCH INTE ANTAGET. Här
    stod `if not siffror: return None`. Den grenen var ONÅBAR redan mot det
    gamla mönstret, och är det med ännu bredare marginal mot det nya: grupp 1
    kan inte matcha annat än siffror, eftersom både alternativen inleds med
    `\d`. Ett blanktecken kan bara stå MELLAN siffergrupper.

    **HÄR STOD EN ANALYS AV DET GAMLA MÖNSTRET, och den beskriver inte längre
    koden.** Den sa att onåbarheten vilar på TVÅ led, `.strip()` och
    kvantifikatorn `+`, och att `' kg'` utan `.strip()` ger `ValueError`. Med
    `(\d{1,3}(?:[\s\u00a0]\d{3})+|\d+)` kan grupp 1 aldrig bära enbart
    blanktecken, så `' kg'` ger `None` med eller utan `.strip()`. Uppmätt i
    skiva 21:s andra granskningsvarv, som också visade att `.strip()`-fällningen
    därmed blivit GRÖN och testet som skulle vakta den vakuöst.

    **`.strip()` BÄR FORTFARANDE NÅGOT, men något annat.** Ett värde med
    omgivande blanktecken i sin value-span, `'  2400 kg  '`, ger 2400 med
    `.strip()` och `None` utan. Det är den egenskapen
    `test_varde_med_omgivande_blanktecken_lases` vaktar, och den fällningen är
    RÖD. Sidans HTML är indenterad, så fallet är källans normalform och inte ett
    kantfall.

    **En gren som inget test kan fälla ser ut som försiktighet utan att vara
    det**, och §7.1 kallar det vakuöst. Det är precis vad som hände här: testet
    som skrevs för `.strip()` slutade binda den när mönstret skärptes, utan att
    någon rad blev röd.
    """
    # BLANKTECKEN GODTAS BARA SOM TUSENAVSKILJARE, aldrig var som helst.
    # Det gamla mönstret var `([\d\s\u00a0]+)kg`, som tillät blanktecken
    # fritt inuti gruppen medan `re.sub` sedan klistrade ihop allt som blev
    # kvar. Ett värde med TVÅ tal blev därför ETT: uppmätt i skiva 21 gav
    # `750 2400 kg` talet 7502400, ett välformat heltal långt över tröskeln.
    # Docstringens "bara siffror, valfria tusenavskiljare" beskrev inte det
    # uttrycket. Grupperingen är nu strukturell OCH KONSEKVENT: antingen bara
    # siffror, eller en till tre siffror följda av grupper om exakt tre med
    # en avskiljare vid VARJE gräns. Den andra halvan behövs: ett mönster
    # med valfri avskiljare läste `2400 750 kg` som 2 400 750, alltså två
    # tal hopklistrade igen, fast med blandad gruppering.
    traff = re.fullmatch(
        r"(\d{1,3}(?:[\s\u00a0]\d{3})+|\d+)[\s\u00a0]*kg",
        varde.strip(),
        flags=re.IGNORECASE,
    )
    if not traff:
        return None

    siffror = re.sub(r"[\s\u00a0]", "", traff.group(1))
    return int(siffror)


def _ja_nej(varde: str) -> bool | None:
    """`Ja` eller `Nej` som bool. Allt annat ger `None`.

    Sidan skriver ut `Nej` för ett fordon utan draganordning, avläst 2026-09-02.
    Ett tredje värde, eller ett tomt, betyder att vi inte vet, och då ska
    nyckeln utelämnas. Ett `Okänd` som tolkades som `Nej` hade gett ett svar som
    påstår att dragkrok saknas, vilket är just det påstående `utvardera`:s
    förval OKLART finns för att undvika.
    """
    rensat = varde.strip().lower()
    if rensat == "ja":
        return True
    if rensat == "nej":
        return False
    return None


def _galler_fordonet(sida: str, regnr: str) -> bool:
    """Sant bara när sidans `canonical` pekar på det begärda registreringsnumret.

    Jämförelsen är skiftlägesokänslig, därför att `slag_upp` normaliserar numret
    till VERSALER medan sidan skriver sin canonical i gemener. Samma sorts
    versalfälla gav 46 av 78 i stället för 77 av 78 vid regnr-avläsningen, se
    `docs/beslutslogg.md` #28. Den ska inte återkomma i en annan modul.

    En sida UTAN canonical ger `False`, alltså `fordonet finns inte`. Det är det
    försiktiga förvalet: ett svar vi inte kan knyta till numret får inte bli
    fordonsfakta om numret.
    """
    traff = re.search(CANONICAL, sida, flags=re.IGNORECASE)
    if not traff:
        return False

    slutet = traff.group(1).rstrip("/").rsplit("/", 1)[-1]
    return slutet.upper() == regnr.upper()


def _las_falt(sida: str) -> dict:
    """Plockar de tre gatande fälten ur sidans HTML.

    SPÄRRENS FÖRSTA LAGER: `EXAKT_ETIKETT` matchas med `re.escape` och en
    avslutande `</span>`, alltså aldrig som prefix. Se modulens docstring om
    `Släpvagnsvikt obromsad`.

    SPÄRRENS ANDRA LAGER: en etikett som förekommer FLERA gånger på sidan är
    tvetydig, och tvetydigheten kastar. Ett `ta första träffen` hade gjort
    sidans ordning till en tyst del av bedömningen.

    Ett fält som saknas eller inte går att tolka UTELÄMNAS ur dict:en. Då fäller
    `fordonsuppslag._kontrollera` med sitt eget skäl, och det anropet faller
    till utkast. Det är rätt riktning: inget skickas på fakta vi inte har.
    """
    ut: dict = {}

    for nyckel, etikett in EXAKT_ETIKETT.items():
        skydd = re.escape(etikett)

        # LAGER 2 RÄKNAR ETIKETTEN, inte värdeparen. Se `ETIKETTSPAN`: ett par
        # vars värde bär nästlad markup syns inte i `MONSTER`, och en räkning
        # på `traffar` missade därför dubbletten och svarade med det andra
        # värdet.
        forekomster = len(re.findall(ETIKETTSPAN.format(etikett=skydd), sida))
        if forekomster > 1:
            raise Hamtningsfel(
                f"etiketten {etikett!r} förekommer {forekomster} gånger, tvetydigt"
            )

        traffar = re.findall(MONSTER.format(etikett=skydd), sida)

        if not traffar:
            continue

        ratt = html.unescape(traffar[0])

        if nyckel == "draganordning":
            varde = _ja_nej(ratt)
        else:
            varde = _tal(ratt)

        if varde is not None:
            ut[nyckel] = varde

    return ut


def biluppgifter_hamtning(
    *,
    oppna: Callable[[str], tuple[int, str]] | None = None,
) -> Callable[[str], dict | None]:
    """Hämtningen som `fordonsuppslag.slag_upp` tar emot som `hamta`.

    `oppna` är den injicerade nätverksdelen och finns för att sviten ska kunna
    pröva parsningen utan socket. Förvalet är den riktiga hämtningen. Att
    parametern har ett förval är avsiktligt och skiljer sig från `slag_upp`:s
    `hamta`, som medvetet saknar det: `slag_upp` väljer KÄLLA, och en tyst
    standardkälla i en sändvägsmodul är vad §10 finns för att hindra. Här är
    källan redan vald av modulens namn.

    RETURKONTRAKTET, det `slag_upp` kräver:

    - `dict` med de fält som gick att läsa. Saknade fält utelämnas, och spärren
      i `_kontrollera` fäller då.
    - `None` när fordonet inte finns. Det avgörs av `canonical` och inte av
      statuskoden, eftersom sidan svarar 200 med söksidan på ett okänt nummer.
    - `Hamtningsfel` när källan inte svarade eller svarade med något annat.
      **Det undantaget fångas inte av `slag_upp`.**
    """
    hamtare = oppna or _hamta_sidan

    def hamta(regnr: str) -> dict | None:
        status, sida = hamtare(regnr)

        if status == 404:
            return None

        if status != 200:
            raise Hamtningsfel(f"biluppgifter.se svarade {status}")

        if not _galler_fordonet(sida, regnr):
            return None

        return _las_falt(sida)

    return hamta


def _hamta_sidan(regnr: str) -> tuple[int, str]:
    """Den riktiga nätverkshämtningen. Returnerar status och kropp.

    404 översätts INTE till ett undantag här, eftersom ett fordon som inte finns
    är ett giltigt svar från källan. Allt annat som går fel blir `Hamtningsfel`,
    inklusive timeout och DNS: `slag_upp` ska se skillnad på tystnad och tomhet.
    """
    begaran = urllib.request.Request(
        URL_MALL.format(regnr=regnr),
        headers={"User-Agent": UA, "Accept-Language": "sv-SE,sv;q=0.9"},
    )

    try:
        with urllib.request.urlopen(begaran, timeout=TIDSGRANS_S) as svar:
            return svar.status, svar.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as fel:
        if fel.code == 404:
            return 404, ""
        raise Hamtningsfel(f"biluppgifter.se svarade {fel.code}") from fel
    except (urllib.error.URLError, TimeoutError, OSError) as fel:
        raise Hamtningsfel(f"biluppgifter.se gick inte att nå: {fel}") from fel
