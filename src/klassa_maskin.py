"""Skiljer maskinmail från mänskligt mail.

BESLUTET FATTAS PÅ HUVUDEN, inte på innehåll. Ett nyhetsbrev och ett kundmail
kan använda samma ord; det som skiljer dem är att utskicket självt deklarerar
vad det är, genom `List-Unsubscribe`, `Auto-Submitted`, `Precedence` eller
`X-Auto-Response-Suppress`. Ett innehållsbaserat kriterium hade klassat kundens
ärende om en faktura som maskinmail.

Domänlistan i `config/maskindomaner.yaml` är ett andra lager, för avsändare som
inte deklarerar sig. Den HÄRLEDS ur materialet med `--harled-domaner` och skrivs
inte för hand: en handskriven lista blir gammal vid första nya avsändaren, och
den som skriver den måste titta på kundernas adresser för att fylla den.

Registrerad i `docs/sparrar.md` som `klassning-maskinmail`.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path

import yaml

from src import urval

ROT = Path(__file__).resolve().parent.parent
DOMANFIL = ROT / "config" / "maskindomaner.yaml"

# Härledningen skriver KANDIDATER hit, inte till konfigurationen.
#
# Skälet är uppmätt. Med 91 härledda domäner och med noll gav klassningen
# IDENTISKA tal: 200/211/144 och 1295/309/0. Lagret bidrog alltså med
# ingenting, vilket följer av härledningen: en domän kommer bara med om
# huvudlagret redan fällt allt från den. Kvar blir enbart framåtriktad risk,
# och den risken är konkret: den första härledda listan innehöll
# `googlemail.com`, vilket hade klassat varje framtida kund med den adressen
# som maskinmail, samt flera offertförmedlare som vidarebefordrar RIKTIGA
# kundärenden till verkstaden.
#
# En domän i konfigurationen är därför Lars beslut, inte kodens.
KANDIDATFIL = ROT / "scratchpad" / "maskindomaner-kandidater.yaml"
BESVARADE = ROT / "data" / "tradar.jsonl"
OBESVARADE = ROT / "data" / "tradar_obesvarade.jsonl"

# Huvuden som bara massutskick och automatik bär.
MASKINHUVUDEN = {
    "list-unsubscribe", "list-unsubscribe-post", "list-id", "list-post",
    "list-help", "auto-submitted", "x-auto-response-suppress",
    "x-campaign-id", "x-mailer-lid", "feedback-id", "x-csa-complaints",
    "x-report-abuse", "x-mailgun-sid", "x-sg-eid", "x-msg-eid",
}

# `Precedence`-värden som betyder utskick. `Precedence: normal` gör det inte.
MASKINPRECEDENCE = {"bulk", "list", "junk", "auto_reply"}

# Lokaldelar som säger rakt ut att svar inte läses.
NOREPLY = re.compile(
    r"^(?:no[-_.]?reply|donot[-_.]?reply|do[-_.]?not[-_.]?reply|noreply"
    r"|nepasrepondre|ingen[-_.]?svar|automat|autoreply|auto[-_.]?reply"
    r"|bounce|bounces|mailer[-_.]?daemon|postmaster|notification|notifications"
    r"|nyhetsbrev|newsletter)(?:\+.*)?$",
    re.IGNORECASE,
)


def las_domaner(sokvag: Path) -> set[str]:
    if not sokvag.exists():
        return set()
    data = yaml.safe_load(sokvag.read_text(encoding="utf-8")) or {}
    return {d.strip().lower() for d in (data.get("maskindomaner") or [])}


def avsandardoman(meddelande: dict) -> str:
    for adress in sorted(urval.adresser(meddelande, {"from"})):
        _, _, doman = adress.partition("@")
        if doman:
            return doman.lower()
    return ""


def _lokaldel(meddelande: dict) -> str:
    for adress in sorted(urval.adresser(meddelande, {"from"})):
        lokal, _, _ = adress.partition("@")
        return lokal.lower()
    return ""


def relayar_manniska(meddelande: dict) -> bool:
    """Sant för maskinSKICKAD post som bär en MÄNNISKAS text.

    Webbformulärets notis är det viktigaste fallet. Den skickas av ett system
    och bär därför maskinhuvuden, men innehållet är kundens ärende och `Reply-To`
    pekar på kunden. Beslutslogg #8 slog fast att notisen ÄR kundens meddelande.

    Utan det här undantaget klassas hela den sortens post som maskinmail, och
    det mest värdefulla kundmaterialet kastas. Uppmätt vid första körningen:
    288 av 555 besvarade trådar föll på `X-Msg-EID` innan undantaget fanns.

    Kriteriet är att `Reply-To` pekar någon annanstans än på avsändaren och
    brevlådan. Ett nyhetsbrev sätter `Reply-To` till sig självt eller inte alls;
    en relä sätter den till människan som ska svaras.
    """
    svarsadresser = urval.adresser(meddelande, {"reply-to"})
    if not svarsadresser:
        return False

    avsandare = urval.adresser(meddelande, {"from"})
    if not avsandare:
        return False

    avsandarorg = {organisationsdoman(a) for a in avsandare}

    for adress in svarsadresser:
        if adress == urval.BREVLADA or adress in avsandare:
            continue
        # Jämförelsen sker på ORGANISATIONSDOMÄN och inte på exakt sträng.
        # `news.exempel.se` är inte lika med `exempel.se`, så ett nyhetsbrev
        # med `From: news@news.exempel.se` och
        # `Reply-To: kundservice@exempel.se` såg ut som ett relä och slapp
        # igenom alla fyra lager. Undantaget körs först och är filens bredaste
        # regel, så ett hål här är ett hål i hela klassningen.
        if organisationsdoman(adress) in avsandarorg:
            continue
        return True
    return False


def organisationsdoman(adress: str) -> str:
    """De två sista etiketterna i domänen, eller tre för `co.uk`-formen.

    Trubbig med avsikt. En fullständig lista över offentliga suffix vore ett
    nytt beroende som måste hållas uppdaterat, och för det här bruket räcker
    det att `news.exempel.se` och `exempel.se` räknas som samma organisation.
    """
    doman = adress.partition("@")[2].lower().strip(".")
    delar = [d for d in doman.split(".") if d]
    if len(delar) < 2:
        return doman
    if len(delar) >= 3 and delar[-2] in {"co", "com", "org", "net", "gov"}:
        return ".".join(delar[-3:])
    return ".".join(delar[-2:])


def skal_maskinmail(meddelande: dict, domaner: set[str] | None = None) -> str:
    """Returnerar SKÄLET till att meddelandet är maskinmail, eller tom sträng.

    Skälet returneras i stället för ett sant eller falskt, så att en
    klassificering går att granska post för post utan att gissa vilket villkor
    som fällde.
    """
    if relayar_manniska(meddelande):
        return ""

    namn = urval.huvudnamn(meddelande)
    traffade = namn & MASKINHUVUDEN
    if traffade:
        return f"huvud: {sorted(traffade)[0]}"

    precedence = urval.huvudvarde(meddelande, "precedence").strip().lower()
    if precedence in MASKINPRECEDENCE:
        return f"precedence: {precedence}"

    if NOREPLY.match(_lokaldel(meddelande)):
        return "avsändare: noreply-form"

    doman = avsandardoman(meddelande)
    if domaner and doman in domaner:
        return "domän: i maskindomaner.yaml"

    return ""


def ar_maskinmail(meddelande: dict, domaner: set[str] | None = None) -> bool:
    return bool(skal_maskinmail(meddelande, domaner))


def tradens_skal(trad: dict, domaner: set[str] | None = None) -> str:
    """En tråd är maskinmail när dess FÖRSTA inkommande meddelande är det.

    Kriteriet ligger på det första inkommande och inte på tråden som helhet,
    eftersom ett svar från oss aldrig är maskinmail och annars hade dragit
    tråden åt fel håll.
    """
    for meddelande in trad.get("messages", []) or []:
        if urval.ar_kundmeddelande(meddelande):
            return skal_maskinmail(meddelande, domaner)
    return ""


def las_tradar(sokvag: Path):
    if not sokvag.exists():
        return
    for rad in sokvag.read_text(encoding="utf-8").splitlines():
        if rad:
            yield json.loads(rad)


def harled_domaner(skordar: list[Path]) -> list[str]:
    """Domäner för avsändare som redan är klassade som maskinmail på HUVUDEN.

    Listan härleds alltså ur de fall där avsändaren själv deklarerat vad den är.
    En domän kommer med först när den bara skickar sådant: en domän som också
    skickat ett odeklarerat mail lämnas utanför, eftersom den kan bära både
    utskick och en människa.
    """
    maskin: Counter[str] = Counter()
    ovrigt: Counter[str] = Counter()

    for skord in skordar:
        for trad in las_tradar(skord):
            for meddelande in trad.get("messages", []) or []:
                if not urval.ar_kundmeddelande(meddelande):
                    continue
                doman = avsandardoman(meddelande)
                if not doman:
                    continue
                if skal_maskinmail(meddelande):
                    maskin[doman] += 1
                else:
                    ovrigt[doman] += 1
                break

    return sorted(d for d in maskin if not ovrigt[d])


def skriv_domaner(domaner: list[str], sokvag: Path) -> None:
    innehall = {
        "maskindomaner": domaner,
    }
    text = (
        "# Domäner som bara skickar deklarerat maskinmail.\n"
        "#\n"
        "# HÄRLEDD, INTE HANDSKRIVEN. Skrivs om av\n"
        "# `python -m src.klassa_maskin --harled-domaner`.\n"
        "#\n"
        "# En domän kommer med först när varje mail från den bär ett\n"
        "# maskinhuvud eller en noreply-avsändare. En domän som också skickat\n"
        "# ett odeklarerat mail lämnas utanför: den kan bära både utskick och\n"
        "# en människa, och att klassa den som maskin hade kastat kundens post.\n"
        "#\n"
        "# §6: en domän är inte persondata, men en LOKALDEL kan vara det.\n"
        "# Därför står bara domäner här, aldrig hela adresser.\n"
        "\n"
    ) + yaml.safe_dump(innehall, allow_unicode=True, sort_keys=False)
    sokvag.parent.mkdir(parents=True, exist_ok=True)
    sokvag.write_text(text, encoding="utf-8")


def rakna(skord: Path, domaner: set[str]) -> dict:
    maskin = 0
    mansklig = 0
    utan_kundmail = 0
    skal: Counter[str] = Counter()

    for trad in las_tradar(skord):
        har_kundmail = any(
            urval.ar_kundmeddelande(m) for m in trad.get("messages", []) or []
        )
        if not har_kundmail:
            utan_kundmail += 1
            continue
        anledning = tradens_skal(trad, domaner)
        if anledning:
            maskin += 1
            skal[anledning.split(":")[0]] += 1
        else:
            mansklig += 1

    return {"maskin": maskin, "mansklig": mansklig,
            "utan_kundmail": utan_kundmail, "skal": skal}


def main(argv: list[str] | None = None) -> int:
    tolk = argparse.ArgumentParser(description=__doc__)
    tolk.add_argument("--besvarade", type=Path, default=BESVARADE)
    tolk.add_argument("--obesvarade", type=Path, default=OBESVARADE)
    tolk.add_argument("--domanfil", type=Path, default=DOMANFIL)
    tolk.add_argument("--kandidatfil", type=Path, default=KANDIDATFIL)
    tolk.add_argument("--harled-domaner", action="store_true")
    arg = tolk.parse_args(argv)

    if arg.harled_domaner:
        domaner = harled_domaner([arg.besvarade, arg.obesvarade])
        skriv_domaner(domaner, arg.kandidatfil)
        print(f"härledda KANDIDATER: {len(domaner)}")
        print(f"skrivna till: {arg.kandidatfil}")
        print("")
        print("Kandidaterna hamnar INTE i konfigurationen automatiskt.")
        print("Lagret bidrog med noll klassningar i det uppmätta materialet,")
        print("och den första härledda listan bar googlemail.com samt flera")
        print("offertförmedlare som vidarebefordrar riktiga kundärenden.")
        print("Lars avgör vilka som förs över till:")
        print(f"  {arg.domanfil}")
        return 0

    domaner = las_domaner(arg.domanfil)
    print(f"maskindomäner i konfigurationen: {len(domaner)}")

    for namn, skord in (("besvarade", arg.besvarade),
                        ("obesvarade", arg.obesvarade)):
        if not skord.exists():
            print(f"\n{namn}: filen finns inte, hoppas över")
            continue
        rakning = rakna(skord, domaner)
        print(f"\n=== {namn.upper()} ({skord.name}) ===")
        print(f"  maskinmail: {rakning['maskin']}")
        print(f"  mänskliga: {rakning['mansklig']}")
        print(f"  trådar utan kundmeddelande: {rakning['utan_kundmail']}")
        print("  maskinmail per skäl:")
        for anledning, antal in rakning["skal"].most_common():
            print(f"    {anledning}: {antal}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
