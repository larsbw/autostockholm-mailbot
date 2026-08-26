#!/usr/bin/env bash
#
# sparr-prova.sh — vakuöstprövning enligt CLAUDE.md §7.1.
#
# Fäller en eller flera rader i en fil, kör testsviten, och återställer filen
# till dess FAKTISKA utgångsläge. Aldrig till HEAD: säkerhetskopian tas av
# filen precis som den ligger, till en temporärfil UTANFÖR repot, och
# återställningen sker i en trap som löper även vid fel eller avbrott. Därför
# är skriptet säkert både när filen är ocommittat ren och när den bär
# ocommittat arbete.
#
# Användning:
#   scripts/sparr-prova.sh --fil <sökväg> --radera <N> [--radera <M> ...]
#   scripts/sparr-prova.sh --fil <sökväg> --ersatt <N=TEXT> [...]
#   ... [-- <argument till pytest>]
#
# --radera raderar raden. --ersatt skriver om den, för de fall där raden inte
# går att radera utan att sviten slutar köra. Flaggorna får blandas och
# upprepas, så att samtliga lager i ett lagrat försvar kan fällas i samma
# körning.
#
# Exitkod:
#   0  RÖD    sviten föll av fällningen. Testet vaktar något.
#   1  GRÖN   sviten passerade. Inkonklusivt eller vakuöst.
#   3  FEL    sviten kunde inte köras. Prövningen genomfördes inte.
#   2  STOPP  återställningen kunde inte kvitteras.

set -euo pipefail

ROT="$(git rev-parse --show-toplevel)"
FIL=""
MUTATIONER=()
PYTEST_ARG=()

while [ "$#" -gt 0 ]; do
    case "$1" in
        --fil)
            FIL="$2"
            shift 2
            ;;
        --radera)
            MUTATIONER+=("--radera" "$2")
            shift 2
            ;;
        --ersatt)
            MUTATIONER+=("--ersatt" "$2")
            shift 2
            ;;
        --)
            shift
            while [ "$#" -gt 0 ]; do
                PYTEST_ARG+=("$1")
                shift
            done
            ;;
        *)
            echo "sparr-prova: okänd flagga $1" >&2
            exit 2
            ;;
    esac
done

if [ -z "$FIL" ]; then
    echo "sparr-prova: --fil krävs" >&2
    exit 2
fi

if [ ! -f "$FIL" ]; then
    echo "sparr-prova: hittar inte $FIL" >&2
    exit 2
fi

if [ "${#MUTATIONER[@]}" -eq 0 ]; then
    echo "sparr-prova: ingen fällning angiven, ge --radera eller --ersatt" >&2
    exit 2
fi

# Säkerhetskopian läggs utanför repot så att den aldrig kan committas,
# städas bort av en git clean, eller plockas upp av testsviten.
KOPIA="$(mktemp -t sparr-prova)"
SHA_FORE="$(shasum -a 256 "$FIL" | awk '{print $1}')"
DIFF_FORE="$(mktemp -t sparr-prova-diff)"
git -C "$ROT" diff -- "$FIL" > "$DIFF_FORE" || true
cp "$FIL" "$KOPIA"

# En otrackad fil har alltid tom git diff. Då är diff-kvittensen sann utan att
# bevisa något, och läsaren ska veta att det bara är sha256 som bär bevis.
if git -C "$ROT" ls-files --error-unmatch "$FIL" > /dev/null 2>&1; then
    SPARAD="ja"
else
    SPARAD="nej"
    echo "OBS: $FIL är otrackad i git. Dess git diff är tom oavsett, så"
    echo "     diff-kvittensen nedan bär inget bevis. Bara sha256 gör det."
    echo ""
fi

aterstall() {
    UTFALL="$?"
    cp "$KOPIA" "$FIL"
    SHA_EFTER="$(shasum -a 256 "$FIL" | awk '{print $1}')"
    DIFF_EFTER="$(mktemp -t sparr-prova-diff)"
    git -C "$ROT" diff -- "$FIL" > "$DIFF_EFTER" || true

    echo ""
    echo "--- ÅTERSTÄLLNING ---"
    if [ "$SHA_FORE" = "$SHA_EFTER" ]; then
        echo "filens sha256 identisk med utgångsläget: OK"
    else
        echo "STOPP: filens sha256 skiljer sig från utgångsläget."
        echo "  före:  $SHA_FORE"
        echo "  efter: $SHA_EFTER"
        echo "  kopia finns kvar: $KOPIA"
        rm -f "$DIFF_FORE" "$DIFF_EFTER"
        exit 2
    fi

    if cmp -s "$DIFF_FORE" "$DIFF_EFTER"; then
        if [ "$SPARAD" = "ja" ]; then
            echo "git diff identisk med utgångsdiffen: OK"
        else
            echo "git diff identisk med utgångsdiffen: OK (otrackad fil, utan bevisvärde)"
        fi
    else
        echo "STOPP: git diff skiljer sig från utgångsdiffen."
        echo "  kopia finns kvar: $KOPIA"
        rm -f "$DIFF_FORE" "$DIFF_EFTER"
        exit 2
    fi

    rm -f "$KOPIA" "$DIFF_FORE" "$DIFF_EFTER"
    exit "$UTFALL"
}
# Bara EXIT: bash kör EXIT-trapen även vid SIGINT och SIGTERM, och en extra
# signal-trap skulle köra återställningen två gånger.
trap aterstall EXIT

echo "--- FÄLLNING i $FIL ---"
"$ROT/.venv/bin/python" "$ROT/scripts/mutera.py" --fil "$FIL" "${MUTATIONER[@]}"

echo ""
echo "--- SVIT ---"
set +e
"$ROT/.venv/bin/python" -m pytest ${PYTEST_ARG[@]+"${PYTEST_ARG[@]}"}
PYTEST_UTFALL="$?"
set -e

echo ""
echo "--- VERDIKT ---"
case "$PYTEST_UTFALL" in
    0)
        echo "GRÖN: sviten passerade trots fällningen."
        echo "Inkonklusivt om spärren har fler lager, vakuöst om den inte har det."
        SLUT=1
        ;;
    1)
        echo "RÖD: sviten föll av fällningen."
        SLUT=0
        ;;
    *)
        echo "FEL: sviten kunde inte köras (pytest exit $PYTEST_UTFALL)."
        echo "Prövningen genomfördes inte. Godkänn inte."
        SLUT=3
        ;;
esac

exit "$SLUT"
