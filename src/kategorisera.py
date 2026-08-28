"""Föreslår kategorier genom att låta Claude läsa varje inkommande text.

VARFÖR INTE KLUSTRING. TF-IDF över materialet gav 39 kluster som alla var
maskinmail, och det mänskliga materialet hamnade i restposten "spridda
ärenden". Metoden grupperade på avsändarens mall i stället för på kundens
ärende, eftersom massutskicken är många och likformiga medan kundmailen är få
och olika. Se `docs/beslutslogg.md` #9.

VAD SOM SKICKAS. Bara MÄNSKLIGA inkommande texter, enligt
`src/klassa_maskin.py`. Texten skickas RÅ, eftersom en maskerad text inte går
att kategorisera: `[NAMN] undrar om [REGNR]` säger ingenting om ärendet.
Anthropic API är en del av stacken enligt CLAUDE.md §0, och det är Lars som
beslutat att materialet får läsas av den.

**KATEGORIERNA SÄTTS INTE I FÖRVÄG.** Modellen får ingen lista att välja ur.
Den ombeds namnge ärendet med två till fyra ord, och kategorierna faller ut ur
att många texter får samma namn. En lista hade gjort utfallet till en
avprickning mot mina gissningar, vilket är precis det skivan ska undvika.

**INGEN HINK FÖRESLÅS.** Ramverksregel 2 i §0: ingen kategori flyttas av kod.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from collections import Counter
from pathlib import Path

from src import kanal, klassa_maskin, maskera, urval

ROT = Path(__file__).resolve().parent.parent
PARFIL = ROT / "data" / "par.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"
BESVARADE = ROT / "data" / "tradar.jsonl"
UTFIL = ROT / "docs" / "kategorier-forslag.md"
EXEMPELFIL = ROT / "scratchpad" / "kategorier-exempel.md"
SVARSFIL = ROT / "data" / "kategorisvar.jsonl"

MODELL = "claude-sonnet-4-6"

# Klassificering är en kort uppgift. Taket är satt lågt med avsikt: ett långt
# svar betyder att modellen resonerar i stället för att namnge.
MAX_TOKENS = 256

# Texten kortas innan den skickas. Ärendet står i början; resten är signatur,
# citat och artighetsfraser. Valt tal, inte uppmätt.
MAX_TECKEN = 1500

SYSTEM = """Du läser inkommande mail till en fristående bilverkstad i Stockholm.

Din enda uppgift är att namnge vad kunden VILL, med två till fyra ord på
svenska. Skriv namnet i grundform och gemener, till exempel
"boka besiktningstid" eller "fråga om pris".

Regler:
- Namnge ärendet, inte fordonet och inte kunden.
- Använd INGEN lista. Hitta det namn som passar texten.
- Är texten inte ett kundärende, svara exakt: inget kundärende.
- Går ärendet inte att utläsa, svara exakt: oklart.

Svara med enbart namnet. Ingen förklaring, inga citattecken, ingen punkt."""

# Regeln om kontext, tillagd i samma sträng för både den fria klassningen och
# pass 2. Den står som en egen konstant för att de två systemprompterna ska
# säga ORDAGRANT samma sak om kontexten: en omformulering i den ena hade gjort
# passen olika utan att det syntes.
KONTEXTREGEL = """

Ett mail kan bära ett kontextblock överst, mellan raderna
--- KONTEXT --- och --- SLUT KONTEXT ---. Det anger vilken kanal mailet kom in
genom och vad ämnesraden var. Kontextblocket är INTE kundens text.

