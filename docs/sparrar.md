# Spärrar

**Version:** 0.10.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §7.1

> **RADNUMMER FÖRÅLDRAS.** Kontrollera alltid att raden i en post fortfarande
> bär det villkor posten påstår, innan du fäller den. En granskning körde det
> dokumenterade kommandot ordagrant, träffade fem docstringrader i stället för
> spärren, och fick verdiktet GRÖN. Ett föråldrat radnummer i det här dokumentet
> producerar alltså ett FALSKT VAKUÖSTVERDIKT, vilket är värre än inget
> dokument. Varje post namnger därför också villkorets TEXT.

**Sändvägens spärrar är ännu inte byggda och fylls i FAS 5.** De spärrar som
står i tabellen nedan kommer inte från sändvägen, utan från mining, urval,
maskering och commitgrinden.

*Rättelse i 0.7.0: här stod "En spärr är registrerad". Tabellen bar då fem.
Meningen räknade sin egen omgivning och blev falsk av den commit som lade till
poster i grannstycket, vilket är precis det CLAUDE.md 0.3.1 förbjuder.*

Det här dokumentet är obligatorisk läsning före varje vakuöstprövning enligt
CLAUDE.md §7.1. Skälet är kolumnen **Redundant med**: mailbotens spärrar är
redundanta med avsikt, och fälls bara det ena lagret förblir sviten grön och
prövningen pekar ut ett äkta spärrtest som vakuöst. Ett grönt utfall efter att
ETT lager fällts är inkonklusivt, inte vakuöst. Samtliga lager som implementerar
spärren ska fällas i samma körning innan verdiktet sätts:

```
scripts/sparr-prova.sh --fil src/x.py --radera 42 --radera 87
```

---

## Översikt

| Spärr | Vad den skyddar mot | Negativkontroll | Redundant med |
| --- | --- | --- | --- |
| `nollfall-max-threads` | Att en körning som ombeds hämta noll trådar raderar föregående skörd | `test_alla_tradar_over_flera_sidor_hamtas` | Sig själv, två lager i `src/mine.py`. Se posten. |
| `urval-gmail-svar` | Att maskinskriven text blir mall och att kundens röst räknas bort | `test_svar_skrivet_i_gmail_kanns_igen`, `test_inkommande_ar_kundmeddelande` | Sig själv, sex lager i `ar_gmail_svar`. Se posten. |
| `maskering-persondata` | Att persondata når ett dokument under `docs/` | `test_ord_vid_meningsstart_maskeras_ocksa` | `src/cluster.py::namn_i_korpus`, i en ANNAN fil, och `scripts/persondatakontroll.py`. Se posten. |
| `klassning-maskinmail` | Att nyhetsbrev och notiser blir kundärenden | `test_vanligt_kundmail_ar_inte_maskinmail` | Fyra lager plus ett UNDANTAG. Se posten. |
| `persondatakontroll` | Att en commit för in persondata i `docs/` | `test_ren_text_ger_inga_fynd` | `maskering-persondata`. Sista linjen, inte den enda. |
| `forbjudna-maskindomaner` | Att en förmedlad kundförfrågan kastas som maskinmail | `test_liknande_doman_skyddas_inte_av_misstag` | Sig själv, två lager i `src/klassa_maskin.py`, och går FÖRE `klassning-maskinmail`. Se posten. |

---

## `nollfall-max-threads`

- **Spärr.** Hindrar att `--max-threads 0` eller ett negativt tal leder till en
  hämtning. Beslutet fattas på **två rader, i två funktioner**:
  - I `lista_trad_id`: `if max_tradar is not None and max_tradar <= 0:`
    följt av `return []`. Skyddar API:et. Inget anrop görs.
  - I `mina`: samma villkor, returnerar innan `utfil` rörs. Skyddar filen.
    Ingen `.delvis` skapas och `data/tradar.jsonl` lämnas orörd.

  Radnumren står inte här, av skälet i rutan överst. Slå upp dem med
  `grep -n "max_tradar is not None and max_tradar <= 0" src/mine.py`, som ger
  båda lagren och bara dem.
