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
#   scripts/sparr-prova.sh --fil <sökväg> --fixtur-ocommittat --ersatt <N=TEXT>
#   scripts/sparr-prova.sh --fil <sökväg> --sjalvtest
#   ... [-- <argument till pytest>]
#
# --radera raderar raden. --ersatt skriver om den, för de fall där raden inte
# går att radera utan att sviten slutar köra. Flaggorna får blandas och
# upprepas, så att samtliga lager i ett lagrat försvar kan fällas i samma
# körning.
#
# --fixtur-ocommittat skapar själv tillståndet "spårad fil med ocommittat
# arbete" och städar bort det efteråt. Utan det läget går fallet inte att pröva
# utan skrivverktyg, och en granskare som saknar dem måste redovisa det som
# OPRÖVAT. Kräver en spårad och ren .py- eller .sh-fil.
#
# --sjalvtest prövar skriptets egna VÄGRANDEN, som annars bara går att läsa sig
# till. Det konstruerar en smutsig fil, både ostagad och stagad, och visar att
# --fixtur-ocommittat vägrar i båda lägena. Samma skäl som fixturen själv: ett
# verktyg som bara kan granskas genom läsning betygsätter sig självt.
#
# Exitkod:
#   0  RÖD    sviten föll av fällningen. Testet vaktar något.
#   1  GRÖN   sviten passerade. Inkonklusivt eller vakuöst.
#   3  FEL    sviten kunde inte köras. Prövningen genomfördes inte.
#   2  STOPP  återställningen kunde inte kvitteras, eller felaktig användning.
#             För --sjalvtest: 0 om samtliga vägranden höll, annars 2.

set -euo pipefail

ROT="$(git rev-parse --show-toplevel)"
FIL=""
FIXTUR="nej"
FIXTUR_SKAPAD="nej"
SJALVTEST="nej"
KOPIA=""
KOPIA_TAGEN="nej"
KOPIA_REN=""
SHA_FORE=""
DIFF_FORE=""
SPARAD="nej"
MUTATIONER=()
PYTEST_ARG=()

# Raden fixturen lägger in. Måste vara en kommentar i målfilens språk, annars
# slutar sviten köra och prövningen ger FEL i stället för RÖD.
FIXTURMARKOR="SPARR-PROVA FIXTUR: ocommittat arbete, tas bort av skriptet"

while [ "$#" -gt 0 ]; do
    case "$1" in
        --fil)
            FIL="$2"
            shift 2
            ;;
        --fixtur-ocommittat)
            FIXTUR="ja"
            shift
            ;;
        --sjalvtest)
            SJALVTEST="ja"
            shift
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

