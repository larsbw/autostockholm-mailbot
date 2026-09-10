#!/usr/bin/env python3
"""Kör KEDJAN mot verkliga mail och skriver ut vad som händer i varje steg.

    .venv/bin/python scripts/kedja-prov.py --antal 10

**INGEN SÄNDNING.** Skriptet importerar `src.kedja`, som saknar sändväg i hela
sin importgraf, prövat av `vy.krav_pa_sandvagsfrihet`. Det finns ingen
`--send` här och ingen väg till en brevlåda.

**UPPSLAGET ÄR KONSTRUERAT, och det står i utdatan vid varje fall.** Mailen är
VERKLIGA och klassificeringen och genereringen är riktiga API-anrop, men
hämtningen träffar inte biluppgifter.se. En skarp begäran mot den källan är
något Lars godkänner styckevis, se `docs/beslutslogg.md` #44, och tio körningar
är inte styckevis.

Källan svarar utifrån registreringsnumrets sista siffra, så att alla fyra
utfallen och båda misslyckandena går att se i en och samma körning. Det är en
FIXTUR och inget påstående om de bilarna.

**§6: ALLT SOM SKRIVS UT ÄR MASKERAT.** Kundtexten och utkastet går genom samma
maskering som `scripts/generera-prov.py` använder, alltså identifierare plus
namnkandidater ur mailet och ur få-exemplen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import prov_stod  # noqa: E402
from src import generera, kategorisera, kedja, maskera, vy  # noqa: E402
from src.kedja import Arende, Kallfel  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
HINKFIL = ROT / "config" / "kategorier.yaml"


def _regnr_i(text: str) -> str | None:
    """Första registreringsnumret i texten, om något.

    Återanvänder `maskera.REGNR` i stället för ett eget mönster. Skiva 11:s
    lärdom i `docs/sparrar.md` gäller åt andra hållet, alltså att ett mönster
    som lånas från en maskering är för SNÄVT för att hitta allt, och det är
    acceptabelt här: hittas inget regnr blir uppslaget ett misslyckande, vilket
    är ett av de vägar som ska synas i utdatan.
    """
    traff = maskera.REGNR.search(text)
    return traff.group(0) if traff else None


def bygg_fixturkalla():
    """En hämtning som täcker alla vägar, styrd av sista siffran.

    **INGEN NÄTTRAFIK.** Returnerar `None` för att visa vägen `okänt fordon`, och
    kastar `ConnectionError` för att visa vägen `källan är nere`, som är den
    `src.kedja` skiljer från den första.
    """
    def hamta(regnr: str) -> dict | None:
        siffror = [t for t in regnr if t.isdigit()]
        sista = int(siffror[-1]) if siffror else 0

        if sista == 7:
            raise ConnectionError("fixtur: källan svarar inte")
        if sista == 8:
            return None

        # Grönt, gult, oklart och rött, styrt av sista siffran.
        if sista <= 2:
            return {"tjanstevikt_kg": 1450, "slapvagnsvikt_kg": 1500,
                    "draganordning": True}
        if sista <= 4:
            return {"tjanstevikt_kg": 1450, "slapvagnsvikt_kg": 1500,
                    "draganordning": False}
        return {"tjanstevikt_kg": 980, "slapvagnsvikt_kg": 600,
                "draganordning": False}

    return hamta


def _a_traktor_spritt(a_traktor: list[dict], antal: int) -> list[dict]:
    """`antal` a-traktorärenden SPRIDDA över de tre kategorierna.

    **SKÄLET ÄR BALANSEN, inte att en kategori annars saknas.** Ett naivt urval
    på längd, `a_traktor[5:25]`, ger `fråga 11, pris 5, boka 4`, alltså alla tre
    kategorierna men med den ena nästan tre gånger den andra. Rundgången ger
    `7, 6, 7`. Med tjugo utkast att läsa är det skillnaden mellan att se hur
    generatorn hanterar en bokning och att se elva varianter av samma fråga.

    Räcker en kategori inte till fylls resten ur de andra, och det behöver inte
    vara jämnt: materialet är ojämnt fördelat och urvalet ska inte låtsas annat.

    *Här stod att de kortaste "ligger samlade i en kategori" och att ett naivt
    urval därför visar tjugo utkast ur samma kategori. Mätt mot
    `data/ometiketterade.jsonl` med funktionens egen sorteringsnyckel är det
    falskt: alla tre kategorierna finns i det naiva urvalet. Fällt av
    §7-granskningen av skiva 35, varv 1.*
    """
    per_kategori: dict[str, list[dict]] = {}
    for post in a_traktor:
        per_kategori.setdefault(post["etikett"], []).append(post)

    valda: list[dict] = []
    while len(valda) < antal:
        lade_till = False
        for kategori in sorted(per_kategori):
            if len(valda) >= antal:
                break
            if per_kategori[kategori]:
                valda.append(per_kategori[kategori].pop(0))
                lade_till = True
        if not lade_till:
            break  # materialet är slut, och då är det slut

    return valda


def las_arenden(antal: int, bara_a_traktor: bool = False) -> list[dict]:
    """Verkliga mail ur materialet: HÄLFTEN a-traktor, hälften annat.

    Med `bara_a_traktor` blir det i stället `antal` a-traktorärenden spridda
    över de tre kategorierna. Läget finns för skiva 35:s DEL B, där vyn ska bära
    a-traktorutkast som Lars läser. **FLAGGAN ÄNDRAR INTE `--antal`:s
    DEFAULTVÄRDE TIO**, alltså är kommandot som gav skivans utfall
    `--antal 20 --bara-a-traktor`. Räcker materialet inte till blir det färre,
    se `_a_traktor_spritt`.

    **A-TRAKTOR MÅSTE VARA MED, och det är fällt fram.** Ett första urval tog en
    per etikett i bokstavsordning och fick då noll a-traktorärenden på tio
    platser. Följden var att uppslaget hoppades över i samtliga tio, alltså
    prövade körningen aldrig den väg fas 4.5 gatar. Ett prov som missar sin
    huvudväg är inget prov.

    Resten är andra kategorier, så att klassificeringen prövas mot mer än
    a-traktor och så att den ogatade vägen syns bredvid den gatade.
    """
    rader = [
        json.loads(r)
        for r in OMETIKETTERADE.read_text(encoding="utf-8").splitlines()
        if r
    ]
    kundarenden = [
        p for p in rader
        if p["text"].strip() and p["etikett"] != "inget kundärende"
    ]

    a_traktor = sorted(
        (p for p in kundarenden if p["etikett"] in kedja.A_TRAKTORKATEGORIER),
        key=lambda p: len(p["text"]),
    )
    ovriga = sorted(
        (p for p in kundarenden if p["etikett"] not in kedja.A_TRAKTORKATEGORIER),
        key=lambda p: (p["etikett"], len(p["text"])),
    )

    # Hoppar över de allra kortaste, som ofta är fragment utan fråga. Samma
    # skäl som `prov_stod.las_forfragningar` anger.
    if bara_a_traktor:
        return _a_traktor_spritt(a_traktor[5:], antal)

    halva = antal // 2
    valda = a_traktor[5 : 5 + halva]

    sedda: set[str] = set()
    for post in ovriga:
        if len(valda) >= antal:
            break
        if post["etikett"] in sedda:
            continue
        valda.append(post)
        sedda.add(post["etikett"])

    return valda[:antal]


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--antal", type=int, default=10)
    argp.add_argument("--bara-a-traktor", action="store_true",
                      help="bara a-traktorärenden, spridda över de tre kategorierna")
    argp.add_argument("--vy", action="store_true",
                      help="starta vyn på fallen i stället för att bara skriva ut")
    argp.add_argument("--port", type=int, default=8765)
    args = argp.parse_args()

    if not OMETIKETTERADE.exists():
        print("saknas: data/ometiketterade.jsonl")
        return 1

    vy.krav_pa_sandvagsfrihet("src.kedja")
    print("SPÄRR: src.kedja är sändvägsfri i hela importgrafen.")

    import yaml
    hinkar = yaml.safe_load(HINKFIL.read_text(encoding="utf-8"))
    taxonomi = json.loads(
        kedja.TAXONOMIFIL.read_text(encoding="utf-8")
    )

    exempel = generera.las_exempel()
    klient = kategorisera.bygg_klient()
    hamta = bygg_fixturkalla()

    # AVSÄNDARHASH OCH TIDSSTÄMPEL kommer ur `par.jsonl`, samma väg vyn tar.
    # `ometiketterade.jsonl` bär bara `etikett`, `kalla` och `text`, alltså blir
    # loggraderna oattribuerbara utan den här kopplingen, och en logg som inte
    # går att koppla till ett ärende är ett svagt underlag för skuggläget.
    parkarta = vy._par_karta(vy.PAR)

    poster = las_arenden(args.antal, bara_a_traktor=args.bara_a_traktor)
    print(f"få-exempel: {len(exempel)}   taxonomi: {len(taxonomi)} kategorier"
          f"   ärenden: {len(poster)}")
    print("UPPSLAGET ÄR EN FIXTUR, ingen nättrafik mot biluppgifter.se.\n")

    raknare = {"utkast": 0, "spärrad": 0, "källfel": 0}
    granskningsfall = []

    for nummer, post in enumerate(poster, start=1):
        regnr = _regnr_i(post["text"])
        par = parkarta.get(post["text"], {})
        arende = Arende(
            text=post["text"],
            amne=post.get("amne", ""),
            regnr=regnr,
            avsandare_hash=par.get("avsandare_hash", ""),
            tidsstampel=par.get("tidsstampel", ""),
        )

        print("=" * 72)
        print(f"ÄRENDE {nummer}   ETIKETT I MATERIALET: {post['etikett']}")
        print(f"REGNR HITTAT: {'ja' if regnr else 'nej'}")
        print("")
        print("KUNDENS MAIL, maskerat:")
        print(maskera.maska_fritext(post["text"]).strip()[:400])
        print("")

        try:
            utfall = kedja.kor(
                arende, klient=klient, hamta=hamta, hinkar=hinkar,
                taxonomi=taxonomi, exempel=exempel,
            )
        except Kallfel as fel:
            raknare["källfel"] += 1
            # LOGGAS, precis som varje annat utfall. Ett driftavbrott som inte
            # lämnar en rad ser i skuggläget ut som ett ärende som aldrig kom
            # in.
            kedja.logga_kallfel(arende, fel)
            print(f"KEDJAN STOPPAD: {fel}")
            print("Inget utkast. Ett driftavbrott är inte ett okänt fordon.\n")
            continue

        for steg in utfall.steg:
            rad = f"  {steg.namn:<16} {steg.utfall}"
            if steg.detalj:
                rad += f"   ({steg.detalj})"
            print(rad)

        kedja.logga_beslut(arende, utfall)
        granskningsfall.append(kedja.till_granskningsfall(arende, utfall))

        if utfall.blev_utkast:
            raknare["utkast"] += 1
            print("\nUTKAST, maskerat:")
            print(prov_stod.maska_svaret(
                utfall.utkast, post["text"], exempel).strip())
        else:
            raknare["spärrad"] += 1
            print(f"\nSPÄRRAD av {utfall.sparr}")
            # SKÄLET MASKERAS. Det byggs av strängar lyfta ordagrant ur
            # modellens svar, alltså kan det bära ett telefonnummer eller ett
            # regnr. Fällt av §7-granskningen av skiva 34, varv 1.
            print(f"skäl: {maskera.maska_fritext(utfall.skal)}")
        print("")

    print("=" * 72)
    print("SUMMERING")
    for nyckel in sorted(raknare):
        print(f"  {nyckel:<10} {raknare[nyckel]}")
    print(f"\nLoggat till {kedja.BESLUTSLOGG.relative_to(ROT)}")

    # VÄGENS SLUTPUNKT. Utan raden slutar kedjan i stdout, och rutten
    # `/granskning/N` renderar "Inga förslag". Skriptet STARTAR ingen server:
    # det visar bara att fallen går att lämna till vyn, och `--vy` gör det.
    if args.vy:
        # VARNINGEN FÖLJER MED IN I VYN. Utkasten bär vikter ur fixturen, och
        # ett utkast som lyder "Tjänstevikten är 980 kg" ser ut som avläst
        # fordonsdata. Skriptets docstring och stdout säger det redan, men vyn
        # är det Lars läser, och sidan lever kvar i en flik långt efter att
        # terminalen rullat vidare.
        server = vy.starta(
            args.port, fall=[], granskning=granskningsfall,
            varning="UPPSLAGET ÄR EN FIXTUR. Vikter och dragkroksbesked i "
                    "utkasten nedan är konstruerade utifrån registreringsnumrets "
                    "sista siffra, inte hämtade från biluppgifter.se.",
        )
        print(f"\nvyn kör på http://127.0.0.1:{args.port}/granskning/0")
        print("avsluta med ctrl-c")
        server.serve_forever()
    else:
        print(f"{len(granskningsfall)} fall är redo för vyn. "
              f"Kör med --vy för att läsa dem.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
