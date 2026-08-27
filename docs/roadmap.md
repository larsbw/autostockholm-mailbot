# Roadmap

**Version:** 0.3.0 · **Uppdaterad:** 2026-08-27 · **Implementerar** CLAUDE.md §10

Fasordning och grindar. En fas lämnas inte därför att arbetet i den är gjort, utan
därför att **Lars fattat fasens grindbeslut**. Grinden står i varje fas och är det
enda som flyttar projektet framåt.

Faserna är sekventiella. Det finns ingen fas som får hoppas över, och ingen kod
får implementera en genväg förbi en grind (CLAUDE.md §0, ramverksreglerna).

---

## SKUGGLÄGE

**Definition.** I skuggläge kör `respond.py` klassificering och generering FULLT
UT, loggar varje beslut till `logg/beslut.jsonl`, och **skickar ingenting**.

Skuggläget finns för att skilja två frågor som annars blandas ihop: om boten
väljer rätt, och om boten skickar rätt. I skuggläge besvaras bara den första, och
den besvaras mot verkliga inkommande mail i stället för mot en testmängd.

Vad skuggläget innebär konkret:

- Varje inkommande mail klassificeras, och kategorin loggas med confidence.
- Svaret genereras i sin helhet, inklusive prisinsättning och mallval, och loggas.
- Spärrarna körs och deras utfall loggas, RÖD eller GRÖN, med skäl.
- `messages.send` anropas ALDRIG. Inte till kunden, inte till en testadress, inte
  för att verifiera att sändningsfunktionen fungerar.
- Loggen är append-only och lyder under §6: hashade avsändare, inga adresser.

**Termen är svensk i repot.** Den engelska formen `shadow mode` ska inte
användas: den saknade definition ända till det här dokumentet och blev därför ett
obelagt begrepp i en motivering (CLAUDE.md:s appendixpost 0.3.0). Ett begrepp som styr sändvägen
ska ha exakt en form och exakt en definition, och den står här.

**Skuggläget är inte en flagga som kan glömmas bort.** Det upphör bara genom
grindbeslutet i fas 6, och `--send` aktiveras aldrig av kod eller default
(CLAUDE.md §6).

---

## Faser

### Fas 0 — Google · KLAR

GCP-projekt, OAuth desktop client, consent screen satt till Internal, scopes
`gmail.modify` och `gmail.send`.

**Grind:** passerad.

### Fas 1 — Repo · KLAR

Repo, `.gitignore`, CLAUDE.md, styrdokument, `.venv`, testsvit,
`scripts/sparr-prova.sh`.

**Grind:** passerad.

### Fas 2 — Auth

`src/auth.py` är byggd och testad mot fejkade credentials. Vad som återstår är
KÖRNINGEN: ingen `token.json` finns, och ingen auktorisering har skett.

**Grind:** Lars kör `.venv/bin/python -m src.auth --auktorisera` själv. Detta är
ett §10-stopp och görs aldrig av agenten. Fasen är passerad när `token.json`
finns och `src/auth.py` returnerar giltiga credentials utan att öppna webbläsare.

### Fas 3 — Mining

`src/mine.py` är byggd, kvotdimensionerad och testad mot fejkad Gmail-respons.
Återstår: provkörning med `--max-threads`, därefter full mining, därefter
extraktion av `data/par.jsonl` ur `data/tradar.jsonl`.

**Grind:** Lars godkänner att full mining körs, efter att en provkörning
redovisat trådstruktur och faktisk kvotåtgång. `data/tradar.jsonl` raderas när
`data/par.jsonl` är extraherad (§6).

### Fas 4 — Kategorier

`docs/kategorier.md` och `config/kategorier.yaml` upprättas ur `data/par.jsonl`.
Varje kategori får en hink: `auto`, `utkast` eller `aldrig`.
`scripts/kategoristatus.py` byggs, så att §12:s maskinproducerade statusrad går
att köra.

**Grind:** Lars beslutar kategorilistan och varje kategoris STARTHINK. Ingen
kategori startar i `auto`. Kod flyttar aldrig en kategori mellan hinkar
(§0, ramverksregel 2).

### Fas 4.5 — Fordonsuppslag

Beslutad av Lars i skiva 11. Ligger mellan kategorierna och mallarna, och
ordningen är inte godtycklig: **a-traktormallarnas INNEHÅLL beror på vad
uppslaget visar**, så mallarna kan inte skrivas först. A-traktor är materialets
största ärendetyp, se `docs/kategorier-forslag.md`.

