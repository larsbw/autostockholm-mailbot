"""VAR DATA, LOGGAR OCH HEMLIGHETER BOR. En plats, och bara en.

Fram till skiva 53 räknade varje modul ut sina sökvägar själv, ur
`Path(__file__).parent.parent`. Det fungerar så länge allt ligger i repot och
går sönder i samma stund något ska ligga någon annanstans.

**SKÄLET ÄR RAILWAY, och det är `docs/beslutslogg.md` #38 som binder det.**
Railway kör om containern vid varje deploy och allt i den försvinner. Ett
persistent volume överlever, men det monteras på EN sökväg, och den sökvägen är
inte repots rot. Utan den här modulen hade varje modul behövt sin egen
miljövariabel.

**FÖRVALEN ÄR REPOTS EGNA, alltså ändras ingenting lokalt.** Sätts ingen
miljövariabel pekar allt precis där det pekade före skivan. Det är villkoret för
att en sådan här omläggning får göras alls: den ska vara osynlig tills någon
uttryckligen flyttar något.

**`config/` OCH `mallar/` STÅR INTE HÄR, och det är avsiktligt.** De är
versionerade, följer med i avbilden och ska göra det: `config/priser.json` och
`config/kategorier.yaml` är §10-grindade och ska ändras genom en deploy och inte
genom att någon redigerar en fil på en server. Att de INTE går att flytta är en
egenskap och inte en lucka.

**`docs/` OCH `scratchpad/` STÅR INTE HELLER HÄR.** De rörs bara av verktyg som
körs på Lars maskin.

**VARIABLERNA LÄSES NÄR MODULEN LADDAS, alltså när processen startar.** Att
ändra `MAILBOT_DATA` i en körande process gör ingenting: modulkonstanterna är
redan satta, och varje annan modul har redan byggt sina filnamn ur dem. Det är
rätt form för drift, där Railway sätter miljön före start, och det är skälet att
testerna prövar `_ur_miljon` och inte konstanterna.
"""

from __future__ import annotations

import os
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent


class Sokvagsfel(Exception):
    """En katalogvariabel pekar någonstans den inte får peka."""


# VAD VARJE VARIABEL FÅR PEKA PÅ INUTI REPOT, som `relativ.parts[:1]`.
#
# `()` betyder repotets ROT. `HEMLIGHETER` får peka dit därför att det är där
# `token.json`, `token-las.json` och `client_secret.json` ligger, alla
# gitignorerade var för sig. `DATA` och `LOGG` får peka på sina egna kataloger,
# som är gitignorerade i sin helhet.
#
# **ALLT ANNAT I REPOT ÄR SPÅRAT ELLER KAN BLI DET.** Se `_krav_pa_lage`.
TILLATNA_I_REPOT = {
    "MAILBOT_DATA": [("data",)],
    "MAILBOT_LOGG": [("logg",)],
    "MAILBOT_HEMLIGHETER": [()],
}


def _krav_pa_lage(namn: str, sokvag: Path) -> None:
    """Kastar när en katalogvariabel pekar in i repot på fel ställe.

    **DEN HÄR RADEN STÄNGER EN LUCKA SKIVA 53 SJÄLV ÖPPNADE, och den är §6.**
    Före skivan hårdkodade `vy.krav_pa_skrivbar_sokvag` `data/` och `logg/`
    UNDER REPOTS ROT. Att skriva kundtext till `src/` eller till repotets rot var
    då omöjligt, oavsett konfiguration.

    När katalogerna blev flyttbara blev de flyttbara ÖVERALLT, också tillbaka in
    i repot. Uppmätt: med `MAILBOT_LOGG` pekad på `src/` släppte
    `krav_pa_skrivbar_sokvag` igenom en skrivning dit. Vyn hade då skrivit rå
    kundtext till en SPÅRAD katalog, och nästa commit hade tagit den med sig.

    **DET ÄR DEN TYSTASTE FORMEN AV §6-LÄCKA:** filen hamnar i git i stället för
    hos Railway, alltså på ett ställe där den inte går att ta bort i efterhand.

    **UTANFÖR REPOT PRÖVAS INGENTING, och det är avsiktligt.** `/volym/data` och
    vilken annan sökväg som helst utanför roten är driftens sak. Regeln gäller
    bara den gräns repot självt kan råka ut för.
    """
    try:
        relativ = sokvag.resolve().relative_to(ROT.resolve())
    except ValueError:
        return

    tillatna = TILLATNA_I_REPOT[namn]
    if relativ.parts[:1] not in tillatna:
        vad = " eller ".join(
            "/".join(t) if t else "repotets rot" for t in tillatna
        )
        raise Sokvagsfel(
            f"{namn}={sokvag} pekar in i repot, på {relativ}. Inuti repot får "
            f"den bara peka på {vad}: allt annat är spårat eller kan bli det, "
            "och det som skrivs dit är rå kundtext eller en credential (§6)."
        )


