"""Fäller rader i en fil på plats. Anropas bara av scripts/sparr-prova.sh,
som ansvarar för säkerhetskopia och återställning.

Två lägen, båda upprepningsbara i samma körning så att flera lager kan fällas
samtidigt (CLAUDE.md §7.1, lagrat försvar):

    --radera N        raderar rad N
    --ersatt N=TEXT   ersätter rad N med TEXT (neutralisering)

Radnumren avser filens utgångsläge. Ersättningar tillämpas före raderingar, så
numren förskjuts aldrig av varandra.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def _tolka_ersatt(varde: str) -> tuple[int, str]:
    if "=" not in varde:
        raise argparse.ArgumentTypeError(
            f"--ersatt vill ha N=TEXT, fick {varde!r}"
        )
    nummer, text = varde.split("=", 1)
    return int(nummer), text


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--fil", required=True, type=Path)
    tolk.add_argument("--radera", action="append", type=int, default=[])
    tolk.add_argument("--ersatt", action="append", type=_tolka_ersatt, default=[])
    arg = tolk.parse_args(argv)

    if not arg.radera and not arg.ersatt:
        print("mutera: ingen fällning angiven", file=sys.stderr)
        return 2

    rader = arg.fil.read_text(encoding="utf-8").splitlines(keepends=True)
    antal = len(rader)

    for nummer in [n for n, _ in arg.ersatt] + list(arg.radera):
        if not 1 <= nummer <= antal:
            print(
                f"mutera: rad {nummer} finns inte i {arg.fil} ({antal} rader)",
                file=sys.stderr,
            )
            return 2

    for nummer, text in arg.ersatt:
        gammal = rader[nummer - 1]
        radslut = "\n" if gammal.endswith("\n") else ""
        rader[nummer - 1] = text + radslut
        print(f"  NEUTRALISERAD rad {nummer}: {gammal.rstrip()!r} -> {text!r}")

    for nummer in sorted(set(arg.radera), reverse=True):
        gammal = rader.pop(nummer - 1)
        print(f"  RADERAD rad {nummer}: {gammal.rstrip()!r}")

    arg.fil.write_text("".join(rader), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
