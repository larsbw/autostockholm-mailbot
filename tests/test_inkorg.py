"""LAGER 1 OCH 2 i skugglägets väg till brevlådan: scopet och den kapade tjänsten.

Lars §10-beslut i skiva 48, se `docs/beslutslogg.md` #113. Lager 3 och 4,
importlagret och källtextlagret, prövas i `tests/test_respond.py`.

**INGET TEST HÄR RÖR NÄTET ELLER EN RIKTIG BREVLÅDA.** Tjänsten är
`tests/fejk.py::FejkGmail`, och tokenen är uppenbart påhittade strängar (§6).
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src import auth, extract, inkorg, kanal, klassa_maskin, urval
from tests import fejk


def _fejktjanst() -> inkorg.Lastjanst:
    """En kapad tjänst runt fejken. Samma inlindning som `las_tjanst` gör."""
    return inkorg.Lastjanst(fejk.FejkGmail(sidor={None: {}}, tradar={}))


# ------------------------------------------------------------ LAGER 1: scopet


def test_LASSCOPES_bar_readonly_och_ingenting_annat():
    """Lager 1 är det enda Google upprätthåller, alltså är listans innehåll
    hela dess styrka.

    `gmail.modify` står INTE här, och det är inte en utelämning: sidan
    https://developers.google.com/workspace/gmail/api/auth/scopes säger om det
    scopet *"Read, compose, and send emails from your Gmail account"*, alltså
    tillåter det sändning. Ett token med modify men utan send kan fortfarande
    skicka.
    """
    assert auth.LASSCOPES == [
        "https://www.googleapis.com/auth/gmail.readonly"]
    assert "gmail.send" not in " ".join(auth.LASSCOPES)
    assert "gmail.modify" not in " ".join(auth.LASSCOPES)


def test_en_SANDFORMOGEN_credential_falls_av_krav_pa_bara_lasning():
    """Pekar någon läsvägen mot `token.json` ska den falla, inte fungera.

    Det är den troliga formen av misstaget: två tokenfiler, och en sökväg som
    blir fel. Utan den här kontrollen hade skuggläget då kört med en credential
    som kan skicka, och de tre kodlagren hade varit allt som stod emellan.
    """
    class FejkCred:
        scopes = list(auth.SCOPES)

    with pytest.raises(auth.Sandformaga, match="gmail.send"):
        auth.krav_pa_bara_lasning(FejkCred())


def test_ett_EXTRA_scope_falls_ocksa():
    """Prövningen är en TILLÅTNINGSLISTA och inte en förbudslista.

    Ett scope vi aldrig hört talas om ska falla lika säkert som `gmail.send`.
    En förbudslista hade krävt att vi vet vilka av Gmails scope som kan skicka,
    och den kunskapen åldras.
    """
    class FejkCred:
        scopes = auth.LASSCOPES + [
            "https://www.googleapis.com/auth/gmail.hittepa"]

    with pytest.raises(auth.Sandformaga):
        auth.krav_pa_bara_lasning(FejkCred())


def test_en_credential_UTAN_scope_falls():
    """Tom mängd är inte samma sak som läsatokenets mängd.

    En tokenfil utan `scopes` ger `cred.scopes is None`, och en prövning som
    tolkade det som ofarligt hade släppt igenom just den trasiga filen.
    """
    class FejkCred:
        scopes = None

    with pytest.raises(auth.Sandformaga):
        auth.krav_pa_bara_lasning(FejkCred())


def test_lasatokenet_ar_en_EGEN_fil_och_gitignorerad():
    """§6 och lager 1: två auktoriseringar kan inte dela tokenfil.

    `_las_token` prövar `has_scopes` mot det filen bär, och en skrivning hade
    skrivit över den andra. Filen bär ett refresh_token till brevlådan och får
    aldrig committas.
    """
    assert auth.LASTOKEN != auth.TOKEN
    gitignore = (auth.ROT / ".gitignore").read_text(encoding="utf-8").split()
    assert auth.LASTOKEN.name in gitignore
    assert auth.TOKEN.name in gitignore


def test_hamta_las_credentials_gar_INTE_att_be_om_andra_scope():
    """`scopes` är ingen parameter, och det är hela poängen.

    `hamta_credentials` tar scopelistan som argument, alltså kan en anropare be
    om vad som helst. Läsvägen ska inte kunna det.
    """
    import inspect

    parametrar = inspect.signature(auth.hamta_las_credentials).parameters
    assert "scopes" not in parametrar


# ------------------------------------------------------- LAGER 2: tjänsten


def test_sandanropet_kastar_i_stallet_for_att_na_gmail():
    """LAGER 2. Det anrop hela spärren handlar om."""
    tjanst = _fejktjanst()

    with pytest.raises(inkorg.Sandforsok, match="send"):
        tjanst.users().messages().send(userId="me", body={})


def test_drafts_kastar_redan_pa_attributatkomsten():
    """Ett utkast i Gmail är ett mail som väntar på en knapptryckning.

    `drafts` är ingen läsväg, och `_Users.__getattr__` fäller innan något anrop
    ens byggs.
    """
    tjanst = _fejktjanst()

    with pytest.raises(inkorg.Sandforsok, match="drafts"):
        tjanst.users().drafts()


def test_modify_kastar_aven_om_det_inte_skickar():
    """Skuggläget LÄSER. Att flytta en etikett är att ändra brevlådan.

    Med `gmail.readonly` vägrar Google ändå, men lager 2 ska säga ifrån vid
    anropet i stället för som ett 403 efter en halv körning.
    """
    tjanst = _fejktjanst()

    with pytest.raises(inkorg.Sandforsok, match="modify"):
        tjanst.users().messages().modify(userId="me", id="x", body={})


def test_de_tva_anrop_repot_faktiskt_gor_gar_igenom():
    """En spärr som stoppar allt stoppar också arbetet.

    Hela repot rör Gmail genom `users().threads().list` och
    `users().threads().get`, alltså ska precis de två fungera oförändrat genom
    inlindningen.
    """
    fejkad = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "t1"}]}},
        tradar={"t1": {"id": "t1", "messages": []}},
    )
    tjanst = inkorg.Lastjanst(fejkad)

    listan = tjanst.users().threads().list(userId="me").execute()
    traden = tjanst.users().threads().get(userId="me", id="t1").execute()

    assert listan["threads"] == [{"id": "t1"}]
    assert traden["id"] == "t1"


def test_mine_kan_kora_hela_vagen_genom_den_kapade_tjansten():
    """Lager 2 får inte kosta en förmåga någon använder.

    `mine.mina` är hämtningen skuggläget går igenom, och den ska fungera
    oförändrat mot den inlindade tjänsten.
    """
    from src import mine

    fejkad = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "t1"}, {"id": "t2"}]}},
        tradar={"t1": {"id": "t1", "messages": []},
                "t2": {"id": "t2", "messages": []}},
    )
    utfil = auth.ROT / "data" / "_prov-inkorg.jsonl"
    try:
        forbrukning = mine.mina(
            inkorg.Lastjanst(fejkad), utfil=utfil,
            sov=fejk.Sovlogg(), fraga="-in:sent",
        )
        assert forbrukning.tradar == 2
        assert forbrukning.fullstandig
    finally:
        utfil.unlink(missing_ok=True)
        utfil.with_name(utfil.name + ".delvis").unlink(missing_ok=True)


# ----------------------------------------------------------- DYGNSGRÄNSEN


def _nu(ar=2026, manad=9, dag=15, timme=12, minut=0):
    return datetime(ar, manad, dag, timme, minut, tzinfo=timezone.utc)


def _ms(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1000))


def _medd(dt: datetime, *, sent=False, etiketter=None) -> dict:
    return {"internalDate": _ms(dt),
            "labelIds": list(etiketter or (["SENT"] if sent else ["INBOX"]))}


def test_GARDAGENS_EFTERMIDDAG_ligger_i_morgonens_fonster():
    """LUCKA 84. Körningen går 05:10 UTC. Ett mail i går 14:00 låg utanför
    dygnet den körningen såg, och utanför nästa också."""
    korning = _nu(dag=15, timme=5, minut=10)
    borjan, slut = inkorg.fonstrets_granser(korning)

    assert borjan <= int(_ms(_nu(dag=14, timme=14))) < slut
    assert borjan <= int(_ms(_nu(dag=14, timme=5, minut=10))) < slut
    assert not borjan <= int(_ms(_nu(dag=14, timme=5, minut=9))) < slut


def test_TVA_KORNINGAR_i_rad_moter_varandra_UTAN_GLAPP():
    """Slutet avrundas till hel minut: sekunderna körningen startar på spelar
    ingen roll."""
    igar = _nu(dag=14, timme=5, minut=10).replace(second=3)
    idag = _nu(dag=15, timme=5, minut=10).replace(second=41)

    assert inkorg.fonstrets_granser(igar)[1] == \
        inkorg.fonstrets_granser(idag)[0]


def test_slutet_ar_EXKLUSIVT():
    """Nästa dygns första millisekund hör till nästa dygn."""
    borjan, slut = inkorg.fonstrets_granser(_nu())

    assert not inkorg._ar_fran_dagen({"internalDate": str(slut)},
                                     (borjan, slut))
    assert inkorg._ar_fran_dagen({"internalDate": str(slut - 1)},
                                 (borjan, slut))


def test_ett_meddelande_UTAN_internalDate_raknas_inte_som_dagens():
    """Att gissa åt andra hållet hade tagit in varje odaterat mail varje dag."""
    granser = inkorg.fonstrets_granser(_nu())

    assert not inkorg._ar_fran_dagen({}, granser)
    assert not inkorg._ar_fran_dagen({"internalDate": ""}, granser)


def test_en_trad_vars_enda_dagsfarska_meddelande_ar_VART_SVAR_tas_inte_med():
    """**ANNARS BESVARAS SAMMA TRÅD PÅ NYTT VARJE DAG VI SVARAR I DEN.**

    Kriteriet ligger på ett INKOMMANDE meddelande från dygnet. En tråd vars
    kundmail är från i förrgår och vars enda färska meddelande är vårt eget svar
    är inget nytt ärende.
    """
    granser = inkorg.fonstrets_granser(_nu())
    igar = _nu(dag=13)

    bara_vart_svar = {"id": "t1", "messages": [
        _medd(igar), _medd(_nu(timme=9), sent=True)]}
    kundmail_i_dag = {"id": "t2", "messages": [
        _medd(igar), _medd(_nu(timme=9))]}

    kvar = inkorg.tradar_fran_dagen([bara_vart_svar, kundmail_i_dag],
                                    granser=granser)

    assert [t["id"] for t in kvar] == ["t2"]


def test_SPAM_och_TRASH_sallas_i_var_kod():
    """`includeSpamTrash` saknar dokumenterat förval, se modulens inledning.

    Etiketterna står i meddelandet, alltså prövas de här i stället för att
    förutsättas.
    """
    granser = inkorg.fonstrets_granser(_nu())
    nu = _nu(timme=9)

    skrap = {"id": "t1", "messages": [_medd(nu, etiketter=["SPAM"])]}
    papperskorg = {"id": "t2", "messages": [_medd(nu, etiketter=["TRASH"])]}
    riktigt = {"id": "t3", "messages": [_medd(nu)]}

    kvar = inkorg.tradar_fran_dagen([skrap, papperskorg, riktigt],
                                    granser=granser)

    assert [t["id"] for t in kvar] == ["t3"]


def test_gmailfragan_ar_ett_GROVT_NAT_och_vidare_an_dygnet():
    """Frågan får inte vara det som drar dagsgränsen.

    `after:`s inklusivitet och tidszon går inte att läsa ut ur Googles
    dokumentation, se modulens inledning. Nätet är därför `newer_than:2d`, och
    gränsen dras mot `internalDate`.
    """
    assert "newer_than:2d" in inkorg.FRAGA
    assert "after:" not in inkorg.FRAGA
    # SKIVA 69. `-in:sent` höll ute webbformulärets notis, som bär SENT.
    assert "in:sent" not in inkorg.FRAGA


def test_webbformularets_NOTIS_ar_ett_dagsfarskt_arende():
    """Skiva 69. Notisen bär `SENT` men har passerat inkommande leverans.
    Dygnsfiltret krävde att `SENT` saknades och fällde varje sådan tråd."""
    granser = inkorg.fonstrets_granser(_nu())
    notis = _medd(_nu(timme=9), sent=True)
    notis["payload"] = {"headers": [{"name": "Delivered-To", "value": ""}]}

    kvar = inkorg.tradar_fran_dagen([{"id": "t1", "messages": [notis]}],
                                    granser=granser)

    assert [t["id"] for t in kvar] == ["t1"]


def test_inkorgs_scopelista_ar_AUTHS_och_inte_en_kopia():
    """En kopia hade kunnat gå isär med den lista auktoriseringen faktiskt
    begär, och då hade utskriften ovanför utkasten påstått fel scope.

    Aliaset finns därför att `scripts/respond.py` skriver ut vilket scope
    körningen har utan att importera `src.auth`: den modulen står i
    `vy.GMAILBARANDE_MODULER`, och slingan ska inte göra det.
    """
    assert inkorg.LASSCOPES is auth.LASSCOPES


def test_las_tjanst_lamnar_ut_den_INLINDADE_och_aldrig_den_rana(monkeypatch):
    """LAGER 2. `las_tjanst`:s docstring påstår att den råa tjänsten aldrig
    lämnar funktionen, och ingenting band det.

    Uppmätt: `return auth.bygg_tjanst(cred)` i stället för
    `return Lastjanst(auth.bygg_tjanst(cred))` lämnade hela sviten GRÖN. Lager 2
    hade då varit en artighet anroparen kan välja bort utan att märka det.
    Fällt av §7.1-prövningen i skiva 48.

    Ingen credential läses: båda anropen till `src.auth` byts ut.
    """
    class FejkCred:
        scopes = list(auth.LASSCOPES)

    ra = fejk.FejkGmail(sidor={None: {}}, tradar={})
    monkeypatch.setattr(inkorg.auth, "hamta_las_credentials",
                        lambda **_: FejkCred())
    monkeypatch.setattr(inkorg.auth, "bygg_tjanst", lambda cred: ra)

    tjanst = inkorg.las_tjanst()

    assert isinstance(tjanst, inkorg.Lastjanst)
    assert tjanst is not ra
    with pytest.raises(inkorg.Sandforsok):
        tjanst.users().messages().send(userId="me", body={})


# ---------------------------------------------- SKÖRDEN, SKIVA 54 DEL A
#
# Lars beslut, två delar: varje körning SKRIVER ÖVER filen, och den bär bara de
# fält kedjan faktiskt använder. Filen är arbetsmaterial för en körning, inte
# ett arkiv.


def _b64(text: str) -> str:
    import base64
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def _huvud(namn: str, varde: str) -> dict:
    return {"name": namn, "value": varde}


def _kundmail(text: str = "Hej, kan ni bygga om min bil? ABC12D",
              *, huvuden=None, etiketter=None, bilaga=False,
              html_ocksa=False) -> dict:
    """Ett meddelande på Gmails form, med de fält Google faktiskt skickar."""
    delar = [{"partId": "0", "mimeType": "text/plain", "filename": "",
              "body": {"size": len(text), "data": _b64(text)}}]
    if html_ocksa:
        rahtml = f"<html><body><p>{text}</p></body></html>"
        delar.append({"partId": "1", "mimeType": "text/html", "filename": "",
                      "body": {"size": len(rahtml), "data": _b64(rahtml)}})
    if bilaga:
        delar.append({"partId": "2", "mimeType": "image/jpeg",
                      "filename": "stotfangare.jpg",
                      "body": {"size": 900, "data": _b64("X" * 900)}})

    return {
        "id": "m1",
        "threadId": "t1",
        "historyId": "8801",
        "sizeEstimate": 40000,
        "snippet": text[:40],
        "internalDate": "1757900000000",
        "labelIds": list(etiketter or ["INBOX", "UNREAD"]),
        "payload": {
            "partId": "",
            "mimeType": "multipart/mixed" if (bilaga or html_ocksa)
                        else "multipart/alternative",
            "filename": "",
            "headers": [
                _huvud("Delivered-To", "info@autostockholm.se"),
                _huvud("Return-Path", "<kund@exempel.se>"),
                _huvud("Received", "from mx.exempel.se by mx.google.com"),
                _huvud("From", "Kund Kundsson <kund@exempel.se>"),
                _huvud("To", "info@autostockholm.se"),
                _huvud("Cc", "systern@exempel.se"),
                _huvud("Bcc", "hemlig@exempel.se"),
                _huvud("Subject", "Fråga om a-traktor"),
                _huvud("Message-ID", "<abc@exempel.se>"),
                _huvud("Content-Type", "multipart/alternative"),
            ] + list(huvuden or []),
            "parts": delar,
        },
    }


def _trad(meddelanden, trad_id="t1") -> dict:
    return {"id": trad_id, "historyId": "8801", "messages": meddelanden}


# ------------------------------------------------ DEL 1: filen skrivs över


def test_varje_korning_SKRIVER_OVER_skorden(tmp_path):
    """**LARS BESLUT, DEL A PUNKT 1.** Skörden är arbetsmaterial för EN körning.

    Raden är inte kosmetisk: växer filen i stället för att bytas ut är den efter
    en månads drift den största samlingen kundmail på servern (§6).

    Prövas genom TVÅ körningar mot samma fil med olika trådar. Ett tillägg hade
    gett fyra rader.
    """
    from src import mine

    utfil = tmp_path / "skord.jsonl"
    forsta = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "a1"}, {"id": "a2"}]}},
        tradar={"a1": _trad([_kundmail()], "a1"),
                "a2": _trad([_kundmail()], "a2")},
    )
    andra = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "b1"}, {"id": "b2"}]}},
        tradar={"b1": _trad([_kundmail()], "b1"),
                "b2": _trad([_kundmail()], "b2")},
    )

    for tjanst in (forsta, andra):
        inkorg.dagens_tradar(inkorg.Lastjanst(tjanst), utfil=utfil,
                             nu=_nu(dag=15))

    idn = [t["id"] for t in extract.las_tradar(utfil)]
    assert idn == ["b1", "b2"], "skörden bar den föregående körningens trådar"


def test_en_AVBRUTEN_korning_lamnar_foregaende_skord_orord(tmp_path):
    """Skriv över betyder inte töm först.

    `mine.mina` skriver till `.delvis` och flyttar på plats, alltså ligger
    föregående körnings skörd kvar när en hämtning faller halvvägs. Utan det
    hade ett kvotfel mitt i en körning både avbrutit dagen och raderat gårdagens
    material att felsöka i.
    """
    from src import mine

    utfil = tmp_path / "skord.jsonl"
    forsta = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "a1"}]}},
        tradar={"a1": _trad([_kundmail()], "a1")},
    )
    inkorg.dagens_tradar(inkorg.Lastjanst(forsta), utfil=utfil, nu=_nu(dag=15))

    trasig = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "b1"}]}},
        tradar={},
        get_fel={"b1": [fejk.behorighetsfel() for _ in range(mine.MAX_FORSOK)]},
    )
    with pytest.raises(Exception):
        inkorg.dagens_tradar(inkorg.Lastjanst(trasig), utfil=utfil,
                             nu=_nu(dag=15))

    assert [t["id"] for t in extract.las_tradar(utfil)] == ["a1"]


# ----------------------------------- DEL 2: bara de fält kedjan läser


def test_skorden_bar_INGA_RAA_HUVUDEN_som_kedjan_inte_laser(tmp_path):
    """**LARS BESLUT, DEL A PUNKT 2, ordagrant:** Bcc, Return-Path,
    Delivered-To och råa huvuden ska aldrig nå disken om kedjan inte läser dem.

    **DE TRE HUVUDENA BEHANDLAS OLIKA, och skillnaden är mätt och inte valfri.**
    `Bcc` läser kedjan inte alls och det faller helt. `Return-Path` och
    `Delivered-To` prövar `urval.ar_kundmeddelande` på FÖREKOMST: det är de som
    avgör att webbformulärets notis, som bär `SENT`, ändå är kundens meddelande
    (beslutslogg #8). Namnen står därför kvar och deras VÄRDEN gör det inte.

    Mätt på filen och inte på returvärdet: det är disken §6 handlar om.
    """
    utfil = tmp_path / "skord.jsonl"
    tjanst = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "t1"}]}},
        tradar={"t1": _trad([_kundmail()])},
    )
    inkorg.dagens_tradar(inkorg.Lastjanst(tjanst), utfil=utfil, nu=_nu(dag=15))
    ratext = utfil.read_text(encoding="utf-8")

    assert "hemlig@exempel.se" not in ratext, "Bcc:s värde nådde disken"
    assert "systern@exempel.se" not in ratext, "Cc:s värde nådde disken"
    assert "mx.google.com" not in ratext, "Received:s värde nådde disken"
    assert "Bcc" not in ratext

    # Och namnen som BÄR ett beslut står kvar, utan värde.
    huvuden = extract.las_tradar(utfil).__next__()["messages"][0]["payload"]["headers"]
    som_dikt = {h["name"]: h["value"] for h in huvuden}
    # SKIVA 68: `Message-ID` STÅR KVAR MED VÄRDE. Här stod att det faller. Gmail-
    # utkastet svarar på det med `In-Reply-To`, och utan värdet hamnar svaret
    # utanför kundens tråd.
    assert som_dikt["Message-ID"] == "<abc@exempel.se>"
    assert som_dikt["Return-Path"] == ""
    assert som_dikt["Delivered-To"] == ""
    assert som_dikt["From"] == "Kund Kundsson <kund@exempel.se>"
    assert som_dikt["Subject"] == "Fråga om a-traktor"


def test_skorden_bar_INGEN_BILAGA_och_ingen_oläst_HTML_kropp(tmp_path):
    """Bilagan och den olästa HTML-kroppen är skördens största poster.

    `urval.brodtext` läser EN kroppsdel: första `text/plain` med data, och
    `text/html` bara när ingen sådan finns. Ett mail som bär båda bär alltså en
    HTML-kropp ingenting öppnar, och en bifogad bild öppnar ingenting alls.
    """
    utfil = tmp_path / "skord.jsonl"
    tjanst = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "t1"}]}},
        tradar={"t1": _trad([_kundmail(bilaga=True, html_ocksa=True)])},
    )
    inkorg.dagens_tradar(inkorg.Lastjanst(tjanst), utfil=utfil, nu=_nu(dag=15))

    trad = next(extract.las_tradar(utfil))
    delar = trad["messages"][0]["payload"].get("parts") or []

    assert [d["mimeType"] for d in delar] == ["text/plain"]
    assert "image/jpeg" not in utfil.read_text(encoding="utf-8")
    assert "stotfangare.jpg" not in utfil.read_text(encoding="utf-8")


def test_HTML_kroppen_foljer_med_nar_den_ar_DEN_SOM_LASES(tmp_path):
    """Negativkontroll till raden ovan.

    Ett mail utan `text/plain` läses ur `text/html`. Föll HTML alltid vore varje
    sådant mail tomt, alltså sållat som "tom brödtext" och obesvarat.
    """
    meddelande = _kundmail(html_ocksa=True)
    meddelande["payload"]["parts"] = [
        d for d in meddelande["payload"]["parts"] if d["mimeType"] != "text/plain"
    ]

    gallrad = inkorg.gallra_meddelande(meddelande)

    assert [d["mimeType"] for d in gallrad["payload"]["parts"]] == ["text/html"]
    assert urval.brodtext(gallrad) == urval.brodtext(meddelande)
    assert urval.brodtext(gallrad) != ""


def test_skorden_bar_INGEN_SNIPPET_och_inga_id_falt_kedjan_inte_laser(tmp_path):
    """`snippet` är Gmails eget klartextutdrag ur kundens mail.

    Det är kundtext, och ingenting i den dagliga körningen läser det.
    """
    utfil = tmp_path / "skord.jsonl"
    tjanst = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "t1"}]}},
        tradar={"t1": _trad([_kundmail()])},
    )
    inkorg.dagens_tradar(inkorg.Lastjanst(tjanst), utfil=utfil, nu=_nu(dag=15))

    trad = next(extract.las_tradar(utfil))
    meddelande = trad["messages"][0]

    assert set(trad) == {"id", "messages"}
    assert set(meddelande) == {"labelIds", "internalDate", "payload"}
    for falt in ("snippet", "sizeEstimate", "historyId", "threadId", "partId",
                 "filename"):
        assert falt not in utfil.read_text(encoding="utf-8"), falt


def test_KROPPSDELEN_som_foljer_med_ar_den_urval_pekar_ut():
    """Gallringen härmar inte `brodtext`:s val, den frågar efter det.

    `urval.textdel` är utbruten just för det. Skulle `brodtext` en dag föredra
    något annat följer skörden med av sig själv.
    """
    meddelande = _kundmail(html_ocksa=True, bilaga=True)

    vald = urval.textdel(meddelande)
    gallrad = inkorg.gallra_meddelande(meddelande)

    assert gallrad["payload"]["parts"][0]["body"]["data"] == vald["body"]["data"]
    assert urval.brodtext(gallrad) == urval.brodtext(meddelande)


def test_en_kropp_DIREKT_pa_payload_overlever_gallringen():
    """Beslutslogg #6: saknas `parts` ligger texten i `payload.body.data`."""
    meddelande = _kundmail()
    text = "Hej, vi har en Volvo V70 som ska bli a-traktor."
    meddelande["payload"].pop("parts")
    meddelande["payload"]["mimeType"] = "text/plain"
    meddelande["payload"]["body"] = {"size": len(text), "data": _b64(text)}

    gallrad = inkorg.gallra_meddelande(meddelande)

    assert "parts" not in gallrad["payload"]
    assert urval.brodtext(gallrad) == urval.brodtext(meddelande)
    assert urval.brodtext(gallrad).startswith("Hej, vi har en Volvo")


def test_ett_meddelande_UTAN_LASBAR_TEXT_gallras_utan_att_kasta():
    """Sållningsskälet "tom brödtext" ska vara detsamma före och efter."""
    meddelande = _kundmail()
    meddelande["payload"]["parts"] = [
        {"partId": "0", "mimeType": "application/pdf", "filename": "offert.pdf",
         "body": {"size": 10, "data": _b64("PDF")}}
    ]

    gallrad = inkorg.gallra_meddelande(meddelande)

    assert urval.brodtext(gallrad) == urval.brodtext(meddelande) == ""
    assert "application/pdf" not in json.dumps(gallrad)


# ------------------------- DEL 3: gallringen ändrar inte kedjans utfall


def _kedjans_utfall(trad: dict, domaner) -> tuple:
    """Precis de bedömningar `scripts/respond.py::arende_ur_trad` gör.

    Skrivet här och inte importerat ur skriptet: `scripts/` ligger inte i ett
    paket, och en import av `respond` drar in `googleapiclient`.
    """
    meddelanden = trad.get("messages") or []
    kund = next((m for m in meddelanden if urval.ar_kundmeddelande(m)), None)
    return (
        klassa_maskin.tradens_skal(trad, domaner),
        None if kund is None else (
            urval.brodtext(kund),
            kanal.amnesrad(kund),
            kanal.namnge(kund),
            urval.hasha(urval.kundadress(kund)),
            urval.tidsstampel(kund),
        ),
    )


@pytest.mark.parametrize("bygg", [
    pytest.param(lambda: _kundmail(), id="vanligt kundmail"),
    pytest.param(lambda: _kundmail(bilaga=True, html_ocksa=True),
                 id="bilaga och html"),
    pytest.param(
        lambda: _kundmail(
            huvuden=[_huvud("List-Unsubscribe", "<https://x.se/av>")]),
        id="maskinmail på huvud"),
    pytest.param(
        lambda: _kundmail(huvuden=[_huvud("Precedence", "bulk")]),
        id="maskinmail på precedence"),
    pytest.param(
        lambda: _kundmail(
            etiketter=["SENT"],
            huvuden=[_huvud("Reply-To", "kund@annanstans.se"),
                     _huvud("X-Msg-EID", "42")]),
        id="webbformulärets notis"),
    pytest.param(
        lambda: _kundmail(huvuden=[_huvud("From", "noreply@exempel.se")]),
        id="noreply-avsändare"),
])
def test_gallringen_andrar_INTE_kedjans_bedomning(bygg):
    """**DEN HÄR RADEN ÄR HELA GRUNDEN FÖR ATT GALLRA ALLS.**

    Ett fält får falla bort först när kedjan bedömer mailet likadant utan det.
    Prövas över de former sållningen faktiskt skiljer på, eftersom en gallring
    som bara håller för det vanliga kundmailet gör en maskinmailsklassning till
    ett ärende, eller tvärtom.
    """
    domaner = {"nyhetsbrev.exempel.se"}
    meddelande = bygg()
    trad = _trad([meddelande])

    assert _kedjans_utfall(inkorg.gallra_trad(trad), domaner) == \
        _kedjans_utfall(trad, domaner)


def _vart_svar(mottagare: str) -> dict:
    """Ett svar skrivet i Gmail: `SENT`, inga leveranshuvuden, svarshuvuden."""
    return {
        "id": "m2", "internalDate": "1757990000000", "labelIds": ["SENT"],
        "payload": {
            "mimeType": "text/plain",
            "headers": [
                _huvud("From", "info@autostockholm.se"),
                _huvud(mottagare, "kund@exempel.se"),
                _huvud("Subject", "Re: Fråga om a-traktor"),
                _huvud("In-Reply-To", "<abc@exempel.se>"),
                _huvud("References", "<abc@exempel.se>"),
            ],
            "body": {"data": _b64("Hej, det går bra.")},
        },
    }


def _besvarad(trad: dict) -> bool:
    """Samma uttryck som `scripts/respond.py::arende_ur_trad`."""
    return any(urval.ar_gmail_svar(m) for m in trad["messages"])


@pytest.mark.parametrize("mottagare", ["To", "Cc"])
def test_gallringen_BEVARAR_att_traden_ar_besvarad(mottagare):
    """SKIVA 69 DEL A. Skörden gallrade svarshuvudena och mottagarna, och då
    var `Arende.besvarad` alltid falskt i inkorgskörningen."""
    trad = _trad([_kundmail(), _vart_svar(mottagare)])

    assert _besvarad(trad) is True
    assert _besvarad(inkorg.gallra_trad(trad)) is True


def test_mottagarnas_VARDEN_foljer_bara_med_vara_EGNA_meddelanden():
    """Kundmailets `Cc` kan vara en tredje persons adress och faller."""
    gallrad = inkorg.gallra_trad(_trad([_kundmail(), _vart_svar("Cc")]))
    kund, svar = (m["payload"]["headers"] for m in gallrad["messages"])

    assert not any(h["name"] in ("To", "Cc") for h in kund)
    assert {"name": "Cc", "value": "kund@exempel.se"} in svar
    assert {"name": "In-Reply-To", "value": ""} in svar


def test_KAND_LUCKA_ett_svar_bara_i_Bcc_ser_obesvarat_ut():
    """`bcc` gallras, Lars beslut i skiva 54. Blir röd den dag det ändras."""
    trad = _trad([_kundmail(), _vart_svar("Bcc")])

    assert _besvarad(trad) is True
    assert _besvarad(inkorg.gallra_trad(trad)) is False


def test_dagens_tradar_ANVANDER_fonstret(tmp_path):
    """Lucka 84, prövat genom hämtningen och inte bara genom gränsfunktionen."""
    i_gar = _kundmail()
    i_gar["internalDate"] = _ms(_nu(dag=14, timme=14))
    for_gammal = _kundmail()
    for_gammal["internalDate"] = _ms(_nu(dag=13, timme=14))
    tjanst = fejk.FejkGmail(
        sidor={None: {"threads": [{"id": "ny"}, {"id": "gammal"}]}},
        tradar={"ny": _trad([i_gar], "ny"),
                "gammal": _trad([for_gammal], "gammal")},
    )

    tradar, _ = inkorg.dagens_tradar(
        inkorg.Lastjanst(tjanst), utfil=tmp_path / "skord.jsonl",
        nu=_nu(dag=15, timme=5, minut=10))

    assert [t["id"] for t in tradar] == ["ny"]


def test_gallringen_andrar_inte_DYGNSGRANSEN():
    """`labelIds` och `internalDate` bär urvalet och måste överleva."""
    granser = inkorg.fonstrets_granser(_nu(dag=15))
    dagens = _kundmail()
    dagens["internalDate"] = _ms(_nu(dag=15, timme=9))
    gammalt = _kundmail()
    gammalt["internalDate"] = _ms(_nu(dag=13, timme=9))

    tradar = [_trad([dagens], "ny"), _trad([gammalt], "gammal")]
    gallrade = [inkorg.gallra_trad(t) for t in tradar]

    assert [t["id"] for t in inkorg.tradar_fran_dagen(gallrade, granser=granser)] \
        == [t["id"] for t in inkorg.tradar_fran_dagen(tradar, granser=granser)] \
        == ["ny"]


def test_SPAM_och_TRASH_overlever_gallringen():
    granser = inkorg.fonstrets_granser(_nu(dag=15))
    skrap = _kundmail(etiketter=["SPAM"])
    skrap["internalDate"] = _ms(_nu(dag=15, timme=9))

    gallrad = inkorg.gallra_trad(_trad([skrap]))

    assert inkorg.tradar_fran_dagen([gallrad], granser=granser) == []


# ------------------- DEL 4: listan över huvuden får inte driva isär


def test_varje_huvud_kedjan_LASER_ETT_VARDE_ur_star_i_HUVUDEN_MED_VARDE():
    """**GALLRINGENS FARLIGASTE FELFORM, och den är tyst.**

    Läggs ett `urval.huvudvarde(meddelande, "x-nytt")` till i sållningen, och
    står `x-nytt` inte i `HUVUDEN_MED_VARDE`, skrivs värdet aldrig till skörden.
    Testsviten bygger sina meddelanden själv och ser fullständiga huvuden, alltså
    är den grön. I drift läser samma kod ett tomt värde och klassar mailet
    annorlunda. Ingenting blir rött.

    Raden läser KÄLLTEXTEN till kedjans moduler och fäller varje namn som läses
    men inte står i listan. `MASKINHUVUDEN` och `LEVERANSHUVUDEN` behöver ingen
    sådan rad: dem importerar `src/inkorg.py`.

    **TRE ANROPSFORMER LÄSES, OCH EN FJÄRDE FINNS INTE UTAN ATT TESTET FÄLLER.**
    Första lydelsen läste två: `huvudvarde(m, "namn")` och `adresser(m, {"namn"})`
    med literaler. `urval.kundadress` använder en tredje, en for-slinga över en
    tupel av namn med `adresser(m, {huvud})`, och den formen såg lydelsen inte
    alls. Att `reply-to` och `from` ändå stod i listan var en slump: de skrivs
    som literaler i `klassa_maskin`. Hade `kundadress` en dag föredragit
    `x-original-from` för en förmedlad förfrågan hade sviten varit grön medan
    gallringen tömde huvudet i drift, och kundens ärende fått fel
    `avsandare_hash`.

    Den formen läses nu. Och det viktiga: varje anrop vars namn INTE går att
    läsa statiskt gör testet RÖTT i stället för att hoppas över. En blind fläck
    som tiger är precis den felform posten beskriver, alltså får den inte
    finnas. Fällt av §7-granskningen av skiva 54.
    """
    import ast

    rot = Path(__file__).resolve().parent.parent
    lasta: dict[str, str] = {}
    mottagarlasta: dict[str, str] = {}
    olasbara: list[str] = []

    def _namn_ur(nod) -> list[str] | None:
        """Huvudnamnen ett argument står för, eller None när det inte går att
        läsa statiskt."""
        if isinstance(nod, ast.Constant) and isinstance(nod.value, str):
            return [nod.value]
        if isinstance(nod, (ast.Set, ast.Tuple, ast.List)):
            ut = []
            for post in nod.elts:
                if not (isinstance(post, ast.Constant)
                        and isinstance(post.value, str)):
                    return None
                ut.append(post.value)
            return ut
        return None

    for modulnamn in ("urval", "klassa_maskin", "kanal"):
        kalla = (rot / "src" / f"{modulnamn}.py").read_text(encoding="utf-8")
        trad = ast.parse(kalla)

        # FORM 3: `for huvud in ("reply-to", "from"): ... adresser(m, {huvud})`.
        # Slingvariabeln binds till tupelns namn, så att anropet nedan går att
        # läsa. Bara slingor vars iterabel är en literal av strängar; allt annat
        # lämnas obundet och fälls av kontrollen längre ned.
        bundna: dict[str, list[str]] = {}
        for nod in ast.walk(trad):
            if isinstance(nod, ast.For) and isinstance(nod.target, ast.Name):
                varden = _namn_ur(nod.iter)
                if varden:
                    bundna[nod.target.id] = varden

        for nod in ast.walk(trad):
            if not isinstance(nod, ast.Call):
                continue
            funktion = nod.func.attr if isinstance(nod.func, ast.Attribute) \
                else getattr(nod.func, "id", "")
            if funktion not in ("huvudvarde", "adresser") or len(nod.args) < 2:
                continue

            argument = nod.args[1]
            namn = _namn_ur(argument)

            # FORM 3, fortsättning: en mängd som bara bär slingvariabeln.
            if namn is None and isinstance(argument, (ast.Set, ast.Tuple,
                                                      ast.List)):
                samlat: list[str] = []
                for post in argument.elts:
                    if isinstance(post, ast.Name) and post.id in bundna:
                        samlat.extend(bundna[post.id])
                    elif (isinstance(post, ast.Constant)
                          and isinstance(post.value, str)):
                        samlat.append(post.value)
                    else:
                        samlat = []
                        break
                namn = samlat or None
            elif namn is None and isinstance(argument, ast.Name) \
                    and argument.id in bundna:
                namn = bundna[argument.id]

            # SKIVA 69. `adresser(m, MOTTAGARHUVUDEN)` i `ar_gmail_svar` LÄSER
            # värden. Här stod att `inkorg` importerar mängden och tar med den
            # av sig självt. Det var falskt, och det var så gallringen kunde
            # tömma `to` och `cc` med sviten grön. Mängden slås nu upp, och
            # `bcc` är det enda namnet som får gallras, Lars beslut i skiva 54.
            if isinstance(argument, ast.Name) and argument.id == "MOTTAGARHUVUDEN":
                for h in urval.MOTTAGARHUVUDEN - {"bcc"}:
                    mottagarlasta[h] = f"src/{modulnamn}.py"
                continue

            if namn is None:
                # EN MÄNGD SOM IMPORTERAS är inte en blind fläck: `inkorg`
                # importerar `LEVERANSHUVUDEN` och `MASKINHUVUDEN` och tar med
                # dem av sig självt. Bara sådana namn får passera, och de
                # namnges här. `SVARSHUVUDEN` och `MASSUTSKICKSHUVUDEN` läses
                # på förekomst och aldrig med värde.
                if isinstance(argument, ast.Name) and argument.id in (
                        "LEVERANSHUVUDEN", "MASKINHUVUDEN",
                        "MASSUTSKICKSHUVUDEN", "SVARSHUVUDEN", "namn"):
                    continue
                olasbara.append(
                    f"src/{modulnamn}.py:{nod.lineno} {funktion}(...) "
                    f"med ett argument som inte går att läsa statiskt"
                )
                continue

            for h in namn:
                lasta[h.lower()] = f"src/{modulnamn}.py"

    # Att uppräkningen inte tystnade, och att den ser den tredje formen.
    assert len(lasta) >= 4, "hittade inga huvudläsningar alls i källtexten"
    assert "reply-to" in lasta and "from" in lasta, (
        "genomgången ser inte `urval.kundadress`:s for-slinga över namn; "
        "då är den blind för den anropsformen"
    )

    assert not olasbara, (
        "en huvudläsning vars namn inte går att läsa ur källtexten: "
        + "; ".join(olasbara)
        + ". Skriv namnet som en literal, eller lägg mängden i uppräkningen "
        "över importerade mängder i det här testet."
    )

    saknade = {h: var for h, var in lasta.items()
               if h not in inkorg.HUVUDEN_MED_VARDE}
    assert not saknade, (
        f"läses med VÄRDE men gallras bort ur skörden: {saknade}. "
        "Lägg namnet i inkorg.HUVUDEN_MED_VARDE."
    )

    assert mottagarlasta, "genomgången ser inte `ar_gmail_svar`:s mottagare"
    saknade = {h: var for h, var in mottagarlasta.items()
               if h not in inkorg.MOTTAGARE_MED_VARDE}
    assert not saknade, (
        f"mottagare läses med VÄRDE men gallras bort ur skörden: {saknade}. "
        "Lägg namnet i inkorg.MOTTAGARE_MED_VARDE."
    )


def test_ett_nytt_MASKINHUVUD_foljer_med_till_skorden_av_sig_sjalvt():
    """Mängderna importeras och skrivs inte av.

    Prövas genom att lägga till ett namn i `klassa_maskin.MASKINHUVUDEN` och
    räkna om, inte genom att jämföra två handskrivna listor.
    """
    assert "x-msg-eid" in inkorg.HUVUDEN_SOM_LASES
    assert klassa_maskin.MASKINHUVUDEN <= inkorg.HUVUDEN_SOM_LASES
    assert urval.LEVERANSHUVUDEN <= inkorg.HUVUDEN_SOM_LASES


def test_gallringen_ar_AV_som_forval_i_mine():
    """Miningens egna skördar rörs inte.

    `src/extract.py` bygger par ur hela trådar. Skördens gallring kastar
    kundmailens mottagare, `Bcc` och svarshuvudenas värden, alltså hade en
    påslagen gallring i `mine.mina` tömt miningens skördar på det.

    *Här stod att varken svarshuvudena eller mottagarna står i skördens lista.
    Skiva 69 DEL A lade tillbaka dem, se `inkorg.MOTTAGARE_MED_VARDE`.*
    """
    import inspect
    from src import mine

    assert inspect.signature(mine.mina).parameters["gallra"].default is None
    assert "bcc" not in inkorg.HUVUDEN_SOM_LASES | inkorg.MOTTAGARE_MED_VARDE
