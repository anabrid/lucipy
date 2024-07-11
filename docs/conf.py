# File highly inspired by
# https://github.com/anabrid/pyanalog/blob/master/doc/conf.py


# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'lucipy'
copyright = '2024, Anabrid GmbH'
author = 'Anabrid GmbH'

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import sys, os
sys.path.insert(0, os.path.abspath('..'))


# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
   'sphinx.ext.autodoc',
   'sphinx.ext.viewcode',
   'sphinx.ext.autosummary',
   'sphinx.ext.mathjax',
   
    # nbsphinx
]

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

autodoc_member_order = "bysource"


# Solves "Sphinx Error contents.rst not found" on some systems, see
# https://stackoverflow.com/a/56448499
#master_doc = "index"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

#html_theme = 'alabaster' # = default
html_theme = 'sphinx_rtd_theme' # Read the docs theme, nicer.

html_static_path = ['_static']


# -- Options for nbsphinx input --------------------------------------------------

nbsphinx_execute = 'never'  # we expect all notebooks to have output stored

# Otherwise we could do this:
#nbsphinx_execute_arguments = [
#    "--InlineBackend.figure_formats={'svg', 'pdf'}",
#    "--InlineBackend.rc={'figure.dpi': 96}",
#]
