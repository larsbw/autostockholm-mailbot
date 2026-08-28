# Incidentlogg

**Version:** 0.7.0 · **Uppdaterad:** 2026-08-28 · **Implementerar** CLAUDE.md §0

Varje regel som bärs av en incident bor här. Dokumentet finns för att förlagornas
styrka är att en härdad regel namnger det fel som skapade den. En regel utan
incident är en förmodan; en regel med incident är ett ärr.

**En post skrivs bara om något faktiskt hänt.** Uppmätt, i det här repot, med
utdata som går att peka på. En hypotetisk risk hör hemma i `docs/sparrar.md` eller
i en beslutspost, aldrig här. Skälet är att posten annars ärver trovärdighet den
inte betalat för: nästa läsare kan inte skilja det som brann från det någon var
orolig för.

Posterna numreras I1, I2, och så vidare. Numren återanvänds aldrig.

---

## I1 — Ett defaultvärde binds när modulen laddas

**Datum:** 2026-08-26 · **Uppmätt i:** skiva 1 · **Berör:** `src/mine.py`,
`tests/test_mine.py`

**Vad som hände.** `logga_korning` hade `logg: Path = MININGLOGG` som
defaultvärde. Ett defaultvärde binds när modulen laddas, inte när funktionen
anropas, så parametern höll en referens till den ursprungliga sökvägen. När
testet bytte ut modulkonstanten `MININGLOGG` mot en temporärfil nådde utbytet
aldrig fram, och `main()` skrev till den riktiga `docs/mining-log.md`. Tre
påhittade körningsrader hann appendas till ett styrdokument innan felet
upptäcktes. De är borttagna.

Samma mönster satt kvar för `sov`, `klocka` och `slumpa`. Berörda funktioner,
avlästa ur `git grep -n "sov=time.sleep\|klocka=time.monotonic\|slumpa=random.random" 820c2ce -- src/mine.py`:
`fordrojning`, `Kvotpacer.__init__`, `_utfor`, `lista_trad_id`, `hamta_trad` och
`mina`. Det gjorde tre rader i testsviten verkningslösa. Raderna såg ut att hålla
sviten vaken och gjorde det inte, så sviten sov på riktigt utan att någon märkte
det.

**Vad det kostade.** Ett styrdokument i arbetsträdet bar under en tid tre rader
som påstod körningar mot brevlådan som aldrig ägt rum. Ingen körning skedde, men
dokumentet påstod motsatsen, vilket är precis den sortens obelagda påstående §7.2
finns för att stoppa.

**Skadan nådde aldrig historiken, och det var tur och inte konstruktion.**
`docs/mining-log.md` var ännu inte committad när raderna appendades: hela skiva 1
låg otrackad i arbetsträdet fram till `820c2ce`. Att felet upptäcktes före den
committen berodde på att ett nytt test råkade skriva till en temporärfil medan
den riktiga filen ändå växte, inte på någon spärr. Belägg:
`git grep -n "UTC" 820c2ce -- docs/mining-log.md` ger noll träffar, och
`git log --oneline --all -- docs/mining-log.md` visar att filens första commit är
`820c2ce`. Hade committen legat före upptäckten hade raderna varit permanenta.

**Hur det upptäcktes.** Inte genom läsning. `logga_korning`-felet föll ut när ett
nytt CLI-test skrev till en temporärfil och den riktiga filen ändå växte. De
kvarvarande fallen, de som rörde `sov`, `klocka` och `slumpa`, fann den oberoende
granskaren genom att MÄTA svittiden, inte genom att läsa koden: raderna såg
korrekta ut och var det inte.

**Uppmätt effekt.** Med samtliga lager fällda blev svitens utdata i skiva 1
`1 failed, 40 passed in 2.89s`, mot baslinjen `41 passed in 0.24s`. Granskaren
mätte i en egen, senare körning av samma fällning `1 failed, 40 passed in 2.90s`.
Talen är alltså två avläsningar av samma fenomen i olika körningar, inte ett tal
som ändrats.

**Reproduktion.** Fällningen är NEUTRALISERANDE och återinför defaultbindningen i
pacerns väg. Radnumren gäller `src/mine.py` från och med `8569073`, alltså inte
i `820c2ce` där samma rader ligger på 121 och 226. Kontrollera dem mot filen före
fällningen:

```
scripts/sparr-prova.sh --fil src/mine.py \
  --ersatt "126=    def __init__(self, enheter_per_minut=ENHETER_PER_MINUT, sov=time.sleep," \
  --ersatt "129=        self._sov = sov" \
  --ersatt "235=    pacer = Kvotpacer() if pacer is None else pacer"
```

Receptet ska stå här och inte lämnas åt läsaren att gissa: en granskare som
tolkade "samtliga lager" på två andra rimliga sätt fick utfall som inte låg i
närheten, och kunde alltså inte skilja en misslyckad reproduktion från ett falskt
tal. Kört om mot dagens svit 2026-08-26: `1 failed, 41 passed in 2.83s` mot
baslinjen `42 passed in 0.21s`. Skillnaden i antal test mot skiva 1 är att den
här skivan lagt till `test_lista_trad_id_med_noll_gor_inga_anrop`.

**Regeln posten bär.** Ett testdubbelt som injiceras genom att byta ut en
modulkonstant skyddar ingenting om anropet läser konstanten via ett defaultvärde.
**Injektionen ska gå genom argumentet vid anropstillfället.** Konkret: skriv
`def f(x=None)` och `x = STANDARD if x is None else x` i kroppen, aldrig
`def f(x=STANDARD)`, för varje värde ett test kan tänkas vilja byta ut.

**Vad som gör den svår att se.** Ett verkningslöst `monkeypatch.setattr` ger
ingen varning, inget rött test, och ingen felutskrift. Sviten förblir grön.
Det enda observerbara är att något som borde vara snabbt är långsamt, och det
märks inte förrän någon tittar efter. Därav kravet nedan.

**Vakt.** `tests/test_mine.py::test_pacerns_sovfunktion_gar_att_byta_ut_utifran`
asserterar att en utbytt `mine.time.sleep` FAKTISKT anropas. Utan den kan
regressionen komma tillbaka tyst, eftersom sviten förblir grön när den återvänder.

