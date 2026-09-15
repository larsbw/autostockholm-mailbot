# Roadmap

**Version:** 0.16.0 · **Uppdaterad:** 2026-09-15 · **Implementerar** CLAUDE.md §10

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

**FASNUMREN ÄR IDENTITETER, ORDNINGEN I FILEN ÄR UTFÖRANDEORDNING.** Sedan
beslutslogg #39 byggs fas 5.5 FÖRE fas 5, och avsnitten står i den ordning de
utförs. Numren är oförändrade därför att de är korsreferenser i
`docs/beslutslogg.md`, `docs/sparrar.md` och CLAUDE.md; en omnumrering hade gjort
varje sådan hänvisning fel utan att tillföra något.

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

`config/kategorier.yaml` upprättas ur materialet, och varje kategori får en
hink: `auto`, `utkast` eller `aldrig`. `scripts/kategoristatus.py` byggs, så att
§12:s maskinproducerade statusrad går att köra.

**Grind:** Lars beslutar kategorilistan och varje kategoris STARTHINK. Kod
flyttar aldrig en kategori mellan hinkar (§0, ramverksregel 2).

*Grindvillkoret bar tidigare meningen "Ingen kategori startar i `auto`". Den är
STRUKEN på Lars beslut i skiva 18, se `docs/beslutslogg.md` #30. Villkoret
skrevs i skiva 3, verifierat med `git log -S`, alltså innan något underlag
fanns. Det var en förhandsgissning om ett beslut som tillhör Lars, och aldrig en
ramverksregel: ramverksregel 2 förbjuder att KOD flyttar en kategori till `auto`
och kräver Lars uttryckliga beslut. Det beslutet är fattat i skiva 17.*

*Raden om `docs/kategorier.md` är struken i samma skiva. Filen behövs inte, se
#30.*

> **GRINDEN ÄR FATTAD I SKIVA 17, se `docs/beslutslogg.md` #29.**
> `config/kategorier.yaml` kom i samma skiva, `scripts/kategoristatus.py` i
> skiva 18. Fasens leverabler är därmed på plats, räknat från den commit som
> bär den här raden: §5 säger att en uppgift inte är klar förrän origin/main
> bär den, och den här meningen skeppas i samma commit som skriptet.

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

#### FEM FÄLT GATAR OMBYGGNADEN

Tre av dem bär §42 och är Lars beslut i skiva 13, se `docs/beslutslogg.md` #25:
**tjänstevikt**, **släpvagnsvikt** och **draganordning**. Två till kom med hans
beslut i skiva 55, se #121: **kaross** och **fyrhjulsdrift**.

*Här stod att "drivning, karosserikod och barlastflak ingår inte i bedömningen"
och att allt annat uppslaget kan visa är merförsäljning. Det var sant från skiva
13 till skiva 55 och är upphävt: karossen avgör om fordonet redan är ombyggt, och
drivningen tillsammans med tjänstevikten om §39:s barlastflakskrav gäller.
`src/fordonsuppslag.py` bar samma mening och är rättad där.*

| Fält | Vad det avgör |
| --- | --- |
| Tjänstevikt | Ett av två ALTERNATIVA lämplighetskriterier i §42 andra stycket. Och §39:s första led, där samma tal är en ÖVRE gräns. |
| Släpvagnsvikt | Det andra av §42:s två. |
| Draganordning | Registrerad dragkrok, ja eller nej. Kravet i §42 första stycket. |
| Kaross | `Ombyggd Bil` betyder att fordonet REDAN är ombyggt. RÖTT, av ett annat skäl än §42:s. |
| Fyrhjulsdrift | `Ja` fäller §39:s andra led: vilar varje hjul på drivningen är det inte `mindre än 60 %`. |

**`totalvikt`, `fordonsår / modellår` och `status` läses men gatar ingenting.**
De bärs av `Uppslag` och visas i vyns härkomstrad, och de når aldrig prompten:
varje tal i prompten blir ett citerbart tal.

**Ett fält Lars bad om finns inte på sidan.** Briefen till skiva 55 säger
`fordonsslag` med värdet `Traktor`. Mätt över tio sparade fordonssidor bär sidan
62 etiketter, och ingen heter `Typ` eller `Fordonsslag`; inget av de 62 värdena
är `Traktor`. Signalen heter `Kaross: Ombyggd Bil` på den öppna sidan, alltså
briefens andra led. Se #121.

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

#### RÖTT UR §42 KRÄVER ATT BÅDA LÄMPLIGHETSVILLKOREN FALLER, OCH ATT BÅDA ÄR AVLÄSTA

Villkoren är förenade med **eller**, så det räcker att ETT av dem uppfylls.

**SEDAN SKIVA 55 RÄCKER DET INTE ATT DE FALLER, DE MÅSTE OCKSÅ VARA AVLÄSTA.**
Ett uppslag kan numera lyckas med släpvagnsvikten tom, eftersom registret inte
bär den för var annan bil. Ett `not lämplig` hade läst den okunskapen som ett NEJ
och gett kunden ett avslag på en uppgift registret aldrig lämnat, alltså skiva
12:s defekt i ny form. `ar_lamplig_som_dragfordon` svarar därför `None` i det
läget, och `utvardera` gör OKLART av det.

**RÖTT HAR DESSUTOM ETT ANDRA SKÄL SEDAN SAMMA SKIVA**, nämligen att fordonet
redan är ombyggt. De två skälen får inte blandas ihop i svaret: det ombyggda fordonet med tjänstevikt 2 005 kg har
tjänstevikt 2 005 kg, alltså ÖVER §42:s tröskel, och ett avslag med viktskälet
hade varit falskt om just den bilen.

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
formuläret. **Avläsaren i fas 4.5 ska läsa VÄRDET i fältet, aldrig huvudet och
aldrig avsändaren.**

