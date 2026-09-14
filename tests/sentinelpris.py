"""Testkorpusens kanoniska pris UTAN källa. Skiva 43 DEL A, Lars beslut.

**VARFÖR MODULEN FINNS.** Korpusen använde `25 000 kr` som sitt exempel på ett
pris som saknar källa. Det är också ett fullt rimligt pris för en
a-traktorkonvertering, alltså kolliderade exemplet med verkligheten: när
`config/priser.json` fylldes med just det talet gick elva vakter röda, och bara
EN av dem vaktade Lars beslut. De tio andra gick röda därför att ett test råkade
ha valt samma tal.

**LARS BESLUT:** korpusen ska byta exempeltal, inte verkligheten. Vad Auto
Stockholm tar betalt får inte styras av vilket tal ett test råkar använda. Se
`docs/beslutslogg.md` #103.

**VARFÖR JUST DET HÄR TALET.** Tre krav, och talet uppfyller alla tre:

1. **Det kan aldrig vara ett riktigt pris i den här verksamheten.** 99 999 999 kr
   är omkring hundra miljoner kronor för en tjänst som prissätts i tiotusental.
   En post i `config/priser.json` som bär det är absurd vid en enda blick, alltså
   kan Lars aldrig fylla det av misstag och kollisionen kan inte återuppstå.

2. **Det krockar inte med något annat tal repot använder.** Tjänstevikter och
   släpvagnsvikter är tre till fyra siffror, tröskeln i VVFS 2003:19 är 1 000,
   årtal fyra siffror, ledtider en till två, och `ALLTID_TILLATNA_TAL` är 1, 2
   och 3. Åtta nior ligger utanför varje sådan mängd. `grep -rn "99999999"` gav
   noll träffar i repot innan den här modulen skrevs.

3. **Det syns som en markör.** En repsiffra läses direkt som ett testvärde och
   inte som en avläsning, vilket är hela poängen: nästa läsare ska inte behöva
   fråga sig om talet kom ur en källa.

**TALET SKRIVS I TRE FORMER, och alla tre ger samma token ur `_tal_i`.**
`SENTINELPRIS` bär tusenavskiljare som ett pris skrivs i löptext,
`SENTINELPRIS_IHOP` är formen utan avskiljare för de rader som prövar att ett tal
ihopskrivet med sin enhet inte blir osynligt, och båda normaliseras till
`SENTINELTAL`.
"""

from __future__ import annotations

# Talet som det skrivs i löptext, med blanksteg som tusenavskiljare.
SENTINELPRIS = "99 999 999"

# Samma tal utan avskiljare, för raderna som prövar ihopskrivna former.
SENTINELPRIS_IHOP = "99999999"

# Samma tal som `generera._tal_i` normaliserar det, alltså det som jämförs mot
# källan.
SENTINELTAL = "99999999"
