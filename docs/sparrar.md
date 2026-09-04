# Spärrar

**Version:** 0.26.0 · **Uppdaterad:** 2026-09-04 · **Implementerar** CLAUDE.md §7.1

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
redundanta med avsikt, och en fällning som inte tar hänsyn till det ger ett
verdikt som inte betyder vad det ser ut att betyda.

> ### EN SAMMANSLAGEN FÄLLNING LJUGER ÅT BÅDA HÅLLEN
>
> **FÄLLER DU FÖR FÅ LAGER FÅR DU FALSKT VAKUÖST.** Fälls bara det ena lagret
> förblir sviten grön, och prövningen pekar ut ett äkta spärrtest som vakuöst.
> Ett grönt utfall efter att ETT lager fällts är INKONKLUSIVT, inte vakuöst: det
> bevisar bara att just den raden inte är ENSAM avgörande.
>
> **FÄLLER DU FÖR MÅNGA RADER PÅ EN GÅNG FÅR DU FALSKT ÄKTA.** Ett rött utfall
> efter att FLERA rader fällts bevisar bara att MINST EN av dem bär. Det säger
> ingenting om de övriga, och läses ändå rutinmässigt som att alla gör det.
>
> **De två felen har motsatt bot, och det är därför båda står här.** Mot det
> första: fäll samtliga lager i samma körning. Mot det andra: fäll varje
> verkställighetspunkt ENSAM, och redovisa utfallet per rad.
>
> ```
> scripts/sparr-prova.sh --fil src/x.py --radera 42 --radera 87   # båda lagren
> scripts/sparr-prova.sh --fil src/x.py --radera 42               # och var för sig
> scripts/sparr-prova.sh --fil src/x.py --radera 87
> ```
>
> **Den andra riktningen är MÄTT, inte befarad.** Skiva 27 fällde
> `krav_pa_skrivbar_sokvag(parfil)` och `krav_pa_skrivbar_sokvag(omdomesfil)`
> tillsammans, fick RÖD, och skrev in det som belägg för att båda var vaktade.
> §7-granskningens första varv raderade sedan `krav_pa_skrivbar_sokvag(omdomesfil)`
> ENSAM och fick **hela sviten grön**: raden var vakuös, och §6 obevakad på vägen
> genom omdömesloggen. Se posten `vyn-skriver-bara-till-data-och-logg`.
>
> **Skillnaden mellan lager och verkställighetspunkter avgör vilken riktning som
> hotar.** Två LAGER som fångar samma fall ska fällas tillsammans. Två
> VERKSTÄLLIGHETSPUNKTER som var och en vaktar sin egen väg ska fällas var för
> sig. Kolumnen **Redundant med** säger vilket som är vilket, och det är därför
> den aldrig får lämnas tom.

---

## Översikt

| Spärr | Vad den skyddar mot | Negativkontroll | Redundant med |
| --- | --- | --- | --- |
| `nollfall-max-threads` | Att en körning som ombeds hämta noll trådar raderar föregående skörd | `test_alla_tradar_over_flera_sidor_hamtas` | Sig själv, två lager i `src/mine.py`. Se posten. |
| `urval-gmail-svar` | Att maskinskriven text blir mall och att kundens röst räknas bort | `test_svar_skrivet_i_gmail_kanns_igen`, `test_inkommande_ar_kundmeddelande` | Sig själv, sex lager i `ar_gmail_svar`. Se posten. |
| `maskering-persondata` | Att persondata når ett dokument under `docs/` | `test_ord_vid_meningsstart_maskeras_ocksa` | `src/cluster.py::namn_i_korpus`, i en ANNAN fil, och `scripts/persondatakontroll.py`. Se posten. |
| `klassning-maskinmail` | Att nyhetsbrev och notiser blir kundärenden | `test_vanligt_kundmail_ar_inte_maskinmail` | Fyra lager plus ett UNDANTAG. Se posten. |
| `persondatakontroll` | Att en commit för in persondata i en bevakad sökväg. Vilka de är står i `BEVAKADE` i skriptet. | `test_ren_text_ger_inga_fynd` | `maskering-persondata`. Sista linjen, inte den enda. |
| `forbjudna-maskindomaner` | Att en förmedlad kundförfrågan kastas som maskinmail | `test_liknande_doman_skyddas_inte_av_misstag` | Sig själv, två lager i `src/klassa_maskin.py`, och går FÖRE `klassning-maskinmail`. Se posten. |
| `fordonsfakta-ur-uppslag` | Att ett utgående mail namnger fordonsfakta som inte kommer ur ett lyckat uppslag | `test_fullstandigt_svar_slapps_igenom`, `test_svar_med_okanda_nycklar_slapps_ocksa_igenom`, `test_mappningsobjekt_som_inte_ar_dict_slapps_igenom` | Ingen annan spärr. Formlager i `_kontrollera` och värdelager i `Uppslag.__post_init__` via `_krav_pa_vikt`. Formlagren är HELT redundanta med varandra, och viktlagren DELAS av två fält. Kända luckor listas i posten. |
| `fordonsfakta-ur-sida` | Att ett tal eller ett dragkroksbesked läses ur en annan sida än det efterfrågade fordonets, eller ur en etikett som bara inleds likadant | `test_alla_tre_falten_lases_ur_ett_avlast_svar`, `test_avlast_fordon_ger_oklart`, `test_normaliserat_nummer_slar_igenom_till_canonical` | `fordonsfakta-ur-uppslag`, men bara DELVIS: den fångar saknade och otolkbara fält, aldrig ett välformat tal ur fel sida. Fyra lager, lager 3 ensamt om sitt fall. Se posten. |
| `dragkrokbesked-har-harkomst` | Att ett besked om dragkrok sätts av en modell och flyttar kunden från en fråga till ett prispåslag | `test_bada_tillatna_kallorna_gar_igenom` | Ingen annan spärr. Se posten, särskilt vad den INTE kan hindra. |
| `kanal-som-kontext-aldrig-grund` | Att kanalen ett mail kom in genom blir ensam grund för dess kategori | `test_kanalen_overstyr_aldrig_modellens_svar`, `test_samma_svar_ger_samma_etikett_med_och_utan_kanal`, `test_kanalen_gor_inte_ett_svar_utanfor_taxonomin_giltigt` | Ingen annan spärr. Vaktar FRÅNVARON av kod och fälls därför genom att skriva dit kopplingen. Se posten. |
| `vyn-har-ingen-sandvag` | Att ett referenssvar lämnar servern som mail | `test_en_ren_modul_slapps_igenom` | Ingen annan spärr. TVÅ LAGER, importlagret och källtextlagret, och de fångar olika fall. Se posten. |
| `spärrfälld-post-utan-textfalt` | Att §9.1:s förbud mot att skriva om ett fällt mail blir ett klick | `test_osparrad_post_visar_textfalt` | Ingen annan spärr. Skyddar gränssnittet, inte texten. Se posten. |
| `vyn-skriver-bara-till-data-och-logg` | Att rå kundtext skrivs till en fil som pushas | `test_de_tva_gitignorerade_katalogerna_slapps_igenom` | `persondatakontroll`, men bara delvis: den fäller vid commit, alltså efter skrivningen. Se posten. |

**Tabellen räknar SPÄRRAR, alltså sådant som kod verkställer.** Dokumentet bär
dessutom poster märkta LUCKA UTAN SPÄRR, som ingen kod implementerar och som
därför inte kan bära någon av kolumnerna ovan: `gmail-etikett-som-ensam-grund`
och `versalkansligt-monster-i-avlasare`. De står i egna sektioner före mallen.
Den som läser den här listan före en prövning enligt §7.1 ska läsa dem också.

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
  innehåll matchar mönster för mailadress, telefonnummer, registreringsnummer,
  postnummer med ort, gatuadress eller personnummer. Installeras som
  pre-commit-hook med `scripts/installera-hook.sh`.

  **Vilka sökvägar som bevakas står i `BEVAKADE` i skriptet, inte här.** Listan
  har utvidgats mer än en gång, och en kopia i det här dokumentet blir föråldrad
  av nästa utvidgning. `test_kod_bevakas_inte` och `test_scripts_bevakas` binder
  ytterkanterna: `src/` och `tests/` är utanför, `scripts/` är innanför.

  *Fältet sade tidigare att spärren gäller stagat innehåll under `docs/`. Det
  var föråldrat redan när `mallar/`, `config/` och `CLAUDE.md` lades till i
  0.7.0, alltså långt före den här rättelsen.*
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

- **Spärr.** Beslutet ligger i **FYRA funktioner** i `src/fordonsuppslag.py`, och
  delningen är avsiktlig:

  | Funktion | Vad den prövar |
  | --- | --- |
  | `_kontrollera` | Svarets FORM: att det är ett mappningsobjekt och att alla tre nycklarna finns |
  | `_krav_pa_vikt` | VÄRDENA i de två vikterna, delat mellan dem |
  | `Uppslag.__post_init__` | Draganordningens värde, och anropar viktkravet |
  | `slag_upp` | Att ett registreringsnummer alls finns, INNAN hämtningen anropas |

  **DEN SOM SKA FÄLLA SPÄRREN ENLIGT §7.1 MÅSTE FÄLLA I ALLA FYRA.** En prövning
  som bara rör `_kontrollera` når varken viktlagren eller regnr-lagret och ger ett
  inkonklusivt verdikt som ser konklusivt ut. Ett femte ställe, `_bar_nyckel`,
  bär mappningskravet och kräver en dubbelfällning; det redovisas för sig längre
  ned.

  **Ett utkast av den här posten sade "två funktioner"** och namngav bara
  `_kontrollera` och `Uppslag.__post_init__`. Det blev falskare av skiva 13, som
  bröt ut `_krav_pa_vikt` och samtidigt strök den mening som var regnr-lagrets
  enda hemvist i fältet.

  **Ett svar som namnger fordonsfakta skickas inte om fakta inte kommer ur ett
  lyckat uppslag**, och ett tomt eller oväntat svar är INTE ett lyckat uppslag:
  det kastar `UppslagMisslyckades` och ärendet faller till utkast.

  **VÄRDEKONTROLLEN LIGGER I TYPEN och inte hos den som råkar anropa rätt.** Det
  är fyndet ur skiva 12:s granskning: `Uppslag` var först en naken dataklass, så
  `Uppslag("gissning", "kanske")` gick att skapa förbi hela spärren, och sviten
  själv gjorde det i varje utvärderingstest. Nu är normal konstruktion och
  `dataclasses.replace` stängda. Vilka vägar som ÄNDÅ kommer förbi, och att två
  av dem är konstruktion, står som lucka 2 nedan.

  Radnumren står inte här, av skälet i rutan överst. Slå upp dem med
  `grep -n "raise UppslagMisslyckades" src/fordonsuppslag.py`. **Det är
  `raise`-raderna som listas, och VILLKORET är raden omedelbart ovanför varje
  träff** — det är villkoret som ska fällas, inte `raise`. Villkoren som TEXT:

  | Funktion | Villkoret som fattar beslutet | Vad det fäller |
  | --- | --- | --- |
  | `_kontrollera` | `if not isinstance(svar, Mapping):` | Hämtningen gav `None`, en rå JSON-sträng, en lista, eller något annat som inte är en post |
  | `_kontrollera` | `if not _bar_nyckel(svar, "tjanstevikt_kg"):` | Svar utan tjänstevikt, och allt som inte är ett mappningsobjekt |
  | `_kontrollera` | `if not _bar_nyckel(svar, "slapvagnsvikt_kg"):` | Svar utan släpvagnsvikt, och detsamma |
  | `_kontrollera` | `if not _bar_nyckel(svar, "draganordning"):` | Svar utan draganordning, och detsamma |
  | `_krav_pa_vikt` | `if isinstance(varde, bool) or not isinstance(varde, int):` | Vikt som text, `None`, flyttal eller `bool` |
  | `_krav_pa_vikt` | `if varde < 0:` | Negativ vikt, alltså ett fel i källan |
  | `Uppslag.__post_init__` | `if not isinstance(drag, bool):` | Draganordning som text, `None` eller heltal |
  | `slag_upp` | `if not normalt:` | Saknat registreringsnummer, INNAN hämtningen anropas |

  **VIKTLAGREN DELAS AV TVÅ FÄLT.** `_krav_pa_vikt` anropas för både
  `tjanstevikt_kg` och `slapvagnsvikt_kg`, så **en fällning där fäller båda
  fälten samtidigt.** Det är avsiktligt: kravet är identiskt och två kopior hade
  drivit isär. Skälet bär fältnamnet, så testerna kan ändå skilja fälten åt, och
  varje viktest asserar mot `f"{falt} är ..."` och inte bara mot ordet.

  Regnr-lagret i `slag_upp` stoppar ett saknat nummer INNAN hämtningen anropas.
  Mot en betald källa är den ordningen pengar, och
  `test_hamtningen_anropas_inte_utan_regnr` vaktar den.

  **VARJE VILLKOR RYMS PÅ EN RAD, och det är ett krav och inte en stilfråga.** Ett
  villkor som bryts över flera rader går inte att neutralisera enligt §7.1 utan att
  filen blir syntaktiskt trasig, och då ger prövningen FEL i stället för RÖD.
  `__post_init__` binder därför `drag` till ett lokalt namn först, och
  `_krav_pa_vikt` finns delvis av samma skäl.

  **`bool`-ledet i viktlagret ser överflödigt ut och är det inte.** `bool` är en
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

  1. **Påhittade men typriktiga värden.** `Uppslag(1500, 1400, True)` går att
     skriva utan att någon källa svarat, och ger ett fullt trovärdigt GRÖNT.
     Typen hindrar ogiltiga värden, inte uppdiktade. Det som skyddar är att fas 5
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
  4. **Dragkroksbeskedets härkomst.** Luckan stod här till och med skiva 12:
     beskedet var en naken `bool` som vem som helst kunde sätta. Den har nu en
     egen spärr, `dragkrokbesked-har-harkomst` nedan, och det som ÅTERSTÅR av
     luckan står i den posten i stället för här.
- **Negativkontroll.** `tests/test_fordonsuppslag.py::test_fullstandigt_svar_slapps_igenom`
  visar att spärren SLÄPPER IGENOM ett fullständigt svar.
  `::test_svar_med_okanda_nycklar_slapps_ocksa_igenom` visar att den inte är för
  bred: okända nycklar tolereras, eftersom varje verklig datakälla bär fler fält
  än de TRE som gatar och en strikthet mot dem hade fällt varje riktig källa vid
  första bytet.

  Nollfallen vaktar samma sak från andra hållet:
  `::test_draganordning_nej_ar_ett_giltigt_uppslag` och
  `::test_vikt_noll_ar_ett_giltigt_uppslag`, det senare parametriserat över BÅDA
  vikterna. Både `False` och `0` är AVLÄSTA värden och inte saknade, och ett
  lager som prövade sanningsvärdet i stället för typen hade fällt dem. En spärr
  som fäller varje fordonsfaktum vore inte en spärr utan ett stopp, och då hade
  inget av de fyra utfallen i fas 4.5 gått att besvara.

  Värdekontrollen i typen har sin egen negativkontroll:
  `::test_uppslag_med_giltiga_varden_gar_att_skapa_direkt` visar att ett
  `Uppslag` med giltiga värden fortfarande går att bygga direkt, vilket sviten
  själv gör i varje utvärderingstest. En vakt som fällde varje direkt
  konstruktion hade gjort utvärderingen otestbar.
- **Redundant med. INGEN ANNAN SPÄRR, men lagren är delvis redundanta med
  varandra, och det är uppmätt.**

  **FORMLAGREN ÄR HELT REDUNDANTA MED VARANDRA, och Mapping-lagret är inte
  ensamt avgörande för någonting.** Uppmätt mot modulen:

  | Svar från hämtningen | Mapping-lagret | Nyckellagren |
  | --- | --- | --- |
  | `None` | fäller | fäller |
  | rå JSON-sträng | fäller | fäller |
  | lista | fäller | fäller |
  | `MappingProxyType` med alla nycklar | släpper | släpper |
  | tom `dict` | släpper | fäller |

  Det var INTE så förut, och skillnaden är en kodrättelse och inte en
  omformulering. Nyckellagren använde ett naket `nyckel in svar`, och `in`
  fungerar på varje container. **En rå JSON-sträng bär alla nyckelnamnen som
  delsträngar**, så nyckellagren släppte igenom den och Mapping-lagret var ensamt
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

  Assertionen mot `skal` är det enda som gör lagren prövbara var för sig, och
  varje viktest asserar dessutom mot fältnamnet, eftersom `_krav_pa_vikt` delas
  av två fält.

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
  | `not isinstance(svar, Mapping)` | RÖD | `5 failed, 349 passed` |
  | `not _bar_nyckel(svar, "tjanstevikt_kg")` | RÖD | `2 failed, 352 passed` |
  | `not _bar_nyckel(svar, "slapvagnsvikt_kg")` | RÖD | `1 failed, 353 passed` |
  | `not _bar_nyckel(svar, "draganordning")` | RÖD | `1 failed, 353 passed` |
  | `_krav_pa_vikt`, typkravet | RÖD | `20 failed, 334 passed` |
  | `_krav_pa_vikt`, teckenkravet | RÖD | `4 failed, 350 passed` |
  | `not isinstance(drag, bool)` | RÖD | `8 failed, 346 passed` |
  | regnr, `not normalt` i `slag_upp` | RÖD | `5 failed, 349 passed` |
  | §42, `tjanstevikt_kg >= TROSKEL_TJANSTEVIKT_KG` | RÖD | `4 failed, 350 passed` |
  | §42, `slapvagnsvikt_kg >= TROSKEL_SLAPVAGNSVIKT_KG` | RÖD | `10 failed, 344 passed` |
  | `not ar_lamplig_som_dragfordon(uppslag)` | RÖD | `5 failed, 349 passed` |
  | `uppslag.draganordning` | RÖD | `6 failed, 348 passed` |
  | `besked is not None and besked.saknas` | RÖD | `2 failed, 352 passed` |

  **REGRESSIONSVAKTEN ÄR PRÖVAD.** Fällningen av §42:s tjänsteviktsvillkor gör
  `test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott` RÖTT. Det är testet som finns
  för att skiva 12:s defekt, att ett fordon med tjänstevikt 2 100 kg och
  släpvagnsvikt 800 kg fick RÖTT, inte ska kunna återkomma tyst.

  **MAPPNINGSKRAVET I `_bar_nyckel` KRÄVER EN DUBBELFÄLLNING, och det är ett eget
  fynd ur prövningen.** Raden `return isinstance(svar, Mapping) and nyckel in svar`
  fälld ENSAM till `return nyckel in svar` ger **GRÖN**, alltså inkonklusivt:
  Mapping-lagret fäller strängen först och maskerar den. Fälld TILLSAMMANS med
  det ger den `5 failed, 349 passed`, och bland de röda ligger båda parametrarna
  i `test_ra_strang_ar_inte_ett_uppslag`. Kommandot:

  ```
  scripts/sparr-prova.sh --fil src/fordonsuppslag.py \
    --ersatt "<rad i _kontrollera>=    if False:" \
    --ersatt "<rad i _bar_nyckel>=    return nyckel in svar"
  ```

  **Svitens storlek står utskriven bredvid varje tal**, 354 test vid prövningen,
  eftersom ett svitresultat är ett tal om koden OCH om sviten, och sviten växer av
  nästa test som skrivs. Verdikten föråldras inte, talen gör det.

  Tabellen körs om i sin helhet varje gång modulen ändras, och den ändrades
  flera gånger i skiva 13: det tredje fältet kom in, granskningen lade till en
  rad i `utvardera`, och ett test togs bort. **Antalet omkörningar skrivs inte
  ut**, eftersom det är ett arbetsförlopp och inte något som går att läsa ur
  repot (§7.2). Det som räknas är att talen ovan gäller filen som den ligger nu:
  en redovisad prövning mot en tidigare filversion är ett tal om något som inte
  längre finns.

  Återställningen kvitterades efter varje körning i tabellen ovan. **BARA
  sha256-kvittensen bär bevis, och det avgörande är att arbetet är STAGAT.**

  `scripts/sparr-prova.sh` bygger sin andra kvittens på `git diff -- <fil>`,
  alltså arbetsträd mot INDEX. När arbetsträdet är identiskt med indexet är den
  diffen tom både före och efter en fällning, och kvittensen jämför tomt mot
  tomt. Den som vill se det själv jämför `git diff --stat -- <fil>`, som är tom,
  mot `git diff HEAD --stat -- <fil>`, som inte är det.

  **Talen ur den jämförelsen skrivs inte ut här.** De ändras av varje commit och
  av varje ny fällning, och de fyller ingen funktion i påståendet: det som bär
  det är att den ena diffen är tom och den andra inte. Ett utkast skrev ut dem
  och hade läst dem mot en filversion som inte längre fanns.

  **Ett utkast av den här posten skrev att kvittensen bär bevis "eftersom filen
  är spårad sedan `6f8bbfc`".** Det är fel skäl och fel slutsats: spårad eller
  ny spelar ingen roll, stagad eller inte gör det. Skriptet skriver sin egen
  varning om saken bara för OTRACKADE filer, så den uteblir i båda fallen.

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

## `fordonsfakta-ur-sida`

**BYGGD I SKIVA 19.** Spärren är prövad enligt §7.1 med `scripts/sparr-prova.sh`.
Den sitter i `src/biluppgifter.py` och vaktar steget FÖRE
`fordonsfakta-ur-uppslag`: att de tre fälten som `src/fordonsuppslag.py` utvärderar
verkligen är avlästa ur den efterfrågade fordonets sida, och inte ur någon annan
sida källan råkade svara med.

**Datakällan är den öppna fordonssidan, inte ett API.** Se `docs/beslutslogg.md`
#31, som också bär förbehållen. Att sidan är öppen HTML och inte ett kontrakterat
gränssnitt är själva skälet till att den här spärren behöver fyra lager: det finns
ingen leverantör som garanterar svarets form.

- **Spärr.** Beslutet ligger i **FYRA LAGER** i `src/biluppgifter.py`, och varje
  lager fäller ett eget fel:

  | Lager | Villkorets text | Vad det fäller |
  | --- | --- | --- |
  | 1 | `lasare.etiketter.count(etikett)`, alltså LIKHET mot etikettnodens text | Att en etikett läses som PREFIX till en annan |
  | 2 | `if forekomster > 1:` som kastar `Hamtningsfel` med texten `tvetydigt` | Att första träffen tas när samma etikett förekommer flera gånger |
  | 3 | `if not _galler_fordonet(sida, regnr):` plus `_galler_fordonet` själv, som prövar schema, värdnamn genom `_vard` och sökväg, och kastar på två ankare | Att en sida som inte gäller numret läses som fordonets |
  | 4 | `_tal` med `re.fullmatch` mot `kg`, dess kastgren `MISSLASNING`, `_ja_nej` med förvalet `None`, `_krav_pa_rimlighet`, och `if bar_element:` i `_las_falt` | Att ett värde som inte är rent tolkas som ett tal eller ett ja, att ett FELLÄST fält ser ut som ett saknat, att ett felläst tal passerar som en vikt, eller att MARKUP inuti värdet konkatenereras in i talet |

  **AVLÄSNINGEN ÄR EN PARSER SEDAN SKIVA 22**, se `docs/beslutslogg.md` #32. Lagren
  är desamma men vilar på `_Faltlasare` i stället för på tre regexuttryck. Tabellen
  bar tidigare `MONSTER`, `ETIKETTSPAN` och `CANONICAL`, alltså konstanter som inte
  finns längre.

  **Skälet till bytet är mätt.** Skiva 21 prövade tio sidändringar och fann FEM
  sändvägsdefekter, alla av samma klass: ett mönster som BESKRIVER sidans markup
  tystnar i stället för att kasta när markupen ser annorlunda ut. De elva
  mutationsfällningarna mot koden hittade ingen av dem, eftersom koden var
  självkonsistent i samtliga fall.

  **DEN SOM SKA FÄLLA SPÄRREN MÅSTE FÄLLA I ALLA FYRA.** Lager 3 har dessutom FYRA
  skilda beslut i sig, och en prövning som bara neutraliserar anropet når inget av
  dem: att saknad `canonical` ger `False`, att TVÅ ankare kastar, att schema och
  värdnamn prövas, och att jämförelsen är skiftlägesokänslig.

  **PARSERN BÄR FYRA EGNA VILLKOR SOM INTE SYNS I LAGERTABELLEN.** `HOPPAS_OVER`
  gör att innehåll i `template` och `noscript` aldrig blir data. Föräldervillkoret
  i `_stang_faltet` gör att en etikett bara paras med ett värde under SAMMA
  förälder, jämförd på identitet. `_behall` gör att en fotnotsMARKÖR inuti en
  etikettnod inte bidrar till dess text. `_varde_bar_markup` jämför VÄRDETS RÅA
  KÄLLTEXT med dess textnoder och kräver att stängningen är värdets egen. Alla
  fyra är fällbara var för sig och står i mutationstabellen nedan, som rad 14, 15,
  19, 21, 23, 24 och 25.

  *Här stod `_markera_markup`, som flaggade på en LISTA av nodtyper och bar lucka
  12 som undantag. Metoden finns inte längre; skiva 25 ersatte listan med
  egenskapen.*

  *Här stod TRE, skrivet innan skiva 24 lade till det fjärde. Fällt av
  granskningsvarv 2, som också fällde att uppslagningsmönstret för parsern inte
  nådde det nya villkoret.*

  **`script` och `style` står i `HOPPAS_OVER` men bärs inte av den**, utan av
  `HTMLParser`:s CDATA-läge. Modulens egen kommentar säger det, och fällning 14
  mäter det: de röda testen är `template`- och `noscript`-fallen, inget
  `script`- eller `style`-fall. Den som räknar de fyra som lager får ett falskt
  bevisvärde. *Här stod att `HOPPAS_OVER` gör att innehåll i alla fyra aldrig blir
  data. Samma fel som posten redan rättat en gång, se `src/biluppgifter.py`:s
  kommentar vid `HOPPAS_OVER`.*

  De två första infördes AV ombyggnaden i skiva 22: en parser som bara letar
  `nästa värdenod` är lösare än den regex den ersatte, och utan villkoret kan en
  etikett utan värde paras ihop med ett värde utan etikett längre ned i
  dokumentet. Det tredje kom i skiva 23 och stänger lucka 7.

  **`re.escape` ÄR BORTA UR MODULEN.** Den stod på raden med `MONSTER.format` och
  försvann med regexen. Här stod tidigare att den inte är ett av lagren eftersom
  den inte är fällbar, mätt till `GRÖN`, `119 passed` i skiva 21. Det påståendet
  gällde den koden och är inte längre ett påstående om något som finns.

  Radnumren står inte här, av skälet i rutan överst. Slå upp villkoren med ett
  sökmönster per lager, i `src/biluppgifter.py`:

  | Lager | `grep -n` |
  | --- | --- |
  | 1 | `'EXAKT_ETIKETT = \|etiketter.count'` |
  | 2 | `'forekomster > 1'` |
  | 3 | `'FORVANTA\|def _galler_fordonet\|len(ankare)\|_galler_fordonet(sida\|vard.startswith'` |
  | 4 | `'re\.fullmatch\|def _ja_nej\|def _krav_pa_rimlighet\|MIN_VIKT_KG\|if bar_element'` |
  | parsern | `'HOPPAS_OVER\|_vantar_foralder\|def _behall\|serie is None\|_varde_bar_markup\|egen_sluttagg\|class _Faltlasare'` |

  **Ett enda kombinerat mönster duger inte, och den här posten har själv burit TVÅ
  som inte gjorde det.** Det första missade det försiktiga förvalet vid saknad
  `canonical`, skiftlägesokänsligheten och `_ja_nej`:s `None`, och gav dessutom en
  träff i en kommentar. Det andra, som ersatte det för lager 1 och löd
  `'EXAKT_ETIKETT = \|re\.escape'`, **missade `MONSTER` självt**, alltså den enda
  rad som bär exaktheten, och gav i stället en träff i en docstring. Båda fälldes
  av §7-granskningen, det första i varv 1 och det andra i varv 2.

  Lager 3:s och 4:s förval ligger INNE i de funktioner mönstren pekar på och
  behöver läsas där, inte räknas ur träfflistan. **Räkna aldrig antalet träffar
  som ett mått på antalet villkor, och kontrollera alltid att mönstret träffar
  KODRADEN och inte en docstring som nämner den.**

  **LAGER 1 OCH 2 VAR DELVIS REDUNDANTA, OCH ÄR DET INTE LÄNGRE.** Redundansen
  kom av att lager 2 räknade träffar på lager 1:s EGET regexuttryck. Föll lager
  1:s stränghet bort träffade mönstret flera etiketter, och då tände lager 2 på
  lager 1:s fällning i stället för på sidans tvetydighet.

  Frikopplingen gjordes i skiva 21 genom att ge räknaren ett eget uttryck, och
  ombyggnaden i skiva 22 gjorde den strukturell: lager 1 är en LIKHETSJÄMFÖRELSE
  mot en nods text och lager 2 är en RÄKNING av samma noder. De har ingen delad
  formulering kvar som kan glida isär, och priset skiva 21 betalade i form av två
  uttryck att hålla i takt är därmed betalt tillbaka.

  Det stycke som stod här föreskrev att lagren alltid ska fällas tillsammans,
  eftersom en ensam fällning av lager 1 blev röd av fel skäl. **Den föreskriften
  gäller inte längre för det här paret.** Talen och verdikten står i
  mutationstabellen längre ned.

  §7.1:s regel om lagrat försvar gäller oförändrat för spärren i stort, och den
  behövdes i skiva 22: nivåvillkoret i parsern gav GRÖN vid en ensam fällning
  därför att föräldrastängningen bar samma spärr. Att ett lager är obundet och att
  ett lager är onödigt ser likadant ut i ett grönt verdikt, och skillnaden avgörs
  genom att fråga vad villkoret vaktar som det andra inte gör.

