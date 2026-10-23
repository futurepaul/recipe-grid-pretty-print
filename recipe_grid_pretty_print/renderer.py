"""
HTML rendering of recipe trees as pretty, print-ready tables
============================================================

This module converts :py:class:`~recipe_grid.recipe.RecipeTreeNode` trees
into HTML tables styled in the manner of recipetables.com: ingredients run
down the left-hand column, steps occupy cells spanning the rows of their
inputs, and preparation steps with no ingredients appear as full-width rows
at the top of the table.

The tabular layout logic mirrors
:py:func:`recipe_grid.renderer.recipe_to_table.recipe_tree_to_table` from the
upstream library but omits the heavy border drawn around root nodes (only
visibly-named sub recipes are outlined) and hoists prep steps into full-width
rows.
"""

from typing import List, Optional, MutableMapping, cast

import re

import html

from xml.sax.saxutils import quoteattr

from recipe_grid.scaled_value_string import ScaledValueString as SVS

from recipe_grid.number_formatting import format_number

from recipe_grid.recipe import (
    Recipe,
    RecipeTreeNode,
    Ingredient,
    Reference,
    Step,
    SubRecipe,
    Quantity,
    Proportion,
)

from recipe_grid.renderer.table import (
    BorderType,
    Cell,
    Table,
    right_pad_table,
    combine_tables,
    set_border_around_table,
)


# ---------------------------------------------------------------------------
# Low level HTML generation
# ---------------------------------------------------------------------------

def t(tag: str, body: Optional[str] = None, **attrs: str) -> str:
    """
    A simple utility function for generating HTML tags. Trailing underscores
    in attribute names are trimmed and double underscores become hyphens.
    """
    attrs_str = " ".join(
        name.rstrip("_").replace("__", "-") + "=" + quoteattr(value)
        for name, value in attrs.items()
    )

    if body is None:
        return f"<{tag} {attrs_str}/>"
    else:
        return f"<{tag}{(' ' + attrs_str).rstrip()}>{body}</{tag}>"


def render_number(number: float) -> str:
    """Format a number (rendering fractions like ``1 1/2`` as plain text)."""
    return html.escape(format_number(number))


def render_scaled_value_string(string: SVS) -> str:
    return string.render(
        format_number=lambda number: t(
            "span", render_number(number), class_="rgp-scaled-value"
        ),
        format_string=html.escape,
    )


# ---------------------------------------------------------------------------
# Cell content rendering
# ---------------------------------------------------------------------------

def render_quantity(quantity: Quantity) -> str:
    """
    Render an ingredient quantity, e.g. ``1/4 cup``, as it appears at the
    start of an ingredient cell (the bold portion).
    """
    parts = render_number(quantity.value)
    if quantity.unit is not None:
        parts += html.escape(quantity.value_unit_spacing + quantity.unit)
    if quantity.preposition:
        parts += html.escape(quantity.preposition)
    return t("span", parts, class_="rgp-quantity")


def render_proportion(proportion: Proportion) -> str:
    if proportion.value is None:
        body = html.escape(
            cast(str, proportion.remainder_wording) + proportion.preposition
        )
        return t("span", body, class_="rgp-proportion-remainder")
    else:
        body = (
            render_number(
                proportion.value * 100 if proportion.percentage else proportion.value
            )
            + html.escape(proportion.preposition).replace("*", "&times;")
        )
        return t("span", body, class_="rgp-proportion")


def generate_subrecipe_output_id(
    sub_recipe: SubRecipe, output_index: int, prefix: str
) -> str:
    name = str(sub_recipe.output_names[output_index])
    return prefix + re.sub(r"[^a-zA-Z0-9._-]", "-", name).strip("-")


def render_reference(reference: Reference, id_prefix: str) -> str:
    amount: str
    if isinstance(reference.amount, Quantity):
        amount = render_quantity(reference.amount) + " "
    elif isinstance(reference.amount, Proportion):
        if reference.amount.value != 1.0:
            amount = render_proportion(reference.amount) + " "
        else:
            amount = ""
    else:
        raise NotImplementedError(type(reference.amount))

    name = render_scaled_value_string(
        reference.sub_recipe.output_names[reference.output_index]
    )

    return t(
        "a",
        amount + name,
        href="#"
        + generate_subrecipe_output_id(
            reference.sub_recipe, reference.output_index, id_prefix
        ),
    )


