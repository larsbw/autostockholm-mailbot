"""KEDJAN: inkommande mail till utkast i vyn. SÄNDVÄG.

Fram till skiva 34 fanns delarna var för sig och ingenting anropade något annat.
`slag_upp` anropades bara ur tester, och vyns granskningsläge hade ingen rutt.
Den här modulen är sömmen, och den är AVSIKTLIGT tunn: den fattar inga beslut
som någon av delarna redan fattar, den bara för vidare.

**INGEN SÄNDNING. VÄGEN SLUTAR I VYN.** Modulen har ingen väg till en brevlåda,
och `vy.krav_pa_sandvagsfrihet("src.kedja")` prövar hela kedjan, inte bara den
här filen: den vandrar importgrafen och läser källtexten i varje modul den når.

Ordningen är:

    mail -> klassificering -> uppslag om a-traktor -> generering -> spärrar
         -> utkast

**`kor` LOGGAR INTE SJÄLV, och skissen framställde det som om den gjorde det.**
Loggningen är ett eget anrop, `logga_beslut` eller `logga_kallfel`, och det görs
av anroparen. Skälet är att `kor` ska gå att köra i ett test utan att röra
disken. Anroparens ansvar är att en rad skrivs för VARJE utfall, källfelet
inräknat. Fällt av §7-granskningen av skiva 34, varv 2.

**HINKEN AVGÖR INGENTING HÄR, och det ska sägas rakt ut.** Ramverksregel 1 i
CLAUDE.md §0 gäller SÄNDNING, och ingenting i den här modulen skickar. Ett
utkast produceras därför för varje kategori, också de i `aldrig`, och hinken
loggas så att skuggläget kan mäta vad som HADE gått ut. Att låta hinken stoppa
generering här hade dolt precis det skuggläget finns för att visa, se
`docs/roadmap.md`.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable

from src import fordonsuppslag, generera, ometikettera
from src.fordonsuppslag import UppslagMisslyckades, Uppslag, Utfall
from src.generera import Forfragan, Sparrfalld
from src.vy import Fall, Granskningsfall, krav_pa_skrivbar_sokvag

ROT = Path(__file__).resolve().parent.parent
BESLUTSLOGG = ROT / "logg" / "beslut.jsonl"
TAXONOMIFIL = ROT / "data" / "taxonomi.json"

# KATEGORIERNA SOM GATAS AV FORDONSUPPSLAGET, ur `docs/roadmap.md` fas 4.5.
# Samma tre som `vy.A_TRAKTORETIKETTER`, och de står här som en egen tupel
# eftersom en import av vyns konstant hade gjort kedjan beroende av vyns
# rendering. `test_kedjans_a_traktorkategorier_matchar_vyns` binder att de två
# inte glider isär.
A_TRAKTORKATEGORIER = (
    "fråga om a-traktorkonvertering",
    "boka a-traktorkonvertering",
    "fråga om pris a-traktorkonvertering",
)


class Kallfel(Exception):
    """Uppslagskällan svarade inte alls.

    **SKILD FRÅN `UppslagMisslyckades` MED FLIT.** `slag_upp`:s docstring skriver
    ut varför: en källa som är nere är inte samma sak som ett fordon utan
    uppgifter, och att översätta det ena till det andra gör ett driftavbrott
    osynligt. Kedjan stannar på den här, och genererar inget alls.

    **`sort` ÄR DET ENDA SOM FÅR LOGGAS, och det är en §6-rättelse.** Undantaget
    byggs av `except Exception` runt ANROPARENS hämtfunktion, alltså inte av
    strängar `src/fordonsuppslag.py` äger. En `ConnectionError` från requests
    lyder *"HTTPSConnectionPool(host=biluppgifter.se, ...): Max retries exceeded
    with url: /fordon/ABC123"*, alltså bär den ett REGISTRERINGSNUMMER, som §6
    namnger som persondata och förbjuder i `logg/`.

    Meddelandet finns kvar i undantaget för den som står vid terminalen, där det
    inte persisteras. `sort` är typnamnet och inget annat, och det är vad
    `logga_kallfel` skriver. Fällt av §7-granskningen av skiva 34, varv 3.
    """

    def __init__(self, sort: str, detalj: str = ""):
        self.sort = sort
        super().__init__(f"{sort}: {detalj}" if detalj else sort)


@dataclass(frozen=True)
class Arende:
    """Ett inkommande mail, med det kedjan behöver och inget mer.

    **INGEN AVSÄNDARADRESS.** §6: loggar bär hashade avsändare. Fältet heter
    `avsandare_hash` för att en adress inte ska kunna smyga in genom att någon
    fyller ett fält som heter `avsandare`.
    """

    text: str
    amne: str = ""
    kanal: str | None = None
    regnr: str | None = None
    avsandare_hash: str = ""
    tidsstampel: str = ""


@dataclass(frozen=True)
class Steg:
    """Ett steg i kedjan, som det gick.

    `utfall` är kort och maskinläsbart, `detalj` är för en människa.
    """

    namn: str
    utfall: str
    detalj: str = ""


@dataclass(frozen=True)
class Kedjeutfall:
    """Vad kedjan kom fram till. Bär ALDRIG ett skickat mail."""

    kategori: str
    hink: str
    uppslag: Uppslag | None = None
    utfall: Utfall | None = None
    utkast: str | None = None
    sparr: str | None = None
    skal: str = ""
    steg: tuple[Steg, ...] = field(default_factory=tuple)

    @property
    def blev_utkast(self) -> bool:
        return self.utkast is not None


def _uppslagssteg(
    arende: Arende,
    hamta: Callable[[str], dict | None],
) -> tuple[Uppslag | None, Utfall | None, Steg]:
    """Uppslaget, och vad som hände.

    **TVÅ SORTERS MISSLYCKANDE, och de leder olika vägar.** Ett fordon utan
    uppgifter ger `uppslag=None` och kedjan fortsätter: generatorn har ett eget
    läge för det, och svaret säger att vi inte kunnat slå upp bilen. En källa som
    KASTAR något annat blir `Kallfel` och stoppar kedjan, eftersom vi då inte vet
    om bilen duger eller inte.
    """
    try:
        uppslag = fordonsuppslag.slag_upp(arende.regnr, hamta=hamta)
    except UppslagMisslyckades as fel:
        return None, None, Steg("uppslag", "misslyckades", str(fel))
    except Exception as fel:  # noqa: BLE001
        raise Kallfel(type(fel).__name__, str(fel)) from fel

    utfall = fordonsuppslag.utvardera(uppslag)
    return uppslag, utfall, Steg("uppslag", "lyckades", utfall.value)


def kor(
    arende: Arende,
    *,
    klient,
    hamta: Callable[[str], dict | None],
    hinkar: dict,
    taxonomi: list[str],
    exempel: list[dict] | None = None,
) -> Kedjeutfall:
    """Hela vägen för ETT ärende. Returnerar aldrig ett skickat mail.

    `klient`, `hamta` och `taxonomi` har inga förval. Den som anropar väljer
    modell, källa och kategorilista medvetet, vilket är samma skäl `slag_upp`
    anger för sitt eget `hamta`: en tyst standardkälla i en sändvägsmodul är
    precis det §10 finns för att hindra.

    **KLASSNINGEN ÄR PASS 2, och det ledet är fällt fram av kedjans egen
    provkörning.** Första lydelsen anropade `kategorisera.kategorisera_en` med
    dess förvalda systemprompt, alltså PASS 1, som uttryckligen säger *"Använd
    INGEN lista. Hitta det namn som passar texten."* Följden var att varje
    a-traktormail fick en påhittad etikett som `offert på a-traktorombyggnad`
    eller `konvertera till elbil`, och eftersom ingen av dem står i taxonomin
    **utlöstes fordonsuppslagets grind aldrig**. Tio av tio ärenden hoppade över
    uppslaget.

    Pass 1 är upptäcktspasset som BYGGER taxonomin. Pass 2 är det som väljer ur
    den, och bara pass 2 ger ett namn som `config/kategorier.yaml` kan hinka.
    """
    steg: list[Steg] = []

    kategori = ometikettera.ometikettera_en(
        klient,
        arende.text,
        taxonomi,
        ometikettera.bygg_system_pass2(taxonomi),
        amne=arende.amne,
        kanal=arende.kanal,
    )
    hink = _hink_for(kategori, hinkar)
    steg.append(Steg("klassificering", kategori, f"hink {hink}"))

    uppslag: Uppslag | None = None
    utfall: Utfall | None = None

    if kategori in A_TRAKTORKATEGORIER:
        uppslag, utfall, uppslagssteg = _uppslagssteg(arende, hamta)
        steg.append(uppslagssteg)
    else:
        steg.append(Steg("uppslag", "hoppades över", "kategorin gatas inte"))

    forfragan = Forfragan(
        text=arende.text,
        kategori=kategori,
        utfall=utfall,
        uppslag=uppslag,
        uppslag_gjordes=kategori in A_TRAKTORKATEGORIER,
    )

    try:
        utkast = generera.generera_utkast(klient, forfragan, exempel=exempel)
    except Sparrfalld as fel:
        steg.append(Steg("spärrar", "fälld", fel.sparr))
        return Kedjeutfall(
            kategori=kategori, hink=hink, uppslag=uppslag, utfall=utfall,
            sparr=fel.sparr, skal=fel.skal, steg=tuple(steg),
        )

    # INGEN RÄKNING HÄR. Strängen `alla tre` stod här och skrevs in i
    # `logg/beslut.jsonl`, alltså blev ett räknat tal en falsk uppgift i
    # skugglägets eget underlag i samma stund en fjärde spärr tillkom. §7.2
    # förbjuder processräkningar av precis det skälet.
    steg.append(Steg("spärrar", "passerade"))
    steg.append(Steg("utkast", "skapat", f"{len(utkast)} tecken"))

    return Kedjeutfall(
        kategori=kategori, hink=hink, uppslag=uppslag, utfall=utfall,
        utkast=utkast, steg=tuple(steg),
    )


def _hink_for(etikett: str, hinkar: dict) -> str:
    """Kategorins hink, med standardhinken som förval.

    **EN KATEGORI I TVÅ HINKAR LARMAR, den väljs aldrig tyst.** Formen är lånad
    från `scripts/kategoristatus.py::hink_for`, som gör detsamma med
    motiveringen *"bättre att utfallet blev synligt än tyst"*. Första lydelsen
    här valde `auto` före `aldrig`, alltså valde en SÄNDVÄGSMODUL den mest
    tillåtande hinken tyst, medan ett mätverktyg larmade. Fällt av
    §7-granskningen av skiva 34, varv 1.

    `tests/test_kategorier_yaml.py` gör läget omöjligt i dag. Skulle den vakten
    falla ska det synas här och inte tolkas till kategorins fördel.
    """
    i_auto = etikett in (hinkar.get("auto") or [])
    i_aldrig = etikett in (hinkar.get("aldrig") or [])

    if i_auto and i_aldrig:
        raise ValueError(
            f"kategorin {etikett!r} står i BÅDE auto och aldrig i "
            "config/kategorier.yaml. Kedjan väljer inte åt Lars."
        )
    if i_auto:
        return "auto"
    if i_aldrig:
        return "aldrig"
    return hinkar.get("standardhink", "utkast")


def till_granskningsfall(arende: Arende, utfall: Kedjeutfall) -> Granskningsfall:
    """Kedjans utfall som ett fall vyn kan visa. **VÄGENS SLUTPUNKT.**

    Utan den här funktionen slutade vägen i en `Kedjeutfall` som ingen kunde
    läsa: rutten `/granskning/N` fanns men hade ingen producent, alltså
    renderade den alltid *"Inga förslag"*. Fällt av §7-granskningen av skiva 34,
    varv 1.

    **HÖGST ETT AV `forslag` OCH `sparr` SÄTTS, och det är en egenskap hos
    `kor` och inte hos den här funktionen.** `kor`:s två normalvägar sätter
    antingen `utkast` eller `sparr`, aldrig båda.

    **INGETDERA VAR MÖJLIGT tills `tomt-svar` byggdes:** ett modellsvar som är
    tomt efter `.strip()` passerade varje spärr, och då blev `blev_utkast` sant
    medan `forslag` var tomt. Spärren stänger den vägen, se
    `docs/beslutslogg.md` #64. HÖGST och inte EXAKT står kvar ändå, eftersom
    garantin är `kor`:s och inte den här funktionens: en direkt konstruerad
    `Kedjeutfall` kan bära vad som helst.

    *Här stod att EXAKT ett av dem sätts, och sedan att `src/vy.py` skrivits om
    medan producentsidan stod kvar. Båda leden var fel: det var VYN som stod kvar
    med EXAKT, och meningen om att ett tomt svar passerar var i presens efter att
    samma varv hade byggt spärren som stoppar det. Fällt av §7-granskningen av
    skiva 34, varv 2 och varv 3.*

    Vad som däremot håller: en post med `sparr` satt får inget textfält av
    `rendera_granskning`, alltså går ett fällt förslag inte att omdöma.
    """
    return Granskningsfall(
        fall=Fall(
            etikett=utfall.kategori,
            kalla="kedjan",
            text=arende.text,
            tidsstampel=arende.tidsstampel,
            avsandare_hash=arende.avsandare_hash,
        ),
        forslag=utfall.utkast or "",
        sparr=utfall.sparr or "",
    )


# ------------------------------------------------------------------ DEL C


def logga_beslut(
    arende: Arende,
    utfall: Kedjeutfall,
    *,
    loggfil: Path = BESLUTSLOGG,
) -> dict:
    """En rad per ärende som passerat kedjan. APPEND-ONLY, §0 ramverksregel 4.

    **DET HÄR ÄR UNDERLAGET FÖR SKUGGLÄGET**, och `docs/roadmap.md` säger att
    det ska finnas INNAN skuggläget börjar. Raden bär det Lars namngav i skiva
    34: kategorin, uppslagets utfall, vilka spärrar som fällde, och om det blev
    ett utkast eller föll ur.

    **§6: INGEN PERSONDATA, och det ledet är fällt fram.** Raden bär
    `avsandare_hash` och aldrig en adress, och den bär ALDRIG utkastets text.
    Utkastet innehåller kundens namn och bilmodell, och en logg som bär det blir
    en persondatafil som lever kvar.

    **`skal` LOGGAS INTE, och det är skälet till att fältet saknas.** Första
    lydelsen skrev `Sparrfalld.skal`, som byggs av strängar lyfta ORDAGRANT ur
    modellens svar. Skriver boten ut ett telefonnummer lyder skälet *"talet …
    kommer varken ur uppslaget eller ur config"* med numret inbakat, och
    `genererat-fordonsfaktum` bär på samma sätt ett ord ur utkastet. Det hade
    redan hänt i den befintliga loggen när granskningen mätte den. Fällt av
    §7-granskningen av skiva 34, varv 1.

    Det maskinläsbara som skuggläget behöver är VILKEN spärr som fällde, och det
    står i `sparr`. Detaljen hör hemma där utkastet läses, alltså i vyn.

    **FILEN ÖPPNAS BARA I `a`-LÄGE.** Ramverksregel 4 är obrytbar, och
    `test_beslutsloggen_ar_APPEND_ONLY` binder att en andra skrivning inte
    raderar den första.
    """
    krav_pa_skrivbar_sokvag(loggfil)

    post = {
        "skrivet": datetime.now(timezone.utc).isoformat(),
        "avsandare_hash": arende.avsandare_hash,
        "tidsstampel": arende.tidsstampel,
        "kategori": utfall.kategori,
        "hink": utfall.hink,
        "uppslag": utfall.utfall.value if utfall.utfall is not None else None,
        "sparr": utfall.sparr,
        "blev_utkast": utfall.blev_utkast,
        "utkast_tecken": len(utfall.utkast) if utfall.utkast else 0,
        "steg": [{"namn": s.namn, "utfall": s.utfall, "detalj": s.detalj}
                 for s in utfall.steg],
    }

    return _skriv(post, loggfil)


def logga_kallfel(
    arende: Arende,
    fel: Kallfel,
    *,
    loggfil: Path = BESLUTSLOGG,
) -> dict:
    """En rad för ett ärende som STOPPADES av ett källfel.

    **ETT DRIFTAVBROTT SOM INTE LOGGAS SER UT SOM ETT ÄRENDE SOM ALDRIG KOM
    IN.** `kor` kastar `Kallfel` och anroparen hoppade vidare, alltså lämnade
    ett nere-liggande biluppgifter.se INGEN rad alls. Skuggläget ska kunna mäta
    hur ofta källan svek, och den skillnaden är exakt vad `Kallfel` byggdes för
    att bevara: ett felläst fält är inte ett saknat fordon.

    Fällt av §7-granskningen av skiva 34, varv 2, som också fällde att modulens
    flödesskiss påstod en rad *oavsett utfall* medan just det här utfallet inte
    fick någon.

    `fel` bär ett undantagsnamn och ett meddelande ur `src/fordonsuppslag.py`,
    alltså fasta strängar och fältnamn. Ingen kundtext, se `logga_beslut`.
    """
    krav_pa_skrivbar_sokvag(loggfil)

    return _skriv(
        {
            "skrivet": datetime.now(timezone.utc).isoformat(),
            "avsandare_hash": arende.avsandare_hash,
            "tidsstampel": arende.tidsstampel,
            "kategori": None,
            "hink": None,
            "uppslag": None,
            "sparr": None,
            "blev_utkast": False,
            "utkast_tecken": 0,
            # `fel.sort` OCH ALDRIG `str(fel)`: meddelandet byggs av anroparens
            # hämtfunktion och bär ett registreringsnummer när requests kastar.
            # Se `Kallfel`.
            "steg": [{"namn": "källa", "utfall": "stoppade kedjan",
                      "detalj": fel.sort}],
        },
        loggfil,
    )


def _skriv(post: dict, loggfil: Path) -> dict:
    """APPEND-ONLY. `a`-läget är ramverksregel 4 och står bara här."""
    loggfil.parent.mkdir(parents=True, exist_ok=True)
    with loggfil.open("a", encoding="utf-8") as fil:
        fil.write(json.dumps(post, ensure_ascii=False) + "\n")

    return post