**Syfte.** En a-traktorförfrågan besvaras inte ur mall enbart. Kundens
registreringsnummer slås upp, och svaret formas av vad uppslaget visar.

**REGELUTVÄRDERINGEN ÄR DETERMINISTISK KOD, INTE EN MODELL.** Beslut av Lars.
Kraven nedan är boolesk logik på uppslagets fält. **En modell avgör aldrig om ett
fordon uppfyller en föreskrift.** Modellen får formulera svaret; den får inte
fatta beslutet om vad som gäller.

#### Krav som beror på ursprungsbilen

Återgivna ur **VVFS 2003:19 4 kap** som Lars formulerat dem i skiva 11.

| Krav | Innebörd |
| --- | --- |
| §39 barlastflak | Krävs om tjänstevikten är högst 2000 kg OCH mindre än 60 procent av tjänstevikten vilar på drivhjulen. Fyrhjulsdrivna fordon och fordon över 2000 kg tjänstevikt omfattas inte. |
| §42 kopplingsanordning | Dragkrok krävs, och fordonet ska i övrigt vara lämpligt som dragfordon. |
| Ursprungsfordonet | Ska vara en serietillverkad täckt bil. |

**FÖRFATTNINGSTEXTEN ÄR INTE UPPSLAGEN I REPOT, och det ska stå här.** Tabellens
paragrafnummer, viktgränsen och procentsatsen är återgivna ur Lars instruktion
och inte avlästa ur VVFS 2003:19. §7.2 kräver att ett tal är avläst eller
utelämnat, och den här raden är hur kravet uppfylls tills texten slagits upp.
**Författningstexten ska verifieras mot källan innan regelutvärderingen byggs.**

Talen i §39-raden styr efter Lars beslut i skiva 11 INTE scenarioutfallet: varken
tjänstevikt eller drivning påverkar GRÖNT, och barlastflak nämns bara som villkor
i GULT vid bakhjulsdrift. Kravet på verifiering står kvar ändå. Raden beskriver en
föreskrift som mallarna kommer att formulera sig om, och en mall som återger ett
författningskrav fel är en sändvägsdefekt även när den inte styr någon gren.

#### SEXTIOPROCENTSREGELN GÅR INTE ATT AVGÖRA UR REGISTRET

Registret bär **garanterade axeltryck**, alltså maxvärden, inte den faktiska
fördelningen av tjänstevikten. Den fördelningen mäts på våg.

Framhjulsdrift är en **stark indikation men inte en mätning**. §7.2 gäller:
**boten påstår aldrig att en viss bil klarar sig utan barlastflak.**

**FÖLJDEN, beslutad av Lars i skiva 11: barlastflak kan varken bekräftas eller
uteslutas i något scenario, och nämns därför inte i GRÖNT.** Frågan avgörs av
registreringsbesiktningen. Där bakhjulsdrift gör barlastflak troligt namnges det
som ett villkor i GULT, vilket är scenario 4. **Varken tjänstevikt eller drivning
påverkar GRÖNT.**

#### Fem scenarier

Alla fem får en mall i fas 5.

| # | Scenario | Vad svaret gör |
| --- | --- | --- |
| 1 | **SAKNAR REGNR** | Ber om registreringsnumret. Alltid korrekt, kan aldrig lova fel, flyttar samtalet framåt. |
| 2 | **UPPSLAG MISSLYCKADES** | Ber om bekräftelse på numret. |
| 3 | **GRÖNT** | Inget känt hinder: täckt bil, ej redan traktorregistrerad, inget körförbud, dragkrok registrerad. Redovisar vad som slagits upp, och att det slutgiltiga avgörs vid registreringsbesiktningen. |
| 4 | **GULT** | Byggbart med villkor som påverkar pris och tid: bakhjulsdrift och därmed troligt barlastflak, dragkrok saknas, automatlåda. Svaret NAMNGER villkoret. |
| 5 | **RÖTT** | Känt hinder: redan traktorregistrerad, ej täckt bil, körförbud. Svaret NAMNGER hindret. |

**GRÖNT PRÖVAR BARA REGISTERFAKTA SOM GÅR ATT LÄSA AV, och det är ett beslut av
Lars i skiva 11.** Täckt bil, ej redan traktorregistrerad, inget körförbud,
dragkrok registrerad. Varje led är något uppslaget svarar på direkt.

