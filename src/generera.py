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
TAL_I_TEXT = re.compile(r"\d+(?:[\s.]\d{3})*")

# ORD SOM GÖR ETT SVAR TILL ETT PRISBESKED. Priser finns inte i config än,
# alltså faller ett svar som nämner ett pris i någon av formerna nedan. Ordet
# VARJE står inte här: uppräkningen är inte uttömmande, se lucka 20.
#
# **`totalt` OCH `summa` ÄR BORTTAGNA.** De är vanlig prosa: "vi tittar totalt
# igenom bilen" fälldes som pris. En spärr som fäller på vanliga ord blir
# avstängd, vilket §7.1 varnar för.
#
# **TILLAGT: prisord i ORD i stället för siffror.** "tjugofemtusen", "femton
# hundra spänn", "en billig peng". Uppräkningen är INTE uttömmande och luckan är
# registrerad i `docs/sparrar.md`: en modell kan omskriva ett pris utan något av
# orden. Systemprompten är det som bär i det fallet.
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
TROSKELTAL = re.compile(
    r"1[\s.]?000|\bettusen\b|\btusen\s*(kilo|kg)\b|\b1\s*ton\b|\bett\s+ton\b",
    flags=re.IGNORECASE,
)

# ORDGRÄNS TILL VÄNSTER, FRI SUFFIX TILL HÖGER. Båda leden är fällda fram.
#
# Varv 1 krävde ordgräns i BÅDA ändar och släppte igenom "Kravet", "Lagkravet",
# "Föreskriften" och "Paragrafen", alltså de former ett svar naturligt tar.
#
# Varv 1:s rättelse tog bort ordgränsen HELT, och bytte därmed en falsk negativ
# mot en familj falska POSITIVA: `lag` matchade inuti `lager`, `lagt`,
# `underlag` och `uppslaget`, så önskade svar som "vi har delarna på lager" och
# "enligt uppslaget är bilen godkänd" fälldes. §7.1: en spärr som fäller
# önskade svar blir avstängd.
#
# **`enligt` STÅR INTE LÄNGRE MED.** Ordet är för svagt: "enligt uppslaget" är
# ett svar som refererar VÅR källa, inte en föreskrift. "Enligt lagen" fälls
# ändå, på `lagen`.
#
# Fällt av §7-granskningen av skiva 31, varv 1 och varv 2.
FORFATTNINGSORD = re.compile(
    r"\bkrav\w*|\bkräv\w*|\bkrav\w*|\blag\b|\blagen\b|\blagkrav\w*|"
    r"\blagstiftning\w*|\bregel\b|\bregeln\b|\breglerna\b|\bföreskrift\w*|"
    r"\bforeskrift\w*|\bbestämmels\w*|\bbestammels\w*|\bvvfs\b|\bparagraf\w*|"
    r"§|\bmåste\b|\bmaste\b|\btrafikverket\b|\btransportstyrelsen\b",
    flags=re.IGNORECASE,
)


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
    exempel = las_exempel() if exempel is None else exempel

    svar = klient.messages.create(
        model=modell,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": bygg_prompt(forfragan, exempel)}],
    )

    text = "".join(b.text for b in svar.content if b.type == "text").strip()

    krav_pa_svaret(text, forfragan)
    return text
