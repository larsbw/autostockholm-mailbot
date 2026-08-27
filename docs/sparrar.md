# Spärrar

**Version:** 0.13.0 · **Uppdaterad:** 2026-08-27 · **Implementerar** CLAUDE.md §7.1

> **RADNUMMER FÖRÅLDRAS.** Kontrollera alltid att raden i en post fortfarande
> bär det villkor posten påstår, innan du fäller den. En granskning körde det
> dokumenterade kommandot ordagrant, träffade fem docstringrader i stället för
> spärren, och fick verdiktet GRÖN. Ett föråldrat radnummer i det här dokumentet
> producerar alltså ett FALSKT VAKUÖSTVERDIKT, vilket är värre än inget
> dokument. Varje post namnger därför också villkorets TEXT.

`config/sparrar.yaml` byggs i FAS 5, tillsammans med mallarna.

**Slå upp i POSTEN var en spärr sitter och om den är byggd.** Det här stycket
sammanfattar med avsikt ingenting. Noterna nedan redovisar de lydelser som har
försökt göra det, och varför var och en föll: några blev falska av en senare
commit, några var falska redan när de skrevs.

En post märkt **PLANERAD** är registrerad före sin kod, och då saknas fil, villkor
och negativkontroll. **En PLANERAD post går inte att pröva enligt §7.1.**

*Rättelse i 0.13.0: här stod "Sändvägens spärrar är ännu inte byggda och fylls i
FAS 5". Det blev falskt av den commit som byggde `fordonsfakta-ur-uppslag` i fas
4.5.*

*Skivans rättelseförsök, var för sig, eftersom de själva fälldes. Det första
skrev "Undantaget är `fordonsfakta-ur-uppslag`". Falskt om sex av tabellens sju
rader: ingen av de sex byggdes i fas 5. Försöket strök dessutom ordet
"Sändvägens" och gjorde påståendet bredare i stället för sannare. Det andra skrev
"Varje post säger själv i vilken fil sin spärr sitter och om den är byggd", och
lade till en mening om att stycket inte påstod något om posterna som grupp. Den
första meningen ÄR en sådan utsaga, så de två motsade varandra.*

*Gemensamt för alla tre lydelser: de kategoriserade sin egen omgivning, vilket
CLAUDE.md 0.3.1 förbjuder. Stycket sammanfattar därför inte längre posterna alls,
utan hänvisar till dem. Samma stycke har rättats för samma form förut; de
rättelserna står som egna noter omedelbart nedan, under 0.12.0 respektive 0.7.0,
och den listan är redovisningen.*

*Rättelse i 0.12.0: här stod att spärrarna i tabellen inte kommer från
sändvägen, utan från mining, urval, maskering och commitgrinden. Två fel.
Uppräkningen täckte inte `klassning-maskinmail` och `forbjudna-maskindomaner`,
och den senare avgör om en förmedlad kundförfrågan alls blir besvarad, vilket
inte utan vidare ligger utanför sändvägen. Dessutom kategoriserade meningen sin
egen omgivning och blev falsk av den commit som lade en sändvägsspärr i tabellen,
vilket är det CLAUDE.md 0.3.1 förbjuder.*

*Rättelse i samma version, efter tredje granskningsvarvet: den första
omskrivningen sade "Varje post nedan namnger själv var dess spärr sitter". Det
blev falskt av den PLANERAD-post samma commit lade till, som uttryckligen inte
kan namnge fil och villkor. Stycket påstår inte längre något om alla poster.*

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
| `fordonsfakta-ur-uppslag` | Att ett utgående mail namnger fordonsfakta som inte kommer ur ett lyckat uppslag | `test_fullstandigt_svar_slapps_igenom`, `test_svar_med_okanda_nycklar_slapps_ocksa_igenom`, `test_mappningsobjekt_som_inte_ar_dict_slapps_igenom` | Ingen annan spärr. Sex lager i TVÅ funktioner, `_kontrollera` och `Uppslag.__post_init__`, varav 1, 2 och 3 är HELT redundanta. Kända luckor listas i posten. |

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

## `fordonsfakta-ur-uppslag`

**BYGGD I SKIVA 12.** Posten var PLANERAD sedan skiva 11 och bar då inget villkor
och ingen negativkontroll. Båda fälten är nu ifyllda i sak, och spärren är prövad
enligt §7.1.

