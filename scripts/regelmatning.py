#!/usr/bin/env python3
"""Vad kostar skiva 55:s regeländringar i överblockering? DEL C, Lars mätorder.

    .venv/bin/python scripts/regelmatning.py

**ORDERN ÄR ATT MÄTA FÖRE OCH INTE EFTER.** *"Mät regeländringarna mot
krav_pa_svaret INNAN de tjugo körs."* Skälet är skiva 47:s: en regel som fäller
önskade svar blir avstängd, och det syns billigare i en mätning mot befintlig
text än i tjugo modellanrop.

**VAD SOM MÄTS.** Varje utgående text i materialet körs genom `krav_pa_svaret`
med en förfrågan som bär det uppslag ärendet faktiskt hade. Två körningar
jämförs:

  FÖRE   spärrarna som de var före skiva 55, alltså utan
         `barlastflak-galler-fordonet` och med fordonsfaktumspärren prövad mot
         HELA uppslaget i stället för per fält.
  EFTER  spärrarna som de är nu.

Skillnaden är skivans pris, och den redovisas per spärr.

**MATERIALET ÄR TVÅ KORPUSAR, och de svarar på olika frågor.**

  `data/granskningsfall.jsonl`  botens EGNA utkast från körningen Lars läste.
                                Mäter vad de nya reglerna hade gjort med de
                                svar som faktiskt gick igenom.
  `data/par.jsonl`              Mattes FAKTISKT SKICKADE svar. Mäter om en regel
                                fäller sådant en människa skriver, vilket är den
                                allvarligare riktningen: de svaren är per
                                definition önskade.

**UPPSLAGEN ÄR AVLÄSTA OCH INTE PÅHITTADE.** Varje fall i granskningsmaterialet
knyts till sitt registreringsnummer och därmed till en sparad fordonssida, om en
sådan finns. Saknas sidan körs fallet utan uppslag, och det redovisas separat:
ett fall utan uppslag kan inte mäta de två nya reglerna, som båda kräver avlästa
fält.

**§6: INGEN KUNDTEXT SKRIVS UT.** Utdatan är antal, andelar och spärrnamn.
Ingen mening och inget fragment ur någon korpus når skärmen.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import biluppgifter, fordonsuppslag, generera, maskera  # noqa: E402
from src.generera import Forfragan, Sparrfalld  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
GRANSKNINGSFALL = ROT / "data" / "granskningsfall.jsonl"
PAR = ROT / "data" / "ometiketterade.jsonl"
PARFIL = ROT / "data" / "par.jsonl"


def _sidkarta(katalog: Path | None) -> dict[str, dict]:
    """Registreringsnummer till uppslag, ur sparade sidor. Tom utan katalog.

    **SIDORNA LIGGER UTANFÖR REPOT**, och nyckelfilen som binder sida till
    nummer likaså. §6: filnamnen är löpnummer, och numret står bara i nyckeln.
    """
    if katalog is None:
        return {}

    nyckelfil = katalog / "nyckel.json"
    if not nyckelfil.exists():
        return {}

    ut: dict[str, dict] = {}
    for stam, post in json.loads(nyckelfil.read_text(encoding="utf-8")).items():
        sidfil = katalog / f"{stam}.html"
        if not sidfil.exists():
            continue

        sida = sidfil.read_text(encoding="utf-8")
        statusar = biluppgifter.falt_med_status(sida)

        falt = {
            nyckel: statusar[nyckel].varde
            for nyckel in tuple(biluppgifter.EXAKT_ETIKETT)
            + biluppgifter.UPPSLAGSFALT
            if statusar[nyckel].status is biluppgifter.Faltstatus.LAST
        }
        falt[biluppgifter.META_FALTSTATUS] = {
            n: statusar[n].status.value for n in biluppgifter.EXAKT_ETIKETT
        }
        falt[biluppgifter.META_DRAGVIKT] = biluppgifter.dragviktslage(
            statusar).value
        ut[post["regnr"]] = falt

    return ut


def _uppslag_for(text: str, sidkarta: dict[str, dict]):
    """Ärendets uppslag, eller `None` när ingen sparad sida finns."""
    traff = maskera.REGNR.search(text)
    if not traff:
        return None

    regnr = fordonsuppslag.normalisera_regnr(traff.group(0))
    falt = sidkarta.get(regnr)
    if falt is None:
        return None

    try:
        return fordonsuppslag._kontrollera(falt)
    except fordonsuppslag.UppslagMisslyckades:
        return None


def _fore_skiva_55(svar: str, forfragan: Forfragan) -> None:
    """Spärrarna SOM DE VAR, byggda ur dagens funktioner.

    **TVÅ SKILLNADER, och båda byggs om här i stället för att resoneras fram.**
    `barlastflak-galler-fordonet` fanns inte, och fordonsfaktumspärren prövade
    hela uppslaget i stället för fältet termen påstår något om. Allt annat är
    oförändrat och anropas rakt av.

    En omkörning av den här funktionen mäter alltså deltat och inte bara nuläget,
    vilket är samma val `scripts/prismatning.py` gör.
    """
    generera.krav_pa_ett_svar(svar)
    generera.krav_pa_tal_med_kalla(svar, forfragan)

    traff = generera.FORDONSORD.search(svar)
    if traff and forfragan.uppslag is None:
        raise Sparrfalld(
            "genererat-fordonsfaktum",
            f"svaret nämner {traff.group(0).lower()} utan ett lyckat uppslag",
        )

    generera.krav_pa_belagt_franvaropastaende(svar, forfragan)
    generera.krav_pa_att_troskeln_inte_ar_forfattningstext(svar)
    generera.krav_pa_atagande_med_kalla(svar, forfragan)


def _utfall(kontroll, svar: str, forfragan: Forfragan) -> str | None:
    try:
        kontroll(svar, forfragan)
    except Sparrfalld as fel:
        return fel.sparr
    return None


def _kor_korpus(namn: str, poster: list[tuple[str, str, object]]) -> None:
    """En korpus genom båda uppsättningarna, med skillnaden per spärr."""
    fore: dict[str, int] = {}
    efter: dict[str, int] = {}
    nya: dict[str, int] = {}
    med_uppslag = 0

    for text, kategori, uppslag in poster:
        if uppslag is not None:
            med_uppslag += 1

        forfragan = Forfragan(
            text="x",
            kategori=kategori,
            utfall=(fordonsuppslag.utvardera(uppslag)
                    if uppslag is not None else None),
            uppslag=uppslag,
            uppslag_gjordes=True,
            regnr_i_mailet=True,
            franvaro_far_pastas=(
                frozenset({"draganordning"})
                if uppslag is not None and uppslag.draganordning is False
                else frozenset()
            ),
        )

        f = _utfall(_fore_skiva_55, text, forfragan)
        e = _utfall(generera.krav_pa_svaret, text, forfragan)

        if f:
            fore[f] = fore.get(f, 0) + 1
        if e:
            efter[e] = efter.get(e, 0) + 1
        # **NY FÄLLNING = föll INTE förut och faller nu.** Ett byte av spärrnamn
        # på ett svar som föll i båda är ingen ny fällning för kunden: svaret
        # kom inte fram i något av fallen.
        if e and not f:
            nya[e] = nya.get(e, 0) + 1

    antal = len(poster)
    print(f"\n{namn}: {antal} texter, varav {med_uppslag} med ett avläst uppslag")
    print(f"  fällda FÖRE  {sum(fore.values()):>4}   {dict(sorted(fore.items()))}")
    print(f"  fällda EFTER {sum(efter.values()):>4}   {dict(sorted(efter.items()))}")
    print(f"  NYA fällningar {sum(nya.values()):>2}   {dict(sorted(nya.items()))}")
    if antal:
        andel = 100 * sum(nya.values()) / antal
        print(f"  ny överblockering: {andel:.1f} %")


def main() -> int:
    argp = argparse.ArgumentParser()
    argp.add_argument("--sidor", default=None,
                      help="katalog med sida-NN.html och nyckel.json, UTANFÖR repot")
    args = argp.parse_args()

    sidkarta = _sidkarta(Path(args.sidor).resolve() if args.sidor else None)
    print(f"sparade sidor: {len(sidkarta)}")

    fall = [json.loads(r) for r in
            GRANSKNINGSFALL.read_text(encoding="utf-8").splitlines() if r]
    botens = [
        (f["forslag"], f["etikett"], _uppslag_for(f["text"], sidkarta))
        for f in fall if f.get("forslag")
    ]
    _kor_korpus("BOTENS EGNA UTKAST (data/granskningsfall.jsonl)", botens)

    # MATTES SKICKADE SVAR. Kategorin hämtas ur `ometiketterade.jsonl` på
    # kundtexten, samma koppling som `generera.las_exempel` och `vy._par_karta`.
    etiketter = {}
    for rad in PAR.read_text(encoding="utf-8").splitlines():
        if rad:
            post = json.loads(rad)
            etiketter[post.get("text")] = post.get("etikett")

    mattes = []
    for rad in PARFIL.read_text(encoding="utf-8").splitlines():
        if not rad:
            continue
        post = json.loads(rad)
        kategori = etiketter.get(post.get("inkommande_text"))
        if kategori not in generera.A_TRAKTORETIKETTER:
            continue
        ut = (post.get("utgaende_text") or "").strip()
        if ut:
            mattes.append(
                (ut, kategori, _uppslag_for(post.get("inkommande_text", ""),
                                            sidkarta)))

    _kor_korpus("MATTES SKICKADE A-TRAKTORSVAR (data/par.jsonl)", mattes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
