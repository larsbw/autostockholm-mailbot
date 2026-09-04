# Beslutslogg

**Version:** 0.33.0 · **Uppdaterad:** 2026-09-04 · **Implementerar** CLAUDE.md §8

Sekventiell och append-only. Nummer återanvänds aldrig. En post rättas genom en
ny post som upphäver den, aldrig genom att den gamla skrivs om.

Append-only binder från och med den commit som inför posten. Redigering av en
post som ännu inte committats är utkastarbete och kräver ingen rättelsepost.

**Undantag: känt falskt påstående stryks på plats.** Upptäcks att en committad
post påstår något som är falskt, stryks falskheten i posten och strykningen
redovisas i en ny versionspost. Allt annat rättas genom tillägg. Skälet är att
§7 slår fast att inget känt falskt påstående får skeppas, och den regeln går
före append-only. Utan undantaget skulle en falsk mening bli permanent så snart
den committats, och rättelseposten hade bara lagt en sann mening bredvid den.

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

## #4 — #3:s verifieringsanvisning upphävs

**Datum:** 2026-08-26 · **Berör:** `docs/beslutslogg.md` #3

**Vad som upphävs.** #3:s sista stycke ber läsaren köra
`grep -rn "5 mail" CLAUDE.md docs` och skilja på "tre sorters träff", varav den
första är §10:s egen rad. **Den sorten finns inte i utdatan.** §10:s rad bär
sedan CLAUDE.md 0.3.0 talet 1, så mönstret `5 mail` matchar den inte alls.
Anvisningen beskriver en träff som kommandot inte producerar, och dess undantag
för självreferenser täcker inte förekomsten i dokumentets egen appendixpost.

**Vad som gäller i stället.** Den föråldrade meningen är den i post #1 som lyder
"i samma anda som §10:s gräns på 5 mail per körning". Den citeras i stället för
att pekas ut med radnummer, eftersom ett radnummer förskjuts av varje tillägg
ovanför sig och redan hunnit bli fel en gång. Den är den enda förekomst i repot som
påstår något falskt om nuläget. Övriga förekomster av strängen är antingen
daterad historik i `CLAUDE.md`:s appendix, eller citat inne i #3, #4 och
versionshistoriken, som alla refererar felet i stället för att göra det.

**#3 skrivs inte om**, eftersom regeln i huvudet förbjuder det för en committad
post. Läs #3:s sista stycke som upphävt av den här posten.

**Varför felet uppstod.** #3:s anvisning ersatte en räkning med en
kategorisering ("tre sorters träff"). Båda formerna beskriver textens egen
omgivning, och båda blir falska när omgivningen växer, vilket den gör av just den
commit som skriver dem. Regeln står i CLAUDE.md:s appendixpost 0.3.1: namnge fil
och rad, räkna och kategorisera aldrig sin egen omgivning.

---

## #5 — `SENT` betyder inte "mänskligt skrivet svar"

**Datum:** 2026-08-26 · **Berör:** kommande `src/extract.py`, `src/mine.py`:s fråga

**Beslut.** `extract.py` får INTE likställa etiketten `SENT` med ett svar skrivet
av Matte eller Lars. Urvalet måste dessutom kräva frånvaro av leveranshuvuden,
eller motsvarande signal, innan ett meddelande får bli höger sida i ett par.

**Underlag.** Uppmätt i provkörningen 2026-08-26, `--max-threads 50`, redovisad i
`docs/mining-log.md`. Frågan `in:sent` fångar tre sorters `SENT`-meddelande:

- **Svar skrivna i Gmail.** Bär `In-Reply-To` och `References`, saknar
  `Received`, `Delivered-To` och `Return-Path`. Detta är de enda som hör hemma i
  `data/par.jsonl` enligt §11.
- **Formulärnotiser.** `From` är Auto Stockholm, `To` är brevlådan själv,
  `Reply-To` är kunden. De bär `SENT` men också hela leveranskedjan med
  `Received` och `Received-SPF`, eftersom de passerat inkommande leverans. De är
  maskinskrivna och skulle förgifta mallarna.
- **Vidarebefordringar till brevlådan själv.** `SENT` med svarsprefix `Fwd:` och
  `To` lika med brevlådan. Mänskligt skrivna, men inte svar till en kund.

**Konsekvens för utbytet.** Av femtio trådar bär trettiotvå enbart
`SENT`-meddelanden, och tjugonio trådar innehåller ett enda meddelande. De bär
alltså ingen kundtext att para ihop med. Antalet användbara par blir väsentligt
lägre än antalet trådar, och det ska inte komma som en överraskning i fas 4.

**Alternativ som valdes bort.** Att snäva Gmail-frågan i `src/mine.py` i stället
för att filtrera i `extract.py`. Miningen ska hämta brett en gång och
`data/tradar.jsonl` ska bära allt; ett urvalsfel i frågan kostar en ny körning
mot brevlådan, medan ett urvalsfel i extraktionen bara kostar en ny körning mot
disk.

---

## #6 — Trådstrukturens kantfall som `extract.py` måste bära

**Datum:** 2026-08-26 · **Berör:** kommande `src/extract.py`

**Beslut.** Följande är uppmätt i provkörningen och får inte antas bort. Varje
punkt har fällt en naiv implementation någon gång, och de står här därför att en
gitignorerad rapport inte är en källa nästa skiva kan läsa.

- **`labelIds` saknas som nyckel.** Äldre meddelanden har den inte alls. Läs med
  `.get`, aldrig med indexering.
- **`text/plain` finns inte alltid.** Ett meddelande kan ha `multipart/mixed` med
  bara `text/html` och en bilaga. En extraktor som kräver `text/plain` får tom
  brödtext.
- **`payload.parts` finns inte alltid.** Enkla meddelanden har brödtexten direkt
  i `payload.body.data` med `payload.mimeType` satt till `text/plain`. En
  rekursiv vandring över `parts` hittar då ingenting.
- **Huvudnamn är inte unika.** `Return-Path` förekommer dubblerat. En uppslagning
  som tar första träffen väljer godtyckligt.
- **Huvudnamnens skiftläge varierar mellan avsändare.** `Message-Id` mot
  `Message-ID`, och gemena `authentication-results` vid sidan av versala. Alla
  jämförelser ska vara skiftlägesokänsliga.
- **Bilaga kan inte definieras som "har filnamn".** Inline-bilder bär
  `attachmentId` utan `filename`.
- **Ämnesraden kan vara tom.** Nollfallet enligt §4.
- **Bilagornas bytes följer inte med.** Textdelar har `body.data`, bilagor har
  bara `attachmentId` och `size`. Vill vi ha innehållet kostar det ett
  `messages.attachments.get` per bilaga.

---

## #7 — Underlaget för mallarna, första mätningen

> **UPPHÄVD I SIN HELHET AV #8.** Talen nedan mättes med ett urval som räknade
> vidarebefordringar som svar och uteslöt formulärnotisen som kundsida. Läs #8.
> Posten står kvar oförändrad utom där den påstod något falskt, enligt regeln i
> huvudet.

**Datum:** 2026-08-26 · **Berör:** fas 4 och fas 5 i `docs/roadmap.md`

**Vad som mättes.** Full mining kördes 2026-08-26, loggad i `docs/mining-log.md`.
Frågan `in:sent` gav 555 trådar och 1120 meddelanden, varav 725 bär `SENT`.

*Rättelse i #8: här stod "Hela brevlådan gav", både i rubriken och i brödtexten.
555 är trådar med minst ett skickat meddelande, inte brevlådan. Trådar som aldrig
besvarats ingår inte.*

**Underlaget, mätt med kriterierna i #5.** Antalet trådar som bär minst ett svar
skrivet i Gmail är **265**. De innehåller 369 sådana svar. Av dessa trådar har
**234** också ett kundmeddelande att para ihop svaret med.

**Vad talet betyder.** 234 är underlaget mallarna ska byggas ur enligt §11.

*Rättelse i #8: här stod att 234 är "taket för antalet par" och att det "är
tillräckligt för att fasen ska kunna genomföras". Det första är falskt: det finns
par ovanför 234, eftersom kundsidan kunde vara en formulärnotis som bär `SENT`.
Det andra är en värdering utan namngiven tröskel. Båda strukna.*

**Vad talet inte betyder.** Det är inte 234 användbara par. Ett svar kan vara en
rad som hänvisar vidare, och en tråd kan handla om något som inte hör till någon
kategori. Gallringen sker i fas 4 och kommer att sänka talet.

**Varför 290 trådar faller bort.** De bär `SENT` men inget skrivet svar.

*Rättelse i #8: här stod "alltså formulärnotiser och vidarebefordringar enligt
#5". Det är inte mätt och det är falskt: hinken innehåller också första utgående
mail utan förlaga, en kategori #5 inte nämner. Koden vet bara att villkoren inte
uppfylldes, inte varför.*

**Nytt kantfall utöver #6.** Materialet bär `multipart/report`, alltså
leveransrapporter och studsar. De ska inte bli par.

---

## #8 — Underlaget för mallarna, rättat urval

**Datum:** 2026-08-26 · **Berör:** fas 4 och fas 5 · **Upphäver:** #7

**Talet.** Antalet trådar som bär både ett svar skrivet i Gmail och kundtext att
para ihop det med är **136**. De innehåller 238 sådana svar, fördelade över 139
trådar; av dem saknar tre kundtext.

Mätt över `in:sent`-urvalets 555 trådar, alltså inte över hela brevlådan.

**Vad som var fel i #7.** Två fel i urvalet, som drog åt varsitt håll och därför
inte tog ut varandra.

- **Vidarebefordringar räknades som svar.** En vidarebefordran bär `In-Reply-To`
  och `References` precis som ett svar och saknar leveranshuvuden. Huvudena
  skiljer dem inte åt. #5 utesluter kategorin uttryckligen, men #7:s urval
  saknade villkoret. Detta drog talet UPP.
- **Formulärnotisen uteslöts som kundsida.** #7 krävde ett meddelande utan
  `SENT` för att tråden skulle räknas som parbar. Men formulärnotisen bär
  kundens ärende och har kunden i `Reply-To`, och den bär `SENT` eftersom den
  passerat brevlådan. En tråd med notis plus skrivet svar är ett fullgott par
  och räknades inte. Detta drog talet NER.

**Urvalet nu, som villkor.** Ett meddelande är ett svar när det bär `SENT`, sak-
nar leveranshuvuden, bär både `In-Reply-To` och `References`, inte är
`multipart/report`, har minst en mottagare utanför brevlådan, och inte bär ett
vidarebefordringsprefix i ämnesraden.

Ett meddelande är kundtext när det saknar `SENT`, eller när det bär `SENT` men
har leveranshuvuden, alltså har kommit utifrån.

**Känd begränsning.** Vidarebefordran skiljs från svar på ämnesradens prefix,
eftersom huvudena inte skiljer dem. Villkoret täcker svenska och engelska
prefix, och bara det YTTERSTA prefixet avgör: `Fwd: X` är en vidarebefordran vi
skickat, medan `Re: Fwd: X` är ett svar på något som vidarebefordrats till oss.
Ett vidarebefordrat mail utan prefix räknas som svar. Begränsningen är känd och
inte förbisedd.

**En andra känd begränsning.** Villkoret som utesluter leveranshuvuden utesluter
också ett svar som lämnats in via SMTP-klient, till exempel från en mobil, om den
sparade kopian bär `Received`. Effekten är inte uppmätt över filen.

**Vad talet inte är.** Det är inte 136 användbara par. Gallringen i fas 4 kommer
att sänka det. Om 136 är tillräckligt är Lars bedömning, inte kodens.

---

## #9 — De obesvarade är tre gånger fler, och mestadels inte kundärenden

**Datum:** 2026-08-26 · **Berör:** fas 4 · **Uppmätt i:** skiva 6

**Vad som mättes.** En andra mining hämtade trådar med inkommande men utan
utgående meddelande. Gmail har ingen operator för det: `q` matchar meddelanden,
och `threads.list` returnerar varje tråd med minst ett matchande meddelande.
Frågan besvarades med mängddifferens, `-in:sent` minus tråd-ID i
`data/tradar.jsonl`. Utfall: 1604 trådar, loggat i `docs/mining-log.md`.

**De obesvarade är tre gånger fler än de besvarade**, 1604 mot 555. En
klassificerare tränad enbart på besvarade trådar hade varit blind för
huvuddelen av inflödet.

*Upphävt av #27 i den del som gäller BESVARAT. Talen 1604 och 555 är riktiga om
FILERNA, men filen säger inget om huruvida någon svarat: uppdelningen gjordes med
`in:sent`, alltså på en Gmail-etikett som ensam grund. Mätt på ett svar i tråden
bär 139 trådar ett mänskligt svar och 2020 gör det inte. Rubrikens förhållande
gäller alltså skördarnas storlek och inte besvarat mot obesvarat. Slutsatsen i
stycket står kvar och blir starkare: skevheten är större än posten trodde.*

**MEN DE ÄR MESTADELS INTE KUNDÄRENDEN.** Efter att massutskick sållats bort på
`List-Unsubscribe`, `Precedence` och besläktade huvuden återstår omkring tusen
dokument, och de största klustren bär noll svar. Filtret fångar det som
deklarerar sig som massutskick. Det fångar inte ett personligt skrivet
leverantörsmail.

*Rättelse: här stod att de största grupperna är "auktionssajter, lösenordsmail,
fakturor, molnlagring och leverantörsutskick". Den uppräkningen motsägs av
tabellen den vilar på: lösenords-, faktura- och molnlagringsklustren är bland de
minsta, inte de största. Klassificeringen var inte mätt, den var läst ur minnet
av vad jag sett när jag bläddrade. Talet 1073 gällde dessutom en tidigare körning
och ändrades av senare rättelser i maskeringen; se `docs/kategorier-forslag.md`,
som är maskinproducerad och alltid aktuell.*

**Konsekvens för fas 4.** Kategorilistan kan inte läsas rakt av ur klustringen.
Den obesvarade populationen behöver en mänsklig genomgång av ett urval innan
kategorierna sätts, och en kategori som bara finns bland obesvarade mail har per
definition inget svar att bygga mall ur.

---

## #10 — Underlaget per kategori, och a-traktor

**Datum:** 2026-08-26 · **Berör:** fas 4 och fas 5

**Talen.** Termsökning över båda källorna, mätt med `src/cluster.py --sok`:

| Term | Kundärenden med svar | Utan svar | Median svarslängd |
| --- | --- | --- | --- |
| a-traktor och stavningsvarianter | 33 | 4 | 466 tecken |
| besiktning | 9 | 21 | 230 tecken |
| service eller reparation | 21 | 371 | 241 tecken |

*Rättelse: tabellen bar först 36 för a-traktor. Det talet räknade SVARSINSTANSER,
och samma kundmeddelande kan ha besvarats två gånger. Efter avdubblering på
kundtexten är talet 33 unika kundärenden, som tillsammans bär 36 svar. Se #11.*

**A-traktor har 33 kundärenden med svar**, mätt med termsträngen
`a-traktor,atraktor,a traktor,epatraktor,epa-traktor`. Det är materialets
största kategori räknat i par.

*Rättelse: här stod att kategorin är "stor nog att bygga mallar ur" och att
"det är kärnverksamheten, och det syns i att den får svar". Det första är en
värdering utan namngiven tröskel, alltså samma fel som #7 ströks för. Det andra
är ett kausalt påstående utan underlag: att a-traktorärenden kommer in via
webbformuläret, som alltid besvaras, förklarar kvoten lika bra. Båda strukna.
Om 36 räcker är Lars bedömning.*

**Talen 36 och 4 är inte mätta på samma population.** Vänsterledet är par ur
`data/par.jsonl`, alltså svarsinstanser. Högerledet är en tråd per rad ur
`data/tradar_obesvarade.jsonl`, och den sidan är dessutom massutskicksfiltrerad
medan parsidan inte är det. Kvoten 36:4 ska därför inte läsas som en
svarsfrekvens.

**Besiktning har 9 par och 21 obesvarade.** För få par för en mall, och en
övervikt av obesvarade som bör förstås innan kategorin sätts.

**Service och reparation ser stort ut och är det inte.** 371 obesvarade mot 21
par. Termerna förekommer i leverantörsutskick och marknadsföring, så talet är
uppblåst av material som inte är kundärenden. Se #9.

**Varför termsökning och inte bara klustring.** En klustring garanterar inte att
en kategori man VET finns hamnar i ett eget kluster: den kan spridas över flera
kluster eller drunkna bland större. Termsökningen är ett oberoende mått som inte
beror på tröskeln, och den ersätter inte klustringen utan kompletterar den.

**Ingen hinktilldelning föreslås.** Fas 4:s grind är Lars beslut, och
ramverksregel 2 säger att ingen kategori flyttas av kod.

---

## #11 — `data/par.jsonl` räknar svarsinstanser, inte kundärenden

**Datum:** 2026-08-26 · **Berör:** `src/extract.py`, `src/cluster.py`, fas 5

**Vad som gäller.** En rad i `data/par.jsonl` är ett SVAR med sitt föregående
kundmeddelande. Har vi svarat två gånger på samma kundmail blir det två rader
med IDENTISK `inkommande_text`. Båda paren är äkta och båda hör hemma i
mallunderlaget: de är två faktiska svar Matte eller Lars skrivit.

**Men de får inte räknas som två ärenden.** Filen bär 226 rader och de motsvarar
217 unika kundtexter. Ett tal som ska beskriva hur många ÄRENDEN vi har underlag
för ska räkna kundtexter; ett tal som ska beskriva hur många SVAR vi kan lära av
ska räkna rader.

**Konsekvens för klustringen.** `src/cluster.py` avdubblerar på kundtexten innan
den klustrar, och tar medianen av svarslängderna när ett ärende har flera svar.
Utan det blåstes ett kluster upp av samma text i flera exemplar, vilket syntes
direkt i en tidigare version av `docs/kategorier-forslag.md`, där samma citat
stod tre gånger i ett kluster om fyra.

**Vad som INTE ändras.** `src/extract.py` fortsätter skriva ett par per svar.
Att slå ihop dem i extraktionen vore att kasta ett äkta svar.

---

## #12 — Maskinmail skiljs från mänskligt på huvuden, med ett undantag

**Datum:** 2026-08-26 · **Berör:** `src/klassa_maskin.py`, fas 4

**Beslut.** Ett meddelande klassas som maskinmail på HUVUDEN och avsändarform,
aldrig på innehåll. Ett nyhetsbrev och ett kundmail kan använda samma ord; det
som skiljer dem är att utskicket självt deklarerar vad det är.

**Undantaget, och det är det viktigaste i posten.** Post som är maskinSKICKAD
men människoSKRIVEN klassas som mänsklig. Webbformulärets notis är fallet: den
bär `X-Msg-EID` och ibland `List-Unsubscribe`, men innehållet är kundens ärende
och `Reply-To` pekar på kunden. **Uppmätt: 288 av 555 besvarade trådar föll som
maskinmail innan undantaget fanns, mot 200 efteråt.**

**Domänlistan härleds, den skrivs inte.** `config/maskindomaner.yaml` fylls av
`--harled-domaner`, som tar domäner där ALL post redan är klassad som maskinmail
på huvuden. En domän som också skickat ett odeklarerat mail lämnas utanför: den
kan bära både utskick och en människa. Listan bär bara domäner, aldrig
lokaldelar, eftersom en lokaldel kan vara persondata.

**Utfall över båda skördarna:**

| Skörd | Maskinmail | Mänskliga | Utan kundmeddelande |
| --- | --- | --- | --- |
| besvarade | 200 | 211 | 144 |
| obesvarade | 1295 | 309 | 0 |

Det mänskliga materialet är alltså 520 trådar av 2159.

---

## #13 — `data/par.jsonl` är RÅ, och ska förbli det

**Datum:** 2026-08-26 · **Berör:** `src/extract.py`, fas 5

**Beslut.** Texterna i `data/par.jsonl` är omaskerade. `src/extract.py` anropar
`urval.brodtext`, som inte maskerar, och det är avsiktligt.

**Skälet.** §11 säger att mallarna byggs ur faktiska svar, alltså ur rösten.
Maskeringen i `src/maskera.py` är avsiktligt trubbig och maskerar varje versalt
ord som inte står i undantagslistan. På ett faktiskt par blir `Är` och `För` till
`[NAMN]`. En maskerad fil hade varit oanvändbar som mallunderlag.

**Vad som skyddar filen i stället.** `data/` är gitignorerad, och `.gitignore`
täcker den. Filen har aldrig funnits i historiken. Maskeringen sker vid
UTSKRIFT, i `src/cluster.py --parexempel` och i exempelfilen, inte i lagringen.

**Vad som följer av det.** Filen ska behandlas som persondata: den får inte
klistras in i ett dokument, ett commitmeddelande eller en rapport. §6 gäller
den fullt ut.

---

## #14 — Domänlagret bidrar med noll och skeppas tomt

**Datum:** 2026-08-26 · **Berör:** `config/maskindomaner.yaml`, #12

**Vad som mättes.** Klassningen kördes två gånger, med 91 härledda domäner och
med noll. Utfallet var IDENTISKT: 200/211/144 för de besvarade och 1295/309/0
för de obesvarade. Skälfördelningen visar varför: varje fällning skedde på
`huvud` eller `avsändare`, aldrig på `domän`.

**Det följer av härledningen.** En domän kommer bara med i listan om huvudlagret
redan fällt ALLT från den. Lagret är därför en tautologi på den population det
härleddes ur, och dess enda verkliga effekt ligger framåt i tiden.

**Och den effekten är farlig.** Den första härledda listan innehöll
`googlemail.com`, alltså Gmails konsumentaliasdomän: varje framtida kund med en
sådan adress hade klassats som maskinmail utan att bära ett enda maskinhuvud.
Listan innehöll också flera offertförmedlare som VIDAREBEFORDRAR riktiga
kundärenden till verkstaden. Att klassa dem som maskinmail hade kastat
kundärenden.

**Beslut.** `config/maskindomaner.yaml` skeppas TOM. Härledningen skriver
kandidater till en gitignorerad fil, och varje post förs över av en människa som
känner igen avsändaren. Mekanismen finns kvar, eftersom Lars bad om den; det är
den automatiska påfyllningen som tagits bort.

**Öppen fråga till Lars.** Offertförmedlarna är den svåra delen. De skickar
maskinmail till formen men kundärenden till innehållet, och undantaget
`relayar_manniska` räddar dem inte, eftersom de inte sätter `Reply-To` till
kunden. Att avgöra vilka av dem som bär affär är verksamhetskunskap, inte kod.

---

## #15 — Ett tal i ett commitmeddelande var påhittat

**Datum:** 2026-08-26 · **Berör:** commit `b597950`, §7.2

**Vad som hände.** Commitmeddelandet i `b597950` skriver att kategoriseraren är
"testad mot en fejkad klient, 41 test". Talet motsvarar ingen avläsbar mängd i
repot: `tests/test_kategorisera.py` bar 17 test, de tre nya testfilerna
tillsammans 49, och hela sviten 185. Talet 41 kom inte ur en körning och inte ur
en fil.

**Varför det står här.** §7.2 säger att varje tal är avläst eller utelämnat, och
att det inte finns någon tredje kategori. Historiken kan inte skrivas om, så
felet redovisas här i stället, enligt §9.1:s princip att historiken ska bära vad
som faktiskt hände.

**Vad som gör felet lätt att missa.** Talet stod i en bisats om testning, i ett
meddelande vars övriga tal alla var avlästa. Det ärvde trovärdighet från sin
omgivning, vilket är precis det §7.2:s sista stycke beskriver.

