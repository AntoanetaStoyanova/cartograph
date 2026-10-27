"""
Configuration des logs du projet.
"""

import logging
import sys
from datetime import datetime
from pathlib import Path


def setup_logging(
    name: str,
    log_dir: Path | None = None,
    level: int = logging.INFO,
    max_files: int = 10,
) -> logging.Logger:
    """
    Configure et renvoie le logger ``name``.

    Les messages vont sur stderr pour laisser stdout aux sorties des commandes.
    Un appel sur un logger déjà configuré le renvoie sans ajouter de handler.

    Parameters
    ----------
    name : str
        Nom du logger, repris dans le nom du fichier de log.
    log_dir : Path | None
        Dossier du fichier de log horodaté ; aucun fichier si ``None``.
    level : int
        Niveau minimal des messages.
    max_files : int
        Nombre maximal de fichiers ``<name>_*.log`` gardés dans ``log_dir``,
        nouveau fichier compris ; les plus anciens sont supprimés.

    Returns
    -------
    logging.Logger
        Logger configuré.
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)
    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler(sys.stderr)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_dir is not None:
        log_dir.mkdir(parents=True, exist_ok=True)
        _prune_logs(log_dir, name, keep=max_files - 1)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_handler = logging.FileHandler(
            log_dir / f"{name}_{timestamp}.log", encoding="utf-8"
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


def _prune_logs(log_dir: Path, name: str, keep: int) -> None:
    """Supprime les plus anciens ``<name>_*.log`` pour n'en garder que ``keep``."""
    # L'horodatage AAAAMMJJ_HHMMSS rend l'ordre alphabétique chronologique.
    log_files = sorted(log_dir.glob(f"{name}_*.log"))
    for old_file in log_files[: max(len(log_files) - keep, 0)]:
        old_file.unlink()
