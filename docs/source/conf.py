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
html_short_title = 'Juturna documentation'

html_static_path = ['_static']

# custom css content (relative to _static path)
html_css_files = [
    'css/style.css',
    "https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/css/all.min.css"
    # 'css/fa-6.7.2.all.min.css'
]

html_js_files = [
    'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.1.1/js/all.min.js',
    'js/meetecho-icon.js'
]

html_theme_options = {
    'banner_text': 'We just released version 1.0.1 - go check it out!',
    'banner_hiding': 'permanent',
    'globaltoc_collapse': False,
    'source_url': 'https://github.com/meetecho/juturna'

}

rst_prolog = f"""
.. |version-badge| replace:: :bdg-secondary-line:`version {version}-{release}`
"""

# html_sidebars = {
#     '**': ['sidebar-nav-bs.html', 'searchbox.html'],
# }