- **Vad den skyddar mot.** Att ett utgående mail bär en vikt eller ett
  dragkroksbesked som är läst ur något annat än det efterfrågade fordonets sida.
  Det konkreta utfallet: kunden får ett svar där släpvagnsvikten är en annan bils,
  eller den obromsade vikten presenterad som den bromsade. Båda talen står under
  etiketter som inleds likadant, och **det ena ligger under `src/fordonsuppslag.py`
  tröskel och det andra över**, så en defekt i lager 1 kan byta ärendets utfall
  tyst, utan att något syns i loggen. **Kan**, inte gör: när det sker beror på
  källans radordning, se stycket om riktningen nedan.

  **RIKTNINGEN ÄR UPPMÄTT, INTE HÄRLEDD, OCH DEN ÄR INTE DEFEKTENS EGENSKAP.** På
  den avlästa sidan ger en prefixmatchning två träffar, i ordningen 2 400 kg och
  därefter 750 kg. Första träffen blir alltså den BROMSADE, det vill säga den RÄTTA.
  **Prefixdefekten gör ingen skada på det avlästa fordonet: den ger rätt tal, av
  ren radordning.** Verifierat genom att fälla lager 1 till prefix och lager 2
  samtidigt, vilket i skiva 21 ger `17 failed, 102 passed` med
  `test_slapvagnsvikt_ar_den_bromsade` GRÖNT och värdet 2 400. Ommätt, och
  utfallet står kvar: det är `..._aven_i_omvand_radordning` som faller, inte det
  test som läser den avlästa sidans egen ordning. Talet stod förut på
  `3 failed, 43 passed`, mätt vid en baslinje som sedan rört sig två gånger.

  *Här stod tidigare att prefixmatchningen bara kan sätta in den OBROMSADE vikten.
  Det var fel, och det var en skärpning av ett tidigare fel: §7-granskningens varv 1
  underkände ett "eller omvänt" som icke-producerbart, och rättelsen bytte det mot
  ett "bara" som är icke-producerbart åt andra hållet. Varv 2 fällde det. Skriv
  aldrig riktningen som en egenskap hos defekten.*

  **Skälet till att spärren finns är därmed starkare än det felaktiga skälet var.**
  Utfallet får inte bero på i vilken ordning källan råkar skriva sina två rader.
  Byter källan ordningen blir första träffen den obromsade, och då kommer 750 in
  där 2 400 hörde. **Först då** tas ett uppfyllt viktkrav bort: 750 ligger under
  `TROSKEL_SLAPVAGNSVIKT_KG`, avläst till 1 000 i `src/fordonsuppslag.py`, medan
  2 400 ligger över. Ingenting skulle synas i loggen, eftersom båda talen är
  välformade vikter.

  **En kvalifikation hör till, och den håller.** Defekten kan bara nå ett fordon
  **där tjänstevikten inte redan räcker**, eftersom de två trösklarna prövas med
  ELLER: tjänstevikten testas först och returnerar direkt, så släpvagnsvikten
  läses aldrig på ett tungt fordon.

  Den skyddar också mot ett fel som statuskoden INTE fångar: källan svarar
  **HTTP 200 med sin söksida** på ett nummer som inte finns, inte 404. Ett
  statusberoende "finns fordonet" är alltså fel byggt mot den här källan. Avläst
  2026-09-02 på ett nummer utan fordon: HTTP 200, och noll förekomster av
  `class="label"` i svaret. Att det senare är noll är det som gör att en naiv
  parser tiger i stället för att ljuga, men det är inte något källan har lovat.
  `canonical`-ankaret i lager 3 är det som gör skillnaden till ett beslut.

- **Negativkontroll.** `tests/test_biluppgifter.py::test_alla_tre_falten_lases_ur_ett_avlast_svar`,
  `tests/test_biluppgifter.py::test_avlast_fordon_ger_oklart` och
  `tests/test_biluppgifter.py::test_normaliserat_nummer_slar_igenom_till_canonical`.
  Den första visar att alla tre fälten läses ur ett svar som är avläst ur den
  skarpa källan, den andra att resultatet går hela vägen genom
  `src/fordonsuppslag.py` till ett utfall, och den tredje att ett nummer som
  normaliserats till VERSALER accepteras mot en `canonical` skriven i GEMENER.
  Riktningen är inte godtycklig: `slag_upp` normaliserar bort blanksteg och
  bindestreck och versaliserar numret, medan källan själv skriver sin `canonical`
  med numret i GEMENER, avläst 2026-09-02. Jämförelsen måste alltså tåla båda
  hållen, och det är därför båda sidor av likheten bär `.upper()`. Numren står
  inte utskrivna här, av §6:s skäl.

- **Redundant med.** `fordonsfakta-ur-uppslag` i `src/fordonsuppslag.py`, men bara
  DELVIS och bara i en riktning. Den spärren prövar svarets FORM och värdenas
  giltighet efter att den här modulen lämnat ifrån sig en mappning. Den kan
  därför fånga att ett fält saknas eller är otolkbart, eftersom nyckeln då
  utelämnas här och `_kontrollera` fäller. **Den kan INTE fånga ett fält som är
  formellt giltigt men läst ur fel sida**, eftersom ett tal ur en annan bils sida
  är ett välformat tal. Lager 3 är alltså ensamt om sitt fall, och de två
  spärrarna får inte räknas som varandras ersättning.

### Prövningen, utförd i skiva 19

Elva fällningar med `scripts/sparr-prova.sh`, neutraliserade och aldrig raderade,
sedan `-- tests/test_biluppgifter.py -q`. Skriptet kvitterade sha256 identisk med
utgångsläget i varje körning.

**BASLINJEN ÄR 50 GRÖNA, OCH HELA TABELLEN ÄR KÖRD OM MOT DEN.** De tio första
fällningarna prövades vid 46 gröna. Sedan tillkom den elfte, `.strip()`-fällningen,
och med den fyra nya parametriserade testfall, så baslinjen blev 50. Tabellen
kördes då om i sin helhet: **samtliga verdikt och alla tal i kolumnen Röda test är
oförändrade.** Ett tal som mäts vid en baslinje slutar gälla när baslinjen rör sig,
och det enda som duger är att mäta om.

**FYRA AV FÄLLNINGARNA GICK INTE ATT REKONSTRUERA UR TABELLENS TIDIGARE
BESKRIVNINGAR**, och det upptäcktes just vid omkörningen. Lager 1:s prefixfällning
måste behålla `[^<]*</span>` för att mönstret alls ska matcha; tas `\s*</span>`
bort helt matchar det ingenting och fällningen ger 9 röda i stället för 5, alltså
RÖD av fel skäl. Lager 3:s skiftlägesfällning sitter i JÄMFÖRELSEN på
`slutet.upper() == regnr.upper()`, inte i `re.search`-flaggan; fälls flaggan i
stället blir sviten GRÖN, `50 passed`. Statusgrenens fällning måste ha samma
indentering som `raise`-raden, annars stannar körningen på insamlingsfel.
Beskrivningarna i tabellen är därför skrivna om till att bära det uttryck som
byts, så att var och en går att köra om utan att gissa.

**TABELLEN ÄR OMMÄTT I SKIVA 25 MOT BASLINJEN 214.** Postens egen regel gäller
den själv: *ett tal som mäts vid en baslinje slutar gälla när baslinjen rör sig,
och det enda som duger är att mäta om.* Baslinjen är `tests/test_biluppgifter.py`,
alltså modulens egen fil, och samma urval som varje tidigare omgång:
`-- tests/test_biluppgifter.py -q`. Hela sviten är ett annat tal och står i
skivans rapport.

*Här räknades tidigare upp vilka baslinjer talen stått vid, med `151` som skiva
22:s. Det talet går inte att belägga: `tests/test_biluppgifter.py` vid `8629223`,
alltså den commit som bär skiva 22:s arbete, samlar `175 passed`. Uppräkningen är
struken i stället för lagad, eftersom varje led i den mäter en filversion som
ingen längre kan köra. Att baslinjen rör sig står kvar, det är påståendet som
bär.*

**Rad 18 till 21 prövar villkor som kom i skiva 23, rad 22 ett som kom i skiva 24,
och rad 23 till 25 sådana som kom i skiva 25.** De fyra sista fäller lucka 11 och
12 på var sitt led: rad 22 tar bort KASTET i `_las_falt`, rad 23 tar bort kravet
att stängningen ska vara värdets egen, och rad 24 och 25 fäller jämförelsen mellan
råtext och textnoder åt var sitt håll.

*Här stod att rad 23 fäller FLAGGNINGEN i `_markera_markup`. Den metoden finns
inte längre: skiva 25 ersatte händelselistan med en egenskap, och radens plats
används nu till ett annat villkor.*

Rad 9 bytte FORMULERING i skiva 23 av skivans egen ändring: värdnamnet går
genom `_vard`. Rad 15 bytte också formulering, men av ett annat skäl: VILLKORET är
skiva 22:s och oförändrat, det var TABELLEN som bar ett namn, `_vantar_niva`, som
aldrig funnits i den committade koden. Skillnaden mellan de två fallen ska stå
utskriven, eftersom det ena är en ändring och det andra ett dokumentfel.

**Rad 22:s plats var ledig, och varför står under tabellen.**

| # | Fällning | Verdikt | Röda test |
| --- | --- | --- | --- |
| 1 | Lager 1, likheten görs till prefix: `if namn == etikett` blir `if namn.startswith(etikett)` | RÖD | 8 |
| 2 | Lager 2, `if forekomster > 1:` blir `if False:` | RÖD | 25 |
| 3 | **Lager 1 och 2 samtidigt** | **RÖD** | **33** |
| 4 | Lager 3, `if not _galler_fordonet(...)` blir `if False:` | RÖD | 9 |
| 5 | Lager 3, saknat ankare godtas: `return False` blir `return True` | RÖD | 6 |
| 6 | Lager 3, skiftläget i JÄMFÖRELSEN: `vag.upper() == f"...".upper()` blir jämförelse utan `upper()` | RÖD | 138 |
| 7 | Lager 3, två ankare godtas: `if len(ankare) > 1:` blir `if False:` | RÖD | 2 |
| 8 | Lager 3, schemat prövas inte: `if delar.scheme.lower() != FORVANTAT_SCHEMA:` blir `if False:` | RÖD | 1 |
| 9 | Lager 3, värdnamnet prövas inte: `if _vard(delar.netloc) != FORVANTAD_VARD:` blir `if False:` | RÖD | 3 |
| 10 | Lager 4, `_tal` `fullmatch` blir `search` | RÖD | 12 |
| 11 | Lager 4, `_ja_nej` förval `None` blir `False` | RÖD | 10 |
| 12 | Lager 4, `.strip()` före matchningen borttagen | RÖD | 3 |
| 13 | Lager 4, rimligheten godtas alltid: `if MIN_VIKT_KG <= varde <= MAX_VIKT_KG:` blir `if True:` | RÖD | 6 |
| 14 | Parsern, `if tagg in HOPPAS_OVER:` blir `if False:` | RÖD | 8 |
| 15 | Parsern, föräldervillkoret stryks ur `if self._vantar is not None and foralder == self._vantar_foralder:` | RÖD | 7 |
| 16 | Statusgrenen kastar inte: `raise Hamtningsfel(...)` blir `return None` | RÖD | 6 |
| 17 | 404-grenen neutraliserad: `if status == 404:` blir `if False:` | RÖD | 1 |
| 18 | Lager 4, kastgrenen: `if MISSLASNING.fullmatch(rensat):` blir `if False:` | RÖD | 6 |
| 19 | Parsern, INGEN fotnot utesluts: `_behall`:s `if serie is None:` blir `if True:` | RÖD | 9 |
| 20 | Lager 3, `www` strippas inte: `return vard[4:] if vard.startswith("www.") else vard` blir `return vard` | RÖD | 2 |
| 21 | Parsern, VARJE fotnot utesluts: `_behall`:s `return text if any(tecken.isalpha() …) else ""` blir `return ""` | RÖD | 4 |
| 22 | Lager 4, lucka 11 och 12:s spärr: `if bar_element:` i `_las_falt` blir `if False:` | RÖD | 17 |
| 23 | **NY i skiva 25.** Egenskapen, utsträckningen: `if not egen_sluttagg:` i `_varde_bar_markup` blir `if False:` | RÖD | 2 |
| 24 | **NY i skiva 25.** Egenskapen godtar ALLT: jämförelsen `unescape(...) != samlad` blir `return False` | RÖD | 15 |
| 25 | **NY i skiva 25.** Egenskapen godtar INGET: samma jämförelse blir `==` i stället för `!=` | RÖD | 115 |

**LAGER 1 OCH 2 ÄR INTE REDUNDANTA, och rad 3 visar det.** 8 + 25 är 33, alltså
exakt additivt: dubbelfällningen fäller precis unionen och inget maskeras. Förr
var summan SUB-additiv, tre mot fem, därför att lager 2 räknade träffar på lager
1:s eget regexuttryck och därmed tände när lager 1:s exakthet föll.

**RAD 18 OCH 13 ÄR INTE VARANDRAS ERSÄTTNING, och skillnaden är hela DEL A.**
Kastgrenen i rad 18 fäller ett värde som inte går att läsa som ett tal.
Rimligheten i rad 13 fäller ett tal som ÄR läst men är omöjligt. Ett värde som
`750 400 kg` går genom den första och fastnar i den andra, vilket är lucka 9
nedan. De två har alltså ett överlapp, men varje lager fäller fall det andra inte
når, och båda är röda var för sig.

**RAD 24 OCH 25 FÄLLER SAMMA JÄMFÖRELSE ÅT VARSITT HÅLL.** Rad 24 låter
egenskapen godta allt, alltså läget före skiva 24, och de femton röda är
kastfallen. Rad 25 låter den godta ingenting, och de 115 röda visar att spärren
då blir ett larm som alltid går: varje verkligt svar faller. Ett villkor med ett
riktigt intervall behöver en fällning i vardera riktningen. *Här stod att
`test_entitet_i_ett_varde_ar_inte_markup` är det test som skiljer de två. Det är
ett av 115, och `unescape`-ledet binds av en annan fällning; se stycket om
entiteter i 0.24.0-posten. Fällt av granskningsvarv 2.*

**SKIVA 24:S RAD 22 ERSATTE EN RAD SOM BLEV OFÄLLBAR, och det ska stå utskrivet.**
Skiva 23:s rad 22 fällde värdevägen i `_stang_faltet`, alltså värdets
textbygge bytt mot `text = self._etikettext()`. Efter att lucka 11:s
spärr kom in ger den fällningen **GRÖN, 214 passed**. I DUBBELFÄLLNING tillsammans
med rad 22 ger den `17 failed`, vilket är exakt rad 22:s egna röda: värdevägen
bidrar alltså med noll också då. Skälet är att ett värde som bär markup numera
kastar innan dess text spelar roll, och ett värde UTAN markup ger identisk text i
båda vägarna.

**Villkoret är alltså inte struket ur koden, men det är inte längre ett lager.**
Det står kvar därför att en framtida uppmjukning av lucka 11:s spärr annars
tyst hade gett värden etikettens fotnotsregel, alltså ett tal med tecken
borttagna. §7.1 kräver att ett obundet villkor namnges, och det är vad den här
noten gör: raden är prövad, GRÖN ensam och utan bidrag i dubbelfällning, och
behållen med skäl.

**RAD 19 OCH 21 FÄLLER SAMMA FUNKTION ÅT VARSITT HÅLL, och det är avsiktligt.**
Rad 19 låter ingen fotnot uteslutas, alltså läget före DEL B: en fotnotad etikett
blir en annan sträng och dubbletten upptäcks inte. Rad 21 utesluter varje
fotnotselement oavsett innehåll, alltså DEL B:s FÖRSTA lydelse, som granskningen
av skiva 23 mätte upp som två sändvägsdefekter. Ett villkor med ett riktigt
intervall behöver en fällning i vardera riktningen; en ensam fällning hade lämnat
halva villkoret obundet.

**FÄLLNING 11 MÅSTE KÖRAS MOT RÄTT RAD, OCH DET ÄR INTE EN SJÄLVKLARHET.**
`_ja_nej`:s förval är den AVSLUTANDE `return None`, inte den `return False` som
står raden ovanför; fälls den senare byter indenteringen nivå och sviten stannar
på insamlingsfel, alltså `FEL` och inte ett verdikt. Uppmätt i skiva 22. Se
`docs/incidentlogg.md` I8 om varför en fällning mot fel rad är farligare än den
ser ut.

**FÄLLNING 15 ÄR ETT LAGRAT FÖRSVAR SOM FÖRST GAV FALSKT GRÖNT.** Nivåvillkoret
fälldes ensamt och sviten förblev grön, eftersom föräldrastängningen längre ned i
`handle_endtag` bar samma spärr för det test som fanns. Villkoret vaktar ändå
något det andra inte gör, nämligen en etikett och ett värde på olika nivåer under
en förälder som aldrig stänger emellan. Det är därför inte struket utan BUNDET,
av `test_varde_pa_annan_niva_paras_inte_med_etiketten`, och raden är röd sedan
dess. §7.1:s val står kvar: döp om testet till vad det bevisar, eller gör det
äkta. Här gjordes det äkta.

Lager 2 räknar sedan skiva 22 etikettNODER, medan lager 1 är en likhet mot
samma noders text. En prefixfällning i lager 1 rör alltså inte räkningen.
**Fälls lager 1 ensamt är samtliga röda rena assertfel, inte `tvetydigt`.**
Uppmätt i skiva 21 mot den dåvarande koden, genom att köra fällningen med
`--tb=line` och LÄSA utdatan: den bar `assert 750 == 2400`,
`assert 'slapvagnsvikt_kg' not in {...}` och tre av formen
`AssertionError: sidändringen gav ett uppslag i stället för att falla`, och
inget `Hamtningsfel ... tvetydigt`.

*Belägget stod först som en rörledning till `grep -c`, vilket §9 förbjuder för
verifiering. Att slutsatsen råkade vara riktig gör inte metoden tillåten, och en
förbjuden metod ska inte stå som förebild i ett styrdokument. Utbytt mot en
avläsning av utdatan.*

Följden för lagerbeskrivningen längre upp i posten står där, under
`LAGER 1 OCH 2 VAR DELVIS REDUNDANTA`, och upprepas inte här.

**TABELLEN ÄR SJÄLVMÄTT I SKIVA 24 tills en granskare kört om den.** Skiva 23:s
granskningsvarv 2 reproducerade den oberoende vid baslinjen 196. Skiva 24 flyttade
baslinjen till 210, bytte ut rad 22 och lade till rad 23, så den körningen säger
ingenting om talen som står nu. Det som överlever är metoden, inte ett mätvärde.

*Här stod "granskningsvarv 2 och 3" om reproduktionen vid 196. Ledet om varv 3
lades till av skiva 24 och går inte att belägga: granskningsrapporterna ligger i
gitignorerad `scratchpad/`, så repot bär inget om vilka rader ett givet varv körde.
Påståendet är smalnat till det som stod i dokumentet före skivan. Fällt av
granskningen av skiva 24.*

Nedströmsraden i `src/fordonsuppslag.py` gav `52 failed, 162 passed` vid
baslinjen 214.

Ordvalet är avsiktligt: `oberoende` är i det här repot §7:s term, satt i motsats
till `självmätt`. Det gäller granskarens körning. Skiva 20:s egen var bara ett
annat pass.

**De fyra som tidigare inte gick att rekonstruera går det nu.** Beskrivningarna
bär det uttryck som byts, och `NEUTRALISERAD`-raden visade i varje fällning ett
ursprungsvärde som var det avsedda villkoret, aldrig en tom sträng. Grep-tabellen
per lager slår upp rätt rader. Också det kontraintuitiva ledet reproducerade:
dubbelfällningen av lager 1 och 2 gav färre röda än lager 1 ensamt.

*Ledet om att raden `aldrig` visade en tom sträng gällde skiva 20:s elva
fällningar och är inte en garanti. En tom sträng är precis vad raden visar när
radnumret är fel, uppmätt i skiva 22, se `docs/incidentlogg.md` I8.*

**Det ledet gäller inte längre.** Frikopplingen i skiva 21 gjorde summan additiv,
och det som var postens mest kontraintuitiva iakttagelse är nu bara aritmetik.
Meningen står kvar i imperfekt därför att den beskriver vad skiva 20 mätte, inte
vad koden gör i dag.

**EN REPRODUKTIONSDETALJ SOM INTE LÄNGRE UTLÖSES AV TABELLENS EGNA RADER.**
Den gällde skiva 20:s fällning 7 och 9, som båda bytte ut en rad där `_tal`:s
anrop och dess mönster stod tillsammans. Mönstrets teckenklass bär en escape för
hårt blanksteg, skriven med omvänt snedstreck följt av `u00a0`, och **den escapen
når inte oförändrad fram till `--ersatt`**: den blir ett blankstegstecken i den
ersatta raden, alltså osynligt i stället för utskrivet.

Anropet är sedan skiva 21 brutet över flera rader, så tabellens motsvarande
fällningar, 10 och 12, byter ut `traff = re.fullmatch(` respektive
`varde.strip(),`. Ingen av dem rör mönsterraden, och problemet uppstår därför
inte. **Detaljen står kvar därför att den gäller varje fällning som någon gång
riktas mot mönsterraden**, och den som gör det ska veta vad `NEUTRALISERAD`-raden
kommer att visa.

**ORSAKEN ÄR INTE SKALET, och den första lydelsen här påstod det.** Uppmätt av
granskningen: `\d`, `\s` och dubblerade snedstreck i samma argument når fram
intakta. Omvandlingen sitter alltså före skalet, i lagret som skriver
verktygsanropet, och inte i skalet.

**UTFALLET ÄR INTE HELLER INVARIANT.** I ett försök blev det det hårda
blanksteget, U+00A0, och i ett annat ett vanligt blanksteg, U+0020. Inuti
teckenklassen är alla tre semantiskt likvärdiga för den här fällningen, och
verdikt och antal röda test blev oförändrade i båda fallen. Men den som följer
tabellen ordagrant kan se ett tredje tecken i `NEUTRALISERAD`-raden än de två som
nämns här, och ska veta att det är väntat och inte en missad fällning.

**Escapen skrivs därför ut i ord här och inte som tecken.** Risken går åt det
motsatta hållet mot vad den första lydelsen sade: ett dokument som bär tecknet
går inte att skilja från ett som bär ett vanligt blanksteg, och läsaren kan inte
se vilket som avsågs. Att skriva escapen som synliga tecken är den lätta
riktningen. Sådana osynliga tecken skrevs in i den här posten när den först
formulerades och är borttagna.

**TRE FÄLLOR I VERKTYGSKEDJAN VAR SANDBOXENS, INTE REPOTS.** Överlämningen till
skiva 20 varnade för dem, och de gäller inte här. Avläst på Lars maskin
2026-09-02, alltså en avläsning och inget påstående om varje maskin:

- **`scripts/sparr-prova.sh` fungerar.** Varningen gällde att skriptet använder
  BSD:s `mktemp -t` och faller i en Linux-sandbox, som därför behövde en egen
  kopia. På darwin är den formen inhemsk, och samtliga elva fällningar kördes med
  repots eget skript.
