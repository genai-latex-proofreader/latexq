from lq.latex_interface.data_model import LatexContent
from lq.query import SECTION_TRUNCATION_NOTICE, SUBSECTION_TRUNCATION_NOTICE
from lq.query.s6_node_renderer import iter_paragraphs

BASELINE_FRAGMENT_BY_KEY: dict[str, LatexContent] = {
    "sec:1": r"""\section{Section 1}
\label{sec:1}
pre-matter

""",
    "sec:1a": r"""\subsection{Section 1a}
\label{sec:1a}
aaa

\begin{equation}
x = y  \label{eq:1a}
\end{equation}

bbb
bbb

""",
    "sec:1b": r"""\subsection{Section 1b}
aaa

bbb
bbb
\label{sec:1b}

""",
    "content-of-unlabeled-section-2": r"""\section{Section 2}
section two text

""",
    "sec:3": r"""\section{Section 3}
\label{sec:3}
ccc

ddd

""",
    "app:sec:A": r"""\section{Section A}
\label{app:sec:A}
appendix aaa

appendix bbb

""",
    "app:sec:B": r"""\section{Section B}
\label{app:sec:B}
appendix section b pre-matter

""",
    "app:sec:B1": r"""\subsection{Section B1}
\label{app:sec:B1}
appendix subsection b1 aaa

appendix subsection b1 bbb

""",
    "app:sec:B2": r"""\subsection{Section B2}
\label{app:sec:B2}
appendix subsection b2 aaa

appendix subsection b2 bbb

""",
}


def content_from_fragments(
    *keys: str,
    paragraph_limit: int | None = None,
) -> LatexContent:
    if paragraph_limit is None:
        return "".join(BASELINE_FRAGMENT_BY_KEY[key] for key in keys)

    return "".join(
        build_preview_fragment(
            BASELINE_FRAGMENT_BY_KEY[key],
            paragraph_limit=paragraph_limit,
        )
        for key in keys
    )


def build_preview_fragment(
    structural_fragment: LatexContent,
    paragraph_limit: int,
) -> LatexContent:
    """Build the expected preview rendering for one structural fragment.

    This mirrors lq's fragment renderer for `[pN]` modifiers, including
    preservation or reattachment of the node's direct label when truncation
    would otherwise remove it.
    """
    heading, body = structural_fragment.split("\n", maxsplit=1)
    body_lines = body.splitlines(keepends=True)
    leading_label_lines: list[LatexContent] = []
    direct_label_line = next(
        (line for line in body_lines if line.lstrip().startswith(r"\label{")),
        None,
    )

    while body_lines and body_lines[0].lstrip().startswith(r"\label{"):
        leading_label_lines.append(body_lines.pop(0))

    paragraphs = tuple(iter_paragraphs(body_lines))

    if len(paragraphs) <= paragraph_limit:
        return structural_fragment

    preview_body = "".join(
        "".join(paragraph) for paragraph in paragraphs[:paragraph_limit]
    )
    rendered_body = "".join(leading_label_lines) + preview_body
    if direct_label_line is not None and r"\label{" not in rendered_body:
        if rendered_body and not rendered_body.endswith("\n"):
            rendered_body += "\n"
        rendered_body += direct_label_line

    rendered_preview = heading + "\n" + rendered_body
    if rendered_preview and not rendered_preview.endswith("\n"):
        rendered_preview += "\n"

    truncation_notice = (
        SECTION_TRUNCATION_NOTICE
        if heading.startswith(r"\section{")
        else SUBSECTION_TRUNCATION_NOTICE
    )
    return rendered_preview + "\n" + truncation_notice
