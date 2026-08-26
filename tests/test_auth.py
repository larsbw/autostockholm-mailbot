"""Tester för src/auth.py.

Påståendena som säger att något INTE sker (webbläsaren öppnas inte, token.json
skrivs inte över) är de som prövas enligt CLAUDE.md §7.1.
"""

from __future__ import annotations

import json

import pytest
from google.auth.exceptions import RefreshError
from google.oauth2.credentials import Credentials

from src import auth
from tests import fejk

FRAMTID = "2099-01-01T00:00:00Z"
DATID = "2020-01-01T00:00:00Z"


class FlodeSpion:
    """Ersätter InstalledAppFlow. Öppnar ingen webbläsare, men räknar varje
    gång koden hade gjort det."""

    def __init__(self):
        self.anrop = []

    def from_client_secrets_file(self, sokvag, scopes):
        self.anrop.append((str(sokvag), tuple(scopes)))
        return self

    def run_local_server(self, port=0):
        return Credentials.from_authorized_user_info(
            fejk.token_data(auth.SCOPES, expiry=FRAMTID)
        )


@pytest.fixture
def spion(monkeypatch):
    s = FlodeSpion()
    monkeypatch.setattr(auth, "InstalledAppFlow", s)
    return s


@pytest.fixture
def hemlighet(tmp_path):
    sokvag = tmp_path / "client_secret.json"
    sokvag.write_text(json.dumps({"installed": {}}), encoding="utf-8")
    return sokvag


def test_giltig_token_ateranvands_och_filen_skrivs_inte_over(
    tmp_path, spion, hemlighet
):
    token = fejk.skriv_token(tmp_path / "token.json", auth.SCOPES, expiry=FRAMTID)
    fore = token.read_bytes()

    cred = auth.hamta_credentials(
        token_sokvag=token, client_secret=hemlighet, tillat_webblasare=True
    )

    assert cred.valid
    assert token.read_bytes() == fore
    assert spion.anrop == []


def test_utgangen_token_fornyas_utan_webblasare(
    tmp_path, monkeypatch, spion, hemlighet
):
    token = fejk.skriv_token(tmp_path / "token.json", auth.SCOPES, expiry=DATID)
    fore = token.read_bytes()
    fornyade = []

    def fejk_refresh(self, request):
        fornyade.append(request)
        self.token = "fornyat-atkomsttoken"
        self.expiry = None

    monkeypatch.setattr(Credentials, "refresh", fejk_refresh)
    monkeypatch.setattr(auth, "Request", lambda: "fejkad-request")

    cred = auth.hamta_credentials(
        token_sokvag=token, client_secret=hemlighet, tillat_webblasare=True
    )

    assert len(fornyade) == 1
    assert cred.valid
    assert spion.anrop == []
    assert token.read_bytes() != fore
    assert json.loads(token.read_text(encoding="utf-8"))["token"] == (
        "fornyat-atkomsttoken"
    )


def test_token_utan_alla_scopes_behandlas_som_saknad(tmp_path, spion, hemlighet):
    token = fejk.skriv_token(
        tmp_path / "token.json",
        ["https://www.googleapis.com/auth/gmail.send"],
        expiry=FRAMTID,
    )

    with pytest.raises(auth.AuthFel):
        auth.hamta_credentials(
            token_sokvag=token, client_secret=hemlighet, tillat_webblasare=False
        )

    assert spion.anrop == []


def test_ingen_token_och_ingen_webblasare_ger_authfel(tmp_path, spion, hemlighet):
    token = tmp_path / "token.json"

    with pytest.raises(auth.AuthFel):
        auth.hamta_credentials(
            token_sokvag=token, client_secret=hemlighet, tillat_webblasare=False
        )

    assert spion.anrop == []
    assert not token.exists()


def test_trasig_tokenfil_behandlas_som_saknad(tmp_path, spion, hemlighet):
    token = tmp_path / "token.json"
    token.write_text("{inte json", encoding="utf-8")

    with pytest.raises(auth.AuthFel):
        auth.hamta_credentials(
            token_sokvag=token, client_secret=hemlighet, tillat_webblasare=False
        )

    assert spion.anrop == []


def test_refresherror_ger_authfel_nar_webblasare_inte_tillaten(
    tmp_path, monkeypatch, spion, hemlighet
):
    token = fejk.skriv_token(tmp_path / "token.json", auth.SCOPES, expiry=DATID)

    def fejk_refresh(self, request):
        raise RefreshError("token återkallat")

    monkeypatch.setattr(Credentials, "refresh", fejk_refresh)
    monkeypatch.setattr(auth, "Request", lambda: "fejkad-request")

    with pytest.raises(auth.AuthFel):
        auth.hamta_credentials(
            token_sokvag=token, client_secret=hemlighet, tillat_webblasare=False
        )

    assert spion.anrop == []


def test_webblasarflodet_kors_nar_det_tillats_och_inget_annat_gar(
    tmp_path, spion, hemlighet
):
    token = tmp_path / "token.json"

    cred = auth.hamta_credentials(
        token_sokvag=token, client_secret=hemlighet, tillat_webblasare=True
    )

    assert len(spion.anrop) == 1
    assert spion.anrop[0][1] == tuple(auth.SCOPES)
    assert cred.valid
    assert token.exists()


def test_scopelistan_ar_last_till_modify_och_send():
    assert auth.SCOPES == [
        "https://www.googleapis.com/auth/gmail.modify",
        "https://www.googleapis.com/auth/gmail.send",
    ]


def test_status_avslojar_inget_innehall(tmp_path):
    token = fejk.skriv_token(tmp_path / "token.json", auth.SCOPES, expiry=FRAMTID)

    rad = auth._status(token)

    assert "fejk-refresh-token" not in rad
    assert "fejk-atkomsttoken" not in rad
    assert str(token.stat().st_size) in rad