- **Spärr.** Beslutet ligger i **två funktioner** i `src/fordonsuppslag.py`, och
  delningen är avsiktlig: `_kontrollera` prövar svarets FORM, `Uppslag.__post_init__`
  prövar VÄRDENA. **Ett svar som namnger fordonsfakta skickas inte om fakta inte
  kommer ur ett lyckat uppslag**, och ett tomt eller oväntat svar är INTE ett
  lyckat uppslag: det kastar `UppslagMisslyckades` och ärendet faller till utkast.

  **VÄRDEKONTROLLEN LIGGER I TYPEN och inte hos den som råkar anropa rätt.** Det
  är fyndet ur skiva 12:s granskning: `Uppslag` var först en naken dataklass, så
  `Uppslag("gissning", "kanske")` gick att skapa förbi hela spärren, och sviten
  själv gjorde det i varje utvärderingstest. Nu är normal konstruktion och
  `dataclasses.replace` stängda. Vilka vägar som ÄNDÅ kommer förbi, och att två
  av dem är konstruktion, står som lucka 2 nedan.

  Beslutet fattas på **sex villkor**. Radnumren står inte här, av skälet i rutan
  överst. Slå upp dem med
  `grep -n "raise UppslagMisslyckades" src/fordonsuppslag.py`, som ger sju rader:
  de sex nedan plus regnr-lagret i `slag_upp`. **Det är `raise`-raderna som
  listas, och VILLKORET är raden omedelbart ovanför varje träff** — det är
  villkoret som ska fällas, inte `raise`. Villkoren som TEXT:

  | # | Funktion | Villkoret som fattar beslutet | Vad det fäller |
  | --- | --- | --- | --- |
  | 1 | `_kontrollera` | `if not isinstance(svar, Mapping):` | Hämtningen gav `None`, en rå JSON-sträng, en lista, eller något annat som inte är en post |
  | 2 | `_kontrollera` | `if not _bar_nyckel(svar, "slapvagnsvikt_kg"):` | Tomt eller halvt svar, och allt som inte är ett mappningsobjekt |
  | 3 | `_kontrollera` | `if not _bar_nyckel(svar, "draganordning"):` | Halvt svar, andra fältet, och allt som inte är ett mappningsobjekt |
  | 4 | `Uppslag.__post_init__` | `if isinstance(vikt, bool) or not isinstance(vikt, int):` | Vikt som text, `None`, flyttal eller `bool` |
  | 5 | `Uppslag.__post_init__` | `if vikt < 0:` | Negativ vikt, alltså ett fel i källan |
  | 6 | `Uppslag.__post_init__` | `if not isinstance(drag, bool):` | Draganordning som text, `None` eller heltal |

  Ett sjunde lager ligger i `slag_upp`: `if not normalt:` stoppar ett saknat
  registreringsnummer INNAN hämtningen anropas. Mot en betald källa är den
  ordningen pengar, och `test_hamtningen_anropas_inte_utan_regnr` vaktar den.

  **VARJE VILLKOR RYMS PÅ EN RAD, och det är ett krav och inte en stilfråga.** Ett
  villkor som bryts över flera rader går inte att neutralisera enligt §7.1 utan att
  filen blir syntaktiskt trasig, och då ger prövningen FEL i stället för RÖD.
  `__post_init__` binder därför `vikt` och `drag` till lokala namn först.

  **`bool`-ledet i lager 4 ser överflödigt ut och är det inte.** `bool` är en
  subklass till `int` i Python, så `True` hade passerat som vikten 1 och `False`
  som vikten 0. Ett fabricerat utfall är värre än ett misslyckat uppslag.
