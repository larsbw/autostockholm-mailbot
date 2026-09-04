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

**SIDAN PARSAS, DEN MATCHAS INTE SOM TEXT.** Beslut av Lars, #32, efter att
skiva 21 mätt upp fem sändvägsdefekter i den regexbaserade avläsningen. Alla
fem hade samma orsak: mönstren BESKREV sidans nuvarande markup, och en
beskrivning som inte längre stämmer tystnar i stället för att kasta. Se
`_Faltlasare` om vad ombyggnaden stänger och vad den avsiktligt inte gör.

En följd som ska sägas rakt ut: **modulen faller inte längre på kosmetiska
markupändringar i ETIKETTEN.** Ett attribut, ett klassord till eller ett annat
elementnamn läses nu i stället för att ge ett saknat fält. Det ser ut som en
uppmjukning och är motsatsen: det var samma okänslighet för markup som gjorde att
en DUBBLERAD etikett inte upptäcktes.

**FÖR VÄRDET GÄLLER MOTSATSEN SEDAN SKIVA 24.** Nästlad markup i ett värde KASTAR,
se lucka 11 i `docs/sparrar.md`: samma konkatenering som gjorde
`2400 <abbr>kg</abbr>` läsbar gjorde `750<sup>1</sup> kg` till 7501. *Här stod att
även nästlad markup i värdet läses, vilket blev falskt av skiva 24 och stod kvar
oförändrat tills granskningens tredje varv fällde det.*

INGET NYTT BEROENDE. `urllib`, `re` och `html.parser` ur standardbiblioteket.
Frågan om ett beroende ställdes i briefen till skiva 22, och svaret är att
stdlib räcker. `requirements.txt` rörs inte.

