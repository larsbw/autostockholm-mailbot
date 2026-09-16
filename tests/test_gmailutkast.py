"""GMAIL-UTKASTET, skiva 68. Sändväg i §7:s mening.

Lars §10-beslut: gmail.compose, egen token, lager 1 faller, lager 2 till 4
byggs om. Utkastet skapas av knappen i vyn och aldrig av den dagliga körningen.

**INGET TEST HÄR RÖR NÄTET ELLER EN RIKTIG BREVLÅDA.** Tjänsten är en fejk som
spelar in anropen, och varje adress är påhittad (§6).
"""

from __future__ import annotations

import base64
import email
import email.policy
import json
from pathlib import Path

import pytest

from src import auth, gmailutkast, vy
from tests.test_respond import SVAR, meddelande, respond, trad
from tests.test_kedja import NU, FejkKlient, HINKAR, TAXONOMI, hamta_gront
from tests.test_vy import FejkHanterare, ett_fall, peka_om_katalogerna

ROT = Path(__file__).resolve().parent.parent

VAG = vy.Svarsvag(
    trad_id="t-123",
    meddelande_id="<kund-1@exempel.invalid>",
    mottagare="kund@exempel.invalid",
    amne="Ombyggnad av min bil",
)


def post(**andrat) -> vy.Granskningsfall:
    grund = {"fall": ett_fall(), "forslag": "Hej!\n\nVi kan ta emot bilen.",
             "svarsvag": VAG}
    grund.update(andrat)
    return vy.Granskningsfall(**grund)


class FejkDrafts:
    """Spelar in `create` och svarar som Gmail. Har ingen `send`: den ska
    aldrig nås, och gör den det är det lager 2 som brustit."""

    def __init__(self, logg, tradsvar):
        self._logg = logg
        self._tradsvar = tradsvar

    def create(self, **kw):
        self._logg.append(("create", kw))
        svar = {"id": "r-1", "message": {"id": "m-1", "threadId":
                                         self._tradsvar(kw)}}

        class Anrop:
            def execute(self_):
                return svar
        return Anrop()


class FejkRa:
    """Den RÅA tjänsten. Bär `send` överallt, så att ett genomsläpp syns."""

    def __init__(self, tradsvar=None):
        self.logg = []
        self._tradsvar = tradsvar or (lambda kw: kw["body"]["message"]["threadId"])

    def users(self):
        return self

    def drafts(self):
        ra = FejkDrafts(self.logg, self._tradsvar)
        ra.send = lambda **kw: self.logg.append(("drafts.send", kw))
        return ra

    def messages(self):
        class M:
            send = staticmethod(lambda **kw: self.logg.append(("send", kw)))
        return M()


# ------------------------------------------------------ LAGER 1: faller

def test_SKRIVSCOPES_ar_compose_och_ingenting_annat():
    """Lars beslut. compose är det snävaste av de tre som `drafts.create` tar."""
    assert auth.SKRIVSCOPES == ["https://www.googleapis.com/auth/gmail.compose"]


@pytest.mark.parametrize("scopes", [
    auth.SCOPES,
    auth.LASSCOPES,
    auth.SKRIVSCOPES + ["https://www.googleapis.com/auth/gmail.send"],
    None,
])
def test_krav_pa_bara_utkast_faller_allt_utom_compose(scopes):
    """Pekar någon utkastvägen mot `token.json` ska den falla: den bär
    gmail.send och gmail.modify."""
    class FejkCred:
        pass
    FejkCred.scopes = scopes

    with pytest.raises(auth.Scopefel):
        auth.krav_pa_bara_utkast(FejkCred())


def test_krav_pa_bara_utkast_slapper_compose():
    """NEGATIVKONTROLL."""
    class FejkCred:
        scopes = list(auth.SKRIVSCOPES)

    auth.krav_pa_bara_utkast(FejkCred())


def test_skrivtokenet_ar_en_TREDJE_fil_och_ignorerad():
    """Tre auktoriseringar, tre filer. Skrivtokenet kan skicka."""
    assert len({auth.TOKEN, auth.LASTOKEN, auth.SKRIVTOKEN}) == 3
    for fil in (".gitignore", ".dockerignore"):
        rader = (ROT / fil).read_text(encoding="utf-8").split()
        assert auth.SKRIVTOKEN.name in rader, f"{fil} saknar token-skriv.json"


