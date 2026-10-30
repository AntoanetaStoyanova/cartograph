"""
Client HTTP de l'API TCGdex.

Ce module :
- fournit un client HTTP robuste pour interroger l'API TCGdex
  (API publique de cartes Pokémon) ;
- centralise :
    - la pause entre les requêtes ;
    - les nouvelles tentatives en cas d'erreur temporaire ;
    - la gestion propre des erreurs.
"""

import logging
import time
from collections.abc import Callable
from types import TracebackType
from typing import Any, Self

import httpx

from cartograph.config import (
    MAX_RETRIES,
    MAX_RETRY_AFTER_S,
    REQUEST_PAUSE_S,
    REQUEST_TIMEOUT_S,
    RETRY_BACKOFF_S,
    RETRY_STATUSES,
    TCGDEX_BASE_URL,
    TCGDEX_USER_AGENT,
)

logger = logging.getLogger(__name__)

# ========  Les Exceptions ========
# deux niveaux d'erreur, en héritage:
# - TcgdexError: erreur générique
# - NotFoundError: cas particulier du 404 (carte ou liste)
# L'appelant peut faire except NotFoundError pour traiter specifiquement
# "la ressource n'existe pas", ou except TcgdexError attraper d'un coup grâce à
# l'héritage


class TcgdexError(Exception):
    """Erreur définitive d'un appel à l'API TCGdex."""


class NotFoundError(TcgdexError):
    """Ressource absente de l'API (réponse 404)."""