def _ur_miljon(namn: str, forval: Path) -> Path:
    """Sökvägen ur miljövariabeln `namn`, eller `forval` när den inte är satt.

    **ETT TOMT VÄRDE RÄKNAS SOM OSATT.** `MAILBOT_DATA=` i en Railway-panel är
    lättare att åstadkomma än att ta bort raden, och en tom sträng hade blivit
    `Path("")`, alltså den aktuella katalogen. Att tyst skriva kundtext till
    arbetskatalogen är inte ett rimligt utfall av en tom ruta.
    """
    varde = (os.environ.get(namn) or "").strip()
    if not varde:
        return forval

    sokvag = Path(varde).expanduser()
    _krav_pa_lage(namn, sokvag)
    return sokvag


# KORPUSARNA OCH SKÖRDARNA. Gitignorerad, bär kundtext (§6).
DATA = _ur_miljon("MAILBOT_DATA", ROT / "data")

# LOGGARNA. `beslut.jsonl` är append-only enligt §0:s ramverksregel 4.
LOGG = _ur_miljon("MAILBOT_LOGG", ROT / "logg")

# TOKENFILERNA OCH `client_secret.json`.
#
# **EGEN VARIABEL OCH INTE EN UNDERKATALOG TILL `DATA`, och skillnaden är §6.**
# Kundtext och credentials är två olika slags hemligheter med två olika
# konsekvenser om de läcker, och de ska gå att lägga på var sitt ställe med var
# sina rättigheter. #38:s öppna punkt ur #20 gäller just det.
HEMLIGHETER = _ur_miljon("MAILBOT_HEMLIGHETER", ROT)


# KÖRNINGSLOGGEN. Driftutfall per dygn, aldrig kundtext (§6).
#
# **ETT FILNAMN I EN KATALOGMODUL, och skälet är att filen har EN SKRIVARE OCH
# EN LÄSARE PÅ VAR SIN SIDA OM `src/`.** `scripts/dagligen.py` skriver den,
# `src/vy.py` läser den. `scripts/` är ingen paketkatalog, alltså kan vyn inte
# importera slingan alls; och att låta slingan importera vyn för ETT filnamn
# hade dragit in hela vymodulen i den dagliga processen. Kvar blir en tredje
# plats, och det är den här.
#
# *Här stod att vyn inte FÅR importera slingan, därför att slingan startar
# `respond.py` som drar in `googleapiclient`. Det är falskt: en subprocess rör
# inte importgrafen, `scripts/dagligen.py` importerar bara stdlib och
# `src.sokvagar`, och filen säger det själv i sin egen inledning.
# `krav_pa_sandvagsfrihet` hade alltså inte fällt någonting. Fällt av
# §7-granskningen av skiva 54.*
#
# Alternativet vore samma sträng skriven på två ställen. Den dagen de skiljer sig
# åt skriver slingan till en fil och vyn läser en annan, och vyns rad säger då
# att ingen körning har lyckats — vilket är den enda formen av fel raden inte får
# ha, eftersom den finns för att larma om just det.
#
# **SÖKVÄGEN ÄR INTE HELA KONTRAKTET.** Fältnamnen i raden är det också, och de
# binds av `tests/test_drift.py::test_slingan_skriver_de_falt_vyns_korningsrad_
# LASER`, som kör skrivaren och ger läsaren resultatet. Den här kommentaren
# vaktade ett tag bara filnamnet, och ett byte av `startad` gav exakt det fel
# stycket ovan säger att raden inte får ha.
KORNINGSLOGG = LOGG / "korningar.jsonl"


def kataloger() -> dict[str, Path]:
    """De tre katalogerna, för utskrift vid uppstart.

    Returnerar SÖKVÄGAR och aldrig innehåll. §6: en sökväg är ingen hemlighet,
    det som ligger i den är det.
    """
    return {"data": DATA, "logg": LOGG, "hemligheter": HEMLIGHETER}
