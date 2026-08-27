# Roadmap

**Version:** 0.6.0 · **Uppdaterad:** 2026-08-27 · **Implementerar** CLAUDE.md §10

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

#### EN FÖRESKRIFT CITERAS ORDAGRANT, ALDRIG SAMMANFATTAD

Regeln är beslutad av Lars i skiva 13 och gäller varje författningstext den här
fasen och mallarna i fas 5 vilar på.

Skälet är mätt och står i `docs/incidentlogg.md` I6. **§39 formulerades om ur
minnet i två skivor i rad**, och **§42 sammanfattades ur en brief utan att någon
hade läst paragrafen.** Sammanfattningen tappade ett helt kriterium och
skeppade en sändvägsdefekt: boten sade nej till fordon som föreskriften godkänner.

En sammanfattning ser ut som ett faktum men bär ingen kontrollerbar källa. Ett
citat gör skillnaden mellan "så här minns vi det" och "så här står det" synlig
för nästa läsare.

#### TRE FÄLT GATAR OMBYGGNADEN

Beslut av Lars i skiva 13, se `docs/beslutslogg.md` #25. Kravbilden är
**tjänstevikt**, **släpvagnsvikt** och **draganordning**.

**Drivning, karosserikod och barlastflak ingår inte i bedömningen.** Vad
uppslaget i övrigt kan visa är merförsäljning, inte gating, och får inte smyga
tillbaka in som ett villkor.

| Fält | Vad det avgör |
| --- | --- |
| Tjänstevikt | Ett av två ALTERNATIVA lämplighetskriterier i §42 andra stycket. |
| Släpvagnsvikt | Det andra av dem. |
| Draganordning | Registrerad dragkrok, ja eller nej. Kravet i §42 första stycket. |

**Tjänstevikt ströks ur bedömningen i skiva 12 och är tillbaka.** Strykningen
gjordes på premissen att §42 saknar tal. Premissen kom ur briefen till den skivan
och motbevisades av föreskriftens text.

#### TRÖSKLARNA ÄR FÖRFATTNINGSKRAV

**§42 ÄR UPPSLAGEN.** Föreskriften är hämtad från Trafikverket,
`webapp.trafikverket.se/TRVFS/pdf/2003nr019.pdf`, och 4 kap 42 § lyder ordagrant,
tryckt sida 16:

> **42 §** A-traktor skall ha kopplingsanordning och i övrigt vara lämplig som
> dragfordon. Kopplingsanordning skall uppfylla kraven i 43 – 45 §§.
>
> A-traktor är lämplig som dragfordon om
> 1. tjänstevikten är 2 000 kg eller högre eller
> 2. ursprungsfordonet är konstruerat för en släpvagnsvikt av minst 1 000 kg.

**Båda talen står alltså i föreskriften**, och de är **ALTERNATIVA kriterier
förenade med ELLER**. `src/fordonsuppslag.py` implementerar dem som
`TROSKEL_TJANSTEVIKT_KG` och `TROSKEL_SLAPVAGNSVIKT_KG`, prövade i
`ar_lamplig_som_dragfordon`.

Fasen kallade till och med skiva 12 släpvagnsvikten för Auto Stockholms praxis,
på grundval av att §42 skulle sakna tal. Det påståendet var falskt, och
praxisramen är struken.

Mallarna i fas 5 får därför gärna återge talen som författningskrav, eftersom de
är det. Det som INTE får skrivas är att de är verkstadens praxis.

#### VEMS TJÄNSTEVIKT AVSER PUNKT 1? AVGJORD.

**Paragrafen byter subjekt mellan sina två punkter, och koden gör det inte.**

Inledningen lyder "A-traktor är lämplig som dragfordon om", och punkt 1 säger
"tjänstevikten" utan att namnge något annat fordon. Punkt 2 byter uttryckligen
till "ursprungsfordonet". En rimlig läsning är alltså att punkt 1 avser
**A-traktorns** tjänstevikt, alltså vikten EFTER ombyggnaden, medan punkt 2 avser
ursprungsbilens konstruktion.

`utvardera` prövar båda mot `uppslag.tjanstevikt_kg`, som kommer ur ett
registeruppslag på kundens nuvarande bil, alltså ursprungsfordonet.