*Meningen sade tidigare att avläsaren ska leta efter FÄLTET. Motsatsställningen
mot huvudet och avsändaren är oförändrad, men ordet FÄLTET bar där den betydelse
som upphävs längre ned: att fältet finns är inte samma sak som att ett värde gick
att läsa. Fältraden bärs av 78 av 78 formulärtrådar medan värdet duger i 77.*

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

**WEBBFORMULÄRET ÄR DEN KANAL SOM FAKTISKT BÄR NUMRET, och den är vår egen.**
Uppmätt i skiva 15. Predikatet för en formulärtråd är att ämnesraden på trådens
första kundmeddelande innehåller `offertförfrågan a-traktor`,
skiftlägesokänsligt. Det ger 78 trådar i `data/tradar.jsonl` och noll i den
obesvarade filen, av skäl som står under `gmail-etikett-som-ensam-grund` i
`docs/sparrar.md`.

Formuläret skickar ett fast fältblock. Etiketterna, avlästa ur den avkodade
kroppen med `src/urval.py::brodtext`:

| Fältetikett | Bärs av |
| --- | --- |
| `Namn` | 78/78 |
| `E-post` | 78/78 |
| `Växellåda` | 78/78 |
| `Bilmodell` | 78/78 |
| `Telefon` | 78/78 |
| `Registreringsnummer` | 78/78 |
| `Meddelande` | 56/78 |
| `Tillval` | 26/78 |
| `Övriga frågor` | 1/78 |

**Fältnamnet är `Registreringsnummer`, utskrivet i sin helhet.** Det matchas av
etikettformen ovan, som redan bär `registreringsnummer` skiftlägesokänsligt, så
ingen ändring av predikatet behövs. Att formen är den fullständiga och inte en
förkortning är däremot värt att veta för den som skriver avläsaren.

**MÖNSTRET FÖR ETT REGISTRERINGSNUMMER, utskrivet så att talen nedan går att
räkna om.** `\b[A-ZÅÄÖ]{3}[\s-]?\d{2}[A-ZÅÄÖ0-9]\b`, prövat
SKIFTLÄGESOKÄNSLIGT. Mönstret lånas ur `scripts/persondatakontroll.py` och
kopieras inte.

**Skiftläget är inte en detalj.** Samma mönster prövat VERSALKÄNSLIGT, alltså
precis som §6-kontrollen använder det, ger 46 av 78 i stället för 77 av 78.
§6-kontrollen är versalkänslig för att inte larma på vanliga ord i löptext, men
en avläsare som ärver den strängheten skulle tappa 31 av de 77 nummer som går
att läsa.

*Här stod meningen "Kunden skriver alltså inte sitt nummer versalt." Den är
falsk som allmän sats, och motsägs av talet i meningen FÖRE den, som den drog
sin slutsats ur: 46 av 78 matchar det versalkänsliga mönstret, alltså skriver
en majoritet versalt. Det som gäller är att INTE ALLA gör det. Struket i skiva
16 efter §7-granskningen.*

**Talet 31 gäller en FÄLTAVLÄSARE, inte en fritextsökning.** Skriptet prövar det
strikta mönstret mot FÄLTVÄRDET, alltså mot samma sträng som den giltiga
avläsningen använder, och får 46 där. Bortfallet 31 av 77 är alltså mätt på det
som fasen ska bygga och inte på kroppen som helhet. Att kroppen och ämnesraden
ger samma 46 är en kontroll, inte källan till talet.

Att de 31 BÄR ett nummer och inte saknar ett följer av mätningen: båda talen
kommer ur samma mönster mot samma sträng, och det enda som skiljer prövningarna
är `re.IGNORECASE`. Vilket skiftläge de 31 har är däremot inte mätt.

> **FÖRESKRIFT: AVLÄSAREN I FAS 4.5 SKA VARA SKIFTLÄGESOKÄNSLIG.**
> Beslut av Lars i skiva 16, se `docs/beslutslogg.md` #28 och luckan
> `versalkansligt-monster-i-avlasare` i `docs/sparrar.md`.
>
> Mönstret får lånas ur `scripts/persondatakontroll.py`, men det ska prövas med
> `re.IGNORECASE`. Att låna mönstret utan flaggan är att ärva en stränghet som
> §6-kontrollen behöver och avläsaren inte tål.
>
> **Detta är en sändvägsdefekt, inte en formfråga.** Ett tappat
> registreringsnummer betyder att uppslaget inte kan göras, att gatingen faller
> till `utkast`, och att kunden får vänta på en handpåläggning som ärendet inte
> behövde. Felet syns inte i något test som matar in versala nummer, eftersom
> testdata skrivs av den som skriver koden och den skriver versalt. **Det slår
> först i drift, mot kundens egen inmatning.**

**TALEN GÅR ATT RÄKNA OM.** Kör `.venv/bin/python scripts/formular-matning.py`.
Skriptet bär avsnittets MÄTTA tal, mäter mot avkodad brödtext, och
skriver ut båda skiftlägesvarianterna. Skulle en framtida körning ge andra tal än
texten här är det texten som är föråldrad.

Undantaget är talet tre i **Formuläret löser INTE gatingen** nedan, som räknar
fält i `src/fordonsuppslag.py` och läses där.

**FÄLTET FINNS ALLTID, VÄRDET DUGER INTE ALLTID.** Fältraden
`Registreringsnummer:` finns med ett icke-tomt värde i 78 av 78, medan det värdet
tolkas som ett registreringsnummer i 77 av 78. Den enda tråd som faller har
alltså ett ifyllt fält vars innehåll inte är ett nummer. Det senare mäts på just den raden och inte som en fritextsökning i kroppen,
eftersom det är fältvärdet en avläsare ska använda.

Den skillnaden är exakt det tillstånd fasen finns för: fältet är läst, numret är
oanvändbart, ärendet faller till utkast. **En avläsare som testar om ETIKETTEN
finns svarar fel på den tråden.** Villkoret är att ett giltigt värde gick att
läsa, aldrig att fältet fanns.