---

## I2 — Felet satt i rättelsen, i varje granskningsvarv

**Datum:** 2026-08-26 · **Uppmätt i:** skiva 8 · **Berör:** `docs/sparrar.md`,
`src/kategorisera.py`, `tests/test_kategorisera.py`

**Vad som hände.** Skiva 8 gick tre granskningsvarv, alltså §7:s tak, och
underkändes i alla tre. I varje varv satt minst ett fynd i den text som skrivits
för att rätta föregående varvs fynd.

Kedjan nedan. **Beläggen ligger på två ställen**, och det ska stå här eftersom
den första lydelsen sa att varje led var belagt i `docs/sparrar.md`:s
versionshistorik. Det gäller bara de två led som rör spärrdokumentet självt,
alltså `forbjudna-maskindomaner`-ledet i 0.9.0 och 0.10.0 och "sex lager"-ledet i
0.11.0. De övriga leden rör `.env`-parsern och testerna, och de beläggs i
`src/kategorisera.py` och `tests/test_kategorisera.py`. `grep -n "splitlines"
docs/sparrar.md` ger noll träffar, vilket är hela poängen med att skriva ut det.

- **Varv 1** underkände `.env`-parserns kodkommentar, som sa att formen
  `ANTHROPIC_API_KEY=värde` var obligatorisk medan parsern accepterade
  citattecken, blanksteg, indrag och en kommentar efter värdet. Den sista formen
  läste in kommentaren SOM DEL AV nyckeln.
- **Rättelsen** skrev en ny kommentar som avslutade med att varje avvikelse nu
  avvisas högljutt. **Varv 2** mätte upp att fem av sju avvikelseklasser i själva
  verket hoppas över tyst.
- **Varv 1** underkände också `docs/sparrar.md`:s påstående att spärren
  `forbjudna-maskindomaner` inte var redundant med något. **Rättelsen**, posten
  0.9.0, skrev ett `Uppmätt`-tal som inte motsvarade någon committad svit.
  **Varv 2** fällde det.
- **Rättelsen efter varv 2** skrev en ny kommentar som delade upp fallen i tysta
  och högljudda. **Varv 3** mätte upp att blanksteg hamnar på olika sidor
  beroende på om det står före eller efter likhetstecknet, och att kommentaren
  lade båda på den tysta sidan.
- **Samma rättelse** skrev posten 0.10.0, som sa att två rader i översiktstabellen
  skriver ut "Sig själv, två lager". Den ena raden skriver "sex lager".
- **Samma rättelse** skrev ett nytt test för radslut vars docstring tillskrev
  mekanismen `str.splitlines()`. **Varv 3** visade med fällningar att
  `Path.read_text()`:s universalradslut är det verksamma lagret och `splitlines`
  det redundanta andra.
- **Samma rättelse** skrev ett test för tomt värde som inte gick att fälla.

**Vad det kostade.** Grinden uttömdes utan godkännande. Skivan stannade före push
och krävde ett grindbeslut av Lars. Ingen falskhet nådde `origin`, men det berodde
på att §7 tog slut, inte på att texten blev sann.

**Hur det upptäcktes.** Av granskaren, i varje varv, och aldrig av den som skrev
rättelsen. Mönstret i sig namngavs först i tredje varvets rapport.

**Varför rättelsetext är farligare än originaltext.** Två mekanismer verkar
samtidigt. Den som skriver rättelsen har nyss läst fyndet och skriver mot minnet
av det i stället för mot filen, vilket är samma ifyllnadsfel som §7.2:s
omskrivningsregel beskriver. Och den som läser rättelsen läser den som ett svar på
en anmärkning, alltså med frågan "täcker den fyndet" i stället för "är den sann".
Båda leden drar åt samma håll, och resultatet är att den minst misstänkta texten i
en skiva granskas slappast.

**Regeln posten bär.** RÄTTELSETEXT GRANSKAS SOM NY TEXT. En mening skriven för
att rätta ett fynd bär inte lägre bevisbörda än den den ersätter. Granskaren prövar
rättelsen mot källan, inte mot fyndet den svarar på. Se CLAUDE.md §7.

---

## I3 — Ett undantag som funnits sedan första committen och nästan aldrig åberopades

**Datum:** 2026-08-26 · **Uppmätt i:** skiva 9, om skivorna 1 till 8 ·
**Berör:** `CLAUDE.md` §7

**Vad som hände.** §7:s dokumentdetaljundantag har funnits sedan repots första
commit och åberopades före skiva 9 i `e9a6772` (skiva 3) och `c8b1214` (skiva 8),
och inte däremellan. Undantagets ålder är avläst ur CLAUDE.md 0.4.0, som skriver
att det funnits sedan `f9b680a`.

**POSTEN SKRIVER INGET TOTALTAL, och det är en rättelse.** Den första lydelsen
sa "åberopades i två skivor" och angav
`git log --all --oneline --grep="dokumentdetaljundantag"` som belägg. Kommandot
gav tre träffar redan när posten committades, eftersom skiva 9:s egen commit
åberopar undantaget i sitt meddelande. Meningen blev alltså falsk av just den
commit som skrev den, vilket är ordagrant det CLAUDE.md 0.3.1 förbjuder: skriv
aldrig en mening som räknar sin egen omgivning. Posten namnger därför de
committar som fanns FÖRE skivan, vilket är stabila fakta, och överlåter dagens
läge åt den som kör kommandot.

**Talet i Lars instruktion stämmer inte, och det redovisas hellre än rättas
tyst.** Instruktionen till skiva 9 sa "åtta skivor, åtta underkännanden.
Undantaget fanns i sju av dem och åberopades i en." Båda leden faller:

- **"åberopades i en"** stämmer inte mot loggen. `e9a6772` och `c8b1214` är två,
  och de fanns båda före skivan.
- **"fanns i sju av åtta"** stämmer inte mot åldern. Undantaget fanns i `f9b680a`,
  alltså före skiva 1, och därmed i varje skiva.
- **"åtta underkännanden" går inte att läsa någonstans i repot.**
  Granskningsrapporterna ligger i den gitignorerade `scratchpad/`. Ingen siffra
  skrivs.

