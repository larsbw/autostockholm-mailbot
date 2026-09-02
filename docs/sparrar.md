# Spärrar

**Version:** 0.18.1 · **Uppdaterad:** 2026-09-02 · **Implementerar** CLAUDE.md §7.1

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
| `persondatakontroll` | Att en commit för in persondata i en bevakad sökväg. Vilka de är står i `BEVAKADE` i skriptet. | `test_ren_text_ger_inga_fynd` | `maskering-persondata`. Sista linjen, inte den enda. |
| `forbjudna-maskindomaner` | Att en förmedlad kundförfrågan kastas som maskinmail | `test_liknande_doman_skyddas_inte_av_misstag` | Sig själv, två lager i `src/klassa_maskin.py`, och går FÖRE `klassning-maskinmail`. Se posten. |
| `fordonsfakta-ur-uppslag` | Att ett utgående mail namnger fordonsfakta som inte kommer ur ett lyckat uppslag | `test_fullstandigt_svar_slapps_igenom`, `test_svar_med_okanda_nycklar_slapps_ocksa_igenom`, `test_mappningsobjekt_som_inte_ar_dict_slapps_igenom` | Ingen annan spärr. Formlager i `_kontrollera` och värdelager i `Uppslag.__post_init__` via `_krav_pa_vikt`. Formlagren är HELT redundanta med varandra, och viktlagren DELAS av två fält. Kända luckor listas i posten. |
| `fordonsfakta-ur-sida` | Att ett tal eller ett dragkroksbesked läses ur en annan sida än det efterfrågade fordonets, eller ur en etikett som bara inleds likadant | `test_alla_tre_falten_lases_ur_ett_avlast_svar`, `test_avlast_fordon_ger_oklart`, `test_normaliserat_nummer_slar_igenom_till_canonical` | `fordonsfakta-ur-uppslag`, men bara DELVIS: den fångar saknade och otolkbara fält, aldrig ett välformat tal ur fel sida. Fyra lager, lager 3 ensamt om sitt fall. Se posten. |
| `dragkrokbesked-har-harkomst` | Att ett besked om dragkrok sätts av en modell och flyttar kunden från en fråga till ett prispåslag | `test_bada_tillatna_kallorna_gar_igenom` | Ingen annan spärr. Se posten, särskilt vad den INTE kan hindra. |
| `kanal-som-kontext-aldrig-grund` | Att kanalen ett mail kom in genom blir ensam grund för dess kategori | `test_kanalen_overstyr_aldrig_modellens_svar`, `test_samma_svar_ger_samma_etikett_med_och_utan_kanal`, `test_kanalen_gor_inte_ett_svar_utanfor_taxonomin_giltigt` | Ingen annan spärr. Vaktar FRÅNVARON av kod och fälls därför genom att skriva dit kopplingen. Se posten. |

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
  | 1 | `MONSTER`, alltså `<span class="label">\s*{etikett}\s*</span>`, där `\s*</span>` är det som gör etiketten exakt | Att en etikett läses som PREFIX till en annan |
  | 2 | `if len(traffar) > 1:` som kastar `Hamtningsfel` med texten `tvetydigt` | Att första träffen tas när samma etikett förekommer flera gånger |
  | 3 | `if not _galler_fordonet(sida, regnr):` plus `_galler_fordonet` själv, som jämför `CANONICAL` mot numret | Att en sida som inte gäller numret läses som fordonets |
  | 4 | `_tal` med `re.fullmatch` mot `kg`, och `_ja_nej` med förvalet `None` | Att ett värde som inte är rent tolkas som ett tal eller ett ja |

  **DEN SOM SKA FÄLLA SPÄRREN MÅSTE FÄLLA I ALLA FYRA.** Lager 3 har dessutom TRE
  skilda beslut i sig, och en prövning som bara neutraliserar anropet når inte de
  två andra: att saknad `canonical` ger `False`, och att jämförelsen är
  skiftlägesokänslig.

  **`re.escape` ÄR INTE ETT AV LAGREN, FÖR DEN ÄR INTE FÄLLBAR.** Anropet står i
  koden på raden med `MONSTER.format` och ska stå kvar, men **neutraliseras det
  blir sviten GRÖN**, `50 passed`. Skälet: ingen av de tre etiketterna i
  `EXAKT_ETIKETT` innehåller ett regex-metatecken, så escapad och oescapad etikett
  ger identiskt mönster. Den är alltså ett skydd mot en FRAMTIDA etikett, inte ett
  lager i den här spärren, och den ska inte räknas som prövad. Sidan bär
  `Släp totalvikt (B)` med parenteser; läggs den etiketten någon gång till blir
  escapen fällbar, och då hör den till lager 1. *Här namngavs `re.escape` tidigare
  som en del av lager 1:s villkor och låg i dess sökmönster. Det var fel: ett
  villkor som inget test fäller är inte ett lager, och §7.1 ställer just den frågan.*

  Radnumren står inte här, av skälet i rutan överst. Slå upp villkoren med ett
  sökmönster per lager, i `src/biluppgifter.py`:

  | Lager | `grep -n` |
  | --- | --- |
  | 1 | `'EXAKT_ETIKETT = \|MONSTER = \|{etikett}'` |
  | 2 | `'len(traffar) > 1'` |
  | 3 | `'CANONICAL = \|def _galler_fordonet\|slutet\.upper()\|_galler_fordonet(sida'` |
  | 4 | `'re\.fullmatch\|def _ja_nej'` |

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

  **LAGER 1 OCH 2 ÄR DELVIS REDUNDANTA, och det är avsiktligt.** Etikettmönstret
  är exakt, så det ger normalt en träff, och tvetydighetskontrollen är då tystnad.
  Faller mönstrets stränghet bort träffar det flera etiketter, och då är det
  kontrollen i lager 2 som fäller. Prövningen: fälls lager 1 ensamt föll fem test,
  fälls lager 2 ensamt föll ett, och fälls **båda samtidigt föll tre** — alltså
  färre än vid lager 1 ensamt.

  **Att dubbelfällningen ger FÄRRE röda är inte en räknefråga, och den första
  förklaringen i den här posten var fel.** Fyra av lager 1:s fem föll på
  `Hamtningsfel ... tvetydigt`, alltså på lager 2:s kast och inte på det de
  själva asserar. Inget av dem kontrollerar tvetydigheten; det gör bara lager 2:s
  eget test, och det passerar när lager 1 fälls ensamt. Neutraliseras lager 2
  också tas första träffen i stället, och **tre av de fyra blir gröna** eftersom
  första träffen råkar vara den rätta i deras fixturer. Den fjärde,
  `test_slapvagnsvikt_ar_den_bromsade_aven_i_omvand_radordning`, förblir röd men
  byter felskäl från undantag till assert, vilket är hela dess uppgift. Kvar blir
  den, `test_etikett_med_annat_suffix_ger_inte_falt` som föll på assert redan vid
  lager 1, och lager 2:s `test_dubblerad_etikett_kastar`: 5 − 3 + 1 = 3.

  **Följden för hur den här spärren ska prövas i framtiden:** ett rött verdikt vid
  fällning av lager 1 ensamt säger nästan ingenting, eftersom rödheten kommer från
  lager 2. Fyra av lager 1:s test har alltså sitt bevisvärde först i
  dubbelfällningen. **Fäll alltid lager 1 och 2 samtidigt**, och läs felskälet och
  inte bara verdiktet.

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
  samtidigt, vilket ger `3 failed, 43 passed` med
  `test_slapvagnsvikt_ar_den_bromsade` GRÖNT och värdet 2 400.

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

