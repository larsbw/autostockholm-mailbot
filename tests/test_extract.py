"""Tester för src/urval.py och src/extract.py.

All indata är påhittad. Inga riktiga adresser, namn eller regnummer.
"""

from __future__ import annotations

import base64
import json

from src import extract, urval

KUND = "kund@exempel.se"
BREVLADA = urval.BREVLADA

SVARSHUVUDEN = ["Content-Type", "Date", "From", "In-Reply-To", "MIME-Version",
                "Message-ID", "References", "Subject", "To"]
LEVERANS = ["Received", "Return-Path", "Delivered-To", "Received-SPF"]

LANG_KUND = "Hej, vad kostar en besiktning av min A-traktor?"
LANG_SVAR = "Hej och tack för din fråga, vi återkommer med en tid nästa vecka."


def koda(text: str) -> str:
    return base64.urlsafe_b64encode(text.encode("utf-8")).decode("ascii")


def meddelande(*, etiketter, huvuden, text="", mottagare=KUND, amne="",
               avsandare=None, tid="1700000000000", mimetyp="text/plain",
               nastlad=False):
    varden = {"to": mottagare, "subject": amne,
              "from": avsandare or f"Namn <{KUND}>"}
    nyttolast = {
        "mimeType": mimetyp,
        "headers": [{"name": n, "value": varden.get(n.lower(), "")}
                    for n in huvuden],
    }
    kropp = {"mimeType": mimetyp, "body": {"data": koda(text)}}
    if nastlad:
        nyttolast["mimeType"] = "multipart/alternative"
        nyttolast["parts"] = [kropp]
        nyttolast["body"] = {}
    else:
        nyttolast["body"] = {"data": koda(text)}
    return {"labelIds": list(etiketter), "internalDate": tid,
            "payload": nyttolast}


def kundmail(text=LANG_KUND, **kw):
    return meddelande(etiketter=["INBOX"], huvuden=SVARSHUVUDEN + LEVERANS,
                      text=text, **kw)


def svar(text=LANG_SVAR, **kw):
    return meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN, text=text, **kw)


# --- textutvinning -----------------------------------------------------------


def test_brodtext_hittar_texten_utan_parts():
    """Beslutslogg #6: enkla meddelanden har brödtexten direkt i payload.body."""
    assert urval.brodtext(kundmail(text="Hej hej")) == "Hej hej"


def test_brodtext_hittar_texten_i_nastlad_del():
    assert urval.brodtext(kundmail(text="Hej hej", nastlad=True)) == "Hej hej"


def test_brodtext_faller_tillbaka_pa_html():
    """Beslutslogg #6: text/plain finns inte alltid."""
    html = "<p>Hej<br>d&aring;</p>"

    assert urval.brodtext(kundmail(text=html, mimetyp="text/html")) == "Hej\ndå"


def test_brodtext_utan_data_ger_tom_strang():
    tomt = {"labelIds": ["INBOX"], "payload": {"mimeType": "text/plain",
                                               "body": {}, "headers": []}}

    assert urval.brodtext(tomt) == ""


def test_citerad_historik_klipps_bort():
    """Utan det bär varje svar hela trådens tidigare text, och en mall byggd på
    det skulle återge kundens egna ord tillbaka till kunden."""
    text = "Vårt svar.\n\nDen 3 mars skrev Namn:\n> tidigare text\n> mer text"

    assert urval.stada(text) == "Vårt svar."


def test_citatmarkor_med_vinkel_klipps_bort():
    assert urval.stada("Svar.\n> citat") == "Svar."


def test_ursprungligt_meddelande_klipps_bort():
    text = "Svar.\n\n-----Ursprungligt meddelande-----\nFrån: Namn"

    assert urval.stada(text) == "Svar."


def test_text_utan_citat_lamnas_orord():
    assert urval.stada("Rad ett\nRad två") == "Rad ett\nRad två"


# --- hashning ----------------------------------------------------------------


def test_adressen_hashas_och_syns_aldrig():
    hash_ = urval.hasha(KUND)

    assert KUND not in hash_
    assert "exempel" not in hash_
    assert len(hash_) == 64


def test_hashen_ar_stabil_och_skiftlagesokanslig():
    assert urval.hasha(KUND) == urval.hasha(" KUND@Exempel.SE ")


def test_olika_adresser_ger_olika_hash():
    assert urval.hasha(KUND) != urval.hasha("annan@exempel.se")


def test_kundadressen_tas_ur_reply_to_for_formularnotis():
    """Notisens From är brevlådan själv; kunden står i Reply-To."""
    notis = meddelande(
        etiketter=["SENT"],
        huvuden=SVARSHUVUDEN + LEVERANS + ["Reply-To"],
        avsandare=f"Auto Stockholm <{BREVLADA}>",
    )
    notis["payload"]["headers"].append(
        {"name": "Reply-To", "value": f"Namn <{KUND}>"}
    )

    assert urval.kundadress(notis) == KUND


# --- parning -----------------------------------------------------------------


