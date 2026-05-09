import pytest

from lq.latex_interface.s6_content_helpers import (
    collect_labels,
    content_has_any_label,
    split_leading_label_command,
)


def test_collect_labels_recurses_into_nested_environments_and_groups():
    content = r"""\section{Results}
\label{sec:results}
\begin{figure}
\caption{Main result \label{fig:main}}
\end{figure}
\begin{equation}
\label{eq:main}
x = 1
\end{equation}
"""

    assert collect_labels(content) == (
        "sec:results",
        "fig:main",
        "eq:main",
    )


def test_content_has_any_label_detects_nested_group_label():
    content = r"""\begin{figure}
\caption{Main result \label{fig:main}}
\end{figure}
"""

    assert content_has_any_label(content) is True


def test_content_has_any_label_returns_false_when_no_label_exists():
    assert content_has_any_label("Visible text\n") is False


def test_collect_labels_rejects_nested_label_inside_label_argument():
    content = r"""\section{Results}
\label{foo \label{bar}}
"""

    with pytest.raises(
        ValueError,
        match=r"Unsupported nested \\label command inside \\label\{\.\.\.\}",
    ):
        collect_labels(content)


def test_split_leading_label_command_keeps_the_direct_label_prefix():
    content = r"""\label{sec:results}
Visible text
"""

    assert split_leading_label_command(content) == (
        r"""\label{sec:results}
""",
        "Visible text\n",
    )


def test_split_leading_label_command_stops_at_leading_comment():
    content = r"""% keep comment first
\label{sec:results}
Visible text
"""

    assert split_leading_label_command(content) == ("", content)