- **Vad den skyddar mot.** Utan lagret i `mina` skrev en nolltrådskörning en tom
  `.delvis`, flyttade den på plats över en färdig skörd, och kvitterade det i
  `docs/mining-log.md` som `fullständig`. En felskrivning på kommandoraden
  förstörde alltså en mining och loggade den som lyckad.
- **Negativkontroll.** `tests/test_mine.py::test_alla_tradar_over_flera_sidor_hamtas`
  visar att spärren SLÄPPER IGENOM när `max_tradar` är `None`: samtliga trådar
  hämtas över flera sidor och skrivs till utfilen.
  `tests/test_mine.py::test_max_threads_lika_med_totalen_hamtar_allt` visar
  detsamma vid det övre gränsvärdet.
- **Redundant med.** Ingen annan spärr, men **redundant med sig själv i två
  lager**, vilket är precis det fall §7.1:s klausul om lagrat försvar handlar om.

  **Historik, och varför posten finns.** I skiva 1 fanns bara ett test som rörde
  nollfallet, och det testade lagret i `mina`. En fällning av **enbart** `:179`
  gav då GRÖN, alltså ett INKONKLUSIVT utfall som utan den här posten läses som
  vakuöst. Granskaren fick upptäcka lagringen på egen hand.

  **Nuläge.** Sedan lagret i `lista_trad_id` fått ett eget test faller varje
  lager för sig:

  | Fällt lager | Test som blir röda |
  | --- | --- |
  | `lista_trad_id` | `test_lista_trad_id_med_noll_gor_inga_anrop` |
  | `mina` | `test_max_threads_noll_ger_inga_anrop_alls`, `test_max_threads_noll_raderar_inte_foregaende_skord` |
  | båda | samtliga tre ovan |

  Lagringen är alltså kvar, men den maskerar inte längre. Varje lager vaktar en
  egen sak: det ena skyddar API:et mot ett anrop, det andra filen mot en
  överskrivning. Den fullständiga prövningen fäller båda i samma körning, med
  radnummer avlästa ur grep-kommandot ovan:

  ```
  scripts/sparr-prova.sh --fil src/mine.py --ersatt "<rad1>=    if False:" --ersatt "<rad2>=    if False:"
  ```

  **Neutralisering, inte radering.** Villkoren är `if`-huvuden, och en radering
  lämnar en syntaktiskt trasig fil. Sviten kan då inte köras alls, och
  prövningen ger FEL i stället för RÖD.

---

## `urval-gmail-svar`

- **Spärr.** `src/urval.py::ar_gmail_svar` avgör vilka meddelanden som
  får bli HÖGER sida i ett par, och `ar_kundmeddelande` vilka som får bli vänster.
  Beslutet fattas på **sex rader i `ar_gmail_svar`**, var och en ett eget villkor:
  `SENT` i labelIds, inga leveranshuvuden, båda svarshuvudena, inte
  `multipart/report`, minst en mottagare utanför brevlådan, och inget
  vidarebefordringsprefix.
- **Vad den skyddar mot.** Att formulärnotiser och vidarebefordringar blir de
  faktiska svar §11 kräver att mallarna byggs ur. En mall byggd ur en
  formulärnotis skulle vara maskinskriven text i Matte och Lars namn. Den
  skyddar också åt andra hållet: `ar_kundmeddelande` hindrar att kundens ärende
  räknas bort bara för att det kom in genom formuläret och därför bär `SENT`.
- **Negativkontroll.** `test_svar_skrivet_i_gmail_kanns_igen` visar att spärren
  SLÄPPER IGENOM ett äkta svar. `test_svar_pa_vidarebefordrat_mail_raknas_som_svar`
  visar att den släpper igenom ett svar på något vidarebefordrat, alltså att
  prefixvillkoret inte är för brett. `test_inkommande_ar_kundmeddelande` och
  `test_formularnotis_ar_kundmeddelande_trots_sent` visar motsvarande för
  kundsidan.
