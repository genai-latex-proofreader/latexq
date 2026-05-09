from pathlib import Path
from typing import cast

import pytest

from lq.latex_interface.data_model import (
    LatexBlock,
    LatexBlockKind,
    LatexStructuralBlock,
    to_latex,
)
from lq.latex_interface.parser import (
    parse_from_latex,
    parse_latex_from_files,
)
from lq.utils.io import InMemoryFileReader

# ---------------------------------------------------------------------------
# Test document
# ---------------------------------------------------------------------------

TEST_DOC = r"""\documentclass[12pt, a4paper, twoside]{amsart}

\usepackage{mathrsfs}

\parindent = 0cm
\parskip   = .2cm

\title[short-title]{A longer title for the paper}

\begin{document}

\begin{abstract}
An abstract
\end{abstract}

\maketitle

\section{Introduction}
\label{sec:introduction}
Suppose we have $x^2 + y^2 = 1$.

\section{The main theorem}
\label{sec:main:theorem}
Some more text

\section{Conclusions}
\label{sec:conclusions}
\section{More conclusions}
\label{sec:more:conclusions}

\appendix

Appendix intro

\section{Derivation of main equations}
\label{sec:app1}
Appendix section introduction

\begin{proof}
The result follows since $x^2 + y^2 = 1$
\end{proof}

\end{document}"""


def _parse_latex_from_file_map(
    files: dict[Path, bytes],
    main_file: Path,
    supporting_file_paths: list[Path],
    supporting_files: dict[Path, bytes] | None = None,
):
    return parse_latex_from_files(
        InMemoryFileReader(files),
        main_file,
        supporting_file_paths=supporting_file_paths,
        supporting_files=supporting_files,
    )


def _pre_section_block(*, in_appendix: bool, body: str) -> LatexBlock:
    return LatexBlock.pre_section(
        in_appendix=in_appendix,
        content=body,
    )


def _section_block(
    *,
    in_appendix: bool,
    title: str,
    body: str,
    all_labels: frozenset[str],
) -> LatexBlock:
    return LatexBlock.section(
        in_appendix=in_appendix,
        content=rf"\section{{{title}}}" + body,
        all_labels=all_labels,
    )


def _subsection_block(
    *,
    in_appendix: bool,
    title: str,
    body: str,
    all_labels: frozenset[str],
) -> LatexBlock:
    return LatexBlock.subsection(
        in_appendix=in_appendix,
        content=rf"\subsection{{{title}}}" + body,
        all_labels=all_labels,
    )


def test_latex_parser_fail_if_duplicate_labels():
    with pytest.raises(Exception, match=r"Duplicate labels: 'sec:introduction' \(x2\)"):
        parse_from_latex(TEST_DOC.replace(r"{sec:main:theorem}", r"{sec:introduction}"))


def test_latex_parser_fails_if_subsection_label_duplicates_section_label():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:introduction}
Intro text

\section{Methods}
\label{sec:methods}
Methods text

\subsection{Setup}
\label{sec:introduction}
Setup text

\end{document}"""

    with pytest.raises(Exception, match=r"Duplicate labels: 'sec:introduction' \(x2\)"):
        parse_from_latex(input_latex)


def test_parse_fails_when_section_labels_have_invalid_characters():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro_valid}
Intro text

\subsection{Setup}
\label{sec:setup?}
Setup text

\end{document}"""

    with pytest.raises(ValueError, match=r"Invalid section label") as exc_info:
        parse_from_latex(input_latex)

    message = str(exc_info.value)
    assert "sec:setup?" in message


def test_parse_accepts_section_labels_with_underscore_and_hyphen():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro_valid}
Intro text

\subsection{Setup}
\label{sec:setup-valid}
Setup text

\end{document}"""

    parse_from_latex(input_latex)


def test_parse_preserves_section_node_with_no_body_before_subsection():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
\label{sec:main}
\subsection{Detail}
\label{sub:detail}
Detail text

\end{document}"""

    doc = parse_from_latex(input_latex)
    assert doc.blocks == (
        _pre_section_block(
            in_appendix=False,
            body="\n\n",
        ),
        _section_block(
            in_appendix=False,
            title="Main",
            body=r"""
\label{sec:main}
""",
            all_labels=frozenset({"sec:main", "sub:detail"}),
        ),
        _subsection_block(
            in_appendix=False,
            title="Detail",
            body=r"""
\label{sub:detail}
Detail text

""",
            all_labels=frozenset({"sub:detail"}),
        ),
    )
    assert [block.kind for block in doc.iter_structural_blocks()] == [
        LatexBlockKind.section,
        LatexBlockKind.subsection,
    ]
    main_block = next(
        block for block in doc.iter_structural_blocks() if block.title == "Main"
    )
    assert main_block.label == "sec:main"
    assert (
        main_block.body
        == r"""
\label{sec:main}
"""
    )