def test_hamta_skriv_credentials_gar_INTE_att_be_om_andra_scope():
    import inspect
    assert "scopes" not in inspect.signature(
        auth.hamta_skriv_credentials).parameters


def test_skrivvagen_fallerar_utan_token_och_anvisar_RATT_kommando(tmp_path):
    """Utan webbläsare är en saknad token ett §10-stopp, och kommandot i
    meddelandet ska begära compose och inget annat."""
    with pytest.raises(auth.AuthFel, match="--skriv --auktorisera"):
        auth.hamta_skriv_credentials(token_sokvag=auth.SKRIVTOKEN.with_name(
            "finns-inte-token-skriv.json"))


def test_krav_pa_bara_utkast_KORS_av_hamtningen(tmp_path, monkeypatch):
    """Utan anropet i `hamta_skriv_credentials` hade `token.json` gått rakt
    igenom som utkastvägens credential."""
    class FejkCred:
        scopes = list(auth.SCOPES)
    monkeypatch.setattr(auth, "hamta_credentials", lambda **_: FejkCred())

    with pytest.raises(auth.Scopefel):
        auth.hamta_skriv_credentials()


# ------------------------------------------------------ LAGER 2: tjänsten

def test_drafts_send_KASTAR():
    tjanst = gmailutkast.Utkastjanst(FejkRa())
    with pytest.raises(gmailutkast.Sandforsok, match="send"):
        tjanst.users().drafts().send(userId="me", body={})


def test_messages_send_KASTAR():
    tjanst = gmailutkast.Utkastjanst(FejkRa())
    with pytest.raises(gmailutkast.Sandforsok, match="messages"):
        tjanst.users().messages()


@pytest.mark.parametrize("metod", ["update", "delete", "list", "get"])
def test_varje_annan_drafts_metod_KASTAR(metod):
    tjanst = gmailutkast.Utkastjanst(FejkRa())
    with pytest.raises(gmailutkast.Sandforsok):
        getattr(tjanst.users().drafts(), metod)


@pytest.mark.parametrize("resurs", ["threads", "settings", "labels"])
def test_varje_annan_resurs_KASTAR(resurs):
    tjanst = gmailutkast.Utkastjanst(FejkRa())
    with pytest.raises(gmailutkast.Sandforsok):
        getattr(tjanst.users(), resurs)


def test_drafts_create_GAR_IGENOM():
    """NEGATIVKONTROLL: en spärr som stoppar allt stoppar också arbetet."""
    ra = FejkRa()
    gmailutkast.Utkastjanst(ra).users().drafts().create(
        userId="me", body={"message": {"threadId": "x"}}).execute()
    assert [namn for namn, _ in ra.logg] == ["create"]


def test_skriv_tjanst_lamnar_ut_den_INLINDADE(monkeypatch):
    ra = FejkRa()
    monkeypatch.setattr(gmailutkast.auth, "hamta_skriv_credentials",
                        lambda **_: object())
    monkeypatch.setattr(gmailutkast.auth, "bygg_tjanst", lambda cred: ra)

    tjanst = gmailutkast.skriv_tjanst()

    assert isinstance(tjanst, gmailutkast.Utkastjanst)
    with pytest.raises(gmailutkast.Sandforsok):
        tjanst.users().drafts().send(userId="me", body={})


# ------------------------------------------------------ LAGER 3: importen

def test_gmailutkast_ar_NAMNGIVEN():
    assert "src.gmailutkast" in vy.GMAILBARANDE_MODULER


@pytest.mark.parametrize("start", ["src.vy", "src.kedja", "scripts.respond",
                                   "scripts.dagligen", "scripts.kedja-prov"])
def test_dagliga_korningen_nar_ALDRIG_gmailutkast(start):
    """INGEN AUTOMATISK SKRIVNING. Vyn, kedjan och den dagliga körningen har
    inte modulen i sin graf. Vyn får funktionen injicerad."""
    assert "src.gmailutkast" not in vy.moduler_i_vyn(start)


def test_serva_ar_den_graf_som_bar_gmailutkast():
    """Negativkontroll till raden ovan: vandringen hittar modulen där den finns,
    och `scripts/serva.py` klarar spärren med den namngiven."""
    assert "src.gmailutkast" in vy.moduler_i_vyn("scripts.serva")
    vy.krav_pa_sandvagsfrihet("scripts.serva", tillatna=vy.UNDANTAGBARA)