Det som faktiskt är mätbart, och som bär regeln, är att undantaget fanns hela
tiden och ändå åberopades bara i `e9a6772` och `c8b1214` före den här skivan,
trots att varje skiva har producerat dokumentdetaljer.

*Rättelse i 0.4.2: här stod "åberopades i två committar". Mätt VID `2d43d00`, som
är den commit meningen skrevs i, gav kommandot fyra träffar: `e9a6772`,
`c8b1214`, `ad72ce9` och `2d43d00` själv, eftersom de två sista bär strängen i
sina meddelanden. Meningen var alltså falsk i samma stund den skrevs,
tjugotvå rader under den fetstil som lovar att posten inte skriver något
totaltal. Den skrevs dessutom om FRÅN "två committade skivor" TILL "två
committar" i den commit som skulle rätta defekten, vilket gjorde den till en
direkt räkning av loggutdatan och alltså sämre. §7.2: vid omskrivning räknas
talet som oläst.*

**Vad det kostade.** Granskningsgrinden maldes på prosaformuleringar i skiva efter
skiva medan sändvägen förblev obyggd. Samma observation gjordes redan i CLAUDE.md
0.4.0, som mätte att `config/` och `mallar/` var tomma och att `src/` bara bar
`auth.py` och `mine.py`.

**Varför regeln inte bet.** Undantagets egen villkorsrad sa att det åberopas per
SKIVA, i briefen, aldrig per fynd i efterhand. En skiva som bygger kod kan inte
åberopa något per skiva utan att också undanta koden, och alternativet, att
åberopa det när dokumentfyndet dyker upp, var uttryckligen förbjudet. Regeln lämnade
alltså ingen väg som var både tillåten och användbar, och den ignorerades därför.

**Regeln posten bär.** Undantaget gäller per DEFEKTKLASS, inte per skiva.
Skillnaden går INUTI ett dokument och inuti en fil, inte mellan filer. En
kodkommentar, en docstring och ett commitmeddelande är text om kod och omfattas;
villkoret kommentaren beskriver är kod och omfattas inte. Se CLAUDE.md §7.

Posten delar mekanism med CLAUDE.md 0.5.0, som sänkte §10:s token-rad av samma
skäl: **en regel som gör systemet oanvändbart börjar ignoreras, och en ignorerad
regel skyddar ingenting.**

---

## I4 — Rättelser i svep inför nya fel snabbare än de tar bort gamla

**Datum:** 2026-08-27 · **Uppmätt i:** skiva 10, om skivorna 8 och 9 ·
**Berör:** `CLAUDE.md` §7, `docs/sparrar.md`, `docs/incidentlogg.md`

**Vad som hände.** I2 slog fast att fyndet satt i rättelsetexten. Regeln
RÄTTELSETEXT GRANSKAS SOM NY TEXT skrevs som svar. Den fångade varje efterföljande
instans, men den hindrade ingen av dem, eftersom den styr GRANSKAREN och inte den
som skriver.

Det som saknades var en regel om TAKT. Varje granskningsvarv fick en LISTA med
fynd och rättade hela listan i ett svep, i en enda skrivomgång, utan att någon
mening prövades mot källan innan nästa skrevs. Hur många fynd listorna bar
skrivs inte ut: rapporterna ligger i den gitignorerade `scratchpad/` och talet
går inte att läsa ur repot.

**De verifierbara instanserna, var och en med sin plats.** Varje rad är en
rättelsepost som själv bär ett fel, registrerat av nästa post:

| Rättelsen | Felet den bar | Registrerat i |
| --- | --- | --- |
| `docs/sparrar.md` 0.9.0 | ett `Uppmätt`-tal som inte motsvarade någon committad svit, och ett fällningskommando byggt på radnummer | 0.10.0 |
| `docs/sparrar.md` 0.10.0 | sa "Sig själv, två lager" om en rad som skriver "sex lager" | 0.11.0 |
| `docs/sparrar.md` 0.11.0 | "Två strykningar" när diffen bar en | 0.11.1 |
| `docs/sparrar.md` 0.11.1 | namngav fel post, två gånger | 0.11.2 |
| `docs/incidentlogg.md` 0.4.1 | skrev om ett tal FRÅN "två committade skivor" TILL "två committar", alltså till en direkt räkning av loggutdatan | 0.4.2 |
| `docs/incidentlogg.md` 0.4.2 | en förbjuden processräkning, "tredje skivan i rad" | 0.4.3 |
| `CLAUDE.md` 0.7.0 | skrev in ett tal som samma commit sa var obelagt | 0.7.1 |

Summan skrivs inte ut. §7.2 kräver att det kontrollerbara redovisas per post i en
lista och aldrig summerat i en bisats, och tabellen ovan är den listan.

**En instans utanför tabellen är äldre än mönstret och visar att det inte är
nytt.** `CLAUDE.md` 0.4.1 registrerar att "0.4.0-posten namngav fel post för
strykningen". Det är samma felklass som `docs/sparrar.md` 0.11.1 bar. Posten
skrevs i skiva 3, avläst ur `git log -S"0.4.1 — 2026-08-26" -- CLAUDE.md` som ger
`0b3f0ef`, "Rätta fyra falska påståenden ur skiva 3:s granskning". Instansen i
`docs/sparrar.md` skrevs i skiva 9.

Den står utanför tabellen därför att tabellen listar rättelseposter ur skiva 8
och 9, som är postens ämne. Ordinalen är borttagen: ett räkneord som "åttonde"
skriver ut totalen och gör tabellen till en summa, vilket är precis vad stycket
ovanför säger att posten inte gör.

**Vad det kostade.** §7:s grind uttömdes i både skiva 8 och skiva 9, båda
gångerna utan godkännande, och båda skivorna stannade före push i väntan på ett
grindbeslut av Lars. Nio committar låg lokalt när skiva 10 började. Ingen
falskhet nådde `origin`, men det berodde på att grinden tog slut och inte på att
texten blev sann.

**Hur det upptäcktes.** Av granskaren, varv efter varv. Aldrig av den som skrev
rättelsen, förrän i skiva 10: utkastet till `docs/sparrar.md` 0.11.2 bar
radnummer som den egna postens tillägg omedelbart sköt ner, och det fångades av
att numren slogs upp på nytt innan posten committades.