- **Redundant med.** Ingen annan spärr, men **redundant med sig själv i sex
  lager**. Varje lager har ett eget test, och fällning av ett lager i taget ger
  RÖD i just det testet. Uppmätt: fällning av leveranshuvudvillkoret fäller
  `test_formularnotis_med_sent_raknas_inte_som_svar`, fällning av
  svarshuvudvillkoret fäller
  `test_forsta_utgaende_mailet_utan_forlaga_raknas_inte_som_svar`, fällning av
  `SENT`-villkoret fäller `test_inkommande_meddelande_raknas_aldrig_som_svar`.

  **Lagringen är farlig här på ett sätt som skiljer sig från `nollfall-max-threads`:**
  lagren är inte redundanta med varandra, de vaktar olika sorters felaktig text.
  Ett fällt lager syns därför som ett rött test, men ett SAKNAT lager syns inte
  alls. Så uppstod felet i #7, där vidarebefordringsvillkoret helt saknades och
  talet blev 265 i stället för 139 utan att något test blev rött.

---

## `maskering-persondata`

- **Spärr.** `src/maskera.py::maska_fritext` och `::maska_adressrad` hindrar att
  persondata når ett dokument under `docs/`. Beslutet fattas på mönstren `URL`,
  `EPOST`, `DOMAN`, `GATA`, `REGNR`, `SIFFROR` och `VERSALT_ORD`, plus
  uteslutningslistan `EJ_NAMN`.
- **Vad den skyddar mot.** §6. Kundmail bär namn, adresser, registreringsnummer
  och telefonnummer, och `docs/kategorier-forslag.md` är maskinproducerad ur
  just den texten.
- **Negativkontroll.** `test_ord_vid_meningsstart_maskeras_ocksa` visar vad
  spärren SLÄPPER IGENOM, nämligen orden i `EJ_NAMN`. En maskering som ersatte
  allt vore inte en spärr utan en tömning.
- **Redundant med.** `src/cluster.py::namn_i_korpus`, och **lagren ligger i
  olika filer**. Det gör spärren svår att pröva: `scripts/sparr-prova.sh` tar
  ett `--fil`, så den fullständiga fällningen kräver två körningar eller en
  manuell dubbelmutation. En granskning fällde `namn_i_korpus` ensamt, fick
  GRÖN på `test_namn_utesluts_ur_etiketten`, och kunde bara redovisa
  INKONKLUSIVT.

  **Historik.** Persondata nådde en committad fil fyra gånger under skiva 6, i
  fyra olika former: förnamn efter fältetikett med kolon, namn i signaturrad,
  fullständigt namn i gemener, och namn i versaler. De tre första berodde på ett
  positionsundantag som räknade varje radbörjan och varje tecken efter kolon som
  meningsstart. Undantaget är borttaget.

  **Det som INTE går att maska.** Ett namn som kunden skrivit med gemener i
  löpande text. Ingen heuristik når det. Därför skrivs citat ur kundmail till
  en gitignorerad fil och aldrig till `docs/`.

---

## `klassning-maskinmail`

- **Spärr.** `src/klassa_maskin.py::skal_maskinmail` avgör om ett meddelande är
  maskinmail. Beslutet fattas på **fyra lager plus ett undantag**, i den
  ordningen:
  0. **FÖRBUDSLISTAN, som sedan skiva 8 körs allra först:** `ar_forbjuden`. Den
     har en egen post nedan, `forbjudna-maskindomaner`, och nämns här bara för
     att ordningen ska stämma. Villkoret är
     `if ar_forbjuden(avsandardoman(meddelande), aldrig, undantag):`.
  1. **UNDANTAGET, som körs före de fyra lagren:** `relayar_manniska`. Post som är
     maskinSKICKAD men människoSKRIVEN, känd på att `Reply-To` pekar utanför
     både avsändaren och brevlådan.
  2. Huvuden i `MASKINHUVUDEN`: `List-Unsubscribe`, `Auto-Submitted`,
     `X-Auto-Response-Suppress` med flera.
  3. `Precedence` med värdet `bulk`, `list`, `junk` eller `auto_reply`.
  4. Avsändarens lokaldel på noreply-form.
  5. Avsändarens domän i `config/maskindomaner.yaml`.
- **Vad den skyddar mot.** Att nyhetsbrev, lösenordsmail och orderbekräftelser
  blir kundkategorier. Klustringen i skiva 6 grupperade på avsändarens mall i
  stället för på kundens ärende just därför att den saknade den här spärren.
