"""Etiketterar de kundtexter som skiva 15 gjorde synliga, och BARA dem.

BAKGRUND. Miningens `in:sent` gjorde Gmail-etiketten SENT till ensam grund för
vilken skördefil en tråd hamnade i, se `docs/beslutslogg.md` #27. Följden var att
kundärenden utan svar som låg i besvarade-skörden räknades i INGEN kolumn i
`docs/kategorier-forslag.md`. Skiva 15 mätte upp dem till 66 unika texter.

VARFÖR INTE EN OMKÖRNING. Pass 2 är inte deterministiskt, se #18. En omkörning
av hela materialet hade flyttat tal som ingenting annat har ändrat, och tabellen
bär fas 4:s grind. Skriptet etiketterar därför bara de nya texterna och LÄGGER
TILL dem.

DE TVÅ PASSEN, samma som resten av korpusen gick igenom:

  FRI KLASSNING  `src/kategorisera.py`:s system. Den avgör vad som är
                 `inget kundärende` respektive `oklart`, och de två raderna i
                 tabellen kan bara växa här. Utan det steget hade varje ny text
                 tvingats in i en kundkategori.
  PASS 2         `src/ometikettera.py` mot den FASTA taxonomin i
                 `data/taxonomi.json`. Samma enum som förra gången, läst från
                 disk. Svar utanför listan rättas inte, de blir `utanför listan`.

IDEMPOTENS ÄR SKYDDET MOT DUBBELRÄKNING. En kandidat vars text redan står i
`data/kategorisvar.jsonl` etiketteras aldrig om. Körs skriptet två gånger gör den
andra körningen ingenting. Det skyddet är starkare än att lita på att antalet
råkar bli rätt, och det gäller oavsett hur kandidaterna härleddes.

DET SKYDDAR INTE MOT EN HALV KÖRNING. Nyckeln läses ur `kategorisvar.jsonl`, som
skrivs FÖRE pass 2. Faller processen mellan de två skrivningarna blir varje
senare körning en tyst nollkörning medan texterna aldrig nådde
`ometiketterade.jsonl`. Kontrollen mot det är att jämföra radantalen i de två
filerna; de ska växa lika mycket.

KOLUMNEN `Med svar` KAN INTE ÄNDRAS AV DEN HÄR KÖRNINGEN. Varje ny post får
`kalla: "utan svar"`, och inget befintligt ändras. Skriptet kontrollerar det mot
tabellen efteråt i stället för att påstå det.

§6: skriptets UTSKRIFTER bär enbart antal och etikettnamn, aldrig kundtext.
Till `data/` skriver det däremot kundtexten och sedan skiva 17 även ämnesraden,
som bär registreringsnummer i 77 av 78 formulärtrådar. Båda filerna ligger under
`data/`, som är gitignorerat, och `docs/kategorier-forslag.md` bär bara etikett
och antal.

    .venv/bin/python scripts/etikettera-nya.py             # torrkörning
    .venv/bin/python scripts/etikettera-nya.py --skarp     # anropar API:t
    .venv/bin/python scripts/etikettera-nya.py --redovisa  # etiketter per kanal
    .venv/bin/python scripts/etikettera-nya.py --rapport   # bygg om rapporten

Bara `--skarp` gör API-anrop. `--rapport` är den sanktionerade vägen att skriva
om `docs/kategorier-forslag.md` när texten i `src/ometikettera.py` ändrats men
etiketterna inte har det: filen är maskinproducerad enligt §0 och får inte
redigeras för hand.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from collections import Counter
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import kanal, kategorisera, klassa_maskin, ometikettera, urval  # noqa: E402

BESVARADE = ROT / "data" / "tradar.jsonl"
PAR = ROT / "data" / "par.jsonl"
KATEGORISVAR = ROT / "data" / "kategorisvar.jsonl"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
TAXONOMI = ROT / "data" / "taxonomi.json"
UTFIL = ROT / "docs" / "kategorier-forslag.md"

# Antalet skiva 15 mätte upp. Avviker körningen från det har något ändrats i
# underlaget, och då ska det synas i utskriften i stället för att passera.
VANTAT = 66


def las_grannskript(namn: str):
    """Importerar ett systerskript vars filnamn bär bindestreck.

    `import_module` duger inte: `besvarad-omklassning` är inget giltigt
    Python-namn. Importen finns för att populationen bakom de nya texterna ska
    härledas ur SAMMA kod som mätte den, inte ur en kopia som glider isär.
    """
    spec = importlib.util.spec_from_file_location(
        namn.replace("-", "_"), ROT / "scripts" / f"{namn}.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def las_jsonl(sokvag: Path) -> list[dict]:
    if not sokvag.exists():
        return []
    return [json.loads(rad)
            for rad in sokvag.read_text(encoding="utf-8").splitlines() if rad]


def lagg_till_jsonl(poster: list[dict], sokvag: Path) -> None:
    """LÄGGER TILL, skriver aldrig om. Filen bär kundtext och är gitignorerad."""
    rader = "".join(json.dumps(p, ensure_ascii=False) + "\n" for p in poster)
    with sokvag.open("a", encoding="utf-8") as fil:
        fil.write(rader)


def nya_texter() -> list[dict]:
    """De nya kundtexterna med sin KONTEXT, avdubblade, i filens ordning.

    Populationen kommer ur `scripts/besvarad-omklassning.py`. Filtret mot
    `kategorisvar.jsonl` är det som gör körningen idempotent.

    POSTERNA BÄR `amne` OCH `kanal`. Utan dem hade den här vägen, som är den
    enda sanktionerade körningen, skickat texterna utan den kontext skiva 17
    infördes för att ge dem. Kontexten tas från meddelandet direkt och inte via
    `kategorisera.kontext_per_text`: här finns meddelandet i handen, och en
    uppslagning på text hade bara kunnat bli sämre.
    """
    bo = las_grannskript("besvarad-omklassning")
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)
    redan = {p["text"] for p in las_jsonl(KATEGORISVAR)}

    sedda: set[str] = set()
    ut: list[dict] = []
    for _, m0 in bo.flyttande_kundarenden(BESVARADE, domaner):
        text = urval.brodtext(m0)
        if not text or text in redan or text in sedda:
            continue
        sedda.add(text)
        ut.append({"text": text, "kalla": "utan svar",
                   "amne": kanal.amnesrad(m0), "kanal": kanal.namnge(m0)})
    return ut


def skriv_om_rapporten() -> int:
    """Bygger om `docs/kategorier-forslag.md` ur `data/ometiketterade.jsonl`.

    INGA API-anrop och ingen ometikettering. Behövs när texten i
    `src/ometikettera.py::skriv_rapport` ändrats men etiketterna inte har det,
    eftersom filen är maskinproducerad och inte får skrivas för hand (§0).
    """
    taxonomi = json.loads(TAXONOMI.read_text(encoding="utf-8"))
    allt = las_jsonl(OMETIKETTERADE)
    sammanstallning = kategorisera.sammanstall(allt)
    ometikettera.skriv_rapport(sammanstallning, UTFIL, len(allt), taxonomi,
                               kategorisera.MODELL)
    kategorisera.skriv_exempel(sammanstallning, ometikettera.EXEMPELFIL)
    med = sum(r["med_svar"] for r in sammanstallning)
    utan = sum(r["utan_svar"] for r in sammanstallning)
    print(f"{UTFIL.name} omskriven ur {OMETIKETTERADE.name}")
    print(f"  texter {len(allt)}   med svar {med}   utan svar {utan}")
    return 0


def redovisa() -> int:
    """Etiketterna för de tillagda texterna, uppdelat på kanal.

    Mängden definieras som kandidaterna ur `flyttande_kundarenden` vars text
    inte står i `par.jsonl`. Skiva 15 mätte överlappet mot den obesvarade
    kolumnen till noll, så den mängden är de 66. Definitionen fungerar även
    efter att texterna etiketterats, till skillnad från `nya_texter`, som
    är idempotent och därför ger tomt efter en skarp körning.

    Inga API-anrop. Läser bara `data/`.
    """
    bo = las_grannskript("besvarad-omklassning")
    domaner = klassa_maskin.las_domaner(klassa_maskin.DOMANFIL)
    par = {p["inkommande_text"] for p in las_jsonl(PAR)}
    etikett = {p["text"]: p["etikett"] for p in las_jsonl(OMETIKETTERADE)}

    form: set[str] = set()
    ovriga: set[str] = set()
    for _, m0 in bo.flyttande_kundarenden(BESVARADE, domaner):
        text = urval.brodtext(m0)
        if not text or text in par:
            continue
        (form if bo.ar_formular(m0) else ovriga).add(text)

    print(f"tillagda texter: {len(form) + len(ovriga)}")
    print(f"  ur webbformuläret: {len(form)}")
    print(f"  ur övriga kanaler: {len(ovriga)}")
    for namn, mangd in (("WEBBFORMULÄRET", form), ("ÖVRIGA KANALER", ovriga)):
        print(f"\n=== {namn}")
        raknare = Counter(etikett.get(t, "<oetiketterad>") for t in mangd)
        for e, antal in raknare.most_common():
            print(f"  {e:38} {antal}")
    return 0


def kor(skarp: bool) -> int:
    texter = nya_texter()
    print(f"nya texter att etikettera: {len(texter)}")
    if len(texter) != VANTAT:
        print(f"  AVVIKER från skiva 15:s uppmätta {VANTAT}.")
        print("  Antingen har underlaget ändrats, eller så är de redan gjorda.")
    if not texter:
        print("  Ingenting att göra. Körningen är idempotent.")
        return 0

    if not skarp:
        print("\nTORRKÖRNING. Inga API-anrop, inga filer skrivna.")
        print(f"  --skarp skulle kosta {len(texter)} anrop i den fria")
        print("  klassningen, plus ett per text som inte blev")
        print("  `inget kundärende` eller `oklart`.")
        return 0

    taxonomi = json.loads(TAXONOMI.read_text(encoding="utf-8"))
    print(f"taxonomi läst från disk: {len(taxonomi)} kategorier")

    # Invarianten mäts FÖRE körningen, så kontrollen efteråt jämför mot ett
    # avläst värde och inte mot ett tal skrivet i källkoden.
    med_svar_fore = sum(1 for p in las_jsonl(OMETIKETTERADE)
                        if p["kalla"] == "med svar")
    print(f"med svar före körningen: {med_svar_fore}")

    klient = kategorisera.bygg_klient()
    atgang = kategorisera.Tokenatgang()

    print(f"\nFRI KLASSNING: {len(texter)} anrop")
    fria = kategorisera.kategorisera_alla(klient, texter, atgang=atgang)
    lagg_till_jsonl(fria, KATEGORISVAR)
    print(f"  tillagda i {KATEGORISVAR.name}")

    akta = ometikettera.akta_kundarenden(fria)
    ovriga = [p for p in fria if p["etikett"] in kategorisera.EJ_KUNDARENDE]
    print(f"\nPASS 2: {len(akta)} anrop"
          f"   ({len(ovriga)} etiketteras inte om)")
    ometiketterade = ometikettera.ometikettera_alla(
        klient, akta, taxonomi, atgang=atgang)

    nya_slutliga = ometiketterade + ovriga
    lagg_till_jsonl(nya_slutliga, OMETIKETTERADE)
    print(f"  tillagda i {OMETIKETTERADE.name}")

    print("\n=== FÖRDELNINGEN AV DE NYA")
    for etikett, antal in Counter(p["etikett"]
                                  for p in nya_slutliga).most_common():
        print(f"  {etikett:38} {antal}")
    utanfor = sum(1 for p in nya_slutliga
                  if p["etikett"] == ometikettera.UTANFOR)
    fel = sum(1 for p in nya_slutliga if p["etikett"] == "fel")
    print(f"\n  utanför taxonomin: {utanfor}")
    print(f"  fel i anropet:     {fel}")

    allt = las_jsonl(OMETIKETTERADE)
    sammanstallning = kategorisera.sammanstall(allt)
    med = sum(r["med_svar"] for r in sammanstallning)
    utan = sum(r["utan_svar"] for r in sammanstallning)

    print("\n=== TOKENÅTGÅNG, avläst ur API-svaren ===")
    for rad in atgang.redovisa():
        print(rad)

    # KONTROLLEN LIGGER FÖRE SKRIVNINGEN, inte efter. En tilläggskörning får
    # inte kunna röra kolumnen `Med svar`, och gör den det ska rapporten aldrig
    # skrivas. Efter skrivningen hade `docs/kategorier-forslag.md` redan varit
    # överskriven när felet upptäcktes.
    if med != med_svar_fore:
        print(f"\nSTOPP: `Med svar` gick från {med_svar_fore} till {med}.")
        print("En tilläggskörning ska inte kunna ändra den kolumnen.")
        print(f"{UTFIL.name} är INTE skriven. Datafilerna bär de nya posterna;")
        print("undersök dem innan du kör om.")
        return 1
    print(f"\n`Med svar` oförändrad: {med_svar_fore}")

    ometikettera.skriv_rapport(sammanstallning, UTFIL, len(allt), taxonomi,
                               kategorisera.MODELL)
    kategorisera.skriv_exempel(sammanstallning, ometikettera.EXEMPELFIL)
    print(f"{UTFIL.name} skriven: {len(allt)} texter, "
          f"med svar {med}, utan svar {utan}")
    return 0


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--skarp", action="store_true",
                      help="Gör API-anropen och skriv filerna. Utan flaggan "
                           "är körningen en torrkörning.")
    tolk.add_argument("--redovisa", action="store_true",
                      help="Etiketterna för de tillagda texterna per kanal. "
                           "Inga API-anrop.")
    tolk.add_argument("--rapport", action="store_true",
                      help="Skriv om docs/kategorier-forslag.md ur "
                           "data/ometiketterade.jsonl. Inga API-anrop.")
    args = tolk.parse_args(argv)
    if args.redovisa:
        return redovisa()
    if args.rapport:
        return skriv_om_rapporten()
    return kor(args.skarp)


if __name__ == "__main__":
    raise SystemExit(main())