**Den instansen står INTE i tabellen ovan**, och kan inte stå där: tabellen
listar committade poster, och den här nådde aldrig en commit. Den går därför
inte att belägga mot repot, till skillnad från varje rad i tabellen, och den
redovisas som det den är, ett arbetsförlopp utan spår. Det som gör den värd att
nämna ändå är att den fångades av precis den takt regeln nedan föreskriver, och
att den är den första instansen som fångades av skribenten och inte av
granskaren.

**Varför svepet är farligare än den enskilda rättelsen.** Tre saker verkar
samtidigt. Den som rättar en hel lista håller hela listan i huvudet och skriver mot
minnet av listan i stället för mot filen. Rättelsetexten läses dessutom som ett
svar på en anmärkning, alltså med frågan "täcker den fyndet" i stället för "är
den sann". Och en appendixpost som läggs överst skjuter ner varje radnummer under
sig, så en rättelse som namnger rader föråldrar sig själv i samma skrivning.

**Regeln posten bär.** EN RÄTTELSE I TAGET, VERIFIERAD MOT KÄLLAN INNAN NÄSTA
SKRIVS. Rättelser görs inte i svep. Se CLAUDE.md §7.

**Vakt.** Ingen automatisk. Regeln styr arbetsordning och inte kod, och det finns
inget test som kan se att två meningar skrevs i fel ordning. Räkna med att felet
återkommer, och att granskarens prövning av rättelsetexten mot källan är det enda
som fångar det.

---

## I5 — `grep` mot `data/*.jsonl` ser bara ingressen, och nollan lästes som ett fynd

**Datum:** 2026-08-27 · **Uppmätt i:** skiva 11 ·
**Berör:** `data/tradar.jsonl`, `data/tradar_obesvarade.jsonl`, `src/urval.py`

**Vad som hände.** Skiva 11 skulle pröva ett påstående i sin egen brief: att
förmedlarnas notiser bär registreringsnummer i ett strukturerat fält. Prövningen
gjordes med `grep -cE` mot filraderna i `data/tradar_obesvarade.jsonl`, fick
noll, och skrev in i `docs/roadmap.md` att briefen var motbevisad.

Nollan var en artefakt, men INTE av det skäl utkastet trodde. Filraden bär
huvudena och fältet `snippet` i klartext; det är bara meddelandetexten som ligger
base64url-kodad, i `body.data` på den MIME-del som bär den. Den delen är en av
`payload.parts` när sådana finns och `payload` självt när de saknas, vilket
`src/urval.py::brodtext` säger i sin docstring och `::_platta` hanterar genom att
platta delträdet. En `grep` mot filraden ser alltså innehåll, men bara ingressen:
längsta uppmätta `snippet` är 201 tecken. I förmedlarnas notiser står
registreringsnumret längre ned, och därför fann `grep` noll.

**Ett andra utkast förklarade nollan med att `grep` "per konstruktion inte kan se
ett ord i något mail". Det är också falskt**, och det är därför den här posten
skriver ut mekanismen i stället för att nöja sig med regeln. I
`data/tradar.jsonl` fann rå `grep` 78 av 79 fält, samtliga via `snippet`. Vore
filraden ogenomskinlig hade det talet varit noll.

**Invändningen restes och avfärdades felaktigt, och det är postens egentliga
innehåll.** Det första utkastet ställde uttryckligen frågan om filerna kunde bära
base64 och prövade den med `grep -c "Hej" data/tradar_obesvarade.jsonl`, som gav
455. Slutsatsen blev att texten var avkodad och nollan verklig.

Mätningen gällde fel population. Filen bär 1604 trådar, och att 455 av dem bär
`Hej` någonstans säger ingenting om de 411 förmedlartrådar invändningen handlade
om. Att en invändning restes och avfärdades är värre än att den aldrig restes:
avfärdandet skrevs in i dokumentet som ett belägg, och gav nollan en trovärdighet
den inte hade.

**Uppmätt effekt.** Etikettform i alla celler, alltså ett regnr-ord följt av
kolon eller likhetstecken. Körningen är
`.venv/bin/python scripts/regnr-matning.py`, som avkodar via
`src/urval.py::brodtext`:

| Population | Rå filrad | Enbart `snippet` | Avkodad kropp |
| --- | --- | --- | --- |
| `data/tradar.jsonl`, alla 555 | 78 | 78 | 79 |
| `data/tradar_obesvarade.jsonl`, alla 1604 | 0 | 0 | 340 |
| förmedlartrådar bland obesvarade, 411 | 0 | 0 | 40 |

De två första kolumnerna är identiska i varje rad: allt `grep` hittade låg i
`snippet`. Förmedlartrådar är avgjorda på `From`, `Reply-To`, `Return-Path` och
`Sender`. Av de 40 bär `bokadirekt.se` 36 och `autobutler.se` 4.

**Det andra utkastet jämförde dessutom 3 mot 40 som om talen gällde samma sak.**
De gjorde det inte: 3 var ordträffar utan etikettkrav över hela filen, 40 var
etikettform över förmedlarsubsetet. Två dimensioner hade bytts utöver den som
stycket handlade om. Det ärliga paret för den populationen är 0 mot 40, och det
står i tabellen ovan.

**Vad det kostade.** Noll i sändvägen, och det berodde på grinden och inte på
texten. Falskheten fångades av §7-granskningen före commit och nådde aldrig
`origin`. Hade den skeppats hade fas 4.5 byggts utan fältavläsare, och boten hade
frågat kunder efter ett registreringsnummer de redan skickat.

**Hur det upptäcktes.** Av granskaren, som körde om mätningen och avkodade
kropparna i stället för att läsa filraden. Skribenten hade rest rätt invändning
och stängt den själv med fel mätning, alltså är det INTE ett fall där felet
saknade misstanke. Misstanken fanns och avfärdades.

**Regeln posten bär, i tre led.**

1. Ett textpåstående om innehållet i `data/*.jsonl` mäts genom
   `src/urval.py::brodtext` eller en likvärdig avkodning, aldrig genom `grep` mot
   filraden. **En nolltäckning från `grep` mot dessa filer är INKONKLUSIV** och
   får aldrig skrivas som ett negativt fynd. En TRÄFF är däremot äkta, vilket är
   vad som gör felet lömskt: verktyget fungerar ibland.