**HÄMTNINGEN ÄR SÄNDVÄG enligt CLAUDE.md §7.** Den avgör med vilket innehåll ett
a-traktorsvar lämnar servern. Full granskning gäller, och spärren nedan är
registrerad i `docs/sparrar.md`.
"""

from __future__ import annotations

import http.client
import json
import re
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

# LOGGEN ÖVER MISSLYCKADE UPPSLAG. Append-only JSONL, samma form som repots
# övriga loggar, och under gitignorerade `logg/`.
#
# **REGISTRERINGSNUMRET SKRIVS HÄR OCH INGEN ANNANSTANS.** §6 förbjuder
# persondata i rapporter, commitmeddelanden, `docs/` och allt som pushas.
# `logg/` är gitignorerad, alltså är den den enda plats numret får stå på.
LOGGFIL = Path(__file__).resolve().parent.parent / "logg" / "uppslag.jsonl"

# Sidans adress. Registreringsnumret kommer normaliserat till VERSALER av
# `fordonsuppslag.slag_upp`, och sidan svarar på både gemener och versaler,
# avläst 2026-09-02. Numret URL-kodas inte: `normalisera_regnr` har redan
# strippat blanksteg och bindestreck. Ett nummer som bär något annat får alltså
# gå ut i URL:en och avvisas därefter av `canonical`-ankaret nedan, INTE av
# statuskoden: sidan svarar 200 med söksidan på ett nummer den inte känner, se
# kommentaren vid `FORVANTAT_SCHEMA` och `_galler_fordonet`. *Hänvisningen gick
# tidigare till `CANONICAL`, en konstant som togs bort med regexen.*
URL_MALL = "https://biluppgifter.se/fordon/{regnr}/"

# EN USER AGENT SOM NAMNGER OSS. Beslut av Lars i skiva 29: ingen förklädnad.
#
# **HÄR STOD EN WEBBLÄSARSTRÄNG, och den var lastbärande.** Kommentaren som
# ersätts sade, avläst 2026-09-02, att sidan svarar 200 på en webbläsarklient och
# avvisade Perplexitys hämtare med klientfel, alltså att filtreringen sker på
# klienten. Att byta till ett ärligt namn kan därför göra att hämtningen slutar
# fungera.
#
# **DET ÄR OPRÖVAT.** Ingen körning mot biluppgifter.se har gjorts med den här
# strängen, och sviten rör inte nätet. Faller hämtningen syns det i
# `logg/uppslag.jsonl` som `natverksfel` eller som en statuskod, vilket är hela
# skälet till att loggningen byggs i samma skiva. PRO-API:t är vägen tillbaka.
UA = "AutoStockholmBot/1.0 (+https://autostockholm.se; info@autostockholm.se)"

TIDSGRANS_S = 20

# Sömmens tre nycklar, avbildade på sidans etiketter. Vänsterledet är
# `fordonsuppslag._kontrollera`:s nycklar och får inte ändras här; högerledet är
# Lars fältval.
EXAKT_ETIKETT = {
    "tjanstevikt_kg": "Tjänstevikt",
    "slapvagnsvikt_kg": "Släpvagnsvikt",
    "draganordning": "Draganordning",
}

# SIDAN PARSAS, DEN MATCHAS INTE SOM TEXT. Beslut av Lars, `docs/beslutslogg.md`
# #32.
#
# **SKÄLET ÄR MÄTT.** Skiva 21 prövade tio sidändringar mot den regexbaserade
# avläsningen och fann FEM sändvägsdefekter, alla av samma klass: ett mönster
# skrivet för sidans nuvarande markup TYSTNAR i stället för att kasta när
# markupen ser annorlunda ut, och släpper då ut ett värde. De elva
# mutationsfällningarna mot koden hittade ingen av dem, eftersom koden var
# självkonsistent i samtliga fall.
#
# De två sista, som den här modulen är omskriven för att stänga:
#
#   dubblett   låg etiketten två gånger och den ENA förekomsten bar ett extra
#              klassord, nästlad markup runt namnet, eller ett annat element än
#              `span`, såg räknaren en enda förekomst. Tvetydigheten tände
#              aldrig, och det andra parets 750 kg gick ut där 2400 kg var rätt.
#   kommentar  ett fält som låg kvar i `<!-- -->` eller i `<template>` lästes som
#              om det vore aktivt.
#
# **BÅDA UPPHÖR AV KONSTRUKTIONEN OCH INTE AV ETT NYTT VILLKOR.** En etikett är
# nu en NOD, alltså räknas den likadant oavsett vilket element den står i och
# vilka klasser elementet bär utöver `label`. En HTML-kommentar når aldrig
# `handle_data`, och `<template>` hoppas över uttryckligen. Det är skillnaden
# mellan att beskriva markupen och att läsa den.
#
# INGET NYTT BEROENDE. `html.parser` ur standardbiblioteket. Frågan ställdes i
# briefen och svaret är att stdlib räcker: det som behövs är taggar, attribut,
# text och kommentarer hållna isär, och `HTMLParser` gör precis det.
# `requirements.txt` rörs inte.

# Element vars INNEHÅLL aldrig är sidans data, och vad som FAKTISKT bär vart och
# ett. Skillnaden mättes upp av granskningen av skiva 22 och ska stå här, för
# den avgör vilken rad en §7.1-prövning ska fälla:
#
#   template   bärs av `HOPPAS_OVER` nedan. Detta är den enda av de fyra som
#              raden binder, och `if tagg in HOPPAS_OVER:` är alltså fällbar.
#   noscript   bärs också av `HOPPAS_OVER`. Innehållet visas bara för en läsare
#              utan skript, alltså är det en ALTERNATIV rendering. Ett fält som
#              bara står där ger utkast, vilket är den säkra riktningen.
#   script     bärs av `HTMLParser`:s CDATA-läge, inte av raden nedan.
#   style      samma sak.
#
# En kommentar bärs varken av raden eller av CDATA-läget utan av att
# `HTMLParser` skickar den till `handle_comment`, som vi inte definierar.
#
# **HÄR STOD ATT `HOPPAS_OVER` HOPPAR ÖVER ALLA TRE.** Det var fel om koden:
# fälls raden blir bara `template`-fallet rött. Att `script` och `style` ändå
# är säkra beror på biblioteket och inte på oss, och den som räknar dem som
# lager får ett falskt bevisvärde.
HOPPAS_OVER = frozenset({"noscript", "script", "style", "template"})

# Taggar som saknar sluttagg. De får aldrig påverka stacken nedan.
#
# MÄNGDEN ÄR DISJUNKT MOT `HOPPAS_OVER`, och det är därför överhoppningens
# djupräknare inte behöver undanta den. Villkoret bar först ett sådant undantag;
# §7.1-prövningen visade att det inte gick att fälla, eftersom `tagg ==
# self._hoppa_tagg` redan innebär att taggen står i `HOPPAS_OVER`.
TOMMA_TAGGAR = frozenset(
    {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }
)

# FOTNOTSELEMENT UTESLUTS UR ETIKETTENS TEXT. Beslut av Lars, skiva 23, som
# stänger lucka 7 strukturellt.
#
# **VAD LUCKAN VAR.** Skrev källan `<span class="label">Släpvagnsvikt<sup>1</sup>`
# blev nodens text `Släpvagnsvikt1`, alltså en annan sträng. Bar sidan BÅDE den
# fotnotade och en oförändrad `Släpvagnsvikt` räknades bara den senare,
# tvetydigheten tände aldrig, och dess värde gick ut. Uppmätt i skiva 22.
#
# **VARFÖR INTE PREFIX.** En räknare som matchar på prefix hade fångat fallet och
# samtidigt kastat på varje verkligt svar, eftersom `Släpvagnsvikt obromsad`
# inleds likadant. `test_prefixraknare_hade_larmat_pa_den_avlasta_sidan` mäter
# det. Ett larm som alltid går blir avstängt.
#
# **MÄNGDEN ÄR INTE AVLÄST UR KÄLLAN, och det ska sägas rakt ut.** Fixturens åtta
# avlästa värden bär ingen fotnot alls, så sidan visar inte vilket element den
# skulle använda. `sup` och `small` är de konventionella bärarna av en
# fotnotsmarkör och en upplysning i småstil. Byter källan till ett tredje element
# står luckan öppen igen för just det elementet.
#
# **BARA ETIKETTEN, ALDRIG VÄRDET.** Ett värde är ett tal vi skickar vidare, och
# att tyst plocka bort tecken ur det vore att ändra talet. Etiketten är en nyckel
# vi jämför, och där är uteslutningen precis vad som gör två skrivningar av samma
# fält till samma nyckel.
FOTNOTSELEMENT = frozenset({"small", "sup"})

# Klassnamnen som bär fältblocket. Sidan skriver `<span class="label">` följd av
# `<span class="value">`, avläst 2026-09-02.
KLASS_ETIKETT = "label"
KLASS_VARDE = "value"


def _klasser(attribut: list[tuple[str, str | None]]) -> set[str]:
    """Elementets klassord som mängd, GEMENER. Tom mängd när `class` saknas.

    **KLASSVÄRDET SKIFTLÄGESNORMALISERAS, och det var en sändvägsdefekt att det
    inte gjordes.** Uppmätt av granskningen av skiva 22: låg etiketten två
    gånger och den ena bar `class="Label"`, såg räknaren en enda förekomst,
    tvetydigheten tände aldrig, och det andra parets 750 kg gick ut där 2400 var
    rätt. Attributnamnet normaliserades men värdet inte, vilket är samma
    versalfälla som `docs/beslutslogg.md` #28 beskriver i en annan modul.

    Riktningen är säker: gemener gör att FLER noder räknas, alltså kastar
    tvetydigheten oftare. Samma normalisering gäller läsaren, så de två kan inte
    glida isär.
    """
    for namn, varde in attribut:
        if namn.lower() == "class":
            return {ord_ for ord_ in (varde or "").lower().split()}
    return set()


def _behall(serie: int | None, text: str) -> str:
    """Textbiten som ska ingå i etikettens namn, eller tom sträng.

    Text utanför varje fotnotselement behålls alltid. Text INUTI ett behålls om
    den bär minst en bokstav, se `_Faltlasare._etikettext` om varför.
    """
    if serie is None:
        return text
    return text if any(tecken.isalpha() for tecken in text) else ""


class _Faltlasare(HTMLParser):
    """Plockar etikettnoder, etikett/värde-par och canonical-ankare ur sidan.

    **ETIKETTERNA SAMLAS SEPARAT FRÅN PAREN, OCH DET ÄR AVSIKTLIGT.**
    `etiketter` bär varje etikettnod i sidans ordning, även de som inte följs av
    något värde. `par` bär bara de som gör det. Tvetydighetskontrollen räknar
    `etiketter` medan avläsningen läser `par`.

    **SKILLNADEN MELLAN DE TVÅ FÅR ALDRIG BLI ETT LARM.** Beslut av Lars i
    briefen till skiva 22. Den skarpa sidan bär fler etikettnoder än par av
    legitima skäl: ett värde vars span öppnar ett element, till exempel
    `Chassinr / VIN` vars value-span öppnar ett `<a hx-get=...>`. Ett larm som
    alltid går blir avstängt, och en spärr som är avstängd skyddar ingenting.

    **ETT PAR MÅSTE HA SAMMA FÖRÄLDER, och villkoret är inte kosmetiskt.** Den
    gamla regexen krävde att värdespannen följde direkt efter etikettspannen i
    källtexten. En parser som bara letar `nästa värdenod` släpper det kravet
    helt, och då kan en etikett utan värde paras ihop med ett värde utan etikett
    längre ned i dokumentet. Resultatet vore ett tal ur ett annat fältblock.

    **FÖRÄLDERN JÄMFÖRS PÅ IDENTITET, INTE PÅ NIVÅTAL, och det var en
    sändvägsdefekt att den inte gjorde det.** Uppmätt av granskningen av
    skiva 22: en OSTÄNGD inline-tagg inuti etikettens förälder blåste upp
    nivåtalet, föräldern stängde utan att villkoret slog till, och etiketten
    parades med ett värde ur ett senare block. Varje öppet element bär därför
    ett eget löpnummer, och paret bildas bara när värdets förälder är SAMMA
    element som etikettens.

    **STACKEN TÅL FELFORMAD HTML, för sidan är inte vår att lita på.** En
    sluttagg letar upp närmaste öppna element med samma NAMN och stänger allt
    ovanför det; en sluttagg utan motsvarande starttagg ignoreras helt. Den
    gamla räkningen minskade i stället ett tal för varje sluttagg, vilket gjorde
    att ett ensamt `</br>` inuti ett `<template>` avslutade överhoppningen mitt
    i mallen och lät resten av innehållet läsas som sidans data. Också det var
    en sändvägsdefekt, och den återöppnade skiva 21:s defekt 2 i ny form.
    """

    def __init__(self, kalla: str) -> None:
        super().__init__(convert_charrefs=True)
        # KÄLLTEXTEN I SIN HELHET, som spärren mäter värdena mot. Se
        # `_varde_bar_markup`.
        self._kalla = kalla
        # Absolut position för varje rads början, så att `getpos()`:s
        # `(rad, kolumn)` går att räkna om till ett index i `_kalla`.
        self._radstart = [0]
        for index, tecken in enumerate(kalla):
            if tecken == "\n":
                self._radstart.append(index + 1)
        self.etiketter: list[str] = []
        # `(etikett, värdetext, värdet bar markup)`. Tredje ledet är lucka 11:s
        # och lucka 12:s spärr, se `_varde_bar_markup` och `_las_falt`.
        self.par: list[tuple[str, str, bool]] = []
        self.ankare: list[str] = []
        # Överhoppningen följer TAGGNAMNET och inte ett tal, se klassens
        # docstring om `</br>` inuti `<template>`.
        self._hoppa_tagg: str | None = None
        self._hoppa_djup = 0
        # Varje öppet element som `(taggnamn, löpnummer, sort)`.
        self._stack: list[tuple[str, int, str | None]] = []
        self._serie = 0
        self._aktiv: int | None = None
        # Varje textbit med löpnumret för det fotnotselement den står i, eller
        # `None`. Se `_etikettext`.
        self._text: list[tuple[str, int | None]] = []
        self._vantar: str | None = None
        self._vantar_foralder: int | None = None
        # Absolut position i `_kalla` där det aktiva värdets INNEHÅLL börjar,
        # alltså direkt efter dess starttagg.
        self._varde_start: int | None = None

    def _oppna(self, tagg: str, attribut: list[tuple[str, str | None]]) -> None:
        """Det som gäller både `<x>` och `<x/>`, alltså utom stacken."""
        if tagg != "link":
            return
        karta = {namn.lower(): varde for namn, varde in attribut}
        if (karta.get("rel") or "").strip().lower() == "canonical":
            self.ankare.append((karta.get("href") or "").strip())

    def _foralder(self, index: int) -> int | None:
        """Löpnumret för elementet UNDER `index` i stacken."""
        return self._stack[index - 1][1] if index > 0 else None

    def _abs_pos(self) -> int:
        """`getpos()` omräknat till ett index i `_kalla`.

        `HTMLParser` sätter positionen till början av den konstruktion som just
        hanteras, alltså till `<` i en tagg. Avläst i en körning, inte antaget.
        """
        rad, kolumn = self.getpos()
        return self._radstart[rad - 1] + kolumn

    def _varde_bar_markup(self, slut: int, egen_sluttagg: bool, samlad: str) -> bool:
        """SPÄRREN MOT LUCKA 11 OCH 12, mätt som en EGENSKAP och inte som en lista.

        **VÄRDETS RÅA KÄLLTEXT SKA VARA IDENTISK MED DESS TEXTNODER.** Är den inte
        det innehöll värdet markup, oavsett sort. Beslut av Lars, skiva 25.

        **VARFÖR EGENSKAPEN OCH INTE HÄNDELSEN.** Varje lydelse före den här
        beskrev en HÄNDELSE, och de föll på en händelse ingen tänkt på. Formerna,
        var för sig:

            skiva 24, första   bara starttaggar flaggade
            granskningsvarv 1  kommentar, processing instruction, declaration
                               och ensam sluttagg gjorde samma sak
            granskningsvarv 2  `handle_endtag` returnerar för `TOMMA_TAGGAR`
                               FÖRE den gren rättelsen lade in
            granskningsvarv 3  `handle_endtag`:s TRÄFFGREN flaggade inte alls

        **En händelselista går alltid att utöka med en post till**, och det är
        därför den fortsatte falla. Jämförelsen nedan går inte att utöka: den
        frågar inte VAD som stod i värdet, bara om värdets text är hela värdet.

        **ENTITETER ÄR INTE MARKUP.** `convert_charrefs` gör `&nbsp;` till ett
        hårt blanksteg i textnoden, så råtexten och textnoden skiljer sig åt på
        varje entitet. `unescape` är samma funktion `html.parser` själv använder,
        så jämförelsen görs efter den. `2&nbsp;400 kg` är källans eget format och
        ska läsas, vilket `test_format_som_sidan_faktiskt_anvander_lases` kräver.

        **EN STÄNGNING SOM INTE ÄR VÄRDETS EGEN GÅR INTE ATT MÄTA, och då är
        egenskapen inte uppfylld.** Stänger en sluttagg ett element UNDER värdet
        avslutas fältet där, och värdets verkliga utsträckning är okänd: allt
        efter sluttaggen släpps utan att någon vet hur mycket det var. Det är
        lucka 12, och det ledet är inte en femte händelse utan samma egenskap
        tillämpad på det fall där den inte GÅR att mäta. Vi vet inte, alltså
        svarar vi inte.

        **HÄR STOD EN TREDJE GREN, `if self._varde_start is None: return True`,
        och den är BORTTAGEN.** Granskningen av skiva 25 fällde den som obunden:
        en fällning gav GRÖN, och en injicerad `AssertionError` på raden gav också
        GRÖN, alltså nådde inget av svitens test grenen över huvud taget.

        Skälet är en invariant: `_varde_start` sätts i samma gren som sätter
        `_aktiv`, och nollställs i `_stang_faltet` i samma andetag som
        `_aktiv = None`. Metoden anropas bara därifrån, alltså är `_varde_start`
        satt när den körs.

        **BRYTS INVARIANTEN KASTAR INGENTING, och det ska stå rätt.** Python
        godtar `None` som snittstart: `'abcdef'[None:3]` ger `'abc'`, avläst i en
        körning. Ett brutet invariant läser alltså från sidans BÖRJAN i stället.
        Utfallet blir ändå säkert, eftersom en jämförelse mot hela sidhuvudet inte
        kan bli lika med värdets textnoder, så värdet flaggas och kastar. Men det
        är jämförelsen som räddar det, inte snittet.

        *Här stod att snittet kastar högljutt. Fällt av granskningsvarv 2 i skiva
        25, och det var rättelsens EGEN motivering som bar felet.*

        Valet att ta bort grenen står ändå: samma val som det borttagna
        `_vantar`-villkoret i `handle_endtag`.
        """
        if not egen_sluttagg:
            return True

        return unescape(self._kalla[self._varde_start : slut]) != samlad

    def _stang_faltet(self, slut: int, egen_sluttagg: bool) -> None:
        """Avslutar det aktiva etikett- eller värdeelementet.

        `slut` är positionen för den sluttagg som avslutar fältet, och
        `egen_sluttagg` säger om den stänger fältets EGET element. Båda behövs av
        `_varde_bar_markup`.
        """
        sort = self._stack[self._aktiv][2]
        foralder = self._foralder(self._aktiv)
        samlad = "".join(data for data, _ in self._text)

        if sort == KLASS_ETIKETT:
            text = self._etikettext()
            self.etiketter.append(text)
            self._vantar = text
            self._vantar_foralder = foralder
        else:
            text = samlad.strip()
            bar_markup = self._varde_bar_markup(slut, egen_sluttagg, samlad)
            if self._vantar is not None and foralder == self._vantar_foralder:
                self.par.append((self._vantar, text, bar_markup))
                self._vantar = None

        self._aktiv = None
        self._text = []
        self._varde_start = None

    def handle_starttag(self, tagg: str, attribut) -> None:
        if self._hoppa_tagg is not None:
            # Bara element med SAMMA namn räknas. En sluttagg av annat slag,
            # ett ensamt `</br>` eller `</li>`, får inte röra djupet: det var
            # den defekten som lät en mall läcka sitt innehåll.
            if tagg == self._hoppa_tagg:
                self._hoppa_djup += 1
            return

        if tagg in HOPPAS_OVER:
            self._hoppa_tagg = tagg
            self._hoppa_djup = 1
            return

        self._oppna(tagg, attribut)

        if tagg in TOMMA_TAGGAR:
            return

        sort: str | None = None
        if self._aktiv is None:
            klasser = _klasser(attribut)
            if KLASS_ETIKETT in klasser:
                sort = KLASS_ETIKETT
            elif KLASS_VARDE in klasser:
                sort = KLASS_VARDE

        self._serie += 1
        self._stack.append((tagg, self._serie, sort))

        if sort is not None:
            self._aktiv = len(self._stack) - 1
            self._text = []
            # VÄRDETS INNEHÅLL BÖRJAR DIREKT EFTER DESS STARTTAGG.
            # `get_starttag_text` ger taggen precis som den står i källan,
            # attribut och blanksteg inräknade, så positionen blir rätt även när
            # taggen är skriven på ett sätt vi inte förutsett.
            self._varde_start = self._abs_pos() + len(self.get_starttag_text())

    def handle_startendtag(self, tagg: str, attribut) -> None:
        # `<x/>` öppnar och stänger i samma tagg och rör därför inte stacken.
        # Basklassens förval anropar start och slut i följd, vilket hade lagt
        # ett element på stacken som ingen sluttagg tar bort.
        if self._hoppa_tagg is not None:
            return
        self._oppna(tagg, attribut)

    def handle_endtag(self, tagg: str) -> None:
        if self._hoppa_tagg is not None:
            if tagg == self._hoppa_tagg:
                self._hoppa_djup -= 1
                if self._hoppa_djup <= 0:
                    self._hoppa_tagg = None
            return

        # INGEN AV DE TVÅ GRENARNA NEDAN FLAGGAR NÅGOT, och det är skiva 25:s
        # hela poäng. `</br>` och en sluttagg utan öppen motsvarighet lämnar
        # spår i värdets RÅTEXT, och den jämförelsen görs i `_varde_bar_markup`
        # när fältet stängs. Att räkna upp nodtyper här var vad de föregående
        # lydelserna gjorde, och de föll på en nodtyp ingen hade räknat.
        if tagg in TOMMA_TAGGAR:
            return

        for index in range(len(self._stack) - 1, -1, -1):
            if self._stack[index][0] == tagg:
                break
        else:
            # Sluttagg utan öppen motsvarighet. Sidan är felformad, och att
            # gissa vad den stänger vore att låta felformningen styra vad vi
            # läser.
            return

        if self._aktiv is not None and self._aktiv >= index:
            self._stang_faltet(self._abs_pos(), index == self._aktiv)

        del self._stack[index:]

        # HÄR STOD EN RENSNING AV `_vantar` NÄR ETIKETTENS FÖRÄLDER STÄNGDE.
        # Den var nödvändig när föräldern jämfördes på NIVÅTAL, och är det inte
        # längre: löpnumren är unika, så när förälderns element väl stängt kan
        # inget senare element få samma nummer, och jämförelsen i
        # `_stang_faltet` fäller paret av sig själv.
        #
        # **§7.1-PRÖVNINGEN VISADE DET.** Fälld ensam förblev sviten grön, och
        # det var inte ett saknat test utan ett villkor som inget kunde fälla,
        # eftersom fallet det vaktade blivit oåtkomligt. Ett villkor som ser ut
        # som försiktighet utan att kunna göra något är precis det §7.1 kallar
        # vakuöst, och då är valet att binda det eller ta bort det.

    def _fotnot_serie(self) -> int | None:
        """Löpnumret för närmaste öppna FOTNOTSELEMENT inuti det aktiva fältet.

        Stacken läses från elementet ovanför det aktiva, alltså räknas fältets
        egen tagg aldrig med: en etikett som SJÄLV står i ett `<small>` är
        fortfarande en etikett, och dess text är fältets namn och ingen fotnot.
        """
        for tagg, serie, _ in reversed(self._stack[self._aktiv + 1 :]):
            if tagg in FOTNOTSELEMENT:
                return serie
        return None

    def _etikettext(self) -> str:
        """Etikettens text med fotnotsMARKÖRER borttagna, aldrig med ORD.

        **VILLKORET ÄR ATT MARKÖREN SAKNAR BOKSTÄVER, och det är inte kosmetik.**
        En uteslutning som tog bort ALLT innehåll i ett `sup` eller `small` gav två
        sändvägsdefekter, båda uppmätta av granskningen av skiva 23 och båda i den
        riktning som släpper ut ett värde:

          `Släpvagnsvikt<small> obromsad</small>` blev `Släpvagnsvikt`, alltså den
          OBROMSADE vikten levererad som den bromsade. 750 kg under tröskeln där
          2400 kg var rätt.

          `<span class="label"><small>Släpvagnsvikt</small></span>` blev en TOM
          etikett, alltså osynlig för räknaren. Låg en oförändrad `Släpvagnsvikt`
          på samma sida tände tvetydigheten aldrig och det andra parets 750 kg gick
          ut. Det är lucka 7 själv, återöppnad av sin egen rättelse.

        En fotnotsMARKÖR är en siffra, en asterisk eller ett kors. Bär elementet en
        bokstav är innehållet ett ORD, och ett ord i etikettnoden är en del av
        fältets namn tills motsatsen är visad. Texten behålls då, etiketten blir en
        annan sträng, och fältet faller till utkast. Det är den säkra riktningen:
        vi svarar inte, i stället för att svara fel.

        Grupperingen sker per fotnotsELEMENT och inte per textbit, eftersom
        `HTMLParser` delar texten vid varje entitet. `<sup>a&nbsp;1</sup>` ska
        bedömas som en enhet, inte som bitarna `a` och `1` var för sig.
        """
        bitar: list[str] = []
        grupp: list[str] = []
        grupp_serie: int | None = None
        oppnad = False

        for data, serie in self._text:
            if oppnad and serie == grupp_serie:
                grupp.append(data)
                continue
            if oppnad:
                bitar.append(_behall(grupp_serie, "".join(grupp)))
            grupp = [data]
            grupp_serie = serie
            oppnad = True

        if oppnad:
            bitar.append(_behall(grupp_serie, "".join(grupp)))

        return "".join(bitar).strip()

    def handle_data(self, data: str) -> None:
        if self._hoppa_tagg is not None or self._aktiv is None:
            return
        self._text.append((data, self._fotnot_serie()))

    # HÄR STOD FYRA METODER, `handle_comment`, `handle_pi`, `handle_decl` och
    # `unknown_decl`, som var för sig flaggade värdet. De är BORTA i skiva 25.
    #
    # De hörde till en händelselista, och listan behövdes bara så länge spärren
    # frågade VAD som stod i värdet. `_varde_bar_markup` frågar i stället om
    # värdets text är hela värdet, och en kommentar, en processing instruction,
    # en declaration och en CDATA-sektion lämnar alla spår i råtexten. Att ta
    # bort metoderna är därför inte en uppmjukning: samma fall fälls, av ett
    # villkor som inte går att utöka.
    #
    # *Här stod att metoderna var den FJÄRDE lydelsen och att TRE föregående föll
    # på en nodtyp ingen räknat. Talen går inte att läsa ur repot. Rättelsen tog
    # först bort dem på ett ställe och lämnade dem kvar här och i
    # `handle_endtag`, sju rader från den här notens eget löfte; fällt av
    # granskningsvarv 3. Formerna är uppräknade var för sig i
    # `_varde_bar_markup`.*


def _lasaren(sida: str) -> _Faltlasare:
    """Parsar sidan en gång och returnerar läsaren.

    SIDAN PARSAS TVÅ GÅNGER PER UPPSLAG, en gång för ankaret och en gång för
    fälten, eftersom `_galler_fordonet` och `_las_falt` tar en sträng var. Det
    är medvetet: de två är svitens angreppsytor och prövas var för sig, och en
    delad läsare hade gjort dem beroende av anropsordningen. Kostnaden är en
    extra parsning av en sida vi redan hämtat över nätet.
    """
    lasare = _Faltlasare(sida)
    lasare.feed(sida)
    lasare.close()
    return lasare


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
# Kontrollen är inte kosmetisk. Utan den läser modulen fältetiketter ur vilken
# sida källan än råkar svara med, och en söksida som en dag bär ett exempel med
# etiketten `Tjänstevikt` hade då blivit ett tal i ett kundmail. Att söksidan i
# dag bär noll `class="label"` är en avläsning av i dag, inte en garanti.
#
# **HELA URL:EN JÄMFÖRS, INTE SISTA SEGMENTET.** Beslut av Lars, #32. Den gamla
# jämförelsen tog `rsplit("/", 1)[-1]` och godtog därför vilken domän och
# vilken sökväg som helst så länge numret stod sist. Uppmätt i skiva 21: ett
# ankare på en helt annan domän med rätt nummer sist gav ett uppslag.
FORVANTAT_SCHEMA = "https"
FORVANTAD_VARD = "biluppgifter.se"
FORVANTAD_KATALOG = "/fordon"


class Hamtningsfel(Exception):
    """Källan svarade inte, eller svarade med något annat än en fordonssida.

    SKILD FRÅN `UppslagMisslyckades` MED AVSIKT. `slag_upp`:s kontrakt säger att
    hämtningens egna undantag INTE fångas utan når anroparen, därför att en
    källa som är nere inte är samma sak som ett fordon utan uppgifter. Att
    översätta det ena till det andra hade gjort ett driftavbrott osynligt.
    """


# ETT VÄRDE SOM SER UT SOM EN VIKT MEN INTE ÄR ETT TAL. Se `_tal` om varför det
# kastar i stället för att utelämnas, och om varför klassen inte skriver ut någon
# escape för hårt blanksteg.
#
# Mönstret kräver MINST EN SIFFRA. Utan det ledet hade `' kg'` fällt grenen, och
# ett tomt värde är ett saknat fält och inte en felläsning. Den skillnaden bärs av
# `test_bara_blanktecken_fore_enheten_ger_none`.
MISSLASNING = re.compile(r"[\d\s]*\d[\d\s]*kg", flags=re.IGNORECASE)


def _tal(varde: str) -> int | None:
    r"""Vikten i hela kilo, `None` när fältet inte är en vikt, KAST när det är
    en felläsning.

    **DE TVÅ UTFALLEN BETYDER OLIKA SAKER, OCH SKILLNADEN ÄR SKIVA 23:S BESLUT.**
    Beslut av Lars. Ett utelämnat fält betyder VI VET INTE och ska falla till
    utkast. Ett värde som bär siffror och enheten `kg` men inte går att läsa som
    ETT tal betyder att avläsningen är FEL, och det ska kasta. `750 2400 kg` är
    det andra fallet: fältet fanns, det lästes, och läsningen misslyckades.

    Skillnaden är inte kosmetisk. Ett saknat fält och ett felläst fält gav förut
    samma svar till anroparen, alltså `None`, och därmed samma skäl nedströms. En
    källa som slår ihop den bromsade och den obromsade vikten i en rad hade då
    sett ut precis som en källa som slutat skriva raden alls.

    **KASTGRENEN KAN BARA NÅS AV SIFFROR OCH BLANKTECKEN.** Villkoret är
    `MISSLASNING` nedan, och texten i undantaget är därmed begränsad till just
    det: ett värde med bokstäver, andra tecken eller ett annat enhetsnamn når
    aldrig grenen och ger `None` som förut.

    **`MISSLASNING` SKRIVER INGEN ESCAPE FÖR HÅRT BLANKSTEG, och det är prövat
    och inte antaget.** `\s` matchar U+00A0 för strängmönster i Python 3, avläst
    med `chr(160)` i en körning. Teckenklassen `[\d\s]` täcker alltså det hårda
    blanksteget utan att källkoden behöver bära ett tecken som inte går att
    skilja från ett vanligt blanksteg när någon läser filen. Det gamla mönstret
    på raden nedan skriver ut escapen, och den formen är oförändrad här: den
    prövades i skiva 21 och 22 och rörs inte av den här skivan.

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
        rensat = varde.strip()
        if MISSLASNING.fullmatch(rensat):
            raise Hamtningsfel(
                f"värdet {rensat!r} bär siffror och enheten kg men går inte att "
                f"läsa som ett tal, alltså en felläsning och inte ett saknat fält"
            )
        return None

    siffror = re.sub(r"[\s\u00a0]", "", traff.group(1))
    return int(siffror)


