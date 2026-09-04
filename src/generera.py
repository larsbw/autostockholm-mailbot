"""Generatorn: boten skriver ett SVARSUTKAST på en a-traktorförfrågan.

**UT KOMMER ETT UTKAST, ALDRIG ETT SKICKAT MAIL.** Modulen har ingen sändväg, och
det är prövat och inte antaget: `src/vy.py::krav_pa_sandvagsfrihet` går över
importgrafen och källtexten, och `tests/test_generera.py` kör den mot den här
modulen. Samma spärr som vyn har, samma två lager.

**DET HÄR ÄR SÄNDVÄG enligt CLAUDE.md §7.** Modulen avgör med vilket INNEHÅLL ett
mail lämnar servern den dag fas 7 kopplar in sändningen. Tre granskningsvarv,
ovillkorligt.

SPÄRRARNA PÅ DET GENERERADE, tre stycken, var och en med sin negativkontroll:

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
    """

    text: str
    kategori: str
    utfall: Utfall | None
    uppslag: Uppslag | None = None


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
PRISORD = re.compile(
    r"\b(kr|kronor|sek|kostar|kostnad|kostnaden|pris|priset|priser|"
    r"offert|avgift|spänn|spann|peng|pengar|"
    r"inkl\.?\s*moms|exkl\.?\s*moms)\b|\btkr\b|\d\s*tkr",
    flags=re.IGNORECASE,
)

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
FORDONSORD = re.compile(
    r"tjänstevikt|tjanstevikt|släpvagnsvikt|slapvagnsvikt|draganordning|"
    r"dragkrok|totalvikt|\bväger\b|\bvager\b|\bvikten\b|\bkrok\b|"
    r"\bsläp\b|\bslap\b|\bsläpet\b|\btung\b|\btyngd\b",
    flags=re.IGNORECASE,
)

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
TROSKELTAL = re.compile(
    r"1[\s.]?000|\bettusen\b|\btusen\w*\s*(kilo(?:gram|n)?|kg)\b|"
    r"\b1\s*ton\b|\bett\s+ton\b",
    flags=re.IGNORECASE,
)

# FÖRFATTNINGSORDEN, EN TERM PER RAD.
#
# **UPPDELNINGEN I EN TUPEL ÄR INTE KOSMETIK.** Mönstret har rättats i fyra
# granskningsvarv, och VARJE gång har rättelsen tappat eller fällt något den
# inte skulle. Senast försvann `kräv` och `regeln` när hela regexen skrevs om i
# ett svep, och regressionstabellen fångade det inte: varje rad som bar
# "kräver" bar också "Lagen", som fälldes av ett annat led.
#
# Termerna står därför var för sig, och `test_varje_forfattningsterm_ar_ISOLERAD`
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
    r"\bkräv\w*",
    r"föreskrift\w*",
    r"foreskrift\w*",
    r"bestämmels\w*",
    r"bestammels\w*",
    r"paragraf\w*",
    r"lagstiftning\w*",
    r"reglement\w*",
    # `regler` MED SINA EGNA BÖJNINGAR OCH INGA ANDRA. Substantivet `regler`
    # delar sträng både med verbet `reglera` och med sammansättningar där
    # `regler` är FÖRSTA ledet: termostaten REGLERAR, tomgången REGLERAS,
    # dragkroken är REGLERBAR, och REGLERVENTILEN sitter på motorn. Alla fyra
    # är verkstadsord. Substantivets egna former är `regler`, `reglerna`,
    # `reglering(en)` och `reglers`, alltså räcker det att kräva att ordet SLUTAR
    # där böjningen slutar.
    r"regler(?:na|ing\w*|s)?\b",
    # `regel` behåller sin HÖGERgräns, som `regelbundet` gjorde lastbärande.
    r"regel\b",
    r"regeln\b",
    # `lag` ÄR GENUINT TVETYDIGT och behåller därför båda gränserna. `lager`,
    # `underlag`, `uppslaget` och `lagt` fälldes av en gränslös lydelse. Värst av
    # alla är `lagar`: en verkstad LAGAR bilar. Bara den bestämda pluralformen
    # är säker.
    r"\blag\b",
    r"\blagen\b",
    r"\blagarna\b",
    r"\blagtext\w*",
    r"\bvvfs\b",
    r"§",
    r"\bmåste\b",
    r"\bmaste\b",
    r"\btrafikverket\b",
    r"\btransportstyrelsen\b",
)

FORFATTNINGSORD = re.compile("|".join(FORFATTNINGSTERMER), flags=re.IGNORECASE)


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
    """
    tillatna = set(ALLTID_TILLATNA_TAL)

    if forfragan.uppslag is not None:
        tillatna.add(str(forfragan.uppslag.tjanstevikt_kg))
        tillatna.add(str(forfragan.uppslag.slapvagnsvikt_kg))

    for fil in (PRISER, FAKTA):
        if fil.exists():
            data = json.loads(fil.read_text(encoding="utf-8"))
            tillatna.update(_tal_i(json.dumps(data, ensure_ascii=False)))

    return tillatna


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


def krav_pa_svaret(svar: str, forfragan: Forfragan) -> None:
    """Alla tre spärrarna, i tur och ordning.

    **VAR OCH EN FÄLLER FÖR SIG.** Testen fäller dem en i taget och aldrig i par:
    skiva 27 mätte att en sammanslagen fällning ger RÖD och därmed falskt ÄKTA,
    alltså ett belägg för att båda bär när bara den ena gör det.
    """
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
offert". Om kunden frågar vad det kostar: säg att en kollega återkommer med \
prisuppgift.
6. ALDRIG ETT TAL som inte står i underlaget nedan. Inga vikter, inga ledtider, \
inga antal du inte fått.
7. Återge aldrig en lagtext eller en föreskrift sammanfattad. Säg inte att något \
är ett krav enligt lag.

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


def _underlag(forfragan: Forfragan) -> str:
    """Vad modellen VET, utskrivet. Allt annat är påhitt och faller på spärren."""
    rader = ["UNDERLAG. Detta är allt du vet. Allt annat får du inte påstå.\n"]
    rader.append(f"Kategori: {forfragan.kategori}")

    if forfragan.uppslag is None:
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

    rader.append(f"Bedömning: {_utfallstext(forfragan.utfall)}")
    rader.append("Priser: INGA. Du har inga prisuppgifter alls.\n")
    return "\n".join(rader)


def _utfallstext(utfall: Utfall | None) -> str:
    """Utfallet i ord, utan att avslöja tröskeln eller föreskriften."""
    return {
        Utfall.GRONT: "bilen ser ut att gå att bygga om.",
        Utfall.GULT: "bilen kan gå att bygga om, men något behöver åtgärdas.",
        Utfall.OKLART: "vi kan inte avgöra det på uppgifterna vi har.",
        Utfall.ROTT: "bilen ser inte ut att gå att bygga om.",
    }.get(utfall, "vi har inte kunnat slå upp bilen.")


# ------------------------------------------------------------------ DEL A


def generera_utkast(klient, forfragan: Forfragan, modell: str = MODELL,
                    exempel: list[dict] | None = None) -> str:
    """Ett svarsutkast, prövat mot alla tre spärrarna innan det returneras.

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
