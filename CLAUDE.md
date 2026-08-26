# CLAUDE.md — autostockholm-mailbot

**Version:** 0.5.5 · **Uppdaterad:** 2026-08-26 · **Speglar:** beslutslogg #13

Beteenderegler för AI-agenten i autostockholm-mailbot. Läses vid varje sessionsstart.
Ärvd från tradingbot-v2 1.5.0 och SEO-agent, anpassad för ett system som skickar mail
i Auto Stockholms namn. **Tradeoff:** reglerna prioriterar försiktighet före hastighet.
Ett skickat mail går inte att ångra, och avsändaren är ett företags rykte.

## 0. Kontext

- **Repo:** `larsbw/autostockholm-mailbot` (GitHub = enda källa till sanning)
- **Brevlåda:** info@autostockholm.se, Google Workspace, domän autostockholm.se
- **Auth:** OAuth desktop client i GCP-projektet `autostockholm-mailbot`, consent
  screen satt till **Internal** (därav ingen Google-verifiering trots restricted
  scopes). Scopes: `gmail.modify`, `gmail.send`. Refresh token i `token.json`,
  klientdata i `client_secret.json`. Båda gitignorerade.
- **Stack:** Python · google-api-python-client · Anthropic API (klassificering och
  generering) · lokal disk för data och loggar. Ingen molndrift, ingen extern databas.
- **Styrdokument:** `docs/roadmap.md` (fasordning, grindar, och definitionen av
  SKUGGLÄGE),
  `docs/kategorier-forslag.md` (maskinproducerad av `src/cluster.py`, skrivs
  aldrig för hand),
  `docs/kategorier.md` (kategoridefinitioner och deras hink) — **planerad, byggs i
  fas 4**, se `docs/roadmap.md`,
  `docs/sparrar.md` (varje spärr, vad den skyddar mot, dess negativkontroll, och om
  den är redundant med någon annan spärr),
  `docs/beslutslogg.md` (sekventiell, append-only),
  `docs/incidentlogg.md` (varje regel med incident bor här),
  `docs/mining-log.md` (varje körning mot brevlådan: datum, query, antal, kvotåtgång)
- **Ramverksregler (obrytbara):**
  1. Inget mail skickas vars kategori inte står i hinken `auto` i `config/kategorier.yaml`.
  2. Ingen kategori flyttas till `auto` av kod. Bara av Lars uttryckliga beslut.
  3. Boten genererar aldrig ett tal. Priser, ledtider och antal läses ur källa eller
     utelämnas (§7.2).
  4. `logg/beslut.jsonl` är append-only.
  Ingen kod får implementera något som bryter dem.

## 1. Think Before Coding

**Anta inte. Dölj inte förvirring. Lyft trade-offs.**

- Ange antaganden explicit. Osäker? Fråga.
- Finns flera tolkningar: presentera dem, välj inte tyst.
- Finns ett enklare sätt: säg det. Push-backa när det är motiverat.
- Något oklart: stanna, namnge vad, fråga.

Gäller särskilt Gmail API:s beteende. Kvoter, scope-täckning och trådsemantik slås
upp i dokumentationen, gissas aldrig fram ur minnet.

## 2. Simplicity First

Minsta kod som löser problemet. Inga spekulativa features, inga abstraktioner för
engångskod, ingen flexibilitet som inte efterfrågats, ingen felhantering för omöjliga
scenarier. Fråga: skulle en senior säga att detta är överkomplicerat? Om ja, förenkla.

## 3. Surgical Changes

Rör bara det du måste. Förbättra inte angränsande kod, refaktorera inte det som inte
är trasigt, matcha befintlig stil. Noterar du orelaterad död kod: nämn den, radera
den inte. Städa orphans som DINA ändringar skapade, inget annat.
Testet: varje ändrad rad ska spåras direkt till uppgiften.

## 4. Goal-Driven Execution

Omvandla uppgifter till verifierbara mål med test först där det går. För
flerstegsuppgifter: kort plan med verify-punkt per steg.

**Mailbot-specifikt:** varje spärr har test för sitt gränsvärdes- och nollfall.
Den tomma tråden, avsändaren utan display-namn, mailet utan brödtext, kategorin med
noll historiska exempel, tröskeln vid exakt gränsvärdet. En spärr som bara testats
mot normalfallet är otestad.

## 5. Ship It

En uppgift är inte klar förrän origin/main bär den. Alltid, utan att fråga:
`git status` → commit (vad + varför) → `git push origin main` → verifiera att
`git rev-parse HEAD` är lika med `git rev-parse origin/main`.

Fråga inte om lov och stanna inte vid "vill du att jag committar?". Enda undantaget
är en uppgift som uttryckligen sagt att den inte ska committas. Att uppgiften inte
nämnde commit är inte ett undantag.

**Sista raden i varje rapport är commit-SHA:n.** Ingen SHA betyder att arbetet aldrig
nådde origin, alltså att det inte är klart. Säg det rakt ut.