Tjänstevikt och drivning står medvetet INTE i GRÖNT. Skiva 11:s brief formulerade
kriteriet som "under 2000 kg, framhjulsdriven", och det ledet var omvänt: §39
gäller fordon vars tjänstevikt är HÖGST 2000 kg, så en låg vikt drar in bilen
under barlastflakskravet i stället för att fria den. Ett fordon ÖVER 2000 kg
omfattas inte av §39 alls. Eftersom sextioprocentsregeln ändå aldrig går att
avgöra ur registret hör barlastflak varken hemma som friande kriterium i GRÖNT
eller som hinder i RÖTT.

**HINKTILLDELNINGEN INGÅR INTE I FASEN.** Vilka scenarier som får autosvaras är
Lars beslut enligt §10, och det fattas efter utkastvyn i fas 5.5. Ramverksregel 2
i CLAUDE.md §0 gäller oförändrat: ingen kategori flyttas till `auto` av kod.

#### Var registreringsnumret redan finns

Scenario 1 utlöses bara när numret saknas, så vilken inflödeskanal som bär det
strukturerat avgör hur ofta scenariot inträffar.

**PREDIKATET, utskrivet så att talen går att räkna om.** En tråd räknas som träff
om någon av dess meddelandekroppar bär `regnr`, `reg.nr`, `reg nr`,
`registreringsnr` eller `registreringsnummer`, skiftlägesokänsligt, följt av
valfritt blanktecken och sedan kolon eller likhetstecken. Den formen kallas
nedan ETIKETTFORM. En tråd räknas som förmedlartråd om något av huvudena `From`,
`Reply-To`, `Return-Path` eller `Sender` i något av dess meddelanden innehåller
en av de fem domänerna. Kroppen avkodas med `src/urval.py::brodtext`.

**TALEN NEDAN GÅR ATT RÄKNA OM.** Kör `.venv/bin/python scripts/regnr-matning.py`.
Skriptet är committat på Lars beslut i skiva 11, mäter samma predikat i tre
lager, och lånar avkodningen ur `src/urval.py` i stället för att kopiera den.
Skulle en framtida körning ge andra tal än tabellerna här är det tabellerna som
är föråldrade, inte skriptet.

**MÄTNINGEN MÅSTE GÖRAS MOT AVKODAD BRÖDTEXT, och skälet är INTE att filraden
saknar text.** Filraden bär huvudena och fältet `snippet` i klartext, men
`snippet` är en avkortad ingress: längsta uppmätta är 201 tecken. Själva texten
ligger base64url-kodad i `body.data` på den MIME-del som bär den, alltså i en av
`payload.parts` när sådana finns och direkt i `payload.body.data` när de saknas.
`src/urval.py::_platta` plattar delträdet just därför. En `grep` mot filraden ser
alltså i praktiken bara de första dryga 200 tecknen av varje meddelande, och ett
fält som ligger längre ned är osynligt för den hur vanligt det än är.

Uppmätt i skiva 11, etikettform, samma predikat i varje kolumn:

| Population | Rå filrad | Enbart `snippet` | Avkodad kropp |
| --- | --- | --- | --- |
| `data/tradar.jsonl`, alla 555 | 78 | 78 | 79 |
| `data/tradar_obesvarade.jsonl`, alla 1604 | 0 | 0 | 340 |
| förmedlartrådar bland obesvarade, 411 | 0 | 0 | 40 |

De två första kolumnerna är identiska: **allt en rå `grep` hittade låg i
`snippet`.** I de besvarade trådarna står fältet tidigt och `grep` såg 78 av 79.
I de obesvarade står det bortom ingressen och `grep` såg noll av 340. En
nolltäckning från `grep` mot dessa filer är därför INKONKLUSIV och aldrig ett
negativt fynd. Se `docs/incidentlogg.md` I5.

**`X-Msg-EID` DUGER INTE SOM KÄNNETECKEN FÖR FÄLTET, och det är mätt åt båda
hållen.**

| Fil | Trådar | Bär fältet | Bär `X-Msg-EID` | Bär båda |
| --- | --- | --- | --- | --- |
| `data/tradar.jsonl` (besvarade) | 555 | 79 | 181 | 78 |
| `data/tradar_obesvarade.jsonl` | 1604 | 340 | 2 | 0 |

