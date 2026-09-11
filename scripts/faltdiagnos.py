r"""Varför saknar uppslaget fält? Sparar råa sidor och jämför vad som STÅR i dem.

    .venv/bin/python scripts/faltdiagnos.py --katalog <utanför repot>

**SKARP TRAFIK MOT TREDJE PART, MED HÅRT TAK.** Skiva 37 DEL A, på Lars order:
MAX SEX BEGÄRAN, ingen loop, inget svep. Taket står som `TAK` nedan och
kontrolleras i koden, inte i huvudet på den som kör.

**FRÅGAN ÄR INTE OM FÄLTET PARSAS, UTAN OM DET STÅR PÅ SIDAN.** Tre hypoteser
som utesluter varandra, Lars formulering:

  1. Sidan visar färre fält för en UTLOGGAD hämtare än för en inloggad.
  2. Källan STRYPTE svaret efter flera anrop i följd.
  3. Fordonen SAKNAR uppgiften i registret.

Skriptet svarar på 1 och 3 genom att läsa den råa sidan. **En KUMULATIV hypotes 2
är redan utesluten utan en enda begäran:** skiva 36:s två körningar gav IDENTISKT
uppslagsutfall för samtliga tjugo ärenden, med lyckandena på samma platser i
båda. Det utesluter inte en deterministisk begränsning per fordon eller en cache,
och det är siddatan nedan som avgör den frågan.

*Här stod "alla tretton ärenden" och att det sista uppslaget LYCKADES i båda.
Tjugo ärenden fanns i båda, och det sista uppslaget MISSLYCKADES i båda. Fällt av
§7-granskningen av skiva 37, varv 1. Talen i `docs/beslutslogg.md` #78 rättades
en gång till i varv 2; den posten bär mätningen, den här raden bara slutsatsen.*

**§6: INGENTING SOM SKRIVS UT BÄR ETT REGISTRERINGSNUMMER.** Sidorna bär
ägaruppgifter och sparas därför UTANFÖR repot, till en katalog som anges på
kommandoraden. Filnamnen är löpnummer, inte fordonsidentiteter. Utdatan säger
vilka ETIKETTER som finns, aldrig vilket fordon som är vilket.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import biluppgifter, fordonsuppslag, maskera  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"

# **TAKET ÄR EN EGENSKAP HOS KODEN, inte en avsikt hos den som kör.** Lars order
# i skiva 37: max sex begäran. Räknaren nedan kastar, den varnar inte.
TAK = 6

# Etiketterna parsern letar efter. Lånade ur `biluppgifter.EXAKT_ETIKETT` i
# stället för skrivna på nytt: en kopia här hade kunnat glida isär och då mätt
# fel sak.
ETIKETTER = biluppgifter.EXAKT_ETIKETT

# Tecken på att sidan döljer något bakom en inloggning.
#
# **MÄTER FÖREKOMST, INTE POSITION.** Kommentaren sade tidigare att hypotes 1
# står och faller med om ett sådant ord står DÄR fältet skulle ha stått. Koden
# söker på hela sidan, alltså gör den inte den diskrimineringen. Att den ändå
# räcker beror på utfallet: `logga in` står på VARJE sida, också de som ger alla
# tre fälten, och inget av de övriga orden träffar någon sida. Ett positionstest
# hade behövts först om orden fördelat sig ojämnt. Fällt av §7-granskningen av
# skiva 37, varv 1.
INLOGGNINGSORD = ("logga in", "logga ditt", "premium", "biluppgifter plus",
                  "skapa konto", "låst", "prenumer")


class Takfel(Exception):
    """Fler begäran än Lars tillåtit."""


def _raknad_hamtare(tak: int = TAK):
    """Den riktiga hämtningen, med en räknare som KASTAR vid taket.

    **RÄKNAREN SITTER PÅ `_ett_forsok` OCH INTE PÅ `_hamta_sidan`, och den
    skillnaden är hela taket.** `_hamta_sidan` gör ETT OMFÖRSÖK vid nätverksfel,
    alltså upp till två faktiska HTTP-begäran per uppslag. En räknare runt den
    yttre funktionen hade tillåtit tolv begäran under ett tak som säger sex, och
    ett misslyckat första försök lämnar inget spår i artefakterna.

    Lars tak gällde BEGÄRAN mot tredje part, inte uppslag. Fällt av
    §7-granskningen av skiva 37, varv 1.

    **TAKET GÄLLER PER PROCESS och inget annat.** Två körningar ger två tak.
    Det står här därför att docstringen tidigare kallade taket "en egenskap hos
    koden": det är sant inom en körning, och den som kör två gånger har gjort
    ett eget val som ingen kod hindrar.
    """
    gjorda = {"n": 0}
    forsok = biluppgifter._ett_forsok

    def raknat_forsok(regnr: str) -> tuple[int, str]:
        if gjorda["n"] >= tak:
            raise Takfel(f"taket på {tak} begäran är nått, ingen till görs")
        gjorda["n"] += 1
        return forsok(regnr)

    def hamta(regnr: str) -> tuple[int, str]:
        # Omförsöket behålls, men varje försök räknas. `_hamta_sidan` läser
        # `_ett_forsok` ur modulen, alltså räcker det att byta där.
        tidigare = biluppgifter._ett_forsok
        biluppgifter._ett_forsok = raknat_forsok
        try:
            return biluppgifter._hamta_sidan(regnr)
        finally:
            biluppgifter._ett_forsok = tidigare

    return hamta, gjorda


def _regnr_i(text: str) -> str | None:
    traff = maskera.REGNR.search(text)
    return traff.group(0) if traff else None


def _arenden_med_regnr() -> list[str]:
    """Registreringsnumren i materialet, i materialets ordning.

    Returneras BARA till den här modulens eget bruk. Inget av dem skrivs ut.
    """
    rader = [
        json.loads(r)
        for r in OMETIKETTERADE.read_text(encoding="utf-8").splitlines()
        if r.strip()
    ]
    # **NORMALISERAS SAMMA VÄG SOM PRODUKTIONEN.** `slag_upp` gör
    # `normalisera_regnr` innan den anropar hämtningen, och en stor del av numren
    # i materialet bär mellanslag. Utan raden byggde skriptet en URL med
    # blanksteg i, fick `InvalidURL` klientsidan, och jag var nära att rapportera
    # det som ett produktionsfel. Det var skriptets fel: det gick förbi
    # `slag_upp`. En diagnos som inte går samma väg som koden mäter något annat
    # än koden.
    #
    # *Här stod "54 procent". Talet gick inte att räkna om: det berodde på hur
    # man räknar, per rad eller per unikt nummer, och inget committat skript
    # producerar det. §7.2: ett tal är avläst eller utelämnat.*
    nummer = []
    for post in rader:
        regnr = fordonsuppslag.normalisera_regnr(_regnr_i(post["text"]))
        if regnr and regnr not in nummer:
            nummer.append(regnr)
    return nummer


def _etikettrader(sida: str) -> dict[str, str]:
    r"""Varje `label`/`value`-par på sidan, som etikett till rått värde.

    **EXAKT ETIKETT, INTE DELSTRÄNG, och den skillnaden är hela mätningen.**
    Första lydelsen frågade `etikett in sida`. Det gav JA för `Släpvagnsvikt` på
    en sida vars enda rad är `Släpvagnsvikt obromsad`, eftersom den ena
    strängen innehåller den andra. Jag läste utdatan som att etiketten fanns och
    parsern missade den, vilket var fel diagnos: fältet fanns inte.

    Sidans form, avläst 2026-09-11: etikett och värde ligger i var sin
    `<span>`, med `class="label"` respektive `class="value"`, åtskilda av
    radbrytning och indrag inuti ett `<li>`. Mönstret tål det med `\s*` och
    `DOTALL`.

    *Här stod formen som en enda rad, `<li><span class="label">X</span>
    <span class="value">Y</span></li>`. Den formen står inte på sidan: en
    literal sökning efter den ger noll träffar på samtliga sex sparade sidor.
    Mätningen är riktig, men "avläst" om en form som inte står där är precis vad
    §7.2 finns för. Fällt av §7-granskningen av skiva 37, varv 1.*

    **DUBBLETTER SKILJS INTE.** Returnerar en dict, alltså behålls sista värdet
    om en etikett står två gånger. `biluppgifter._las_falt` har en egen
    tvetydighetsspärr för det fallet, så en dubblerad etikett skulle här
    rapporteras som STÅR MEN TOLKAS EJ fast spärren gjorde rätt. Gäller inte det
    här stickprovet: varje etikett förekommer högst en gång per sida, avläst.
    """
    par = re.findall(
        r'<span class="label">(.*?)</span>\s*<span class="value">(.*?)</span>',
        sida,
        flags=re.DOTALL,
    )
    return {html.unescape(re.sub(r"<[^>]+>", "", e)).strip():
            html.unescape(re.sub(r"<[^>]+>", "", v)).strip()
            for e, v in par}


def _granska_sidan(sida: str) -> dict:
    """Vad som FAKTISKT står på sidan, utan att tolka det.

    Skiljer de lägen som annars ser likadana ut i `slag_upp`:s utfall: etiketten
    finns inte alls, etiketten finns men värdet gick inte att tolka, och sidan
    bär ett inloggningstecken.
    """
    lag = sida.lower()
    rader = _etikettrader(sida)
    return {
        "tecken": len(sida),
        "etiketter": {n: (e in rader) for n, e in ETIKETTER.items()},
        # Det RÅA värdet för varje etikett som finns. Det är här skillnaden
        # mellan "saknas i registret" och "parsern tar inte formen" syns.
        "ravarden": {n: rader.get(e, "") for n, e in ETIKETTER.items()},
        "inloggningsord": sorted({o for o in INLOGGNINGSORD if o in lag}),
    }


def _las_sparat(katalog: Path) -> int:
    """Analyserar redan hämtade sidor. INGEN nättrafik, inget mot taket.

    Finns för att diagnosen ska gå att RÄKNA OM utan att röra källan igen.
    Första analysen bar en delsträngsträff och gav fel svar; att rätta den fick
    inte kosta sex nya begäran.
    """
    sidor = sorted(katalog.glob("sida-*.html"))
    if not sidor:
        print(f"inga sparade sidor i {katalog}")
        return 1

    print(f"{len(sidor)} sparade sidor, ingen nättrafik\n")
    summering = {"komplett": 0, "saknas_pa_sidan": 0, "star_men_tolkas_ej": 0}

    for fil in sidor:
        sida = fil.read_text(encoding="utf-8")
        granskning = _granska_sidan(sida)
        try:
            last = biluppgifter._las_falt(sida)
        # Brett fånget med flit: vilken parsningsdefekt som helst ska synas
        # i utdatan i stället för att stoppa diagnosen.
        except Exception as fel:
            last = {}
            print(f"{fil.name}  FEL: {type(fel).__name__}: {fel}")

        print(f"{fil.name}  {granskning['tecken']:>7} tecken")
        for nyckel, etikett in ETIKETTER.items():
            finns = granskning["etiketter"][nyckel]
            tolkat = nyckel in last
            ravarde = granskning["ravarden"][nyckel]
            if not finns:
                dom = "SAKNAS PÅ SIDAN"
                summering["saknas_pa_sidan"] += 1
            elif tolkat:
                dom = "läst"
                summering["komplett"] += 1
            else:
                dom = f"STÅR PÅ SIDAN MEN TOLKAS EJ, rått värde {ravarde!r}"
                summering["star_men_tolkas_ej"] += 1
            print(f"    {etikett:<16} {dom}")
        print()

    print("SUMMERING över de tre fälten på varje sida:")
    for namn, antal in summering.items():
        print(f"  {namn:<20} {antal}")
    return 0


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--katalog", required=True,
                      help="katalog UTANFÖR repot för de råa sidorna (§6)")
    argp.add_argument("--antal", type=int, default=TAK)
    argp.add_argument("--paus", type=float, default=2.0)
    argp.add_argument("--las-sparat", action="store_true",
                      help="analysera redan sparade sidor, INGEN nättrafik")
    args = argp.parse_args()

    katalog = Path(args.katalog).resolve()
    if ROT in katalog.parents or katalog == ROT:
        print("STOPP: katalogen ligger i repot. Sidorna bär ägaruppgifter (§6).")
        return 2

    if args.antal > TAK:
        print(f"STOPP: {args.antal} överskrider taket {TAK}.")
        return 2

    if args.las_sparat:
        return _las_sparat(katalog)

    katalog.mkdir(parents=True, exist_ok=True)
    hamta, gjorda = _raknad_hamtare()
    nummer = _arenden_med_regnr()

    print(f"material: {len(nummer)} unika registreringsnummer")
    print(f"tak: {TAK} begäran, denna körning: {args.antal}")
    print(f"sidor sparas i {katalog}, UTANFÖR repot\n")

    utfall = []
    for i, regnr in enumerate(nummer[:args.antal]):
        if i:
            time.sleep(args.paus)

        try:
            status, sida = hamta(regnr)
        except Takfel as fel:
            print(f"STOPPAD: {fel}")
            break

        (katalog / f"sida-{i:02d}.html").write_text(sida, encoding="utf-8")

        # Vad SÖMMEN gör av samma sida, så att skillnaden mellan "står inte på
        # sidan" och "gick inte att tolka" syns.
        try:
            last = biluppgifter._las_falt(sida)
            felet = ""
        # Brett fånget med flit: vilken parsningsdefekt som helst ska synas
        # i utdatan i stället för att stoppa diagnosen.
        except Exception as fel:
            last, felet = {}, f"{type(fel).__name__}: {fel}"

        granskning = _granska_sidan(sida)
        utfall.append({"i": i, "status": status, **granskning,
                       "last": sorted(last), "fel": felet})

        etiketter = " ".join(
            f"{n.split('_')[0]}={'JA' if v else 'NEJ'}"
            for n, v in granskning["etiketter"].items()
        )
        print(f"sida {i:02d}  status {status}  {granskning['tecken']:>7} tecken  "
              f"{etiketter}")
        print(f"          parsern läste: {sorted(last) or 'inget'}"
              + (f"   FEL: {felet}" if felet else ""))
        if granskning["inloggningsord"]:
            print(f"          inloggningsord: {granskning['inloggningsord']}")

    print(f"\nbegäran gjorda: {gjorda['n']} av taket {TAK}")
    (katalog / "utfall.json").write_text(
        json.dumps(utfall, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"sammanfattning i {katalog / 'utfall.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
