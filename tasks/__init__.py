"""Tâches d'automatisation — exécutées via `inv <commande>`."""

import shlex
import tempfile
from pathlib import Path

from invoke import Context, Exit, task

# ---------------------------------------------------------------------------
# Qualité du code
# ---------------------------------------------------------------------------


@task
def lint(c: Context) -> None:
    """Lance les hooks pre-commit (Ruff, fichiers) sur tous les fichiers."""
    c.run("uv run pre-commit run --all-files")


@task
def hooks(c: Context) -> None:
    """Installe le hook Git pre-commit."""
    c.run("uv run pre-commit install")


@task
def fmt(c: Context) -> None:
    """Formate le code avec Ruff."""
    c.run("uv run ruff format .")


@task
def typecheck(c: Context) -> None:
    """Vérifie les types avec mypy."""
    c.run("uv run mypy src/cartograph")


@task(pre=[lint, typecheck])  # type: ignore[misc]
def check(c: Context) -> None:
    """Lance lint + typecheck en séquence."""


@task
def test(c: Context) -> None:
    """Lance les tests pytest avec coverage."""
    c.run("uv run pytest")


@task(pre=[check, test])  # type: ignore[misc]
def ci(c: Context) -> None:
    """Lance la suite complète CI : lint, typecheck, tests."""


# ---------------------------------------------------------------------------
# Collecte
# ---------------------------------------------------------------------------


@task
def collect(
    c: Context,
    catalogue: bool = False,
    prices: bool = True,
    languages: str = "",
    data_dir: str = "",
) -> None:
    """Collecte les prix du jour (et le catalogue avec --catalogue) dans data/."""
    args = ["uv run python -m cartograph.bin.collect.run"]
    if catalogue:
        args.append("--catalogue")
    if not prices:
        args.append("--no-prices")
    if languages:
        args.append(f"--languages {shlex.quote(languages)}")
    if data_dir:
        args.append(f"--data-dir {shlex.quote(data_dir)}")
    c.run(" ".join(args))


# ---------------------------------------------------------------------------
# Pilotage
# ---------------------------------------------------------------------------


@task
def suivi(c: Context, mois: str = "", force: bool = False) -> None:
    """Rapport de suivi du mois (en cours par défaut) ; lancer après inv ci."""
    args = ["uv run python -m cartograph.bin.suivi.run"]
    if mois:
        args.append(f"--mois {shlex.quote(mois)}")
    if force:
        args.append("--force")
    c.run(" ".join(args))


# ---------------------------------------------------------------------------
# Documentation
# ---------------------------------------------------------------------------


@task
def docs(c: Context) -> None:
    """Génère la documentation Sphinx dans docs/_build/html/."""
    c.run("uv run sphinx-build -b html docs docs/_build/html")
    print("Documentation disponible dans docs/_build/html/index.html")


@task
def docs_clean(c: Context) -> None:
    """Supprime la documentation générée."""
    c.run("rm -rf docs/_build")


@task
def okflint(c: Context) -> None:
    """Vérifie le frontmatter et les liens des specs et plans (okf-base.yaml)."""
    c.run("uv run okflint validate --manifest okf-base.yaml")


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


@task
def release(c: Context, dry_run: bool = False) -> None:
    """Bump, changelog, tag, push et PR vers main ; sur develop seulement."""
    branch = _current_branch(c)
    if branch != "develop":
        raise Exit(f"inv release se lance sur develop, pas sur {branch}.")
    _require_clean(c)
    if dry_run:
        _bump(c, "uv run cz bump --dry-run --yes")
        return
    c.run("git pull --ff-only")
    lint(c)
    typecheck(c)
    test(c)
    _bump(c, "uv run cz bump --yes")
    docs(c)
    c.run("git push --follow-tags")
    _open_release_pr(c)


@task
def finish(c: Context) -> None:
    """Contrôles, push et PR vers develop ; sur une branche feature/ seulement."""
    branch = _current_branch(c)
    if not branch.startswith("feature/"):
        raise Exit(f"inv finish se lance sur une branche feature/, pas sur {branch}.")
    _require_clean(c)
    lint(c)
    typecheck(c)
    test(c)
    okflint(c)
    c.run("git push -u origin HEAD")
    existing = c.run("gh pr view --json url --jq .url", hide=True, warn=True)
    if existing.ok and existing.stdout.strip():
        print(f"PR déjà ouverte : {existing.stdout.strip()}")
        return
    c.run("gh pr create --base develop --fill")


def _current_branch(c: Context) -> str:
    """Nom de la branche courante."""
    return str(c.run("git branch --show-current", hide=True).stdout.strip())


def _require_clean(c: Context) -> None:
    """Arrête la tâche si l'arbre de travail a des modifications."""
    if c.run("git status --porcelain", hide=True).stdout.strip():
        raise Exit("Arbre de travail non propre : commiter ou ranger d'abord.")


def _open_release_pr(c: Context) -> None:
    """Ouvre la PR develop → main de la version publiée, ou affiche celle qui existe."""
    tag = "v" + c.run("uv version --short", hide=True).stdout.strip()
    existing = c.run(
        "gh pr list --base main --head develop --state open --json url --jq '.[0].url'",
        hide=True,
    ).stdout.strip()
    if existing:
        print(f"PR develop → main déjà ouverte : {existing}")
        return
    body = _changelog_section(Path("CHANGELOG.md").read_text(encoding="utf-8"), tag)
    with tempfile.TemporaryDirectory() as tmp:
        body_file = Path(tmp) / "body.md"
        body_file.write_text(body, encoding="utf-8")
        c.run(
            "gh pr create --base main --head develop"
            f" --title {shlex.quote(f'Release {tag}')}"
            f" --body-file {shlex.quote(str(body_file))}"
        )


def _changelog_section(text: str, tag: str) -> str:
    """Contenu de la section `## <tag>` du changelog, sans son titre."""
    lines = text.splitlines()
    start = next(
        (i for i, line in enumerate(lines) if line.split(" ")[:2] == ["##", tag]),
        None,
    )
    if start is None:
        raise Exit(f"Section {tag} absente de CHANGELOG.md.")
    end = next(
        (i for i in range(start + 1, len(lines)) if lines[i].startswith("## v")),
        len(lines),
    )
    return "\n".join(lines[start + 1 : end]).strip()


def _bump(c: Context, command: str) -> None:
    """Lance cz bump ; codes 3 et 21 : aucun commit qui change la version."""
    result = c.run(command, warn=True)
    if result.exited in (3, 21):
        raise Exit("Rien à publier : aucun feat, fix, refactor ou perf depuis le tag.")
    if result.exited:
        raise Exit(code=result.exited)
