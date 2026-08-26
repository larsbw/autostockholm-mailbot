# Incidentlogg

**Version:** 0.1.0 · **Uppdaterad:** 2026-08-26 · **Speglar:** CLAUDE.md 0.3.0 §0 ·
beslutslogg: ingen post rör incidenterna ännu

Varje regel som bärs av en incident bor här. Dokumentet finns för att förlagornas
styrka är att en härdad regel namnger det fel som skapade den. En regel utan
incident är en förmodan; en regel med incident är ett ärr.

**En post skrivs bara om något faktiskt hänt.** Uppmätt, i det här repot, med
utdata som går att peka på. En hypotetisk risk hör hemma i `docs/sparrar.md` eller
i en beslutspost, aldrig här. Skälet är att posten annars ärver trovärdighet den
inte betalat för: nästa läsare kan inte skilja det som brann från det någon var
orolig för.

Posterna numreras I1, I2, och så vidare. Numren återanvänds aldrig.

---

## I1 — Ett defaultvärde binds när modulen laddas

**Datum:** 2026-08-26 · **Uppmätt i:** skiva 1 · **Berör:** `src/mine.py`,
`tests/test_mine.py`

**Vad som hände.** `logga_korning` hade `logg: Path = MININGLOGG` som
defaultvärde. Ett defaultvärde binds när modulen laddas, inte när funktionen
anropas, så parametern höll en referens till den ursprungliga sökvägen. När
testet bytte ut modulkonstanten `MININGLOGG` mot en temporärfil nådde utbytet
aldrig fram, och `main()` skrev till den riktiga `docs/mining-log.md`. Tre
påhittade körningsrader hann appendas till ett committat styrdokument innan felet
upptäcktes. De är borttagna.

Samma mönster satt kvar på fyra ställen till: `sov`, `klocka` och `slumpa` som
defaultvärden i `Kvotpacer.__init__`, `_utfor`, `lista_trad_id`, `hamta_trad`,
`mina` och `fordrojning`. Det gjorde tre rader i testsviten verkningslösa. Raderna
såg ut att hålla sviten vaken och gjorde det inte, så sviten sov på riktigt utan
att någon märkte det.

**Vad det kostade.** Ett committat styrdokument bar under en tid tre rader som
påstod körningar mot brevlådan som aldrig ägt rum. Ingen körning skedde, men
dokumentet påstod motsatsen, vilket är precis den sortens obelagda påstående §7.2
finns för att stoppa.

**Hur det upptäcktes.** Inte genom läsning. `logga_korning`-felet föll ut när ett
nytt CLI-test skrev till en temporärfil och den riktiga filen ändå växte. De fyra
kvarvarande fallen fann den oberoende granskaren genom att MÄTA svittiden, inte
genom att läsa koden: raderna såg korrekta ut och var det inte.

**Uppmätt effekt.** Med samtliga lager fällda blev svitens utdata i mitt eget pass
`1 failed, 40 passed in 2.89s`, mot baslinjen `41 passed in 0.24s`. Granskaren
mätte i en egen, senare körning av samma fällning `1 failed, 40 passed in 2.90s`.
Talen är alltså två avläsningar av samma fenomen i olika körningar, inte ett tal
som ändrats.

**Regeln posten bär.** Ett testdubbelt som injiceras genom att byta ut en
modulkonstant skyddar ingenting om anropet läser konstanten via ett defaultvärde.
**Injektionen ska gå genom argumentet vid anropstillfället.** Konkret: skriv
`def f(x=None)` och `x = STANDARD if x is None else x` i kroppen, aldrig
`def f(x=STANDARD)`, för varje värde ett test kan tänkas vilja byta ut.

**Vad som gör den svår att se.** Ett verkningslöst `monkeypatch.setattr` ger
ingen varning, inget rött test, och ingen felutskrift. Sviten förblir grön.
Det enda observerbara är att något som borde vara snabbt är långsamt, och det
märks inte förrän någon tittar efter. Därav kravet nedan.

**Vakt.** `tests/test_mine.py::test_pacerns_sovfunktion_gar_att_byta_ut_utifran`
asserterar att en utbytt `mine.time.sleep` FAKTISKT anropas. Utan den kan
regressionen komma tillbaka tyst, eftersom sviten förblir grön när den återvänder.

---

## Mall för en incidentpost

Kopiera blocket nedan. Ett fält som inte går att fylla i är ett skäl att inte
skriva posten ännu, inte ett skäl att lämna fältet tomt.

### `I<n> — <vad som gick fel, i en rad>`

- **Datum, var det uppmättes, vad det berör.** Fil och funktion.
- **Vad som hände.** Förloppet, inte slutsatsen. Vad koden gjorde, inte vad den
  borde ha gjort.
- **Vad det kostade.** Den faktiska skadan. Blev den noll, skriv noll och skriv
  varför den blev noll, eftersom det oftast var tur och inte konstruktion.
- **Hur det upptäcktes.** Särskilt om det INTE var genom läsning. Ett fel som
  bara en mätning kunde hitta säger något om vilka fel som finns kvar.
- **Uppmätt effekt.** Tal avlästa ur verktygsutdata, med körningen namngiven.
  Inga tal ur minnet (§7.2).
- **Regeln posten bär.** Formulerad så att den går att följa utan att känna till
  incidenten.
- **Vakt.** Testet eller spärren som gör att felet inte kan återkomma tyst. Finns
  ingen, skriv `ingen` och räkna med att felet återkommer.

---

## Appendix — versionshistorik (nyaste överst)

### 0.1.0 — 2026-08-26

Dokumentet upprättat. `CLAUDE.md` §0 har räknat upp filen sedan repots första
commit `f9b680a` utan att den funnits, och CLAUDE.md 0.2.0:s appendix skrev
uttryckligen att loggen "börjar tom". Den börjar inte tom: skiva 1 producerade
I1, uppmätt och inte hypotetisk. Strukturen följer `docs/sparrar.md`.