---

## #16 — Förmedlade offertförfrågningar är kunder

**Datum:** 2026-08-26 · **Berör:** `config/maskindomaner-forbjudna.yaml`, #12, #14

**Beslut av Lars.** Följande domäner får ALDRIG klassas som maskinmail, oavsett
vad härledningen föreslår: `bokadirekt.se` med subdomäner, `autobutler.se`,
`hittabilverkstad.nu`, `verkstadsdeal.se` och `verkstadsoffert.se`. Undantagna
är `support.autobutler.se` och `bokadirekt-b88c555211e9.intercom-mail.com`, som
är supportkanaler. `googlemail.com` får aldrig in, eftersom det är Gmails
konsumentaliasdomän.

**Skälet, med Lars ord.** En förmedlad offertförfrågan är en kund, och en domän
som råkar skicka den maskinellt är fortfarande en kund.

**Uppmätt effekt.** Samma material, listan tom mot ifylld:

| Skörd | Maskinmail utan listan | Med listan | Räddade |
| --- | --- | --- | --- |
| besvarade | 200 | 187 | 13 |
| obesvarade | 1295 | 934 | 361 |

**374 trådar var alltså på väg att kastas.** Den mänskliga korpusen växte från
520 till 894 trådar, alltså med sjuttiotvå procent.

**Vad det säger om metoden.** Klassningen på huvuden är rätt som förval, men den
kan inte skilja maskinell FORM från maskinellt INNEHÅLL. Den skillnaden kräver
verksamhetskunskap om vilka förmedlare som bär affär, och den kunskapen finns
hos Lars och inte i materialet. Härledningen i #14 hade aldrig kunnat nå
slutsatsen: den föreslog tvärtom precis de domänerna som maskinmail.

**Domänlistan i övrigt förblir tom**, enligt #14. Den öppnas först när något
visar att den behövs.

---

## #17 — Intercom-undantaget stryks: ett undantag från ett skydd som aldrig nådde det

**Datum:** 2026-08-26 · **Berör:** `config/maskindomaner-forbjudna.yaml`, #16

**Beslut av Lars.** Undantagsposten för en Intercom-avsändare tas bort ur
`config/maskindomaner-forbjudna.yaml`. Lars formulering: posten var hans
instruktion i skiva 8 och den var fel.

**Skälet är mekaniskt.** `ar_forbjuden` jämför ORGANISATIONSDOMÄN.
`intercom-mail.com` är en annan organisationsdomän än `bokadirekt.se`, så
skyddet i `aldrig_maskin` omfattade aldrig avsändaren. Ett undantag från ett
skydd som inte gäller gör ingenting. Posten läste ut som om en kanal aktivt
undantogs, medan `ar_forbjuden` returnerade `False` för den domänen ändå.

**#16 ändras inte.** Den bär sin lydelse som den skrevs, inklusive uppräkningen
av undantagen. Den här posten upphäver den delen av #16 som räknade posten som
verksam. Filen bär numera en kommentar som säger varför ett undantag måste ha
sin organisationsdomän under `aldrig_maskin` för att betyda något.

**Ingen mätbar effekt på klassningen.** Beteendet är oförändrat, eftersom posten
aldrig hade någon. Det som ändras är att filen slutar påstå något den inte gör.

---

## #18 — Kategorierna sätts i två pass, och taxonomin är fast i det andra

**Datum:** 2026-08-26 · **Berör:** `src/ometikettera.py`,
`docs/kategorier-forslag.md`, #11

**Beslut av Lars.** Den fria etiketteringen i skiva 8 ersätts av två pass. Pass
1 konsoliderar etiketterna till en fast taxonomi i ETT anrop. Pass 2
etiketterar om varje äkta kundärende mot den listan. `inget kundärende` och
`oklart` etiketteras INTE om.

**Vad den fria omgången faktiskt mätte.** Den gav en etikett per FORMULERING,
inte per ärendetyp. `rekond` bar fjorton rader i tabellen, varav två
felstavningar modellen övertagit ur kundens text, och `a-traktor` låg utspridd
över flera etiketter. 157 äkta kategorier över 210 texter är ingen taxonomi,
det är en uppräkning.

**Varför två pass och inte en bättre prompt.** En modell som ser en text i taget
kan inte veta vilka namn de andra 794 texterna fick. Konsolideringen kräver att
hela etikettlistan är synlig samtidigt, och det är precis vad pass 1 är. Att i
stället sätta taxonomin för hand hade brutit mot #11:s princip att kategorierna
ska falla ut ur datan.

**ENUM UTAN SCHEMATVÅNG, och det är ett aktivt val.** Pass 2:s taxonomi är en
enum i den mening som räknas: svaret måste vara en medlem. Tvånget ligger i en
kontroll i `ometikettera_en` och inte i API:ts schema. Skälet är att ett
schematvång hade tryckt in en text som inte passar i närmaste FEL kategori utan
att det syntes. Taxonomin bär därför `övrigt` som uttalad utväg, och ett svar
utanför listan får etiketten `utanför listan`, räknas och redovisas. Är den
raden stor är det taxonomin som är för smal, inte texterna som är konstiga.
Det är §9.1 tillämpad på klassningen: en fälld klassning är ett stopptecken,
inte ett formuleringsproblem.

**Taxonomin skrivs till `data/taxonomi.json` mellan passen**, så att pass 2 går
att köra om utan att pass 1 körs igen och så att listan går att läsa innan de
dyra anropen görs. Etiketterna PER TEXT skrivs till `data/ometiketterade.jsonl`,
eftersom tabellen säger hur många par en kategori har men inte VILKA, och
mallbygget i fas 5 behöver de senare.

**PASS 2 ÄR INTE DETERMINISTISKT, och det är uppmätt och inte förmodat.** Samma
taxonomi och samma 210 texter kördes två gånger. A-traktorraderna, som är
skivans tyngsta utfall:

| Kategori | Körning 1 | Körning 2 |
| --- | --- | --- |
| `fråga om a-traktorkonvertering` | 27 texter, 27 par | 25 texter, 25 par |
| `fråga om pris a-traktorkonvertering` | 11 texter, 10 par | 12 texter, 11 par |
| `boka a-traktorkonvertering` | 7 texter, 7 par | 7 texter, 7 par |

Ett par texter vandrar mellan GRANNKATEGORIER, alltså mellan `fråga om X` och
`fråga om pris X`, som beskriver närliggande ärenden. Slutsatserna står still:
båda körningarna ger två kategorier över tröskeln, samma två, och a-traktor
störst med bred marginal.

**Följden för hur talen ska läsas.** Ett enskilt kategoriantal i
`docs/kategorier-forslag.md` är en avläsning och inte en konstant. Skillnader på
någon enstaka text mellan två kategorier betyder ingenting. Filen bär alltid
talen från den SENASTE körningen, och en jämförelse mot ett äldre tal ur en
rapport jämför två körningar och inte två tillstånd.

**Vad som INTE gjordes.** Temperaturen sänktes inte och ingen omröstning över
flera anrop infördes. Bägge hade kostat mer och köpt en precision som inte
behövs: tröskeln på tio par är grovkornig, och den avgörs inte av en text hit
eller dit.

---

## #19 — Cachemarkören sätts trots att den inte biter, och det står i koden

**Datum:** 2026-08-26 · **Berör:** `src/kategorisera.py`

**Beslut av Lars.** Systemprompten ska bära `cache_control`. Skälet han angav:
den är identisk i alla anrop och är största delen av varje anrop, och i drift
kör boten samma systemprompt varje gång.

**MARKÖREN BITER INTE VID DAGENS PROMPTSTORLEK, och det ska sägas rakt ut.**
Minsta cachebara prefix för `claude-sonnet-4-6` är 1024 tokens, avläst i
Anthropics dokumentation 2026-08-26. `SYSTEM` mättes samma dag till 204 tokens
med `messages.count_tokens`. Under gränsen skapas ingen cachepost, utan fel och
utan varning: `cache_creation_input_tokens` förblir 0. Det är exakt vad skiva
8:s körning redan visade, med noll i båda cachefälten över 795 anrop.

**Markören sätts ändå.** Den kostar ingenting när den inte biter, och
`Tokenatgang` läser båda cachefälten, så den dag prompten passerar gränsen syns
det i redovisningen utan att någon behöver minnas att slå på det. Vägen dit är
känd: generering av svarsmail kommer att bära mallar, priser och fakta i
systemprompten.

**Vad som INTE gjordes.** Systemprompten fylldes inte ut för att nå 1024
tokens. Det hade kostat mer än det sparat och gjort prompten sämre för att
tillfredsställa en tröskel.

---

## #20 — Boten flyttar i sin helhet till mailagent.dasher.se

**Datum:** 2026-08-27 · **Berör:** `CLAUDE.md` §0, `docs/roadmap.md`, `token.json`

**Beslut av Lars.** Boten flyttar i sin helhet till `mailagent.dasher.se`. Inte
bara utkastvyn.

**Skälet, med Lars ord.** Delad drift betyder kunddata på två platser med en synk
emellan. Att låta vyn ligga hostad medan mining och klassificering körs på Lars
maskin hade krävt att trådar, par och omdömen fanns i båda ändar, och synken hade
blivit en egen felkälla utan att lösa något.

**FÖLJDEN SOM ÄR SJÄLVA RISKFÖRFLYTTNINGEN, och den ska stå utskriven:**
`token.json` flyttar från Lars maskin till en hostad server. **Den token kan
skicka mail som info@autostockholm.se.** Scopet `gmail.send` finns i den, enligt
§0.

Före det här beslutet låg sändningsförmågan på en maskin Lars fysiskt kontrollerar.
Efter det ligger den på en server som är nåbar från internet. Det är inte en
gradskillnad i förvaring, det är en flytt av var ett intrång skulle behöva ta sig
in för att kunna skicka mail i företagets namn.

**Vad som INTE följer av beslutet.** Ingen sändning aktiveras av flytten. Tre
regler gäller oförändrat: §5:s undantag, att sändning aldrig är del av att
avsluta en uppgift; §6:s rad om att `--send` bara aktiveras av Lars explicita
val; och §10:s stopp om första sändningen i en ny miljö. En hostad
server ÄR en ny miljö, så den första skarpa sändningen därifrån kräver ett eget
beslut även om sändning redan skett från Lars maskin.

**Öppen punkt, inte avgjord här.** Hur `token.json` och `client_secret.json`
förvaras på servern, och vad som skyddar dem från att läsas av något annat som
kör där, är inte bestämt. Det avgörs innan flytten görs, inte nu.

**§0:s rad om ingen molndrift är struken** i CLAUDE.md 0.8.0. Den var aldrig
Lars beslut och blev falsk av det här.

---

## #21 — Inloggning till vyn: Google med domänlås plus committad whitelist

**Datum:** 2026-08-27 · **Berör:** `config/`, #20

> **STÄNGD AV #37.** Whitelisten byggs inte. Inloggningen sker som
> `info@autostockholm.se`, alltså ett konto på domänen, och båda de öppna
> punkterna nedan upphör: sakkonflikten mellan whitelist och Internal finns inte
> när ingen extern identitet ska släppas in, och Lars privata adress behövs
> aldrig. **Posten skrivs inte om**, den står kvar som det beslut den var och som
> det underlag #37 vilar på.

**Beslut av Lars.** Autentisering till utkastvyn sker med Sign in with Google,
med `hd=autostockholm.se`, plus en whitelist i `config/` för adresser utanför
domänen. Första posten i whitelisten är Lars privata Gmail-adress.

**Adressen står inte utskriven här.** §6 är kategorisk om att persondata aldrig
förekommer i `docs/`, och `scripts/persondatakontroll.py` fällde committen när
den stod här. Beslutet är återgivet, värdet hör hemma i whitelisten. Se den öppna
punkten nedan.

**WHITELISTEN ÄR COMMITTAD, ALDRIG EN MILJÖVARIABEL.** Beslut av Lars. En
miljövariabel går att ändra på servern utan att någon ser det i historiken, och
listan avgör vem som får läsa kundmail och fatta beslut om utgående svar. Den
hör till samma klass som `config/sparrar.yaml`: ändras den ska ändringen synas i
en diff.

**`hd` är ett filter, inte en spärr.** Parametern styr vilket konto Google
föreslår och kan sättas om av den som gör anropet. Domäntillhörigheten
verifieras på svaret, mot den `hd`-claim som kommer tillbaka, aldrig mot vad som
skickades. Detta är en implementationsföreskrift och inte ett beslut, men den
står här därför att motsatsen ser ut att fungera.

**Whitelisten prövas mot verifierad e-postadress**, inte mot namn eller
användar-ID, och adressen ska vara bekräftad av Google i svaret.

**ÖPPEN PUNKT 1, OCH DEN ÄR EN SAKKONFLIKT I INSTRUKTIONEN.** Whitelisten och
Internal går inte ihop, och den ena av dem måste ge vika.

Uppslaget i Googles dokumentation 2026-08-27: en app vars user type är
**Internal** avvisar konton utanför organisationen med felet `org_internal`
INNAN appen får se någon identitet. Ett privat Gmail-konto kan alltså inte logga
in på en Internal-app i `autostockholm.se`, och whitelisten får aldrig något att
pröva. User type sätts dessutom på PROJEKTNIVÅ, så en ny
webbklient i samma projekt ärver Internal. Att ge inloggningsklienten en egen
consent screen är alltså inte möjligt inom projektet `autostockholm-mailbot`.

Tre vägar, och valet är Lars:

1. **Lars får ett konto på `autostockholm.se`.** Whitelisten behövs inte, allt
   förblir Internal, och §0:s verifieringsargument står orört. Ingen
   OAuth-konfiguration ändras. Ett konto kostar däremot en Workspace-licens och
   läggs upp i Admin-konsolen, så vägen är inte gratis.
2. **Ett EGET GCP-projekt för inloggningsklienten**, med egen consent screen satt
   till External. Inloggningen begär bara identitetsscopes, som inte är
   restricted, så External där utlöser ingen verifiering.
   `autostockholm-mailbot` förblir Internal för Gmail-åtkomsten. Bevarar
   whitelisten, men bryter mot "samma consent screen" i #22.
3. **Hela projektet blir External.** Avvisas här: det är precis vad §0:s
   Internal-val finns för att undvika, och det skulle utlösa Googles verifiering
   av `gmail.modify` och `gmail.send`.

**Ingen av vägarna får väljas av kod.** Punkten står öppen tills Lars avgör den,
och whitelisten byggs inte innan dess.

**ÖPPEN PUNKT 2, om spärren, och den måste avgöras innan whitelisten byggs.**
`config/` står i `BEVAKADE` i `scripts/persondatakontroll.py`, så spärren kommer
att fälla committen av whitelisten på exakt samma grund som den fällde den här
posten. Två vägar finns, och valet är Lars:

1. **Adressen läggs i `TILLATNA` med skälet utskrivet**, vilket är den väg
   spärrens eget felmeddelande anvisar. Whitelisten blir då committad som
   beslutat, och undantaget syns i en diff.
2. **Whitelisten flyttas ut ur `BEVAKADE`** som filklass, med motiveringen att en
   lista över behöriga läsare per definition bär adresser.

Väg 1 är snävare och lämnar spärren orörd för allt annat under `config/`.
**Men den bär en invändning som måste stå med:** `TILLATNA` ligger i
`scripts/persondatakontroll.py`, som är spårad och pushas. Väg 1 flyttar alltså
adressen från en bevakad fil till en obevakad, utan att den slutar finnas i
repot, och §6 säger att persondata aldrig förekommer i något som pushas. Väg 1
gör undantaget synligt i en diff, vilket är dess förtjänst, men den löser inte
§6-frågan utan flyttar den.

*Upphävt av #28 i ett led. `scripts/` ligger sedan skiva 16 i `BEVAKADE`, så
`scripts/persondatakontroll.py` är inte längre en obevakad fil och väg 1 flyttar
ingenting från bevakat till obevakat. **Invändningen kvarstår av ett annat
skäl:** ett `TILLATNA`-undantag gäller exakt strängen, så adressen skulle stå
oskyddad i en spårad fil även om filen granskas. Slutsatsen står alltså kvar, att
väg 1 inte löser §6-frågan utan flyttar den, medan mekanismen är en annan. Den
öppna punkten är fortfarande öppen och väntar på Lars.*

Väg 2 har samma problem i annan form: adressen står kvar i `config/`, bara
utanför spärrens räckvidd.

**Frågan under båda vägarna är alltså om Lars privata adress över huvud taget
ska stå i repot.** Blir svaret nej faller båda vägarna, och whitelisten måste
läsas från en fil som inte committas, vilket i sin tur strider mot beslutet i
den här posten om att listan ska vara committad. Det är samma knut som ÖPPEN
PUNKT 1, och väg 1 där, ett konto på `autostockholm.se`, löser den här punkten
också: då behövs ingen adress utanför domänen alls.

**Ingen av vägarna får väljas genom att skriva om whitelisten tills spärren
släpper**, vilket är §9.1:s förbjudna åtgärd i dokumentform.

---

## #22 — Egen OAuth-klient för inloggningen, skild från mailbot-cli

**Datum:** 2026-08-27 · **Berör:** GCP-projektet `autostockholm-mailbot`, #21

**Beslut av Lars.** Inloggningen till vyn får en egen OAuth-klient av typen **Web
application**, skild från `mailbot-cli`, som är av typen desktop och sköter
Gmail-åtkomsten. Samma consent screen, som redan är Internal.

**Skälet att inte återanvända mailbot-cli.** De två klienterna gör olika saker
och bär olika risk. `mailbot-cli` bär `gmail.modify` och `gmail.send` mot
brevlådan; inloggningsklienten behöver bara veta vem besökaren är. En delad
klient hade knutit vyns redirect-URI:er till den klient som bär
sändningsscopet, och en felkonfigurerad redirect är en känd väg att fånga upp
en auktoriseringskod.

**Inloggningsklienten begär inga Gmail-scopes.** Den behöver identitet, inte
brevlådeåtkomst. Att lägga till ett scope på den är ett §10-stopp som vilket
annat nytt scope som helst.

**Consent screen förblir Internal.** Det är vad som gör att projektet slipper
Googles verifiering trots restricted scopes, enligt §0.

**MEN INTERNAL OCH WHITELISTEN I #21 GÅR INTE IHOP, och det är en sakkonflikt
och inte en formulering.** Se den öppna punkten i #21. Den här posten sa
tidigare att whitelisten "finns just för att Internal låser ut adresser utanför
domänen". Det är falskt: Internal låser ut dem så hårt att whitelisten aldrig
får se dem.

---

## #23 — Datakälla för fordonsuppslag: ägaruppgifter väljs bort aktivt

**Datum:** 2026-08-27 · **Berör:** `docs/roadmap.md` fas 4.5, CLAUDE.md §6

**Beslut av Lars.** Fordonsuppslaget i fas 4.5 ska hämta **tekniska fält utan
ägaruppgifter**. Vilken leverantör som levererar dem är inte beslutat, se den
öppna punkten nedan.

**Alternativen som övervägs**, återgivna ur Lars instruktion i skiva 11:

| Väg | Vad den ger |
| --- | --- |
| Transportstyrelsens direktåtkomst, via **Bilvision** eller **Dun & Bradstreet** | Hela vägtrafikregistret, **inklusive ägaruppgifter** |
| **Biluppgifter PRO API** | Tekniska fält, JSON mot API-nyckel, utan ägardata |
| **Fordonsfakta** | Tekniska fält, JSON mot API-nyckel, utan ägardata |

**ATT AVSTÅ ÄGARUPPGIFTER ÄR ETT AKTIVT VAL, INTE EN BEGRÄNSNING.** Boten behöver
veta vad bilen ÄR, inte vem som äger den. Direktåtkomsten ger mer data än behovet
och är enligt Lars sämre ur GDPR-synpunkt.

Valet har en förlängning i §6, som säger att kundmail bär persondata och att den
aldrig når rapporter, `docs/` eller något som pushas. **Ett uppslag mot
registreringsnumret som svarar med ägaren skulle dra in persondata i ett flöde
som i övrigt bara behöver teknik**, och den datan hade sedan funnits i varje logg
och varje felsökning på vägen. Den billigaste hanteringen av persondata är att
aldrig hämta den.

**LEVERANTÖRSUPPGIFTERNA ÄR ÅTERGIVNA, INTE VERIFIERADE.** Att de fyra
namngivna leverantörerna finns, och att de två sistnämnda levererar JSON mot
API-nyckel utan ägardata, är Lars uppgift och är inte uppslaget i den här
sessionen. Det ska prövas mot leverantörernas egen dokumentation innan avtal
tecknas.

**ÖPPEN PUNKT: leverantör är inte vald.** Priset per uppslag och avtalsformen är
inte avlästa och **skrivs därför inte**, enligt §7.2:s regel att ett tal är avläst
eller utelämnat. Lars avgör. Detta är fas 4.5:s grind, och fasen lämnas inte
förrän den är avgjord.

**Ingen leverantör får väljas av kod**, och ingen får väljas genom att en
implementation redan råkar peka på en av dem.

---

## #24 — Två fält gatar ombyggnaden

**Datum:** 2026-08-27 · **Berör:** `docs/roadmap.md` fas 4.5,
`src/fordonsuppslag.py`, `docs/sparrar.md`, #23

**Beslut av Lars.** Kravbilden för a-traktorombyggnad snävas till **två fält**:
släpvagnsvikt och draganordning. Inget annat gatar.

**Vad som UTGÅR.** Tjänstevikt, drivning, karosserikod och barlastflak. De stod i
fas 4.5 till och med skiva 11 och ingår inte längre i bedömningen. Vad uppslaget i
övrigt kan visa är merförsäljning, inte gating.

Den tidigare kravbilden var alltså felaktig, inte bara ofullständig. Det är värt
att skriva ut, eftersom skiva 11 lade granskningsarbete på att räta ut viktledets
riktning i ett krav som nu utgår helt.

*Strykning enligt undantaget i dokumentets huvud: här stod att tröskeln 1000 kg
är Auto Stockholms praxis och inte ett författningskrav, att §42 saknar tal, och
att en mall som återger 1000 som författningskrav vore en sändvägsdefekt. Postens
rubrik bar samma påstående. Allt detta är FALSKT och struket. §42 slogs upp på
Lars instruktion i samma skiva och anger talet uttryckligen. Se versionsposten
0.19.0 och `docs/roadmap.md` fas 4.5, som citerar paragrafen ordagrant.*

**TRÖSKELN 1000 KG ÄR ETT FÖRFATTNINGSKRAV.** VVFS 2003:19 4 kap 42 § punkt 2:
*"ursprungsfordonet är konstruerat för en släpvagnsvikt av minst 1 000 kg"*.
Talet bor i `src/fordonsuppslag.py` som `TROSKEL_SLAPVAGNSVIKT_KG`.

**§42 HAR TVÅ KRITERIER, FÖRENADE MED *ELLER*, OCH KODEN PRÖVAR ETT.** Ett fordon
är lämpligt som dragfordon om tjänstevikten är minst 2 000 kg ELLER om
släpvagnsvikten är minst 1 000 kg. `utvardera` prövar bara det senare.

**Ett fordon med tjänstevikt 2 100 kg och släpvagnsvikt 800 kg får därför RÖTT,
medan föreskriften säger att det duger.** Det är en sändvägsdefekt, och att rätta
den kräver tjänstevikt som ett tredje fält, alltså just det fält den här posten
stryker ur bedömningen.

**BESLUTET OM TVÅ FÄLT FATTADES PÅ ETT UNDERLAG SOM NU ÄR MOTBEVISAT.**