class TcgdexClient:
    """
    Client synchrone de l'API TCGdex, avec pause et nouvelles tentatives.

    S'utilise comme gestionnaire de contexte pour fermer la connexion HTTP.

    Examples
    --------
    >>> transport = httpx.MockTransport(lambda request: httpx.Response(200, json=[]))
    >>> with TcgdexClient(transport=transport) as client:
    ...     client.get_json("/fr/cards")
    []
    """

    # mémorise les paramètres dans l'objet et construit le client HTTP, réutilisé
    # pour toutes les requêtes (en-têtes, délai et connexion partagés)
    def __init__(
        self,
        base_url: str = TCGDEX_BASE_URL,
        pause: float = REQUEST_PAUSE_S,
        max_retries: int = MAX_RETRIES,
        backoff: float = RETRY_BACKOFF_S,
        timeout: float = REQUEST_TIMEOUT_S,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        """
        Prépare le client HTTP ; aucune requête n'est envoyée.

        Parameters
        ----------
        base_url : str, optional
            Racine de l'API, par défaut ``TCGDEX_BASE_URL``.
        pause : float, optional
            Pause en secondes avant chaque requête sauf la première, par défaut
            ``REQUEST_PAUSE_S``.
        max_retries : int, optional
            Nombre de nouvelles tentatives après une erreur temporaire, par
            défaut ``MAX_RETRIES``.
        backoff : float, optional
            Attente en secondes avant la première nouvelle tentative, doublée à
            chaque suivante, par défaut ``RETRY_BACKOFF_S``.
        timeout : float, optional
            Délai d'attente d'une requête en secondes, par défaut
            ``REQUEST_TIMEOUT_S``.
        transport : httpx.BaseTransport | None, optional
            Transport HTTP, remplacé en test par ``httpx.MockTransport`` ;
            transport réseau de ``httpx`` si ``None``.
        sleep : Callable[[float], None], optional
            Fonction d'attente, par défaut ``time.sleep`` ; injectée en test.
        """
        self._pause = pause
        self._max_retries = max_retries
        self._backoff = backoff
        self._sleep = sleep
        self._has_requested = False
        self._client = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": TCGDEX_USER_AGENT},
            timeout=timeout,
            transport=transport,
            follow_redirects=True,
        )

    # l'utilisation:
    # with TcgdexClient() as client:
    #     client.get_json("/fr/cards")
    #     print("fini")
    # L'objet existe, le client HTTP est prêt, mais personne ne l'a encore reçu.
    # with déclenche l'appel automatiquement :
    # la valeur renvoyée va dans client et le bloc suivant s'exécute.
    # dès que le bloc se termine, python appelle __exit__ qui lance le self.close()
    # et ferme la connexion
    # exemple de schéma de la chronologie:
    # with TcgdexClient() as client:
    #      │
    #      ├─ 1. __init__   → l'objet est créé
    #      ├─ 2. __enter__  → renvoie l'objet  ──► rangé dans "client"
    #      ├─ 3. ton bloc   → client.get_json(...)
    #      └─ 4. __exit__   → ferme la connexion
    # Sans le with, je dois penser à fermer la connexion.
    def __enter__(self) -> Self:
        """
        Renvoie le client pour un bloc ``with``.

        Returns
        -------
        Self
            Le client lui-même.
        """
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        """
        Ferme la connexion HTTP en sortie de bloc ``with``.

        L'exception éventuelle n'est pas interceptée.

        Parameters
        ----------
        exc_type : type[BaseException] | None
            Type de l'exception levée dans le bloc, ``None`` sinon.
        exc_value : BaseException | None
            Exception levée dans le bloc, ``None`` sinon.
        traceback : TracebackType | None
            Trace de l'exception, ``None`` sinon.
        """
        self.close()

    def close(self) -> None:
        """Ferme la connexion HTTP."""
        self._client.close()

    # Cherche une page de l'API ; si ça échoue, get_json réessaie avant d'abandonner.
    # Si ça marche, la fonction rend les données JSON.
    def get_json(self, path: str) -> Any:
        """
        Renvoie la réponse JSON de ``GET path``.

        Pause de ``pause`` secondes avant l'appel, sauf au premier ; nouvelles
        tentatives sur les codes de ``RETRY_STATUSES`` et les erreurs réseau.

        Parameters
        ----------
        path : str
            Chemin relatif à la racine de l'API, par exemple ``/fr/cards``.

        Returns
        -------
        Any
            Réponse JSON décodée.

        Raises
        ------
        NotFoundError
            Si l'API répond 404, y compris pour une liste (``/fr/cards``) si
            ``base_url`` est fausse.
        TcgdexError
            Sur une autre erreur 4xx, une réponse qui n'est pas du JSON, ou une
            fois les tentatives épuisées.
        """
        # On évite de "harceler" l'API de requêtes avec une pause :
        # avant chaque requête, on attend quelques dixièmes de seconde.
        if self._has_requested:
            self._sleep(self._pause)
        self._has_requested = True

        for attempt in range(self._max_retries + 1):
            # à chaque tentative, la requête est envoyée
            try:
                response = self._client.get(path)
            # la requête n'a pas réussi
            # problème de réseau > raison > calcul de l'attente avant de réessayer
            except httpx.TransportError as error:
                reason = f"erreur réseau {type(error).__name__}"
                delay = self._backoff * 2**attempt
            # on reçoit une réponse du serveur
            else:
                # la ressource n'existe pas
                if response.status_code == 404:
                    raise NotFoundError(f"{path} introuvable (404)")
                # erreur définitive (400, 403…) ; sinon on renvoie le JSON
                if response.status_code not in RETRY_STATUSES:
                    if response.is_error:
                        raise TcgdexError(f"{path} : HTTP {response.status_code}")
                    # une page HTML d'erreur avec un code 200 ne doit pas faire
                    # planter toute la collecte : on la traite comme un échec
                    try:
                        return response.json()
                    except ValueError as error:
                        raise TcgdexError(f"{path} : réponse non JSON") from error
                # erreur temporaire : on note la raison et on calcule le délai,
                # celui du serveur (Retry-After) s'il en donne un, sinon
                # l'attente exponentielle
                reason = f"HTTP {response.status_code}"
                delay = _retry_after(response) or self._backoff * 2**attempt

            # on décide de réessayer ou d'abandonner
            # (erreur temporaire : réseau ou code de RETRY_STATUSES)
            if attempt == self._max_retries:
                break
            logger.warning(
                "%s sur %s, nouvelle tentative dans %.1f s", reason, path, delay
            )
            self._sleep(delay)

        raise TcgdexError(f"{path} : {reason} après {self._max_retries + 1} tentatives")


def _retry_after(response: httpx.Response) -> float | None:
    """
    Lit l'attente demandée par l'en-tête ``Retry-After``, plafonnée à
    ``MAX_RETRY_AFTER_S``.

    Parameters
    ----------
    response : httpx.Response
        Réponse 429 ou 5xx de l'API.

    Returns
    -------
    float | None
        Attente en secondes, ``None`` si l'en-tête est absent ou n'est pas un
        nombre (format date HTTP).
    """
    try:
        return min(float(response.headers["Retry-After"]), MAX_RETRY_AFTER_S)
    except (KeyError, ValueError):
        return None
