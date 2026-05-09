import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from lq import __version__


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="lq")
    # "lq --version" should print the version and exit with code 0.
    parser.add_argument(
        "--version", action="version", version=f"lq version {__version__}"
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # lq flatten:
    #  - read the input project's files so \input{} references can be resolved,
    #  - optionally filter structural content through one query,
    #  - write one LaTeX document file intended for human review/compilation.
    flatten_parser = subparsers.add_parser(
        "flatten", help="Flatten a LaTeX project into a single file"
    )
    flatten_parser.add_argument(
        "--input-file", type=Path, required=True, help="Input main LaTeX file"
    )
    flatten_parser.add_argument(
        "--output-file", type=Path, required=True, help="Output LaTeX filename"
    )
    flatten_parser.add_argument(
        "--query",
        type=str,
        help="Optional lq query selecting which structural nodes to keep",
    )

    # lq select:
    select_parser = subparsers.add_parser(
        "select", help="Select structural content as a LaTeX fragment"
    )
    select_parser.add_argument(
        "--input-file", type=Path, required=True, help="Input main LaTeX file"
    )
    select_output_group = select_parser.add_mutually_exclusive_group(required=False)
    select_output_group.add_argument(
        "--output-file", type=Path, help="Output fragment filename"
    )
    select_output_group.add_argument(
        "--stdout", action="store_true", help="Write selected fragment to stdout"
    )
    select_parser.add_argument(
        "--query",
        type=str,
        required=True,
        help="lq query selecting which structural nodes to emit",
    )

    # lq split: split a LaTeX document so each section/subsection is in a separate file.
    split_parser = subparsers.add_parser(
        "split", help="Split a LaTeX document into per-section files"
    )
    split_parser.add_argument(
        "--input-file", type=Path, required=True, help="Input main LaTeX file"
    )
    split_parser.add_argument(
        "--output-dir", type=Path, help="Output directory for split mode"
    )
    split_parser.add_argument(
        "--config-file", type=Path, required=True, help="Split config file path"
    )
    split_parser.add_argument(
        "--validate",
        action="store_true",
        help="Validate that split-generated .tex files match lq split output",
    )

    # lq graph:
    graph_parser = subparsers.add_parser(
        "graph", help="Build a containment-based reference graph"
    )
    graph_parser.add_argument(
        "--input-file", type=Path, required=True, help="Input main LaTeX file"
    )
    graph_output_group = graph_parser.add_mutually_exclusive_group(required=False)
    graph_output_group.add_argument(
        "--output-file", type=Path, help="Output graph filename"
    )
    graph_output_group.add_argument(
        "--stdout", action="store_true", help="Write graph output to stdout"
    )
    graph_parser.add_argument(
        "--format",
        choices=("text", "json"),
        required=True,
        help="Graph output format",
    )

    return parser


def get_args(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = _build_parser()
    args = parser.parse_args(None if argv is None else list(argv))

    if args.command == "split":
        if args.validate and args.output_dir is not None:
            parser.error("--output-dir cannot be used with --validate")
        if not args.validate and args.output_dir is None:
            parser.error("the following arguments are required: --output-dir")

    return args


def _raise_cli_error(message: str) -> None:
    sys.stderr.write(f"lq: error: {message}\n")
    raise SystemExit(2)


def cli(argv: Sequence[str] | None = None) -> None:
    args = get_args(argv)

    if args.command == "flatten":
        from lq.flatten.command import flatten_command
        from lq.query import QueryError, QuerySyntaxError
        from lq.utils.output import OutputTarget, get_writer

        try:
            flatten_command(
                args.input_file,
                get_writer(OutputTarget(output_file=args.output_file, stdout=False)),
                args.query,
            )
        except QuerySyntaxError as error:
            _raise_cli_error(f"invalid query syntax: {error}")
        except QueryError as error:
            _raise_cli_error(f"invalid query: {error}")
        return

    if args.command == "select":
        from lq.query import QueryError, QuerySyntaxError
        from lq.select import SelectionQueryRequest, select_command
        from lq.utils.output import OutputTarget, get_writer

        try:
            select_command(
                args.input_file,
                get_writer(
                    OutputTarget(
                        output_file=args.output_file,
                        stdout=args.stdout or args.output_file is None,
                    )
                ),
                SelectionQueryRequest(
                    query_text=args.query,
                    output_mode="fragment",
                ),
            )
        except QuerySyntaxError as error:
            _raise_cli_error(f"invalid query syntax: {error}")
        except QueryError as error:
            _raise_cli_error(f"invalid query: {error}")
        return

    if args.command == "split":
        from lq.latex_interface.roundtrip import LatexRoundtripValidationError
        from lq.split.command import split_command
        from lq.split.validate import validate_split_command

        if args.validate:
            validate_split_command(args.input_file, args.config_file)
            return

        assert args.output_dir is not None
        try:
            split_command(args.input_file, args.output_dir, args.config_file)
        except LatexRoundtripValidationError as error:
            _raise_cli_error(f"input manuscript failed roundtrip validation: {error}")
        return

    if args.command == "graph":
        from lq.graph.command import graph_command
        from lq.utils.output import OutputTarget, get_writer

        graph_command(
            args.input_file,
            get_writer(
                OutputTarget(
                    output_file=args.output_file,
                    stdout=args.stdout or args.output_file is None,
                )
            ),
            args.format,
        )
        return

    raise Exception("Something went wrong.")
