#!/usr/bin/env python3
"""Vad kostar VÄG B i överblockering? Skiva 58 DEL 0, Lars mätorder.

    .venv/bin/python scripts/faktakalla-matning.py

**VÄG B.** Ett faktavärde som bär siffror blir källa bara när värdet står
ORDAGRANT i satsen. Dess siffergrupper går aldrig in i den globala mängden
tillåtna tal. Före ändringen la `generera._tillatna_tal` varje faktavärdes tal i
den globala mängden, alltså gjorde telefonnumret `076`, `860`, `38` och `15`
skrivbara var som helst i ett utgående mail.

**TVÅ FRÅGOR, och skriptet svarar på båda i en körning.**

1. **UNDERBLOCKERINGEN SOM STÄNGS.** `SONDER` nedan är svar som ska FALLA efter
   ändringen. **BARA DE TRE FÖRSTA PASSERADE FÖRE DEN**, och det är de som mättes
   i skiva 58 DEL 0.1. De tre sista föll redan mot HEAD: de blir intressanta först
   i kombinationen adress plus den gamla globala regeln, alltså i väg A, och står
   här som den jämförelse Lars beslut vilade på. Raderna är skrivna här och bär
   ingen kundtext.

2. **ÖVERBLOCKERINGEN SOM BETALAS.** Mattes faktiskt skickade a-traktorsvar,
   `data/par.jsonl`, körda genom `krav_pa_svaret`. Måttet är hur många texter
   som går från PASSERANDE till FÄLLD.

**MÄTNINGEN JÄMFÖR INTE MOT EN SIMULERAD GAMMAL KOD.** Skriptet kör den kod som
ligger i arbetsträdet och skriver ut utfallet. Deltat fås genom att köra det en
gång före ändringen och en gång efter, alltså mot två verkliga koduppsättningar
och inte mot en efterbyggd. Det är skillnaden mot `scripts/prismatning.py`, som
bygger om den gamla satsdelningen: där fanns ingen commit att köra mot, här finns
det.

**§6: INGEN KUNDTEXT SKRIVS UT.** Mattes texter redovisas som antal och som
löpnummer i filen. **INGEN SATS SKRIVS UT ALLS**, alltså finns här ingen väg som
kan bära kundtext vidare. De skäl som skrivs ut hör till de konstruerade raderna
i `SONDER` och `HELA`, och de går ändå genom `maskera.maska_sparrskal`, samma väg
som vyn: en rad som senare byter korpus ska inte behöva komma ihåg att lägga till
maskeringen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import generera, maskera  # noqa: E402
from src.generera import Forfragan, Sparrfalld  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PARFIL = ROT / "data" / "par.jsonl"

# SVAR SOM SKA FALLA EFTER VÄG B, alltså hålet ändringen stänger. Talen är
# telefonnumrets siffergrupper och adressens, och ingen av dem har någon källa
# i den mening svaret skriver.
#
# **RADERNA ÄR KONSTRUERADE HÄR.** De bär ingen kundtext och inget riktigt
# ärende. Formen är den `docs/sparrar.md` beskriver för lucka 57: en påhittad
# ledtid eller ett påhittat antal, skrivet med ett tal som råkar vara en
# siffergrupp ur ett faktavärde.
SONDER = (
    "Vi hör av oss inom 15 dagar.",
    "Ombyggnaden tar 38 dagar.",
    "Vi har byggt om 860 bilar.",
    "Vi hör av oss inom 48 timmar.",
    "Ombyggnaden tar 42 dagar.",
    "Vi har byggt om 113 bilar av samma modell.",
)

# SVAR SOM SKA PASSERA BÅDE FÖRE OCH EFTER, alltså negativkontrollen. Utan den
# vore "fäll varje tal" en grön lösning på raden ovan.
#
# Varje rad citerar ett faktavärde ORDAGRANT som det står i `config/fakta.json`.
HELA = (
    "Ring oss på 076-860 38 15 så bokar vi in en tid.",
    "Du når oss på 076-860 38 15.",
)


def _forfragan(kategori: str) -> Forfragan:
    """En förfrågan utan uppslag, alltså utan uppslagets egna tal.

    Samma väg som `scripts/lucka30-matning.py::mattes`: mätningen gäller
    talspärrens KÄLLBEGREPP, och ett uppslag bidrar med vikter som inte har med
    faktafilen att göra.
    """
    return Forfragan(
        text="x",
        kategori=kategori,
        utfall=None,
        uppslag=None,
        uppslag_gjordes=True,
        regnr_i_mailet=True,
    )


def _fallning(text: str, kategori: str) -> tuple[str, str, str] | None:
    """Spärr, skäl och den fällda satsen, eller None när texten passerar."""
    try:
        generera.krav_pa_svaret(text, _forfragan(kategori))
    except Sparrfalld as fel:
        return fel.sparr, fel.skal, fel.sats
    return None


def raderna() -> None:
    """De konstruerade raderna, var och en med sitt utfall."""
    kategori = "fråga om a-traktorkonvertering"

    print("SVAR SOM VÄG B SKA FÄLLA")
    for text in SONDER:
        utfall = _fallning(text, kategori)
        if utfall is None:
            print(f"  PASSERAR   {text}")
        else:
            print(f"  FÄLLS      {text}")
            print(f"               {maskera.maska_sparrskal(utfall[1])}")

    print("\nSVAR SOM SKA PASSERA BÅDE FÖRE OCH EFTER")
    for text in HELA:
        utfall = _fallning(text, kategori)
        if utfall is None:
            print(f"  PASSERAR   {text}")
        else:
            print(f"  FÄLLS      {text}")
            print(f"               {maskera.maska_sparrskal(utfall[1])}")


def _mattes_texter() -> list[tuple[int, str, str]]:
    """Mattes a-traktorsvar som (löpnummer, text, kategori).

    Kategorin hämtas ur `ometiketterade.jsonl` på kundtexten, samma koppling som
    `generera.las_exempel` och `scripts/lucka30-matning.py`.
    """
    etiketter = {}
    for rad in OMETIKETTERADE.read_text(encoding="utf-8").splitlines():
        if rad:
            post = json.loads(rad)
            etiketter[post.get("text")] = post.get("etikett")

    texter = []
    for nr, rad in enumerate(PARFIL.read_text(encoding="utf-8").splitlines(), 1):
        if not rad:
            continue
        post = json.loads(rad)
        kategori = etiketter.get(post.get("inkommande_text"))
        if kategori not in generera.A_TRAKTORETIKETTER:
            continue
        ut = (post.get("utgaende_text") or "").strip()
        if ut:
            texter.append((nr, ut, kategori))
    return texter


def mattes() -> None:
    """Överblockeringen, mätt mot Mattes egna skickade svar."""
    texter = _mattes_texter()

    passerar: list[int] = []
    per_sparr: dict[str, int] = {}
    for nr, text, kategori in texter:
        utfall = _fallning(text, kategori)
        if utfall is None:
            passerar.append(nr)
        else:
            per_sparr[utfall[0]] = per_sparr.get(utfall[0], 0) + 1

    print("\nMATTES SKICKADE A-TRAKTORSVAR (data/par.jsonl)")
    print(f"  texter                  {len(texter)}")
    print(f"  passerar                {len(passerar)}   löpnr {passerar}")
    print(f"  fälls                   {len(texter) - len(passerar)}   "
          f"{dict(sorted(per_sparr.items()))}")


def _faktatal() -> set[str]:
    """Siffergrupperna i `config/fakta.json`:s värden, alltså det VÄG B tar bort.

    Räknat med `_varden_ur`, samma väg `_tillatna_tal` gick före ändringen.
    Kommentarnycklar är utelämnade, som de alltid varit.
    """
    tal: set[str] = set()
    for varde in generera._varden_ur(generera.las_konfig(generera.FAKTA)):
        tal |= generera._tal_i(varde)
    return tal


def _faktavarden() -> list[str]:
    """Faktavärdena, i den form filen skriver dem. Spärrens egen mängd."""
    return generera._faktakallor()


def talen_som_tappar_kalla() -> None:
    """Hur många tal i Mattes svar som förlorar sin källa av VÄG B.

    **DET HÄR ÄR MÄTNINGENS TYNGSTA TAL, och skälet är att texträkningen ovan
    har ett TAK PÅ ETT.** Fyrtiofyra av Mattes fyrtiofem svar faller redan i dag,
    alltså kan högst en enda text gå från passerande till fälld hur hård formen
    än blir. En sådan mätning kan inte skilja en liten överblockering från en
    stor, och §7.1 säger vad ett mått som inte kan slå ut är värt.

    Måttet här är i stället per TAL: ett tal som stod i faktafilens
    siffergrupper, och som efter ändringen inte längre har någon källa i den sats
    det står i. Det är EGENSKAPEN som betalas, oberoende av om texten redan föll
    på något annat.

    **RÄKNINGEN GÅR GENOM SPÄRRENS EGEN HJÄLPARE**, `_tal_utan_ordagrann_kalla`,
    och bygger alltså inte om regeln här. En mätning som skriver av en regel
    mäter sin egen avskrift den dag regeln ändras, vilket §7-granskningen av
    skiva 58 visade: den första lydelsen av både spärren och den här slingan drog
    bort värdets tal ur HELA satsen, och båda hade behövt rättas var för sig.
    """
    faktatal = _faktatal()
    varden = _faktavarden()

    texter_med_tapp = 0
    tal_som_tappar: dict[str, int] = {}
    for _nr, text, _kategori in _mattes_texter():
        tappade: set[str] = set()
        for sats in generera._meningar(text):
            tappade |= (
                generera._tal_utan_ordagrann_kalla(sats, varden) & faktatal
            )
        if tappade:
            texter_med_tapp += 1
            for tal in tappade:
                tal_som_tappar[tal] = tal_som_tappar.get(tal, 0) + 1

    print("\nTAL SOM TAPPAR SIN KÄLLA AV VÄG B (data/par.jsonl)")
    print(f"  faktafilens siffergrupper   {sorted(faktatal)}")
    print(f"  texter med minst ett sådant tal   {texter_med_tapp}")
    print(f"  per tal   {dict(sorted(tal_som_tappar.items()))}")


def main() -> int:
    raderna()
    mattes()
    talen_som_tappar_kalla()
    return 0


if __name__ == "__main__":
    sys.exit(main())