Huvudet är inte TILLRÄCKLIGT: i de besvarade bärs det av 181 trådar medan fältet
bärs av 79. Huvudet är inte heller NÖDVÄNDIGT: i de obesvarade bär 340 trådar
fältet medan 2 bär huvudet. Att kopplingen är stark i den ena filen, 78 av 79
besvarade fälttrådar bär också huvudet, ändrar inget: den kopplingen finns inte
alls i den andra filen, som är den större. Att webbformulärets notis BÄR
`X-Msg-EID` står i beslutslogg #12 och i `docs/sparrar.md` under
`klassning-maskinmail`, men ingen av dem säger att huvudet är unikt för
formuläret. **Avläsaren i fas 4.5 ska leta efter FÄLTET, aldrig efter huvudet
och aldrig efter avsändaren.**

**BRIEFENS PÅSTÅENDE STÅR SIG FÖR EN DOMÄN, INTE FÖR FÖRMEDLARNA SOM GRUPP.**
Briefen sade att notiserna från de fem domänerna bär registreringsnummer i ett
strukturerat fält. Fördelningen bland de 411 obesvarade förmedlartrådarna:

| Domän | Trådar | Bär fältet |
| --- | --- | --- |
| `bokadirekt.se` | 79 | 36 |
| `autobutler.se` | 287 | 4 |
| `hittabilverkstad.nu` | 26 | 0 |
| `verkstadsoffert.se` | 18 | 0 |
| `verkstadsdeal.se` | 1 | 0 |
| **Summa** | **411** | **40** |

**Bara `bokadirekt.se` bär fältet i någon meningsfull omfattning**, 36 av 79.
`autobutler.se` är materialets största förmedlare med 287 trådar och bär det i 4
av dem. De tre övriga bär det inte alls. Räknat över gruppen bär 40 av 411
trådar fältet, alltså färre än var tionde. **Att anta att en förmedlad
förfrågan bär numret vore alltså fel i nio fall av tio**, och det är just det
antagandet briefens formulering inbjuder till.

**Vad som INTE går att belägga.** Briefen angav klustringens exempelutdata från
skiva 6 som källa. Den utdatan finns inte kvar att pröva: `src/cluster.py`,
`src/kategorisera.py` och `src/ometikettera.py` skriver alla tre till samma
sökväg, `scratchpad/kategorier-exempel.md`, och `scratchpad/` är gitignorerad.
Att just skiva 6:s fil skrivits över är inte belagt, bara att ingen skiva 6-utdata
ligger kvar på sökvägen.

**Följden för fasen.** Fas 4.5 bygger en fältavläsare, och den villkoras på
FÄLTET och aldrig på avsändaren: finns etikettformen i tråden används numret,
saknas den går ärendet till scenario 1. Det är samma regel för alla inflöden och
kräver ingen domänlista. Att i stället lita på avsändaren hade gett fel svar för
`autobutler.se`, där 283 av 287 trådar saknar fältet.

Avläsaren ändrar däremot ingenting i vad som får PÅSTÅS. Ett avläst
registreringsnummer är en INDATA till uppslaget, aldrig ett faktum om bilen.

**SPÄRREN SOM SKA VAKTA DET FINNS INTE ÄNNU.** `docs/sparrar.md` bär posten
`fordonsfakta-ur-uppslag`, som ska hindra att ett svar namnger fordonsfakta utan
lyckat uppslag, men posten är märkt **PLANERAD** och spärren byggs i fas 5.
Fram till dess finns regeln men inget som verkställer den, och den skillnaden ska
inte läsas bort: en registrerad post är inte ett skydd. Det som skyddar i fas 4.5
är att fasen inte får lämnas, och att ingen mall skrivs, innan grinden är
passerad.

**Grind:** Lars beslut om **datakälla och avtal**, se beslutslogg #23. Fasen
lämnas inte av att koden fungerar mot en testnyckel.

### Fas 5 — Mallar och spärrar

Mallarna byggs ur `data/par.jsonl`, alltså ur faktiska svar (§11).
`config/sparrar.yaml` och spärrlogiken byggs, och varje spärr registreras i
`docs/sparrar.md` med sin negativkontroll och sin redundans.
`config/priser.json` och `config/fakta.json` upprättas.