**COMMIT_MSG-provenans.** `.git/COMMIT_MSG` är en scratch-fil som lever kvar mellan
committar. Skriv den ALLTID färskt för den aktuella committen med Write (som
trunkerar), och verifiera att kroppen namnger rätt uppgift INNAN push. Ärvd regel,
buren av tradingbot-v2:s incident där en skiva var nära att skeppa under en tidigare
skivas meddelande.

**UNDANTAG — sändning är ALDRIG del av "ship it".**
Push till main: alltid. Att köra `respond.py --send`: aldrig som del av att avsluta
en uppgift, aldrig som default, aldrig för att verifiera att koden fungerar.
Verifiering sker mot `--dry-run` och mot testbrevlådan. Ett mail som skickats för att
bevisa att sändningsfunktionen fungerar är fortfarande ett mail som en kund läser.

## 6. Driftregler (bindande)

- Skriv aldrig ut en hemlighet i upplöst form. Inte client secret, inte refresh token,
  inte API-nyckel. Rapportera existens och längd, aldrig innehåll.
- Rapportera aldrig ett värde du inte läst i verktygsutdata denna session.
- `--send` aktiveras aldrig av kod eller default, bara av Lars explicita val.
- **Persondata.** Kundmail innehåller namn, adresser, registreringsnummer och
  telefonnummer. Dessa förekommer ALDRIG i rapporter, commit-meddelanden, dokument i
  `docs/`, eller i något som pushas. Loggar i `logg/` bär hashade avsändare, inte
  adresser. `data/tradar.jsonl` raderas när `data/par.jsonl` är extraherad.

## 7. Granskningsgrind

Inget byggsteg eller dokumentsteg rapporteras klart förrän en oberoende granskare
returnerat GODKÄND på samtliga framgångskriterier. Flöde: bygg → granskare → åtgärda
→ granskare igen. Max 3 varv. Kvarstår underkännanden: stoppa och rapportera öppet i
stället för att sänka kraven. Granskaren verifierar i egen kontext och kör egna
kommandon. Obligatorisk för: all generativ output, all klassificeringslogik, all
spärrlogik, alla mallar.

**Sändvägen får full §7, ovillkorligt.** Sändvägen är allt som kan ändra **om**,
**till vem**, eller **med vilket innehåll** ett mail lämnar servern. Hit hör spärrarna,
kategorihinkarna, confidence-tröskeln, mottagarupplösning, mallarnas brödtext,
prisinsättning, `--send`-flaggans styrning, och mutationers RÖD/GRÖN-verdikt.
Hit hör också mallarnas ordalydelse, som ser ut som prosa: ett mail som lovar en tid
vi inte kan hålla är en sändvägsdefekt även om koden är felfri.

**Är du osäker på om något är sändvägen, SÅ ÄR DET.**

**Undantag för dokumentdetaljer.** Prosaformuleringar i `docs/`, radnummer, appendix-
och changelog-formuleringar, korsreferensform: EN granskningsomgång, därefter skeppat
med status utskriven, *"självmätt, inte oberoende granskad"*. Undantaget måste åberopas
aktivt, omfattar aldrig sändvägen, och rättfärdigar aldrig att skeppa ett känt falskt
påstående. Noll omgångar är aldrig tillåtet.

**NÄR undantaget ska åberopas, inte bara att det får.** En skiva vars leverabler är
enbart dokument åberopar undantaget som FÖRVAL. Undantaget åberopas per skiva, i
briefen eller i första meddelandet, aldrig per fynd i efterhand. Att åberopa det efter
ett underkännande vore att sänka kraven mitt i grinden, vilket §7 förbjuder.

Bär skivan både dokument och kod gäller förvalet bara dokumentdelen. Koden, och varje
verifiering mot brevlådan, får full §7 som vanligt.

### 7.1 Vakuösa test — ett grönt test som inte kan bli rött

Varje test som påstår sig vakta en spärr prövas i tre steg. Prövningen är en KÖRNING,
aldrig ett resonemang.

> **Steg 1 — notera utgångsdiffen** (`git diff`), så återställningen går att kvittera.
> **Steg 2 — peka ut raden.** Vilken rad fattar beslutet: villkoret, spärren, grenen?
> **Steg 3 — fäll den.** Radera raden, kör sviten, läs utdatan. Blev testet rött?

Blev det inte rött testar det ingenting. Då gäller ett av två: döp om det till vad
det faktiskt bevisar, eller gör det äkta.

**Urvalet är påståendebaserat, aldrig prefixbaserat.** Prövningen gäller varje test
vars påstående är att något INTE sker: mailet skickas inte, tråden hoppas över,
spärren håller, kategorin faller till utkast, tröskeln avvisar. Ett namnmönster fångar
bara de fall någon redan misstänkte, och det är de omärkta som slinker igenom. Steget
ligger i granskningen och inte hos den som skrev testet, eftersom skribenten skrev det
i god tro och trodde att det täckte något.

**Redovisa varje prövning:** vilken rad som fälldes, vad svitens utdata blev, och OM
raden RADERADES eller NEUTRALISERADES. Det sista är inget formkrav. En rad som inte
går att radera utan att sviten slutar köra bär ett annat bevisvärde, och nästa läsare
ska kunna reproducera prövningen utan att gissa vilket som gjordes.

