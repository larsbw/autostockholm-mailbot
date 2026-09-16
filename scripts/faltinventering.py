r"""Vilka fält BÄR de sparade sidorna, per fordon? Skiva 40 DEL A, mätsteget.

    .venv/bin/python scripts/faltinventering.py --katalog <utanför repot>

**INGEN NÄTTRAFIK.** Skriptet läser bara redan sparade sidor. Skiva 37:s
`faltdiagnos.py` hämtade dem under ett hårt tak om sex begäran; den här
mätningen ska kunna räknas om hur många gånger som helst utan att röra
biluppgifter.se igen.

**FRÅGAN SOM STYR SKIVA 40.** Lars fynd: en sida saknar `Släpvagnsvikt` HELT
medan en annan bär den. Biluppgifter renderar bara fält som har ett värde,
alltså betyder en SAKNAD etikett att registret inte bär uppgiften, inte att
parsern föll. `src/biluppgifter.py` behandlar de två likadant i dag, och det är
två olika saker:

  FANNS INTE PÅ SIDAN     registret saknar uppgiften. Ett faktum, inte ett fel.
  FANNS MEN TOLKADES EJ   parsern föll. Det här är felet.
  LÄSTES                  värdet finns och gick att tolka.

**§6: INGENTING SOM SKRIVS UT BÄR ETT REGISTRERINGSNUMMER.** Sidorna bär
ägaruppgifter och ligger utanför repot. Kolumnerna är sidornas löpnummer, alltså
`sida-00.html` och så vidare, aldrig fordonsidentiteter. Inga råa värden skrivs
ut annat än för `Draganordning`, vars två former (`Ja Kula`, `Nej`) redan står
committade i `docs/sparrar.md` och inte identifierar någon.

**ETIKETTLISTAN ÄR LARS.** De tre modulen redan läser, plus de åtta han räknar
upp i DEL A. Ordningen är hans, inte alfabetisk, så att tabellen går att läsa mot
briefen.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scripts.faltdiagnos import _etikettrader  # noqa: E402

# ETIKETTERNA SOM MÄTS, i Lars ordning ur DEL A.
#
# De tre första är de `src/biluppgifter.py` läser i dag, avläst ur
# `EXAKT_ETIKETT`. Resten är de Lars räknar upp, med den lydelse han använder.
# Att en etikett INTE hittas är ett av mätningens giltiga svar, alltså ska en
# felstavning här synas som en tom rad och inte tolkas som ett registerfaktum.
ETIKETTER = (
    "Tjänstevikt",
    "Släpvagnsvikt",
    "Draganordning",
    "Kaross",
    "Fyrhjulsdrift",
    "Totalvikt",
    "Passagerare",
    # LARS SKREV `Modellår`. Sidan skriver `Fordonsår / Modellår`, på samtliga
    # sex sidor. Första körningen gav 0/6 för `Modellår`, och kontrollen nedan
    # visade varför: etiketten heter något annat. Det är skillnaden mellan ett
    # registerfaktum och ett fel i den här listan, alltså precis vad skivan
    # handlar om, uppmätt på mätverktyget självt.
    "Fordonsår / Modellår",
    "Status",
)

# SLÄPVIKT FINNS I FYRA FORMER PÅ SIDAN, och bara en av dem läser modulen.
# Mätt, se `_skriv_vad_sidorna_bar`:s utdata. Listan finns för att DEL B ska
# kunna avgöras mot vad som FAKTISKT står, inte mot vad vi trodde stod.
SLAPVIKTSFORMER = (
    "Släpvagnsvikt",
    "Släpvagnsvikt obromsad",
    "Släp totalvikt (B)",
    "Släp totalvikt (B+)",
)

# ETIKETTER VI INTE VET LYDELSEN PÅ ska inte tyst bli "saknas". Sidan kan skriva
# `Antal passagerare` där briefen skriver `Passagerare`. Varje etikett som ger
# noll träffar på SAMTLIGA sidor listas separat, tillsammans med de etiketter
# sidorna faktiskt bär, så att skillnaden går att se i stället för att gissas.


def _inventera(katalog: Path) -> int:
    sidor = sorted(katalog.glob("sida-*.html"))
    if not sidor:
        print(f"inga sparade sidor i {katalog}")
        return 1

    print(f"{len(sidor)} sparade sidor, ingen nättrafik\n")

    rader_per_sida = []
    for fil in sidor:
        rader_per_sida.append(_etikettrader(fil.read_text(encoding="utf-8")))

    _skriv_tabellen(sidor, rader_per_sida)
    _skriv_slapvikterna(sidor, rader_per_sida)
    _skriv_tolkbarheten(rader_per_sida)
    _skriv_aldrig_traffade(rader_per_sida)
    _skriv_vad_sidorna_bar(rader_per_sida)
    return 0


def _skriv_tolkbarheten(rader_per_sida) -> None:
    """Går de NÄRVARANDE värdena att tolka? Skiljer utfall 2 från utfall 3.

    **BARA FÄLT SOM FINNS PRÖVAS.** Ett saknat fält är utfall 1 och hör inte
    hemma här: det är hela poängen med skivan att de två inte blandas.

    Parsarna är modulens egna, alltså mäts det `src/biluppgifter.py` faktiskt
    skulle göra, inte en efterhärmning. Fält modulen inte läser i dag redovisas
    som RÅTT, med en längd i stället för ett värde, eftersom §6 inte behöver
    utmanas för att svara på frågan om fältet är tomt.
    """
    from src import biluppgifter

    print("\nTOLKBARHET FÖR NÄRVARANDE FÄLT. Bara fält som FINNS prövas.\n")
    print("| Etikett | finns på | tolkas | tomt värde | tolkas EJ |")
    print("| --- | --- | --- | --- | --- |")

    for etikett in ETIKETTER:
        finns = tolkas = tomt = faller = 0
        for rader in rader_per_sida:
            if etikett not in rader:
                continue
            finns += 1
            ravarde = rader[etikett]
            if not ravarde.strip():
                tomt += 1
                continue
            if etikett in ("Tjänstevikt", "Släpvagnsvikt", "Totalvikt"):
                tolkas += 1 if biluppgifter._tal(ravarde) is not None else 0
                faller += 1 if biluppgifter._tal(ravarde) is None else 0
            elif etikett == "Draganordning":
                tolkas += 1 if biluppgifter._draganordning(ravarde) is not None else 0
                faller += 1 if biluppgifter._draganordning(ravarde) is None else 0
            else:
                # INGEN PARSER FINNS ÄN. Ett icke-tomt värde räknas som läsbart
                # råtext, vilket är allt DEL A behöver veta om det.
                tolkas += 1
        print(f"| {etikett} | {finns} | {tolkas} | {tomt} | {faller} |")


def _skriv_slapvikterna(sidor, rader_per_sida) -> None:
    """Sidans fyra släpviktsformer, per sida. Underlag för DEL B.

    **DEN SIDA SOM SAKNAR `Släpvagnsvikt` KAN BÄRA EN ANNAN FORM**, och då är
    "registret saknar uppgiften" fel svar till kunden. Raden mäter det i stället
    för att anta det.
    """
    print("\nSLÄPVIKTENS FYRA FORMER. `x` = etiketten finns.\n")
    print("| Form | " + " | ".join(
        f.stem.replace("sida-", "") for f in sidor) + " | finns på |")
    print("| --- |" + " --- |" * (len(sidor) + 1))

    for form in SLAPVIKTSFORMER:
        rutor = ["x" if form in rader else "" for rader in rader_per_sida]
        antal = sum(1 for r in rutor if r)
        print(f"| {form} | " + " | ".join(rutor) + f" | {antal}/{len(sidor)} |")


def _skriv_tabellen(sidor, rader_per_sida) -> None:
    """En rad per etikett, en kolumn per sida. `x` betyder att fältet finns."""
    print("FÄLT PER SIDA. `x` = etiketten finns, tomt = den finns INTE.\n")

    huvud = "| Etikett | " + " | ".join(
        f.stem.replace("sida-", "") for f in sidor) + " | finns på |"
    print(huvud)
    print("| --- |" + " --- |" * (len(sidor) + 1))

    for etikett in ETIKETTER:
        rutor = ["x" if etikett in rader else "" for rader in rader_per_sida]
        antal = sum(1 for r in rutor if r)
        print(f"| {etikett} | " + " | ".join(rutor) + f" | {antal}/{len(sidor)} |")


def _skriv_aldrig_traffade(rader_per_sida) -> None:
    """Etiketter ur listan som inte finns på NÅGON sida.

    Skiljer två lägen som annars ser likadana ut i tabellen: fältet saknas på
    varje fordon, eller etiketten heter något annat på sidan. Det andra är ett
    fel i den här listan och inte ett registerfaktum.
    """
    aldrig = [e for e in ETIKETTER
              if not any(e in rader for rader in rader_per_sida)]
    if not aldrig:
        print("\nVarje etikett i listan finns på minst en sida.")
        return

    print("\nETIKETTER SOM INTE FINNS PÅ NÅGON SIDA:")
    for etikett in aldrig:
        print(f"  {etikett}")
    print("  Antingen saknar registret fältet för samtliga sex fordon, eller")
    print("  så heter etiketten något annat. Se listan nedan innan du drar")
    print("  slutsatsen att det är ett registerfaktum.")


def _skriv_vad_sidorna_bar(rader_per_sida) -> None:
    """Varje etikett som FINNS på sidorna, med antal sidor som bär den.

    Det här är kontrollen mot att `ETIKETTER` är felstavad: en etikett som
    liknar en i listan men inte är identisk syns här.
    """
    alla: dict[str, int] = {}
    for rader in rader_per_sida:
        for etikett in rader:
            alla[etikett] = alla.get(etikett, 0) + 1

    print(f"\nSAMTLIGA {len(alla)} ETIKETTER SOM STÅR PÅ SIDORNA, "
          "fallande på antal sidor:")
    for etikett, antal in sorted(alla.items(), key=lambda p: (-p[1], p[0])):
        markering = "  <- i listan" if etikett in ETIKETTER else ""
        print(f"  {antal}  {etikett}{markering}")


def _skriv_vardeformer(rader_per_sida) -> None:
    """Vilka DISTINKTA värden bär varje fält? Underlag för parservalet.

    **FORMEN AVGÖR PARSERN, och den ska mätas och inte gissas.** `Fyrhjulsdrift`
    kan vara `Ja`/`Nej` eller en text; `Status` och `Kaross` är text;
    `Passagerare` och `Fordonsår / Modellår` är tal med olika rimliga intervall.
    Utan den här avläsningen väljs parser på antagande, vilket är precis den
    klass av fel skivan handlar om.

    **DISTINKTA VÄRDEN, INTE PER SIDA.** Utdatan säger vilka former som
    förekommer, aldrig vilket fordon som bär vilken. Fälten är fordonsdata och
    inte ägaruppgifter, men kopplingen fordon-till-värde behövs inte för att
    välja parser, och då skrivs den inte ut. §6.
    """
    print("\nDISTINKTA VÄRDEN PER FÄLT, sorterade. Ingen koppling till sida.\n")
    for etikett in ETIKETTER + SLAPVIKTSFORMER:
        varden = sorted({rader[etikett] for rader in rader_per_sida
                         if etikett in rader})
        if not varden:
            print(f"  {etikett}: finns inte på någon sida")
            continue
        print(f"  {etikett}: " + " | ".join(repr(v) for v in varden))


def _skriv_utfallen(sidor) -> None:
    """Kör DEL A:s `falt_med_status` och `dragviktslage` mot de sparade sidorna.

    **PRÖVAR KODEN MOT VERKLIGHETEN, inte mot en fixtur.** Fixturen är skriven
    av samma hand som koden och delar därför dess antaganden. De sex sidorna gör
    det inte.
    """
    from src import biluppgifter

    print("\nDEL A MOT DE SPARADE SIDORNA. Utfall per fält.\n")

    nycklar = (list(biluppgifter.EXAKT_ETIKETT)
               + list(biluppgifter.OVRIGA_ETIKETT)
               + list(biluppgifter.SLAPVIKT_ALTERNATIV))

    print("| Fält | " + " | ".join(
        f.stem.replace("sida-", "") for f in sidor) + " |")
    print("| --- |" + " --- |" * len(sidor))

    per_sida = [biluppgifter.falt_med_status(f.read_text(encoding="utf-8"))
                for f in sidor]

    kort = {biluppgifter.Faltstatus.LAST: "läst",
            biluppgifter.Faltstatus.SAKNAS_PA_SIDAN: "SAKNAS",
            biluppgifter.Faltstatus.TOLKAS_EJ: "TOLKAS EJ"}

    for nyckel in nycklar:
        rutor = [kort[falt[nyckel].status] for falt in per_sida]
        print(f"| {nyckel} | " + " | ".join(rutor) + " |")

    print("\nDRAGVIKTSLÄGE PER SIDA, alltså DEL B:s indata:\n")
    for fil, falt in zip(sidor, per_sida):
        lage = biluppgifter.dragviktslage(falt)
        print(f"  {fil.stem.replace('sida-', 'sida ')}: {lage.name}  ({lage.value})")


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--katalog", required=True,
                      help="katalogen med sida-NN.html, UTANFÖR repot")
    argp.add_argument("--visa-varden", action="store_true",
                      help="skriv distinkta värden per fält, för parservalet")
    argp.add_argument("--utfall", action="store_true",
                      help="kör DEL A:s statusar och dragviktsläge mot sidorna")
    args = argp.parse_args()
    katalog = Path(args.katalog).resolve()

    sidor = sorted(katalog.glob("sida-*.html"))
    if not sidor and (args.visa_varden or args.utfall):
        print(f"inga sparade sidor i {katalog}")
        return 1

    if args.visa_varden:
        _skriv_vardeformer(
            [_etikettrader(f.read_text(encoding="utf-8")) for f in sidor])
        return 0

    if args.utfall:
        _skriv_utfallen(sidor)
        return 0

    return _inventera(katalog)


if __name__ == "__main__":
    sys.exit(main())