- **Negativkontroll.** `test_vanligt_kundmail_ar_inte_maskinmail` visar att
  spärren SLÄPPER IGENOM en människa.
  `test_avsandare_som_bara_borjar_pa_no_ar_inte_noreply` visar att
  noreply-mönstret inte är för brett, och
  `test_precedence_normal_ar_inte_maskinmail` att `Precedence: normal` inte
  fäller.
- **Redundant med.** `src/urval.py::ar_massutskick`, som fortfarande anropas
  från `src/cluster.py` och implementerar en AVVIKANDE maskinmailregel: den
  saknar undantaget helt och behandlar `precedence` som huvudnamn. Den är kvar
  enligt §3 och rörs inte, men den ska inte förväxlas med den här spärren.

  De fyra lagren i `skal_maskinmail` är inte redundanta med varandra: var och
  en fångar en egen sorts avsändare, så ett saknat lager syns inte som ett rött
  test.

  **MEN UNDANTAGET ÄR REDUNDANT INTERNT, och det överraskade en granskare.**
  `relayar_manniska` har två `continue`-villkor, och för självadresserat
  `Reply-To` fäller de samma fall. En fällning av det ena ensamt lämnar
  `test_nyhetsbrev_med_reply_to_till_sig_sjalvt_ar_fortfarande_maskinmail`
  GRÖN, alltså ett inkonklusivt utfall som utan den här raden läses som
  vakuöst. Fäll båda:

  ```
  scripts/sparr-prova.sh --fil src/klassa_maskin.py \
    --ersatt "<rad-brevlada>=        if False:" \
    --ersatt "<rad-organisation>=        if False:"
  ```

  Raderna slås upp med
  `grep -n "continue" src/klassa_maskin.py` inne i `relayar_manniska`.

  **UNDANTAGET ÄR DET FARLIGASTE ATT TAPPA.** Utan `relayar_manniska` klassas
  webbformulärets notis som maskinmail, eftersom den bär `X-Msg-EID`. Uppmätt
  vid första körningen: **288 av 555 besvarade trådar** föll som maskinmail
  innan undantaget fanns, mot 200 efteråt. Det är det mest värdefulla
  kundmaterialet, och beslutslogg #8 slog fast att notisen ÄR kundens
  meddelande.

  Undantaget får samtidigt inte vara för brett, och tre test vaktar det:
  `Reply-To` till sig självt, till avsändarens egen domän, och till brevlådan
  ska alla lämna klassningen som maskinmail.

---

## `forbjudna-maskindomaner`

- **Spärr.** `src/klassa_maskin.py::ar_forbjuden`, läst ur den committade
  `config/maskindomaner-forbjudna.yaml`. Den prövas FÖRST i `skal_maskinmail`,
  före undantaget och före alla fyra lager, och den styr också vad
  `harled_domaner` får föreslå.
- **Vad den skyddar mot.** **En förmedlad offertförfrågan är en KUND, och en
  domän som råkar skicka den maskinellt är fortfarande en kund.** Formen är
  maskinell, innehållet är affär. Utan spärren kastades hela inflödeskanaler ur
  underlaget, och boten hade blivit blind för dem.

  `googlemail.com` står på listan av ett annat skäl: det är Gmails
  konsumentaliasdomän, alltså privatpersoner. En härledning som fick med den
  hade klassat varje framtida kund med en sådan adress som maskinmail.
- **UPPMÄTT EFFEKT.** Med listan tom mot med listan ifylld, samma material:

  | Skörd | Maskinmail utan listan | Med listan | Räddade |
  | --- | --- | --- | --- |
  | besvarade | 200 | 187 | 13 |
  | obesvarade | 1295 | 934 | 361 |

  361 obesvarade trådar räddades alltså från att kastas. Hur många av dem som
  är förmedlade kundärenden är INTE mätt: `googlemail.com` står på samma lista
  och är enligt stycket ovan privatpersoner, inte en förmedlare. Talet är antal
  räddade trådar, inte antal ärenden. Listan är i vilket fall verksamhets-
  kunskap som ingen härledning kunde ha nått: den är Lars beslut, inte kodens.
- **Negativkontroll.** `test_liknande_doman_skyddas_inte_av_misstag` visar att
  spärren SLÄPPER IGENOM en domän som bara slutar på samma bokstäver.
  `test_undantaget_ar_mer_specifikt_och_provas_forst` visar att undantaget
  vinner över moderdomänen i `ar_forbjuden`, alltså att `support.autobutler.se`
  inte skyddas av att `autobutler.se` gör det. Testet anropar inte
  `skal_maskinmail` och säger därför ingenting om vad som sedan händer med
  posten.