Går raden inte att radera utan att bygget faller så att sviten inte kan köras alls:
neutralisera villkoret i stället, invertera det eller gör det alltid sant. Poängen är
att spärren slutar spärra MEDAN sviten fortfarande kör. Går inte heller det är just
det fyndet: rapportera att prövningen inte kunde genomföras, godkänn inte i stället.

**LAGRAT FÖRSVAR GER FALSKT VAKUÖST, och det är normalfallet här.** Mailbotens spärrar
är redundanta med avsikt. En och samma tråd blockeras typiskt av både *tråden bär
mänskligt svar* och *avsändaren besvarad senaste dygnet*. Fälls bara den ena förblir
testet grönt, och prövningen pekar ut ett äkta spärrtest som vakuöst. Ett grönt utfall
bevisar alltså bara att just den raden inte är ENSAM avgörande. **Fäll samtliga lager
som implementerar spärren innan verdiktet sätts.** Annars är utfallet inkonklusivt,
inte vakuöst. Vilka spärrar som är redundanta med varandra står i `docs/sparrar.md`,
och den listan är obligatorisk läsning före en prövning.

**ÅTERSTÄLLNING — styrs av vad FILEN bär, inte av vad passet heter.**
Fråga inte vilken sorts pass du tror att du kör, utan om filen har ocommittat arbete
i sig just nu:

- **Filen är ocommittat ren.** Fällningen är dess enda skillnad mot HEAD. Då duger
  `git checkout -- <fil>`.
- **Filen bär ocommittat arbete.** Då är `git checkout` FÖRBJUDET. Återställ med
  INVERS REDIGERING: skriv tillbaka exakt den text du tog bort.

Skälet är att `git checkout -- <fil>` inte vet något om din fällning. Den kan en enda
sak, göra filen identisk med indexet, som i ett byggpass normalt är detsamma som HEAD.
Är skillnaden mot den utgångspunkten större än fällningen raderas resten också, tyst
och utan varning.

`scripts/sparr-prova.sh` är säkert i BÅDA lägena och är förstahandsvalet när det går:
det kopierar filen till en temporärfil utanför repot före mutationen och kopierar
tillbaka i en trap, till filens FAKTISKA utgångsläge, aldrig till HEAD.
**Granskaren har inga skrivverktyg och kör alltid `sparr-prova.sh`.**

**Kvittera återställningen, anta den aldrig.** Kör `git diff` igen och jämför mot
utgångsdiffen från steg 1. Den ska vara IDENTISK, inte tom: bär arbetsträdet
ocommittat arbete ska det ligga kvar precis som det gjorde. Skiljer den sig är
återställningen ofullständig, och det är ett stoppläge.

**Granskarens verdikt:** ett spärrtest som inte går att fälla är UNDERKÄND.
Blockerande, och förbrukar ett granskningsvarv som vilket annat underkännande som
helst. Det är inte en anteckning vid sidan av.

### 7.2 Utsmyckande faktapåståenden — bisatsen prövas som huvudsatsen

Ett faktapåstående som inte bär slutsatsen prövas med SAMMA krav som det som gör det.
Gäller bisatser i kodkommentarer, docstrings, commitmeddelanden, rapporter **och i
allt som lämnar servern som mail**: antal, tider, priser, "den enda", "alltid",
jämförelser mellan värden.

**VARJE TAL ÄR AVLÄST ELLER UTELÄMNAT.** Ett tal i löptext, rapport, commitmeddelande
eller utgående mail ska antingen vara direkt avläst ur verktygsutdata eller ur en
committad källa i samma session, eller inte skrivas alls. Det finns ingen tredje
kategori. En exakt siffra som inte kommer ur en körning eller en fil är otillåten, hur
rimlig den än ser ut. Vaga mängdord är tillåtna men befriar inte från kravet.
Vet du inte, skriv inte.

För utgående mail betyder det konkret: priser läses ur `config/priser.json`, ledtider
och öppettider ur `config/fakta.json`. Saknas posten faller mailet till `utkast`,
oavsett kategori och oavsett confidence. Formuleringen "ring för offert" används aldrig,
och ett ungefärligt pris hittas aldrig på för att fylla hålet.

**VID OMSKRIVNING RÄKNAS TALET SOM OLÄST.** Formuleras en mening om, av vilket skäl som
helst och även för att rätta något annat i den, är dess tal OLÄST och ska verifieras på
nytt före leverans. Att det stod där innan och passerade en granskning duger inte: det
som passerade var den gamla formuleringen. **Detta gäller mallarna särskilt**, eftersom
de kommer att formuleras om löpande medan deras siffror ärvs oförändrade genom
omskrivningarna. Kravet utlöses också när talets UNDERLAG ändras i en grannmening.

Skälet är mekaniskt, inte moraliskt. När en mening formuleras om reproduceras dess FORM
ur minnet medan detaljerna fylls i på nytt, och det är i ifyllnaden felen uppstår.
Reflexen att sätta en trovärdig siffra där en siffra hör hemma är starkare än minnet av
vilken siffra som stod där.

