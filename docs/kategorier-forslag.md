# Kategoriförslag

**Version:** 0.1.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §0

Maskinproducerad av `src/cluster.py`. **Skriv inte i den här filen för hand**: den skrivs om vid nästa körning.

Kategorierna är inte satta i förväg. De faller ut ur en oövervakad klustring av inkommande text, och etiketten per kategori är de termer som skiljer klustret från de andra.

**INGEN HINKTILLDELNING FÖRESLÅS.** Vilken kategori som hamnar i `auto`, `utkast` eller `aldrig` är Lars beslut i fas 4:s grind. Ramverksregel 2 i CLAUDE.md §0 säger att ingen kategori flyttas av kod.

**CITATEN STÅR INTE HÄR.** De skrivs till `scratchpad/kategorier-exempel.md`, som är gitignorerad. Ett namn som kunden skrivit med gemener i löpande text går inte att hitta med någon heuristik, och §6 tillåter ingen persondata i `docs/`. Kategorinamn, antal och medianer är härledda storheter och kan maskas säkert; citaten kan det inte.

---

## Översikt

Dokument i klustringen: 1291

| Kategori | Totalt | Med svar | Utan svar | Median svarslängd |
| --- | --- | --- | --- | --- |
| siffror, beställning, produkter | 250 | 0 | 250 | inget svar |
| profil, siffror, blockerad | 141 | 0 | 141 | inget svar |
| lägg, bud, siffror | 128 | 0 | 128 | inget svar |
| oss, produkter, kommer | 67 | 0 | 67 | inget svar |
| länk, bokning, ner | 50 | 1 | 49 | 228 |
| säljaren, länk, knappen | 28 | 0 | 28 | inget svar |
| epost, information, siffror | 27 | 9 | 18 | 801 |
| förfrågan, offert, söker | 24 | 0 | 24 | inget svar |
| länk, bids, finansiering | 13 | 0 | 13 | inget svar |
| mottagare, fil, bifogad | 11 | 6 | 5 | 288 |
| siffror, moms, gata | 11 | 2 | 9 | 224 |
| länk, betala, appen | 10 | 0 | 10 | inget svar |
| kunden, gjorts, bedömning | 10 | 0 | 10 | inget svar |
| länk, top, varukorg | 9 | 0 | 9 | inget svar |
| faktura, bifogad, fil | 9 | 1 | 8 | 477 |
| icloud, länk, bilder | 8 | 0 | 8 | inget svar |
| säkerställa, era, länk | 8 | 0 | 8 | inget svar |
| återbetalning, utfärdat, uppmärksam | 8 | 0 | 8 | inget svar |
| order, siffror, följa | 7 | 0 | 7 | inget svar |
| följesedel, sändningsnumret, sändning | 7 | 0 | 7 | inget svar |
| lösenord, länk, återställa | 6 | 0 | 6 | inget svar |
| verifieringskod, efterfrågat, verifiera | 6 | 0 | 6 | inget svar |
| favoriter, såna, mejlnotiser | 6 | 0 | 6 | inget svar |
| bilagor, eventuella, länk | 5 | 4 | 1 | 209 |
| email, addressees, contained | 5 | 4 | 1 | 199 |
| fordringar, skrivelsen, förfallit | 5 | 0 | 5 | inget svar |
| ärende, siffror, miljön | 5 | 1 | 4 | 241 |
| länk, finner, företagsinformation | 5 | 0 | 5 | inget svar |
| bygga, post, dragkrok | 5 | 5 | 0 | 783 |
| ios, länk, helger | 5 | 5 | 0 | 255 |
| none, text, block | 4 | 0 | 4 | inget svar |
| size, text, body | 4 | 1 | 3 | 193 |
| inlämning, bokningen, domän | 4 | 0 | 4 | inget svar |
| tvist, länk, nöjd | 4 | 0 | 4 | inget svar |
| länk, companies, here | 4 | 0 | 4 | inget svar |
| länk, siffror, epost | 4 | 2 | 2 | 167 |
| ärende, sekunder, enkäten | 4 | 1 | 3 | 241 |
| postadress, konto, bekräftat | 4 | 0 | 4 | inget svar |
| ordererkännande, lokale, representant | 4 | 0 | 4 | inget svar |
| _spridda ärenden, kluster under 4_ | 376 | 175 | 201 | — |

---

## Kategorier

### siffror, beställning, produkter

- **Antal totalt:** 250
- **Med svar:** 0
- **Utan svar:** 250
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### profil, siffror, blockerad

- **Antal totalt:** 141
- **Med svar:** 0
- **Utan svar:** 141
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### lägg, bud, siffror

- **Antal totalt:** 128
- **Med svar:** 0
- **Utan svar:** 128
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### oss, produkter, kommer