*Strykning enligt undantaget i dokumentets huvud, gjord i skiva 14. Här stod, i
sin helhet: att punkten är öppen och blockerande; att fasen inte får lämnas och
ingen mall skrivas innan Lars avgjort om tjänstevikt ska tillbaka; och att* ingen
kod ändras av agenten. *Allt blev falskt av #25, som förde tillbaka tjänstevikt
som tredje fält OCH ändrade `src/fordonsuppslag.py` för att göra det. Den sista
meningen är alltså inte struken för att den var överflödig, utan för att den var
lika falsk som de andra.*

*Strykningen ligger utanför skiva 14:s brief och gjordes därför att en känd
falskhet inte får skeppas (§7), och därför att den satt i presens och läses som
nuläge. Se versionsposten 0.22.0.*

Att ändra talet ändrar vilka kunder som får ett rött svar. Det är sändväg och
inte en konstant bland andra, och `test_troskeln_ar_tusen_kilo` finns för att en
ändring ska kräva ett medvetet beslut i stället för att glida igenom.

**HÄMTNINGEN LIGGER BAKOM GRÄNSSNITTET SOM EN UTBYTBAR IMPLEMENTATION.**
`slag_upp` tar en `hamta`-funktion. `manuell_hamtning` är den som finns nu:
värdena matas in för hand och modulen utvärderar.

Skälet är #23. **Datakällan är inte avgjord**, varken leverantör, pris per uppslag
eller avtalsform, och modulen ska överleva ett byte. Ett byte av källa ska vara
ett byte av EN funktion och inte en omskrivning. Den manuella hämtningen finns
dessutom för att fasen ska gå att bygga och pröva innan ett avtal existerar.

**`hamta` har inget förval.** Den som anropar väljer källa medvetet. En tyst
standardkälla i en sändvägsmodul är precis vad §10 finns för att hindra.

**REGELUTVÄRDERINGEN ÄR DETERMINISTISK KOD.** `utvardera` är boolesk logik på två
fält. Ingen modell avgör om ett fordon kan byggas om; modellen får formulera
svaret, aldrig fatta beslutet.

**BESLUT AV LARS: SKILLNADEN MELLAN GULT OCH OKLART ÄR ETT BESKED FRÅN KUNDEN.**

Briefen till skiva 12 listade båda med samma registervillkor, "släpvagnsvikt
minst 1000 och draganordning nej". En deterministisk funktion på två fält kan
inte ge två utfall för samma indata, och registret kan inte skilja en omonterad
dragkrok från en monterad men oregistrerad.

Agenten föreslog att skillnaden ligger i ett besked från kunden. **Lars antog
förslaget som beslut i skiva 12**, med hans formulering: briefen gav samma indata
två utfall, vilket en deterministisk funktion inte kan göra.

`utvardera` bär beskedet som parametern `dragkrok_bekraftad_saknas`. **Förvalet
är OKLART utan besked**, alltså en fråga till kunden och aldrig ett påstående om
att dragkrok saknas. Det förvalet står fast.

Biten bär ingen härkomst, till skillnad från fordonsfakta som måste passera
spärren. Den luckan är registrerad i `docs/sparrar.md`.

---

## #25 — Tjänstevikt tillbaka som tredje fält, och beskedet får härkomst

**Datum:** 2026-08-27 · **Berör:** `src/fordonsuppslag.py`, `docs/roadmap.md`
fas 4.5, `docs/sparrar.md`, #24

**Beslut av Lars.** Gatingen rättas mot VVFS 2003:19 4 kap 42 §.
**Tjänstevikt är tillbaka som tredje fält.**

**Lämplig som dragfordon enligt 42 § andra stycket:** tjänstevikt minst 2 000 kg
**ELLER** släpvagnsvikt minst 1 000 kg. Förenade med *eller*, inte *och*.

Gatingen är alltså **draganordning plus lämplighet enligt ovan**.

**RÖTT KRÄVER ATT BÅDA LÄMPLIGHETSVILLKOREN FALLER.** Ett fordon med tjänstevikt
2 100 kg och släpvagnsvikt 800 kg är GRÖNT eller GULT beroende på draganordning,
aldrig RÖTT.

`tests/test_fordonsuppslag.py::test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott`
finns för just det fallet. Det var defekten som låg i koden när skiva 12
skeppades, och den ska inte kunna återkomma tyst.

**OM STRYKNINGEN I #24, som det var.** Tjänstevikt ströks ur bedömningen i skiva
12. **Premissen var att §42 saknar tal. Den kom ur briefen till den skivan och
var motbevisad av föreskriftens text**, som ingen då hade läst. Strykningen var
alltså inte ett avvägt val mellan kända alternativ, utan ett beslut fattat på en
felaktig uppgift. #24 bär strykningen av det falska påståendet med kursiv not.

**Ett uppslag utan tjänstevikt är INTE ett giltigt uppslag** och faller till
utkast, samma regel som för de två andra fälten. Att gissa vikten hade varit att
fabricera underlaget för ett rött besked.

**DRAGKROKSBESKEDET FÅR HÄRKOMST.** Beslut av Lars. Fältet flyttar kunden från
OKLART, alltså en fråga, till GULT, alltså ett svar som namnger ett prispåslag.
Det fick **enbart** sättas av ett uttryckligt kundsvar eller av manuell inmatning
i utkastvyn. **Aldrig av en modell, aldrig av klassificeraren.**

Spärren är byggd: beskedet är en `DragkrokBesked` som måste namnge en källa ur
`BeskedKalla`, och uppräkningen bär ingen medlem för en modell. Vad spärren INTE
kan hindra, en anropare som medvetet anger fel källa, står utskrivet i
`docs/sparrar.md` under `dragkrokbesked-har-harkomst`.

**EN FÖRESKRIFT CITERAS ORDAGRANT, ALDRIG SAMMANFATTAD.** Regeln följer av
skivan och står i `docs/roadmap.md` fas 4.5, med incidenten i
`docs/incidentlogg.md` I6. §39 formulerades om ur minnet i två skivor i rad, och
§42 sammanfattades ur en brief utan att någon hade läst paragrafen. Den
sammanfattningen tappade ett helt kriterium och skeppade en sändvägsdefekt.

**#24 namnger `test_troskeln_ar_tusen_kilo`. Testet heter sedan skiva 13
`test_trosklarna_kommer_ur_forfattningen`**, eftersom det nu asserar båda
trösklarna. Beslutsloggen är append-only, så #24 står kvar med det gamla namnet
och den här raden är rättelsen.

**VEMS TJÄNSTEVIKT AVSER §42 PUNKT 1?** Paragrafen inleder med "A-traktor är
lämplig som dragfordon om" och punkt 1 säger "tjänstevikten", medan punkt 2
uttryckligen byter till "ursprungsfordonet". **Att paragrafen byter ord mellan två
intilliggande punkter talar för att punkt 1 avser vikten efter ombyggnaden.**

`utvardera` prövar båda mot uppslagets tjänstevikt, alltså ursprungsfordonets.

**BESLUT AV LARS: TJÄNSTEVIKTEN ÄR DENSAMMA FÖRE OCH EFTER OMBYGGNADEN.** Frågan
saknar därmed praktisk betydelse, eftersom det är samma tal oavsett vilket av
fordonen paragrafen syftar på, och `utvardera` prövar rätt storhet.

**§39:s barlastflak är den ombyggnad som skulle kunna flytta tjänstevikten**,
eftersom den tillför massa. Det är den enda kända invändningen mot beskedet, och
**beskedet gäller ändå**.

**Att invändningen ska stå utskriven och inte utelämnas är Lars instruktion i
skiva 14**, inte ett redaktionellt val. Skälet är att göra beskedets räckvidd
synlig: hittar någon ett fordon där vikterna skiljer sig är det det här beslutet
som ska omprövas, och inte en glömd detalj.

*Strykning enligt undantaget i dokumentets huvud, gjord i skiva 14 på Lars
instruktion. Här stod, i sin helhet: att punkten är BLOCKERANDE för fas 4.5 och
avgörs av besked från en besiktningsman och inte av oss; att detta var **Lars
eget beslut i skiva 13**; att frågan är hur §42 tillämpas vid en
registreringsbesiktning, vilket varken ordalydelsen eller ett resonemang i repot
kan avgöra; att antagandet om vikterna är agentens och inte belagt; att
felriktningen är densamma som skiva 12:s defekt; och att ingen kod ändras under
tiden.*

***Att det Lars beslutade i skiva 13 är det Lars vänder i skiva 14 ska synas.***
*Punkten var blockerande på hans beslut, och den är avgjord på hans besked. Se
versionsposten 0.22.0 och #26, som bär beskedet med sina skäl.*

---

## #26 — Tjänstevikten är densamma före och efter ombyggnaden, och #25:s öppna punkt är därmed avgjord

**Datum:** 2026-08-27 · **Berör:** `docs/roadmap.md` fas 4.5,
`src/fordonsuppslag.py`, #25

**Beslut av Lars.** **Tjänstevikten är densamma före och efter ombyggnaden.**

**Följden.** Frågan om §42 punkt 1 avser ursprungsfordonet eller den ombyggda
A-traktorn **saknar praktisk betydelse**, eftersom det är samma tal oavsett.
`utvardera` prövar rätt storhet, och den öppna punkten i #25 är avgjord.

**#25:s status som BLOCKERANDE upphävs här.** Fas 4.5 stannar inte längre på den
punkten.

*Rättelse i 0.22.0: här stod att posten #25 står kvar med sin ursprungliga
lydelse, enligt append-only. Det blev falskt av skiva 14, som strök de
presensformuleringar i #25 som beskedet ovan gjorde osanna. #25 står kvar
oförändrad UTOM där den påstod något falskt, enligt regeln i dokumentets huvud.*

**VAD SOM SKULLE KUNNA FLYTTA TJÄNSTEVIKTEN, och som beskedet gäller ändå.**
§39:s barlastflak är den ombyggnad som tillför massa till fordonet. Skulle någon
enskild ombyggnad kunna göra före och efter till olika tal är det den. **Lars
besked gäller ändå**, och det står här utskrivet så att nästa läsare ser att
frågan är ställd och besvarad och inte förbisedd.

Att skriva ut invändningen är inte att ifrågasätta beskedet. Det är att göra
beskedets räckvidd synlig: den som i framtiden hittar ett fordon där vikterna
skiljer sig vet då att det är det här beslutet som ska omprövas, och inte att
någon glömde tänka på barlastflaket.

**Ingen kod ändras av posten.** `ar_lamplig_som_dragfordon` prövade redan båda
kriterierna mot uppslagets tjänstevikt, och beskedet bekräftar att det är rätt.

---

## #27 — Besvarad avgörs av ett svar i tråden, aldrig av vilken fil tråden ligger i

**Datum:** 2026-08-28 · **Berör:** `docs/kategorier-forslag.md`, `src/kategorisera.py`,
`docs/sparrar.md`, fas 4:s grind, #5, **och upphäver #9 i den del som gäller
besvarat**

**Beslut av Lars.** **EN GMAIL-ETIKETT FÅR ALDRIG VARA ENDA GRUNDEN FÖR EN
KLASSNING.** Etiketter sätts för hand av Lars och Matte, retroaktivt och ojämnt.
Ett mail utan etikett är inte ett mail utan ärende. En etikett får användas som
bekräftande signal och som säker positiv träff, aldrig som nödvändigt villkor och
aldrig som ensam grund. Regeln bor i `docs/sparrar.md` under
`gmail-etikett-som-ensam-grund`.

**Följden här.** En tråd är BESVARAD om den bär ett mänskligt skrivet svar enligt
`src/urval.py::ar_gmail_svar`, och obesvarad annars. Vilken skördefil den ligger i
säger ingenting.

**#5 AVGJORDE REDAN DET HÄR, ETT PLAN NER.** #5 slår fast att `SENT` inte betyder
"mänskligt skrivet svar", och `src/extract.py` följer den. Men miningen delade
materialet med `in:sent`, alltså på samma etikett, som ensam grund för vilken FIL
en tråd hamnade i. Sammanblandningen #5 förbjöd på meddelandenivå återinfördes
alltså på filnivå av frågan som hämtade materialet.

**Ingen ny mining behövs, och det är tur snarare än förtjänst.** Den obesvarade
skörden kördes som `-in:sent` minus redan hämtade tråd-ID, så komplementet hämtades
också. Trådarna ligger på disk, i fel fil. #5:s egen varning, att ett urvalsfel i
frågan kostar en ny körning mot brevlådan, gällde alltså med nöd och näppe inte.

**Uppmätt med `scripts/besvarad-omklassning.py`:**

| Fack | Antal |
| --- | --- |
| `data/tradar.jsonl`, rader | 555 |
| varav bär ett mänskligt svar | 139 |
| varav SAKNAR svar | 416 |
| — därav utan kundmeddelande alls | 141 |
| — därav maskinmail | 183 |
| — därav **kundärenden som flyttar** | **92** |
| `data/tradar_obesvarade.jsonl`, rader | 1604 |
| varav ändå bär ett svar | 0 |

Kontrollen åt andra hållet ger noll: ingen tråd i den obesvarade filen bär ett
svar. Felet går alltså bara åt ett håll.

**#9 UPPHÄVS I DEN DEL SOM GÄLLER BESVARAT.** Dess rubrik lyder "De obesvarade är
tre gånger fler, och mestadels inte kundärenden", och dess bärande tal står i
brödtexten: "De obesvarade är tre gånger fler än de besvarade, 1604 mot 555".
Båda beskriver skördarnas storlek och inte besvarat mot obesvarat. Mätt på ett svar i tråden är
förhållandet 139 mot 2020. #9:s slutsats står kvar och blir starkare: en
klassificerare tränad enbart på den besvarade filen hade varit blind för mer av
inflödet än posten trodde. En kursiv not i #9 pekar hit.

**KOLUMNEN *MED SVAR* VAR ALDRIG FEL, och briefens premiss stämde inte.** Briefen
antog att talen 213 och a-traktorns 43 vilar på den gamla uppdelningen.
`src/kategorisera.py` rad 84–93 tar den besvarade sidan ur `data/par.jsonl`, som
byggs på `ar_gmail_svar` via `src/extract.py`, inte ur filnamnet. 213 unika
kundtexter står kvar. A-traktorns 43 är summan av *Med svar* över de tre
a-traktorkategorierna och står också kvar.

**Det är den obesvarade sidan som var underräknad.** Rad 95–109 läser bara
`tradar_obesvarade.jsonl`, så en tråd utan svar i fel fil hamnade i INGEN kolumn.
De 92 bidrar med **66 unika kundtexter som saknas i båda kolumnerna**.

| Korpus | Före | Efter |
| --- | --- | --- |
| Texter i underlaget | 795 | 861 |
| Med svar | 213 | 213 |
| Utan svar | 582 | 648 |

795 är avläst ur raden `Texter i underlaget` i `docs/kategorier-forslag.md` som
den stod när posten skrevs, och 213 ur körningen. **Den raden bär i dag 861**,
eftersom #28 lade till de 66; filen är maskinproducerad och alltid aktuell. 582
är både differensen mellan dem och ett direkt mätvärde: skriptet bygger den
obesvarade kolumnen med samma urval som `src/kategorisera.py` rad 95–109 och får
582 texter. Att de 66 saknas i BÅDA kolumnerna är också mätt, inte antaget:
överlappet mot den obesvarade kolumnen är 0.

**WEBBFORMULÄRET ÄR DEN ENSKILT STÖRSTA KANALEN BLAND DE 92**, med 32 trådar,
och 23 av de 66 nya texterna kommer därifrån. Båda talen läses ur
`scripts/besvarad-omklassning.py`, som känner igen formuläret på ÄMNESRADEN och
inte på avsändardomänen: den egna domänen bär också annan maskinell trafik. Att
domänraden i tabellen nedan också står på 32 är alltså en kontroll och inte
samma mätning.

Talet 23 räknas per unik text när texten läggs till första gången, vilket vore
ordningsberoende om samma text bars av både en formulärtråd och en annan tråd.
Skriptet mäter det: noll texter korsar den gränsen.

Formulärets ämnesrad är en offertförfrågan om A-traktor, så de 23 är
a-traktorärenden av kanalens konstruktion, oavsett vilken av kategorierna de
sedan hamnar i.

*Ifrågasatt av #28. När de 23 etiketterades hamnade bara 8 i en
a-traktorkategori. Slutledningen ovan drog en slutsats om ÄRENDET ur
ämnesradens form, och det ledet håller inte utan att kundens egen text har
prövats. Vad de övriga är, och varför, är inte mätt.*

Tabellen ger i dag 25/12/7 totalt för de tre a-traktorkategorierna med *Utan
svar* 0, 1 och 0. Bilden av a-traktorärenden som i praktiken alltid besvarade
vilar alltså på att de obesvarade låg i fel fil.

*Talen ovan gällde när posten skrevs och är föråldrade av #28, som etiketterade
de 66. Tabellen ger nu 29/14/9 med `Utan svar` 4, 3 och 2. Meningens slutsats
står kvar: skevheten kom av att de obesvarade låg i fel fil. Talen läses ur
`docs/kategorier-forslag.md`, som är maskinproducerad och alltid aktuell.*

**Detta är INTE en rangordning mellan kategorier.** De återstående 43 texterna är
oetiketterade och kan fördela sig var som helst, och ingen jämförelse mot någon
annan kategoris basvärde är gjord.

*Också föråldrat av #28: de 43 är etiketterade sedan skiva 16, och #28:s
kanaltabell redovisar utfallet. Förbehållet i meningen står kvar i sak, eftersom
posten ändå inte gjorde någon jämförelse mot andra kategoriers basvärden.*

**Kanalerna som bär felet**, avsändardomän för de 92. Domäner med färre än tre
träffar är hopslagna enligt §6, eftersom en personlig domän kan identifiera en
person:

| Domän | Trådar |
| --- | --- |
| `autostockholm.se` (eget webbformulär) | 32 |
| `gmail.com` | 20 |
| `autobutler.se` | 12 |
| `wint.se` | 5 |
| `smartab.com` | 4 |
| `googlemail.com` | 3 |
| `melias.se` | 3 |
| 10 domäner med färre än 3 träffar | 13 |

**Varför de saknar svar**, räknat per meddelande i de 92 trådarna och inte per
tråd: 64 meddelanden är inte skickade av oss, 48 är skickade men vidarebefordran,
32 är skickade men bär leveranshuvud, 12 är skickade men saknar svarshuvud.
**Vidarebefordran är den intressanta posten.** Ett vidarebefordrat ärende kan ha
hanterats utanför brevlådan. *Obesvarad* betyder här att brevlådan inte
svarade, aldrig att kunden lämnades utan svar.

**PER KATEGORI GÅR INTE ATT SVARA PÅ UTAN EN NY ETIKETTERINGSKÖRNING.** De 66
texterna är oetiketterade. Pass 2 i `src/ometikettera.py` kostar anrop mot
Anthropic API, och en omkörning av hela materialet är dessutom inte deterministisk
enligt #18, alltså skulle den flytta tal som ingenting annat har ändrat. Att köra
enbart de 66 och lägga till dem är den rimliga vägen, men det är ett eget beslut
och fattas inte här.

*Beslutet fattades i skiva 16, se #28. De 66 är etiketterade och satsen om att de
är oetiketterade gäller alltså läget när posten skrevs. Vägen som pekas ut här,
att köra enbart de 66, är den som togs.*

**FAS 4:S GRIND ÄR INTE FATTAD I DEN HÄR POSTEN.** Kategoritabellen kan inte bära
ett hinkbeslut förrän de 66 är etiketterade.

**Bokningsnotiserna är INTE kundärenden, och domänvägen vore fel verktyg ändå.**
De 8 trådar vars ämnesrad innehåller `Appointment` är 210 till 272 tecken långa,
25 till 32 ord, bär inga fältetiketter, inget registreringsnummer och inget
mänskligt svar. Det är statusmallar om en bokning, inte kundens egna ord.

Även om bedömningen varit den motsatta kan `config/maskindomaner-forbjudna.yaml`
inte uttrycka den, eftersom posten matchar på DOMÄN.

**POPULATIONEN, utskriven så att talen går att räkna om.** En tråd räknas som
maskinmail med egen domän om `klassa_maskin.tradens_skal` är sann OCH
`klassa_maskin.avsandardoman` på trådens första kundmeddelande är
`autostockholm.se`. Populationen är BÅDA skördarna. Det ger 105 trådar, varav 8
är bokningsnotiserna och 97 är övriga. Alla 8 har en och samma avsändaradress,
och 103 av de 105 delar den adressen.

En post på `autostockholm.se` hade alltså slutat klassa 105 trådar som maskinmail
för att komma åt 8. Vad de 97 övriga är, mätt mot AVKODAD text och inte mot
filraden: 78 av 97 bär ordet `wordpress` någonstans i tråden, och 97 av 97 bär
huvudet `X-Msg-EID`. Att 19 saknar ordet är skälet att posten inte kallar dem
något mer bestämt än övriga notiser från den egna sajten.

**Filen ändras inte i den här skivan.**

**PREFIXKOLLISION, registrerad som förbehåll.** En jämförelse av kundtexter på
deras första 400 tecken slår ihop två texter som delar ingress men skiljer sig
längre ned. `scripts/besvarad-omklassning.py` jämför HELA strängen, så talet 66
vilar inte på ett prefix.

**Kollisionen är inte realiserad i det här materialet.** Skriptets prefixkontroll
ger 74 texter bakom de nya, 66 unika på hela strängen och 66 unika på 400 teckens
prefix. Att formulärmailen har fast ingress gör risken tänkbar men den utfaller
inte här, och förbehållet står som en regel för framtida mätningar och inte som
ett påstående om ett fel som finns.

**Alternativ som valdes bort.** Att köra om miningen med en riktig fråga.
Materialet finns på disk, en ny körning kostar kvot mot brevlådan, och #5 slog
redan fast att miningen ska hämta brett en gång.

---

## #28 — De 66 etiketteras, och ett lånat mönster får inte ärva sin stränghet

**Datum:** 2026-08-28 · **Berör:** `scripts/etikettera-nya.py` (ny),
`docs/kategorier-forslag.md`, `src/ometikettera.py`, `docs/roadmap.md` fas 4.5,
`docs/sparrar.md`, `scripts/persondatakontroll.py`,
`tests/test_persondatakontroll.py`, `scripts/besvarad-omklassning.py`, #18, #27,
**och upphäver ett led i #21:s ÖPPEN PUNKT 2**

**Beslut av Lars.** Tre saker i skiva 16.

**1. De 66 texterna etiketteras, och bara de.** Ingen omkörning av materialet.
Pass 2 är inte deterministiskt enligt #18, och en omkörning hade flyttat tal som
ingenting annat har ändrat, i den tabell som bär fas 4:s grind.

**2. Avläsaren i fas 4.5 ska vara skiftlägesokänslig.** Föreskriften står i
`docs/roadmap.md`, luckan i `docs/sparrar.md` under
`versalkansligt-monster-i-avlasare`.

**3. `scripts/` bevakas av persondatakontrollen.** En spärr som inte täcker en
katalog är en lucka oavsett vad som råkar ligga där.

### Etiketteringen

Utförd av `scripts/etikettera-nya.py`, som är idempotent: en kandidat vars text
redan står i `data/kategorisvar.jsonl` etiketteras aldrig om, så en andra körning
gör ingenting. Skyddet mot dubbelräkning ligger där och inte i att antalet råkar
bli rätt.

