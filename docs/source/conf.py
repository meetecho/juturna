project = 'juturna'
copyright = '2025, Meetecho'
author = 'Antonio Bevilacqua'
version = '1.0.1'
release = 'beta'

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

# theme configuration

html_theme = 'piccolo_theme'
html_title = 'Juturna documentation page'
html_short_title = 'Juturna docs'
html_favicon = '_static/img/logo_dark.svg'

show_authors = True
html_show_copyright = True

# pygments_style = "one-dark"
# pygments_dark_style = "one-dark"

html_static_path = ['_static']

html_css_files = [
    'css/style.css',
    'css/fa-6.7.2.all.min.css'
]

html_js_files = [
    'js/fa-6.7.2.all.min.js',
    'js/meetecho-icon.js'
]

html_theme_options = {
    'banner_text': 'We just released version 1.0.1 - go check it out!',
    'banner_hiding': 'permanent',
    'globaltoc_collapse': False,
    'source_url': 'https://github.com/meetecho/juturna',
    # "dark_mode_code_blocks": False,
}

rst_prolog = f"""
.. |version-badge| replace:: :bdg-secondary-line:`version {version}-{release}`
"""
