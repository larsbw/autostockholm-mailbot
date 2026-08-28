"""Ometikettering i två pass, DEL D i skiva 9.

Skiva 8 lät modellen namnge varje text fritt. Det gav 159 etiketter över 795
texter, alltså en etikett per FORMULERING och inte per ärendetyp: `rekond` bar
fjorton rader, varav två felstavningar modellen övertagit ur kundens text.

Passen här rättar det:

  PASS 1  Ett anrop. Modellen får de äkta kundetiketterna med sina antal och
          konsoliderar dem till en fast taxonomi. Synonymer, böjningar och
          felstavningar slås ihop. Ärendetypen behålls, kundens ordval inte.

  PASS 2  Ett anrop per äkt kundärende. Texten etiketteras om mot den fasta
          listan. `inget kundärende` och `oklart` etiketteras INTE om: de är
          inte kundärenden och ska inte bära en kundkategori.

TAXONOMIN SKRIVS TILL DISK MELLAN PASSEN, så att pass 2 går att köra om utan
att pass 1 körs igen, och så att listan går att läsa innan de dyra anropen
görs. `--bara-pass1` stannar efter konsolideringen.

ENUM UTAN SCHEMA. Listan är en enum i den mening som räknas: svaret måste vara
en medlem, och allt annat är synligt. Tvånget ligger i en kontroll här och inte
i API:ts schema, därför att ett schematvång hade tryckt in en text som inte
passar i närmaste fel kategori UTAN att det syntes. Taxonomin bär därför
`övrigt` som uttalad utväg, och ett svar utanför listan räknas som
`utanför listan` i redovisningen i stället för att rättas tyst.
"""

from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from src import kategorisera

ROT = Path(__file__).resolve().parent.parent
KATEGORISVAR = ROT / "data" / "kategorisvar.jsonl"
TAXONOMIFIL = ROT / "data" / "taxonomi.json"
UTFIL = ROT / "docs" / "kategorier-forslag.md"
EXEMPELFIL = ROT / "scratchpad" / "kategorier-exempel.md"

# Etiketterna PER TEXT, inte bara aggregatet. Tabellen i `docs/` säger hur
# många par en kategori har; den säger inte VILKA. Mallbygget i fas 5 behöver
# de senare, och utan den här filen kostar det 210 anrop att få fram dem igen.
# Filen bär kundtext och är därför gitignorerad, precis som `kategorisvar.jsonl`.
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"

# Pass 1 svarar med en lista, inte med en etikett, och behöver därför mer
# utrymme än pass 2. Talet är ett tak och inte en förväntan.
MAX_TOKENS_PASS1 = 4000

# Svaret som betyder att texten inte passar någon kategori i listan.
OVRIGT = "övrigt"

# Etiketten en text får när modellen svarar med något som inte står i
# taxonomin. Den räknas och redovisas, den rättas aldrig tyst.
UTANFOR = "utanför listan"

SYSTEM_PASS1 = """Du får en lista över ärendekategorier som en annan modell \
satt fritt, en per inkommande mail till en fristående bilverkstad i Stockholm. \
Varje rad bär kategorin och hur många texter som fick den.

Listan är för finkornig. Den bär samma ärendetyp under flera namn, eftersom \
varje namn följde kundens egen formulering.

Din uppgift är att slå ihop dem till en FAST TAXONOMI.

Regler:
- Slå ihop synonymer, böjningar och felstavningar. "boka rekond", \
"boka rekonditionering" och "boka rekondtid" är samma ärende.
- Behåll ÄRENDETYPEN, inte kundens ordval.
- Skilj på ärenden som kräver olika svar. Att boka en tid och att fråga om ett \
pris är olika ärenden även för samma tjänst.
- Namnge med två till fyra ord på svenska, i grundform och gemener.
- Så få kategorier som möjligt UTAN att slå ihop ärenden som kräver olika svar.
- Sista raden ska vara exakt: övrigt

Svara med enbart kategorinamnen, en per rad. Ingen numrering, inga \
bindestreck, ingen förklaring."""


def las_kategorisvar(fil: Path) -> list[dict]:
    return [json.loads(rad)
            for rad in fil.read_text(encoding="utf-8").splitlines() if rad]


