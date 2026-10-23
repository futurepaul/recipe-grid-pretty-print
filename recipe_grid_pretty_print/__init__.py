"""
recipe-grid-pretty-print
========================

Render `recipe grid <https://github.com/mossblaser/recipe_grid>`_ recipe
sources as beautiful, print-ready HTML tables in the style of
`recipetables.com <https://recipetables.com/how-it-works>`_.

Typical usage::

    from recipe_grid_pretty_print import render_file

    html = render_file("my_recipe.md")
"""

from recipe_grid_pretty_print.document import (
    render_source,
    render_file,
)

__version__ = "0.1.0"

__all__ = ["render_source", "render_file"]