**Bara `--skarp` gör API-anrop.** `--redovisa` visar etiketterna per kanal och
`--rapport` bygger om `docs/kategorier-forslag.md` ur `data/ometiketterade.jsonl`,
båda utan anrop. `--rapport` är den sanktionerade vägen att skriva om filen när
texten i `src/ometikettera.py` ändrats men etiketterna inte har det, eftersom §0
säger att den är maskinproducerad och aldrig skrivs för hand.

**BÅDA PASSEN, samma väg som resten av korpusen.** Först den fria klassningen ur
`src/kategorisera.py`, som är den enda plats där `inget kundärende` och `oklart`
kan uppstå. Sedan pass 2 mot den fasta taxonomin, läst ur `data/taxonomi.json`
och inte omräknad. Hade bara pass 2 körts vore varje ny text tvingad in i en
kundkategori, och de 41 som inte är kundärenden hade blivit det.

Fördelningen av de 66:

| Utfall | Antal |
| --- | --- |
| `inget kundärende` | 41 |
| `fråga om a-traktorkonvertering` | 4 |
| `boka tillbehörsmontage` | 4 |
| `boka däckbyte` | 3 |
| `boka service` | 3 |
| `oklart` | 3 |
| `boka a-traktorkonvertering` | 2 |
| `fråga om pris a-traktorkonvertering` | 2 |
| `boka rekond` | 1 |
| `fråga om praktisk info` | 1 |
| `fråga om tjänst` | 1 |
| `övrigt` | 1 |

**Noll föll utanför taxonomin, och noll anrop misslyckades.** Att `utanför
listan` inte växte är ett utfall och inte ett mål: raden är en mätpunkt på
taxonomins täckning, och att den står stilla säger att de 28 kategorierna räckte
för de nya texterna.

Åtgången, avläst ur API-svaren: 88 anrop, 35205 in-tokens, 829 ut-tokens.

**Talet 88 går att härleda ur repot**, som 66 fria anrop plus 22 i pass 2, där 22
är 66 minus de 44 som blev `inget kundärende` eller `oklart`. **Tokentalen gör
det inte.** De kommer ur körningens egna API-svar och går inte att räkna om utan
att göra anropen igen, vilket idempotensen förhindrar. De står här som kostnad,
inte som något en granskare kan kvittera.

**KORPUSEN.** 795 texter före, 861 efter. `Med svar` står oförändrad på 213, och
det är kontrollerat mot tabellen och inte påstått: varje ny post bär
`utan svar`, och kolumnen är identisk kategori för kategori. `Utan svar` går från
582 till 648.

### Vad de 66 säger om kanalerna, och vad det INTE avgör

Uppdelat på kanal med `scripts/etikettera-nya.py --redovisa`:

| Kanal | Texter | Blev kundkategori | `inget kundärende` eller `oklart` |
| --- | --- | --- | --- |
| Webbformuläret | 23 | 20 | 3 |
| Övriga kanaler | 43 | 2 | 41 |

**De texter som inte är kundärenden kommer nästan uteslutande från de andra
kanalerna.** Av de 43 övriga bär 40 `inget kundärende` och 1 bär `oklart`.

> **TALET 41 BÄR TVÅ BETYDELSER I DEN HÄR POSTEN, och de är olika mängder.**
> I fördelningstabellen är 41 antalet texter som fick etiketten
> `inget kundärende`, oavsett kanal. I kanaltabellen är 41 antalet texter ur
> ÖVRIGA KANALER som blev `inget kundärende` eller `oklart`, alltså 40 plus 1.
> Att de sammanfaller är ett sammanträffande. Den som räknar om ett tal härifrån
> ska kontrollera vilken av dem som avses.

**VAD DE ÄR, ÄR INTE MÄTT.** Skivan har deras etikett och deras avsändardomän,
inte deras ärendetyp. En uppräkning av vad de innehåller vore läst ur minnet av
att ha bläddrat, och det är precis den defekt den kursiva rättelsen i #9 bär.
Det som är avläst är domänfördelningen i #27.

Formuläret å sin sida fick en kundkategori i 20 fall av 23. Att kategorin är
RÄTT är inte mätt, bara att den inte blev `inget kundärende` eller `oklart`.

**EN ÖPPEN FRÅGA SOM INTE AVGÖRS HÄR.** Formulärets ämnesrad är en
offertförfrågan om A-traktor, men bara 8 av de 23 hamnade i någon av de tre
a-traktorkategorierna. Av de 15 övriga blev 12 en annan kundkategori, nämligen
`boka tillbehörsmontage` 4, `boka service` 3, `boka däckbyte` 3, `boka rekond` 1
och `fråga om tjänst` 1. De sista 3 är de `oklart` och `inget kundärende` som
kanaltabellen ovan redovisar. Klassificeraren läser
BRÖDTEXTEN och inte ämnesraden, så den läser vad kunden skrivit i formulärets
fält. **Varför de skiljer sig är inte mätt**, och posten gissar därför inte:
det kan vara att formuläret används för annat än a-traktor, eller att kundens
egen text pekar mot en annan tjänst. Frågan hör till fas 4:s grind.

**FAS 4:S GRIND ÄR INTE FATTAD HÄR.**

### Versalkänsligheten

`scripts/persondatakontroll.py` bär ett regnr-mönster som är versalkänsligt,
avläst ur filen. Att det BÖR vara det är en slutsats och inte ett citat: en
§6-kontroll som larmar skiftlägesokänsligt larmar på vanliga ord i löptext, och
filens kommentar om postnummer gör samma avvägning uttryckligt för ett annat
mönster. Mot webbformulärets fältvärde ger samma mönster 46 av 78 versalkänsligt
och 77 av 78 skiftlägesokänsligt. **En fältavläsare som lånar mönstret utan
`re.IGNORECASE` tappar 31 av de 77 nummer som går att läsa.**

Följden är att uppslaget inte kan göras, gatingen faller till `utkast`, och
kunden väntar på en handpåläggning som ärendet inte behövde. Ingen spärr fälls
och inget larm går.

**Det slår först i drift, och skälet är mekaniskt.** Testdata skrivs av den som
skriver koden, och den skriver versalt. Ett test som bara matar in versala nummer
är grönt för alltid. Luckposten kräver därför att ett test för avläsaren bär ett
gement och ett blandat nummer.

### `scripts/` under persondatakontrollen

`BEVAKADE` bar `docs/`, `mallar/`, `config/` och `CLAUDE.md`. Skiva 15 lade två
mätskript under `scripts/` som läser skarp kundpost och skriver antal ur den. En
utskrift som råkar bära ett värde i stället för en räkning hade passerat.

**`src/` och `tests/` bevakas fortfarande inte**, och skillnaden är inte att det
ena är kod. Den är att skripten under `scripts/` läser skarp kundpost och skriver
utdata ur den, medan `src/` och `tests/` bär mönster och påhittade fixturer.
Kommentaren i filen sade tidigare att kod inte kontrolleras, och den var tvungen
att skrivas om av samma ändring.

Kontrollen går från 9 till 17 spårade filer och ger noll fynd.
`test_scripts_bevakas` binder katalogen, och prövningen enligt §7.1 gav RÖD när
`BEVAKADE`-raden neutraliserades.

**ETT LED I #21:s ÖPPEN PUNKT 2 UPPHÄVS AV DEN HÄR ÄNDRINGEN.** Punkten säger
att väg 1, att lägga Lars adress i `TILLATNA`, flyttar adressen från en bevakad
fil till en obevakad. `scripts/persondatakontroll.py` är bevakad efter den här
skivan, så det ledet gäller inte längre.

**Punktens slutsats står ändå kvar**, av ett annat skäl: ett
`TILLATNA`-undantag gäller exakt strängen, så adressen vore oskyddad i en spårad
fil även när filen granskas. Väg 1 löser alltså fortfarande inte §6-frågan utan
flyttar den. Den öppna punkten väntar oförändrat på Lars, och #21 bär en kursiv
not som pekar hit.

**Alternativ som valdes bort.** Att bevaka hela repot. Det hade fällt `src/` och
`tests/` på påhittade fixturer, och en spärr som larmar på sin egen testdata blir
avstängd.

---

## #29 — Kanalen blir kontext, och fas 4:s grind fattas

**Datum:** 2026-08-28 · **Berör:** `src/kanal.py` (ny), `src/kategorisera.py`,
`src/ometikettera.py`, `config/kategorier.yaml` (ny), `scripts/etikettera-nya.py`,
`scripts/besvarad-omklassning.py`, `scripts/formular-matning.py`,
`tests/test_kanal.py` (ny), `tests/test_kategorier_yaml.py` (ny),
`tests/test_etikettera_nya.py` (ny), `scripts/sparr-prova.sh`,
`docs/incidentlogg.md`, `requirements.txt`, `docs/sparrar.md`,
`docs/roadmap.md`, `CLAUDE.md`, #18, #27, #28

### DEL A — klassificeraren ser ämnesraden och kanalen

**FYNDET.** Webbformuläret ÄR a-traktorformuläret. Dess fältblock bär
`Registreringsnummer`, `Bilmodell` och `Växellåda`, alla tre i 78 trådar av 78.
Klassificeraren läste bara fritexten och såg aldrig att inskicket kom den vägen.

**VARFÖR `Växellåda` finns i formuläret är Lars uppgift, inte en mätning:**
manuell och automat påverkar hastighetsbegränsningen vid ombyggnad. Skälet står
utskrivet därför att det förklarar varför fältblocket är a-traktorspecifikt, men
det går inte att belägga ur repot. Det som ÄR mätt är att fälten finns.

Mätt med `scripts/formular-matning.py` över alla 78 formulärtrådar, alla
återfunna i korpusen:

| Utfall | Antal |
| --- | --- |
| **Klassade som en a-traktorkategori** | **36** |
| **Klassade som något annat** | **42** |

De 42, fallande: `boka tillbehörsmontage` 14, `boka service` 7, `oklart` 6,
`boka däckbyte` 5, `boka rekond` 4, `fråga om tjänst` 2, `inget kundärende` 1,
`fråga om pris rekond` 1, `begära offert` 1, `fråga om pris tillbehör` 1.
De 36: `fråga om a-traktorkonvertering` 21, `fråga om pris
a-traktorkonvertering` 9, `boka a-traktorkonvertering` 6.

**Talet gäller alla 78 och inte bara de 23 nya.** #28 mätte 8 av 23 bland de
texter skiva 16 lade till. Över hela formulärpopulationen är det 36 av 78.

**Beslut av Lars.** Ämnesrad och kanal går in i prompten som KONTEXT.

**KANALEN ÄR BEKRÄFTANDE SIGNAL, ALDRIG ENSAM GRUND.** Samma regel som #27, nu
tillämpad på en andra signal. En text som kom via formuläret men uppenbart
handlar om något annat ska fortfarande kunna klassas som det.

**Konstruktionen.** `src/kanal.py` namnger kanalen och lämnar ämnesraden.
Kontexten läggs i ett avgränsat block överst i användarmeddelandet, och
systemprompten säger ordagrant att kanalen aldrig ensam avgör kategorin och att
texten går före när de säger emot varandra.

**SYSTEMPROMPTEN ÄNDRAS FÖR ALLA TEXTER, inte bara för dem med kontext.**
`KONTEXTREGEL` läggs till ovillkorligt. Det är avsiktligt: två olika
systemprompter hade gjort klassningen beroende av om kontexten råkade gå att
fastställa, och den skillnaden hade inte synts i utfallet. Regeln är formulerad
så att den är sann också när blocket saknas. Följden är att varje framtida
klassificering, även av en text utan kanal, körs mot en annan systemprompt än
före den här skivan.

**DEN BESVARADE SIDANS KONTEXT SLÅS UPP PÅ TEXTEN.** `data/par.jsonl` bär ingen
ämnesrad, så `kontext_per_text` bygger ett index ur trådfilen. Indexet tar med
VARJE kundmeddelande och inte bara trådens första, eftersom
`src/extract.py::par_ur_trad` parar ett svar med `senaste_kund`: en par-text kan
komma från vilken position som helst i tråden. Ett index på förstameddelanden
hade dessutom låtit en text från position tre kollidera ouppdagat med en annan
tråds förstameddelande och få dess kanal.

**Bär samma text motstridig kontext får den ingen alls.** VET INTE är svaret,
aldrig en gissning avgjord av läsordningen.

**INGEN KOD MAPPAR KANAL TILL KATEGORI.** Det är hela skyddet, och det är
prövat: `tests/test_kanal.py` låter modellen svara `boka biltvätt` medan kanalen
är a-traktorformuläret och kräver att svaret står kvar orört. Prövningen enligt
§7.1 gjordes genom att INFÖRA den förbjudna kopplingen i `ometikettera_en`, och
tre negativkontroller föll. En regel om frånvaro av kod går inte att fälla genom
att radera en rad; den fälls genom att skriva dit den.

**Trunkeringen gäller texten, inte summan.** Vore taket satt på hela strängen
hade ett långt kontextblock ätit av kundens egna ord, alltså det enda som får
avgöra kategorin. Prövat: fälld trunkering ger RÖD.

**Kanalen fastställs på ÄMNESRADEN, inte på avsändardomänen.** Den egna domänen
bär också annan maskinell trafik, uppmätt i #27: 103 av 105 maskinmailtrådar med
egen domän delar adress med bokningsnotiserna.

**Predikatet bodde på två ställen och bor nu på ett.**
`scripts/besvarad-omklassning.py` och `scripts/formular-matning.py` bar var sin
kopia. Båda läser nu `src/kanal.py`. Talen är oförändrade efter flytten.

**KORPUSEN ETIKETTERAS INTE OM AV DEN HÄR ÄNDRINGEN.** Tabellen i
`docs/kategorier-forslag.md` bär etiketter satta UTAN kontext. Fixen gäller
framtida klassificering. En omkörning hade flyttat tal som ingenting annat har
ändrat, eftersom pass 2 inte är deterministiskt enligt #18, och den är inte
gjord.

**Den inkrementella vägen bär kontexten.** `scripts/etikettera-nya.py` byggde
sina poster utan `amne` och `kanal`, och eftersom den är den enda sanktionerade
körningen hade fixen då inte nått någon körbar väg alls. Den bygger dem nu ur
meddelandet direkt, inte via uppslagningen på text: där finns meddelandet i
handen.

**Varför det är sändväg.** I drift misdirigerar samma fel samma ärenden: ett
a-traktorärende som hamnar i `boka däckbyte` bedöms mot fel kategoris hink och
fel mall.

### DEL B — fas 4:s grind

**Beslut av Lars, dikterat.** `config/kategorier.yaml` upprättad.

**`auto`:** `fråga om a-traktorkonvertering`.

**`aldrig`:** `bestrida faktura`, `reklamera utfört arbete`, `godkänna offert`,
`begära dokument`, `ansöka om praktikplats`, `ge feedback`, `inget kundärende`,
`oklart`, `utanför listan`.

**`utkast`:** allt övrigt, som STANDARDHINK. Filen räknar inte upp den. En
kategori som ingen tagit ställning till faller därmed till `utkast` och aldrig
till `auto`, och en ny kategori i taxonomin ändrar inget utan Lars beslut.

**Skälen, Lars ord.**

`auto` kräver **minst tio par med svar OCH att svaret inte beror på en bedömning
i verkstaden**. Bara en kategori uppfyller båda. Avläst ur tabellen: fyra rader
bär tio eller fler i kolumnen *Med svar*, nämligen `inget kundärende` 52,
`oklart` 31, `fråga om a-traktorkonvertering` 25 och `fråga om pris
a-traktorkonvertering` 11. De två första är inga kundkategorier.

*Ledet "Bara en kategori uppfyller båda" är UPPHÄVT av #30. Där avgör Lars att
`fråga om pris a-traktorkonvertering` når tröskeln OCH att dess svar inte beror
på en bedömning i verkstaden, alltså att den uppfyller båda kriterierna. Två
kategorier gör det. Vad som håller prisfrågan i `utkast` är i stället att
`config/priser.json` saknas, och att flytten kräver ett eget beslut även när
filen fylls. Resten av stycket står kvar: talen är avlästa och riktiga.*

`fråga om pris a-traktorkonvertering` når tröskeln med 11 par men **står i
utkast tills `config/priser.json` är fylld**. En prismall utan priskälla faller
ändå på §7.2. Att flytta den när filen finns är ett eget beslut.

**ÖPPEN PUNKT: DE TVÅ SKÄLEN GÅR INTE IHOP, och de är inte omskrivna.** Lars
första mening säger att bara EN kategori uppfyller båda kriterierna. Hans andra
säger att prisfrågan NÅR TRÖSKELN och står i utkast TILLS priskällan finns.

Läses de tillsammans följer att prisfrågan skulle falla på det andra kriteriet,
alltså att dess svar beror på en bedömning i verkstaden. **Det står ingenstans i
repot**, och den slutsatsen är inte dragen här. Läses den andra meningen ensam
är prisfrågan kvalificerad och hindras bara av den saknade filen, men då är
"bara en uppfyller båda" inte riktigt.

Skillnaden är inte akademisk: den avgör om kategorin flyttas automatiskt när
`config/priser.json` fylls, eller om den kräver ett nytt beslut även då.
`config/kategorier.yaml` säger därför bara att kategorin står i utkast och att
frågan är öppen. **Ingen av Lars meningar är omskriven, och ingen tolkning är
vald.** §10: vid tvetydig instruktion som rör sändning frågas vad som menas.

*AVGJORD I #30. Lars valde den andra meningen: kategorin är kvalificerad och
hindras enbart av att `config/priser.json` saknas, men den flyttas inte
automatiskt när filen fylls. Stycket ovan beskriver alltså läget när posten
skrevs. `config/kategorier.yaml` säger inte längre att frågan är öppen, och en
tolkning ÄR vald. Frågan ställdes, och den blev besvarad.*

`godkänna offert` och `begära dokument` står i `aldrig` för att de **utlöser
handling i verkstaden**, inte för att de är känsliga.

**GRINDEN FATTAS PÅ TAL SOM FORTSÄTTER RÖRA SIG, OCH DET ÄR AVSIKTLIGT.** Talen
har räknats om upprepade gånger utan att slutsatsen har ändrats: a-traktor är
den enda ärendetyp som bär mallunderlag. Det är avläsbart i dag, inte ett
påstående om historien: de enda KUNDKATEGORIER som når tio par med svar är
`fråga om a-traktorkonvertering` 25 och `fråga om pris a-traktorkonvertering`
11, och båda är a-traktor.

**Lars skäl att fatta grinden ändå:** DEL A kan göra kategorin större, aldrig
mindre, och en större kategori ändrar inte hinken.

*Ledet "aldrig mindre" är Lars bedömning och inte belagt här. Kontexten kan i
princip flytta en text MELLAN de tre a-traktorkategorierna, och formulärtrådarna
fördelar sig redan i dag över alla tre: 21, 9 och 6. Att a-traktor som helhet
skulle krympa vore däremot att en formulärtråd slutar vara ett a-traktorärende
av att klassificeraren FÅR VETA att den kom via a-traktorformuläret, och pass 2
är dessutom inte deterministiskt enligt #18. Bedömningen är rimlig; belagd är
den inte, och hinkbeslutet vilar inte på den.*

**NOTERAT, INTE BESLUTAT.** De KUNDKATEGORIER som bär flest obesvarade texter är
`boka rekond` 19, `avboka bokning` 12, `boka biltvätt` 11 och `boka däckbyte` 10.

Kvalifikationen är nödvändig och inte en artighet: `inget kundärende` bär 536
obesvarade och `oklart` 10, alltså mer respektive lika mycket som den fjärde i
listan. Ingen av dem är en kundkategori, och båda står i `aldrig`.
**`boka biltvätt` har noll svar av elva.** Det är kunder som skrev och aldrig
fick svar, och det är där botens värde ligger även om mallunderlaget saknas.

**Filen ändras för hand, aldrig av en körning.** Ramverksregel 2. Testerna i
`tests/test_kategorier_yaml.py` binder varje namn mot taxonomin, så att ett
stavfel inte tyst tar bort en kategori ur `aldrig` och lägger den i
standardhinken. Prövat enligt §7.1: en fälld standardhink ger RÖD.

**ÖPPEN PUNKT.** §0 listar `docs/kategorier.md` som planerad och byggd i fas 4.
Grinden är fattad men filen finns inte, och den ingick inte i den här skivans
brief. Frågan är ställd och obesvarad.

*AVGJORD I #30: filen behövs inte, och §0:s rad är struken och ersatt av
`config/kategorier.yaml`. Frågan är alltså besvarad, inte obesvarad.*

---

## #30 — Grindvillkoret stryks, prisfrågan avgörs, och fas 4 får sina filer

**Datum:** 2026-08-28 · **Berör:** `docs/roadmap.md`, `config/kategorier.yaml`,
`scripts/kategoristatus.py` (ny), `tests/test_kategoristatus.py` (ny),
`tests/test_kategorier_yaml.py`, `CLAUDE.md` §0, `docs/incidentlogg.md`, #29

### DEL A — "Ingen kategori startar i `auto`" stryks

**Beslut av Lars.** Villkoret i `docs/roadmap.md` fas 4 tas BORT. Det är inte
`auto`-raden i `config/kategorier.yaml` som ska bort.

**Skälet.** Villkoret skrevs i skiva 3. Verifierat med
`git log -S "startar i \`auto\`" -- docs/roadmap.md`, som ger TVÅ committar:
`e9a6772 Skiva 3`, där frasen infördes, och `05a6596 Skiva 17`, som rörde den
när noten skrevs. Den äldre är införandet.

Villkoret skrevs alltså innan något underlag fanns. **Det är en förhandsgissning
om ett beslut som tillhör Lars**, och det var aldrig en ramverksregel:
ramverksregel 2 förbjuder att KOD flyttar en kategori till `auto` och kräver
Lars uttryckliga beslut. Det beslutet är fattat i skiva 17.

*Skälstycket sade först att §10 gör beslutet till Lars. §10:s punkt gäller att
BEFORDRA en kategori mellan hinkar, och en kategori som startar i `auto` har
inte befordrats. Att starthinken är Lars beslut följer av ramverksregel 2 och av
fasens egen grindrad, inte av §10.*

#29 lät meningen stå kvar med en not, på grunden att den var sann som förväntan
när den skrevs. Lars avgör att en förhandsgissning som visat sig fel inte ska stå
kvar i ett grindvillkor: den läses av nästa läsare som ett krav.

### DEL B — prisfrågan, tolkning vald

**Beslut av Lars.** #29:s öppna punkt är avgjord. **Den andra meningen gäller**,
och svaret har två led som båda ska stå skrivna.

**LED 1. Kategorin är KVALIFICERAD för `auto`.** `fråga om pris
a-traktorkonvertering` når tröskeln med 11 par, och **svaret beror inte på en
bedömning i verkstaden**. Det enda som hindrar den är att `config/priser.json`
saknas.

**LED 2. Den flyttas ändå INTE automatiskt när filen fylls.** En fylld prisfil är
inte samma sak som verifierade priser, och flytten kräver ett nytt uttryckligt
beslut av Lars.

**Led 2 är inte en formalitet.** Utan det hade led 1 gjort flytten till en
följdverkan av att en fil får innehåll, alltså till något kod kunde utlösa. Det
är precis vad ramverksregel 2 förbjuder.

**#29:S "BARA EN KATEGORI UPPFYLLER BÅDA" UPPHÄVS HÄRMED.** Led 1 säger att
prisfrågan uppfyller båda kriterierna, alltså att två kategorier gör det. En
kursiv not i #29 pekar hit. Talen i den posten står kvar: de var och är avlästa. Båda leden står därför i
`config/kategorier.yaml`, och filen bär ingen villkorad markering som en
framtida läsare kunde ta för en instruktion.