# ---------------------------------------------------------------------------
# Tree to table conversion
# ---------------------------------------------------------------------------

def recipe_tree_to_table(
    recipe_tree: RecipeTreeNode, highlight_root: bool = True
) -> Table[RecipeTreeNode]:
    """
    Convert a recipe tree into a :py:class:`~recipe_grid.renderer.table.Table`.
    When ``highlight_root`` is false, no emphasised outline is drawn around
    the resulting table (used for anonymous root steps so that only
    deliberately-named sub recipes stand out).
    """
    if isinstance(recipe_tree, (Ingredient, Reference)):
        table: Table[RecipeTreeNode] = Table([[Cell(recipe_tree)]])
        if highlight_root:
            return set_border_around_table(table, BorderType.sub_recipe)
        return table

    elif isinstance(recipe_tree, Step):
        input_tables = [
            recipe_tree_to_table(input_tree, highlight_root=False)
            for input_tree in recipe_tree.inputs
        ]

        # Pad all input tables to the same width and stack them up
        input_columns = max(table.columns for table in input_tables)
        input_tables = [right_pad_table(table, input_columns) for table in input_tables]
        combined_input_tables = combine_tables(input_tables, axis=0)

        # Add the step to the RHS of the inputs
        table = combine_tables(
            [
                combined_input_tables,
                Table.from_dict(
                    {
                        (0, 0): Cell(
                            recipe_tree, rows=combined_input_tables.rows
                        )
                    }
                ),
            ],
            axis=1,
        )

        if highlight_root:
            return set_border_around_table(table, BorderType.sub_recipe)
        return table

    elif isinstance(recipe_tree, SubRecipe):
        sub_tree_table = recipe_tree_to_table(recipe_tree.sub_tree, False)

        if len(recipe_tree.output_names) == 1:
            if recipe_tree.show_output_names:
                return set_border_around_table(
                    combine_tables(
                        [
                            Table.from_dict(
                                {
                                    (0, 0): Cell(
                                        cast(RecipeTreeNode, recipe_tree),
                                        columns=sub_tree_table.columns,
                                    ),
                                }
                            ),
                            sub_tree_table,
                        ],
                        axis=0,
                    ),
                    BorderType.sub_recipe,
                )
            else:
                # An output-name-hiding wrapper (e.g. around a single-input
                # step): only outline when this is the recipe root.
                if highlight_root:
                    return set_border_around_table(
                        sub_tree_table, BorderType.sub_recipe
                    )
                return sub_tree_table
        else:
            # Multiple outputs: render the output list out to the right of
            # the table, outside the grid.
            return combine_tables(
                [
                    set_border_around_table(sub_tree_table, BorderType.sub_recipe),
                    Table.from_dict(
                        {
                            (0, 0): Cell(
                                cast(RecipeTreeNode, recipe_tree),
                                rows=sub_tree_table.rows,
                                border_top=BorderType.none,
                                border_right=BorderType.none,
                                border_bottom=BorderType.none,
                            ),
                        }
                    ),
                ],
                axis=1,
            )
    else:
        raise NotImplementedError(type(recipe_tree))


# ---------------------------------------------------------------------------
# Table to HTML
# ---------------------------------------------------------------------------

def render_cell(cell: Cell[RecipeTreeNode], id_prefix: str) -> str:
    spans: MutableMapping[str, str] = {}
    if cell.columns != 1:
        spans["colspan"] = str(cell.columns)
    if cell.rows != 1:
        spans["rowspan"] = str(cell.rows)

    class_names: List[str] = []

    body: str
    if isinstance(cell.value, Ingredient):
        class_names.append("rgp-ingredient")
        quantity = (
            render_quantity(cell.value.quantity) + " "
            if cell.value.quantity is not None
            else ""
        )
        body = quantity + render_scaled_value_string(cell.value.description)
    elif isinstance(cell.value, Reference):
        class_names.append("rgp-reference")
        body = render_reference(cell.value, id_prefix)
    elif isinstance(cell.value, Step):
        class_names.append("rgp-step")
        body = render_scaled_value_string(cell.value.description)
    elif isinstance(cell.value, SubRecipe):
        if len(cell.value.output_names) == 1:
            class_names.append("rgp-sub-recipe-header")
            body = render_scaled_value_string(cell.value.output_names[0])
            spans["id"] = generate_subrecipe_output_id(cell.value, 0, id_prefix)
        else:
            class_names.append("rgp-sub-recipe-outputs")
            body = t(
                "ul",
                "\n".join(
                    t(
                        "li",
                        render_scaled_value_string(name),
                        id=generate_subrecipe_output_id(cell.value, index, id_prefix),
                    )
                    for index, name in enumerate(cell.value.output_names)
                ),
                class_="rgp-sub-recipe-output-list",
            )

    for edge in ["top", "bottom", "left", "right"]:
        border_type = getattr(cell, f"border_{edge}")
        if border_type == BorderType.none:
            class_names.append(f"rgp-border-{edge}-none")
        elif border_type == BorderType.sub_recipe:
            class_names.append(f"rgp-border-{edge}-thick")

    return t("td", body, class_=" ".join(class_names), **spans)