| Fällning | Verdikt | Röda test |
| --- | --- | --- |
| Lager 1, exakt etikett görs till prefix: `{etikett}\s*</span>` blir `{etikett}[^<]*</span>` | RÖD | 5 |
| Lager 2, `if len(traffar) > 1:` blir `if False:` | RÖD | 1 |
| **Lager 1 och 2 samtidigt** | **RÖD** | **3** |
| Lager 3, `if not _galler_fordonet(...)` blir `if False:` | RÖD | 1 |
| Lager 3, saknad `canonical` godtas: `return False` blir `return True` | RÖD | 1 |
| Lager 3, skiftläget i JÄMFÖRELSEN: `slutet.upper() == regnr.upper()` blir `slutet == regnr` | RÖD | 7 |
| Lager 4, `_tal` `fullmatch` blir `search` | RÖD | 2 |
| Lager 4, `_ja_nej` förval `None` blir `False` | RÖD | 5 |
| Lager 4, `.strip()` före matchningen borttagen | RÖD | 4 |
| Statusgrenen kastar inte: `raise Hamtningsfel(...)` blir `return None` | RÖD | 6 |
| 404-grenen neutraliserad: `if status == 404:` blir `if False:` | RÖD | 1 |

**SAMTLIGA ELVA RADER ÄR REPRODUCERADE I SKIVA 20, OCH AV DESS GRANSKARE.**
Tabellen ovan var självmätt när den skrevs, se statusrubriken i 0.18.0-posten.
Den är nu körd om två gånger av andra pass än det som skrev den: först av skiva
20 och sedan av skiva 20:s **oberoende granskare** i §7:s mening. Båda körde
`scripts/sparr-prova.sh` med `-- tests/test_biluppgifter.py -q` mot baslinjen 50
gröna. **Verdikt och antal röda test stämmer i varje rad i båda körningarna**, och
skriptet kvitterade sha256 identisk med utgångsläget varje gång.

Ordvalet är avsiktligt: `oberoende` är i det här repot §7:s term, satt i motsats
till `självmätt`. Det gäller granskarens körning. Skiva 20:s egen var bara ett
annat pass.

**De fyra som tidigare inte gick att rekonstruera går det nu.** Beskrivningarna
bär det uttryck som byts, och `NEUTRALISERAD`-raden visade i varje fällning ett
ursprungsvärde som var det avsedda villkoret, aldrig en tom sträng. Grep-tabellen
per lager slår upp rätt rader. Också det kontraintuitiva ledet reproducerar:
dubbelfällningen av lager 1 och 2 ger färre röda än lager 1 ensamt.

**EN REPRODUKTIONSDETALJ I FÄLLNING 7 OCH 9.** Bägge byter ut raden med
`re.fullmatch`, vars teckenklass bär en escape för hårt blanksteg, skriven med
omvänt snedstreck följt av `u00a0`. **Den escapen når inte oförändrad fram till
`--ersatt`.** Den blir ett blankstegstecken i den ersatta raden, alltså osynligt
i stället för utskrivet.

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
  `data/taxonomi.json`. På den här maskinen finns filen, och hela sviten ger 488
  gröna.

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
obromsade raden först. Först därefter fäller dubbelfällningen tre test.

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
fungerar, testerna är självbärande, och hela sviten ger 488 gröna. Utan noteringen
drar nästa läsare slutsatsen att sviten beror på filer utanför repot.

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
