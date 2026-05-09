from dataclasses import dataclass

import pytest

from lq.latex_interface.data_model import (
    LatexBlockKind,
    LatexStructuralBlock,
)
from lq.latex_interface.parser import parse_from_latex


@dataclass(frozen=True)
class ExpectedStructuralMetadata:
    heading_source: str
    title: str
    label: str | None
    body: str
    all_labels: frozenset[str]


def _extract_structural_metadata_by_key(
    input_latex: str,
) -> dict[str, LatexStructuralBlock]:
    """Parse LaTeX and return structural blocks keyed by semantic title."""
    doc = parse_from_latex(input_latex)

    def _section_key(block: LatexStructuralBlock) -> str:
        if block.kind is LatexBlockKind.subsection:
            return f"sub:{block.title}"
        if block.kind is LatexBlockKind.section:
            return f"sec:{block.title}"
        raise ValueError(f"Unhandled block kind: {block.kind}")

    return {_section_key(block): block for block in doc.iter_structural_blocks()}


def _assert_structural_metadata(
    block: LatexStructuralBlock,
    *,
    heading_source: str,
    title: str,
    label: str | None,
    body: str,
    all_labels: frozenset[str],
) -> None:
    assert block.heading_source == heading_source
    assert block.title == title
    assert block.label == label
    assert block.body == body
    assert block.all_labels == all_labels


def _assert_sections_metadata(
    input_latex: str,
    expected_sections: dict[str, ExpectedStructuralMetadata],
) -> None:
    sections = _extract_structural_metadata_by_key(input_latex)

    assert set(sections) == set(expected_sections)

    for key, expected in expected_sections.items():
        _assert_structural_metadata(
            sections[key],
            heading_source=expected.heading_source,
            title=expected.title,
            label=expected.label,
            body=expected.body,
            all_labels=expected.all_labels,
        )


def test_no_sections():
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\end{document}"""
    assert _extract_structural_metadata_by_key(input_latex) == {}


def test_metadata_extraction_preserves_plain_section_metadata() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the introduction.
\end{document}"""
    _assert_sections_metadata(
        input_latex,
        {
            "sec:Introduction": ExpectedStructuralMetadata(
                heading_source=r"\section{Introduction}",
                title="Introduction",
                label="sec:intro",
                body=r"""
\label{sec:intro}
This is the introduction.
""",
                all_labels=frozenset({"sec:intro"}),
            )
        },
    )


def test_no_labels():
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
This is some text.
\end{document}"""
    _assert_sections_metadata(
        input_latex,
        {
            "sec:Introduction": ExpectedStructuralMetadata(
                heading_source=r"\section{Introduction}",
                title="Introduction",
                label=None,
                body=r"""
This is some text.
""",
                all_labels=frozenset(),
            )
        },
    )


@pytest.mark.parametrize("filler", ["", "some text", "aa \n bbb \n ccc\n"])
def test_single_section_label(filler: str):
    """The section label should be detected even if it's not cleanly on first line"""
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}<FILLER>\label{sec:intro}
This is the introduction.
\end{document}""".replace("<FILLER>", filler)
    _assert_sections_metadata(
        input_latex,
        {
            "sec:Introduction": ExpectedStructuralMetadata(
                heading_source=r"\section{Introduction}",
                title="Introduction",
                label="sec:intro",
                body=(
                    filler
                    + r"""\label{sec:intro}
This is the introduction.
"""
                ),
                all_labels=frozenset({"sec:intro"}),
            )
        },
    )


def test_metadata_extraction_uses_long_title_from_optional_short_section_heading() -> (
    None
):
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section[Intro]{Introduction}
\label{sec:intro}
This is the introduction.
\subsection[Bg]{Background}
\label{sub:bg}
Background text.
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Introduction": ExpectedStructuralMetadata(
                heading_source=r"\section[Intro]{Introduction}",
                title="Introduction",
                label="sec:intro",
                body=r"""
\label{sec:intro}
This is the introduction.
""",
                all_labels=frozenset({"sec:intro", "sub:bg"}),
            ),
            "sub:Background": ExpectedStructuralMetadata(
                heading_source=r"\subsection[Bg]{Background}",
                title="Background",
                label="sub:bg",
                body=r"""
\label{sub:bg}
Background text.
""",
                all_labels=frozenset({"sub:bg"}),
            ),
        },
    )


def test_unnumbered_section_is_ignored_as_structural_node() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section*{Overview}
Prelude text.
\section{Main}
\label{sec:main}
Main text.
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Main": ExpectedStructuralMetadata(
                heading_source=r"\section{Main}",
                title="Main",
                label="sec:main",
                body=r"""
\label{sec:main}
Main text.
""",
                all_labels=frozenset({"sec:main"}),
            )
        },
    )


def test_unnumbered_subsection_remains_in_section_body() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Main}
\label{sec:main}
Intro text.
\subsection*{Ignored detail}
Still section content.
\subsection{Detail}
\label{sub:detail}
Detail text.
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Main": ExpectedStructuralMetadata(
                heading_source=r"\section{Main}",
                title="Main",
                label="sec:main",
                body=r"""
\label{sec:main}
Intro text.
\subsection*{Ignored detail}
Still section content.
""",
                all_labels=frozenset({"sec:main", "sub:detail"}),
            ),
            "sub:Detail": ExpectedStructuralMetadata(
                heading_source=r"\subsection{Detail}",
                title="Detail",
                label="sub:detail",
                body=r"""
