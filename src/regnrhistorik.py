"""Regnrfiltret: vad Gmail vet om ANDRA trådar med samma registreringsnummer.

UPPDRAG 2026-09-25, DEL 1, Lars beslut (tolkning A). Bara den SENASTE
a-traktorförfrågan om en bil ska få ett utkast. En bil som redan fått ett
riktigt SVAR inom `FONSTER_DAGAR` ska inte få något nytt automatiskt utkast
alls under fönstret. Ett obesickat UTKAST i en äldre tråd är INTE ett stopp:
kommer en nyare förfrågan om samma bil in tas det gamla utkastet bort och
den nya får ett eget, se `src.kedja.RegnrLage`.

LÄSER, SKICKAR ALDRIG. Modulen skapar och tar aldrig bort ett utkast själv;
det gör `scripts/respond.py` via `src.gmailutkast.ta_bort_utkast`, efter att
`src.kedja.kor` bekräftat att den nya förfrågan går vidare. Den här modulen
bara söker och svarar.

GROVT NÄT, EXAKT LOKALT FILTER. Samma mönster som `src/inkorg.py`: Gmails
`q` är bara ett fönster som håller kvoten nere, aldrig den exakta gränsen.
Gmails egen tokenisering av en söksträng som "KZE564" är inte dokumenterad
(avsökt 2026-09-25: supportsidan för sökoperatorer säger vilka operatorer
som finns, inte hur fritext utan operator delas i token), alltså vilar den
exakta träffen på samma mönster som extraherar ett regnr ur ett kundmail,
`maskera.REGNR`, normaliserat med `fordonsuppslag.normalisera_regnr` och
prövat mot VARJE kandidattråds meddelanden. Ett registreringsnummer utan
inre skiljetecken ("KZE564") delas inte av något känt tokenmönster, men §1
förbjuder att vila på den gissningen ensam.

`mine.lista_trad_id`/`mine.hamta_trad` ÅTERANVÄNDS OCH INTE EGNA ANROP. De
bär kvotpacing och backoff mot 429, och en egen väg hade behövt hålla takt
med den, samma skäl `inkorg.dagens_tradar` anger.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from src import fordonsuppslag, inkorg, maskera, mine, urval, vy
from src.kedja import RegnrLage

FONSTER_DAGAR = 14


def _inom_fonstret(meddelande: dict, nu: datetime, dagar: int) -> bool:
    """Är meddelandet inom de senaste `dagar` dagarna, räknat FRÅN `nu`?

    **SAMMA MÖNSTER SOM `inkorg.fonstrets_granser`/`_ar_fran_dagen`.** Gmails
    `newer_than:` är bara det grova nätet (modulens docstring), inte gränsen:
    dess inklusivitet och tidszon är odokumenterad, precis det skälet
    `inkorg.py` anger för sin egen 24-timmarsgräns. Skillnaden här är bara
    fönstrets längd, dagar i stället för timmar. Ett meddelande utan
    `internalDate` räknas INTE som inom fönstret, samma val som
    `inkorg._ar_fran_dagen` gör.
    """
    ra = meddelande.get("internalDate")
    if not ra:
        return False
    borjan = int((nu - timedelta(days=dagar)).timestamp() * 1000)
    slut = int(nu.timestamp() * 1000)
    return borjan <= int(ra) <= slut


def _regnr_i_meddelandet(meddelande: dict) -> str:
    """Normaliserat regnr ur meddelandets brödtext, eller tom sträng.

    Samma mönster som `scripts/respond.py::_regnr_i`, som medvetet återanvänder
    `maskera.REGNR` i stället för ett eget. Två mönster hade kunnat driva isär.
    """
    traff = maskera.REGNR.search(urval.brodtext(meddelande))
    return fordonsuppslag.normalisera_regnr(traff.group(0) if traff else None)


def sok(
    tjanst: inkorg.Lastjanst,
    regnr: str,
    eget_trad_id: str,
    egen_tidsstampel: str,
    nu: datetime,
    *,
    dagar: int = FONSTER_DAGAR,
    omdomesfil=None,
    pacer=None,
    forbrukning=None,
) -> RegnrLage:
    """Söker Gmail efter ANDRA trådar med samma regnr och avgör utfallet.

    `regnr` ska redan vara normaliserat (`fordonsuppslag.normalisera_regnr`),
    samma form `kedja.kor` skickar. `eget_trad_id` utesluts ur träffarna: utan
    den skulle den egna förfrågan jämföras mot sig själv.

    **EN NYARE TRÅD STOPPAR.** "Nyare" avgörs av den andra trådens SENASTE
    kundmeddelande, samma mått som `Arende.tidsstampel`
    (`scripts/respond.py::_senaste_kundmeddelandet`), jämfört mot
    `egen_tidsstampel`. Ett strikt senare värde stoppar; lika gammalt gör det
    inte, så att ETT mail som råkar ge två identiska tidsstämplar inte
    stoppar sig själv genom en annan tråd.

    **ETT RIKTIGT SVAR STOPPAR ALLTID**, oavsett ålder. `urval.ar_gmail_svar`
    är samma kriterium `arende_ur_trad` sätter `Arende.besvarad` med.

    **ETT OBESICKAT UTKAST STOPPAR INTE.** Dess tråd-ID samlas i stället i
    `aldre_utkast_trad_id`, för borttagning OM den här förfrågan går vidare.
    `vy.gmailutkast_finns` avgör om tråden bär ett sådant utkast just nu.
    """
    omdomesfil = vy.OMDOMEN if omdomesfil is None else omdomesfil
    # `mine.lista_trad_id`/`mine.hamta_trad` HAR INGET FÖRVAL FÖR NÅGONDERA,
    # till skillnad från `mine.mina`, som slår upp dem samma väg. En egen väg
    # som glömde det hade kastat `AttributeError` mot `None.vanta`.
    pacer = mine.Kvotpacer() if pacer is None else pacer
    forbrukning = mine.Forbrukning() if forbrukning is None else forbrukning
    fraga = f"{regnr} newer_than:{dagar}d"
    trad_id_lista = mine.lista_trad_id(
        tjanst, pacer=pacer, forbrukning=forbrukning, fraga=fraga,
    )

    egen_tid = datetime.fromisoformat(egen_tidsstampel) if egen_tidsstampel \
        else None

    stoppa = False
    aldre_utkast: list[str] = []

    for trad_id in trad_id_lista:
        if trad_id == eget_trad_id:
            continue
        trad = mine.hamta_trad(
            tjanst, trad_id, pacer=pacer, forbrukning=forbrukning,
        )
        # LOKAL BEKRÄFTELSE, BÅDA LEDEN. Gmails `q` är bara det grova nätet:
        # `_inom_fonstret` prövar DAGARNA, `_regnr_i_meddelandet` nedan
        # prövar TEXTEN. Se modulens docstring för varför ingetdera litar på
        # Gmail ensamt.
        meddelanden = [m for m in trad.get("messages") or []
                       if _inom_fonstret(m, nu, dagar)]

        if not any(_regnr_i_meddelandet(m) == regnr
                   for m in meddelanden if urval.ar_kundmeddelande(m)):
            continue

        if any(urval.ar_gmail_svar(m) for m in meddelanden):
            stoppa = True
            continue

        kundmeddelanden = [m for m in meddelanden if urval.ar_kundmeddelande(m)]
        if kundmeddelanden and egen_tid is not None:
            senaste = max(kundmeddelanden,
                          key=lambda m: int(m.get("internalDate") or 0))
            senaste_tidsstampel = urval.tidsstampel(senaste)
            if senaste_tidsstampel:
                if datetime.fromisoformat(senaste_tidsstampel) > egen_tid:
                    stoppa = True
                    continue

        if vy.gmailutkast_finns(trad_id, omdomesfil):
            aldre_utkast.append(trad_id)

    if stoppa:
        return RegnrLage(stoppa=True)
    return RegnrLage(stoppa=False, aldre_utkast_trad_id=tuple(aldre_utkast))
