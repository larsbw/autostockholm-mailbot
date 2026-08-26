# Kategoriförslag

**Version:** 0.2.0 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §0

Maskinproducerad av `src/kategorisera.py` med `claude-sonnet-4-6`. **Skriv inte i den här filen för hand**: den skrivs om vid nästa körning.

Kategorierna är inte satta i förväg. Modellen fick ingen lista att välja ur, utan ombads namnge vad kunden vill med två till fyra ord. Kategorierna faller ut ur att många texter fick samma namn.

**INGEN HINKTILLDELNING FÖRESLÅS.** Vilken kategori som hamnar i `auto`, `utkast` eller `aldrig` är Lars beslut i fas 4:s grind. Ramverksregel 2 i CLAUDE.md §0 säger att ingen kategori flyttas av kod.

**CITATEN STÅR INTE HÄR.** De skrivs till `scratchpad/kategorier-exempel.md`, som är gitignorerad. Ett namn som kunden skrivit med gemener i löpande text går inte att hitta med någon heuristik, och §6 tillåter ingen persondata i `docs/`.

Endast MÄNSKLIGA inkommande texter ingår, enligt `src/klassa_maskin.py`. Maskinmail är bortsållat på huvuden.

---

## Kategorier

Texter i underlaget: 795

| Kategori | Totalt | Med svar | Utan svar |
| --- | --- | --- | --- |
| inget kundärende | 547 | 52 | 495 |
| oklart | 38 | 31 | 7 |
| boka rekond | 13 | 1 | 12 |
| boka biltvätt | 10 | 0 | 10 |
| boka service | 7 | 7 | 0 |
| boka rekonditionering | 7 | 2 | 5 |
| fråga om a-traktor ombyggnad | 6 | 6 | 0 |
| boka däckbyte | 4 | 0 | 4 |
| boka rekondtid | 3 | 0 | 3 |
| boka tid | 2 | 2 | 0 |
| godkänna offert | 2 | 1 | 1 |
| fråga om starttid | 2 | 2 | 0 |
| fråga om epa-konvertering | 2 | 2 | 0 |
| boka bromskontroll | 2 | 0 | 2 |
| boka oljebyte | 2 | 0 | 2 |
| fråga om pris | 2 | 2 | 0 |
| fråga om a-traktor konvertering | 2 | 2 | 0 |
| bygga om till a-traktor | 2 | 2 | 0 |
| avboka bokning | 2 | 0 | 2 |
| efterfråga bromsoffert | 1 | 1 | 0 |
| laga punkterat däck | 1 | 0 | 1 |
| fråga om rekondpris | 1 | 1 | 0 |
| byta spiralfjädrar | 1 | 0 | 1 |
| fråga om övningskörningsbil och reparation | 1 | 1 | 0 |
| fråga om lackskydd | 1 | 1 | 0 |
| boka servicebesök | 1 | 1 | 0 |
| fråga om pris och innehåll för service | 1 | 1 | 0 |
| fråga om tändstiftsbyte | 1 | 1 | 0 |
| boka besökstid | 1 | 1 | 0 |
| boka tid för reparation | 1 | 1 | 0 |
| fråga om service | 1 | 1 | 0 |
| fråga om pris och bokning | 1 | 1 | 0 |
| boka tid sidospegel | 1 | 1 | 0 |
| offert på a-traktorombyggnad | 1 | 1 | 0 |
| ansöka om praktikplats | 1 | 1 | 0 |
| boka praktikintervju | 1 | 1 | 0 |
| omvandling till a-traktor med dragkrok | 1 | 1 | 0 |
| montera dragkrok | 1 | 1 | 0 |
| fråga om tidplan | 1 | 1 | 0 |
| boka ombyggnation av bil | 1 | 1 | 0 |
| fråga om inredningsanpassning | 1 | 1 | 0 |
| efterfråga betalningsuppgifter | 1 | 0 | 1 |
| fråga om pris på modifiering | 1 | 1 | 0 |
| fråga om trimning och pris | 1 | 1 | 0 |
| reklamera bromsrenovering | 1 | 0 | 1 |
| bestrida faktura | 1 | 1 | 0 |
| boka tvätt och sanering | 1 | 0 | 1 |
| fråga om konvertering | 1 | 1 | 0 |
| boka bromsservice | 1 | 0 | 1 |
| efterfråga komplettering | 1 | 1 | 0 |
| fråga om rekond med takbox | 1 | 1 | 0 |
| reklamera skada efter service | 1 | 1 | 0 |
| fråga om atraktorsombyggnad | 1 | 1 | 0 |
| fråga om ombyggnadstid | 1 | 1 | 0 |
| offerta bilombyggnad | 1 | 1 | 0 |
| begära offert på reparationer | 1 | 1 | 0 |
| begära kvitto | 1 | 0 | 1 |
| fråga om a-traktorombyggnad och tillval | 1 | 0 | 1 |
| boka hjulbalansering | 1 | 0 | 1 |
| omboka rekondtid | 1 | 1 | 0 |
| fråga om pris sätesreparation | 1 | 1 | 0 |
| köpa och installera tillbehör | 1 | 1 | 0 |
| fråga om servicepris | 1 | 1 | 0 |
| boka servicetid | 1 | 1 | 0 |
| konvertering enligt regelverk | 1 | 1 | 0 |
| fråga om ombyggnadspris | 1 | 1 | 0 |
| boka akut bilservice | 1 | 0 | 1 |
| fråga om bagageutrymme ombyggnad | 1 | 1 | 0 |
| fråga om dörrlåskonvertering | 1 | 1 | 0 |
| fråga om pris på service och ac-påfyllning | 1 | 1 | 0 |
| boka service tid | 1 | 1 | 0 |
| boka inlämningstid | 1 | 1 | 0 |
| boka tid för lampbyte | 1 | 1 | 0 |
| avboka verkstadsbesök | 1 | 1 | 0 |
| boka tid för installation | 1 | 1 | 0 |
| meddela betalningsplan | 1 | 1 | 0 |
| boka bromslagningstid | 1 | 1 | 0 |
| fråga om a-traktorombyggnad | 1 | 1 | 0 |
| fråga om ac-service | 1 | 1 | 0 |
| boka däckmontering | 1 | 0 | 1 |
| åtgärda anmärkningar efter besiktning | 1 | 1 | 0 |
| fråga om pris rollbur | 1 | 1 | 0 |
| bekräfta bokning och fråga om parkering | 1 | 1 | 0 |
| fråga om adress och nyckelinlämning | 1 | 1 | 0 |
| bygga om a-traktor | 1 | 1 | 0 |
| fråga om pris och tid för epa-konvertering | 1 | 1 | 0 |
| begära kostnadsförslag reparation | 1 | 1 | 0 |
| efterfråga kostnadsförslag | 1 | 1 | 0 |
| byta blinkers till gula | 1 | 0 | 1 |
| fråga om a-traktorkonvertering | 1 | 1 | 0 |
| fråga om pris reparation | 1 | 1 | 0 |
| boka tid för bilhämtning | 1 | 1 | 0 |
| offert och frågor om ombyggnad | 1 | 1 | 0 |
| fråga om prisskillnad på rekond | 1 | 1 | 0 |
| boka tid för a-traktorkonvertering | 1 | 1 | 0 |
| boka montering av dragkrok | 1 | 1 | 0 |
| fråga om a-traktor omregistrering | 1 | 1 | 0 |
| fakturera för rekonstruktion | 1 | 1 | 0 |
| fråga om produktkompatibilitet | 1 | 1 | 0 |
| avboka rekondtid | 1 | 0 | 1 |
| konvertera och modifiera bil | 1 | 1 | 0 |
| boka reparation och hjulinställning | 1 | 0 | 1 |
| ändra eller kontrollera bokning | 1 | 1 | 0 |
| ge positiv feedback | 1 | 1 | 0 |
| fråga om rekond och lackförsegling | 1 | 1 | 0 |
| fråga om bilförmedling | 1 | 0 | 1 |
| boka tid tidigare | 1 | 1 | 0 |
| bekräfta avtalad tid | 1 | 1 | 0 |
| fråga om lackbehandling | 1 | 1 | 0 |
| fråga om atraktorombyggnad | 1 | 1 | 0 |
| fråga om ombyggnadskrav | 1 | 1 | 0 |
| fråga om offert för omprogrammering av ecu | 1 | 1 | 0 |
| inredning och tillbehör | 1 | 1 | 0 |
| fråga om pris på vinterdäck | 1 | 1 | 0 |
| begära arbetsorder | 1 | 1 | 0 |
| boka tid för fjädringsbyte | 1 | 1 | 0 |
| efterfråga offert på fjädring | 1 | 1 | 0 |
| boka felsökningstid | 1 | 0 | 1 |
| fråga om pris a-traktorombyggnad | 1 | 1 | 0 |
| fråga om däckförvaring | 1 | 1 | 0 |
| begära marknadsföringsmaterial | 1 | 1 | 0 |
| konvertera till tvåhjulsdrift | 1 | 1 | 0 |
| svara på ombyggnadsförfrågan | 1 | 1 | 0 |
| fråga om rekonditioineringstjänst | 1 | 0 | 1 |
| fråga om pris invändig rekond | 1 | 1 | 0 |
| boka invändig bilrengöring | 1 | 1 | 0 |
| fråga om inlämningstid | 1 | 1 | 0 |
| klaga på pris | 1 | 1 | 0 |
| fråga om lådbyggnation och pris | 1 | 1 | 0 |
| fråga om batteripris | 1 | 1 | 0 |
| fråga om rekondpaket | 1 | 0 | 1 |
| avisera förälder kontaktar verkstad | 1 | 1 | 0 |
| beställa och montera tillbehör | 1 | 1 | 0 |
| ombygnad till a-traktor | 1 | 1 | 0 |
| boka polering och vaxning | 1 | 0 | 1 |
| fråga om pris växellådsolja | 1 | 0 | 1 |
| konvertera bil till epa | 1 | 1 | 0 |
| fråga om epa-byggande | 1 | 1 | 0 |
| fråga om epa-ombyggnad | 1 | 1 | 0 |
| fråga om kontaktuppgifter | 1 | 1 | 0 |
| klaga på rekondkvalitet | 1 | 0 | 1 |
| fråga om pris på rengöring | 1 | 0 | 1 |
| boka invändig tvätt | 1 | 0 | 1 |
| avboka servicebokning | 1 | 0 | 1 |
| boka tvätt och glasförsegling | 1 | 0 | 1 |
| byta batteri i vcm-enhet | 1 | 0 | 1 |
| fråga om pris och tjänster | 1 | 0 | 1 |
| boka rekonditioning | 1 | 0 | 1 |
| boka tid bromsservice | 1 | 0 | 1 |
| offert och bokning av spindelledbyte | 1 | 0 | 1 |
| fråga om kampanjpris | 1 | 0 | 1 |
| bestrida felaktig faktura | 1 | 0 | 1 |
| begära serviceprotokoll | 1 | 0 | 1 |
| avboka bokad service | 1 | 0 | 1 |
| fråga om delbetalning | 1 | 0 | 1 |
| boka handtvätt | 1 | 0 | 1 |
| boka däckbyte och tvätt | 1 | 0 | 1 |
| boka tid för däckbyte | 1 | 0 | 1 |
| boka däckbyte och däckhotell | 1 | 0 | 1 |

---

## Appendix — versionshistorik (nyaste överst)

### 0.2.0 — 2026-08-26

Klustringen ersatt av kategorisering med Anthropic API. TF-IDF grupperade på avsändarens mall i stället för på kundens ärende, och det mänskliga materialet hamnade i restposten. Se beslutslogg #9.

### 0.1.0 — 2026-08-26

Filen upprättad av `src/cluster.py`.