def akta_kundarenden(poster: list[dict]) -> list[dict]:
    """De texter som ska etiketteras om.

    `inget kundärende` och `oklart` etiketteras inte om, på Lars beslut i
    skiva 9. De är inte kundärenden, och en kundkategori på dem hade gjort
    korpusen större än den är.
    """
    return [p for p in poster
            if p["etikett"] not in kategorisera.EJ_KUNDARENDE]


def etikettrader(poster: list[dict]) -> list[str]:
    """Etiketterna med sina antal, största först, som pass 1 ska läsa."""
    antal: dict[str, int] = {}
    for post in poster:
        antal[post["etikett"]] = antal.get(post["etikett"], 0) + 1
    ordnade = sorted(antal.items(), key=lambda p: (-p[1], p[0]))
    return [f"{etikett} ({styck})" for etikett, styck in ordnade]


# Ledande numrering, bindestreck eller punkt i modellens listsvar.
# `SYSTEM_PASS1` förbjuder dem, men en modell som ändå punktar listan ska inte
# kosta 210 anrop, och det är billigare att skala av dem än att förlita sig på
# att instruktionen följs.
LISTPREFIX = re.compile(r"^\s*(?:\d+[.)]|[-*•])\s*")

# En taxonomi som bara bär `övrigt` är inte en taxonomi. Golvet finns för att
# pass 1 ska FALLA HÖGLJUTT i stället för att pass 2 ska etikettera hela
# korpusen som `övrigt` till priset av 210 anrop.
MINSTA_TAXONOMI = 2


def las_taxonomi(ratext: str) -> list[str]:
    """Modellens svar till en lista, avdubblad och med ordningen bevarad.

    Varje rad normaliseras med samma regel som pass 2:s svar, så att listan
    och etiketterna är jämförbara. En rad som inte klarar normaliseringen
    släpps: den är inte en kategori.

    Ledande numrering och punkter skalas av först. Utan det gav ett numrerat
    svar en taxonomi på ett enda element, `övrigt`, och pass 2 etiketterade då
    hela korpusen som `övrigt` utan varning. §7-granskningen av skiva 9 mätte
    upp det.
    """
    lista: list[str] = []
    for rad in ratext.splitlines():
        namn = kategorisera.normalisera(LISTPREFIX.sub("", rad))
        if namn in ("oklart", "inget kundärende") or namn in lista:
            continue
        lista.append(namn)
    if OVRIGT not in lista:
        lista.append(OVRIGT)
    if len(lista) < MINSTA_TAXONOMI:
        raise SystemExit(
            "Pass 1 gav ingen användbar taxonomi.\n"
            "\n"
            f"Efter normalisering återstod {len(lista)} kategori, och en\n"
            "taxonomi som bara bär `övrigt` hade etiketterat hela korpusen\n"
            "som `övrigt`. Kör pass 1 igen, eller läs modellens råa svar.\n"
            "\n"
            "Körningen stoppas HÄR, före pass 2, så att felet kostar ett\n"
            "anrop och inte tvåhundratio."
        )
    return lista


def konsolidera(klient, etiketter: list[str], modell: str = kategorisera.MODELL,
                atgang: kategorisera.Tokenatgang | None = None) -> list[str]:
    """PASS 1. Ett anrop, hela etikettlistan in, taxonomin ut."""
    svar = klient.messages.create(
        model=modell,
        max_tokens=MAX_TOKENS_PASS1,
        system=kategorisera.systemblock(SYSTEM_PASS1),
        messages=[{"role": "user", "content": "\n".join(etiketter)}],
    )
    if atgang is not None:
        atgang.lagg_till(getattr(svar, "usage", None))
    return las_taxonomi(kategorisera.textinnehall(svar))


def bygg_system_pass2(taxonomi: list[str]) -> str:
    punkter = "\n".join(f"- {namn}" for namn in taxonomi)
    return (
        "Du läser ett inkommande mail till en fristående bilverkstad i "
        "Stockholm.\n"
        "\n"
        "Välj den kategori ur listan nedan som bäst beskriver vad kunden VILL.\n"
        "\n"
        f"{punkter}\n"
        "\n"
        "Regler:\n"
        "- Svara med EXAKT en av raderna ovan, ordagrant.\n"
        "- Hittar du på ett eget namn är svaret fel.\n"
        f"- Passar ingen kategori, svara exakt: {OVRIGT}\n"
        "\n"
        "Svara med enbart kategorinamnet. Ingen förklaring, inga citattecken, "
        "ingen punkt."
    )