def test_parse_preserves_optional_short_heading_source() -> None:
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section[Short intro]{Introduction}
\label{sec:intro}
Intro text

\subsection[Bg]{Background}
\label{sub:bg}
Background text

\end{document}"""

    doc = parse_from_latex(input_latex)
    section = cast(LatexStructuralBlock, doc.blocks[1])
    subsection = cast(LatexStructuralBlock, doc.blocks[2])

    assert section.heading_source == r"\section[Short intro]{Introduction}"
    assert section.title == "Introduction"
    assert section.label == "sec:intro"
    assert (
        section.body
        == r"""
\label{sec:intro}
Intro text

"""
    )

    assert subsection.heading_source == r"\subsection[Bg]{Background}"
    assert subsection.title == "Background"
    assert subsection.label == "sub:bg"
    assert (
        subsection.body
        == r"""
\label{sub:bg}
Background text

"""
    )

    assert to_latex(doc) == input_latex


def test_parse_ignores_commented_out_sectioning_commands():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

% \section{Ignored main section}
\section{Main}
\label{sec:main}
% \subsection{Ignored detail}
\subsection{Detail}
\label{sub:detail}
Detail content

\end{document}"""

    doc = parse_from_latex(input_latex)
    assert doc.blocks == (
        _pre_section_block(
            in_appendix=False,
            body=r"""

% \section{Ignored main section}
""",
        ),
        _section_block(
            in_appendix=False,
            title="Main",
            body=r"""
\label{sec:main}
% \subsection{Ignored detail}
""",
            all_labels=frozenset({"sec:main", "sub:detail"}),
        ),
        _subsection_block(
            in_appendix=False,
            title="Detail",
            body=r"""
\label{sub:detail}
Detail content

""",
            all_labels=frozenset({"sub:detail"}),
        ),
    )


def test_parse_assigns_direct_label_after_intervening_plain_text():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
Intro text before the label.
\label{sec:main}
Main content

\end{document}"""

    doc = parse_from_latex(input_latex)

    assert doc.blocks == (
        _pre_section_block(
            in_appendix=False,
            body="\n\n",
        ),
        _section_block(
            in_appendix=False,
            title="Main",
            body=r"""
Intro text before the label.
\label{sec:main}
Main content

""",
            all_labels=frozenset({"sec:main"}),
        ),
    )


def test_parse_does_not_assign_direct_label_after_intervening_command():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
	extbf{break direct label eligibility}
\label{sec:main}
Main content

\end{document}"""

    doc = parse_from_latex(input_latex)

    assert doc.blocks == (
        _pre_section_block(
            in_appendix=False,
            body="\n\n",
        ),
        _section_block(
            in_appendix=False,
            title="Main",
            body=r"""
	extbf{break direct label eligibility}
\label{sec:main}
Main content

""",
            all_labels=frozenset({"sec:main"}),
        ),
    )


def test_parse_does_not_assign_direct_label_after_intervening_environment():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
\begin{equation}
\label{eq:main}
x = 1
\end{equation}
\label{sec:main}
Main content

\end{document}"""

    doc = parse_from_latex(input_latex)

    assert doc.blocks == (
        _pre_section_block(
            in_appendix=False,
            body="\n\n",
        ),
        _section_block(
            in_appendix=False,
            title="Main",
            body=r"""
\begin{equation}
\label{eq:main}
x = 1
\end{equation}
\label{sec:main}
Main content

""",
            all_labels=frozenset({"eq:main", "sec:main"}),
        ),
    )


def test_parse_fails_when_file_has_leading_comment_before_documentclass():
    input_latex = r"""% leading comment
\documentclass{article}

\begin{document}

\maketitle

\section{Main}
Main text

\end{document}"""

    with pytest.raises(
        Exception, match=r"\\documentclass expected to be at start of file"
    ):
        parse_from_latex(input_latex)


def test_parse_fails_when_document_has_no_maketitle():
    input_latex = r"""\documentclass{article}

\begin{document}