**Ämnesraden bär samma nummer, och de säger aldrig emot varandra.** Av de 78
matchar 77 ämnesrader mönstret, samma 77 som i kroppen, och i alla 77 är värdena
identiska. Noll trådar har numret i kroppen men inte i ämnesraden.

**Det gör ämnesraden till en bekräftande signal, aldrig till en ensam grund.**
Negativkontroll, samma mönster mot ämnesraden på varje tråds FÖRSTA
kundmeddelande, alltså en rad per tråd och inte varje meddelandes: 8 av de 411
trådar i `data/tradar.jsonl` som bär ett kundmeddelande matchar utan att vara
formulärtrådar, och 23 av de 1604 obesvarade. Mätningen avgör INTE om de
träffarna är verkliga registreringsnummer, som en kund mycket väl kan skriva i en
ämnesrad, eller sammanträffanden i fakturareferenser. Den avgör bara att mönstret
ensamt inte skiljer kanalerna åt. Avläsaren läser alltså fältet, och får använda
ämnesraden för att kontrollera det den redan läst.

> **TALET 411 BÄR TVÅ BETYDELSER I DET HÄR AVSNITTET, och de är olika mängder.**
> Ovan, i tabellen över förmedlare, är 411 antalet förmedlartrådar bland de
> OBESVARADE. Här är 411 antalet trådar i `data/tradar.jsonl` som bär ett
> kundmeddelande. Båda är uppmätta och sammanfallandet är ett sammanträffande.
> Den som räknar om ett tal härifrån ska kontrollera vilken av dem som avses.

**Formuläret löser INTE gatingen.** Inget av fälten är tjänstevikt,
släpvagnsvikt eller draganordning, alltså de tre fält som `src/fordonsuppslag.py`
utvärderar. Formuläret bidrar med registreringsnumret, som är INDATA till
uppslaget, och med `Bilmodell` och `Växellåda`, som är kundens egna uppgifter och
inte fakta om fordonet. Gatingen vilar oförändrat på uppslaget.

**§6-följd som gäller varje framtida rapport.** Formulärets ämnesrad bär
registreringsnumret i klartext i 77 av 78 trådar. En rapport, ett commitmeddelande
eller ett dokument som citerar ämnesrader ur det här materialet läcker alltså
persondata, även när brödtexten aldrig rörs.

**Följden för fasen.** Fas 4.5 bygger en fältavläsare, och den villkoras på
VÄRDET i fältet och aldrig på avsändaren: gick ett giltigt nummer att läsa ur
etikettformen används det, annars faller ärendet till utkast. Det är samma regel
för alla inflöden och kräver ingen domänlista.

*Villkoret stod tidigare som att numret används om etikettformen finns i tråden.
Den lydelsen är upphävd av mätningen ovan: etiketten bärs av 78 av 78
formulärtrådar medan ett giltigt värde går att läsa i 77. Att fältet finns är
alltså inte samma sak som att numret gick att läsa, och det är värdet som
villkoret gäller.* Att i stället lita på avsändaren hade gett fel svar för
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

**Grind:** Lars beslut om **datakälla och avtal**, se beslutslogg #23 och #31.
Fasen lämnas inte av att koden fungerar mot en testnyckel.

> **GRINDEN ÄR PASSERAD. BÅDA LEDEN ÄR AVGJORDA AV LARS.**
> #31 väljer **den öppna fordonssidan** hos biluppgifter.se, utan API-nyckel och
> utan avtal. Avtalsledet avgjorde Lars 2026-09-02 genom att stryka det:
> **källans användarvillkor läses inte, och frågan ska inte tas upp igen.**
>
> **Villkoren är alltså olästa, och ingenting påstås här om vad de säger.** Två
> frågor lämnas obesvarade med avsikt: om automatiserad hämtning av de öppna
> sidorna är tillåten, och om vidareförmedling av fälten i ett kommersiellt
> kundmail är tillåten. Risken är **oläst och accepterad**, inte bedömd. Se #31:s
> avsnitt *AVGJORT AV LARS* för vad beslutet inte innebär.
>
> `src/biluppgifter.py` är byggd och prövad enligt §7.1, se spärren
> `fordonsfakta-ur-sida` i `docs/sparrar.md`. **Att den fungerar var aldrig
> grindens villkor**, av samma skäl som raden ovan ger om testnyckeln. Grinden
> passeras av beslutet, inte av koden.

### Fas 5.5 — Utkastvyn · BYGGS FÖRE FAS 5

Webbvyn där Lars och Matte läser botens förslag och fäller omdöme om dem.
**Inloggningen sker som ett DELAT konto enligt #37**, så loggen skiljer inte de
två åt. Så länge Lars ensam granskar är det utan betydelse; kopplas Matte in
krävs ett eget konto, och det är ett eget beslut.
Beslutad av Lars i skiva 10. Hostas på `mailagent.dasher.se` enligt
beslutslogg #20 och #38, med inloggning enligt #37 och #22.

**BYGGS FÖRE FAS 5, beslutslogg #39.** Lars skriver fyra till fem referenssvar
direkt i vyn, alltså skapas rösten här, och mallarna i fas 5 byggs ur de svaren
tillsammans med `data/par.jsonl`. Den gamla ordningen krävde att mallarna fanns
innan Lars skrivit något, och att Lars skrev i en vy som inte fanns.

**BINDANDE: VYN SKA KUNNA VISA ETT INKOMMANDE MAIL UTAN ETT BOTGENERERAT
FÖRSLAG.** Tomt fält, Lars skriver, det sparas som ett par i `data/par.jsonl`.
Det är ett krav fasen inte var specad för: den utgick från att varje post bär ett
förslag som ska bedömas med ett av fyra omdömen. Den utgångspunkten gäller inte
för de första posterna.

**BINDANDE: ETT REFERENSSVAR SKICKAS ALDRIG.** Kunderna har fått svar för länge
sedan eller inte alls. Texten sparas som ett par, aldrig som utgående mail.

