"""Configuration Sphinx pour cartograph."""

import importlib.metadata

project = "cartograph"
author = "Antoaneta Stoyanova"
release = importlib.metadata.version("cartograph")

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
]

html_theme = "furo"
