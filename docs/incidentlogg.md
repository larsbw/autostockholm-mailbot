# Incidentlogg

**Version:** 0.4.1 · **Uppdaterad:** 2026-08-27 · **Implementerar** CLAUDE.md §0

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
tiden och åberopades i två committar trots att varje skiva har producerat
dokumentdetaljer.

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

**Vad som gör den svår att se.** Ett verkningslöst `monkeypatch.setattr` ger
ingen varning, inget rött test, och ingen felutskrift. Sviten förblir grön.
Det enda observerbara är att något som borde vara snabbt är långsamt, och det
märks inte förrän någon tittar efter. Därav kravet nedan.

**Vakt.** `tests/test_mine.py::test_pacerns_sovfunktion_gar_att_byta_ut_utifran`
asserterar att en utbytt `mine.time.sleep` FAKTISKT anropas. Utan den kan
regressionen komma tillbaka tyst, eftersom sviten förblir grön när den återvänder.

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

## Appendix — versionshistorik (nyaste överst)

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
