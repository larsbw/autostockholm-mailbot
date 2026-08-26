"""Fejkad Gmail-tjänst och fejkade OAuth-artefakter för testsviten.

Ingenting här rör en riktig brevlåda. Alla nycklar och hemligheter är uppenbart
påhittade strängar (CLAUDE.md §6).
"""

from __future__ import annotations

import json

import httplib2
from googleapiclient.errors import HttpError


def httpfel(status: int, orsak: str) -> HttpError:
    """Ett HttpError med den statuskod och error.errors[0].reason som Gmail
    returnerar."""
    svar = httplib2.Response({"status": status})
    kropp = json.dumps(
        {"error": {"code": status, "errors": [{"reason": orsak}],
                   "message": orsak}}
    ).encode("utf-8")
    return HttpError(svar, kropp, uri="https://gmail.example/fejk")


def kvotfel() -> HttpError:
    return httpfel(429, "userRateLimitExceeded")


def behorighetsfel() -> HttpError:
    return httpfel(403, "insufficientPermissions")


class _Anrop:
    def __init__(self, producent):
        self._producent = producent

    def execute(self):
        return self._producent()


class _Threads:
    def __init__(self, gmail):
        self._g = gmail

    def list(self, **kw):
        self._g.list_anrop.append(kw)

        def producent():
            if self._g.list_fel:
                raise self._g.list_fel.pop(0)
            return self._g.sidor[kw.get("pageToken")]

        return _Anrop(producent)

    def get(self, **kw):
        self._g.get_anrop.append(kw)

        def producent():
            ko = self._g.get_fel.get(kw["id"])
            if ko:
                raise ko.pop(0)
            return self._g.tradar[kw["id"]]

        return _Anrop(producent)


class _Messages:
    def __init__(self, gmail):
        self._g = gmail

    def get(self, **kw):
        self._g.messages_anrop.append(kw)
        return _Anrop(lambda: self._g.meddelanden[kw["id"]])


class FejkGmail:
    """Räcker precis så långt src/mine.py sträcker sig.

    sidor:    {pageToken -> threads.list-svar}, None som nyckel för första sidan
    tradar:   {trådId -> threads.get-svar}
    list_fel: fel som kastas, ett per threads.list-anrop, innan svaret ges
    get_fel:  {trådId -> [fel, ...]} som kastas före svaret
    """

    def __init__(self, sidor, tradar, *, list_fel=None, get_fel=None,
                 meddelanden=None):
        self.sidor = sidor
        self.tradar = tradar
        self.list_fel = list(list_fel or [])
        self.get_fel = {k: list(v) for k, v in (get_fel or {}).items()}
        self.meddelanden = meddelanden or {}
        self.list_anrop = []
        self.get_anrop = []
        self.messages_anrop = []

    def users(self):
        return self

    def threads(self):
        return _Threads(self)

    def messages(self):
        return _Messages(self)


class Sovlogg:
    """Ersätter time.sleep i testerna och sparar varje begärd fördröjning."""

    def __init__(self):
        self.sovtider = []

    def __call__(self, sekunder):
        self.sovtider.append(sekunder)


class Klocka:
    """Monoton klocka som bara rör sig när Sovlogg sover."""

    def __init__(self, sovlogg):
        self._sovlogg = sovlogg
        self._start = 1000.0

    def __call__(self):
        return self._start + sum(self._sovlogg.sovtider)


TOKEN_URI = "https://oauth2.googleapis.com/token"


def token_data(scopes, *, expiry=None, refresh_token="fejk-refresh-token"):
    data = {
        "token": "fejk-atkomsttoken",
        "refresh_token": refresh_token,
        "token_uri": TOKEN_URI,
        "client_id": "fejk-klient-id",
        "client_secret": "fejk-klienthemlighet",
        "scopes": list(scopes),
    }
    if expiry is not None:
        data["expiry"] = expiry
    return data


def skriv_token(sokvag, scopes, **kw):
    sokvag.write_text(json.dumps(token_data(scopes, **kw)), encoding="utf-8")
    return sokvag
