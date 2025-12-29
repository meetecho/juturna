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
    'sphinx_new_tab_link',
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# open external links in blank targets
new_tab_link_show_external_link_icon = True

# theme configuration
html_theme = 'furo'
html_title = 'Juturna'
html_short_title = 'Juturna docs'
html_favicon = '_static/img/logo_dark.svg'

show_authors = True
html_show_copyright = True

pygments_style = 'solarized-light'
pygments_dark_style = 'nord-darker'

html_static_path = ['_static']

html_css_files = ['css/meetecho_style.css', 'css/fa-6.7.2.all.min.css']

html_js_files = ['js/fa-6.7.2.all.min.js', 'js/meetecho-icon.js']

html_theme_options = {
    'globaltoc_collapse': False,
    'light_logo': 'img/logo_light_alt.svg',
    'dark_logo': 'img/logo_dark_alt.svg',
    'footer_icons': [
        {
            'name': 'GitHub',
            'url': 'https://github.com/meetecho/juturna',
            'html': '',
            'class': 'fa-brands fa-solid fa-github fa-2x',
        },
        {
            'name': 'MeetEcho',
            'url': 'https://meetecho.com',
            'html': """
                <svg stroke="currentColor" fill="currentColor" stroke-width="0" viewBox="0 0 24 24">
                    <path fill-rule="evenodd" d="M4.44,15.54 C4.44,15.54 4.44,21.60 4.44,21.60 4.44,21.60 6.42,21.60 6.42,21.60 6.42,21.60 8.40,21.60 8.40,21.60 8.40,21.60 8.42,18.44 8.42,18.44 8.46,15.54 8.47,15.30 8.66,15.34 8.87,15.37 11.22,16.72 11.70,17.08 11.92,17.24 11.99,17.22 12.60,16.80 13.34,16.30 15.17,15.24 15.28,15.24 15.32,15.24 15.36,16.67 15.36,18.42 15.36,18.42 15.36,21.60 15.36,21.60 15.36,21.60 17.34,21.60 17.34,21.60 17.34,21.60 19.32,21.60 19.32,21.60 19.32,21.60 19.32,15.54 19.32,15.54 19.32,15.54 19.32,9.48 19.32,9.48 19.32,9.48 17.34,9.48 17.34,9.48 17.34,9.48 15.36,9.48 15.36,9.48 15.36,9.48 15.36,10.18 15.36,10.18 15.36,10.18 15.36,10.88 15.36,10.88 15.36,10.88 13.63,12.04 13.63,12.04 13.63,12.04 11.92,13.18 11.92,13.18 11.92,13.18 10.16,12.02 10.16,12.02 10.16,12.02 8.41,10.86 8.41,10.86 8.41,10.86 8.40,10.16 8.40,10.16 8.40,10.16 8.40,9.48 8.40,9.48 8.40,9.48 6.42,9.48 6.42,9.48 6.42,9.48 4.44,9.48 4.44,9.48 4.44,9.48 4.44,15.54 4.44,15.54 Z M16.25,2.81 C15.20,3.26 14.52,4.32 14.52,5.46 14.52,6.26 14.71,6.76 15.25,7.38 15.79,7.98 16.45,8.28 17.32,8.28 18.49,8.28 19.45,7.68 19.93,6.66 20.22,6.02 20.23,4.90 19.93,4.26 19.69,3.71 18.98,3.05 18.41,2.81 17.90,2.59 16.74,2.60 16.25,2.81 Z M5.15,2.99 C3.12,4.07 3.11,6.89 5.15,7.94 7.60,9.22 10.25,6.65 9.01,4.21 8.26,2.75 6.59,2.22 5.15,2.99Z"></path>
                </svg>
            """,
            'class': '',
        },
    ],
}

rst_prolog = f"""
.. |version-badge| replace:: :bdg-secondary-line:`version {version}-{release}`
"""
