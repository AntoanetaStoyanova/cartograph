from cartograph.bin.collect import skipped_step


def test_skipped_step_is_empty_and_skipped() -> None:
    step = skipped_step()

    assert step["status"] == "skipped"
    assert step["fetched"] == 0
    assert step["failed"] == step["files"] == step["missing_languages"] == []
    assert step["source"] is None
    assert step["error"] is None


def test_skipped_step_returns_fresh_lists() -> None:
    first, second = skipped_step(), skipped_step()
    first["failed"].append("fr/a")
    first["files"].append({"name": "x", "rows": 0, "bytes": 0})
    first["missing_languages"].append("ja")

    assert second["failed"] == second["files"] == second["missing_languages"] == []