**Grind:** Lars godkänner varje mall ORDAGRANT, och varje ändring i
`config/sparrar.yaml`, `config/priser.json` och `config/fakta.json` är ett
§10-stopp. Hela fasen är sändväg och får full §7, ovillkorligt.

### Fas 5.5 — Utkastvyn

Webbvyn där Lars och Matte läser botens förslag och fäller omdöme om dem.
Beslutad av Lars i skiva 10. Hostas på `mailagent.dasher.se` enligt
beslutslogg #20, med inloggning enligt #21 och #22.

**BYGGS FÖRE SKUGGLÄGET, och det är hela skälet till att fasen finns.** Skuggläge
utan vy producerar en loggfil ingen läser. Fas 6 mäter klassificeringens
träffsäkerhet och spärrarnas utfall, och den mätningen kräver att någon faktiskt
går igenom förslagen post för post. Utan vyn blir `logg/beslut.jsonl` en fil som
växer medan grinden till fas 7 aldrig får sitt underlag.

**Fyra omdömen**, loggade åtskilt till `logg/omdomen.jsonl`, append-only:

| Omdöme | Betyder |
| --- | --- |
| `godkann` | Förslaget dugde som det stod. |
| `forbattra` | Förslaget dugde inte, och den redigerade texten är det som skulle skickats. |
| `forkasta` | Förslaget dugde inte, och ingen text ersätter det. |
| `neka` | Kategorin ska inte besvaras av boten alls. |

De fyra loggas ÅTSKILT och slås aldrig ihop till godkänt eller icke godkänt.
`forkasta` och `neka` ser lika ut i en tvågradig skala och betyder helt olika
saker: det första är ett dåligt svar på ett riktigt ärende, det andra är att
ärendet inte hör hemma hos boten.

**`forbattra` bär den redigerade texten och skriver ett nytt par till
`data/par.jsonl`.** Det är den enda av de fyra som tränar rösten. De andra tre
säger vad som var fel; bara den här säger vad som skulle stått i stället, och
§11 kräver att mallarna vilar på faktiska svar och inte på text skriven från
grunden.

**SPÄRRFÄLLDA FÖRSLAG VISAS UTAN TEXTFÄLT.** Vyn visar vilken spärr som fällde
och varför. Ingen redigeringsruta, ingen skicka-knapp, ingen väg vidare från den
posten.

Skälet är §9.1. Den förbjuder att ett fällt mails text skrivs om tills spärren
släpper igenom det, och en redigeringsruta bredvid ett fällt förslag gör det
förbudet till ett klick. Spärren fällde mailet därför att något i det inte gick
att verifiera, eller därför att tråden inte var vad klassificeraren trodde, och
ingen omskrivning rör den orsaken.

**Detta är sändväg och får full §7, ovillkorligt.** Vyn avgör vad en människa
ser och kan göra med ett förslag, och därmed om och med vilket innehåll ett mail
senare lämnar servern.

**VYN SKICKAR ALDRIG MAIL. Den skriver omdömen.** Sändning sker först i fas 7,
genom `respond.py`, och styrs av `--send` enligt §6 och §10. I fas 6 anropas
`messages.send` ALDRIG, enligt skugglägets definition överst i det här
dokumentet. Att lägga en skicka-knapp i vyn vore att flytta sändvägen till ett
gränssnitt utan de stopp §10 föreskriver.

**Grind:** Lars beslutar att omdömesvolymen räcker. Talet sätts inte i förväg,
eftersom det beror på hur många kategorier som visar sig bära underlag, och
skiva 9 mätte att bara två kategorier når tio par med svar.

### Fas 6 — Skuggläge

`respond.py` körs i skuggläge enligt definitionen överst. Beslutsloggen samlas
och läses. Klassificeringens träffsäkerhet mäts mot verkliga mail, och spärrarnas
utfall granskas post för post.

**Grind:** Lars beslutar att skuggläget upphör, efter att ha läst
`logg/beslut.jsonl` och funnit klassificeringen och spärrutfallen godtagbara.
Beslutet fattas per kategori, inte för boten som helhet.

### Fas 7 — Auto

Kategorier befordras från `utkast` till `auto`, en i taget. Första skarpa
sändningen är manuell.

**Grind:** varje befordran till `auto` är ett eget §10-stopp och ett eget
uttryckligt beslut av Lars. En körning som skulle skicka fler än 1 mail är också
ett §10-stopp, och det talet är ett öppet antagande som revideras när mining
visat dagsvolymen.