def render_prep_row(prep_step: Step, columns: int) -> str:
    return t(
        "tr",
        t(
            "td",
            t("span", "prep", class_="rgp-prep-label")
            + t("span", render_scaled_value_string(prep_step.description), class_="rgp-prep-text"),
            class_="rgp-prep",
            colspan=str(columns),
        ),
        class_="rgp-prep-row",
    )


def render_table(
    table: Table[RecipeTreeNode],
    prep_steps: List[Step] = [],
    id: Optional[str] = None,
    id_prefix: str = "sub-recipe-",
) -> str:
    """
    Render a recipe table (and any prep steps belonging to its recipe) as a
    ``<table class="rgp">`` element.
    """
    rows = []

    for prep_step in prep_steps:
        rows.append(render_prep_row(prep_step, table.columns))

    for row_cells in table.cells:
        # A sub-recipe header must never be separated from the rows which
        # follow it when the table is split across pages.
        row_classes = []
        if any(
            isinstance(cell, Cell)
            and isinstance(cell.value, SubRecipe)
            and len(cell.value.output_names) == 1
            for cell in row_cells
        ):
            row_classes.append("rgp-header-row")
        rows.append(
            t(
                "tr",
                "\n".join(
                    render_cell(cell, id_prefix)
                    for cell in row_cells
                    if isinstance(cell, Cell)
                ),
                **({"class": " ".join(row_classes)} if row_classes else {}),
            )
        )

    return t(
        "table",
        "\n".join(rows),
        class_="rgp",
        **({"id": id} if id is not None else {}),
    )


def render_recipe_tree(
    recipe_tree: RecipeTreeNode,
    prep_steps: List[Step] = [],
    id_prefix: str = "sub-recipe-",
) -> str:
    """
    Render a recipe tree (plus its prep steps) as an HTML table.
    """
    id: Optional[str] = None
    if (
        isinstance(recipe_tree, SubRecipe)
        and len(recipe_tree.output_names) == 1
        and recipe_tree.show_output_names
    ):
        id = generate_subrecipe_output_id(recipe_tree, 0, id_prefix)

    return render_table(
        recipe_tree_to_table(recipe_tree, highlight_root=False),
        prep_steps,
        id,
        id_prefix,
    )


def render_recipe(
    recipe: Recipe,
    id_prefix: str = "recipe-",
) -> str:
    """
    Render all of the recipe trees in a
    :py:class:`~recipe_grid.recipe.Recipe` as a stacked series of tables
    inside a ``div.rgp-recipe-block``. Prep steps are hoisted into full-width
    rows at the top of the first table.
    """
    from recipe_grid_pretty_print.prepare import extract_prep_steps

    from recipe_grid_pretty_print.prepare import extract_prep_steps

    recipe, prep_steps = extract_prep_steps(recipe)

    trees = list(recipe.recipe_trees)
    if not trees and prep_steps:
        # Prep-only recipe: render the prep steps as their own table so they
        # still appear in the output.
        return t(
            "div",
            t(
                "table",
                "\n".join(render_prep_row(step, 1) for step in prep_steps),
                class_="rgp rgp-prep-only",
            ),
            class_="rgp-recipe-block",
        )

    tables = [
        render_recipe_tree(
            tree,
            prep_steps=(prep_steps if index == 0 else []),
            id_prefix=id_prefix,
        )
        for index, tree in enumerate(trees)
    ]

    return t("div", "\n".join(tables), class_="rgp-recipe-block")
