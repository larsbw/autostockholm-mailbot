# CLAUDE.md — autostockholm-mailbot

**Version:** 1.1.0 · **Uppdaterad:** 2026-09-25

Beteenderegler för AI-agenten i autostockholm-mailbot. Läses vid varje
sessionsstart.

Ersätter 0.12.14, som var ärvd från tradingbot-v2 och skriven för ett system där
ett fel kostar kapital per sekund. Den förlagan var fel. Det här systemet skriver
mail till verkstadskunder som annars ofta inte får något svar alls, och ett fel
kostar ett pinsamt mail som en människa redan läst innan det gick ut.

## 0. Vad systemet gör

Läser info@autostockholm.se. Sorterar bort maskinmail. Klassificerar det som är
kvar. För a-traktorförfrågningar: slår upp registreringsnumret på
biluppgifter.se, avgör om bilen går att bygga om, och skriver ett svarsutkast.

Utkastet hamnar i en granskningsvy. Lars läser det. Ingenting skickas
automatiskt förrän han beslutar att en kategori får det.

- **Repo:** `larsbw/autostockholm-mailbot`
- **Brevlåda:** info@autostockholm.se, Google Workspace
- **Stack:** Python, stdlib där det går. Gmail API, Anthropic API.
- **Styrdokument:** `docs/roadmap.md`, `docs/beslutslogg.md`, `docs/sparrar.md`

**Fyra regler som aldrig bryts:**

1. Inget mail skickas vars kategori inte står i `auto` i `config/kategorier.yaml`.
2. Ingen kategori flyttas till `auto` av kod. Bara av Lars.
3. Boten påstår aldrig ett faktum om ett fordon som inte kommer ur ett uppslag,
   och aldrig ett pris som inte står i `config/priser.json`.
4. `logg/beslut.jsonl` är append-only.

## 1. Fråga när något är oklart

Anta inte. Finns flera tolkningar, presentera dem. Finns ett enklare sätt, säg
det. Push-backa när det är motiverat.

Gäller särskilt Gmail API och biluppgifter.se: slå upp beteendet, gissa inte.

## 2. Minsta lösningen

Minsta kod som löser problemet. Inga abstraktioner för engångskod, ingen
flexibilitet som inte efterfrågats, ingen felhantering för omöjliga scenarier.

Frågan att ställa: skulle en senior säga att det här är överkomplicerat?

## 3. Rör bara det du måste

Förbättra inte angränsande kod, refaktorera inte det som fungerar. Städa orphans
som dina egna ändringar skapade, inget annat.

## 4. Verifiera det som kan gå fel i drift

Skriv test för det som skickar mail, det som läser fordonsdata och det som
avgör om ett svar får gå ut. Skriv inte test för att höja ett antal.

Ett test som inte kan bli rött är värre än inget test. Går en spärr att ta bort
med hela sviten grön, mäter testet ingenting.

## 5. Skeppa

En uppgift är inte klar förrän origin/main bär den. `git status`, commit, push,
verifiera att HEAD är lika med origin/main. Fråga inte om lov.

Sista raden i varje rapport är commit-SHA:n.

**Sändning är aldrig del av att skeppa.** `respond.py --send` körs på Lars
uttryckliga instruktion, aldrig som default, aldrig för att pröva att koden
fungerar.

## 6. Hemligheter och persondata

Skriv aldrig ut en hemlighet i upplöst form.

Kundmail bär namn, adresser, registreringsnummer och telefonnummer. De förekommer
aldrig i `docs/`, i commit-meddelanden eller i något som pushas. `data/` och
`logg/` är gitignorerade och är enda platsen för kundtext.

`scripts/persondatakontroll.py` kör som pre-commit-hook.

Undantag beslutat av Lars. Filer i scratchpad/ får innehålla kundnamn, registreringsnummer, telefonnummer och fullständiga svarstexter. Scratchpad ligger bara lokalt hos Lars och används för rapporter och BESLUT-filer.

## 7. Granskning

**Kod som kan påverka ett utgående mail granskas av en oberoende granskare
innan den skeppas.** Hit hör spärrarna, klassificeringen, fordonsuppslaget,
generatorn och mallarna. En omgång. Kvarstår fynd efter den: rätta dem och
skeppa med statusen utskriven.

**All annan kod: ingen granskningsomgång.** Skeppa och rapportera vad som
byggdes.

**Dokument och text om kod: ingen granskningsomgång.** Skeppa.

Ett känt falskt påstående rättas alltid, oavsett nivå.

### 7.1 Pröva att en spärr biter

En spärr som påstår sig hindra något ska gå att fälla. Ta bort den beslutande
raden, kör sviten, och kontrollera att den blir röd. Blir den inte det mäter
testet ingenting.

Är spärren redundant, alltså om två rader vaktar samma sak, fäll båda. Ett
grönt utfall efter att en av dem fällts betyder inget.

Fäll en rad i taget när du vill veta om just den raden bär. Fäller du två
tillsammans och får rött vet du bara att minst en av dem bär.

`scripts/sparr-prova.sh` gör det säkert. Återställ och kontrollera att
arbetsträdet är oförändrat.

### 7.2 Skriv inga tal du inte läst

Ett tal i en rapport, ett dokument eller ett utgående mail är antingen avläst i
den här sessionen eller utelämnat. Ingen tredje möjlighet.

Skriver du om en mening blir dess tal oläst igen. Kontrollera dem på nytt.

Räkna inte arbetsförlopp: hur många granskningsvarv, hur många rättelser, hur
många instanser av ett mönster. Sådana tal går inte att verifiera mot repot och
blir falska vid nästa ändring.

## 8. Dokument

`docs/` underhålls av Claude Code på instruktion från chatten.