---

## Appendix — versionshistorik (nyaste överst)

### 0.3.0 — 2026-08-27

**Fas 4.5 FORDONSUPPSLAG tillkommer**, mellan kategorierna och mallarna, på
beslut av Lars i skiva 11.

Fasen ligger FÖRE mallarna därför att a-traktormallarnas innehåll beror på vad
uppslaget visar. Regelutvärderingen är deterministisk kod och aldrig en modell:
en modell avgör inte om ett fordon uppfyller en föreskrift. Fem scenarier får
var sin mall i fas 5, och hinktilldelningen ingår inte i fasen.

**Sextioprocentsregeln i §39 går inte att avgöra ur registret**, eftersom
registret bär garanterade axeltryck och inte den faktiska viktfördelningen.
Framhjulsdrift är en indikation och inte en mätning, så boten påstår aldrig att
en viss bil klarar sig utan barlastflak.

**BARLASTFLAK NÄMNS INTE I GRÖNT, och GRÖNT prövar bara avläsbara registerfakta.**
Beslut av Lars efter tredje granskningsvarvet. GRÖNT är täckt bil, ej redan
traktorregistrerad, inget körförbud, dragkrok registrerad. Varken tjänstevikt
eller drivning påverkar det.

Skälet är sakligt och inte formellt. Briefen formulerade GRÖNT med "under 2000
kg, framhjulsdriven", och viktledet var omvänt: §39 gäller fordon vars tjänstevikt
är HÖGST 2000 kg, så en låg vikt drar in bilen under barlastflakskravet i stället
för att fria den. Eftersom sextioprocentsregeln dessutom aldrig går att avgöra ur
registret kan barlastflak varken bekräftas eller uteslutas, och det hör därför
hemma som villkor i GULT vid bakhjulsdrift och i övrigt hos
registreringsbesiktningen.

**Författningstalen är återgivna, inte avlästa, och fasen säger det själv.**
Paragrafnumren, viktgränsen och procentsatsen kommer ur Lars instruktion.
VVFS 2003:19 är inte uppslagen i repot. §7.2 tillåter inte ett tal som varken är
avläst eller utelämnat, och kravet uppfylls här genom att källan och dess gräns
namnges i fasen.

Talen styr efter beslutet ovan inte längre någon scenariogren. Kravet på
verifiering mot författningen står ändå kvar, eftersom mallarna i fas 5 kommer
att formulera sig om föreskriften och en mall som återger ett författningskrav
fel är en sändvägsdefekt även när den inte styr en gren.

**FÖRMEDLARNAS NOTISER BÄR FÄLTET I 40 AV 411 TRÅDAR, och fördelningen är ojämn.**
Uppmätt i skiva 11 mot avkodad brödtext: `bokadirekt.se` 36 av 79,
`autobutler.se` 4 av 287, och `hittabilverkstad.nu`, `verkstadsoffert.se` och
`verkstadsdeal.se` noll.

Fasen skriver ut fördelningen per domän utöver summan, eftersom summan ensam
döljer att materialets största förmedlare knappt bär fältet alls. Briefen till
skiva 11 sade att notiserna från de fem domänerna bär registreringsnummer i ett
strukturerat fält; **mätningen bär det påståendet för `bokadirekt.se` och inte
för gruppen**, och fasen är skriven efter mätningen och inte efter briefen.

**UTKASTEN FÖRE DET HÄR FÄLLDES AV §7-GRANSKNINGEN, och felen låg i mätningen.**
De redovisas per fel, inte summerat.

- **Mätning mot filraden.** Ett utkast mätte med `grep` mot filraden, fick noll
  och skrev att briefen var motbevisad.
- **Kontrollmätning på fel population.** Base64-invändningen restes i samma
  utkast och avfärdades med en räkning över HELA filen i stället för över den
  delmängd invändningen gällde.
- **Fel mekanism.** Ett senare utkast förklarade nollan med att filraden är
  base64 och att `grep` "per konstruktion" inte kan se ett ord. Det är falskt:
  filraden bär `snippet` i klartext och rå `grep` fann 78 av 79 fält i
  `data/tradar.jsonl` just den vägen. Orsaken är att `snippet` är avkortad,
  längst uppmätt 201 tecken.