### DEL C — fasens egna filer

**`scripts/kategoristatus.py` är byggd.** Den producerar statusraden §12 kräver:
antal kategorier per hink, antal texter per kategori, och datum för senaste
mining. Allt ur filer i arbetsträdet, aldrig för hand. Två av de fyra ligger
under `data/` och är alltså inte committade, se nedan.

Källorna är `config/kategorier.yaml`, `data/ometiketterade.jsonl`,
`data/taxonomi.json` och `docs/mining-log.md`.

**EN SAKNAD ELLER OLÄSLIG KÄLLA ÄR ETT STOPP, inte en tystnad.** Skriptet
namnger filen och avslutar med exit 1 utan att skriva någon tabell. En halv
statusrad ser komplett ut och är värre än ett namngivet hål, vilket är hela
skälet till att §12 lät raden utebli i stället för att någon skrev den för hand.

**En fil som FINNS men inte går att läsa är samma hål.** En katalog i stället för
en fil, trasig JSON eller YAML, en YAML som parsar till fel typ, en JSONL-rad
utan `etikett`: alla ger det namngivna hålet i stället för ett traceback. Den
trasiga raden namnges med sitt RADNUMMER och aldrig med sitt innehåll, eftersom
raderna bär kundtext (§6).

**§7.1-PRÖVNINGEN, redovisad per fällning.** Samtliga NEUTRALISERADE, inte
raderade: en radering av `if not sokvag.exists():` lämnar ett hängande `raise`
och ger `IndentationError`, alltså FEL och inte ett verdikt.

**RADERNA CITERAS, DE NUMRERAS INTE.** Ett radnummer föråldras av varje
redigering i filen, och den här tabellen bevisade det själv: dess första lydelse
namngav rader som en rättelse av ett ANNAT fynd, i samma skrivning, hade skjutit
ner. Hur många steg går inte att belägga, eftersom filen var otrackad och ingen
tidigare version finns i git; talet är därför inte utskrivet. Se §7:s stycke om
appendixposten som föråldrar sig själv.

Talen nedan är avlästa ur körningar mot filen som den levereras, gjorda EFTER
varje annan ändring i skivan, och sviten är hela svitens.

| Fälld rad, citerad | Fällning | Svitens utdata | Verdikt |
| --- | --- | --- | --- |
| `if not sokvag.exists():` i `las_text` | `if False:` | `438 passed` | **GRÖN, inkonklusiv** |
| Samma rad OCH `except OSError as fel:` | `if False:` respektive `except ZeroDivisionError as fel:` | `7 failed, 431 passed` | **RÖD** |
| `except Saknas as fel:` i `main` | `except ZeroDivisionError as fel:` | `6 failed, 432 passed` | **RÖD** |
| `if standard == "auto":` i `las_hinkar` | `if False:` | `1 failed, 437 passed` | **RÖD** |
| `if kallor:` i `statusrader` | `if False:` | `1 failed, 437 passed` | **RÖD** |

De två sista vakterna infördes i rättelsevarvet och prövades i samma varv.
Ingendera bär lagrat försvar: `if standard not in HINKAR` släpper igenom `auto`,
eftersom `auto` ÄR en giltig hink, och källutskriften har ingen andra väg.

**LAGRAT FÖRSVAR, och det var inte planerat.** Existenskontrollen
`if not sokvag.exists():` och `except OSError as fel:`, båda i `las_text`,
producerar samma `Saknas` för en saknad fil: `FileNotFoundError` ÄR en
`OSError`. Fälls bara den ena förblir sviten grön, och prövningen hade pekat ut
ett äkta test som vakuöst. Det är precis det fall §7.1 varnar för, och det
uppstod av den refaktorering som skrevs för att täcka oläsliga filer. Verdiktet
sattes först efter att båda lagren fällts tillsammans.

*Stycket numrerade först de två raderna, tolv rader under den rubrik som säger
att rader ska citeras och inte numreras. Numren var föråldrade av samma
redigeringar som föråldrade tabellens. Rättelsen av tabellen tillämpades alltså
inte på stycket rakt under den.*

**Statusraden går bara att köra där `data/` finns.** Två av de fyra källorna
ligger där, och `.gitignore` utesluter hela katalogen, så en färsk klon kan inte
producera raden.

**Skälen för de två är olika, och de ska inte slås ihop.**
`data/ometiketterade.jsonl` bär kundtext och kan inte committas enligt §6.
`data/taxonomi.json` bär 28 kategorinamn och ingen kundtext; den är ocommittad
enbart därför att den ligger under `data/`. Att flytta den är inte den här
skivans fråga, men skälet ska stå rätt: `git check-ignore -v data/taxonomi.json`
ger `.gitignore:4:data/`, inte §6.

**Utfallet vid skrivögonblicket:** `auto` 1 kategori och 29 texter, `utkast` 21
kategorier och 181 texter, `aldrig` 9 kategorier och 651 texter. 861 texter
totalt, senaste mining 2026-08-26 16:42 UTC.

**STATUSRADEN NAMNGER SINA KÄLLOR.** Flaggorna gör det möjligt att producera
raden ur godtyckliga filer, och utan källorna utskrivna hade en sådan rad varit
teckenidentisk med en producerad ur repot. §12:s krav är att raden inte ska gå
att skriva för hand; en rad utan härkomst går att skriva för hand med en omväg.

**`standardhink: auto` avvisas.** `auto` är en giltig hink men en otillåten
STANDARDhink: en kategori ingen tagit ställning till hade då blivit sändbar av
att någon lade till den i taxonomin. Att `utkast` är standard är hela poängen.

**§12 säger "mail", skriptet räknar TEXTER, och skillnaden står utskriven i
docstringen.** `src/kategorisera.py` avdubblar per kundtext och tar ett
meddelande per tråd, så en kategori med tio texter kan vila på fler mail än tio.
Kolumnerna heter därför `Texter` och inte `Mail`.

**Ett fel hittades av testerna, inte av läsning.** Felhanteringen anropade
`Path.relative_to(ROT)`, som KASTAR för en sökväg utanför repot. Varje
`--hinkar` som pekade någon annanstans fick alltså ett traceback i stället för
beskedet om vilken fil som saknades, alltså i precis det läge skriptet finns
för. Rättat med en vakt, och `test_sokvag_utanfor_repot_kraschar_inte` binder
den.

**§6-kontrollen täckte inte den nya koden när skivan granskades.**
`scripts/persondatakontroll.py` läser `git ls-files`, alltså enbart spårade
filer, och `scripts/kategoristatus.py` och `tests/test_kategoristatus.py` var
otrackade. Kontrollen biter först vid `git add`, och commit-hookens utfall står
i skivans rapport. Filerna skriver antal, kategorinamn, ett datum och ett
RADNUMMER för en trasig rad, aldrig radens innehåll.

### `docs/kategorier.md` behövs inte, och §0:s rad stryks

**Avgjort i den här skivan.** §0 listade filen som "kategoridefinitioner och
deras hink", planerad till fas 4. Ingen av de två delarna motiverar en fil till:

- **Hinken** står i `config/kategorier.yaml`, som är committad och som
  `scripts/kategoristatus.py` läser.
- **Kategorinamnen** står i `docs/kategorier-forslag.md`, som bär taxonomins 28
  rader och är committad. `data/taxonomi.json` är gitignorerad, så det är
  dokumentet som är den committade hemvisten.
- **DEFINITIONER utöver namnen finns inte, och systemet är byggt så med avsikt.**
  `src/ometikettera.py::bygg_system_pass2` ger modellen enbart namnen, en per
  rad. Namnen ÄR alltså definitionen i den mening som styr utfallet. En
  definitionsfil hade antingen upprepat namnen eller hittat på semantik som
  ingen kod läser, och den senare hade blivit citerad som om den styrde något.

§0:s rad pekar därför på `config/kategorier.yaml` i stället. **Kartan ska peka på
det som finns.**

### Tvivlet om §7.1-prövningar gjorda före I7

`docs/incidentlogg.md` I7 visade att en kvitterad återställning kunde lämna
fällningens kod kvar i bytekoden. **Varje §7.1-prövning som gjordes före den
åtgärden vilar därmed på en kvittens som inte bevisade vad den påstods bevisa.**

Prövningarna är inte därmed fel. Fönstret krävde en fällning av exakt samma
längd inom samma sekund, och de flesta fällningar ändrar längden. Men skillnaden
mellan "prövad" och "prövad med ett verktyg vars kvittens hade ett hål" ska stå
utskriven där någon senare läser dem som belagda.

**Prövningarna körs INTE om.** Beslut av Lars. En omkörning hade gett ett nytt
utfall att lita på utan att säga något om vad de gamla var värda, och kostnaden
bärs inte av den frågan.

Noteringen står i `docs/incidentlogg.md` under I7.

---

## #31 — Datakällan för fordonsuppslaget: den öppna fordonssidan, och villkoren är olästa

**Datum:** 2026-09-02 · **Berör:** `docs/roadmap.md` fas 4.5, `docs/sparrar.md`
`fordonsfakta-ur-sida`, `src/biluppgifter.py` (ny), `tests/test_biluppgifter.py`
(ny), CLAUDE.md §6, #23

**Beslut av Lars.** #23:s öppna punkt är besvarad i ett led och inte i två. Fas
4.5 hämtar de tre fälten ur **den öppna fordonssidan hos biluppgifter.se**, alltså
HTML utan API-nyckel, och inte ur någon av de fyra leverantörer #23 ställde upp.
PRO-API:t står kvar som ett alternativ men är inte valt.

**Vad valet ger.** De tre fält `src/fordonsuppslag.py` utvärderar finns på sidan.
Avläst 2026-09-02: alla tre står på svaret för ett fordon, var etikett en gång.
Det svaret ger `Uppslag(tjanstevikt_kg=2140, slapvagnsvikt_kg=2400,
draganordning=False)`. Avbildningen är:

| Fält i `Uppslag` | Etikettens text på sidan |
| --- | --- |
| `tjanstevikt_kg` | `Tjänstevikt` |
| `slapvagnsvikt_kg` | `Släpvagnsvikt` |
| `draganordning` | `Draganordning` |

**MEN DE TRE FÄLTEN STÅR INTE PÅ VARJE FORDONS SIDA.** Ett andra skarpt svar,
avläst samma dag, bär `Tjänstevikt` men **noll** förekomster av `Släpvagnsvikt` och
`Draganordning` — och det trots att svarets `canonical` matchar det begärda numret,
alltså trots att fordonet finns. Modulen utelämnar då nycklarna och
`src/fordonsuppslag.py` kastar `UppslagMisslyckades: svaret saknar
slapvagnsvikt_kg`. Ärendet blir alltså inget besked, vilket är rätt beteende: ett
A-traktorbesked på en gissad släpvagnsvikt vore värre än tystnad.

**Det är likväl ett driftsfaktum som hör till valet:** den här källan kan inte ge
besked om alla verkliga fordon. **Hur stor andel är inte mätt**, och två avlästa
svar duger inte för att uppskatta den. Ett PRO-API med ett dokumenterat fältschema
hade gett ett svar på den frågan i förväg. Den öppna sidan ger det inte, och det
är en kostnad för valet som inte var känd när valet gjordes.

**`Släpvagnsvikt` är den BROMSADE vikten.** Sidan bär också
`Släpvagnsvikt obromsad` som en egen rad, och det är den avbildningen som bestämmer
vilket tal som når tröskeln i `src/fordonsuppslag.py`. Att etiketterna inleds
likadant är skälet till att `fordonsfakta-ur-sida` matchar etiketten exakt och inte
som prefix.

**ÄGARDATA HÄMTAS INTE, OCH DET ÄR GRATIS HÄR.** #23:s aktiva val håller: sidans
ägaruppgifter ligger bakom inloggning hos källan, och modulen begär bara den
öppna sidan. Valet av öppen HTML försämrar alltså inte §6-läget jämfört med ett
API utan ägardata. Det ska inte tolkas som att en spärr hindrar en framtida
inloggning. Ingen sådan spärr finns, och luckan står utskriven i
`docs/sparrar.md`.

### FÖRBEHÅLL 1 — valet byter ut ett kontrakt mot en avläsning

Ett API mot nyckel har en form någon lovat. Den öppna sidan har en form vi har
**avläst en dag**. Skillnaden är inte teoretisk:

- **Källan filtrerar på klient.** Hämtningen lyckas beroende på `User-Agent`.
  Det är inte ett kontrakt, och en skärpning hos källan stoppar flödet utan
  förvarning.
- **Sidan svarar HTTP 200 med sin söksida** på ett nummer som inte finns, inte
  404. Ett statusberoende "finns fordonet" är alltså fel byggt mot den här
  källan, och `fordonsfakta-ur-sida` löser det med `canonical` i stället.
- **Etiketternas stavning kan ändras** utan att någon meddelar det. Utfallet är
  rätt — nyckeln utelämnas, `fordonsfakta-ur-uppslag` fäller, ärendet faller till
  utkast — men felet syns som en tystnad och inte som ett larm.

Beslutet fattas med de tre förbehållen skrivna, inte utan dem. **Kostnaden för
valet är inte noll bara för att priset är noll.**

### FÖRBEHÅLL 2 — IMPLEMENTATIONEN KOM FÖRE DEN HÄR POSTEN

#23 avslutas med: *"Ingen leverantör får väljas av kod, och ingen får väljas
genom att en implementation redan råkar peka på en av dem."*

**Ordningen i skiva 19 var den omvända.** `src/biluppgifter.py` skrevs mot den
öppna sidan innan någon beslutspost fanns, och den här posten är valets första
skriftliga form. Det är utskrivet här och inte utelämnat, eftersom en läsare annars
ser en beslutspost och en modul som pekar samma väg, och drar slutsatsen att posten
kom först.

Valet står kvar som Lars, inte som kodens. Men den som ändrar det ska veta att
det finns kod byggd mot den här källan, och att kodens existens inte är ett
skäl att behålla källan.

### AVGJORT AV LARS: ANVÄNDARVILLKOREN LÄSES INTE

**Fas 4.5:s grind är passerad, och avtalsledet är avgjort genom att strykas.**
Grindraden i `docs/roadmap.md` lyder *"Lars beslut om datakälla och avtal"*.
Datakällan är avgjord ovan. Avtalsledet avgjorde Lars 2026-09-02: **källans
användarvillkor ska inte läsas, och frågan ska inte tas upp igen.**

**Vad beslutet innebär, utskrivet.** Två frågor lämnas obesvarade och ska inte
utredas: om automatiserad hämtning av de öppna sidorna är tillåten, och om
vidareförmedling av fälten i ett kommersiellt kundmail är tillåten. Ingen har
läst villkoren, och **den här posten påstår ingenting om vad de säger.** Risken är
därmed varken bedömd eller avförd, utan **oläst och accepterad**. Det är en
juridisk fråga och inte en teknisk, och den är Lars att avgöra, också genom att
låta den vara.

**Vad beslutet INTE innebär.** Det är inget påstående om att hämtningen är
tillåten. Skulle källan invända är det här posten som visar att frågan var ställd
och att beslutet var att inte utreda den. **Ingen spärr och ingen annan post ska
läsas som ett juridiskt godkännande**, och det gäller även `fordonsfakta-ur-sida`,
som prövar härkomst och inte rättighet.

Modulen är byggd och prövad enligt §7.1. Att den fungerar var aldrig grindens
villkor, precis som fasens egen rad säger om testnyckeln; grinden passeras av
beslutet ovan och inte av koden.

### Vad posten INTE avgör

- **Om luckan `versalkansligt-monster-i-avlasare` är stängd.** Den gäller
  avläsaren som plockar registreringsnumret ur MEJLTEXT, som inte är byggd.
  `src/biluppgifter.py` tar emot ett redan normaliserat nummer och rör inte
  luckan.
- **Om `config/priser.json` finns.** #30:s led 2 står oförändrat.
- **Var driften körs.** #20 står oförändrat.

---

## #32 — Skiva 21 stängs inte, och avläsningen byggs om till en parser

**Datum:** 2026-09-03 · **Berör:** `src/biluppgifter.py`,
`tests/test_biluppgifter.py`, `docs/sparrar.md` `fordonsfakta-ur-sida`,
`docs/incidentlogg.md` I8, CLAUDE.md §6 och §7, #31

**Beslut av Lars.** Skiva 21 gick in i sitt tredje och sista granskningsvarv och
underkändes. §7 säger då stoppa och rapportera öppet, vilket gjordes. **Lars
beslut är att skivan inte stängs utan fortsätter som skiva 22**, och att det som
finns committas först, med statusen utskriven.

**Grunden för beslutet.** Skiva 21 prövade vad som händer när SIDAN ändras i
stället för när koden gör det. Prövningen hittade fem sändvägsdefekter av samma
klass: ett regexmönster skrivet för sidans nuvarande markup TYSTNAR i stället för
att kasta när markupen ser annorlunda ut, och släpper då ut ett värde. Tre
stängdes under skivan, två står öppna.

**De elva mutationsfällningarna mot koden hittade ingen av de fem**, eftersom
koden var självkonsistent i samtliga fall. Det är skillnaden mellan att pröva
koden och att pröva källan, och den är nu uppmätt och inte antagen.

**Beslutet om metoden: sidan ska PARSAS, inte matchas som text.** Grundfelet
bakom båda de öppna defekterna är att modulen läser HTML som en sträng. En
HTML-kommentar och ett `<template>`-element är inte noder i ett parsat träd, och
en etikett räknas som en nod i stället för som en strängmatchning. `html.parser`
ur stdlib används om den räcker; krävs ett beroende ska det namnges och motiveras
före det läggs till.

**Ett larm som alltid går blir avstängt.** Modulen ska INTE kasta på att antalet
etikettelement skiljer sig från antalet par. Sidan bär det glappet av legitima
skäl, nämligen värden vars span öppnar ett element.

**Ankaret jämför hela URL:en**, alltså domän och sökväg, inte sista segmentet.
Två ankare ska KASTA i stället för att lösas tyst med första träffen: lager 3 ska
bete sig som lager 2 gör i samma läge.

**Rimlighetskontroll införs mot lucka 5.** Ett värde utanför rimligt intervall är
en felläsning och inte ett fordon. Gränserna sätts ur fixturen och ur vad som är
fysiskt möjligt, och deras ursprung skrivs ut: §7.2 tillåter avlästa tal och
utelämnade tal, inget däremellan.

**Fall 4 avgörs i båda halvorna.** Ett tal med hårt blanksteg som tusenavskiljare
SKA läsas, eftersom det är källans eget format. Kravet gäller att två tal
hopklistrade aldrig får bli ett.

**Persondatakontrollens falska positiv avgörs mot undantag.** Två konstruerade
registreringsnummer i `docs/` fällde kontrollen. Numren utgår ur dokumentet.
Ingen `TILLATNA`-post, eftersom ett undantag gäller exakt strängen och därmed
hade släppt igenom ett framtida riktigt nummer med samma tecken. Samma
avvägning som för postnummer i skiva 7.

---

## #33 — Felläst skiljs från saknat, lucka 7 stängs, och två luckor avgörs som luckor

**Datum:** 2026-09-03 · **Berör:** `src/biluppgifter.py`,
`tests/test_biluppgifter.py`, `docs/sparrar.md` `fordonsfakta-ur-sida`,
CLAUDE.md §7.1, #32

**Beslut av Lars i skiva 23.** Fem beslut, alla i sändvägen.

**1. `_tal` KASTAR i stället för att returnera `None` när fältet lästes fel.** Ett
utelämnat fält betyder VI VET INTE och ska falla till utkast. Ett värde som bär
siffror och enheten `kg` men inte går att läsa som ett tal betyder att avläsningen
är FEL. `750 2400 kg` är det andra. Ett fält som fanns men lästes fel får inte se
ut som ett fält som saknades.

Skiva 22 lät båda fallen ge `None`, alltså samma skäl nedströms. En källa som
slår ihop den bromsade och den obromsade vikten i en rad hade då sett ut precis
som en källa som slutat skriva raden alls.

**Gränsen är den avgörande delen av beslutet.** Ett värde i ett okänt FORMAT,
alltså `1200` utan enhet eller `ca 1200 kg`, ger fortfarande `None`. Kastgrenen
nås bara av siffror och blanktecken följda av `kg`. Utan den gränsen hade sidans
egna `Max 750 kg (Teoretisk)`-rader tagit hela uppslaget med sig.

**2. Lucka 9 registreras, och den går inte att stänga.** Två hopklistrade tal som
landar under 9999 kan inte skiljas från en tusengruppering: `1 200 kg` och
`750 400 kg` har samma form. Skyddet ligger i rimlighetsintervallet och inte i
formen, alltså i en gräns och inte i ett bevis.

**3. Lucka 7 stängs STRUKTURELLT.** Fotnotselement utesluts ur etikettnodens
textinnehåll innan jämförelsen. Då är `Släpvagnsvikt` med fotnot samma etikett som
utan, medan `Släpvagnsvikt obromsad` förblir en annan. **Ingen prefixmatchning:**
den mäter upp ett larm på varje verkligt svar, och ett larm som alltid går blir
avstängt. Mängden är `sup` och `small`, och att den är konventionell och inte
avläst står utskrivet i `docs/sparrar.md`.

**Uteslutningen gäller MARKÖRER och inte ord, och det ledet är byggets, inte
Lars.** En uteslutning av allt innehåll i elementet uppfyller instruktionens
första mening men BRYTER dess andra: `Släpvagnsvikt<small> obromsad</small>` blir
då `Släpvagnsvikt`, alltså den obromsade vikten levererad som den bromsade, och
hela namnet inuti elementet blir en tom etikett som räknaren inte ser. Båda är
uppmätta av granskningen av skiva 23, båda släpper ut 750 kg där 2400 är rätt.

Villkoret är därför att markören saknar bokstäver. **Lars beslut styr utfallet,
och utfallet han skrev ut är att den obromsade raden ska förbli en annan
etikett**; den snävare formen är vägen dit och inte en egen ändring av beslutet.
Att den ändå är ett tillägg står här, eftersom nästa läsare annars läser
instruktionen som om den bar villkoret.

**4. `www` godtas som samma värd.** Skiva 22:s strikthet var säker i riktningen
men producerade ett fel som inte syns: börjar källan skriva sin canonical med
`www` faller varje uppslag till utkast, utan larm och utan rött test. Boten slutar
fungera och ingen märker det. Varje annan domän avvisas fortfarande.

**5. Lucka 5 och 8 avgörs som luckor, inte som defekter.** Rimlighetsgränsen 1 till
9999 står, och inget snävare tal sätts. Den semantiska omdöpningen lämnas öppen:
den kräver en kontroll mot ett fjärde fält och är inte värd komplexiteten nu.
Skälet skrivs in i posten så att nästa läsare ser att luckan är VÄGD och inte
förbisedd.

### Vad posten INTE avgör

- **Vilket element källan faktiskt använder för en fotnot.** Fixturens avlästa
  värden bär ingen, så mängden `FOTNOTSELEMENT` är konventionell. Ett tredje
  element lämnar luckan öppen för just det.
- **Om bokstavsvillkoret ska stå kvar i den formen.** Det är byggets tillägg för
  att nå det utfall posten kräver, inte ett beslut av Lars. Villkoret bär två
  restrisker, en åt vardera hållet, och båda står som luckor i `docs/sparrar.md`:
  en markör som ÄR en bokstav, `<sup>a</sup>`, faller utanför och ger utkast,
  medan ett SKILT etikettnamn vars särskiljande led saknar bokstäver
  normaliseras in i vårt och släpper ut sitt tal. Den senare är lucka 10 och är
  den farliga riktningen. Frågan är ställd.
