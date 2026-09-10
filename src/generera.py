"""Generatorn: boten skriver ett SVARSUTKAST på en a-traktorförfrågan.

**UT KOMMER ETT UTKAST, ALDRIG ETT SKICKAT MAIL.** Modulen har ingen sändväg, och
det är prövat och inte antaget: `src/vy.py::krav_pa_sandvagsfrihet` går över
importgrafen och källtexten, och `tests/test_generera.py` kör den mot den här
modulen. Samma spärr som vyn har, samma två lager.

**DET HÄR ÄR SÄNDVÄG enligt CLAUDE.md §7.** Modulen avgör med vilket INNEHÅLL ett
mail lämnar servern den dag fas 7 kopplar in sändningen. Tre granskningsvarv,
ovillkorligt.

SPÄRRARNA PÅ DET GENERERADE, var och en med sin negativkontroll:

  `tomt-svar`                    Ett svar som är tomt efter `.strip()` är inget
                                 utkast. De andra SÖKER EFTER SAKER och släppte
                                 därför igenom det tomma.
  `genererat-tal-har-kalla`      Ett tal i svaret ska komma ur uppslaget eller ur
                                 config. Priser finns inte än, alltså faller ett
                                 svar som nämner ett pris i känd form.
  `genererat-fordonsfaktum`      Ett fordonsfaktum kräver ett LYCKAT uppslag.
                                 Kopplar `fordonsfakta-ur-uppslag` uppströms.
  `troskeln-som-forfattningstext` Tröskeln 1 000 kg får inte återges som en
                                 sammanfattad föreskrift.

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

from src.fordonsuppslag import Uppslag, Utfall

ROT = Path(__file__).resolve().parent.parent
PAR = ROT / "data" / "par.jsonl"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
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


# ------------------------------------------------------------------ DEL C


# TAL SOM ALLTID FÅR STÅ I ETT SVAR, oavsett uppslag.
#
# `1` och `2` slinker igenom som ordningstal och som "en till två veckor", och
# ett årtal är inte ett påstående om pris eller vikt. Listan är en UNDANTAGSLISTA
# och hålls kort med flit: varje tillägg är ett hål i spärren.
ALLTID_TILLATNA_TAL = frozenset({"1", "2", "3"})

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

    **PRISER FINNS INTE ÄN.** `config/priser.json` existerar inte, alltså bidrar
    den med noll tal, och det är avsiktligt: ett svar som nämner ett pris ska
    falla tills filen finns och är fylld av Lars.

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
    for fil in (PRISER, FAKTA):
        for varde in _varden_ur(las_konfig(fil)):
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
    """
    if PRISORD.search(svar):
        raise Sparrfalld(
            "genererat-tal-har-kalla",
            "svaret nämner ett pris, och config/priser.json finns inte",
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


def krav_pa_fordonsfakta_ur_uppslag(svar: str, forfragan: Forfragan) -> None:
    """SPÄRR: ett fordonsfaktum kräver ett LYCKAT uppslag.

    Kopplar `fordonsfakta-ur-uppslag` uppströms: den spärren vaktar att ett
    uppslag är helt, den här att svaret inte påstår fordonsfakta när inget
    uppslag finns.
    """
    traff = FORDONSORD.search(svar)
    if traff and forfragan.uppslag is None:
        raise Sparrfalld(
            "genererat-fordonsfaktum",
            f"svaret nämner {traff.group(0).lower()} utan ett lyckat uppslag",
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


def krav_pa_ett_svar(svar: str) -> None:
    """SPÄRR: ett tomt svar är inget utkast.

    **DE TRE ANDRA SPÄRRARNA SÖKER EFTER SAKER, alltså släpper alla tre igenom
    en tom sträng.** Följden var att ett tomt modellsvar blev ett godkänt
    utkast: `blev_utkast` sant, `forslag` tomt, ingen spärr angiven. I vyn blev
    det ett tomt textfält som gick att omdöma, och ett `forbattra` hade skrivit
    ett par med en tom förlaga till `data/par.jsonl`, som generatorn läser som
    få-exempel.

    Uppmätt som en möjlig väg av §7-granskningen av skiva 34, varv 2.
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
    krav_pa_att_troskeln_inte_ar_forfattningstext(svar)


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


# BOKNINGSBESKEDET, som promptregel 10 vilar på. Står som egen konstant för att
# gå att binda ORDAGRANT, precis som `SYSTEM`. En ordlista över förbjudna ord
# fångar de ord någon råkade tänka på; en likhet fångar varje ändring.
#
# **DET HÄR ÄR ETT PÅSTÅENDE OM AUTO STOCKHOLM, och rätt hemvist är
# `config/fakta.json`.** Att det står här och inte där är en känd avvikelse, se
# LUCKA 43 i `docs/sparrar.md`: filen är ett §10-stopp och Lars order gällde att
# SKAPA den, inte att fylla den. Att flytta raden dit är hans beslut.
BOKNINGSBESKED = (
    "Bokningar: vi tar emot bokningar löpande och kommer överens om tid "
    "med kunden. Du får bekräfta att det går att lösa. Du får INTE ange "
    "någon tid, vecka, månad eller ledtid: den bestäms i kontakten."
)

SYSTEM = """Du skriver svarsutkast åt Auto Stockholm, en fristående verkstad i \
Stockholm som bygger om bilar till a-traktor.

DU SKRIVER ETT UTKAST. En människa läser det innan det går ut.

REGLER SOM ALDRIG BRYTS:

1. Första person plural. Vi, oss, vår, våra. Aldrig jag, mig, min, eller man.
2. Inga tankstreck eller bindestreck som skiljetecken. Komma, punkt, kolon, \
eller skriv om meningen.
3. Skriv aldrig "friverkstad". Skriv "fristående verkstad".
4. Nämn aldrig en konkurrent.
5. ALDRIG ETT PRIS. Inte ett belopp, inte ett ungefärligt pris, inte "ring för \
offert". Om kunden frågar vad det kostar: säg att VI återkommer med prisuppgift.
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
sig så bestämmer vi tid. Hänvisa inte vidare och be dem inte återkomma senare.
11. FRÅGA ALDRIG EFTER UPPGIFTER SOM REDAN STÅR I MAILET. Läs mailet först. \
Står registreringsnumret där, fråga inte efter det. Frågan är rimlig bara när \
uppgiften saknas.

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
    """Bedömningsraden, med tre lägen i stället för två.

    **DET TREDJE LÄGET ÄR "INGEN BEDÖMNING GJORDES", och det saknades.** En
    kategori som inte gatas av fordonsuppslaget har inget utfall, och `None`
    föll då till samma text som ett MISSLYCKAT uppslag. Följden var att en
    rekondbokning fick svaret att vi inte kunnat slå upp fordonet. Fällt av
    kedjans provkörning i skiva 34.
    """
    if not forfragan.uppslag_gjordes:
        return (
            "ingen fordonsbedömning behövs för den här kategorin. Svara på det "
            "kunden faktiskt frågar om."
        )
    return _utfallstext(forfragan.utfall, forfragan.uppslag is not None)


def _underlag(forfragan: Forfragan) -> str:
    """Vad modellen VET, utskrivet. Allt annat är påhitt och faller på spärren."""
    rader = ["UNDERLAG. Detta är allt du vet. Allt annat får du inte påstå.\n"]
    rader.append(f"Kategori: {forfragan.kategori}")

    if not forfragan.uppslag_gjordes:
        # KATEGORIN GATAS INTE, alltså gjordes inget uppslag. Att skriva INGET
        # här hade varit sant men vilselett: modellen svarade då att vi inte
        # kunnat slå upp bilen, på en fråga som inte handlade om bilen.
        rader.append(
            "Fordonsuppslag: EJ AKTUELLT för den här kategorin. Nämn inte "
            "bilens uppgifter, och säg INTE att vi försökt slå upp något."
        )
    elif forfragan.uppslag is None:
        rader.append(
            "Fordonsuppslag: INGET. Du vet ingenting om kundens bil. Nämn inte "
            "tjänstevikt, släpvagnsvikt eller draganordning."
        )
    else:
        u = forfragan.uppslag
        rader.append(
            f"Fordonsuppslag: tjänstevikt {u.tjanstevikt_kg} kg, "
            f"släpvagnsvikt {u.slapvagnsvikt_kg} kg, "
            f"draganordning {'ja' if u.draganordning else 'nej'}."
        )

    rader.append(f"Bedömning: {_bedomning(forfragan)}")
    rader.append("Priser: INGA. Du har inga prisuppgifter alls.")
    # **BOKNINGSBESKEDET STÅR I UNDERLAGET, inte bara i regel 10.** Regel 8
    # förbjuder påståenden om vad Auto Stockholm erbjuder UTÖVER underlaget, och
    # att vi kan ta emot en bil i juni är ett sådant påstående. Regel 10 beordrar
    # det. Motsägelsen löses genom att beskedet blir UNDERLAG, alltså något
    # modellen VET, i stället för att två regler drar åt olika håll.
    #
    # Raden lovar en ÖVERENSKOMMELSE och FÖRBJUDER uttryckligen en tidsangivelse.
    # Fällt av §7-granskningen av skiva 36, varv 1.
    #
    # *Här stod "ingen månad, ingen vecka och inget datum står här". Orden står
    # bokstavligen i `BOKNINGSBESKED`, i förbudsledet. Meningen rättades i
    # `docs/beslutslogg.md` #73 medan den stod kvar HÄR, alltså i sändvägskoden,
    # känt falsk. Fällt av §7-granskningen av skiva 36, varv 3.*
    rader.append(BOKNINGSBESKED)
    rader.append(_faktarader())
    return "\n".join(rader)


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
    """
    data = las_konfig(fil)
    if not isinstance(data, dict):
        return {}

    return {n: v for n, v in data.items()
            if not str(n).startswith("_") and str(v).strip()}


def las_fakta(faktafil: Path | None = None) -> dict:
    """`config/fakta.json`:s värden. Se `las_konfigvarden`."""
    return las_konfigvarden(faktafil or FAKTA)


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
    return (
        "Fakta om oss, avlästa ur config/fakta.json. Dessa FÅR du skriva, "
        f"ordagrant och oförändrade:\n{rader}\n"
    )


def _utfallstext(utfall: Utfall | None, har_uppslag: bool = True) -> str:
    """Utfallet i ord, utan att avslöja tröskeln eller föreskriften.

    **`har_uppslag` STYR OM SIFFROR FÅR BEGÄRAS, och det ledet är fällt fram.**
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

    return {
        Utfall.GRONT: "bilen ser ut att gå att bygga om.",
        Utfall.GULT: "bilen kan gå att bygga om, men något behöver åtgärdas.",
        Utfall.OKLART: "vi kan inte avgöra det på uppgifterna vi har.",
        Utfall.ROTT: rott_med_siffror if har_uppslag else rott_utan_siffror,
    }.get(utfall, "vi har inte kunnat slå upp bilen.")


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
