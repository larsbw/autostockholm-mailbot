"""Tester för scripts/osynliga-tecken.py.

Skriptet är ett GRANSKNINGSVERKTYG, och ett granskningsverktyg som säger noll
fynd när det borde säga ett är värre än inget verktyg: det producerar ett falskt
GRÖN som ingen ifrågasätter. Det är samma mekanism som rutan överst i
`docs/sparrar.md` beskriver. Testerna nedan bär därför påståendet att kontrollen
FÄLLER, alltså den sort §7.1 kräver att man prövar genom att fälla raden.

**VARJE OSYNLIGT TECKEN BYGGS MED `chr()`, ALDRIG SOM LITERAL.** Skrevs de
literalt skulle den här filen själv bära osynliga tecken, och
`test_repot_sjalvt_ar_rent` längst ned vore ett test som motsäger sin egen fil.
Det är lärdomen ur skiva 20:s fällning 7 och 9 åt andra hållet, som
`docs/sparrar.md` redovisar i posten `fordonsfakta-ur-sida`: där blev en escape
för hårt blanksteg ett literalt blankstegstecken utan att någon såg det, här
hålls tecknet borta ur källan med flit.
"""

from __future__ import annotations

import importlib.util
import subprocess
import unicodedata
from collections import Counter
from pathlib import Path

ROT = Path(__file__).resolve().parent.parent
_spec = importlib.util.spec_from_file_location(
    "osynliga_tecken", ROT / "scripts" / "osynliga-tecken.py"
)
osynliga = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(osynliga)


def test_femton_namngivna_kodpunkter():
    """Listans längd MÄTS, den påstås inte i löptext.

    Briefen för skiva 27 sade femton namngivna kodpunkter, och listan hämtades
    ordagrant ur skiva 26:s körning. Det här testet är det som gör talet
    kontrollerbart i stället för ihågkommet: växer eller krymper listan blir
    raden röd och den som ändrade den får skriva om varje mening som räknar den.
    """
    assert len(osynliga.NAMNGIVNA) == 15


def test_atta_av_de_namngivna_ar_cf():
    """FÖRDELNINGEN MÄTS, den påstås inte.

    Skriptets docstring sade först att de femton "ligger utanför Cf och Cc".
    Det är falskt för åtta av dem: mjukt bindestreck, nollbreddstecknen,
    riktningsmarkörerna, `WORD JOINER` och `ZERO WIDTH NO-BREAK SPACE` ÄR Cf och
    fälls redan av kategorigrenen. Resten är blanksteg och radseparatorer i Zs,
    Zl och Zp. Funnet av §7-granskningen av skiva 27, varv 1.

    Talen här är avlästa ur `scripts/osynliga-tecken.py --lista`, och testet
    finns för att nästa formulering av samma mening ska ha en källa att prövas
    mot i stället för ett minne.
    """
    kategorier = Counter(
        unicodedata.category(chr(k)) for k in osynliga.NAMNGIVNA
    )

    assert kategorier["Cf"] == 8
    assert kategorier["Zs"] == 5
    assert kategorier["Zl"] == 1
    assert kategorier["Zp"] == 1
    assert kategorier["Cc"] == 0


def test_varje_namngiven_kodpunkt_falls():
    """NEGATIVKONTROLL per kodpunkt. Ingen av de femton får slinka igenom.

    Prövas de bara som grupp räcker det att en enda faller ur `NAMNGIVNA` för
    att kontrollen ska tappa den tyst.
    """
    for kodpunkt in sorted(osynliga.NAMNGIVNA):
        fynd = osynliga.granska("ab" + chr(kodpunkt) + "cd", "x.py")
        assert len(fynd) == 1, f"U+{kodpunkt:04X} slank igenom"
        assert fynd[0][3] == f"U+{kodpunkt:04X}"


def test_hart_blanksteg_hittas_med_rad_och_kolumn():
    """Kodpunkten som faktiskt uppstått i repot: U+00A0, skiva 20."""
    fynd = osynliga.granska("rad ett\nett" + chr(0x00A0) + "hart", "src/x.py")

    assert fynd == [("src/x.py", 2, 4, "U+00A0", "NO-BREAK SPACE")]


def test_cf_falls_aven_utan_att_vara_namngiven():
    """Kategorin Cf bär fler tecken än de femton, och de ska fällas ändå.

    U+061C ARABIC LETTER MARK står inte i `NAMNGIVNA`. Utan Cf-grenen hade den
    passerat, och listan hade blivit ett tak i stället för ett golv.
    """
    assert 0x061C not in osynliga.NAMNGIVNA

    fynd = osynliga.granska("ab" + chr(0x061C) + "cd", "x.py")

    assert [f[3] for f in fynd] == ["U+061C"]


def test_cc_falls_och_saknat_namn_kraschar_inte():
    """Styrtecken under U+0020 har inget Unicode-namn.

    `unicodedata.name` kastar `ValueError` för dem. Kastade `namnge` vidare hade
    kontrollen dött på precis det fynd den skulle rapportera.
    """
    fynd = osynliga.granska("ab" + chr(0x0001) + "cd", "x.py")

    assert len(fynd) == 1
    assert fynd[0][3] == "U+0001"
    assert "utan namn" in fynd[0][4]


