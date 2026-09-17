#!/bin/sh
# STARTKOMMANDOT PÅ RAILWAY. Bara schemat, i förgrunden.
#
# **SKIVA 72, LARS BESLUT: VYN ÄR INTE LÄNGRE EN DEL AV FLÖDET.** Den dagliga
# körningen skapar Gmail-utkast själv, och Lars läser och skickar dem i Gmail.
# Här startades förut `scripts/serva.py` i förgrunden och exponerades utåt.
# Den startas inte längre. Koden står kvar för felsökning lokalt:
# `scripts/serva.py --lokalt` eller `scripts/kor-vy.py`.
#
# **SCHEMAT ÄR NU PID 1**, och en känd lucka stängs med det: dör schemat dör
# containern, och Railway startar om den. Förut levde containern vidare på
# vyn medan schemat var dött, `docs/beslutslogg.md` #119.
#
# **VARFÖR INTE RAILWAYS CRON.** Oförändrat skäl, avläst ur docs.railway.com
# 2026-09-15: Railways cron kör en services STARTKOMMANDO på schema, och
# volymen, som bär `logg/omdomen.jsonl` och tokenen, sitter på den här
# servicen. Slingan i `scripts/dagligen.py` sover till nästa körning.

set -eu

echo "[start] $(date -u +%Y-%m-%dT%H:%M:%SZ) startar schemat, ingen vy"

# `exec` gör schemat till pid 1, så att Railways stoppsignal når det direkt.
exec python scripts/dagligen.py
