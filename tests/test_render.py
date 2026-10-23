import re

import pytest

from peggie import ParseError

from recipe_grid_pretty_print import render_source
from recipe_grid_pretty_print.prepare import extract_prep_steps
from recipe_grid_pretty_print.style import build_css
from recipe_grid_pretty_print.document import generate_document
from recipe_grid.markdown import compile_markdown


MUFFINS = """
Breakfast muffins for 12
========================

    "preheat oven to 300°F / 150°C" (_oven)
    "generously oil a rimmed half sheet pan" (_pan)

    12 eggs
    1/4 cup whole milk
    1 1/2 tsp salt

    whisked = "whisk eggs, milk & salt" (eggs, whole milk, salt)
    "cool, cut into rounds" (whisked)
"""


def strip_tags(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


class TestDocument:
    def test_renders_standalone_document(self):
        html = render_source(MUFFINS)
        assert html.startswith("<!DOCTYPE html>")
        assert "<title>Breakfast muffins</title>" in html
        assert "table.rgp" in html  # stylesheet inlined

    def test_preparation_steps(self):
        html = render_source(MUFFINS)
        assert 'class="rgp-prep"' in html
        assert "preheat oven to" in html
        # Dummy ingredients must never appear in the output
        assert "_oven" not in html
        assert "_pan" not in html

    def test_ingredient_quantities(self):
        html = render_source(MUFFINS)
        assert "rgp-quantity" in html
        assert "whole milk" in html
        assert "1 1/2" in strip_tags(html)

    def test_no_title(self):
        html = render_source("\n    1 egg\n    boil(egg)\n")
        assert "<title>Recipe</title>" in html

    def test_document_title_escaped(self):
        html = render_source("# Eggs & ham\n\n    1 egg\n    boil(egg)\n")
        assert "<title>Eggs &amp; ham</title>" in html


class TestScaling:
    def test_scale(self):
        html = render_source(MUFFINS, scale=2)
        assert "24" in strip_tags(html)

    def test_servings(self):
        html = render_source(MUFFINS, servings=24)
        assert "24" in strip_tags(html)
        assert "Rescaled from" in html

    def test_servings_requires_known_servings(self):
        with pytest.raises(ValueError):
            render_source("\n    1 egg\n    boil(egg)\n", servings=4)

    def test_scale_and_servings_mutually_exclusive(self):
        with pytest.raises(ValueError):
            render_source(MUFFINS, scale=2, servings=4)


class TestOptions:
    def test_paper(self):
        assert "size: A4" in build_css(paper="a4")
        assert "size: letter" in build_css(paper="letter")
        with pytest.raises(ValueError):
            build_css(paper="a5")

    def test_orientation(self):
        assert "size: A4" in build_css(orientation="portrait")
        assert "size: A4 landscape" in build_css(orientation="landscape")

    def test_accent(self):
        html = generate_document(MUFFINS, accent="#ddefff")
        assert "#ddefff" in html

    def test_toolbar_optional(self):
        assert 'class="rgp-toolbar"' in render_source(MUFFINS)
        assert 'class="rgp-toolbar"' not in render_source(
            MUFFINS, include_toolbar=False
        )

    def test_pagination_script(self):
        html = render_source(MUFFINS)
        assert "rgp-force-break" in html  # pagination script embedded
        assert "--rgp-content-height" in html  # page capacity CSS variable
        assert html.count("<script>") == 1
        assert "<script>" not in render_source(MUFFINS, paginate=False)


class TestPrepare:
    def test_prep_steps_extracted(self):
        recipe = compile_markdown(MUFFINS).recipes[0][0]
        cleaned, prep = extract_prep_steps(recipe)
        assert len(prep) == 2
        assert "preheat oven" in str(prep[0].description)
        # The single-use "whisked" sub recipe is inlined into the final step,
        # leaving a single recipe tree.
        assert len(cleaned.recipe_trees) == 1

    def test_mixed_dummy_inputs_hidden(self):
        recipe = compile_markdown(
            "\n    \"fry the onions\" (1 onion, _pan)\n"
        ).recipes[0][0]
        cleaned, prep = extract_prep_steps(recipe)
        assert prep == []
        (tree,) = cleaned.recipe_trees
        (step_input,) = tree.inputs
        assert "onion" in str(step_input.description)

    def test_normal_ingredients_untouched(self):
        recipe = compile_markdown("\n    1 egg\n    boil(egg)\n").recipes[0][0]
        cleaned, prep = extract_prep_steps(recipe)
        assert prep == []
        assert len(cleaned.recipe_trees) == 1


class TestSpecialRecipes:
    def test_multiple_outputs(self):
        html = render_source(
            """
                boiled veg, veg water = "drain reserving water" (carrots, peas)
                "serve" (boiled veg, veg water)
            """
        )
        assert "rgp-sub-recipe-outputs" in html
        assert "boiled veg" in html and "veg water" in html

    def test_named_sub_recipe_header(self):
        html = render_source(
            """
                sauce := "simmer" (tomatoes)
                "serve" (sauce)
            """
        )
        assert "rgp-sub-recipe-header" in html

    def test_shared_ingredient_reference(self):
        html = render_source(
            """
                1 tsp salt
                a(salt)
                b(salt)
            """
        )
        assert "rgp-reference" in html

    def test_invalid_recipe_raises(self):
        with pytest.raises(ParseError):
            render_source("\n    fry((\n")

    def test_page_break_helpers_in_css(self):
        css = render_source(MUFFINS)
        assert "break-inside: avoid" in css
        assert "break-after: avoid" in css
        assert "@page" in css
        assert ".rgp-force-break" in css

    def test_continuation_cells_are_css_styled(self):
        assert "rgp-continuation" in render_source(MUFFINS)