- **Talpar utan gemensam grund.** Samma utkast jämförde 3 mot 40 som om talen
  gällde samma sak. 3 var ordträffar över hela filen utan etikettkrav, 40 var
  etikettform över förmedlarsubsetet. Fasen bär nu en tabell med samma predikat
  i varje kolumn.

Felen är samma felklass i olika skepnad: ett tal avläst för en annan population
än den meningen beskriver. Se `docs/incidentlogg.md` I5.

**`X-Msg-EID` duger inte som kännetecken för fältet, åt något håll.** Huvudet är
inte tillräckligt, 181 besvarade trådar bär det mot fältets 79, och inte
nödvändigt, 340 obesvarade trådar bär fältet mot huvudets 2. Beslutslogg #12
säger att webbformulärets notis BÄR huvudet, inte att huvudet är unikt för
formuläret. Fasen säger nu att avläsaren ska leta efter FÄLTET, och den regeln
villkorar inte heller på avsändaren, eftersom `autobutler.se` saknar fältet i 283
av 287 trådar.

**MÄTNINGEN ÄR REPRODUCERBAR: `scripts/regnr-matning.py` är committat.** Beslut
av Lars. Fasens tal går att räkna om med ett kommando i stället för att härledas
ur prosa, och skriptet lånar avkodningen ur `src/urval.py` i stället för att
kopiera den. Skivans brief sade INGEN KOD, men det syftade på botens kod och inte
på ett mätverktyg som bär fasens centrala påstående.

**SPÄRRPOSTENS PLANERAD-STATUS SYNS NU I ROADMAPEN.** Fasens stycke om vad som
får påstås skrev tidigare i presens att `fordonsfakta-ur-uppslag` fäller varje
obelagt fordonsfaktum, medan `docs/sparrar.md` märker posten PLANERAD. En läsare
kunde tro att skyddet fanns. Stycket säger nu att regeln finns men inte något som
verkställer den, och att en registrerad post inte är ett skydd.

**VÄGEN TILL GRÖNT-LYDELSEN, redovisad därför att felet hann bytas mot ett annat.**
Ett första rättelseförsök bytte "under 2000 kg" mot "under §39:s gräns i
kravtabellen ovan". Det bevarade inverteringen och lade en tvetydighet ovanpå,
eftersom §39-raden bär två gränsvärden. Lars avgjorde saken därefter, och GRÖNT
prövar nu bara avläsbara registerfakta.

Ny fas ⇒ MINOR.

### 0.2.1 — 2026-08-27

**En falskhet om sändvägen struken.** 0.2.0 skrev "Sändning sker i fas 6 och fas
7". Fas 6 är SKUGGLÄGE, och det här dokumentets egen definition överst säger att
`messages.send` anropas ALDRIG där, inte till kunden, inte till en testadress.
Sändning sker först i fas 7. Meningen låg i ett stycke som texten själv utropar
till sändväg, och §7:s dokumentdetaljundantag omfattar aldrig sändvägen.

**En paragrafhänvisning rättad i samma stycke.** Regeln att `--send` bara
aktiveras av Lars explicita val står i §6, inte §5.

Rättad falskhet i sändvägstext ⇒ PATCH.

### 0.2.0 — 2026-08-27

**Fas 5.5 UTKASTVYN tillkommer**, mellan mallar och skuggläge, på beslut av Lars
i skiva 10.

Fasen ligger FÖRE skuggläget därför att skuggläge utan vy producerar en loggfil
ingen läser. Den bär fyra omdömen loggade åtskilt, varav `forbattra` är den enda
som tränar rösten eftersom den ensam skriver ett nytt par till `data/par.jsonl`.

**Spärrfällda förslag visas utan textfält**, vilket är §9.1 i gränssnittsform: en
redigeringsruta bredvid ett fällt förslag gör förbudet mot att skriva om texten
tills spärren släpper till ett klick. Fasen är sändväg och får full §7.

Ingen kod skrevs i skiva 10. Fasen är beslutad, inte byggd.

Ny fas ⇒ MINOR.

### 0.1.0 — 2026-08-26

Dokumentet upprättat på instruktion av Lars i skiva 3. SKUGGLÄGE definieras här
och ersätter det odefinierade `shadow mode`, som fanns i CLAUDE.md 0.3.0:s
appendixpost som motivering till att sänka §10:s gräns per körning utan att någon
kunde säga vad begreppet innebar.
