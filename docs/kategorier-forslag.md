# Kategoriförslag

**Version:** 0.4.0 · **Uppdaterad:** 2026-08-28 · **Implementerar** CLAUDE.md §0

Maskinproducerad av `src/ometikettera.py` med `claude-sonnet-4-6`. **Skriv inte i den här filen för hand**: den skrivs om vid nästa körning.

**FRAMTAGEN I TVÅ PASS.** Pass 1 läste de etiketter en tidigare körning satt fritt, en per text, och konsoliderade dem till den fasta taxonomin nedan. Pass 2 etiketterade om varje kundärende mot den listan. Den fria omgången gav en etikett per FORMULERING, inte per ärendetyp.

**`inget kundärende` och `oklart` är INTE ometiketterade.** De bär sina tal från den fria omgången och är med här för att tabellen ska täcka hela materialet.

**`utanför listan`** är texter där modellen svarade med något som inte står i taxonomin. De rättas inte tyst. Är raden stor är det taxonomin som är för smal, inte texterna som är konstiga.

**INGEN HINKTILLDELNING FÖRESLÅS.** Vilken kategori som hamnar i `auto`, `utkast` eller `aldrig` är Lars beslut i fas 4:s grind. Ramverksregel 2 i CLAUDE.md §0 säger att ingen kategori flyttas av kod.

**CITATEN STÅR INTE HÄR.** De skrivs till `scratchpad/kategorier-exempel.md`, som är gitignorerad. Ett namn som kunden skrivit med gemener i löpande text går inte att hitta med någon heuristik, och §6 tillåter ingen persondata i `docs/`.

---

## Taxonomin ur pass 1

- boka rekond
- boka biltvätt
- boka service
- boka däckbyte
- boka bromskontroll
- boka reparation
- boka tillbehörsmontage
- boka a-traktorkonvertering
- avboka bokning
- omboka bokning
- fråga om a-traktorkonvertering
- fråga om pris rekond
- fråga om pris service
- fråga om pris reparation
- fråga om pris däck
- fråga om pris a-traktorkonvertering
- fråga om pris tillbehör
- fråga om däckförvaring
- fråga om tjänst
- fråga om praktisk info
- begära offert
- godkänna offert
- begära dokument
- bestrida faktura
- reklamera utfört arbete
- ge feedback
- ansöka om praktikplats
- övrigt

---

## Kategorier

Texter i underlaget: 861

| Kategori | Totalt | Med svar | Utan svar |
| --- | --- | --- | --- |
| inget kundärende | 588 | 52 | 536 |
| oklart | 41 | 31 | 10 |
| fråga om a-traktorkonvertering | 29 | 25 | 4 |
| boka rekond | 23 | 4 | 19 |
| fråga om pris a-traktorkonvertering | 14 | 11 | 3 |
| avboka bokning | 13 | 1 | 12 |
| boka tillbehörsmontage | 12 | 7 | 5 |
| boka däckbyte | 12 | 2 | 10 |
| boka reparation | 11 | 4 | 7 |
| boka biltvätt | 11 | 0 | 11 |
| fråga om praktisk info | 11 | 9 | 2 |
| begära offert | 11 | 8 | 3 |
| boka service | 9 | 4 | 5 |
| boka a-traktorkonvertering | 9 | 7 | 2 |
| övrigt | 8 | 4 | 4 |
| fråga om pris rekond | 7 | 6 | 1 |
| omboka bokning | 7 | 7 | 0 |
| begära dokument | 7 | 4 | 3 |
| fråga om tjänst | 6 | 3 | 3 |
| fråga om pris reparation | 5 | 4 | 1 |
| fråga om pris service | 5 | 5 | 0 |
| godkänna offert | 5 | 4 | 1 |
| reklamera utfört arbete | 3 | 1 | 2 |
| bestrida faktura | 3 | 2 | 1 |
| boka bromskontroll | 3 | 1 | 2 |
| ansöka om praktikplats | 2 | 2 | 0 |
| fråga om pris däck | 2 | 1 | 1 |
| utanför listan | 1 | 1 | 0 |
| ge feedback | 1 | 1 | 0 |
| fråga om däckförvaring | 1 | 1 | 0 |
| fråga om pris tillbehör | 1 | 1 | 0 |

---

## Appendix — versionshistorik (nyaste överst)

### 0.4.0 — 2026-08-28

**Vad version 0.4.0 gjorde**, i skiva 16: `scripts/etikettera-nya.py` lade till 66 kundtexter och etiketterade enbart dem. De blev synliga av att `docs/beslutslogg.md` #27 rättade uppdelningen besvarad mot obesvarad: miningens `in:sent` gjorde en Gmail-etikett till ensam grund för vilken skördefil en tråd hamnade i, så kundärenden utan svar i fel fil räknades i ingen kolumn.

De 66 gick genom BÅDA passen, alltså först den fria klassningen som avgör `inget kundärende` och `oklart`, sedan pass 2 mot den fasta taxonomin. Taxonomin lästes från `data/taxonomi.json` och kördes INTE om. Varje ny post bar `utan svar`, så kolumnen `Med svar` kunde inte ändras av den körningen. Skälet att inte köra om materialet är att pass 2 inte är deterministiskt, se beslutslogg #18.

**APPENDIXET ÄR STATISKT OCH BESKRIVER VARJE VERSIONS ÄNDRING, aldrig den senaste körningen.** Posterna ligger i `src/ometikettera.py::skriv_rapport` och skrivs ut oförändrade vid varje körning. En full omkörning av `src/ometikettera.py` etiketterar om HELA korpusen och är alltså inte det posten ovan beskriver; den som gör en sådan körning ska höja versionen och lägga till en egen post innan filen committas.

### 0.3.0 — 2026-08-26

Den fria etiketteringen ersatt av två pass. Pass 1 konsoliderar etiketterna till en fast taxonomi i ett anrop, pass 2 etiketterar om kundärendena mot den. Den fria omgången gav en etikett per formulering och inte per ärendetyp. Se beslutslogg #18.

### 0.2.0 — 2026-08-26

Klustringen ersatt av kategorisering med Anthropic API. TF-IDF grupperade på avsändarens mall i stället för på kundens ärende, och det mänskliga materialet hamnade i restposten. Se beslutslogg #9.

### 0.1.0 — 2026-08-26

Filen upprättad av `src/cluster.py`.