**PROCESSRÄKNINGAR SKRIVS INTE.** Räkningar av ett arbetsförlopp, hur många prövningar
eller granskningsvarv eller instanser av ett mönster, går inte att verifiera mot repot
och blir falska vid nästa rättelse. Det kontrollerbara redovisas per post i en lista,
aldrig summerat i en bisats. Tal som går att läsa ur repot eller ur en körning omfattas
inte.

**SJÄLVRAPPORTERING VERIFIERAS MOT KÄLLAN.** Ett påstående om vad passet SJÄLVT har
gjort, vilka filer som ändrats, vilken form en ändring tog, och SHA:n i rapportens sista
rad, verifieras mot diffen före leverans, aldrig ur minnet av avsikten.

**Granskaren namnger, per prövat påstående, den fil och rad eller kommandoutdata som
belägger det.** Ett påstående utan namngiven källa i granskningssvaret räknas som
OPRÖVAT, inte som godkänt. Utan det kravet producerar prövningen ingen artefakt och kan
efterlevas i sken, vilket är precis svagheten som gjorde de vakuösa testen i §7.1
möjliga.

Skälet till regeln i stort är att bisatsen är farligare, inte mindre farlig. Den läses
som bakgrund och granskas därför slappare, men den ärver trovärdighet från en korrekt
omgivning och blir sedan citerad som om den vore belagd. Ett fel i huvudpåståendet syns
när slutsatsen inte går ihop. Ett fel i bisatsen syns aldrig.

## 8. Dokumentägarskap

`docs/` är enda hemvist för projektdokument och underhålls uteslutande av Claude Code
på instruktion från chatten. Varje ändring: kirurgisk, på plats, appendixpost i berört
dokument, commit. En ändring utan appendixpost är en ospårbar ändring.
Dokumenttillstånd är inte verifierad verklighet.

**ÖPPEN PUNKT:** SEO-agents §8 föreskriver att Claude i claude.ai aldrig producerar
dokumentfiler, endast uppdateringsinstruktioner. Detta dokument producerades som fil i
claude.ai. Om konventionen ska bära hit levereras nästa revision som instruktioner.
Frågan är ställd till Lars och obesvarad.

Varje körning mot brevlådan loggas i `docs/mining-log.md` med datum, Gmail-query, antal
träffar och åtgången kvot innan nästa körning startas.

## 9. Bash-disciplin

Gäller ALLA Bash-anrop, huvudloop och varje subagent, granskare inkluderad.

- Kommandoraden ska vara literal: inga expansioner (`$(…)`, backticks, `$VAR`), inga
  inline-loopar, inga heredocs, inga pipes till `grep`/`awk` för verifiering. Behövs
  loop eller expansion: lägg i ett committat skript, anropa literalt.
- **Läsning och sökning:** läs med `Read`. Sök med `Grep`/`Glob` när de står i DIN
  verktygslista. Saknas de är den sanktionerade reserven `grep -n` respektive
  `grep -rn` på en literal enradig bash-rad med citerat mönster: inga pipes, inga
  expansioner. `cat` och `head` ersätter aldrig `Read`. Skälet: `Read` talar om när
  den bara visar en del av en fil, `cat` och `head` tiger. En tyst delvis läsning
  producerar exakt det slags påstående §7.2 finns för att stoppa.
- Terminalkommandon som visas för Lars inleds med `clear && `.
- Commit-meddelanden: enradiga literalt med `git commit -m`. Flerradiga skrivs först
  till `.git/COMMIT_MSG` med Write, sedan `git commit -F .git/COMMIT_MSG`.

**AUTO-LÄGET SÄGER MOTSATSEN, och det är känt.** Med `permissions.defaultMode: "auto"`
injicerar Claude Code en instruktion om att läsa med `cat`/`head`/`sed -n`, söka med
`grep`/`find` och ändra filer med `sed`/heredocs framför de dedikerade verktygen. Den
är produktbeteende och går inte att redigera bort. **§9 går före i det här repot**, för
läsning såväl som redigering.

### 9.1 Blockerad ärlig formulering — stopptecken, inte formuleringsproblem

När en vakt eller klassificerare fäller ett ärligt commit-meddelande: STANNA och
eskalera till Lars. Omformulera ALDRIG innehållet tills det slinker igenom. Historiken
ska bära vad som faktiskt hände.

**Motsvarigheten för sändvägen, och den är den farligaste frestelsen i hela projektet.**
När en spärr fäller ett mail är det ett stopptecken, inte ett formuleringsproblem.
Följande är samma fel i tre former och alla tre är förbjudna utan Lars uttryckliga
beslut:

1. Skriva om mailets text tills spärren släpper igenom det.
2. Sänka confidence-tröskeln så att kategorin passerar.
3. Flytta kategorin till en mildare hink för att komma runt spärren.

Spärren fällde mailet därför att något i det inte gick att verifiera, eller därför att
tråden inte var vad klassificeraren trodde. Ingen av de tre åtgärderna rör den orsaken.
De döljer den, och mailet går ut ändå.

## 10. Mailbot-specifika stopp

Stanna ALLTID och invänta Lars uttryckliga beslut före:

- Första auktoriseringen mot en brevlåda, alltså varje körning som skapar
  `token.json` eller begär nya scopes. Rutinmässig förnyelse av en befintlig
  token är inte ett stopp.
