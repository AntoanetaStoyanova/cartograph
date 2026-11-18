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
ROTATION_SIZE : int
    Fiches hors prix relues chaque jour pour tenir le catalogue à jour, les
    plus anciennes d'abord.
DATA_DIR : pathlib.Path
    Dossier local des sorties de collecte (``snapshots/``, ``raw/``,
    ``runs/``), ignoré par Git.
LOG_DIR : pathlib.Path
    Dossier des fichiers de log, ignoré par Git.
SNAPSHOT_COMPRESSION : str
    Codec de compression des snapshots Parquet.
DATA_REPO : str
    Dépôt GitHub de la collecte, lu par le tableau de suivi.
COLLECT_WORKFLOW : str
    Fichier du workflow de collecte dans ``DATA_REPO``.
PRICES_REPO : str
    Dépôt privé des Releases mensuelles ``data-AAAA-MM`` (prix et brut).
ACTIONS_USD_PER_MIN : float
    Prix d'une minute de runner Linux de 4 processeurs, équivalent payant du
    runner gratuit d'un dépôt public.
RUNNER_VCPUS : int
    Processeurs d'un runner de dépôt public.
RUNNER_MEMORY_GB : int
    Mémoire d'un runner de dépôt public.
RUNNER_WATTS : float
    Puissance estimée d'un runner, méthode Cloud Carbon Footprint.
GRID_KG_CO2E_PER_KWH : float
    Facteur d'émission de l'électricité du runner.
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
ROTATION_SIZE = 1000
DATA_DIR = PROJECT_ROOT / "data"
LOG_DIR = PROJECT_ROOT / "logs"
SNAPSHOT_COMPRESSION = "zstd"

DATA_REPO = "AntoanetaStoyanova/cartograph-data"
COLLECT_WORKFLOW = "collect.yml"
PRICES_REPO = "AntoanetaStoyanova/cartograph-prices"
# `linux_4_core`, 2026-11-15 :
# docs.github.com/en/billing/reference/actions-runner-pricing
ACTIONS_USD_PER_MIN = 0.012
RUNNER_VCPUS = 4
RUNNER_MEMORY_GB = 16
# Cloud Carbon Footprint (cloudcarbonfootprint.org/docs/methodology, 2026-11-15) :
# moyenne Azure 0,78 à 3,76 W par vCPU, 50 % d'utilisation faute de mesure,
# 0,392 W par Go de mémoire, PUE 1,185 ; région du runner inconnue, East US retenue.
_CCF_MIN_W, _CCF_MAX_W, _CCF_UTILISATION = 0.78, 3.76, 0.5
_CCF_MEMORY_W_PER_GB, _CCF_PUE = 0.392, 1.185
RUNNER_WATTS = _CCF_PUE * (
    RUNNER_VCPUS * (_CCF_MIN_W + _CCF_UTILISATION * (_CCF_MAX_W - _CCF_MIN_W))
    + RUNNER_MEMORY_GB * _CCF_MEMORY_W_PER_GB
)
GRID_KG_CO2E_PER_KWH = 0.379069