**Det är en ANNAN KNAPP än den vyn var specad för, och den måste vara omöjlig att
förväxla.** Fältet innehåller text som ser ut precis som ett svar och som ändå
aldrig får nå en kund. Raden längre ned om att vyn aldrig skickar mail gäller
oförändrat och skärps av detta.

**BINDANDE: EN SPÄRRFÄLLD POST VISAR ALDRIG ETT TEXTFÄLT, OAVSETT LÄGE.** Lars
beslut, beslutslogg #40. Detta stänger den öppna punkt fasen bar: en post kan ha
både ett fällt förslag och ett behov av ett referenssvar, och då gäller
textfältsförbudet.

Behövs en referens för ett ärende vars förslag fälldes, **tas en annan post av
samma kategori**. Referenssvaret är ett underlag för rösten och inte ett svar på
just det ärendet, så vilken post texten skrivs mot spelar ingen roll för det
kravet, medan det spelar all roll för §9.1.

Skälet är att en textruta på en spärrfälld post gör förbudet till ett klick även
när knappen heter spara och inte skicka. **Vyn ska inte lära handen den
rörelsen.** Regeln är alltså inte att texten skulle nå en kund, utan att
gränssnittet inte ska öva in rörelsen att skriva om ett fällt mail.

Byggd i skiva 27, `src/vy.py` i `rendera_granskning`, och registrerad i
`docs/sparrar.md`.

**BINDANDE, DRIFT: `token.json` och `data/` ligger på ett PERSISTENT VOLUME,
aldrig i containern.** Beslutslogg #38. Railway kör om containern vid varje
deploy och allt i den försvinner. Kravet står här och inte bara i beslutsloggen
därför att det ska vara läst innan fasen byggs, inte upptäckas i drift.

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

**BYGGD LOKALT FÖRST, skiva 27.** Vyn kördes på `127.0.0.1` utan inloggning och
utan Railway, så att den gick att se och rätta innan den exponeras. Hosting
enligt #38 och inloggning enligt #37 är en EGEN SKIVA och är inte gjord.

Vad skiva 27 byggde: `src/vy.py` med båda lägena, `scripts/kor-vy.py` som
startar den, och spärren mot att vyn har någon sändväg alls.

**BÅDA LÄGENA HAR EN VÄG IN. GRANSKNINGSLÄGET FICK SIN RUTT I SKIVA 34**,
`/granskning/N` för att läsa och `/omdome/N` för att spara. `do_GET` rutar
`/granskning` till granskningsläget och allt annat till referensläget, och
`scripts/kedja-prov.py --vy` startar det på sparade fall.

*Här stod att granskningsläget RENDERAR MEN INTE ÄR KOPPLAT, att
`rendera_granskning` och `spara_omdome` saknar anropare i `src/` och `scripts/`,
och att `do_GET` rutar VARJE begäran till referensläget. Alla tre leden blev
falska av skiva 34, och `src/vy.py::bygg_hanterare` skriver ut rättelsen i sin
egen docstring medan den stod kvar här, i den fas Lars läser för att veta vad som
är byggt. Samma defektform som de två posterna i fas 5.*

**Grind:** Lars beslutar att omdömesvolymen räcker. Talet sätts inte i förväg,
eftersom det beror på hur många kategorier som visar sig bära underlag, och
skiva 9 mätte att bara två kategorier når tio par med svar.

### Fas 5 — Mallar och spärrar · BYGGS EFTER FAS 5.5

Mallarna byggs ur `data/par.jsonl` OCH ur de referenssvar Lars skriver i vyn,
alltså ur faktiska svar (§11).
`config/sparrar.yaml` och spärrlogiken byggs, och varje spärr registreras i
`docs/sparrar.md` med sin negativkontroll och sin redundans.
`config/priser.json` och `config/fakta.json` upprättas.

**GENERATORN ÄR BYGGD I SKIVA 31**, `src/generera.py`, se
`docs/beslutslogg.md` #49. Den skriver ett SVARSUTKAST och har ingen sändväg.

**Rösten kommer ur `data/par.jsonl` som FÅ-EXEMPEL, inte som mallar att fylla i.**
Det är en avvikelse från fasens ordalydelse ovan och ett medvetet val: en mall
med hål tvingar in varje svar i samma form, medan få-exempel bär tonen och låter
svaret följa frågan. `config/sparrar.yaml` finns fortfarande inte.

**Spärrarna på det genererade är byggda och registrerade**, en post per spärr i
`docs/sparrar.md`. `src/generera.py::krav_pa_svaret` anropar dem i tur och
ordning, och den funktionen är listan: `tomt-svar`, `genererat-tal-har-kalla`,
`genererat-fordonsfaktum`, `pastaende-om-franvaro`,
`troskeln-som-forfattningstext` och `atagande-om-priset`.

*Här stod "TRE spärrar" med tre namn uppräknade. `tomt-svar` byggdes i skiva 34
och `pastaende-om-franvaro` i skiva 40, båda registrerade i `docs/sparrar.md`,
alltså var talet falskt i den lista Lars läser för att veta vad som är byggt.
Rättat i skiva 46, som lade till den sjätte.*

**Vad som ÅTERSTÅR i fasen:**

- `config/priser.json` FINNS sedan skiva 41 och är **FYLLD av Lars i skiva 44**.
  Fem poster bär pris, `tillbehor` står kvar tom därför att prislistan inte bär
  något fast tillbehörspris. Att ändra ett värde är Lars beslut, och
  `test_prisfilen_i_repot_bar_EXAKT_det_Lars_BESLUTAT` binder HELA innehållet
  ordagrant. Se `docs/beslutslogg.md` #94 och #106.
  **DE FYRA LUCKOR SOM GATADE FYLLNINGEN ÄR AVGJORDA AV LARS I SKIVA 42.** Lucka
  52, 53 och 54 är stängda, lucka 55 är öppen och medvetet så. Se
  `docs/beslutslogg.md` #96 till #99.
  *Här stod att filen bär sex poster som ALLA ÄR TOMMA och att
  `test_prisfilen_i_repot_har_BARA_TOMMA_varden` binder dem. Lars fyllde filen i
  skiva 44 och vakten band om och bytte namn i samma skiva, alltså var båda leden
  falska i just den lista Lars läser för att veta vad som återstår. Här stod före
  det att lucka 52 måste avgöras innan en post fylls, vilket blev falskt av skiva
  42.*
