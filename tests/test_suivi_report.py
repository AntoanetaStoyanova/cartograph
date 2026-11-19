from datetime import date
from pathlib import Path

import pytest

from cartograph.bin.suivi.actions import RunStats
from cartograph.bin.suivi.estimates import estimate
from cartograph.bin.suivi.quality import Coverage
from cartograph.bin.suivi.report import (
    COMMENT_PLACEHOLDER,
    Report,
    render,
    write_report,
)
from cartograph.bin.suivi.roadmap import Lot, LotState

LOTS = [
    Lot("FND-01", LotState.DONE, "P1"),
    Lot("DBT-01", LotState.OPEN, "P1"),
    Lot("EMB-03", LotState.OPEN, "P2"),
    Lot("STO-03", LotState.DROPPED, None),
]


def report(**changes: object) -> Report:
    values: dict[str, object] = {
        "month": "2026-11",
        "generated": date(2026, 11, 15),
        "lots": LOTS,
        "days": [date(2026, 11, 1), date(2026, 11, 7)],
        "runs": RunStats(
            runs=20, succeeded=17, failed=3, billed_minutes=1879, in_progress=0
        ),
        "tests": 162,
        "coverage": Coverage(percent=97.5, statements=812, measured=date(2026, 11, 14)),
        "estimates": estimate(billed_minutes=1879),
    }
    values.update(changes)
    return Report(**values)  # type: ignore[arg-type]


def test_render_a_full_month() -> None:
    text = render(report())

    assert text.startswith(
        "---\ntype: reference\nstatut: brouillon\nredige_le: 2026-11-15\n---\n"
    )
    assert "# Suivi — novembre 2026" in text
    assert "| Fait | 1 | 0 | 0 | 0 | 1 |" in text
    assert "| Ouvert | 1 | 1 | 0 | 0 | 2 |" in text
    assert "| Supprimé | 0 | 0 | 0 | 1 | 1 |" in text
    assert "| Jours travaillés | 2 (1er, 7) |" in text
    assert "| Exécutions | 20 (17 réussies, 3 en échec) |" in text
    assert "| Minutes facturables | 1 879 |" in text
    assert "| Tests | 162 |" in text
    assert (
        "| Couverture | 97,5 % (812 instructions, mesurée le 14 novembre 2026) |"
        in text
    )
    assert "| Énergie des minutes Actions | 0,57 kWh |" in text
    assert "| Émissions | 0,22 kg CO₂e |" in text
    assert "## Commentaire" in text


def test_render_a_month_without_data() -> None:
    text = render(
        report(
            days=[],
            runs=RunStats(0, 0, 0, 0, 1),
            tests=None,
            coverage=None,
            estimates=estimate(billed_minutes=0),
        )
    )

    assert "| Jours travaillés | 0 |" in text
    assert (
        "| Exécutions | 0 (0 réussies, 0 en échec ; 1 en cours, non comptée) |" in text
    )
    assert "| Tests | non mesuré |" in text
    assert "| Couverture | non mesuré |" in text


def test_write_report_refuses_to_overwrite(tmp_path: Path) -> None:
    path = tmp_path / "suivi" / "2026-11.md"
    write_report(path, "premier", force=False)

    with pytest.raises(FileExistsError, match="--force"):
        write_report(path, "second", force=False)
    assert path.read_text(encoding="utf-8") == "premier"


def test_write_report_with_force_replaces_the_figures(tmp_path: Path) -> None:
    path = tmp_path / "2026-11.md"
    write_report(path, render(report(tests=100)), force=False)

    write_report(path, render(report(tests=170)), force=True)

    assert "| Tests | 170 |" in path.read_text(encoding="utf-8")


def test_write_report_with_force_keeps_comment_and_status(tmp_path: Path) -> None:
    path = tmp_path / "2026-11.md"
    first = render(report(tests=100)).replace("statut: brouillon", "statut: fait")
    path.write_text(
        first.replace(COMMENT_PLACEHOLDER, "**Avancement.** Porte 0 franchie.\n"),
        encoding="utf-8",
    )

    write_report(path, render(report(tests=170)), force=True)

    text = path.read_text(encoding="utf-8")
    assert "| Tests | 170 |" in text
    assert "statut: fait" in text
    assert "**Avancement.** Porte 0 franchie." in text
    assert COMMENT_PLACEHOLDER not in text


def test_render_says_nothing_is_paid() -> None:
    text = render(report())

    assert "valorisé" not in text
    assert "| Équivalent Actions payant (gratuit : dépôt public) | 22,55 $ |" in text


def test_write_report_with_force_over_a_free_text(tmp_path: Path) -> None:
    path = tmp_path / "2026-11.md"
    path.write_text("ancien texte\n", encoding="utf-8")

    write_report(path, render(report()), force=True)

    assert path.read_text(encoding="utf-8") == render(report())


def test_write_report_with_force_keeps_a_comment_with_a_second_title(
    tmp_path: Path,
) -> None:
    path = tmp_path / "2026-11.md"
    comment = "Texte.\n\n## Commentaire\n\nSuite.\n"
    path.write_text(
        render(report()).replace(COMMENT_PLACEHOLDER, comment), encoding="utf-8"
    )

    write_report(path, render(report(tests=170)), force=True)

    assert path.read_text(encoding="utf-8").endswith(comment)
