"""Tâches d'automatisation — exécutées via `inv <commande>`."""

import shlex

from invoke import Context, task

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


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------


@task
def push_develop(c: Context) -> None:
    """Pousse la branche courante vers origin/develop."""
    c.run("git push origin develop")


@task
def push_main(c: Context) -> None:
    """Pousse la branche courante vers origin/main (confirmation requise)."""
    answer = input("Push vers main — confirmer ? [o/n] ").strip().lower()
    if answer == "o":
        c.run("git push origin main")
    else:
        print("Push annulé.")
