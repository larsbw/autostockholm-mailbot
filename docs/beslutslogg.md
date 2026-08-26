# Beslutslogg

**Version:** 0.3.0 · **Uppdaterad:** 2026-08-26 · **Speglar:** CLAUDE.md 0.3.0

Sekventiell och append-only. Nummer återanvänds aldrig. En post rättas genom en
ny post som upphäver den, aldrig genom att den gamla skrivs om.

Append-only binder från och med den commit som inför posten. Redigering av en
post som ännu inte committats är utkastarbete och kräver ingen rättelsepost.

**Räckvidd.** Regeln binder de NUMRERADE beslutsposterna. Appendix är
versionshistorik och lyder under §8: en ändring där redovisas med en ny
versionspost, inte genom att en äldre versionspost skrivs om. Två committar i
skiva 1, `8569073` och `0cd6751`, skrev om 0.1.1:s appendixpost på plats i stället
för att lägga till en ny. De står kvar som de är. Den här raden namnger dem, så
att nästa läsare ser att historiken har den skarven i sig.

---

## #1 — Mining hämtar hela tråden, och pacingen dimensioneras mot per-användarkvoten

**Datum:** 2026-08-26 · **Berör:** `src/mine.py`

**Beslut.** `src/mine.py` hämtar varje tråd med `threads.get` i ett anrop i
stället för `messages.get` per meddelande, och sprider ut anropen mot Gmails
per-användarkvot.

**Underlag.** Kvottabellen är avläst denna dag ur
`https://developers.google.com/workspace/gmail/api/reference/quota`. Sidan anger
"Last updated 2026-07-31 UTC" och att gränserna uppdaterades "As of May 1, 2026".
GCP-projektet `autostockholm-mailbot` är skapat efter det datumet och lyder under
dessa värden:

| Post | Värde |
| --- | --- |
| `threads.list` | 10 kvotenheter |
| `threads.get` | 40 kvotenheter |
| Per minut per projekt | 1 200 000 kvotenheter |
| Per minut per användare per projekt | 6 000 kvotenheter |

Boten kör mot en enda brevlåda, så per-användargränsen binder långt före
projektgränsen. Pacingen dimensioneras därför mot 6 000 enheter per minut.

**Marginalen är ett val, inte ett avläst värde.** `ANDEL_AV_KVOT = 0.5` i
`src/mine.py` är satt för att Matte och Lars egna Gmail-klienter och mobiler
förbrukar ur samma per-användarpott, och en mining-körning får inte tränga ut
dem. Talet har inget mätt underlag och ska revideras när den första körningen
visat faktisk samtidig förbrukning. Öppet antagande, i samma anda som §10:s
gräns på 5 mail per körning.

**Konsekvens.** Halva potten är 3 000 enheter per minut, och 40 enheter per
`threads.get` ger 75 `threads.get` per minut. Det är ett övre gränsvärde för
hämtningsdelen, inte för körningen som helhet: `threads.list` förbrukar ur samma
pott, så den faktiska trådtakten ligger strax under. Båda talen är avlästa ur
`src/mine.py` och låsta av `tests/test_mine.py::test_pacingen_dimensioneras_mot_anvandarkvoten`.
En större brevlåda tar därför tid att mina, och det är avsiktligt.

**Alternativ som valdes bort.** `messages.get` per meddelande ger samma innehåll
men ett anrop per meddelande i stället för ett per tråd. Dyrare i både kvot och
väggklocka utan att tillföra något.

---

## #2 — Auktorisering öppnar aldrig webbläsare av sig själv

**Datum:** 2026-08-26 · **Berör:** `src/auth.py`

**Beslut.** `hamta_credentials()` har `tillat_webblasare=False` som förval.
Ordningen är återanvänd, förnya, auktorisera. En giltig token returneras utan
att `token.json` skrivs om. En utgången token med `refresh_token` förnyas tyst.
Först när ingetdera går krävs webbläsarflödet, och då bara om anroparen
uttryckligen begärt det.

**Skäl.** CLAUDE.md §10 gör första sändningen i en ny miljö till Lars beslut, och
första auktoriseringen är den grind som öppnar den miljön. Ett förval som öppnar
webbläsaren skulle låta vilket skript som helst dra igång auktoriseringen som
sidoeffekt. `src/mine.py` anropar därför alltid med `tillat_webblasare=False` och
faller med `AuthFel` i stället för att auktorisera på egen hand.

**Konsekvens.** Auktorisering sker med ett eget, uttryckligt kommando:
`.venv/bin/python -m src.auth --auktorisera`.

---

## #3 — §10:s gräns per körning är 1, och #1:s referens till 5 upphävs

**Datum:** 2026-08-26 · **Berör:** `docs/beslutslogg.md` #1, `CLAUDE.md` §10

