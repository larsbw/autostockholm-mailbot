"""Generatorn: boten skriver ett SVARSUTKAST på en a-traktorförfrågan.

**UT KOMMER ETT UTKAST, ALDRIG ETT SKICKAT MAIL.** Modulen har ingen sändväg, och
det är prövat och inte antaget: `src/vy.py::krav_pa_sandvagsfrihet` går över
importgrafen och källtexten, och `tests/test_generera.py` kör den mot den här
modulen. Samma spärr som vyn har, samma två lager.

**DET HÄR ÄR SÄNDVÄG enligt CLAUDE.md §7.** Modulen avgör med vilket INNEHÅLL ett
mail lämnar servern den dag fas 7 kopplar in sändningen. En granskningsomgång,
ovillkorligt.

*Här stod "Tre granskningsvarv". CLAUDE.md 1.0.0 ersatte tre varv med en omgång,
och raden pekade alltså ut en styrande regel som inte längre finns. Rättat i
skiva 46.*

SPÄRRARNA PÅ DET GENERERADE, var och en med sin negativkontroll:

  `tomt-svar`                    Ett svar som är tomt efter `.strip()` är inget
                                 utkast. De andra SÖKER EFTER SAKER och släppte
                                 därför igenom det tomma.
  `genererat-tal-har-kalla`      Ett tal i svaret ska komma ur uppslaget eller ur
                                 config. `config/priser.json` är FYLLD sedan
                                 skiva 44, alltså prövas ett pris mot filens
                                 egna tal: en prissats måste bära minst ett tal,
                                 och varje tal i satsen ska komma därifrån.
                                 *Här stod att filen är TOM och att varje svar
                                 som nämner ett pris därför faller. Lars fyllde
                                 den i skiva 44. Rättat i skiva 46.*
  `genererat-fordonsfaktum`      Ett fordonsfaktum kräver ett LYCKAT uppslag.
                                 Kopplar `fordonsfakta-ur-uppslag` uppströms.
  `pastaende-om-franvaro`        Att en uppgift SAKNAS måste vara belagt av ett
                                 avläst värde. *Raden saknades i den här listan
                                 sedan skiva 40 byggde spärren, alltså påstod
                                 uppräkningen en fullständighet den inte hade.
                                 Rättat i skiva 46.*
  `troskeln-som-forfattningstext` Tröskeln 1 000 kg får inte återges som en
                                 sammanfattad föreskrift.
  `barlastflak-galler-fordonet`  Barlastflak får inte nämnas för ett fordon där
                                 §39:s krav bevisligen inte gäller, alltså ett
                                 fyrhjulsdrivet eller ett över 2 000 kg. Skiva
                                 55, LUCKA 69.
  `atagande-om-priset`           Ett påstående om att ett arbete INGÅR, är
                                 KOSTNADSFRITT eller TÄCKS av priset är ett
                                 prisbesked, och kräver samma källa som ett
                                 belopp: `config/priser.json`, ordagrant.

**SPÄRRARNA FÄLLER TILL UTKAST, DE RÄTTAR ALDRIG TEXTEN.** §9.1: en fälld text är
ett stopptecken och inte ett formuleringsproblem. Att skriva om svaret tills
spärren släpper igenom det är uttryckligen förbjudet, och därför finns det ingen
kod här som gör det.

RÖSTEN KOMMER UR `data/par.jsonl`, som få-exempel och inte som mallar att fylla
i. §11. Hur många par som faktiskt går att använda är MÄTT, se
`scripts/par-matning.py` och `docs/beslutslogg.md` #49.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

from src import fordonsuppslag, sokvagar
from src.fordonsuppslag import Uppslag, Utfall

ROT = Path(__file__).resolve().parent.parent

# KORPUSARNA UR `src/sokvagar.py`, skiva 53. Se den modulens huvud.
PAR = sokvagar.DATA / "par.jsonl"
OMETIKETTERADE = sokvagar.DATA / "ometiketterade.jsonl"

# **`config/` FLYTTAR INTE, och det är avsiktligt.** Båda filerna är §10-grindade
# och versionerade: de ska ändras genom en deploy och aldrig genom att någon
# redigerar en fil på en server. Se `src/sokvagar.py`.
PRISER = ROT / "config" / "priser.json"
FAKTA = ROT / "config" / "fakta.json"

MODELL = "claude-sonnet-4-6"
MAX_TOKENS = 1024

# Samma tre etiketter som `src/vy.py::A_TRAKTORETIKETTER`.
A_TRAKTORETIKETTER = (
    "boka a-traktorkonvertering",
    "fråga om a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)

# TAK FÖR ETT FÅ-EXEMPELS SVAR. Samma tal som `scripts/par-matning.py`, och det
# är ett VAL och ingen mätning: ett längre exempel lär modellen att svara långt.
MAX_TECKEN_EXEMPEL = 900

# Hur många få-exempel prompten bär. Fler än så äter kontexten utan att rösten
# blir tydligare, och underlaget är ändå bara 14 dugliga a-traktorpar.
ANTAL_EXEMPEL = 6


class Sparrfalld(Exception):
    """Det genererade svaret får inte gå vidare.

    Bär spärrens NAMN och skälet, så att `logg/beslut.jsonl` kan räkna per spärr
    och per dygn i stället för att bara veta att något föll.
    """

    def __init__(self, sparr: str, skal: str):
        self.sparr = sparr
        self.skal = skal
        super().__init__(f"{sparr}: {skal}")


@dataclass(frozen=True)
class Forfragan:
    """Det generatorn får in. Ett inkommande mail med sin kategori och sitt utfall.

    `uppslag` är None när uppslaget MISSLYCKADES eller när inget gjordes. Det är
    inte samma sak som ett rött utfall: rött betyder att fordonet inte duger,
    None betyder att vi inte vet. Skillnaden avgör vilka fakta som får nämnas.

    **`uppslag_gjordes` SKILJER ETT MISSLYCKAT UPPSLAG FRÅN ETT SOM ALDRIG
    GJORDES, och den skillnaden är fälld fram av kedjan i skiva 34.** Utan den
    fick en REKONDBOKNING svaret *"Vi har inte kunnat slå upp ditt fordon just
    nu"*, eftersom `utfall=None` bara hade en betydelse. Vi hade inte försökt
    slå upp något: kategorin gatas inte av fordonsuppslaget. Kunden bad om en
    tid och fick ett besked om ett uppslag som aldrig gjordes.

    Förvalet är `True`, alltså oförändrat för varje anropare som bara har de två
    lägen som fanns före kedjan.
    """

    text: str
    kategori: str
    utfall: Utfall | None
    uppslag: Uppslag | None = None
    uppslag_gjordes: bool = True

    # OM MAILET ÖVER HUVUD TAGET BAR ETT REGISTRERINGSNUMMER. Skiva 46 DEL B.
    #
    # **`uppslag=None` HADE TVÅ BETYDELSER KVAR, och den ena blev ett falskt
    # besked till kunden.** `uppslag_gjordes` skilde ut kategorin som inte gatas.
    # Kvar i samma `None` låg ändå två helt olika lägen: mailet bar inget nummer
    # att slå upp, och numret fanns men uppslaget föll. Ärende 14 i
    # `data/granskningsfall.jsonl` är det första: kundens mail bär inget
    # registreringsnummer, och svaret inleds *"Vi har inte kunnat slå upp bilen i
    # registret"*. Kunden får veta att något misslyckats utan att förstå varför,
    # och blir aldrig ombedd att skicka numret.
    #
    # **FÖRVALET ÄR `True`, ALLTSÅ OFÖRÄNDRAT BETEENDE FÖR VARJE ANROPARE.**
    # Samma val som `uppslag_gjordes` ovan och av samma skäl. Det motsatta
    # förvalet är INTE det säkra här: en anropare som inte känner fältet hade då
    # fått prompten att be om ett registreringsnummer som redan står i mailet,
    # vilket är precis den form promptens regel 11 finns för att hindra.
    #
    # **VILLKORET SÄTTS UR SAMMA FUNKTION SOM FÄLLER UPPSLAGET.** `src/kedja.py`
    # skickar `fordonsuppslag.normalisera_regnr(arende.regnr)`, alltså exakt det
    # uttryck vars tomhet får `slag_upp` att kasta *"registreringsnummer
    # saknas"*. Två skrivsätt för samma faktum hade kunnat gå isär.
    regnr_i_mailet: bool = True

    # VILKA FRÅNVAROPÅSTÅENDEN SOM ÄR BELAGDA. Skiva 40 DEL B.
    #
    # **TOM MÄNGD ÄR DET SÄKRA FÖRVALET, och det är avsiktligt.** En anropare
    # som inte vet något om registrets luckor ska inte kunna låta boten påstå
    # att en uppgift saknas. Varje namn här är ett faktum boten FÅR säga saknas,
    # därför att sidan bevisligen inte bär det.
    #
    # **BARA `draganordning` KAN HAMNA HÄR.** Mängden sätts på ett enda ställe,
    # `src/kedja.py`, och bara när ett LYCKAT uppslag läst `Draganordning: Nej`.
    # `dragvikt` står i `FRANVAROFAKTA` och kan aldrig bli belagd: en dragvikt
    # går bara att LÄSA, aldrig att belägga genom sin frånvaro.
    #
    # *Kommentaren sade att namnen sätts ur `biluppgifter.falt_med_status` och
    # `biluppgifter.dragviktslage`. Den vägen togs bort av VÄG TRE i skiva 41,
    # och ingendera funktionen rör mängden. Fällt av §7-granskningen av skiva
    # 41, varv 1.*
    franvaro_far_pastas: frozenset[str] = frozenset()


# ------------------------------------------------------------------ DEL C


# TAL SOM ALLTID FÅR STÅ I ETT SVAR, oavsett uppslag.
#
# `1` och `2` slinker igenom som ordningstal och som "en till två veckor", och
# ett årtal är inte ett påstående om pris eller vikt. Listan är en UNDANTAGSLISTA
# och hålls kort med flit: varje tillägg är ett hål i spärren.
ALLTID_TILLATNA_TAL = frozenset({"1", "2", "3"})

# NYCKELN I `config/fakta.json` VARS VÄRDE FÅR STÅ I EN PRISSATS.
#
# Egen konstant därför att `krav_pa_tal_med_kalla` slår upp just den posten, och
# ett nyckelnamn som bara står inuti en spärr är ett obundet led. Lars beslut i
# skiva 44; skälet står i spärrens docstring.
TELEFONNYCKEL = "telefon"

# VARJE SIFFERFÖLJD, med tusengruppering som en del av talet.
#
# **INGA ORDGRÄNSER, och det ledet är fällt fram två gånger.** Första lydelsen
# krävde `\b` efter sista siffran, alltså var `25000kr` och `1000kg` OSYNLIGA för
# spärren: `_tal_i` gav en tom mängd. Det är den vanligaste svenska skrivformen,
# och den gick rakt igenom alla tre spärrarna.
#
# **AVSKILJAREN ÄR BARA BLANKSTEG ELLER PUNKT FÖLJT AV EXAKT TRE SIFFROR.**
# Första lydelsen tog med komma och slog därmed ihop `1400, 1500` till talet
# `14001500`, alltså en FALSK fällning av två avlästa vikter. Det var lucka 22
# och den är nu stängd i stället för registrerad.
#
# Fällt av §7-granskningen av skiva 31, varv 2.
TAL_I_TEXT = re.compile(r"\d+(?:[\s.]\d{3}(?!\d))*")

# TAL SKRIVET HELT I ORD. Det var lucka 24: "tjugofemtusen" har varken siffra
# eller prisord och passerade alla tre spärrarna, mätt i skiva 31 varv 3.
#
# **VAGA MÄNGDORD FÅNGAS INTE, och det är avsiktligt.** §7.2 tillåter dem
# uttryckligen. "tusentals", "hundratals" och "sextiotalet" är inte tal utan
# mängdord, och en spärr som fäller dem fäller vanlig prosa.
#
# Skillnaden är MULTIPLIKATORN, alltså en egenskap och inte en uppräkning av
# priser: ett tal i ord bär ett räkneord FÖRE `tusen` eller `hundra`, ett
# mängdord gör det inte. `femtusen` och `tjugofem tusen` fälls, `tusentals`
# inte. Suffixdelen matchar aldrig över en BOKSTAV, eftersom `\s` inte matchar
# bokstäver, alltså kan räkneordet och multiplikanden inte spänna över ett
# mellanliggande ord.
#
# *Här stod "matchar aldrig över mer än ett blanksteg". Det var falskt:
# `TAL_I_ORD.search("tjugofem   tusen kronor")` träffar, och över radbrytning
# likaså, eftersom `\s*` tar hur många blanktecken som helst. Skälet som angavs
# belade ett annat påstående än det som skrevs. Fällt av §7-granskningen av
# skiva 32, varv 2.*
#
# **FÖRSIKTIG ÅT FÄLLNINGSHÅLLET.** "fjortonhundra kilo" fälls även om 1400 står
# i uppslaget, eftersom talord inte slås upp mot källan. Utfallet blir `utkast`,
# alltså det säkra hållet, och formen är sällsynt i utkorgen.
RAKNEORD = (
    r"en|ett|två|tva|tre|fyra|fem|sex|sju|åtta|atta|nio|tio|elva|tolv|"
    r"tretton|fjorton|femton|sexton|sjutton|arton|nitton|tjugo|trettio|"
    r"fyrtio|femtio|sextio|sjuttio|åttio|attio|nittio"
)
TAL_I_ORD = re.compile(
    rf"\b(?:ettusen|(?:{RAKNEORD})[\wåäö]*\s*(?:tusen|hundra))\b",
    flags=re.IGNORECASE,
)

# ORD SOM GÖR ETT SVAR TILL ETT PRISBESKED. Priser finns inte i config än,
# alltså faller ett svar som nämner ett pris i någon av formerna nedan. Ordet
# VARJE står inte här: uppräkningen är inte uttömmande, se lucka 20.
#
# **`totalt` OCH `summa` ÄR BORTTAGNA.** De är vanlig prosa: "vi tittar totalt
# igenom bilen" fälldes som pris. En spärr som fäller på vanliga ord blir
# avstängd, vilket §7.1 varnar för.
#
# **TILLAGT: `spänn`, `peng` och `tkr`.** De fångar "femton hundra spänn" och
# "en billig peng".
#
# **ETT PRIS SKRIVET HELT I ORD FÅNGAS INTE HÄR, men det fälls av `TAL_I_ORD`.**
# "tjugofemtusen" har varken siffra eller prisord och passerade tidigare alla
# tre spärrarna. Lucka 24 är DELVIS stängd i skiva 32: kvar är ett räkneord utan
# multiplikand, som "fjorton dagar".
#
# *Här stod i presens att formen "passerar alla tre spärrarna, mätt". Det blev
# falskt av `TAL_I_ORD`, som infördes 26 rader ovanför i SAMMA commit. Fällt av
# §7-granskningen av skiva 32, varv 2. Och dessförinnan stod här att formen är
# tillagd i `PRISORD`; det var den inte. Fällt av granskningen av skiva 31,
# varv 3.*
#
# Uppräkningen är INTE uttömmande. Systemprompten är det som bär i det fallet,
# och HELA prompten är sedan skiva 32 bunden ordagrant av
# `test_HELA_systemprompten_ar_bunden` i `tests/test_generera.py`.
#
# *Här stod först att prompten är "själv obunden av test, se lucka 25". Sedan
# stod att den är bunden av `REGLER_I_PROMPTEN`, vilket band de sju numrerade
# raderna men inte ramen omkring dem: raden "REGLER SOM ALDRIG BRYTS:" gick att
# invertera med grön svit. Fällt av §7-granskningen av skiva 32, varv 1 och
# varv 2.*
#
# **EN TERM PER RAD, UTAN INTERN ALTERNATION.** Se `FORFATTNINGSTERMER` för
# skälet: en gren inuti en term är ett lager som isoleringsvakten inte når.
PRISTERMER = (
    r"\bkr\b",
    r"\bkronor\b",
    r"\bsek\b",
    r"\bkostar\b",
    r"\bkostnad\b",
    r"\bkostnaden\b",
    r"\bpris\b",
    r"\bpriset\b",
    r"\bpriser\b",
    r"\boffert\b",
    r"\bavgift\b",
    r"\bspänn\b",
    r"\bspann\b",
    r"\bpeng\b",
    r"\bpengar\b",
    r"\binkl\.?\s*moms\b",
    r"\bexkl\.?\s*moms\b",
    r"\btkr\b",
    r"\d\s*tkr",
)

PRISORD = re.compile("|".join(PRISTERMER), flags=re.IGNORECASE)

# **`prisuppgift` STÅR MED FLIT INTE I LISTAN.** "En kollega återkommer med
# prisuppgift" är precis det svar spärren finns för att framtvinga, och en
# lydelse som tog ordet `pris` som stam fällde varje bra svar. Ordgränsen efter
# `pris` är därför lastbärande och inte kosmetik.

# FORDONSFAKTA. Orden som bara får stå när ett LYCKAT uppslag finns.
#
# **UPPRÄKNINGEN ÄR INTE UTTÖMMANDE, och det är en REGISTRERAD LUCKA.** Se
# `docs/sparrar.md` `genererat-fordonsfaktum`. Första lydelsen tog fem termer
# och missade varje omskrivning: "bilen väger tillräckligt", "din bil klarar
# släp", "det finns krok". Stammarna nedan täcker de formerna, men en modell kan
# alltid formulera ett faktum utan något av orden, och den vägen stängs inte av
# en ordlista.
#
# Det som bär i det fallet är SYSTEMPROMPTEN, som säger att modellen inte vet
# något om bilen när uppslaget saknas. Spärren är nätet under, inte det enda
# skyddet.
FORDONSTERMER = (
    r"tjänstevikt",
    r"tjanstevikt",
    r"släpvagnsvikt",
    r"slapvagnsvikt",
    r"draganordning",
    r"dragkrok",
    r"totalvikt",
    r"\bväger\b",
    r"\bvager\b",
    r"\bvikten\b",
    r"\bkrok\b",
    r"\bsläp\b",
    r"\bslap\b",
    r"\bsläpet\b",
    r"\btung\b",
    r"\btyngd\b",
)

FORDONSORD = re.compile("|".join(FORDONSTERMER), flags=re.IGNORECASE)

# VILKET FÄLT VARJE FORDONSTERM PÅSTÅR NÅGOT OM. Skiva 55 DEL A.
#
# **UPPDELNINGEN BEHÖVDES FÖRST NÄR ETT UPPSLAG KUNDE BLI DELVIS.** Före skiva 55
# var `uppslag is not None` liktydigt med att alla tre gatande fälten var avlästa,
# alltså räckte ett enda villkor. Nu kan uppslaget LYCKAS med `slapvagnsvikt_kg`
# tom, och då är *"släpvagnsvikten räcker"* ett påstående om en uppgift registret
# aldrig lämnat, medan *"bilen saknar registrerad draganordning"* är sant i samma
# svar. Ett villkor som prövar uppslaget som helhet kan inte skilja dem åt.
#
# **TERMERNA ÄR INTE OMSKRIVNA, BARA GRUPPERADE.** Varje sträng nedan står
# ordagrant i `FORDONSTERMER` ovan, och `test_varje_FORDONSTERM_har_ett_falt`
# kräver att unionen är EXAKT lika med den tupeln. Det är det som gör att
# `test_varje_term_ar_ISOLERAD` och `test_ingen_term_gommer_en_alternation`
# fortsätter vakta samma mängd: en term som läggs till i den ena och glöms i den
# andra blir röd.
#
# **`nagon_vikt` ÄR DE OSPECIFIKA ORDEN.** *"bilen väger tillräckligt"* namnger
# ingen storhet, och att kräva just tjänstevikten hade fällt ett sant svar om
# totalvikten. Vilken som helst av de tre avlästa vikterna belägger dem.
FORDONSFAKTUM_FALT = {
    "tjanstevikt_kg": (r"tjänstevikt", r"tjanstevikt"),
    "slapvagnsvikt_kg": (r"släpvagnsvikt", r"slapvagnsvikt",
                         r"\bsläp\b", r"\bslap\b", r"\bsläpet\b"),
    "draganordning": (r"draganordning", r"dragkrok", r"\bkrok\b"),
    "totalvikt_kg": (r"totalvikt",),
    "nagon_vikt": (r"\bväger\b", r"\bvager\b", r"\bvikten\b",
                   r"\btung\b", r"\btyngd\b"),
}

# VIKTFÄLTEN SOM BELÄGGER ETT OSPECIFIKT VIKTORD.
VIKTFALT_I_UPPSLAGET = ("tjanstevikt_kg", "slapvagnsvikt_kg", "totalvikt_kg")

FORDONSFAKTUM_MONSTER = {
    falt: re.compile("|".join(termer), flags=re.IGNORECASE)
    for falt, termer in FORDONSFAKTUM_FALT.items()
}

# TRÖSKELN SOM FÖRFATTNINGSTEXT. Talet 1000 i sällskap med ett ord som gör det
# till en återgiven föreskrift.
# TRÖSKELN, i siffror och i ord, med och utan mellanrum före enheten.
#
# Varv 1 stängde `1 000 kg` och lämnade `1000kg`, `ettusen kilo`, `tusen kg` och
# `minst 1 ton` öppna. Två av dem gällde GRÄNSBILEN, där uppslaget ger talet en
# källa så att talspärren inte fäller först. Fällt av §7-granskningen, varv 2.
# **ENHETEN ÄR EN MASSENHET, inte varje ord som börjar på `kilo`.** Första
# lydelsen tog `kilo\w*` och fällde därmed *"bilen har gått tusentals
# kilometer"*, alltså ett önskat svar om körsträcka. Massenhetens böjningar är
# `kilo`, `kilogram` och `kilon`; `kilometer` är en LÄNGDenhet och hör inte hit.
# Fällt av §7-granskningen av skiva 32, varv 2.
#
# **ENHETENS BÖJNINGAR STÅR SOM EGNA TERMER, inte som en gren i en grupp.**
# Lydelsen `(kilo(?:gram|n)?|kg)` gjorde `gram`- och `n`-grenarna osynliga för
# isoleringsvakten, alltså gick de att ta bort med grön svit. Det var lucka 34.
# **LUCKA 33 ÄR STÄNGD I SKIVA 34, och den stängdes genom UPPRÄKNING.** Fem
# böjningar som `kilo\w*` fångade tappades när enheten snävades för att inte
# fälla `kilometer`: `kilos`, `kilot`, `kilona`, `kilogrammen`, `kilogrammet`.
#
# **VARFÖR EN UPPRÄKNING ÄR RÄTT SVAR HÄR, undantagsvis.** Egenskapen som
# skiljer massenheten från längdenheten är att `kilometer` finns och ska undantas,
# och det uttrycks naturligt som `kilo(?!meter)\w*`. Den formen är FÖRBJUDEN av
# `test_ingen_term_gommer_en_alternation`, eftersom en lookahead bär `(`.
#
# Förbudet är inte i vägen av misstag: det finns för att en gren inuti en term
# är ett lager isoleringsvakten inte når, vilket var lucka 34. En sluten mängd
# böjningar är däremot något man KAN räkna upp, och varje böjning blir då en
# egen term med en egen isolerande rad. Uppräkningen är alltså inte ett avsteg
# från egenskapstänket utan dess pris i det här fallet.
TROSKELTERMER = (
    r"1[\s.]?000",
    r"\bettusen\b",
    r"\btusen\w*\s*kilo\b",
    r"\btusen\w*\s*kilos\b",
    r"\btusen\w*\s*kilot\b",
    r"\btusen\w*\s*kilon\b",
    r"\btusen\w*\s*kilona\b",
    r"\btusen\w*\s*kilogram\b",
    r"\btusen\w*\s*kilogrammen\b",
    r"\btusen\w*\s*kilogrammet\b",
    r"\btusen\w*\s*kg\b",
    r"\b1\s*ton\b",
    r"\bett\s+ton\b",
)

TROSKELTAL = re.compile("|".join(TROSKELTERMER), flags=re.IGNORECASE)

# FÖRFATTNINGSORDEN, EN TERM PER RAD.
#
# **UPPDELNINGEN I EN TUPEL ÄR INTE KOSMETIK.** Mönstret har rättats i fyra
# granskningsvarv, och VARJE gång har rättelsen tappat eller fällt något den
# inte skulle. Senast försvann `kräv` och `regeln` när hela regexen skrevs om i
# ett svep, och regressionstabellen fångade det inte: varje rad som bar
# "kräver" bar också "Lagen", som fälldes av ett annat led.
#
# Termerna står därför var för sig, och `test_varje_term_ar_ISOLERAD`
# kräver en rad i regressionstabellen där VARJE term är den enda som matchar.
# En term som tappas gör den raden röd, och en term som SNÄVAS likaså.
#
# **VAKTEN GÄLLER TERMNIVÅN OCH INTE ALTERNATIV INUTI EN TERM.** En gren i
# `regler(?:na|ing\w*|s)?\b` går att ta bort med hela sviten grön, mätt. Det är
# lucka 34. *Här stod att vakten "gör klassen av fel omöjlig", vilket är sant på
# termnivå och falskt en nivå längre in. Fällt av §7-granskningen av skiva 32,
# varv 3.*
#
# Fällt av §7-granskningen av skiva 32, varv 2.
#
# **VÄNSTERORDGRÄNSEN FALLER FÖR DE ENTYDIGA STAMMARNA**, eftersom ordet kan vara
# ANDRA ledet i en sammansättning: `myndighetskrav`, `Trafikföreskriften`,
# `Lagparagrafen`, `Vägtrafiklagstiftningen`.
#
# **`enligt` STÅR INTE MED.** Ordet är för svagt: "enligt uppslaget" refererar
# VÅR källa, inte en föreskrift. "Enligt lagen" fälls ändå, på `lagen`.
FORFATTNINGSTERMER = (
    r"krav\w*",
    # **`\w+` DÄR DEN NAKNA STAMMEN INTE ÄR ETT ORD.** `bestämmels` och
    # `reglement` förekommer aldrig ensamma på svenska, alltså är den tomma
    # böjningen en gren som ingen rad kan pröva. Ett `\w*` som bara kan matcha
    # icke-ord är ett otestbart lager, och `test_en_SNAVAD_term_tappar_en_rad`
    # fäller det. Där stammen ÄR ett ord står `\w*` kvar och prövas av en rad.
    # Fällt av §7-granskningen av skiva 33, varv 2.
    #
    # *`kräv` stod här som `\w+` med motiveringen att stammen inte är ett ord.
    # Det var FALSKT: `kräv` är imperativ av `kräva`, och skärpningen tappade
    # formen "Kräv 1 000 kg". Fällt av §7-granskningen av skiva 33, varv 3.*
    #
    # **VÄNSTERGRÄNSEN FALLER I SKIVA 34**, så att `påkrävt` fångas. `kräv` är
    # lika entydigt som `krav` på raden ovanför, och de behandlades olika bara
    # för att stavningen skiljer dem åt. Det var lucka 32.
    r"kräv\w*",
    r"föreskrift\w*",
    r"foreskrift\w*",
    r"bestämmels\w+",
    r"bestammels\w+",
    r"paragraf\w*",
    # `lagstift\w*` OCH INTE `lagstiftning\w*`: varv 2 mätte upp att
    # `Lagstiftaren` läckte, alltså saknades agentformen. Den kortare stammen
    # bär båda, och den längre är då en DÖD term som vakterna larmar på.
    # `\w+`: den nakna stammen `lagstift` är ingen svensk ordform, alltså vore
    # nollängdsalternativet ett lager som ingen rad kan pröva.
    r"lagstift\w+",
    r"reglement\w+",
    # `regler` MED SINA EGNA BÖJNINGAR OCH INGA ANDRA. Substantivet `regler`
    # delar sträng både med verbet `reglera` och med sammansättningar där
    # `regler` är FÖRSTA ledet: termostaten REGLERAR, tomgången REGLERAS,
    # dragkroken är REGLERBAR, och REGLERVENTILEN sitter på motorn. Alla fyra
    # är verkstadsord. Substantivets egna former är `regler`, `reglerna`,
    # `reglering(en)` och `reglers`, alltså räcker det att kräva att ordet SLUTAR
    # där böjningen slutar.
    #
    # **BÖJNINGARNA STÅR SOM FYRA TERMER och inte som en grupp.** Lydelsen
    # `regler(?:na|ing\w*|s)?\b` gick att förkorta till `regler(?:na|ing\w*)?\b`
    # med hela sviten grön: `|s`-grenen var ett lager som ingen rad prövade. Det
    # var lucka 34, och den är stängd av att grenar inte längre får gömma sig
    # inuti en term.
    r"regler\b",
    r"reglerna\b",
    r"reglernas\b",
    r"reglering\w*",
    r"reglers\b",
    # `regel` behåller sin HÖGERgräns, som `regelbundet` gjorde lastbärande.
    # **GENITIVFORMEN ÄR EN EGEN TERM för varje bestämd form.** `\blagens\b` och
    # `reglernas\b` lades till i skiva 34, men `regelns` och `lagarnas` glömdes,
    # alltså tillämpades egenskapen bara på de instanser fyndet räknade upp.
    # Båda läckte hela vägen. Fällt av §7-granskningen av skiva 34, varv 1.
    r"regel\b",
    r"regeln\b",
    r"regelns\b",
    # `lag` ÄR GENUINT TVETYDIGT och behåller därför båda gränserna. `lager`,
    # `underlag`, `uppslaget` och `lagt` fälldes av en gränslös lydelse. Värst av
    # alla är `lagar`: en verkstad LAGAR bilar. Bara den bestämda pluralformen
    # är säker.
    r"\blag\b",
    r"\blagen\b",
    r"\blagens\b",
    r"\blagarna\b",
    r"\blagarnas\b",
    r"\blagtext\w*",
    # Fyra stammar som varv 2 mätte upp. **TRE AV DEM BEHÅLLER SIN
    # VÄNSTERGRÄNS**, eftersom de uppmätta formerna står vid ordets början och
    # ingen mätt form kräver att gränsen faller. Att släppa en gräns utan en rad
    # som isolerar den är att bygga ett lager `test_en_SNAVAD_term_tappar_en_rad`
    # inte kan se, alltså precis den otestbarhet vakterna finns för.
    #
    # `lagrum` är dessutom det enda av de fyra där en gränslös lydelse mäts fälla
    # ett annat ord: `slagrum`. Mätt med `scripts/stamprov.py`.
    r"\blagenlig\w*",
    r"\blagändring\w*",
    r"\blagrum\w*",
    # **LUCKA 32 ÄR INTE STÄNGD, OCH DET ÄR MÄTT.** Nio former som repots första
    # lydelse fångade föll bort när vänstergränsen rättades. De nio är åtgärdade
    # här, liksom varv 1:s fyra och varv 2:s fyra av sex. Men EN ÖPPEN MÄNGD
    # ÅTERSTÅR, och den går inte att uttrycka som en term.
    #
    # **`lag` ÄR GENUINT TVETYDIGT I BÅDA RIKTNINGARNA, och det är hela skälet.**
    # `lagen\b` utan vänstergräns fäller `uppslagen`, `förslagen`, `avslagen`,
    # `beslagen` och `utslagen`, och `uppslagen` är vad kedjan GÖR. `\blag\w*`
    # utan högergräns fäller `lagar`, `lager`, `lagt` och `lagning`, alltså en
    # verkstads vanligaste verb. Mätt med `scripts/stamprov.py`.
    #
    # Mängden bär `lag` i ANDRA ledet (`Vägtrafiklagen`, `Fordonslagen`), i
    # FÖRSTA ledet (`Lagboken`, `Lagrådet`) och böjningar utanför de vitlistade
    # (`reglerat`, `måsten`). Den står som LUCKA 39 i `docs/sparrar.md` med de
    # mätta formerna uppräknade, och uppräkningen är aldrig gränsen.
    #
    # Enligt skiva 34:s DEL A: går formen inte att uttrycka som en term lämnas
    # den öppen och mätt, och inget särfall byggs.
    #
    # `lagens` och `reglernas` står som EGNA termer och inte som `\blagen\w*`,
    # eftersom `lagen` följt av vad som helst öppnar för `lagenlig` och liknande.
    # Genitivformen är sluten och entydig.
    #
    # `laglig` och `lagstadga` är egna stammar, inte böjningar av `lag`, och är
    # entydiga: inget verkstadsord bär dem.
    # **VÄNSTERGRÄNSEN FALLER ÄVEN HÄR, och det ledet var inkonsekvent.**
    # Kommentaren ovan säger att gränsen faller för de entydiga stammarna, och
    # `laglig` och `lagstadga` beskrevs i samma andetag som entydiga. Ändå
    # skrevs de med `\b`, alltså läckte `olagligt` och `olagliga` hela vägen
    # genom `krav_pa_svaret`. Fällt av §7-granskningen av skiva 34, varv 1.
    r"laglig\w*",
    # `\w+`: den nakna stammen `lagstadga` är en infinitiv som inte förekommer
    # i ett verkstadssvar, alltså vore den tomma böjningen ett otestbart lager.
    # `laglig` och `regelverk` är däremot ord på egen hand och behåller `\w*`.
    r"lagstadga\w+",
    r"regelverk\w*",
    r"\bvvfs\w*",
    r"§",
    r"\bmåste\b",
    r"\bmaste\b",
    r"\btrafikverket\w*",
    r"\btransportstyrelsen\w*",
)

FORFATTNINGSORD = re.compile("|".join(FORFATTNINGSTERMER), flags=re.IGNORECASE)

# ORD SOM GÖR ETT SVAR TILL ETT ÅTAGANDE OM VAD PRISET TÄCKER. LUCKA 59.
#
# **ETT ÅTAGANDE OM VAD SOM INGÅR ÄR SAMMA KLASS SOM ETT PÅHITTAT PRIS, och det
# är Lars besked.** Ärende 19 i `data/granskningsfall.jsonl` skrev *"dragkrok
# ingår i bygget"*. Prisfilens post säger att priset gäller arbetet och de delar
# som ingår i GRUNDPAKETET, och boten vet inte vad grundpaketet innehåller.
# Alltså lovade den bort ett arbete gratis. Ingen befintlig spärr rörde den
# meningen: den bär inget tal och inget prisord, alltså är den varken en prissats
# för `krav_pa_tal_med_kalla` eller ett fordonsfaktum.
#
# **SKILLNADEN MOT ETT ERBJUDANDE ÄR HELA REGELN, och den är Lars.** Ett svar FÅR
# säga att vi KAN UTFÖRA ett arbete: *"Extraljusen kopplar vi in"* och *"vi kan
# montera en dragkrok"* är inga prisåtaganden och står orörda här. Det som fälls
# är påståendet att arbetet inte kostar något extra.
#
# TERMERNA ÄR MÄTTA, inte uppfunna. `data/par.jsonl` är Mattes egna skickade svar
# och bär `ingår`, `inkluderar`, `omfattar`, `bjuder ... på` och `på köpet` i just
# den betydelsen, och `data/granskningsfall.jsonl` bär botens `ingår`.
# `kostnadsfri\w*`, `gratis` och `täcker`/`täcks` står för de två klasser Lars
# namnger utöver INGÅR, alltså KOSTNADSFRITT och TÄCKS av priset, och de är inte
# uppmätta i korpusen. Det redovisas som ett val.
#
# **FORMER SOM REDAN FÄLLS AV `PRISORD` STÅR MED FLIT INTE HÄR.** *"utan
# kostnad"*, *"utan extra kostnad"* och *"kostar inget"* bär alla en PRISTERM,
# alltså blir meningen en prissats utan tal och faller redan på
# `krav_pa_tal_med_kalla`. Ett andra lager på samma form hade gjort båda
# oprövbara var för sig, vilket §7.1 varnar för.
#
# **INGA ASCII-VARIANTER, och det är ett mätt beslut och ingen glömska.**
# `PRISTERMER` bär `\bspann\b` bredvid `\bspänn\b`, men den vägen är stängd för
# den här mängden. ASCII-formen av `ingår` är `ingar`, av `på köpet` är `pa
# kopet`, och av `täcks` är `tacks`, som ligger en bokstav från `tack`: ordet
# står 37 gånger i `data/par.jsonl`:s utgående svar. En mängd som får
# ASCII-varianter för somliga termer och inte för andra är just den
# inkonsekvens `laglig\w*` och `lagstadga\w+` fälldes för i skiva 34, alltså
# faller de för alla. Formen står som LUCKA 60 i `docs/sparrar.md`.
#
# *Här stod att `tack` är "verkstadssvarets vanligaste ord". Räknat över
# `utgaende_text` i `data/par.jsonl` står `att` 372 gånger och `vi` 323, alltså
# är det inte ens i närheten. Talet 37 stämde, superlativen inte. Fällt av
# §7-granskningen av skiva 46.*
#
# **EN TERM PER RAD, UTAN INTERN ALTERNATION.** Samma krav som de tre mängderna
# ovan, bundet av `test_ingen_term_gommer_en_alternation`.
ATAGANDETERMER = (
    r"\bingår\b",
    # `\w+` DÄR DEN NAKNA STAMMEN INTE ÄR ETT ORD. `inkluder` förekommer aldrig
    # ensamt på svenska, alltså vore den tomma böjningen en gren ingen rad kan
    # pröva. Samma skäl som `bestämmels\w+`. `kostnadsfri` ÄR ett ord och
    # behåller därför `\w*`, med en isolerande rad i naken form.
    r"\binkluder\w+",
    # `omfattar` OCH INTE `omfatt\w*`. Stammen delar sträng med `omfattning`,
    # som är ett MÄNGDORD och inget åtagande: *"från 2 500 kr beroende på
    # omfattning"* står i `data/par.jsonl` och är ett prisförbehåll, alltså
    # motsatsen till det som fälls här.
    r"\bomfattar\b",
    r"\bkostnadsfri\w*",
    r"\bgratis\b",
    r"\bpå köpet\b",
    # **`täcker` OCH `täcks` STÅR INTE HÄR, och det är ett fynd och ingen
    # glömska.** Lars klass är att ett arbete TÄCKS AV PRISET, och en naken
    # täck-term är inte ankrad till priset: den fäller varje mening om vad en
    # FÖRSÄKRING eller en GARANTI täcker. Två inkommande mail i `data/par.jsonl`
    # nämner en försäkring, och noll utgående svar bär `täcker` eller `täcks` i
    # någon betydelse. En fällning rapporterad som `atagande-om-priset` på ett
    # försäkringsbesked är dessutom ett STOPPTECKEN enligt §9.1, alltså inget
    # utkast alls.
    #
    # **DEN PRISANKRADE FORMEN FÄLLS REDAN.** *"Priset täcker monteringen"* och
    # *"det täcks av priset"* bär båda `\bpriset\b`, som är en PRISTERM, alltså
    # blir meningen en prissats utan tal och faller på `krav_pa_tal_med_kalla`.
    # En term här hade varit ett andra lager på samma form, vilket §7.1 varnar
    # för. Den oankrade formen *"det täcker vi"* står kvar som en del av
    # LUCKA 61. Fällt av §7-granskningen av skiva 46.
    # BÅDA ORDFÖLJDERNA, som var sin term. `bjuder` ensamt är för svagt: *"vi
    # bjuder in dig"* är ingen utfästelse om priset. Båda formerna står i
    # `data/par.jsonl`: *"Vi bjuder på en Guldtvätt"* och *"Denna bjuder vi på"*.
    r"\bbjuder på\b",
    r"\bbjuder vi på\b",
)

ATAGANDEORD = re.compile("|".join(ATAGANDETERMER), flags=re.IGNORECASE)


# ETT NEKANDE DIREKT EFTER ETT ÅTAGANDEORD VÄNDER SATSEN, alltså räknas dess
# svans INTE som en uppräkning av vad priset täcker. `Dragkrok ingår inte och
# offereras separat` stod i prisposten en stund, och utan det här ledet hade
# `dragkrok` blivit en BELAGD del och friat precis det åtagande spärren finns
# för att fälla.
_NEKAT_EFTER_ATAGANDE = re.compile(r"^\W*(?:inte|ej|aldrig)\b", re.IGNORECASE)

# KORTASTE DEL SOM RÄKNAS. Ett kort ord är oftast ett funktionsord, och ett
# funktionsord som del hade friat varje sats som råkar bära det. Filen bär i dag
# sju delar, de kortaste `belysning` och `lgf-skylt` på nio tecken, alltså
# ligger tröskeln med god marginal under det som faktiskt står där.
#
# **TRÖSKELN RÄDDAR INTE FRÅN VARJE KORT DEL.** `moms` är fyra tecken och
# passerar den, och ordet står i praktiskt taget varje prismening. Ett
# prisvärde som skrev `priset inkluderar moms` hade alltså gjort `moms` till en
# belagd del. Formen står som en del av LUCKA 66 och är ingen egenskap hos
# dagens fil. Fällt av §7-granskningen av skiva 47.
MINSTA_DEL = 4


def _uppraknade_delar(kategori: str) -> frozenset[str]:
    """Delarna ärendets EGNA prispost räknar upp som INGÅENDE i ett pris.

    **KATEGORIN VÄLJER POSTEN, skiva 52.** Funktionen läste tidigare hela
    `config/priser.json`, alltså kunde en post för en annan tjänst belägga ett
    åtagande. A-traktorpostens `grundombyggnaden omfattar ...` bidrar med sju
    delar, och de friade ett `ingår` i ett svar om service eller rekond lika
    gärna som i ett a-traktorsvar. Se `priser_for`.

    **BARA EN SVANS SOM STYRS AV ETT ÅTAGANDEORD RÄKNAS, och det ledet är
    lastbärande.** Posten `rekond` räknar upp `Guldtvätt 1 500 kr` och
    `glasförsegling 1 000 kr`, alltså tjänster med EGNA priser. Bleve de delar
    hade *"Guldtvätt ingår"* passerat i ett a-traktorsvar, vilket är ett
    påhittat prisbesked av precis den klass §0:s ramverksregel 3 förbjuder.
    `rekond` bär inget åtagandeord och bidrar därför med noll delar.

    **ETT NEKANDE VÄNDER SVANSEN**, se `_NEKAT_EFTER_ATAGANDE`.

    **SVANSEN SLUTAR VID MENINGSSLUT.** Ett värde med två meningar ska inte
    låta den förstas åtagandeord svälja den andras innehåll.

    Delarna jämförs sedan som DELSTRÄNGAR och inte ordgränsat, så att en böjd
    form träffar: källan säger `besiktning`, svaret skriver `besiktningen`.
    """
    delar: set[str] = set()

    for varde in priser_for(kategori).values():
        for traff in ATAGANDEORD.finditer(varde):
            svans = varde[traff.end():]
            if _NEKAT_EFTER_ATAGANDE.match(svans):
                continue

            svans = re.split(r"[.!?]", svans)[0]
            for bit in re.split(r",|\boch\b", svans):
                bit = bit.strip().lower()

                # DE TVÅ FILTREN STÅR SOM EGNA RADER, så att vart och ett går
                # att fälla för sig. §7.1: fälls de tillsammans vet man bara
                # att minst ett av dem bär.
                if len(bit) < MINSTA_DEL:
                    continue
                if any(t.isdigit() for t in bit):
                    continue

                delar.add(bit)

    return frozenset(delar)


def _UTAN_PRISVARDE(varde: str) -> re.Pattern:
    """Mönstret som stryker ETT prisvärde ur ett svar. Se `krav_pa_atagande_med_kalla`.

    Varje tecken i värdet citeras med `re.escape`, alltså kan ingen prisrad
    tolkas som ett reguljärt uttryck. Blankteckensrun blir `\\s+`, så att en
    radbrytning i svaret matchar ett mellanslag i filen. Skiftläget är fritt, så
    att en prisrad först i en mening matchar.

    **`\\s+` OCH INTE `\\s*`.** Ett blanktecken i värdet ska motsvaras av minst
    ett i svaret: `20 000` och `20000` är inte samma skrivform, och `_tal_i`
    normaliserar dem bara för talspärren.
    """
    delar = [re.escape(bit) for bit in varde.split()]
    if not delar:
        # ETT TOMT VÄRDE SKULLE GE ETT TOMT MÖNSTER, som matchar mellan varje
        # tecken och därmed stryker HELA svaret. Spärren hade då tystnat utan
        # att något blev rött. `las_konfigvarden` utelämnar tomma värden, men
        # den invarianten bor i en annan funktion, och en sändvägsspärr ska
        # inte kunna tystna av att en granne ändras.
        return re.compile(r"(?!)")
    return re.compile(r"\s+".join(delar), flags=re.IGNORECASE)


# EN BILMODELL LÄSES SOM ETT TAL, och det är lucka 30. Utan den
#
# **`V50` OCH `ABC156` ÄR NAMN PÅ SAKER, inte kvantiteter.** Utan den här
# skillnaden fälls `A5`, `V50` och registreringsnummer som påhittade tal: fem av
# elva fällningar i skiva 32:s mätning över 100 svar var falska positiva av den
# formen. Det är lucka 30, och den är fortfarande ÖPPEN.
#
# **SKIVA 33 FÖRSÖKTE STÄNGA DEN I TRE LYDELSER OCH ÅTERSTÄLLDE ALLA TRE.**
# Var och en öppnade ett hål mot §0:s ramverksregel 3, som är obrytbar:
#
#   varv 1  varje tal ur kundens text blev tillåtet, alltså kunde boten skriva
#           ett PRIS och en LEDTID som våra egna
#   varv 2  bokstäver FÖRE siffran gjorde en kvantitet till en beteckning:
#           kunden skrev `ca25000`, och då fick boten skriva `25000` fritt
#   varv 3  en beteckning maskerades bort ur svaret innan talen lästes, och då
#           blev `ca10 dagar`, `ca800` och `ca950 kg` osynliga för spärren
#
# **DE TVÅ FÖRSTA behandlade kundens text som en källa.** Det är den inte: §7.2
# säger att priser läses ur `config/priser.json` och ledtider ur
# `config/fakta.json`.
#
# **DEN TREDJE gjorde spärren SÄMRE ÄN FÖRE SKIVAN**, alltså en regression, och
# den upptäcktes först i sista granskningsvarvet.
#
# Gemensamt för alla tre: varje regel som gör en siffra intill bokstäver
# ofarlig gör också en KVANTITET intill bokstäver ofarlig. Se
# `docs/beslutslogg.md` #56.
def _tal_i(text: str) -> set[str]:
    """Talen i en text, normaliserade utan blanksteg och avskiljare."""
    rena = set()
    for traff in TAL_I_TEXT.findall(text):
        rent = re.sub(r"[\s.,]", "", traff)
        if rent:
            rena.add(rent)
    return rena


def _tillatna_tal(forfragan: Forfragan) -> set[str]:
    """Talen ett svar får nämna: uppslagets egna plus config plus undantagen.

    **PRISFILEN FINNS OCH ÄR TOM.** `config/priser.json` upprättades i skiva 41
    på Lars §10-beslut, med varje värde tomt. Den bidrar alltså med noll tal, och
    det är avsiktligt: ett svar som nämner ett pris faller tills Lars fyllt en
    post. *Här stod att filen inte existerar, vilket blev falskt av den skiva som
    skapade den. Fällt av §7-granskningen av skiva 41, varv 1.*

    **KUNDENS TEXT ÄR INGEN KÄLLA, och det ledet är fällt fram i två varv.**
    Skiva 33 lade två gånger `forfragan.text` här, för att lösa lucka 30, och
    båda lydelserna öppnade ett hål i sändvägen. Feltanken var densamma: att
    kunden nämnt ett tal gör inte talet till en källa. §7.2 säger var priser och
    ledtider läses, och det är i `config/`.

    **LUCKA 30 ÄR ÖPPEN**, se noten vid `_tal_i` ovan för alla tre försöken.
    """
    tillatna = set(ALLTID_TILLATNA_TAL)

    if forfragan.uppslag is not None:
        tillatna.add(str(forfragan.uppslag.tjanstevikt_kg))
        tillatna.add(str(forfragan.uppslag.slapvagnsvikt_kg))

    # **BARA VÄRDENA, ALDRIG KOMMENTARERNA.** Raden läste tidigare hela filen
    # och plockade tal ur `json.dumps(data)`. Skiva 36 gav `config/fakta.json`
    # två kommentarnycklar som nämner `§7.2` och `§10`, och därmed blev 7 och 10
    # TILLÅTNA TAL i ett utgående mail: "vi hör av oss inom 10 dagar" passerade
    # spärren, uppmätt. Det bryter §0:s ramverksregel 3, som är obrytbar.
    #
    # En kommentar i en konfigurationsfil får aldrig kunna vidga en sändvägsspärr.
    #
    # **FÖRSTA RÄTTELSEN STÄNGDE BARA TOPPNIVÅN, och det räckte inte.** Den
    # filtrerade `_`-nycklar och dumpade sedan hela dicten, alltså gick både
    # NYCKELNAMN och NÄSTLADE kommentarer vidare: `{"ledtid_14_dagar": ...}` gav
    # 14, och `{"a": {"_om": "se §7.2"}}` gav 7. Fällt av §7-granskningen av
    # skiva 36, varv 2.
    #
    # `_varden_ur` plockar VÄRDEN och aldrig nycklar, hela vägen ned.
    for varde in _varden_ur(las_konfig(FAKTA)):
        tillatna.update(_tal_i(varde))

    # **PRISFILEN GÅR EN ANNAN VÄG SEDAN SKIVA 52, och det är hela skivan.**
    # Raden ovanför läste tidigare `PRISER` på samma sätt, alltså blev VARJE
    # prispostal ett tillåtet tal oavsett kategori. Se `priser_for`.
    #
    # **`priser_for` ÄR SNÄVARE ÄN `_varden_ur` OCKSÅ PÅ EN ANDRA PUNKT, och
    # riktningen är den säkra.** `_varden_ur` går NED genom en nästlad struktur
    # och tar dess värden; `priser_for` går via `las_konfigvarden`, som utelämnar
    # ett nästlat värde helt. Ett nästlat pris kan därmed inte längre bidra med
    # tal. Filen ska vara platt (lucka 53), alltså är skillnaden noll för dagens
    # fil, men en spärr ska inte vidgas av att filen får fel form.
    for varde in priser_for(forfragan.kategori).values():
        tillatna.update(_tal_i(varde))

    return tillatna


def _varden_ur(data: object) -> list[str]:
    """Varje VÄRDE i en konfigurationsstruktur, som text. Aldrig en nyckel.

    **DEN HÄR FUNKTIONEN ÄR SÄNDVÄG.** Allt den returnerar blir tal boten får
    skriva i ett kundmail, se `_tillatna_tal`.

    Går ned genom dictar och listor. **`_`-nycklar hoppas över på VARJE nivå**,
    inte bara den översta: en kommentar en nivå ned är lika mycket en kommentar.
    Nyckelnamnen släpps aldrig igenom alls, eftersom ett namn är en etikett och
    inte en avläsning: `ledtid_14_dagar` är inte en källa för talet 14.
    """
    if isinstance(data, dict):
        varden = []
        for namn, varde in data.items():
            if str(namn).startswith("_"):
                continue
            varden.extend(_varden_ur(varde))
        return varden

    # **LISTGRENEN ÄR DEN SOM `config/priser.json` MEST SANNOLIKT BEHÖVER.** Ett
    # prisregister per tjänst är en lista av objekt i JSON, och utan den här
    # grenen faller listan igenom till `str(data)` nedan, alltså till REPR:EN av
    # listan med varje nästlad `_`-kommentar inbakad. Då är hålet tillbaka.
    if isinstance(data, (list, tuple)):
        varden = []
        for post in data:
            varden.extend(_varden_ur(post))
        return varden

    text = str(data).strip()
    return [text] if text else []


def krav_pa_tal_med_kalla(svar: str, forfragan: Forfragan) -> None:
    """SPÄRR: varje tal i svaret ska ha en källa. §7.2.

    Faller svaret på ett tal utan källa är det ett STOPPTECKEN. Texten skrivs
    inte om tills den passerar, se §9.1.

    **PRISGRENEN VILAR PÅ VAD `config/priser.json` BÄR, inte på att den finns.**
    Före skiva 41 fällde den varje prisord ovillkorligt, med skälet att filen
    inte existerade. Filen finns sedan skiva 41 och är FYLLD sedan skiva 44,
    alltså prövas ett pris nu mot filens egna tal.

    *Skälet var dessutom FALSKT så snart filen skapades. Fällt av
    §7-granskningen av skiva 41, varv 1.*

    *Här stod i presens att filen är TOM och att utfallet därför är oförändrat.
    Lars fyllde fem av sex poster i skiva 44. Fällt av §7-granskningen av
    skiva 46.*

    *Noten sade också att strängen går in i `logg/beslut.jsonl` och i vyn. Båda
    leden är falska: `kedja.logga_beslut` skriver uttryckligen inget `skal`, och
    `till_granskningsfall` skickar `sparr` och aldrig `skal`. En rättelsetext som
    inflaterade allvaret i det den rättade, med en dataväg repot redan tagit
    bort. Fällt av §7-granskningen av skiva 41, varv 2.*

    **DEN DAG LARS FYLLER EN POST HADE DEN GAMLA GRENEN FÄLLT VARJE SVAR SOM
    PROMPTEN BEDER OM.** `_prisrader` skriver in priset och ber modellen återge
    det ordagrant; den ovillkorliga grenen hade sedan fällt varje svar som gjorde
    det. Det är precis den motsägelse §9.1 finns för: nästa skiva möter en spärr
    som fäller det prompten beställt, och frestelsen blir att skriva om texten
    tills den slinker igenom. Uppmätt av §7-granskningen av skiva 41, varv 1.

    **ETT PRIS PRÖVAS MOT PRISKÄLLAN, INTE MOT ALLA TILLÅTNA TAL.** Regeln är en
    egenskap och inte två grenar: **en sats som bär ett prisord får bara bära tal
    som kommer ur `config/priser.json`, och den måste bära minst ett.**

    *En första lydelse lät prisordet falla igenom till den allmänna talloopen så
    snart filen bar något. Den mängden bär också uppslagets vikter och
    `ALLTID_TILLATNA_TAL`, alltså blev fordonets TJÄNSTEVIKT ett tillåtet PRIS:
    "Ombyggnaden kostar 1400 kr" och "Vi tar 3 kr" passerade båda, uppmätt.
    Samma lydelse påstod att ett prisord utan tal faller, men prövade `_tal_i`
    över HELA svaret, så "Det kostar en del, vi hör av oss inom 2 dagar"
    passerade på tvåan. Fällt av §7-granskningen av skiva 41, varv 2.*

    **PRÖVNINGEN SKER PER SATS**, med samma delning som
    `krav_pa_belagt_franvaropastaende`. Ett prisord i en sats ska inte kunna
    hämta sin källa ur ett tal i en annan. Vilka satser som prövas avgörs av
    `_prissatser`, som fogar ihop de par delningen klöv mitt i en prisfras.

    **TELEFONNUMRET ÄR EN KÄLLA OCKSÅ I EN PRISSATS, MEN BARA ORDAGRANT.** Lars
    beslut i skiva 44, se `docs/beslutslogg.md`. Prompten beordrar sedan samma
    skiva att ett svar som nämner ett pris ska följa det med numret, och
    prisgrenen fällde den formen: numrets siffergrupper kommer inte ur
    `config/priser.json`. Uppmätt över tjugo körda mail spärrades FYRA på just
    `talet 076 står i en prismening`, alltså på ett svar som var korrekt för
    kunden.

    **DET ÄR INGEN SÄNKT TRÖSKEL, och skillnaden är exaktheten.** Villkoret är
    att `config/fakta.json`:s telefonvärde står ORDAGRANT i satsen, alltså en
    identisk delsträng ur en §10-grindad källa. Ett godtyckligt tal går inte att
    tvätta den vägen, och en omskriven form av numret, `076 860 38 15` i stället
    för `076-860 38 15`, matchar inte och fäller. Det är samma krav som
    `PRISFOT` och `FAKTAFOT` ställer: ett värde härifrån återges som det står.

    **INVARIANTEN STÅR KVAR: en prissats måste bära minst ett tal ur
    priskällan.** Numrets siffergrupper DRAS BORT ur satsens tal innan regeln
    tillämpas, i stället för att läggas till de tillåtna. Skillnaden är
    lastbärande: ett tillägg hade gjort *"Ring oss på 076-860 38 15 för pris."*
    till ett godkänt prisbesked utan belopp, alltså tagit bort den gren som
    fäller ett prisord utan tal.

    **SUBTRAKTIONEN ÖVERBLOCKERAR I ETT FALL, och det är den säkra riktningen.**
    Bär samma sats både numret och ett pris vars belopp är IDENTISKT med en av
    numrets siffergrupper, faller satsen på att inget tal återstår. Det kräver
    ett pris på 76, 860, 38 eller 15 kronor i samma mening som numret. Utfallet
    blir `utkast`, som Lars läser ändå. Samma avvägning som lucka 55.
    """
    # BARA ÄRENDETS EGEN PRISPOST, skiva 52. Raden läste tidigare hela filen,
    # alltså var `4650` ur `service` en giltig källa i ett a-traktorsvar. Skälet
    # och mätningen står i `priser_for`.
    priskallans_tal: set[str] = set()
    for varde in priser_for(forfragan.kategori).values():
        priskallans_tal |= _tal_i(varde)

    telefon = las_fakta().get(TELEFONNYCKEL, "")
    telefonens_tal = _tal_i(telefon) if telefon else set()

    for sats in _prissatser(svar):
        talen = _tal_i(sats)
        # ORDAGRANT, och därför `in` mot satsen och inte mot talen. Ett nummer
        # som är omskrivet är inte det värde `config/fakta.json` bär.
        if telefon and telefon in sats:
            talen -= telefonens_tal
        if not talen:
            raise Sparrfalld(
                "genererat-tal-har-kalla",
                "svaret nämner ett pris utan att ange ett tal som går att "
                "slå upp mot config/priser.json",
            )
        for tal in sorted(talen - priskallans_tal):
            raise Sparrfalld(
                "genererat-tal-har-kalla",
                f"talet {tal} står i en prismening men kommer inte ur "
                f"config/priser.json",
            )

    traff_i_ord = TAL_I_ORD.search(svar)
    if traff_i_ord:
        raise Sparrfalld(
            "genererat-tal-har-kalla",
            f"svaret skriver talet {traff_i_ord.group(0).lower()!r} i ord, "
            "och ett talord slås inte upp mot någon källa",
        )

    tillatna = _tillatna_tal(forfragan)
    for tal in sorted(_tal_i(svar)):
        if tal not in tillatna:
            raise Sparrfalld(
                "genererat-tal-har-kalla",
                f"talet {tal} kommer varken ur uppslaget eller ur config",
            )


def _faltet_ar_last(uppslag: Uppslag | None, falt: str) -> bool:
    """Bär uppslaget ett AVLÄST värde för det fält termen påstår något om?

    **`None` ÄR INTE ETT VÄRDE, oavsett varför det är `None`.** Ett fält
    registret inte bär och ett fält vi inte kunde läsa ser likadana ut här, och
    det är rätt: båda betyder att svaret inte har någon uppgift att stå för.
    Skillnaden mellan dem avgör något annat, nämligen om UPPSLAGET faller, och
    den frågan är redan avgjord av `fordonsuppslag._krav_pa_gatande_falt` när
    koden når hit.
    """
    if uppslag is None:
        return False

    if falt == "nagon_vikt":
        return any(getattr(uppslag, n) is not None for n in VIKTFALT_I_UPPSLAGET)

    return getattr(uppslag, falt) is not None


def _faltet_for(ord_: str) -> str | None:
    """Vilket fält en träffad fordonsterm påstår något om."""
    for falt, monster in FORDONSFAKTUM_MONSTER.items():
        if monster.fullmatch(ord_):
            return falt
    return None


def krav_pa_fordonsfakta_ur_uppslag(svar: str, forfragan: Forfragan) -> None:
    """SPÄRR: ett fordonsfaktum kräver ett AVLÄST värde för just det fältet.

    Kopplar `fordonsfakta-ur-uppslag` uppströms: den spärren vaktar att ett
    uppslag bara bär värden som hämtningen faktiskt lämnat, den här att svaret
    inte påstår fordonsfakta vi inte har.

    **PRÖVNINGEN ÄR PER FÄLT SEDAN SKIVA 55, och den ändringen är tvingad av
    DEL A.** Ett uppslag kan nu LYCKAS med ett gatande fält tomt, alltså är
    `uppslag is not None` inte längre ett belägg för att en viss uppgift är
    avläst. Med det gamla villkoret hade ett fordon vars sida saknar
    `Släpvagnsvikt` fått skriva *"släpvagnsvikten räcker"* med spärren nöjd.
    Se `FORDONSFAKTUM_FALT`.

    **TRÄFFARNA GÅS IGENOM I TEXTENS ORDNING och inte i fältens.** Skälet bär
    det ord som står FÖRST i svaret, precis som före skiva 55, och en ordning
    som följde `FORDONSFAKTUM_FALT`:s nycklar hade bytt ut skälet på varje svar
    som nämner två fält. Ett skäl Lars läser ska peka på samma mening som förut.

    **SKÄLET SKILJER DE TVÅ LÄGENA ÅT.** Utan uppslag lyder det som alltid, och
    det är den formen `tests/test_generera.py` binder. Med ett uppslag som inte
    bär fältet säger det vilket fält som saknades, eftersom det är den uppgift
    Lars behöver för att se om spärren fällde rätt.
    """
    for traff in FORDONSORD.finditer(svar):
        ord_ = traff.group(0)
        falt = _faltet_for(ord_)

        # **ETT ORD UTAN FÄLT FÄLLER, och grenen är inte död kod.** Unionen binds
        # av `test_varje_FORDONSTERM_har_ett_falt`, men bindningen gäller den
        # TUPEL som finns, inte den som skrivs härnäst. Faller en term ur
        # uppdelningen utan att testet körs ska den behandlas som obelagd, alltså
        # åt det hållet som inte släpper ut något.
        if falt is not None and _faltet_ar_last(forfragan.uppslag, falt):
            continue

        if forfragan.uppslag is None:
            raise Sparrfalld(
                "genererat-fordonsfaktum",
                f"svaret nämner {ord_.lower()} utan ett lyckat uppslag",
            )

        raise Sparrfalld(
            "genererat-fordonsfaktum",
            f"svaret nämner {ord_.lower()} men uppslaget bär ingen uppgift om "
            f"{falt}",
        )


# FAKTA BOTEN KAN PÅSTÅ SAKNAS, med de ord den faktiskt använder om dem.
#
# **ORDEN ÄR AVLÄSTA UR UTFALL, inte uppfunna.** `dragvikt` står i det utkast
# Lars fällde i skiva 40: *"då den saknar dragvikt"*. Resten är samma storhet
# under sidans och kundernas namn.
FRANVAROFAKTA = {
    "dragvikt": r"dragvikt(?:er|en)?|släpvagnsvikt(?:er|en)?|släpvikt(?:er|en)?",
    "draganordning": r"draganordning(?:ar|en)?|dragkrok(?:ar|en)?",
}

# ORD SOM PÅSTÅR ATT NÅGOT INTE FINNS.
#
# **`utan` STÅR MED OCH ÄR DEN LURIGASTE.** *"en bil utan dragvikt"* påstår
# frånvaro lika bestämt som *"saknar dragvikt"*, men innehåller varken `inte`
# eller `saknar`.
#
# **`inte ... någon` ÄR SVENSKANS VANLIGASTE NEKADE EXISTENS, och den saknades
# i en första lydelse.** *"Vi kan tyvärr inte se någon släpvagnsvikt"* slank
# igenom: `ingen` står i listan, men `någon` efter ett `inte` är en annan
# teckenföljd. Uppmätt under bygget, inte i efterhand.
#
# **BARA `inte` DUGER INTE SOM ORD.** Det står i var tredje artig mening, och
# *"det är inte något problem, dragvikten räcker"* är inget frånvaropåstående.
# Därför krävs ett `någ`-ord efter, inom ett kort avstånd.
FRANVAROORD = (
    r"saknar|saknas|utan|ingen|inget|inga|inte finns|finns inte|har inte"
    r"|inte[^.!?]{0,20}?någ\w+"
)

# BAKLÄNGESRIKTNINGEN HAR EN EGEN ORDMÄNGD, och skälet är uppmätt.
#
# `Dragvikten saknas i registret` är ett frånvaropåstående. `Dragvikten är 2000
# kg, så det är inte något problem` är det inte, men med hela `FRANVAROORD` i
# baklängesriktningen fälldes den, mätt under bygget. Ett `inte något` EFTER ett
# faktum negerar något annat än faktumet.
#
# Framlängesriktningen behåller hela mängden: där står nekandet FÖRE ordet, och
# `utan dragvikt` och `inte se någon släpvagnsvikt` är båda äkta.
#
# **MÄNGDEN VAR FÖRST `saknas|saknar` OCH DET VAR FÖR SNÄVT.** Fyra former
# slank igenom, uppmätta av §7-granskningen av skiva 40 varv 1: `finns inte i
# registret`, `är inte angiven`, `är okänd`, `är inte tillgänglig`. Det
# utlösande utkastet sade `saknar dragvikt`, och en omformulering till
# `dragvikten är inte angiven` hade passerat. Varje tillagd form är en
# NEKANDE BESTÄMNING av faktumet, aldrig ett löst `inte`.
# **MÄNGDEN ÄR NU EN EGENSKAP OCH INGEN UPPRÄKNING, och det är varv 2:s fynd.**
# Lydelsen före denna räknade upp `finns inte`, `inte angiven`, `okänd` och
# `inte tillgänglig`, alltså precis de fyra former varv 1 hittade. Varv 2 hittade
# tre till, `framgår inte`, `står inte` och en till, och det kommer alltid att
# gå: en händelselista går att utöka med en post till, vilket
# `biluppgifter._varde_bar_markup` redan bär lärdomen om.
#
# Baklänges godtas därför VARJE NEKANDE ORD. Priset är falska träffar när
# nekandet hör till en annan sats, och det priset betalas av `SATSBROTT` nedan
# i stället för av en uppräkning som aldrig blir färdig.
FRANVAROORD_EFTER = r"inte|ej|ingen|inget|inga|utan|saknar|saknas|okänd|okänt"

# SATSGRÄNSER SOM BRYTER KOPPLINGEN. Uppmätt falsk träff: *"Vi saknar tyvärr en
# ledig tid, men dragvikten är 2000 kg."* Frånvaroordet hör till tiden och inte
# till dragvikten, och det är `, men` som visar det.
#
# **PUNKT RÄCKER INTE**, eftersom samma sak skrivs i en mening lika ofta som i
# två. Fällt av §7-granskningen av skiva 40, varv 1.
SATSBROTT = (", men ", ", så ", ", däremot ", ", fast ", ", utan att ")

# **`, och ` STÅR INTE HÄR LÄNGRE.** Det är SAMORDNANDE, alltså binder det satser
# om samma sak, och delningen blev själv ett kryphål: *"Dragvikten, och det är
# tråkigt, saknas i registret"* delades i tre satser där ingen bar både faktum
# och nekande. Uppmätt av §7-granskningen av skiva 40, varv 2.
#
# De som står kvar är MOTSÄTTANDE eller FÖLJDANGIVANDE, alltså just de fall där
# nekandet hör till en annan sak än faktumet.

# ATT ERBJUDA SIG ATT MONTERA ÄR INTE ATT NEKA. Skiva 40 DEL F, regel 13.
#
# **PROMPTEN BER OM DEN HÄR FORMULERINGEN**, alltså måste den gå igenom:
# *"Om bilen saknar dragkrok monterar vi en"* är ett ERBJUDANDE och inte ett
# negativt besked. Utan undantaget ber regel 13 om en mening spärren fäller,
# vilket §7-granskningen av skiva 40 varv 1 mätte upp.
#
# **UNDANTAGET GÄLLER BARA `draganordning`, och det är avsiktligt.** En dragkrok
# går att montera, en dragvikt gör det inte: den är fordonets konstruktion.
# Ett erbjudande kan alltså aldrig göra ett dragviktspåstående ofarligt.
# **UNDANTAGET KRÄVER BÅDE ETT VILLKOR OCH ETT ERBJUDANDE, och villkoret är
# varv 2:s rättelse.** En första lydelse prövade bara om satsen bar ett
# erbjudandeverb, alltså friade den också ett PÅSTÅENDE: *"Din bil saknar
# dragkrok så det ordnar vi"* slank igenom. Regel 13 ber om en VILLKORSSATS,
# *"Om bilen saknar dragkrok…"*, och det är den formen som undantas.
VILLKOR = r"\bom\b|\bifall\b|\bskulle\b|\bvid behov\b"

ERBJUDANDE = re.compile(
    rf"(?=.*(?:{VILLKOR}))"
    r"(?=.*(?:monterar vi|vi monterar|vi kan montera|kan vi montera"
    r"|ordnar vi|vi ordnar|fixar vi|vi fixar|sätter vi (?:dit|på)))",
    re.IGNORECASE | re.DOTALL,
)

# HUR LÅNGT MELLAN FRÅNVAROORDET OCH FAKTUMET. Måttet är tecken inom SAMMA
# mening: `[^.!?]` slutar vid meningsslut, alltså kan spärren inte koppla ihop
# ett `saknar` i en mening med ett `dragvikt` i nästa.
_AVSTAND = r"[^.!?]{0,80}?"

FRANVAROPASTAENDE = {
    namn: re.compile(
        # BÅDA RIKTNINGARNA. `saknar dragvikt` och `dragvikt saknas` är samma
        # påstående, och en spärr som bara tog den ena hade fällts av den andra.
        rf"(?:(?:{FRANVAROORD}){_AVSTAND}(?:{ord_})"
        rf"|(?:{ord_}){_AVSTAND}(?:{FRANVAROORD_EFTER}))",
        re.IGNORECASE,
    )
    for namn, ord_ in FRANVAROFAKTA.items()
}


def krav_pa_belagt_franvaropastaende(svar: str, forfragan: Forfragan) -> None:
    """SPÄRR: ett påstående om att en uppgift SAKNAS måste vara belagt.

    **RAMVERKSREGEL 3 BRÖTS AV DEN HÄR KLASSEN, och den syntes inte.** Ett
    fordon vars sida saknade `Släpvagnsvikt` fick svaret *"Tyvärr går denna bil
    inte att bygga om till A-traktor då den saknar dragvikt"*, samtidigt som
    härkomstraden sade att uppslaget MISSLYCKADES. Boten gav ett negativt besked
    om ett fält den just rapporterat att den inte kunde läsa.

    **VARFÖR `genererat-fordonsfaktum` INTE FÅNGADE DET.** Den spärren prövar
    VÄRDEN: ett tal eller ett citerat fordonsfaktum. *"saknar dragvikt"* är
    varken. Ett påstående om FRÅNVARO bär inget värde att pröva, och därför fanns
    hela klassen utanför spärrens räckvidd.

    **VAD SOM GÖR PÅSTÅENDET BELAGT: ETT AVLÄST VÄRDE, och ingenting annat.**
    Bara `draganordning` kan bli belagd, och bara genom att uppslaget LYCKATS
    och läst `Nej`. Lars beslut i skiva 41, VÄG TRE, se `docs/beslutslogg.md`
    #93.

    **ETT MISSLYCKAT UPPSLAG GER ALDRIG NÅGON RÄTT**, oavsett vilket av de tre
    lägena härkomstraden rapporterar. En frånvaro är aldrig ett belägg: att
    sidan bara renderar fält som HAR ett värde är sant om SIDAN och osant om vår
    läsning av den, och ett mjukt bindestreck i `Släpvagnsvikt` räcker för att
    fältet ska se saknat ut. LUCKA 50 bär mätningen.

    *Stycket sade att `Faltstatus.SAKNAS_PA_SIDAN` och
    `Dragviktslage.REGISTRET_SAKNAR` gör ett påstående belagt, och att det
    första av tre lägen får sägas. Båda blev falska av VÄG TRE, i spärrens EGEN
    docstring. Fällt av §7-granskningen av skiva 41, varv 1.*
    """
    for mening in _meningar(svar):
        for namn, monster in FRANVAROPASTAENDE.items():
            if namn in forfragan.franvaro_far_pastas:
                continue
            if not monster.search(mening):
                continue

            # ETT ERBJUDANDE OM ATT MONTERA ÄR INGET NEGATIVT BESKED, och bara
            # draganordningen går att montera. Se `ERBJUDANDE`.
            if namn == "draganordning" and ERBJUDANDE.search(mening):
                continue

            raise Sparrfalld(
                "pastaende-om-franvaro",
                f"svaret påstår att {namn} saknas, och det är inte belagt att "
                f"registret saknar uppgiften",
            )


def _delat_pa_mening(svar: str) -> list[str]:
    """Svaret delat vid meningsslut. Delningen tar bort BARA blanktecken.

    **DEN TAR ETT ELLER FLERA, och `_prissatser` skarvar med ETT.** Hopfogningen
    är alltså en NORMALISERING och ingen ångring: `Det är inkl.\\n\\nmoms.` blir
    `Det är inkl. moms.`, en sträng som inte stod i svaret. Det är ofarligt därför
    att varje flerordsterm i `PRISTERMER` tar godtyckligt många blanktecken med
    `\\s*`, inte därför att delningen skulle gå att ångra.

    Skillnaden mot `_delat_pa_satsbrott`, som KASTAR sin avskiljare, är ändå den
    som styr anropsordningen i `_prissatser`: en hopfogning över en sådan skarv
    tillverkar prisfraser som aldrig stått i svaret.

    *Här stod att egenskapen "är lastbärande för `_prissatser`" och att en
    delning som kastar tecken "inte går att ångra utan att texten ändras", alltså
    hela den premiss varv 2 fällde och ersatte på fyra andra ställen. Den här
    docstringen var ett femte ställe, och varv 2:s självrapport sade "rättad på
    alla fyra ställena". Fällt av §7-granskningen av skiva 42, varv 3.*
    """
    return re.split(r"(?<=[.!?])\s+", svar)


def _delat_pa_satsbrott(delar: list[str]) -> list[str]:
    """Delarna vidare delade vid `SATSBROTT`. Delningen KASTAR avskiljaren."""
    for brott in SATSBROTT:
        nya: list[str] = []
        for del_ in delar:
            nya.extend(del_.split(brott))
        delar = nya
    return delar


def _meningar(svar: str) -> list[str]:
    """Svaret som meningar, och satser skilda av `SATSBROTT` som egna.

    **PRÖVNINGEN SKER PER SATS OCH INTE PER SVAR.** Ett frånvaroord i en sats
    ska inte kunna kopplas till ett fordonsfaktum i en annan, och `[^.!?]` i
    mönstret räcker inte: *"Vi saknar tyvärr en ledig tid, men dragvikten är
    2000 kg"* är EN mening med två satser.
    """
    return _delat_pa_satsbrott(_delat_pa_mening(svar))


def _prisord_over_skarven(forsta: str, andra: str) -> bool:
    """Ligger ett prisord ÖVER skarven mellan två angränsande MENINGAR?

    Måttet är en MATCHNING SOM SPÄNNER, inte en jämförelse av vad halvorna var
    för sig bär. Skillnaden är lastbärande och uppmätt: *"Det kostar 25 000 kr
    exkl. moms 1400."* har ett giltigt prisord i sin FÖRSTA halva, alltså hade
    ett villkor av formen "ingendera halvan bär ett prisord" låtit paret vara.
    Då prövas `moms 1400.` aldrig av prisgrenen, och 1400 faller ned i den
    allmänna talloopen där uppslagets tjänstevikt är tillåten. Det är lucka 54:s
    egen defekt, flyttad ett steg.

    **BARA MENINGSSKARVAR, ALDRIG `SATSBROTT`-SKARVAR.** `_delat_pa_satsbrott`
    KASTAR sin avskiljare, och en hopfogning över en sådan skarv TILLVERKAR text
    som aldrig stått i svaret: *"Vi tar det exkl, men moms är inräknad 1400."* bär
    inget prisord alls, men blir `exkl moms` när `, men ` faller bort, och då
    fälls en avläst tjänstevikt med motiveringen att den står i en prismening som
    inte finns. Uppmätt av §7-granskningen av skiva 42, varv 1. Skyddet ligger i
    anropsordningen i `_prissatser`, inte här.

    **MENINGSSKARVEN ÄR OFARLIG DÄRFÖR ATT VARJE FLERORDSTERM ÄR BLANKSTEGSTÅLIG,
    inte därför att hopfogningen återställer det som togs bort.**
    `_delat_pa_mening` delar på `\\s+`, alltså ETT ELLER FLERA blanktecken, medan
    hopfogningen skarvar med ETT mellanslag. Det är en NORMALISERING och ingen
    återställning: `Det är inkl.\\n\\nmoms.` blir `Det är inkl. moms.`, en sträng
    som inte stod i svaret. Den kan ändå varken skapa eller förstöra en
    `PRISORD`-matchning, eftersom `inkl\\.?\\s*moms`, `exkl\\.?\\s*moms` och
    `\\d\\s*tkr` alla tar godtyckligt många blanktecken med `\\s*`, och `_tal_i`
    stryper `[\\s.,]`.

    *Här stod att skarvens blanksteg "återställer vad `_delat_pa_mening` tog bort,
    ingenting annat". Det är falskt för varje skarv med mer än ett blanktecken,
    och meningen hade citerats vidare till två styrdokument och en testdocstring.
    Fällt av §7-granskningen av skiva 42, varv 2.*
    """
    skarv = len(forsta)
    par = f"{forsta} {andra}"
    return any(traff.start() < skarv and traff.end() > skarv + 1
               for traff in PRISORD.finditer(par))


def _prissatser(svar: str) -> list[str]:
    """Satserna som ska prövas av prisgrenen, med klyvda prisfraser lagade.

    **SATSDELNINGEN FÅR ALDRIG TAPPA ETT PRISORD.** `PRISORD` bär fraser med
    punkt i, `inkl. moms` och `exkl. moms`, och `_meningar` klyver dem mitt itu:
    `Det är inkl.` plus `moms.`, där ingendera halvan matchar.

    **LUCKA 54, LARS BESLUT I SKIVA 42: FOGA SAMMAN SATSPAR.** Reserven längst
    ned fångade klyvningen BARA när ingen sats alls bar ett prisord. Bar en annan
    mening ett giltigt prisord blev urvalet icke-tomt, reserven löpte aldrig, och
    den klyvda satsen prövades inte av prisgrenen alls. Uppmätt mot hela
    `krav_pa_svaret` i skiva 41 varv 3, med prisfilen fylld och ett uppslag med
    tjänstevikt 1400: *"Konverteringen kostar 25 000 kr. Dragkroken blir 1400
    extra inkl. moms."* passerade, alltså blev fordonets tjänstevikt ett
    citerbart pris.

    Regeln är en EGENSKAP och ingen förkortningslista: spänner ett prisord över
    skarven mellan två angränsande meningar, så har delningen förstört frasen och
    de fogas ihop. Se `_prisord_over_skarven`.

    **HOPFOGNINGEN GÅR I KEDJA OCH ALDRIG PARVIS, och det ledet är fällt fram.**
    En parvis regel som hoppar två steg efter en hopfogning prövar aldrig skarven
    mellan den andra halvan och nästa mening. Bär en mening slutet av en prisfras
    OCH början av nästa blir den tredje delen föräldralös och når aldrig
    prisgrenen: *"Det kostar 25 000 kr exkl. moms är inkl. moms 1400."* passerade,
    och 1400 är uppslagets tjänstevikt. Det är lucka 54:s defekt igen, flyttad ett
    steg. Uppmätt av §7-granskningen av skiva 42, varv 1.

    **ORDNINGEN ÄR LASTBÄRANDE: MENINGAR, HOPFOGNING, SEDAN `SATSBROTT`.**
    `_delat_pa_satsbrott` kastar sin avskiljare, alltså skulle en hopfogning
    efter den delningen TILLVERKA prisfraser som aldrig stått i svaret. En
    hopfogning över en MENINGSSKARV normaliserar däremot bara blanktecken, och
    det kan inte ändra vilken pristerm som matchar. Se `_prisord_over_skarven`.

    **DET HÄR ÄR EN AVVÄGNING LARS GJORT, inte en gratis förbättring.** Varje
    hopfogning gör en sats större, och prisgrenen kräver att VARJE tal i en
    prissats kommer ur `config/priser.json`. Fler tal i samma sats betyder alltså
    fler fällningar, och lucka 55 är den kostnaden. Lars skäl, ordagrant:
    överblockering kostar Lars fem sekunders läsning, underblockering kostar ett
    felaktigt prisbesked till en kund. `scripts/prismatning.py` mäter priset.

    **RESERVEN ÄR BORTTAGEN, och det är ett fynd och ingen förenkling.** Raden
    `if not satser and PRISORD.search(svar)` prövade hela svaret som en sats när
    ingen enskild sats bar prisordet. Med kedjefogningen är den ONÅBAR: en
    fällning av den gav GRÖN svit över hela sviten, alltså band inget test den.
    Skälet den motiverades med, en prisfras som spänner över TRE delar, kan inte
    inträffa: de enda fleroordstermerna i `PRISTERMER` är `inkl. moms`,
    `exkl. moms` och `\\d\\s*tkr`, och ingen av dem kan rymma två klyvpunkter,
    eftersom `_delat_pa_mening` klyver vid `[.!?]` och `_delat_pa_satsbrott` vid
    strängar som alla bär ett kommatecken. Invarianten den bar, att ett svar med
    ett prisord alltid ger minst en sats att pröva, är bunden av
    `tests/test_generera_monster.py::test_ett_PRISORD_i_tabellen_nar_ALLTID_prisgrenen`.
    Uppmätt av §7-granskningen av skiva 42, varv 1.

    *Raden namngav `test_varje_PRISTERM_overlever_delningen`, ett testnamn som
    inte finns i repot: `grep -rn` gav en enda träff, citatet självt. Det är
    samma form som beslutsradstabellen i `docs/sparrar.md` fälldes för i samma
    skiva, en obefintlig kodrad utbytt mot en obefintlig testrad, och den satsen
    är hela argumentet för att en sändvägsreserv fick tas bort. Fällt av
    §7-granskningen av skiva 42, varv 2.*
    """
    delar = _delat_pa_mening(svar)

    hopfogade: list[str] = []
    i = 0
    while i < len(delar):
        j = i
        while j + 1 < len(delar) and _prisord_over_skarven(delar[j], delar[j + 1]):
            j += 1
        hopfogade.append(" ".join(delar[i:j + 1]))
        i = j + 1

    return [s for s in _delat_pa_satsbrott(hopfogade) if PRISORD.search(s)]


# BARLASTFLAKET, i de former ett svar skriver det. LUCKA 69.
#
# **EN TERM PER RAD, UTAN INTERN ALTERNATION**, samma krav som de fyra mängderna
# ovan och bundet av `test_ingen_term_gommer_en_alternation`.
#
# **ASCII-FORMEN STÅR MED**, till skillnad från `ATAGANDETERMER`. Skälet som
# stänger den vägen där är att `tacks` ligger en bokstav från `tack`; `barlastflak`
# bär inget diakritiskt tecken alls, alltså finns ingen ASCII-variant att välja
# bort. Raden `barlastflak` täcker både `barlastflaket` och `barlastflaken` genom
# `\w*`.
BARLASTTERMER = (
    r"barlastflak\w*",
    r"barlast\b",
    r"barlasten\b",
)

BARLASTORD = re.compile("|".join(BARLASTTERMER), flags=re.IGNORECASE)


def krav_pa_barlastflak_som_galler_fordonet(svar: str,
                                            forfragan: Forfragan) -> None:
    """SPÄRR: barlastflak får inte nämnas för ett fordon §39 inte gäller. LUCKA 69.

    Faller svaret här är det ett STOPPTECKEN. Texten skrivs inte om tills den
    passerar, se §9.1.

    **REGELN ÄR LARS, skiva 55 DEL A gatingsregel 2.** `config/priser.json`:s
    a-traktorpost räknar upp `barlastflak` som en del av grundombyggnaden, och
    prompten beordrar att priset återges. För ett fordon där §39:s krav
    bevisligen inte gäller blir uppräkningen ett falskt påstående om just den
    bilen. Hans fall är det fyrhjulsdrivna fordonet i körningen.

    **SPÄRREN FÄLLER BARA PÅ ETT BEVISAT `False`.** `kraver_barlastflak` svarar
    `None` när registret inte räcker till, och då säger vi ingenting: ett svar
    som nämner flaket faller alltså inte bara för att vi är osäkra. Det är samma
    riktning som `pastaende-om-franvaro` har, och av samma skäl: en spärr som
    fäller på okunskap fäller de flesta svaren och blir avstängd.

    **DEN ÄR NÄTET UNDER PROMPTEN, inte det enda skyddet.** `_underlag` skriver
    ut för varje sådant fordon att flaket inte ska nämnas, och `PRISFOT`:s krav
    på ordagrann återgivning är vikt för den raden. Ordlistan är lika lite
    uttömmande som `PRISORD` och `FORDONSORD`: en modell kan räkna upp
    grundombyggnadens innehåll utan att skriva ordet. Formen står som LUCKA 70.

    **SPÄRREN KAN INTE STÄNGA HÅLET I `config/priser.json`, och det ska sägas
    rakt ut.** Prisradens uppräkning gäller varje bil, och för de här fordonen är
    den fel oavsett vad boten skriver. Att ändra posten är §10 och Lars beslut.
    """
    if forfragan.uppslag is None:
        return

    if fordonsuppslag.kraver_barlastflak(forfragan.uppslag) is not False:
        return

    traff = BARLASTORD.search(svar)
    if traff:
        raise Sparrfalld(
            "barlastflak-galler-fordonet",
            f"svaret nämner {traff.group(0).lower()} för ett fordon som §39 "
            f"inte gäller",
        )


def krav_pa_att_troskeln_inte_ar_forfattningstext(svar: str) -> None:
    """SPÄRR: tröskeln 1 000 kg får inte återges som en sammanfattad föreskrift.

    Talet står i VVFS 2003:19 4 kap 42 §, och paragrafen har TVÅ kriterier
    förenade med ELLER. Ett svar som återger det ena som "kravet" gör en
    ofullständig föreskrift till ett besked, se `docs/roadmap.md` fas 4.5.
    """
    if TROSKELTAL.search(svar) and FORFATTNINGSORD.search(svar):
        raise Sparrfalld(
            "troskeln-som-forfattningstext",
            "svaret återger tröskeln 1 000 kg som ett krav eller en regel",
        )


def krav_pa_atagande_med_kalla(svar: str, forfragan: Forfragan) -> None:
    """SPÄRR: ett åtagande om vad priset täcker kräver en källa. LUCKA 59.

    Faller svaret här är det ett STOPPTECKEN. Texten skrivs inte om tills den
    passerar, se §9.1.

    **`forfragan` TILLKOM I SKIVA 52 och bär bara kategorin.** Spärren tog förut
    enbart svaret, eftersom dess källa var hela `config/priser.json`. Nu väljer
    kategorin posten, se `priser_for`, och då måste den nå hit. Parametern har
    INGET förval: en anropare som glömmer den ska falla på `TypeError` och inte
    tyst få en spärr som vaktar fel kategoris priser.

    **REGELN ÄR LARS, och skälet är hans:** ett åtagande om vad som ingår i ett
    pris är samma klass som ett påhittat pris. Ärende 19 skrev *"dragkrok ingår i
    bygget"* medan prisfilens post säger att priset gäller de delar som ingår i
    GRUNDPAKETET, ett innehåll boten inte känner. Meningen bär varken tal eller
    prisord, alltså rörde ingen befintlig spärr den.

    **FÖREMÅLET PRÖVAS, INTE ORDET. LARS §10-BESLUT I SKIVA 47.** Hans skäl,
    ordagrant: spärren fällde på ORDET i stället för på PÅSTÅENDET, och ordet
    `ingår` är inget fel, ett obelagt föremål är det.

    Prövningen sker i tre led, per sats:

    1. Varje värde ur `config/priser.json` stryks ur svaret. Är prisraden
       ORDAGRANT återgiven finns inget åtagandeord kvar att pröva.
    2. Bär satsen ett `FORDONSORD` faller den alltid, också när den dessutom
       namnger en belagd del. `I priset ingår barlastflak och dragkrok.` ska
       falla på dragkroken och inte frias av barlastflaket.
    3. Annars passerar satsen om den namnger minst en DEL som källan räknar upp
       som ingående, se `_uppraknade_delar`.

    **LED 3 PRÖVAR SATSEN SOM EN PÅSE OCH INTE ÅTAGANDETS FÖREMÅL, och det är
    en ÖPPEN LUCKA.** Namnger satsen en enda belagd del passerar varje annat
    åtagande i samma sats, så länge det inte är ett `FORDONSORD`:
    *"I priset ingår besiktning och lackering."* passerar. Klassen är uppmätt i
    verklig korpus och står som LUCKA 67 i `docs/sparrar.md`. Att skärpa regeln
    är §10 och Lars beslut, se `docs/beslutslogg.md` #111.

    **DEN FÖRRA LYDELSEN GODTOG KÄLLAN ORDAGRANT OCH INGENTING ANNAT, och den
    föll på mätning.** Kravet var samma som `PRISFOT` ställer på prompten. I
    fält infriades det aldrig: TRETTIO genereringar över tre olika lydelser av
    prisposten gav NOLL ordagranna återgivningar, och de tjugo gav noll utkast.
    Modellen skriver *"En grundombyggnad kostar … och omfattar …"* och eliderar
    det upprepade subjektet, alltså är innehållet rätt och bindningen omskriven.

    **DE TRE MÄTTA LYDELSERNA VAR KANDIDATER OCH INTE DE TRE SOM FÖRKASTATS I
    TUR OCH ORDNING.** Skillnaden är fällt fram: kandidaterna prövades i samma
    mätning, mot samma tio mail, och TVÅ av dem bar inget åtagandeord alls i
    källan, `för grundombyggnaden med …` respektive `för en grundombyggnad
    med …`. Modellen skrev `ingår` eller `inkluderar` ändå i nio fall av tio.
    Att räkna upp vad ett paket innehåller är att skriva ett åtagandeord på
    svenska, och det är ingen egenskap hos någon lydelse.

    *Här stod bara "de tre lydelserna", vilket läste som de tre lydelser
    prisposten haft i tur och ordning. De bär alla ett åtagandeord, alltså var
    meningen falsk under den läsningen. Fällt av §7-granskningen av skiva 47.*

    **ORDAGRANNHETEN GÄLLER ORDEN, inte versalen och inte radbrytningen, och det
    ledet är fällt fram.** En första lydelse strök värdet med `str.replace`,
    alltså skiftlägeskänsligt och teckenexakt på varje blanktecken. Följden var
    att ett svar som INLEDER en mening med prisraden föll: `Från 20 000 till…`
    är inte `från 20 000 till…`. Promptens regel 15 beordrar att priset ALLTID
    skrivs i ett a-traktorsvar, alltså hade en versal begynnelsebokstav eller en
    radbrytning mitt i raden gjort varje sådant svar till ett STOPPTECKEN enligt
    §9.1, på precis den kategori boten finns för. Uppmätt av §7-granskningen av
    skiva 46.

    Strykningen är därför skiftlägesokänslig, och varje blankteckensrun i värdet
    matchar en godtycklig blankteckensrun i svaret. **DET ÄR INGEN SÄNKT
    TRÖSKEL:** varje ORD och varje siffra måste fortfarande stå i sin ordning,
    och ett inskjutet eller struket ord fäller lika hårt som förut.

    **ETT TOMT VÄRDE NÅR ALDRIG HIT.** `las_konfigvarden` utelämnar det, och det
    ledet är lastbärande: ett mönster byggt ur en tom sträng matchar mellan varje
    tecken, alltså hade hela svaret strukits och spärren tystnat helt.
    `config/priser.json` bär en tom post i dag, `tillbehor`.

    **PRÖVNINGEN SKER PER SATS, och det ledet kom med skiva 47.** Samma skäl som
    de andra spärrarna har: ett åtagandeord i en sats ska inte kunna hämta sitt
    BELÄGG ur en annan. *"I priset ingår barlastflak. Lackering ingår också."*
    har en belagd sats och en obelagd, och den andra faller för sig. Bunden av
    `test_PRÖVNINGEN_SKER_PER_SATS_och_inte_per_svar`.

    *Exemplet här var först *"…Dragkrok ingår också."*, som faller ÄVEN utan
    per-sats-ledet, på `dragkrok` som `FORDONSORD`. Det bevisade alltså
    ingenting om det här ledet, och ledet självt var OFÄLLBART: satt till
    `for sats in [kvar]` gick hela sviten grön. Fällt av §7-granskningen av
    skiva 47.*

    **SATSDELNINGEN KAN FLYTTA ETT FORDONSORD UR SATSEN.** `SATSBROTT` kastar
    sin avskiljare, alltså hamnar `krok` i en egen sats i *"Vi sätter dit en
    krok, så besiktning och montering ingår."* och fordonsordsledet ser den
    aldrig. Formen passerar, och den föll vid HEAD. LUCKA 68.

    *Här stod VARFÖR PRÖVNINGEN INTE SKER PER SATS, med skälet att ingenting
    hämtades och att strykningen bara var textuell. Det skälet upphörde att
    gälla när föremålsprövningen kom in: nu HÄMTAS ett belägg, och då måste
    satsgränsen hålla.*

    **STRYKNINGEN KAN TILLVERKA EN TRÄFF, och det är en ÖVERBLOCKERING.** Värdet
    byts mot ett BLANKSTEG och inte mot ingenting, alltså kan två halvor inte
    fogas ihop till en term som spänner över skarven. Men en term som ligger
    INTILL skarven får en ny ordgräns av blanksteget: `…motortvätt 500 kringår.`
    bär ingen term, och efter strykningen står `ingår` där. Utfallet blir ett
    utkast Lars läser, aldrig ett släppt åtagande.

    *Här stod att strykningen INTE KAN tillverka ett åtagandeord, med skälet att
    varje term är ordgränsad. Skälet täcker bara en term som spänner ÖVER
    skarven, och påståendet var alltså falskt för en term intill den. Fällt av
    §7-granskningen av skiva 46.*

    *Här stod att spärren ÖVERBLOCKERAR när modellen skriver om prisraden, och
    att det är den säkra riktningen. Formen passerar numera, och det är hela
    ändringen i skiva 47.*

    **DELARNA JÄMFÖRS SOM DELSTRÄNGAR, och det är en medveten uppmjukning.**
    Källan säger `besiktning`, svaret skriver `besiktningen`. En ordgränsad
    jämförelse hade fällt varje böjd form. Priset är att en del kan namnges av
    en slump: bär källan en KORT del friar den varje sats som råkar bära
    tecknen, och `MINSTA_DEL` finns just för det. Formen står som en del av
    LUCKA 66 i `docs/sparrar.md`.

    **UPPRÄKNINGEN AV ORD ÄR INTE UTTÖMMANDE.** Samma sak gäller `PRISORD` och
    `FORDONSORD`: en modell kan alltid formulera ett åtagande utan något av
    orden. Vad som bär i det fallet står som LUCKA 61 i `docs/sparrar.md`, och
    det är ingen promptregel i dag: §11 gör promptens ordalydelse till Lars.
    """
    # BARA ÄRENDETS EGEN PRISPOST STRYKS, och bara den räknar upp delar.
    # Skiva 52: båda raderna läste tidigare hela filen. Följden var att
    # `grundombyggnaden omfattar ...` i a-traktorposten friade ett åtagande i ett
    # SERVICEsvar, och tvärtom. Se `priser_for`.
    egna_priser = priser_for(forfragan.kategori)

    kvar = svar
    for varde in egna_priser.values():
        kvar = _UTAN_PRISVARDE(varde).sub(" ", kvar)

    delar = _uppraknade_delar(forfragan.kategori)

    for sats in _meningar(kvar):
        traff = ATAGANDEORD.search(sats)
        if not traff:
            continue

        ord_ = traff.group(0).lower()

        # ETT FORDONSORD I SAMMA SATS FÄLLER ALLTID, också när satsen dessutom
        # namnger en belagd del. `I priset ingår barlastflak och dragkrok.`
        # ska falla på dragkroken och inte frias av barlastflaket, alltså
        # prövas det här ledet FÖRST.
        fordon = FORDONSORD.search(sats)
        if fordon:
            raise Sparrfalld(
                "atagande-om-priset",
                f"svaret säger {ord_!r} om {fordon.group(0).lower()}, och den "
                f"delen står inte i config/priser.json",
            )

        # FÖREMÅLET PRÖVAS MOT KÄLLANS UPPRÄKNING. Namnger satsen minst en del
        # som `config/priser.json` räknar upp är åtagandet belagt.
        if any(del_ in sats.lower() for del_ in delar):
            continue

        raise Sparrfalld(
            "atagande-om-priset",
            f"svaret säger {ord_!r} om ett arbete som inte står i "
            f"config/priser.json",
        )


def krav_pa_ett_svar(svar: str) -> None:
    """SPÄRR: ett tomt svar är inget utkast.

    **VARJE ANNAN SPÄRR SÖKER EFTER SAKER, alltså släpper de alla igenom
    en tom sträng.** Följden var att ett tomt modellsvar blev ett godkänt
    utkast: `blev_utkast` sant, `forslag` tomt, ingen spärr angiven. I vyn blev
    det ett tomt textfält som gick att omdöma, och ett `forbattra` hade skrivit
    ett par med en tom förlaga till `data/par.jsonl`, som generatorn läser som
    få-exempel.

    Uppmätt som en möjlig väg av §7-granskningen av skiva 34, varv 2.

    *Här stod "DE TRE ANDRA SPÄRRARNA" och "alla tre". `krav_pa_svaret` anropar
    sex, alltså fem andra än den här. Talet var falskt redan när skiva 40 byggde
    `pastaende-om-franvaro`, och skiva 46 gjorde det falskare. Fällt av
    §7-granskningen av skiva 46.*
    """
    if not svar.strip():
        raise Sparrfalld("tomt-svar", "modellen svarade ingenting")


def krav_pa_svaret(svar: str, forfragan: Forfragan) -> None:
    """Varje spärr på det genererade, i tur och ordning.

    **VAR OCH EN FÄLLER FÖR SIG.** Testen fäller dem en i taget och aldrig i par:
    skiva 27 mätte att en sammanslagen fällning ger RÖD och därmed falskt ÄKTA,
    alltså ett belägg för att båda bär när bara den ena gör det.
    """
    krav_pa_ett_svar(svar)
    krav_pa_tal_med_kalla(svar, forfragan)
    krav_pa_fordonsfakta_ur_uppslag(svar, forfragan)
    krav_pa_belagt_franvaropastaende(svar, forfragan)
    krav_pa_barlastflak_som_galler_fordonet(svar, forfragan)
    krav_pa_att_troskeln_inte_ar_forfattningstext(svar)
    krav_pa_atagande_med_kalla(svar, forfragan)


# ------------------------------------------------------------------ DEL B


def las_exempel(parfil: Path | None = None, antal: int = ANTAL_EXEMPEL,
                etikettfil: Path | None = None) -> list[dict]:
    """Få-exemplen ur `data/par.jsonl`, BARA a-traktorpar, filtrerade enligt §11.

    **KATEGORIFILTRET ÄR HELA POÄNGEN, och det saknades.** Lars brief säger "ta
    a-traktorparen som få-exempel". Första lydelsen tog de kortaste av SAMTLIGA
    par i utkorgen, och de sex som hamnade i prompten var bokningsbekräftelser
    och en fråga om en mellanvägg. **Noll a-traktorpar.** Mätningen i DEL B
    räknade alltså en population koden inte använde. Fällt av §7-granskningen av
    skiva 31, varv 1.

    `par.jsonl` bär ingen kategori, så den hämtas ur `ometiketterade.jsonl` på
    kundtexten, samma koppling som `src/vy.py::_par_karta` och
    `scripts/par-matning.py`.

    **ETT EXEMPEL SOM BRYTER MOT §11 LÄR MODELLEN ATT BRYTA MOT DEN.** Uppmätt
    med `scripts/par-matning.py`: av 43 a-traktorpar ryms 32 under taket, och 18
    av dem bryter mot §11. Kvar blir 14.

    Urvalet är de kortaste av de dugliga, eftersom ett kort exempel lämnar plats
    åt fler och åt kundens egen text.
    """
    parfil = PAR if parfil is None else parfil
    etikettfil = OMETIKETTERADE if etikettfil is None else etikettfil

    if not parfil.exists():
        return []

    par = [json.loads(r) for r in parfil.read_text(encoding="utf-8").splitlines() if r]
    a_traktortexter = _a_traktortexter(etikettfil)

    dugliga = [
        p
        for p in par
        if p.get("inkommande_text") in a_traktortexter and _duger_som_exempel(p)
    ]
    dugliga.sort(key=lambda p: len(p["utgaende_text"]))
    return dugliga[:antal]


def _a_traktortexter(etikettfil: Path) -> set[str]:
    """Kundtexterna som är etiketterade som a-traktorärenden.

    Saknas filen returneras en TOM mängd, alltså inga exempel alls. Det är
    avsiktligt: hellre en prompt utan få-exempel än en med exempel ur fel
    kategori, vilket är precis felet den här funktionen finns för att rätta.
    """
    if not etikettfil.exists():
        return set()

    texter = set()
    for rad in etikettfil.read_text(encoding="utf-8").splitlines():
        if not rad:
            continue
        post = json.loads(rad)
        if post.get("etikett") in A_TRAKTORETIKETTER:
            texter.add(post.get("text"))
    return texter


# §11:s FÖRBJUDNA PRONOMEN, som ORDGRÄNSER och inte som blankstegsomgivning.
#
# Första lydelsen letade efter `" jag "`, alltså med blanksteg på båda sidor, och
# missade varje förekomst följd av skiljetecken: "Det fixar jag." och "Jag, som
# skrev, ordnar det." dög båda som exempel. `man` saknades helt trots att §11
# namnger det. Fällt av §7-granskningen av skiva 31.
FORBJUDNA_PRONOMEN = re.compile(
    r"\b(jag|mig|min|mitt|mina|man)\b", flags=re.IGNORECASE
)

# BINDESTRECK SOM SKILJETECKEN, alltså med blanksteg omkring. Ett bindestreck
# inuti ett ord, som i "a-traktor", är inte ett skiljetecken och ska passera.
BINDESTRECK_SOM_SKILJETECKEN = re.compile(r"\s[-—–]\s")


def _duger_som_exempel(par: dict) -> bool:
    """Ett par duger när båda leden bär text, svaret ryms, och §11 hålls.

    §11:s regler som prövas här: första person plural, inga tankstreck eller
    bindestreck som skiljetecken, aldrig "friverkstad". Konkurrentnamn prövas
    INTE, eftersom det kräver en lista över konkurrenter som repot inte har; det
    är en registrerad lucka i `docs/sparrar.md`.
    """
    in_text = (par.get("inkommande_text") or "").strip()
    ut_text = (par.get("utgaende_text") or "").strip()

    if not in_text or not ut_text:
        return False
    if len(ut_text) > MAX_TECKEN_EXEMPEL:
        return False
    if "—" in ut_text or "–" in ut_text:
        return False
    if BINDESTRECK_SOM_SKILJETECKEN.search(ut_text):
        return False
    if "friverkstad" in ut_text.lower():
        return False

    return not FORBJUDNA_PRONOMEN.search(ut_text)


# **BOKNINGSBESKEDET LIGGER I `config/fakta.json` SEDAN SKIVA 37.** Det var en
# konstant här, alltså ett påstående om Auto Stockholm som bodde i kod, vilket är
# lucka 29:s form och stod som LUCKA 43. Lars flyttade det med ett §10-beslut och
# stängde luckan. Källan är nu grindad, och `_faktarader` skriver ut den.
#
# Att konstanten är BORTA och inte bara oanvänd är §3: en orphan som mina egna
# ändringar skapade städas.

SYSTEM = """Du skriver svarsutkast åt Auto Stockholm, en fristående verkstad i \
Stockholm som bygger om bilar till a-traktor.

