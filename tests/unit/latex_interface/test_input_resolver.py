from pathlib import Path

import pytest

from lq.latex_interface.data_model import ResolvedLatexIncludes
from lq.latex_interface.input_resolver import (
    resolve_input_path,
    resolve_latex_includes,
)
from lq.utils.io import InMemoryFileReader


def _resolve_latex_includes(
    files: dict[Path, bytes],
    main_file: Path,
    supporting_file_paths: list[Path],
) -> ResolvedLatexIncludes:
    return resolve_latex_includes(
        InMemoryFileReader(files),
        main_file=main_file,
        supporting_file_paths=supporting_file_paths,
    )


# --- test resolve_input_path ---


def test_resolve_input_path_without_extension():
    """Test input{filename} -> filename.tex"""
    result = resolve_input_path("intro", Path("/project/main.tex"))
    expected = Path("/project/intro.tex")
    assert result == expected


def test_resolve_input_path_with_extension():
    r"""Test \input{filename.tex} -> filename.tex"""
    result = resolve_input_path("intro.tex", Path("/project/main.tex"))
    expected = Path("/project/intro.tex")
    assert result == expected


def test_resolve_input_path_subdirectory():
    """Test relative paths from subdirectories"""
    result = resolve_input_path("sections/introduction", Path("/project/main.tex"))
    expected = Path("/project/sections/introduction.tex")
    assert result == expected


# --- test expand_latex_includes : error handling ---


def test__expand_latex_includes__fail_if_input_command_not_on_own_line():
    r"""Test that inline \input{} commands raise ValueError"""
    files = {
        Path("main.tex"): rb"text \input{inline} more",
    }

    with pytest.raises(ValueError):
        _resolve_latex_includes(
            files,
            main_file=Path("main.tex"),
            supporting_file_paths=[],
        )


def test__expand_latex_includes__missing_input_file_error():
    files = {
        Path("main.tex"): rb"\input{missing_file}",
    }

    with pytest.raises(FileNotFoundError):
        _resolve_latex_includes(
            files,
            main_file=Path("main.tex"),
            supporting_file_paths=[],
        )


def test__expand_latex_includes__missing_main_file_error():
    files = {
        Path("main.tex"): rb"AAA",
    }

    with pytest.raises(FileNotFoundError):
        _resolve_latex_includes(
            files,
            main_file=Path("a-missing-main.tex"),
            supporting_file_paths=[],
        )


def test__expand_latex_includes__rejects_absolute_paths():
    files = {
        Path("/tmp/main.tex"): rb"\input{intro}",
        Path("/tmp/intro.tex"): rb"AAA",
    }

    with pytest.raises(ValueError, match="must be relative"):
        _resolve_latex_includes(
            files,
            main_file=Path("/tmp/main.tex"),
            supporting_file_paths=[],
        )


# --- test expand_latex_includes : typical use case ---


def test__expand_latex_includes__with_tex_extension():
    files = {
        Path("main.tex"): rb"\input{intro.tex}",
        Path("intro.tex"): rb"AAA",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex="AAA",
        label_source_files={},
    )


def test__expand_latex_includes__supporting_files_exact_match():
    files = {
        Path("main.tex"): rb"""AAA
\input{intro}
\input{tables/data}
BBB
""",
        Path("intro.tex"): b"INTRO\n",
        Path("tables/data.tex"): b"TABLE\n",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[Path("tables/data.tex"), Path("missing")],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""AAA
INTRO
\input{tables/data}
BBB
""",
        label_source_files={},
    )


def test__expand_latex_includes__supporting_files_exact_paths_only():
    files = {
        Path("main.tex"): rb"""AAA
\input{intro}
\input{tables/data1}
\input{tables/data2.tex}
BBB
""",
        Path("intro.tex"): b"INTRO\n",
        Path("tables/data1.tex"): b"TABLE1\n",
        Path("tables/data2.tex"): b"TABLE2\n",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[Path("tables/data2.tex")],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""AAA
INTRO
TABLE1
\input{tables/data2.tex}
BBB
""",
        label_source_files={},
    )


def test__expand_latex_includes__single_level_expansion():
    files = {
        Path("main.tex"): rb"""AAA
\input{intro}
BBB
""",
        Path("intro.tex"): rb"""% foo
CCC % some comment
%
% \input{some other file}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""AAA
% foo
CCC % some comment
%
% \input{some other file}
BBB
""",
        label_source_files={},
    )


def test__expand_latex_includes__comments_preserved():
    """Comments in non-input lines are passed through verbatim."""
    files = {
        Path("main.tex"): rb"""AAA %% some comment
BBB % some other comment
%
%%
% \input{some other file}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""AAA %% some comment
BBB % some other comment
%
%%
% \input{some other file}
""",
        label_source_files={},
    )


def test__expand_latex_includes__input_with_trailing_comment_rejected():
    r"""An \input{} followed by a trailing comment is rejected."""
    files = {
        Path("main.tex"): rb"\input{intro} % include intro",
        Path("intro.tex"): rb"Hello",
    }

    with pytest.raises(ValueError, match="only non-whitespace content"):
        _resolve_latex_includes(
            files,
            main_file=Path("main.tex"),
            supporting_file_paths=[],
        )


