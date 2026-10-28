"""
Boucle de collecte commune au catalogue et aux prix.
"""

import logging
from collections.abc import Callable, Sequence
from typing import Any

from cartograph.bin.collect import FetchResult
from cartograph.bin.collect.client import CardNotFoundError, TcgdexClient, TcgdexError
from cartograph.config import MAX_CONSECUTIVE_FAILURES, PROGRESS_EVERY

logger = logging.getLogger(__name__)


def fetch_each[K](
    client: TcgdexClient,
    keys: Sequence[K],
    path: Callable[[K], str],
    build: Callable[[K, Any], dict[str, Any]],
    card_id: Callable[[K], str],
    label: str,
) -> FetchResult:
    """
    Appelle l'API pour chaque clé et poursuit malgré les cartes en échec.

    Parameters
    ----------
    client : TcgdexClient
        Client de l'API.
    keys : Sequence[K]
        Éléments à récupérer, un appel chacun.
    path : Callable[[K], str]
        Chemin de l'appel pour une clé.
    build : Callable[[K, Any], dict[str, Any]]
        Enregistrement à garder à partir de la clé et de la réponse JSON.
    card_id : Callable[[K], str]
        Identifiant de carte noté dans ``failed`` et dans les logs.
    label : str
        Nom de la collecte dans les logs, par exemple ``catalogue fr``.

    Returns
    -------
    FetchResult
        Enregistrements construits et identifiants en échec.

    Raises
    ------
    TcgdexError
        Après ``MAX_CONSECUTIVE_FAILURES`` cartes en ``TcgdexError`` d'affilée ;
        les ``CardNotFoundError`` ne comptent pas.
    """
    logger.info("%s : %d cartes à récupérer", label, len(keys))
    items: list[dict[str, Any]] = []
    failed: list[str] = []
    consecutive = 0
    for done, key in enumerate(keys, start=1):
        try:
            payload = client.get_json(path(key))
        except TcgdexError as error:
            failed.append(card_id(key))
            logger.warning("%s : %s en échec (%s)", label, card_id(key), error)
            if not isinstance(error, CardNotFoundError):
                consecutive += 1
            if consecutive >= MAX_CONSECUTIVE_FAILURES:
                logger.error("%s : arrêt après %d échecs d'affilée", label, consecutive)
                raise TcgdexError(
                    f"{label} : arrêt après {consecutive} échecs d'affilée"
                ) from error
        else:
            items.append(build(key, payload))
            consecutive = 0
        if done % PROGRESS_EVERY == 0:
            logger.info("%s : %d / %d cartes traitées", label, done, len(keys))
    logger.info("%s : %d récupérées, %d en échec", label, len(items), len(failed))
    return FetchResult(items=items, failed=failed)
