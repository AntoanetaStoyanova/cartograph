"""
Point d'entrée de ``python -m cartograph``.
"""

from pathlib import Path

from cartograph.config import LANGUAGES
from cartograph.log import setup_logging

PROJECT_NAME = "cartograph"
PROJECT_DIR = Path(__file__).resolve().parent


def get_chemin(dossier: str) -> Path:
    """
    Construit le chemin absolu d'un dossier du paquet ``cartograph``.

    Parameters
    ----------
    dossier : str
        Nom ou chemin relatif du dossier, depuis ``src/cartograph/``.

    Returns
    -------
    Path
        Chemin absolu vers le dossier demandé.
    """
    return PROJECT_DIR / dossier


def main() -> None:
    """
    Journalise le démarrage et les langues configurées.

    Les logs vont sur stderr et dans
    ``src/cartograph/log/cartograph_<AAAAMMJJ_HHMMSS>.log``.
    """
    path_log = get_chemin("log")
    logger = setup_logging(PROJECT_NAME, log_dir=path_log)
    logger.info("Démarrage de %s", PROJECT_NAME)
    logger.info("Dossier des logs : %s", path_log)
    logger.info("Langues : %s", ", ".join(LANGUAGES))


if __name__ == "__main__":
    main()