**Beslut.** §10:s gräns för hur många mail en körning får skicka är **1**, satt av
Lars i skiva 2. `CLAUDE.md` 0.3.0 bär ändringen och dess skäl.

**Vad som upphävs.** Post #1 skriver, i presens, "i samma anda som §10:s gräns på
5 mail per körning". Den meningen var sann när den skrevs och är det inte längre.
**#1 skrivs inte om**, eftersom regeln i det här dokumentets huvud förbjuder det
för en committad post. Läs i stället #1:s mening som daterad till `820c2ce`, och
den här posten som dess rättelse.

**Vad som INTE upphävs.** #1:s sak står kvar: `ANDEL_AV_KVOT` är ett öppet
antagande utan mätt underlag. Bara jämförelsetalet är föråldrat, inte poängen den
gjorde.

**Hur felet uppstod.** Skiva 2 ändrade §10 från 5 till 1 och missade att
beslutsloggen citerade det gamla talet i presens. Ett tal som är avläst när det
skrivs blir falskt när dess källa ändras, och ingenting i verktygskedjan varnar
för det. Granskaren fann det med `grep -rn "5 mail" CLAUDE.md docs`. Kör om den
sökningen och skilj på tre sorters träff: §10:s egen rad, som nu bär 1;
CLAUDE.md 0.2.0:s appendix, där 5 är korrekt daterad historik; och #1:s mening,
som är den föråldrade. Referenser inifrån den här posten räknas inte, de citerar
felet.

---

## Appendix — versionshistorik (nyaste överst)

### 0.3.0 — 2026-08-26

Post **#3** tillkommer och upphäver #1:s referens till §10:s gräns på 5 mail per
körning. Talet är 1 sedan CLAUDE.md 0.3.0. #1 är orörd.

**Append-only-regelns räckvidd skrivs ut i huvudet.** Regeln binder de numrerade
beslutsposterna; appendix lyder under §8. Raden namnger också att `8569073` och
`0cd6751` skrev om 0.1.1:s appendixpost på plats. Utan den raden gör den nya
regeln repots egen färska historik till retroaktiva brott utan att någon ser det.

**Om 0.2.0-postens svar.** Att append-only binder från committen kom som
uttrycklig instruktion från Lars i skiva 2, tillsammans med beskedet att
hanteringen i skiva 1 var rätt. Det var alltså inte passets egen tolkning. Det
skrivs ut här därför att 0.1.1:s appendix ställde frågan till Lars och en läsare
annars inte kan se vem som svarade.

Ny post och utvidgad regel i huvudet ⇒ MINOR.

### 0.2.0 — 2026-08-26

**Den öppna frågan i 0.1.1:s appendixpost är BESVARAD.** Frågan gällde om
append-only omfattar redigeringar gjorda innan posten committats. Svaret står nu
i dokumentets huvud: append-only binder från och med den commit som inför posten,
och redigering dessförinnan är utkastarbete som inte kräver rättelsepost.

Frågan besvaras här och inte genom att 0.1.1:s post skrivs om. Det vore att
tillämpa den lösare tolkningen på en post som redan är committad, alltså precis
det regeln nu förbjuder.

**Hanteringen i skiva 1 var rätt.** Post #1 rättades innan loggen committades
första gången, och ingen rättelsepost skrevs. Det är vad regeln nu föreskriver.

Ny regel i huvudet ⇒ MINOR.

### 0.1.1 — 2026-08-26

Rättelser i #1 efter granskning, per post:

- Kvottabellens minutgränser bar inte kvalifikationen "per projekt" som
  källsidan skriver ut. Rättat till "per minut per projekt" respektive "per minut
  per användare per projekt".
- Konsekvensstycket kallade 75 trådar per minut för "taket" trots att
  `threads.list` förbrukar ur samma pott. Omformulerat till övre gränsvärde för
  hämtningsdelen. Talet 75 är omräknat och avläst på nytt enligt
  omskrivningsregeln, inte ärvt genom omformuleringen.

**Om append-only och det här passet.** Rättelserna gjordes innan loggen
committades första gången, alltså på en post som aldrig funnits i historiken.
Ingen committad post har skrivits om. Belägget är `git show
820c2ce:docs/beslutslogg.md`: där bär post #1 redan sin rättade lydelse, både
kvottabellens "Per minut per användare per projekt" och konsekvensstyckets "övre
gränsvärde". Huruvida regeln på raderna 5 och 6 ska omfatta även
förcommit-redigeringar är en öppen fråga till Lars; som den står ger den inget
svar, och det här passet har valt den tolkning som historiken kan bekräfta.

Inga beslut ändrade, bara formuleringen av deras underlag ⇒ PATCH.

### 0.1.0 — 2026-08-26

Loggen upprättad vid första arkitekturbeslutet, enligt CLAUDE.md:s versionshuvud.
Posterna #1 och #2 skrivna i samma pass som `src/mine.py` och `src/auth.py`.