\section{Main}
Main text

\end{document}"""

    with pytest.raises(Exception, match=r"\\maketitle not found"):
        parse_from_latex(input_latex)


def test_parse_fails_when_document_has_more_than_one_maketitle():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle
\maketitle

\section{Main}
Main text

\end{document}"""

    with pytest.raises(Exception, match=r"at most one \\maketitle is supported"):
        parse_from_latex(input_latex)


def test_parse_treats_unsupported_sectioning_commands_as_ordinary_content():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\part{Preface}
\chapter{Ignored Chapter}
\section*{Overview}
Prelude text

\section{Main}
\label{sec:main}
Main intro
\subsection*{Ignored detail}
Still section content

\subsection{Detail}
\label{sub:detail}
Detail text
\subsubsection{Lower heading}
Still subsection content

\end{document}"""

    doc = parse_from_latex(input_latex)

    assert [block.kind for block in doc.blocks] == [
        LatexBlockKind.pre_section,
        LatexBlockKind.section,
        LatexBlockKind.subsection,
    ]

    pre_section, section, subsection = doc.blocks
    section = cast(LatexStructuralBlock, section)
    subsection = cast(LatexStructuralBlock, subsection)

    assert r"\part{Preface}" in pre_section.content
    assert r"\chapter{Ignored Chapter}" in pre_section.content
    assert r"\section*{Overview}" in pre_section.content

    assert section.title == "Main"
    assert r"\subsection*{Ignored detail}" in section.body
    assert "Still section content" in section.body

    assert subsection.title == "Detail"
    assert r"\subsubsection{Lower heading}" in subsection.body
    assert "Still subsection content" in subsection.body


def test_parse_fails_when_direct_label_contains_reserved_query_substring():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro..results}
Intro text

\end{document}"""

    with pytest.raises(ValueError, match=r"substring '\.\.' is reserved") as exc_info:
        parse_from_latex(input_latex)

    assert "sec:intro..results" in str(exc_info.value)


def test_parse_fails_when_nested_label_contains_reserved_query_substring():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
Intro text

\begin{equation}
E = mc^2
\label{eq:mass..energy}
\end{equation}

\end{document}"""

    with pytest.raises(ValueError, match=r"substring '\.\.' is reserved") as exc_info:
        parse_from_latex(input_latex)

    assert "eq:mass..energy" in str(exc_info.value)


@pytest.mark.parametrize(
    "split_marker",
    [
        "",
        r"\appendix",
        r"\appendix\n\section{Foo}",
    ],
)
def test_parse_latex_from_files_rejects_duplicate_direct_labels(split_marker: str):
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:introduction}
Intro text

<SPLIT>

\section{Setup}
\label{sec:introduction}
Setup text

\end{document}""".replace("<SPLIT>", split_marker)

    with pytest.raises(Exception, match=r"Duplicate labels: 'sec:introduction' \(x2\)"):
        parse_latex_from_files(
            InMemoryFileReader({Path("main.tex"): input_latex.encode()}),
            Path("main.tex"),
            supporting_file_paths=[],
        )


def test_parse_fails_when_nested_labels_duplicate_anywhere_in_document():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
\begin{equation}
\label{eq:shared}
x = 1
\end{equation}

\section{Methods}
\label{sec:methods}
\begin{figure}
\label{fig:shared}
\caption{Shared figure}
\end{figure}

\section{Results}
\label{sec:results}
\begin{equation}
\label{eq:shared}
y = 2
\end{equation}
\begin{table}
\label{fig:shared}
\caption{Repeated label}
\end{table}

\end{document}"""

    with pytest.raises(
        Exception, match=r"Duplicate labels detected in LaTeX document"
    ) as exc_info:
        parse_from_latex(input_latex)

    message = str(exc_info.value)
    assert "'eq:shared' (x2)" in message
    assert "'fig:shared' (x2)" in message


def test_parse_latex_from_files_resolves_included_files():
    files = {
        Path("main.tex"): rb"""\documentclass{article}

\begin{document}

\maketitle

\input{intro}
\input{setup}

\end{document}""",
        Path("intro.tex"): rb"""\section{Introduction}
\label{sec:introduction}
Intro text
""",
        Path("setup.tex"): rb"""\section{Setup}
\label{sec:setup}
Setup text
""",
    }

    doc = _parse_latex_from_file_map(files, Path("main.tex"), supporting_file_paths=[])

    assert (
        to_latex(doc)
        == r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:introduction}
Intro text
\section{Setup}
\label{sec:setup}
Setup text

\end{document}"""
    )


