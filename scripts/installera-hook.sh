#!/usr/bin/env bash
#
# Installerar persondatakontrollen som pre-commit-hook.
#
# Hooken bor i .git/hooks/, som INTE följer med i en klon. Skriptet är därför
# committat och måste köras en gång per arbetskopia. Att hooken inte kan
# committas är också skälet till att kontrollen går att köra för hand:
#
#     .venv/bin/python scripts/persondatakontroll.py --alla
#
# En hook går att kringgå med `git commit --no-verify`. Det är avsiktligt i
# git och går inte att stänga av. Spärren är alltså ett skydd mot MISSTAG,
# inte mot en beslutsam användare, och den ska läsas så.

set -euo pipefail

ROT="$(git rev-parse --show-toplevel)"
HOOK="$ROT/.git/hooks/pre-commit"

cat > "$HOOK" <<'HOOKSLUT'
#!/usr/bin/env bash
set -euo pipefail
ROT="$(git rev-parse --show-toplevel)"
exec "$ROT/.venv/bin/python" "$ROT/scripts/persondatakontroll.py"
HOOKSLUT

chmod +x "$HOOK"

echo "pre-commit-hook installerad: $HOOK"
echo "Kör en kontroll för hand med:"
echo "  .venv/bin/python scripts/persondatakontroll.py --alla"