# RIMLIGHETSGRÄNSER FÖR EN VIKT I KILO. Se `_krav_pa_rimlighet` om härkomsten.
MIN_VIKT_KG = 1
MAX_VIKT_KG = 9999


def _krav_pa_rimlighet(nyckel: str, varde: int) -> None:
    """Kastar när vikten ligger utanför vad en avläsning rimligen kan ge.

    **ETT VÄRDE UTANFÖR INTERVALLET ÄR EN FEL LÄSNING, INTE ETT FORDON.**
    Beslut av Lars, `docs/beslutslogg.md` #32, som lucka 5:s motmedel. Den
    defekt som gjorde kontrollen nödvändig gav 7502400, alltså två av sidans
    tal hopklistrade till ett välformat heltal långt över varje tröskel.
    `_tal` är skärpt så att just den hopklistringen inte längre går, men
    kontrollen står oberoende av mönstrets form: nästa avläsningsfel behöver
    inte se ut som det förra.

    **HÄRKOMSTEN, ETT LED I TAGET, EFTERSOM §7.2 KRÄVER DET.**

    Nedre gränsen är `1`, alltså strikt större än noll. Den är FYSISK och inget
    avläst tal: ett fordon väger mer än ingenting.

    Övre gränsen är `9999`, alltså fyra siffror. Två led bär den. Det första är
    avläst i repot: samtliga åtta värden i `SIDA_AVLAST` i
    `tests/test_biluppgifter.py` har högst fyra siffror, och fixturen är en
    verkliga VÄRDEN, avlästa ur ett svar 2026-09-02 och uppräknade i
    fixturkommentaren. *Här stod att fixturen är en verklig fordonssida. Sidan
    är byggd av testets egen `sida()`; det är värdena som är avlästa.* Det
    andra ledet är fysiskt: ett femsiffrigt kilotal är minst
    tio ton, alltså inget som konverteras till a-traktor.

    **DETTA ÄR SIFFERGRÄNSEN OCH INTE EN KALIBRERAD PERSONBILSGRÄNS, och det
    ska stå utskrivet.** En snävare övre gräns hade fångat mer, men den hade
    krävt ett tal jag varken kan läsa ur repot eller ur en körning, och §7.2
    säger att ett sådant tal ska utelämnas hur rimligt det än ser ut.

    **LARS HAR SVARAT I SKIVA 23: GRÄNSEN STÅR, och inget snävare tal sätts.** Se
    `docs/beslutslogg.md` #33 och lucka 8 i `docs/sparrar.md`. Den permissiva
    riktningen består alltså som ett vägt val. *Här stod att frågan är ställd
    till Lars och obesvarad; det gällde när det skrevs.*

    Kontrollen KASTAR i stället för att utelämna nyckeln. Det är avsiktligt och
    följer lager 2: ett fält som saknas betyder att vi inte vet, medan ett fält
    med ett omöjligt värde betyder att avläsningen är fel. De två ska inte se
    likadana ut för anroparen.
    """
    if MIN_VIKT_KG <= varde <= MAX_VIKT_KG:
        return

    raise Hamtningsfel(
        f"{nyckel} lästes som {varde} kg, utanför "
        f"{MIN_VIKT_KG}..{MAX_VIKT_KG} och alltså en felaktig avläsning"
    )


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