def ometikettera_en(klient, text: str, taxonomi: list[str], system: str,
                    modell: str = kategorisera.MODELL,
                    atgang: kategorisera.Tokenatgang | None = None,
                    amne: str = "", kanal: str | None = None) -> str:
    """PASS 2, en text. Svar utanför taxonomin RÄTTAS INTE, de märks.

    `amne` och `kanal` är KONTEXT och går in i användarmeddelandet, aldrig i
    valet. Ingenting här mappar en kanal till en kategori: svaret prövas bara
    mot taxonomin, precis som utan kontext.
    """
    namn = kategorisera.kategorisera_en(
        klient, text, modell=modell, atgang=atgang, system=system,
        amne=amne, kanal=kanal,
    )
    return namn if namn in taxonomi else UTANFOR


def ometikettera_alla(klient, poster: list[dict], taxonomi: list[str],
                      modell: str = kategorisera.MODELL,
                      atgang: kategorisera.Tokenatgang | None = None,
                      sov=None, skriv=print) -> list[dict]:
    """En text i taget. Ett fel kostar en text, inte körningen.

    `sov` resolveras i kroppen och inte som defaultvärde. Ett defaultvärde
    binds när modulen laddas, vilket är incident I1 i `docs/incidentlogg.md`.
    """
    sov = time.sleep if sov is None else sov
    system = bygg_system_pass2(taxonomi)
    resultat = []
    for nummer, post in enumerate(poster, start=1):
        try:
            namn = ometikettera_en(klient, post["text"], taxonomi, system,
                                   modell=modell, atgang=atgang,
                                   amne=post.get("amne", ""),
                                   kanal=post.get("kanal"))
        except Exception as fel:  # noqa: BLE001
            skriv(f"  fel på text {nummer}: {type(fel).__name__}")
            namn = "fel"
            sov(2.0)
        resultat.append({**post, "etikett": namn})
        if nummer % 25 == 0:
            skriv(f"  {nummer}/{len(poster)} ometiketterade")
    return resultat


def skriv_ometiketterade(poster: list[dict], utfil: Path) -> None:
    """Etiketterna per text, en JSON-post per rad.

    Filen bär kundtext och hör hemma under `data/`, som är gitignorerad. §6.
    """
    rader = [json.dumps(post, ensure_ascii=False) for post in poster]
    utfil.write_text("\n".join(rader) + "\n", encoding="utf-8")


def ror_a_traktor(etikett: str) -> bool:
    """Rör kategorin a-traktor?

    Prövningen är på ORD och inte på substräng. Den första lydelsen skrev
    `"epa" in etikett`, och `epa` är en substräng av `reparation`, så
    `boka reparation` och `fråga om pris reparation` räknades in i a-traktor.
    Talet blev därför för högt i en redovisning som var skivans utfall.
    """
    ord = re.findall(r"[a-zåäöéèü]+", etikett)
    return any(o in ("epa", "epatraktor") or "traktor" in o for o in ord)


def underlag_efter_konsolidering(sammanstallning: list[dict],
                                 minsta: int = kategorisera.MINSTA_PAR
                                 ) -> tuple[list, list]:
    """Skivans utfall: vilka kategorier som bär tillräckligt mallunderlag.

    `utanför listan` är ingen kategori. Den är en mätpunkt på taxonomins
    täckning och räknas därför inte som en äkta kundkategori, lika lite som
    `inget kundärende`, `oklart` och `fel` gör det.
    """
    akta = [k for k in sammanstallning
            if k["etikett"] not in kategorisera.EJ_KUNDARENDE
            and k["etikett"] != UTANFOR]
    return akta, [k for k in akta if k["med_svar"] < minsta]