- **Vad den skyddar mot.** Ett utgående mail som påstår något om kundens bil som
  ingen källa belägger. Samma regel som `config/priser.json`, av samma skäl:
  **§7.2 säger att ett tal är avläst eller utelämnat**, och en släpvagnsvikt är
  samma sorts påstående som ett pris. Saknas uppslaget faller mailet till
  `utkast`, det fylls inte med ett rimligt värde.

  Det konkreta utfallet den hindrar: ett svar som säger GRÖNT eller RÖTT till en
  kund på grundval av ett tomt eller trasigt svar från datakällan. Utfallet avgör
  om vi säger att bilen går att bygga om, så en fabricerad indata blir ett
  fabricerat besked.

  **VAD DEN INTE SKYDDAR MOT. Kända luckor, med källan per post.** Listan är inte
  en garanti för att den är uttömmande; den är vad granskningen hittade.
  Den står här därför att en spärrpost som bara räknar upp vad spärren gör läses
  som en täckthetsgaranti, och det är just den läsningen som gjorde att den
  första versionen av den här posten kunde skeppas med en väg rakt förbi sig.

  1. **Påhittade men typriktiga värden.** `Uppslag(1400, True)` går att skriva
     utan att någon källa svarat, och ger ett fullt trovärdigt GRÖNT. Typen
     hindrar ogiltiga värden, inte uppdiktade. Det som skyddar är att fas 5
     hämtar sina fakta via `slag_upp`.
     *Källa:* `test_typen_hindrar_ogiltiga_varden_men_inte_pahittade` i sviten.
  2. **Invarianten gäller bara där `__post_init__` faktiskt körs.** Fyra vägar
     kommer förbi, och de ska namnges var för sig i stället för samlas under ett
     ord:

     | Väg | Varför den kommer förbi |
     | --- | --- |
     | `object.__setattr__` på en färdig instans | Går förbi `frozen`, ändrar värdet efteråt |
     | `pickle.loads` | Återskapar instansen utan att köra `__init__` |
     | `object.__new__` | Skapar objektet utan att köra `__init__` |
     | Subklass som skuggar `__post_init__` | Konstruktionen körs, men vakten är överskuggad |

     **Två av dem är KONSTRUKTION**, subklassen och `pickle`, så ordet
     "konstruktionsvägarna är stängda" är fel och används inte. Det som är sant
     är snävare: normal konstruktion och `dataclasses.replace` är stängda.

     Uppmätt: `object.__setattr__(u, "slapvagnsvikt_kg", -5)` på en giltig
     instans ger ett tyst RÖTT, och en subklass som skuggar `__post_init__` ger
     `isinstance(x, Uppslag) is True` med en sträng som vikt.

     **Detta hårdnas medvetet INTE mot.** Boten möter ingen fientlig indata, och
     skyddet är inte tänkt att vara det. Beslut av Lars i skiva 12.
     *Källa:* körningar i varv 2 och varv 3, återgivna i granskningarna.
  3. **En hämtning som KASTAR i stället för att svara.** `slag_upp` fångar inte
     källans egna undantag; de når anroparen. Det är avsiktligt, eftersom en
     källa som är nere inte är samma sak som ett fordon utan uppgifter, men det
     betyder att **spärren täcker svaret och inte tystnaden**. Anroparen i fas 5
     måste hantera båda. Kontraktet står i `slag_upp`:s docstring.
     *Källa:* `slag_upp` saknar `try` kring anropet, avläst i koden, och en
     körning i varv 2 lät ett `RuntimeError` nå anroparen orört.
  4. **`dragkrok_bekraftad_saknas` bär ingen härkomst.** Vikten och
     draganordningen måste passera spärren; den biten är en naken `bool` som
     vilken anropare som helst kan sätta, inklusive en modell. En felaktigt satt
     `True` flyttar kunden från OKLART, alltså en fråga, till GULT, alltså ett
     svar som namnger ett prispåslag. Ingen spärr rör den biten i dag.
     *Källa:* parameterns signatur i `utvardera`, avläst i koden. Ingen körning
     behövs och ingen redovisas.
- **Negativkontroll.** `tests/test_fordonsuppslag.py::test_fullstandigt_svar_slapps_igenom`
  visar att spärren SLÄPPER IGENOM ett fullständigt svar.
  `::test_svar_med_okanda_nycklar_slapps_ocksa_igenom` visar att den inte är för
  bred: okända nycklar tolereras, eftersom varje verklig datakälla bär fler fält
  än de två som gatar och en strikthet mot dem hade fällt varje riktig källa vid
  första bytet.

  Två nollfall vaktar samma sak från andra hållet:
  `::test_draganordning_nej_ar_ett_giltigt_uppslag` och
  `::test_slapvagnsvikt_noll_ar_ett_giltigt_uppslag`. Både `False` och `0` är
  AVLÄSTA värden och inte saknade, och ett lager som prövade sanningsvärdet i
  stället för typen hade fällt dem. En spärr som fäller varje fordonsfaktum vore
  inte en spärr utan ett stopp, och då hade inget av de fyra utfallen i fas 4.5
  gått att besvara.

  Värdekontrollen i typen har sin egen negativkontroll:
  `::test_uppslag_med_giltiga_varden_gar_att_skapa_direkt` visar att ett
  `Uppslag` med giltiga värden fortfarande går att bygga direkt, vilket sviten
  själv gör i varje utvärderingstest. En vakt som fällde varje direkt
  konstruktion hade gjort utvärderingen otestbar.
