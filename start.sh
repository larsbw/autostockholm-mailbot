#!/bin/sh
# STARTKOMMANDOT PÅ RAILWAY. Schemat i bakgrunden, vyn i förgrunden.
#
# **VARFÖR BÅDA I SAMMA CONTAINER.** Avläst ur docs.railway.com 2026-09-15:
#
#   "Each service can only have a single volume attached"
#   Railways cron kör en services STARTKOMMANDO på schema.
#   "If you see that a previous execution of your Cron service has a status of
#    Active, the execution is still running and any new executions will not be
#    run."
#
# Den sista raden är den som avgör: en service vars startkommando är en
# webbserver avslutas aldrig, alltså är den permanent Active, alltså kör cron
# ALDRIG. Inte "ibland" och inte "opålitligt" — aldrig.
#
# Vyn läser `data/granskningsfall.jsonl` och den dagliga körningen skriver den,
# alltså måste de dela katalog. Med ett volume per service betyder det samma
# service, och då kan den servicens cron inte användas. Schemat ligger därför i
# containern.
#
# *Här stod att ett volume inte KAN DELAS mellan två services, som en avläsning.
# Det står ingenstans i dokumentationen; det som står är att en service bara kan
# ha ETT volume. Slutsatsen är densamma men premissen var påhittad. Fällt av
# §7-granskningen av skiva 53.*
#
# **VYN KÖR I FÖRGRUNDEN, och det är avsiktligt.** Railway mäter om containern
# lever på förgrundsprocessen. Dör vyn ska containern dö och startas om. Dör
# schemat gör den inte det, och DET ÄR EN KÄND LUCKA: se `docs/beslutslogg.md`
# #119 och DEL C i skivans rapport. En krasch i schemat syns i loggen och
# ingenstans annars.

set -eu

echo "[start] $(date -u +%Y-%m-%dT%H:%M:%SZ) startar schema och vy"

python scripts/dagligen.py &
SCHEMA=$!
echo "[start] schemat kör som pid $SCHEMA"

# `exec` gör vyn till pid 1, så att Railways stoppsignal når den direkt i
# stället för att fastna i det här skalet.
exec python scripts/serva.py