- Första sändningen i en ny miljö, även till en egen testadress
- Att befordra en kategori från `utkast` till `auto`, eller från `aldrig` till `utkast`
- Varje ändring i `config/sparrar.yaml`
- Varje ändring i `config/priser.json` eller `config/fakta.json`
- Sänkning av confidence-tröskeln
- Radering eller migrering av `logg/beslut.jsonl` (append-only)
- En körning som skulle skicka fler än 1 mail (talet är ett öppet antagande, se appendix)
- Att lägga till ett nytt OAuth-scope
- Att ändra avsändaradress eller svarsadress

Vid tvetydig instruktion som rör sändning: fråga vad som faktiskt menas.
Gissningar mot en kunds inkorg är den sortens fel som syns utåt.

## 11. Innehållsregler för genererade mail

Dessa gäller allt som lämnar servern och ingår i sändvägen. Talregeln i §7.2 gäller
parallellt och går före vid konflikt.

- **Mallarna byggs ur `data/par.jsonl`**, alltså ur faktiska svar som Matte och Lars
  redan skickat. De skrivs inte från grunden. Rösten finns redan i utkorgen.
- **Första person plural.** Vi, oss, vår, våra. Aldrig jag, mig, min, eller man.
- **Inga tankstreck eller bindestreck som skiljetecken.** Komma, punkt, kolon, eller
  skriv om meningen.
- **Aldrig "friverkstad".** Alltid "fristående verkstad".
- **Inga konkurrentnamn i brödtext.**
- Varje mall bär en kommentarrad överst som namnger vilka par i `par.jsonl` den vilar
  på, och datum för senaste avläsning av de tal den innehåller.

## 12. Dokumentkonventioner & färskhetskontroll

**Vid sessionsstart, och innan något påstås om nuläget:** kör färskhetskontrollen.
(1) det här dokumentets `Speglar`, (2) högsta numret i `docs/beslutslogg.md`. Är de
överens är nuläget avläst. Är de oense: synka om innan du påstår något. Gissa inte
vilken signal som har rätt.

Numret läses ur `grep -n "^## #" docs/beslutslogg.md`, aldrig ur minnet av vad det
stod på sist. **Bara CLAUDE.md bär en pekare mot ett rörligt nummer.** Övriga styrdokument
namnger i stället vilken paragraf de implementerar, eftersom en pekare med patchnivå
blir gammal av varje rättelse här och tvingar fram innehållslösa versionsposter i varje
dokument som pekar. Se `docs/beslutslogg.md` 0.6.0.

**Varje slutrapport avslutas med en MASKINPRODUCERAD statusrad över kategorierna:**
`.venv/bin/python scripts/kategoristatus.py`. Raden får **aldrig skrivas för hand**.
Den redovisar antal kategorier per hink, antal mail per kategori, och datum för senaste
mining. En handskriven status är sann när den skrivs och falsk i nästa tråd.

**Före fas 4 finns skriptet inte**, och då gäller i stället: skriv ut att statusraden
inte kan produceras och varför. Skriv ALDRIG en handskriven ersättning. Kravet är
uppfyllt av att hålet namnges, inte av att det fylls.

**Rapporten skrivs till en egen fil med tidsstämpel** i den gitignorerade `scratchpad/`:

```
scratchpad/Mailbot-CC-report-YYYYMMDD-HHMM.md
```

Tidsstämpeln tas ur `date -u +%Y%m%d-%H%M` **vid skrivögonblicket**, aldrig för hand.
Filen skrivs SIST, efter grinden. Rapportens första rad är den fullständiga
tidsstämpeln, andra raden HEAD-SHA. **Skrivningen ska VERIFIERAS innan den
rapporteras:** kör `ls -la` på filen och återge sökväg, storlek och tidsstämpel.
**Ett påstående om en skrivning är inte en skrivning.**

**Motsvarande för sändning: ett påstående om ett skickat mail är inte ett skickat mail.**
Efter varje `messages.send`, läs tillbaka det returnerade message-ID:t med `messages.get`
och återge ID och tidsstämpel i rapporten. Går det inte att bekräfta: säg det rakt ut och
behandla mailet som osäkert skickat, aldrig som skickat.

Arkitekturbeslut skrivs i `docs/beslutslogg.md`, append-only, numren återanvänds aldrig.

---

**Reglerna fungerar om:** noll mail skickade till fel mottagare, noll tal i utgående
text som inte går att belägga, noll fall där en spärr kringgåtts genom omskrivning,
noll kategorier befordrade utan Lars beslut, och noll persondata i git-historiken.

---

## Appendix — versionshistorik (nyaste överst)

### 0.5.5 — 2026-08-26

`Speglar` följer med beslutsloggen till #13. Avläst ur
`grep -n "^## #" docs/beslutslogg.md`. Ren synk ⇒ PATCH.

### 0.5.4 — 2026-08-26

`Speglar` följer med beslutsloggen till #11. Avläst ur
`grep -n "^## #" docs/beslutslogg.md`. Ren synk ⇒ PATCH.

### 0.5.3 — 2026-08-26