- **Redundant med. INGEN ANNAN SPÄRR, men lagren är delvis redundanta med
  varandra, och det är uppmätt.**

  **LAGREN 1, 2 OCH 3 ÄR HELT REDUNDANTA MED VARANDRA, och lager 1 är inte
  ensamt avgörande för någonting.** Uppmätt mot modulen i skiva 12:

  | Svar från hämtningen | Lager 1 | Lager 2 | Lager 3 |
  | --- | --- | --- | --- |
  | `None` | fäller | fäller | fäller |
  | rå JSON-sträng | fäller | fäller | fäller |
  | lista | fäller | fäller | fäller |
  | `MappingProxyType` med båda nycklarna | släpper | släpper | släpper |
  | tom `dict` | släpper | fäller | fäller |

  Det var INTE så förut, och skillnaden är en kodrättelse och inte en
  omformulering. Lagren 2 och 3 använde ett naket `nyckel in svar`, och `in`
  fungerar på varje container. **En rå JSON-sträng bär båda nyckelnamnen som
  delsträngar**, så lagren 2 och 3 släppte igenom den och lager 1 var ensamt
  avgörande. Det är normalfelet vid det första bytet av `hamta`: en hämtning som
  glömt parsa svaret. Lagren prövar nu `isinstance(svar, Mapping)` via
  `_bar_nyckel`.

  Kravet gäller `Mapping` och inte `dict`, så en källa som returnerar en
  `MappingProxyType` eller en egen mappningsklass fortfarande går igenom.
  `test_mappningsobjekt_som_inte_ar_dict_slapps_igenom` vaktar det.

  Det är precis §7.1:s klausul om lagrat försvar, och den slog till här: ett
  utkast av den här skivan bar
  `test_lista_som_svar_ar_inte_ett_uppslag` med enbart
  `pytest.raises(UppslagMisslyckades)` och utan assertion mot skälet. Testet
  förblev GRÖNT när lager 1 fälldes ensamt, och granskningen pekade ut det som
  vakuöst. **Varje lagertest asserar därför nu mot `fel.value.skal`.**

  Uppmätt efter rättelsen: fällning av lager 2 ensamt ger `1 failed, 311 passed`
  och felet är `assert 'slapvagnsvikt_kg' in 'svaret saknar draganordning'`.
  Assertionen mot `skal` är alltså det enda som gör lagren prövbara var för sig.

  §7.2:s talregel vaktar samma felklass för priser, ledtider och öppettider, men
  **den är en regel i CLAUDE.md och inte en spärr i det här dokumentet**. Den
  skillnaden är hela poängen med §7.1: en regel läses av den som skriver, en
  spärr biter i koden. Prisregelns spärr byggs i fas 5, och när den finns ska
  båda posterna namnge varandra här.
- **Prövning enligt §7.1, samtliga lager, `scripts/sparr-prova.sh`.** Villkoren
  NEUTRALISERADES till `if False:` och raderades inte: en radering av ett
  `if`-huvud lämnar ett föräldralöst `raise`, och då slutar sviten köra och
  prövningen ger FEL i stället för RÖD.

  | Fällt lager | Utfall | Sviten |
  | --- | --- | --- |
  | 1, `not isinstance(svar, Mapping)` | RÖD | `5 failed, 310 passed` |
  | 2, `not _bar_nyckel(svar, "slapvagnsvikt_kg")` | RÖD | `1 failed, 314 passed` |
  | 3, `not _bar_nyckel(svar, "draganordning")` | RÖD | `1 failed, 314 passed` |
  | 4, `isinstance(vikt, bool) or not isinstance(vikt, int)` | RÖD | `10 failed, 305 passed` |
  | 5, `vikt < 0` | RÖD | `2 failed, 313 passed` |
  | 6, `not isinstance(drag, bool)` | RÖD | `8 failed, 307 passed` |
  | regnr, `not normalt` i `slag_upp` | RÖD | `5 failed, 310 passed` |
  | tröskeln, `< TROSKEL_SLAPVAGNSVIKT_KG` | RÖD | `4 failed, 311 passed` |
  | `uppslag.draganordning` | RÖD | `5 failed, 310 passed` |
  | `dragkrok_bekraftad_saknas` | RÖD | `2 failed, 313 passed` |

  **MAPPNINGSKRAVET I `_bar_nyckel` KRÄVER EN DUBBELFÄLLNING, och det är ett eget
  fynd ur prövningen.** Raden `return isinstance(svar, Mapping) and nyckel in svar`
  fälld ENSAM till `return nyckel in svar` ger **GRÖN**, alltså inkonklusivt:
  lager 1 fäller strängen först och maskerar den. Fälld TILLSAMMANS med lager 1
  ger den `5 failed, 310 passed`, och bland de röda ligger båda parametrarna i
  `test_ra_strang_ar_inte_ett_uppslag`. Kommandot:

  ```
  scripts/sparr-prova.sh --fil src/fordonsuppslag.py \
    --ersatt "<rad i _kontrollera>=    if False:" \
    --ersatt "<rad i _bar_nyckel>=    return nyckel in svar"
  ```

  **Svitens storlek står utskriven bredvid varje tal**, 315 test vid prövningen,
  eftersom ett svitresultat är ett tal om koden OCH om sviten, och sviten växer av
  nästa test som skrivs. Verdikten föråldras inte, talen gör det.

  Tabellen är omkörd i sin helhet efter granskningen: värdekontrollen flyttade
  från `_kontrollera` till `Uppslag.__post_init__`, alltså flyttade raderna, och
  en redovisad prövning mot en tidigare filversion hade varit ett tal om något
  som inte längre finns.

  Återställningen kvitterades efter varje körning i tabellen ovan. **Bara
  sha256-kvittensen bär bevis här.** `src/fordonsuppslag.py` är en NY fil, så
  `git diff` mot den är tom både före och efter fällningen och kan inte skilja
  ett återställt arbetsträd från ett trasigt. `scripts/sparr-prova.sh` skriver
  ut den varningen bara för OTRACKADE filer, och filen var stagad vid
  prövningen, så varningen uteblev. Den står här i stället.

  **Instruktionen till skiva 11 sade "prisregeln i §11". Den står i §7.2.**
  `grep -n "priser.json" CLAUDE.md` ger TVÅ rader, 266 och 371. Rad 266 är
  prisregeln och ligger inom §7.2, vars rubrik står på rad 252 och vars efterföljare
  §8 står på 304. Rad 371 är något annat: §10:s stopp för ändringar i filen, inom
  §10 som börjar på 361. §11 börjar på 381 och bär ingen prisregel; den skjuter
  tvärtom ifrån sig frågan med raden *"Talregeln i §7.2 gäller parallellt och går
  före vid konflikt."*

  Rättat här hellre än återgivet, eftersom en felaktig paragrafhänvisning i ett
  spärrdokument skickar den som ska fälla spärren till fel text. **Radnumren
  föråldras**, enligt rutan överst i det här dokumentet: kommandot ovan är det som
  gäller, inte talen.

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