def test__expand_latex_includes__input_with_leading_whitespace_expanded():
    files = {
        Path("main.tex"): rb""" \input{appendix/a01_sec_proof.tex}
""",
        Path("appendix/a01_sec_proof.tex"): rb"""\section{Proof}
Proof text.
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""\section{Proof}
Proof text.
""",
        label_source_files={},
    )


def test__expand_latex_includes__supporting_input_with_leading_whitespace_preserved():
    files = {
        Path("main.tex"): rb""" \input{tables/data}
""",
        Path("tables/data.tex"): b"TABLE\n",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[Path("tables/data.tex")],
    ) == ResolvedLatexIncludes(
        expanded_latex=r""" \input{tables/data}
""",
        label_source_files={},
    )


def test__expand_latex_includes__three_level_expansion():
    files = {
        Path("main.tex"): rb"\input{level1}",
        Path("level1.tex"): rb"\input{level2}",
        Path("level2.tex"): rb"\input{level3}",
        Path("level3.tex"): rb"Level 3 content",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex="Level 3 content",
        label_source_files={},
    )


def test_collect_label_source_files_with_nested_inputs():
    files = {
        Path("main.tex"): rb"""\section{Main}
\label{sec:main}
\input{parts/intro}
""",
        Path("parts/intro.tex"): rb"""\subsection{Intro}
\label{sub:intro}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""\section{Main}
\label{sec:main}
\subsection{Intro}
\label{sub:intro}
""",
        label_source_files={
            "sec:main": Path("main.tex"),
            "sub:intro": Path("parts/intro.tex"),
        },
    )


def test_resolve_latex_includes_collects_content_and_label_sources_in_one_result():
    files = {
        Path("main.tex"): rb"""\section{Main}
\label{sec:main}
\input{parts/intro}
""",
        Path("parts/intro.tex"): rb"""\subsection{Intro}
\label{sub:intro}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""\section{Main}
\label{sec:main}
\subsection{Intro}
\label{sub:intro}
""",
        label_source_files={
            "sec:main": Path("main.tex"),
            "sub:intro": Path("parts/intro.tex"),
        },
    )


def test_collect_label_source_files_ignores_comments_and_supporting_files():
    files = {
        Path("main.tex"): rb"""% \label{ignored:comment}
\label{sec:main}
\input{refs}
""",
        Path("refs.tex"): rb"""\label{ref:entry}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[Path("refs.tex")],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""% \label{ignored:comment}
\label{sec:main}
\input{refs}
""",
        label_source_files={"sec:main": Path("main.tex")},
    )


def test_collect_label_source_files_ignores_comment_labels_after_escaped_percent():
    files = {
        Path("main.tex"): rb"""\section{Progress 50\%}
\label{sec:main} % \label{ignored:comment}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""\section{Progress 50\%}
\label{sec:main} % \label{ignored:comment}
""",
        label_source_files={"sec:main": Path("main.tex")},
    )


def test_collect_label_source_files_detects_labels_inside_group_content():
    files = {
        Path("main.tex"): rb"""\begin{figure}
\caption{Main result \label{fig:main}}
\end{figure}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""\begin{figure}
\caption{Main result \label{fig:main}}
\end{figure}
""",
        label_source_files={"fig:main": Path("main.tex")},
    )


def test_collect_label_source_files_tolerates_multiline_non_label_commands():
    files = {
        Path("main.tex"): rb"""Text \cite{AuthorA:1999,
AuthorB:00}
\label{sec:main}
""",
    }

    assert _resolve_latex_includes(
        files,
        main_file=Path("main.tex"),
        supporting_file_paths=[],
    ) == ResolvedLatexIncludes(
        expanded_latex=r"""Text \cite{AuthorA:1999,
AuthorB:00}
\label{sec:main}
""",
        label_source_files={"sec:main": Path("main.tex")},
    )


# --- test expand_latex_includes : cycle detection tests ---


def test__expand_latex_includes__self_reference():
    files = {
        Path("main.tex"): rb"\input{main}",
    }

    with pytest.raises(ValueError, match="Circular input dependency detected"):
        _resolve_latex_includes(
            files,
            main_file=Path("main.tex"),
            supporting_file_paths=[],
        )


def test__expand_latex_includes__circular_dependency_two_files():
    files = {
        Path("file1.tex"): rb"\input{file2}",
        Path("file2.tex"): rb"\input{file1}",
    }
    main_file = Path("file1.tex")

    with pytest.raises(ValueError, match="Circular input dependency detected"):
        _resolve_latex_includes(files, main_file, supporting_file_paths=[])


def test__expand_latex_includes__circular_dependency_three_files():
    files = {
        Path("file1.tex"): rb"\input{file2}",
        Path("file2.tex"): rb"\input{file3}",
        Path("file3.tex"): rb"\input{file1}",
    }

    with pytest.raises(ValueError, match="Circular input dependency detected"):
        _resolve_latex_includes(
            files,
            main_file=Path("file1.tex"),
            supporting_file_paths=[],
        )
