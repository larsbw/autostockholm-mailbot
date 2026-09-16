#!/usr/bin/env python3
"""Hur ofta fäller LUCKA 30 ett svar? Skiva 56 DEL A, Lars mätorder.

    .venv/bin/python scripts/lucka30-matning.py

**LUCKAN.** `generera._tal_i` läser varje siffergrupp som ett tal, också den som
är en del av ett NAMN: `V70` ger `70`, `E60` ger `60`, `X3M` ger `3`, och ett
registreringsnummers form, tre bokstäver följda av tre tecken, ger sina tre
siffror. Ett sådant tal har ingen källa, alltså faller hela svaret på
`genererat-tal-har-kalla`. Skiva 33 försökte tre lydelser och återställde alla
tre; var och en gjorde också en KVANTITET intill bokstäver ofarlig, se
`docs/beslutslogg.md` #56.

**ORDERN ÄR ATT MÄTA, INTE ATT BYGGA EN FJÄRDE LYDELSE.** Skiva 55 stängde
orsaken i PROMPTEN i stället, som regel 17: *"SKRIV ALDRIG BILENS
MODELLBETECKNING."* Frågan den här mätningen svarar på är om luckan fäller något
i praktiken efter det.

**TVÅ KORPUSAR, och de svarar på olika frågor.**

  `data/granskningsfall.jsonl`  DE TJUGO, alltså botens egna svar under den
                                prompt som bär regel 17 och 18. Mäter om luckan
                                fäller något som boten faktiskt skriver.
  `data/par.jsonl`              MATTES SKICKADE a-traktorsvar. Mäter om luckan
                                skulle fälla sådant en människa skriver, alltså
                                den form botens svar ska likna enligt §11.

**DE TVÅ MÄTS PÅ OLIKA VÄGAR, och skillnaden är redovisad.** Ett spärrat
granskningsfall bär inget `forslag`: texten som fälldes finns inte kvar. Det
bär sedan skiva 56 spärrens skäl och den fällda satsen, och de läses här.
Mattes svar finns i sin helhet och körs genom `krav_pa_svaret`.

**KLASSNINGEN ÄR EN EGENSKAP HOS TEXTEN OCH INGEN GISSNING.** Ett tal räknas som
en BETECKNING när varje förekomst av det i texten står direkt efter en bokstav.
`V70` uppfyller det, och ett registreringsnummer i löptext likaså. En kvantitet
med enhet gör det inte: `1400 kg` och `1400kg` har båda ett blanksteg eller en
radbörjan före talet. Se `_ar_beteckning`.

*Strängen som illustrerade regnr-formen är UTBYTT MOT EN BESKRIVNING av den.
`scripts/` är en bevakad katalog, och `persondatakontroll` fällde commit:en på
den. Åtgärden är Lars beslut i skiva 56 och densamma som skiva 33 och 43 landade
i: beskriv formen, skriv inte ut en sträng som har den. Spärren är orörd och
`TILLATNA` likaså.*

**§6: INGEN KUNDTEXT SKRIVS UT.** Utdatan är antal, spärrnamn och tal. En sats
går genom `maskera.maska_fritext` och ett skäl genom `maskera.maska_sparrskal`,
samma två vägar som vyn. Den senare lämnar det tal spärren namnger omaskerat,
skiva 57 DEL 0.
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import fordonsuppslag, generera, maskera  # noqa: E402
from src.generera import Forfragan, Sparrfalld  # noqa: E402

ROT = Path(__file__).resolve().parent.parent
GRANSKNINGSFALL = ROT / "data" / "granskningsfall.jsonl"
OMETIKETTERADE = ROT / "data" / "ometiketterade.jsonl"
PARFIL = ROT / "data" / "par.jsonl"

# TALET UR SPÄRRENS SKÄL. Båda formerna `krav_pa_tal_med_kalla` skriver börjar
# med `talet <tal>`, och ingen annan spärr skriver det ordet.
TALET_I_SKALET = re.compile(r"talet (\d+)")

# EN TROLIG BETECKNING: versal begynnelse, en till tre bokstäver, siffror, och
# möjligen en bokstavssvans. Fångar `V70`, `E60`, `A3` och `X3M`, och även ett
# registreringsnummers form.
#
# **NÄTET ÄR VITT MED AVSIKT.** Det är ett FÖRKRAV och ingen fällning: raden
# svarar på om texten alls bär en beteckning, alltså om luckan kan utlösas. Att
# den överskattar är den ofarliga riktningen.
TROLIG_BETECKNING = re.compile(
    r"\b[A-ZÅÄÖ][A-Za-zÅÄÖåäö]{0,2}\d{1,4}[A-Za-zÅÄÖåäö]{0,2}\b"
)


def _ar_beteckning(tal: str, text: str) -> bool:
    """Står talet ALLTID direkt efter en bokstav i texten?

    Det är villkoret som skiljer `70` i `V70` från `70` i `70 kg`. Kravet är att
    VARJE förekomst uppfyller det: bär texten både `V70` och `70 kg` är talet en
    kvantitet, och fällningen är då inte lucka 30.

    Hittas talet inte alls är svaret nej. Det inträffar när `_tal_i`
    normaliserat bort en tusenavskiljare, alltså för ett grupperat tal, och ett
    grupperat tal är aldrig en beteckning.
    """
    forekomster = list(re.finditer(re.escape(tal), text))
    if not forekomster:
        return False
    return all(
        traff.start() > 0 and text[traff.start() - 1].isalpha()
        for traff in forekomster
    )


def _fallning(text: str, kategori: str, uppslag) -> tuple[str, str, str] | None:
    """Spärr, skäl och den fällda satsen, eller None när texten passerar."""
    forfragan = Forfragan(
        text="x",
        kategori=kategori,
        utfall=(fordonsuppslag.utvardera(uppslag) if uppslag is not None
                else None),
        uppslag=uppslag,
        uppslag_gjordes=True,
        regnr_i_mailet=True,
    )
    try:
        generera.krav_pa_svaret(text, forfragan)
    except Sparrfalld as fel:
        return fel.sparr, fel.skal, fel.sats
    return None


def _bara_beteckningen_stod_i_vagen(text: str, kategori: str) -> bool:
    """Skulle texten passera HELA `krav_pa_svaret` om beteckningen inte fanns?

    **DET HÄR ÄR MÄTNINGENS HUVUDTAL, och skälet är att det första inte räcker.**
    `krav_pa_tal_med_kalla` fäller på det FÖRSTA tal utan källa den hittar,
    sorterat, alltså kan ett beteckningstal ligga bakom ett annat okällat tal och
    aldrig bli det redovisade skälet. En räkning av skälen underskattar därför
    hur ofta luckan står i vägen.

    Måttet är i stället: stryk varje TROLIG BETECKNING ur texten och kör om
    samtliga spärrar. Passerar texten då, och bara då, var beteckningen det enda
    som stod mellan svaret och ett utkast.

    **STRYKNINGEN SKER HÄR OCH ALDRIG I EN SPÄRR.** Skiva 33 varv 3 lade just den
    här maskeringen INUTI `krav_pa_tal_med_kalla`, och då blev `ca10 dagar`,
    `ca800` och `ca950 kg` osynliga för spärren, alltså en regression. Ett
    mätverktyg får göra det en spärr inte får: ingenting härifrån når ett
    kundmail.
    """
    utan = TROLIG_BETECKNING.sub(" ", text)
    if utan == text:
        return False
    return _fallning(utan, kategori, None) is None


def _redovisa(namn: str, antal: int, fallningar: list[tuple[str, str, str]],
              texter: list[str], enbart: int | None = None) -> None:
    """En korpus rad för rad: fällningar totalt, och hur många som är lucka 30."""
    lucka30 = []
    for sparr, skal, sats in fallningar:
        traff = TALET_I_SKALET.search(skal)
        if not traff or sparr != "genererat-tal-har-kalla":
            continue
        if _ar_beteckning(traff.group(1), sats or skal):
            lucka30.append(traff.group(1))

    med_beteckning = sum(1 for t in texter if TROLIG_BETECKNING.search(t))

    per_sparr: dict[str, int] = {}
    for sparr, _skal, _sats in fallningar:
        per_sparr[sparr] = per_sparr.get(sparr, 0) + 1

    print(f"\n{namn}")
    print(f"  texter                        {antal}")
    print(f"  fällda                        {len(fallningar)}   "
          f"{dict(sorted(per_sparr.items()))}")
    print(f"  LUCKA 30 som REDOVISAT skäl   {len(lucka30)}   {lucka30}")
    if enbart is not None:
        print(f"  texter där beteckningen var ENDA hindret  {enbart}")
    print(f"  texter som bär en beteckning  {med_beteckning}   "
          "(förkrav, inte fällning)")


def de_tjugo() -> None:
    """Botens egna svar ur den senaste körningen.

    **EN SPÄRRAD POST OCH EN PASSERAD MÄTS PÅ OLIKA SÄTT, och det är inget val.**
    Den spärrade bär inget `forslag`: texten som fälldes sparas ingenstans. Den
    bär spärrens skäl och den fällda satsen, och det räcker för att avgöra om
    talet var en beteckning. Den passerade bär hela texten, och för den är
    frågan om den alls bär en beteckning, eftersom den per definition inte föll.
    """
    if not GRANSKNINGSFALL.exists():
        print(f"saknas: {GRANSKNINGSFALL.relative_to(ROT)}, kör kedja-prov först")
        return

    poster = [json.loads(r) for r in
              GRANSKNINGSFALL.read_text(encoding="utf-8").splitlines() if r]

    fallningar = [
        (p["sparr"], p.get("sparrskal", ""), p.get("sparrsats", ""))
        for p in poster if p.get("sparr")
    ]
    texter = [p["forslag"] for p in poster if p.get("forslag")]

    _redovisa("DE TJUGO, botens egna svar (data/granskningsfall.jsonl)",
              len(poster), fallningar, texter)

    for sparr, skal, sats in fallningar:
        print(f"    spärrad av {sparr}")
        print(f"      skäl: {maskera.maska_sparrskal(skal)}")
        if sats:
            print(f"      sats: {maskera.maska_fritext(sats)}")


def mattes() -> None:
    """Mattes faktiskt skickade a-traktorsvar, körda genom spärrarna.

    Kategorin hämtas ur `ometiketterade.jsonl` på kundtexten, samma koppling som
    `generera.las_exempel` och `scripts/regelmatning.py` gör.

    **UTAN UPPSLAG.** Mätningen gäller talspärren, som inte behöver ett uppslag
    för att fälla ett beteckningstal: en beteckning står varken i uppslaget eller
    i config i något läge. `scripts/regelmatning.py` är den mätning som knyter
    varje ärende till sin sparade fordonssida, och den mäter andra spärrar.
    """
    etiketter = {}
    for rad in OMETIKETTERADE.read_text(encoding="utf-8").splitlines():
        if rad:
            post = json.loads(rad)
            etiketter[post.get("text")] = post.get("etikett")

    texter = []
    for rad in PARFIL.read_text(encoding="utf-8").splitlines():
        if not rad:
            continue
        post = json.loads(rad)
        kategori = etiketter.get(post.get("inkommande_text"))
        if kategori not in generera.A_TRAKTORETIKETTER:
            continue
        ut = (post.get("utgaende_text") or "").strip()
        if ut:
            texter.append((ut, kategori))

    fallningar = [f for f in
                  (_fallning(t, k, None) for t, k in texter) if f]
    enbart = sum(1 for t, k in texter if _bara_beteckningen_stod_i_vagen(t, k))

    _redovisa("MATTES SKICKADE A-TRAKTORSVAR (data/par.jsonl)",
              len(texter), fallningar, [t for t, _ in texter], enbart)

    # DE FÄLLNINGAR SOM REDOVISAR EN BETECKNING, med satsen maskerad. Utan den
    # går talet inte att kontrollera, vilket är hela skälet till att DEL 0 finns.
    for sparr, skal, sats in fallningar:
        traff = TALET_I_SKALET.search(skal)
        if traff and sparr == "genererat-tal-har-kalla" \
                and _ar_beteckning(traff.group(1), sats or skal):
            print(f"    {maskera.maska_sparrskal(skal)}")
            print(f"      sats: {maskera.maska_fritext(sats)}")


def main() -> int:
    de_tjugo()
    mattes()
    return 0


if __name__ == "__main__":
    sys.exit(main())
