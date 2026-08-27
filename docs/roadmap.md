# Roadmap

**Version:** 0.2.1 · **Uppdaterad:** 2026-08-27 · **Implementerar** CLAUDE.md §10

Fasordning och grindar. En fas lämnas inte därför att arbetet i den är gjort, utan
därför att **Lars fattat fasens grindbeslut**. Grinden står i varje fas och är det
enda som flyttar projektet framåt.

Faserna är sekventiella. Det finns ingen fas som får hoppas över, och ingen kod
får implementera en genväg förbi en grind (CLAUDE.md §0, ramverksreglerna).

---

## SKUGGLÄGE

**Definition.** I skuggläge kör `respond.py` klassificering och generering FULLT
UT, loggar varje beslut till `logg/beslut.jsonl`, och **skickar ingenting**.

Skuggläget finns för att skilja två frågor som annars blandas ihop: om boten
väljer rätt, och om boten skickar rätt. I skuggläge besvaras bara den första, och
den besvaras mot verkliga inkommande mail i stället för mot en testmängd.

Vad skuggläget innebär konkret:

- Varje inkommande mail klassificeras, och kategorin loggas med confidence.
- Svaret genereras i sin helhet, inklusive prisinsättning och mallval, och loggas.
- Spärrarna körs och deras utfall loggas, RÖD eller GRÖN, med skäl.
- `messages.send` anropas ALDRIG. Inte till kunden, inte till en testadress, inte
  för att verifiera att sändningsfunktionen fungerar.
- Loggen är append-only och lyder under §6: hashade avsändare, inga adresser.

**Termen är svensk i repot.** Den engelska formen `shadow mode` ska inte
användas: den saknade definition ända till det här dokumentet och blev därför ett
obelagt begrepp i en motivering (CLAUDE.md:s appendixpost 0.3.0). Ett begrepp som styr sändvägen
ska ha exakt en form och exakt en definition, och den står här.

**Skuggläget är inte en flagga som kan glömmas bort.** Det upphör bara genom
grindbeslutet i fas 6, och `--send` aktiveras aldrig av kod eller default
(CLAUDE.md §6).

---

## Faser

### Fas 0 — Google · KLAR

GCP-projekt, OAuth desktop client, consent screen satt till Internal, scopes
`gmail.modify` och `gmail.send`.

**Grind:** passerad.

### Fas 1 — Repo · KLAR

Repo, `.gitignore`, CLAUDE.md, styrdokument, `.venv`, testsvit,
`scripts/sparr-prova.sh`.

**Grind:** passerad.

### Fas 2 — Auth

`src/auth.py` är byggd och testad mot fejkade credentials. Vad som återstår är
KÖRNINGEN: ingen `token.json` finns, och ingen auktorisering har skett.

**Grind:** Lars kör `.venv/bin/python -m src.auth --auktorisera` själv. Detta är
ett §10-stopp och görs aldrig av agenten. Fasen är passerad när `token.json`
finns och `src/auth.py` returnerar giltiga credentials utan att öppna webbläsare.

### Fas 3 — Mining

`src/mine.py` är byggd, kvotdimensionerad och testad mot fejkad Gmail-respons.
Återstår: provkörning med `--max-threads`, därefter full mining, därefter
extraktion av `data/par.jsonl` ur `data/tradar.jsonl`.

**Grind:** Lars godkänner att full mining körs, efter att en provkörning
redovisat trådstruktur och faktisk kvotåtgång. `data/tradar.jsonl` raderas när
`data/par.jsonl` är extraherad (§6).

### Fas 4 — Kategorier

`docs/kategorier.md` och `config/kategorier.yaml` upprättas ur `data/par.jsonl`.
Varje kategori får en hink: `auto`, `utkast` eller `aldrig`.
`scripts/kategoristatus.py` byggs, så att §12:s maskinproducerade statusrad går
att köra.

**Grind:** Lars beslutar kategorilistan och varje kategoris STARTHINK. Ingen
kategori startar i `auto`. Kod flyttar aldrig en kategori mellan hinkar
(§0, ramverksregel 2).

### Fas 5 — Mallar och spärrar

Mallarna byggs ur `data/par.jsonl`, alltså ur faktiska svar (§11).
`config/sparrar.yaml` och spärrlogiken byggs, och varje spärr registreras i
`docs/sparrar.md` med sin negativkontroll och sin redundans.
`config/priser.json` och `config/fakta.json` upprättas.

**Grind:** Lars godkänner varje mall ORDAGRANT, och varje ändring i
`config/sparrar.yaml`, `config/priser.json` och `config/fakta.json` är ett
§10-stopp. Hela fasen är sändväg och får full §7, ovillkorligt.

### Fas 5.5 — Utkastvyn

Webbvyn där Lars och Matte läser botens förslag och fäller omdöme om dem.
Beslutad av Lars i skiva 10. Hostas på `mailagent.dasher.se` enligt
beslutslogg #20, med inloggning enligt #21 och #22.

**BYGGS FÖRE SKUGGLÄGET, och det är hela skälet till att fasen finns.** Skuggläge
utan vy producerar en loggfil ingen läser. Fas 6 mäter klassificeringens
träffsäkerhet och spärrarnas utfall, och den mätningen kräver att någon faktiskt
går igenom förslagen post för post. Utan vyn blir `logg/beslut.jsonl` en fil som
växer medan grinden till fas 7 aldrig får sitt underlag.