- **DEN HÄR SPÄRRENS tester är självbärande.** Varningen namngav HTML-fixturer
  utanför repot. `tests/test_biluppgifter.py` kördes utan dem, med 50 gröna som
  baslinje. Påståendet gäller den filen och inte sviten som helhet; nästa punkt
  handlar om det.
- **Sviten är hel.** Varningen sade att ett test i
  `tests/test_kategorier_yaml.py` är rött därför att det kräver den gitignorerade
  `data/taxonomi.json`. På den här maskinen finns filen, och hela sviten är hel.
  Talet stod som `488 gröna`, mätt i skiva 20. **Skiva 21 lade till test och
  gjorde det föråldrat**; avläst i skiva 21 ger `.venv/bin/python -m pytest -q`
  i stället `557 passed`. Påståendet som bär noteringen är att sviten är HEL,
  och det håller vid båda talen.

**Skälet att skriva ut det:** utan den här noteringen drar nästa läsare slutsatsen
att sviten är beroende av filer utanför repot. Det är den inte. Den är beroende av
`data/`, som är gitignorerad, och det är en annan sak än en fixtur i en
temporärkatalog.

**Skälen att katalogen är ocommittad ska inte slås ihop.** `data/tradar.jsonl` och
`data/par.jsonl` bär kundtext, och §6 hindrar att de committas.
`data/taxonomi.json`, som är den enda fil det röda testet handlar om, bär 28
kategorinamn och ingen kundtext; den är ocommittad enbart av katalogregeln i
`.gitignore`. Samma skillnad står i `docs/beslutslogg.md` #30.

**ETT TEST VAR VAKUÖST OCH RÄTTADES.** Fällningen av lager 1 och 2 samtidigt lät
först `test_slapvagnsvikt_ar_den_bromsade` stå GRÖNT — just det test som skrevs
för prefixfällan. Skälet: med prefixmatchning ger `re.findall` två träffar, och
den första råkade bli den rätta eftersom den bromsade raden står först i källans
HTML. **Testet vaktade dokumentordningen och inte spärren.** Åtgärdat med
`test_slapvagnsvikt_ar_den_bromsade_aven_i_omvand_radordning`, som lägger den
obromsade raden först. Först därefter fäller dubbelfällningen mer än lager 1
ensamt. Talet stod som `tre test`, mätt vid baslinjen 50; i skiva 22 är det 24
mot lager 1:s 6, se mutationstabellen.

**EN FÄLLNING PÅ EN TOM RAD GER FALSKT GRÖNT, och det hände i den här prövningen.**
Lager 3:s förval prövades först på ett radnummer som pekade en rad FEL, på den tomma
raden efter `return False`. Fällningen blev då död kod efter en `return`, alltså en
no-op, och skriptet svarade GRÖN. Verdiktet var korrekt för det som faktiskt gjordes
och helt fel om lagret. **Skriptet skrev ut felet i klartext**, som
`NEUTRALISERAD rad N: '' -> ...`, med en tom sträng som ursprungsvärde. Den som
prövar ska läsa `NEUTRALISERAD`-raden och kontrollera att ursprungsvärdet är det
villkor som skulle fällas, aldrig bara verdiktet. Detta är samma feltyp som rutan
överst varnar för, med den skillnaden att radnumret var felräknat och inte
föråldrat. Effekten är identisk.

### Sidändringsprövningen, utförd i skiva 21 och byggd om i skiva 22

**MUTATIONERNA PRÖVAR KODEN, INTE KÄLLAN.** Fällningarna ovan visar att
lagren biter när koden ändras. De säger ingenting om vad som händer när SIDAN
ändras, och det är det som faktiskt kommer att inträffa: biluppgifter.se ändrar
sin markup utan att fråga oss.

Skiva 21 konstruerade ändrade sidor ur samma fixtur och prövade tio fall.
**Kravet är ensidigt: ett fall får aldrig returnera ett värde som ser giltigt ut.**

| Fall | Utfall | Skäl eller undantag |
| --- | --- | --- |
| 1 `Släpvagnsvikt` omdöpt | utkast | `svaret saknar slapvagnsvikt_kg` |
| 2 `Draganordning` omdöpt | utkast | `svaret saknar draganordning` |
| 3 `Tjänstevikt` omdöpt | utkast | `svaret saknar tjanstevikt_kg` |
| 4 värdet i okänt format | utkast | `svaret saknar slapvagnsvikt_kg` |
| 5 fältet borttaget | utkast | fältets eget skäl |
| 6 två träffar på etiketten | **`Hamtningsfel`** | `... förekommer 2 gånger, tvetydigt` |
| 7 ankaret pekar på annat fordon | utkast | `hämtningen gav inget svar` |
| 8 ankaret saknas | utkast | `hämtningen gav inget svar` |
| 9 felsida med status 200 | utkast | `hämtningen gav inget svar` eller saknat fält |
| 10 tom eller trunkerad sida | utkast | `hämtningen gav inget svar` eller saknat fält |

Fall 6 skiljer ut sig genom att kasta i stället för att falla till utkast, och
det är avsiktligt: `slag_upp` fångar inte hämtningens egna undantag. Kravet
gäller ändå, eftersom inget värde kommer ut. Att undantaget sedan LEDER till
utkast är en skyldighet på fas 5:s anropare och inte något den här modulen kan
garantera; ingen kod konsumerar det ännu.

**FALL 4 HAR SEDAN SKIVA 23 TVÅ UTFALL, och raden ovan bär det ena.** Ett värde i
ett okänt FORMAT, alltså `1200` utan enhet, `1,2 ton` eller `ca 1200 kg`, ger
fortfarande utkast: vi kunde inte tolka fältet. Ett värde som bär siffror och
enheten `kg` men inte går att läsa som ett tal, alltså `750 2400 kg`, KASTAR i
stället, eftersom fältet fanns och lästes fel. Skillnaden är DEL A i skiva 23 och
står under `_tal`.

**TABELLEN OVAN GÄLLER EFTER TVÅ RÄTTELSER, OCH SÅ SÅG DEN INTE UT FÖRST.**
Skivans första lydelse skrev "INGET AV DE TIO RETURNERAR ETT VÄRDE". Den var
falsk. §7-granskningen hittade **två sändvägsdefekter inom kategorierna 4 och
6**, båda i den farliga riktningen, alltså ett tal under tröskeln 1 000 där det
rätta ligger över:

1. **Fall 6, dubbletten som inte kastade.** Lager 2 räknade träffar på
   `MONSTER`, vars värdegrupp `([^<]*)` inte matchar ett värde med nästlad
   markup. Låg etiketten två gånger och ETT värde var nästlat gav mönstret EN
   träff, tvetydigheten tände aldrig, och modulen svarade **750 kg** som om det
   vore entydigt. **Premissen finns på den skarpa sidan**: fixturkommentaren
   mäter 62 label-span mot 54 par, och ett av glappen är avläst: `Chassinr /
   VIN`, vars value-span öppnar ett element. Att hela glappet har den orsaken
   är en subtraktion, inte en avläsning.
   Rättat i två steg: skiva 21 lät lager 2 räkna ett eget uttryck för
   ETIKETTEN, och skiva 22 ersatte hela avläsningen med en parser som
   räknar etiketten som en NOD. Det första steget räckte inte, se nedan.
2. **Fall 4, värdet med två tal.** `_tal`:s mönster tillät blanktecken var som
   helst i siffergruppen medan `re.sub` klistrade ihop det som blev kvar.
   `750 2400 kg` gav **7502400**, ett välformat heltal långt över tröskeln.
   Rättat: avskiljare godtas bara som tusenavskiljare och måste vara
   KONSEKVENTA vid varje gräns. Den andra halvan behövdes: ett mönster med
   valfri avskiljare läste `2400 750 kg` som 2 400 750.

Båda är bundna av test som blir röda när rättelsen fälls.
**Den rättade tabellen är alltså inte en självmätning av att allt var bra från
början**, utan resultatet efter att fel hittats och stängts.

**GRANSKNINGEN FANN TRE FEL TILL, OCH DE TVÅ SISTA ÄR SKÄLET TILL SKIVA 22.**
Varv 2 fällde att rättelsen av fall 6 inte räckte: räknarens egna uttryck var
lika strängt som läsarens, så en dubblett där ena etiketten bar ett ATTRIBUT
släppte fortfarande ut ett värde. Varv 3 fällde två till, båda av samma klass:

3. **Fall 6 igen.** Räknaren var lös i taggen men lika sträng i KLASSVÄRDET och
   i etikettens INNEHÅLL. Bar ena förekomsten `class="label bold"`, nästlad
   markup runt namnet, eller ett annat element än `span`, såg varken räknaren
   eller läsaren den, och det andra parets **750 kg** gick ut. Samma sak på
   `Draganordning` löste ett Ja mot ett Nej tyst.
4. **Fall 5.** Ett fält som låg kvar i `<!-- -->` eller i `<template>` lästes
   som om det vore aktivt, alltså var fältet borttaget i briefens mening men
   modulen svarade ändå.

**MÖNSTRET ÄR HELA POÄNGEN.** Fem defekter, fem gånger samma orsak: ett uttryck
som BESKRIVER sidans markup tystnar i stället för att kasta när markupen ser
annorlunda ut. Varje rättelse som stannade i regexens värld födde nästa fel.
Lars beslut i #32 är därför att byta metod och inte mönster: **sidan parsas**,
etiketter räknas som noder, och kommentarer och `template` är inte data. De två
sista defekterna upphör av konstruktionen, se `_Faltlasare`.

En sak till, som gäller varje mätning i det här avsnittet: **de elva
mutationsfällningarna mot koden hittade ingen av de fem.** Koden var
självkonsistent i samtliga fall, och det är precis vad prövningen av KÄLLAN
finns för att fånga.

**FALL 4 DELADES I TVÅ HALVOR, OCH DET ÄR EN INSKRÄNKNING AV BRIEFEN.** Briefen
säger "För VART OCH ETT: uppslaget ska MISSLYCKAS". `1 200 kg` är sidans egen
form, och en modul som föll på den hade inte kunnat slå upp något alls, så
kravet lästes som att det gäller de format källan INTE använder: `1200` utan
enhet, `1,2 ton`, `1200 lbs`, `ca 1200 kg`, `1200 kg (Teoretisk)` och
`-1200 kg`. `1200` är det farligaste, eftersom talet är rätt och bara enheten
saknas.

**LARS HAR SVARAT, OCH LÄSNINGEN STÅR.** Beskedet i skiva 22 är att
`1 200 kg` med hårt blanksteg SKA läsas, eftersom det är källans eget format,
och att kravet gäller att `750 2400 kg` aldrig blir 7502400. Uppdelningen var
skivans egen tolkning när den skrevs och är sedan #32 ett beslut. *Här stod att
frågan är ställd och obesvarad; det gällde när det skrevs.*

**SKIVA 23 SKÄRPER ANDRA HALVAN FRÅN UTELÄMNAT TILL KASTAT.** Att `750 2400 kg`
inte blir 7502400 räckte inte: fältet utelämnades, och ett utelämnat fält betyder
VI VET INTE. Här vet vi något annat, nämligen att fältet fanns och lästes fel.
Lars beslut är att `_tal` KASTAR i det läget, se `MISSLASNING` och
mutationsfällning 18. Fall 4:s första halva är oförändrad: källans eget format
läses, med båda sorternas blanksteg.

**Vilken form källan faktiskt använder är inte belagt i repot.** `_tal`:s
docstring säger att tusenavskiljaren är blanksteg eller hårt blanksteg, medan
fixturen `SIDA_AVLAST`, vars åtta värden är avlästa, skriver `2140 kg` och
`2400 kg` UTAN avskiljare. Alla tal i den är fyrsiffriga eller mindre, så de två
källorna motsäger inte varandra, men ingen av dem visar en avskiljare i bruk.
Mönstret tål båda formerna, och det är det som gör frågan ofarlig i dag.

**MARKUPÄNDRINGAR UTANFÖR LISTAN PRÖVADES OCKSÅ**, alla rimliga i en omdesign
och ingen av dem i briefen: ett attribut på etikettspannen, ett bytt klassnamn,
ett extra ord i klassen, nästlad markup i värdet, värdet helt inuti ett element,
något inskjutet mellan etikett och värde, och sedan skiva 22 också etiketten i
ett annat element än `span`.

**HÄR STOD ATT ALLA SEX FALLER TILL UTKAST, OCH DET ÄR INTE LÄNGRE SANT.** Efter
ombyggnaden i skiva 22 LÄSTES sex av de sju. Bara det bytta klassnamnet föll, och
det ska det: klassen är hur parsern vet att noden är en etikett.

**Ändringen ser ut som en uppmjukning och är motsatsen.** Att utelämna fältet på
en kosmetisk markupändring är inte försiktighet, det är en spärr som fäller på
det ofarliga och därför blir avstängd vid nästa omdesign hos källan. Och det var
SAMMA okänslighet för markup som gjorde att en dubblerad etikett inte upptäcktes,
alltså defekt 1 och 3 ovan.

**SKIVA 24 TOG TILLBAKA UPPMJUKNINGEN FÖR DE TVÅ FALL SOM RÖR VÄRDET.** `nästlad
markup i värdet` och `värdet helt inuti ett element` KASTAR nu, se lucka 11.
Skälet är att just den okänsligheten hade en andra följd som ingen såg när den
infördes: samma konkatenering som gjorde `2400 <abbr>kg</abbr>` läsbar gjorde
`750<sup>1</sup> kg` till 7501.

**Uppmjukningen står kvar där den är ofarlig.** Ett attribut, ett extra klassord,
något inskjutet mellan etikett och värde, eller ett annat elementnamn kan inte
ändra ett TAL. Ett element inuti värdet kan.

`test_markupandring_lases_av_parsern` bär de fyra som fortfarande läses,
`test_markupandring_utan_etikettklassen_faller` det som faller till utkast, och
`test_varde_med_element_kastar` de två som numera kastar.

**TESTERNA LIGGER I REPOT, INTE I `/tmp`.** Sidorna byggs ur `sida()` och
`rad()` i `tests/test_biluppgifter.py`, alltså ur samma fixtur som resten av
filen. Skiva 19:s överlämning bar fixturer i `/tmp`, och en fixtur utanför repot
gör testet obeständigt.

**Nollfallet bär avsnittet.** `test_baslinjen_ger_ett_uppslag` prövar att den
oförändrade sidan fortfarande GER ett uppslag. Utan den vore varje test ovan
värdelöst: slutade fixturen bygga en läsbar sida hade allt fallit till utkast av
fel skäl, och samtliga test blivit gröna utan att pröva något.

**§7.1-PRÖVNINGEN AV DE HÄR TESTEN LIGGER I MUTATIONSTABELLEN OVAN.** Här stod
tidigare en egen tabell med nio rader. Den dubblerade mutationstabellen i sju av
dem, och de återstående två fällde uttryck som ombyggnaden i skiva 22 tog bort:
`MONSTER`, `ETIKETTSPAN` och de rättelser som gjordes inuti dem.

Mutationstabellens tjugofem rader är körda mot baslinjen 214 och täcker samtliga
fyra lager plus parserns egna villkor. Att hålla två tabeller som mäter samma
fällningar mot samma baslinje är inte dubbel säkerhet: det är två tal att hålla i
takt, och postens historik visar vad som händer när de glider isär.

**EN FÄLLNING LIGGER I EN ANNAN MODUL OCH HÖR HIT ÄNDÅ.** Briefens fall 1, 2, 3
och 5 faller inte på något i `src/biluppgifter.py`, utan på att nyckeln utelämnas
och att spärren nedströms fäller. Testen asserar därför på SKÄLET och inte bara
på att något kastades, och skälet produceras av `_kontrollera`:

| Fälld rad, citerad | Fällning | Utdata | Verdikt |
| --- | --- | --- | --- |
| `_kontrollera`:s TRE grenar i `src/fordonsuppslag.py`, `if not _bar_nyckel(svar, ...)` | `if False:` × 3 | `52 failed, 162 passed` | RÖD |

Utan den fällningen vore det oprövat om testen mäter avläsningen eller bara att
`slag_upp` kastar något över huvud taget.

**RADNUMREN I `src/fordonsuppslag.py` HAR RÖRT SIG MINST TVÅ GÅNGER.** Skiva 21
körde fällningen mot numren från skiva 19 och fick `pytest exit 2`, alltså `FEL`
och inte `GRÖN`. Det är skriptets avsedda beteende, och skälet till att felet
syntes i stället för att passera som ett verdikt: **en fällning som inte går att
köra får aldrig läsas som att spärren höll.** Numren ovan är avlästa i skiva 22
omedelbart före körningen, och ska läsas om före nästa. Se
`docs/incidentlogg.md` I8.

**ALLA TRE GRENARNA FÄLLS, INTE BARA EN.** Skivans första prövning fällde bara
`slapvagnsvikt_kg`-grenen, och lämnade därmed de test som rör tjänstevikt och
draganordning OPRÖVADE: de var gröna i den körningen. §7.1:s klausul om lagrat
försvar gäller här i sin egen form, eftersom de tre grenarna är oberoende och
varje test bara binder sin egen.

**Hjälparen `utfallet_av` är själv en spärr.** Den kastar `AssertionError` om
ett uppslag kommer ut i stället för ett skäl, så ett fall som en dag börjar
svara med fakta blir rött i stället för tyst grönt. Att den biter är prövat: med
lager 3 fällt är det just den assertionen som fäller
`test_canonical_for_annat_fordon_faller_till_utkast`.

### Kända luckor

1. **Källan filtrerar på klient och kan börja neka.** Att svaret alls går att hämta
   beror på ett `User-Agent`-huvud. Det är inte ett kontrakt, och en skärpning hos
   källan gör hämtningen till ett `Hamtningsfel` utan förvarning. Det är hanterat
   som ett fall, ärendet faller till utkast, men det är inte hanterat som en risk.
2. **Etiketternas stavning är avläst en dag, inte garanterad.** Byter källan
   `Släpvagnsvikt` mot något annat utelämnas nyckeln, `fordonsfakta-ur-uppslag`
   fäller, och varje ärende faller till utkast. Det är rätt utfall, men felet syns
   först som en tystnad i flödet och inte som ett larm.
3. **Ägaruppgifter ligger bakom inloggning hos källan och hämtas inte.** Det är
   #23:s aktiva val och gäller så länge modulen bara begär den öppna sidan. Skulle
   någon lägga till en inloggning finns ingen spärr som hindrar det.
4. **Spärren gäller svaret, inte anroparens fantasi.** `Uppslag` går att
   konstruera förbi den här modulen helt, precis som lucka 2 under
   `fordonsfakta-ur-uppslag` beskriver.
5. **EN SEMANTISK OMDÖPNING UPPTÄCKS INTE AV NÅGON BYGGD KONTROLL, och den ger
   ett värde.**
   Uppmätt i skiva 21. Lucka 2 ovan gäller när en etikett byter NAMN. Det
   omvända fallet är farligare: källan behåller namnet `Släpvagnsvikt` men låter
   det beteckna ett annat tal. Konkret, och prövat: tas den bromsade raden bort
   och den obromsade döps om till `Släpvagnsvikt`, så bär sidan exakt EN rad med
   den etiketten och ett välformat värde. **Samtliga fyra lager passerar och
   modulen svarar 750 kg**, alltså den obromsade vikten presenterad som den
   bromsade.

   Talet ligger UNDER tröskeln 1 000 medan det rätta ligger över, så felet kan
   byta ärendets utfall och gör det tyst. Det är samma riktning som prefixfällan
   i lager 1, men utan att någon kod är fel: modulens kontrakt är att läsa fältet
   med ett givet namn, och källan har ändrat vad namnet betyder.

   **Ingen kontroll är byggd, och det är inte ett förbiseende.** En rimlig sådan
   vore att kräva att `Släpvagnsvikt obromsad` också finns och är mindre. **Den
   skulle upptäcka fallet**, så luckan är inte oupptäckbar utan obevakad; här
   stod först att den inte GÅR att upptäcka, vilket motsades av den här
   meningen. Kontrollen kopplar dock spärren till ett fjärde fält och faller
   själv om källan tar bort det. Avvägningen är Lars, inte kodens.

   **LARS HAR SVARAT I SKIVA 23, OCH SVARET ÄR ATT LUCKAN LÄMNAS ÖPPEN.**
   Kontrollen kräver ett fjärde fält och är inte värd komplexiteten nu. Det som
   ändras här är alltså inte koden utan att luckan är VÄGD: nästa läsare ska se
   ett avslag med skäl och inte ett förbiseende. *Här stod att frågan är ställd
   och obesvarad; det gällde när det skrevs.*

   **VÄRDET KOMMER BARA UT NÄR BÅDA RADERNA ÄNDRAS.** Står den bromsade raden
   kvar bär sidan `Släpvagnsvikt` två gånger, och lager 2 kastar. Luckan kräver
   alltså att källan BÅDE tar bort den bromsade raden OCH döper om den
   obromsade, vilket är briefens fall 5 och fall 1 i kombination.

   **RIMLIGHETSKONTROLLEN I SKIVA 22 STÄNGER INTE DEN HÄR LUCKAN.** Lars brief
   namnger `_krav_pa_rimlighet` som lucka 5:s motmedel, och det ska sägas rakt
   ut att den bara är ett DELVIS sådant: 750 kg är en fullt rimlig vikt, så
   kontrollen släpper igenom exakt det värde luckan producerar. Den fångar den
   grövre klassen, ett tal som inte kan komma från en avläsning alls. Luckan
   står alltså kvar, nu som ett avgjort val enligt stycket ovan.
6. **ANKARET PRÖVADE BARA SISTA SEGMENTET I SÖKVÄGEN. STÄNGD I SKIVA 22.**
   Uppmätt i skiva 21: `_galler_fordonet` gjorde `rsplit("/", 1)[-1]` och
   jämförde det med numret, så en canonical som
   `https://biluppgifter.se/sok/<numret>/` passerade lager 3. Granskningsvarv 3
   mätte dessutom upp att ett ankare på en HELT ANNAN DOMÄN med rätt nummer
   sist också gav ett uppslag, vilket den ursprungliga lydelsen inte nämnde.

   Lars beslut i #32 är att hela URL:en prövas: schema, värdnamn och sökväg.
   `test_ankaret_provar_hela_urlen` bevakar fem former, och det relativa
   ankaret faller med de andra, eftersom ett svar utan värdnamn inte går att
   knyta till en domän.

   *Här stod att luckan är ofarlig i dag därför att källans söksida svarar med
   `/fordon/` utan nummer. Det ledet gällde söksidan och inte en annan domän,
   och det var därför en smalare grund än luckan behövde.*
7. **EN FOTNOT I ETIKETTEN GJORDE DEN OSYNLIG FÖR RÄKNAREN. STÄNGD I SKIVA 23.**
   Uppmätt i skiva 22. Skrev källan
   `<span class="label">Släpvagnsvikt<sup>1</sup></span>` blev nodens text
   `Släpvagnsvikt1`, alltså en annan sträng. Bar sidan BÅDE den fotnotade och en
   oförändrad `Släpvagnsvikt` räknades bara den senare, tvetydigheten tände
   aldrig, och dess värde gick ut. Riktningen var den farliga: 750 kg under
   tröskeln där 2400 kg var rätt.

   **STÄNGD STRUKTURELLT OCH INTE MED EN PREFIXRÄKNARE.** Beslut av Lars. En
   fotnotsMARKÖR i ett `FOTNOTSELEMENT` utesluts ur etikettnodens text innan
   jämförelsen, så `Släpvagnsvikt` med fotnot är samma etikett som utan, medan
   `Släpvagnsvikt obromsad` förblir en annan. Fällning 19 och 21 binder villkoret
   i var sin riktning.

   **UTESLUTNINGEN GÄLLER MARKÖRER, INTE ORD, och den skillnaden är själv en
   rättelse av två sändvägsdefekter.** Skivans första lydelse tog bort ALLT
   innehåll i ett `sup` eller `small`. Granskningen av skiva 23 mätte upp följden,
   båda gångerna med 750 kg ut där 2400 kg var rätt:

   - `Släpvagnsvikt<small> obromsad</small>` blev `Släpvagnsvikt`, alltså den
     obromsade vikten levererad som den bromsade. Markupen är inte konstruerad:
     `obromsad` ÄR en upplysning i småstil.
   - `<span class="label"><small>Släpvagnsvikt</small></span>` blev en TOM
     etikett, osynlig för räknaren, så en dubblett tände aldrig tvetydigheten.
     **Det är lucka 7 själv, återöppnad av sin egen rättelse.**

   Villkoret är därför att markören saknar BOKSTÄVER. Ett fotnotselement med en
   bokstav bär ett ord, och ett ord i etikettnoden hör till fältets namn tills
   motsatsen är visad: texten behålls, etiketten blir en annan sträng, och fältet
   faller till utkast. Det är den säkra riktningen.

   *Här stod att `test_fotnoten_gor_inte_obromsad_till_samma_etikett` binder
   gränsen. Det gör det inte: fällning 19 lämnar det testet GRÖNT, eftersom det
   binder lager 1:s exakthet och inte uteslutningens gräns. Gränsen bärs åt två
   håll: `test_ord_i_fotnotselementet_ar_en_del_av_namnet` och
   `test_hela_namnet_i_ett_fotnotselement_gor_inte_etiketten_osynlig` är röda
   under fällning 21, och `test_markorer_utan_bokstav_utesluts` under fällning 19.*

   **PREFIX VAR ALDRIG VÄGEN, och skälet är MÄTT och inte principiellt.** En
   räknare som matchar på PREFIX hade fångat fallet. Samma räknare ger TVÅ
   träffar på den avlästa sidan, eftersom `Släpvagnsvikt obromsad` också inleds
   med `Släpvagnsvikt`, alltså hade den kastat på varje verkligt svar. Ett larm
   som alltid går blir avstängt, och det är samma avvägning Lars gjorde i briefen
   till skiva 22 om att inte larma på glappet mellan etiketter och par.
   `test_prefixraknare_hade_larmat_pa_den_avlasta_sidan` mäter påståendet i
   stället för att låta det stå som ett resonemang, och står kvar oförändrat:
   det är beviset för att den stängning som valdes var den rätta.

   **MÄNGDEN ÄR EN AV RESTRISKERNA.** `FOTNOTSELEMENT` bär `sup` och `small`.
   Fixturens åtta avlästa värden bär ingen fotnot alls, så sidan visar inte vilket
   element källan skulle använda, och mängden är därför konventionell och inte
   avläst. Byter källan till ett tredje element står luckan öppen igen för just
   det elementet.

   *Här stod "DET SOM ÅTERSTÅR ÄR MÄNGDEN, inte metoden". Det var ett uttömmande
   påstående och det är falskt: metoden bär lucka 10 nedan, i den riktning som
   släpper ut ett värde. Fällt av granskningsvarv 2.*

   **En markör som ÄR en bokstav faller också utanför.** Skriver källan
   `<sup>a</sup>` bär elementet en bokstav, texten behålls, och etiketten blir
   `Släpvagnsvikta`. Fältet utelämnas då och ärendet faller till utkast. Det är
   den säkra riktningen och inte en stängning, och det står här hellre än att
   räknas som löst.