def test_serva_KOR_sparren_vid_start(monkeypatch):
    """Anropet i `serva.main` är det som fäller en onamngiven Gmail-modul i drift."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "serva_under_test", ROT / "scripts" / "serva.py")
    serva = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(serva)

    anrop = []

    def fall(*a, **k):
        anrop.append((a, k))
        raise vy.Sandvagsfel("prov")
    monkeypatch.setattr(serva.vy, "krav_pa_sandvagsfrihet", fall)

    with pytest.raises(vy.Sandvagsfel):
        serva.main(["--lokalt"])

    # FÖRSTA ANROPET ÄR SERVAS EGET. `vy.starta` anropar samma funktion utan
    # argument, och utan raden var testet rött av det anropet i stället.
    assert anrop[0] == (("scripts.serva",), {"tillatna": vy.UNDANTAGBARA})


# ------------------------------------------------------ LAGER 4: källtexten

def test_drafts_send_FALLS_av_kalltextlagret(tmp_path):
    """Före skiva 68 bar mönstret bara messages().send."""
    (tmp_path / "src").mkdir()
    (tmp_path / "src" / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "src" / "gmailutkast.py").write_text(
        "def ut(t):\n    return t.users().drafts().send(userId='me').execute()\n",
        encoding="utf-8")
    (tmp_path / "src" / "start.py").write_text(
        "from src import gmailutkast\n", encoding="utf-8")

    with pytest.raises(vy.Sandvagsfel, match="drafts\\(\\).send"):
        vy.krav_pa_sandvagsfrihet("src.start", rot=tmp_path,
                                  tillatna=vy.UNDANTAGBARA)


def test_drafts_create_falls_INTE_av_kalltextlagret():
    """Negativkontroll: mönstret får inte fälla det enda tillåtna anropet."""
    assert not vy.FORBJUDET_MONSTER.search(
        vy._kod_utan_prosa("t.users().drafts().create(userId='me')"))


# ------------------------------------------------------ DEL B: tråden

def _avkodat(kropp: dict):
    raa = base64.urlsafe_b64decode(kropp["message"]["raw"])
    return email.message_from_bytes(raa, policy=email.policy.default)


def test_utkastet_ar_ett_SVAR_i_kundens_trad():
    kropp = gmailutkast.bygg_meddelande(post())
    brev = _avkodat(kropp)

    assert kropp["message"]["threadId"] == "t-123"
    assert brev["To"] == "kund@exempel.invalid"
    assert brev["Subject"] == "Re: Ombyggnad av min bil"
    assert brev["In-Reply-To"] == "<kund-1@exempel.invalid>"
    assert brev["References"] == "<kund-1@exempel.invalid>"
    assert brev.get_content().strip() == "Hej!\n\nVi kan ta emot bilen."
    assert brev["From"] is None


def test_svenska_tecken_i_amne_och_text_overlever():
    vag = vy.Svarsvag(**{**VAG.__dict__, "amne": "Fråga om dragkrok på Volvo"})
    brev = _avkodat(gmailutkast.bygg_meddelande(
        post(svarsvag=vag, forslag="Hej! Vi återkommer, välkommen.")))

    assert brev["Subject"] == "Re: Fråga om dragkrok på Volvo"
    assert "återkommer, välkommen" in brev.get_content()


@pytest.mark.parametrize("amne, vantat", [
    ("Re: Fråga", "Re: Fråga"),
    ("SV: Fråga", "SV: Fråga"),
    ("RE:Fråga", "RE:Fråga"),
    ("Refråga", "Re: Refråga"),
])
def test_svarsprefixet_laggs_inte_DUBBELT(amne, vantat):
    assert gmailutkast.svarsamne(amne) == vantat


def test_ett_utkast_i_FEL_trad_kastar():
    """Token auktoriserat för fel konto: tråden finns inte där."""
    tjanst = gmailutkast.Utkastjanst(FejkRa(tradsvar=lambda kw: "annan"))

    with pytest.raises(gmailutkast.EjUtkastbar, match="r-1"):
        gmailutkast.skapa_utkast(tjanst, post())


def test_skapa_utkast_ger_gmails_meddelande_id():
    ra = FejkRa()
    assert gmailutkast.skapa_utkast(gmailutkast.Utkastjanst(ra), post()) == "m-1"
    assert ra.logg[0][1]["userId"] == "me"


# ------------------------------------------------------ DEL C: vad som får

@pytest.mark.parametrize("andrat, skal", [
    ({"inget_svar": True}, "inget svar"),
    ({"sparr": "talspärren"}, "spärrad"),
    ({"forslag": "   "}, "inget utkast"),
    ({"svarsvag": None}, "ingen svarsväg"),
    ({"svarsvag": vy.Svarsvag(**{**VAG.__dict__, "trad_id": ""})}, "trad_id"),
    ({"svarsvag": vy.Svarsvag(**{**VAG.__dict__, "meddelande_id": ""})},
     "meddelande_id"),
    ({"svarsvag": vy.Svarsvag(**{**VAG.__dict__, "mottagare": ""})},
     "mottagare"),
    ({"svarsvag": vy.Svarsvag(**{**VAG.__dict__, "amne": ""})}, "amne"),
    ({"svarsvag": vy.Svarsvag(**{**VAG.__dict__, "mottagare": "ingen"})},
     "ingen adress"),
])
def test_varje_VAGRAN_i_modulen_faller_for_sig(andrat, skal):
    """Varje led en rad (§7.1). Och ingenting når Gmail."""
    ra = FejkRa()
    with pytest.raises(gmailutkast.EjUtkastbar, match=skal):
        gmailutkast.skapa_utkast(gmailutkast.Utkastjanst(ra), post(**andrat))
    assert ra.logg == []


VARD = "127.0.0.1:8765"


class Post(FejkHanterare):
    """En begäran från vyn själv: `Origin` stämmer med `Host`."""

    def __init__(self, hanterare, vag, origin=f"http://{VARD}"):
        super().__init__(hanterare, vag)
        self.headers["Host"] = VARD
        if origin is not None:
            self.headers["Origin"] = origin


class Spion:
    def __init__(self, fel=None, logg=None):
        self.poster = []
        self._fel = fel
        self._logg = logg
        self.logg_vid_anropet = None

    def __call__(self, p):
        self.poster.append(p)
        if self._logg is not None:
            self.logg_vid_anropet = self._logg.read_text(encoding="utf-8")
        if self._fel:
            raise self._fel
        return "m-1"


@pytest.fixture
def katalog(tmp_path, monkeypatch):
    peka_om_katalogerna(monkeypatch, tmp_path)
    return tmp_path


def _fejk(poster, spion, vag, katalog):
    hanterare = vy.bygg_hanterare(
        [], granskning=poster, skapa_utkast=spion,
        omdomesfil=katalog / "logg" / "omdomen.jsonl")
    return Post(hanterare, vag)


@pytest.mark.parametrize("andrat", [
    {"sparr": "talspärren"},
    {"inget_svar": True},
    {"svarsvag": None},
])
def test_en_SPARRAD_eller_ofullstandig_post_nar_ALDRIG_gmail(andrat, katalog):
    """DEL C: en spärrad post blir aldrig ett Gmail-utkast. Vyns egna vägran,
    prövad med modulens vägran bortkopplad: spionen vägrar ingenting."""
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion()
    fejk = Post(vy.bygg_hanterare(
        [], granskning=[post(**andrat)], skapa_utkast=spion,
        omdomesfil=omdomen), "/gmailutkast/0")
    fejk.post()

    assert fejk.kod == 400
    assert spion.poster == []
    assert not omdomen.exists()


def test_en_GODKAND_post_blir_ett_utkast_och_ett_OMDOME(katalog):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion()
    hanterare = vy.bygg_hanterare([], granskning=[post()], skapa_utkast=spion,
                                  omdomesfil=omdomen)
    fejk = Post(hanterare, "/gmailutkast/0")
    fejk.post()

    assert fejk.kod == 200
    assert "m-1" in fejk.svar
    assert len(spion.poster) == 1
    rader = [json.loads(r) for r in
             omdomen.read_text(encoding="utf-8").splitlines()]
    assert [r["utfall"] for r in rader] == ["begärt", "skapat"]
    assert all(r["omdome"] == vy.OMDOME_GMAILUTKAST for r in rader)
    assert all(r["trad_id"] == "t-123" for r in rader)
    assert rader[1]["gmail_id"] == "m-1"
    # §6: loggen bär ingen adress och ingen text.
    assert "exempel.invalid" not in omdomen.read_text(encoding="utf-8")
    assert "ta emot bilen" not in omdomen.read_text(encoding="utf-8")


def test_ett_ANDRA_tryck_ger_inget_andra_utkast(katalog):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion()
    hanterare = vy.bygg_hanterare([], granskning=[post()], skapa_utkast=spion,
                                  omdomesfil=omdomen)
    Post(hanterare, "/gmailutkast/0").post()
    andra = Post(hanterare, "/gmailutkast/0")
    andra.post()

    assert andra.kod == 400
    assert len(spion.poster) == 1


def test_ett_utkast_i_EN_trad_hindrar_inte_en_ANNAN(katalog):
    """Negativkontroll: spärren gäller tråden och inte vilket utkast som helst."""
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion()
    annan = post(svarsvag=vy.Svarsvag(**{**VAG.__dict__, "trad_id": "t-2"}))
    hanterare = vy.bygg_hanterare([], granskning=[post(), annan],
                                  skapa_utkast=spion, omdomesfil=omdomen)
    Post(hanterare, "/gmailutkast/0").post()
    andra = Post(hanterare, "/gmailutkast/1")
    andra.post()

    assert andra.kod == 200
    assert len(spion.poster) == 2


def test_ett_MISSLYCKAT_forsok_SPARRAR_traden(katalog):
    """§7-granskningen av skiva 68: kontrollen av tråden kastar EFTER att Gmail
    skapat utkastet. Loggades inget försök gav varje nytt tryck ett nytt
    utkast som kan skickas."""
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion(fel=gmailutkast.EjUtkastbar("fel tråd"))
    hanterare = vy.bygg_hanterare([], granskning=[post()], omdomesfil=omdomen,
                                  skapa_utkast=spion)
    fejk = Post(hanterare, "/gmailutkast/0")
    fejk.post()
    andra = Post(hanterare, "/gmailutkast/0")
    andra.post()

    assert fejk.kod == 400
    assert "fel tråd" in fejk.svar
    assert andra.kod == 400
    assert len(spion.poster) == 1
    utfall = [json.loads(r)["utfall"] for r in
              omdomen.read_text(encoding="utf-8").splitlines()]
    assert utfall == ["begärt", "misslyckades"]


def test_forsoket_LOGGAS_INNAN_gmail_nas(katalog):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    spion = Spion(logg=omdomen)
    hanterare = vy.bygg_hanterare([], granskning=[post()], omdomesfil=omdomen,
                                  skapa_utkast=spion)
    Post(hanterare, "/gmailutkast/0").post()

    assert '"begärt"' in spion.logg_vid_anropet


@pytest.mark.parametrize("origin", [None, "https://ond.example",
                                    "http://127.0.0.1:9999"])
def test_en_begaran_fran_ANNAN_SIDA_nar_aldrig_gmail(origin, katalog):
    """CSRF, §7-granskningen av skiva 68. `--lokalt` har ingen session."""
    spion = Spion()
    fejk = Post(vy.bygg_hanterare(
        [], granskning=[post()], skapa_utkast=spion,
        omdomesfil=katalog / "logg" / "omdomen.jsonl"),
        "/gmailutkast/0", origin=origin)
    fejk.post()

    assert fejk.kod == 400
    assert spion.poster == []


def test_loggspärren_provas_FORE_utkastet(tmp_path):
    """Ett utkast som inte går att logga hade inte hindrat ett andra tryck."""
    spion = Spion()
    hanterare = vy.bygg_hanterare([], granskning=[post()], skapa_utkast=spion,
                                  omdomesfil=tmp_path / "utanfor.jsonl")
    fejk = Post(hanterare, "/gmailutkast/0")
    fejk.post()

    assert fejk.kod == 400
    assert spion.poster == []


def test_utan_injicerad_funktion_VAGRAR_rutten(katalog):
    fejk = Post(vy.bygg_hanterare([], granskning=[post()]),
                         "/gmailutkast/0")
    fejk.post()
    assert fejk.kod == 400
    assert "inte inkopplat" in fejk.svar


@pytest.mark.parametrize("vag", ["/gmailutkast", "/gmailutkast/1",
                                 "/gmailutkast/0/../0"])
def test_rutten_KLAMPAR_ALDRIG(vag, katalog):
    spion = Spion()
    fejk = _fejk([post()], spion, vag, katalog)
    fejk.post()
    assert fejk.kod == 400
    assert spion.poster == []


def test_knappen_visas_BARA_med_funktion_och_svarsvag():
    def sida(p, spion):
        fejk = Post(
            vy.bygg_hanterare([], granskning=[p], skapa_utkast=spion),
            "/granskning/0")
        fejk.get()
        return fejk.svar

    knapp = "action='/gmailutkast/0'"
    assert knapp in sida(post(), Spion())
    assert knapp not in sida(post(), None)
    assert knapp not in sida(post(svarsvag=None), Spion())
    assert knapp not in sida(post(sparr="talspärren"), Spion())


def test_knappen_renderas_aldrig_i_SPARRGRENEN():
    assert "gmailutkast" not in vy.rendera_granskning(
        ett_fall(), "", sparr="talspärren", gmailknapp=True)
    assert "gmailutkast" not in vy.rendera_granskning(
        ett_fall(), "", inget_svar=True, gmailknapp=True)


def test_starta_LAMNAR_VIDARE_funktionen():
    spion = Spion()
    server = vy.starta(port=0, fall=[], granskning=[post()],
                       skapa_utkast=spion)
    try:
        fejk = Post(server.RequestHandlerClass, "/granskning/0")
        fejk.get()
        assert "action='/gmailutkast/0'" in fejk.svar
    finally:
        server.server_close()


# ------------------------------------------------------ svarsvägen

def test_svarsvagen_overlever_filen(katalog):
    fil = katalog / "data" / "granskningsfall.jsonl"
    vy.spara_granskningsfall([post(), post(svarsvag=None)], fil)

    lasta = vy.las_granskningsfall(fil)
    assert lasta[0].svarsvag == VAG
    assert lasta[1].svarsvag is None


def test_en_gammal_fil_UTAN_nyckeln_ger_ingen_svarsvag(katalog):
    fil = katalog / "data" / "granskningsfall.jsonl"
    vy.spara_granskningsfall([post()], fil)
    rad = json.loads(fil.read_text(encoding="utf-8"))
    del rad["svarsvag"]
    fil.write_text(json.dumps(rad) + "\n", encoding="utf-8")

    assert vy.las_granskningsfall(fil)[0].svarsvag is None


def test_svarsvagen_ur_en_FORMULARNOTIS_gar_till_reply_to():
    """Notisen bär `From` lika med brevlådan och kunden i `Reply-To`."""
    notis = meddelande("Hej, går ABC12X att bygga om?", sent=True, huvuden={
        "From": "info@autostockholm.se",
        "Reply-To": "kund@exempel.invalid",
        "Delivered-To": "info@autostockholm.se",
        "Subject": "Nytt formulär",
        "Message-ID": "<form-1@exempel.invalid>",
    })

    vag = respond.svarsvag_ur_trad(trad(notis, trad_id="t9"))

    assert vag == vy.Svarsvag(trad_id="t9",
                              meddelande_id="<form-1@exempel.invalid>",
                              mottagare="kund@exempel.invalid",
                              amne="Nytt formulär")


def test_svarsvagen_pekar_pa_SAMMA_meddelande_som_texten():
    """Utkastet svarar på den text som bedömdes: trådens första kundmail."""
    forsta = meddelande("Första", huvuden={"Message-ID": "<a@x.invalid>"},
                        internal="1757900000000")
    andra = meddelande("Andra", huvuden={"Message-ID": "<b@x.invalid>"},
                       internal="1757990000000")

    vag = respond.svarsvag_ur_trad(trad(forsta, andra))
    arende, _ = respond.arende_ur_trad(trad(forsta, andra), set())

    assert vag.meddelande_id == "<a@x.invalid>"
    assert arende.text == "Första"


def test_slingan_lagger_svarsvagen_pa_RATT_granskningsfall(katalog):
    arenden = [respond.Arende(text="Hej ABC12X", regnr="ABC12X"),
               respond.Arende(text="Hej DEF34Y", regnr="DEF34Y")]
    vagar = [VAG, vy.Svarsvag(**{**VAG.__dict__, "trad_id": "t-2"})]
    korning = respond.Korning(tradar=2)

    respond.kor_alla(
        arenden, klient=FejkKlient(*SVAR, *SVAR), hamta=hamta_gront,
        hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
        korning=korning, nu=NU, loggfil=katalog / "logg" / "beslut.jsonl",
        skriv=lambda *_: None, svarsvagar=vagar)

    assert [g.svarsvag.trad_id for g in korning.granskningsfall] == \
        ["t-123", "t-2"]


def test_slingan_VAGRAR_olika_langd(katalog):
    with pytest.raises(ValueError):
        respond.kor_alla(
            [respond.Arende(text="x")], klient=None, hamta=hamta_gront,
            hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
            korning=respond.Korning(), nu=NU,
            loggfil=katalog / "logg" / "beslut.jsonl",
            skriv=lambda *_: None, svarsvagar=[])
