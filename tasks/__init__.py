"""Tâches d'automatisation — exécutées via `inv <commande>`."""

import os
import re
import shlex
import shutil
import tempfile
import time
from datetime import date
from pathlib import Path, PurePosixPath

import duckdb
from invoke import Context, Exit, call, task

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
def sql_fmt(c: Context) -> None:
    """Corrige le SQL de dbt/models et dbt/analyses avec sqlfluff fix."""
    # pre-commit sort en erreur dès qu'il modifie un fichier : le commit revérifie.
    c.run(
        "uv run pre-commit run sqlfluff-fix --all-files --hook-stage manual",
        warn=True,
    )


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


DATABASE = Path("data/cartograph.duckdb")
REBUILD_DATABASE = Path("data/cartograph.rebuild.duckdb")
SAMPLE_DIR = Path("dbt/sample/snapshots")
SAMPLE_DATABASE = Path("data/cartograph.sample.duckdb")
REAL_DATA_TAG = "donnees_reelles"
TESTING_COMMANDS = {"build", "test"}


@task
def dbt(c: Context, args: str = "build", sample: bool = False) -> None:
    """Lance dbt (build par défaut) ; --sample : échantillon, sans tests réels."""
    Path("data").mkdir(exist_ok=True)
    if not sample:
        c.run(_dbt_command(args))
        return
    variables = shlex.quote(f"{{snapshot_dir: {SAMPLE_DIR.as_posix()}}}")
    command = args.split()[:1]
    if command and command[0] in TESTING_COMMANDS:
        args = f"{args} --exclude tag:{REAL_DATA_TAG}"
    c.run(
        _dbt_command(f"{args} --vars {variables}"),
        env={"CARTOGRAPH_DUCKDB": str(SAMPLE_DATABASE)},
    )


def _dbt_command(args: str) -> str:
    """Commande dbt sur le projet et le profil de dbt/."""
    return f"uv run dbt {args} --project-dir dbt --profiles-dir dbt"


@task
def couverture_tests(c: Context) -> None:
    """Liste les colonnes dbt sans test et les clés sans relationships."""
    c.run("uv run python -m cartograph.bin.dbt_coverage")


@task
def regles(c: Context, parse: bool = True) -> None:
    """Contrôle le lien entre regles-metier.md et les tests dbt et pytest."""
    if parse:
        c.run(
            _dbt_command("parse"),
            env={"CARTOGRAPH_DUCKDB": str(SAMPLE_DATABASE)},
        )
    c.run("uv run python -m cartograph.bin.regles_metier")


@task(  # type: ignore[misc]
    pre=[check, test, call(dbt, sample=True), call(regles, parse=False)]
)
def ci(c: Context) -> None:
    """Lance la CI : lint, typecheck, tests, dbt sur l'échantillon, règles métier."""


# ---------------------------------------------------------------------------
# Données
# ---------------------------------------------------------------------------


@task
def collect(
    c: Context,
    catalogue: bool = False,
    prices: bool = True,
    languages: str = "",
    data_dir: str = "",
) -> None:
    """
    Collecte dans data/ les sets, les nouvelles cartes et les prix, puis met à jour
    le dernier catalogue ; --catalogue fait une collecte complète du catalogue.
    """
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


@task
def rebuild(c: Context, skip_download: bool = False) -> None:
    """Rapatrie les snapshots des Releases et reconstruit data/cartograph.duckdb."""
    start = time.monotonic()
    if not skip_download:
        c.run("uv run python -m cartograph.bin.rebuild")
    DATABASE.parent.mkdir(exist_ok=True)
    _remove_database(REBUILD_DATABASE)
    duckdb.connect(REBUILD_DATABASE).close()
    result = c.run(
        _dbt_command("build"),
        env={"CARTOGRAPH_DUCKDB": str(REBUILD_DATABASE)},
        warn=True,
    )
    if not result.ok:
        _remove_database(REBUILD_DATABASE)
        raise Exit(f"dbt build a échoué : {DATABASE} inchangée.")
    _wal(DATABASE).unlink(missing_ok=True)
    REBUILD_DATABASE.replace(DATABASE)
    print(f"{DATABASE} reconstruite en {time.monotonic() - start:.1f} s.")