- **Redundant med. SIG SJÄLV, i två lager, och det är fyndet ur §7-granskningen
  av skiva 8.** Spärren implementeras i två funktioner i
  `src/klassa_maskin.py`. Villkoren, som TEXT, eftersom radnummer föråldras:

  | Funktion | Villkoret som fattar beslutet |
  | --- | --- |
  | `skal_maskinmail` | `if ar_forbjuden(avsandardoman(meddelande), aldrig, undantag):` |
  | `harled_domaner` | `if not ovrigt[d] and not ar_forbjuden(d, aldrig, undantag)` |

  Fälls bara `harled_domaner`-lagret förblir HELA sviten grön, och en granskare
  som prövar `test_harledningen_foreslar_aldrig_en_forbjuden_doman` sätter då
  ett FALSKT vakuöstverdikt på ett äkta spärrtest. Slå upp raderna först, kör
  sedan fällningen med de nummer utdatan gav:

  ```
  grep -n "ar_forbjuden" src/klassa_maskin.py
  scripts/sparr-prova.sh --fil src/klassa_maskin.py \
    --ersatt "<rad i skal_maskinmail>=    if False:" \
    --ersatt "<rad i harled_domaner>=        if not ovrigt[d]"
  ```

  Uppmätt mot en svit om 224 test: `harled_domaner`-lagret ensamt ger GRÖN
  sviten igenom, båda lagren ger `2 failed, 222 passed`. **Svitens storlek står
  utskriven därför att talet annars föråldras tyst av nästa test som skrivs**,
  vilket det hann göra inom samma skiva. Verdikten föråldras inte.

  Mot ANDRA spärrar är den inte redundant. Den går FÖRE
  `klassning-maskinmail`, som annars hade fällt samma post. Ordningen är
  spärren: byts den blir listan verkningslös utan att något test blir rött, om
  inte `test_forbudslistan_gar_fore_maskinhuvuden` finns. Det gör det.

  **Undantagen prövas före moderdomänen**, eftersom de är mer specifika.
  `support.autobutler.se` är en supportkanal medan `autobutler.se` är en
  kundkanal.

---

## `persondatakontroll`

- **Spärr.** `scripts/persondatakontroll.py` vägrar en commit vars STAGADE
  innehåll under `docs/` matchar mönster för mailadress, telefonnummer,
  registreringsnummer, postnummer med ort, gatuadress eller personnummer.
  Installeras som pre-commit-hook med `scripts/installera-hook.sh`.
- **Vad den skyddar mot.** §6. Skiva 5 och skiva 6 hade båda persondata nära en
  commit, och i skiva 6 nådde det ända in i en commit. Båda gångerna fångades
  det av en granskning. **En granskare tittar ibland. En spärr biter varje
  gång.**
- **Negativkontroll.** `test_ren_text_ger_inga_fynd` visar att spärren SLÄPPER
  IGENOM vanlig text, och `test_bart_femsiffrigt_tal_falls_inte` att
  kvotåtgången i `docs/mining-log.md` inte larmar som postnummer.
- **Redundant med.** `maskering-persondata`. Den här spärren är den SISTA
  linjen och inte den enda: maskeringen ska hindra att persondata skrivs, och
  kontrollen ska hindra att den committas om maskeringen ändå brister.

  **Kontrollen läser INDEXET, inte arbetsträdet.** Ett `git add` följt av en
  redigering hade annars sluppit igenom.

  **En hook går att kringgå med `git commit --no-verify`.** Det går inte att
  stänga av i git. Spärren skyddar alltså mot MISSTAG, inte mot en beslutsam
  användare, och den ska läsas så.

  **Ett falskt larm rättas i mönstret eller i `TILLATNA`, med skäl utskrivet.**
  Att skriva om dokumentet tills spärren släpper igenom det är §9.1:s förbjudna
  åtgärd i dokumentform.

---

## Mall för en spärrpost

Kopiera blocket nedan per spärr. Varje fält fylls i, tomma fält är en ofärdig
post och inte en spärr som saknar egenskapen.

