"""LAGER 1 OCH 2 i skugglägets väg till brevlådan: scopet och den kapade tjänsten.

Lars §10-beslut i skiva 48, se `docs/beslutslogg.md` #113. Lager 3 och 4,
importlagret och källtextlagret, prövas i `tests/test_respond.py`.

**INGET TEST HÄR RÖR NÄTET ELLER EN RIKTIG BREVLÅDA.** Tjänsten är
`tests/fejk.py::FejkGmail`, och tokenen är uppenbart påhittade strängar (§6).
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src import auth, inkorg
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


def _nu(ar=2026, manad=9, dag=15, timme=12):
    return datetime(ar, manad, dag, timme, tzinfo=inkorg.TIDSZON)


def _ms(dt: datetime) -> str:
    return str(int(dt.timestamp() * 1000))


def _medd(dt: datetime, *, sent=False, etiketter=None) -> dict:
    return {"internalDate": _ms(dt),
            "labelIds": list(etiketter or (["SENT"] if sent else ["INBOX"]))}


def test_dygnet_ar_EUROPE_STOCKHOLMS_och_inte_UTC():
    """Dygnet Lars menar är hans, inte serverns.

    Klockan 01:00 svensk tid den 15:e är 23:00 UTC den 14:e. Ett dygn räknat i
    UTC hade lagt just det mailet på fel dag, och i skuggläget syns det som ett
    ärende som aldrig kom in.
    """
    borjan, slut = inkorg.dygnets_granser(_nu())

    tidigt = datetime(2026, 9, 15, 1, 0, tzinfo=inkorg.TIDSZON)
    assert borjan <= int(_ms(tidigt)) < slut
    assert tidigt.astimezone(timezone.utc).day == 14


def test_slutet_ar_EXKLUSIVT():
    """Nästa dygns första millisekund hör till nästa dygn."""
    borjan, slut = inkorg.dygnets_granser(_nu())

    assert not inkorg._ar_fran_dagen({"internalDate": str(slut)},
                                     (borjan, slut))
    assert inkorg._ar_fran_dagen({"internalDate": str(slut - 1)},
                                 (borjan, slut))


def test_ett_meddelande_UTAN_internalDate_raknas_inte_som_dagens():
    """Att gissa åt andra hållet hade tagit in varje odaterat mail varje dag."""
    granser = inkorg.dygnets_granser(_nu())

    assert not inkorg._ar_fran_dagen({}, granser)
    assert not inkorg._ar_fran_dagen({"internalDate": ""}, granser)


def test_en_trad_vars_enda_dagsfarska_meddelande_ar_VART_SVAR_tas_inte_med():
    """**ANNARS BESVARAS SAMMA TRÅD PÅ NYTT VARJE DAG VI SVARAR I DEN.**

    Kriteriet ligger på ett INKOMMANDE meddelande från dygnet. En tråd vars
    kundmail är från i förrgår och vars enda färska meddelande är vårt eget svar
    är inget nytt ärende.
    """
    granser = inkorg.dygnets_granser(_nu())
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
    granser = inkorg.dygnets_granser(_nu())
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
    assert "-in:sent" in inkorg.FRAGA


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