- `config/fakta.json` FINNS sedan skiva 36, bär `bokningar` sedan skiva 37 och
  **`telefon` sedan skiva 44**, båda på Lars §10-beslut.
  `test_faktafilen_i_repot_bar_EXAKT_det_Lars_BESLUTAT` binder hela innehållet.
  Se `docs/beslutslogg.md` #74, #77 och #106.
  *Här stod att `telefon` är fortfarande TOM, att boten därför inte kan skriva
  numret, och att `test_faktafilen_i_repot_har_TOM_telefon` binder det. Lars
  fyllde posten i skiva 44 och vakten bytte namn, alltså var alla tre leden
  falska. Boten skriver numret i varje läst utkast sedan dess.*
- `config/sparrar.yaml`, som fasen kräver och som fortfarande inte finns.
- Mallarna ur Lars referenssvar i vyn, se fas 5.5. Generatorn använder paren som
  få-exempel och bygger inga mallar.
- §11:s härkomstrad: ett utkast bär i dag ingen uppgift om vilka par det vilar
  på, se `docs/beslutslogg.md` #49.

Med `priser.json` FYLLD prövas ett pris mot filens egna tal: en sats som bär ett
prisord måste bära minst ett tal, och varje tal i den satsen ska komma ur
prisfilen. Ett åtagande om vad priset TÄCKER prövas av `atagande-om-priset`, och
godtas bara när prisfilens värde står ordagrant. Kända luckor står i
`docs/sparrar.md` under `genererat-tal-har-kalla` och `atagande-om-priset`.

*Här stod "Så länge `priser.json` är TOM faller varje svar som nämner ett pris".
Lars fyllde filen i skiva 44, alltså var meningens premiss falsk i presens.
Fällt i skiva 46.*

*Här stod att bara `priser.json` och `fakta.json` återstår, och att VARJE svar
som nämner ett pris faller. Båda leden var för snäva respektive för breda. Fällt
av §7-granskningen av skiva 31, varv 1.*

*Här stod sedan "Tills `priser.json` finns", och listan ovan sade att filen
återstår att upprätta. Filen skapades i skiva 41, alltså blev båda falska i den
lista Lars läser för att veta vad som återstår. Det är EXAKT den defekt 0.15.1
skrevs för att rätta för `config/fakta.json`, upprepad för prisfilen. Fällt av
§7-granskningen av skiva 41, varv 2.*

**Grind:** Lars godkänner varje mall ORDAGRANT, och varje ändring i
`config/sparrar.yaml`, `config/priser.json` och `config/fakta.json` är ett
§10-stopp. Hela fasen är sändväg och får full §7, ovillkorligt.

### Fas 6 — Skuggläge

`respond.py` körs i skuggläge enligt definitionen överst. Beslutsloggen samlas
och läses. Klassificeringens träffsäkerhet mäts mot verkliga mail, och spärrarnas
utfall granskas post för post.

**KEDJAN OCH BESLUTSLOGGEN ÄR BYGGDA I SKIVA 34**, se `docs/beslutslogg.md` #61
och #62. `src/kedja.py` binder ihop klassificering, fordonsuppslag, generering,
spärrar och vy, och `kedja.logga_beslut` skriver raden. Loggen finns alltså
FÖRE skuggläget, som fasen kräver.

**SLINGAN ÄR BYGGD I SKIVA 48**, `scripts/respond.py`. Den bygger ett ärende ur
varje Gmail-tråd, sållar bort maskinmail vid källan, kör kedjan per ärende,
loggar en rad för VARJE utfall och sparar fallen till vyn. Den har ingen
`--send` och ingen väg till en brevlåda.

**HÄMTNINGEN UR BREVLÅDAN ÄR BYGGD I SAMMA SKIVA**, `src/inkorg.py`, efter
Lars §10-beslut om ett nytt OAuth-scope. Se `docs/beslutslogg.md` #113.

`vyn-har-ingen-sandvag` i sin ursprungliga form går inte att hålla för en modul
som ska läsa brevlådan: `src/mine.py` drar in `googleapiclient.errors` och
`src.auth`, och den senare `googleapiclient.discovery`. Uppmätt i skiva 48.
Lars beslut var FYRA LAGER i stället, och bara det första är Googles:

| # | lager | vad det är |
| --- | --- | --- |
| 1 | scopet | `gmail.readonly` mot `token-las.json`. Sändförmågan FINNS INTE. |
| 2 | tjänsten | `inkorg.Lastjanst`, bara läsvägarna öppna. |
| 3 | importlagret | `vy.GMAILBARANDE_MODULER`, tre namngivna moduler. |
| 4 | källtexten | `vy.FORBJUDET_MONSTER`, oförändrat över hela grafen. |

**VYNS OCH KEDJANS PRÖVNING ÄR OFÖRÄNDRAD.** `tillatna` är tom som förval, och
`src/vy.py` och `src/kedja.py` anropar utan den: för dem gäller fortfarande
ingen väg alls.

**`token.json` RÖRS INTE.** Fas 7 bygger sin sändmodul mot den filen, alltså
kräver vägen tillbaka till sändning ingen ny consent.

*Här stod att `respond.py` FINNS INTE ÄN och att kedjan anropas i dag bara av
`scripts/kedja-prov.py`. Båda blev falska av skiva 48, i den fas Lars läser för
att veta vad som är byggt. Samma defektform som de rättade posterna i fas 5 och
fas 5.5.*

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

### 0.16.0 — 2026-09-15

**FAS 6:s SLINGA ÄR BYGGD, `scripts/respond.py`.** Fasens stycke sade att
`respond.py` FINNS INTE ÄN och att kedjan anropas bara av
`scripts/kedja-prov.py`. Båda blev falska av skiva 48 och är rättade med en
kursiv not.

