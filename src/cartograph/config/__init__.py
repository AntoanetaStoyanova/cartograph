"""
Paramètres du projet.

Les valeurs propres à l'environnement sont lues dans ``.env`` (voir
``.env.example``) ou dans les variables d'environnement.

Attributes
----------
LANGUAGES : tuple[str, ...]
    Codes des langues TCGdex collectées.
TCGDEX_BASE_URL : str
    Racine de l'API TCGdex.
TCGDEX_USER_AGENT : str
    En-tête ``User-Agent`` envoyé à l'API, lu dans la variable
    ``TCGDEX_USER_AGENT``.
REQUEST_PAUSE_S : float
    Pause minimale entre deux requêtes, en secondes.
REQUEST_TIMEOUT_S : float
    Délai d'attente d'une requête, en secondes.
MAX_RETRIES : int
    Nombre de nouvelles tentatives après une erreur temporaire.
RETRY_BACKOFF_S : float
    Attente avant la première nouvelle tentative, doublée à chaque suivante.
MAX_RETRY_AFTER_S : float
    Plafond de l'attente demandée par l'en-tête ``Retry-After``, en secondes.
RETRY_STATUSES : frozenset[int]
    Codes HTTP temporaires qui déclenchent une nouvelle tentative.
MAX_CONSECUTIVE_FAILURES : int
    Nombre de cartes en échec d'affilée (hors 404) qui arrête une collecte.
PROGRESS_EVERY : int
    Nombre de cartes entre deux messages de progression.
DATA_DIR : pathlib.Path
    Dossier local des sorties de collecte (``snapshots/``, ``raw/``,
    ``runs/``), ignoré par Git.
LOG_DIR : pathlib.Path
    Dossier des fichiers de log, ignoré par Git.
SNAPSHOT_COMPRESSION : str
    Codec de compression des snapshots Parquet.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[3]
ENV_FILE = PROJECT_ROOT / ".env"

load_dotenv(ENV_FILE)


def _require_env(name: str) -> str:
    """
    Renvoie la variable d'environnement ``name``.

    Parameters
    ----------
    name : str
        Nom de la variable.

    Returns
    -------
    str
        Valeur de la variable.

    Raises
    ------
    RuntimeError
        Si la variable est absente ou vide.
    """
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(
            f"Variable {name} absente : copier .env.example en .env, ou la définir "
            "dans l'environnement (variable GitHub Actions dans les workflows)."
        )
    return value


LANGUAGES: tuple[str, ...] = ("fr", "en", "ja")

TCGDEX_BASE_URL = "https://api.tcgdex.net/v2"
TCGDEX_USER_AGENT = _require_env("TCGDEX_USER_AGENT")
REQUEST_PAUSE_S = 0.1
REQUEST_TIMEOUT_S = 30.0
MAX_RETRIES = 4
RETRY_BACKOFF_S = 1.0
MAX_RETRY_AFTER_S = 60.0
RETRY_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})
MAX_CONSECUTIVE_FAILURES = 20
PROGRESS_EVERY = 1000
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
SNAPSHOT_COMPRESSION = "zstd"