def _vard(netloc: str) -> str:
    """Värdnamnet i gemener, med ett inledande `www.` borttaget.

    **`www` GODTAS SOM SAMMA VÄRD. Beslut av Lars, skiva 23.** Skälet är inte att
    strikthet är fel, utan vilken sorts fel den producerar här. Börjar källan
    skriva sin canonical med `www` faller VARJE uppslag till utkast, och det syns
    inte: inget larm går, inget test blir rött, och flödet ser ut som en dag utan
    a-traktorärenden. En bot som slutat fungera och en bot utan trafik är samma
    bild för den som tittar.

    **VARJE ANNAN DOMÄN AVVISAS FORTFARANDE.** Uteslutningen gäller exakt
    prefixet `www.` och ingenting annat. `www.exempel.invalid` blir
    `exempel.invalid`, som inte är `FORVANTAD_VARD`, och faller. Det som stängdes
    i skiva 22, ett ankare på en annan domän med rätt nummer sist, är alltså
    orört.

    Prefixet kräver punkten. En värd som `wwwbiluppgifter.se` är ett annat
    värdnamn och rörs inte.
    """
    vard = netloc.lower()
    return vard[4:] if vard.startswith("www.") else vard


def _galler_fordonet(sida: str, regnr: str) -> bool:
    """Sant bara när sidans `canonical` pekar på det begärda registreringsnumret.

    Jämförelsen är skiftlägesokänslig, därför att `slag_upp` normaliserar numret
    till VERSALER medan sidan skriver sin canonical i gemener. Samma sorts
    versalfälla gav 46 av 78 i stället för 77 av 78 vid regnr-avläsningen, se
    `docs/beslutslogg.md` #28. Den ska inte återkomma i en annan modul.

    En sida UTAN canonical ger `False`, alltså `fordonet finns inte`. Det är det
    försiktiga förvalet: ett svar vi inte kan knyta till numret får inte bli
    fordonsfakta om numret.

    **TVÅ ANKARE KASTAR, de löses inte tyst.** Beslut av Lars, #32. Den gamla
    koden tog `re.search`, alltså första träffen, och en sida med vårt fordon
    först och ett annat sedan gav därför ett uppslag. Tvetydigheten var reell
    och besvarades med en gissning. **Lager 3 beter sig nu som lager 2 i samma
    läge:** en källa som säger två saker om vilket fordon sidan gäller har inte
    sagt något vi kan skicka ett mail på.

    **HELA URL:EN PRÖVAS.** Schema, värdnamn och sökväg, inte bara numret sist.
    Ett relativt ankare, `/fordon/<nummer>/`, har inget värdnamn och faller
    därför också: vi kan inte bekräfta vilken domän svaret kom ifrån, och det
    är samma försiktiga förval som vid ett saknat ankare.

    **VÄRDNAMNET JÄMFÖRS UTAN `www`, se `_vard`.** Det är den enda uppmjukningen
    i lager 3, den gäller exakt det prefixet, och skälet är att alternativet är
    ett fel som inte syns.
    """
    ankare = _lasaren(sida).ankare

    if len(ankare) > 1:
        raise Hamtningsfel(
            f"sidan bär {len(ankare)} canonical-ankare, tvetydigt vilket fordon den gäller"
        )

    if not ankare:
        return False

    delar = urlsplit(ankare[0])

    if delar.scheme.lower() != FORVANTAT_SCHEMA:
        return False

    if _vard(delar.netloc) != FORVANTAD_VARD:
        return False

    vag = delar.path.rstrip("/")
    return vag.upper() == f"{FORVANTAD_KATALOG}/{regnr}".upper()