**BESLUT AV LARS: TJÄNSTEVIKTEN ÄR DENSAMMA FÖRE OCH EFTER OMBYGGNADEN.** Se
`docs/beslutslogg.md` #26.

**Därmed saknar frågan praktisk betydelse.** Är talet detsamma spelar det ingen
roll vilket av fordonen paragrafen syftar på, och `utvardera` prövar rätt storhet.
Punkten stod som blockerande för fasen fram till beskedet och gör det inte längre.

**§39:s BARLASTFLAK ÄR DEN OMBYGGNAD SOM SKULLE KUNNA FLYTTA VIKTEN, och beskedet
gäller ändå.** Ett barlastflak tillför massa, så om någon enskild ombyggnad kunde
göra före och efter till olika tal är det den. Lars besked omfattar det.

Invändningen står här för att göra beskedets räckvidd synlig, inte för att
ifrågasätta det. Hittar någon i framtiden ett fordon där vikterna skiljer sig är
det **det här beslutet** som ska omprövas, inte en glömd detalj.

#### RÖTT KRÄVER ATT BÅDA LÄMPLIGHETSVILLKOREN FALLER

Villkoren är förenade med **eller**, så det räcker att ETT av dem uppfylls.

**Ett fordon med tjänstevikt 2 100 kg och släpvagnsvikt 800 kg är GRÖNT eller
GULT beroende på draganordning, aldrig RÖTT.** Skiva 12 prövade bara
släpvagnsvikten och gav ett sådant fordon RÖTT, alltså ett nej till en kund vars
bil uppfyller kravet. Defekten skeppades och är rättad i skiva 13.

`tests/test_fordonsuppslag.py::test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott`
finns för att den inte ska kunna återkomma tyst. Testet blir rött om
tjänsteviktsvillkoret fälls.

#### §39 om barlastflak, för fullständighetens skull

Barlastflak ingår inte i bedömningen, men §39 citeras här enligt regeln överst:
en föreskrift citeras ordagrant. Skiva 11 och 12 formulerade båda om den ur
minnet. Ordagrant, tryckt sida 15:

> **39 §** Om A-traktorn har en tjänstevikt av högst 2 000 kg, och mindre än 60 %
> av tjänstevikten vilar på drivhjulen, skall den vara försedd med barlastflak
> som medger tillräcklig barlast.
>
> Om A-traktorn har anordning för påhängsvagn, inräknas tillåten belastning på
> vändskivan i bruttovikten och vid beräkning av den procentuella
> axelbelastningen. Av tjänstevikten skall dock minst 40% vila på drivhjulen.

Skiva 11:s återgivning av första stycket stämmer mot källan. Andra stycket, om
påhängsvagn och 40-procentsgränsen, har aldrig stått i repot förrän nu.

#### Fyra utfall

Utvärderingen är boolesk logik på de tre fälten, i
`src/fordonsuppslag.py::utvardera`. Varje utfall får en mall i fas 5.

**LÄMPLIG** nedan betyder §42 andra stycket: tjänstevikt minst 2 000 kg ELLER
släpvagnsvikt minst 1 000 kg.

| Utfall | Villkor | Vad svaret gör |
| --- | --- | --- |
| **GRÖNT** | LÄMPLIG OCH draganordning ja | Redovisar vad som slagits upp, och att det slutgiltiga avgörs vid registreringsbesiktningen. |
| **GULT** | LÄMPLIG, draganordning nej, och kunden har bekräftat att dragkrok saknas | Dragkrok monteras. Svaret NAMNGER prispåslaget. |
| **OKLART** | LÄMPLIG, draganordning nej, inget besked från kunden | Som gult, men FRÅGAR om det ändå sitter en dragkrok som inte är registrerad. |
| **RÖTT** | INTE lämplig, alltså BÅDA villkoren under sin tröskel | Svaret NAMNGER hindret. |

**GULT OCH OKLART HAR SAMMA REGISTERVILLKOR, och det är inte en lucka i tabellen
utan en egenskap hos registret.** En omonterad dragkrok och en monterad men
oregistrerad ser likadana ut i en registeruppgift. Det som skiljer utfallen är
alltså inte något uppslaget kan svara på, utan ett besked från kunden.

