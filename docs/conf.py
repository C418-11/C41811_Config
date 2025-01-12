# -*- coding: utf-8 -*-
# Configuration file for the Sphinx documentation builder.


from setuptools_scm import get_version

project = "C41811.Config"
# noinspection PyShadowingBuiltins
copyright = "2024, C418____11"
author = "C418____11"
release = get_version(
    fallback_version="0.0+UNKNOWN",
    search_parent_directories=True
)

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# noinspection SpellCheckingInspection
extensions = [
    "sphinx.ext.autodoc",
    "sphinx_copybutton",
]

templates_path = ["_templates"]
exclude_patterns = []

language = "zh_CN"

python_display_short_literal_types = True
add_module_names = False

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "furo"
html_static_path = ["_static"]
html_css_files = [
    "pygments_darcula.css",
]
html_short_title = "C41811.Config"
html_favicon = "./_static/favicon.png"

# -- AutoAPI Configuration ---------------------------------------------------
# https://sphinx-autoapi.readthedocs.io/en/latest/reference/config.html
extensions.append("autoapi.extension")

autoapi_dirs = ["../src/"]
autoapi_member_order = "groupwise"
autoapi_python_class_content = "both"
# noinspection SpellCheckingInspection
autoapi_options = [
    "members",
    "inherited-members",
    "undoc-members",
    "private-members",
    "special-members",
    "show-inheritance",
    "show-module-summary",
    "imported-members",
]