### `<spärrens namn>`

- **Spärr.** Vad den gör, och exakt var i koden beslutet fattas: fil och den rad
  eller det villkor som fäller. Utan det går prövningen enligt §7.1 inte att
  utföra utan gissningar.
- **Vad den skyddar mot.** Det konkreta utfallet den finns för att förhindra,
  formulerat som något som annars skulle lämna servern.
- **Negativkontroll.** Det test som visar att spärren SLÄPPER IGENOM när den ska.
  En spärr som alltid fäller är inte en spärr, den är ett stopp. Namnge testet
  med fil och testfunktion.
- **Redundant med.** Varje annan spärr som fäller samma fall. Skriv `ingen` om
  spärren är ensam, aldrig tomt. Posten läses av den som ska fälla samtliga
  lager, och ett tomt fält går inte att skilja från ett obesvarat fält.

---

## Appendix — versionshistorik (nyaste överst)

### 0.10.0 — 2026-08-26

Rättelser efter ANDRA granskningsvarvet i skiva 8. Varvet underkände 0.9.0,
och båda fynden satt i det som skrevs FÖR att rätta ett falskt påstående.

**0.9.0 skrev ett falskt `Uppmätt`-tal i den post som rättade ett falskt
påstående.** Fältet "Redundant med" sa att båda lagren ger
`2 failed, 215 passed`. Det motsvarar ingen committad svit alls: mätningen
gjordes när sviten var 217 test, och fem test skrevs efteråt i samma skiva.
Talet var alltså falskt redan när det committades.

**Mekanismen, som är regelns egentliga innehåll.** Ett svitresultat är inte
ett tal om koden. Det är ett tal om koden OCH om sviten, och sviten växer av
nästa test som skrivs, ofta i samma skiva och ofta av samma anledning. §7.2
säger att en omskriven mening gör sitt tal oläst; här räckte det att
GRANNSKAPET växte. Därför står svitens storlek nu utskriven bredvid varje
sådant tal. Blir de två oense har läsaren en signal i stället för ett
förtroende.

**Radnummer var tillbaka.** 0.9.0 byggde sitt fällningskommando på `201=` och
`282=`, alltså precis den form rutan överst i det här dokumentet förbjuder
efter 0.5.0:s falska verdikt. Posten bär nu villkoren som TEXT i en tabell,
och kommandot inleds med den `grep` som ger raderna.

**Översiktstabellens rad namngav inte lagren.** Raderna för
`nollfall-max-threads` och `urval-gmail-svar` skriver ut "Sig själv, två
lager", medan `forbjudna-maskindomaner` bara sa "Går FÖRE
`klassning-maskinmail`". En granskare som stannar vid tabellen fick alltså
kvar exakt den signal som orsakade det falska verdiktet. Rättat.

Rättade påståenden och en ny mätning ⇒ MINOR.

### 0.9.0 — 2026-08-26

Rättelser efter §7-granskningen av skiva 8, per post:

**`forbjudna-maskindomaner` sa "Redundant med. Ingen".** Det var falskt och
mätbart falskt. Spärren ligger i två lager, ett i `skal_maskinmail` och ett i
`harled_domaner`, och en fällning av det senare ensamt lämnar hela sviten grön.
Granskaren följde posten, prövade
`test_harledningen_foreslar_aldrig_en_forbjuden_doman` och fick ett FALSKT
vakuöstverdikt på ett äkta spärrtest. Posten namnger nu båda villkoren som
TEXT och det kommando som fäller dem samtidigt.

Det här dokumentet varnar i sin egen ruta överst för precis den felklassen,
och 0.5.0 och 0.7.0 finns för att den redan inträffat. Den här gången fångades
den i granskningen i stället för i sändvägen, vilket är billigare men inte
gratis.

**"361 obesvarade trådar var alltså förmedlade kundärenden".** Övertolkning.
`googlemail.com` står på samma lista och är enligt postens eget stycke ovan
privatpersoner, inte en förmedlare. Talet är antal räddade trådar; hur många
av dem som är förmedlade ärenden är inte mätt. Omskrivet.

