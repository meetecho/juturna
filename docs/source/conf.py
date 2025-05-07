import os
import sys


sys.path.insert(0, os.path.abspath('../../juturna'))

project = 'juturna'
copyright = '2025, Antonio Bevilacqua'
author = 'Antonio Bevilacqua'
release = '0.1.0'

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.doctest',
    'sphinx_design',
    'sphinx_new_tab_link'
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# open external links in blank targets
new_tab_link_show_external_link_icon = True

html_theme = 'pydata_sphinx_theme'
html_static_path = ['_static']

# custom css content (relative to _static path)
html_css_files = [
    './css/style.css',
    './css/fa-6.7.2.all.min.css'
]

html_theme_options = {
    "github_url": "https://github.com/b3by/juturna",
    "collapse_navigation": True
}