def skriv_rapport(sammanstallning: list[dict], utfil: Path, antal: int,
                  taxonomi: list[str], modell: str) -> None:
    rader = [
        "# Kategoriförslag",
        "",
        "**Version:** 0.4.0 · **Uppdaterad:** 2026-08-28 · "
        "**Implementerar** CLAUDE.md §0",
        "",
        f"Maskinproducerad av `src/ometikettera.py` med `{modell}`. "
        "**Skriv inte i den här filen för hand**: den skrivs om vid nästa "
        "körning.",
        "",
        "**FRAMTAGEN I TVÅ PASS.** Pass 1 läste de etiketter en tidigare "
        "körning satt fritt, en per text, och konsoliderade dem till den fasta "
        "taxonomin nedan. Pass 2 etiketterade om varje kundärende mot den "
        "listan. Den fria omgången gav en etikett per FORMULERING, inte per "
        "ärendetyp.",
        "",
        "**`inget kundärende` och `oklart` är INTE ometiketterade.** De bär "
        "sina tal från den fria omgången och är med här för att tabellen ska "
        "täcka hela materialet.",
        "",
        "**`utanför listan`** är texter där modellen svarade med något som "
        "inte står i taxonomin. De rättas inte tyst. Är raden stor är det "
        "taxonomin som är för smal, inte texterna som är konstiga.",
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
        "---",
        "",
        "## Taxonomin ur pass 1",
        "",
    ]
    rader += [f"- {namn}" for namn in taxonomi]
    rader += [
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
        rader.append(f"| {rad['etikett']} | {rad['antal']} | "
                     f"{rad['med_svar']} | {rad['utan_svar']} |")

    # §8: en ändring utan appendixpost är en ospårbar ändring. Filen är
    # maskinproducerad, så appendixet skrivs av koden. Skiva 9 höjde versionen
    # från 0.2.0 till 0.3.0 och tog samtidigt bort hela historiken, eftersom
    # den förra skrivaren bar den i sin mall och den här inte gjorde det.
    rader += [
        "",
        "---",
        "",
        "## Appendix — versionshistorik (nyaste överst)",
        "",
        "### 0.4.0 — 2026-08-28",
        "",
        "**Vad version 0.4.0 gjorde**, i skiva 16: "
        "`scripts/etikettera-nya.py` lade till 66 kundtexter och etiketterade "
        "enbart dem. De blev synliga av att `docs/beslutslogg.md` #27 rättade "
        "uppdelningen besvarad mot obesvarad: miningens `in:sent` gjorde en "
        "Gmail-etikett till ensam grund för vilken skördefil en tråd hamnade "
        "i, så kundärenden utan svar i fel fil räknades i ingen kolumn.",
        "",
        "De 66 gick genom BÅDA passen, alltså först den fria klassningen som "
        "avgör `inget kundärende` och `oklart`, sedan pass 2 mot den fasta "
        "taxonomin. Taxonomin lästes från `data/taxonomi.json` och kördes "
        "INTE om. Varje ny post bar `utan svar`, så kolumnen `Med svar` kunde "
        "inte ändras av den körningen. Skälet att inte köra om materialet är "
        "att pass 2 inte är deterministiskt, se beslutslogg #18.",
        "",
        "**APPENDIXET ÄR STATISKT OCH BESKRIVER VARJE VERSIONS ÄNDRING, "
        "aldrig den senaste körningen.** Posterna ligger i "
        "`src/ometikettera.py::skriv_rapport` och skrivs ut oförändrade vid "
        "varje körning. En full omkörning av `src/ometikettera.py` "
        "etiketterar om HELA korpusen och är alltså inte det posten ovan "
        "beskriver; den som gör en sådan körning ska höja versionen och lägga "
        "till en egen post innan filen committas.",
        "",
        "### 0.3.0 — 2026-08-26",
        "",
        "Den fria etiketteringen ersatt av två pass. Pass 1 konsoliderar "
        "etiketterna till en fast taxonomi i ett anrop, pass 2 etiketterar om "
        "kundärendena mot den. Den fria omgången gav en etikett per "
        "formulering och inte per ärendetyp. Se beslutslogg #18.",
        "",
        # De två posterna nedan är återgivna ORDAGRANT ur filen som den såg ut
        # i `196e60a`. Skiva 9 höjde versionen till 0.3.0 och tog samtidigt
        # bort hela historiken, eftersom den här skrivaren inte bar något
        # appendix. Historik återskapas genom att kopieras, aldrig genom att
        # skrivas om ur minnet.
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
    utfil.write_text("\n".join(rader), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--kategorisvar", type=Path, default=KATEGORISVAR)
    tolk.add_argument("--taxonomi", type=Path, default=TAXONOMIFIL)
    tolk.add_argument("--utfil", type=Path, default=UTFIL)
    tolk.add_argument("--ometiketterade", type=Path, default=OMETIKETTERADE)
    tolk.add_argument("--modell", default=kategorisera.MODELL)
    tolk.add_argument("--bara-pass1", action="store_true",
                      help="Stanna efter konsolideringen. Inga dyra anrop.")
    tolk.add_argument("--aterbruka-taxonomi", action="store_true",
                      help="Läs taxonomin från disk i stället för att köra "
                           "pass 1 igen.")
    tolk.add_argument("--max-poster", type=int, default=0,
                      help="Provkörning: etikettera bara så här många om.")
    args = tolk.parse_args(argv)

    poster = las_kategorisvar(args.kategorisvar)
    akta = akta_kundarenden(poster)
    ovriga = [p for p in poster
              if p["etikett"] in kategorisera.EJ_KUNDARENDE]
    print(f"texter totalt: {len(poster)}")
    print(f"  äkta kundärenden att etikettera om: {len(akta)}")
    print(f"  ej ometiketterade: {len(ovriga)}")

    klient = kategorisera.bygg_klient()
    atgang = kategorisera.Tokenatgang()

    if args.aterbruka_taxonomi:
        taxonomi = json.loads(args.taxonomi.read_text(encoding="utf-8"))
        print(f"taxonomi läst från {args.taxonomi}: {len(taxonomi)} kategorier")
    else:
        etiketter = etikettrader(akta)
        print(f"\nPASS 1: konsoliderar {len(etiketter)} etiketter, ett anrop")
        taxonomi = konsolidera(klient, etiketter, modell=args.modell,
                               atgang=atgang)
        args.taxonomi.write_text(json.dumps(taxonomi, ensure_ascii=False,
                                            indent=2), encoding="utf-8")
        print(f"  {len(taxonomi)} kategorier, skrivna till {args.taxonomi}")

    for namn in taxonomi:
        print(f"    {namn}")

    if args.bara_pass1:
        print("\n--bara-pass1: stannar här. Pass 2 är inte kört.")
        return 0

    att_gora = akta[:args.max_poster] if args.max_poster else akta
    print(f"\nPASS 2: {len(att_gora)} anrop")
    ometiketterade = ometikettera_alla(klient, att_gora, taxonomi,
                                       modell=args.modell, atgang=atgang)

    allt = ometiketterade + (ovriga if not args.max_poster else [])
    skriv_ometiketterade(allt, args.ometiketterade)
    sammanstallning = kategorisera.sammanstall(allt)
    skriv_rapport(sammanstallning, args.utfil, len(allt), taxonomi,
                  args.modell)
    kategorisera.skriv_exempel(sammanstallning, EXEMPELFIL)

    print("\n=== TOKENÅTGÅNG, avläst ur API-svaren ===")
    for rad in atgang.redovisa():
        print(rad)

    akta_kat, fa_par = underlag_efter_konsolidering(sammanstallning)
    nar_troskeln = [k for k in akta_kat
                    if k["med_svar"] >= kategorisera.MINSTA_PAR]
    print("\n=== UNDERLAG PER KATEGORI ===")
    print(f"  äkta kundkategorier: {len(akta_kat)}")
    print(f"  som NÅR {kategorisera.MINSTA_PAR} par med svar: "
          f"{len(nar_troskeln)}")
    for rad in nar_troskeln:
        print(f"    {rad['etikett']}: {rad['med_svar']} par med svar")
    print(f"  med färre än {kategorisera.MINSTA_PAR}: {len(fa_par)}")

    traktor = [k for k in sammanstallning if ror_a_traktor(k["etikett"])]
    print("\n=== A-TRAKTOR ===")
    for rad in traktor:
        print(f"  {rad['etikett']}: {rad['antal']} texter, "
              f"{rad['med_svar']} par med svar")
    if not traktor:
        print("  ingen kategori i taxonomin nämner a-traktor eller epa")

    print(f"\nutfil: {args.utfil}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