**HÄMTNINGEN UR BREVLÅDAN ÄR OCKSÅ BYGGD, `src/inkorg.py`.** Lars §10-beslut
om ett nytt OAuth-scope, se `docs/beslutslogg.md` #113. Fasens stycke bär de
fyra lagren och noterar att vyns och kedjans prövning är oförändrad.

Två byggda led i en fas ⇒ MINOR.

### 0.15.5 — 2026-09-14

**TRE FALSKA PÅSTÅENDEN RÄTTADE, alla i den text Lars läser för att veta vad som
är byggt och vad som återstår.**

Fas 5 sade att `config/priser.json` bär sex poster som ALLA ÄR TOMMA och att
`config/fakta.json`:s `telefon` är fortfarande TOM. Lars fyllde båda filerna i
skiva 44, se `docs/beslutslogg.md` #106. Båda raderna namngav dessutom vakter
som bytte namn i samma skiva.

Fas 5.5 sade att GRANSKNINGSLÄGET RENDERAR MEN ÄR INTE KOPPLAT, att
`rendera_granskning` och `spara_omdome` saknar anropare och att `do_GET` rutar
varje begäran till referensläget. Alla tre blev falska av skiva 34, och
`src/vy.py::bygg_hanterare` skriver ut rättelsen i sin egen docstring.

**0.15.4:s EGEN SLUTRAD BLEV FALSK AV SKIVA 44.** Den sade INGET VÄRDE ÄR SATT.
Appendixposter skrivs inte om, alltså står den kvar och upphävs av den här.

Rättade påståenden i två faser ⇒ PATCH.

### 0.15.4 — 2026-09-14

**FAS 5:s RAD OM PRISFILEN SADE ATT LUCKA 52 MÅSTE AVGÖRAS INNAN EN POST
FYLLS.** Lars avgjorde den, och lucka 53, 54 och 55, i skiva 42. Raden är rättad
och bär en kursiv not: den stod i just den lista Lars läser för att veta vad som
återstår, vilket är samma defekt 0.15.1 och 0.15.3 skrevs för att rätta.

**FILEN KAN NU FYLLAS.** Lucka 52, 53 och 54 är stängda, lucka 55 är öppen och
medvetet så, se `docs/beslutslogg.md` #96 till #99.

**INGET VÄRDE ÄR SATT.** Prisfilen bär fortfarande sex tomma poster, och
`config/fakta.json`:s `telefon` är fortfarande tom. Båda raderna i listan gäller
i övrigt oförändrat.

Rättad rad i fas 5 ⇒ PATCH.

### 0.15.3 — 2026-09-14

**`config/priser.json` FLYTTAS UR "Vad som ÅTERSTÅR" TILL EN FYLLD RAD.** Filen
upprättades i skiva 41 på Lars §10-beslut, tom, se `docs/beslutslogg.md` #94.

**DET ÄR EXAKT DEN DEFEKT 0.15.1 SKREVS FÖR ATT RÄTTA, UPPREPAD.** Den posten
rättade samma sak för `config/fakta.json` och skrev ut att raden annars är känt
falsk i den lista Lars läser för att veta vad som återstår. Skiva 41 skapade
prisfilen och rörde inte roadmapen. Fällt av §7-granskningen av skiva 41,
varv 2.

**RADEN "Tills `priser.json` finns" ÄR OCKSÅ RÄTTAD.** Villkoret är inte längre
att filen finns utan att den är TOM.

**LUCKA 52 ÄR UTSKRIVEN PÅ RADEN.** Systempromptens regel 5 förbjuder varje pris
utan förbehåll och är bunden ordagrant, alltså måste den avgöras innan en post
fylls. Den som läser listan för att veta vad som återstår ska se det där.

Rättade påståenden ⇒ PATCH.

### 0.15.2 — 2026-09-11

**Samma rad blev falsk igen, av nästa skiva.** 0.15.1 rättade att fas 5:s
ÅTERSTÅR-lista sade att `config/fakta.json` var kvar att upprätta. Skiva 37
flyttade bokningsbeskedet dit på Lars §10-beslut, och då blev den rättade
lydelsen, *"finns men är TOM"*, i sin tur falsk.

**Filen bär nu posten `bokningar`. `telefon` är fortfarande tom.** Raden skiljer
de två, eftersom skillnaden är hela poängen: ett tomt värde når aldrig prompten.

*Att raden faller två skivor i rad är värt att notera. En ÅTERSTÅR-lista som
beskriver en fils INNEHÅLL föråldras av varje ändring i filen. Att i stället
peka på `docs/beslutslogg.md` och låta posten där bära innehållet vore
stabilare, men det är en omskrivning av fasen och inte en rättelse.*

Rättat påstående ⇒ PATCH.

### 0.15.1 — 2026-09-10

**Fas 5:s ÅTERSTÅR-lista sade att `config/fakta.json` var kvar att upprätta.**
Filen skapades i skiva 36 på Lars order, se `docs/beslutslogg.md` #74, alltså var
raden känt falsk i den lista Lars läser för att veta vad som återstår.

Raden är delad: `config/priser.json` återstår, `config/fakta.json` finns men är
TOM. Skillnaden är hela poängen, eftersom ett tomt värde aldrig når prompten.

**Fasbeskrivningen och grindregeln är oförändrade.** Att filerna UPPRÄTTAS i
fasen är fortfarande sant, och att varje ändring i dem är ett §10-stopp gäller
oförändrat.

Rättat påstående ⇒ PATCH.

### 0.15.0 — 2026-09-10

**Fas 6 bär nu vad som ÄR byggt och vad som återstår.** Skiva 34 kopplade kedjan
och byggde beslutsloggen, alltså finns fasens underlag före fasen. Det som
saknas är hämtningen av inkommande mail och en slinga över dem.