Kanalen är en BEKRÄFTANDE SIGNAL. Den får aldrig ensam avgöra kategorin och är
aldrig ett nödvändigt villkor. Handlar kundens egen text uppenbart om något
annat än kanalen antyder, så följ TEXTEN."""

# Avgränsarna. De är literala och innehåller inga tecken som förekommer i en
# etikett, så ett svar som råkar återge dem syns i stället för att smälta in.
KONTEXT_START = "--- KONTEXT ---"
KONTEXT_SLUT = "--- SLUT KONTEXT ---"

# Ett svar som inte ser ut som en kort etikett är ett fel, inte en kategori.
GILTIG_ETIKETT = re.compile(r"^[a-zåäöéèü][a-zåäöéèü \-]{2,48}$")


def kontext_per_text(besvarade: Path) -> dict[str, dict]:
    """Ämnesrad och kanal per kundtext i den besvarade skörden.

    `data/par.jsonl` bär ingen ämnesrad, bara texterna. Kontexten hämtas därför
    ur trådfilen och slås upp på texten. Det är vad parametern `besvarade` i
    `texter_att_kategorisera` är till för; den togs emot utan att användas fram
    till skiva 17.

    VARJE KUNDMEDDELANDE INDEXERAS, inte bara trådens första.
    `src/extract.py::par_ur_trad` parar ett utgående svar med `senaste_kund`,
    alltså med det kundmeddelande som stod närmast före svaret. En par-text kan
    därför komma från vilken position som helst i tråden. Ett index byggt på
    enbart förstameddelanden hade dels missat de texterna, dels låtit en text
    från position tre kollidera OUPPTÄCKT med en annan tråds förstameddelande
    och få dess kanal.

    EN TEXT SOM BÄR MOTSTRIDIG KONTEXT FÅR INGEN. Ligger samma text i två
    trådar med olika ämnesrad går det inte att veta vilken som hör till posten,
    och då är svaret VET INTE. En gissad kanal hade sett mätt ut, och regeln i
    `src/kanal.py` bygger på att kanalen är en bekräftande signal.
    """
    funna: dict[str, dict | None] = {}
    if not besvarade.exists():
        return {}
    for rad in besvarade.read_text(encoding="utf-8").splitlines():
        if not rad:
            continue
        trad = json.loads(rad)
        # `or []` och inte `or [trad]`: en TRÅD är inget meddelande, och
        # `ar_kundmeddelande` returnerar sant för den eftersom den saknar
        # `labelIds`. Samma form som systerloopen i `texter_att_kategorisera`.
        for meddelande in trad.get("messages", []) or []:
            if not urval.ar_kundmeddelande(meddelande):
                continue
            text = urval.brodtext(meddelande)
            if not text:
                continue
            ny = {"amne": kanal.amnesrad(meddelande),
                  "kanal": kanal.namnge(meddelande)}
            if text in funna and funna[text] != ny:
                funna[text] = None
            else:
                funna.setdefault(text, ny)
    return {text: k for text, k in funna.items() if k is not None}


def texter_att_kategorisera(parfil: Path, besvarade: Path, obesvarade: Path,
                            domaner: set[str]) -> list[dict]:
    """Mänskliga inkommande texter ur båda skördarna, med sin kontext.

    Den besvarade sidan tas ur `par.jsonl`, som redan är parad och avdubblad
    per kundtext. Den obesvarade tas ur trådfilen, ett meddelande per tråd.

    Varje post bär `amne` och `kanal` när de går att fastställa. De är KONTEXT
    till klassificeringen och aldrig dess grund, se `src/kanal.py`.
    """
    poster: list[dict] = []
    sedda: set[str] = set()
    kontext = kontext_per_text(besvarade)

    # `par.jsonl` är REDAN maskinfiltrerad: `src/extract.py` sållar vid källan,
    # där trådstrukturen finns. Här filtreras inget om, och det ska inte göras
    # om heller: en andra filtrering utan tråd-ID hade behövt gissa.
    if parfil.exists():
        for rad in parfil.read_text(encoding="utf-8").splitlines():
            if not rad:
                continue
            post = json.loads(rad)
            text = post["inkommande_text"]
            if text in sedda:
                continue
            sedda.add(text)
            poster.append({"text": text, "kalla": "med svar",
                           **kontext.get(text, {})})

    if obesvarade.exists():
        for rad in obesvarade.read_text(encoding="utf-8").splitlines():
            if not rad:
                continue
            trad = json.loads(rad)
            if klassa_maskin.tradens_skal(trad, domaner):
                continue
            for meddelande in trad.get("messages", []) or []:
                if not urval.ar_kundmeddelande(meddelande):
                    continue
                text = urval.brodtext(meddelande)
                if text and text not in sedda:
                    sedda.add(text)
                    poster.append({
                        "text": text, "kalla": "utan svar",
                        "amne": kanal.amnesrad(meddelande),
                        "kanal": kanal.namnge(meddelande)})
                break

    return varva(poster)


def varva(poster: list[dict]) -> list[dict]:
    """Varvar källorna, så att VARJE PREFIX är blandat.

    Utan det låg alla besvarade först, och `--max-poster 20` drog tjugo poster
    ur enbart den besvarade sidan. Provkörningen blev då blind för de
    obesvarade, som är tre gånger fler och strukturellt annorlunda: till stor
    del förmedlade offertförfrågningar. Prompten hade alltså prövats mot en
    fjärdedel av materialet och körts mot allt.
    """
    med = [p for p in poster if p["kalla"] == "med svar"]
    utan = [p for p in poster if p["kalla"] != "med svar"]

    varvat = []
    for index in range(max(len(med), len(utan))):
        if index < len(med):
            varvat.append(med[index])
        if index < len(utan):
            varvat.append(utan[index])
    return varvat


ENVFIL = ROT / ".env"
NYCKELNAMN = "ANTHROPIC_API_KEY"

# Etiketter som INTE är kundärenden. `fel` sätts av koden, de två andra av
# modellen. Ingen av dem får en mall.
EJ_KUNDARENDE = ("inget kundärende", "oklart", "fel")

# Så många par MED SVAR en kategori behöver för att en mall ska kunna byggas
# ur den. Talet är ett ANTAGANDE, satt av Lars i skiva 8:s brief, och det är
# inte kalibrerat mot något utfall. Det revideras när mallbygget visat hur
# många exempel som faktiskt behövs.
MINSTA_PAR = 10


def las_api_nyckel(envfil: Path | None = None) -> str:
    """Nyckeln ur miljön, annars ur den gitignorerade `.env`.

    `.env` finns med därför att en `export` i en interaktiv terminal INTE når
    ett skal som startas om per anrop. Nyckeln i en fil som redan är
    gitignorerad är den väg som fungerar i båda fallen.

    Returnerar tom sträng om ingen nyckel finns. NYCKELN SKRIVS ALDRIG UT, och
    den som felsöker får veta att den saknas, aldrig vad den är (§6).
    """
    ur_miljon = os.environ.get(NYCKELNAMN, "").strip()
    if ur_miljon:
        return ur_miljon

    envfil = ENVFIL if envfil is None else envfil
    if not envfil.exists():
        return ""

    for rad in envfil.read_text(encoding="utf-8").splitlines():
        if not rad.strip() or rad.lstrip().startswith("#"):
            continue

        # FORMEN ÄR `ANTHROPIC_API_KEY=värde`, och inget annat. Raden börjar i
        # kolumn ett, likhetstecknet bär inga blanksteg, och värdet står bart:
        # inga citattecken, ingen kommentar efter sig.
        #
        # Toleransen mot en bar nyckel utan namn togs bort på Lars beslut, med
        # §1 som skäl: en oklarhet ska lyftas, inte tystas. Granskningen av
        # skiva 8 mätte upp att resten av toleransen var värre än den formen.
        # En kommentar efter värdet lästes in SOM DEL AV NYCKELN, vilket når
        # den som felsöker först som ett 401 från API:t och aldrig som ett
        # formatfel.
        #
        # TRE KONTROLLER, och de skiljer sig åt i vad de gör. Kontrollen
        # nedanför gäller radens BÖRJAN och hoppar över TYST. Nästa gäller ett
        # TOMT värde och hoppar också över tyst. Den tredje gäller ett värde
        # som finns men inte går att lita på, och den fäller körningen
        # HÖGLJUTT.
        #
        # Att de två första är tysta beror på att en `.env` med flera rader är
        # normalfallet: en rad som inte är nyckelraden ska inte stoppa
        # läsningen, och ett tomt värde är en platshållare och inte ett
        # formatfel. Saknas nyckeln därefter helt säger `bygg_klient` det med
        # formen utskriven.
        #
        # Den tredje fäller därför att alternativet vore att skicka en trasig
        # nyckel till API:t, vilket når den som felsöker som ett 401 och aldrig
        # som ett formatfel.
        #
        # NOTERA att blanksteg hamnar på OLIKA sidor beroende på var det står.
        # `ANTHROPIC_API_KEY =värde` faller på kontrollen nedanför och är tyst,
        # medan `ANTHROPIC_API_KEY= värde` passerar den och fälls högljutt av
        # den tredje. Det är inte en design, det är en konsekvens av att
        # kontrollerna prövas i den ordning de står. Kommentaren sa tidigare
        # att båda var tysta, vilket är fynd 2 i skiva 8:s tredje
        # granskningsvarv.
        if not rad.startswith(NYCKELNAMN + "="):
            continue

        varde = rad[len(NYCKELNAMN) + 1 :]
        if not varde:
            continue
        if varde != varde.strip() or any(t in varde for t in " \t\"'"):
            raise SystemExit(
                f"Raden med {NYCKELNAMN} i {envfil} har fel form.\n"
                "\n"
                "Värdet står bart. Det får inte bära citattecken, blanksteg\n"
                "eller en kommentar efter sig. Skriv EXAKT:\n"
                "\n"
                f"  {NYCKELNAMN}=sk-ant-...\n"
                "\n"
                "Nyckeln skrivs inte ut här (§6)."
            )
        return varde
    return ""


def bygg_klient(nyckel: str = ""):
    """Importeras lokalt, så att resten av modulen går att testa och granska
    utan att SDK:t är installerat."""
    import anthropic

    nyckel = nyckel or las_api_nyckel()
    if not nyckel:
        raise SystemExit(
            f"Ingen {NYCKELNAMN} hittad.\n"
            "\n"
            "Sätt den i miljön, eller skriv EXAKT den här raden i .env i\n"
            "repots rot:\n"
            "\n"
            f"  {NYCKELNAMN}=sk-ant-...\n"
            "\n"
            "Formen är obligatorisk och läses bokstavligt. Raden ska börja i\n"
            "kolumn ett, likhetstecknet ska sakna blanksteg, och värdet ska\n"
            "stå bart utan citattecken. En bar nyckel utan namn, ett\n"
            "export-prefix eller ett indrag läses INTE, och det är avsiktligt:\n"
            "en tolerant parser hade dolt att formatet var fel.\n"
            "Filen .env är gitignorerad."
        )
    return anthropic.Anthropic(api_key=nyckel)


class Tokenatgang:
    """Åtgången per körning, avläst ur API-svaren.

    Finns för att driftkostnaden per anrop måste vara MÄTT innan boten går i
    drift, och en körning över hela korpusen är det bästa mättillfället som
    finns. Fält som ett svar saknar räknas som noll i stället för att fälla
    körningen: en utebliven mätning får inte kosta en klassificering.
    """

    def __init__(self) -> None:
        self.anrop = 0
        self.in_tokens = 0
        self.ut_tokens = 0
        self.cache_skrivna = 0
        self.cache_lasta = 0

    def lagg_till(self, forbrukning) -> None:
        self.anrop += 1
        self.in_tokens += getattr(forbrukning, "input_tokens", 0) or 0
        self.ut_tokens += getattr(forbrukning, "output_tokens", 0) or 0
        self.cache_skrivna += (
            getattr(forbrukning, "cache_creation_input_tokens", 0) or 0
        )
        self.cache_lasta += (
            getattr(forbrukning, "cache_read_input_tokens", 0) or 0
        )

    def redovisa(self) -> list[str]:
        if not self.anrop:
            return ["  inga anrop"]
        return [
            f"  anrop: {self.anrop}",
            f"  in-tokens totalt: {self.in_tokens}",
            f"  ut-tokens totalt: {self.ut_tokens}",
            f"  cache skrivna: {self.cache_skrivna}",
            f"  cache lästa: {self.cache_lasta}",
            f"  in-tokens per anrop, medel: {self.in_tokens / self.anrop:.1f}",
            f"  ut-tokens per anrop, medel: {self.ut_tokens / self.anrop:.1f}",
        ]


def systemblock(text: str) -> list[dict]:
    """Systemprompten som ETT block med cachemarkör.

    Markören är korrekt men BITER INTE VID DAGENS PROMPTSTORLEK, och det ska
    stå här så att nästa läsare inte tror att cachen är i drift. Minsta
    cachebara prefix för `claude-sonnet-4-6` är 1024 tokens, avläst i
    Anthropics dokumentation 2026-08-26. `SYSTEM` mättes samma dag till 204
    tokens med `messages.count_tokens`. Under gränsen skapas ingen post, utan
    fel och utan varning: `cache_creation_input_tokens` förblir 0.

    Markören sitter ändå här av två skäl. Den kostar ingenting när den inte
    biter, och `Tokenatgang` läser båda cachefälten, så den dag prompten växer
    förbi gränsen syns det i redovisningen utan att någon behöver minnas att
    slå på det. Generering av svarsmail kommer att bära mallar, priser och
    fakta i systemprompten, och det är den vägen som passerar 1024.
    """
    return [{"type": "text", "text": text,
             "cache_control": {"type": "ephemeral"}}]


def bygg_anvandarmeddelande(text: str, amne: str = "",
                            kanal: str | None = None) -> str:
    """Kundens text, med ett kontextblock överst när kontext finns.

    TRUNKERINGEN GÄLLER TEXTEN, inte summan. Vore taket satt på hela strängen
    hade ett långt kontextblock ätit av kundens egna ord, alltså det enda som
    får avgöra kategorin. Kontexten läggs till EFTER trunkeringen.

    Saknas både ämne och kanal returneras texten oförändrad. Det gäller
    ANVÄNDARMEDDELANDET och inte anropet i sin helhet: `kategorisera_en` lägger
    `KONTEXTREGEL` till systemprompten OVILLKORLIGT, så systemblocket skiljer
    sig från det som skickades före skiva 17 även för en text utan kontext.
    Regeln är formulerad så att den är sann också när blocket saknas, och
    prompten hålls medvetet identisk för alla texter: två olika systemprompter
    hade gjort klassningen beroende av om kontexten råkade gå att fastställa.
    """
    kropp = text[:MAX_TECKEN]
    rader = []
    if kanal:
        rader.append(f"Kanal: {kanal}")
    if amne.strip():
        rader.append(f"Ämnesrad: {amne.strip()}")
    if not rader:
        return kropp
    return "\n".join([KONTEXT_START, *rader, KONTEXT_SLUT, "", kropp])


def kategorisera_en(klient, text: str, modell: str = MODELL,
                    atgang: Tokenatgang | None = None,
                    system: str = SYSTEM, amne: str = "",
                    kanal: str | None = None) -> str:
    svar = klient.messages.create(
        model=modell,
        max_tokens=MAX_TOKENS,
        system=systemblock(system + KONTEXTREGEL),
        messages=[{"role": "user",
                   "content": bygg_anvandarmeddelande(text, amne, kanal)}],
    )
    if atgang is not None:
        atgang.lagg_till(getattr(svar, "usage", None))
    return normalisera(textinnehall(svar))


def textinnehall(svar) -> str:
    """Textblocken i ett API-svar, hopfogade."""
    return "".join(block.text for block in svar.content if block.type == "text")


def normalisera(ratext: str) -> str:
    """Ett svar som inte ser ut som en kort etikett blir `oklart`.

    Utan det blir en modellens förklaring till en egen kategori, och
    kategorilistan fylls av engångsposter som ser ut som kategorier.
    """
    etikett = " ".join(ratext.strip().lower().strip('."\'').split())
    if not GILTIG_ETIKETT.match(etikett):
        return "oklart"
    return etikett


def kategorisera_alla(klient, poster: list[dict], modell: str = MODELL,
                      sov=time.sleep,
                      atgang: Tokenatgang | None = None) -> list[dict]:
    """Kategoriserar en text i taget och returnerar posterna med etikett.

    En text i taget, inte i batch: ett fel på en text ska kosta en text, och
    ett svar ska gå att spåra till sin fråga. Fel sväljs inte, men de stoppar
    inte heller resten: posten får etiketten `fel` och räknas för sig.
    """
    ut = []
    for nummer, post in enumerate(poster):
        try:
            etikett = kategorisera_en(
                klient, post["text"], modell, atgang,
                amne=post.get("amne", ""), kanal=post.get("kanal"))
        except Exception as fel:  # noqa: BLE001
            etikett = "fel"
            print(f"  fel på post {nummer}: {type(fel).__name__}")
            sov(2.0)
        ut.append({**post, "etikett": etikett})
        if nummer and nummer % 25 == 0:
            print(f"  {nummer}/{len(poster)} kategoriserade")
    return ut


def sammanstall(poster: list[dict]) -> list[dict]:
    per_etikett: dict[str, dict] = {}
    for post in poster:
        rad = per_etikett.setdefault(
            post["etikett"],
            {"etikett": post["etikett"], "antal": 0, "med_svar": 0,
             "utan_svar": 0, "exempel": []},
        )
        rad["antal"] += 1
        if post["kalla"] == "med svar":
            rad["med_svar"] += 1
        else:
            rad["utan_svar"] += 1
        if len(rad["exempel"]) < 3:
            rad["exempel"].append(post["text"])

    return sorted(per_etikett.values(), key=lambda r: -r["antal"])


def underlag_per_kategori(sammanstallning: list[dict],
                          minsta: int = MINSTA_PAR) -> tuple[list, list]:
    """DEL C i skiva 8: talet som avgör hur många kategorier som kan få mallar.

    Returnerar `(äkta, med för få par)`. ÄKTA är kategorierna sedan de tre
    icke-ärendena dragits bort. `inget kundärende` och `oklart` är etiketter
    modellen sätter; `fel` sätts av `kategorisera_alla` när anropet inte gick
    igenom. Ingen av dem är ett kundärende, och ingen av dem ska få en mall.

    Tröskeln är antal par MED SVAR, inte antal texter: en mall byggs ur ett
    faktiskt svar Matte eller Lars redan skrivit (CLAUDE.md §11), och en
    kategori utan svar bär inget underlag hur många texter den än har.
    """
    akta = [k for k in sammanstallning if k["etikett"] not in EJ_KUNDARENDE]
    return akta, [k for k in akta if k["med_svar"] < minsta]


def _exempel(text: str, tecken: int = 160) -> str:
    enradigt = " ".join(maskera.maska_fritext(text).split())
    if len(enradigt) > tecken:
        enradigt = enradigt[:tecken].rstrip() + " …"
    return enradigt


def skriv_rapport(sammanstallning: list[dict], utfil: Path, antal: int,
                  modell: str) -> None:
    rader = [
        "# Kategoriförslag",
        "",
        "**Version:** 0.2.0 · **Uppdaterad:** 2026-08-26 · "
        "**Implementerar** CLAUDE.md §0",
        "",
        f"Maskinproducerad av `src/kategorisera.py` med `{modell}`. "
        "**Skriv inte i den här filen för hand**: den skrivs om vid nästa "
        "körning.",
        "",
        "Kategorierna är inte satta i förväg. Modellen fick ingen lista att "
        "välja ur, utan ombads namnge vad kunden vill med två till fyra ord. "
        "Kategorierna faller ut ur att många texter fick samma namn.",
        "",
        "**INGEN HINKTILLDELNING FÖRESLÅS.** Vilken kategori som hamnar i "
        "`auto`, `utkast` eller `aldrig` är Lars beslut i fas 4:s grind. "
        "Ramverksregel 2 i CLAUDE.md §0 säger att ingen kategori flyttas av "
        "kod.",
        "",
        "**CITATEN STÅR INTE HÄR.** De skrivs till "
        f"`{EXEMPELFIL.parent.name}/{EXEMPELFIL.name}`, som är gitignorerad. "
        "Ett namn som kunden skrivit med gemener i löpande text går inte att "
        "hitta med någon heuristik, och §6 tillåter ingen persondata i `docs/`.",
        "",
        "Endast MÄNSKLIGA inkommande texter ingår, enligt "
        "`src/klassa_maskin.py`. Maskinmail är bortsållat på huvuden.",
        "",
        "---",
        "",
        "## Kategorier",
        "",
        f"Texter i underlaget: {antal}",
        "",
        "| Kategori | Totalt | Med svar | Utan svar |",
        "| --- | --- | --- | --- |",
    ]

    for rad in sammanstallning:
        rader.append(
            f"| {rad['etikett']} | {rad['antal']} | {rad['med_svar']} | "
            f"{rad['utan_svar']} |"
        )

    rader += [
        "",
        "---",
        "",
        "## Appendix — versionshistorik (nyaste överst)",
        "",
        "### 0.2.0 — 2026-08-26",
        "",
        "Klustringen ersatt av kategorisering med Anthropic API. TF-IDF "
        "grupperade på avsändarens mall i stället för på kundens ärende, och "
        "det mänskliga materialet hamnade i restposten. Se beslutslogg #9.",
        "",
        "### 0.1.0 — 2026-08-26",
        "",
        "Filen upprättad av `src/cluster.py`.",
        "",
    ]

    utfil.parent.mkdir(parents=True, exist_ok=True)
    utfil.write_text("\n".join(rader), encoding="utf-8")


def skriv_exempel(sammanstallning: list[dict], utfil: Path) -> None:
    rader = [
        "# Kategoriexempel",
        "",
        "**GITIGNORERAD. INNEHÅLLER PERSONDATA.** Maskerad så långt "
        "`src/maskera.py` når, men ett namn som kunden skrivit med gemener går "
        "inte att hitta med någon heuristik. Filen får inte committas eller "
        "klistras in i ett dokument under `docs/`.",
        "",
        "---",
        "",
    ]
    for rad in sammanstallning:
        rader += [f"## {rad['etikett']} ({rad['antal']})", ""]
        for exempel in rad["exempel"]:
            rader += [f"> {_exempel(exempel)}", ""]

    utfil.parent.mkdir(parents=True, exist_ok=True)
    utfil.write_text("\n".join(rader), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--parfil", type=Path, default=PARFIL)
    tolk.add_argument("--besvarade", type=Path, default=BESVARADE)
    tolk.add_argument("--obesvarade", type=Path, default=OBESVARADE)
    tolk.add_argument("--utfil", type=Path, default=UTFIL)
    tolk.add_argument("--exempelfil", type=Path, default=EXEMPELFIL)
    tolk.add_argument("--svarsfil", type=Path, default=SVARSFIL)
    tolk.add_argument("--modell", default=MODELL)
    tolk.add_argument("--max-poster", type=int, default=None,
                      help="begränsa antalet texter, för en provkörning")
    tolk.add_argument("--kalla", choices=("alla", "med-svar", "utan-svar"),
                      default="alla",
                      help="dra bara ur en källa, för en riktad provkörning")
    arg = tolk.parse_args(argv)

    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)
    poster = texter_att_kategorisera(arg.parfil, arg.besvarade,
                                     arg.obesvarade, domaner)
    if arg.kalla != "alla":
        onskad = "med svar" if arg.kalla == "med-svar" else "utan svar"
        poster = [p for p in poster if p["kalla"] == onskad]

    if arg.max_poster:
        poster = poster[:arg.max_poster]

    med_svar = sum(1 for p in poster if p["kalla"] == "med svar")
    print(f"mänskliga texter att kategorisera: {len(poster)}")
    print(f"  med svar: {med_svar}")
    print(f"  utan svar: {len(poster) - med_svar}")
    if not poster:
        print("inget att göra")
        return 1

    klient = bygg_klient()
    atgang = Tokenatgang()
    kategoriserade = kategorisera_alla(klient, poster, arg.modell,
                                       atgang=atgang)

    arg.svarsfil.parent.mkdir(parents=True, exist_ok=True)
    with arg.svarsfil.open("w", encoding="utf-8") as fil:
        for post in kategoriserade:
            fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    sammanstallning = sammanstall(kategoriserade)
    skriv_rapport(sammanstallning, arg.utfil, len(kategoriserade), arg.modell)
    skriv_exempel(sammanstallning, arg.exempelfil)

    fordelning = Counter(p["etikett"] for p in kategoriserade)

    print("")
    print("=== TOKENÅTGÅNG, avläst ur API-svaren ===")
    for rad in atgang.redovisa():
        print(rad)
    print("")

    akta, fa_par = underlag_per_kategori(sammanstallning)
    print("=== UNDERLAG PER KATEGORI ===")
    print(f"  äkta kundkategorier: {len(akta)}")
    print(f"  av dem med FÄRRE ÄN TIO par med svar: {len(fa_par)}")
    print(f"  alltså med tio eller fler: {len(akta) - len(fa_par)}")
    print("")

    print(f"kategorier: {len(sammanstallning)}")
    print(f"  varav 'oklart': {fordelning.get('oklart', 0)}")
    print(f"  varav 'inget kundärende': {fordelning.get('inget kundärende', 0)}")
    print(f"  varav 'fel': {fordelning.get('fel', 0)}")
    print(f"utfil: {arg.utfil}")
    print(f"exempelfil, gitignorerad: {arg.exempelfil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