`Speglar` följer med beslutsloggen till #10. Avläst ur
`grep -n "^## #" docs/beslutslogg.md`. §0:s styrdokumentlista bär nu också
`docs/kategorier-forslag.md`, som är maskinproducerad av `src/cluster.py`.
Ren synk och en listrad ⇒ PATCH.

### 0.5.2 — 2026-08-26

`Speglar` följer med beslutsloggen till #8. Avläst ur
`grep -n "^## #" docs/beslutslogg.md`. Ren synk ⇒ PATCH.

### 0.5.1 — 2026-08-26

`Speglar` följer med beslutsloggen till #7 efter full mining. Avläst ur
`grep -n "^## #" docs/beslutslogg.md`. Ren synk ⇒ PATCH.

### 0.5.0 — 2026-08-26

**§10:s rad om `token.json` får en snävare lydelse.** Den sa tidigare "varje
körning som skriver eller skriver om `token.json`". Bokstavligt träffade den även
en rutinmässig token-förnyelse, som `src/auth.py` gör utan att någon ber om det,
och därmed hade varje framtida körning mot brevlådan varit ett §10-stopp.
Granskaren läste den precis så i skiva 4 och rapporterade ett möjligt passerat
stopp. Så var det inte: `token.json` bar auktoriseringens tidsstämpel och rördes
inte av körningen. Men läsningen var rimlig, och det är regelns fel och inte
läsarens.

Skälet att rätta är inte att den gamla lydelsen var obekväm. **En regel som gör
systemet oanvändbart börjar ignoreras**, och en ignorerad regel skyddar
ingenting. Stoppet ska ligga där risken finns: när en brevlåda auktoriseras för
första gången, eller när scopelistan vidgas. En förnyelse av en token som redan
har Lars godkännande flyttar ingen gräns.

Ändrad regel i §10 ⇒ MINOR.

### 0.4.2 — 2026-08-26

`Speglar` följer med beslutsloggen till #6, som är loggens högsta nummer efter
provkörningens två nya poster. Avläst ur `grep -n "^## #" docs/beslutslogg.md`.
Ren synk av pekaren ⇒ PATCH.

### 0.4.1 — 2026-08-26

Rättelser efter skiva 3:s granskningsomgång, per post:

- **0.4.0-posten namngav fel post för strykningen.** Den skrev "Rättelse i
  0.3.1-posten"; strykningen ligger i 0.3.0-posten. Självrapportering ska
  verifieras mot diffen, inte skrivas ur minnet av avsikten (§7.2).
- **En andra falskhet fanns oredovisad.** 0.3.1-posten sa att 0.3.0-posten "säger
  nu i stället var begreppet SAKNAS, vilket är ett påstående som inte förändras
  av att texten omkring växer". Den meningen blev falsk av strykningen i samma
  commit, och blev det på precis det sätt den påstod var uteslutet. Struken.
- **Ett committat citat hade retroöversatts.** Lars motivering i 0.3.0-posten
  skrevs om från "shadow mode" till "skuggläge" och omformulerades, utöver
  strykningen. Ursprunglig ordalydelse återställd. Undantaget tillåter att en
  falskhet stryks, inte att ett citat moderniseras.
- **Processräkning struken.** 0.4.0-posten skrev att skiva 1 och skiva 2 gick
  "tre granskningsvarv" var. §7.2 namnger `granskningsvarv` ordagrant som
  förbjuden processräkning, och talet går inte att läsa ur repot: rapporterna
  ligger i gitignorerad `scratchpad/`. Ersatt med det som är avläsbart, att
  `config/` och `mallar/` är tomma.
- **`färskhetstriangeln` var upphävd men refererades i presens** på två ställen.
  Båda bär nu en not.
- **§0 och §12 pekade på filer som inte finns.** `docs/kategorier.md` är markerad
  som planerad till fas 4, och §12 säger nu vad som gäller innan
  `scripts/kategoristatus.py` finns: skriv ut att raden inte kan produceras,
  aldrig en handskriven ersättning.

Skivan åberopade §7:s dokumentundantag, alltså en granskningsomgång. Dessa
rättelser är gjorda efter den omgången och är **självmätta, inte oberoende
granskade**. De rör inte sändvägen. Undantaget begränsar antalet omgångar, inte
kravet på sanning: ett känt falskt påstående får inte skeppas oavsett.

### 0.4.0 — 2026-08-26

**§7:s dokumentundantag får en regel om NÄR det ska åberopas.** Undantaget har
funnits sedan `f9b680a` och åberopades aldrig, eftersom ingenting sade när.
Följden var att granskningsgrinden maldes på prosa medan sändvägen förblev
obyggd: `ls -la config` och `ls -la mallar` är tomma, och `src/` bär bara
`auth.py` och `mine.py`. En skiva vars leverabler är enbart dokument åberopar nu
undantaget som förval, och åberopandet sker per skiva i briefen, aldrig per fynd
i efterhand. Det senare vore att sänka kraven mitt i grinden.