### 0.13.0 — 2026-08-27

**`fordonsfakta-ur-uppslag` ÄR BYGGD**, i skiva 12, och posten bär nu fil,
villkor, negativkontroll och en fullständig §7.1-prövning. Den var PLANERAD sedan
skiva 11 och gick då inte att pröva.

Spärren ligger i TVÅ funktioner: `_kontrollera` prövar svarets form,
`Uppslag.__post_init__` prövar värdena. Sex villkor, som står som TEXT i posten
och inte som radnummer. Ett sjunde lager i `slag_upp` stoppar ett saknat
registreringsnummer innan hämtningen anropas.

**TREDJE GRANSKNINGSVARVET FÄLLDE EN SPÄRR SOM SLÄPPTE IGENOM EN RÅ JSON-STRÄNG,
och det är den ENDA rättelsen i skivan som ändrade beteende.** Lagren 2 och 3 lät
först `nyckel in svar` avgöra, och `in` fungerar på varje container. En sträng som
`'{"slapvagnsvikt_kg": 1400, ...}'` bär båda nyckelnamnen som delsträngar och
passerade dem; bara lager 1 stoppade den. Det är normalfelet vid det första bytet
av `hamta`, alltså en hämtning som glömt parsa svaret.

Beslut av Lars: en rättad mening om en spärr som fortfarande släpper igenom en
JSON-sträng är sämre än ingen rättelse, eftersom den ser ut som en åtgärd. Lagren
prövar nu `isinstance(svar, Mapping)` via `_bar_nyckel`, kravet gäller `Mapping`
och inte `dict`, och `test_ra_strang_ar_inte_ett_uppslag` samt
`test_mappningsobjekt_som_inte_ar_dict_slapps_igenom` vaktar båda sidorna.

**Mappningskravet krävde en DUBBELFÄLLNING för att bevisas.** Fällt ensamt ger det
GRÖN, eftersom lager 1 maskerar det. Kommandot och utfallen står i posten.

**GRANSKNINGEN FÄLLDE OCKSÅ EN VÄG RAKT FÖRBI SPÄRREN.** `Uppslag` var först en
naken dataklass utan konstruktorvakt, medan
modulens docstring påstod att en instans "bara kan skapas via `slag_upp`".
`Uppslag("gissning", "kanske")` gick att skapa, och med typriktiga men påhittade
tal gav den ett fullt trovärdigt GRÖNT. Sviten själv gick den vägen i varje
utvärderingstest. Värdekontrollen flyttade därför in i `__post_init__`, så att
normal konstruktion och `dataclasses.replace` är stängda. Vilka vägar som ändå
kommer förbi står som en egen lucka i posten, med var och en namngiven.

