# Mining-logg

**Version:** 0.3.1 · **Uppdaterad:** 2026-08-26 · **Implementerar** CLAUDE.md §8

Varje körning av `src/mine.py` mot brevlådan skrivs in i tabellen nedan av koden,
aldrig för hand. Kolumnerna är de §8 kräver: datum, Gmail-query, antal träffar och åtgången
kvot. Anropsräknaren finns med därför att åtgången kvot annars inte går att
härleda till vad som faktiskt kördes.

Åtgången kvot räknas i kvotenheter enligt tabellen i beslutslogg #1, och
inkluderar anrop som fällts av kvottaket, eftersom de kostar kvot även när de
inte ger något svar.

Statuskolumnen skiljer den färdiga körningen från den avbrutna. En körning som
faller loggas ändå, eftersom kvoten är förbrukad oavsett utfall och §8 kräver att
åtgången står här innan nästa körning startas. `AVBRUTEN` betyder också att
`data/tradar.jsonl` INTE uppdaterades: det halva resultatet ligger kvar som
`data/tradar.jsonl.delvis`.

**Inga adresser, ämnesrader eller trådinnehåll skrivs här.** Dokumentet är
committat och lyder under CLAUDE.md §6.

| Datum | Query | Trådar | Anrop | Kvotenheter | Status |
| --- | --- | --- | --- | --- | --- |
| 2026-08-26 11:38 UTC | `in:sent` | 50 | 51 | 2010 | fullständig |
| 2026-08-26 14:32 UTC | `in:sent` | 555 | 561 | 22260 | fullständig |
| 2026-08-26 16:42 UTC | `-in:sent minus tråd-ID i tradar.jsonl` | 1604 | 1623 | 64350 | fullständig |

---

## Appendix — versionshistorik (nyaste överst)

### 0.3.1 — 2026-08-26

Inledningen sa att raden "appendas här av koden". Efter fixen i `7301f90`
appendas den inte, den skrivs in sist i tabellen. Rättat. Ingen körning loggad
av den här ändringen. ⇒ PATCH.

### 0.3.0 — 2026-08-26

**`Speglar` ersätts av en sektionspekare utan versionsnummer**, beslut av Lars i
skiva 3. Synkposterna 0.2.1 till 0.2.3 i den här filen är just de innehållslösa
poster som ändringen finns för att slippa. Ingen körning loggad. ⇒ MINOR.

### 0.2.3 — 2026-08-26

Korsreferenssynk till CLAUDE.md 0.3.2. Ingen körning loggad. ⇒ PATCH.

### 0.2.2 — 2026-08-26

Korsreferensen följer med CLAUDE.md till 0.3.1. Ingen körning loggad.

Posten redovisar också att 0.2.1:s appendixpost fick ett stavfel rättat på plats
i `b03139d`, efter att den committats, utan versionshöjning. Det bryter mot §8 på
samma sätt som de större fallen i samma commit, och står här i stället för att
tigas ihjäl därför att det är litet. Ren synk och en formrättelse ⇒ PATCH.

### 0.2.1 — 2026-08-26

Korsreferensen i versionshuvudet följer med CLAUDE.md till 0.3.0. Inget innehåll
ändrat, ingen kolumn rörd, ingen körning loggad. Ändringen görs därför att §12:s
färskhetstriangel kräver att korsreferenserna är överens: en pekare mot 0.2.0
hade gjort triangeln oense från och med den här skivan. Ren synk ⇒ PATCH.

*Upphävt i 0.3.0: §12 heter numera färskhetskontrollen, har två signaler i
stället för tre, och kräver inte längre att korsreferenserna är överens. Kravet
den här posten åberopar finns inte kvar.*

### 0.2.0 — 2026-08-26

Statuskolumn tillkommer, och med den stycket om vad `AVBRUTEN` innebär för
`data/tradar.jsonl`. Skälet är att `src/mine.py` nu loggar även en körning som
faller, i stället för att en förbrukad kvot försvinner tyst. Ny kolumn ⇒ MINOR.

### 0.1.0 — 2026-08-26

Dokumentet upprättat i samma skiva som `src/mine.py`, eftersom koden appendar hit
enligt §8 och inte ska skapa styrdokument på egen hand. Ingen körning loggad:
skivan rörde aldrig brevlådan.
