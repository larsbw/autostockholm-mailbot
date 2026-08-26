# Kategoriförslag

**Version:** 0.3.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §0

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

Texter i underlaget: 795

| Kategori | Totalt | Med svar | Utan svar |
| --- | --- | --- | --- |
| inget kundärende | 547 | 52 | 495 |
| oklart | 38 | 31 | 7 |
| fråga om a-traktorkonvertering | 25 | 25 | 0 |
| boka rekond | 22 | 4 | 18 |
| avboka bokning | 13 | 1 | 12 |
| fråga om pris a-traktorkonvertering | 12 | 11 | 1 |
| boka reparation | 11 | 4 | 7 |
| boka biltvätt | 11 | 0 | 11 |
| begära offert | 11 | 8 | 3 |
| fråga om praktisk info | 10 | 9 | 1 |
| boka däckbyte | 9 | 2 | 7 |
| boka tillbehörsmontage | 8 | 7 | 1 |
| fråga om pris rekond | 7 | 6 | 1 |
| omboka bokning | 7 | 7 | 0 |
| boka a-traktorkonvertering | 7 | 7 | 0 |
| begära dokument | 7 | 4 | 3 |
| övrigt | 7 | 4 | 3 |
| boka service | 6 | 4 | 2 |
| fråga om pris reparation | 5 | 4 | 1 |
| fråga om tjänst | 5 | 3 | 2 |
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