**Ett spärrtest var vakuöst och är rättat.** `test_lista_som_svar_ar_inte_ett_uppslag`
asserade bara `pytest.raises` och förblev grönt när lager 1 fälldes ensamt,
eftersom en lista fälls av lagren 1, 2 OCH 3. Det är §7.1:s klausul om lagrat
försvar, i samma commit som skrev ut klausulen. Varje lagertest asserar nu mot
`fel.value.skal`.

**REDUNDANSEN ÄR REGISTRERAD, och lagren 2 och 3 är dessutom RÄTTADE I KODEN.**
Ett utkast av den här skivan lät dem pröva `nyckel in svar`, och `in` fungerar på
varje container: en rå JSON-sträng bär båda nyckelnamnen som delsträngar och
passerade. Det är normalfelet vid det första bytet av `hamta`. Lagren prövar nu
`isinstance(svar, Mapping)` via `_bar_nyckel`, och lager 1 är därmed inte ensamt
avgörande för någonting. Beslut av Lars: en rättad mening om en spärr som
fortfarande släpper igenom en JSON-sträng är sämre än ingen rättelse, eftersom
den ser ut som en åtgärd.

**SPÄRRENS KÄNDA LUCKOR står nu utskrivna** i fältet *Vad den skyddar mot*, var
och en med sin källa och utan påstående om att listan är uttömmande: påhittade
men typriktiga värden, invarianten som gäller konstruktionen och inte en färdig
instans, en hämtning som kastar i stället för att svara, och
`dragkrok_bekraftad_saknas` som saknar härkomstkrav. En spärrpost som bara räknar
upp vad spärren gör läses som en täckthetsgaranti, och det var precis den
läsningen som lät den första versionen skeppas med en väg förbi sig.

**Prövningen är omkörd i sin helhet efter rättelserna**, eftersom värdekontrollen
bytte funktion och raderna flyttade. Villkoren NEUTRALISERADES till `if False:`
och raderades inte: en radering av ett `if`-huvud lämnar ett föräldralöst
`raise`, och då ger prövningen FEL i stället för RÖD. Varje villkor ryms därför
också på EN rad, vilket är ett krav och inte en stilfråga.

**En mening i huvudet blev falsk av den här posten och är rättad på plats.**
Rättelseförsöken redovisas var för sig i noten där, utan summa: ett skrev
"Undantaget är", ett skrev "Varje post säger själv". Båda var utsagor om
posterna som grupp, alltså samma form som fällts förut, och stycket
sammanfattar dem inte längre alls.

Ny prövad spärr ⇒ MINOR.

### 0.12.0 — 2026-08-27

**Spärren `fordonsfakta-ur-uppslag` registrerad**, på beslut av Lars i skiva 11.
Ett svar som namnger fordonsfakta skickas inte om fakta inte kommer ur ett
lyckat uppslag.

**POSTEN ÄR REGISTRERAD FÖRE SIN KOD, och det är utskrivet i posten.** Spärren
byggs i fas 5. Fältet **Negativkontroll kan därför inte fyllas**, eftersom inget
test finns, och fältet säger det i klartext i stället för att stå tomt. Skälet är
mallens, om än uttalat för ett annat fält: dess punkt *Redundant med* säger att
"ett tomt fält går inte att skilja från ett obesvarat fält", och det gäller
*Negativkontroll* lika mycket. En påhittad testnamnsrad hade varit värre än båda:
den hade producerat exakt det falska prövbarhetssken som rutan överst varnar för.

Fil och villkorets TEXT kan inte heller namnges ännu, och posten skriver ut att
den ska kompletteras i samma skiva som spärren byggs.

**Fältet "Redundant med" säger INGEN REGISTRERAD SPÄRR.** §7.2:s talregel vaktar
samma felklass för priser och fakta, men den är en regel i CLAUDE.md och inte en
spärr i det här dokumentet. Prisregelns spärr är inte byggd heller.

**Instruktionen till skiva 11 placerade prisregeln i §11. Den står i §7.2.**
`grep -n "priser.json" CLAUDE.md` ger TVÅ rader, 266 och 371, och posten återger
båda: 266 är prisregeln inom §7.2, 371 är §10:s stopp för ändringar i filen. §11
bär ingen prisregel utan hänvisar till §7.2 för talfrågan. Rättat i posten i
stället för återgivet, eftersom en felaktig paragrafhänvisning i ett
spärrdokument leder den som ska fälla spärren till fel text.

**En mening i huvudet blev falsk av den här posten och är rättad på plats.**
Stycket sade att spärrarna i översiktstabellen inte kommer från sändvägen, utan
från mining, urval, maskering och commitgrinden.

