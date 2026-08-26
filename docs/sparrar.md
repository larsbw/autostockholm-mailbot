# Spärrar

**Version:** 0.2.2 · **Uppdaterad:** 2026-08-26 · **Speglar:** CLAUDE.md 0.3.1 §7.1 ·
beslutslogg: ingen post rör spärrarna ännu

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
| `nollfall-max-threads` | Att en körning som ombeds hämta noll trådar raderar föregående skörd | `test_alla_tradar_over_flera_sidor_hamtas` | Sig själv, två lager (`src/mine.py:179` och `:238`). Se posten. |

---

## `nollfall-max-threads`

- **Spärr.** Hindrar att `--max-threads 0` eller ett negativt tal leder till en
  hämtning. Beslutet fattas på **två rader, i två funktioner**:
  - `src/mine.py:179` i `lista_trad_id`: `if max_tradar is not None and
    max_tradar <= 0: return []`. Skyddar API:et. Inget anrop görs.
  - `src/mine.py:238` i `mina`: samma villkor, returnerar innan `utfil` rörs.
    Skyddar filen. Ingen `.delvis` skapas och `data/tradar.jsonl` lämnas orörd.
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

  **Nuläge, uppmätt 2026-08-26 i den här skivan.** Sedan `:179` fått ett eget
  test faller varje lager för sig:

  | Fällning | Test som blir röda |
  | --- | --- |
  | `--radera 179 --radera 180` | `test_lista_trad_id_med_noll_gor_inga_anrop` |
  | `--radera 238 --radera 239 --radera 240` | `test_max_threads_noll_ger_inga_anrop_alls`, `test_max_threads_noll_raderar_inte_foregaende_skord` |
  | båda lagren | samtliga tre ovan |

  Lagringen är alltså kvar, men den maskerar inte längre. Varje lager vaktar en
  egen sak: `:179` skyddar API:et mot ett anrop, `:238` skyddar filen mot en
  överskrivning. Den fullständiga prövningen fäller ändå båda i samma körning:

  ```
  scripts/sparr-prova.sh --fil src/mine.py --radera 179 --radera 180 --radera 238 --radera 239 --radera 240
  ```

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
