"""Klustrar INKOMMANDE-sidan och föreslår kategorier.

Kategorierna ska falla ut ur datan och inte sättas i förväg. Klustringen är
därför oövervakad: ingen etikettlista finns, och etiketterna som föreslås är
de termer som skiljer klustret från de andra.

TVÅ KÄLLOR. Besvarade trådar kommer ur `data/par.jsonl`, obesvarade ur
`data/tradar_obesvarade.jsonl`. Båda behövs: `in:sent` fångar bara det som
besvarats, och de mail som aldrig fick svar är den population boten finns för
att fånga. En klassificerare tränad enbart på besvarade trådar är blind för dem.

METOD. TF-IDF över ordstammar, cosinuslikhet, och agglomerativ klustring med
tröskel. Inget externt beroende läggs till för detta: `requirements.txt` bär
Gmail-klienten och pytest, och en klustring som kan skrivas med standard-
biblioteket motiverar inte ett nytt beroende i ett projekt som ska kunna
granskas rad för rad.

**KLUSTRINGEN FÖRESLÅR INGEN HINK.** Vilken kategori som hamnar i `auto`,
`utkast` eller `aldrig` är Lars beslut i fas 4:s grind, och ramverksregel 2 i
CLAUDE.md §0 säger att ingen kategori flyttas av kod.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter
from pathlib import Path

from src import maskera, urval

ROT = Path(__file__).resolve().parent.parent
PARFIL = ROT / "data" / "par.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"
UTFIL = ROT / "docs" / "kategorier-forslag.md"

# Citaten hamnar HÄR och inte i den committade rapporten. `scratchpad/` är
# gitignorerad.
#
# Skälet är §6 och inte bekvämlighet. Ett namn skrivet med gemener i löpande
# text går inte att hitta med någon heuristik: maskeringen bygger på att
# svenskan inte versaliserar vanliga substantiv, och det säger ingenting om ett
# namn som kunden själv skrivit gement. En granskning fann fyra sorters
# persondata i citaten i en committad fil, varav en var ett fullständigt namn i
# gemener. Kategorinamn, antal och medianer är däremot härledda storheter och
# går att maska säkert; de blir kvar i rapporten.
EXEMPELFIL = ROT / "scratchpad" / "kategorier-exempel.md"

ORD = re.compile(r"[a-zåäöéèü]{3,}")

# Svenska stoppord plus mailfloskler. Utan dem klustrar allt på "hej" och "tack".
STOPPORD = {
    "och", "att", "det", "som", "för", "med", "har", "den", "till", "jag",
    "inte", "kan", "man", "vad", "vi", "ska", "eller", "men", "hej", "tack",
    "vill", "vara", "från", "hur", "här", "där", "vid", "mot", "under", "över",
    "efter", "innan", "hos", "sedan", "utan", "samt", "också", "bara", "mer",
    "mycket", "något", "någon", "några", "alla", "andra", "ett", "en", "är",
    "var", "vem", "när", "detta", "denna", "dessa", "dess", "sin", "sitt",
    "sina", "hans", "hennes", "deras", "mvh", "hälsningar", "vänliga", "bästa",
    "skickat", "skickades", "mailet", "meddelandet", "svar", "svara", "gärna",
    "möjligt", "behöver", "önskar", "undrar", "gäller", "avser", "finns",
    "skulle", "kunde", "borde", "måste", "blir", "blev", "vore", "samma",
    "eftersom", "därför", "alltså", "iväg", "igen", "helst", "kanske",
}

# Rester av HTML och mailteknik som överlever textutvinningen. De bär ingen
# information om ärendet, och utan dem klustrar mail på avsändarens mall.
STOPPORD |= {
    "auml", "ouml", "aring", "nbsp", "amp", "quot", "apos", "eacute",
    "style", "font", "div", "span", "table", "tbody", "align", "valign",
    "width", "height", "margin", "padding", "border", "color", "background",
    "class", "href", "img", "src", "alt", "strong", "center", "right", "left",
    "cid", "png", "jpg", "jpeg", "gif", "utm", "medium", "source", "campaign",
    "content", "term", "click", "clicks", "trk", "noreply", "mailto",
    "unsubscribe", "com", "www", "https", "http", "html", "the", "and", "you",
    "your", "for", "with", "this", "that", "any", "may", "are", "our", "från",
    "till", "den", "det", "vår", "våra", "min", "mina", "ditt", "dina",
    "skrev", "ons", "tis", "tors", "fre", "mån", "sön", "lör", "jan", "feb",
    "mar", "apr", "maj", "jun", "jul", "aug", "sep", "okt", "nov", "dec",
}

# Cosinuslikhet över denna tröskel lägger två dokument i samma kluster.
# VALT tal, inte uppmätt. Sänks det växer klustren ihop, höjs det splittras de.
TROSKEL = 0.28

# Kluster mindre än så här redovisas samlat som "spridda ärenden" i stället för
# som egna kategorier. Ett kluster om ett dokument är inte en kategori.
MINSTA_KLUSTER = 4


def tokenisera(text: str, uteslut: set[str] | None = None) -> list[str]:
    """Tokeniserar den MASKERADE texten, aldrig råtexten.

    Adresser, länkar, regnummer och telefonnummer blir till platshållare innan
    orden plockas ut. Utan det blev lokaldelen i en signaturadress ett ord, och
    kundernas användarnamn hamnade som kategorinamn i en committad fil.
    Spårningsparametrar i länkar gjorde detsamma: `utm`, `medium` och `source`
    bildade en av de största kategorierna utan att betyda något.
    """
    uteslut = STOPPORD if uteslut is None else STOPPORD | uteslut
    maskerat = maskera.maska_fritext(text).lower()
    return [ord_ for ord_ in ORD.findall(maskerat) if ord_ not in uteslut]


ORD_MED_SKIFTLAGE = re.compile(r"\b[A-ZÅÄÖa-zåäöéèü]{3,}\b")


def namn_i_korpus(texter: list[str]) -> set[str]:
    """Egennamn över hela materialet, i gemen form.

    Etiketterna byggs av gemena tokens, så versalheuristiken kan inte tillämpas
    på dem. Den körs därför på hela korpusen och resultatet blir en
    uteslutningslista. Utan den hamnade kundernas namn som KATEGORINAMN i en
    committad fil, vilket är en §6-överträdelse och inte en skönhetsfläck.

    KRITERIET ÄR STATISTISKT, inte positionellt. Ett ord räknas som namn när det
    oftare skrivs versalt än gement i materialet. `Melias` och `Annika` skrivs
    nästan alltid versalt, medan `besiktning` skrivs versalt bara när det råkar
    inleda en mening. En regel som bara tittade på position missade namn i
    signaturblock, där varje rad börjar med versal.

    Att namn utesluts är dessutom rätt även analytiskt: en kategori ska falla ut
    ur vad kunden VILL, inte ur vem som råkade skriva.
    """
    versalt: Counter[str] = Counter()
    gement: Counter[str] = Counter()
    for ratext in texter:
        # Räkningen sker på text där adresser, länkar och domäner redan är
        # maskerade men skiftläget är orört. Räknas råtexten röstar ordets
        # gemena förekomster inuti en e-postadress ned det under tröskeln, och
        # ett kundförnamn slapp igenom som kategorinamn.
        text = maskera.maska_identifierare(ratext)
        for traff in ORD_MED_SKIFTLAGE.finditer(text):
            ord_ = traff.group(0)
            if ord_ in maskera.EJ_NAMN:
                continue
            if ord_[0].isupper():
                versalt[ord_.lower()] += 1
            else:
                gement[ord_.lower()] += 1

    return {ord_ for ord_, antal in versalt.items() if antal > gement[ord_]}


def tfidf(dokument: list[list[str]]) -> list[dict[str, float]]:
    """TF-IDF med L2-normalisering, så att cosinuslikheten blir en skalärprodukt."""
    antal = len(dokument)
    dokumentfrekvens: Counter[str] = Counter()
    for tokens in dokument:
        dokumentfrekvens.update(set(tokens))

    vektorer = []
    for tokens in dokument:
        frekvens = Counter(tokens)
        vektor = {}
        for ord_, raknare in frekvens.items():
            idf = math.log((antal + 1) / (dokumentfrekvens[ord_] + 1)) + 1.0
            vektor[ord_] = (raknare / len(tokens)) * idf
        norm = math.sqrt(sum(v * v for v in vektor.values())) or 1.0
        vektorer.append({o: v / norm for o, v in vektor.items()})
    return vektorer


def likhet(a: dict[str, float], b: dict[str, float]) -> float:
    if len(a) > len(b):
        a, b = b, a
    return sum(vikt * b.get(ord_, 0.0) for ord_, vikt in a.items())


def klustra(vektorer: list[dict[str, float]]) -> list[list[int]]:
    """Agglomerativ klustring med centroid och tröskel.

    Ett dokument läggs i det kluster vars centroid det liknar mest, om
    likheten når över tröskeln. Annars startar det ett eget kluster. Ordningen
    påverkar utfallet, vilket är metodens kända svaghet; dokumenten sorteras
    därför på längd så att de längsta, som bär mest signal, får bilda klustren
    först.
    """
    ordning = sorted(range(len(vektorer)), key=lambda i: -len(vektorer[i]))
    klustren: list[list[int]] = []
    centroider: list[dict[str, float]] = []

    for index in ordning:
        vektor = vektorer[index]
        basta, basta_likhet = None, TROSKEL
        for nummer, centroid in enumerate(centroider):
            poang = likhet(vektor, centroid)
            if poang > basta_likhet:
                basta, basta_likhet = nummer, poang

        if basta is None:
            klustren.append([index])
            centroider.append(dict(vektor))
        else:
            klustren[basta].append(index)
            centroider[basta] = _uppdatera(centroider[basta],
                                           vektor, len(klustren[basta]))
    return klustren


def _uppdatera(centroid: dict[str, float], vektor: dict[str, float],
               antal: int) -> dict[str, float]:
    ny = dict(centroid)
    for ord_, vikt in vektor.items():
        ny[ord_] = ny.get(ord_, 0.0) + (vikt - ny.get(ord_, 0.0)) / antal
    norm = math.sqrt(sum(v * v for v in ny.values())) or 1.0
    return {o: v / norm for o, v in ny.items()}


def etikett(klustret: list[int], vektorer: list[dict[str, float]],
            antal_ord: int = 3) -> str:
    """Klustrets etikett är dess mest utmärkande termer.

    Etiketten är ett FÖRSLAG och en beskrivning av vad som faktiskt står i
    texterna, inte en kategori någon bestämt i förväg.
    """
    summa: Counter[str] = Counter()
    for index in klustret:
        for ord_, vikt in vektorer[index].items():
            summa[ord_] += vikt
    return ", ".join(ord_ for ord_, _ in summa.most_common(antal_ord))


def las_kallor(parfil: Path, obesvarade: Path) -> list[dict]:
    """Inkommande texter från båda källorna, med källan utskriven per post."""
    dokument = []

    if parfil.exists():
        # Samma kundmeddelande kan vara vänster sida i FLERA par, när vi svarat
        # två gånger på det. Paren är äkta, men i en klustring skulle den texten
        # räknas flera gånger och blåsa upp sitt kluster. Klustringen ser därför
        # varje kundtext en gång, och svarslängden blir medianen av svaren.
        sedda: dict[str, dict] = {}
        for rad in parfil.read_text(encoding="utf-8").splitlines():
            if not rad:
                continue
            post = json.loads(rad)
            text = post["inkommande_text"]
            if text in sedda:
                sedda[text]["svarslangder"].append(len(post["utgaende_text"]))
                continue
            sedda[text] = {"text": text, "kalla": "med svar",
                           "svarslangder": [len(post["utgaende_text"])]}

        for post in sedda.values():
            dokument.append({
                "text": post["text"],
                "kalla": "med svar",
                "svarslangd": _median(post["svarslangder"]),
            })

    if obesvarade.exists():
        for rad in obesvarade.read_text(encoding="utf-8").splitlines():
            if not rad:
                continue
            trad = json.loads(rad)
            for meddelande in trad.get("messages", []) or []:
                if not urval.ar_kundmeddelande(meddelande):
                    continue
                # Massutskick sållas bort HÄR och inte i miningen. Miningen ska
                # hämta brett en gång; ett urvalsfel där kostar en ny körning
                # mot brevlådan, medan ett urvalsfel här kostar en körning mot
                # disk.
                if urval.ar_massutskick(meddelande):
                    break
                text = urval.brodtext(meddelande)
                if text:
                    dokument.append({"text": text, "kalla": "utan svar",
                                     "svarslangd": None})
                break

    return dokument


def _median(varden: list[int]) -> int | None:
    if not varden:
        return None
    sorterade = sorted(varden)
    mitten = len(sorterade) // 2
    if len(sorterade) % 2:
        return sorterade[mitten]
    return (sorterade[mitten - 1] + sorterade[mitten]) // 2


def _exempel(text: str, tecken: int = 160) -> str:
    maskerat = maskera.maska_fritext(urval.stada(text))
    enradigt = " ".join(maskerat.split())
    if len(enradigt) > tecken:
        enradigt = enradigt[:tecken].rstrip() + " …"
    return enradigt


def sammanstall(dokument: list[dict], klustren: list[list[int]],
                vektorer: list[dict[str, float]]) -> list[dict]:
    sammanstallning = []
    for klustret in klustren:
        poster = [dokument[i] for i in klustret]
        med_svar = [p for p in poster if p["kalla"] == "med svar"]
        sammanstallning.append({
            "etikett": etikett(klustret, vektorer),
            "antal": len(poster),
            "med_svar": len(med_svar),
            "utan_svar": len(poster) - len(med_svar),
            "median_svarslangd": _median(
                [p["svarslangd"] for p in med_svar if p["svarslangd"]]
            ),
            "exempel": [_exempel(p["text"]) for p in poster[:3]],
        })
    sammanstallning.sort(key=lambda k: -k["antal"])
    return sammanstallning


def skriv_rapport(sammanstallning: list[dict], utfil: Path,
                  antal_dokument: int) -> None:
    stora = [k for k in sammanstallning if k["antal"] >= MINSTA_KLUSTER]
    sma = [k for k in sammanstallning if k["antal"] < MINSTA_KLUSTER]

    rader = [
        "# Kategoriförslag",
        "",
        "**Version:** 0.1.0 · **Uppdaterad:** 2026-08-26 · "
        "**Implementerar** CLAUDE.md §0",
        "",
        "Maskinproducerad av `src/cluster.py`. **Skriv inte i den här filen för "
        "hand**: den skrivs om vid nästa körning.",
        "",
        "Kategorierna är inte satta i förväg. De faller ut ur en oövervakad "
        "klustring av inkommande text, och etiketten per kategori är de termer "
        "som skiljer klustret från de andra.",
        "",
        "**INGEN HINKTILLDELNING FÖRESLÅS.** Vilken kategori som hamnar i "
        "`auto`, `utkast` eller `aldrig` är Lars beslut i fas 4:s grind. "
        "Ramverksregel 2 i CLAUDE.md §0 säger att ingen kategori flyttas av kod.",
        "",
        "**CITATEN STÅR INTE HÄR.** De skrivs till "
        f"`{EXEMPELFIL.parent.name}/{EXEMPELFIL.name}`, som är gitignorerad. "
        "Ett namn som kunden skrivit med gemener i löpande text går inte att "
        "hitta med någon heuristik, och §6 tillåter ingen persondata i `docs/`. "
        "Kategorinamn, antal och medianer är härledda storheter och kan maskas "
        "säkert; citaten kan det inte.",
        "",
        "---",
        "",
        "## Översikt",
        "",
        f"Dokument i klustringen: {antal_dokument}",
        "",
        "| Kategori | Totalt | Med svar | Utan svar | Median svarslängd |",
        "| --- | --- | --- | --- | --- |",
    ]

    for kategori in stora:
        median = kategori["median_svarslangd"]
        rader.append(
            f"| {kategori['etikett']} | {kategori['antal']} | "
            f"{kategori['med_svar']} | {kategori['utan_svar']} | "
            f"{median if median is not None else 'inget svar'} |"
        )

    if sma:
        spridda = sum(k["antal"] for k in sma)
        med_svar = sum(k["med_svar"] for k in sma)
        rader.append(
            f"| _spridda ärenden, kluster under {MINSTA_KLUSTER}_ | {spridda} | "
            f"{med_svar} | {spridda - med_svar} | — |"
        )

    rader += ["", "---", "", "## Kategorier"]

    for kategori in stora:
        median = kategori["median_svarslangd"]
        rader += [
            "",
            f"### {kategori['etikett']}",
            "",
            f"- **Antal totalt:** {kategori['antal']}",
            f"- **Med svar:** {kategori['med_svar']}",
            f"- **Utan svar:** {kategori['utan_svar']}",
            f"- **Median svarslängd:** "
            f"{median if median is not None else 'inget svar att mäta'}",
            f"- **Exempel:** se `{EXEMPELFIL.parent.name}/{EXEMPELFIL.name}`",
        ]

    rader += [
        "---",
        "",
        "## Appendix — versionshistorik (nyaste överst)",
        "",
        "### 0.1.0 — 2026-08-26",
        "",
        "Filen upprättad av `src/cluster.py`. Den skrivs om i sin helhet vid "
        "varje körning och versionshistoriken bärs därför av committarna, inte "
        "av den här listan.",
        "",
    ]

    utfil.parent.mkdir(parents=True, exist_ok=True)
    utfil.write_text("\n".join(rader), encoding="utf-8")


def skriv_exempel(sammanstallning: list[dict], utfil: Path) -> None:
    """Citaten, till en gitignorerad fil. Maskerade så långt heuristiken når,
    men INTE säkra: läs dem som persondata och behandla dem därefter."""
    rader = [
        "# Kategoriexempel",
        "",
        "**GITIGNORERAD. INNEHÅLLER PERSONDATA.** Citaten är maskerade så långt "
        "`src/maskera.py` når, men ett namn som kunden skrivit med gemener går "
        "inte att hitta med någon heuristik. Filen får inte committas, klistras "
        "in i ett dokument under `docs/`, eller skickas vidare.",
        "",
        "Maskinproducerad av `src/cluster.py`. Skrivs om vid nästa körning.",
        "",
        "---",
        "",
    ]
    for kategori in sammanstallning:
        if kategori["antal"] < MINSTA_KLUSTER:
            continue
        rader += [f"## {kategori['etikett']}", ""]
        for exempel in kategori["exempel"]:
            rader += [f"> {exempel}", ""]

    utfil.parent.mkdir(parents=True, exist_ok=True)
    utfil.write_text("\n".join(rader), encoding="utf-8")


def visa_par(parfil: Path, index: int) -> None:
    """Skriver ut ETT par ur data/par.jsonl, maskerat.

    Finns för att kunna svara på frågan om filens innehåll utan att citera den.
    Filen är RÅ, alltså omaskerad, vilket är avsiktligt: mallarna byggs ur
    faktiska svar enligt §11, och en maskerad text hade förstört rösten. Filen
    ligger i den gitignorerade `data/`. Maskeringen sker HÄR, i utskriften.
    """
    rader = parfil.read_text(encoding="utf-8").splitlines()
    if not 0 <= index < len(rader):
        print(f"index {index} finns inte, filen har {len(rader)} rader")
        return

    post = json.loads(rader[index])
    print(f"=== PAR {index}, MASKERAT FÖR UTSKRIFT ===")
    print(f"  fält: {sorted(post)}")
    print(f"  tidsstampel: {post['tidsstampel']}")
    print(f"  avsandare_hash: {post['avsandare_hash'][:16]}… ({len(post['avsandare_hash'])} tecken)")
    print("")
    print(f"  inkommande_text, {len(post['inkommande_text'])} tecken:")
    for rad in maskera.maska_fritext(post["inkommande_text"]).split("\n")[:8]:
        print(f"    {rad}")
    print("")
    print(f"  utgaende_text, {len(post['utgaende_text'])} tecken:")
    for rad in maskera.maska_fritext(post["utgaende_text"]).split("\n")[:8]:
        print(f"    {rad}")


def sok(dokument: list[dict], term: str) -> None:
    """Räknar dokument som nämner en term, per källa.

    Finns därför att en klustring inte garanterar att en kategori man VET finns
    hamnar i ett eget kluster. En kategori kan vara spridd över flera kluster
    eller drunkna bland större. Att räkna direkt på termen är ett oberoende mått
    som inte beror på tröskeln.
    """
    termer = [t.strip().lower() for t in term.split(",") if t.strip()]
    med_svar = 0
    utan_svar = 0
    svarslangder = []

    for post in dokument:
        text = post["text"].lower()
        if not any(t in text for t in termer):
            continue
        if post["kalla"] == "med svar":
            med_svar += 1
            if post["svarslangd"]:
                svarslangder.append(post["svarslangd"])
        else:
            utan_svar += 1

    print(f"=== TERMSÖKNING: {', '.join(termer)} ===")
    print(f"  dokument totalt: {med_svar + utan_svar}")
    print(f"  med svar, alltså par som går att bygga mall ur: {med_svar}")
    print(f"  utan svar: {utan_svar}")
    print(f"  median svarslängd: {_median(svarslangder)}")


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--parfil", type=Path, default=PARFIL)
    tolk.add_argument("--obesvarade", type=Path, default=OBESVARADE)
    tolk.add_argument("--utfil", type=Path, default=UTFIL)
    tolk.add_argument("--exempelfil", type=Path, default=EXEMPELFIL)
    tolk.add_argument(
        "--sok",
        default=None,
        help="räkna dokument som innehåller termen, per källa, i stället för "
             "att klustra",
    )
    tolk.add_argument("--parexempel", type=int, default=None,
                      help="skriv ut ett par ur par.jsonl, maskerat")
    arg = tolk.parse_args(argv)

    if arg.parexempel is not None:
        visa_par(arg.parfil, arg.parexempel)
        return 0

    dokument = las_kallor(arg.parfil, arg.obesvarade)

    if arg.sok:
        sok(dokument, arg.sok)
        return 0
    if not dokument:
        print("inga dokument att klustra")
        return 1

    namn = namn_i_korpus([d["text"] for d in dokument])
    tokens = [tokenisera(d["text"], namn) for d in dokument]
    behallna = [i for i, t in enumerate(tokens) if t]
    dokument = [dokument[i] for i in behallna]
    vektorer = tfidf([tokens[i] for i in behallna])

    klustren = klustra(vektorer)
    sammanstallning = sammanstall(dokument, klustren, vektorer)
    skriv_rapport(sammanstallning, arg.utfil, len(dokument))
    skriv_exempel(sammanstallning, arg.exempelfil)

    med_svar = sum(1 for d in dokument if d["kalla"] == "med svar")
    print(f"dokument: {len(dokument)}")
    print(f"  med svar: {med_svar}")
    print(f"  utan svar: {len(dokument) - med_svar}")
    print(f"kluster: {len(klustren)}")
    print(f"  varav minst {MINSTA_KLUSTER} dokument: "
          f"{sum(1 for k in sammanstallning if k['antal'] >= MINSTA_KLUSTER)}")
    print(f"utfil: {arg.utfil}")
    print(f"exempelfil, gitignorerad: {arg.exempelfil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