**Kaskaden stängs.** Bara det här dokumentet bär en pekare mot ett rörligt nummer.
Övriga styrdokument namnger vilken paragraf de implementerar. §12:s
färskhetskontroll är omskriven därefter: den jämförde tidigare korsreferenser som
nu avsiktligt är borta. Beslut av Lars i skiva 3, som svar på den öppna fråga
`docs/sparrar.md` ställde i sin 0.2.2-post.

**`docs/roadmap.md` upprättas och listas i §0.** Den bär fasordningen, varje fas
grindbeslut, och definitionen av SKUGGLÄGE.

**Två strykningar på plats, båda i redan committade appendixposter.**

`0.3.0`-posten sa att `shadow mode` inte var definierat någonstans i repot. Det
blev falskt av `docs/roadmap.md`, som skapades i samma skiva. `0.3.1`-posten sa i
sin tur att 0.3.0-posten "säger nu i stället var begreppet SAKNAS, vilket är ett
påstående som inte förändras av att texten omkring växer". Det blev falskt av den
första strykningen, och blev det på precis det sätt meningen påstod var uteslutet.

Båda falskheterna är strukna på plats med stöd av undantaget i
`docs/beslutslogg.md`:s huvud, och varje strykning bär en kursiv not där den
stod. **Lars citerade motivering i 0.3.0-posten står kvar ordagrant**, inklusive
den engelska termen: undantaget tillåter att en falskhet stryks, inte att ett
committat citat översätts i efterhand.

Ny regel i §7 ⇒ MINOR.

### 0.3.2 — 2026-08-26

**Processräkningar strukna ur 0.3.0- och 0.3.1-posterna.** Formuleringarna "Fyra
ändringar efter skiva 1" och "Två rättelser" räknade posternas eget innehåll, och
"Regeln som de tre rättelserna gav" räknade instanser av ett mönster. §7.2
förbjuder den formen. Uppräkningarna står kvar, summorna är borta.

Den tyngsta av dem satt i regeln mot självräknande meningar. Den räknade tre
instanser, och en av dem, "Ger tre träffar", har aldrig funnits i något
styrdokument: `git grep -n "tre träffar" 7397e8e` ger exit 1. Frasen stod i en
granskningsrapport och blev aldrig committad, alltså var den aldrig en rättelse.
Regeln bars alltså av ett räkneexempel som själv bröt mot regeln, vilket är den
sortens bisats §7.2 säger blir citerad som belagd. Instanserna redovisas nu per
post, med sin plats.

**Strykningarna är gjorda på plats i redan committade appendixposter.** Det är
tillåtet under det undantag som samtidigt skrivs in i `docs/beslutslogg.md`:s
huvud: ett känt falskt påstående stryks på plats, och strykningen redovisas i en
ny versionspost. Allt annat rättas genom tillägg.

### 0.3.1 — 2026-08-26

Rättelser efter granskningen av 0.3.0, per post nedan.

**`Speglar` sätts till #4**, alltså till loggens högsta nummer efter den här
skivans rättelser. 0.3.0 lämnade huvudet på #2 medan loggen växte, vilket är
samma osynk som 0.3.0 infördes för att stänga. **Pekaren ska kontrolleras mot
`grep -n "^## #" docs/beslutslogg.md` i varje pass som rör beslutsloggen**, inte
skrivas ur minnet av vad den stod på sist.

**Kvantifieringen om `shadow mode` stryks ur 0.3.0-posten.** Den sa att en
`grep`-sökning bara träffar en mening. Sökningen träffar hela stycket, och blev
falsk av den omskrivning som skulle rätta ett närliggande fel.

*Rättelse i 0.4.0: här stod att 0.3.0-posten i stället säger var begreppet
saknas, och att det är ett påstående som inte förändras av att texten omkring
växer. Båda leden är struket. Meningen det syftade på är själv struken ur
0.3.0-posten, och den blev falsk av precis det den påstods vara oberoende av.*

**Om formen.** 0.3.0:s appendixpost redigerades på plats i `b03139d`, efter att
den committats. Det bryter mot beslutsloggens räckviddsregel, som infördes i
samma commit. Den här posten är rättelsen: härefter rättas en committad
appendixpost genom en ny versionspost, inte genom omskrivning.

**Regeln som rättelserna gav.** Skriv aldrig en mening som räknar eller
kategoriserar sin egen omgivning. Den blir falsk när texten omkring växer, och
den växer oftast av just den commit som skriver meningen. Namnge fil och rad i
stället. Belagda instanser, var och en med sin plats:

- `shadow mode`-meningen i 0.3.0-posten, som sa att en `grep`-sökning bara
  träffar en mening.
- `docs/beslutslogg.md` #3, vars anvisning bad läsaren skilja på tre sorters
  träff varav den första inte finns i utdatan. Upphävd av #4.

### 0.3.0 — 2026-08-26

Ändringar efter skiva 1, per post nedan. Beslutsloggen finns nu.

**Versionshuvudets `Speglar` sätts till #2, och stycket som föreskrev #1 raderas
helt.** Talet #1 skrevs innan någon visste hur många beslut den första skivan
skulle producera. Rätt värde är #2. Stycket ersätts inte, eftersom ett dokument
inte ska bära en instruktion om vilket tal det självt ska få: det är ett ogrundat
tal i en bisats, alltså precis det §7.2 finns för att stoppa. Att `Speglar`
uppdateras när loggen växer följer av §12 och behöver ingen egen föreskrift.
*(Namnet färskhetstriangeln, som stod här, är upphävt i 0.4.0: kontrollen har två
signaler.)*