2. Prövas en hypotes om en DELMÄNGD ska kontrollmätningen göras på den
   delmängden. En räkning över hela filen kan inte avfärda en invändning som
   gäller en del av den, hur stort talet än blir.
3. **Två tal ställs bara mot varandra om varje dimension utom den jämförda är
   densamma.** Population, predikat och avkodning ska vara identiska. En
   jämförelse där två av tre bytts är inte en mätning av något.

**Vakt: `scripts/regnr-matning.py`, committat på Lars beslut i skiva 11.**
Mätningen låg först i den gitignorerade `scratchpad/` och fanns alltså inte i
repot. Skivans instruktion sade INGEN KOD, men den syftade på botens kod och inte
på ett mätverktyg som bär ett styrdokuments centrala påstående, och §9:s krav på
ett COMMITTAT skript väger tyngre. Skriptet mäter samma predikat i tre lager, rå
filrad, `snippet` och avkodad kropp, och lånar avkodningen ur `src/urval.py` i
stället för att kopiera den.

Vakten är partiell och ska läsas så. Den hindrar att talen blir ohärledbara och
gör talpar utan gemensam grund svåra att skriva, eftersom varje kolumn i utdatan
bär samma predikat. **Den hindrar inte att någon ställer en ny `grep` mot
`data/*.jsonl` och tror på nollan.** Ingen spärr kan se det, och `data/` är
gitignorerad så inget test kan köras mot den. Räkna med att felet återkommer vid
nästa mätning som görs snabbt, och att granskarens omkörning är det som fångar
det.

---

## I6 — En sammanfattad föreskrift tappade ett kriterium och skeppade en sändvägsdefekt

**Datum:** 2026-08-27 · **Uppmätt i:** skiva 13, om skivorna 11 och 12 ·
**Berör:** `docs/roadmap.md` fas 4.5, `src/fordonsuppslag.py`

**Vad som hände.** Fas 4.5 vilade på VVFS 2003:19 4 kap 42 §. Paragrafen fanns
aldrig i repot. Det som fanns var en SAMMANFATTNING ur en brief: att §42 kräver
kopplingsanordning och att fordonet i övrigt är lämpligt som dragfordon, utan att
ange något tal.

Sammanfattningen var fel på två sätt. Paragrafen anger ett tal, och den anger
**två alternativa kriterier förenade med *eller***. Sammanfattningen bar bara det
ena, och det utan tal.

Följden byggdes in i koden. `utvardera` prövade släpvagnsvikten ensam, så **ett
fordon med tjänstevikt 2 100 kg och släpvagnsvikt 800 kg fick RÖTT**, medan
föreskriften säger att det ÄR lämpligt som dragfordon. Boten hade sagt nej till
en kund vars bil uppfyller kravet.

Ovanpå det byggdes en hel ram: talet 1 000 kallades Auto Stockholms praxis, med
verkstadens erfarenhet och besked från besiktningsmän som namngiven källa, och
fas 4.5 slog fast att en mall som återgav talet som författningskrav vore en
sändvägsdefekt. **Ramen var precis tvärtemot vad som gällde**, och den hade en
egen paragraf i fasen och tre stycken i beslutspost #24.

**Samma felklass i en andra form.** §39 om barlastflak formulerades om ur minnet
i skiva 11 och igen i skiva 12. Den återgivningen råkade stämma i sak för första
stycket, men paragrafens andra stycke, om påhängsvagn och att minst 40 % av
tjänstevikten skall vila på drivhjulen, fanns inte i repot förrän §39 citerades
ordagrant.

**Vad det kostade.** En skeppad sändvägsdefekt. Skiva 12 pushades med felet i
koden, och `6f8bbfc` bär det. Skadan mot kund blev noll, men det berodde på att
fas 4.5 inte är kopplad till någon sändning ännu och inte på att felet fångades.

Granskningsarbete lades dessutom på att räta ut viktledets riktning i §39, alltså
i ett krav som inte gatade något och som utgick helt kort därefter. Det skedde i
skiva 11, enligt `docs/beslutslogg.md` #24 och `docs/roadmap.md` 0.3.0. **Antalet
varv skrivs inte ut**: rapporterna ligger i den gitignorerade `scratchpad/` och
talet går inte att läsa ur repot (§7.2).

**Hur det upptäcktes.** Genom att Lars gav instruktionen att slå upp paragrafen
och rapportera vad som faktiskt står. **Ingen granskning hittade det**, och det
kunde ingen granskning göra: repot bar en sammanfattning och en granskare som
prövar text mot repot hittar då bara sammanfattningen. Felet var osynligt inifrån.

**Uppmätt effekt.** Sammanfattningen bar ett av två kriterier. Föreskriften är
hämtad från `webapp.trafikverket.se/TRVFS/pdf/2003nr019.pdf` och citeras
ordagrant i `docs/roadmap.md` fas 4.5, tryckt sida 16 för §42 och sida 15 för
§39.

**Regeln posten bär. EN FÖRESKRIFT CITERAS ORDAGRANT, ALDRIG SAMMANFATTAD.**
Beslut av Lars i skiva 13. Det gäller varje författningstext som en fas eller en
mall vilar på. En sammanfattning ser ut som ett faktum men bär ingen
kontrollerbar källa, och skillnaden mellan "så här minns vi det" och "så här
står det" måste vara synlig för nästa läsare.

Följdregel: **ett citat ska ange var det är hämtat och var i källan det står.**
Utan det är citatet bara en sammanfattning med citattecken.

**Vakt.** Ingen automatisk, och det finns ingen rimlig sådan: ingen kod kan veta
att en text i `docs/` är en korrekt avskrift av en författning. Vakten är regeln
plus att en granskare kan jämföra ett citat mot en namngiven källa, vilket är
precis vad en sammanfattning omöjliggör. **Räkna med att felet återkommer varje
gång en föreskrift refereras utan att någon öppnat den.**

---

## Mall för en incidentpost

