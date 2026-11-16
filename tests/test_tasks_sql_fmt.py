from invoke import MockContext, Result

from tasks import sql_fmt

SQLFLUFF = "uv run pre-commit run sqlfluff-fix --all-files --hook-stage manual"


def test_sql_fmt_runs_sqlfluff_fix() -> None:
    c = MockContext(run={SQLFLUFF: Result()})
    sql_fmt(c)
    assert [call.args[0] for call in c.run.call_args_list] == [SQLFLUFF]


def test_sql_fmt_does_not_stop_when_files_change() -> None:
    c = MockContext(run={SQLFLUFF: Result(exited=1)})
    sql_fmt(c)
    assert c.run.call_args.kwargs["warn"] is True
