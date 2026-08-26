# Beslutslogg

**Version:** 0.1.1 · **Uppdaterad:** 2026-08-26 · **Speglar:** CLAUDE.md 0.2.0

Sekventiell och append-only. Nummer återanvänds aldrig. En post rättas genom en
ny post som upphäver den, aldrig genom att den gamla skrivs om.

---

## #1 — Mining hämtar hela tråden, och pacingen dimensioneras mot per-användarkvoten

**Datum:** 2026-08-26 · **Berör:** `src/mine.py`

**Beslut.** `src/mine.py` hämtar varje tråd med `threads.get` i ett anrop i
stället för `messages.get` per meddelande, och sprider ut anropen mot Gmails
per-användarkvot.

**Underlag.** Kvottabellen är avläst denna dag ur
`https://developers.google.com/workspace/gmail/api/reference/quota`. Sidan anger
"Last updated 2026-07-31 UTC" och att gränserna uppdaterades "As of May 1, 2026".
GCP-projektet `autostockholm-mailbot` är skapat efter det datumet och lyder under
dessa värden:

| Post | Värde |
| --- | --- |
| `threads.list` | 10 kvotenheter |
| `threads.get` | 40 kvotenheter |
| Per minut per projekt | 1 200 000 kvotenheter |
| Per minut per användare per projekt | 6 000 kvotenheter |

Boten kör mot en enda brevlåda, så per-användargränsen binder långt före
projektgränsen. Pacingen dimensioneras därför mot 6 000 enheter per minut.

**Marginalen är ett val, inte ett avläst värde.** `ANDEL_AV_KVOT = 0.5` i
`src/mine.py` är satt för att Matte och Lars egna Gmail-klienter och mobiler
förbrukar ur samma per-användarpott, och en mining-körning får inte tränga ut
dem. Talet har inget mätt underlag och ska revideras när den första körningen
visat faktisk samtidig förbrukning. Öppet antagande, i samma anda som §10:s
gräns på 5 mail per körning.

**Konsekvens.** Halva potten är 3 000 enheter per minut, och 40 enheter per
`threads.get` ger 75 `threads.get` per minut. Det är ett övre gränsvärde för
hämtningsdelen, inte för körningen som helhet: `threads.list` förbrukar ur samma
pott, så den faktiska trådtakten ligger strax under. Båda talen är avlästa ur
`src/mine.py` och låsta av `tests/test_mine.py::test_pacingen_dimensioneras_mot_anvandarkvoten`.
En större brevlåda tar därför tid att mina, och det är avsiktligt.

**Alternativ som valdes bort.** `messages.get` per meddelande ger samma innehåll
men ett anrop per meddelande i stället för ett per tråd. Dyrare i både kvot och
väggklocka utan att tillföra något.

---

## #2 — Auktorisering öppnar aldrig webbläsare av sig själv

**Datum:** 2026-08-26 · **Berör:** `src/auth.py`

**Beslut.** `hamta_credentials()` har `tillat_webblasare=False` som förval.
Ordningen är återanvänd, förnya, auktorisera. En giltig token returneras utan
att `token.json` skrivs om. En utgången token med `refresh_token` förnyas tyst.
Först när ingetdera går krävs webbläsarflödet, och då bara om anroparen
uttryckligen begärt det.

**Skäl.** CLAUDE.md §10 gör första sändningen i en ny miljö till Lars beslut, och
första auktoriseringen är den grind som öppnar den miljön. Ett förval som öppnar
webbläsaren skulle låta vilket skript som helst dra igång auktoriseringen som
sidoeffekt. `src/mine.py` anropar därför alltid med `tillat_webblasare=False` och
faller med `AuthFel` i stället för att auktorisera på egen hand.

**Konsekvens.** Auktorisering sker med ett eget, uttryckligt kommando:
`.venv/bin/python -m src.auth --auktorisera`.

---

## Appendix — versionshistorik (nyaste överst)

### 0.1.1 — 2026-08-26

Rättelser i #1 efter granskning, per post:

- Kvottabellens minutgränser bar inte kvalifikationen "per projekt" som
  källsidan skriver ut. Rättat till "per minut per projekt" respektive "per minut
  per användare per projekt".
- Konsekvensstycket kallade 75 trådar per minut för "taket" trots att
  `threads.list` förbrukar ur samma pott. Omformulerat till övre gränsvärde för
  hämtningsdelen. Talet 75 är omräknat och avläst på nytt enligt
  omskrivningsregeln, inte ärvt genom omformuleringen.

**Om append-only och det här passet.** Rättelserna gjordes innan loggen
committades första gången, alltså på en post som aldrig funnits i historiken.
Ingen committad post har skrivits om. Belägget är `git show
820c2ce:docs/beslutslogg.md`: där bär post #1 redan sin rättade lydelse, både
kvottabellens "Per minut per användare per projekt" och konsekvensstyckets "övre
gränsvärde". Huruvida regeln på raderna 5 och 6 ska omfatta även
förcommit-redigeringar är en öppen fråga till Lars; som den står ger den inget
svar, och det här passet har valt den tolkning som historiken kan bekräfta.

Inga beslut ändrade, bara formuleringen av deras underlag ⇒ PATCH.

### 0.1.0 — 2026-08-26

Loggen upprättad vid första arkitekturbeslutet, enligt CLAUDE.md:s versionshuvud.
Posterna #1 och #2 skrivna i samma pass som `src/mine.py` och `src/auth.py`.