- **Vad som ska göras åt lucka 11.** Markup inuti ett VÄRDE konkateneras in i
  talet, så `750<sup>1</sup> kg` blir 7501, vilket ligger över tröskeln. Luckan är
  äldre än skivan och uppmätt identisk mot `8629223`. Att utesluta markörer ur
  värden vore att tyst ändra ett tal, så den lämnas registrerad och obeslutad.
- **Om `config/priser.json` finns.** #30:s led 2 står oförändrat.
- **Var driften körs.** #20 står oförändrat.

---

## #34 — Skiva 23 godkänns trots varv 3, lucka 11 stängs genom kast, lucka 10 registreras öppen

**Datum:** 2026-09-03 · **Berör:** `src/biluppgifter.py`,
`tests/test_biluppgifter.py`, `docs/sparrar.md` `fordonsfakta-ur-sida`,
`docs/incidentlogg.md` I9, CLAUDE.md §7, #33

**1. SKIVA 23 ÄR GODKÄND, trots att §7:s tredje och sista granskningsvarv
underkände.** Beslut av Lars.

**Skälet är vad fynden var, inte hur många de var.** **Varv 3:s fynd var
påståenden i `docs/sparrar.md`, utom ett: en lucka som visade sig vara ÄLDRE än
skivan och alltså inte något skiva 23 införde.** Den luckan låg i koden, i den
parser skiva 22 byggde, och stängs av skiva 24. *Här stod "inget av varv 3:s fynd
låg i koden", vilket motsades av samma stycke två rader ned och av att skiva 24
skriver kod för att stänga just den luckan. Fällt av granskningen av skiva 24.*

Granskaren skrev själv ut att sändvägen var i det skick posten beskrev:
samtliga mutationsrader röda och reproducerbara, varje nytt test bundet, hela
sviten grön. Luckan är registrerad som lucka 11 i `docs/sparrar.md`.

*Här räknades varv 3:s fynd. Räkningarna gick inte att läsa ur repot, eftersom
granskningsrapporterna ligger i gitignorerad `scratchpad/`, och §7.2 namnger den
formen som förbjuden. Fällt av granskningen av skiva 24, som i sitt andra varv
fällde en räkning till, `de tre textfynden`, i det stycke som skulle ha strukit
den första. Det som bär beslutet är VAD fynden var, och det står kvar.*

**Textfynden rättades efter grinden och är därmed självmätta, inte oberoende
granskade.** Att de rättades trots att varven var slut följer av §7:s
egen ordning: undantaget begränsar antalet omgångar, aldrig kravet på sanning, och
ett känt falskt påstående får inte skeppas. Att rätta ett känt fel är inte att
sänka kraven.

**Det här är ett beslut om EN skiva och inte en ny regel.** §7:s tre varv står
oförändrade, och nästa skiva som underkänns i varv 3 ska stoppas och rapporteras
öppet precis som skiva 23 gjorde. Skillnaden här är att grinden hade gjort sitt
arbete: varje varv fällde något som en ensam byggare inte såg.

*Här räknades fynden per varv, och stycket sade dessutom att samtliga fynd var
stängda eller registrerade. Räkningen var förbjuden form enligt §7.2. Den
universella utsagan ströks först till `varje fynd`, vilket är samma utsaga med ett
annat ord och lika obelagt, och granskningsvarv 2 fällde den igen. Den är nu
BORTA i stället för omskriven: vad som är stängt och vad som står öppet framgår av
`docs/sparrar.md`:s luckor, och den här posten sammanfattar dem inte.*

**2. LUCKA 11 STÄNGS GENOM KAST, INTE GENOM SANERING.** *Beslutet står; UTFALLET
blev DELVIS. Granskningens tredje varv mätte upp en väg till, registrerad som
lucka 12 i `docs/sparrar.md` och öppen när skivan stannade.* Ett värde som innehåller
ett element är inte ett tal och ska KASTA.

Invändningen mot att stänga luckan var att varje väg innebär att tecken plockas
bort ur ett tal vi skickar vidare. **Invändningen var riktig, slutsatsen fel.**
Ingenting plockas bort. En sida som skriver 750 med en fotnot inuti säger något vi
inte kan tolka, och rätt svar är att avläsningen är fel.

Samma regel som `750 2400 kg` fick i #33: ett fält som fanns men lästes fel ser
inte ut som ett fält som saknades.

**Kostnaden är att en fotnot i ett värde ger ett kast, och den är SYNLIG.** 7501
var det inte, och det är hela skillnaden.

**Luckan var öppen i två committade versioner**, `8629223` och `52d0a97`. Den
infördes av parsern i skiva 22 och kom fram först när skiva 23 tittade på
fotnotselement i ETIKETTER. Att den hittades av en tillfällighet och inte av en
prövning är skälet att det står utskrivet.

*Här stod `0863a8e` i stället för `52d0a97`. Fällt av granskningen av skiva 24:
`0863a8e` är skiva 21 och läser värden med regex, `git grep -n "class
_Faltlasare" 0863a8e -- src/biluppgifter.py` ger noll träffar. De två versioner
som bar parsern och därmed luckan är `8629223` och `52d0a97`, alltså mellanläget
och skiva 23:s commit.*

**3. LUCKA 10 REGISTRERAS SOM ÖPPEN SÄNDVÄGSLUCKA.** Bokstavsvillkoret i `_behall`
står; det var rätt läsning av instruktionen i #33. Men luckan är den FARLIGA
riktningen, alltså den som släpper ut ett värde, och den ska stå som en öppen
sändvägslucka och inte som ett kantfall.

**Formen är uppmätt i fixturen.** `Släp totalvikt (B)` och `Släp totalvikt (B+)`
skiljer sig bara på `+`, som inte är en bokstav. Ingen av dem är ett fält vi
läser, så formen FINNS på sidan utan att BITA i dag. Skillnaden mellan de två
leden är skälet att luckan står öppen i stället för stängd.

### Vad posten INTE avgör

- **Om lucka 10 ska stängas, och hur.** Den står registrerad med riktningen
  utskriven, inte avgjord.
- **Om `config/priser.json` finns.** #30:s led 2 står oförändrat.
- **Var driften körs.** #20 står oförändrat.

---

## #35 — Skiva 24 godkänns med lucka 12 öppen, och spärren mäter en egenskap i stället för en händelse

**Datum:** 2026-09-04 · **Berör:** `src/biluppgifter.py`,
`tests/test_biluppgifter.py`, `docs/sparrar.md` `fordonsfakta-ur-sida` lucka 11
och 12, #34

**1. SKIVA 24 ÄR GODKÄND med lucka 12 öppen och registrerad.** Beslut av Lars.

**Skälet är att luckan var MÄTT OCH SYNLIG, vilket är den säkra formen av att
inte veta.** En registrerad lucka med uppmätt utdata går att fatta beslut om. En
lucka ingen känner till gör det inte.

**Att den fjärde självmätta rättelsen inte skrevs efter förbrukad grind var
rätt.** §7:s tre varv var slut, och de två föregående rättelserna av samma spärr
var båda fel på samma sätt. En tredje gissning som ingen prövar är inte
försiktighet, den är samma fel en gång till med mindre insyn.

**2. SPÄRREN BYTER FRÅN HÄNDELSE TILL EGENSKAP.** Beslut av Lars.

**Varje tidigare lydelse har beskrivit en HÄNDELSE, och de föll på en händelse
ingen tänkt på.** Formerna är uppräknade var för sig i `_varde_bar_markup`:s
docstring: kommentar, processing instruction, declaration, ensam sluttagg, tom
tagg, sluttagg under fältet. **En händelselista går alltid att utöka med en post
till, och det är därför den fortsätter falla.**

*Här räknades lydelserna och fällningarna. Talen går inte att läsa ur repot, och
§7.2 namnger formen som förbjuden. Fällt av granskningen av skiva 25.*

**Egenskapen: VÄRDETS RÅA KÄLLTEXT SKA VARA IDENTISK MED DESS TEXTNODER.** Är den
inte det innehöll värdet markup, oavsett sort. Det villkoret går inte att utöka.
Kasta när de skiljer sig. Sanera inte, tolka inte.

**Lucka 12 stängs av samma egenskap tillämpad där den inte GÅR att mäta.** Stängs
fältet av något annat än värdets egen sluttagg är utsträckningen okänd, och då vet
vi inte hur mycket text som släpptes. Det ledet är inte en femte händelse.

**3. EGENSKAPEN GÅR ATT MÄTA MED STDLIB, alltså föll DEL B bort.** Briefen bad om
besked ifall `html.parser` inte räckte, och att inte bygga en femte händelselista i
stället. Den frågan behövde inte ställas: `getpos()` och `get_starttag_text()` ger
det som krävs, och läsaren bär källtexten. `requirements.txt` rörs inte.

**Entiteter är inte markup.** `convert_charrefs` gör `&nbsp;` till ett hårt
blanksteg i textnoden, så jämförelsen görs efter `unescape`, samma funktion
parsern själv använder. Utan det ledet hade källans eget sifferformat kastat,
uppmätt till `2 failed, 212 passed` med en fällning som tar bort `unescape`.

*Här hängdes talet 115 på det ledet, hämtat från mutationsrad 25, som mäter något
annat. Fällt av granskningsvarv 2 i skiva 25.*

### Vad posten INTE avgör

- **Om lucka 10 ska stängas.** Den står registrerad som öppen sedan #34.
- **Om `config/priser.json` finns.** #30:s led 2 står oförändrat.
- **Var driften körs.** #20 står oförändrat.

---

## #36 — Skiva 25 godkänns: varv 3 underkände, men fynden låg i texten

**Datum:** 2026-09-04 · **Berör:** `docs/sparrar.md` lucka 11 och 12,
`docs/incidentlogg.md` I10, #35

**Beslut av Lars.** Skiva 25 är godkänd, trots att §7:s tredje och sista
granskningsvarv underkände.

**Skälet är var fynden låg.** Enligt `d38b59e` godkände varv 3 kriterierna K1 och
K3 till K7, och granskaren skrev ut att alla tre fynden ligger i text: en
processräkning som låg kvar på två ställen, en statusrad som pekade på en redan
stängd lucka, och en utfallsbeskrivning i presens om ett beteende som inte längre
finns.

**Spärren själv fick godkänt.** Varje form ur lucka 11 och 12:s historia kastar,
och två oberoende produktsvep om vardera tiotusen konstruerade sidor hittade
ingen väg förbi. Mutationstabellen är delvis reproducerad av granskningen: varv 2
körde om tjugo rader och varv 3 tolv, samtliga med samma tal.

**Det här är ett beslut om EN skiva, inte en ny regel.** Samma sak sades i #34 och
gäller likadant här: §7:s tre varv står oförändrade, och nästa skiva som underkänns
i varv 3 ska stoppas och rapporteras öppet. Skillnaden är att grinden gjorde sitt
arbete och att det som återstod inte kunde nå en kund.

**Rättelserna efter grinden är självmätta, inte oberoende granskade**, och det
gäller både varv 2:s och varv 3:s.

*Fyra tal i den här posten fälldes av granskningen av skiva 26 mot `d38b59e`:
"kriterierna utom två" där källan namnger K1 och K3 till K7, "uttömmande" där
källan säger oberoende, "oberoende reproducerad i två varv" där källan säger tjugo
respektive tolv rader, och "varv 2:s sex" där källan säger fem. Talen är strukna
eller sänkta till det källan bär. Att posten återger ett granskningsförlopp gör
varje sådant tal till en processräkning enligt §7.2, och de står därför inte kvar
som summor.*

---

## #37 — Inloggningen till vyn sker som info@autostockholm.se, och #21 stängs

**Datum:** 2026-09-04 · **Berör:** `docs/roadmap.md` fas 5.5, GCP-projektet
`autostockholm-mailbot`, #21, #22

**Beslut av Lars.** Sign in with Google med `hd=autostockholm.se`, och
inloggningen sker som **info@autostockholm.se**, alltså det konto som redan
finns.

**INGEN WHITELIST. INGEN NY LICENS. INGET NYTT KONTO.**

**Skälet.** Kontot finns, det ligger på domänen, och Internal-spärren släpper
igenom det. Ingen av #21:s tre vägar behöver alltså väljas: kostnaden i väg 1 var
en Workspace-licens, väg 2 bröt mot #22, och väg 3 avvisades redan.

**#21:S WHITELIST GICK ALDRIG ATT BYGGA, och det är den avgörande upptäckten.**
En app vars user type är Internal avvisar konton utanför organisationen med
`org_internal` INNAN appen får se någon identitet. Whitelisten hade därför aldrig
fått något att pröva. Beslutet river alltså inte en fungerande konstruktion, det
stryker en som inte kunde fungera.

**BÅDA #21:S ÖPPNA PUNKTER STÄNGS.** Öppen punkt 1 var sakkonflikten mellan
whitelist och Internal, och den upphör med whitelisten. Öppen punkt 2 var om Lars
privata adress kan stå i repot, och den upphör därför att adressen aldrig behövs.
**Den hamnar därmed aldrig i repot**, vilket är det utfall §6 pekar mot.

**KOSTNADEN, och den ska stå utskriven.** Med ett DELAT konto signeras varje
omdöme av `info@`, och `logg/omdomen.jsonl` skiljer inte Lars från Matte.

Så länge Lars ensam granskar spelar det ingen roll: alla omdömen är hans, och
loggen är entydig i sak även om den inte är det i namn. **Kopplas Matte in senare
krävs ett eget konto**, och det är ett eget beslut som ska fattas då. Fas 5.5:s
grind mäter omdömesvolym och inte vem som fällde omdömet, så inget nedströms
kräver åtskillnaden i dag.

**EN SPÄNNING MOT FAS 5.5:S EGEN LYDELSE, och den ska stå utskriven.** Fasen
inleds med att vyn är där *"Lars och Matte"* läser förslagen. Den meningen är
äldre än det här beslutet och rörs inte, men den beskriver en användning som
kräver det egna konto posten skjuter upp. **Så länge fasen byggs och används av
Lars ensam finns ingen konflikt**, och den dag Matte kopplas in är kontot en del
av samma beslut.

**Egen OAuth-klient av typen Web application**, skild från `mailbot-cli`, i samma
projekt och med samma consent screen. Det är #22 oförändrat, och det fungerar nu
när ingen extern identitet ska släppas in.

---

## #38 — Hosting: Railway, och mailagent.dasher.se pekas dit med CNAME

**Datum:** 2026-09-04 · **Berör:** `docs/roadmap.md`, `token.json`, `data/`, #20

**Beslut av Lars.** Boten hostas på **Railway**. `mailagent.dasher.se` pekas dit
med CNAME. Detta kompletterar #20, som avgjorde att HELA boten flyttar och till
vilken ADRESS, men inte på vilken VÄRD den körs. *Här stod "men inte VART", vilket
är falskt om #20: dess rubrik namnger adressen. Fällt av granskningen av skiva
26.*

**Skälet, alternativ för alternativ.** #20 flyttar hela boten och inte bara vyn,
alltså krävs en långlivad process med persistent disk och schemalagd mining.

- **Cloudflare Workers** saknar båda. En worker är kortlivad och har ingen disk.
- **Cloudways** är WordPress-hosting och fel maskin för kundmail.
- **Vultr** fungerar, men ger en VPS att underhålla.
- **Railway** ger deploy från repot, HTTPS, volume, cron och miljövariabler, och
  Lars kör det redan i ett annat projekt.

**BINDANDE: `token.json` OCH `data/` LIGGER PÅ ETT PERSISTENT VOLUME, aldrig i
containern.** Railway kör om containern vid varje deploy och allt i den
försvinner. Skrivs det inte in i fasen från början upptäcks det i drift, och det
som försvinner är en token som kostar en ny auktorisering och en `data/`-katalog
som bär hela underlaget.

**RISKFÖRFLYTTNINGEN, och den ska vara utskriven.** Två filer flyttar till en
tredjepartsleverantör:

- **`data/par.jsonl` bär kundtext.** Faktiska mail från namngivna personer.
- **`token.json` kan skicka mail som info@autostockholm.se.** Scopet
  `gmail.send` finns i den.

#20 skrev ut det andra ledet som en flytt av var ett intrång måste ta sig in.
Den här posten lägger till det första: efter flytten ligger kundtexten hos
Railway, och det är en behandling av persondata hos en leverantör och inte bara
en driftfråga.

**Vad som INTE följer.** Ingen sändning aktiveras. §10:s stopp om första
sändningen i en NY MILJÖ gäller Railway, oavsett vad som skickats från Lars
maskin.

**Öppen punkt ur #20 kvarstår:** hur `token.json` och `client_secret.json` skyddas
från annat som kör på servern. Railway ger volume och miljövariabler; vilket som
används och med vilka rättigheter är inte avgjort här.

---

## #39 — Fas 5.5 flyttas före fas 5, och vyn får ett krav den inte var specad för

**Datum:** 2026-09-04 · **Berör:** `docs/roadmap.md` fas 5 och 5.5,
`data/par.jsonl`, #11, #13

**Beslut av Lars.** Fas 5.5, utkastvyn, byggs FÖRE fas 5, mallar och spärrar.

**Skälet.** Lars ska skriva fyra till fem referenssvar direkt i vyn. **Rösten
skapas alltså där**, och mallarna i fas 5 byggs ur de svaren tillsammans med
`data/par.jsonl`. Ordningen i den gamla roadmapen hade krävt att mallarna fanns
innan Lars skrivit något, och att Lars skrev i en vy som inte fanns.

**KRAVET SOM FÖLJER, och som vyn inte var specad för: den ska kunna visa ett
inkommande mail UTAN att boten genererat ett förslag.** Tomt fält, Lars skriver,
det sparas som ett par.

Utan det finns ingenting att skriva innan mallarna finns, och mallarna kan inte
finnas innan Lars skrivit. Fas 5.5:s ursprungliga spec utgick från att varje post
i vyn bär ett botgenererat förslag som ska bedömas med ett av fyra omdömen. Den
utgångspunkten gäller inte längre för de första posterna.

**BINDANDE: ETT REFERENSSVAR SKICKAS ALDRIG.** Kunderna har fått svar för länge
sedan eller inte alls. Vyn sparar texten som ett par i `data/par.jsonl`, aldrig
som utgående mail.

**Det är en ANNAN KNAPP än den vyn var specad för, och den måste vara omöjlig att
förväxla.** Fas 5.5 bär sedan tidigare raden att vyn aldrig skickar mail; den här
posten skärper den till att vyn nu har ett textfält vars innehåll ser ut precis
som ett svar och som ändå aldrig får nå en kund.

**Förhållandet till `forbattra`.** Omdömet `forbattra` skriver också ett nytt par
till `data/par.jsonl`, och referenssvaret gör detsamma. Skillnaden är att
`forbattra` förutsätter ett förslag att förbättra. Referenssvaret är samma
skrivning utan förslaget, och båda vägarna slutar i samma fil.

**#13 gäller oförändrat:** `data/par.jsonl` är RÅ. Ett referenssvar skrivs dit
som det skrevs, utan efterbehandling.

---

## #40 — En spärrfälld post visar aldrig ett textfält, oavsett läge

**Datum:** 2026-09-04 · **Berör:** `docs/roadmap.md` fas 5.5, `src/vy.py`,
`docs/sparrar.md`, CLAUDE.md §9.1, #39

**Beslut av Lars.** Detta stänger den öppna punkt #39 lämnade efter sig, och som
fas 5.5 bar utskriven: vad som gäller när en post har både ett spärrfällt förslag
och ett behov av ett referenssvar.

**EN SPÄRRFÄLLD POST VISAR ALDRIG ETT TEXTFÄLT, OAVSETT LÄGE.** §9.1 väger tyngre
än bekvämligheten att kunna skriva ett referenssvar på just den posten.

**Behövs en referens för ett ärende vars förslag fälldes, tas en annan post av
samma kategori.** Det kostar ingenting: referenssvaret är underlag för rösten och
inte ett svar på det enskilda ärendet.

**Skälet, med Lars ord:** en textruta på en spärrfälld post gör förbudet till ett
klick även när knappen heter spara och inte skicka. Vyn ska inte lära handen den
rörelsen.

**Det är en regel om GRÄNSSNITTET, inte om texten.** Ett referenssvar når aldrig
en kund, alltså skulle ingen omskrivning på en fälld post faktiskt skicka något.
Invändningen missar vad §9.1 skyddar mot. Förbudet gäller rörelsen att skriva om
ett fällt mail tills det ser bra ut, och en vy som övar in den rörelsen på
ofarliga poster har lärt ut den när posterna inte längre är ofarliga.

**Byggt i skiva 27.** `rendera_granskning` i `src/vy.py` returnerar sidan utan
`<textarea>` och utan `<button>` när ett spärrnamn är satt. Spärren är
registrerad i `docs/sparrar.md` med sin negativkontroll.

---

## #41 — Vyns poster i par.jsonl bär `kalla` och `utfall`, och det är mitt tillägg

**Datum:** 2026-09-04 · **Berör:** `data/par.jsonl`, `src/vy.py`, #11, #13, #39

**Detta är INTE ett beslut av Lars.** Det är ett val jag gjorde när skiva 27
byggde skrivvägen, och det står här för att det ändrar formen på en fil som andra
läsare räknar poster ur. Lars kan riva det.

**Vad som lades till.** En post som vyn skriver bär, utöver de fyra ursprungliga
nycklarna, fälten `kalla` satt till `referenssvar`, `utfall`, `etikett` och
`skrivet`.

**Skälet till `kalla`.** Utan markören blandar `data/par.jsonl` ihop två olika
saker: svar som FAKTISKT skickades till en kund, skrivna av Matte eller Lars i
sin tid, och referenssvar som aldrig lämnat vyn. #11 säger att filen räknar
svarsinstanser, och en senare läsare hade räknat referenssvaren som skickade
svar. Det är den sortens tysta felräkning §7.2 finns för.

**Skälet till `utfall`.** Fas 4.5:s fyra utfall grönt, gult, oklart och rött går
inte alltid att avgöra utan ett fordonsuppslag. Fältet låter Lars ange utfallet
för hand när han skriver svaret, och tomt är ett tillåtet värde.

**#13 står orört.** De fyra ursprungliga nycklarna är oförändrade och texten
skrivs RÅ. Varje befintlig läsare av filen fortsätter fungera, eftersom de nya
fälten är tillägg och inte omtolkningar.

**ÖPPEN PUNKT:** om mallbygget i fas 5 ska läsa referenssvaren tillsammans med de
skickade svaren eller hålla dem isär. `kalla` gör båda möjliga; vilket som gäller
är inte avgjort.

---

## #42 — Skiva 27 godkänns, och #41 står

**Datum:** 2026-09-04 · **Berör:** `src/vy.py`, `data/par.jsonl`, #34, #36, #41

**Beslut av Lars.** Skiva 27 är godkänd, trots att §7:s tredje och sista
granskningsvarv underkände.

**Skälet är detsamma som i #34 och #36, med ett tillägg.** Där låg fynden i
texten och inte i spärren. Här låg det sista fyndet i KODEN, och det är just
därför skivan godkänns: hålet är stängt. Alternativet var att skeppa en spärr som
inte såg relativa importer, alltså ett känt sändvägshål, och det är sämre än att
skeppa en självmätt rättelse med statusen utskriven.

**De självmätta rättelserna granskas i skiva 28**, som en egen omgång på dem och
bara på dem. Att godkänna skivan är alltså inte att godkänna rättelserna
ogranskade, utan att flytta granskningen av dem till en egen grind.