`utvardera` bär det som parametern `besked`, och **förvalet är det försiktiga**:
utan besked blir utfallet OKLART, alltså en fråga, aldrig ett påstående om att
dragkrok saknas. GULT nås först när beskedet finns.

**BESKEDET BÄR SIN HÄRKOMST sedan skiva 13.** Det är en `DragkrokBesked` som
måste namnge en källa ur `BeskedKalla`, och de tillåtna källorna är ett
uttryckligt kundsvar eller manuell inmatning i utkastvyn. **Aldrig en modell,
aldrig klassificeraren.** Se `docs/sparrar.md` under
`dragkrokbesked-har-harkomst`.

Ett besked med `saknas=False`, alltså att kunden säger att det SITTER en dragkrok
som registret inte känner till, lämnar fallet på OKLART. Det utfallet är inte
definierat av Lars, och koden stannar därför på det försiktiga.

**BESLUTAT AV LARS i skiva 12.** Briefen listade GULT och OKLART som två utfall
med identiska villkor, vilket en deterministisk funktion inte kan honorera.
Agenten föreslog att beskedet från kunden är det som skiljer dem, och Lars antog
förslaget som beslut. Förvalet OKLART utan besked står fast. Se
`docs/beslutslogg.md` #24.

#### Två tillstånd som inte är utfall

| Tillstånd | Följd |
| --- | --- |
| Registreringsnummer saknas | Utkast |
| Uppslaget misslyckades | Utkast |

Båda bärs av `UppslagMisslyckades` i `src/fordonsuppslag.py` och leder till
utkast. De står åtskilda från utfallen därför att de inte säger något om
FORDONET: de säger att vi inte vet något om det. Ett tomt eller oväntat svar från
hämtningen är ett misslyckat uppslag och aldrig ett utfall.

**Ett svar som saknar TJÄNSTEVIKT är inte ett giltigt uppslag**, samma regel som
för de två andra fälten. Beslut av Lars i skiva 13. Ett uppslag utan tjänstevikt
går inte att pröva mot §42:s första kriterium, och att gissa det hade varit att
fabricera underlaget för ett rött besked.

**HINKTILLDELNINGEN INGÅR INTE I FASEN.** Vilka utfall som får autosvaras är
Lars beslut enligt §10, och det fattas efter utkastvyn i fas 5.5. Ramverksregel 2
i CLAUDE.md §0 gäller oförändrat: ingen kategori flyttas till `auto` av kod.

#### Hämtningen är utbytbar, och det är avsiktligt

`src/fordonsuppslag.py::slag_upp` tar en `hamta`-funktion. Datakällan är inte
avgjord, se beslutslogg #23, så **ett byte av källa ska vara ett byte av EN
funktion och inte en omskrivning av modulen.**

`manuell_hamtning` är den implementation som finns nu: värdena matas in och
modulen utvärderar. Den finns för att fasen ska gå att bygga och pröva innan
avtalet är på plats.

`hamta` har inget förval. Den som anropar väljer källa medvetet, eftersom en tyst
standardkälla i en sändvägsmodul är precis vad §10 finns för att hindra.

#### Var registreringsnumret redan finns

Tillståndet *registreringsnummer saknas* utlöses bara när numret inte går att
hitta, så vilken inflödeskanal som bär det strukturerat avgör hur ofta ärendet
faller till utkast av det skälet.

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
saknas den faller ärendet till utkast. Det är samma regel för alla inflöden och
kräver ingen domänlista. Att i stället lita på avsändaren hade gett fel svar för
`autobutler.se`, där 283 av 287 trådar saknar fältet.

Avläsaren ändrar däremot ingenting i vad som får PÅSTÅS. Ett avläst
registreringsnummer är en INDATA till uppslaget, aldrig ett faktum om bilen.