Kopiera blocket nedan. Ett fält som inte går att fylla i är ett skäl att inte
skriva posten ännu, inte ett skäl att lämna fältet tomt.

### `I<n> — <vad som gick fel, i en rad>`

- **Datum, var det uppmättes, vad det berör.** Fil och funktion.
- **Vad som hände.** Förloppet, inte slutsatsen. Vad koden gjorde, inte vad den
  borde ha gjort.
- **Vad det kostade.** Den faktiska skadan. Blev den noll, skriv noll och skriv
  varför den blev noll, eftersom det oftast var tur och inte konstruktion.
- **Hur det upptäcktes.** Särskilt om det INTE var genom läsning. Ett fel som
  bara en mätning kunde hitta säger något om vilka fel som finns kvar.
- **Uppmätt effekt.** Tal avlästa ur verktygsutdata, med körningen namngiven.
  Inga tal ur minnet (§7.2).
- **Regeln posten bär.** Formulerad så att den går att följa utan att känna till
  incidenten.
- **Vakt.** Testet eller spärren som gör att felet inte kan återkomma tyst. Finns
  ingen, skriv `ingen` och räkna med att felet återkommer.

---

## I7 — En kvitterad återställning lämnade fällningens kod kvar i bytekoden

**Uppmätt i:** skiva 17, av granskaren · **Berör:** `scripts/sparr-prova.sh`,
CLAUDE.md §7.1

**Vad som hände.** En §7.1-fällning av `src/kanal.py` bytte `        return ra`
mot `        return ""`. Verktyget körde sviten, fick RÖD, återställde filen och
kvitterade: `filens sha256 identisk med utgångsläget: OK` och `git diff
identisk med utgångsdiffen: OK`.

**Nästa `pytest` var ändå röd.** Samma test föll, med
`AssertionError: assert '' == 'Fråga om pris'`, alltså på fällningens beteende,
medan ingen rad i repot bar felet.

**Orsaken.** CPython validerar en `.pyc` mot källans MTIME och STORLEK, inte mot
dess innehåll. De två raderna är exakt lika långa, och fällning och
återställning skedde inom samma sekund. Bytekoden såg därför giltig ut och kördes
i stället för den återställda källan.

**Varför kvittensen inte fångade det.** Både sha256 och `git diff` mäter FILEN.
Ingen av dem säger något om vad tolken kommer att köra. §7.1:s regel "Kvittera
återställningen, anta den aldrig" var alltså uppfylld till punkt och pricka, och
ändå var repot i ett falskt tillstånd.

**Följden under granskningen.** En fällning rapporterade fyra fallna test i
stället för tre. Det fjärde var föroreningen. Granskaren såg avvikelsen, spårade
den, och kunde visa att källan var oskadd genom att köra sviten med
`PYTHONPYCACHEPREFIX` satt utanför repot.

**Åtgärd.** `scripts/sparr-prova.sh` raderar `__pycache__` under repot i BÅDA
riktningarna, och kvitterar att katalogerna är borta.

- **Efter körningen**, i återställningen, mot det som hände här: en föråldrad
  `.pyc` gör repot rött när källan är återställd.
- **Före sviten**, direkt efter muteringen, mot det FARLIGARE fallet. En mutation
  skriven inom samma sekund som förra skrivningen, med samma längd, kan läsas ur
  en färsk `.pyc` så att fällningen aldrig får effekt. Verktyget hade då
  rapporterat GRÖN, och ett äkta spärrtest hade dömts som vakuöst.
- **Kvittensen** räknar kvarvarande `__pycache__` och stoppar med exit 2 om
  någon finns. En städning som tyst misslyckas hade återskapat samma lucka.

Verifierat genom att reproducera fällningen ordagrant: verdiktet är RÖD,
kvittensraden `bytekod under repot städad: OK` skrivs ut, och sviten är grön
efteråt. Verktygets `--sjalvtest` kör oförändrat igenom.

**Den andra riktningen upptäcktes av granskaren i samma varv som åtgärden.**
Den första fixen täckte bara det fall incidenten visade, alltså den riktning som
råkade göra sig hörd. Att den motsatta var den farligare syntes först när någon
frågade vad åtgärden INTE gjorde.

**Vad incidenten säger i stort.** En kvittens mäter det den mäter. Två oberoende
kontroller av samma storhet, filens innehåll, ger ingen täckning av en tredje
storhet, tolkens cache. Ett verktyg som betygsätter sig självt genom att
rapportera OK är inte prövat förrän någon prövat det utfall det inte tittar på.

---

## Appendix — versionshistorik (nyaste överst)

### 0.7.0 — 2026-08-28

**I7 tillkommer:** en kvitterad §7.1-återställning lämnade fällningens kod kvar
i `__pycache__`, och nästa svitkörning var röd utan att någon rad i repot bar
felet. Funnen av granskaren i skiva 17.

Posten bär åtgärden i `scripts/sparr-prova.sh` och skälet: sha256 och `git diff`
mäter båda FILEN, och två oberoende kontroller av samma storhet ger ingen
täckning av tolkens cache.

Ny post ⇒ MINOR.

### 0.6.0 — 2026-08-27

**I6 tillkommer:** en sammanfattad föreskrift tappade ett kriterium och skeppade
en sändvägsdefekt. VVFS 2003:19 4 kap 42 § fanns aldrig i repot, bara en
sammanfattning ur en brief, och den bar ett av paragrafens två alternativa
kriterier och utan tal.

Följden byggdes in i `utvardera`: ett fordon med tjänstevikt 2 100 kg och
släpvagnsvikt 800 kg fick RÖTT trots att föreskriften säger att det duger.
Ovanpå det byggdes en praxisram som var raka motsatsen till vad som gällde.

**Posten bär regeln EN FÖRESKRIFT CITERAS ORDAGRANT, ALDRIG SAMMANFATTAD**,
beslutad av Lars i skiva 13, med följdregeln att ett citat ska ange var det är
hämtat och var i källan det står.

**Ingen granskning hittade felet, och ingen kunde.** Repot bar en
sammanfattning, och en granskare som prövar text mot repot hittar då bara
sammanfattningen. Posten skriver ut att vakten är regeln och inte kod: ingen
kod kan veta att en text i `docs/` är en korrekt avskrift av en författning.

