"""Testkorpusens kanoniska pris UTAN källa. Skiva 43 DEL A, Lars beslut.

**VARFÖR MODULEN FINNS.** Korpusen använde `25 000 kr` som sitt exempel på ett
pris som saknar källa. Det är också ett fullt rimligt pris för en
a-traktorkonvertering, alltså kolliderade exemplet med verkligheten: när
`config/priser.json` fylldes med just det talet gick en rad vakter röda, och bara
EN av dem vaktade Lars beslut. Resten gick röda därför att ett test råkade ha
valt samma tal.

**HUR STOR EFFEKTEN ÄR, MÄTT PÅ DAGENS KORPUS.** Fyll en post med sentineltalet
självt, alltså med korpusens kanoniska okällade pris, och kör sviten:
`23 failed, 1473 passed, 54 skipped, 16 xfailed`. Det är formen den gamla
korpusen hade för ett VERKLIGT pris.

**FÖR DE FLESTA VERKLIGA PRISER ÄR UTFALLET `1 failed`, MEN INTE FÖR ALLA.**
Uppmätt `1 failed` för bland andra `25 000 kr`, `18 000 kr`, `1400 kr`,
`1500 kr`, `1 000 kr`, `55 kr` och `123456 kr`. Men `7`, `10`, `14`, `15`, `50`,
`70`, `90`, `156` och `1450 kr` ger fler, eftersom andra korpusrader ännu bär
dem. Se LUCKA 58 i `docs/sparrar.md`.

*Talet stod som 21, skrivet i varv 1 och oläst efter varv 2, som bytte
ytterligare två korpusrader till sentineltalet i samma commit. Omkört till 23 i
varv 3. Och här stod att utfallet för "ett verkligt pris i dag" är `1 failed`,
utan förbehåll; nio lagliga belopp falsifierar det. Fällt av §7-granskningen av
skiva 43, varv 3.*

*Här stod "elva vakter" och "de tio andra". Talet kom ur Lars brief och inte ur
repot, och det gick inte att reproducera: `grep -rn "gick röda" docs/` hittade
ingen mätning, och skiva 42:s poster bär ingen. Det är samma fel som skiva 42:s
"de fem nycklar", alltså ett tal avskrivet ur en order i stället för läst ur
källan. §7.2 gäller också ett tal som kommer ur en order. Fällt av
§7-granskningen av skiva 43, varv 1.*

**LARS BESLUT:** korpusen ska byta exempeltal, inte verkligheten. Vad Auto
Stockholm tar betalt får inte styras av vilket tal ett test råkar använda. Se
`docs/beslutslogg.md` #103.

**VARFÖR JUST DET HÄR TALET.** Tre krav, och talet uppfyller alla tre:

1. **Det kan aldrig vara ett riktigt pris i den här verksamheten.** 99 999 999 kr
   är omkring hundra miljoner kronor för en tjänst som prissätts i tiotusental.
   En post i `config/priser.json` som bär det är absurd vid en enda blick, alltså
   kan Lars aldrig fylla det av misstag och kollisionen kan inte återuppstå.

2. **Det krockar inte med något annat tal repot använder.** En avläst vikt ligger
   mellan `biluppgifter.MIN_VIKT_KG` och `MAX_VIKT_KG`, alltså 1 till 9999,
   trösklarna i VVFS 2003:19 är 2 000 och 1 000, årtal har fyra siffror, ledtider
   en till två, och `ALLTID_TILLATNA_TAL` är 1, 2 och 3. Åtta nior ligger utanför
   varje sådan mängd. `git grep -n "99999999" 8492939` gav noll träffar, alltså
   fanns talet inte i repot innan den här modulen skrevs. *Raden sade "tröskeln
   … är 1 000", i bestämd singular. `src/fordonsuppslag.py` bär TVÅ trösklar och
   skriver ut att de är alternativa kriterier förenade med ELLER. Slutsatsen bär,
   bisatsen gjorde det inte. Fällt av §7-granskningen av skiva 43, varv 3.*

3. **Det syns som en markör.** En repsiffra läses direkt som ett testvärde och
   inte som en avläsning, vilket är hela poängen: nästa läsare ska inte behöva
   fråga sig om talet kom ur en källa.

**TALET SKRIVS I TVÅ FORMER, och båda ger samma token ur `_tal_i`.**
`SENTINELPRIS` bär tusenavskiljare som ett pris skrivs i löptext, och
`SENTINELPRIS_IHOP` är formen utan avskiljare för de rader som prövar att ett tal
ihopskrivet med sin enhet inte blir osynligt. `SENTINELTAL` är inte en tredje
skrivform utan den TOKEN `generera._tal_i` normaliserar båda till, alltså det som
faktiskt jämförs mot källan. Bundet av
`test_SENTINELTALET_ar_samma_i_varje_skrivform`.

*Här stod "TRE FORMER", vilket räknade `SENTINELTAL` som en skrivform, och
"tjänstevikter och släpvagnsvikter är tre till fyra siffror", vilket inte är
repots faktiska intervall. Båda fällda av §7-granskningen av skiva 43, varv 1.*
"""

from __future__ import annotations

# Talet som det skrivs i löptext, med blanksteg som tusenavskiljare.
SENTINELPRIS = "99 999 999"

# Samma tal utan avskiljare, för raderna som prövar ihopskrivna former.
SENTINELPRIS_IHOP = "99999999"

# Samma tal som `generera._tal_i` normaliserar det, alltså det som jämförs mot
# källan.
SENTINELTAL = "99999999"