# --- SJÄLVTEST ---------------------------------------------------------------
# Prövar de två vägranden som annars bara går att läsa sig till. Har sin egen
# trap, eftersom den varken fäller rader eller kör sviten.
if [ "$SJALVTEST" = "ja" ]; then
    if [ "${#MUTATIONER[@]}" -ne 0 ]; then
        echo "sparr-prova: --sjalvtest tar ingen fällning. Ta bort --radera och --ersatt." >&2
        exit 2
    fi
    if [ "$FIXTUR" = "ja" ]; then
        echo "sparr-prova: --sjalvtest sätter fixturen själv. Ta bort --fixtur-ocommittat." >&2
        exit 2
    fi
    case "$FIL" in
        *sparr-prova.sh|*mutera.py)
            echo "sparr-prova: --sjalvtest kan inte köras mot sitt eget verktyg." >&2
            echo "             Skriptet läses medan det körs. Välj en annan fil." >&2
            exit 2
            ;;
    esac
    if ! git -C "$ROT" ls-files --error-unmatch "$FIL" > /dev/null 2>&1; then
        echo "sparr-prova: --sjalvtest kräver en SPÅRAD fil. $FIL är otrackad." >&2
        exit 2
    fi
    if [ -n "$(git -C "$ROT" diff HEAD -- "$FIL")" ]; then
        echo "sparr-prova: --sjalvtest kräver en REN fil. $FIL bär redan arbete." >&2
        exit 2
    fi
    case "$FIL" in
        *.py|*.sh)
            ;;
        *)
            echo "sparr-prova: --sjalvtest kan bara kommentera .py och .sh. Fick $FIL." >&2
            exit 2
            ;;
    esac

    SJT_KOPIA="$(mktemp -t sparr-prova-sjt)"
    cp "$FIL" "$SJT_KOPIA"

    sjalvtest_stad() {
        SJT_UTFALL="$?"
        git -C "$ROT" reset --quiet -- "$FIL" > /dev/null 2>&1 || true
        cp "$SJT_KOPIA" "$FIL"
        rm -f "$SJT_KOPIA"
        echo ""
        echo "--- SJÄLVTESTETS STÄDNING ---"
        if [ -n "$(git -C "$ROT" diff HEAD -- "$FIL")" ]; then
            echo "STOPP: $FIL är inte ren mot HEAD efter självtestet."
            exit 2
        fi
        echo "$FIL är ren mot HEAD igen: OK"
        exit "$SJT_UTFALL"
    }
    trap sjalvtest_stad EXIT

    SJT_FEL=0
    SJT_UTDATA="$(mktemp -t sparr-prova-sjt-ut)"

    # Exit 2 delas av flera lägen: okänd flagga, saknad fil, otrackad fil, fel
    # filändelse, redan smutsig fil. Koden ensam bevisar därför inte att RÄTT
    # kontroll fällde. Assertionen går på meddelandet, och utdatan skrivs ut så
    # att beviset går att läsa i efterhand i stället för att kastas bort.
    SJT_VANTAT="bär redan ocommittat arbete"

    echo "--- SJÄLVTEST: vägran mot fil med OSTAGAT arbete ---"
    printf '\n# %s\n' "SJALVTEST: ostagat arbete" >> "$FIL"
    set +e
    "$ROT/scripts/sparr-prova.sh" --fil "$FIL" --fixtur-ocommittat --radera 1 \
        > "$SJT_UTDATA" 2>&1
    SJT_EXIT="$?"
    set -e
    echo "verktygets svar: $(head -n 1 "$SJT_UTDATA")"
    if [ "$SJT_EXIT" -eq 2 ] && grep -q "$SJT_VANTAT" "$SJT_UTDATA"; then
        echo "vägrade av RÄTT skäl, med exit 2: OK"
    else
        echo "STOPP: väntade exit 2 och skälet \"$SJT_VANTAT\", fick exit $SJT_EXIT."
        SJT_FEL=1
    fi

    echo ""
    echo "--- SJÄLVTEST: vägran mot fil med STAGAT arbete ---"
    git -C "$ROT" add -- "$FIL"
    set +e
    "$ROT/scripts/sparr-prova.sh" --fil "$FIL" --fixtur-ocommittat --radera 1 \
        > "$SJT_UTDATA" 2>&1
    SJT_EXIT="$?"
    set -e
    echo "verktygets svar: $(head -n 1 "$SJT_UTDATA")"
    if [ "$SJT_EXIT" -eq 2 ] && grep -q "$SJT_VANTAT" "$SJT_UTDATA"; then
        echo "vägrade av RÄTT skäl, med exit 2: OK"
        echo 'Detta är ledet som "git diff" ensamt hade missat: arbetsträdet är'
        echo 'identiskt med INDEXET, så den ostagade diffen är tom trots att'
        echo 'filen skiljer sig från HEAD.'
    else
        echo "STOPP: väntade exit 2 och skälet \"$SJT_VANTAT\", fick exit $SJT_EXIT."
        SJT_FEL=1
    fi
    rm -f "$SJT_UTDATA"

    echo ""
    echo "--- SJÄLVTESTETS VERDIKT ---"
    if [ "$SJT_FEL" -eq 0 ]; then
        echo "Samtliga vägranden höll."
        exit 0
    fi
    echo "Minst ett vägrande höll inte. Godkänn inte."
    exit 2
fi

if [ "${#MUTATIONER[@]}" -eq 0 ]; then
    echo "sparr-prova: ingen fällning angiven, ge --radera eller --ersatt" >&2
    exit 2
fi