8. **RIMLIGHETSKONTROLLENS ÖVRE GRÄNS ÄR SIFFERGRÄNSEN, INTE EN
   PERSONBILSGRÄNS.** `_krav_pa_rimlighet` kastar utanför 1 till 9999 kg. Den
   fångar den defektklass som gav 7502400, men ett felläst tal som RÅKAR ligga
   inom fyra siffror passerar, och riktningen är permissiv: ett påhittat
   `9000 kg` hade gett GRÖNT.

   Gränsen är satt så därför att en snävare hade krävt ett tal som varken går
   att läsa ur repot eller ur en körning, och §7.2 säger att ett sådant tal ska
   utelämnas hur rimligt det än ser ut.

   **LARS HAR SVARAT I SKIVA 23: GRÄNSEN 1 TILL 9999 STÅR, och inget snävare tal
   sätts.** Luckan är därmed avgjord som lucka, inte stängd som defekt: den
   permissiva riktningen består och står kvar utskriven här. *Här stod att frågan
   är ställd och obesvarad; det gällde när det skrevs.*

9. **TVÅ HOPKLISTRADE TAL UNDER GRÄNSEN GÅR INTE ATT SKILJA FRÅN EN
   TUSENGRUPPERING.** Registrerad i skiva 23 på Lars beslut, samtidigt som DEL A
   byggdes, och den går inte att stänga i formen.

   `1 200 kg` och `750 400 kg` har exakt samma form: en till tre siffror, en
   avskiljare, tre siffror. Den första är källans eget sätt att skriva 1200 och
   MÅSTE läsas. Den andra är två tal som klistrats ihop till 750400. Inget
   mönster kan skilja dem åt, eftersom skillnaden inte finns i tecknen.

   **Skyddet ligger i rimlighetsintervallet och inte i formen, och det är en
   gräns och inget bevis.** 750400 fastnar i lucka 8:s intervall. Ett hopklistrat
   par vars produkt hamnar UNDER 9999 gör det inte, och `1 200 kg` är exakt det
   fallet. Att den läsningen är rätt just där är tur i formen, inte ett resultat
   av en kontroll.

   **Kastgrenen i `_tal` täcker den INTE.** Den fäller värden som inte går att
   läsa som ett tal alls, alltså `750 2400 kg` där grupperingen är inkonsekvent.
   Ett konsekvent grupperat värde är per definition läsbart, och där tar
   intervallet vid. `test_kand_lucka_hopklistring_under_gransen_ser_ut_som_tusengruppering`
   mäter båda leden och blir rött den dag någon tror sig ha stängt luckan i
   mönstret.

10. **ETT ICKE-ALFABETISKT LED I ETT FOTNOTSELEMENT NORMALISERAS IN I VÅR
    ETIKETT.** Registrerad i skiva 23, fälld av granskningsvarv 2, och den är
    metodens egen kostnad snarare än ett förbiseende.

    Uteslutningen i `_behall` avgör att ett `sup` eller `small` bär en MARKÖR
    genom att dess text saknar bokstäver. Den kan inte veta om ledet är en
    fotnotsmarkör eller ett betydelsebärande suffix. Uppmätt hela vägen genom
    `slag_upp`, med bara den fotnotade raden på sidan:

    ```
    Släpvagnsvikt<sup>2</sup>    med värdet 750 kg   ->  slapvagnsvikt_kg=750
    Släpvagnsvikt<sup>*</sup>                        ->  slapvagnsvikt_kg=750
    Släpvagnsvikt<sup>(2)</sup>                      ->  slapvagnsvikt_kg=750
    ```

    Skriver källan en dag en SKILD etikett vars särskiljande led är
    icke-alfabetiskt och står i ett fotnotselement, blir den vår etikett och dess
    tal vårt fält. Riktningen är den farliga: 750 kg ligger under
    `TROSKEL_SLAPVAGNSVIKT_KG`, avläst till 1 000 i `src/fordonsuppslag.py`.

    **Detta är inte lucka 5.** Där behåller källan namnet och byter betydelse.
    Här har källan ett ANNAT namn, och modulen gör det till vårt.

    **Motsatt riktning är prövad och säker.** Ligger både den fotnotade och den
    rena etiketten på sidan kastar lager 2 med `tvetydigt`, uppmätt i samma
    körning. Luckan kräver alltså att bara den fotnotade raden finns.

    **Varför den inte stängs.** Ett suffix som saknar bokstäver går inte att
    skilja från en markör utan att veta vad källan MENAR, och det är precis vad
    en avläsare inte vet. Alternativet är att inte utesluta något, vilket är
    lucka 7 tillbaka. Avvägningen är Lars, och frågan är ställd i
    `docs/beslutslogg.md` #33.

    **ÖPPEN SÄNDVÄGSLUCKA, och riktningen ska stå utskriven.** Beslut av Lars i
    skiva 24: bokstavsvillkoret STÅR, men luckan registreras som öppen och inte
    som ett kantfall. Riktningen är den farliga, alltså den som SLÄPPER UT ett
    värde: en skild etikett normaliseras in i vår, dess tal blir vårt fält, och
    ingenting syns i loggen. Motsatsen, att vår etikett blir en annan sträng och
    fältet utelämnas, ger utkast och är ofarlig.

    **FORMEN FINNS I FIXTUREN, och det är mätt och inte antaget.** Av de åtta
    avlästa etiketterna bildar `Släp totalvikt (B)` och `Släp totalvikt (B+)` ett
    par som skiljer sig bara på `+`, som inte är en bokstav. Sätter källan
    plustecknet i ett `sup`, vilket är typografiskt naturligt, blir de två
    etiketterna SAMMA sträng. Uppmätt:

    ```
    Släp totalvikt (B)  och  Släp totalvikt (B<sup>+</sup>)
      ->  ['Släp totalvikt (B)', 'Släp totalvikt (B)']
    ```

    **Ingen av de två är ett fält vi läser.** Paret ligger utanför
    `EXAKT_ETIKETT`, så formen finns på sidan men BITER inte i dag. Skillnaden
    mellan att finnas och att bita är hela skälet att luckan står som öppen och
    inte som stängd. `test_lucka_10_formen_finns_bland_de_avlasta_etiketterna`
    mäter båda leden och blir rött den dag fixturen slutar bära paret.

11. **MARKUP INUTI ETT VÄRDE KORRUMPERADE TALET. DELVIS STÄNGD I SKIVA 24,
    HELT I SKIVA 25.** Den väg som återstod efter skiva 24 är lucka 12 nedan,
    och den är stängd. *Här stod först STÄNGD, fällt av granskningens tredje varv
    i skiva 24. Därefter stod DELVIS STÄNGD med lucka 12 som återstående väg i
    presens, vilket blev falskt av skiva 25 och fälldes av dess tredje varv.*
    Fälld av granskningsvarv 3 i skiva 23, uppmätt då mot både arbetsträdet och
    `8629223`:

    ```
    värdet 750<sup>1</sup> kg   ->  8629223=7501   arbetsträdet=7501
    värdet <sup>1</sup>750 kg   ->  8629223=1750   arbetsträdet=1750
    värdet 7<sup>1</sup>50 kg   ->  8629223=7150   arbetsträdet=7150
    ```

    **Talen är identiska i båda versionerna**, alltså infördes luckan av parsern i
    skiva 22 och inte av fotnotsuteslutningen i skiva 23. Den kom fram nu därför
    att skiva 23 tittade på fotnotselement, inte därför att skivan skapade den.

    Parsern konkatenerar textnoderna i ett värde, och det var avsiktligt: fram
    till skiva 24 krävde `test_markupandring_lases_av_parsern` att
    `2400 <abbr>kg</abbr>` lästes som `2400 kg`. Samma konkatenering gjorde en
    fotnotsmarkör inuti talet till en siffra i talet. *Här stod kravet i presens
    efter att skiva 24 flyttat fallet till `test_varde_med_element_kastar`. Fällt
    av granskningen av skiva 24.*

    **Riktningen är farlig och sifferkontrollerna når den inte.** 7501, 1750 och
    7150 ligger alla inom `MIN_VIKT_KG..MAX_VIKT_KG` och ÖVER
    `TROSKEL_SLAPVAGNSVIKT_KG`, avläst till 1 000. Ett fordon vars verkliga
    släpvagnsvikt är 750 kg får därmed ett jakande besked på ett tal ingen källa
    har skrivit.

    **STÄNGD GENOM KAST, INTE GENOM SANERING.** Beslut av Lars i skiva 24. Ett
    värde vars text är avdelad av något som inte är text går inte att tolka, och
    då är avläsningen fel. `if bar_element:` i `_las_falt` kastar, och
    mutationsrad 22 till 25 fäller leden.

    **SEDAN SKIVA 25 MÄTS EGENSKAPEN OCH INTE HÄNDELSEN**, se lucka 12. Samma fall
    fälls, av ett villkor som inte går att utöka.

    **SPÄRRENS FÖRSTA LYDELSE VAR FÖR SMAL, och det ska stå här.** Den satte
    flaggan bara i `handle_starttag` och `handle_startendtag`. Granskningen av
    skiva 24 mätte upp att FYRA andra nodtyper ger exakt samma korrumperade tal:

    ```
    750<!--x-->1 kg       HTML-kommentar          ->  7501
    750<?x?>1 kg          processing instruction  ->  7501
    750<!doctype y>1 kg   declaration             ->  7501
    750</b>1 kg           ENSAM sluttagg          ->  7501
    ```

    Samtliga vände dragfordonsbeskedet från NEJ till JA på ett fordon vars
    verkliga släpvagnsvikt är 750 kg. **Den ensamma sluttaggen är den farligaste**,
    eftersom `_Faltlasare` på annan plats skriver ut som en EGENSKAP att en
    sluttagg utan motsvarande starttagg ignoreras helt. Den egenskapen är riktig
    för stacken och var fel för värdet.

    **Skälet att lydelsen var för smal är mekaniskt:** den beskrev en HÄNDELSE,
    *en tagg öppnas*, i stället för det den skulle vakta, *värdets text är
    avdelad av något som inte är text*. Det är samma form som defekterna i skiva
    21, där mönstren beskrev sidans markup i stället för att läsa den.

    **RÄTTELSEN GJORDE OM SAMMA FEL, och granskningsvarv 2 fällde den.** Den lade
    flaggan i `handle_endtag`:s gren för en sluttagg utan öppen motsvarighet, men
    `handle_endtag` returnerar för `TOMMA_TAGGAR` FÖRE den grenen:

    ```
    750</br>1 kg    ->  7501
    750</hr>1 kg    ->  7501
    750</img>1 kg   ->  7501
    ```

    Det är samma tidiga return som `handle_starttag`:s egen kommentar varnar för,
    och rättelsen hade tillämpat insikten på den ena metoden och inte på den
    andra. **`</br>` är inte ett hittepåfall:** ett ensamt `</br>` inuti ett
    `<template>` bärs som en uppmätt sändvägsdefekt sedan skiva 22 i
    `_Faltlasare`:s egen docstring i `src/biluppgifter.py`. *Här stod att den
    står i den här posten. Fällt av granskningens tredje varv: dokumentet bär den
    inte, koden gör det.*

    **Att fällningen kom av att rättelsen följde en UPPRÄKNING i stället för
    egenskapen är postens lärdom.** Varv 1 räknade upp fyra nodtyper, rättelsen
    stängde de fyra, och den femte fanns bakom en gren ingen hade räknat.
    `test_varde_avdelat_av_nagot_som_inte_ar_text_kastar` bär formerna som
    parametrar, en per form. *Här stod "samtliga sex". Skiva 25 lade till en
    CDATA-parameter i samma test, och gjorde därmed sin egen räkning falsk i
    samma commit. Fällt av granskningsvarv 2.*

    **DET HÄNDE EN TREDJE GÅNG.** Varv 3 fällde att `handle_endtag`:s TRÄFFGREN,
    alltså den där en matchande starttagg hittas på stacken, inte heller
    flaggade. Den vägen är lucka 12 nedan.

    **VARJE RÄTTELSE FÖLJDE VARVETS UPPRÄKNING i stället för egenskapen**, och
    det var skälet att nästa inte skrevs i skiva 24: §7:s varv var slut, och en
    självmätt spärrändring efter grinden hade prövats av ingen. **Skiva 25 bytte
    i stället metod**, se lucka 12. Händelselistan är borta ur koden.

    *Här stod "tre rättelser i rad" och att nästa hade varit "den fjärde
    gissningen". Båda är räkningar av ett arbetsförlopp som repot inte bär:
    skiva 24 är EN commit, och granskningsrapporterna ligger i gitignorerad
    `scratchpad/`. §7.2 namnger den formen som förbjuden. Fällt av granskningen
    av skiva 25. Lydelserna är uppräknade var för sig i `_varde_bar_markup`:s
    docstring, och det är den formen som bär.*

12. **EN SLUTTAGG SOM STÄNGER ETT ELEMENT UNDER VÄRDET KLIPPTE VÄRDETS TEXT,
    OFLAGGAT. STÄNGD I SKIVA 25.** Uppmätt av granskningens tredje varv i skiva
    24, reproducerad av mig i egen körning.

    `handle_endtag` letar upp närmaste öppna element med samma namn. Ligger det
    UNDER det aktiva värdet på stacken anropas `_stang_faltet`, som lägger paret
    med den text som hunnit samlas. Före skiva 25 var flaggan då `False`, och
    resten av värdet släpptes utan att någon visste hur mycket det var.

    ```
    <li><b><span class="label">Släpvagnsvikt</span>
           <span class="value">1500 kg</b> enligt registrering, verklig 750 kg</span></b></li>

      utan </b>  ->  ('Släpvagnsvikt', '1500 kg enligt registrering, verklig 750 kg', False)
      med  </b>  ->  ('Släpvagnsvikt', '1500 kg', False)
    ```

    Utan sluttaggen föll fältet till utkast, eftersom texten inte är en ren vikt.
    Med den blev svaret `1500 kg`, alltså **en välformad vikt som sidan aldrig
    påstått om släpvagnen**, och den ligger över tröskeln. I dag kastar båda
    formerna. *Här stod meningen i presens efter att skiva 25 stängt luckan, medan
    grannmeningarna skrevs om till imperfekt. Fällt av granskningsvarv 3.*

    **Riktningen är den farliga**, och luckan är av samma klass som lucka 11:
    markup inuti ett värde ändrar det avlästa talet utan att flaggan sätts.

    **VARFÖR DEN INTE STÄNGDES I SKIVA 24.** §7:s tre granskningsvarv var
    förbrukade när den hittades, och de två föregående rättelserna av samma spärr
    var båda fel på samma sätt. En tredje självmätt spärrändring efter grinden
    hade ingen prövat. Luckan stod därför registrerad och mätt, och åtgärden blev
    Lars beslut. **Det beslutet är #35**, och det gjorde om spärren i grunden i
    stället för att lappa den.

    **STÄNGD GENOM ATT MÄTA EGENSKAPEN, INTE GENOM ETT FEMTE VILLKOR.** Beslut av
    Lars, skiva 25. Kravet är att stängningen ska vara VÄRDETS EGEN sluttagg. Det
    är inte en femte händelse utan samma egenskap tillämpad där den inte GÅR att
    mäta: stängs fältet av något annat är värdets verkliga utsträckning okänd,
    och då vet vi inte hur mycket text som släpptes. Mutationsrad 23 fäller
    villkoret, och `test_varde_som_stangs_av_nagot_annat_an_sin_egen_sluttagg_kastar`
    bär de två formerna.

    **Att jämförelsen mellan råtext och textnoder INTE fångar det här fallet ska
    stå utskrivet.** Fältet stängs vid sluttaggen, så råtexten fram till den
    punkten ÄR lika med textnoderna. Det som saknas är utsträckningen, inte
    innehållet.

    **Etikettsidan är inte drabbad.** Föräldrajämförelsen på löpnummer fäller
    paret där, eftersom numret ändras när elementet tas av stacken. Det är värdet
    som saknar motsvarande skydd.

    Invändningen mot att stänga luckan var att varje väg innebär att tecken
    plockas bort ur ett tal vi skickar vidare. **Den invändningen var riktig och
    slutsatsen fel:** ingenting plockas bort. En sida som skriver 750 med en
    fotnot inuti säger något vi inte kan tolka.

    **Kostnaden är att en fotnot i ett värde ger ett kast, och den är SYNLIG.**
    7501 var det inte. Samma regel som `750 2400 kg` fick i skiva 23: ett fält som
    fanns men lästes fel ser inte ut som ett fält som saknades.

    **Spärren sitter i `_las_falt` och inte i parsern**, alltså gäller den bara de
    tre fält `EXAKT_ETIKETT` namnger. Den skarpa sidan bär värden med nästlad
    markup i fält vi aldrig läser, `Chassinr / VIN` är det avlästa exemplet, och
    en spärr i parsern hade kastat på varje verkligt svar.
    `test_element_i_ett_falt_vi_inte_laser_ror_ingenting` mäter det.

    **`750 kg<sup>1</sup>` gav förut utkast och kastar nu.** Utfallet är
    fortfarande att inget värde kommer ut, men skälet är ett annat, och det är en
    avsiktlig följd av regeln.

    **TVÅ KOMMITTADE VERSIONER BAR LUCKAN ÖPPEN**, `8629223` och `52d0a97`. Den
    infördes av parsern i skiva 22 och kom fram först när skiva 23 tittade på
    fotnotselement i ETIKETTER, alltså av en tillfällighet. Det är postens
    tydligaste belägg för att en prövning som bara följer skivans egen ändring
    inte räcker.

---

## `dragkrokbesked-har-harkomst`

**BYGGD I SKIVA 13**, på beslut av Lars. Luckan stod registrerad i
`fordonsfakta-ur-uppslag` sedan skiva 12 och är nu en egen spärr.

- **Spärr.** `utvardera`, `DragkrokBesked` och `BeskedKalla` i
  `src/fordonsuppslag.py`. **`utvardera` står först därför att den är spärrens
  viktigaste lager**, se nedan: utan typkontrollen där binder de två andra
  ingenting.
  **Ett besked om att dragkrok saknas går inte att sätta utan att samtidigt
  namnge sin källa**, och källan måste vara en medlem i `BeskedKalla`.

  Beslutet fattas på fyra ställen, som TEXT:

  | Var | Villkoret | Vad det fäller |
  | --- | --- | --- |
  | `utvardera` | `if besked is not None and not isinstance(besked, DragkrokBesked):` | Vilket objekt som helst som inte ÄR ett besked |
  | `DragkrokBesked.__post_init__` | `if not isinstance(self.saknas, bool):` | Ett besked som inte är ja eller nej |
  | `DragkrokBesked.__post_init__` | `if not isinstance(self.kalla, BeskedKalla):` | En källa som inte finns i uppräkningen, inklusive strängen `"kundsvar"` |
  | `BeskedKalla` | Uppräkningens INNEHÅLL | Allt som inte är `KUNDSVAR` eller `UTKASTVY` |

  **TYPKONTROLLEN I `utvardera` ÄR SPÄRRENS VIKTIGASTE LAGER, och den saknades i
  ett utkast av den här skivan.** Utan den prövade `utvardera` bara
  `besked.saknas`, alltså en ankuppslagning. **Vilket objekt som helst med det
  attributet gav GULT**, förbi hela härkomstkravet. Uppmätt i granskningen:
  `utvardera(u, besked=SimpleNamespace(saknas=True))` gav `Utfall.GULT`.

  Att `DragkrokBesked` var svår att konstruera fel spelade ingen roll när ingen
  krävde ett `DragkrokBesked`. **En spärr som inte binder vid anropsstället
  binder ingenstans.** `test_besked_av_fel_typ_avvisas` vaktar det.

  **Att `kalla` är ett obligatoriskt argument är i sig ett lager.** `DragkrokBesked(saknas=True)`
  kastar `TypeError` innan någon vakt hinner köras, och
  `test_besked_kraver_en_kalla` vaktar det.

  De tillåtna källorna är beslutade av Lars: **ett uttryckligt kundsvar, eller
  manuell inmatning i utkastvyn i fas 5.5. Aldrig en modell, aldrig
  klassificeraren.** Uppräkningen bär ingen medlem för dem, och det är hela
  mekanismen.
- **Vad den skyddar mot.** Att ett svar namnger ett PRISPÅSLAG på grundval av
  något ingen människa har sagt.

  Beskedet flyttar utfallet från OKLART, alltså en fråga till kunden, till GULT,
  alltså ett svar som säger att dragkrok ska monteras och vad det kostar. Före
  skiva 13 var det en naken `bool` i `utvardera`, och en klassificerare som
  gissade rätt sorts ärende kunde sätta den utan att någon i efterhand kunde se
  varifrån den kom.

  Fordonsfakta måste passera `fordonsfakta-ur-uppslag`; den här biten passerade
  ingenting. Asymmetrin var luckan.
- **Negativkontroll.** `tests/test_fordonsuppslag.py::test_bada_tillatna_kallorna_gar_igenom`
  visar att spärren SLÄPPER IGENOM båda de tillåtna källorna. Testet är
  parametriserat över `list(BeskedKalla)`, så en framtida tredje källa får sin
  negativkontroll automatiskt.

  `::test_uppraekningen_bar_ingen_modellkalla` vaktar från andra hållet: det
  asserar att uppräkningen bär exakt `kundsvar` och `utkastvy`. **Läggs en
  modellkälla till upphör spärren att betyda något**, och testet gör det till ett
  medvetet beslut i stället för en tyst ändring (§10).
- **Redundant med. INGEN ANNAN SPÄRR.** Lagren i tabellen ovan är inte heller
  redundanta med varandra: de fäller olika fel, och vart och ett har ett eget
  test som blir rött när just det fälls. Det gäller också det femte lagret, att
  `kalla` är ett obligatoriskt argument.
- **VAD DEN INTE KAN HINDRA. Kända luckor, och listan är inte en garanti för att
  vara uttömmande.**

  1. **En anropare som medvetet anger fel källa.** Ingenting i koden kan avgöra
     om `BeskedKalla.KUNDSVAR` verkligen motsvarar ett kundsvar. Skillnaden mot
     förut är att det kräver **en uttrycklig osanning i koden** i stället för ett
     bortglömt `True`, och att källan går att logga och granska i efterhand.
  2. **Sex uppmätta vägar ger ett objekt som `utvardera` accepterar.** De namnges
     var för sig, av samma skäl som i posten ovan: ett samlingsord döljer att
     listan är ojämn. **Listan är inte uttömmande** — de två sista tillkom när en
     granskare letade bredare än den förra.

     | Väg | Vad som går fel | `kalla` blir |
     | --- | --- | --- |
     | Subklass som skuggar `__post_init__` | Vakten överskuggas, konstruktionen körs | `"modell"` |
     | `object.__new__` + `object.__setattr__` | `__init__` körs aldrig | `"modell"` |
     | `pickle.loads` av en doktorerad instans | Återskapas utan `__init__` | `"modell"` |
     | `object.__setattr__` på en FÄRDIG instans | `__post_init__` KÖRDE, objektet muterades efteråt | oförändrad, giltig |
     | `copy.copy` och `copy.deepcopy` | Kopieras utan att `__post_init__` anropas | ärvs från förlagan |
     | `unittest.mock.Mock(spec=DragkrokBesked)` | `isinstance` är sant mot en attrapp | finns inte alls |

     **`Mock`-raden är den mest närliggande i praktiken**, eftersom fas 5:s
     tester kommer att bygga attrapper. Uppmätt: en `Mock` med `spec` och enbart
     `.saknas` satt ger GULT, och `kalla` existerar inte ens på objektet.
     `utvardera` rör bara `.saknas`, så typkontrollen släpper igenom den.

     **Raden om `object.__setattr__` på en färdig instans missades av ett utkast**,
     som skrev "aldrig körde `__post_init__`" som kriterium. Just den vägen körde
     det, och den kräver ingen exotisk konstruktion alls: den muterar ett äkta
     besked.

     De tre första sätter `kalla` till strängen `"modell"`, alltså ett värde som
     `__post_init__` hade avvisat.

     Samtliga uppmätta i skiva 13. Ingen av dem hårdnas mot, eftersom boten inte
     möter fientlig indata.
  3. **Att beskedet är SANT.** En kund kan minnas fel om sin egen bil. Det är
     inte en defekt i spärren utan en gräns för vad ett besked är värt, och den
     hör hemma i mallarnas ordalydelse i fas 5.

  Spärren flyttar felet från *slarv* till *avsikt*. Det är en verklig skärpning
  och inte en garanti, och den som läser posten ska inte ta den för mer än så.
- **Prövning enligt §7.1, `scripts/sparr-prova.sh`.** Villkoren NEUTRALISERADES
  till `if False:`, utom uppräkningen, där en medlem ERSATTES.

  | Fällt lager | Fällning | Utfall | Sviten |
  | --- | --- | --- | --- |
  | typkontrollen i `utvardera` | `if False:` | RÖD | `4 failed, 350 passed` |
  | `not isinstance(self.saknas, bool)` | `if False:` | RÖD | `1 failed, 353 passed` |
  | `not isinstance(self.kalla, BeskedKalla)` | `if False:` | RÖD | `5 failed, 349 passed` |
  | `kalla` obligatoriskt | `kalla: BeskedKalla = BeskedKalla.KUNDSVAR` | RÖD | `1 failed, 353 passed` |
  | `UTKASTVY = "utkastvy"` | `MODELL = "modell"` | RÖD | `1 failed, 353 passed` |

  Svitens storlek vid prövningen: 354 test. **Samtliga fem lager går att fälla
  var för sig**, alltså är inget av dem maskerat av ett annat.

  **RADEN OM DET OBLIGATORISKA `kalla`-ARGUMENTET SAKNADES i ett utkast**, trots
  att posten deklarerade lagret fyra rader ovanför. Granskningen körde
  fällningen och fick RÖD. Det är samma defekt som posten själv fördömer i
  stycket nedan, en paragraf bort.

  **Uppräkningen GÅR att fälla, och ett utkast av den här posten påstod motsatsen.**
  Utkastet skrev att innehållet inte går att fälla utan att modulen slutar
  importeras, och kallade det en svaghet i prövningen. Granskningen körde
  fällningen och fick RÖD. Att byta ut en medlem mot `MODELL = "modell"` lämnar
  modulen importerbar, och `test_uppraekningen_bar_ingen_modellkalla` faller.
  **En redovisad prövning som avstår från en prövning som går att göra är sämre
  än ingen redovisning**, eftersom den ser ut som ett fullständigt varv.