DU SKRIVER ETT UTKAST. En människa läser det innan det går ut.

REGLER SOM ALDRIG BRYTS:

1. Första person plural. Vi, oss, vår, våra. Aldrig jag, mig, min, eller man.
2. Inga tankstreck eller bindestreck som skiljetecken. Komma, punkt, kolon, \
eller skriv om meningen.
3. Skriv aldrig "friverkstad". Skriv "fristående verkstad".
4. Nämn aldrig en konkurrent.
5. ALDRIG ETT PRIS utöver det som står i underlaget nedan. Inte ett belopp, inte \
ett ungefärligt pris, inte "ring för offert". Står inget pris i underlaget och \
kunden frågar vad det kostar: säg att VI återkommer med prisuppgift.
6. ALDRIG ETT TAL som inte står i underlaget nedan. Inga vikter, inga ledtider, \
inga antal du inte fått.
7. Återge aldrig en lagtext eller en föreskrift sammanfattad. Säg inte att något \
är ett krav enligt lag.
8. Påstå aldrig något om vad Auto Stockholm har, erbjuder eller innehåller \
utöver det som står i underlaget nedan. Inte vår hemsida, inte våra öppettider, \
inte vårt lager, inte våra tjänster.
9. INGA KOLLEGOR. Vi är en liten verkstad utan en organisation att hänvisa \
vidare till. Skriv aldrig "en kollega", "vår tekniker", "vår säljare" eller \
"en av våra". Det är VI som återkommer, VI som tittar på bilen, VI som hör av \
oss.
10. EN BOKNINGSFÖRFRÅGAN BESVARAS MED JA. Frågar kunden om vi kan ta emot bilen \
en viss månad eller vecka, så svarar vi att det löser vi och ber dem höra av \
sig så bestämmer vi tid. Hänvisa inte vidare och be dem inte återkomma senare. \
LOVA ALDRIG EN TID: ingen vecka, ingen månad, inget datum och ingen ledtid. \
Tiden bestäms i kontakten, aldrig i det här mailet.
11. FRÅGA ALDRIG EFTER UPPGIFTER SOM REDAN STÅR I MAILET. Läs mailet först. \
Står registreringsnumret där, fråga inte efter det. Frågan är rimlig bara när \
uppgiften saknas.
12. SKRIV OM REGISTRET, INTE OM REGISTERFÄLTET. Säg "bilen saknar registrerad \
draganordning", aldrig "bilen har en registrerad draganordning som anger nej". \
Det andra beskriver vår avläsning i stället för bilen, och kunden läser om sin \
bil och inte om vår databas.
13. EN SAKNAD DRAGKROK ÄR INGET HINDER. Behöver bilen en dragkrok, skriv att vi \
kan montera en om det behövs. Ber du kunden bekräfta om det sitter en dragkrok, \
så skriv i samma mening att vi kan montera en. Utan det läser frågan som ett \
villkor kunden måste uppfylla själv.
14. NÄMNER DU ETT PRIS, SKRIV TELEFONNUMRET DIREKT EFTER I EN EGEN MENING. \
Priset är ett intervall och varje bygge är unikt, alltså är beloppet aldrig ett \
besked om vad just den här bilen kostar. Återge priset som det står i \
underlaget, sätt punkt, och be kunden ringa oss på numret i underlaget så \
tittar vi på just den bilen. Priset och numret får ALDRIG stå i samma mening.
15. FRÅGAR KUNDEN OM EN OMBYGGNAD TILL A-TRAKTOR OCH STÅR PRISET I UNDERLAGET, \
SKRIV ALLTID VAD DEN KOSTAR. Det gäller ÄVEN när du inte kan ge något besked om \
just den bilen. Att uppslaget är oklart, att en uppgift saknas, eller att vi \
behöver titta närmare på bilen är inget skäl att utelämna priset. Kunden vill \
veta vad en ombyggnad kostar oavsett vad registret säger om just den bilen.
16. SKRIV ALDRIG ATT EN DRAGKROK INGÅR. Inte att den ingår i priset, i bygget \
eller i grundombyggnaden, och inte att den följer med eller är inkluderad. \
Regel 13 står oförändrad och säger vad du DÄREMOT skriver när bilen behöver en.
17. SKRIV ALDRIG BILENS MODELLBETECKNING. Inte V70, inte E60, inte A3, inte \
X3M. Skriv "bilen", "din bil" eller "er bil". Fabrikatet får du skriva. \
Beteckningen bär nästan alltid en siffra, och en siffra i ett utgående mail \
måste ha en källa.
18. ETT PRISORD KRÄVER ETT BELOPP I SAMMA MENING. Orden pris, priset, kostar, \
kostnad, offert, avgift och kronor får bara stå i en mening som också bär \
priset ur underlaget. Vill du säga att vi tittar närmare på bilen, skriv det \
utan prisord: "hör av dig så tittar vi på just din bil". Behöver du säga att \
priset beror på bilen, skriv "vi återkommer med prisuppgift".
19. NÄR DU ERBJUDER EN DRAGKROK SKA DU SÄGA VARFÖR DEN HJÄLPER. Står det i \
underlaget att bilen duger som dragfordon, skriv ut släpvagnsvikten ur \
underlaget i samma stycke. En dragkrok på en bil som inte duger hjälper inte, \
och ett erbjudande utan skälet läser kunden som ett villkor.