**Raden om `vyn-har-ingen-sandvag` är ny och viktig:** kopplingen till
`src/mine.py` drar in `googleapiclient` och blir det första steget som inte kan
ligga under den spärren. Var gränsen ska gå skrivs ut som ett eget beslut i
stället för att avgöras i förbigående.

Ändrad fastext ⇒ MINOR.

### 0.14.0 — 2026-09-04

**Fas 5 bär nu vad som ÄR byggt och vad som återstår.** Generatorn finns sedan
skiva 31, med tre registrerade spärrar. `config/priser.json` och
`config/fakta.json` återstår och är §10-stopp.

**En avvikelse från fasens ordalydelse står utskriven:** rösten kommer ur
`data/par.jsonl` som FÅ-EXEMPEL och inte som mallar att fylla i. Fasen sade
"mallar"; generatorn bygger inga. Skälet står i fasen.

Ändrad fas ⇒ MINOR.

### 0.13.1 — 2026-09-04

Rättelse efter §7-granskningen av skiva 27, varv 1.

**Raden om granskningsläget angav det svagare av två skäl.** Den sade att läget
inte har något att visa eftersom generatorn hör till fas 5. Det stämmer, men det
grundläggande är att `rendera_granskning` och `spara_omdome` inte har någon
anropare alls: ingen rutt når dem. Båda skälen står nu, med skillnaden mellan
dem utskriven.

Rättat påstående ⇒ PATCH.

### 0.13.0 — 2026-09-04

**Fas 5.5:s öppna punkt om den spärrfällda posten är STÄNGD och ersatt av ett
bindande krav.** Beslut av Lars, `docs/beslutslogg.md` #40: en spärrfälld post
visar aldrig ett textfält, oavsett läge, och behövs en referens för den
kategorin tas en annan post. Punkten stod utskriven i 0.12.0 som något som skulle
avgöras innan fasen byggdes, och den avgjordes innan fasen byggdes.

**Fas 5.5 bär nu ett stycke om vad som FAKTISKT är byggt**, alltså att skiva 27
byggde vyn lokalt på `127.0.0.1`, utan inloggning och utan Railway, och att
hosting enligt #38 och inloggning enligt #37 är en egen skiva som inte är gjord.
Skälet att skriva in det är att fasen annars läses som byggd i sin helhet nästa
gång någon slår upp den.

**Granskningsläget renderar men har inget att visa**, eftersom generatorn hör
till fas 5. Det står i fasen och inte bara i koden, så att nästa läsare inte tror
att omdömesflödet är taget i drift.

Öppen punkt stängd och nya rader i en fas ⇒ MINOR.

### 0.12.0 — 2026-09-04

**FAS 5.5 STÅR NU FÖRE FAS 5.** Beslut av Lars, `docs/beslutslogg.md` #39.
Avsnitten är fysiskt flyttade, inte omnumrerade: numren är korsreferenser i tre
andra dokument, och en omnumrering hade gjort varje sådan hänvisning fel. En rad
överst i `## Faser` säger nu att numren är identiteter och ordningen
utförandeordning.

**FAS 5.5 FÅR TRE BINDANDE KRAV.**

- Vyn ska kunna visa ett inkommande mail UTAN ett botgenererat förslag. Det är
  ett krav fasen inte var specad för, och utan det finns ingenting att skriva
  innan mallarna finns.
- Ett referenssvar SKICKAS ALDRIG. Det sparas som ett par i `data/par.jsonl`, och
  knappen måste vara omöjlig att förväxla med en skicka-knapp.
- `token.json` och `data/` ligger på ett PERSISTENT VOLUME, aldrig i containern,
  enligt #38. Kravet står i fasen och inte bara i beslutsloggen därför att det
  ska läsas innan fasen byggs.

**FAS 5:S FÖRSTA MENING ÄR ÄNDRAD.** Mallarna byggs ur `data/par.jsonl` OCH ur
referenssvaren Lars skriver i vyn. Före den här posten namngav fasen bara filen.

**Fas 5.5:s inloggnings- och hostingrader pekar om.** Inloggning enligt #37 i
stället för #21, som är stängd, och hosting enligt #20 och #38. Fasens första
mening bär nu också att kontot är DELAT, alltså att loggen inte skiljer Lars från
Matte.

**EN ÖPPEN PUNKT ÄR TILLAGD.** Vad som gäller för en spärrfälld post när vyn
också ska kunna bära ett tomt fält är inte avgjort. Fälld av granskningen av
skiva 26 som ett hål i en fas som får full §7.

Flyttad fas, tre bindande krav och en öppen punkt ⇒ MINOR.

### 0.11.0 — 2026-09-02

**Fas 4.5:s grindrad bär nu #31 och en ruta om att grinden är passerad.** Nytt
innehåll i ett grindvillkor ⇒ MINOR.

Datakällan är avgjord i #31, den öppna fordonssidan. Avtalsledet avgjorde Lars
samma dag genom att stryka det: källans användarvillkor läses inte. **Båda leden är
alltså avgjorda och grinden är passerad**, och rutan skriver ut att villkoren därmed
är olästa och att risken är accepterad utan att vara bedömd.

*Rutan bar först lydelsen att avtalsledet var bortdefinierat och att ett led
återstod. Det står inte kvar. Se #31:s avsnitt AVGJORT AV LARS.*

Rutan säger också uttryckligen att en byggd och prövad `src/biluppgifter.py`
inte passerar grinden. Skälet är att fasens egen rad redan varnar för samma
förväxling i testnyckelns form, och den nya källan har ingen nyckel att peka på.

### 0.10.0 — 2026-08-28

**Grindvillkoret "Ingen kategori startar i `auto`" är STRUKET**, på Lars beslut i
skiva 18, se `docs/beslutslogg.md` #30. Skiva 17 lät meningen stå kvar med en
not; Lars avgör att en förhandsgissning som visat sig fel inte ska stå kvar i ett
grindvillkor, eftersom nästa läsare tar den för ett krav.

En kursiv not står där meningen stod, med härkomsten verifierad via `git log -S`.