**§10 får en ny första rad om auktorisering.** Beslutslogg #2 behandlar
auktoriseringen som den grind som öppnar miljön, medan §10 bara namngav första
sändningen. Hålet blottades av #2 utan att något påstående i §10 blev falskt: det
som saknades var en rad, inte en rättelse. Raden namnger `token.json` uttryckligen,
eftersom det är skrivningen till den filen som är den observerbara händelsen.

**§10:s gräns per körning sänks från 5 till 1.** Femman hade inget underlag och
läses som en kalibrerad tröskel, vilket den aldrig var. Ettan är golvet och är
därför inget påstående om volym. Talet revideras när mining visat den faktiska
dagsvolymen. Raden behåller sin pekare hit.

Lars motiverade sänkningen med att ingenting skickas under shadow mode och att
första skarpa sändningen är manuell. Sänkningen vilar inte på begreppet, utan på
att 1 är golvet, så motiveringen håller även om shadow mode aldrig införs.

*Rättelse i 0.4.0: här stod att begreppet inte var definierat någonstans i repot.
Det påståendet blev falskt av `docs/roadmap.md` och är struket. Lars motivering
ovan står kvar i sin ursprungliga ordalydelse, inklusive den engelska termen, för
att den är ett citat. Begreppet heter SKUGGLÄGE i repot och definieras i
`docs/roadmap.md`.*

**§0:s styrdokumentlista räknade upp `docs/incidentlogg.md` medan filen inte
fanns.** Filen är nu upprättad och bär sin första post, I1, om defaultvärden som
binds när modulen laddas. Listraden är oförändrad. Uppmätt i skiva 1, inte
hypotetisk.

Ny regel i §10 och raderat innehåll i huvudet ⇒ MINOR.

### 0.2.0 — 2026-08-26

Avstämd mot SEO-agents CLAUDE.md, som 0.1.0 inte hade tillgång till. Fyra regler som
tradingbot-v2 1.5.0 komprimerat bort återinförs, och tre av dem väger tyngre här än i
förlagorna.

**§7.2 tillkommer i sin helhet.** Talregeln, omskrivningsregeln, processräkningsförbudet
och kravet att granskaren namnger källa per påstående. 0.1.0 hade bara prisregeln, alltså
ett specialfall av talregeln, och saknade den generella formen. Omskrivningsregeln är den
viktigaste delen här: mallarna kommer formuleras om löpande medan deras siffror ärvs
oförändrade genom omskrivningarna, vilket är exakt det fall regeln finns för.

**§9.1 tillkommer, utvidgad till sändvägen.** Förlagan gäller ett blockerat
commit-meddelande. Utvidgningen till tre namngivna förbjudna åtgärder vid fälld sändning
saknar motsvarighet i förlagorna och tillkommer därför att frestelsen är specifik för det
här systemet: en spärr som fäller ett mail har en orsak, och alla tre kringgåendena lämnar
orsaken orörd.

**§7.1:s återställningsdisciplin tillkommer.** Skillnaden mellan ren fil och fil med
ocommittat arbete, förbudet mot `git checkout` i det andra fallet, och kravet att
kvittera mot utgångsdiffen som ska vara identisk och inte tom.

**Klausulen om lagrat försvar tillkommer, och är omskriven till att beskriva
normalfallet.** I förlagan är den ett kantfall med en uppmätt instans. Här är
redundanta spärrar designen, så klausulen bär en pekare till `docs/sparrar.md` och
gör den listan obligatorisk läsning före en prövning. Det tillägget saknar motsvarighet
i förlagan.

**§8 bär en namngiven öppen punkt** om huruvida SEO-agents förbud mot att claude.ai
producerar dokumentfiler ska bära hit. Punkten skrivs ut i stället för att avgöras, och
dokumentet du läser är självt en instans av frågan.

**§10:s gräns på 5 mail per körning är fortfarande satt utan underlag** och ska revideras
när mining-fasen visat den faktiska dagsvolymen. Namngivet öppet antagande, inte ett mätt
värde. Raden bär nu en explicit pekare hit så att talet inte läses som ett beslut.

**Inga incidenter bärs ännu.** Förlagornas styrka är att varje härdad regel namnger den
incident som skapade den. Detta dokument har inga egna. De ärvda incidenterna hör hemma i
respektive förlagas historik och återges inte här. `docs/incidentlogg.md` börjar tom.

Nya regler tillkom ⇒ MINOR. Inget befintligt innehåll omorganiserat utöver att §7 fått
underrubriker och att den tidigare §11 numrerats om till §12 för att ge plats åt
innehållsreglerna.

### 0.1.0 — 2026-08-26

Baseline, byggd enbart på tradingbot-v2 1.5.0. Kapitalvägen definieras om till
sändvägen, §5:s deploy-undantag mappas till sändning, och innehållsreglerna för
genererade mail tillkommer som ny sektion utan förlaga.