def test_parse_latex_from_files_roundtrips_preserved_supporting_tex_inputs():
    files = {
        Path("main.tex"): rb"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
\input{tables/data1.tex}
\input{tables/data2.tex}

\end{document}""",
        Path("tables/data1.tex"): b"Data 1 content\n",
        Path("tables/data2.tex"): b"Data 2 content\n",
    }

    doc = _parse_latex_from_file_map(
        files,
        Path("main.tex"),
        supporting_file_paths=[
            Path("tables/data1.tex"),
            Path("tables/data2.tex"),
        ],
        supporting_files={
            Path("tables/data1.tex"): files[Path("tables/data1.tex")],
            Path("tables/data2.tex"): files[Path("tables/data2.tex")],
        },
    )

    assert (
        to_latex(doc)
        == r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
\input{tables/data1.tex}
\input{tables/data2.tex}

\end{document}"""
    )


def test_parse_fails_when_main_document_starts_with_subsection():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\subsection{Early stuff}
Some early content

\section{Main}
\label{sec:main}
Main content

\end{document}"""

    with pytest.raises(ValueError, match=r"main body must begin with \\section"):
        parse_from_latex(input_latex)


def test_parse_fails_when_appendix_starts_with_subsection():
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Main}
Main content

\appendix

\subsection{Appendix detail}
Appendix content

\end{document}"""

    with pytest.raises(ValueError, match=r"appendix must begin with \\section"):
        parse_from_latex(input_latex)


def test_parse_latex_from_files_does_not_preserve_supporting_files_implicitly():
    files = {
        Path("main.tex"): TEST_DOC.encode(),
        Path("notes.txt"): b"supporting content",
    }

    doc = _parse_latex_from_file_map(files, Path("main.tex"), supporting_file_paths=[])

    assert doc.supporting_files == {}


def test_parse_latex_from_files_preserves_explicit_supporting_files():
    supporting_files = {Path("refs.bib"): b"@article{key, title={Example}}"}

    doc = _parse_latex_from_file_map(
        {Path("main.tex"): TEST_DOC.encode()},
        Path("main.tex"),
        supporting_file_paths=[],
        supporting_files=supporting_files,
    )

    assert doc.supporting_files == supporting_files


def test_parse_latex_from_files_rejects_absolute_paths():
    with pytest.raises(ValueError, match="must be relative"):
        _parse_latex_from_file_map(
            {Path("/tmp/main.tex"): TEST_DOC.encode()},
            Path("/tmp/main.tex"),
            supporting_file_paths=[],
        )


def test_parse_from_latex_allows_absolute_supporting_files():
    doc = parse_from_latex(
        TEST_DOC, supporting_files={Path("/tmp/refs.bib"): b"@article{key, title={X}}"}
    )
    assert Path("/tmp/refs.bib") in doc.supporting_files


def test_parse_from_latex_exposes_all_source_labels_on_latex_document():
    input_latex = r"""\documentclass{article}

\begin{document}
\label{front:doc}

\maketitle

Main setup
\label{main:pre}

\section{Intro}
\label{sec:intro}
Intro text
\begin{equation}
\label{eq:intro}
x = 1
\end{equation}

\begin{thebibliography}{9}
\bibitem{ref} Ref text
\label{bib:entry}
\end{thebibliography}

\end{document}"""

    doc = parse_from_latex(input_latex)

    assert doc.all_source_labels == frozenset(
        {"front:doc", "main:pre", "sec:intro", "eq:intro", "bib:entry"}
    )


@pytest.mark.parametrize(
    "post_document",
    ["", "\n", "\r\n", "\n\n", "\n% trailing comment\n", " trailing text"],
)
def test_parse_preserves_post_document_content(
    post_document: str,
):
    input_latex = (
        r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
Hello World!

\end{document}"""
        + post_document
    )

    document = parse_from_latex(input_latex)

    assert document.post_document == post_document
    assert to_latex(document) == input_latex


def test_roundtrip_validation_preserves_post_document_content() -> None:
    input_latex = r"""\documentclass{article}

\begin{document}

\maketitle

\section{Introduction}
\label{sec:intro}
Hello World!

\end{document}

% trailing comment
"""

    from lq.latex_interface.roundtrip import validate_latex_roundtrip

    validate_latex_roundtrip(input_latex)