Ett första utkast till rättelse behöll uppräkningen och lade bara till ordet
BYGGDA. §7-granskningen fällde den: uppräkningen täckte inte
`klassning-maskinmail` och `forbjudna-maskindomaner`, och den senare avgör om en
förmedlad kundförfrågan alls blir besvarad, vilket inte utan vidare ligger
utanför sändvägen. Rättelsen hade dessutom behållit formen som var felet, en
mening som kategoriserar sin egen omgivning och blir falsk av nästa commit.

**Ett andra utkast bytte kategoriseringen mot en annan universell utsaga**,
"Varje post nedan namnger själv var dess spärr sitter", och den var falsk redan
när den skrevs: PLANERAD-posten i samma commit kan inte namnge fil och villkor.
Stycket säger nu i stället att varje post ska läsas för sig, och påstår ingenting
om alla poster.

Det är RÄTTELSETEXT GRANSKAS SOM NY TEXT i praktiken, två gånger om samma
stycke: båda rättelserna svarade på fyndet utan att bli sanna om filen.

**Rubriknoten i den nya posten beskrev mallen fel och är rättad.** Den sade att
posten är "ofärdig i den mening mallen definierar". Mallen definierar ofärdig som
ett TOMT fält, *"Varje fält fylls i, tomma fält är en ofärdig post"*, och inget
fält i posten är tomt. Noten sade också
att bara *Negativkontroll* var ofyllbart; även *Spärr* är det, eftersom mallen
kräver fil och villkor och koden inte finns. Noten namnger nu båda fälten och
skiljer på ofullständig i sak och fullständig i form.

Ny post ⇒ MINOR.

### 0.11.3 — 2026-08-27

**0.11.2 införde en förbjuden processräkning i samma commit som strök en ur
incidentloggen.** Den skrev "Detta är tredje gången samma felklass registreras i
repot" och kallade sig själv "den andra kända instansen i `docs/sparrar.md`".
Båda är räkningar av instanser av ett mönster, vilket §7.2 namnger ordagrant som
förbjudet, och talen saknade underlag. De registrerade instanserna är CLAUDE.md
0.4.1, som skriver att 0.4.0-posten namngav fel post för strykningen, och
`docs/sparrar.md` 0.11.1. Stycket namnger dem nu och skriver ingen summa.

**Ingen `grep`-utdata anges som belägg här**, och det är avsiktligt. Ett sådant
kommando träffar även de rättelseposter som SKRIVER om felklassen, alltså den
här posten och 0.11.2, så utdatan växer av varje ny rättelse och en mening som
citerar dess antal blir falsk av sin egen commit. Instanserna namnges i stället.

**0.11.1 skrevs om på plats i skiva 10 utan kursiv not.** Det är samma formfel
som 0.11.1 själv registrerade mot 0.10.0. Den här posten är noten, i efterhand.

Rättade påståenden ⇒ PATCH.

### 0.11.2 — 2026-08-27

**0.11.1 namngav fel post, två gånger.** Den skrev att båda dess rättelser låg i
0.11.0-posten, och att stycket om översiktstabellen var 0.11.0:s. Stycket ligger
i 0.10.0-posten.

Avläst genom att jämföra radnumret för stycket mot rubrikraderna ur
`grep -n "^### " docs/sparrar.md`: det omskrivna stycket och dess kursiva not
ligger EFTER rubriken `### 0.10.0` och FÖRE `### 0.9.0`. Den andra rättelsen,
noten om "Två strykningar", ligger däremot mellan `### 0.11.0` och `### 0.10.0`
och alltså i 0.11.0 precis som posten sa.

**Radnumren skrivs inte ut här, och det är avsiktligt.** Ett utkast av den här
posten bar dem, och de var föråldrade innan posten ens committades: posten sköt
själv ner alla rubriker under sig när den lades överst i appendixet. Det är samma
mekanism som rutan överst i det här dokumentet varnar för, och den slår till
snabbast just i en appendixpost.

**Samma felklass finns registrerad på ett ställe till.** CLAUDE.md 0.4.1 skriver
"0.4.0-posten namngav fel post för strykningen". Instanserna, avlästa ur
`grep -rn "namngav fel post" docs/ CLAUDE.md`, är den posten och den här; båda
gällde en rättelsepost som pekade på fel granne. Ingen summa skrivs, eftersom en
räkning av instanser av ett mönster är den form §7.2 förbjuder.

En rättelsenot pekar på en post ovanför sig i filen, och
avståndet mellan noten och rubriken är oftast bara några rader, vilket gör det
lätt att skriva rubriken ur minnet i stället för att slå upp den.