---

## `kanal-som-kontext-aldrig-grund`

**BYGGD I SKIVA 17.** Till skillnad från `gmail-etikett-som-ensam-grund`, som
är en regel utan kod, har den här posten kod och går att fälla.

- **Spärr.** Ingen funktion mappar en kanal till en kategori.
  `src/kanal.py::namnge` returnerar ett kanalNAMN eller `None`, och
  `src/kategorisera.py::bygg_anvandarmeddelande` lägger namnet i ett avgränsat
  kontextblock i användarmeddelandet. `src/ometikettera.py::ometikettera_en`
  prövar modellens svar mot taxonomin och gör inget annat. Kanalen påverkar
  alltså vad modellen SER, aldrig vad koden GÖR med svaret.
- **Vad den skyddar mot.** Att en bekräftande signal blir ensam grund. Lars
  regel i #27, tillämpad på kanalen i #29. Frestelsen är konkret: 42 av 78
  formulärtrådar klassades som något annat än a-traktor, och en
  kanal-till-kategori-koppling hade rättat statistiken i ett slag. Den hade
  också gjort varje biltvättsfråga som råkat komma via formuläret till ett
  a-traktorärende.
- **Negativkontroll.** `test_kanalen_overstyr_aldrig_modellens_svar` låter
  modellen svara `boka biltvätt` medan kanalen är a-traktorformuläret och kräver
  att svaret står kvar. `test_samma_svar_ger_samma_etikett_med_och_utan_kanal`
  visar att efterbehandlingen är identisk med och utan kanal.
  `test_kanalen_gor_inte_ett_svar_utanfor_taxonomin_giltigt` visar att kanalen
  inte heller räddar ett svar utanför listan.
- **Redundant med.** Ingen annan spärr.

**PRÖVNINGEN GÅR INTE TILL SOM DE ANDRA, och det är inte en brist.** Posten
vaktar FRÅNVARON av kod. Att radera en rad gör ingenting, eftersom raden inte
finns. Fällningen sker genom att SKRIVA DIT den förbjudna kopplingen:

    scripts/sparr-prova.sh --fil src/ometikettera.py \
      --ersatt '<rad>=    return "boka a-traktorkonvertering" if kanal else (namn if namn in taxonomi else UTANFOR)' \
      -- -q tests/test_kanal.py

Utfört i skiva 17: RÖD, tre negativkontroller föll. Radnumret skrivs inte ut
här, eftersom det flyttar av varje redigering i filen; raden är den enda
`return` i `ometikettera_en`.

**Trunkeringen är ett eget lager.** `bygg_anvandarmeddelande` kortar TEXTEN
och lägger kontexten till efteråt. Vore taket satt på summan hade ett långt
kontextblock ätit av kundens egna ord, alltså det enda som får avgöra
kategorin. `test_trunkeringen_galler_texten_inte_summan` binder det, och en
fälld trunkering ger RÖD.

**Kanalen fastställs på ÄMNESRADEN, inte på avsändardomänen.** Den egna
domänen bär också annan maskinell trafik: uppmätt i #27 delar 103 av 105
maskinmailtrådar med egen domän adress med bokningsnotiserna. En domänprövning
hade därför gjort varje WordPress-notis till ett formulärinskick.

**`None` betyder VET INTE, aldrig `e-post` som slasktratt.** En påhittad kanal
hade varit en signal som såg mätt ut, och en signal man hittat på bekräftar
ingenting.

---

## `vyn-har-ingen-sandvag`

**BYGGD I SKIVA 27.** Registrerad som byggd, inte som PLANERAD.

- **Spärr.** `src/vy.py::krav_pa_sandvagsfrihet` kastar `Sandvagsfel` om någon
  modul vyn drar in kan skicka mail. Beslutet fattas på TVÅ villkor:
  `if importerad in FORBJUDNA_MODULER or rot_namn in FORBJUDNA_MODULER`
  (importlagret) och `if traff` efter
  `FORBJUDET_MONSTER.search(_kod_utan_prosa(kalla))` (källtextlagret).
  Prövningen körs av `starta` på raden `krav_pa_sandvagsfrihet()`, alltså INNAN
  servern binder porten.
- **Vad den skyddar mot.** Att ett referenssvar lämnar servern som mail.
  `docs/beslutslogg.md` #39 gör det bindande att ett referenssvar ALDRIG skickas,
  och fältets text ser ut precis som ett svar. **Spärren är att det inte finns
  någon väg, inte att vägen är stängd**: en knapp som inte syns, eller ett anrop
  bakom ett villkor, är en väg som råkar vara oanvänd.
- **Negativkontroll.** `tests/test_vy.py::test_en_ren_modul_slapps_igenom` visar
  att spärren SLÄPPER IGENOM en modul som importerar `json` och en lokal modul.
  Utan den raden vore en spärr som alltid fäller omöjlig att skilja från en som
  fungerar, och en spärr som alltid fäller blir avstängd.
- **Redundant med.** Ingen annan spärr. De två LAGREN är däremot redundanta med
  varandra i vissa fall, se tabellen: fälls bara det ena förblir en del av
  sviten grön.

**De två lagren är INTE utbytbara, och det är mätt.** En modul kan nå en färdig
Gmail-tjänst som ARGUMENT och anropa `messages().send` utan att importera något
förbjudet; då ser importlagret ingenting.
`test_kalltextlagret_faller_ett_anrop_utan_import` är det fallet.

**Källtextlagret läser KOD, inte prosa om kod.** `_kod_utan_prosa` tar bort
kommentarer och strängar före sökningen. Utan det ledet fälldes `src/vy.py` av
sin egen kommentar, som namnger `messages().send` för att förklara vad som är
förbjudet. Uppmätt vid skivans första körning av testet, och det är samma fälla
som rutan överst i det här dokumentet varnar för.

**`from x import y` ger både `x` och `x.y`.** Utan det ledet följde prövningen
aldrig kedjan vidare, och `from src import auth` hade sett ut som en import av
`src`. En enda indirektion hade räckt för att gömma en sändväg.

| Fälld rad | Utfall | Form |
| --- | --- | --- |
| båda lagren, villkoren satta till `False` | RÖD, `9 failed, 36 passed` | neutraliserade |
| enbart importlagret | RÖD, `8 failed, 37 passed` | neutraliserad |
| enbart källtextlagret | RÖD, `1 failed, 44 passed` | neutraliserad |
| kedjeledet `namn.update(f"{paket}.{alias.name}" ...)` | RÖD, `4 failed, 41 passed` | raderad |
| kedjeledet `namn.add(paket)` | RÖD, `2 failed, 43 passed` | raderad |
| nivåvillkoret `if nod.level:` satt till `if False:` | RÖD, `4 failed, 41 passed` | neutraliserad |
| `i_modul` i `moduler_i_vyn`, satt till tom sträng | RÖD, `1 failed, 44 passed` | neutraliserad |
| `i_modul` i `krav_pa_sandvagsfrihet`, satt till tom sträng | RÖD, `1 failed, 44 passed` | neutraliserad |
| `krav_pa_sandvagsfrihet()` i `starta` | RÖD, `1 failed, 44 passed` | raderad |
| `HTTPServer(("127.0.0.1", port), ...)` satt till `"0.0.0.0"` | RÖD, `1 failed, 44 passed` | neutraliserad |
| `def log_message` omdöpt, alltså övertäckningen borttagen | RÖD, `1 failed, 44 passed` | neutraliserad |

**DE TVÅ `i_modul`-ARGUMENTEN FÄLLS VAR FÖR SIG, och de bär olika fall.** Det i
`moduler_i_vyn` är det som får VANDRINGEN att följa en relativ import vidare;
det i `krav_pa_sandvagsfrihet` är det som får NAMNET prövat mot
`FORBJUDNA_MODULER`. Efter att skiva 28 rättat vandringen blev det andra grönt
vid fällning, alltså inkonklusivt: de två bar varandra. Testet
`test_relativ_import_av_en_forbjuden_modul_falls_pa_NAMNET` skiljer dem åt genom
att göra den importerade modulen ofarlig, så att bara namnprövningen kan fälla.

**DE TRE KEDJELEDEN FÄLLS VAR FÖR SIG, av samma skäl som de två anropen i
`vyn-skriver-bara-till-data-och-logg`.** `namn.add(nod.module)` gick att radera
med hela sviten grön. Funnet av §7-granskningen av skiva 27, varv 2, och stängt
med `test_importlagret_foljer_kedjan_aven_via_paketform`.

*Här stod att inget test använde formen `from paket.modul import namn`. Det är
falskt: `tests/test_vy.py` bär sedan `8e369ce` fixturen
`from googleapiclient.discovery import build`, som är just den formen. Raden var
vakuös av ett smalare skäl: inget test använde formen för en modul vars
förbjudna namn är hela den punktade sökvägen och inte dess rotpaket, så
`googleapiclient`-fixturen fälldes av `rot_namn`-grenen i stället. Slutsatsen
stod, förklaringen inte. Fällt av §7-granskningen av skiva 27, varv 3.*

**De två sista raderna vaktar §6 och inte sändvägen**, men de sitter i samma
kod och prövas därför här. Bindningen till loopback är skivans centrala
§6-påstående, eftersom vyn saknar inloggning: den som når porten når kundtexten.
Båda var ovaktade fram till varv 2.

Sviten var `tests/test_vy.py`, som bar 45 test vid mätningen. Kommandot är
`scripts/sparr-prova.sh --fil src/vy.py --ersatt "<rad>=..." -- tests/test_vy.py
-q --tb=no -rN`. Radnumren skrivs inte ut, eftersom de flyttar av varje
redigering i filen; villkorens TEXT står ovan.

**KÄNDA LUCKOR. Posten säger "det finns ingen väg", och spärren MÄTER något
smalare.** Registrerade av §7-granskningen av skiva 27, varv 1, och utskrivna
här av samma skäl som `fordonsfakta-ur-uppslag` skriver ut sina: en spärrpost som
låter heltäckande är farligare än en som namnger sin räckvidd.

- **Lucka 13. `FORBJUDNA_MODULER` och `FORBJUDET_MONSTER` är UPPRÄKNINGAR, inte
  en egenskap.** De bär tre namn respektive tre anropsformer. `subprocess`,
  `socket`, `urllib.request`, `http.client`, `requests` och `os.system` fälls av
  ingetdera lagret. Ingen av dem finns i vyn i dag, mätt genom att läsa
  `src/vy.py`:s importer, men spärren skulle inte fälla dem om de kom.
  Riktningen är alltså densamma som lucka 12 hade före skiva 25: en händelselista
  där en egenskap vore starkare.
- **Lucka 14. Ingångspunkten granskas inte.** `krav_pa_sandvagsfrihet` startar
  sin vandring på `src.vy`. `scripts/kor-vy.py`, som är det som FAKTISKT startar
  vyn, ligger utanför grafen och prövas aldrig. Ett sändanrop där hade passerat.
  Filen läses i dag av `test_repot_sjalvt_ar_rent` för osynliga tecken, alltså
  finns den i sviten, men inte i den här spärren.

- **Lucka 16. HTTP-lagret är otestat, och luckan är MÄTT i stället för bara
  namngiven.** Se det egna avsnittet nedan.

Ingen av luckorna är stängd av den här skivan.

### Lucka 16 i detalj — vad som är oprövat i HTTP-lagret

**En lucka som är mätt är synlig. En som bara är namngiven är det inte.** Därför
står rutterna, testtäckningen och konsekvenserna utskrivna här i stället för
sammanfattade i en mening.

**RUTTERNA.** `bygg_hanterare` bygger en `BaseHTTPRequestHandler` med tre
metoder: `do_GET`, `do_POST` och en tystad `log_message`. All vägval sker i
`_index_ur_vag`, som tar SISTA segmentet av sökvägen.

| Metod | Väg | Vad som händer |
| --- | --- | --- |
| GET | vilken som helst, tom fall-lista | sidan `Inga fall.` |
| GET | vilken som helst, med fall | `rendera_referens` på det upplösta indexet |
| POST | vilken som helst | `spara_referenssvar` på det upplösta indexet |
| POST | vid `ValueError` | `rendera_fel`, status 400 |

**INGEN AV DEM HAR ETT TEST.** `grep -rn "do_GET\|do_POST\|_index_ur_vag" tests`
ger en enda träff, och den ligger i en docstring. Två rader går att fälla med
hela sviten grön:
`_index_ur_vag`:s klämning och `do_GET`:s tomfall. Även sömmen
`self._svara(rendera_fel(fel), 400)` går att byta mot en tom sida med sviten
grön: `rendera_fel` är prövad, anropet av den är det inte.

**VAD `_index_ur_vag` FAKTISKT GÖR.** Avläst genom att anropa funktionen med
`antal` lika med 5:

| Väg | Index | Kommentar |
| --- | --- | --- |
| `/referens/0` | 0 | |
| `/referens/3` | 3 | |
| `/referens/999` | 4 | **klämt till sista posten, tyst** |
| `/referens/-1` | 0 | minustecknet gör `isdigit` falskt |
| `/referens/` | 0 | |
| `/` | 0 | |
| `/omdome` | 0 | **okänd väg blir post 0, tyst** |

**VAD ETT FEL HÄR SKULLE BETYDA, och det är inte en krasch.** Varje icke-siffra
blir 0 och varje för stort tal blir sista posten, båda utan att något syns.
Konsekvensen av fel index i `do_POST` är att **Lars referenssvar sparas som ett
par mot FEL inkommande mail**. `data/par.jsonl` bär då en hopparning som aldrig
funnits, och fas 5 bygger mallarna ur den filen. Det är alltså inte en trasig
sida utan ett felaktigt träningsunderlag för rösten, infört tyst.

**DEN KONKRETA INSTANSEN FINNS REDAN I KODEN.** `rendera_granskning`:s formulär
har `action='/omdome'`. Den vägen löses till index 0, och `do_POST` anropar
`spara_referenssvar`, inte `spara_omdome`. Ett omdöme skulle alltså sparas som
ett REFERENSSVAR mot första posten. Det är ofarligt i dag enbart därför att
lucka 15 gör att ingen rutt når granskningsläget, alltså skyddar en lucka en
annan.

**Vad som skulle stänga den.** Ett test per rutt, och en `_index_ur_vag` som
AVVISAR en väg den inte känner igen i stället för att falla tillbaka på 0. Den
andra delen är en beteendeändring i sändvägen och hör därför till den skiva som
kopplar in granskningsläget, inte till den här.

**RELATIVA IMPORTER: EN LUCKA SOM TOG TVÅ RÄTTELSER ATT STÄNGA.** Ingen av
luckorna 13 till 15 täckte formen, och `src/__init__.py` finns, så en enda
relativ rad hade räckt för att dra in `src/auth.py`.

**Första rättelsen, skiva 27 varv 3.** `from . import auth` gav en TOM mängd ur
`_lokala_importer`, eftersom villkoret krävde `nod.module`. Stängd med `_paket`,
som löser nivån mot modulens eget namn.

**Andra rättelsen, skiva 28.** Den första lämnade `from .auth import bygg`
öppen. Där ÄR `nod.module` satt, men bara till en DEL av sökvägen, och
uttrycket `nod.module or _paket(...)` tog modulnamnet och ignorerade nivån.
Spärren fick `auth` i stället för `src.auth`: namnet matchade inte
`FORBJUDNA_MODULER`, och vandringen letade efter `auth.py` i repotet.

**VILLKORET FRÅGAR NU EFTER `nod.level` OCH INTE EFTER `nod.module`.** Är nivån
större än noll löses paketet alltid upp, och modulnamnet fogas på när det finns.
Formerna och deras AST står i `_lokala_importer`:s docstring, avlästa med
`ast.parse`.

**Skälet till att den första rättelsen missade** var en falsk premiss i sin egen
docstring, att relativa importer inte bär något paketnamn. Den premissen är
struken, och det är samma klass av fel som lucka 12: ett villkor formulerat efter
de FORMER man råkat tänka på, i stället för efter den egenskap som avgör.

Formerna bärs av ett test var, samtliga i `tests/test_vy.py`:

| Form | Test |
| --- | --- |
| `from src import mellan` | `test_importlagret_foljer_kedjan_ett_steg_till` |
| `from src.mellan import hjalp` | `test_importlagret_foljer_kedjan_aven_via_paketform` |
| `from . import auth` | `test_importlagret_ser_relativa_importer` |
| `from .auth import bygg` | `test_relativ_import_med_modulnamn_ser_ocksa_sandvagen` |
| nivån djupare än modulen | `test_relativ_import_utan_kant_modul_gissar_inte` |

---

## `spärrfälld-post-utan-textfalt`

**BYGGD I SKIVA 27**, på Lars beslut i `docs/beslutslogg.md` #40.

- **Spärr.** `src/vy.py::rendera_granskning` returnerar sidan utan `<textarea>`
  och utan `<button>` när argumentet `sparr` är satt. Beslutet fattas på raden
  `if sparr:`, som returnerar tidigt med en förklaringsruta i stället för
  formuläret.
- **Vad den skyddar mot.** Att §9.1:s förbud mot att skriva om ett fällt mail
  tills spärren släpper igenom det blir ett klick. **Regeln gäller
  GRÄNSSNITTET, inte texten.** Ett referenssvar når aldrig en kund, alltså skulle
  ingen omskrivning på en fälld post faktiskt skicka något. Det är inte
  invändningen: en vy som övar in rörelsen på ofarliga poster har lärt ut den när
  posterna inte längre är ofarliga.
- **Negativkontroll.** `tests/test_vy.py::test_osparrad_post_visar_textfalt`
  visar att en post UTAN spärr får sitt textfält och sina fyra omdömen. Utan den
  raden hade `rendera_granskning` kunnat sluta visa formulär helt, och
  granskningsläget varit oanvändbart utan att något blev rött.
- **Redundant med.** Ingen annan spärr. `vyn-har-ingen-sandvag` skyddar mot en
  annan sak: att texten lämnar servern. Den här skyddar mot att rörelsen övas in.

| Fälld rad | Utfall | Form |
| --- | --- | --- |
| `if sparr:` satt till `if False:` | RÖD, `1 failed, 44 passed` | neutraliserad |
| `html.escape` runt `forslag` och `sparr` borttagen | RÖD, `1 failed, 44 passed` | neutraliserade |
| `html.escape(str(fel))` i `rendera_fel` borttagen | RÖD, `1 failed, 44 passed` | neutraliserad |

**De tre sista raderna vaktar §6 och inte DEL 0**, och står här därför att de
sitter i samma renderare.

**VILKA SOM VAR OVAKTADE, per plats i stället för summerat.** Avläst ur
`git grep -n "html.escape" e16be28 -- src/vy.py` mot
`git grep -n "escapas" e16be28 -- tests/test_vy.py`: åtta escapningsplatser,
varav två vaktade. De två var `fall.text` i vardera renderaren, av
`test_kundtexten_escapas_i_sidan` och
`test_kundtexten_escapas_aven_i_granskningslaget`. Ovaktade var `fall.etikett` i
båda renderarna, `fall.kalla`, `sparr`, `forslag` och `str(fel)`.

*Här stod att kundtext, förslag, spärrnamn och felmeddelande escapades "utan att
något test mätte det" och att därför VARJE `html.escape` gick att ta bort med
sviten grön. Kundtexten var mätt, av de två testen ovan, alltså är båda leden
falska. Meningen ersatte en sann och smalare lydelse med en bredare, vilket är
den form rutan överst i det här dokumentet redan noterar. Här stod också att
varv 3 fann "fyra till"; det var sex, och uppräkningen utelämnade `sparr`, som
tabellraden ovanför namnger. Fällt av §7-granskningen av skiva 28.*

**Varv 2 stängde EN instans, och testet som skulle stänga KLASSEN gjorde det
inte.** Det räknade upp de fält som fanns när det skrevs, alltså föll det inte
av ett nytt fält. Granskningen av skiva 28 renderade ett befintligt men
ouppräknat `Fall`-fält oescapat och fick hela sviten grön.

**Nu härleds fälten ur `Fall` och parametrarna ur `inspect.signature`**, så ett
nytt fält eller en ny strängparameter blir rött av att EXISTERA. Det är
skillnaden mellan en uppräkning och en egenskap, alltså samma skillnad som
lucka 12 och lucka 13 handlar om, tillämpad på ett test i stället för på en
spärr.

`rendera_fel` är UTBRUTEN ur `do_POST` för att gå att pröva alls. Den bär det
enda stället där data rakt ur POST-kroppen reflekteras tillbaka i HTML, och
inbakad i hanteraren kunde escapningen bara testas genom att testet upprepade
den, vilket är ett test som inte kan bli rött.

**Behövs en referens för ett ärende vars förslag fälldes, tas en annan post av
samma kategori.** Det står i #40 och i fas 5.5, och det är vad som gör spärren
kostnadsfri: referenssvaret är underlag för rösten och inte ett svar på det
enskilda ärendet.

**KÄND LUCKA 15: #40 säger OAVSETT LÄGE, och spärren är verkställd i ETT läge.**
Registrerad av §7-granskningen av skiva 27, varv 1.

`rendera_granskning` tar en `sparr` och lyder. `rendera_referens` har ingen
sådan parameter och visar alltid sitt textfält, och `do_GET` rutar varje
begäran dit. En post som bär både ett fällt förslag och ett behov av
referenssvar, alltså precis det fall #40 avgör, skulle i dag få sitt textfält
genom referensläget.

**Luckan är ofarlig i dag och blir farlig i fas 5.** Ingen post KAN vara
spärrfälld nu, eftersom generatorn inte finns och ingen spärr har något förslag
att fälla. Den dag den finns är det här den första platsen att stänga, och
stängningen hör till den skiva som kopplar in generatorn: `rendera_referens`
behöver samma `sparr`-argument, och urvalet behöver veta vilka poster som är
fällda.

Luckan är öppen och inte stängd av den här skivan.

---

## `vyn-skriver-bara-till-data-och-logg`

**BYGGD I SKIVA 27.**

- **Spärr.** `src/vy.py::krav_pa_skrivbar_sokvag` kastar `Skrivfel` om en sökväg
  ligger utanför repot eller utanför `data/` och `logg/`. Beslutet fattas på
  raden `if relativ.parts[:1] != ("data",) and relativ.parts[:1] != ("logg",):`.
  Formen är ett SNITT och inte en indexering, eftersom `parts` är TOM när
  sökvägen är repoteten självt: `parts[0]` kastade då `IndexError` i stället för
  `Skrivfel`, alltså fällde spärren med fel undantag. Funnet av
  §7-granskningen av skiva 27, varv 1, och bundet av
  `test_repotet_sjalvt_kastar_skrivfel_och_inte_indexerror`. Kontrollen ligger i
  SKRIVFUNKTIONERNA, `spara_referenssvar` och `spara_omdome`, och inte hos
  anroparen: en kontroll hos anroparen är en kontroll någon glömmer.
- **Vad den skyddar mot.** §6. Vyn visar RÅ KUNDTEXT på skärmen, och den texten
  får inte hamna i `docs/`, i ett commitmeddelande, eller i en logg utanför de
  två gitignorerade katalogerna. Utan spärren räcker ett felstavat argument för
  att skriva kundtext till en fil som pushas.
- **Negativkontroll.**
  `tests/test_vy.py::test_de_tva_gitignorerade_katalogerna_slapps_igenom` visar
  att båda de tillåtna katalogerna passerar. En spärr som fäller på allt hade
  gjort vyn oskrivbar och därmed avstängd.
- **Redundant med.** `persondatakontroll`, men bara delvis och för sent: den
  fäller vid commit, alltså efter att texten redan skrivits till disk. Den här
  fäller före skrivningen.

| Fälld rad | Utfall | Form |
| --- | --- | --- |
| `if relativ.parts[:1] != ("data",) and ... != ("logg",):` satt till `if False:` | RÖD, `4 failed, 41 passed` | neutraliserad |
| `krav_pa_skrivbar_sokvag(parfil)` i `spara_referenssvar`, ENSAMT | RÖD, `1 failed, 44 passed` | raderad |
| `krav_pa_skrivbar_sokvag(omdomesfil)` i `spara_omdome`, ENSAMT | RÖD, `1 failed, 44 passed` | raderad |

Sviten var `tests/test_vy.py` med 45 test, samma som ovan.

**DE TVÅ ANROPEN FÄLLS VAR FÖR SIG, ALDRIG TILLSAMMANS, och det är ett fynd och
inte en formsak.** Skiva 27:s första prövning fällde båda i samma körning, fick
RÖD, och skrev in det som ett belägg för att båda var vaktade. Det var falskt:
`krav_pa_skrivbar_sokvag(omdomesfil)` gick att RADERA HELT med hela sviten grön,
alltså var raden vakuös och §6 obevakad på vägen genom `spara_omdome`. Funnet av
§7-granskningen av skiva 27, varv 1, och stängt med
`test_omdome_kan_inte_loggas_utanfor_logg`.

**Mekanismen är §7.1:s klausul om lagrat försvar, SPEGELVÄND.** Klausulen varnar
för att en ofullständig fällning ger falskt VAKUÖST. Här gav en SAMMANSLAGEN
fällning falskt ÄKTA: ett rött utfall bevisar bara att MINST EN av de fällda
raderna är bärande, aldrig att alla är det. Fäll varje verkställighetspunkt
ensam.

**LÄS DETTA FÖRE NÄSTA PRÖVNING AV DEN HÄR SPÄRREN.** Testerna som påstår att
skrivningen inte sker pekar på sökvägar under `tmp_path`, aldrig på riktiga
sökvägar i repot. Skälet är att prövningen enligt §7.1 fäller spärren och kör
sviten: med en riktig sökväg går skrivningen då igenom på riktigt, och prövningen
av spärren blir själv det spärren finns för att förhindra.

