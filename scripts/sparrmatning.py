r"""Vad spärrade vad i den sparade körningen? Skiva 40 DEL C och D, mätsteget.

    .venv/bin/python scripts/sparrmatning.py

**MÄT FÖRE ÄNDRING.** Lars order i skiva 40 DEL C och DEL D: mät vad som
FAKTISKT spärrar svaren innan något skrivs om. Två premisser skulle prövas, och
en av dem höll inte.

**§6: INGEN KUNDTEXT SKRIVS UT.** Skriptet läser `data/granskningsfall.jsonl`,
som bär kundernas mail i klartext, och rör aldrig `text`-fältet. Utdatan består
av etiketter, spärrnamn och antal.

**INGA API-ANROP.** Filen är redan skriven av en tidigare körning. Att räkna om
den ska inte kosta tjugo anrop mot modellen.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
FALLFIL = ROT / "data" / "granskningsfall.jsonl"

# FÄLT SOM FÅR LÄSAS. Allt annat i posten, `text` främst, är kundens och rörs
# inte. Listan är en spärr och inte en bekvämlighet: en framtida utökning av
# skriptet ska behöva lägga till ett fält här medvetet.
TILLATNA_FALT = ("etikett", "sparr", "uppslagskalla", "forslag")


def _las_poster() -> list[dict]:
    if not FALLFIL.exists():
        print(f"saknas: {FALLFIL.relative_to(ROT)}")
        print("Kör scripts/kedja-prov.py --kor först.")
        return []

    poster = []
    for rad in FALLFIL.read_text(encoding="utf-8").splitlines():
        if not rad.strip():
            continue
        hel = json.loads(rad)
        poster.append({f: hel.get(f) for f in TILLATNA_FALT})
    return poster


def _korstabell(poster: list[dict]) -> None:
    """Etikett mot spärr. Svarar på DEL C och DEL D:s mätfrågor."""
    etiketter = sorted({p["etikett"] for p in poster})
    sparrar = sorted({p["sparr"] or "INGEN, alltså ett utkast" for p in poster})

    print(f"{len(poster)} fall i {FALLFIL.relative_to(ROT)}\n")
    print("ETIKETT MOT SPÄRR\n")
    print("| Etikett | " + " | ".join(sparrar) + " | summa |")
    print("| --- |" + " --- |" * (len(sparrar) + 1))

    for etikett in etiketter:
        rad = []
        for sparr in sparrar:
            antal = sum(
                1 for p in poster
                if p["etikett"] == etikett
                and (p["sparr"] or "INGEN, alltså ett utkast") == sparr
            )
            rad.append(str(antal))
        summa = sum(1 for p in poster if p["etikett"] == etikett)
        print(f"| {etikett} | " + " | ".join(rad) + f" | {summa} |")


def _bokningarna(poster: list[dict]) -> None:
    """DEL D: fälls bokningssvaren av en spärr, eller följer modellen inte regeln?

    **DE TVÅ HYPOTESERNA UTESLUTER VARANDRA, och det är hela poängen med att
    mäta.** Fälls svaret av en spärr har regeln aldrig nått Lars ögon. Går det
    igenom som utkast är det modellen som inte följer den, och då är det
    prompten och inte spärrarna som ska ändras.
    """
    bokningar = [p for p in poster if p["etikett"] == "boka a-traktorkonvertering"]
    if not bokningar:
        print("\ninga bokningsärenden i materialet")
        return

    sparrade = [p for p in bokningar if p["sparr"]]
    utkast = [p for p in bokningar if not p["sparr"]]

    print(f"\nDEL D. BOKNINGSÄRENDEN: {len(bokningar)} st")
    print(f"  spärrade: {len(sparrade)}")
    print(f"  utkast:   {len(utkast)}")
    for sparr in sorted({p["sparr"] for p in sparrade}):
        antal = sum(1 for p in sparrade if p["sparr"] == sparr)
        print(f"    {antal}  {sparr}")

    # ORDEN SOM VISAR ATT REGELN FÖLJTS. Regel 10 säger att vi svarar att det
    # löser vi och ber kunden höra av sig. Ett svar som bär något av de här
    # orden har åtminstone försökt.
    #
    # **DET HÄR ÄR EN INDIKATION OCH INGEN BEDÖMNING.** Ett svar kan bära orden
    # och ändå vara avvisande, och Lars läsning i vyn är den som avgör.
    jaord = ("det löser vi", "det ordnar vi", "det fixar vi", "absolut",
             "javisst", "det går bra", "gärna")
    with_ja = [p for p in utkast
               if any(o in (p["forslag"] or "").lower() for o in jaord)]
    print(f"  av utkasten bär {len(with_ja)} av {len(utkast)} ett jakande ord")


def main() -> int:
    poster = _las_poster()
    if not poster:
        return 1
    _korstabell(poster)
    _bokningarna(poster)
    return 0


if __name__ == "__main__":
    sys.exit(main())