def _remove_database(path: Path) -> None:
    """Supprime une base DuckDB et son journal .wal s'ils existent."""
    path.unlink(missing_ok=True)
    _wal(path).unlink(missing_ok=True)


def _wal(path: Path) -> Path:
    """Journal DuckDB d'une base, à retirer avec elle."""
    return path.with_name(path.name + ".wal")


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
def okflint(c: Context) -> None:
    """Vérifie le frontmatter et les liens des specs et plans (okf-base.yaml)."""
    c.run("uv run okflint validate --manifest okf-base.yaml")


# ---------------------------------------------------------------------------
# Nettoyage
# ---------------------------------------------------------------------------

CLEAN_FILE = Path(".clean")
PROTECTED_PATHS = (
    ".env",
    ".venv",
    ".git",
    "data/snapshots",
    "data/raw",
    "data/cartograph.duckdb",
    "docs/plans",
    "docs/specs",
)
_WILDCARD = re.compile(r"[*?\[]")


@task
def clean(c: Context) -> None:
    """Supprime les fichiers générés déclarés dans .clean, jamais le travail."""
    patterns = _read_clean(CLEAN_FILE)
    tracked = set(c.run("git ls-files", hide=True).stdout.splitlines())
    targets = _clean_targets(Path.cwd(), patterns, tracked)
    for target in targets:
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
        print(f"Supprimé : {target.relative_to(Path.cwd()).as_posix()}")
    if not targets:
        print("Rien à nettoyer.")


