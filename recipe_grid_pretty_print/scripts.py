"""
The ``recipe-grid-pretty-print`` command
========================================

Compiles a recipe grid markdown file into a beautiful, print-ready, standalone
HTML page in the style of recipetables.com.
"""

import sys

from argparse import ArgumentParser

from pathlib import Path

from fractions import Fraction

from recipe_grid.number_parser import number

from peggie import ParseError

from recipe_grid.compiler import RecipeCompileError

from recipe_grid_pretty_print.document import generate_document


def main() -> None:
    parser = ArgumentParser(
        description="""
            Compile a recipe grid markdown file into a beautiful, print-ready
            standalone HTML page (recipetables.com style). Print the generated
            page from any browser (Cmd/Ctrl+P) to produce a nicely paginated
            PDF.
        """,
    )

    parser.add_argument(
        "recipe",
        type=Path,
        help="The recipe grid markdown file to compile.",
    )
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="""
            The output filename. Defaults to the input filename with the
            extension replaced with '.html'. Use '-' to write to stdout.
        """,
    )

    scaling_group = parser.add_mutually_exclusive_group()
    scaling_group.add_argument(
        "--servings",
        "-s",
        type=int,
        metavar="SERVINGS",
        default=None,
        help="""
            Rescale the recipe to the specified number of servings. Requires
            the recipe to declare its servings in the title (e.g. '... for 4').
        """,
    )
    scaling_group.add_argument(
        "--scale",
        "-S",
        type=number,
        metavar="MULTIPLIER",
        default=None,
        help="Scale all quantities by a multiplier (e.g. '2', '0.5' or '1 1/2').",
    )

    parser.add_argument(
        "--paper",
        choices=["a4", "letter"],
        default="a4",
        help="Paper size to tune page breaks and margins for. Default: a4.",
    )
    parser.add_argument(
        "--orientation",
        choices=["portrait", "landscape"],
        default="portrait",
        help="Page orientation. Default: portrait.",
    )
    parser.add_argument(
        "--accent",
        default=None,
        metavar="CSS_COLOUR",
        help="""
            CSS colour used for step cells (default: the theme's warm peach,
            e.g. '#f9e7d7').
        """,
    )
    parser.add_argument(
        "--no-toolbar",
        action="store_true",
        default=False,
        help="Omit the on-screen print toolbar from the generated page.",
    )

    args = parser.parse_args()

    try:
        with args.recipe.open("r") as f:
            markdown_source = f.read()

        html = generate_document(
            markdown_source,
            scale=args.scale,
            servings=args.servings,
            paper=args.paper,
            orientation=args.orientation,
            accent=args.accent,
            include_toolbar=not args.no_toolbar,
        )
    except (OSError, ParseError, RecipeCompileError, ValueError) as e:
        sys.stderr.write(f"{e}\n")
        sys.exit(1)

    if args.output == Path("-"):
        sys.stdout.write(html)
    else:
        output = args.output
        if output is None:
            output = args.recipe.with_suffix(".html")
        with output.open("w") as f:
            f.write(html)


if __name__ == "__main__":
    main()