def test_par_byggs_av_kundmail_och_foljande_svar():
    trad = {"messages": [kundmail(), svar()]}

    par = extract.par_ur_trad(trad)

    assert len(par) == 1
    assert par[0]["inkommande_text"] == LANG_KUND
    assert par[0]["utgaende_text"] == LANG_SVAR
    assert par[0]["avsandare_hash"] == urval.hasha(KUND)
    assert par[0]["tidsstampel"].startswith("2023-")


def test_svar_utan_foregaende_kundmail_ger_inget_par():
    """Ett svar kan inte besvara text som inte fanns när det skrevs."""
    trad = {"messages": [svar(), kundmail()]}

    assert extract.par_ur_trad(trad) == []


def test_svaret_paras_med_narmast_foregaende_kundmail():
    trad = {"messages": [
        kundmail(text="Första frågan om besiktning"),
        kundmail(text="Andra frågan om besiktning"),
        svar(),
    ]}

    par = extract.par_ur_trad(trad)

    assert len(par) == 1
    assert par[0]["inkommande_text"] == "Andra frågan om besiktning"


def test_flera_svar_i_en_trad_ger_flera_par():
    trad = {"messages": [
        kundmail(text="Fråga ett om besiktning"),
        svar(text="Svar ett till dig om besiktningen"),
        kundmail(text="Fråga två om besiktning"),
        svar(text="Svar två till dig om besiktningen"),
    ]}

    assert len(extract.par_ur_trad(trad)) == 2


def test_vidarebefordran_blir_inget_par():
    trad = {"messages": [kundmail(), svar(amne="Fwd: Offert")]}

    assert extract.par_ur_trad(trad) == []


def test_for_kort_svar_blir_inget_par():
    """En kvittens är inte ett svar att bygga mall ur."""
    trad = {"messages": [kundmail(), svar(text="Tack!")]}

    assert extract.par_ur_trad(trad) == []


def test_for_kort_kundmail_blir_inget_par():
    trad = {"messages": [kundmail(text="Hej"), svar()]}

    assert extract.par_ur_trad(trad) == []


def test_formularnotis_duger_som_kundsida():
    """Beslutslogg #8: notisen bär kundens ärende och har SENT."""
    notis = meddelande(etiketter=["SENT"], huvuden=SVARSHUVUDEN + LEVERANS,
                       text=LANG_KUND)
    trad = {"messages": [notis, svar()]}

    par = extract.par_ur_trad(trad)

    assert len(par) == 1
    assert par[0]["inkommande_text"] == LANG_KUND


def test_tom_trad_ger_inga_par():
    assert extract.par_ur_trad({"messages": []}) == []
    assert extract.par_ur_trad({}) == []


# --- filskrivning ------------------------------------------------------------


def test_extrahera_skriver_en_post_per_rad(tmp_path):
    utfil = tmp_path / "par.jsonl"
    trad = {"messages": [kundmail(), svar()]}

    rakning = extract.extrahera([trad, trad], utfil)

    rader = utfil.read_text(encoding="utf-8").splitlines()
    assert len(rader) == 2
    assert json.loads(rader[0])["avsandare_hash"] == urval.hasha(KUND)
    assert rakning == {"tradar_lasta": 2, "tradar_maskin": 0,
                       "tradar_med_par": 2, "par_totalt": 2}


def test_maskintrad_ger_inga_par(tmp_path):
    """Ett nyhetsbrev som vi råkat svara på är inget kundärende, och en mall
    byggd ur det svaret vore ett svar på ett utskick."""
    utfil = tmp_path / "par.jsonl"
    nyhetsbrev = kundmail()
    nyhetsbrev["payload"]["headers"].append(
        {"name": "List-Unsubscribe", "value": "<x>"}
    )
    trad = {"messages": [nyhetsbrev, svar()]}

    rakning = extract.extrahera([trad], utfil)

    assert rakning["tradar_maskin"] == 1
    assert rakning["par_totalt"] == 0
    assert utfil.read_text(encoding="utf-8") == ""


def test_ingen_adress_i_utfilen(tmp_path):
    """§6. Filen bär brödtext, som är underlaget, men aldrig en adress i
    klartext på ett fält vi själva skriver."""
    utfil = tmp_path / "par.jsonl"

    extract.extrahera([{"messages": [kundmail(), svar()]}], utfil)

    text = utfil.read_text(encoding="utf-8")
    post = json.loads(text.splitlines()[0])
    assert KUND not in post["avsandare_hash"]
    assert set(post) == {"inkommande_text", "utgaende_text", "tidsstampel",
                         "avsandare_hash"}


def test_avbruten_extraktion_lamnar_utfilen_orord(tmp_path):
    utfil = tmp_path / "par.jsonl"
    utfil.write_text('{"id": "tidigare"}\n', encoding="utf-8")

    def trasig():
        yield {"messages": [kundmail(), svar()]}
        raise RuntimeError("avbrott")

    try:
        extract.extrahera(trasig(), utfil)
    except RuntimeError:
        pass

    assert utfil.read_text(encoding="utf-8") == '{"id": "tidigare"}\n'