Det inträffade i skiva 27. Första fällningen av villkoret lämnade efter sig en
`docs/x.jsonl` med två poster i arbetsträdet, som `git status` fångade inför
committen. Filen bar fixturtext och ingen kundtext, alltså kostade det ingenting;
med en post ur `data/par.jsonl` i fixturen hade det varit ett §6-brott begånget av
granskningen själv. Testet skriver nu i `tmp_path`, och fällningen gjordes om med
samma verdikt och utan filrest.

---

## LUCKA UTAN SPÄRR: `gmail-etikett-som-ensam-grund`

> **DET HÄR ÄR INTE EN SPÄRR OCH GÅR INTE ATT FÄLLA ENLIGT §7.1.** Ingen kod
> implementerar den. Posten står i det här dokumentet därför att den vaktar samma
> sorts fel som spärrarna, och därför att den som läser dokumentet före en
> prövning ska se den.
>
> **Mot mallens fyra fält:** *Spärr* är den inte, se rubriken. *Vad den skyddar
> mot* står som **Vad den vaktar** nedan. **Negativkontroll: ingen finns**,
> eftersom det inte finns någon kod att pröva; vad som skulle krävas för att ge
> den en står under *Vad som skulle göra den till en spärr*. **Redundant med:
> ingen.**

**EN GMAIL-ETIKETT FÅR ALDRIG VARA ENDA GRUNDEN FÖR EN KLASSNING.** Regel av Lars
i skiva 15, se `docs/beslutslogg.md` #27.

Etiketter sätts för hand av Lars och Matte, retroaktivt och ojämnt. **Ett mail
utan etikett är inte ett mail utan ärende.** En etikett får användas som
bekräftande signal och som säker positiv träff, aldrig som nödvändigt villkor och
aldrig som ensam grund.

- **Vad den vaktar.** Att en klassning tar en etikett för ett sakförhållande. En
  etikett säger vad någon HAR MARKERAT, inte vad som ÄR. De två sammanfaller så
  ofta att skillnaden inte märks förrän den kanal dyker upp där de går isär.
- **UPPMÄTT INSTANS, skiva 15.** Miningen delade materialet med Gmail-queryn
  `in:sent`, alltså på etiketten `SENT` som ensam grund. En tråd hamnade i
  `data/tradar.jsonl`, "besvarade", om den innehöll ett skickat meddelande.

  **Webbformuläret skickar från brevlådan.** Varje formulärnotis bär därför `SENT`
  och matchade `in:sent`, oavsett om någon svarat. Obesvarade-skörden kördes
  dessutom som `-in:sent` minus redan hämtade tråd-ID, så samma trådar var
  utestängda även därifrån.

  Uppmätt med `scripts/besvarad-omklassning.py`: av 555 trådar i besvarade-skörden
  bär **139** ett mänskligt svar enligt `urval.ar_gmail_svar`. **92 är
  kundärenden utan svar**, och de bidrar med **66 kundtexter som saknas i BÅDA
  kolumnerna** i `docs/kategorier-forslag.md`.
- **Vad som INTE var fel.** Kolumnen *Med svar* tas ur `data/par.jsonl`, som
  byggs på `ar_gmail_svar` via `src/extract.py` (`src/kategorisera.py` rad 84–93).
  Den var alltså riktig hela tiden. Felet låg i att den obesvarade sidan bara
  hämtades ur den ena filen, så trådar utan svar i fel skörd räknades i ingen
  kolumn.
- **Andra etiketter som används som villkor i dag.** `urval.ar_gmail_svar` kräver
  `SENT` för att ett meddelande ska räknas som svar, och `ar_kundmeddelande`
  läser samma fält. Det är SYSTEMSATTA etiketter och inte handsatta, vilket är
  skillnaden regeln vilar på: `SENT` säger sanningsenligt att brevlådan skickade
  meddelandet. Felet uppstod inte av att `SENT` lästes, utan av att `SENT` fick
  betyda "besvarad".

  Materialet bär 13 distinkta handsatta etiketter, avlästa med
  `scripts/formular-matning.py`, som räknar PER TRÅD och tar med varje etikett i
  tråden. Den som följer formuläret, `Label_4067421502860552187`, bärs av 89
  trådar, varav 76 av de 78 formulärtrådarna.

  **Ingen kod läser något etikett-ID.** `grep -rn "Label_" src tests config` ger
  exit 1, alltså noll träffar. Den enda kod som rör etiketterna alls är
  mätskriptet, som räknar dem på prefixet och aldrig på ett enskilt ID. Det är
  rätt läge: regeln tillåter dem som bekräftande signal, aldrig som villkor.

  > Meningen ovan söker i `src`, `tests` och `config` och räknar INTE upp var
  > träffarna ligger i `docs/`. En sådan uppräkning blir falsk av nästa
  > appendixpost som nämner ett etikett-ID, alltså ofta av just den commit som
  > skriver den. En tidigare lydelse här gjorde precis det. Se CLAUDE.md §7.2.
- **Vad som skulle göra den till en spärr.** En kontroll som vägrar en klassning
  vars enda indata är ett fält ur `labelIds`. Den finns inte, och skulle vara
  svår att formulera utan att också fälla de legitima systemetikettsläsningarna
  ovan. Tills vidare är det här en regel som en granskare bär, inte kod.

---

## LUCKA UTAN SPÄRR: `versalkansligt-monster-i-avlasare`

> **DET HÄR ÄR INTE EN SPÄRR OCH GÅR INTE ATT FÄLLA ENLIGT §7.1.** Avläsaren i
> fas 4.5 finns inte ännu, så det finns ingen kod att pröva. Posten står här för
> att luckan ska vara känd INNAN koden skrivs, vilket är enda tillfället då den
> går att undvika i stället för att upptäckas.
>
> **Mot mallens fyra fält:** *Spärr* är den inte. *Vad den skyddar mot* står som
> **Vad den vaktar**. **Negativkontroll: ingen finns**, eftersom det inte finns
> någon kod att pröva; vad som skulle krävas står under *Vad som skulle göra den
> till en spärr*. **Redundant med: ingen.**

**ETT MÖNSTER SOM LÅNAS UR §6-KONTROLLEN ÄRVER DESS VERSALKÄNSLIGHET.**
Registrerad i skiva 16 på Lars beslut, se `docs/beslutslogg.md` #28.

- **Vad den vaktar.** Att en avläsare i sändvägen tappar giltig kundinmatning
  därför att den ärvt en stränghet som fanns av ett helt annat skäl.
  `scripts/persondatakontroll.py` bär mönstret
  `\b[A-ZÅÄÖ]{3}[\s-]?\d{2}[A-ZÅÄÖ0-9]\b`. Att det är VERSALKÄNSLIGT är avläst
  ur filen; att det är det med avsikt står inte utskrivet där och är en
  slutsats. Skälet håller ändå: en §6-kontroll som larmar skiftlägesokänsligt
  larmar på vanliga ord i löptext, och filens egen kommentar om postnummer visar
  samma avvägning. Samma stränghet i en AVLÄSARE är däremot ett fel, eftersom
  **inte alla kunder skriver versalt**: 46 av de 77 läsbara fältvärdena matchar
  det versalkänsliga mönstret, alltså gör en majoritet det och 31 gör det inte.
  En avläsare måste bära båda.
- **UPPMÄTT INSTANS, skiva 15.** Mot webbformulärets fältvärde ger mönstret 46 av
  78 versalkänsligt och 77 av 78 skiftlägesokänsligt. **En fältavläsare som ärver
  strängheten tappar alltså 31 av de 77 nummer som går att läsa.** Avläst med
  `scripts/formular-matning.py`, som skriver ut båda varianterna.
- **Varför den är en sändvägsdefekt.** Ett tappat registreringsnummer betyder att
  fordonsuppslaget inte kan göras, att gatingen faller till `utkast`, och att
  kunden väntar på en handpåläggning som ärendet inte behövde. Ingen spärr fälls,
  inget larm går, och utfallet ser ut som försiktighet.
- **VARFÖR DEN INTE SYNS I TEST.** Testdata skrivs av den som skriver koden, och
  den skriver versalt. Kunden skriver det som faller ur tangentbordet. Ett test
  som bara matar in versala nummer är grönt för alltid, och det är därför luckan
  slår först i drift. Ett test för den avläsare den här posten gäller måste bära
  ett gement och ett blandat nummer, annars är det vakuöst i §7.1:s mening utan
  att se ut så.

  *Här stod ett utskrivet exempelnummer, och `persondatakontroll` fällde posten
  på det. Spärren hade rätt: §6 säger att registreringsnummer aldrig förekommer i
  `docs/`, och en läsare kan inte se att ett nummer är påhittat. Att lägga det i
  `TILLATNA` hade varit fel av samma skäl som mönsterkommentaren anger för
  postnummer: undantaget hade släppt igenom ett framtida RIKTIGT nummer som råkar
  vara detsamma. Meningen säger nu vad exemplet visade i stället för att visa det.*
- **UPPMÄTT INSTANS, skiva 19: SAMMA STRÄNGHET ÅT ANDRA HÅLLET.** Versalkänsligheten
  har en följd för `docs/` som inte stod här: **§6-kontrollen släpper igenom ett
  registreringsnummer skrivet i GEMENER.** I skiva 19 kom två nummer in i den här
  filen i en och samma rättelsemening. Det VERSALA, ett påhittat testnummer, fälldes
  av `scripts/persondatakontroll.py`. Det GEMENA, som var ett verkligt fordons
  nummer, passerade kontrollen utan larm och hittades först av en manuell
  skiftlägesokänslig sökning. Båda är borta nu.

  **Följden: en grön `persondatakontroll` är inget bevis för att §6 hålls.** Kör
  före commit också `grep -rniE '\b[A-ZÅÄÖ]{3}[[:space:]-]?[0-9]{2}[A-ZÅÄÖ0-9]\b'`
  **med de stagade filerna som uttryckliga sökvägsargument**, och läs träfflistan
  för hand.

  **Sökvägsargumenten är inte valfria.** Utan dem söker kommandot hela trädet,
  `.venv/` inräknat, och gav i skiva 19 **8 361 rader**. Med skivans sex
  stagade filer som argument gav samma mönster **38 rader**, en lista
  som går att läsa för hand. *Här föreskrevs kommandot tidigare utan
  sökvägsargument.*

  **BÅDA TALEN ÄR MÄTTA EFTER ATT ALL TEXT I POSTEN VAR SKRIVEN.** De tal som
  först stod här mätte ett tidigare skede och föråldrades av rättelsemeningarna
  själva, som lade till egna träffrader i den här filen. Brusexemplen nedan är
  en del av bruset. En uppgift om antal träffar i filer som uppgiften själv
  ändrar måste mätas sist av allt.

  Den bullrar även då, och brusets dominerande klass är **ett treställigt ord följt
  av ett mätvärde**: `mot 555`, `Max 750`, `och 371`, `ver 795`, `rad 252`. Ordet
  `sha256` ger fyra träffar. *Här stod tidigare att den bullrar på sha256-SUMMOR.
  Det är fel: i de sex filerna finns NOLL 64-teckens hexsträngar, och de fyra
  träffarna kommer av ordet i löptext.* Bruset är just den bräddning som motiverar
  att skriptets eget mönster är strängt.

  **Att därför göra skriptets mönster skiftlägesokänsligt föreslås inte här**, av
  skälet i punkten ovan; det vore ett beslut för Lars och inte för en granskare.
- **Vad som skulle göra den till en spärr.** Att avläsaren i fas 4.5 kompilerar
  sitt mönster med `re.IGNORECASE` och bär ett test med gement indata.
  Föreskriften ligger i `docs/roadmap.md` fas 4.5. Tills koden finns är detta en
  regel som en granskare bär, inte kod.
- **Räckvidden är inte bara det här mönstret.** Regeln är generell: ett mönster
  som lånas ur en kontroll vars syfte är att INTE larma för brett får inte
  användas oförändrat där syftet är att INTE missa. `scripts/formular-matning.py`
  visar formen, den håller `REGNR_STRIKT` och `REGNR` isär och skriver ut båda.

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

### 0.26.0 — 2026-09-04

Skiva 28. En full §7-omgång på skiva 27:s självmätta rättelser, alltså på den kod
som skrevs efter att grinden var förbrukad och som ingen annan hade sett.
Omgången UNDERKÄNDE dem.

**KLAUSULEN OM LAGRAT FÖRSVAR BÄR NU BÅDA RIKTNINGARNA**, i rutan överst.
Klausulen har sedan skiva 5 sagt att för få fällda lager ger falskt VAKUÖST.
Skiva 27 visade motriktningen: en SAMMANSLAGEN fällning av flera rader ger RÖD,
och det läses som att alla bär när bara den ena gör det. Instansen är mätt och
utskriven. Skillnaden mellan LAGER, som fångar samma fall, och
VERKSTÄLLIGHETSPUNKTER, som var och en vaktar sin väg, avgör vilken riktning som
hotar. Beslut av Lars i skiva 28.

**SÄNDVÄGSSPÄRREN LÄCKTE FORTFARANDE, en systerform bort.** Skiva 27:s rättelse
stängde `from . import auth` och lämnade `from .auth import bygg` öppen, eftersom
uttrycket frågade efter `nod.module` i stället för efter `nod.level`. Spärren
fick `auth` i stället för `src.auth`. Villkoret frågar nu efter nivån, och de
fyra importformerna har ett test var.

**ESCAPNINGEN VAR INTE STÄNGD SOM KLASS, trots att den påstod sig vara det.**
Testet räknade upp de fält som fanns när det skrevs. Granskningen renderade ett
befintligt men ouppräknat `Fall`-fält oescapat och fick hela sviten grön. Fälten
härleds nu ur `Fall` och parametrarna ur `inspect.signature`.

**Ett andra vakuöst led hittades i samma funktion**, `i_modul` i
`moduler_i_vyn`, och stängdes. Efter den rättelsen blev det andra argumentet
grönt vid fällning, alltså inkonklusivt, och ett test skiljer nu de två åt.

**Tre kända falskheter strukna på plats i 0.25.3**, med not där de stod: att
`nod.module` är None för varje relativ import, att escapningen var stängd som
klass, och att varv 3 fann fyra ovaktade platser. Det var sex, avläst ur
`git grep -n "html.escape" e16be28 -- src/vy.py`.

**LUCKA 16 ÄR MÄTT i stället för namngiven**, i ett eget avsnitt: rutterna,
`_index_ur_vag`:s faktiska utfall per väg, och vad ett fel skulle betyda. Det
sista är inte en krasch utan ett referenssvar sparat mot FEL inkommande mail,
alltså ett felaktigt träningsunderlag för rösten. Beslut av Lars i skiva 28.

**Varje tal i varje tabell är omkört mot 45 test.**

Ny klausul, ny lucktext och stängda hål ⇒ MINOR.

### 0.25.3 — 2026-09-04

**ÄNDRINGARNA HÄR ÄR GJORDA EFTER ATT §7:s TRE VARV VAR FÖRBRUKADE. De är
SJÄLVMÄTTA och inte oberoende granskade.** Varv 3 underkände skivan på ett
blockerande fynd. §7 säger att arbetet då ska stoppas och rapporteras öppet, och
det är gjort: beslutet om skivan ligger hos Lars. Att stänga hålet i stället för
att lämna det öppet sänker inget krav, men det byter granskad kod mot ogranskad,
och därför står det utskrivet här.

**Sändvägsspärren såg inte relativa importer.** `from . import auth` gav en TOM
mängd: villkoret krävde `nod.module`. `src/__init__.py` finns, så formen är
giltig, och en enda rad hade dragit in `src/auth.py`. Stängt med `_paket`, som
löser nivån mot modulens eget namn och lämnar tomt när det inte går. Två test,
ett för formen och ett för nollfallet.

*Här stod att `nod.module` är None "för varje relativ import". Struket som känt
falskt: `from .auth import bygg` är relativ och bär `module` lika med `auth`.
Den premissen var dessutom skälet till att rättelsen lämnade den formen öppen.
Fällt av §7-granskningen av skiva 28, se 0.25.4.*

**Escapningen stängdes som instanser.** Varv 2 stängde en ovaktad
`html.escape`, och varv 3 stängde de övriga. `rendera_fel` är utbruten ur
`do_POST` för att escapningen av POST-data ska gå att pröva alls.

*Här stod att escapningen var "stängd som KLASS, inte som instans" och att varv
3 fann "fyra till". Båda struket som känt falskt: testet räknade upp de fält som
fanns när det skrevs, alltså föll det inte av ett nytt fält, och de ovaktade
platserna var sex. Klassen stängdes först i skiva 28. Fällt av
§7-granskningen av skiva 28, se 0.25.4.*

**Ett test mätte att en metod FANNS, inte att den tiger.**
`test_servern_loggar_inte_vad_lars_laser` anropar nu `log_message` med stderr
fångad.

**Lucka 16 registrerad:** HTTP-lagret är otestat. **Ett känt falskt påstående
struket:** att inget test använde formen `from paket.modul import namn`.
`tests/test_vy.py` bär den sedan `8e369ce`. Och ett led preciserat: `snippet`
finns på alla 1604 trådar men är tomt på fem.

**Varje tal i varje tabell är omkört mot 41 test.**

Stängd lucka, ny lucka, omkörda tal ⇒ PATCH.

### 0.25.2 — 2026-09-04

Rättelser efter §7-granskningen av skiva 27, varv 2. **Varv 1:s rättelser bar
själva två fynd**, vilket är precis vad `docs/incidentlogg.md` I10 säger att man
ska räkna med.

**ETT ANDRA VAKUÖST LED I SÄNDVÄGSSPÄRREN.** `namn.add(nod.module)` gick att
radera med hela sviten grön, alltså följde vandringen inte kedjan för formen
`from paket.modul import namn`. Det är samma defektklass som varv 1:s B1, i
samma fil, och den hittades av samma systematiska sökning efter rader som går
att fälla utan att något blir rött. Stängt.

**Docstringen påstod att ledet var uppmätt av ett test som mätte den ANDRA
halvan.** Rättat, med båda formerna och båda testen utskrivna.

**TRE OVAKTADE §6-RADER, alla i vyns kod.** Bindningen till `127.0.0.1`,
övertäckningen av `log_message`, och `html.escape` i `rendera_granskning`. Alla
tre åberopas i kommentarer eller docstrings som skäl att lita på vyn, och ingen
av dem hade ett test. Bindningen är den tyngsta: vyn saknar inloggning, så den
som når porten når kundtexten.

**Tabellerna bär nu fyra rader till, och varje tal är omkört** mot de 37 test
`tests/test_vy.py` bär efter rättelserna.

Nya rader i tabellerna och omkörda tal ⇒ PATCH.

### 0.25.1 — 2026-09-04

Rättelser efter §7-granskningen av skiva 27, varv 1.

**Ett spärrtest var vakuöst, och det var min sammanslagna fällning som dolde
det.** `krav_pa_skrivbar_sokvag(omdomesfil)` i `spara_omdome` gick att radera
helt med hela sviten grön. Posten
`vyn-skriver-bara-till-data-och-logg` redovisade en fällning av BÅDA anropen som
RÖD, vilket bara bevisade att minst ett av dem var bärande. Tabellen redovisar nu
de två anropen var för sig, och stycket under den skriver ut mekanismen: §7.1:s
klausul om lagrat försvar, spegelvänd.

**Tre kända luckor registrerade, ingen stängd.** Lucka 13, spärrens två
uppräkningar är inte en egenskap. Lucka 14, `scripts/kor-vy.py` ligger utanför
den granskade grafen fastän det är den som startar vyn. Lucka 15, #40 säger
OAVSETT LÄGE medan `rendera_referens` saknar `sparr`.

**Skälet att registrera i stället för att stänga:** lucka 15 kan inte stängas
meningsfullt innan generatorn finns, eftersom urvalet då behöver veta vilka
poster som är fällda, och lucka 13 är samma riktning som lucka 12 hade före
skiva 25. Att skriva ut dem är det §7.2 kräver av en post som annars låter
heltäckande.

Nya luckor och en rättad tabell ⇒ PATCH.

### 0.25.0 — 2026-09-04

**TRE NYA SPÄRRPOSTER, alla BYGGDA i skiva 27 och ingen PLANERAD.**

- **`vyn-har-ingen-sandvag`**, två lager, och prövningen fällde dem både var för
  sig och tillsammans. Skälet att fälla båda står i §7.1: ett lagrat försvar ger
  falskt vakuöst om bara det ena lagret fälls.
- **`spärrfälld-post-utan-textfalt`**, Lars beslut i `docs/beslutslogg.md` #40.
- **`vyn-skriver-bara-till-data-och-logg`**, §6 verkställd i skrivfunktionen.

**Översiktstabellen bär de tre.** Den läses före varje prövning enligt §7.1, och
en spärr som saknas där fälls inte av den som följer listan.

**Ett fynd som spärren gjorde mot sig själv står utskrivet i posten.**
Källtextlagret fällde `src/vy.py` på modulens EGEN KOMMENTAR, som namnger
`messages().send` för att förklara vad som är förbjudet. Det är samma fälla som
rutan överst i det här dokumentet varnar för, den här gången i kod i stället för
i ett dokumenterat radnummer. Lagret läser nu källan med kommentarer och strängar
borttagna.

Tre nya spärrposter ⇒ MINOR.

### 0.24.0 — 2026-09-04

**SPÄRREN MOT MARKUP I ETT VÄRDE MÄTER SEDAN NU EN EGENSKAP, INTE EN HÄNDELSE.**
Beslut av Lars, `docs/beslutslogg.md` #35. Villkoret är att **värdets råa
källtext ska vara identisk med dess textnoder**. Är den inte det innehöll värdet
markup, oavsett sort.

**LUCKA 12 ÄR STÄNGD.** Kravet att stängningen ska vara värdets EGEN sluttagg är
inte ett femte villkor i en lista utan samma egenskap tillämpad där den inte GÅR
att mäta: stängs fältet av något annat är värdets utsträckning okänd.

**VARJE LYDELSE FÖRE DEN HÄR BESKREV EN HÄNDELSE, och de föll på en händelse
ingen tänkt på**, var för sig: starttaggar, sedan kommentar och processing
instruction och declaration och ensam sluttagg, sedan `TOMMA_TAGGAR`-grenens
tidiga return, sedan träffgrenen. **En händelselista går alltid att utöka med en
post till.** *Här summerades lydelserna och fällningarna i en bisats, i samma fil
som noten i lucka 11:s post stryker just den formen. Fällt av granskningsvarv 2.
*Avståndet stod först utskrivet som ett radantal, vilket är en mening som räknar
sin egen omgivning och föråldras av nästa appendixpost.*
Jämförelsen går inte att utöka: den frågar inte VAD som stod i värdet, bara om
värdets text är hela värdet.

**FYRA METODER ÄR BORTTAGNA UR KODEN**, `handle_comment`, `handle_pi`,
`handle_decl` och `unknown_decl`, tillsammans med `_markera_markup` och
`_i_varde`. Samma fall fälls fortfarande, uppmätt form för form: det är därför
borttagningen inte är en uppmjukning.

**ENTITETER ÄR INTE MARKUP, och det är gränsen som gör spärren användbar.**
`convert_charrefs` gör `&nbsp;` till ett hårt blanksteg i textnoden, så råtext och
textnod skiljer sig på varje entitet. Jämförelsen görs efter `unescape`, samma
funktion `html.parser` själv använder. Utan det ledet hade källans eget
sifferformat kastat: en fällning som tar bort `unescape` ur jämförelsen ger
**`2 failed, 212 passed`**, och de två röda är
`test_format_som_sidan_faktiskt_anvander_lases[2&nbsp;400 kg-2400]`, som är äldre
än skivan, och `test_entitet_i_ett_varde_ar_inte_markup`.

*Här stod att mutationsrad 25 mäter vad det ledet kostar, med talet 115. Rad 25
mäter något annat, nämligen att vända jämförelsens riktning. Talet var avläst men
hängt på fel fällning. Fällt av granskningsvarv 2.*

**EGENSKAPEN GÅR ATT MÄTA MED `html.parser`, alltså krävdes inget nytt
beroende.** `getpos()` ger positionen för den konstruktion som hanteras, och
`get_starttag_text()` ger starttaggen precis som den står i källan. Läsaren bär
källtexten och en tabell över radstarter, och räknar om `(rad, kolumn)` till ett
index. DEL B:s fråga är därmed besvarad med nej: ingenting saknas.

**MUTATIONSTABELLEN ÄR OMMÄTT MOT BASLINJEN 214 och utökad till tjugofem rader.**
Rad 23, 24 och 25 är nya, rad 22 gick från 14 till 17 röda, och rad 6 från 134
till 138. Rad 23:s plats bar tidigare ett villkor som inte finns kvar.

**ETT OBUNDET VILLKOR ÄR BORTTAGET UR `_varde_bar_markup`.** Granskningen fällde
`if self._varde_start is None: return True` som ovärderbar: både en fällning och
en injicerad `AssertionError` på raden gav GRÖN, alltså nådde inget test grenen.
Skälet står i metodens docstring, och valet är detsamma som för det borttagna
`_vantar`-villkoret: ett villkor som ser ut som försiktighet utan att kunna göra
något binds eller tas bort.

En stängd lucka, en spärr som bytt metod och en ommätt tabell ⇒ MINOR.

### 0.23.0 — 2026-09-03

**LUCKA 11 ÄR DELVIS STÄNGD GENOM KAST.** Beslut av Lars, `docs/beslutslogg.md`
#34. Ett värde vars text är avdelad av något som inte är text går inte att tolka,
och `if bar_element:` i `_las_falt` kastar. **Den återstående vägen är lucka 12**,
uppmätt av granskningens tredje varv och registrerad öppen. Ingenting saneras: att plocka bort tecken
ur ett värde vore att ändra ett tal vi skickar vidare.

*Föråldrad av 0.24.0: lucka 12 är stängd, så meningen ovan gäller läget när den
skrevs och inte i dag. Posten skrivs inte om, eftersom en committad appendixpost
rättas genom en ny versionspost.*

**SPÄRRENS FÖRSTA LYDELSE FÖLJDE BARA STARTTAGGAR, och granskningen fällde den.**
En HTML-kommentar, en processing instruction, en declaration och en ENSAM sluttagg
gav alla `7501` på en sida vars verkliga släpvagnsvikt är 750 kg, alltså samma
defekt genom fyra andra dörrar, och alla fyra vände dragfordonsbeskedet.

**RÄTTELSEN GJORDE OM SAMMA FEL och fälldes i varv 2.** Den följde varv 1:s
uppräkning i stället för egenskapen, och missade att `handle_endtag` returnerar
för `TOMMA_TAGGAR` före den gren rättelsen la in: `750</br>1 kg` gav fortfarande
7501. Flaggan sätts nu från varje nodtyp som avdelar en textnod, se
`_markera_markup`.

