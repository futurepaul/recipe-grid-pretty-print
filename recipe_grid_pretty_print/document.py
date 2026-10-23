"""
Document generation
===================

Compiles a recipe grid markdown file into a single, standalone, print-ready
HTML document with all styles inlined.
"""

from typing import Optional, Union

import html

from fractions import Fraction

from pathlib import Path

from recipe_grid.markdown import compile_markdown, MarkdownRecipe

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid_pretty_print.renderer import (
    t,
    render_number,
    render_recipe,
)

from recipe_grid_pretty_print.style import build_css

from recipe_grid_pretty_print.pagination import pagination_script


def _render_scaled_value_string(string: SVS) -> str:
    return string.render(
        format_number=lambda number: t(
            "span", render_number(number), class_="rgp-scaled-value"
        ),
    )


def render_recipe_markdown(
    recipe: MarkdownRecipe,
    scale: Union[int, float, Fraction] = 1,
    id_prefix_seed: int = 0,
) -> str:
    """
    Render the compiled HTML of a :py:class:`~recipe_grid.markdown.MarkdownRecipe`
    with all placeholders substituted for scaled values and pretty-printed
    recipe tables.
    """
    html = recipe.html

    # Substitute scaled value strings (e.g. in the title and prose)
    for placeholder, svs in recipe.scaled_value_strings.items():
        html = html.replace(placeholder, _render_scaled_value_string(svs.scale(scale)))

    # Substitute recipe tables
    id_prefix_index = 0
    for placeholder, recipe_block in recipe.recipe_placeholders.items():
        if recipe_block.follows is None:
            id_prefix_index += 1

        if id_prefix_index > 1:
            id_prefix = f"recipe{id_prefix_index + id_prefix_seed}-"
        else:
            id_prefix = f"recipe{id_prefix_seed + 1}-"

        html = html.replace(
            placeholder,
            render_recipe(recipe_block.scale(scale), id_prefix),
        )

    # Wrap the title in a header element, adding a scaling note if needed
    if (
        recipe.title is not None
        and recipe.pre_title_placeholder is not None
        and recipe.post_title_placeholder is not None
    ):
        html = html.replace(recipe.pre_title_placeholder, "<header>")
        post_title_text = ""
        if scale != 1:
            if recipe.servings is not None:
                orig_servings = t(
                    "span",
                    f"{recipe.servings} serving{'s' if recipe.servings != 1 else ''}",
                    class_="rg-original-servings",
                )
                post_title_text = t(
                    "p", f"Rescaled from {orig_servings}.", class_="rgp-scaling-note"
                )
            else:
                scale_str = t(
                    "span",
                    f"{render_number(scale)}&times;",
                    class_="rg-scaling-factor",
                )
                post_title_text = t(
                    "p", f"Scaled {scale_str}", class_="rgp-scaling-note"
                )
        html = html.replace(
            recipe.post_title_placeholder, f"{post_title_text}</header>"
        )

    return html


def generate_document(
    markdown_source: str,
    scale: Optional[Union[int, float, Fraction]] = None,
    servings: Optional[int] = None,
    paper: str = "a4",
    orientation: str = "portrait",
    accent: Optional[str] = None,
    title_fallback: str = "Recipe",
    include_toolbar: bool = True,
    paginate: bool = True,
) -> str:
    """
    Generate a complete, standalone, print-ready HTML document from recipe
    grid markdown source.

    Parameters
    ==========
    markdown_source:
        The complete markdown source of the recipe.
    scale:
        An optional multiplier to scale all quantities by (e.g. ``2`` or
        ``Fraction(1, 2)``). Must not be given alongside ``servings``.
    servings:
        Scale the recipe to this number of servings. Requires the recipe to
        declare its number of servings in its title (e.g. ``... for 4``).
    paper:
        Paper size the document is tuned for: ``a4`` or ``letter``.
    orientation:
        ``portrait`` or ``landscape``.
    accent:
        Optional CSS colour to use for step cells (defaults to the warm
        peach of the standard theme).
    title_fallback:
        Document title used when the recipe has no title.
    include_toolbar:
        Include the on-screen floating "Print" toolbar (hidden when
        printing).
    paginate:
        Embed the deterministic pagination script, which computes exactly
        where pages will break and forces breaks between whole table cells
        so no cell ever straddles two pages. Requires JavaScript; when
        disabled, a CSS-only fallback is used.
    """
    if scale is not None and servings is not None:
        raise ValueError("Only one of 'scale' and 'servings' may be given.")

    recipe = compile_markdown(markdown_source)

    if scale is None and servings is not None:
        if recipe.servings is None:
            raise ValueError(
                "Cannot scale to a number of servings: the recipe's title "
                "does not state how many servings it makes (e.g. '... for 4')."
            )
        scale = Fraction(servings, recipe.servings)
    elif scale is None:
        scale = 1

    body = render_recipe_markdown(recipe, scale)

    css = build_css(paper=paper, orientation=orientation, accent=accent)

    toolbar = ""
    if include_toolbar:
        toolbar = t(
            "div",
            t("span", "Print-ready &mdash; enable &ldquo;Background graphics&rdquo; for full colour")
            + t("button", "Print", onclick="window.print()", type_="button"),
            class_="rgp-toolbar",
        )

    title = recipe.title if recipe.title is not None else title_fallback
    script = pagination_script() if paginate else ""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)}</title>
<style>
{css}
</style>
</head>
<body>
{toolbar}
<main class="rgp-sheet">
<article class="rgp-doc">
{body}
</article>
</main>
{script}
</body>
</html>
"""


def render_source(
    markdown_source: str,
    **kwargs,
) -> str:
    """
    Render recipe grid markdown source (a string) into a standalone,
    print-ready HTML document. See :py:func:`generate_document` for the
    available options.
    """
    return generate_document(markdown_source, **kwargs)


def render_file(
    input_file: Union[str, Path],
    **kwargs,
) -> str:
    """
    Render a recipe grid markdown file into a standalone, print-ready HTML
    document. See :py:func:`generate_document` for the available options.
    """
    with Path(input_file).open("r") as f:
        markdown_source = f.read()
    return generate_document(markdown_source, **kwargs)