**Negativkontrollen påstod fel sak om sitt test.**
`test_undantaget_ar_mer_specifikt_och_provas_forst` anropar aldrig
`skal_maskinmail`. Det asserar bara att `ar_forbjuden` väljer undantaget före
moderdomänen. Beteendet posten beskrev stämmer, men testet visar det inte.
Omskrivet till vad testet faktiskt bevisar.

**`klassning-maskinmail` sa att undantaget körs FÖRST.** Sedan skiva 8 gör det
inte det: förbudslistan går före. Två poster i samma dokument sa emot varandra
om samma funktions ordning. Listan bär nu ett steg 0.

**`test_tom_doman_ar_inte_forbjuden` gick inte att fälla**, alltså UNDERKÄNT
enligt §7.1. Det skickade `aldrig={"x.se"}`, och då är utfallet `False` även
utan raden som fäller tom domän. Testet skickar nu `aldrig={""}`, vilket är
det verkliga fallet: `las_forbjudna` bygger mängden med `d.strip().lower()`,
så en YAML-post `- ""` lägger tomma strängen i mängden och hade då skyddat
varje avsändare utan tolkbar domän. Uppmätt efter rättelsen, mot en svit om
224 test: fällning av villkoret `if not doman:` i `ar_forbjuden` ger
`1 failed, 223 passed`.

**ÖPPEN PUNKT, för Lars.** `config/maskindomaner-forbjudna.yaml` bär under
`undantag` en post för en Intercom-avsändare vars organisationsdomän inte står
under `aldrig_maskin`. Posten är därför verkningslös: `ar_forbjuden` returnerar
`False` för den domänen ändå. Filen är Lars beslutslista och ändras inte av
kod. Frågan är om posten ska bort eller om moderdomänen ska in.

Ny mätning och rättade påståenden ⇒ MINOR.

### 0.8.0 — 2026-08-26

Spärren `forbjudna-maskindomaner` registrerad, på beslut av Lars i skiva 8.
Listan går före all klassning och styr också vad härledningen får föreslå.

Den räddade 361 obesvarade och 13 besvarade trådar som var på väg att kastas som
maskinmail. Det var förmedlade kundärenden: formen maskinell, innehållet affär.
Ingen härledning hade kunnat nå den slutsatsen, eftersom den kräver
verksamhetskunskap om vilka förmedlare som bär affär.

Ny post ⇒ MINOR.

### 0.7.0 — 2026-08-26

Rättelser efter granskning, per post:

- **"En spärr är registrerad" var falskt.** Tabellen bar fem. Meningen räknade
  sin egen omgivning. Struken på plats med not.
- **"Lagren är INTE redundanta med varandra" var falskt om undantaget.**
  `relayar_manniska`s två `continue`-villkor fäller samma fall för
  självadresserat `Reply-To`, och en fällning av det ena ensamt ger GRÖN. En
  granskare som följde posten satte ett falskt vakuöstverdikt på ett äkta test.
  Posten namnger nu båda och hur de fälls tillsammans.
- **Fältet "Redundant med" sa "Ingen annan spärr".** `src/urval.py::ar_massutskick`
  är en avvikande maskinmailregel som fortfarande anropas. Nu namngiven.
- **`persondatakontroll` bevakar nu också `mallar/`, `config/` och `CLAUDE.md`.**
  `mallar/` är den tyngsta posten och saknades: §11 säger att mallarna byggs ur
  rå kundtext.

### 0.6.0 — 2026-08-26

Två spärrar registrerade: `klassning-maskinmail` och `persondatakontroll`.

Den första bär ett UNDANTAG som körs före alla lager, och undantaget är det
farligaste att tappa: utan det klassas webbformulärets notis som maskinmail och
det mest värdefulla kundmaterialet kastas.

Den andra är en pre-commit-hook. Den finns därför att två skivor i rad hade
persondata nära en commit och båda gångerna fångades av granskning. En
granskare tittar ibland; en spärr biter varje gång.

Två nya poster ⇒ MINOR.

### 0.5.0 — 2026-08-26

**Radnumren i `nollfall-max-threads` var föråldrade och gav ett FALSKT
GRÖN-VERDIKT.** `--uteslut` sköt ned villkoren, och det dokumenterade kommandot
raderade fem docstringrader i stället för spärren. Posten namnger nu villkorets
TEXT och ett grep-kommando i stället för radnummer, och rutan överst varnar för
klassen av fel. Posten säger också att villkoren ska NEUTRALISERAS och inte
raderas, eftersom en radering av ett `if`-huvud gör filen syntaktiskt trasig.