**#41 STÅR.** `kalla` löser ett verkligt problem: utan markören blandar
`data/par.jsonl` ihop svar som FAKTISKT skickades till en kund med referenssvar
som aldrig lämnat vyn, och #11 räknar svarsinstanser ur filen. De fyra
ursprungliga nycklarna är orörda, alltså gäller #13 oförändrat.

Posten #41 är fortfarande märkt som mitt val och inte Lars beslut. Det här
beslutet gör inte om den till hans; det säger att den får stå.

---

## #43 — Lucka 13 väntar, och skälet är vad lucka 12 kostade

**Datum:** 2026-09-04 · **Berör:** `docs/sparrar.md` lucka 12 och 13,
`src/vy.py`, #38

**Beslut av Lars.** Lucka 13, att sändvägsspärren räknar upp modulnamn och
anropsformer i stället för att mäta en egenskap, stängs INTE nu.

**Egenskapen är rätt riktning.** Det är samma riktning lucka 12 tog i skiva 25,
och den ordningen är inte ifrågasatt.

**Men vyn saknar inloggning och är inte exponerad.** Den kör på `127.0.0.1` och
har ingen sändväg alls. Uppräkningen räcker tills vyn ska ut på Railway enligt
#38, och den flytten är en egen skiva med egen grind. Då, och inte innan, är
uppräkningen otillräcklig.

**SKÄLET ATT VÄNTA ÄR MÄTT, inte principiellt.** Avläsningen av fordonsfakta ur
en sida tog fem skivor: `0863a8e`, `8629223`, `52d0a97`, `64b56e4` och
`d38b59e`, alltså skiva 21 till 25. Skiva 21 bar redan klassen, att ett mönster
skrivet för sidans nuvarande markup TYSTNAR i stället för att kasta.

**Två metodbyten behövdes, inte ett.** Skiva 22 bytte regex mot `html.parser` på
beslut i #32. Först därefter kunde spärren mot markup i ett värde formuleras, och
den formulerades som en HÄNDELSELISTA som föll om och om igen, tills skiva 25
bytte till att mäta EGENSKAPEN.

*Här stod att varje mellanliggande skiva rättade en uppräkning med en längre.
Det är falskt om skiva 22, som bytte metod och som dessutom införde lucka 11 i
stället för att rätta en uppräkning: spärren mot markup fanns inte än. Fällt av
§7-granskningen av skiva 28, varv 2.*

**Lärdomen ska användas och inte upprepas.** Att byta från uppräkning till
egenskap är rätt drag, men det är ett drag som förtjänar en egen skiva med egen
grind, inte ett tillägg till en skiva som gör något annat. Lucka 13 stängs när
vyn ska exponeras, och då som skivans enda uppgift.

---

## Appendix — versionshistorik (nyaste överst)

### 0.33.0 — 2026-09-04

**Två poster tillkommer, båda beslut av Lars i skiva 28.**

- **#42** godkänner skiva 27 och låter #41 stå. Skälet skiljer sig från #34 och
  #36 på en punkt som skrivs ut: där låg fynden i texten, här i koden.
- **#43** låter lucka 13 vänta till den skiva som exponerar vyn, med lucka 12:s
  kostnad som mätt skäl.

**#43:s tal är namngivna commits och inte en processräkning.** De fem skivorna
står som SHA:n, så räkningen går att göra om ur repot. §7.2 förbjuder räkningar
av ett arbetsförlopp som repot inte bär; den här bär det.

Två nya poster ⇒ MINOR.

### 0.32.0 — 2026-09-04

**Två poster tillkommer, och bara den ena är ett beslut av Lars.**

- **#40** stänger #39:s öppna punkt: en spärrfälld post visar aldrig ett
  textfält, oavsett läge. Beslut av Lars i skiva 27, och byggt i samma skiva.
- **#41** redovisar ett val JAG gjorde, alltså inte ett beslut av Lars: vyns
  poster i `data/par.jsonl` bär fyra nya fält. Posten står i loggen därför att
  den ändrar formen på en fil som andra läsare räknar ur, och den säger rakt ut
  vem som bestämt vad.

**Att en post som inte är Lars beslut ligger i beslutsloggen är en avvikelse och
den är avsiktlig.** Alternativet var att lägga ändringen bara i en docstring, där
ingen som räknar par i `data/par.jsonl` hade hittat den. Posten är märkt i sin
första mening.

Två nya poster ⇒ MINOR.

### 0.31.0 — 2026-09-04

**Fyra poster tillkommer**, samtliga beslut av Lars i skiva 26:

- **#36** godkänner skiva 25, med skälet att varv 3:s fynd låg i texten och inte
  i koden.
- **#37** avgör inloggningen till vyn: `info@autostockholm.se`, ingen whitelist.
  **#21 stängs**, och båda dess öppna punkter med den. **#21:s text har fått en
  stängningsruta överst**, alltså en redigering på plats i en committad numrerad
  post. Loggens huvud tillåter det bara för att stryka en känd falskhet; det här
  är en markör och inte en strykning, och den redovisas därför här.
- **#38** avgör hostingen: Railway, med `mailagent.dasher.se` via CNAME. Bindande
  krav på persistent volume, och riskförflyttningen utskriven.
- **#39** flyttar fas 5.5 före fas 5 och ger vyn ett krav den inte var specad
  för.

**#21 stängs av att dess konstruktion visade sig omöjlig**, inte av att ett val
gjordes mellan dess vägar. Whitelisten kunde aldrig få något att pröva bakom en
Internal-app. Det som är avläsbart nytt är markören: `grep -n "STÄNGD"
docs/beslutslogg.md` ger en enda träff, rutan i #21.

*Här stod att #21 är den FÖRSTA posten som stängs så. Det är ett superlativ utan
namngiven källa, och loggen bär närliggande fall: #17 ströks därför att undantaget
aldrig nådde det skydd det var ett undantag från, och #4 upphävde en anvisning som
beskrev en träff kommandot inte producerar. Fällt av granskningen av skiva 26.*

Fyra nya beslutsposter ⇒ MINOR.

### 0.30.0 — 2026-09-04

**#35 tillkommer:** skiva 24 godkänns med lucka 12 öppen och registrerad, och
spärren mot markup i ett värde byter från att beskriva en HÄNDELSE till att mäta
en EGENSKAP. Två beslut av Lars i skiva 25.

Posten skriver ut varför en registrerad lucka är den säkra formen av att inte
veta, och varför en händelselista alltid går att utöka med en post till.

Ny beslutspost ⇒ MINOR.

### 0.29.0 — 2026-09-03

**#34 tillkommer:** skiva 23 godkänns trots varv 3:s underkännande, lucka 11
stängs genom kast, och lucka 10 registreras som öppen sändvägslucka med
riktningen utskriven. Tre beslut av Lars i skiva 24.

Godkännandet är ett beslut om EN skiva. §7:s tre varv står oförändrade, och
posten skriver ut det.

Ny beslutspost ⇒ MINOR.

### 0.28.0 — 2026-09-03

**#33 tillkommer:** felläst skiljs från saknat i `_tal`, lucka 7 stängs
strukturellt, `www` godtas som samma värd, lucka 9 registreras, och lucka 5 och 8
avgörs som luckor med skäl utskrivna. Fem beslut av Lars i skiva 23, samtliga i
sändvägen.

Posten ligger EFTER #32, alltså i nummerordning, enligt 0.27.2.

Ny beslutspost ⇒ MINOR.

### 0.27.2 — 2026-09-03

**#32 LÅG FYSISKT FÖRE #31, OCH LIGGER NU EFTER.** Påpekat av Lars i skiva 22.
Loggen är sekventiell, alltså ska den fysiska ordningen följa numren. Posten
skrevs in ovanför #31 när den skapades, och `grep -n "^## #"` visade därför #32
på ett lägre radnummer än #31.

**Ingen posttext är ändrad, och det är hela poängen med att redovisa det här.**
Blocket är flyttat oförändrat, vilket syns i diffen: de borttagna och de tillagda
raderna är samma text. Skarven fick dessutom det `---` som saknades mellan #32
och #31. `grep -c "^---$"` ger 32 i den committade filen och 33 efter flytten.

**Färskhetskontrollen i CLAUDE.md §12 påverkas inte.** Den läser högsta numret
och inte radordningen, och det är fortfarande #32.

Flyttad post, ingen ändrad text ⇒ PATCH.

### 0.27.1 — 2026-09-02

**0.27.0-posten fick en statusrubrik som saknades.** Skiva 19 förbrukade §7:s tre
granskningsvarv, varv 3 underkände formellt på kriterierna 2, 4, 5, 8 och 9, och
rättelserna är självmätta. Tillagd i efterhand på Lars beslut i skiva 20, i samma
form som skivorna 15 till 18 bar.

Posten bär också två saker som annars går förlorade: att granskningsrapporterna
låg i `/tmp` i den dåvarande sandboxen och inte är bevarade, och att
commitmeddelandet för `3c7c751` bar underkännandet men inte att rättelserna är
oberoende ogranskade.

**Ingen ny beslutspost.** Skiva 20 fattar inget beslut och journalför en status
som redan gällde, så `Speglar` i CLAUDE.md står kvar på #31.

**Granskningsomgången fällde skälet till kriterienumren.** Meningen stod i presens
och sade att ett nummer går att slå upp mot granskningen, vilket nästa stycke i
samma post upphäver: rapporterna finns inte. Den står nu i konditionalis, och
härkomsten är utskriven — kriterium 5 är belagt i commitmeddelandet, medan 2, 4,
8 och 9 kommer ur överlämningen och inte går att kvittera mot repot.

**STATUSEN GÄLLER ÄVEN DEN HÄR SKIVAN.** Dokumentdetaljundantaget ger en
granskningsomgång, och den är förbrukad. Fynden i den är rättade, och de
rättelserna är **självmätta**. Undantaget begränsar antalet omgångar, aldrig
kravet på sanning: de två falska påståendena rättades därför att §7 förbjuder att
skeppa ett känt falskt påstående, inte därför att en omgång fanns kvar.

Tillägg till en befintlig post ⇒ PATCH.

### 0.27.0 — 2026-09-02

**#31 tillkommer.** Datakällan för fas 4.5 är vald: den öppna fordonssidan, inte
PRO-API:t. Ny post ⇒ MINOR.

Posten stänger #23:s öppna punkt i BÅDA leden. Datakällan är vald. Avtalsledet
avgjorde Lars samma dag genom att stryka det: **källans användarvillkor läses
inte.** **Fas 4.5:s grind är därmed passerad**, av beslutet och inte av koden, och
grindrutan i `docs/roadmap.md` är omskriven till samma lydelse.

*Posten bar först rubriken ÖPPEN PUNKT och lydelsen att grinden inte var passerad.
Det var sant när den skrevs och står inte kvar: avsnittet heter nu AVGJORT AV LARS
och journalför beslutet i stället för att vänta på en åtgärd. Vad beslutet inte
innebär är utskrivet där: risken är oläst och accepterad, inte bedömd, och ingen
spärr ska läsas som ett juridiskt godkännande.*

Posten bär också att ordningen var omvänd: `src/biluppgifter.py` skrevs före
beslutsposten, vilket är det #23:s sista mening förbjuder. Utskrivet i posten
i stället för utelämnat.

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skiva 19 förbrukade alla tre, och **varv 3 UNDERKÄNDE FORMELLT på kriterierna
2, 4, 5, 8 och 9**. Fynden är rättade. **RÄTTELSERNA ÄR SJÄLVMÄTTA, INTE
OBEROENDE GRANSKADE.**

Kriterienumren står utskrivna och inte bara fyndklasserna, eftersom ett nummer
HADE gått att slå upp mot granskningen och en klass inte hade det. Att
uppslagningen inte längre går att göra ändrar inte vilket av de två som bär mer.

**DETALJERNA BAKOM KRITERIERNA ÄR INTE ÅTERFINNBARA.** Granskningsrapporterna låg
enligt överlämningen i `/tmp` i den dåvarande sandboxen och är inte bevarade,
varken i repot eller någon annanstans. Vad varje kriterium prövade går alltså
inte att slå upp, och det står här i stället för att läsaren ska tro att
materialet finns någonstans.

**NUMREN HAR OLIKA HÄRKOMST.** Kriterium 5 är belagt i commitmeddelandet för
`3c7c751`. Kriterierna 2, 4, 8 och 9 kommer ur Lars överlämning till skiva 20 och
går inte att kvittera mot repot.

**Commitmeddelandet för `3c7c751` bar en del av detta och dokumenten ingen.**
Meddelandet skriver att varv 3 underkände på fyra kodfynd och två
dokumentdetaljfynd, samtliga rättade. Det är riktigt, men det säger inte att
rättelserna är oberoende ogranskade, och en läsare av dokumenten såg ingenting
alls. Rubriken ovan är tillagd i efterhand på Lars beslut i skiva 20, och
tillägget redovisas i 0.27.1.

### 0.26.0 — 2026-08-28

**#30 tillkommer:** grindvillkoret "Ingen kategori startar i `auto`" stryks,
#29:s öppna punkt om prisfrågan avgörs, och fas 4 får sina egna filer.

Posten redovisar att `docs/kategorier.md` INTE behövs och varför: hinken står i
`config/kategorier.yaml`, namnen i `docs/kategorier-forslag.md`, och definitioner
utöver namnen finns inte, eftersom pass 2 ger modellen enbart namnen. §0:s rad
pekar därför på yaml-filen i stället.

Prisfrågans svar bär två led, och led 2 är det som hindrar en automatisk flytt
när `config/priser.json` fylls. Utan det hade led 1 gjort flytten till en
följdverkan av att en fil får innehåll, alltså till något kod kunde utlösa.

`scripts/kategoristatus.py` faller högljutt när en källa saknas eller inte går
att läsa, i stället för att skriva en halv statusrad. Ett fel i felhanteringen
hittades av testerna: `relative_to` kastar för sökvägar utanför repot.

**Rättelser efter §7-granskningen, per post.** Påståendet att två av fyra källor
bär kundtext var fel; bara `data/ometiketterade.jsonl` gör det, och
`data/taxonomi.json` är ocommittad enbart därför att `data/` är gitignorerad. En
räkning av hur många skivor §12:s hål stått var varken avläst eller tillåten
enligt §7.2 och är struken. En testdocstring sade att alla kategorinamn var
påhittade; tre är verkliga, med avsikt. §7.1-redovisningen namngav varken rad,
utdata eller om fällningen var en radering, vilket §7.1 kräver.

**Prövningen avslöjade dessutom ett lagrat försvar**, och den delen är ett fynd
i sak: existenskontrollen och `except OSError` ger båda `Saknas` för en saknad
fil, så en ensam fällning gav GRÖN. Verdiktet sattes först efter att båda lagren
fällts.

Två kvarlämnade motsägelser är också rättade: en testdocstring och yaml-filens
företrädesregel pekade båda på #29:s öppna punkt, som den här posten avgör.

**Andra granskningsvarvet fällde §7.1-tabellen, och mekanismen är den §7 varnar
för.** Tabellens radnummer var riktiga när prövningen kördes och föråldrades av
rättelsen av ett ANNAT fynd i samma skrivning: `las_text`:s docstring växte, och
varje nummer under den sköts ner lika mycket. Svitens utdata var dessutom räknad
före de två vakter samma varv införde. Tabellen citerar nu raderna i stället för
att numrera dem, prövningarna är omkörda mot filen som levereras, och de två nya
vakterna är med.

**#29:s båda öppna punkter bar kvar sin presens.** Den om prisfrågan sade att
ingen tolkning var vald, och den om `docs/kategorier.md` att frågan var
obestämd. Båda avgörs av den här posten, och båda bär nu en kursiv not.

**Tredje varvet fällde samma mekanism en gång till.** Stycket om lagrat försvar
numrerade två rader, tolv rader under rubriken som säger att rader ska citeras
och inte numreras. Rättelsen av tabellen tillämpades inte på stycket rakt under
den. Talet "sex steg" gick dessutom inte att belägga, eftersom filen var otrackad
och ingen tidigare version finns i git; det är struket i stället för omräknat.
`Berör`-raden saknade `tests/test_kategorier_yaml.py`, vilket är tredje skivan i
rad som fäller den raden.

**Ett fynd i varv 3 höll INTE, och det ska stå här.** Granskaren skrev att
`src/kategorisera.py` lägger till en post per kundmeddelande och inte en per
tråd, och att docstringens formulering därför är falsk. Loopen i
`texter_att_kategorisera` avslutas med ett ovillkorligt `break` sist i
kroppen, så den tar trådens FÖRSTA kundmeddelande och bryter. Påståendet står
kvar oförändrat. Granskaren hade sannolikt `kontext_per_text` i sikte, som
skiva 17 ändrade från `break` till `continue` av just det skälet att den ska se
varje kundmeddelande.

**GRINDEN ÄR FÖRBRUKAD FÖR DEL C, OCH DET SKA SYNAS.** §7 ger max tre
granskningsvarv. DEL C förbrukade alla tre och det sista underkände också.
Fynden i det varvet är rättade, men de rättelserna är **självmätta och inte
oberoende granskade**. DEL A och B åberopade dokumentdetaljundantaget och
förbrukade sin enda omgång i varv 1; deras rättelser i varv 2 och 3 är
självmätta av samma skäl.

Rättelserna gjordes därför att §7 förbjuder att skeppa ett känt falskt påstående
även när varvsgränsen eller undantaget är uttömt. Gränsen begränsar antalet
granskningar, inte kravet på sanning.

Ny post ⇒ MINOR.

### 0.25.0 — 2026-08-28

**#29 tillkommer:** kanalen blir kontext i klassificeringen, och fas 4:s grind
fattas.

DEL A bär mätningen som föranledde bygget: av 78 formulärtrådar klassades 42 som
något annat än en a-traktorkategori. Posten skriver ut att ingen kod mappar kanal
till kategori, och hur den regeln fälldes enligt §7.1 genom att den förbjudna
kopplingen SKREVS DIT. Den skriver också ut att korpusen inte etiketteras om.

DEL B återger Lars diktamen och hans skäl, och noterar utan att besluta att
`boka biltvätt` har noll svar av elva.

**Rättelser efter §7-granskningen, per post.** `kontext_per_text` var helt
otestad och gick att neutralisera utan att ett enda test föll; den har nu tester
för konfliktfallet, positionskollisionen, nollfallen och den tomma texten.
Funktionens konfliktvakt såg bara trådarnas FÖRSTA kundmeddelanden och kunde
därför ge fel kanal till en par-text från en senare position; indexet täcker nu
varje kundmeddelande. `scripts/etikettera-nya.py` byggde poster utan kontext, så
den enda körbara vägen levererade ingenting av fixen. Påståendet att anropet är
teckenidentiskt utan kontext var falskt och gällde bara användarmeddelandet.
Superlativet om obesvarade texter saknade kvalifikationen KUNDKATEGORI, och
`inget kundärende` bär 536. `config/kategorier.yaml`:s kommentar sade "bara en
kategori" utan samma kvalifikation och räknade två kriterier medan filen själv
tillämpade ett tredje. `Berör`-raden var ofullständig mot diffen.

**Andra granskningsvarvet fällde, per post.** `config/kategorier.yaml` lovade att
inte återge skäl och återgav dem sedan; kommentarerna namnger nu kriteriet och
pekar vidare. Filens två förklaringar till varför prisfrågan står i utkast gick
inte ihop, och den motsägelsen är INTE omskriven utan lyft som en öppen punkt.
Rättelsen av `scripts/etikettera-nya.py` var varken exekverad eller testad,
eftersom torrkörningen filtrerar bort varje kandidat innan raden nås;
`tests/test_etikettera_nya.py` binder den nu och en fälld kontext ger RÖD.
Påståendet om varför `Växellåda` finns i formuläret stod under rubriken
"uppmätt" men är Lars uppgift. En processräkning om hur många skivor talen
räknats om i är struken.

**Granskningen fann också ett fel i §7.1:s eget verktyg**, se
`docs/incidentlogg.md` I7. En kvitterad återställning lämnade fällningens kod
kvar i bytekoden, och repots svit var röd utan att någon rad bar felet.
`scripts/sparr-prova.sh` städar nu `__pycache__` i båda riktningarna och
kvitterar att katalogerna är borta.

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skivan förbrukade alla tre och det sista underkände också. Fynden i det varvet är
rättade, men de rättelserna är **självmätta och inte oberoende granskade**:

- **Ett sändvägsgap.** `texter_att_kategorisera`:s inkoppling av kontexten gick
  att strippa i BÅDA grenarna utan att ett test föll. Hela DEL A kunde alltså
  tas bort ur den fulla korpusvägen tyst. Tre tester binder den nu, och båda
  grenarna ger RÖD vid fällning. Det är samma defektklass som varv 2 fällde för
  systerfunktionen, åtgärdad där och lämnad kvar här.
- En testdocstring valde den tolkning av prisfrågan som den här posten säger att
  ingen valt.
- `config/kategorier.yaml` lovade fortfarande att inte återge resonemang och
  gjorde det sex rader ned.
- Bisatsen "aldrig mindre" är Lars bedömning och står nu som det.
- `CLAUDE.md` räknade fyra nya filer där det är fem, och `Berör`-raden var
  ofullständig mot diffen igen.
- Verktygsåtgärden täckte bara den riktning incidenten visade.

Rättelserna gjordes därför att §7 förbjuder att skeppa ett känt falskt påstående
även när varvsgränsen är uttömd. Gränsen begränsar antalet granskningar, inte
kravet på sanning.

**En sakkonflikt är utskriven, inte tyst löst.** `docs/roadmap.md` fas 4 sade
"Ingen kategori startar i `auto`". Lars beslut lägger en kategori där. Villkoret
var en förväntan och inte en ramverksregel, meningen står kvar oförändrad, och en
not under fasen säger att den inte längre beskriver läget.

Ny post ⇒ MINOR.

### 0.24.0 — 2026-08-28

**#28 tillkommer:** de 66 texterna etiketterade, föreskriften att avläsaren i fas
4.5 ska vara skiftlägesokänslig, och `scripts/` under persondatakontrollen.

Posten redovisar fördelningen per kategori och per kanal, att `Med svar` står
oförändrad på 213, och en öppen fråga som den inte avgör: bara 8 av formulärets
23 texter hamnade i en a-traktorkategori trots att ämnesraden är en
offertförfrågan om A-traktor. Skälet är inte mätt och gissas därför inte.

**Rättelser efter §7-granskningen, per post.** Uppräkningen av vad formulärets
övriga texter blev sade "de övriga" men täckte 12 av 15 och motsades av postens
egen kanaltabell; den redovisar nu alla tre delmängderna. En karakterisering av
vad de icke-kundärenden innehåller var inte mätt, och är struken: det är samma
defekt som den kursiva rättelsen i #9 redan bär. Påståendet att §6-mönstret är
versalkänsligt MED AVSIKT var en slutsats och inte ett citat, och skiljs nu från
det avlästa. `Berör`-raden utelämnade skivans huvudleverabel. Talet 41 bär två
betydelser i posten och har fått en varning i repots befintliga form.

**Andra granskningsvarvet fällde, per post.** Skivans egen ändring av `BEVAKADE`
gjorde ett led i #21:s ÖPPEN PUNKT 2 falskt, nämligen att väg 1 flyttar adressen
till en obevakad fil. #21 bär nu en kursiv not, **och en sådan not är också
inlagd i #21:s egen appendixpost**, som upprepade påståendet. #28 upphäver ledet
uttryckligen, och punktens slutsats står kvar av ett annat skäl.

