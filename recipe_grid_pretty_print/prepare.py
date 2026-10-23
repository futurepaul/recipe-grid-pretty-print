"""
Prep-step extraction
====================

The recipe grid language requires every step to have at least one input, but
pretty-printed recipe tables (like the ones on recipetables.com) support
"prep" steps which have no ingredients -- things like "Preheat oven to
300F / 150C" or "Generously oil a half sheet pan".

This module implements a simple, explicit convention for writing prep steps
in recipe grid source: give the step a *dummy ingredient* whose name starts
with an underscore. For example::

    "preheat oven to 300F / 150C" (_oven)
    "generously oil a rimmed half sheet pan" (_pan)

Steps whose inputs are all dummy ingredients are hoisted out of the table and
rendered as full-width "prep" rows above the grid. Dummy ingredients mixed in
with real ones are simply hidden, e.g.::

    "fry the onions" (1 onion, _pan)

becomes a normal step with the ``_pan`` ingredient omitted.

Each dummy name should only be used once (they are registered as sub-recipe
output names by the recipe grid compiler when a step has a single input).
"""

from typing import List, Optional, Tuple

from dataclasses import replace

from recipe_grid.recipe import (
    Recipe,
    RecipeTreeNode,
    Ingredient,
    Step,
    SubRecipe,
)

DUMMY_PREFIX = "_"


def is_dummy_ingredient(node: RecipeTreeNode) -> bool:
    """
    Is this node a dummy ingredient (e.g. ``_pan``) used to satisfy the
    recipe grid language's requirement that steps have inputs?
    """
    return (
        isinstance(node, Ingredient)
        and node.quantity is None
        and str(node.description).startswith(DUMMY_PREFIX)
    )


def _root_step(tree: RecipeTreeNode) -> Optional[Step]:
    """
    Unwrap a recipe tree root, returning the underlying :py:class:`Step` if
    the root is a step (possibly wrapped in an output-name-hiding SubRecipe,
    which the compiler adds for single-input steps).
    """
    if isinstance(tree, Step):
        return tree
    if (
        isinstance(tree, SubRecipe)
        and not tree.show_output_names
        and isinstance(tree.sub_tree, Step)
    ):
        return tree.sub_tree
    return None


def _strip_dummy_inputs(node: RecipeTreeNode) -> RecipeTreeNode:
    """
    Return a copy of the tree with dummy ingredients removed from any step
    which has at least one non-dummy input. Steps which consist only of
    dummy inputs are left untouched (they will be handled as prep steps if
    they are at the root of a recipe tree).
    """
    if isinstance(node, Step):
        new_inputs = tuple(_strip_dummy_inputs(i) for i in node.inputs)
        kept = tuple(i for i in new_inputs if not is_dummy_ingredient(i))
        if kept and kept != tuple(node.inputs):
            return replace(node, inputs=kept)
        return node
    elif isinstance(node, SubRecipe):
        return replace(node, sub_tree=_strip_dummy_inputs(node.sub_tree))
    return node


def extract_prep_steps(
    recipe: Recipe,
) -> Tuple[Recipe, List[Step]]:
    """
    Split a :py:class:`~recipe_grid.recipe.Recipe` into a cleaned recipe (with
    prep steps and dummy ingredients removed) and a list of the prep steps
    found at the root of its recipe trees, in source order.
    """
    prep_steps: List[Step] = []
    kept_trees: List[RecipeTreeNode] = []

    for tree in recipe.recipe_trees:
        step = _root_step(tree)
        if step is not None and step.inputs and all(
            is_dummy_ingredient(i) for i in step.inputs
        ):
            prep_steps.append(step)
        else:
            kept_trees.append(_strip_dummy_inputs(tree))

    cleaned = replace(recipe, recipe_trees=tuple(kept_trees))
    return cleaned, prep_steps