**SPÄRREN SOM VAKTAR DET ÄR BYGGD.** `fordonsfakta-ur-uppslag` ligger i
`src/fordonsuppslag.py`, fördelad på **fyra funktioner**: `_kontrollera` prövar
svarets form, `_krav_pa_vikt` prövar de två vikterna, `Uppslag.__post_init__`
prövar draganordningen, och `slag_upp` stoppar ett saknat registreringsnummer.
Den är registrerad i `docs/sparrar.md` med sin negativkontroll och sin
fullständiga §7.1-prövning. Den hindrar att fordonsfakta som inte kommer ur ett
lyckat uppslag når ett svar: ett tomt eller oväntat svar från hämtningen kastar
och faller till utkast.

**Spärren `dragkrokbesked-har-harkomst` är byggd i skiva 13** och ligger i
`DragkrokBesked`, i `BeskedKalla` och i `utvardera`. Den senare är dess viktigaste
lager: utan typkontrollen där räcker vilket objekt som helst med ett
`.saknas`-attribut.

**Den vaktar hämtningen, inte formuleringen.** Att en mall återger tröskeln 1000
som ett författningskrav är fortfarande en sändvägsdefekt som ingen kod fångar,
och som därför ligger hos §7:s grind när mallarna skrivs i fas 5.

**SPÄRRENS KÄNDA LUCKOR står utskrivna i `docs/sparrar.md`**, och den som bygger
fas 5 ska läsa dem först. Bland dem: påhittade men typriktiga värden går att
konstruera förbi hämtningen, invarianten gäller konstruktionen och inte en färdig
instans, en källa som KASTAR i stället för att svara fångas inte, och
`dragkrok_bekraftad_saknas` bär ingen härkomst. Spärren täcker hämtningens svar,
inte tystnaden och inte anroparens fantasi.

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

### 0.6.0 — 2026-08-27

**FASENS BLOCKERANDE ÖPPNA PUNKT ÄR AVGJORD.** Beslut av Lars, se
`docs/beslutslogg.md` #26: tjänstevikten är densamma före och efter ombyggnaden.

Frågan om §42 punkt 1 avser ursprungsfordonet eller den ombyggda A-traktorn
saknar därmed praktisk betydelse, eftersom det är samma tal oavsett, och
`utvardera` prövar rätt storhet. **Fasen stannar inte längre på den punkten.**

Avsnittet skriver ut att §39:s barlastflak är den ombyggnad som skulle kunna
flytta vikten och att beskedet gäller ändå. Det står där för att göra beskedets
räckvidd synlig: hittar någon ett fordon där vikterna skiljer sig är det
beslutet som ska omprövas.

**0.5.0-posten nedan säger att punkten är blockerande.** Den står kvar som den
skrevs; den här posten är upphävandet, enligt §8:s regel att en committad
appendixpost rättas genom en ny versionspost och inte genom omskrivning.

Avgjord blockerande punkt ⇒ MINOR.

### 0.5.0 — 2026-08-27

**Fas 4.5 omskriven mot §42:s faktiska lydelse**, på beslut av Lars i skiva 13,
se `docs/beslutslogg.md` #25.

**Kravbilden är tre fält.** Tjänstevikt är tillbaka. §42 andra stycket ger två
ALTERNATIVA lämplighetskriterier förenade med *eller*, och **RÖTT kräver att
båda faller**. Skiva 12 prövade bara släpvagnsvikten och gav ett fordon med
tjänstevikt 2 100 kg och släpvagnsvikt 800 kg RÖTT, alltså ett nej till en kund
vars bil uppfyller kravet. Fasen namnger regressionsvakten som hindrar att det
återkommer.

**Ny regel: EN FÖRESKRIFT CITERAS ORDAGRANT, ALDRIG SAMMANFATTAD.** Skälet står
i `docs/incidentlogg.md` I6. §39 formulerades om ur minnet i två skivor, och §42
sammanfattades ur en brief utan att någon läst paragrafen; sammanfattningen
tappade ett helt kriterium.

**Beskedet om dragkrok bär sin härkomst**, och fasen namnger de två tillåtna
källorna. Ett besked med `saknas=False` lämnar fallet på OKLART, eftersom det
utfallet inte är definierat.

**BLOCKERANDE ÖPPEN PUNKT: vems tjänstevikt avser §42 punkt 1?** Punkten är
blockerande för fasen och avgörs av besked från en besiktningsman, inte av oss.
Beslut av Lars. Paragrafen byter subjekt
mellan sina punkter, koden gör det inte, och antagandet att de två vikterna är
samma är agentens och inte belagt. Fasen bär punkten.