# Raderar all bytekod under repot, utom i `.venv`. Kvitteras av anroparen.
#
# ANROPAS I BÅDA RIKTNINGARNA, och det är inte symmetri för sakens skull.
# EFTER körningen skyddar den mot att en föråldrad .pyc gör repot rött när
# källan är återställd. FÖRE muteringen skyddar den mot det farligare fallet:
# en mutation skriven inom samma sekund som förra skrivningen, med samma längd,
# kan läsas ur en färsk .pyc så att FÄLLNINGEN ALDRIG FÅR EFFEKT. Verktyget
# hade då rapporterat GRÖN, och ett äkta spärrtest hade dömts som vakuöst.
stada_bytekod() {
    find "$ROT" -name "__pycache__" -type d -not -path "$ROT/.venv/*" \
        -exec rm -rf {} + 2>/dev/null || true
}

# Kvitterar att ingen bytekod ligger kvar. En städning som tyst misslyckas är
# precis det `docs/incidentlogg.md` I7 handlar om: ett verktyg som rapporterar
# OK om ett utfall det inte tittar på.
kvittera_bytekod() {
    KVAR="$(find "$ROT" -name "__pycache__" -type d \
        -not -path "$ROT/.venv/*" 2>/dev/null | wc -l | tr -d ' ')"
    if [ "$KVAR" = "0" ]; then
        echo "bytekod under repot städad: OK"
    else
        echo "STOPP: $KVAR __pycache__ ligger kvar efter städning."
        echo "  Nästa svitkörning kan läsa fällningens kod ur cachen."
        exit 2
    fi
}

# Trapen sätts INNAN något ändras, och funktionen definieras innan trapen. Ett
# fönster mellan fixturens insättning och en senare trap hade kunnat lämna
# ocommittad text kvar i en spårad fil om skriptet föll däremellan under set -e.
aterstall() {
    UTFALL="$?"

    # Fixturen läggs in innan säkerhetskopian tas, så trapen kan löpa i ett
    # läge där kopian ännu inte finns. Då är den rena kopian det enda som finns
    # att gå tillbaka till, och det viktiga är att inte lämna fixturen kvar.
    #
    # Grenen frågar om kopian FAKTISKT ÄR TAGEN, inte om variabeln är satt.
    # `mktemp` sätter variabeln till en tom fil, och faller något mellan den
    # och `cp` hade den normala grenen kopierat den tomma filen över målfilen.
    if [ "$KOPIA_TAGEN" != "ja" ]; then
        echo ""
        echo "--- ÅTERSTÄLLNING ---"
        if [ "$FIXTUR_SKAPAD" = "ja" ]; then
            cp "$KOPIA_REN" "$FIL"
            rm -f "$KOPIA_REN"
            echo "Skriptet föll innan säkerhetskopian togs. Fixturen är bortstädad."
        else
            echo "Skriptet föll innan något ändrades. Inget att återställa."
        fi
        exit "$UTFALL"
    fi

    cp "$KOPIA" "$FIL"

    # BYTEKODEN MÅSTE BORT, och sha256 fångar inte det.
    #
    # CPython validerar en .pyc på källans mtime OCH storlek. En fällning som
    # är exakt lika lång som originalet och landar i samma sekund ger en .pyc
    # som ser giltig ut men bär FÄLLNINGENS kod. Efter en kvitterad
    # återställning körde nästa `pytest` då den fällda modulen ur cachen, och
    # ett test föll utan att någon rad i repot bar felet.
    #
    # Uppmätt i skiva 17: `return ra` → `return ""` i `src/kanal.py`, samma
    # längd, samma sekund. Trapen kvitterade sha256 OK och sviten var ändå
    # röd. Se `docs/incidentlogg.md` I7.
    stada_bytekod

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

    kvittera_bytekod

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

    # K7(b): kvittera att det ocommittade arbetet överlevde fällningen. Det är
    # hela poängen med fixturen. Hade återställningen gått via `git checkout --`
    # vore raden borta här, tyst och utan varning.
    if [ "$FIXTUR_SKAPAD" = "ja" ]; then
        if grep -q "$FIXTURMARKOR" "$FIL"; then
            echo "K7(b): det ocommittade arbetet överlevde fällningen: OK"
        else
            echo "STOPP: det ocommittade arbetet försvann i återställningen."
            echo "  ren kopia finns kvar: $KOPIA_REN"
            rm -f "$DIFF_FORE" "$DIFF_EFTER"
            exit 2
        fi

        # Fixturen städar upp efter sig genom att lägga tillbaka den rena
        # kopian, inte genom git. Skriptet ska inte lämna arbete efter sig.
        cp "$KOPIA_REN" "$FIL"
        if [ -n "$(git -C "$ROT" diff HEAD -- "$FIL")" ]; then
            echo "STOPP: fixturen kunde inte städas bort. $FIL skiljer sig från HEAD."
            echo "  ren kopia finns kvar: $KOPIA_REN"
            rm -f "$DIFF_FORE" "$DIFF_EFTER"
            exit 2
        fi
        echo "fixturen borttagen, $FIL är ren mot HEAD igen: OK"
        rm -f "$KOPIA_REN"
    fi

    rm -f "$KOPIA" "$DIFF_FORE" "$DIFF_EFTER"
    exit "$UTFALL"
}
# Bara EXIT: bash kör EXIT-trapen även vid SIGINT och SIGTERM, och en extra
# signal-trap skulle köra återställningen två gånger.
trap aterstall EXIT

# FIXTUR: skapar tillståndet "spårad fil med ocommittat arbete" åt granskaren.
#
# Utan detta läge går K7(b) inte att pröva utan skrivverktyg, och det fallet är
# just det som mest behöver oberoende verifiering: det är där `git checkout --`
# raderar arbete tyst. I skiva 1 redovisade granskaren fallet som OPRÖVAT och
# den som byggt verktyget körde det själv, alltså betygsatte sig själv på den
# enda punkt ingen annan kunde kontrollera. Hålet låg i verktyget.
#
# Raden läggs in FÖRE säkerhetskopian, så att kopian bär det ocommittade
# arbetet. Trapen återställer då till filens FAKTISKA utgångsläge, inte till
# HEAD, vilket är precis det som ska bevisas.
if [ "$FIXTUR" = "ja" ]; then
    if ! git -C "$ROT" ls-files --error-unmatch "$FIL" > /dev/null 2>&1; then
        echo "sparr-prova: --fixtur-ocommittat kräver en SPÅRAD fil. $FIL är otrackad." >&2
        exit 2
    fi
    # `git diff` ensamt ser inte stagade ändringar. En fil med bara stagat
    # arbete hade då passerat som "ren", och slutraden om att filen är ren mot
    # HEAD hade blivit osann. `git diff HEAD` täcker båda.
    if [ -n "$(git -C "$ROT" diff HEAD -- "$FIL")" ]; then
        echo "sparr-prova: $FIL bär redan ocommittat arbete, stagat eller ej." >&2
        echo "             Fixturen behövs inte, och skulle blanda sig i arbete" >&2
        echo "             som inte är dess." >&2
        exit 2
    fi
    case "$FIL" in
        *.py|*.sh)
            ;;
        *)
            echo "sparr-prova: fixturen kan bara kommentera .py och .sh. Fick $FIL." >&2
            exit 2
            ;;
    esac
    KOPIA_REN="$(mktemp -t sparr-prova-ren)"
    cp "$FIL" "$KOPIA_REN"
    printf '\n# %s\n' "$FIXTURMARKOR" >> "$FIL"
    FIXTUR_SKAPAD="ja"
    echo "--- FIXTUR ---"
    echo "La in ocommittat arbete sist i $FIL. Filen är nu spårad OCH smutsig."
    echo "Trapen ska återställa till detta läge, inte till HEAD."
    echo ""
fi

# Säkerhetskopian läggs utanför repot så att den aldrig kan committas,
# städas bort av en git clean, eller plockas upp av testsviten.
KOPIA="$(mktemp -t sparr-prova)"
SHA_FORE="$(shasum -a 256 "$FIL" | awk '{print $1}')"
DIFF_FORE="$(mktemp -t sparr-prova-diff)"
git -C "$ROT" diff -- "$FIL" > "$DIFF_FORE" || true
cp "$FIL" "$KOPIA"
KOPIA_TAGEN="ja"

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

echo "--- FÄLLNING i $FIL ---"
"$ROT/.venv/bin/python" "$ROT/scripts/mutera.py" --fil "$FIL" "${MUTATIONER[@]}"

# FÖRE sviten, inte bara efter. En mutation av samma längd skriven inom samma
# sekund som förra skrivningen kan annars läsas ur en färsk .pyc, så att
# fällningen aldrig får effekt och verktyget rapporterar GRÖN. Se I7.
stada_bytekod

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
