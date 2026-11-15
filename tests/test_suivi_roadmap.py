from pathlib import Path

from cartograph.bin.suivi.roadmap import Lot, LotState, read_lots

ROADMAP = Path(__file__).parent / "fixtures" / "suivi" / "roadmap.md"


def test_read_lots_reads_every_lot_row() -> None:
    assert read_lots(ROADMAP) == [
        Lot("FND-01", LotState.DONE, "P1"),
        Lot("DBT-01", LotState.OPEN, "P1"),
        Lot("STO-03", LotState.DROPPED, None),
        Lot("EMB-03", LotState.OPEN, "P2"),
        Lot("MLB-01", LotState.OPEN, None),
    ]


def test_read_lots_ignores_headers_and_check_lists(tmp_path: Path) -> None:
    path = tmp_path / "roadmap.md"
    path.write_text(
        "|     | Id | Lot | Prio |\n| --- | -- | --- | ---- |\n- [ ] critère\n",
        encoding="utf-8",
    )

    assert read_lots(path) == []