**Om formen.** Fas 4.5 skrevs om i skiva 13 utan att den här posten skrevs och
utan versionshöjning. §8 säger att en ändring utan appendixpost är en ospårbar
ändring. Granskningen fällde det, och posten är skriven i efterhand inom samma
skiva. Följden var att 0.4.0-posten nedan beskrev ett innehåll som inte längre
fanns, utan att något upphävde den.

Omskriven fas och ny regel ⇒ MINOR.

### 0.4.0 — 2026-08-27

**Fas 4.5 skriven om mot en ny kravbild**, på beslut av Lars i skiva 12, se
`docs/beslutslogg.md` #24.

**Kraven är två: släpvagnsvikt och draganordning.** Tjänstevikt, drivning,
karosserikod och barlastflak utgår ur bedömningen och är struket ur fasen.
Den kravbild fasen bar till och med 0.3.0 var alltså felaktig och inte bara
ofullständig.

**Tröskeln 1000 kg står utskriven som PRAXIS.** VVFS 2003:19 4 kap 42 § kräver
kopplingsanordning utan att ange något tal; talet kommer ur verkstadens
erfarenhet och ur besked från besiktningsmän. Fasen säger uttryckligen att en
mall som återger talet som ett författningskrav är en sändvägsdefekt.

**Fem scenarier ersatta av fyra utfall plus två tillstånd.** Utfallen är GRÖNT,
GULT, OKLART och RÖTT, och de avgörs av `src/fordonsuppslag.py::utvardera`.
Tillstånden, saknat registreringsnummer och misslyckat uppslag, är inte utfall:
de säger inget om fordonet utan att vi inte vet något om det, och båda leder till
utkast.

**GULT och OKLART har identiska registervillkor**, och fasen skriver ut att det
är en egenskap hos registret och inte en lucka i tabellen. Skillnaden bärs av ett
besked från kunden, med det försiktiga förvalet OKLART. **Den tolkningen är
agentens och inte Lars beslut**, och fasen bär den som en öppen punkt.

**Hämtningen är utbytbar**, med #23 som skäl: datakällan är inte avgjord.
`hamta` har inget förval, eftersom en tyst standardkälla i en sändvägsmodul är
vad §10 finns för att hindra.

**Spärren `fordonsfakta-ur-uppslag` är byggd**, i `src/fordonsuppslag.py`, och
stycket som sade att den inte fanns är ersatt. Fasen säger nu också vad spärren
INTE vaktar: att en mall återger tröskeln som författningskrav fångas av ingen
kod, och de luckor granskningen hittade, var och en med sin källa.

**§42 ÄR UPPSLAGEN, OCH PRAXISRAMEN FÖLL.** Lars gav instruktionen att läsa
föreskriften och rapportera vad som faktiskt står. Den är hämtad från Trafikverket
och citeras nu ordagrant i fasen.

Paragrafen ANGER ett tal: punkt 2 säger "släpvagnsvikt av minst 1 000 kg". Fasen
hade sagt motsatsen, att §42 saknar tal och att 1000 är verkstadens praxis. Det
var falskt, och hela ramen är struken. Talet är ett författningskrav.

**Uppslagningen gav också ett andra kriterium som ingen kände till.** §42:s
villkor är förenade med *eller*: tjänstevikt minst 2 000 kg ELLER släpvagnsvikt
minst 1 000 kg. `utvardera` prövar bara det senare, så ett fordon med tjänstevikt
2 100 kg och släpvagnsvikt 800 kg får RÖTT trots att föreskriften säger att det
duger. Att rätta det kräver tjänstevikt som ett tredje fält, alltså det fält
skivan strök på premissen att §42 var tyst. **Punkten är öppen och blockerande,
och ingen kod ändrades av agenten.**

**§39 citeras nu ordagrant i fasen**, trots att barlastflak inte gatar. Skiva 11
och 12 formulerade båda om paragrafen ur minnet. Första stycket stämde; andra
stycket, om påhängsvagn och en 40-procentsgräns, har aldrig stått i repot förrän
nu.

Omskriven fas och ny kravbild ⇒ MINOR.

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