Ny post ⇒ MINOR.

### 0.5.0 — 2026-08-27

**I5 tillkommer:** `grep` mot `data/*.jsonl` ser bara ingressen, och nollan lästes
som ett fynd. Uppmätt i skiva 11, där en `grep`-mätning gav noll och skrevs in i
`docs/roadmap.md` som ett motbevis mot skivans egen brief.

**Posten bär tre regler.** Innehållspåståenden om `data/*.jsonl` mäts genom
`src/urval.py::brodtext`, och en nolltäckning från `grep` är inkonklusiv medan en
träff är äkta. Prövas en hypotes om en delmängd görs kontrollmätningen på den
delmängden. Och två tal ställs bara mot varandra om varje dimension utom den
jämförda är densamma.

**Mekanismen är utskriven därför att ett utkast fick den om bakfoten.** Utkastet
skrev att filraden är base64 och att `grep` "per konstruktion" inte kan se ett ord
i något mail. Filraden bär `snippet` i klartext, och rå `grep` fann 78 av 79 fält
i `data/tradar.jsonl` just den vägen. Orsaken till nollan är att `snippet` är
avkortad, längst uppmätt 201 tecken, och att fältet i förmedlarnas notiser ligger
bortom den. En regel med rätt slutsats och fel mekanism leder nästa läsare fel i
motsatt riktning, och det är därför den tredje regeln finns.

**Posten bär en PARTIELL vakt, och det är utskrivet.** `scripts/regnr-matning.py`
är committat på Lars beslut och gör talen härledbara med ett kommando. Den
hindrar inte att någon ställer en ny `grep` mot `data/*.jsonl` och tror på
nollan, och posten säger det i stället för att låta skriptet läsas som ett skydd.

Skadan blev noll, och posten skriver ut att det berodde på §7-grinden och inte på
texten.

Ny post ⇒ MINOR.

### 0.4.4 — 2026-08-27

Rättelser i I4 efter §7-granskningen av skiva 10. Varje punkt nedan satt i den
tabell eller den brödtext som är postens eget bevis, vilket är samma svepmönster
posten dokumenterar. Antalet skrivs inte ut: listan är det kontrollerbara, och
§7.2 kräver att sådant redovisas per post och aldrig summerat i en bisats.

- **Tabellrad 2 tillskrev fel post ett fel.** Radnummerfelet bars av 0.9.0 och
  registrerades av 0.10.0, inte tvärtom. Avläst ur att stycket "Radnummer var
  tillbaka. 0.9.0 byggde sitt fällningskommando på `201=` och `282=`" ligger
  mellan rubrikerna `### 0.10.0` och `### 0.9.0` i `docs/sparrar.md`. Raderna 1
  och 2 är rättade.
- **"En åttonde instans" skrev ut summan tre rader under löftet att inte göra
  det.** Ordinalen är borttagen. Samma felklass som I3 fick sin rättelse för i
  0.4.2, med kortare avstånd.
- **"två skivor tidigare" är sex.** CLAUDE.md 0.4.1 skrevs i skiva 3, avläst ur
  `git log -S"0.4.1 — 2026-08-26" -- CLAUDE.md` som ger `0b3f0ef`;
  `docs/sparrar.md` 0.11.1 skrevs i skiva 9. Talet är ersatt av de två skivorna.
- **Utkastinstansen påstods stå "i tabellen ovan".** Den gör den inte och kan
  inte göra det: tabellen listar committade poster. Stycket säger nu det, och
  redovisar instansen som ett arbetsförlopp utan spår i repot.

**En processräkning struken ur brödtexten.** "Varje granskningsvarv fick en lista
med fem till sju fynd" går inte att läsa ur repot av samma skäl som posten själv
anför om rapporterna i gitignorerade `scratchpad/`. Talet är borta.

**Två stycken flyttade tillbaka till I1.** Fälten "Vad som gör den svår att se"
och "Vakt" om `monkeypatch` och pacerns sovfunktion hörde till I1 och hamnade i
slutet av I3 när I2 och I3 sattes in i skiva 9. Avläst ur
`git show 196e60a:docs/incidentlogg.md`, där de ligger direkt efter I1:s "Regeln
posten bär". Flytten är återställd.

Rättade påståenden ⇒ PATCH.

### 0.4.3 — 2026-08-27

**I4 tillkommer**, på beslut av Lars i skiva 10, och bär regeln EN RÄTTELSE I
TAGET som skrivs in i CLAUDE.md §7 i samma skiva. Posten räknar upp de
rättelseposter som själva bar ett fel, var och en med sin plats, och skriver
ingen summa.

*Rättelse i 0.4.4: sista ledet var falskt när det skrevs. I4 bar då ordinalen
"En åttonde instans" tre rader under sitt eget löfte att inte summera. Ordinalen
är struken i 0.4.4 och påståendet är sant i dag, men det var det inte här.
CLAUDE.md 0.8.1 redovisar sin identiska tvilling; den här noten är
incidentloggens.*

**En processräkning struken ur 0.4.2.** Den skrev "Detta är tredje skivan i rad"
och "i andra granskningsvarvet". §7.2 namnger båda formerna ordagrant som
förbjudna, instanser av ett mönster respektive granskningsvarv, och den första
går inte att belägga: dokumenterade instanser finns för skiva 8 i I2 och för
skiva 9 i I3:s rättelsenot, alltså inte för tre skivor. Strykningen är gjord på
plats med kursiv not, enligt beslutsloggens undantag.

**Samma processräkning står kvar i commit-meddelandet till `d8e5494`** och kan
inte rättas där utan att historiken skrivs om. Den redovisas här i stället, som
beslutslogg #15 gjorde med ett påhittat tal i `b597950`.

Ny post och en strykning ⇒ MINOR.

### 0.4.2 — 2026-08-27

**I3 skrev ett totaltal tjugotvå rader under sin egen fetstil om att den inte
gör det.** Sammanfattningsmeningen sa "åberopades i två committar". Mätt vid
`2d43d00`, den commit meningen skrevs i, gav
`git log --all --oneline --grep="dokumentdetaljundantag"` fyra träffar.

