"""Mäter var ett strukturerat REGISTRERINGSNUMMER finns i det minade materialet.

Bär det centrala påståendet i `docs/roadmap.md` fas 4.5: vilka inflöden som
levererar numret i ett avläsbart fält, och därmed hur ofta scenario 1, SAKNAR
REGNR, alls behöver utlösas.

VARFÖR SKRIPTET FINNS OCH INTE BARA ETT `grep`. En `grep` mot filraden i
`data/*.jsonl` ser huvudena och fältet `snippet`, som är en avkortad ingress,
men inte meddelandetexten: den ligger base64url-kodad i `body.data` på den
MIME-del som bär den. Skiva 11 mätte först med `grep`, fick noll, och skrev in
i ett styrdokument att materialet saknade fältet. Det var falskt. Se
`docs/incidentlogg.md` I5.

Skriptet mäter därför samma predikat i tre lager, så att skillnaden mellan vad
`grep` ser och vad som finns blir synlig i utdatan i stället för att behöva
misstänkas.

AVKODNINGEN LÅNAS UR `src/urval.py`, den kopieras inte. En andra kopia driver
isär från pipelinen, och då mäter skriptet något annat än det boten läser.
Samma skäl som `scripts/tradstruktur.py` bär i sitt huvud.

§6: skriptet skriver ENBART antal och längder. Ingen kundtext, inget
registreringsnummer, ingen adress och ingen avsändare når utdatan.

    .venv/bin/python scripts/regnr-matning.py
    .venv/bin/python scripts/regnr-matning.py --fil data/tradar.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROT))

from src import urval  # noqa: E402

FILER = (
    ROT / "data" / "tradar.jsonl",
    ROT / "data" / "tradar_obesvarade.jsonl",
)

# Förmedlarna ur `config/maskindomaner-forbjudna.yaml`, alltså de domäner
# beslutslogg #16 slår fast bär kundärenden. `googlemail.com` hör inte hit:
# den står på samma lista av ett annat skäl, som privatpersonernas aliasdomän.
FORMEDLARE = (
    "bokadirekt.se",
    "autobutler.se",
    "hittabilverkstad.nu",
    "verkstadsdeal.se",
    "verkstadsoffert.se",
)

# Huvuden som säger var posten KOMMER IFRÅN. `To` och `Cc` duger inte: en
# förmedlare kan stå som mottagare i en tråd som någon annan startat.
AVSANDARHUVUDEN = {"from", "reply-to", "return-path", "sender"}

_REGNR_ORD = r"regnr|reg\.nr|reg nr|registreringsnr|registreringsnummer"

# ETIKETTFORM är predikatet som räknas: ordet följt av kolon eller
# likhetstecken. Det är den formen som gör fältet maskinellt avläsbart, till
# skillnad från ordet i löptext. `docs/roadmap.md` fas 4.5 definierar det
# ordagrant, och den definitionen och den här raden ska säga samma sak.
ETIKETT = re.compile(rf"({_REGNR_ORD})\s*[:=]", re.IGNORECASE)


def meddelanden(trad: dict) -> list[dict]:
    """Trådens meddelanden. En rad utan `messages` behandlas som ett meddelande,
    vilket beslutslogg #6 säger förekommer."""
    if isinstance(trad.get("messages"), list):
        return trad["messages"]
    return [trad]


def avsandardomaner(meddelande: dict) -> set[str]:
    ut = set()
    for namn, varde in urval.huvuden(meddelande):
        if namn.lower() in AVSANDARHUVUDEN:
            lagt = varde.lower()
            for doman in FORMEDLARE:
                if doman in lagt:
                    ut.add(doman)
    return ut


def har_huvud(meddelanden_: list[dict], sokt: str) -> bool:
    sokt = sokt.lower()
    return any(
        namn.lower() == sokt
        for m in meddelanden_
        for namn, _ in urval.huvuden(m)
    )


class Rakning:
    def __init__(self) -> None:
        self.tradar = 0
        self.ra = 0
        self.snippet = 0
        self.avkodad = 0
        self.eid = 0
        self.eid_och_falt = 0

    def rad(self, etikett: str) -> str:
        return (
            f"  {etikett:<34} {self.tradar:>6} {self.ra:>10} "
            f"{self.snippet:>10} {self.avkodad:>10}"
        )


def mat(sokvag: Path) -> None:
    alla = Rakning()
    formedlare = Rakning()
    per_doman: dict[str, list[int]] = {d: [0, 0] for d in FORMEDLARE}
    langsta_snippet = 0
    flerdoman = 0

    with sokvag.open(encoding="utf-8") as fil:
        for rad in fil:
            rad = rad.strip()
            if not rad:
                continue

            alla.tradar += 1
            # Mätt mot den OAVKODADE raden, alltså det en `grep` hade sett.
            ra_traff = bool(ETIKETT.search(rad))
            alla.ra += ra_traff

            try:
                trad = json.loads(rad)
            except json.JSONDecodeError:
                continue

            msgs = meddelanden(trad)

            snippet_text = "\n".join(m.get("snippet", "") or "" for m in msgs)
            avkodad_text = "\n".join(urval.brodtext(m) for m in msgs)
            langsta_snippet = max(
                langsta_snippet,
                max((len(m.get("snippet", "") or "") for m in msgs), default=0),
            )

            snippet_traff = bool(ETIKETT.search(snippet_text))
            avkodad_traff = bool(ETIKETT.search(avkodad_text))
            eid = har_huvud(msgs, "x-msg-eid")

            alla.snippet += snippet_traff
            alla.avkodad += avkodad_traff
            alla.eid += eid
            alla.eid_och_falt += eid and avkodad_traff

            domaner = set()
            for m in msgs:
                domaner |= avsandardomaner(m)
            if not domaner:
                continue

            if len(domaner) > 1:
                flerdoman += 1
            formedlare.tradar += 1
            formedlare.ra += ra_traff
            formedlare.snippet += snippet_traff
            formedlare.avkodad += avkodad_traff
            for doman in domaner:
                per_doman[doman][0] += 1
                per_doman[doman][1] += avkodad_traff

    print(f"=== {sokvag.name}")
    print(f"  längsta snippet: {langsta_snippet} tecken")
    print(f"  {'population':<34} {'trådar':>6} {'rå filrad':>10} "
          f"{'snippet':>10} {'avkodad':>10}")
    print(alla.rad("alla trådar"))
    print(formedlare.rad("förmedlartrådar"))
    print(f"  bär X-Msg-EID: {alla.eid}, "
          f"bär både huvudet och fältet: {alla.eid_och_falt}")
    print("  per domän: trådar / med fältet avkodat")
    for doman in FORMEDLARE:
        antal, med = per_doman[doman]
        print(f"    {doman:<24} {antal:>6} / {med}")
    # En tråd med två förmedlardomäner hade dubbelräknats i tabellen ovan
    # medan summan inte gör det. Talet skrivs ut i stället för antas vara noll.
    print(f"  trådar med mer än en förmedlardomän: {flerdoman}")
    print()


def main() -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument(
        "--fil",
        type=Path,
        action="append",
        help="Mät bara den här filen. Kan upprepas. Utan flaggan mäts båda.",
    )
    arg = tolk.parse_args()

    filer = tuple(arg.fil) if arg.fil else FILER
    for sokvag in filer:
        if not sokvag.exists():
            print(f"saknas: {sokvag}", file=sys.stderr)
            return 1
        mat(sokvag)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