**`urval-gmail-svar` pekade på fel fil.** Funktionen flyttade till `src/urval.py`
i skiva 6 och posten hängde kvar i `scripts/tradstruktur.py`.

**Spärren `maskering-persondata` registrerad.** Dess lager ligger i OLIKA FILER,
vilket gör den svår att pröva med ett verktyg som tar ett `--fil`. En granskning
kunde bara redovisa INKONKLUSIVT, och posten skriver ut varför.

Rättade påståenden och en ny post ⇒ MINOR.

### 0.4.0 — 2026-08-26

Spärren `urval-gmail-svar` registrerad. Den kommer inte från sändvägen utan från
urvalet av träningsmaterial, och registreras därför att den är lagrat försvar i
sex lager som INTE är redundanta med varandra. Ett fällt lager syns som ett rött
test; ett saknat lager syns inte alls. Precis så uppstod felet i beslutslogg #7.

Ny post ⇒ MINOR.

### 0.3.0 — 2026-08-26

**`Speglar` ersätts av en sektionspekare utan versionsnummer.** Den öppna fråga
som 0.2.2 ställde till Lars är därmed besvarad: pekaren ska inte bära patchnivå.
Skälet står i den posten och upprepas inte här. Ändrad form på versionshuvudet
⇒ MINOR.

### 0.2.3 — 2026-08-26

Korsreferenssynk till CLAUDE.md 0.3.2. Inget spärrinnehåll ändrat. Posten är
ännu en instans av det som 0.2.2 lyfte som öppen fråga till Lars. ⇒ PATCH.

### 0.2.2 — 2026-08-26

Korsreferensen följer med CLAUDE.md till 0.3.1. Inget spärrinnehåll ändrat.

**Öppen fråga till Lars, som den här posten gör synlig.** Varje PATCH i CLAUDE.md
tvingar fram en versionshöjning i varje dokument som speglar den, enbart för att
hålla §12:s triangel överens. Sådana poster bär inget innehåll och skymmer de
poster som gör det. Alternativet vore att `Speglar` pekar på MAJOR.MINOR och inte
på patchnivån. Frågan avgörs inte här. ⇒ PATCH.

### 0.2.1 — 2026-08-26

Versionshuvudets korsreferens rättad. 0.2.0 satte den till "beslutslogg #1", men
#1 handlar om trådhämtning och kvotpacing, inte om `nollfall-max-threads`. Ingen
beslutspost rör spärrarna, och huvudet säger nu det i stället för att peka på en
post som råkar ligga i samma fil. Ren rättelse av en korsreferens ⇒ PATCH.

### 0.2.0 — 2026-08-26

Första spärren registrerad: `nollfall-max-threads`. Den kommer inte från
sändvägen utan från mining, och den registreras därför att den är **lagrat
försvar i två lager**. I skiva 1 gav en fällning av bara det ena lagret GRÖN, och
granskaren fick upptäcka lagringen på egen hand. Det är exakt vad den här listan
finns för att slippa: §7.1 gör den obligatorisk läsning före varje prövning, och
en oregistrerad lagring gör varje prövning av spärren inkonklusiv utan att det
syns.

Posten namnger båda raderna, kommandot som fäller dem samtidigt, och testet per
lager. Det andra lagret fick sitt eget test i samma skiva, och posten skiljer
därför uttryckligen på hur det MÄTTES i skiva 1 och hur det MÄTS nu: efter det
nya testet ger varje lager RÖD även fällt för sig. Skillnaden är utskriven
eftersom en post som bara sagt "GRÖN vid ett lager" hade varit falsk i samma
stund den skrevs.

Ny post ⇒ MINOR.

### 0.1.0 — 2026-08-26

Dokumentet upprättat som tom mall i samma skiva som `scripts/sparr-prova.sh`,
eftersom CLAUDE.md §7.1 förutsätter att båda finns. Rubrikerna är de fyra §7.1
kräver: spärr, vad den skyddar mot, negativkontroll, redundant med. Inget
innehåll, ingen spärr byggd ännu.