def _las_falt(sida: str) -> dict:
    """Plockar de tre gatande fälten ur sidans HTML.

    SPÄRRENS FÖRSTA LAGER: `EXAKT_ETIKETT` jämförs med LIKHET mot etikettnodens
    text, alltså aldrig som prefix. Se modulens docstring om
    `Släpvagnsvikt obromsad`. Jämförelsen låg tidigare i ett regexuttryck med
    `re.escape` och en avslutande `</span>`. **Den ligger nu på TVÅ ställen, och
    det ska namnges rätt:** `namn == etikett` i urvalet av värden är lager 1,
    medan `lasare.etiketter.count(etikett)` är lager 2:s räkning. Här stod att
    lager 1 ligger i `str.count`; det var fel på båda leden, eftersom metoden är
    `list.count` och raden hör till lager 2.

    SPÄRRENS ANDRA LAGER: en etikett som förekommer FLERA gånger på sidan är
    tvetydig, och tvetydigheten kastar. Ett `ta första träffen` hade gjort
    sidans ordning till en tyst del av bedömningen.

    SPÄRRENS FJÄRDE LAGER bär sedan skiva 22 också en RIMLIGHETSKONTROLL, se
    `_krav_pa_rimlighet`. Den skiljer ett fält vi inte kunde läsa från ett fält
    vi läste FEL, och de två ska inte se likadana ut för anroparen.

    Ett fält som saknas eller inte går att tolka UTELÄMNAS ur dict:en. Då fäller
    `fordonsuppslag._kontrollera` med sitt eget skäl, och det anropet faller
    till utkast. Det är rätt riktning: inget skickas på fakta vi inte har.
    """
    lasare = _lasaren(sida)
    ut: dict = {}

    for nyckel, etikett in EXAKT_ETIKETT.items():
        # LAGER 2 RÄKNAR ETIKETTNODER. Jämförelsen är exakt likhet mot nodens
        # text, alltså aldrig ett prefix: `Släpvagnsvikt obromsad` är en annan
        # sträng och räknas inte.
        forekomster = lasare.etiketter.count(etikett)
        if forekomster > 1:
            raise Hamtningsfel(
                f"etiketten {etikett!r} förekommer {forekomster} gånger, tvetydigt"
            )

        varden = [
            (varde, bar_element)
            for namn, varde, bar_element in lasare.par
            if namn == etikett
        ]

        if not varden:
            continue

        ratt, bar_element = varden[0]

        # LUCKA 11:S SPÄRR. Ett värde vars text är avdelad av något som inte är
        # text går inte att tolka. Skälet står i `_varde_bar_markup`.
        #
        # MEDDELANDET SÄGER INTE `tal`, och det är avsiktligt: spärren gäller
        # alla tre fälten, och `draganordning` är ett ja eller ett nej.
        # Granskningen av skiva 24 fällde en tidigare lydelse som sade `tal` om
        # ett ja/nej-fält.
        if bar_element:
            raise Hamtningsfel(
                f"värdet för {etikett!r} bär markup och går därför inte att "
                f"tolka, alltså en felläsning och inte ett saknat fält"
            )

        if nyckel == "draganordning":
            varde = _ja_nej(ratt)
        else:
            varde = _tal(ratt)
            if varde is not None:
                _krav_pa_rimlighet(nyckel, varde)

        if varde is not None:
            ut[nyckel] = varde

    return ut