- **Antal totalt:** 67
- **Med svar:** 0
- **Utan svar:** 67
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, bokning, ner

- **Antal totalt:** 50
- **Med svar:** 1
- **Utan svar:** 49
- **Median svarslängd:** 228
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### säljaren, länk, knappen

- **Antal totalt:** 28
- **Med svar:** 0
- **Utan svar:** 28
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### epost, information, siffror

- **Antal totalt:** 27
- **Med svar:** 9
- **Utan svar:** 18
- **Median svarslängd:** 801
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### förfrågan, offert, söker

- **Antal totalt:** 24
- **Med svar:** 0
- **Utan svar:** 24
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, bids, finansiering

- **Antal totalt:** 13
- **Med svar:** 0
- **Utan svar:** 13
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### mottagare, fil, bifogad

- **Antal totalt:** 11
- **Med svar:** 6
- **Utan svar:** 5
- **Median svarslängd:** 288
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### siffror, moms, gata

- **Antal totalt:** 11
- **Med svar:** 2
- **Utan svar:** 9
- **Median svarslängd:** 224
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, betala, appen

- **Antal totalt:** 10
- **Med svar:** 0
- **Utan svar:** 10
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### kunden, gjorts, bedömning

- **Antal totalt:** 10
- **Med svar:** 0
- **Utan svar:** 10
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, top, varukorg

- **Antal totalt:** 9
- **Med svar:** 0
- **Utan svar:** 9
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### faktura, bifogad, fil

- **Antal totalt:** 9
- **Med svar:** 1
- **Utan svar:** 8
- **Median svarslängd:** 477
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### icloud, länk, bilder

- **Antal totalt:** 8
- **Med svar:** 0
- **Utan svar:** 8
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### säkerställa, era, länk

- **Antal totalt:** 8
- **Med svar:** 0
- **Utan svar:** 8
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### återbetalning, utfärdat, uppmärksam

- **Antal totalt:** 8
- **Med svar:** 0
- **Utan svar:** 8
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### order, siffror, följa

- **Antal totalt:** 7
- **Med svar:** 0
- **Utan svar:** 7
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### följesedel, sändningsnumret, sändning

- **Antal totalt:** 7
- **Med svar:** 0
- **Utan svar:** 7
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### lösenord, länk, återställa

- **Antal totalt:** 6
- **Med svar:** 0
- **Utan svar:** 6
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### verifieringskod, efterfrågat, verifiera

- **Antal totalt:** 6
- **Med svar:** 0
- **Utan svar:** 6
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### favoriter, såna, mejlnotiser

- **Antal totalt:** 6
- **Med svar:** 0
- **Utan svar:** 6
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### bilagor, eventuella, länk

- **Antal totalt:** 5
- **Med svar:** 4
- **Utan svar:** 1
- **Median svarslängd:** 209
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### email, addressees, contained

- **Antal totalt:** 5
- **Med svar:** 4
- **Utan svar:** 1
- **Median svarslängd:** 199
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### fordringar, skrivelsen, förfallit

- **Antal totalt:** 5
- **Med svar:** 0
- **Utan svar:** 5
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### ärende, siffror, miljön

- **Antal totalt:** 5
- **Med svar:** 1
- **Utan svar:** 4
- **Median svarslängd:** 241
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, finner, företagsinformation

- **Antal totalt:** 5
- **Med svar:** 0
- **Utan svar:** 5
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### bygga, post, dragkrok

- **Antal totalt:** 5
- **Med svar:** 5
- **Utan svar:** 0
- **Median svarslängd:** 783
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### ios, länk, helger

- **Antal totalt:** 5
- **Med svar:** 5
- **Utan svar:** 0
- **Median svarslängd:** 255
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### none, text, block

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### size, text, body

- **Antal totalt:** 4
- **Med svar:** 1
- **Utan svar:** 3
- **Median svarslängd:** 193
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### inlämning, bokningen, domän

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### tvist, länk, nöjd

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, companies, here

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### länk, siffror, epost

- **Antal totalt:** 4
- **Med svar:** 2
- **Utan svar:** 2
- **Median svarslängd:** 167
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### ärende, sekunder, enkäten

- **Antal totalt:** 4
- **Med svar:** 1
- **Utan svar:** 3
- **Median svarslängd:** 241
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### postadress, konto, bekräftat

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`

### ordererkännande, lokale, representant

- **Antal totalt:** 4
- **Med svar:** 0
- **Utan svar:** 4
- **Median svarslängd:** inget svar att mäta
- **Exempel:** se `scratchpad/kategorier-exempel.md`
---

## Appendix — versionshistorik (nyaste överst)

### 0.1.0 — 2026-08-26

Filen upprättad av `src/cluster.py`. Den skrivs om i sin helhet vid varje körning och versionshistoriken bärs därför av committarna, inte av den här listan.