def test_tab_och_radbrytning_slapps_igenom():
    """NEGATIVKONTROLL ÅT ANDRA HÅLLET: kontrollen är inte ett larm som alltid går.

    TAB och radbrytning är Cc. Fälldes de skulle varje fil i repot ge tusentals
    fynd, utdatan bli oläsbar, och verktyget sluta köras. En kontroll som ingen
    kör skyddar ingenting.
    """
    assert osynliga.granska("ett\tva\nrad\ttre", "x.py") == []


def test_vagnretur_falls():
    """Vagnretur är undantagen från `TILLATNA` med avsikt.

    Den är lika osynlig som resten och hör inte hemma i det här repots filer.
    """
    fynd = osynliga.granska("rad" + chr(0x000D) + "\nrad", "x.py")

    assert [f[3] for f in fynd] == ["U+000D"]


def test_ren_text_ger_inga_fynd():
    """Huvudfallet. Svenska tecken är inte osynliga tecken."""
    assert osynliga.granska("Räksmörgås på Öland, 100 kr.", "x.py") == []


def test_utdatan_bar_aldrig_radens_innehall():
    """§6. Skriptet ska kunna riktas mot data/ utan att läcka kundtext.

    Returvärdet bär fil, rad, kolumn, kodpunkt och namn. Bär det också raden
    hamnar kundtext i varje rapport som klistrar in utdatan, och skriptet blir
    farligt att köra mot just de filer som mest behöver kontrolleras.

    Namnet i indatan är påhittat, som i `tests/test_persondatakontroll.py`.
    """
    kundtext = "Hej, jag heter Kalle Karlsson" + chr(0x200B) + " och har en Volvo"

    fynd = osynliga.granska(kundtext, "data/par.jsonl")

    assert len(fynd) == 1
    for falt in fynd[0]:
        assert "Kalle" not in str(falt)
        assert "Volvo" not in str(falt)


def _repo_med_en_commit(tmp_path: Path) -> None:
    """Ett git-repo som HAR en historik, eftersom `git diff HEAD` kräver det.

    Ett tomt repo saknar HEAD och ger avslutskod 128. Fixturen ska likna
    verkligheten: skiva 27:s situation var en ospårad fil i ett repo med
    historik, inte en fil i ett repo utan.
    """
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "fanns.py").write_text("redan = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "fanns.py"], cwd=tmp_path, check=True)
    subprocess.run(
        [
            "git",
            "-c", "user.email=test@example.invalid",
            "-c", "user.name=test",
            "commit", "-q", "-m", "start",
        ],
        cwd=tmp_path,
        check=True,
    )


def test_diffen_ser_osparade_filer(tmp_path):
    """REGRESSIONEN SOM FAKTISKT INTRÄFFADE, och den är skriptets egen.

    Första körningen av `--diff` i skiva 27 skrev noll fynd medan skivans fyra
    nya filer var ospårade. `git diff HEAD` ser dem inte, alltså granskade
    kontrollen ingenting och rapporterade rent. Det är exakt det falska GRÖN
    skriptet finns för att förhindra, producerat av skriptet självt.

    Här ligger ett hårt blanksteg i en ospårad fil. Ser `--diff` det inte är
    raden röd.
    """
    _repo_med_en_commit(tmp_path)
    (tmp_path / "ny.py").write_text(
        "x = 1" + chr(0x00A0) + "+ 2\n", encoding="utf-8"
    )

    rader = osynliga.adderade_rader(stagat=False, rot=tmp_path)

    assert ("ny.py", "x = 1" + chr(0x00A0) + "+ 2") in rader


def test_stagat_tar_inte_med_osparade_filer(tmp_path):
    """NEGATIVKONTROLL: de två flaggorna svarar på olika frågor.

    `--stagat` svarar på vad committen bär. En ospårad fil ingår inte i den, och
    tas den med där blir svaret fel åt andra hållet.
    """
    _repo_med_en_commit(tmp_path)
    (tmp_path / "ny.py").write_text("x = 1\n", encoding="utf-8")

    assert osynliga.adderade_rader(stagat=True, rot=tmp_path) == []


def test_repot_sjalvt_ar_rent():
    """Skivans egna filer bär inga osynliga tecken.

    Det här är påståendet skiva 26:s granskare inte kunde belägga, och det är
    nu belagt av ett committat test i stället för av en engångskörning.
    """
    for sokvag in (
        "src/vy.py",
        "tests/test_vy.py",
        "scripts/osynliga-tecken.py",
        "scripts/kor-vy.py",
        "scripts/par-koppling.py",
        "tests/test_osynliga_tecken.py",
    ):
        text = (ROT / sokvag).read_text(encoding="utf-8", newline="")
        assert osynliga.granska(text, sokvag) == []