Skriv kort, konkret och vänligt. Svara på det kunden faktiskt frågar."""


def bygg_prompt(forfragan: Forfragan, exempel: list[dict]) -> str:
    """Användarmeddelandet: få-exempel, underlag, och kundens mail.

    Exemplen märks som EXEMPEL och kundens mail som det som ska besvaras, så att
    modellen inte svarar på ett exempel i stället.
    """
    delar = []

    if exempel:
        delar.append(
            "Så här har vi svarat tidigare. Härma TONEN, inte innehållet.\n"
        )
        for i, par in enumerate(exempel, start=1):
            delar.append(
                f"EXEMPEL {i}\n"
                f"Kund: {par['inkommande_text'].strip()}\n"
                f"Vi: {par['utgaende_text'].strip()}\n"
            )

    delar.append(_underlag(forfragan))
    delar.append(
        "MAILET SOM SKA BESVARAS:\n"
        f"{forfragan.text.strip()}\n\n"
        "Skriv vårt svar. Bara svarets text, ingen hälsningsfras om avsändare."
    )
    return "\n".join(delar)


def _bedomning(forfragan: Forfragan) -> str:
    """Bedömningsraden, med fyra lägen i stället för två.

    **DET TREDJE LÄGET ÄR "INGEN BEDÖMNING GJORDES", och det saknades.** En
    kategori som inte gatas av fordonsuppslaget har inget utfall, och `None`
    föll då till samma text som ett MISSLYCKAT uppslag. Följden var att en
    rekondbokning fick svaret att vi inte kunnat slå upp fordonet. Fällt av
    kedjans provkörning i skiva 34.

    **DET FJÄRDE ÄR "MAILET BAR INGET NUMMER", och det är skiva 46 DEL B.** Samma
    defektform ett steg in: kvar i `uppslag=None` låg två lägen som betyder helt
    olika saker för kunden. Ärende 14 fick *"Vi har inte kunnat slå upp bilen i
    registret"* på ett mail som aldrig bar ett registreringsnummer, alltså ett
    besked om ett misslyckande som inte inträffat och ingen fråga efter det som
    faktiskt saknades. Se `Forfragan.regnr_i_mailet`.

    **VILLKORET BÄR `uppslag is None` OCKSÅ**, alltså inte bara flaggan. Kedjan
    kan inte ge ett lyckat uppslag utan ett nummer, men bedömningsraden ska säga
    vad som GÄLLER och inte vad en anropare lovat: finns ett uppslag är det
    uppslaget som är bedömningen, oavsett vad flaggan säger.
    """
    if not forfragan.uppslag_gjordes:
        return (
            "ingen fordonsbedömning behövs för den här kategorin. Svara på det "
            "kunden faktiskt frågar om."
        )
    if forfragan.uppslag is None and not forfragan.regnr_i_mailet:
        return SAKNAT_REGNR_BEDOMNING
    return _utfallstext(forfragan.utfall, forfragan.uppslag)


# VAD UNDERLAGET SÄGER OM ETT GATANDE FÄLT REGISTRET INTE BÄR. Skiva 55 DEL B
# punkt 3.
#
# **RADEN SÄGER VAD MODELLEN INTE VET, ALDRIG VAD REGISTRET SAKNAR.** Skillnaden
# är skiva 41:s VÄG TRE, och den är hela skälet till att den här raden är
# formulerad i första person. Skrev den *"registret saknar släpvagnsvikt"* vore
# det en inbjudan till exakt det påstående `pastaende-om-franvaro` fäller, alltså
# en prompt som beställer ett STOPPTECKEN. Se `docs/beslutslogg.md` #93.
FALT_VI_SAKNAR = {
    "tjanstevikt_kg": "tjänstevikt",
    "slapvagnsvikt_kg": "släpvagnsvikt",
    "draganordning": "draganordning",
}


def _uppslagsrad(u: Uppslag) -> str:
    """Uppslagets AVLÄSTA fält, och en order att tiga om de övriga.

    **RADEN SKREV FÖRUT ALLA TRE FÄLTEN OVILLKORLIGT.** Efter skiva 55 kan ett
    fält vara `None`, och en f-sträng hade då skrivit *"släpvagnsvikt None kg"*
    rakt in i prompten. Det är inte ett tal modellen kan citera, men det är en
    rad den läser som ett faktum om bilen.

    **DE AVLÄSTA SKRIVS UT, DE ÖVRIGA NAMNGES SOM ICKE-VETANDE.** Att tiga helt
    om ett saknat fält hade lämnat modellen att gissa om den får nämna det, och
    `_faktarader` och `_prisrader` bär redan samma val och samma skäl.

    **BARA DE TRE GATANDE FÄLTEN STÅR HÄR.** `kaross`, `fyrhjulsdrift`,
    `totalvikt`, `arsmodell` och `status` läses och bärs av `Uppslag`, men de når
    aldrig prompten: varje tal i prompten blir ett citerbart tal via
    `_tillatna_tal`, och inget av de fem svarar på något kunden frågat. De två
    som gatar talar i stället genom bedömningsraden och `_barlastrad`.
    """
    avlasta = []
    if u.tjanstevikt_kg is not None:
        avlasta.append(f"tjänstevikt {u.tjanstevikt_kg} kg")
    if u.slapvagnsvikt_kg is not None:
        avlasta.append(f"släpvagnsvikt {u.slapvagnsvikt_kg} kg")
    if u.draganordning is not None:
        avlasta.append(f"draganordning {'ja' if u.draganordning else 'nej'}")

    saknade = [ord_ for nyckel, ord_ in FALT_VI_SAKNAR.items()
               if getattr(u, nyckel) is None]

    rad = "Fordonsuppslag: " + (", ".join(avlasta) if avlasta
                                else "inga uppgifter alls")

    if not saknade:
        return rad + "."

    return (
        f"{rad}. VI HAR INGEN UPPGIFT OM {' och '.join(saknade).upper()} för "
        "den här bilen. Nämn inte det, varken som ett värde eller som något "
        "som saknas, och säg ALDRIG att uppslaget misslyckats: vi HAR slagit "
        "upp bilen och fått de uppgifter som står ovan."
    )


def _barlastrad(uppslag: Uppslag | None) -> str:
    """Vad prompten säger om barlastflaket. Skiva 55 DEL A gatingsregel 2.

    **RADEN SKRIVS BARA NÄR §39 BEVISLIGEN INTE GÄLLER.** `kraver_barlastflak`
    svarar `None` när registret inte räcker till, och då säger prompten
    ingenting: en order byggd på okunskap är ett påstående om bilen.

    **DEN UNDANTAR UPPRÄKNINGEN, INTE PRISET.** Promptens regel 15 kräver att
    priset skrivs, och `PRISFOT` att det återges ordagrant och i sin helhet.
    Prisradens värde är två led: ett belopp och en uppräkning av vad
    grundombyggnaden omfattar. För de här fordonen är uppräkningens `barlastflak`
    falskt, och raden säger därför uttryckligen att BELOPPET återges medan
    uppräkningen utelämnas.

    **DET ÄR ETT UNDANTAG FRÅN `PRISFOT` OCH INGET KRINGGÅENDE AV DEN.** Foten
    finns mot ett HALVT ÅTERGIVET INTERVALL, alltså mot att `från 20 000 till
    25 000 kr` blir `från 20 000 kr`, vilket skiva 44 mätte upp som ett annat
    prisbesked än filens. Beloppet står orört här; det som utelämnas är en
    uppräkning av arbetsmoment, och priset blir inte ett annat av att den saknas.

    **HÅLET LIGGER I `config/priser.json` OCH STÄNGS INTE HÄR.** Posten säger att
    grundombyggnaden omfattar barlastflak, vilket för de här fordonen är fel
    oavsett vad boten skriver. Att ändra posten är §10 och Lars beslut.
    """
    if uppslag is None:
        return ""

    if fordonsuppslag.kraver_barlastflak(uppslag) is not False:
        return ""

    return (
        "BARLASTFLAK: den här bilen omfattas INTE av barlastflakskravet. Skriv "
        "inte ordet barlastflak, och räkna inte upp vad grundombyggnaden "
        "omfattar. Priset skriver du ändå: återge BELOPPET ur prisraden "
        "ordagrant, båda gränserna, och hoppa över uppräkningen efter det."
    )


def _underlag(forfragan: Forfragan) -> str:
    """Vad modellen VET, utskrivet. Allt annat är påhitt och faller på spärren."""
    rader = [UNDERLAGSRUBRIK]
    rader.append(f"Kategori: {forfragan.kategori}")

    if not forfragan.uppslag_gjordes:
        # KATEGORIN GATAS INTE, alltså gjordes inget uppslag. Att skriva INGET
        # här hade varit sant men vilselett: modellen svarade då att vi inte
        # kunnat slå upp bilen, på en fråga som inte handlade om bilen.
        rader.append(
            "Fordonsuppslag: EJ AKTUELLT för den här kategorin. Nämn inte "
            "bilens uppgifter, och säg INTE att vi försökt slå upp något."
        )
    elif forfragan.uppslag is None and not forfragan.regnr_i_mailet:
        # MAILET BAR INGET NUMMER, alltså gjordes inget uppslag att misslyckas
        # med. Raden ovanför sade tidigare samma sak i båda lägena, och
        # bedömningsraden lade till att vi inte kunnat slå upp bilen. Se
        # `_bedomning` och `Forfragan.regnr_i_mailet`.
        rader.append(SAKNAT_REGNR_UNDERLAG)
    elif forfragan.uppslag is None:
        rader.append(
            "Fordonsuppslag: INGET. Du vet ingenting om kundens bil. Nämn inte "
            "tjänstevikt, släpvagnsvikt eller draganordning."
        )
    else:
        rader.append(_uppslagsrad(forfragan.uppslag))

    rader.append(f"Bedömning: {_bedomning(forfragan)}")
    rader.append(_barlastrad(forfragan.uppslag))
    # KATEGORIN VÄLJER PRISPOSTEN, skiva 52. Raden skrev tidigare hela
    # `config/priser.json`, se `priser_for`.
    rader.append(_prisrader(forfragan.kategori))
    # **BOKNINGSBESKEDET KOMMER NU VIA `_faktarader`**, alltså ur
    # `config/fakta.json`. Regel 8 förbjuder påståenden om vad Auto Stockholm
    # erbjuder UTÖVER underlaget, och att vi kan ta emot en bil är ett sådant
    # påstående. Regel 10 beordrar det. Motsägelsen är löst genom att beskedet
    # står i den §10-grindade källan, alltså där lucka 29 kräver att fakta om oss
    # bor. Lars beslut i skiva 37, lucka 43 stängd.
    rader.append(_faktarader())
    # `_barlastrad` ger tom sträng för varje fordon §39 kan gälla, alltså för de
    # flesta. En tom rad i underlaget är ingen instruktion, men den ser ut som en
    # avdelare och delar blocket på ett ställe som inte betyder något.
    return "\n".join(rad for rad in rader if rad)


def las_konfig(fil: Path) -> object:
    """En konfigurationsfils RÅA innehåll, eller `{}` om filen saknas.

    Filtrerar ingenting. Det gör `_varden_ur` och `las_konfigvarden`, som är de
    två som bär olika krav: sändvägens tal respektive promptens fakta.
    """
    if not fil.exists():
        return {}

    return json.loads(fil.read_text(encoding="utf-8"))


def las_konfigvarden(fil: Path) -> dict:
    """En konfigurationsfils VÄRDEN på toppnivå, utan kommentarer och tomma.

    Används av `_faktarader` för att skriva ut fakta i prompten, alltså för det
    modellen får LÄSA. Sändvägens tal går en annan väg, `_varden_ur`, som går
    ned genom hela strukturen. **De två har olika krav och ska inte slås ihop:**
    prompten vill ha namn och värde i par, spärren vill ha varje värde var det
    än ligger.

    **NYCKLAR SOM BÖRJAR MED `_` ÄR KOMMENTARER** och tas bort. JSON saknar
    kommentarssyntax, och filerna behöver förklara för Lars vad de betyder,
    eftersom han är den enda som får fylla dem (§10). En kommentar ska inte
    hamna i prompten som ett faktum om oss.

    *Här stod att kommentarernas tal annars blir TILLÅTNA TAL, med skiva 36:s
    mätning som belägg. Den historien tillhör `_varden_ur`: den här funktionen
    ligger inte på talspärrens väg och rör bara `config/fakta.json`. Ett
    påstående lånat från grannfunktionen. Fällt av §7-granskningen av skiva 36,
    varv 3.*

    **ETT TOMT VÄRDE ÄR INTE ETT VÄRDE.** Det utelämnas, alltså når det aldrig
    prompten och räknas aldrig som källa. Skillnaden mot att sakna nyckeln är
    noll med flit: §0:s ramverksregel 3 säger att ett tal läses ur källa eller
    utelämnas, och en tom sträng är inte en avläsning.

    **EN FIL MED GILTIG JSON AV FEL TYP GER TOMT**, i stället för
    `AttributeError`: en lista på toppnivån gör att inga fakta finns, vilket är
    den säkra riktningen.

    *Formuleringen sade först "en trasig konfigfil", vilket är bredare än koden.
    Syntaktiskt trasig JSON kastar fortfarande `JSONDecodeError` ur `las_konfig`
    och stoppar genereringen. Det är avsiktligt: en fil som inte går att tolka
    är ett driftfel som ska synas, inte ett tomt faktaunderlag. Fällt av
    §7-granskningen av skiva 36, varv 3.*

    **FILEN ÄR PLATT, OCH ETT NÄSTLAT VÄRDE UTELÄMNAS.** Lars beslut i skiva 42,
    lucka 53. Funktionen filtrerade `_`-nycklar bara på TOPPNIVÅN och körde sedan
    `str(v)` på vad som helst, alltså renderade en nästlad post hela sin repr i
    prompten med varje inre kommentar inbakad. Uppmätt med en prisfil där
    `a_traktor` var `{'_internt': 'kostar oss 9 000 kr', 'pris': '25 000 kr'}`:
    raden hamnade under rubriken *"Priser, avlästa ur config/priser.json"* och
    över foten *"Varje pris här återges ordagrant"*, alltså blev vårt INKÖPSPRIS
    ett citerbart pris.

    **TALETS HALVA VAR REDAN STÄNGD, TEXTENS INTE.** `_varden_ur` hindrar att
    9000 blir ett tillåtet tal, men ingenting hindrade att texten stod i
    prompten. Det är skillnaden mellan de två läsarna, och den var hålet.

    **ETT NÄSTLAT VÄRDE UTELÄMNAS I STÄLLET FÖR ATT KASTA**, av samma skäl som
    raden ovanför: en fil av fel form ska inte kunna tala, och utelämnandet är
    den säkra riktningen. Att filerna i repot FAKTISKT är platta binds separat,
    av `test_bada_konfigfilerna_i_repot_ar_PLATTA`.
    """
    data = las_konfig(fil)
    if not isinstance(data, dict):
        return {}

    return {n: v for n, v in data.items()
            if not str(n).startswith("_")
            and not isinstance(v, (dict, list, tuple))
            and str(v).strip()}


def las_fakta(faktafil: Path | None = None) -> dict:
    """`config/fakta.json`:s värden. Se `las_konfigvarden`."""
    return las_konfigvarden(faktafil or FAKTA)


# UNDERLAGETS RUBRIK. Egen konstant av samma skäl som faktablockets ram.
#
# **RADEN BAR SAMMA FALSKHET SOM `FAKTARUBRIK` FÄLLDES FÖR, och den stod kvar
# hundra rader upp i samma funktion.** Den löd *"Detta är allt du vet. Allt annat
# får du inte påstå."* `SYSTEM` kallar oss en fristående verkstad som bygger om
# bilar till a-traktor, regel 9 kallar oss en liten verkstad utan organisation,
# och få-exemplen är faktiska tidigare svar fulla av påståenden om oss. Modellen
# vet alltså mer än underlaget, och raden är dessutom den FÖRSTA den läser i
# blocket.
#
# **DEN VAR OCKSÅ VAKUÖS.** En lydelse som bad modellen påstå mer om oss
# passerade hela testfilen. `Priser: INGA` två rader ned var bunden; just den rad
# som bar falskheten var det inte. Fällt av §7-granskningen av skiva 37, varv 3.
UNDERLAGSRUBRIK = (
    "UNDERLAG. Det här är vad du vet om det HÄR ärendet. Fyll inte i något som "
    "saknas, och gissa aldrig ett värde.\n"
)

# DE TVÅ RADERNA FÖR ETT MAIL UTAN REGISTRERINGSNUMMER. Skiva 46 DEL B.
#
# **EGNA KONSTANTER AV SAMMA SKÄL SOM `UNDERLAGSRUBRIK` OCH `PRISFOT`: de är
# sändvägstext och ska gå att binda ORDAGRANT.** En lydelse som låter modellen
# påstå ett misslyckat uppslag ändå skulle annars passera ett test som bara söker
# en delsträng, vilket är lucka 25:s form.
#
# **BÅDA RADERNA BEHÖVS, och det är inte en upprepning.** `_underlag` säger vad
# LÄGET är, `_bedomning` säger vad SVARET ska göra åt det. Skiva 34:s tredje läge
# är byggt likadant, och skälet är detsamma: modellen läser bedömningsraden som
# sin instruktion och uppslagsraden som sitt faktum. Fanns bara den ena, så
# hämtade den andra sin text ur ett förval som säger något annat.
#
# **INGENDERA RADEN PÅSTÅR ATT MAILET SAKNAR ETT NUMMER, och det ledet är fällt
# fram.** En första lydelse sade *"Mailet bär inget registreringsnummer"* och
# beordrade ovillkorligt *"BE KUNDEN SKICKA REGISTRERINGSNUMRET"*. Vad vi
# faktiskt vet är att VI inte har något nummer, alltså att extraktionen inte gav
# något, och den är snävare än verkligheten: mönstret söker inte i ämnesraden
# och täcker inte varje skrivform. Se LUCKA 62 i `docs/sparrar.md`.
#
# Följden av den gamla lydelsen var att en missad extraktion blev en ORDER att
# fråga efter ett nummer som står i mailet, alltså precis det promptens regel 11
# förbjuder. Raderna säger nu vad vi vet och lämnar frågan villkorad av vad
# modellen läser i mailet. Fällt av §7-granskningen av skiva 46.
SAKNAT_REGNR_UNDERLAG = (
    "Fordonsuppslag: INGET UPPSLAG GJORDES. Vi har inget registreringsnummer "
    "för det här ärendet, alltså har vi aldrig försökt slå upp bilen och "
    "ingenting har misslyckats. Nämn inte tjänstevikt, släpvagnsvikt eller "
    "draganordning."
)

SAKNAT_REGNR_BEDOMNING = (
    "vi har inget registreringsnummer att gå på, alltså har vi inte bedömt "
    "bilen. Säg ALDRIG att ett uppslag misslyckats, att vi inte kunnat hitta "
    "bilen eller att vi inte kunnat slå upp den: vi har inte försökt. Skriv "
    "ingenting om bilens uppgifter. Står registreringsnumret inte i mailet: "
    "BE KUNDEN SKICKA DET så tittar vi på bilen. Står det där: läs det ur "
    "mailet och fråga inte efter det."
)

# FAKTABLOCKETS RAM, som egna konstanter för att gå att binda ORDAGRANT.
#
# **RUBRIKEN ÄR SÄNDVÄGSTEXT OCH VAR OBUNDEN.** En lydelse som uttryckligen bad
# modellen hitta på mer om oss passerade hela sviten, eftersom testet bara sökte
# efter delsträngen `Fakta om oss`. Det är samma hål som lucka 25 stängde för
# `SYSTEM`, flyttat ett lager. Fällt av §7-granskningen av skiva 37, varv 2.
#
# **RUBRIKEN SÄGER INTE "det ENDA du vet om oss", och det ledet var falskt.**
# `SYSTEM` kallar oss en fristående verkstad i Stockholm som bygger om bilar till
# a-traktor, regel 9 säger att vi är en liten verkstad utan organisation, och
# få-exemplen är faktiska tidigare svar fulla av påståenden om oss. Rubriken
# säger i stället vad som gäller för TILLÄGG.
FAKTARUBRIK = (
    "Fakta om oss, avlästa ur config/fakta.json. Utöver det som redan står i "
    "reglerna ovan får du inte påstå något om Auto Stockholm som inte står "
    "här:\n"
)

FAKTAFOT = "Varje TAL här återges ordagrant och ändras aldrig.\n"

# PRISBLOCKETS RAM, egna konstanter av samma skäl som faktablockets: raden är
# sändvägstext och ska gå att binda ORDAGRANT. En lydelse som bad modellen
# uppskatta ett pris skulle annars passera ett test som bara söker delsträngen.
PRISRUBRIK = (
    "Priser, avlästa ur config/priser.json. Du har inga andra priser, och du "
    "uppskattar aldrig ett pris som inte står här:\n"
)

# **HELHETSKRAVET ÄR LARS BESLUT I SKIVA 44, och det kom ur ett läst utkast.**
# Foten sade bara ORDAGRANT, och boten skrev *"priser för konvertering till
# A-traktor startar från 20 000 kr"* om en post vars värde är
# `från 20 000 till 25 000 kr ...`. Varje tal i den meningen hade en källa,
# alltså fällde ingen spärr, men kunden läser 20 000 som priset. Ett halvt
# återgivet intervall är ett annat prisbesked än det filen bär.
#
# **REGELN ÄR HELHET, inte en uppräkning av vad man inte får stryka.** Ett pris
# ur `config/priser.json` återges i sin helhet eller inte alls. Foten är
# sändvägstext och binds ORDAGRANT av `test_prisblockets_ram_star_ORDAGRANT`, av
# samma skäl som rubriken: en lydelse som bara sade "ordagrant" passerade ett
# test som söker en delsträng.
PRISFOT = (
    "Varje pris här återges ORDAGRANT och ändras aldrig, och det återges i SIN "
    "HELHET eller inte alls. Är priset ett intervall skriver du båda gränserna. "
    "Plocka aldrig ut en del av en prisrad, och gör aldrig om ett pris till ett "
    "ungefärligt.\n"
)

# BESKEDET NÄR FILEN ÄR TOM. Ordagrant den rad som stod hårdkodad före skiva 41,
# eftersom den var bunden och fungerade: den säger rakt ut att inga priser finns.
INGA_PRISER = "Priser: INGA. Du har inga prisuppgifter alls."


# VILKEN PRISPOST SOM HÖR TILL VILKEN KATEGORI. Lars beslut i skiva 52.
#
# **POSTEN HÖR TILL TJÄNSTEN, och varje kategori som handlar om den tjänsten
# pekar på den.** `config/priser.json`:s `_nycklarna` säger att nycklarna är
# namngivna efter taxonomins `fråga om pris`-kategorier, och det är sant om
# NAMNEN. Det gör dem inte till en fullständig karta: `boka a-traktorkonvertering`
# och `fråga om a-traktorkonvertering` handlar om samma tjänst som
# `fråga om pris a-traktorkonvertering` och ska bära samma prispost. En karta
# byggd på enbart namnlikhet hade tystat prisraden i två av kedjans tre
# kategorier, och de sex utkasten i `data/granskningsfall.jsonl` hade inte
# kunnat citera priset.
#
# **EN KATEGORI SOM INTE STÅR HÄR FÅR INGEN PRISPOST ALLS**, alltså `INGA_PRISER`
# i prompten och noll prisbelagda tal i spärrarna. Det är den säkra riktningen:
# ett svar som ändå nämner ett pris faller och blir ett utkast Lars läser.
#
# **`boka biltvätt` OCH `boka bromskontroll` STÅR MED FLIT INTE HÄR.** Posten
# `rekond` bär tvättpriser och `reparation` bär bromspriser, men att de två
# kategorierna prissätts ur just de posterna är ett antagande om verkstadens
# uppdelning, inte något filen säger. §10 gör den kopplingen till Lars beslut.
#
# Kartan binds mot båda sina ändar av
# `test_prisnyckelkartan_pekar_bara_pa_verkliga_namn`: varje kategori ska stå i
# `data/taxonomi.json` och varje nyckel i `config/priser.json`.
PRISNYCKEL_FOR_KATEGORI = {
    "fråga om pris a-traktorkonvertering": "a_traktorkonvertering",
    "fråga om a-traktorkonvertering": "a_traktorkonvertering",
    "boka a-traktorkonvertering": "a_traktorkonvertering",
    "fråga om pris rekond": "rekond",
    "boka rekond": "rekond",
    "fråga om pris service": "service",
    "boka service": "service",
    "fråga om pris reparation": "reparation",
    "boka reparation": "reparation",
    "fråga om pris däck": "dack",
    "boka däckbyte": "dack",
    "fråga om pris tillbehör": "tillbehor",
    "boka tillbehörsmontage": "tillbehor",
}


def priser_for(kategori: str, prisfil: Path | None = None) -> dict:
    """Prisposten ärendets EGEN kategori får nämna. Tom dict när ingen finns.

    **DEN HÄR FUNKTIONEN ÄR SÄNDVÄG.** Den är enda källan till priser för både
    prompten och de tre prisspärrarna, alltså avgör den vilka prisbelopp boten
    får skriva i ett kundmail.

    **HÅLET DEN STÄNGER, Lars beslut i skiva 52.** `_prisrader` skrev in HELA
    `config/priser.json` i varje prompt, och `las_priser().values()` var tillåtna
    källor för prisspärrarna, i båda fallen oberoende av kategori. Följden var att
    ett a-traktorsvar kunde skriva *"en stor service kostar 4 650 kr"* och passera
    varje spärr, eftersom talet står i filen. Det är ett prisbesked om en tjänst
    ärendet inte gäller, och §0:s ramverksregel 3 säger att ett pris kommer ur
    `config/priser.json` — inte att vilket pris som helst ur filen duger till
    vilken fråga som helst.

    **ÄNDRINGEN TAR BORT EN MÖJLIGHET, INTE ETT OBSERVERAT FEL.** Mätt i skiva 52
    mot `data/granskningsfall.jsonl` och `data/par.jsonl`: noll av botens sex
    utkast bär ett tal ur en annan kategoris prispost, och vändningsmätningen över
    båda materialen gav 0 av 6 respektive 3 av 222, där två av de tre är
    `inget kundärende` och `oklart` och aldrig får ett utkast. Hålet var alltså
    teoretiskt i det material som finns. Det stängs ändå: en prompt ska inte bära
    priser för tjänster ärendet inte gäller, oavsett om modellen råkat använda
    dem. Talen står i `docs/beslutslogg.md` #118.

    **ETT TOMT VÄRDE GER TOM DICT**, inte en post med tomt värde. Samma regel som
    `las_konfigvarden`: en tom sträng är ingen avläsning. `tillbehor` är tom i dag,
    alltså får `fråga om pris tillbehör` ingen prispost trots att kartan pekar.
    """
    nyckel = PRISNYCKEL_FOR_KATEGORI.get(kategori)
    if nyckel is None:
        return {}

    varde = las_priser(prisfil).get(nyckel)
    return {nyckel: varde} if varde else {}


def las_priser(prisfil: Path | None = None) -> dict:
    """`config/priser.json`:s värden. Se `las_konfigvarden`.

    Ett TOMT värde utelämnas, alltså når det aldrig prompten och räknas aldrig
    som källa. En ofylld nyckel kostar ingenting, vilket är hela skälet till att
    filen kan skapas med varje post tom.
    """
    return las_konfigvarden(prisfil or PRISER)


def _prisrader(kategori: str, prisfil: Path | None = None) -> str:
    """Priser som FÅR nämnas för `kategori`, eller beskedet att inga finns.

    **BESKEDET SKRIVS UT I BÅDA FALLEN**, av samma skäl som `_faktarader`: att
    tiga när filen är tom hade lämnat modellen att gissa om den får nämna ett
    pris.

    **PROMPTEN BÄR BARA ÄRENDETS EGEN POST, Lars beslut i skiva 52.** Funktionen
    skrev tidigare ut HELA `config/priser.json` oberoende av kategori, alltså
    fick varje a-traktorprompt posterna `rekond`, `reparation`, `service` och
    `dack` med sig. Se `priser_for` för hålet och för mätningen.

    **FILEN FINNS SEDAN SKIVA 41 OCH ÄR FYLLD SEDAN SKIVA 44.** Lars §10-beslut
    båda gångerna. Åtta av nio spärrade svar i skiva 40:s mätning föll på att
    svaret nämner ett pris medan filen inte fanns, se `docs/beslutslogg.md` #90.
    Fem av sex poster bär i dag ett pris. `tillbehor` står tom, alltså utelämnas
    den och är ingen källa.

    **`INGA_PRISER` NÅS NU AV VARJE KATEGORI UTAN EGEN POST**, och det är de
    flesta: 15 av taxonomins 28 står inte i `PRISNYCKEL_FOR_KATEGORI`. Före
    skiva 52 krävdes att HELA filen tömdes. Raden säger rakt ut att inga priser
    finns, vilket är sant för den kategorin, och den är därmed det säkra
    utfallet: modellen lämnas inte att gissa.
    """
    priser = priser_for(kategori, prisfil)
    if not priser:
        return INGA_PRISER

    rader = "\n".join(f"  {namn}: {varde}" for namn, varde in priser.items())
    return PRISRUBRIK + f"{rader}\n" + PRISFOT


def _faktarader(faktafil: Path | None = None) -> str:
    """Fakta om oss som FÅR nämnas, eller beskedet att inga finns.

    Raden skrivs ut i BÅDA fallen. Att tiga när filen är tom hade lämnat
    modellen att gissa om den får skriva ett telefonnummer, och den åttonde
    promptregeln säger att den inte får påstå något om oss utöver underlaget.
    Här står det uttryckligen.
    """
    fakta = las_fakta(faktafil)
    if not fakta:
        return (
            "Fakta om oss: INGA. Du har inget telefonnummer, inga öppettider "
            "och inga ledtider. Skriv 'ring oss' eller 'hör av dig' utan "
            "nummer, aldrig ett påhittat nummer.\n"
        )

    rader = "\n".join(f"  {namn}: {varde}" for namn, varde in fakta.items())
    return FAKTARUBRIK + f"{rader}\n" + FAKTAFOT


def _utfallstext(utfall: Utfall | None, uppslag: Uppslag | None) -> str:
    """Utfallet i ord, utan att avslöja tröskeln eller föreskriften.

    **PARAMETERN VAR `har_uppslag: bool` OCH ÄR NU UPPSLAGET SJÄLVT.** Skiva 55
    behöver veta mer än ATT ett uppslag finns: RÖTT har två skäl som inte får
    förväxlas, och OKLART har två lägen där bara det ena är ett nej. En `bool`
    kan inte bära den skillnaden, och ett andra booleskt argument hade blivit
    fyra kombinationer där bara tre finns.

    **PARAMETERN HAR INGET FÖRVAL, och det är samma skäl som `kor`:s `hamta` och
    `till_granskningsfall`:s `skarp` anger.** Ett förval hade valt en av de två
    RÖDA texterna åt den som glömmer argumentet, alltså bett om bilens egna
    siffror för en bil vi inte slagit upp, eller tigit om dem för en vi har.
    Utan förval kastar Python i stället, och det syns.

    **ATT SIFFROR FÅR BEGÄRAS STYRS AV ATT ETT UPPSLAG FINNS, och det ledet är
    fällt fram.**
    Första lydelsen bad ALLTID om bilens egna siffror vid RÖTT. Med
    `utfall=ROTT` och `uppslag=None` producerade `_underlag` då en prompt som i
    samma stycke förbjöd och beordrade viktangivelser:

        Fordonsuppslag: INGET. ... Nämn inte tjänstevikt, släpvagnsvikt ...
        Bedömning: ... SÄG DET SOM SKÄLET, med bilens egna siffror ...

    Varje lydigt svar fälldes sedan av `krav_pa_fordonsfakta_ur_uppslag`, alltså
    en garanterad falsk fällning. §7.1: en spärr som fäller önskade svar blir
    avstängd. Fällt av §7-granskningen av skiva 33, varv 1.

    **RÖTT SÄGER VARFÖR OCH VAD KUNDEN KAN GÖRA, och det är skiva 33:s ändring.**
    Skiva 31:s röda svar sade bara att bedömningen är negativ. Det lämnar kunden
    utan något att göra, och i det tomrummet hittade modellen på en resurs hos
    oss: tre av tjugo röda svar hänvisade till vad vår hemsida innehåller. Det
    var lucka 29. Åtgärden är att ge modellen något VERKLIGT att erbjuda i
    stället för en spärr som fäller påhittet i efterhand. Beslut av Lars.

    **SKÄLET NAMNGER BÅDA VILLKOREN, inte bara släpvagnsvikten.** `RÖTT` kräver
    att `fordonsuppslag.ar_lamplig_som_dragfordon` faller, och den bär TVÅ
    alternativa villkor förenade med ELLER. Ett svar som anger släpvagnsvikten
    som enda skäl gör en ofullständig föreskrift till ett besked, vilket är
    precis vad `troskeln-som-forfattningstext` finns för och vad skiva 12:s
    defekt bestod i. Siffrorna kommer ur uppslaget och är alltså avlästa.
    """
    har_uppslag = uppslag is not None

    rott_med_siffror = (
        "bilen ser inte ut att gå att bygga om, eftersom varken "
        "tjänstevikten eller släpvagnsvikten räcker till. SÄG DET SOM "
        "SKÄLET, med bilens egna siffror ur underlaget ovan, och skriv att "
        "kunden är välkommen att höra av sig med ett annat fordon så tittar "
        "vi på det. Hänvisa inte till något annat hos oss."
    )
    # UTAN UPPSLAG NÄMNS INGENTING OM BILEN, inte ens ordet vikt.
    #
    # Första rättelsen tog bort SIFFRORNA men lät orden `tjänstevikten` och
    # `släpvagnsvikten` stå kvar. Båda är `FORDONSORD`, alltså fälldes varje
    # lydigt svar ändå av `krav_pa_fordonsfakta_ur_uppslag`, och prompten
    # förbjöd och beordrade fortfarande samma sak. Rättelsen bar nästa fynd.
    # Fällt av §7-granskningen av skiva 33, varv 2.
    #
    # Utan uppslag VET vi inte varför, alltså ska svaret inte påstå ett skäl.
    rott_utan_siffror = (
        "bilen ser inte ut att gå att bygga om. Säg det, MEN UTAN att nämna "
        "något om bilen alls, eftersom du inte har några uppgifter om den, och "
        "skriv att kunden är välkommen att höra av sig med ett annat fordon så "
        "tittar vi på det. Hänvisa inte till något annat hos oss."
    )

    # **REDAN OMBYGGD ÄR ETT ANNAT RÖTT, skiva 55 DEL A regel 1.** Kunden ber om
    # en ombyggnad av något som registret säger redan är ombyggt.
    #
    # **SKÄLET FÅR INTE VARA VIKTERNAS.** `rott_med_siffror` säger att varken
    # tjänstevikten eller släpvagnsvikten räcker, och för det ombyggda fordon
    # som väger 2 005 kg är det FALSKT: vikten ligger över §42:s tröskel. RÖTT är
    # en helt annan orsak, och ett svar som angav vikten som skäl hade varit ett
    # påhittat fordonsfaktum av precis den klass §0:s ramverksregel 3 förbjuder.
    #
    # **INGA SIFFROR HÄR, och det är inte en glömska.** Vad kunden behöver veta
    # är att bilen redan är registrerad som ombyggd, inte vad den väger.
    rott_redan_ombyggd = (
        "REGISTRET SÄGER ATT BILEN REDAN ÄR OMBYGGD. Säg det vänligt och rakt: "
        "enligt registret är bilen redan registrerad som ombyggd, alltså finns "
        "det ingen grundombyggnad kvar att göra. Fråga om kunden vill något "
        "annat med bilen, eller om det gäller en annan bil, så tittar vi på "
        "den. Nämn ingenting om bilens vikter, och säg inte att den inte duger."
    )

    # **DEN ENDA SOM SAKNAS ÄR DRAGKROKEN. Skiva 55 DEL B punkt 2 och 4.**
    #
    # `OKLART` sade förut *"vi kan inte avgöra det på uppgifterna vi har"* i
    # BÅDA de lägen som nu skiljs åt, och det var falskt i det ena. För det
    # fyrhjulsdrivna fordonet är släpvagnsvikten avläst till 1 600 kg, alltså
    # är §42 andra stycket uppfyllt och det enda registret inte visar är en
    # dragkrok. Lars läste tre
    # sådana svar: de erbjöd en dragkrok utan att säga varför den hjälper.
    #
    # **SIFFRAN SKA MED, och den har en källa.** `_tillatna_tal` bär uppslagets
    # släpvagnsvikt, alltså faller svaret inte på talspärren.
    oklart_bara_dragkroken = (
        "BILEN DUGER SOM DRAGFORDON. Säg det som ett JA: släpvagnsvikten i "
        "registret räcker, och skriv ut talet ur underlaget ovan som skälet. "
        "Det enda registret inte visar är en dragkrok, så skriv i samma "
        "andetag att vi monterar en om det behövs. Be aldrig kunden ordna "
        "kroken själv, och gör inte dragkroken till ett villkor."
    )

    oklart_utan_besked = "vi kan inte avgöra det på uppgifterna vi har."

    if utfall is Utfall.ROTT and uppslag is not None \
            and fordonsuppslag.ar_redan_ombyggd(uppslag):
        return rott_redan_ombyggd

    if utfall is Utfall.OKLART and _bara_dragkroken_saknas(uppslag):
        return oklart_bara_dragkroken

    return {
        Utfall.GRONT: "bilen ser ut att gå att bygga om.",
        Utfall.GULT: "bilen kan gå att bygga om, men något behöver åtgärdas.",
        Utfall.OKLART: oklart_utan_besked,
        Utfall.ROTT: rott_med_siffror if har_uppslag else rott_utan_siffror,
    }.get(utfall, "vi har inte kunnat slå upp bilen.")


def _bara_dragkroken_saknas(uppslag: Uppslag | None) -> bool:
    """Är §42 andra stycket uppfyllt med ETT AVLÄST tal, och kroken det enda öppna?

    **BÅDA LEDEN BEHÖVS, och de fäller olika fordon.** Lämpligheten skiljer
    det fyrhjulsdrivna fordonet, vars släpvagnsvikt är avläst till 1 600 kg,
    från det vars sida inte bär någon släpvagnsvikt alls: båda blir `OKLART`, och
    bara det första är ett ja. Släpvagnsviktens avläsning skiljer i sin tur det
    fordonet från ett
    fordon som är lämpligt på TJÄNSTEVIKTEN, där talet att skriva ut vore ett
    annat och meningen om släpvagnsvikten falsk.

    **TREDJE LEDET ÄR ATT KROKEN FAKTISKT ÄR DET SOM SAKNAS.** Är
    `draganordning` avläst till `Nej` är det belagt, och `kedja.py` lägger då
    fältet i `franvaro_far_pastas`. Är den `None` vet vi ingenting om kroken, och
    då ska svaret varken påstå att den saknas eller erbjuda sig att montera en.
    """
    if uppslag is None:
        return False

    if uppslag.slapvagnsvikt_kg is None:
        return False

    if fordonsuppslag.ar_lamplig_som_dragfordon(uppslag) is not True:
        return False

    return uppslag.draganordning is False


# ------------------------------------------------------------------ DEL A


def generera_utkast(klient, forfragan: Forfragan, modell: str = MODELL,
                    exempel: list[dict] | None = None) -> str:
    """Ett svarsutkast, prövat mot varje spärr innan det returneras.

    **KASTAR `Sparrfalld` I STÄLLET FÖR ATT RETURNERA EN FÄLLD TEXT.** Anroparen
    får då ett utkast eller ett skäl, aldrig något däremellan, och kan inte råka
    använda en text som inte höll.
    """
    text = generera_ratext(klient, forfragan, modell, exempel)
    krav_pa_svaret(text, forfragan)
    return text


def generera_ratext(klient, forfragan: Forfragan, modell: str = MODELL,
                    exempel: list[dict] | None = None) -> str:
    """Modellens text FÖRE spärrarna. Enbart för MÄTNING.

    **DEN HÄR VÄGEN FÅR ALDRIG NÅ ETT UTKAST SOM VISAS ELLER SKICKAS.** Den
    finns därför att en mätning av hur ofta en spärr fäller ett ÖNSKAT svar
    måste kunna läsa texten spärren fällde, och `Sparrfalld` bär bara ett skäl.
    `generera_utkast` är den enda väg som lämnar ut en text, och den prövar
    alltid `krav_pa_svaret` först.

    Kravet i skiva 32 DEL D är att lucka 28:s frekvens mäts INNAN `FORDONSORD`
    ändras, och utan råtexten går den mätningen inte att göra.
    """
    exempel = las_exempel() if exempel is None else exempel

    svar = klient.messages.create(
        model=modell,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": bygg_prompt(forfragan, exempel)}],
    )

    return "".join(b.text for b in svar.content if b.type == "text").strip()