**Raden om `docs/kategorier.md` är struken ur fasen.** Filen behövs inte, se #30.
Fas 4:s leverabler är därmed `config/kategorier.yaml` och
`scripts/kategoristatus.py`, och båda finns.

Struket grindvillkor ⇒ MINOR.

### 0.9.0 — 2026-08-28

**Fas 4:s grind är fattad**, se `docs/beslutslogg.md` #29. En not under fasen
säger vad som finns och vad som inte gör det: `config/kategorier.yaml` finns,
`docs/kategorier.md` och `scripts/kategoristatus.py` gör det inte, och fasen är
därmed inte avslutad.

**Grindvillkoret "Ingen kategori startar i `auto`" höll inte.** Lars beslut lägger
`fråga om a-traktorkonvertering` direkt i `auto`. Villkoret var en förväntan
skriven i skiva 3, innan något underlag fanns, och det var aldrig en
ramverksregel: ramverksregel 2 förbjuder att KOD flyttar en kategori till `auto`
och kräver Lars uttryckliga beslut, vilket är exakt vad som skedde.

Meningen står kvar oförändrad, eftersom den var sann som förväntan när den
skrevs. Noten säger att den inte längre beskriver läget.

*Föråldrad av 0.10.0. Meningen är STRUKEN på Lars beslut i skiva 18, och samma
post gjorde också det som stod högre upp här falskt: `docs/kategorier.md` behövs
inte och `scripts/kategoristatus.py` finns. Båda leden gällde när posten skrevs.*

Ändrat grindläge ⇒ MINOR.

### 0.8.0 — 2026-08-28

**Fas 4.5 får en FÖRESKRIFT: avläsaren ska vara skiftlägesokänslig.** Beslut av
Lars i skiva 16, se `docs/beslutslogg.md` #28 och luckan
`versalkansligt-monster-i-avlasare` i `docs/sparrar.md`.

Skiva 15 mätte upp skillnaden men skrev bara ut den. Mätningen band ingen kod:
en avläsare som lånar mönstret ur `scripts/persondatakontroll.py` utan
`re.IGNORECASE` tappar 31 av de 77 nummer som går att läsa. Föreskriften säger nu
vad avläsaren ska göra, och varför det är en sändvägsdefekt och inte en formfråga.

**Meningen om att avläsaren ska leta efter FÄLTET är rättad.** Den stod kvar
oannoterad medan avsnittet längre ned upphävde just den betydelsen: att fältet
finns är inte samma sak som att ett värde gick att läsa. Motsatsställningen mot
huvudet och avsändaren är oförändrad, men villkoret gäller VÄRDET. Skiva 15
rättade `Följden för fasen` längre ned i fasen men rörde inte den här meningen,
vilket syns på att dess stycke ligger utanför den commitens hunkar, och Lars
avgjorde i skiva 16 att den skulle rättas.

**Rättelse efter §7-granskningen.** Posten sade först vad granskningen av skiva
15 bedömde om den meningen. Granskningsrapporterna ligger i den gitignorerade
`scratchpad/` och går inte att belägga ur repot, så påståendet är ersatt av det
som syns i historiken: meningen lämnades orörd medan grannmeningarna rättades.

**En mening ur skiva 15 är struken i skiftlägesstycket.** Den sade att kunden
alltså inte skriver sitt nummer versalt, vilket motsägs av talet i meningen före
den: 46 av 78 matchar det versalkänsliga mönstret. Fälld i granskningen av skiva
16, och struken med en kursiv not där den stod.

Ny föreskrift ⇒ MINOR.

### 0.7.0 — 2026-08-28

**Fas 4.5 får ett avsnitt om webbformuläret**, uppmätt i skiva 15. Formulärets
fältblock med etiketternas täckning, att fältnamnet är `Registreringsnummer`
utskrivet i sin helhet, och att fältet bärs av 78 av 78 medan ett giltigt värde
går att läsa i 77 av 78. Den skillnaden är fasens utkastfall, och en avläsare som
prövar om ETIKETTEN finns svarar fel på den tråden.

**`FÖLJDEN FÖR FASEN` BAR PRECIS DEN AVLÄSAREN, och lydelsen är upphävd.** Den
sade att numret används om etikettformen finns i tråden. Mätningen ovan
falsifierar det. Villkoret gäller nu att ett giltigt värde gick att läsa, och en
kursiv not står kvar där den gamla lydelsen stod.

Ämnesraden bär samma nummer i alla 77 och säger aldrig emot kroppen, men 8
ämnesrader bland de besvarade och 23 bland de obesvarade matchar samma mönster
utan att vara formulärtrådar. Ämnesraden skrivs därför in som bekräftande signal
och aldrig som ensam grund, vilket är Lars etikettregel i `docs/sparrar.md`
tillämpad på en annan signal.

**Mönstret står utskrivet och skiftläget är en egen mätning.** Prövat
versalkänsligt, alltså som §6-kontrollen använder det, faller talet från 77 till
46 av 78. `scripts/formular-matning.py` bär varje tal i avsnittet och skriver ut
båda varianterna.

**Granskningen fällde följande led i det här avsnittet.** Bortfallet
beskrevs som "nästan var tredje nummer" där mätvärdet är 31 av 77, alltså mer än
var tredje. Talet 77 tillskrevs "ett giltigt värde" medan skriptet sökte mönstret
i hela kroppen; skriptet mäter nu VÄRDET på fältraden och ger samma 77. Och
`Följden för fasen` återanvände ordet FÄLTET i den betydelse den kursiva noten
just upphävt, och säger nu VÄRDET i fältet.

Avsnittet skriver också ut att formuläret INTE löser gatingen: inget av dess fält
är någon av de tre `src/fordonsuppslag.py` utvärderar. Och att ämnesraden bär
registreringsnumret i klartext, alltså att en rapport som citerar ämnesrader ur
materialet läcker persondata enligt §6.

Nytt avsnitt ⇒ MINOR.

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