**Luckan var öppen i två committade versioner**, `8629223` och `52d0a97`. Den
infördes av parsern i skiva 22 och kom fram först när skiva 23 tittade på
fotnotselement i etiketter. Det är postens tydligaste belägg för att en prövning
som bara följer skivans egen ändring inte räcker.

*Här stod `0863a8e` i stället för `52d0a97`, alltså fel commit i just det led
posten kallar sitt tydligaste belägg. `0863a8e` är skiva 21 och läser värden med
regex, och `git grep -n "class _Faltlasare" 0863a8e -- src/biluppgifter.py` ger
noll träffar. Fällt av granskningen av skiva 24.*

**SPÄRREN SITTER I `_las_falt` OCH INTE I PARSERN.** Den skarpa sidan bär värden
med nästlad markup i fält vi aldrig läser, `Chassinr / VIN` är det avlästa
exemplet, och en spärr i parsern hade kastat på varje verkligt svar.

**SKIVA 22:S UPPMJUKNING ÄR DELVIS ÅTERTAGEN, och det ska sägas rakt ut.** Två av
de sex markupändringar som skiva 22 gjorde läsbara rör VÄRDET och kastar nu.
`test_markupandring_lases_av_parsern` bär fyra fall i stället för sex. De fyra som
står kvar kan inte ändra ett tal; de två som togs bort kunde.

**`750 kg<sup>1</sup>` gav förut utkast och kastar nu.** Utfallet är fortfarande
att inget värde kommer ut, men skälet är ett annat.

**LUCKA 10 ÄR REGISTRERAD SOM ÖPPEN SÄNDVÄGSLUCKA, inte som kantfall.** Beslut av
Lars. Riktningen står utskriven: den som släpper ut ett värde. **Formen är uppmätt
i fixturen**, `Släp totalvikt (B)` och `Släp totalvikt (B+)` skiljer sig bara på
`+`, men ingen av dem är ett fält vi läser, så formen finns utan att bita i dag.

**MUTATIONSTABELLEN ÄR OMMÄTT MOT BASLINJEN 210.** Rad 22 och 23 är nya och fäller
lucka 11:s spärr på var sitt led, kastet respektive flaggningen. Skiva 23:s rad 22,
som fällde värdevägen i `_stang_faltet`, ger nu GRÖN både ensam och i
dubbelfällning: spärren kastar innan värdets text spelar roll. Villkoret står kvar
i koden men är inte längre ett lager, och det står utskrivet under tabellen. Rad 6
och 19 ändrade tal av skivans egna test.

**LUCKA 12 TILLKOMMER OCH ÄR ÖPPEN.** Granskningens tredje varv mätte upp att
`handle_endtag`:s träffgren klipper värdets text utan att flagga. Skivan stannade
där: §7:s tre varv var slut, och de två föregående rättelserna av samma spärr var
båda fel på samma sätt, så en tredje självmätt spärrändring skrevs inte.

**SPÄRRENS TRE MISSAR HAR SAMMA FORM, och det är postens lärdom.** Varje lydelse
beskrev en HÄNDELSE i stället för egenskapen den skulle vakta: *ett element
öppnas*, sedan *en av fyra namngivna nodtyper*, sedan *en nodtyp som inte är en
tagg*. Egenskapen är hela tiden densamma: *värdets text är inte sammanhängande*.

En delvis stängd lucka, två luckor registrerade som öppna, en delvis återtagen
uppmjukning och en ommätt tabell ⇒ MINOR.

### 0.22.0 — 2026-09-03

**ETT FELLÄST FÄLT SER INTE LÄNGRE UT SOM ETT SAKNAT.** Beslut av Lars, skiva 23.
`_tal` KASTAR när värdet bär siffror och enheten `kg` men inte går att läsa som
ett tal, och ger `None` bara när fältet inte är en vikt alls. Skiva 22 lät båda
fallen ge `None`, och en källa som slår ihop två vikter i en rad såg då ut precis
som en källa som slutat skriva raden. Kastgrenen är fällning 18 i
mutationstabellen, och `test_vardet_som_inte_ar_viktlikt_utelamnas_i_stallet_for_att_kasta`
bevakar gränsen: `Max 750 kg (Teoretisk)`, som står på sidans egna rader, får
aldrig nå den.

**LUCKA 7 ÄR STÄNGD, STRUKTURELLT.** En fotnotsMARKÖR i ett `FOTNOTSELEMENT`
utesluts ur etikettnodens text, så `Släpvagnsvikt` med fotnot är samma etikett som
utan medan `Släpvagnsvikt obromsad` förblir en annan. Ingen prefixräknare: den
hade kastat på varje verkligt svar, vilket posten mätte upp redan i skiva 22.

**UTESLUTNINGENS FÖRSTA LYDELSE BAR TVÅ SÄNDVÄGSDEFEKTER, båda fällda av
granskningen och båda i den riktning som släpper ut ett värde.** Den tog bort allt
innehåll i ett `sup` eller `small`, och då blev `Släpvagnsvikt<small> obromsad</small>`
till `Släpvagnsvikt`, medan hela namnet inuti elementet blev en TOM etikett som
räknaren inte såg. Den andra är lucka 7 själv, återöppnad av sin egen rättelse.
Villkoret är därför att markören saknar bokstäver, och rad 21 i mutationstabellen
fäller precis den första lydelsen.

**Varje prövad form av defekt 1 kastar, fotnotsformen inräknad.** Formerna är
uppräknade per rad i `test_dubblett_dar_etiketten_bar_annan_markup_kastar`,
`test_dubblett_dar_ena_etiketten_bar_attribut_kastar_anda`,
`test_dubblett_med_annat_skiftlage_i_klassvardet_kastar`,
`test_dubblerad_draganordning_kastar_i_stallet_for_att_valja`,
`test_dubblett_dar_ena_etiketten_bar_fotnot_kastar` och
`test_hela_namnet_i_ett_fotnotselement_gor_inte_etiketten_osynlig`.

**Att ÖVERHOPPNINGEN inte är för bred bärs av två test, och de påstår olika
saker.** `test_overhoppningen_tar_slut_och_falten_efter_lases` ger VÄRDE: ett fält
som står efter ett överhoppat element läses. `test_inaktivt_falt_lases_inte` ger
UTKAST: ett fält som bara står inuti ett inaktivt block läses inte. Det senare kan
per konstruktion aldrig ge värde, eftersom `utfallet_av` kastar om ett uppslag
kommer ut.

**FOTNOTSUTESLUTNINGENS gräns bärs av andra test**, nämligen de som blir röda
under fällning 21: `test_ord_i_fotnotselementet_ar_en_del_av_namnet` och
`test_hela_namnet_i_ett_fotnotselement_gor_inte_etiketten_osynlig`. *Här stod
`uteslutningen` om de två överhoppningstesten. Ordet är i den här posten reserverat
för fotnotsuteslutningen, och meningen blev därför falsk om de test den namngav.
Fällt av granskningsvarv 3.*

*Här stod "Elva former av defekt 1 kastar nu, mot tio före skivan". Båda talen
räknade instanser av ett mönster utan att någon lista i repot bar dem, vilket
§7.2 förbjuder, och det ena var dessutom fel: fotnotsformen prövas mot både `sup`
och `small`, alltså två parametrar och inte en.*

*Rättelsen bar SJÄLV tre fel, fällda av granskningsvarv 2 i samma stycke som
strök talen. Den skrev att "de tre negativkontrollerna ger fortfarande värde" och
namngav `test_inaktivt_falt_lases_inte` som en av dem. Det testet ger UTKAST och
inte värde; dess sida bär ingen dubblett utan ett enda inaktivt fält; och "de
tre" var en ny instansräkning i den mening som stryker en instansräkning. Båda
testen är nu beskrivna var för sig, med vad de faktiskt påstår.*

**LUCKA 9 TILLKOMMER, och den går inte att stänga.** Två hopklistrade tal som
landar under den övre rimlighetsgränsen har samma form som en tusengruppering.
`1 200 kg` och `750 400 kg` går inte att skilja åt i tecknen. Skyddet ligger i
intervallet och inte i formen, alltså i en gräns och inte i ett bevis.

**LUCKA 10 TILLKOMMER OCKSÅ, och den är fotnotsuteslutningens egen kostnad.**
Ett `sup` eller `small` vars text saknar bokstäver behandlas som markör, oavsett
om källan menade en markör eller ett betydelsebärande suffix. En SKILD etikett
med ett icke-alfabetiskt led normaliseras därmed in i vår, och dess tal blir
vårt fält. Uppmätt genom `slag_upp` och registrerad i stället för stängd:
alternativet är att inte utesluta något, vilket är lucka 7 tillbaka.
Granskningsvarv 2 fällde skivans påstående att bara mängden återstod.

**`www` GODTAS SOM SAMMA VÄRD.** Beslut av Lars. Skiva 22:s strikthet var säker i
riktningen men producerade ett fel som inte syns: börjar källan skriva `www` i
sin canonical faller varje uppslag till utkast, utan larm och utan rött test.
Varje ANNAN domän avvisas fortfarande, `www` eller inte, och
`test_ankaret_provar_hela_urlen` bär det med två nya former.

**LUCKA 5 OCH 8 ÄR AVGJORDA SOM LUCKOR.** Lars beslut är att rimlighetsgränsen 1
till 9999 står, och att den semantiska omdöpningen lämnas öppen därför att en
kontroll mot ett fjärde fält inte är värd komplexiteten nu. Båda står kvar
utskrivna, nu som vägda val i stället för öppna frågor.

**MUTATIONSTABELLEN ÄR OMMÄTT MOT BASLINJEN 196 och utökad till tjugotvå rader.**
Rad 9 bytte formulering av skivans egen ändring, rad 15 av att tabellen bar ett
namn som aldrig funnits i koden. Rad 18 till 22 är nya. Nedströmsraden i
`src/fordonsuppslag.py` gav `52 failed, 144 passed`. Samtliga rader är RÖD.

**Granskningsvarv 2 körde om samtliga rader mot baslinjen 196 och fick tal för tal
detsamma**, nedströmsraden inräknad. Rad 22 tillkom efter det varvet och är därför
självmätt. Ett varv tidigare kördes tabellen mot baslinjen 188, som sedan
flyttades av rättelserna, och den körningen säger ingenting om talen som står nu.

*Här stod att tabellen bär tjugoen rader, att rad 18 till 21 är de nya, och att
talen är självmätta igen efter att baslinjen flyttat. Alla tre leden var falska
när varv 3 läste dem: tabellen bär tjugotvå rader, rad 22 är också ny, och varv 2
körde om talen vid 196 och inte vid 188. Posten motsade dessutom sin egen brödtext
på två ställen.*

**ETT FÖRÅLDRAT NAMN ÄR RÄTTAT PÅ TVÅ STÄLLEN.** `_vantar_niva` finns inte i
koden och har aldrig funnits i en committad version av modulen:
`git log --all -S "_vantar_niva" -- src/biluppgifter.py` ger noll committar.
Föräldern jämförs på identitet genom `_vantar_foralder`. Namnet stod i
grep-tabellen för parsern och i mutationsrad 15, och den som följde tabellen
hittade ingen rad att fälla.

**GREP-TABELLEN NÅR NU `_behall` OCH `_vard`.** Parserraden bär `def _behall` och
`serie is None`, lager 3:s rad bär `vard.startswith`, båda kontrollerade mot
filen. *Här stod att tabellen pekar på VARJE rad som fälls. Det är fel: rad 21:s
och 22:s villkor står inuti funktioner mönstren pekar på och måste läsas där,
precis som lager 3:s och 4:s förval. Fällt av granskningsvarv 2.*

**LUCKA 11 TILLKOMMER, och den är ÄLDRE än skivan.** Markup inuti ett värde
konkateneras in i talet, så `750<sup>1</sup> kg` blir 7501. Uppmätt identiskt mot
`8629223` och mot arbetsträdet, alltså infört av parsern i skiva 22 och bara
funnet nu. Fälld av granskningsvarv 3.

En ny kastgren, en stängd lucka, tre nya luckor varav en äldre än skivan, en
uppmjukad värdjämförelse och en ommätt tabell ⇒ MINOR.

### 0.21.0 — 2026-09-03

**`fordonsfakta-ur-sida` LÄSER SIDAN MED EN PARSER I STÄLLET FÖR MED REGEX.**
Beslut av Lars, `docs/beslutslogg.md` #32, efter att skiva 21:s granskning lämnat
två sändvägsdefekter öppna. `html.parser` ur standardbiblioteket; inget nytt
beroende, och frågan om ett sådant ställdes i briefen och besvarades med en
mätning.

**DE TVÅ ÖPPNA DEFEKTERNA ÄR STÄNGDA, och båda upphör av konstruktionen.**

- En dubblerad etikett där ena förekomsten bar ett extra klassord, nästlad markup
  eller ett annat elementnamn räknades förut som EN, och det andra parets 750 kg
  gick ut där 2400 var rätt. Etiketten är nu en NOD, så elementnamn och övriga
  klassord spelar ingen roll.
- Ett fält som låg kvar i `<!-- -->` eller i `<template>` lästes som aktivt. En
  kommentar når aldrig `handle_data`, och `HOPPAS_OVER` hoppar över `template`,
  `script` och `style`.

**FEM DEFEKTER, EN ENDA ORSAK, och det är postens viktigaste rad.** Alla fem som
skiva 21 och dess granskning fann hade samma form: ett uttryck som BESKRIVER
sidans markup tystnar i stället för att kasta när markupen ser annorlunda ut.
Varje rättelse som stannade i regexens värld födde nästa fel. De elva
mutationsfällningarna mot koden hittade ingen av de fem, eftersom koden var
självkonsistent i samtliga fall.

**LUCKA 6 ÄR STÄNGD.** Ankaret prövar hela URL:en, alltså schema, värdnamn och
sökväg, och **två ankare KASTAR** i stället för att lösas tyst med första
träffen. Lager 3 beter sig därmed som lager 2 i samma läge. Granskningen mätte
dessutom upp ett led den ursprungliga luckan inte nämnde: ett ankare på en helt
annan DOMÄN med rätt nummer sist gav också ett uppslag.

**LUCKA 7 OCH 8 TILLKOMMER, båda namngivna i stället för stängda.** Lucka 7 är
fotnoten i etiketten, som gör noden osynlig för räknaren; skälet att den inte
stängs är MÄTT, eftersom en prefixräknare hade kastat på varje verkligt svar.
Lucka 8 är att rimlighetskontrollens övre gräns är SIFFERGRÄNSEN och inte en
kalibrerad personbilsgräns.

**RIMLIGHETSKONTROLLEN ÄR BYGGD OCH ÄR BARA ETT DELVIS MOTMEDEL MOT LUCKA 5.**
Lars brief namnger den som luckans motmedel; posten skriver ut att 750 kg är en
fullt rimlig vikt, så kontrollen släpper igenom exakt det värde lucka 5
producerar. Den fångar den grövre klassen, ett tal som inte kan komma från en
avläsning alls. Att säga något annat vore att stänga en lucka i texten i stället
för i koden.

**FALL 4:S UPPDELNING ÄR INTE LÄNGRE EN ÖPPEN PUNKT.** Lars besked är att
källans eget format ska läsas och att två tal aldrig får bli ett.

**SEX MARKUPÄNDRINGAR LÄSES NU DÄR DE FÖRUT FÖLL.** Posten skrev att alla sex
faller till utkast; det gäller inte längre, och ändringen är avsiktlig. Att
fälla på en kosmetisk markupändring är inte försiktighet utan en spärr som blir
avstängd, och det var samma okänslighet som dolde dubbletterna.

**MUTATIONSTABELLEN ÄR OMMÄTT MOT BASLINJEN 151 och utökad från elva till sjutton
rader.** Sju fällningar bytte formulering, eftersom uttrycken de pekade på inte
finns kvar. Den separata §7.1-tabellen är BORTTAGEN: den dubblerade
mutationstabellen i sju rader och fällde borttagna uttryck i de övriga. Två
tabeller som mäter samma sak mot samma baslinje är två tal att hålla i takt, och
postens egen historik visar vad som händer när de glider isär.

**ETT VILLKOR GAV FALSKT GRÖNT OCH GJORDES ÄKTA I STÄLLET FÖR STRUKET.**
Nivåvillkoret i parsern fälldes ensamt utan att sviten föll, eftersom
föräldrastängningen bar samma spärr. Villkoret vaktar ändå något det andra inte
gör, och `test_varde_pa_annan_niva_paras_inte_med_etiketten` binder det nu.
Risken det vaktar infördes AV ombyggnaden: en parser som bara letar nästa
värdenod är lösare än den regex den ersatte.

Två stängda sändvägsdefekter, en stängd lucka, två nya luckor, en ny
kontroll och en ommätt tabell ⇒ MINOR.

### 0.20.0 — 2026-09-03

Skiva 21 stängdes inte. Lars grindbeslut är att den fortsätter som skiva 22, och
att det som finns committas med statusen utskriven. Den här posten är den
committen; skiva 22:s eget arbete kommer efter den.

**0.19.0-POSTEN FÅR SIN STATUSRUBRIK.** Den redovisade skivan som avslutad medan
tre granskningsvarv var förbrukade och det sista underkände. Rubriken skriver ut
kriterienumren, och skiljer på det som är stängt och det som inte är det: varv 1
och 2:s fynd är rättade i koden, medan **två sändvägsdefekter står ÖPPNA** i fall
5 och fall 6 och är kända, verifierade och committade som sådana.

**§6-STYCKET SKREV SJÄLVT IN TVÅ REGISTRERINGSNUMMER I `docs/`.** Stycket fanns
för att redovisa att ingen persondata följde med fixturen in i repot, och blev
det enda i skivan som fällde repots egen kontroll: `granska()` gav två fynd av
sorten `registreringsnummer`. Numren är påhittade, alltså en falsk positiv, men
**Lars beslut är att de ska UT ur `docs/`, inte undantas.** Ett undantag i
`TILLATNA` gäller exakt strängen och hade släppt igenom ett framtida riktigt
nummer med samma tecken. Samma avvägning som för postnummer i skiva 7.

**SEX PÅSTÅENDEN SOM SKIVANS EGNA ÄNDRINGAR GJORDE FALSKA ÄR RÄTTADE**, var och
en mot en mätning i skiva 21 och inte mot minnet av vad som stod där:

| Vad som stod | Vad som gäller |
| --- | --- |
| postens första mening namngav `biluppgifter-fordonsfakta` | spärren heter `fordonsfakta-ur-sida` |
| "Tre av dem returnerade ett värde när skivan började" | tre defekter på TVÅ av fallen, och den tredje uppstod i skivans egen första rättelse |
| §7.1-tabellens ingress sade baslinjen 112 | tabellen under är körd vid 119 |
| `re.escape` neutraliserad ger `50 passed` | `119 passed` |
| dubbelfällningen ger `3 failed, 43 passed` | `17 failed, 102 passed` |
| hela sviten ger `488 gröna` | `557 passed` |

De tre sista är tal jag lämnade orörda därför att jag inte skrev om just de
meningarna. **§7.2:s omskrivningskrav utlöses också när talets UNDERLAG ändras**,
och underlaget var här baslinjen.

**ETT BELÄGG VAR EN RÖRLEDNING TILL `grep -c`**, vilket §9 förbjuder för
verifiering. Att slutsatsen råkade vara riktig gör inte metoden tillåten, och en
förbjuden metod ska inte stå som förebild i ett styrdokument. Utbytt mot en
avläsning av `--tb=line`-utdatan, som namnger felskälen i klartext.

**`ETIKETTSPAN`-KOMMENTAREN PÅSTOD ATT BÅDA UTTRYCKEN FALLER STÄNGT.** Sant om
räknarens ÖVERskattning, falskt om dess UNDERskattning, och det är den senare som
släpper ut ett värde. Kommentaren skriver nu ut i vilken dimension räknaren är
lösare, i vilka den inte är det, och att defekten är öppen till skiva 22.

**`docs/incidentlogg.md` I8 tillkommer:** en fällning mot fel radnummer gav
`GRÖN`, ett verdikt som inte går att skilja från ett äkta vakuöst utfall. Den
inträffade två gånger i samma pass, och andra gången var orsaken passets egen
kommentarändring i samma fil.

Statusrubrik, en struken lydelse och sex rättade påståenden ⇒ MINOR.

### 0.19.0 — 2026-09-03

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skiva 21 förbrukade alla tre och **varv 3 underkände**, på kriterierna 1, 2, 6,
7, 8 och 11. Varv 1 och varv 2 underkände också, och deras fynd är stängda i
koden. **Varv 3:s fynd är däremot INTE alla stängda:**

- **Två sändvägsdefekter står ÖPPNA**, i fall 5 och fall 6. De är verifierade av
  skivan själv i egen körning och beskrivna nedan. Lars grindbeslut är att skivan
  inte stängs utan fortsätter som skiva 22, som bygger om avläsningen till en
  parser. Defekterna committas alltså KÄNDA och utskrivna, inte dolda.
- **Dokumentfynden är rättade, men de rättelserna är självmätta och inte
  oberoende granskade**: spärrens namn i postens första mening, satsen om hur
  många av de tio fallen som bar defekter, §7.1-tabellens ingress som etiketterade
  sin egen tabell med en föråldrad baslinje, tre tal som skivans egna test gjorde
  falska, `ETIKETTSPAN`-kommentarens påstående att båda uttrycken faller stängt,
  och ett belägg som var en rörledning till `grep -c`.

Rättelserna gjordes därför att §7 förbjuder att skeppa ett känt falskt påstående
även när varvsgränsen är uttömd. Gränsen begränsar antalet granskningar, inte
kravet på sanning.

**`fordonsfakta-ur-sida` får en SIDÄNDRINGSPRÖVNING.** De elva
mutationsfällningarna prövar koden; den här prövar källan. Tio fall konstruerade
ur samma fixtur. **TVÅ av de tio fallen bar sändvägsdefekter**, nummer 4 och
nummer 6, och de bar TRE stycken: två fanns när skivan började och en uppstod i
skivans egen första rättelse. Alla tre är stängda och utskrivna nedan.
Sex markupändringar utanför briefens lista prövades också, och även de faller
till utkast.

**TVÅ DEFEKTER STÅR ÖPPNA I FALL 5 OCH FALL 6**, fällda av granskningsvarv 3 och
verifierade av skivan själv. De är inte stängda i skiva 21. Se statusrubriken
nedan och avsnittet om vad varv 3 fann.

Prövningen bär sitt eget nollfall: den oförändrade sidan ska fortfarande ge ett
uppslag, annars vore de tio testen gröna utan att pröva något.

**De ändrade sidorna ligger i repot som en BYGGARE, inte som filer.** `sida_med`
i `tests/test_biluppgifter.py` sätter ihop den avlästa sidan med ett led utbytt,
och varje fall namnger sitt byte. Kravet att ingenting får ligga i `/tmp` är
uppfyllt: det finns ingen fixtur utanför repot, och sviten kör utan filer vid
sidan av. Formen valdes framför tio HTML-filer därför att skillnaden mellan
fallen då syns i testet i stället för i en diff mellan två nästan identiska
filer, och därför att en byggare inte kan glida ifrån baslinjefixturen.

**Fall 4 har två halvor**, och posten skriver ut varför kravet inte kan gälla
båda: `1 200 kg` är sidans egen form och måste läsas.

**En ny lucka, nummer 5: den semantiska omdöpningen.** Behåller källan namnet
`Släpvagnsvikt` men låter det beteckna den obromsade vikten passerar samtliga
fyra lager och modulen svarar 750 kg. Den är **obevakad, inte oupptäckbar**:
modulen läser fältet med det namn den fått, och källan har ändrat vad namnet
betyder, men en rimlighetskontroll mot ett fjärde fält skulle kunna fånga den.
Ingen sådan är byggd, och avvägningen är Lars. **Frågan är ställd och obesvarad.**

Lucka 5 ligger utanför briefens tio fall: där är etiketten omdöpt, här står den
kvar oförändrad. Den är alltså inte en av de tre defekterna ovan.

**§7.1-prövningen av de nya testen står utskriven per fällning**, med citerade
rader och hela svitens utdata, körd sist i skivan. En av fällningarna ligger i
`src/fordonsuppslag.py` med avsikt, eftersom fall 1, 2, 3 och 5 vilar på spärren
nedströms och inte på något i hämtningsmodulen.

**§7-GRANSKNINGEN HITTADE TRE SÄNDVÄGSDEFEKTER, och de är rättade i koden.**
Alla tre låg INOM briefens tio kategorier och alla tre returnerade ett värde där
spärren skulle ha fällt. Två fälldes i varv 1 och en i varv 2:

- **Fall 6, varv 1.** Lager 2 räknade träffar på `MONSTER` i stället för
  förekomster av etiketten. Ett värde med nästlad markup syns inte i `MONSTER`,
  så en dubblerad etikett där ett värde var nästlat gav 750 kg i stället för
  `Hamtningsfel`. `ETIKETTSPAN` tillkommer och lager 2 räknar nu etiketten.
- **Fall 4, varv 1.** `_tal` tillät blanktecken var som helst i siffergruppen, så
  `750 2400 kg` blev 7502400. Mönstret kräver nu konsekventa tusenavskiljare.
- **Fall 6 igen, varv 2.** `ETIKETTSPAN` skrevs lika strängt som `MONSTER`, så en
  dubblett där ena etikettspannen bar ett attribut, `data-id="7"`, extra blanksteg
  i taggen eller enkla citattecken, räknades som en enda förekomst och släppte
  ut ett värde. Räknaren är nu lösare än läsaren, och modulkommentaren skriver ut
  varför den asymmetrin är hela konstruktionen: räknaren överräknar och kastar,
  läsaren underträffar och utelämnar, båda faller stängt.

**Den första rättelsen av `_tal` räckte inte, och det står här därför att
mönstret annars ser färdigt ut.** Den gjorde avskiljaren VALFRI mellan grupperna
och lät gruppen upprepas noll gånger. Följden var att grupperingen fick blandas
inom ett och samma tal, så `2400 750 kg` lästes fortfarande som 2400750, alltså
samma defektklass en runda senare.

Den levererade formen, `traff = re.fullmatch(` i `_tal`, kräver i stället
antingen bara siffror eller en till tre siffror följda av grupper om exakt tre
med en avskiljare vid VARJE gräns. De två alternativen är åtskilda, och det är
åtskillnaden som stänger den blandade grupperingen. **Raden citeras här och
numreras inte**, av skälet i rutan överst.