**Fyra omdömen**, loggade åtskilt till `logg/omdomen.jsonl`, append-only:

| Omdöme | Betyder |
| --- | --- |
| `godkann` | Förslaget dugde som det stod. |
| `forbattra` | Förslaget dugde inte, och den redigerade texten är det som skulle skickats. |
| `forkasta` | Förslaget dugde inte, och ingen text ersätter det. |
| `neka` | Kategorin ska inte besvaras av boten alls. |

De fyra loggas ÅTSKILT och slås aldrig ihop till godkänt eller icke godkänt.
`forkasta` och `neka` ser lika ut i en tvågradig skala och betyder helt olika
saker: det första är ett dåligt svar på ett riktigt ärende, det andra är att
ärendet inte hör hemma hos boten.

**`forbattra` bär den redigerade texten och skriver ett nytt par till
`data/par.jsonl`.** Det är den enda av de fyra som tränar rösten. De andra tre
säger vad som var fel; bara den här säger vad som skulle stått i stället, och
§11 kräver att mallarna vilar på faktiska svar och inte på text skriven från
grunden.

**SPÄRRFÄLLDA FÖRSLAG VISAS UTAN TEXTFÄLT.** Vyn visar vilken spärr som fällde
och varför. Ingen redigeringsruta, ingen skicka-knapp, ingen väg vidare från den
posten.

Skälet är §9.1. Den förbjuder att ett fällt mails text skrivs om tills spärren
släpper igenom det, och en redigeringsruta bredvid ett fällt förslag gör det
förbudet till ett klick. Spärren fällde mailet därför att något i det inte gick
att verifiera, eller därför att tråden inte var vad klassificeraren trodde, och
ingen omskrivning rör den orsaken.

**Detta är sändväg och får full §7, ovillkorligt.** Vyn avgör vad en människa
ser och kan göra med ett förslag, och därmed om och med vilket innehåll ett mail
senare lämnar servern.

**VYN SKICKAR ALDRIG MAIL. Den skriver omdömen.** Sändning sker först i fas 7,
genom `respond.py`, och styrs av `--send` enligt §6 och §10. I fas 6 anropas
`messages.send` ALDRIG, enligt skugglägets definition överst i det här
dokumentet. Att lägga en skicka-knapp i vyn vore att flytta sändvägen till ett
gränssnitt utan de stopp §10 föreskriver.

**Grind:** Lars beslutar att omdömesvolymen räcker. Talet sätts inte i förväg,
eftersom det beror på hur många kategorier som visar sig bära underlag, och
skiva 9 mätte att bara två kategorier når tio par med svar.

### Fas 6 — Skuggläge

`respond.py` körs i skuggläge enligt definitionen överst. Beslutsloggen samlas
och läses. Klassificeringens träffsäkerhet mäts mot verkliga mail, och spärrarnas
utfall granskas post för post.

**Grind:** Lars beslutar att skuggläget upphör, efter att ha läst
`logg/beslut.jsonl` och funnit klassificeringen och spärrutfallen godtagbara.
Beslutet fattas per kategori, inte för boten som helhet.

### Fas 7 — Auto

Kategorier befordras från `utkast` till `auto`, en i taget. Första skarpa
sändningen är manuell.

**Grind:** varje befordran till `auto` är ett eget §10-stopp och ett eget
uttryckligt beslut av Lars. En körning som skulle skicka fler än 1 mail är också
ett §10-stopp, och det talet är ett öppet antagande som revideras när mining
visat dagsvolymen.

---

## Appendix — versionshistorik (nyaste överst)

### 0.2.1 — 2026-08-27

**En falskhet om sändvägen struken.** 0.2.0 skrev "Sändning sker i fas 6 och fas
7". Fas 6 är SKUGGLÄGE, och det här dokumentets egen definition överst säger att
`messages.send` anropas ALDRIG där, inte till kunden, inte till en testadress.
Sändning sker först i fas 7. Meningen låg i ett stycke som texten själv utropar
till sändväg, och §7:s dokumentdetaljundantag omfattar aldrig sändvägen.

**En paragrafhänvisning rättad i samma stycke.** Regeln att `--send` bara
aktiveras av Lars explicita val står i §6, inte §5.

Rättad falskhet i sändvägstext ⇒ PATCH.

### 0.2.0 — 2026-08-27

**Fas 5.5 UTKASTVYN tillkommer**, mellan mallar och skuggläge, på beslut av Lars
i skiva 10.

Fasen ligger FÖRE skuggläget därför att skuggläge utan vy producerar en loggfil
ingen läser. Den bär fyra omdömen loggade åtskilt, varav `forbattra` är den enda
som tränar rösten eftersom den ensam skriver ett nytt par till `data/par.jsonl`.

**Spärrfällda förslag visas utan textfält**, vilket är §9.1 i gränssnittsform: en
redigeringsruta bredvid ett fällt förslag gör förbudet mot att skriva om texten
tills spärren släpper till ett klick. Fasen är sändväg och får full §7.

Ingen kod skrevs i skiva 10. Fasen är beslutad, inte byggd.

Ny fas ⇒ MINOR.

### 0.1.0 — 2026-08-26

Dokumentet upprättat på instruktion av Lars i skiva 3. SKUGGLÄGE definieras här
och ersätter det odefinierade `shadow mode`, som fanns i CLAUDE.md 0.3.0:s
appendixpost som motivering till att sänka §10:s gräns per körning utan att någon
kunde säga vad begreppet innebar.
