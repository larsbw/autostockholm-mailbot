"""Vilken kanal ett inkommande mail kom in genom, och dess ämnesrad.

VARFÖR MODULEN FINNS. Klassificeraren läste bara fritexten. Webbformuläret ÄR
a-traktorformuläret, men dess inskick spred sig över kategorierna eftersom
ingenting i prompten sade var texten kom ifrån. Uppmätt i skiva 17 med
`scripts/formular-matning.py`: av 78 formulärtrådar klassades 42 som något annat
än en a-traktorkategori. Se `docs/beslutslogg.md` #29.

**KANALEN ÄR KONTEXT, ALDRIG GRUND, MED ETT UNDANTAG SEDAN SKIVA 73**, se
nedan. Lars regel, införd i #27 och tillämpad här: en kanalsignal får användas som bekräftande signal och som säker positiv
träff, aldrig som nödvändigt villkor och aldrig som ensam grund. En text som kom
via formuläret men uppenbart handlar om något annat ska fortfarande kunna klassas
som det.

**INGEN FUNKTION HÄR AVGÖR EN KATEGORI.** Modulen namnger en kanal och lämnar
ämnesraden. Klassningen, `src/ometikettera.py`, använder kanalen bara som
kontext i prompten.

**ETT SMALT UNDANTAG SEDAN SKIVA 73, Lars beslut.** `src/kedja.py::kor` byter
en kategori utanför a-traktor, och utanför hinken `aldrig`, mot
`kedja.KANALKATEGORI` när kanalen är `WEBBFORMULAR`. Markören är ingen gissning
på kanal: formuläret ÄR a-traktorformuläret. Principen gäller i övrigt. Se
`docs/sparrar.md` under `kanal-som-kontext-aldrig-grund`.

*Här stod att kopplingen kanal → kategori inte finns i kod och inte ska finnas.
Sant till och med skiva 72.*
"""

from __future__ import annotations

from email.header import decode_header, make_header

from src import urval

# Ämnesraden som webbformuläret sätter. Formuläret är a-traktorformuläret:
# dess fältblock bär `Registreringsnummer`, `Bilmodell` och `Växellåda`, alla
# tre i 78 trådar av 78, uppmätt med `scripts/formular-matning.py`.
#
# VARFÖR `Växellåda` finns i formuläret är Lars uppgift och inte en mätning:
# manuell och automat påverkar hastighetsbegränsningen vid ombyggnad. Skälet
# står här för att det förklarar varför fältblocket är a-traktorspecifikt, men
# det går inte att belägga ur repot och ska inte citeras som mätt.
#
# DETTA ÄR ENDA DEFINITIONEN. `scripts/formular-matning.py` och
# `scripts/besvarad-omklassning.py` läser den härifrån i stället för att bära
# egna kopior.
WEBBFORMULAR_MARKOR = "offertförfrågan a-traktor"

# Namnet som går in i prompten. Det säger vad formuläret ÄR, eftersom det är
# den upplysning klassificeraren saknade.
WEBBFORMULAR = "webbformuläret för a-traktorkonvertering"


def amnesrad(meddelande: dict) -> str:
    """Ämnesraden, avkodad ur eventuell MIME-kodning.

    En kodad ämnesrad ser ut som `=?UTF-8?B?...?=` i råhuvudet, och en
    prövning mot den råa strängen missar varje ämnesrad med svenska tecken.
    Faller avkodningen returneras råvärdet, aldrig ett undantag: en trasig
    ämnesrad ska inte kosta klassificeringen av texten.
    """
    ra = urval.huvudvarde(meddelande, "subject")
    try:
        return str(make_header(decode_header(ra)))
    except Exception:  # noqa: BLE001
        return ra


def ar_webbformular(meddelande: dict) -> bool:
    """Kom meddelandet via webbformuläret?

    Prövningen är på ÄMNESRADEN och inte på avsändardomänen. Den egna domänen
    bär också annan maskinell trafik: uppmätt i #27 delar 103 av 105
    maskinmailtrådar med egen domän adress med bokningsnotiserna.
    """
    return WEBBFORMULAR_MARKOR in amnesrad(meddelande).lower()


def namnge(meddelande: dict) -> str | None:
    """Kanalens namn, eller None när den inte går att fastställa.

    None betyder VET INTE, aldrig `e-post` som slasktratt. Ett påhittat
    kanalnamn hade varit en signal som såg mätt ut, och regeln ovan bygger på
    att kanalen är en bekräftande signal: en signal man hittat på bekräftar
    ingenting.
    """
    return WEBBFORMULAR if ar_webbformular(meddelande) else None
