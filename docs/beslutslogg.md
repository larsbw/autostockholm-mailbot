# Beslutslogg

**Version:** 0.12.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §8

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

## Appendix — versionshistorik (nyaste överst)

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