def logga_uppslag(regnr: str, skal: str, **extra) -> dict:
    """Skriver ett misslyckat uppslag till `logg/uppslag.jsonl`. Append-only.

    **ETT UPPSLAG SOM FALLER ÄR RÄTT BETEENDE. ETT SOM FALLER UTAN ATT NÅGON
    MÄRKER DET ÄR EN TYST NEDGÅNG.** Utan den här raden syns en sidändring bara
    i att a-traktorsvaren långsamt börjar hamna i `utkast`, vilket ser ut som
    försiktighet och inte som ett fel.

    `skal` är den maskinläsbara orsaken, och den är avsiktligt grov: den ska gå
    att räkna per dygn. `falt_saknas` är den som betyder att sidan bytt markup.

    En misslyckad SKRIVNING får inte hindra ett uppslag: går disken full är det
    bättre att uppslaget fortsätter utan logg än att övervakningen blir den sak
    som fäller. Därför sväljs `OSError` här, och ingen annanstans i modulen.

    **ABSOLUTET GÄLLER SKRIVNINGEN, INTE SERIALISERINGEN.** `json.dumps` kan
    kasta `TypeError` för ett värde som inte går att serialisera, och det fångas
    inte. Med `_hamta_sidan` som hämtare är `status` alltid `int` och `detalj`
    alltid `str`, så vägen är oåtkomlig i drift, men en injicerad `oppna` kan nå
    den. *Här stod "får ALDRIG hindra ett uppslag", vilket var starkare än
    koden. Fällt av §7-granskningen av skiva 29, varv 1.*
    """
    post = {
        "tidsstampel": datetime.now(timezone.utc).isoformat(),
        "regnr": regnr,
        "skal": skal,
        **extra,
    }
    try:
        LOGGFIL.parent.mkdir(parents=True, exist_ok=True)
        with LOGGFIL.open("a", encoding="utf-8") as fil:
            fil.write(json.dumps(post, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return post


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
        # LOGGAS OCH KASTAS VIDARE, aldrig sväljs. `Hamtningsfel` ur `hamtare`
        # är den form ett nätverksfel eller en timeout tar, och den ska nå
        # anroparen oförändrad. Loggraden är ett tillägg, inte en hantering.
        try:
            status, sida = hamtare(regnr)
        except Hamtningsfel as fel:
            logga_uppslag(regnr, "natverksfel", detalj=str(fel))
            raise

        if status == 404:
            logga_uppslag(regnr, "okant_fordon", status=404)
            return None

        if status != 200:
            logga_uppslag(regnr, "statuskod", status=status)
            raise Hamtningsfel(f"biluppgifter.se svarade {status}")

        # BÅDA STEGEN LIGGER UNDER SAMMA RAM, och det är ett fynd och inte en
        # stilfråga. Först låg bara `_las_falt` här, medan `_galler_fordonet`
        # kastade på raden ovanför utan att logga: en sida med två
        # canonical-ankare gav `Hamtningsfel` och INGEN rad, alltså precis den
        # tvetydighet loggen byggdes för. Fällt av §7-granskningen av skiva 29.
        #
        # Spärrarna är oförändrade. Ramen lägger till en loggrad före kastet och
        # kastar vidare med bar `raise`.
        try:
            if not _galler_fordonet(sida, regnr):
                logga_uppslag(regnr, "fel_fordon")
                return None
            falt = _las_falt(sida)
        except Hamtningsfel as fel:
            logga_uppslag(regnr, "fel_vid_lasning", detalj=str(fel))
            raise

        # **DEN HÄR RADEN ÄR SKÄLET TILL ATT LOGGEN FINNS.** Sidan svarade 200,
        # gällde rätt fordon, och gick att parsa, men bar inte fälten. Det är
        # vad en markupändring ser ut som, och utan loggen syns den bara i att
        # svaren tyst börjar hamna i `utkast`.
        saknade = sorted(set(EXAKT_ETIKETT) - set(falt))
        if saknade:
            logga_uppslag(regnr, "falt_saknas", saknade=saknade)

        return falt

    return hamta


def _hamta_sidan(regnr: str) -> tuple[int, str]:
    """Den riktiga nätverkshämtningen. Returnerar status och kropp.

    404 översätts INTE till ett undantag här, eftersom ett fordon som inte finns
    är ett giltigt svar från källan. Allt annat som går fel blir `Hamtningsfel`,
    inklusive timeout och DNS: `slag_upp` ska se skillnad på tystnad och tomhet.

    **ETT OMFÖRSÖK, INGEN LOOP.** Beslut av Lars i skiva 29. Omförsöket gäller
    bara det som kan vara övergående, alltså nätverksfel och timeout. En
    HTTP-statuskod är källans SVAR och försöks aldrig om: ett 403 blir inte 200
    av att frågas igen, och en loop mot en källa som avvisar oss är precis vad
    en ärlig user agent finns för att slippa.
    """
    # OMFÖRSÖKET FÅNGAR DE RÅA UNDANTAGEN, inte `Hamtningsfel`. Fångade det
    # `Hamtningsfel` skulle även en statuskod försökas om, eftersom `_ett_forsok`
    # kastar samma typ för båda, och docstringen ovan vore falsk om sin egen kod.
    try:
        return _ett_forsok(regnr)
    except (urllib.error.URLError, TimeoutError, OSError, http.client.IncompleteRead):
        pass

    try:
        return _ett_forsok(regnr)
    except (urllib.error.URLError, TimeoutError, OSError, http.client.IncompleteRead) as fel:
        raise Hamtningsfel(f"biluppgifter.se gick inte att nå: {fel}") from fel


def _ett_forsok(regnr: str) -> tuple[int, str]:
    """Ett enda anrop mot sidan. Omförsöket ligger i `_hamta_sidan`.

    Nätverksfel kastas RÅA härifrån, så att `_hamta_sidan` kan skilja dem från
    en statuskod.

    `HTTPError` är en subklass av `URLError`, och skyddet mot att en statuskod
    försöks om ligger INTE i klausulordning: funktionen har en enda `except`.
    Det ligger i att `HTTPError` KONVERTERAS till `Hamtningsfel` här, alltså
    innan den kan nå `_hamta_sidan`:s omförsök, som bara fångar de råa typerna.
    *Här stod "fångas därför först", som beskriver en ordning mellan klausuler
    som inte finns. Fällt av §7-granskningen av skiva 29, varv 1.*
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