**Kursiva noter är också inlagda i #27**, på tre satser som skiva 16 gjorde
falska: a-traktortabellens tal 25/12/7, att de 43 texterna är oetiketterade, och
att de 66 är det. Alla tre gällde när #27 skrevs och är föråldrade av
etiketteringen, inte felaktiga då. #27:s slutledning att
formulärets 23 texter är a-traktorärenden av kanalens konstruktion är
ifrågasatt med en not, eftersom bara 8 blev det. Tokentalen är märkta som
icke reproducerbara. `--rapport` och `--redovisa` var odokumenterade här.

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skivan förbrukade alla tre och det sista underkände också. Fynden i det varvet är
rättade, men de rättelserna är **självmätta och inte oberoende granskade**: tre
satser i #27 som skivans egen etikettering gjorde föråldrade, en versionspost i
`docs/sparrar.md` som påstod som faktum det den själv sagt var en slutsats, och
en kursiv not i `docs/roadmap.md` som sade att den strukna meningen bar ett tal.
Den bar inget; talet stod i meningen före, avläst ur `be560a4`.

Rättelserna gjordes därför att §7 förbjuder att skeppa ett känt falskt påstående
även när varvsgränsen är uttömd. Gränsen begränsar antalet granskningar, inte
kravet på sanning.

Ny post ⇒ MINOR.

### 0.23.0 — 2026-08-28

**#27 tillkommer:** besvarad avgörs av ett svar i tråden, aldrig av vilken
skördefil tråden ligger i. Lars regel om att en Gmail-etikett aldrig får vara
ensam grund för en klassning, dess uppmätta instans, den omräknade korpusen,
bokningsnotiserna och prefixförbehållet.

Posten redovisar också att briefens premiss inte stämde: kolumnen *Med svar* tas
ur `data/par.jsonl` och var aldrig påverkad. Det var den obesvarade sidan som
räknade för lågt.

**#9 får en kursiv not och upphävs i den del som gäller besvarat.** Dess rubrik
säger att de obesvarade är tre gånger fler, och dess brödtext skriver ut talen
1604 mot 555. Båda beskriver skördarnas storlek och inte besvarat mot obesvarat. Mätt på ett svar i
tråden är förhållandet 139 mot 2020. Posten i övrigt står kvar, och dess slutsats
blir starkare av rättelsen.

**Rättelser efter §7-granskningen av den här skivan, per post.** Ett superlativ om
vilken kategori som påverkas mest är struket och ersatt med det som är mätt, att
webbformuläret är den enskilt största kanalen bland de 92. En självrapportering om
att ett skript var committat är struken, eftersom filen var ospårad när den
skrevs. Karakteriseringen "WordPress-brus" är ersatt av mätvärden mot AVKODAD
text, 78 av 97 respektive 97 av 97. Populationen bakom talet 105 står nu utskriven
som predikat. Bisatsen om att formulärmail är särskilt utsatta för
prefixkollision är ersatt av en mätning som visar noll kollisioner.

**Andra granskningsvarvet fällde rättelsetexten, per post.** Talet 23 om
webbformulärets bidrag producerades inte av något skript och mäts nu av
`scripts/besvarad-omklassning.py`, som dessutom känner igen formuläret på
ÄMNESRADEN i stället för på avsändardomänen. Citatet ur #9 tillskrevs rubriken
men står i brödtexten. Ett hårdkodat 92 i skriptets utskrift räknas nu.
Motsvarande fynd i `docs/sparrar.md` och `docs/roadmap.md` redovisas i de
filernas egna appendixposter.

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skivan förbrukade alla tre och det sista underkände också. Fynden i det varvet är
rättade, men de rättelserna är **självmätta och inte oberoende granskade**:
grep-meningen om etikett-ID:n som skivans egen appendixpost gjorde falsk, den
versalkänsliga jämförelsen som mätte kroppen där avsnittet talar om fältvärdet,
och en universell bisats om att mätskriptet bär varje tal i sitt avsnitt.

Rättelserna gjordes därför att §7 förbjuder att skeppa ett känt falskt påstående
även när undantaget eller varvsgränsen är uttömd. Varvsgränsen begränsar antalet
granskningar, inte kravet på sanning. Två av de tre krävde ny mätning i
`scripts/formular-matning.py`, som nu prövar det strikta mönstret mot
FÄLTVÄRDET, och i `scripts/besvarad-omklassning.py`, som mäter om någon text
korsar formulärgränsen. Båda mätningarna är körda och deras utfall står i posten.

Ny post ⇒ MINOR.

### 0.22.0 — 2026-08-27

**Strykningar på plats i #24 och #25, av påståenden som blivit falska och som
stod i PRESENS.** Undantaget i dokumentets huvud tillåter det, och var och en bär
en kursiv not där den stod. **#26 bär en egen not** om ett påstående den här
skivan själv gjorde falskt.

**#25 sade** att frågan om vems tjänstevikt §42 punkt 1 avser är BLOCKERANDE för
fas 4.5; att den avgörs av besked från en besiktningsman och inte av oss; att
detta var **Lars eget beslut i skiva 13**; att frågan är hur §42 tillämpas vid en
registreringsbesiktning; att antagandet om vikterna är agentens och obelagt; att
felriktningen är densamma som skiva 12:s defekt; och att ingen kod ändras under
tiden.

Lars besked i skiva 14 gör dem falska: tjänstevikten är densamma före och efter
ombyggnaden, så frågan saknar praktisk betydelse och `utvardera` prövar rätt
storhet. **#25 bär nu beskedet som Lars beslut med hans skäl**, i stället för
punkten. Att det Lars beslutade i skiva 13 är det han vänder i skiva 14 står
utskrivet i noten, eftersom det annars försvann ur posten.

Beskedet fanns redan i #26. Skillnaden är att #25 fram till nu läste som om
punkten vore öppen för den som stannade där, och strykningen gör att den inte
längre gör det. Att komplettera med en ny post räckte alltså inte.

**§39:s barlastflak står utskrivet i #25 som den enda kända invändningen**, och
att beskedet gäller ändå. Att invändningen ska stå och inte utelämnas är Lars
instruktion i skiva 14.

**#24 sade** att punkten om två fält är öppen och blockerande; att fasen inte får
lämnas och ingen mall skrivas innan Lars avgjort om tjänstevikt ska tillbaka; och
att ingen kod ändras av agenten. Allt blev falskt av #25, som förde tillbaka
tjänstevikt som tredje fält och ändrade `src/fordonsuppslag.py` för att göra det.

**Den strykningen låg utanför skiva 14:s brief** och gjordes därför att
påståendena stod i presens och läses som nuläge, och §7 tillåter inte att en känd
falskhet skeppas.

**TRE APPENDIXPOSTER BLEV OSANNA AV DEN HÄR SKIVAN och upphävs härmed
uttryckligen**, i stället för underförstått. De står kvar som de skrevs, enligt
Räckvidd i dokumentets huvud och §8:

- **0.21.0** säger att #25 står kvar oförändrad enligt append-only. Samma
  påstående stod i #26:s brödtext och bär där en kursiv not.
- **0.20.0** säger att frågan om vems tjänstevikt är BLOCKERANDE för fas 4.5.
- **0.19.0** säger att punkten om två fält är öppen och blockerande.

Strykningar på plats och uttryckliga upphävanden ⇒ MINOR.

### 0.21.0 — 2026-08-27

**#26 tillkommer**, på beslut av Lars: tjänstevikten är densamma före och efter
ombyggnaden. **#25:s öppna punkt om vems tjänstevikt §42 punkt 1 avser är därmed
avgjord**, och dess status som blockerande för fas 4.5 är upphävd.

Skälet är Lars, och det är sakligt och inte formellt: är talet detsamma spelar
det ingen roll vilket av fordonen paragrafen syftar på. `utvardera` prövar rätt
storhet.

**Posten skriver ut §39:s barlastflak** som den ombyggnad som skulle kunna flytta
tjänstevikten, och att beskedet gäller ändå. Skälet att ta med invändningen är
att göra beskedets räckvidd synlig: hittar någon i framtiden ett fordon där
vikterna skiljer sig är det det här beslutet som ska omprövas.

#25 står kvar oförändrad enligt append-only.

Ny post ⇒ MINOR.

### 0.20.0 — 2026-08-27

**#25 tillkommer**, på beslut av Lars i skiva 13. Tjänstevikt är tillbaka som
tredje fält, och gatingen följer §42 andra styckets *eller*: RÖTT kräver att
BÅDA lämplighetsvillkoren faller.

Posten skriver ut strykningen i #24 **som den var**: premissen att §42 saknar tal
kom ur briefen till skiva 12 och var motbevisad av föreskriftens text. Det var
inte ett avvägt val utan ett beslut på en felaktig uppgift.

**Dragkroksbeskedet får härkomst**, och luckan som stod registrerad i
`docs/sparrar.md` sedan skiva 12 är nu en byggd spärr.

**En föreskrift citeras ordagrant, aldrig sammanfattad.** Regeln står i fas 4.5
och bärs av `docs/incidentlogg.md` I6.

**Frågan om vems tjänstevikt §42 punkt 1 avser är BLOCKERANDE för fas 4.5 och
avgörs av en besiktningsman.** Beslut av Lars efter tredje granskningsvarvet.
Den går inte att avgöra ur ordalydelsen, och ingen kod ändras på antagandet
under tiden.

Ny post ⇒ MINOR.

### 0.19.0 — 2026-08-27

**§42 ÄR UPPSLAGEN, OCH #24 BAR ETT FALSKT PÅSTÅENDE SOM ÄR STRUKET PÅ PLATS.**
Lars gav i skiva 12 instruktionen att slå upp VVFS 2003:19 4 kap 42 § och
rapportera vad som faktiskt står. Föreskriften är hämtad från Trafikverket och
citerad ordagrant i `docs/roadmap.md` fas 4.5.

**Paragrafen anger ett tal.** §42 punkt 2 säger *"ursprungsfordonet är
konstruerat för en släpvagnsvikt av minst 1 000 kg"*. #24 sade att §42 saknar
tal och att 1000 är verkstadens praxis, i rubriken och i tre stycken. Det var
falskt, och praxisramen faller med det. Strykningen är gjord på plats med kursiv
not, enligt undantaget i dokumentets huvud, och rubriken är ändrad av samma skäl.

**En andra sak föll ut av uppslagningen, och den är allvarligare.** §42:s två
villkor är förenade med *eller*: tjänstevikt minst 2 000 kg ELLER släpvagnsvikt
minst 1 000 kg. `utvardera` prövar bara det senare, så ett fordon med tjänstevikt
2 100 kg och släpvagnsvikt 800 kg får RÖTT trots att föreskriften säger att det
duger. Att rätta det kräver tjänstevikt som ett tredje fält, alltså det fält #24
stryker ur bedömningen. **Beslutet om två fält vilar därmed på ett underlag som
är motbevisat**, och punkten är öppen och blockerande. Ingen kod ändrades av
agenten.

**GULT mot OKLART är inte längre en öppen punkt.** Lars antog agentens tolkning
som beslut: skillnaden är ett besked från kunden, och förvalet OKLART utan besked
står fast. Posten är omskriven från "agentens tolkning" till Lars beslut.

Struket falskt påstående och nytt beslutsinnehåll ⇒ MINOR.

### 0.18.0 — 2026-08-27

**#24 tillkommer**, på beslut av Lars i skiva 12: kravbilden för
a-traktorombyggnad snävas till släpvagnsvikt och draganordning, och tjänstevikt,
drivning, karosserikod och barlastflak utgår ur bedömningen.

*Rättelse i 0.19.0: stycket nedan återger #24:s ursprungliga påstående om
tröskeln. Det är falskt och struket i posten. §42 anger talet.*

**Tröskeln 1000 kg är Auto Stockholms praxis och inte ett författningskrav.**
VVFS 2003:19 4 kap 42 § kräver kopplingsanordning utan att ange något tal.
Källan, verkstadens erfarenhet och besked från besiktningsmän, är namngiven i
posten just för att den inte är författningen, och posten slår fast att en mall
som återger talet som författningskrav är en sändvägsdefekt.

**Hämtningen ligger bakom gränssnittet som en utbytbar implementation**, med #23
som skäl: datakällan är inte avgjord och modulen ska överleva ett byte.

Posten bär en **öppen punkt**: briefens GULT och OKLART har identiska
registervillkor, och agentens tolkning att skillnaden är ett besked från kunden
är inte beslutad av Lars. Efter granskningen är tolkningen märkt som agentens
också i koden, i `utvardera`:s docstring, och inte bara i `docs/`. Det ställe fas
5 faktiskt läser är koden.

**Påståendet om §42 är märkt som återgivet.** Granskningen fällde att skivan
gjorde ett starkare påstående om föreskriften än förut, att den inte anger något
tal, samtidigt som den strök kravet på att verifiera texten. Kravet är
återinfört, här och i fas 4.5.

Ny post ⇒ MINOR.

### 0.17.0 — 2026-08-27

**#23 tillkommer**, på beslut av Lars i skiva 11: fordonsuppslaget i fas 4.5
hämtar tekniska fält utan ägaruppgifter, och bortvalet är ett aktivt val och
inte en begränsning.

Posten namnger leverantörsvägarna Lars räknade upp och skriver ut att
uppgifterna om dem är ÅTERGIVNA och inte uppslagna i sessionen. **Priset per
uppslag och avtalsformen skrivs inte**, eftersom de inte är avlästa och §7.2
inte tillåter en tredje kategori mellan avläst och utelämnat.

Bortvalet av ägardata kopplas till §6: ett uppslag som svarar med ägaren hade
dragit in persondata i ett flöde som annars bara behöver teknik, och den datan
hade sedan legat i varje logg på vägen.

**Öppen punkt: leverantör är inte vald**, och den punkten ÄR fas 4.5:s grind.

Ny post ⇒ MINOR.

### 0.16.1 — 2026-08-27

Rättelser i #20, #21 och #22 efter §7-granskningen av skiva 10.

**#22 påstod att whitelisten finns för att Internal låser ut adresser utanför
domänen.** Det är falskt, och motsägelsen är en sakkonflikt. Uppslaget i Googles
dokumentation 2026-08-27: en Internal-app avvisar konton utanför organisationen
med `org_internal` INNAN appen får se någon identitet, och user type sätts på
projektnivå. Whitelisten kan alltså aldrig få något att pröva så länge consent
screen är Internal. #21 bär nu ÖPPEN PUNKT 1 med tre vägar och överlämnar valet
till Lars.

**#21:s persondatapunkt saknade en invändning.** `TILLATNA` ligger i
`scripts/persondatakontroll.py`, som pushas, så väg 1 flyttar adressen från en
bevakad fil till en obevakad utan att den slutar finnas i repot. Punkten säger nu
det, och namnger den underliggande frågan: om adressen över huvud taget ska stå i
repot.

*Ledet om bevakat mot obevakat är upphävt av #28: `scripts/` ligger sedan skiva
16 i `BEVAKADE`. Den underliggande frågan och slutsatsen står kvar. Den kursiva
noten i #21 bär skälet.*

**#20 tillskrev §5 en regel som står i §6.** Att `--send` bara aktiveras av Lars
explicita val står i §6. §5:s undantag säger något annat, att sändning aldrig är
del av att avsluta en uppgift. Båda är nu utskrivna var för sig.

Rättade påståenden ⇒ PATCH.

### 0.16.0 — 2026-08-27

Tre poster tillkommer, alla på beslut av Lars i skiva 10, och alla om drift.

**#20** flyttar boten i sin helhet till `mailagent.dasher.se`, med
riskförflyttningen utskriven: `token.json` bär `gmail.send` och flyttar från
Lars maskin till en server som är nåbar från internet.

**#21** sätter inloggningen till utkastvyn: Google med `hd=autostockholm.se`
plus en COMMITTAD whitelist, och slår fast att `hd` är ett filter och inte en
spärr.

**#22** ger inloggningen en egen OAuth-klient av typen Web application, skild
från `mailbot-cli` som bär sändningsscopet.

Tre nya poster ⇒ MINOR.

### 0.15.0 — 2026-08-26

Tre poster tillkommer, alla på beslut av Lars i skiva 9.

**#17** stryker Intercom-undantaget ur förbudslistan. Posten var verkningslös:
`intercom-mail.com` är en annan organisationsdomän än `bokadirekt.se`, så
skyddet nådde den aldrig. Fyndet kom ur §7-granskningen av skiva 8.

**#18** ersätter den fria etiketteringen med två pass och en fast taxonomi, och
skriver ut varför enum-tvånget ligger i en kontroll och inte i API:ts schema.

**#19** bokför att cachemarkören sätts trots att den inte biter vid dagens
promptstorlek, med de två mätta talen och gränsen utskrivna, så att ingen
framtida läsare tror att cachen är i drift.

Tre nya poster ⇒ MINOR.

### 0.14.0 — 2026-08-26

Post **#16** tillkommer: förbudslistan över domäner som aldrig får klassas som
maskinmail, på beslut av Lars. Den räddade 374 trådar och lät den mänskliga
korpusen växa från 520 till 894.

Ny post ⇒ MINOR.

### 0.13.0 — 2026-08-26

Posterna **#14** och **#15** tillkommer efter granskning. #14 slår fast att
domänlagret bidrar med noll och skeppas tomt. #15 redovisar ett påhittat tal i
ett commitmeddelande som inte går att skriva om.

En rättelse i #12:s tabell: `src/extract.py` sållar nu bort maskintrådar vid
källan, vilket sänkte antalet par från 226 till 222 och antalet trådar med par
från 134 till 130. Fyra trådar var nyhetsbrev vi råkat svara på.

Två nya poster ⇒ MINOR.

### 0.12.0 — 2026-08-26

Posterna **#12** och **#13** tillkommer. #12 slår fast att maskinmail skiljs på
huvuden, med det undantag som räddar webbformulärets notiser. #13 slår fast att
`data/par.jsonl` är rå och ska förbli det, eftersom en maskerad fil hade varit
oanvändbar som mallunderlag.

Två nya poster ⇒ MINOR.

### 0.11.0 — 2026-08-26

Rättelser i #9 och #10 efter granskning, alla strukna på plats enligt undantaget
i huvudet, var och en med en kursiv not där den stod:

- #9 räknade upp vilka grupper som är störst. Uppräkningen motsägs av tabellen
  den vilar på: lösenords-, faktura- och molnlagringsklustren är bland de minsta.
  Klassificeringen var inte mätt.
- #10 kallade a-traktor "stor nog att bygga mallar ur", en värdering utan
  namngiven tröskel, och påstod ett orsakssamband mellan kärnverksamhet och
  svarsfrekvens som inte är belagt.
- #10 namngav inte termsträngen, så talet 36 gick inte att reproducera utan
  gissning. Strängen står nu utskriven.
- #10 saknade upplysningen att 36 och 4 inte är mätta på samma population.

Ny post **#11** om extraktionens parräkning tillkommer.

Ny post och rättelser ⇒ MINOR.

### 0.10.0 — 2026-08-26

Posterna **#9** och **#10** tillkommer efter miningen av obesvarade trådar och
klustringen. #9 slår fast att de obesvarade är tre gånger fler men mestadels
inte kundärenden. #10 bär underlaget per kategori, inklusive a-traktorns 36 par.

Två nya poster ⇒ MINOR.

### 0.9.0 — 2026-08-26

Post **#8** tillkommer och upphäver **#7**. Urvalet i #7 räknade
vidarebefordringar som svar och uteslöt formulärnotisen som kundsida. Felen drog
åt varsitt håll och tog inte ut varandra: talet 234 var varken tak eller golv.
Rättat tal är 136.

Falska påståenden i #7 är strukna på plats enligt undantaget i huvudet, var och
en med en kursiv not där den stod: att 555 trådar är "hela brevlådan", att 234 är
"taket för antalet par", att det är "tillräckligt", och att de 290 trådarna är
formulärnotiser och vidarebefordringar. Det sista är falsifierat av ett första
utgående mail utan förlaga, en kategori #5 inte nämner.

Ny post som upphäver en tidigare ⇒ MINOR.

### 0.8.0 — 2026-08-26

Post **#7** tillkommer med underlaget för mallarna, uppmätt över hela brevlådan
efter full mining. Talet står i en committad källa och inte bara i en
gitignorerad rapport, eftersom fas 4 och fas 5 vilar på det.

Ny post ⇒ MINOR.

### 0.7.0 — 2026-08-26

Posterna **#5** och **#6** tillkommer efter provkörningen mot brevlådan. #5
slår fast att `SENT` inte är en proxy för mänskligt skrivet svar, och #6 räknar
upp de strukturella kantfall `extract.py` måste bära. Båda vilar på uppmätt
material och inte på antaganden.

**Om en processräkning i historiken.** Commitmeddelandet i `6673aea` inleder ett
stycke med "TVÅ FEL SOM FÖRSTA KÖRNINGEN BLOTTADE". Det är en räkning av
instanser av ett mönster i ett arbetsförlopp, alltså den form §7.2 förbjuder, och
den blev omedelbart falsk: granskningen fann fler fel i samma verktyg. Meddelandet
ligger i historiken och kan inte skrivas om. Räkningen upphävs här.

Två nya poster ⇒ MINOR.

### 0.6.1 — 2026-08-26

**Falsk radhänvisning struken ur post #4.** Posten pekade ut den föråldrade
meningen i #1 som `docs/beslutslogg.md:49`. Meningen ligger inte där: ett tillägg
i huvudet sköt ned den, och den flyttar sig igen vid nästa tillägg. Hänvisningen
är ersatt av ett citat, som är stabilt. Struken på plats enligt undantaget i
huvudet, redovisad här. ⇒ PATCH.

### 0.6.0 — 2026-08-26

**`Speglar` ersätts av en sektionspekare utan versionsnummer.** En pekare som bär
ett versionsnummer blir gammal av varje PATCH i CLAUDE.md, och tvingade fram
innehållslösa versionsposter i vart och ett av de dokument som pekade. Pekaren
säger nu vilken paragraf dokumentet implementerar, vilket är det som faktiskt är
stabilt.

Beslut av Lars i skiva 3, som svar på den öppna fråga `docs/sparrar.md` ställde i
sin 0.2.2-post. Bara CLAUDE.md behåller `Speglar`, och den pekar på den här
loggen.

Ändrad form på versionshuvudet ⇒ MINOR.

### 0.5.0 — 2026-08-26

**Processräkning struken ur post #4.** Rubriken sa "och det är samma orsak tredje
gången", och citerade en instans, "gav tre träffar", som aldrig funnits i repot:
`git grep -n "tre träffar" 7397e8e` ger exit 1. Frasen stod i en granskningsrapport
och blev aldrig committad, alltså var den aldrig en rättelse. Räkningen är struken
och rubriken lyder nu "Varför felet uppstod". §7.2 förbjuder räkningar av instanser
av ett mönster summerade i en bisats, och regeln bars här av ett exempel som själv
bröt mot den.

**Undantaget för känt falskt påstående skrivs in i huvudet.** Räckviddsregeln och
§7 pekade åt olika håll: den ena förbjöd omskrivning av en committad post, den
andra förbjuder att ett känt falskt påstående skeppas. Skiva 2 löste konflikten
tyst på flera ställen genom att stryka falskheten på plats och redovisa
strykningen i en ny versionspost. Den medelvägen står nu utskriven i stället för
att tillämpas underförstått.

Ny regel i huvudet ⇒ MINOR.

### 0.4.0 — 2026-08-26

Post **#4** tillkommer och upphäver #3:s verifieringsanvisning, som beskrev en
träffsort som kommandot inte producerar. #3 är orörd.

Ny post ⇒ MINOR.

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
