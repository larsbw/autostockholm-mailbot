# AVBILDEN SOM KÖRS PÅ RAILWAY. `docs/beslutslogg.md` #38, byggd i skiva 53.
#
# **INGENTING SOM BÄR KUNDTEXT ELLER EN HEMLIGHET KOPIERAS IN HÄR.** Vad som
# kommer med styrs av `.dockerignore`, och den filen är §6-gränsen: `data/`,
# `logg/`, `token*.json` och `client_secret.json` står där. Det som ska finnas i
# drift ligger på volymen och läggs dit av Lars, aldrig av en deploy.

FROM python:3.13-slim

# Inget .pyc-skrivande, och obuffrad utdata så att Railways logg visar raderna
# när de skrivs i stället för när bufferten råkar tömmas. Det senare är hela
# skillnaden mellan en körningslogg man kan läsa och en man får i efterhand.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Beroendena först, i ett eget lager: de ändras sällan och kan då cachas medan
# koden ändras ofta.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# **KATALOGERNA PEKAS IN I VOLYMEN.** Railway monterar volymen på en sökväg, och
# den sökvägen är inte repots rot. Utan de här tre variablerna skriver boten i
# containern, och containern töms vid varje deploy (#38).
#
# Monteringspunkten är `/volym`, satt i Railways gränssnitt. Står den någon
# annanstans är det de här tre raderna som ska ändras.
ENV MAILBOT_DATA=/volym/data \
    MAILBOT_LOGG=/volym/logg \
    MAILBOT_HEMLIGHETER=/volym/hemligheter

# Startkommandot: bara schemat, sedan skiva 72. Vyn startas inte. Se
# `start.sh`.
CMD ["./start.sh"]