Skriv kort. Ett dokument som ingen läser skyddar ingenting. Arkitekturbeslut går
i `docs/beslutslogg.md`, append-only.

## 9. Bash

Läs filer med `Read`, sök med `Grep` och `Glob`. Inte `cat`, `sed` eller `grep`
i Bash.

Undvik heredocs, backticks och expansioner på kommandoraden. De har ätit innehåll
ur committade dokument fyra gånger i det här repot.

Flerradiga commit-meddelanden skrivs till `.git/COMMIT_MSG` med Write, sedan
`git commit -F`.

### 9.1 En fälld spärr är ett stopptecken

Fäller en spärr ett mail eller ett commit-meddelande: stanna och fråga Lars.
Skriv aldrig om texten tills den slinker igenom, sänk aldrig en tröskel, flytta
aldrig en kategori för att komma runt spärren.

Spärren fällde av en orsak, och ingen av de tre åtgärderna rör orsaken.

## 10. Stanna och fråga Lars

- Första sändningen i en ny miljö, även till en egen testadress
- Att flytta en kategori mellan hinkar
- Ändring i `config/sparrar.yaml`, `config/priser.json` eller `config/fakta.json`
- Att sänka confidence-tröskeln
- En körning som skulle skicka mer än ett mail
- Nytt OAuth-scope, ny avsändaradress

Vid tvetydig instruktion som rör sändning: fråga vad som menas.

## 11. Hur mailen ska låta

- **Rösten byggs ur `data/par.jsonl`**, alltså ur svar Matte faktiskt skickat.
- **Första person plural.** Vi, oss, vår. Aldrig jag eller man.
- **Inga kollegor.** Matte driver verkstaden själv.
- **Inga tankstreck eller bindestreck som skiljetecken.**
- **Aldrig "friverkstad".** Alltid "fristående verkstad".
- **Inga konkurrentnamn.**
- **Bokningsförfrågningar bekräftas positivt.** En kund som frågar om ni kan ta
  emot bilen i juni ska få ja och ett telefonnummer, inte en hänvisning.
- **Fråga inte efter ett registreringsnummer som redan står i mailet.**
- **Inga påståenden om vad Auto Stockholm har eller erbjuder** utöver vad som
  står i `config/`.

## 12. Rapporten

Varje avstämning får en fil i den gitignorerade `scratchpad/`:

```
scratchpad/Mailbot-CC-report-YYYYMMDD-HHMM.md
```

Tidsstämpeln ur `date -u`, aldrig för hand. Första raden tidsstämpel, andra
HEAD-SHA. Kontrollera att filen skrevs innan du säger att den gjorde det.

Efter varje `messages.send`: läs tillbaka message-ID:t och återge det. Går det
inte att bekräfta, säg det.

### 12.1 Beslutsfil vid väntan på besked

Innan ett pass stannar och väntar på besked från Lars: skriv en fil i
`scratchpad/`, namnet `Mailbot-CC-BESLUT-ÅÅÅÅMMDD-HHMM.md`, tidsstämpel ur
`date -u`. Filen ska innehålla vad som är gjort hittills, exakt vilka beslut
som behövs, och vad du föreslår. Lars kör flera CC-fönster samtidigt och ser
bara via filerna om hans input behövs.

Varje pass avslutas dessutom alltid med rapportfilen enligt ovan. Ingen fil,
inget klart.

---

**Reglerna fungerar om:** noll mail till fel mottagare, noll påhittade priser
eller fordonsfakta, noll kategorier befordrade utan Lars beslut, noll persondata
i git-historiken, och en bot som faktiskt svarar på mail.

---

## Appendix

### 1.1.0 — 2026-09-25

§12 fick en underrubrik, 12.1: en beslutsfil (`Mailbot-CC-BESLUT-*.md`) skrivs
till `scratchpad/` innan ett pass stannar och väntar på Lars, utöver
rapportfilen som redan avslutar varje pass. Lars kör flera CC-fönster
parallellt och behöver kunna se via filerna, utan att öppna varje fönster,
om ett pass väntar på honom.

### 1.0.0 — 2026-09-14

Omskriven från grunden. 0.12.14 var 1980 rader ärvda från tradingbot-v2, ett
system där ett fel kostar kapital per sekund. Mappningen av kapitalvägen till
sändvägen var Lars fel och gjordes i skiva 1.

**Vad som ändrades:**

Granskningsgrinden gick från tre varv med uttömmande formkrav till en omgång på
det som kan påverka ett utgående mail och noll på allt annat. Fyrtiotvå skivor
producerade nästan uteslutande underkännanden, och merparten av fynden låg i
meningar om kod.

Dokumentdetaljundantaget, vakuitetsstegets formkrav, mutationstabellernas
redovisningsform, färskhetskontrollen, rättelsetaktregeln och kraven på
appendixposter och versionshuvuden är strukna. De beskrev hur arbete redovisas,
inte vad systemet gör, och de genererade mer fynd än de förhindrade.

§7.1 och §7.2 står kvar i kort form. De är de två regler som faktiskt fångade
defekter i sändvägen: en spärr som inte går att fälla mäter ingenting, och ett
tal som inte är avläst är påhittat.

§11 har växt med de regler som kom ur att Lars läste botens utkast: inga
kollegor, bokningar bekräftas positivt, fråga inte efter ett regnr som redan
står i mailet.

**Vad som inte ändrades:** de fyra ramverksreglerna, §6 om persondata, §9.1 om
att en fälld spärr är ett stopptecken, och §10:s lista över vad som kräver Lars
beslut.

**Luckorna 1 till 58 i `docs/sparrar.md` står kvar som de är.** Ingen av dem
stängs av den här ändringen, och ingen av dem öppnas.