**Skivans egen text påstod att inget av de tio returnerar ett värde.** Det var
falskt och står nu rättat med defekterna utskrivna, eftersom en post som säger
att allt höll från början döljer att tre fel hittades och stängdes.

**Att alla tre är samma defektklass är postens viktigaste fynd.** Var och en
uppstod därför att ett mönster skrivet för sidans NUVARANDE markup tystnade i
stället för att kasta när markupen såg annorlunda ut. Det är precis den risk
briefen namngav: `biluppgifter.se ändrar sin markup utan att fråga oss`. Elva
mutationsfällningar mot koden hade inte hittat någon av dem, eftersom koden var
självkonsistent i alla tre fallen.

Lucka 5:s rubrik sade att den semantiska omdöpningen inte GÅR att upptäcka,
vilket motsades av postens eget nästa stycke. Den säger nu att den är obevakad.
**Lucka 6 tillkommer:** ankaret prövar bara sista segmentet i sökvägen.

**Fall 4:s uppdelning är namngiven som en öppen punkt**, inte som en
nödvändighet. Skivan avgjorde själv att briefens krav inte kan gälla källans
eget format, och det är Lars fråga.

**§6-GENOMGÅNGEN AV FIXTUREN ÄR GJORD FÖR HAND, och den behövdes.**
`scripts/persondatakontroll.py` bevakar `docs/`, `mallar/`, `config/`, `scripts/`
och `CLAUDE.md`, alltså varken `src/` eller `tests/`, och en körning av den säger
därför ingenting om testfilen. Vad som prövades och vad utfallet blev:

- **Etiketterna och de åtta avlästa värdena i `SIDA_AVLAST` är vikter**, alltså
  fordonsdata utan bärare. Ingen ägaruppgift följde med.
- `Chassinr / VIN` förekommer som ETIKETTNAMN i en kommentar, inte som värde.
  Det står där för att förklara glappet mellan 62 label-span och 54 par.
- **Registreringsnumren i testfilen är konstruerade**, och det nummer källans
  sida faktiskt lästes för står inte i repot. §6 räknar registreringsnummer som
  persondata, så skillnaden är inte kosmetisk. **Numren skrivs inte ut här**, av
  skälet i nästa stycke.

**DEN FÖRSTA LYDELSEN SKREV UT DE TVÅ KONSTRUERADE NUMREN, och fälldes av
repots egen kontroll.** `granska()` på det här dokumentet gav två fynd av sorten
`registreringsnummer`, båda på den raden. Kontrollen hade en falsk positiv,
eftersom numren är påhittade, men lydelsen är ändå struken: **Lars beslut är att
numren ska ut ur `docs/`, inte att de ska undantas.**

Skälet är att ett undantag i `TILLATNA` gäller exakt strängen och därmed hade
släppt igenom ett framtida RIKTIGT nummer med samma tecken. Det är samma
avvägning som gjordes för postnummer i skiva 7, och den finns redan utskriven i
det här dokumentet på två ställen. Ett stycke som redovisar att ingen persondata
läckte in ska inte självt vara det som för in mönstret.
- Sökningar efter personnummer, telefonnummer och VIN-liknande sekvenser i
  `tests/test_biluppgifter.py`, `src/biluppgifter.py` och det här dokumentet gav
  en enda träff, ett Gmail-etikett-ID i en äldre post, som inte är persondata.

**Mutationstabellen och §7.1-tabellen är ommätta mot baslinjen 119.** Båda stod
vid tidigare baslinjer, 50 respektive 112, och skivans egna test flyttade dem.
Postens egen regel om att ett tal slutar gälla när baslinjen rör sig gäller
posten själv. Elva plus nio verdikt står kvar som RÖD; talen är andra.

**Redundansstycket om lager 1 och 2 är omskrivet.** Lagren var kopplade därför
att lager 2 räknade lager 1:s uttryck. Efter `ETIKETTSPAN` är de frikopplade, och
dubbelfällningen ger nu 17 röda mot 5 plus 12, alltså exakt additivt. Den gamla
föreskriften att alltid fälla dem tillsammans gällde den gamla kopplingen och
gäller inte den levererade koden.

Tre rättelser i sändvägen, ett nytt avsnitt och två nya luckor ⇒ MINOR.

### 0.18.1 — 2026-09-02

**0.18.0-posten fick en statusrubrik som saknades.** Skiva 19 förbrukade §7:s tre
granskningsvarv, varv 3 underkände formellt på kriterierna 2, 4, 5, 8 och 9, och
rättelserna är självmätta. Posten bar ingen sådan rubrik och läste därför som en
avslutad redovisning. Tillagd i efterhand på Lars beslut i skiva 20, i den form
`docs/beslutslogg.md` använt sedan skiva 15. **Det här dokumentets egna poster har
aldrig burit en**, så kontrasten gäller mot beslutsloggen och inte mot
spärrdokumentets historik.

Posten bär också att granskningsrapporterna låg i `/tmp` i den dåvarande
sandboxen och inte är bevarade, så att ingen letar efter dem.

**Mutationstabellen bär nu sin egen verifiering.** Samtliga elva rader är
oberoende reproducerade i skiva 20 mot baslinjen 50 gröna, med sha256 kvitterad
per körning. Verdikt och antal röda test stämmer i varje rad, och de fyra som
tidigare inte gick att rekonstruera går det nu. En reproduktionsdetalj är
utskriven: escapen för hårt blanksteg når inte oförändrad genom skalet i fällning
7 och 9, men är semantiskt identisk inuti teckenklassen.

**Tre fällor ur överlämningen var sandboxens och inte repots**, och det står nu
utskrivet som en avläsning på Lars maskin: repots eget `scripts/sparr-prova.sh`
fungerar, testerna är självbärande, och hela sviten är hel. Utan noteringen
drar nästa läsare slutsatsen att sviten beror på filer utanför repot.

*Rättelse i 0.20.0: här stod `488 gröna`. Talet var avläst när posten skrevs och
gjordes föråldrat av skiva 21:s nya test. Avläst i skiva 21: `557 passed`. Bara
talet är struket; noteringens påstående, att sviten är hel utan filer utanför
repot, står kvar.*

**Granskningsomgången fällde två falska påståenden i den här skivans egen text.**
Det första: att skivorna 15 till 18 alla bar en statusrubrik. Sant om
`docs/beslutslogg.md`, falskt om det dokument meningen stod i, som aldrig burit
en och som skiva 18 inte ens rörde. Det andra: att escapen omvandlas av SKALET.
Granskaren mätte att `\d`, `\s` och dubblerade snedstreck når fram intakta i
samma argument, så omvandlingen sitter före skalet, och utfallet visade sig
dessutom variera mellan hårt och vanligt blanksteg.

Fem formuleringsfynd är också rättade: skälet till kriterienumren stod i presens
och upphävdes av nästa stycke, en räkning av tecken i ett aldrig committat utkast
är struken, meningen om förväxlingsrisken hade riktningen bakvänd, rubriken om
självbärande tester lovade mer än brödtexten belade, och ordet `oberoende` användes
om skivans egen körning i stället för granskarens.

**Granskaren körde om samtliga elva rader och alla stämde.** Tabellen bär därför
nu två oberoende reproduktioner och inte bara skiva 20:s egen.

Tillägg till en befintlig post ⇒ PATCH.

### 0.18.0 — 2026-09-02

**`fordonsfakta-ur-sida` tillkommer som SPÄRR**, byggd i skiva 19, se
`docs/beslutslogg.md` #31. MINOR då en post tillkommer. Posten står efter
`fordonsfakta-ur-uppslag` eftersom den vaktar steget före den, och
översiktstabellen bär nu tio rader.

**En befintlig post ändras också.** `versalkansligt-monster-i-avlasare` får en
uppmätt instans: §6-kontrollens versalkänslighet gör att den SLÄPPER IGENOM ett
gement registreringsnummer i `docs/`. Instansen uppstod i den här skivan, i en
rättelsemening i den nya spärrposten, och är åtgärdad. Punkten bär också den
manuella sökning som behövs före commit, och skriver ut att den bullrar.

**§7-granskningen underkände första varvet på den här posten**, på fyra
sakpåståenden om koden: prövningens förklaring till varför dubbelfällningen ger
färre röda än lager 1 ensamt, versal- och gemenriktningen i negativkontrollen,
ett "eller omvänt" om utfallsriktningen som inte är producerbart, och ett
`grep`-kommando som missade fyra av de villkor posten påstår att det slår upp.
Samtliga är rättade mot avläst källa. **Talen 5, 1 och 3 var däremot riktiga hela
tiden**; det var förklaringen till dem som var fel, vilket är svårare att se.

**ANDRA VARVET UNDERKÄNDE OCKSÅ, på åtta fynd.** Ett i sändvägen: det "bara" som
ersatte varv 1:s "eller omvänt" var icke-producerbart åt andra hållet. Mot den
avlästa sidan ger en prefixmatchning den RÄTTA vikten, av radordning, så
riktningen skrivs nu som en egenskap hos källans radordning och inte hos defekten.
Sex i koden: samma felaktiga följdsats i modulens filhuvud och i ett
testdocstring, ett `grep`-mönster som missade `MONSTER` och gav en docstringträff,
ett `grep`-kommando utan sökvägsargument som söker hela trädet, en onåbar gren i
`_tal`, `re.escape` utpekad som ett lager utan att något test fäller den, och
fixturkommentarens påstående om radordningen, som är källans för sju av åtta och
inte för alla. Ett i dokumentdetalj: `SIDA_AVLAST` bär åtta avlästa värden, inte
tre.

*Uppräkningen ovan namngav först bara FEM kodfynd och lade det sjätte,
fixturkommentarens radordning, i dokumentdetaljmeningen. Klasstotalerna 1/6/1 var
rätt, men uppräkningen bakom dem var det inte. Det spelar roll, för undantaget
gäller PER DEFEKTKLASS: ett kodfynd som journalförs som dokumentdetalj ser i
efterhand ut att ha fått en lägre bevisbörda än det fick. Varv 2:s klassning är
avläst i rapporten: fynd 1 SÄNDVÄG, fynd 2 till 7 KOD, fynd 8 DOKUMENTDETALJ.*

**Två av rättelserna ändrar KODEN och inte bara texten.** `_tal`s tomkontroll är
borttagen: en svepning över samtliga 1 114 112 Unicode-kodpunkter visar att inget
tecken finns där regexens `\s` matchar men `str.strip()` inte tar bort det, så
grenen var bevisat onåbar och inte bara oprövad. Onåbarheten vilar på TVÅ led,
`.strip()` före matchningen och kvantifikatorn `+`, och båda står nu utskrivna i
docstringen med ett uppmätt utfall per led.
`test_bara_blanktecken_fore_enheten_ger_none` fäller ledet `.strip()` med `4`
röda; det befintliga `'kg'`-fallet fäller ledet `+`. *Återinförandevillkoret
namngav först bara `+`. Det var för smalt: `.strip()` är en lika tillräcklig
utlösare, och den fällningen lämnade sviten GRÖN, `46 passed`, så länge testet
inte fanns.* Och `re.escape` står kvar i koden men är utskriven
som ett skydd mot en FRAMTIDA etikett, inte som ett lager.

**Ett nionde fynd tillkom vid rättelsearbetet, utanför granskningen.** En kommentar
i modulen påstod att `(?!\s*<)` fäller en tom etikett. Uttrycket finns inte i
mönstret. Den FÖRSTA rättelsen av den var i sin tur också fel: den påstod att en
tom söksträng ger första label/value-parets värde. Uppmätt ger den NOLL träffar
mot den avlästa sidan, för med tom etikett kräver mönstret en label-span som bara
bär blanktecken, och någon sådan finns inte där. Mot en konstruerad sida som HAR
en sådan span ger den det TOMMA parets värde, inte det första. Ofarligt i dag
eftersom `EXAKT_ETIKETT` bara bär icke-tomma etiketter. **Lärdomen: en kommentar
som namnger ett regex-uttryck ska läsas mot mönstret, och en rättelse av den ska
MÄTAS och inte resoneras fram.**

Redundansen mot `fordonsfakta-ur-uppslag` är utskriven som DELVIS och i en
riktning, eftersom den äldre spärren prövar form och inte härkomst. Ett tal ur en
annan bils sida är ett välformat tal och passerar den. Redundansen INOM posten,
mellan lager 1 och 2, är också utskriven, med talen ur prövningen.

**Två fynd ur prövningen står i posten och gäller alla framtida §7.1-prövningar.**
Det första: ett test som skrevs för prefixfällan visade sig vakta källans
radordning i stället för spärren, och rättades med ett test i omvänd ordning. Det
andra: en fällning på en TOM rad blir död kod och ger falskt GRÖNT.
`scripts/sparr-prova.sh` avslöjar det i sin `NEUTRALISERAD`-rad, som då bär en tom
sträng som ursprungsvärde. Posten föreskriver att den raden läses, inte bara
verdiktet.

**GRINDEN ÄR FÖRBRUKAD, OCH DET SKA SYNAS.** §7 ger max tre granskningsvarv.
Skiva 19 förbrukade alla tre, och **varv 3 UNDERKÄNDE FORMELLT på kriterierna
2, 4, 5, 8 och 9**. Fynden är rättade. **RÄTTELSERNA ÄR SJÄLVMÄTTA, INTE
OBEROENDE GRANSKADE.**

Kriterienumren står utskrivna och inte bara fyndklasserna. **Ett nummer HADE gått
att slå upp mot granskningen, en klass hade det inte**, och det är skälet att
skriva ut dem. Att uppslagningen inte längre går att göra ändrar inte vilket av
de två som bär mer.

**DETALJERNA BAKOM KRITERIERNA ÄR INTE ÅTERFINNBARA.** Granskningsrapporterna från
skiva 19 låg enligt överlämningen i `/tmp` i den dåvarande sandboxen och är inte
bevarade, varken i repot eller någon annanstans. Vad varje kriterium prövade, och
exakt vilket fynd som fällde det, går alltså inte att slå upp. Det står här för
att nästa läsare inte ska tro att materialet ligger någonstans och bara är svårt
att hitta.

**NUMREN HAR OLIKA HÄRKOMST, och det ska synas.** Kriterium 5 är belagt i en
committad källa: commitmeddelandet för `3c7c751` skriver ut det ordagrant.
**Kriterierna 2, 4, 8 och 9 kommer ur Lars överlämning till skiva 20** och går
inte att kvittera mot repot. Det gör dem inte osanna, men läsaren ska inte tro
att de går att kontrollera här.

**Statusrubriken saknades ända till skiva 20.** Följden var att posten läste som
en grundlig och avslutad redovisning, utan något som sade att skivan skeppades
underkänd. Rubriken är tillagd i efterhand på Lars beslut, och tillägget
redovisas i 0.18.1.

*Formen är hämtad från `docs/beslutslogg.md`, där skivorna 15 till 18 alla bar en
sådan rubrik. **Det här dokumentets egna poster gjorde det inte**: 0.15.0, 0.16.0
och 0.17.0 bär ingen, och skiva 18 rörde inte den här filen alls. Kontrasten
gäller alltså mot beslutsloggen och inte mot spärrdokumentets egen historik.*

### 0.17.0 — 2026-08-28

**`kanal-som-kontext-aldrig-grund` tillkommer som SPÄRR**, byggd i skiva 17, se
`docs/beslutslogg.md` #29. Till skillnad från de två luckposterna har den kod och
går att fälla.

Posten vaktar FRÅNVARON av en kanal-till-kategori-koppling, och skriver därför ut
att prövningen inte går till som de andra: fällningen sker genom att SKRIVA DIT
kopplingen, inte genom att radera en rad. Utfört i skiva 17, RÖD, tre
negativkontroller föll. Radnumret skrivs INTE ut i posten, eftersom det flyttar
av varje redigering i filen.

Trunkeringen är redovisad som ett eget lager: taket gäller texten och inte
summan, så ett långt kontextblock inte äter av kundens egna ord.

Ny post ⇒ MINOR.

### 0.16.0 — 2026-08-28

**`versalkansligt-monster-i-avlasare` tillkommer**, märkt LUCKA UTAN SPÄRR.
Registrerad i skiva 16 på Lars beslut, se `docs/beslutslogg.md` #28.

Ett mönster som lånas ur `scripts/persondatakontroll.py` ärver dess
versalkänslighet, som är rimlig i en §6-kontroll och fel i en avläsare. Uppmätt mot
webbformulärets fältvärde: 46 av 78 versalkänsligt mot 77 av 78
skiftlägesokänsligt, alltså 31 tappade nummer av de 77 som går att läsa.

Posten skriver ut varför luckan inte syns i test, nämligen att testdata skrivs
versalt av den som skriver koden, och kräver därför att ett test för avläsaren
bär ett gement och ett blandat nummer. Föreskriften ligger i `docs/roadmap.md`.

**`persondatakontroll` fällde den här posten under arbetet**, på ett utskrivet
exempelnummer i just den punkten. Spärren hade rätt, och exemplet är borttaget.
Att lägga det i `TILLATNA` avvisades av samma skäl som mönsterkommentaren anger
för postnummer: undantaget gäller exakt strängen och hade släppt igenom ett
framtida riktigt nummer som råkar vara detsamma. En kursiv not står kvar där
exemplet stod.

**Rättelser efter §7-granskningen, per post.** Rättelsenoten i Spärr-fältet
daterade utvidgningen till 0.6.0. Den skedde i 0.7.0, vars post i det här
appendixet bär punkten om att `mallar/`, `config/` och `CLAUDE.md` tillkom.
Samma fel stod i den här posten och är rättat på båda ställena. **Översikt-tabellens rad om `persondatakontroll` bar kvar exakt den
falskhet som Spärr-fältet rättades från**, alltså att spärren gäller `docs/`, och
var efter skivan mer fel än före eftersom en katalog till tillkommit; raden pekar
nu på `BEVAKADE`. En räkning av hur många gånger listan vuxit gick inte att
belägga och är ersatt av "mer än en gång". Påståendet om avsikten bakom
versalkänsligheten skiljs nu från det avlästa.

**Andra varvet fällde luckpostens skäl.** Den sade att kunden inte skriver
versalt, vilket motsägs av talet i punkten under: 46 av de 77 läsbara
fältvärdena matchar det versalkänsliga mönstret, alltså skriver en majoritet
versalt. Det som gäller är att inte alla gör det, och luckan är verklig av det
skälet. Samma formulering står committad i `docs/roadmap.md` sedan skiva 15 och
är struken där med en kursiv not. Posten kallade dessutom sig själv en spärr i
sin sista punkt, och den här versionsposten räknade luckorna i stället för att
namnge dem.

**Noten under Översikt-tabellen namnger nu båda luckposterna.** Den räknar dem
inte, eftersom en mening som räknar sin egen omgivning blir falsk av nästa post.

**`persondatakontroll` bevakar nu `scripts/`.** Postens negativkontroll är
oförändrad; det nya testet `test_scripts_bevakas` binder katalogen och gav RÖD
vid prövning enligt §7.1.

**Postens Spärr-fält bar ett föråldrat påstående och pekar nu på konstanten.**
Det sade att spärren gäller stagat innehåll under `docs/`, vilket slutade vara
sant redan i 0.7.0 när `mallar/`, `config/` och `CLAUDE.md` lades till. En kopia
av kataloglistan i det här dokumentet blir föråldrad av varje utvidgning, så
fältet namnger `BEVAKADE` i stället och överlåter innehållet åt skriptet.

Ny post ⇒ MINOR.

### 0.15.0 — 2026-08-28

**`gmail-etikett-som-ensam-grund` tillkommer**, som en LUCKA UTAN SPÄRR. Regel av
Lars i skiva 15, se `docs/beslutslogg.md` #27. Posten bär sin uppmätta instans:
miningens `in:sent` gjorde etiketten `SENT` till ensam grund för uppdelningen
besvarad mot obesvarad, och webbformuläret skickar från brevlådan så att varje
formulärnotis bär `SENT` oavsett om någon svarat.

Posten skriver ut att den INTE går att fälla enligt §7.1, eftersom ingen kod
implementerar den, och vad som skulle krävas för att göra den till en spärr.
Den skiljer också systemsatta etiketter från handsatta: `ar_gmail_svar` läser
`SENT` och får göra det, felet var att `SENT` fick betyda besvarad.

**Posten sade först "den handsatta etikett som finns i materialet".** Materialet
bär 13 distinkta handsatta etiketter. Den bestämda formen var alltså falsk, och
den bar postens poäng om att läget är rätt.

**Talet bakom rättelsen var i sin tur fel, och felet satt i mätskriptet.**
Etikettloopen bröt efter varje meddelandes FÖRSTA `Label_`-id, så räknaren blev
ett meddelandetal medan posten kallade det trådar, och mängden distinkta
etiketter blev en undre gräns: en etikett som aldrig låg först räknades aldrig.
Skriptet räknar nu per tråd och tar med varje etikett i tråden.

De felaktiga talen skrivs inte ut här. De stod aldrig i en committad version och
går inte att räkna om, eftersom loopen som producerade dem är borta. De riktiga
talen är avlästa i posten ovan och går att kvittera mot `grep -c` i datafilerna.

**Översikten fick en rad om att den här posten inte står i den.** Tabellen räknar
spärrar som kod verkställer och kan inte bära en lucka utan kod utan att göra sina
egna kolumnrubriker falska. Posten är i stället utpekad i en mening under
tabellen, och redovisar mot mallens fyra fält vilka den saknar och varför.

Ny post ⇒ MINOR.

### 0.14.0 — 2026-08-27

**Spärren `dragkrokbesked-har-harkomst` registrerad och byggd**, på beslut av
Lars i skiva 13. Luckan stod registrerad i `fordonsfakta-ur-uppslag` sedan skiva
12: dragkroksbeskedet var en naken `bool` som en modell kunde sätta, och som
flyttar kunden från en fråga till ett prispåslag.

Beskedet är nu en `DragkrokBesked` som måste namnge en källa ur `BeskedKalla`, och
uppräkningen bär bara `KUNDSVAR` och `UTKASTVY`.

**GRANSKNINGEN FÄLLDE ATT SPÄRREN INTE BAND VID ANROPSSTÄLLET.** Ett utkast lät
`utvardera` pröva bara `besked.saknas`, alltså en ankuppslagning, så vilket objekt
som helst med det attributet gav GULT förbi hela härkomstkravet. Uppmätt:
`SimpleNamespace(saknas=True)` gav `Utfall.GULT`. Att typen var svår att
konstruera fel spelade ingen roll när ingen krävde den. Typkontrollen i
`utvardera` är tillagd och är spärrens viktigaste lager.

**Posten skriver ut vad spärren INTE kan hindra**, utan påstående om att listan är
uttömmande: en anropare som medvetet anger en tillåten men osann källa, de vägar
som kommer förbi `__post_init__`, och att beskedet är sant. Skärpningen flyttar
felet från slarv till avsikt, vilket är verkligt men inte en garanti.

**Ett utkast namngav två av de vägarna och missade två**, och dess kriterium
"aldrig körde `__post_init__`" täckte inte `object.__setattr__` på en färdig
instans, alltså den väg som inte kräver någon exotisk konstruktion alls. Posten
bär nu en tabell med en rad per väg.

**Ett utkast påstod att uppräkningen inte går att fälla. Det är falskt**, och
granskningen körde fällningen. Prövningstabellen bär nu raden, och en till: det
obligatoriska `kalla`-argumentet var deklarerat som lager men saknades i
tabellen. Båda är fällda och röda.

**Ett test togs bort ur sviten.** `test_ett_kilo_under_tjanstevikttroskeln_ensam_racker_inte`
lades till i skivan och visade sig vara ett exakt duplikat av två andra: det
finns inget sätt att pröva tjänsteviktströskeln NEDÅT utan att släpvagnsvillkoret
också faller, eftersom ett uppfyllt villkor räcker. Täckningen är oförändrad, och
skälet står i det kvarvarande testets docstring.

**`fordonsfakta-ur-uppslag` prövar ett TREDJE fält, `tjanstevikt_kg`**, efter att
gatingen rättats mot §42 andra stycket. Viktkraven delas nu av två fält genom
`_krav_pa_vikt`, så en fällning där fäller båda samtidigt; skälet bär fältnamnet
och varje viktest asserar mot det.

**Prövningstabellerna är omkörda i sin helhet**, mot en svit om 354 test. Bland
fällningarna ligger §42:s två lämplighetsvillkor var för sig, och fällningen av
tjänsteviktsvillkoret gör regressionsvakten
`test_tung_bil_med_lag_slapvagnsvikt_ar_inte_rott` röd.

**Kvittensmeningen om `git diff` är rättad.** Tidigare lydelser skyllde tomheten
på att filen var NY, och därefter på att den är spårad. Båda missade det som
faktiskt avgör: arbetet är STAGAT, så `git diff -- <fil>` jämför arbetsträd mot
index, som är identiska. Kvittensen jämför tomt mot tomt oavsett om filen är ny
eller spårad. **Bara sha256 bär bevis.**

Lydelserna redovisas utan att räknas. Antalet rättelseförsök är ett arbetsförlopp
och inte något som går att läsa ur repot, eftersom mellanversionerna aldrig
committades (§7.2).

**Talen ur diffjämförelsen är strukna, inte omräknade.** En lydelse skrev ut
antalet tillagda och borttagna rader och hade läst dem mot en filversion som inte
längre fanns. Beslut av Lars: ett tal som ingen behöver är inte värt en tredje
rättelse. Påståendet bärs av att den ena diffen är tom och den andra inte, inte
av hur stor den andra är.

**SPÄRR-FÄLTET SADE "TVÅ FUNKTIONER" OCH SPÄRREN LIGGER I FYRA.** Fältet bär nu
en tabell över dem, och kravet att en §7.1-prövning måste fälla i alla fyra.
Skivan gjorde meningen falskare genom att bryta ut `_krav_pa_vikt` och samtidigt
stryka den mening som var regnr-lagrets enda hemvist i fältet; den hemvisten är
återinförd. Samma utelämnande fanns i `dragkrokbesked-har-harkomst`, vars
Spärr-fält saknade `utvardera`, och i testfilens huvud. Båda rättade.

**Luckelistan för dragkroksbeskedet bär två vägar till**, `copy.copy`/`copy.deepcopy`
och `unittest.mock.Mock(spec=...)`, båda funna av granskaren och båda uppmätta.
`Mock`-raden är den mest närliggande i praktiken, eftersom fas 5:s tester kommer
att bygga attrapper.

Ny prövad spärr och ett tredje fält i en befintlig ⇒ MINOR.

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
