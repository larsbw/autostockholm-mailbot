"""GMAIL-UTKASTET, skiva 68. Sändväg i §7:s mening.

Lars §10-beslut: gmail.compose, egen token, lager 1 faller, lager 2 till 4
byggs om. Utkastet skapas av knappen i vyn och, sedan skiva 69, av den dagliga
körningen utan granskning.

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

from src import auth, generera, gmailutkast, vy
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

    def delete(self, **kw):
        """UPPDRAG 2026-09-25 DEL 1. Tomt svar, se `ta_bort_utkast`s
        docstring: AVLÄST att ett lyckat anrop ger ett tomt JSON-objekt."""
        self._logg.append(("delete", kw))

        class Anrop:
            def execute(self_):
                return {}
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


@pytest.mark.parametrize("metod", ["update", "list", "get"])
def test_varje_annan_drafts_metod_KASTAR(metod):
    """`delete` STÅR INTE HÄR SEDAN UPPDRAGET 2026-09-25 DEL 1, se
    `test_drafts_delete_GAR_IGENOM` för dess egen, positiva kontroll."""
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


def test_drafts_delete_GAR_IGENOM():
    """NEGATIVKONTROLL, UPPDRAG 2026-09-25 DEL 1. Samma form som `create`s."""
    ra = FejkRa()
    gmailutkast.ta_bort_utkast(gmailutkast.Utkastjanst(ra), "d-1")
    assert ra.logg == [("delete", {"userId": "me", "id": "d-1"})]


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


@pytest.mark.parametrize("start", ["src.vy", "src.kedja",
                                   "scripts.dagligen", "scripts.kedja-prov"])
def test_vyn_och_kedjan_nar_ALDRIG_gmailutkast(start):
    """Vyn och kedjan har inte modulen i sin graf. Vyn får funktionen
    injicerad. `scripts.respond` stod här till och med skiva 68; Lars beslut i
    skiva 69 lade utkasten i den dagliga körningen."""
    assert "src.gmailutkast" not in vy.moduler_i_vyn(start)


def test_respond_bar_gmailutkast_och_KLARAR_sparren():
    """Skiva 69. `dagligen` startar respond som process och når den inte."""
    assert "src.gmailutkast" in vy.moduler_i_vyn("scripts.respond")
    vy.krav_pa_sandvagsfrihet("scripts.respond", tillatna=vy.UNDANTAGBARA)


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


def test_skapa_utkast_ger_gmails_meddelande_id_och_utkast_id():
    """UPPDRAG 2026-09-25 DEL 1: två skilda Gmail-id, se `UtkastResultat`."""
    ra = FejkRa()
    resultat = gmailutkast.skapa_utkast(gmailutkast.Utkastjanst(ra), post())
    assert resultat.meddelande_id == "m-1"
    assert resultat.utkast_id == "r-1"
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
        return gmailutkast.UtkastResultat(meddelande_id="m-1", utkast_id="d-1")


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


# ------------------------------------------ SKIVA 69: den dagliga körningen

SPARRAT = "Hej! Ombyggnaden kostar 12345 kronor.\n\nAuto Stockholm"


def _slinga(katalog, arenden, svar, spion, *, vagar=None, hamta=hamta_gront,
            stoppa=False, rader=None):
    korning = respond.Korning(tradar=len(arenden))
    respond.kor_alla(
        arenden, klient=FejkKlient(*svar), hamta=hamta,
        hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
        korning=korning, nu=NU, loggfil=katalog / "logg" / "beslut.jsonl",
        skriv=(lambda *_: None) if rader is None else rader.append,
        svarsvagar=vagar or [vy.Svarsvag(**{**VAG.__dict__,
                                            "trad_id": f"t-{i}"})
                             for i in range(len(arenden))],
        skapa_utkast=spion, omdomesfil=katalog / "logg" / "omdomen.jsonl",
        stoppa_vid_kallfel=stoppa)
    return korning


def _utfall(katalog):
    fil = katalog / "logg" / "omdomen.jsonl"
    if not fil.exists():
        return []
    return [(r["trad_id"], r["utfall"]) for r in
            map(json.loads, fil.read_text(encoding="utf-8").splitlines())]


def test_slingan_lagger_ett_PASSERAT_utkast_i_gmail(katalog):
    spion = Spion()
    rader = []
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X")],
                      SVAR, spion, rader=rader)

    assert korning.gmail_skapade == 1
    assert spion.poster == [korning.granskningsfall[0]]
    assert _utfall(katalog) == [("t-0", "begärt"), ("t-0", "skapat")]
    assert any("m-1" in r and "INTE skickat" in r for r in rader)


def test_ett_SPARRAT_arende_far_ALDRIG_ett_utkast(katalog):
    """DEL 0.1: oförändrat. Spionen vägrar ingenting, alltså är det slingan
    och `lagg_gmailutkast` som håller posten borta."""
    spion = Spion()
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X")],
                      (SVAR[0], SPARRAT), spion)

    assert korning.sparrade == 1
    assert spion.poster == []
    assert _utfall(katalog) == []


# ------------------------------------------ SKIVA 81: larmutkastet i slingan

WEBBFORMULARTEXT = (
    "Namn: Kim Andersson\nE-post: kim@exempel.invalid\n"
    "Telefon: 0701234567\nRegistreringsnummer: ABC12X\n"
    "Meddelande: Går det att bygga om min bil?"
)


class LarmSpion:
    """Spelar in anrop mot `skapa_larm`. Skiljt från `Spion` (kundutkast),
    eftersom de har olika signaturer: `skapa_larm` tar bara textargument."""

    def __init__(self, fel=None):
        self.anrop = []
        self._fel = fel

    def __call__(self, **kwargs):
        self.anrop.append(kwargs)
        if self._fel:
            raise self._fel
        return gmailutkast.UtkastResultat(meddelande_id="larm-1",
                                          utkast_id="larm-utkast-1")


def _slinga_med_larm(katalog, arenden, svar, *, skapa_larm, vagar=None):
    korning = respond.Korning(tradar=len(arenden))
    respond.kor_alla(
        arenden, klient=FejkKlient(*svar), hamta=hamta_gront,
        hinkar=HINKAR, taxonomi=TAXONOMI, exempel=[], skarp=True,
        korning=korning, nu=NU, loggfil=katalog / "logg" / "beslut.jsonl",
        skriv=lambda *_: None,
        svarsvagar=vagar or [VAG for _ in arenden],
        skapa_utkast=None, omdomesfil=katalog / "logg" / "omdomen.jsonl",
        skapa_larm=skapa_larm)
    return korning


def test_ALLA_FORSOK_SPARRAT_ger_ETT_LARMUTKAST(katalog):
    """Skiva 81, Lars beslut. Ett ärende spärrat på ALLA genereringsförsök
    ska ge exakt ETT larmutkast, med namn ur formuläret, kundens riktiga
    adress ur svarsvägen, datumet, VARJE försöks skäl och en sökväg till
    tråden."""
    larm = LarmSpion()
    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X",
                                 tidsstampel="2026-09-25T10:00:00+00:00")],
        (SVAR[0], SPARRAT), skapa_larm=larm)

    assert korning.sparrade == 1
    assert korning.larm_skapade == 1
    assert len(larm.anrop) == 1
    kwargs = larm.anrop[0]
    assert kwargs["regnr"] == "ABC12X"
    assert kwargs["kundnamn"] == "Kim Andersson"
    assert kwargs["kundepost"] == VAG.mottagare
    assert kwargs["datum"] == "2026-09-25T10:00:00+00:00"
    assert len(kwargs["forsok"]) == generera.MAX_GENERERINGSFORSOK
    for skal, sats in kwargs["forsok"]:
        assert "SENTINELPRIS" not in skal  # sanity: äkta text, inte ett stub
        assert skal and sats
    assert "rfc822msgid:" in kwargs["tradsokvag"]
    assert VAG.trad_id in kwargs["tradsokvag"]


def test_ALLA_FORSOK_SPARRAT_genom_den_RIKTIGA_gmailutkast_funktionen(katalog):
    """§7-granskningsfynd: `LarmSpion` ovan tar `**kwargs` och accepterar VAD
    SOM HELST, alltså hade den aldrig fällt en framtida namnändring i
    `_larmutkast`s anrop mot `gmailutkast.bygg_larmmeddelande`s riktiga
    parametrar. Den här körningen går genom den RIKTIGA
    `gmailutkast.larmutkastskapare` och en fejkad Gmail-tjänst, alltså fäller
    den ett sådant glapp med ett `TypeError` i stället för att tyst passera.
    """
    ra = FejkRa(tradsvar=lambda kw: "ny-fristaende-trad")
    larm = gmailutkast.larmutkastskapare(tjanst=gmailutkast.Utkastjanst(ra))

    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X",
                                 tidsstampel="2026-09-25T10:00:00+00:00")],
        (SVAR[0], SPARRAT), skapa_larm=larm)

    assert korning.larm_skapade == 1
    assert korning.larm_misslyckade == 0
    assert [namn for namn, _ in ra.logg] == ["create"]
    brev = _avkodat(ra.logg[0][1]["body"])
    assert brev["To"] == gmailutkast.LARMADRESS
    assert brev["Subject"].startswith("MANUELLT SVAR KRÄVS: ABC12X")
    assert "Kim Andersson" in brev.get_content()


@pytest.mark.parametrize("falt, farligt", [
    ("kundnamn", "Kim\r\nBcc: attacker@ond.example"),
    ("kundnamn", "Kim\nX-Injicerad: ja"),
    # REGNR ÄR NORMALISERAT INNAN DET NÅR HIT (`fordonsuppslag.
    # normalisera_regnr` stryger blanksteg, `\r`/`\n` inräknat), men den
    # garantin ligger hos ANROPAREN. Funktionen ska vara säker även om den
    # kallas direkt med ett oskyddat regnr, eftersom `Subject` interpolerar
    # det rakt av.
    ("regnr", "ABC123\r\nBcc: attacker@ond.example"),
])
def test_ETT_FARLIGT_FALT_KAN_INTE_ANDRA_MOTTAGAREN(falt, farligt):
    """§7.1-fynd: `Subject` är det enda riktiga e-posthuvud som interpolerar
    en anropares text (`regnr`). `kundnamn` går bara i brödtexten via
    `EmailMessage.set_content`, som aldrig kan bli ett huvud, men prövas ändå
    här som negativkontroll: samma indata, samma garanti oavsett fält.
    Antingen bygger meddelandet ändå med `To` orört, eller så vägrar
    `EmailMessage` värdet rakt av (Pythons egen policy förbjuder rad-brytande
    tecken i ett huvudvärde) — ingendera utfall kan sätta en annan mottagare
    eller ett extra huvud.
    """
    kwargs = {
        "regnr": "ABC123", "kundnamn": "Kim",
        "kundepost": "kim@exempel.invalid", "datum": "2026-09-25",
        "sparr": "genererat-tal-har-kalla",
        "forsok": [("skäl", "sats")], "tradsokvag": "t-1",
    }
    kwargs[falt] = farligt

    try:
        kropp = gmailutkast.bygg_larmmeddelande(**kwargs)
    except ValueError:
        return  # EmailMessage vägrade värdet. Säkert: inget meddelande byggs.
    brev = _avkodat(kropp)
    assert brev["To"] == gmailutkast.LARMADRESS
    assert brev.get_all("Bcc") is None
    assert brev.get_all("X-Injicerad") is None


def test_LARM_HOPPAR_OVER_en_BESVARAD_trad(katalog):
    larm = LarmSpion()
    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X",
                                 besvarad=True)],
        (SVAR[0], SPARRAT), skapa_larm=larm)

    assert korning.sparrade == 1
    assert korning.larm_skapade == 0
    assert korning.larm_hoppade_over == 1
    assert larm.anrop == []


def test_LARM_HOPPAR_OVER_UTAN_svarsvag(katalog):
    larm = LarmSpion()
    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X")],
        (SVAR[0], SPARRAT), skapa_larm=larm, vagar=[None])

    assert korning.sparrade == 1
    assert korning.larm_skapade == 0
    assert korning.larm_hoppade_over == 1
    assert larm.anrop == []


def test_ETT_MISSLYCKAT_LARM_STOPPAR_INTE_slingan(katalog):
    larm = LarmSpion(fel=RuntimeError("gmail nere"))
    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X")],
        (SVAR[0], SPARRAT), skapa_larm=larm)

    assert korning.sparrade == 1
    assert korning.larm_misslyckade == 1
    assert korning.larm_skapade == 0


def test_UTAN_skapa_larm_SKAPAS_INGET_LARM(katalog):
    """Bakåtkompatibelt: `skapa_larm=None` (förvalet) ger samma tystnad som
    innan skiva 81."""
    korning = _slinga_med_larm(
        katalog, [respond.Arende(text=WEBBFORMULARTEXT, regnr="ABC12X")],
        (SVAR[0], SPARRAT), skapa_larm=None)

    assert korning.sparrade == 1
    assert korning.larm_skapade == 0
    assert korning.larm_hoppade_over == 0
    assert korning.larm_misslyckade == 0


# ------------------------------------------ SKIVA 81: hjälparna

def test_namn_i_lasger_webbformularets_falt():
    assert respond._namn_i(WEBBFORMULARTEXT) == "Kim Andersson"


def test_namn_i_ger_None_utan_faltet():
    assert respond._namn_i("Hej, kan ni bygga om min bil?") is None


def test_tradsokvag_strippar_hakparenteserna_ur_message_id():
    vag = vy.Svarsvag(trad_id="t-9", meddelande_id="<a@b.invalid>",
                      mottagare="kund@exempel.invalid", amne="Fråga")
    sokvag = respond._tradsokvag(vag)

    assert "rfc822msgid:a@b.invalid" in sokvag
    assert "<" not in sokvag and ">" not in sokvag.split("rfc822msgid:")[1].split()[0]
    assert "t-9" in sokvag


@pytest.mark.parametrize("andrat", [
    {"sparr": "talspärren"},
    {"inget_svar": True},
    {"svarsvag": None},
])
def test_lagg_gmailutkast_VAGRAR_posten_sjalv(katalog, andrat):
    """Vägran i funktionen, med `Utkastvagran` och inte med ett krasch som
    råkar ge samma utfall (§7.1)."""
    spion = Spion()
    with pytest.raises(vy.Utkastvagran):
        vy.lagg_gmailutkast(post(**andrat), spion,
                            katalog / "logg" / "omdomen.jsonl")
    assert spion.poster == []


def test_ett_BESVARAT_arende_far_inget_utkast(katalog):
    spion = Spion()
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X",
                                               besvarad=True)],
                      SVAR, spion)

    assert korning.utkast == 1
    assert korning.gmail_besvarade == 1
    assert spion.poster == []
    assert _utfall(katalog) == []


def test_ett_MISSLYCKAT_utkast_stoppar_inte_slingan(katalog):
    class Vaxlar(Spion):
        def __call__(self, p):
            self.poster.append(p)
            if len(self.poster) == 1:
                raise RuntimeError("nere")
            return gmailutkast.UtkastResultat(meddelande_id="m-2",
                                              utkast_id="d-2")

    spion = Vaxlar()
    arenden = [respond.Arende(text="Hej ABC12X", regnr="ABC12X"),
               respond.Arende(text="Hej DEF34Y", regnr="DEF34Y")]
    korning = _slinga(katalog, arenden, (*SVAR, *SVAR), spion)

    assert korning.gmail_misslyckade == 1
    assert korning.gmail_skapade == 1
    assert _utfall(katalog) == [("t-0", "begärt"), ("t-0", "misslyckades"),
                                ("t-1", "begärt"), ("t-1", "skapat")]


def test_en_trad_med_ETT_FORSOK_far_inget_andra_i_slingan(katalog):
    """Knappen och slingan delar logg: ett tryck i går hindrar ett utkast i dag."""
    omdomen = katalog / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(ett_fall(), "t-0", "skapat", "m-0",
                         omdomesfil=omdomen)
    spion = Spion()
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X")],
                      SVAR, spion)

    assert korning.gmail_vagrade == 1
    assert spion.poster == []


def test_TVA_DAGLIGA_KORNINGAR_i_samma_trad_ger_ETT_utkast(katalog):
    """Lucka 84: en tråd där kunden skrivit två dagar i rad kommer med i två
    körningar. Den andra får inget nytt utkast, fast kunden skrivit igen.
    Ärendet är detsamma i båda, eftersom texten är trådens första kundmail."""
    spion = Spion()
    arende = respond.Arende(text="Hej ABC12X", regnr="ABC12X")
    forsta = _slinga(katalog, [arende], SVAR, spion)
    andra = _slinga(katalog, [arende], SVAR, spion)

    assert forsta.gmail_skapade == 1
    assert andra.gmail_skapade == 0
    assert andra.gmail_vagrade == 1
    assert len(spion.poster) == 1
    assert _utfall(katalog) == [("t-0", "begärt"), ("t-0", "skapat")]


def test_utan_funktion_skapas_INGET_utkast(katalog):
    """`--gmailutkast` är ett val. Förvalet rör inte Gmail."""
    korning = respond.Korning(tradar=1)
    respond.kor_alla(
        [respond.Arende(text="Hej ABC12X", regnr="ABC12X")],
        klient=FejkKlient(*SVAR), hamta=hamta_gront, hinkar=HINKAR,
        taxonomi=TAXONOMI, exempel=[], skarp=True, korning=korning, nu=NU,
        loggfil=katalog / "logg" / "beslut.jsonl", skriv=lambda *_: None,
        svarsvagar=[VAG], omdomesfil=katalog / "logg" / "omdomen.jsonl")

    assert korning.gmail_skapade == 0
    assert _utfall(katalog) == []


@pytest.mark.parametrize("stoppa, kallfel, utkast", [(True, 1, 0),
                                                      (False, 2, 0)])
def test_backfillen_STOPPAR_vid_forsta_kallfelet(katalog, stoppa, kallfel,
                                                 utkast):
    def avvisar(_regnr):
        raise ConnectionError("429")

    spion = Spion()
    arenden = [respond.Arende(text="Hej ABC12X", regnr="ABC12X"),
               respond.Arende(text="Hej DEF34Y", regnr="DEF34Y")]
    korning = _slinga(katalog, arenden, (SVAR[0], SVAR[0]), spion,
                      hamta=avvisar, stoppa=stoppa)

    assert korning.kallfel == kallfel
    assert korning.utkast == utkast
    assert spion.poster == []


def test_en_OFULLSTANDIG_svarsvag_vagras_UTAN_logg_och_utan_larm(katalog):
    """§7-granskningen av skiva 69: ett ämneslöst mail gav `begärt`,
    `misslyckades` och en röd körning."""
    spion = Spion()
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X")],
                      SVAR, spion,
                      vagar=[vy.Svarsvag(**{**VAG.__dict__, "amne": ""})])

    assert korning.gmail_vagrade == 1
    assert korning.gmail_misslyckade == 0
    assert spion.poster == []
    assert _utfall(katalog) == []


def test_ett_SKAPAT_utkast_vars_loggrad_faller_redovisas_inte_som_oskapat(
        katalog, monkeypatch):
    """§7-granskningen av skiva 69. Utkastet finns; felet ska säga det."""
    riktig = vy.spara_gmailutkast

    def faller_pa_skapat(fall, trad_id, utfall, *a, **k):
        if utfall == "skapat":
            raise OSError("disken full")
        return riktig(fall, trad_id, utfall, *a, **k)
    monkeypatch.setattr(vy, "spara_gmailutkast", faller_pa_skapat)

    omdomen = katalog / "logg" / "omdomen.jsonl"
    with pytest.raises(vy.Skrivfel, match="m-1 ligger i Gmail"):
        vy.lagg_gmailutkast(post(), Spion(), omdomen)

    fejk = Post(vy.bygg_hanterare(
        [], granskning=[post(svarsvag=vy.Svarsvag(
            **{**VAG.__dict__, "trad_id": "t-annan"}))],
        skapa_utkast=Spion(), omdomesfil=omdomen), "/gmailutkast/0")
    fejk.post()
    assert "ligger i Gmail" in fejk.svar
    assert "skapades inte" not in fejk.svar


def test_CLI_larmar_och_bygger_tjansten_FORE_slingan():
    """§7-granskningen av skiva 69: raderna fälldes inte av något test."""
    kod = vy._kod_utan_prosa((ROT / "scripts" / "respond.py")
                             .read_text(encoding="utf-8"))
    i_kor = kod.split("def _kor")[1]

    assert ("return ( 1 if utkastfel or korning . gmail_misslyckade \n"
            " or korning . larm_misslyckade or tappade else 0 )") in i_kor
    assert "tappade = over_taket if arg . inkorg else 0" in i_kor
    assert i_kor.index("skriv_tjanst ( )") < i_kor.index("kor_alla (")
    fangst = i_kor.split("except BaseException")[1][:200]
    assert "vy . spara_granskningsfall" in fangst
    assert "raise" in fangst


# ------------------------------------ SKIVA 70 DEL B: inaktuellt utkast

SENARE = "2099-01-01T00:00:00+00:00"
TIDIGARE = "2000-01-01T00:00:00+00:00"


def _skapat(katalog, trad_id="t-0", utfall="skapat"):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(ett_fall(), trad_id, utfall, "m-0",
                         omdomesfil=omdomen)
    return omdomen


@pytest.mark.parametrize("trad_id, kundmail, utfall, vantat", [
    ("t-0", SENARE, "skapat", "m-0"),
    ("t-0", TIDIGARE, "skapat", ""),
    ("t-9", SENARE, "skapat", ""),
    ("t-0", SENARE, "begärt", ""),
    ("t-0", "", "skapat", ""),
])
def test_inaktuellt_KRAVER_skapat_utkast_i_TRADEN_fore_kundens_mail(
        katalog, trad_id, kundmail, utfall, vantat):
    omdomen = _skapat(katalog, utfall=utfall)
    assert vy.inaktuellt_gmailutkast(trad_id, kundmail, omdomen) == vantat


@pytest.mark.parametrize("skrivet", ["", "2099-01-01T00:00:00", None])
def test_en_TRASIG_loggrad_faller_inte_flaggan(katalog, skrivet):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    rad = {"omdome": vy.OMDOME_GMAILUTKAST, "trad_id": "t-0",
           "utfall": "skapat", "gmail_id": "m-0"}
    if skrivet is not None:
        rad["skrivet"] = skrivet
    omdomen.parent.mkdir(parents=True, exist_ok=True)
    omdomen.write_text(json.dumps(rad) + "\n", encoding="utf-8")

    assert vy.inaktuellt_gmailutkast("t-0", SENARE, omdomen) == ""


def test_VART_UTKAST_i_traden_ar_inget_kundmail():
    """§7-granskningen av skiva 70: ett utkast bär bara DRAFT och daterade
    ärendet, alltså kunde det flagga sig självt som inaktuellt."""
    fraga = meddelande("Hej, kan ni bygga om min bil?",
                       internal="1757900000000")
    utkast = meddelande("Hej, det kan vi.", internal="1757990000000",
                        huvuden={"From": "info@autostockholm.se"})
    utkast["labelIds"] = ["DRAFT"]

    arende, _ = respond.arende_ur_trad(trad(fraga, utkast), set())

    assert arende.tidsstampel == respond.urval.tidsstampel(fraga)


def test_slingan_FLAGGAR_ett_utkast_kunden_skrivit_efter(katalog):
    _skapat(katalog)
    spion = Spion()
    rader = []
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X",
                                               tidsstampel=SENARE)],
                      SVAR, spion, rader=rader)

    assert korning.granskningsfall[0].inaktuellt_utkast == "m-0"
    assert korning.gmail_inaktuella == 1
    assert spion.poster == []
    assert any("INAKTUELLT" in r for r in rader)


def test_en_flaggad_post_NAR_VYN_aven_utan_svar(katalog):
    _skapat(katalog)
    korning = _slinga(katalog, [respond.Arende(text="Hej, däcken",
                                               tidsstampel=SENARE)],
                      ("boka däckbyte",), Spion())

    assert [p.inget_svar for p in korning.granskningsfall] == [True]
    assert korning.granskningsfall[0].inaktuellt_utkast == "m-0"


def test_en_oflaggad_post_utan_svar_nar_INTE_vyn(katalog):
    """Negativkontroll: skiva 61 gäller för allt annat."""
    korning = _slinga(katalog, [respond.Arende(text="Hej, däcken",
                                               tidsstampel=SENARE)],
                      ("boka däckbyte",), Spion())
    assert korning.granskningsfall == []


def test_en_BESVARAD_trad_flaggas_inte(katalog):
    _skapat(katalog)
    korning = _slinga(katalog, [respond.Arende(text="Hej ABC12X",
                                               regnr="ABC12X",
                                               tidsstampel=SENARE,
                                               besvarad=True)],
                      SVAR, Spion())
    assert korning.granskningsfall[0].inaktuellt_utkast == ""


@pytest.mark.parametrize("andrat", [{}, {"sparr": "talspärren"},
                                    {"inget_svar": True}])
def test_flaggan_SYNS_i_alla_tre_grenarna(andrat):
    sida = vy.rendera_granskning(
        ett_fall(), "Hej!", inaktuellt_utkast="m-0",
        **{k: v for k, v in andrat.items()})
    assert "KUNDEN HAR SKRIVIT IGEN" in sida
    assert "m-0" in sida
    assert "KUNDEN HAR SKRIVIT IGEN" not in vy.rendera_granskning(
        ett_fall(), "Hej!", **andrat)


def test_en_flaggad_post_far_INGEN_knapp():
    spion = Spion()
    fejk = Post(vy.bygg_hanterare(
        [], granskning=[post(inaktuellt_utkast="m-0")], skapa_utkast=spion),
        "/granskning/0")
    fejk.get()
    assert "KUNDEN HAR SKRIVIT IGEN" in fejk.svar
    assert "action='/gmailutkast/0'" not in fejk.svar


def test_flaggan_OVERLEVER_filen(katalog):
    fil = katalog / "data" / "granskningsfall.jsonl"
    vy.spara_granskningsfall([post(inaktuellt_utkast="m-0")], fil)
    assert vy.las_granskningsfall(fil)[0].inaktuellt_utkast == "m-0"


# ------------------------------------ SKIVA 75: borttaget utkast


def _rad(katalog, utfall, trad_id="t-0", gmail_id="m-0"):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(ett_fall(), trad_id, utfall, gmail_id,
                         omdomesfil=omdomen)
    return omdomen


@pytest.mark.parametrize("utfall, spärrad", [
    (["begärt", "skapat"], True),
    (["begärt", "skapat", "borttaget"], False),
    (["begärt", "skapat", "borttaget", "begärt"], True),
    (["begärt", "misslyckades"], True),
])
def test_TRADENS_SENASTE_RAD_avgor_sparren(katalog, utfall, spärrad):
    for u in utfall:
        omdomen = _rad(katalog, u)
    assert vy.gmailutkast_finns("t-0", omdomen) is spärrad


def test_utkast_id_for_trad_las_senaste_SKAPAT_raden(katalog):
    """UPPDRAG 2026-09-25 DEL 1. Samma skanningsform som `gmailutkast_finns`."""
    omdomen = katalog / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(ett_fall(), "t-0", "begärt", omdomesfil=omdomen)
    vy.spara_gmailutkast(ett_fall(), "t-0", "skapat", "m-0", "d-0",
                         omdomesfil=omdomen)
    assert vy.utkast_id_for_trad("t-0", omdomen) == "d-0"


def test_utkast_id_for_trad_tom_strang_utan_skapad_rad(katalog):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    assert vy.utkast_id_for_trad("t-0", omdomen) == ""
    vy.spara_gmailutkast(ett_fall(), "t-0", "begärt", omdomesfil=omdomen)
    assert vy.utkast_id_for_trad("t-0", omdomen) == ""


def test_utkast_id_for_trad_tom_strang_efter_BORTTAGET(katalog):
    omdomen = katalog / "logg" / "omdomen.jsonl"
    vy.spara_gmailutkast(ett_fall(), "t-0", "skapat", "m-0", "d-0",
                         omdomesfil=omdomen)
    vy.spara_gmailutkast(ett_fall(), "t-0", "borttaget", omdomesfil=omdomen)
    assert vy.utkast_id_for_trad("t-0", omdomen) == ""


def test_ett_BORTTAGET_utkast_flaggas_inte_som_inaktuellt(katalog):
    _rad(katalog, "skapat")
    omdomen = _rad(katalog, "borttaget")
    assert vy.inaktuellt_gmailutkast("t-0", SENARE, omdomen) == ""


def _borttaget_skript():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "utkast_borttaget", ROT / "scripts" / "utkast-borttaget.py")
    modul = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modul)
    return modul


def _gmail(meddelanden):
    from src import inkorg
    from tests import fejk
    return inkorg.Lastjanst(fejk.FejkGmail(
        sidor={None: {}}, tradar={"t-0": {"id": "t-0",
                                          "messages": meddelanden}}))


@pytest.mark.parametrize("meddelanden, vantat", [
    ([{"id": "k-1", "labelIds": ["INBOX"]}], "markerat borttaget"),
    ([{"id": "m-0", "labelIds": ["DRAFT"]}], "VÄGRAT: utkastet finns kvar"),
    ([{"id": "m-9", "labelIds": ["DRAFT"]}], "VÄGRAT: tråden bär ett annat"),
    # §7-granskningen av skiva 75.
    ([], "VÄGRAT: Gmail gav inga"),
    ([{"id": "k-1", "labelIds": ["INBOX"]},
      {"id": "s-1", "labelIds": ["SENT"]}], "VÄGRAT: tråden bär ett eget"),
])
def test_skriptet_MARKERAR_bara_nar_gmail_bekraftar(katalog, meddelanden,
                                                    vantat):
    omdomen = _rad(katalog, "skapat")
    utfall = _borttaget_skript().markera("m-0", _gmail(meddelanden), omdomen)

    assert utfall.startswith(vantat)
    assert vy.gmailutkast_finns("t-0", omdomen) is (
        not utfall.startswith("markerat"))


def test_skriptet_VAGRAR_ett_okant_id(katalog):
    omdomen = _rad(katalog, "skapat")
    utfall = _borttaget_skript().markera("m-okand", _gmail([]), omdomen)
    assert utfall.startswith("VÄGRAT: inget skapat")
    assert vy.gmailutkast_finns("t-0", omdomen)


def test_skriptet_VAGRAR_ett_BEGART_utan_SKAPAT(katalog):
    """§7-granskningen av skiva 75. Tomt id matchar `begärt`-raden."""
    omdomen = _rad(katalog, "begärt", gmail_id="")
    utfall = _borttaget_skript().markera(
        "", _gmail([{"id": "k-1", "labelIds": ["INBOX"]}]), omdomen)
    assert utfall.startswith("VÄGRAT: inget skapat")
    assert vy.gmailutkast_finns("t-0", omdomen)


def test_skriptet_VAGRAR_en_redan_markerad_trad(katalog):
    _rad(katalog, "skapat")
    omdomen = _rad(katalog, "borttaget")

    class Rakna:
        anrop = 0

        def users(self):
            Rakna.anrop += 1
            raise AssertionError("Gmail ska inte nås")

    utfall = _borttaget_skript().markera("m-0", Rakna(), omdomen)
    assert utfall.startswith("VÄGRAT: tråden är redan markerad")


def test_BORTTAGET_skrivs_BARA_av_skriptet_eller_regnrfiltret():
    """§7-granskningen av skiva 75, utökad UPPDRAG 2026-09-25 DEL 1.

    `scripts/utkast-borttaget.py` skriver BORTTAGET efter att en människa
    bekräftat via läsvägen att utkastet är borta ur Gmail. `scripts/respond.py`
    skriver den sedan DEL 1 av samma skäl, fast bekräftat av ett LYCKAT
    `drafts().delete`-anrop i stället för en människas ögon: se
    `_ta_bort_aldre_utkast`. Ingen TREDJE fil får skriva den utan att
    motsvarande bekräftelse finns och den här listan utökas medvetet.
    """
    import ast

    TILLATNA_SKRIVARE = frozenset({"utkast-borttaget.py", "respond.py"})

    def bar_borttaget(nod) -> bool:
        return any(
            (isinstance(n, ast.Constant) and n.value == vy.BORTTAGET)
            or (isinstance(n, ast.Name) and n.id == "BORTTAGET")
            or (isinstance(n, ast.Attribute) and n.attr == "BORTTAGET")
            for n in ast.walk(nod))

    anrop = 0
    for fil in list((ROT / "src").glob("*.py")) + list(
            (ROT / "scripts").glob("*.py")):
        for nod in ast.walk(ast.parse(fil.read_text(encoding="utf-8"))):
            if not isinstance(nod, ast.Call):
                continue
            namn = getattr(nod.func, "attr", getattr(nod.func, "id", ""))
            if namn != "spara_gmailutkast":
                continue
            anrop += 1
            if fil.name not in TILLATNA_SKRIVARE:
                assert not bar_borttaget(nod), f"{fil.name}:{nod.lineno}"
    assert anrop >= 5, "genomgången hittar inga anrop"


def test_TAKET_raknar_det_som_faller_och_tar_resten(tmp_path, monkeypatch,
                                                    capsys):
    """LUCKA 86, skiva 70. Ärenden över `--antal` körs inte, och antalet
    skrivs ut i stället för att tystna."""
    # Tre ärenden och, efter taket, ett maskinmail. Maskinmailet är sållat och
    # inget tappat ärende, och trådräkningen tar inte med de tappade.
    maskin = trad(meddelande("Veckans erbjudanden", huvuden={
        "List-Unsubscribe": "<mailto:av@exempel.invalid>"}), trad_id="tm")
    fil = tmp_path / "tradar.jsonl"
    fil.write_text("".join(
        json.dumps(trad(meddelande(f"Hej, fråga nummer {i}"),
                        trad_id=f"t{i}")) + "\n" for i in range(3))
        + json.dumps(maskin) + "\n",
        encoding="utf-8")
    fick = []
    monkeypatch.setattr(respond, "kor_alla",
                        lambda arenden, **kw: fick.extend(arenden))
    monkeypatch.setattr(respond, "bygg_kalla", lambda paus_s: (None, True))
    monkeypatch.setattr(respond.kategorisera, "bygg_klient", lambda: None)
    # Stubbarna skriver ingenting. Sökvägarna ligger under roten bara för att
    # utskriften räknar dem relativt den.
    monkeypatch.setattr(respond.vy, "spara_granskningsfall",
                        lambda fall: respond.ROT / "data" / "stubb.jsonl")

    respond.main(["--tradar", str(fil), "--antal", "1"])

    ut = capsys.readouterr()
    assert [a.text for a in fick] == ["Hej, fråga nummer 0"]
    assert "TAKET NÅTT: 2 ärenden" in ut.out
    assert "trådar lästa            2" in ut.out
    assert "sållade före kedjan     1" in ut.out
    assert "TAKET NÅTT" in ut.err


def test_CLI_tar_ETT_nu_FORE_hamtningen():
    """§7-granskningen av lucka 84: fönstret räknades efter hämtningen, vars
    längd varierar, och då möttes inte två dagars fönster."""
    kod = vy._kod_utan_prosa((ROT / "scripts" / "respond.py")
                             .read_text(encoding="utf-8"))
    i_kor = kod.split("def _kor")[1]
    i_kallan = kod.split("def _kallan")[1].split("def _kor")[0]

    assert i_kor.index("nu = datetime . now") < i_kor.index("_kallan ( arg , nu )")
    assert "dagens_tradar ( tjanst , utfil = arg . skord , nu = nu )" in i_kallan
    assert "nu = nu ," in i_kor
    assert i_kor.count("datetime . now") == 1


# ------------------------------------------ SKIVA 81: larmutkastet


def test_larmmeddelandet_gar_ALLTID_till_LARMADRESS():
    """DEN STRUKTURELLA GARANTIN Lars bad om. Varje textargument sätts till
    något som SER UT som ett försök att styra mottagaren, och `To`-huvudet
    ska ändå bli exakt `LARMADRESS`, alltid."""
    kropp = gmailutkast.bygg_larmmeddelande(
        regnr="ABC123",
        kundnamn="Attack <attack@ond.example>",
        kundepost="kund@ond.example",
        datum="2026-09-25",
        sparr="genererat-tal-har-kalla",
        forsok=[("skäl", "sats")],
        tradsokvag="rfc822msgid:x@y",
    )
    brev = _avkodat(kropp)

    assert brev["To"] == gmailutkast.LARMADRESS == "info@autostockholm.se"


def test_larmmeddelandet_har_INGEN_threadId():
    """Skillnaden mot `bygg_meddelande`: inget `threadId` sätts alls, alltså
    kan `skapa_larmutkast` aldrig landa i kundens (eller någon annan) tråd."""
    kropp = gmailutkast.bygg_larmmeddelande(
        regnr="ABC123", kundnamn="Kim", kundepost="kim@exempel.invalid",
        datum="2026-09-25", sparr="genererat-tal-har-kalla",
        forsok=[("skäl", "sats")], tradsokvag="t-1")

    assert "threadId" not in kropp["message"]


def test_larmamnet_borjar_med_MANUELLT_SVAR_KRAVS_och_bar_regnr():
    kropp = gmailutkast.bygg_larmmeddelande(
        regnr="XPU944", kundnamn="Kim", kundepost="kim@exempel.invalid",
        datum="2026-09-25", sparr="genererat-tal-har-kalla",
        forsok=[("skäl", "sats")], tradsokvag="t-1")
    brev = _avkodat(kropp)

    assert brev["Subject"].startswith("MANUELLT SVAR KRÄVS")
    assert "XPU944" in brev["Subject"]


def test_larmkroppen_bar_allt_LARS_BAD_OM():
    """Namn, e-post, datum, VARJE försöks skäl och en sökväg till tråden."""
    kropp = gmailutkast.bygg_larmmeddelande(
        regnr="XPU944", kundnamn="Kim Andersson",
        kundepost="kim@exempel.invalid", datum="2026-09-23T18:34:15+00:00",
        sparr="genererat-tal-har-kalla",
        forsok=[("skäl ett", "sats ett"), ("skäl två", "sats två")],
        tradsokvag="Sök i Gmail: rfc822msgid:abc@x  (tråd-id t-9)")
    kropp_text = _avkodat(kropp).get_content()

    assert "Kim Andersson" in kropp_text
    assert "kim@exempel.invalid" in kropp_text
    assert "2026-09-23T18:34:15+00:00" in kropp_text
    assert "genererat-tal-har-kalla" in kropp_text
    assert "skäl ett" in kropp_text and "sats ett" in kropp_text
    assert "skäl två" in kropp_text and "sats två" in kropp_text
    assert "rfc822msgid:abc@x" in kropp_text
    assert "XPU944" in kropp_text


def test_skapa_larmutkast_anvander_BARA_drafts_create():
    ra = FejkRa(tradsvar=lambda kw: "ny-fristaende-trad")
    resultat = gmailutkast.skapa_larmutkast(
        gmailutkast.Utkastjanst(ra), regnr="ABC123", kundnamn="Kim",
        kundepost="kim@exempel.invalid", datum="2026-09-25",
        sparr="genererat-tal-har-kalla",
        forsok=[("skäl", "sats")], tradsokvag="t-1")

    assert [namn for namn, _ in ra.logg] == ["create"]
    assert resultat.meddelande_id == "m-1"
    assert resultat.utkast_id == "r-1"


def test_larmutkastskapare_ger_en_ANROPBAR_funktion():
    ra = FejkRa(tradsvar=lambda kw: "ny-fristaende-trad")
    larma = gmailutkast.larmutkastskapare(tjanst=gmailutkast.Utkastjanst(ra))

    resultat = larma(regnr="ABC123", kundnamn="Kim",
                     kundepost="kim@exempel.invalid", datum="2026-09-25",
                     sparr="genererat-tal-har-kalla",
                     forsok=[("skäl", "sats")], tradsokvag="t-1")

    assert resultat.meddelande_id == "m-1"
    assert [namn for namn, _ in ra.logg] == ["create"]


def test_CLI_lamnar_funktionen_och_stoppet_VIDARE():
    """Utan raderna i `_kor` hade flaggorna varit tysta."""
    kod = vy._kod_utan_prosa((ROT / "scripts" / "respond.py")
                             .read_text(encoding="utf-8"))
    i_kor = kod.split("def _kor")[1]

    assert "skapa_utkast = skapa_utkast" in i_kor
    assert "stoppa_vid_kallfel = arg . stoppa_vid_kallfel" in i_kor
    assert "bygg_kalla ( arg . paus_s )" in i_kor
