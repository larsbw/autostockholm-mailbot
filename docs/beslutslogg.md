# Beslutslogg

**Version:** 0.23.0 · **Uppdaterad:** 2026-08-28 · **Implementerar** CLAUDE.md §8

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

795 är avläst på rad 54 i `docs/kategorier-forslag.md` och 213 ur körningen. 582
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

Tabellen ger i dag 25/12/7 totalt för de tre a-traktorkategorierna med *Utan
svar* 0, 1 och 0. Bilden av a-traktorärenden som i praktiken alltid besvarade
vilar alltså på att de obesvarade låg i fel fil.

**Detta är INTE en rangordning mellan kategorier.** De återstående 43 texterna är
oetiketterade och kan fördela sig var som helst, och ingen jämförelse mot någon
annan kategoris basvärde är gjord.

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

## Appendix — versionshistorik (nyaste överst)

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