\label{sub:detail}
Detail text.
""",
                all_labels=frozenset({"sub:detail"}),
            ),
        },
    )


def test_extract_labels_of_different_types():
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Methods}
\label{sec:methods}
This section describes our methods.
\begin{equation}
E = mc^2 \label{eq:einstein}
\end{equation}
\begin{figure}
\caption{A diagram} \label{fig:diagram}
\end{figure}
\begin{theorem} \label{thm:main}
This is our main theorem.
\end{theorem}
\end{document}"""
    _assert_sections_metadata(
        input_latex,
        {
            "sec:Methods": ExpectedStructuralMetadata(
                heading_source=r"\section{Methods}",
                title="Methods",
                label="sec:methods",
                body=r"""
\label{sec:methods}
This section describes our methods.
\begin{equation}
E = mc^2 \label{eq:einstein}
\end{equation}
\begin{figure}
\caption{A diagram} \label{fig:diagram}
\end{figure}
\begin{theorem} \label{thm:main}
This is our main theorem.
\end{theorem}
""",
                all_labels=frozenset(
                    {
                        "sec:methods",
                        "eq:einstein",
                        "fig:diagram",
                        "thm:main",
                    }
                ),
            )
        },
    )


def test_complex_label_names():
    """Test extraction of labels with complex naming schemes."""
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Results}
\label{sec:deep_learning_2024}
\begin{equation}
x = 1 \label{eq:loss_function-v2}
\end{equation}
\begin{figure}
\caption{Results} \label{fig:results.accuracy}
\end{figure}
\begin{table}
\caption{Comparison} \label{tab:comparison:models}
\end{table}
\end{document}"""
    _assert_sections_metadata(
        input_latex,
        {
            "sec:Results": ExpectedStructuralMetadata(
                heading_source=r"\section{Results}",
                title="Results",
                label="sec:deep_learning_2024",
                body=r"""
\label{sec:deep_learning_2024}
\begin{equation}
x = 1 \label{eq:loss_function-v2}
\end{equation}
\begin{figure}
\caption{Results} \label{fig:results.accuracy}
\end{figure}
\begin{table}
\caption{Comparison} \label{tab:comparison:models}
\end{table}
""",
                all_labels=frozenset(
                    {
                        "sec:deep_learning_2024",
                        "eq:loss_function-v2",
                        "fig:results.accuracy",
                        "tab:comparison:models",
                    }
                ),
            )
        },
    )


def test_multiple_sections_with_different_labels() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
Basic introduction.
\section{Methods}
\label{sec:methods}
\begin{equation}
y = mx + b \label{eq:linear}
\end{equation}
\section{Results}
\label{sec:results}
Results with no additional labels.
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Introduction": ExpectedStructuralMetadata(
                heading_source=r"\section{Introduction}",
                title="Introduction",
                label="sec:intro",
                body=r"""
\label{sec:intro}
Basic introduction.
""",
                all_labels=frozenset({"sec:intro"}),
            ),
            "sec:Methods": ExpectedStructuralMetadata(
                heading_source=r"\section{Methods}",
                title="Methods",
                label="sec:methods",
                body=r"""
\label{sec:methods}
\begin{equation}
y = mx + b \label{eq:linear}
\end{equation}
""",
                all_labels=frozenset({"sec:methods", "eq:linear"}),
            ),
            "sec:Results": ExpectedStructuralMetadata(
                heading_source=r"\section{Results}",
                title="Results",
                label="sec:results",
                body=r"""
\label{sec:results}
Results with no additional labels.
""",
                all_labels=frozenset({"sec:results"}),
            ),
        },
    )


def test_handle_nested_labels_for_an_unlabeled_section() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Results}
Here is the key equation:
\begin{equation}
E = mc^2 \label{eq:einstein}
\end{equation}
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Results": ExpectedStructuralMetadata(
                heading_source=r"\section{Results}",
                title="Results",
                label=None,
                body=r"""
Here is the key equation:
\begin{equation}
E = mc^2 \label{eq:einstein}
\end{equation}
""",
                all_labels=frozenset({"eq:einstein"}),
            )
        },
    )


def test_nested_labels() -> None:
    input_latex = r"""\documentclass{article}
\begin{document}
\maketitle
\section{Section A}
\label{sec:a}
Content
\subsection{Subsection B}
\label{subsec:b}
More content
\begin{equation}
\label{eq:1}
1=1
\end{equation}
\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Section A": ExpectedStructuralMetadata(
                heading_source=r"\section{Section A}",
                title="Section A",
                label="sec:a",
                body=r"""
\label{sec:a}
Content
""",
                all_labels=frozenset({"sec:a", "subsec:b", "eq:1"}),
            ),
            "sub:Subsection B": ExpectedStructuralMetadata(
                heading_source=r"\subsection{Subsection B}",
                title="Subsection B",
                label="subsec:b",
                body=r"""
\label{subsec:b}
More content
\begin{equation}
\label{eq:1}
1=1
\end{equation}
""",
                all_labels=frozenset({"subsec:b", "eq:1"}),
            ),
        },
    )


def test_all_labels_includes_subsection_labels() -> None:
    r"""Section blocks must include labels from their subsections."""
    input_latex = r"""\documentclass{article}

\begin{document}
\maketitle

\section{Main}
\label{sec:main}
Intro.

\subsection{Sub}
\label{subsec:sub}
Content.

\end{document}"""

    _assert_sections_metadata(
        input_latex,
        {
            "sec:Main": ExpectedStructuralMetadata(
                heading_source=r"\section{Main}",
                title="Main",
                label="sec:main",
                body=r"""
\label{sec:main}
Intro.

""",
                all_labels=frozenset({"sec:main", "subsec:sub"}),
            ),
            "sub:Sub": ExpectedStructuralMetadata(
                heading_source=r"\subsection{Sub}",
                title="Sub",
                label="subsec:sub",
                body=r"""
\label{subsec:sub}
Content.

""",
                all_labels=frozenset({"subsec:sub"}),
            ),
        },
    )
