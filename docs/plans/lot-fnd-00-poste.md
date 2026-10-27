# Plan — FND-00 Poste de travail

*Rédigé le : 27 octobre 2026*
*Référence : [roadmap-lots.md](roadmap-lots.md) (lot sans code, pas de spec dédiée)*

## Objectif

Un PC prêt à développer sous WSL : Ubuntu, Git, accès GitHub par SSH, uv et VS Code connecté à WSL.

## Mode de travail

**Exécuté par Antoaneta, pour apprendre.** Pour chaque point, Claude donne la commande, explique ce qu'elle fait et le résultat attendu. Antoaneta la lance elle-même dans le terminal, puis colle la sortie (ou la lance avec `! <commande>`) pour que Claude vérifie avant de passer au point suivant. Claude n'exécute aucun de ces points à sa place.

## Pourquoi WSL

- **Même système que la CI** : GitHub Actions tourne sur des machines Ubuntu. Développer sous Linux évite les écarts entre le PC et la CI (chemins, fins de ligne, paquets compilés).
- **Outils pensés pour Linux** : dbt, DuckDB, OpenCV et les scripts shell des workflows s'y installent et s'y documentent d'abord.
- **Un seul environnement** : un `.venv` ne sert qu'à un système. Le `.venv` actuel, créé sous Windows (`Scripts/`), est inutilisable depuis WSL.
- **Windows reste l'interface** : VS Code tourne sous Windows et se connecte à WSL ; les fichiers restent visibles dans l'explorateur Windows.
- **Emplacement** : le projet reste dans `/mnt/c/Users/antoa/programme/cartograph` (convention des projets). Les accès disque y sont plus lents que dans `~/` ; si `uv sync` ou les tests deviennent pénibles, déplacer le projet dans `~/programme/`.

## Étapes

- [x] 1. **WSL et Ubuntu** : dans PowerShell, `wsl --install -d Ubuntu` si ce n'est pas déjà fait, puis `wsl --update`. Vérifier avec `wsl -l -v` (version 2).
- [x] 2. **Paquets de base** dans Ubuntu : `sudo apt update && sudo apt install -y git curl build-essential`.
- [x] 3. **Git** dans Ubuntu : `git config --global user.name "Antoaneta Stoyanova"`, `git config --global user.email <email>`, et `git config --global core.autocrlf input` pour garder des fins de ligne Linux.
- [x] 4. **Accès GitHub** : `ssh-keygen -t ed25519`, ajouter la clé publique dans GitHub (Settings → SSH keys), tester avec `ssh -T git@github.com`.
- [x] 5. **uv** : `curl -LsSf https://astral.sh/uv/install.sh | sh`, rouvrir le terminal, vérifier `uv --version`. uv installe lui-même Python 3.13 (`.python-version`).
- [x] 6. **VS Code** : installer l'extension « WSL » (Microsoft) sous Windows, puis, dans Ubuntu, `cd /mnt/c/Users/antoa/programme/cartograph && code .`. La barre d'état doit afficher « WSL: Ubuntu ». Installer les extensions Python et Ruff dans cette fenêtre (elles s'installent côté WSL).
- [x] 7. **Règle d'usage** : toutes les commandes du projet (`uv`, `inv`, `git`, `dbt`) se lancent dans le terminal WSL, jamais dans PowerShell, pour ne pas recréer un `.venv` Windows.

Le choix de l'interpréteur `.venv/bin/python` dans VS Code se fait dans FND-01, une fois le `.venv` recréé.

## Critères de fin

- [x] `wsl -l -v` affiche Ubuntu en version 2.
- [x] `uv --version` répond dans le terminal WSL.
- [x] `git config --global --list` contient le nom, l'e-mail et `core.autocrlf=input`.
- [x] `ssh -T git@github.com` répond « successfully authenticated ».
- [x] VS Code ouvert sur le projet affiche « WSL: Ubuntu ».
- [x] FND-00 coché dans `docs/plans/roadmap-lots.md`.
