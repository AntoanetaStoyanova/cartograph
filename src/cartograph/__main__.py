"""
Point d'entrée de ``python -m cartograph``.
"""

from cartograph.config import LANGUAGES, LOG_DIR
from cartograph.log import setup_logging

PROJECT_NAME = "cartograph"


def main() -> None:
    """
    Journalise le démarrage et les langues configurées.

    Les logs vont sur stderr et dans
    ``logs/cartograph_<AAAAMMJJ_HHMMSS>.log`` à la racine du dépôt.
    """
    logger = setup_logging(PROJECT_NAME, log_dir=LOG_DIR)
    logger.info("Démarrage de %s", PROJECT_NAME)
    logger.info("Dossier des logs : %s", LOG_DIR)
    logger.info("Langues : %s", ", ".join(LANGUAGES))


if __name__ == "__main__":
    main()
