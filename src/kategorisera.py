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
import re
import time
from collections import Counter
from pathlib import Path

from src import klassa_maskin, maskera, urval

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

# Ett svar som inte ser ut som en kort etikett är ett fel, inte en kategori.
GILTIG_ETIKETT = re.compile(r"^[a-zåäöéèü][a-zåäöéèü \-]{2,48}$")


def texter_att_kategorisera(parfil: Path, besvarade: Path, obesvarade: Path,
                            domaner: set[str]) -> list[dict]:
    """Mänskliga inkommande texter ur båda skördarna.

    Den besvarade sidan tas ur `par.jsonl`, som redan är parad och avdubblad
    per kundtext. Den obesvarade tas ur trådfilen, ett meddelande per tråd.
    """
    poster: list[dict] = []
    sedda: set[str] = set()

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
            poster.append({"text": text, "kalla": "med svar"})

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
                    poster.append({"text": text, "kalla": "utan svar"})
                break

    return poster


def bygg_klient():
    """Importeras lokalt, så att resten av modulen går att testa och granska
    utan att SDK:t är installerat."""
    import anthropic

    return anthropic.Anthropic()


def kategorisera_en(klient, text: str, modell: str = MODELL) -> str:
    svar = klient.messages.create(
        model=modell,
        max_tokens=MAX_TOKENS,
        system=SYSTEM,
        messages=[{"role": "user", "content": text[:MAX_TECKEN]}],
    )
    delar = [block.text for block in svar.content if block.type == "text"]
    return normalisera("".join(delar))


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
                      sov=time.sleep) -> list[dict]:
    """Kategoriserar en text i taget och returnerar posterna med etikett.

    En text i taget, inte i batch: ett fel på en text ska kosta en text, och
    ett svar ska gå att spåra till sin fråga. Fel sväljs inte, men de stoppar
    inte heller resten: posten får etiketten `fel` och räknas för sig.
    """
    ut = []
    for nummer, post in enumerate(poster):
        try:
            etikett = kategorisera_en(klient, post["text"], modell)
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
    arg = tolk.parse_args(argv)

    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)
    poster = texter_att_kategorisera(arg.parfil, arg.besvarade,
                                     arg.obesvarade, domaner)
    if arg.max_poster:
        poster = poster[:arg.max_poster]

    print(f"mänskliga texter att kategorisera: {len(poster)}")
    if not poster:
        print("inget att göra")
        return 1

    klient = bygg_klient()
    kategoriserade = kategorisera_alla(klient, poster, arg.modell)

    arg.svarsfil.parent.mkdir(parents=True, exist_ok=True)
    with arg.svarsfil.open("w", encoding="utf-8") as fil:
        for post in kategoriserade:
            fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    sammanstallning = sammanstall(kategoriserade)
    skriv_rapport(sammanstallning, arg.utfil, len(kategoriserade), arg.modell)
    skriv_exempel(sammanstallning, arg.exempelfil)

    fordelning = Counter(p["etikett"] for p in kategoriserade)
    print(f"kategorier: {len(sammanstallning)}")
    print(f"  varav 'oklart': {fordelning.get('oklart', 0)}")
    print(f"  varav 'inget kundärende': {fordelning.get('inget kundärende', 0)}")
    print(f"  varav 'fel': {fordelning.get('fel', 0)}")
    print(f"utfil: {arg.utfil}")
    print(f"exempelfil, gitignorerad: {arg.exempelfil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