def _read_clean(path: Path) -> list[str]:
    """Motifs de .clean, sans lignes vides ni commentaires."""
    if not path.exists():
        raise Exit(f"{path} absent : la liste des fichiers à supprimer y est déclarée.")
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def _clean_targets(root: Path, patterns: list[str], tracked: set[str]) -> list[Path]:
    """Chemins à supprimer ; Exit avant toute suppression si un motif est dangereux.

    Parameters
    ----------
    root : Path
        Racine du dépôt.
    patterns : list[str]
        Motifs glob relatifs à la racine ; ``/`` final : dossiers seulement.
    tracked : set[str]
        Fichiers suivis par Git (``git ls-files``).

    Returns
    -------
    list[Path]
        Fichiers et dossiers correspondants, sans descendre dans un dossier retenu
        ni dans un chemin protégé.
    """
    for pattern in patterns:
        _check_pattern(pattern)
    found: list[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        base = PurePosixPath(Path(dirpath).relative_to(root).as_posix())
        for name in list(dirnames):
            rel = (base / name).as_posix()
            matched = _clean_match(rel, patterns, is_dir=True)
            if matched:
                found.append(rel)
            if matched or rel in PROTECTED_PATHS:
                dirnames.remove(name)
        found += [
            rel
            for rel in ((base / name).as_posix() for name in filenames)
            if _clean_match(rel, patterns, is_dir=False)
        ]
    for rel in found:
        _check_target(rel, tracked)
    return [root / rel for rel in found]


def _check_pattern(pattern: str) -> None:
    """Refuse un motif hors du dépôt ou dont la partie fixe vise un chemin protégé."""
    path = PurePosixPath(pattern)
    if path.is_absolute() or ".." in path.parts:
        raise Exit(f"Motif {pattern} de .clean hors du dépôt.")
    fixed: list[str] = []
    for part in path.parts:
        if _WILDCARD.search(part):
            break
        fixed.append(part)
    prefix = "/".join(fixed)
    for protected in PROTECTED_PATHS:
        if prefix and (prefix == protected or prefix.startswith(protected + "/")):
            raise Exit(f"Motif {pattern} de .clean : chemin protégé ({protected}).")


def _clean_match(rel: str, patterns: list[str], is_dir: bool) -> bool:
    """Vrai si ``rel`` correspond à un motif (``/`` final : dossiers seulement)."""
    path = PurePosixPath(rel)
    for pattern in patterns:
        if pattern.endswith("/"):
            if is_dir and path.full_match(pattern.rstrip("/")):
                return True
        elif path.full_match(pattern):
            return True
    return False


def _check_target(rel: str, tracked: set[str]) -> None:
    """Refuse un chemin protégé, qui en contient un ou qui contient un fichier suivi."""
    for protected in PROTECTED_PATHS:
        if rel == protected or protected.startswith(rel + "/"):
            raise Exit(f"{rel} retenu par .clean : chemin protégé ({protected}).")
    if rel in tracked or any(path.startswith(rel + "/") for path in tracked):
        raise Exit(f"{rel} retenu par .clean contient un fichier suivi par Git.")


# ---------------------------------------------------------------------------
# Git
# ---------------------------------------------------------------------------

JOURNAL = Path(".ai-context/JOURNAL.md")
LOG = Path(".ai-context/LOG.md")
LOG_HEADER = (
    "# Log — versions publiées\n\n"
    "> Entrées de `JOURNAL.md` déplacées par `inv release`, une section par version.\n"
)
_JOURNAL_ENTRY = re.compile(r"^## \[\d{4}-\d{2}-\d{2}\]", re.MULTILINE)
_LOG_VERSION = re.compile(r"^# v", re.MULTILINE)
_VERSION_BUMP = re.compile(r"^(feat|fix|refactor|perf)(\([^)]*\))?!?:")
CODE_PATHS = ("src/", "tasks/", "dbt/models/", "dbt/macros/")
PROTECTED_BRANCHES = ("main", "develop")


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
    dbt(c, sample=True)
    _archive_journal(c, _next_version(c))
    _bump(c, "uv run cz bump --yes")
    docs(c)
    c.run("git push --follow-tags")
    _open_release_pr(c)
    clean(c)


@task
def finish(c: Context) -> None:
    """Contrôles, push et PR vers develop ; sur une branche feature/ seulement."""
    branch = _current_branch(c)
    if not branch.startswith("feature/"):
        raise Exit(f"inv finish se lance sur une branche feature/, pas sur {branch}.")
    _require_clean(c)
    _confirm_without_bump(c)
    lint(c)
    typecheck(c)
    test(c)
    dbt(c, sample=True)
    okflint(c)
    c.run("git push -u origin HEAD")
    existing = c.run("gh pr view --json url --jq .url", hide=True, warn=True)
    if existing.ok and existing.stdout.strip():
        print(f"PR déjà ouverte : {existing.stdout.strip()}")
    else:
        c.run("gh pr create --base develop --fill")
    clean(c)


@task
def delete_branch(c: Context, name: str, force: bool = False) -> None:
    """Supprime une branche en local et sur origin ; PR fusionnée sauf --force."""
    _check_deletable(c, name)
    if not force and not _merged_pr(c, name):
        raise Exit(f"{name} : aucune PR fusionnée (--force pour supprimer quand même).")
    _delete_branch(c, name)
    c.run("git fetch --prune")


@task
def clean_branches(c: Context) -> None:
    """Supprime, après confirmation, les branches locales dont la PR est fusionnée."""
    current = _current_branch(c)
    local = c.run("git for-each-ref --format=%(refname:short) refs/heads/", hide=True)
    merged = [
        branch
        for branch in local.stdout.split()
        if branch not in (*PROTECTED_BRANCHES, current) and _merged_pr(c, branch)
    ]
    if not merged:
        print("Aucune branche fusionnée à supprimer.")
        return
    print("Branches fusionnées :")
    for branch in merged:
        print(f"  {branch}")
    if input("Supprimer en local et sur origin ? (o/N) ").strip().lower() != "o":
        return
    for branch in merged:
        _delete_branch(c, branch)
    c.run("git fetch --prune")


def _check_deletable(c: Context, branch: str) -> None:
    """Refuse main, develop et la branche courante, même avec --force."""
    if branch in PROTECTED_BRANCHES:
        raise Exit(f"{branch} est protégée : jamais supprimée.")
    if branch == _current_branch(c):
        raise Exit(f"{branch} est la branche courante : changer de branche d'abord.")


def _merged_pr(c: Context, branch: str) -> bool:
    """Vrai si une PR de la branche est fusionnée (reconnaît aussi un squash)."""
    result = c.run(
        f"gh pr list --head {shlex.quote(branch)} --state merged"
        " --json number --jq length",
        hide=True,
    )
    return int(result.stdout.strip() or 0) > 0


def _delete_branch(c: Context, branch: str) -> None:
    """Supprime la branche en local, puis sur origin si elle y est encore."""
    name = shlex.quote(branch)
    c.run(f"git branch -D {name}")
    if c.run(f"git ls-remote --heads origin {name}", hide=True).stdout.strip():
        c.run(f"git push origin --delete {name}")


def _bumps_version(subjects: list[str]) -> bool:
    """Vrai si un sujet de commit fait monter la version (feat, fix, refactor, perf)."""
    return any(_VERSION_BUMP.match(subject) for subject in subjects)


def _touches_code(paths: list[str]) -> bool:
    """Vrai si un chemin modifié est du code livré (src, tasks, dbt)."""
    return any(path.startswith(CODE_PATHS) for path in paths)


def _confirm_without_bump(c: Context) -> None:
    """Demande confirmation si la branche modifie du code sans commit de version."""
    diff = c.run("git diff --name-only origin/develop...HEAD", hide=True)
    if not _touches_code(diff.stdout.split()):
        return
    log = c.run("git log --format=%s origin/develop..HEAD", hide=True)
    subjects = log.stdout.splitlines()
    if _bumps_version(subjects):
        return
    print("Code modifié sans commit feat, fix, refactor ou perf :")
    for subject in subjects:
        print(f"  {subject}")
    print("inv release ne publiera pas de version (corriger avec git commit --amend).")
    if input("Continuer quand même ? (o/N) ").strip().lower() != "o":
        raise Exit("Aucun push : renommer le commit puis relancer inv finish.")


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


def _next_version(c: Context) -> str:
    """Version que cz bump va publier ; arrête la tâche s'il n'y a rien à publier."""
    result = c.run("uv run cz bump --get-next", hide=True, warn=True)
    if result.exited in (3, 21):
        raise Exit("Rien à publier : aucun feat, fix, refactor ou perf depuis le tag.")
    if result.exited:
        raise Exit(code=result.exited)
    return str(result.stdout.strip())


def _journal_to_log(
    journal: str, log: str, version: str, day: str
) -> tuple[str, str] | None:
    """Journal réduit à sa dernière entrée et log complété ; None si rien à déplacer."""
    starts = [m.start() for m in _JOURNAL_ENTRY.finditer(journal)]
    if len(starts) < 2:
        return None
    kept = journal[: starts[1]].rstrip() + "\n"
    section = f"# v{version} — {day}\n\n{journal[starts[1] :].strip()}\n"
    log = log or LOG_HEADER
    first = _LOG_VERSION.search(log)
    if first is None:
        return kept, log.rstrip() + "\n\n" + section
    return kept, log[: first.start()] + section + "\n" + log[first.start() :]


def _archive_journal(c: Context, version: str) -> None:
    """Déplace dans LOG.md les entrées du journal sauf la plus récente, puis commite."""
    if not JOURNAL.exists():
        return
    log = LOG.read_text(encoding="utf-8") if LOG.exists() else ""
    moved = _journal_to_log(
        JOURNAL.read_text(encoding="utf-8"), log, version, date.today().isoformat()
    )
    if moved is None:
        return
    JOURNAL.write_text(moved[0], encoding="utf-8")
    LOG.write_text(moved[1], encoding="utf-8")
    c.run(f"git add {JOURNAL} {LOG}")
    c.run(f"git commit -m 'chore(journal): archive avant v{version}'")
