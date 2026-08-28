"""Statusraden §12 kräver, producerad ur repot och aldrig för hand.

§12 kräver en maskinproducerad statusrad över kategorierna som aldrig skrivs för
hand, och som redovisar antal kategorier per hink, antal mail per kategori, och
datum för senaste mining. Lydelsen står i CLAUDE.md och återges inte ordagrant
här, eftersom en avskrift föråldras av varje ändring i regeln.

**§12 SÄGER "MAIL", OCH SKRIPTET RÄKNAR TEXTER.** Skillnaden är verklig och ska
inte döljas: `src/kategorisera.py` avdubblar per kundtext och tar ett meddelande
per tråd, så en kategori med tio texter kan vila på fler mail än tio. Texten är
den enhet resten av systemet räknar i, och kolumnerna heter därför `Texter`.

Skriptet fanns inte förrän skiva 18, och §12 föreskrev under tiden att hålet
skulle namnges i varje rapport i stället för att fyllas för hand. Se
`docs/beslutslogg.md` #30.

KÄLLORNA, alla i arbetsträdet men inte alla committade:

- `config/kategorier.yaml`      hinkarna. `auto` och `aldrig` räknas upp,
                                allt annat faller till `standardhink`. Spårad.
- `data/ometiketterade.jsonl`   etiketten per text, med `kalla`. Ocommittad,
                                eftersom `.gitignore` utesluter hela `data/`.
                                Den får dessutom inte committas: den bär
                                kundtext, och §6 förbjuder det.
- `data/taxonomi.json`          taxonomin, så att en kategori med NOLL texter
                                syns i stället för att försvinna. Ocommittad av
                                samma katalogregel, men den bär inga
                                kundtexter: skälen ska inte slås ihop.
- `docs/mining-log.md`          datum för senaste körning mot brevlådan. Spårad.

FÖLJDEN ÄR ATT EN FÄRSK KLON INTE KAN PRODUCERA RADEN. Två av källorna ligger
under `data/`. Det är inte en brist i skriptet, men det ska inte komma som en
överraskning.

EN SAKNAD ELLER OLÄSLIG KÄLLA ÄR ETT STOPP, inte en tystnad. Skriptet skriver ut
vilken fil det gäller och avslutar med exit 1. En halv statusrad ser komplett ut
och är värre än ett namngivet hål: det är hela skälet till att §12 hellre lät
raden utebli än att någon skrev den för hand.

§6: skriptet skriver ENBART antal, kategorinamn och ett datum. Aldrig kundtext.

    .venv/bin/python scripts/kategoristatus.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import kategorisera, ometikettera  # noqa: E402

HINKFIL = ROT / "config" / "kategorier.yaml"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
TAXONOMIFIL = ROT / "data" / "taxonomi.json"
MININGLOGG = ROT / "docs" / "mining-log.md"

HINKAR = ("auto", "utkast", "aldrig")

# Raden i mining-loggens tabell. Datumet står först och gör raden entydig:
# tabellhuvudet och avgränsarraden bär inget datum och matchar därför inte.
MININGRAD = re.compile(r"^\|\s*(\d{4}-\d{2}-\d{2}[^|]*?)\s*\|")

# Statusen står i tabellens sista kolumn. `src/mine.py` loggar även en körning
# som faller, och `docs/mining-log.md` skriver att `AVBRUTEN` betyder att
# `data/tradar.jsonl` INTE uppdaterades. En avbruten körning är alltså en
# körning som kostat kvot men inte gett material, och statusraden får inte
# redovisa den som om den gjort det.
FULLSTANDIG = "fullständig"


class Saknas(Exception):
    """En källa saknas. Statusraden kan inte produceras."""


def namnge(sokvag: Path) -> str:
    """Sökvägen relativt repot när den ligger där, annars i sin helhet.

    `relative_to` KASTAR för en sökväg utanför repot, och den vägen är inte
    hypotetisk: varje `--hinkar` som pekar någon annanstans går den. Utan det
    här föll felhanteringen med ett ValueError i stället för att skriva ut
    vilken fil som saknades, alltså precis i det läge skriptet finns för.
    """
    try:
        return str(sokvag.relative_to(ROT))
    except ValueError:
        return str(sokvag)


def las_text(sokvag: Path) -> str:
    """Filens innehåll, eller `Saknas` med filen namngiven.

    EN FIL SOM FINNS MEN INTE GÅR ATT LÄSA ÄR SAMMA HÅL som en som saknas.
    Utan det här gav en katalog i stället för en fil `IsADirectoryError` som
    traceback, alltså precis det utfall skriptet finns för att undvika. Samma
    klass av fel som `namnge` byggdes för.
    """
    if not sokvag.exists():
        raise Saknas(f"{namnge(sokvag)} finns inte")
    try:
        return sokvag.read_text(encoding="utf-8")
    except OSError as fel:
        raise Saknas(f"{namnge(sokvag)} går inte att läsa: "
                     f"{type(fel).__name__}") from fel
    except UnicodeDecodeError as fel:
        raise Saknas(f"{namnge(sokvag)} är inte UTF-8") from fel


def las_hinkar(sokvag: Path) -> dict:
    try:
        data = yaml.safe_load(las_text(sokvag))
    except yaml.YAMLError as fel:
        raise Saknas(f"{namnge(sokvag)} är inte giltig YAML") from fel
    if not isinstance(data, dict):
        raise Saknas(f"{namnge(sokvag)} bär {type(data).__name__}, "
                     "inte en tabell med hinkar")
    standard = data.get("standardhink")
    if standard not in HINKAR:
        raise Saknas(f"{namnge(sokvag)}: standardhink saknas "
                     f"eller är okänd ({standard!r})")
    if standard == "auto":
        raise Saknas(f"{namnge(sokvag)}: standardhink får inte vara `auto`. "
                     "En kategori ingen tagit ställning till hade då blivit "
                     "sändbar av att någon lade till den i taxonomin.")
    return data


def hink_for(etikett: str, hinkar: dict) -> str:
    """Kategorins hink.

    Ordningen är `auto` före `aldrig` före standardhinken, men den spelar
    ingen roll i praktiken: `tests/test_kategorier_yaml.py` binder att ingen
    kategori står i två hinkar. Skulle den vakten falla vore det bättre att
    utfallet blev synligt än tyst, och därför larmar funktionen i stället för
    att välja.
    """
    i_auto = etikett in (hinkar.get("auto") or [])
    i_aldrig = etikett in (hinkar.get("aldrig") or [])
    if i_auto and i_aldrig:
        raise Saknas(f"{etikett!r} står i både auto och aldrig")
    if i_auto:
        return "auto"
    if i_aldrig:
        return "aldrig"
    return hinkar["standardhink"]


def las_antal(sokvag: Path) -> dict[str, dict]:
    """Antal texter per etikett, uppdelat på `kalla`.

    En trasig rad namnges med sitt RADNUMMER, inte med sitt innehåll: raderna
    bär kundtext och får inte skrivas ut (§6).
    """
    per: dict[str, dict] = {}
    for nummer, rad in enumerate(las_text(sokvag).splitlines(), start=1):
        if not rad:
            continue
        try:
            post = json.loads(rad)
            etikett = post["etikett"]
            kalla = post["kalla"]
        except (json.JSONDecodeError, KeyError, TypeError) as fel:
            raise Saknas(f"{namnge(sokvag)} rad {nummer} går inte att läsa: "
                         f"{type(fel).__name__}") from fel
        rad_ = per.setdefault(etikett,
                              {"totalt": 0, "med_svar": 0, "utan_svar": 0})
        rad_["totalt"] += 1
        if kalla == "med svar":
            rad_["med_svar"] += 1
        else:
            rad_["utan_svar"] += 1
    return per


def las_taxonomi(sokvag: Path) -> list[str]:
    try:
        data = json.loads(las_text(sokvag))
    except json.JSONDecodeError as fel:
        raise Saknas(f"{namnge(sokvag)} är inte giltig JSON") from fel
    if not isinstance(data, list):
        raise Saknas(f"{namnge(sokvag)} bär {type(data).__name__}, "
                     "inte en lista med kategorinamn")
    return data


def senaste_mining(sokvag: Path) -> tuple[str, str]:
    """Datum OCH status ur SISTA tabellraden i mining-loggen.

    Sista och inte största: raden skrivs in sist i tabellen av `src/mine.py` i
    kronologisk ordning. En sortering hade tyst rättat en logg som var i
    oordning, och den oordningen är i så fall det som ska synas.

    STATUSEN FÖLJER MED, och det är inte pynt. `src/mine.py` loggar även en
    körning som faller, och `docs/mining-log.md` skriver att `AVBRUTEN` betyder
    att `data/tradar.jsonl` INTE uppdaterades. En statusrad som redovisar ett
    datum utan sin status hade alltså kunnat påstå färskt material där det bara
    fanns förbrukad kvot.
    """
    rader = []
    for rad in las_text(sokvag).splitlines():
        if not MININGRAD.match(rad):
            continue
        falt = [f.strip() for f in rad.strip().strip("|").split("|")]
        rader.append((falt[0], falt[-1]))
    if not rader:
        raise Saknas(f"{namnge(sokvag)} bär ingen körning")
    return rader[-1]


def alla_kategorier(antal: dict[str, dict], taxonomi: list[str],
                    hinkar: dict) -> list[str]:
    """Taxonomin, det som faktiskt förekommer, och det hinkarna namnger.

    Unionen och inte bara taxonomin: `inget kundärende`, `oklart`, `fel` och
    `utanför listan` är etiketter en text kan bära utan att stå i taxonomin.
    Och en kategori som en hink namnger men som inte finns någonstans är ett
    fynd som ska synas, inte utelämnas.
    """
    namn = set(taxonomi) | set(antal)
    namn |= set(hinkar.get("auto") or [])
    namn |= set(hinkar.get("aldrig") or [])
    return sorted(namn)


def statusrader(hinkar: dict, antal: dict[str, dict], taxonomi: list[str],
                mining: tuple[str, str],
                kallor: dict[str, Path] | None = None) -> list[str]:
    """Statusraden. `kallor` namnger var talen kommer ifrån.

    HÄRKOMSTEN STÅR I RADEN, och det är inte pynt. Flaggorna gör det möjligt att
    producera raden ur godtyckliga filer, och utan källorna utskrivna vore en
    sådan rad teckenidentisk med en producerad ur repot. §12:s krav är att raden
    inte ska gå att skriva för hand; en rad utan härkomst går att skriva för hand
    med en omväg.
    """
    kategorier = alla_kategorier(antal, taxonomi, hinkar)
    per_hink: dict[str, list[str]] = {h: [] for h in HINKAR}
    for namn in kategorier:
        per_hink[hink_for(namn, hinkar)].append(namn)

    rader = ["=== KATEGORISTATUS", ""]
    rader.append("Kategorier och texter per hink:")
    rader.append("")
    rader.append("| Hink | Kategorier | Texter | Med svar | Utan svar |")
    rader.append("| --- | --- | --- | --- | --- |")
    for hink in HINKAR:
        namn = per_hink[hink]
        totalt = sum(antal.get(n, {}).get("totalt", 0) for n in namn)
        med = sum(antal.get(n, {}).get("med_svar", 0) for n in namn)
        utan = sum(antal.get(n, {}).get("utan_svar", 0) for n in namn)
        rader.append(f"| {hink} | {len(namn)} | {totalt} | {med} | {utan} |")

    alla_texter = sum(r["totalt"] for r in antal.values())
    datum, status = mining
    rader += ["", f"Texter i underlaget: {alla_texter}",
              f"Senaste mining: {datum} ({status})"]
    if status != FULLSTANDIG:
        rader.append("  VARNING: den senaste körningen är inte fullständig.")
        rader.append("  `data/tradar.jsonl` uppdaterades inte av den, så talen")
        rader.append("  ovan vilar på en tidigare körning.")
    rader.append("")

    if kallor:
        rader.append("Källor:")
        for namn, sokvag in kallor.items():
            rader.append(f"  {namn:11} {namnge(sokvag)}")
        rader.append("")

    rader.append("Per kategori, fallande på antal texter:")
    rader.append("")
    rader.append("| Kategori | Hink | Totalt | Med svar | Utan svar |")
    rader.append("| --- | --- | --- | --- | --- |")
    for namn in sorted(kategorier,
                       key=lambda n: (-antal.get(n, {}).get("totalt", 0), n)):
        rad = antal.get(namn, {"totalt": 0, "med_svar": 0, "utan_svar": 0})
        rader.append(f"| {namn} | {hink_for(namn, hinkar)} | {rad['totalt']} "
                     f"| {rad['med_svar']} | {rad['utan_svar']} |")

    tomma = [n for n in kategorier if antal.get(n, {}).get("totalt", 0) == 0]
    if tomma:
        rader += ["", "KATEGORIER UTAN TEXTER: " + ", ".join(tomma)]
        rader.append("  En hink som namnger en kategori utan texter är inte ett")
        rader.append("  fel i sig, men den bär inget mallunderlag.")

    ej_kategori = [n for n in kategorier
                   if n in kategorisera.EJ_KUNDARENDE
                   or n == ometikettera.UTANFOR]
    if ej_kategori:
        rader += ["", "RADER SOM INTE ÄR KUNDKATEGORIER: "
                  + ", ".join(sorted(ej_kategori))]
        rader.append("  De står med för att tabellen ska täcka hela materialet.")
    return rader


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--hinkar", type=Path, default=HINKFIL)
    tolk.add_argument("--etiketter", type=Path, default=OMETIKETTERADE)
    tolk.add_argument("--taxonomi", type=Path, default=TAXONOMIFIL)
    tolk.add_argument("--mining", type=Path, default=MININGLOGG)
    arg = tolk.parse_args(argv)

    kallor = {"hinkar": arg.hinkar, "etiketter": arg.etiketter,
              "taxonomi": arg.taxonomi, "mining": arg.mining}
    try:
        rader = statusrader(
            las_hinkar(arg.hinkar),
            las_antal(arg.etiketter),
            las_taxonomi(arg.taxonomi),
            senaste_mining(arg.mining),
            kallor,
        )
    except Saknas as fel:
        print("STATUSRADEN KAN INTE PRODUCERAS.")
        print(f"  {fel}")
        print("  §12 förbjuder en handskriven ersättning. Skriv ut hålet.")
        return 1

    print("\n".join(rader))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
