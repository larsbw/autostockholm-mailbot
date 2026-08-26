# Spärrar

**Version:** 0.5.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §7.1

> **RADNUMMER FÖRÅLDRAS.** Kontrollera alltid att raden i en post fortfarande
> bär det villkor posten påstår, innan du fäller den. En granskning körde det
> dokumenterade kommandot ordagrant, träffade fem docstringrader i stället för
> spärren, och fick verdiktet GRÖN. Ett föråldrat radnummer i det här dokumentet
> producerar alltså ett FALSKT VAKUÖSTVERDIKT, vilket är värre än inget
> dokument. Varje post namnger därför också villkorets TEXT.

**Sändvägens spärrar är ännu inte byggda och fylls i FAS 5.** En spärr är
registrerad, och den kommer inte från sändvägen utan från mining.

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
| `maskering-persondata` | Att persondata når ett dokument under `docs/` | `test_ord_vid_meningsstart_maskeras_ocksa` | `src/cluster.py::namn_i_korpus`, i en ANNAN fil. Se posten. |

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