Rättelsen i 0.4.1 gjorde meningen SÄMRE och inte bättre: den skrevs om från "två
committade skivor" till "två committar", vilket förvandlade en luddig formulering
till en direkt räkning av loggutdatan. §7.2 säger att ett tal räknas som oläst
vid omskrivning och ska verifieras på nytt. Det gjordes inte.

Meningen namnger nu de två committar som fanns FÖRE skivan, precis som stycket
ovanför den och som CLAUDE.md §7 redan gjorde. Avgränsningen "före den här
skivan" var det som saknades.

Fyndet satt i rättelsetexten igen, vilket är exakt vad I2 handlar om och vad
CLAUDE.md §7:s regel RÄTTELSETEXT GRANSKAS SOM NY TEXT finns för att fånga.
Regeln fångade det här fallet.

*Rättelse i 0.4.3: här stod "Detta är tredje skivan i rad", och meningen slutade
med "i andra granskningsvarvet". Båda är processräkningar av det slag §7.2
namnger ordagrant som förbjudna, instanser av ett mönster respektive
granskningsvarv, och den första går inte att belägga: dokumenterade instanser
finns för skiva 8 i I2 och för skiva 9 här, alltså inte för tre skivor. De
verifierbara instanserna räknas upp i I4 i stället, var och en med sin plats.*

Rättat påstående ⇒ PATCH.

### 0.4.1 — 2026-08-27

Rättelser efter §7-granskningen av skiva 9, som underkände 0.4.0:s poster på tre
punkter. Alla tre satt i text skriven för att rätta ett tidigare fynd, vilket är
precis vad I2 handlar om.

- **I2 påstod att varje led var belagt i `docs/sparrar.md`.** Fem av sju led
  beläggs i `src/kategorisera.py` och `tests/test_kategorisera.py`.
  `grep -n "splitlines" docs/sparrar.md` ger exit 1. Posten skriver nu ut
  uppdelningen.
- **I3:s grep-mening blev falsk av sin egen commit.** Den sa att kommandot ger två
  träffar; det gav tre redan när posten committades, eftersom skiva 9:s eget
  commitmeddelande åberopar undantaget. Posten namnger nu de committar som fanns
  före skivan och överlåter dagens läge åt den som kör kommandot. Rubriken följde
  med.
- **I3 kallade "åtta underkännanden" en förbjuden processräkning.** Den
  formuleringen räknade själv granskningsvarv i samma post. Skälet att inte skriva
  talet är enklare och sant: det går inte att läsa i repot, eftersom rapporterna
  ligger i gitignorerade `scratchpad/`. En räkning som DÄREMOT går att läsa ur
  repot, som antalet versionsposter i `docs/sparrar.md`, omfattas inte av
  förbudet, och I2:s "tre granskningsvarv" är av det slaget: 0.9.0, 0.10.0 och
  0.11.0 bär ett varv var.

Rättade påståenden ⇒ PATCH.

### 0.4.0 — 2026-08-26

**I2 och I3 tillkommer**, båda på beslut av Lars i skiva 9, och båda bär en regel
som skrivs in i CLAUDE.md §7 i samma skiva.

I2 dokumenterar att skiva 8:s fynd i alla tre granskningsvarven satt i den text
som skrivits för att rätta föregående varvs fynd. Beläggen ligger på två ställen:
de två led som rör spärrdokumentet i `docs/sparrar.md` 0.9.0 till 0.11.0, och de
övriga i `src/kategorisera.py` och `tests/test_kategorisera.py`. Posten skriver ut
den uppdelningen.

I3 dokumenterar att §7:s dokumentdetaljundantag funnits sedan repots första commit
och åberopats sällan. **Posten redovisar samtidigt att Lars instruktions tal inte
gick att belägga**, och skriver ut varför i stället för att återge dem.

**Posten skriver medvetet inget totaltal över hur många skivor som åberopat
undantaget.** Varje skiva som åberopar det ändrar talet, och en mening som räknar
sin egen omgivning blir falsk av just den commit som skriver den. Posten namnger
i stället de committar som fanns FÖRE skivan.

Två nya poster ⇒ MINOR.

### 0.3.0 — 2026-08-26

**`Speglar` ersätts av en sektionspekare utan versionsnummer**, beslut av Lars i
skiva 3. Ingen incidentpost ändrad. ⇒ MINOR.

### 0.2.1 — 2026-08-26

Korsreferenssynk till CLAUDE.md 0.3.2. Ingen post ändrad. ⇒ PATCH.

### 0.2.0 — 2026-08-26

Post I1 utvidgad och rättad efter granskning. Per post:

- Stycket "Vad som hände" sa att raderna nådde ett **committat** styrdokument.
  Ordet är struket. Filen var otrackad när det hände. Samma fel rättades i
  "Vad det kostade" redan i `b03139d`, men raden i "Vad som hände" lämnades kvar,
  så posten motsade sig själv mellan två stycken.
- Reproduktionsreceptet sa att radnumren gäller från och med `820c2ce`. De gäller
  från och med `8569073`; i `820c2ce` ligger samma rader på 121 och 226. Den som
  följde anvisningen bokstavligen hade muterat fel rader.
- "Hade committen legat en halvtimme tidigare" bar ett kontrafaktiskt tal utan
  källa. Siffran är struken, meningen bär utan den.
- "De fyra kvarvarande fallen" räknade fall som posten inte räknar upp. Ersatt
  med vilka värden det gällde.

**Om formen.** Post I1 skrevs om på plats i `b03139d`, efter att den committats i
`7397e8e`, utan versionshöjning och utan appendixpost. Det bryter mot §8 och mot
beslutsloggens räckviddsregel. Den här posten är rättelsen: I1:s brödtext ändras
härefter inte utan att en versionspost redovisar vad som ändrades.

Utvidgad post och ny regel om formen ⇒ MINOR.

### 0.1.0 — 2026-08-26

Dokumentet upprättat. `CLAUDE.md` §0 har räknat upp filen sedan repots första
commit `f9b680a` utan att den funnits, och CLAUDE.md 0.2.0:s appendix skrev
uttryckligen att loggen "börjar tom". Den börjar inte tom: skiva 1 producerade
I1, uppmätt och inte hypotetisk. Strukturen följer `docs/sparrar.md`.