**Vakten mot det är mekanisk, inte moralisk:** slå upp rubrikraden med
`grep -n "^### " docs/sparrar.md` och jämför radnumret INNAN posten namnges.
Det är den kontroll som saknades i båda instanserna.

Rättade påståenden ⇒ PATCH. Skivan åberopar §7:s dokumentdetaljundantag för den
här posten, alltså EN granskningsomgång, och statusen är utskriven i skiva 10:s
rapport.

### 0.11.1 — 2026-08-27

Två rättelser efter §7-granskningen av skiva 9, en i 0.11.0-posten och en i
0.10.0-posten.

**"Två strykningar" var en.** Diffen mot `196e60a` bär en kursiv not, i
0.8.0-posten. §7.2: självrapportering verifieras mot diffen, inte mot minnet av
avsikten.

**0.10.0:s stycke om översiktstabellen skrevs om på plats utan not.** Det sa att
BÅDA de namngivna raderna skriver ut "Sig själv, två lager"; raden för
`urval-gmail-svar` skriver "sex lager". Omskrivningen har nu sin kursiva not.

**Om formen, och det är fyndets egentliga innehåll.** Båda rättelserna skrevs in
i `2d43d00` med noter som hänvisade till "0.11.1", medan filhuvudet stod kvar på
0.11.0 och ingen 0.11.1-post fanns. Noterna pekade alltså på en version som inte
existerade, vilket är ett falskt påstående om repot i just de meningar som skulle
rätta ett annat. Den här posten är den version noterna pekar på.

Rättade påståenden ⇒ PATCH.

### 0.11.0 — 2026-08-26

Skiva 8:s tredje granskningsvarv underkände fem punkter, och Lars grindbeslut var
att inte bevilja ett fjärde varv. Fynd 1 och 5 rör det här dokumentet och rättas
här. Bägge är text om kod och omfattas av §7:s dokumentdetaljundantag, som från
och med CLAUDE.md 0.7.0 gäller per defektklass.

**Fynd 1: den strukna övertolkningen stod kvar i samma fil som förklarade den
struken.** 0.9.0-posten skrev att meningen "361 obesvarade trådar var alltså
förmedlade kundärenden" var struken ur huvudposten. Den fanns i två instanser, och
0.8.0-postens instans stod kvar orättad. Nu struken på plats med en kursiv not, som
`docs/beslutslogg.md`:s undantag föreskriver.

Det är samma felklass som posten själv rättar, en version senare, i samma fil. Det
är därför skiva 8 fick incidentpost I2 i `docs/incidentlogg.md`.

**Fynd 5: en rad i översiktstabellen tillskrevs fel ordalydelse.** 0.10.0-posten
skrev att raderna för `nollfall-max-threads` och `urval-gmail-svar` båda skriver ut
"Sig själv, två lager". Raden för `urval-gmail-svar` skriver "sex lager". Rättat.

En strykning och en rättad ordalydelse ⇒ MINOR.

*Rättelse i 0.11.1: här stod "Två strykningar". Diffen bär en, i 0.8.0-posten.
§7.2:s krav på att självrapportering verifieras mot diffen, inte mot minnet av
avsikten.*

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

**Översiktstabellens rad namngav inte lagren.** Raden för
`nollfall-max-threads` skriver ut "Sig själv, två lager" och den för
`urval-gmail-svar` "Sig själv, sex lager", medan `forbjudna-maskindomaner`
bara sa "Går FÖRE `klassning-maskinmail`". En granskare som stannar vid
tabellen fick alltså kvar exakt den signal som orsakade det falska verdiktet.
Rättat.

*Rättelse i 0.11.1: stycket ovan skrevs om på plats i skiva 9. Det sa tidigare
att BÅDA raderna skriver ut "Sig själv, två lager"; raden för
`urval-gmail-svar` skriver "sex lager". Omskrivningen saknade den här noten,
vilket är samma formfel som 0.9.0 rättade i en annan post.*

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
maskinmail.

*Rättelse i 0.11.0: här stod att de räddade trådarna VAR förmedlade
kundärenden, med formen maskinell och innehållet affär. Struket. Hur många av
dem som är förmedlade ärenden är inte mätt, och `googlemail.com` står på samma
lista utan att vara en förmedlare. Huvudposten rättades i 0.9.0; den här
instansen stod kvar i samma fil som förklarade den struken, och det är fynd 1 i
skiva 8:s tredje granskningsvarv.*

Ingen härledning hade kunnat nå listan, eftersom den kräver verksamhetskunskap
om vilka förmedlare som bär affär.

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
