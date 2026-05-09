from lq.latex_interface.data_model import to_latex
from lq.latex_interface.parser import parse_from_latex


def test_empty_appendix():
    latex_in = r"""\documentclass{article}
\begin{document}
\maketitle
Some content before appendix.
\appendix
\end{document}"""
    doc = parse_from_latex(latex_in)
    latex_out = to_latex(doc)
    assert r"\appendix" in latex_out
    assert latex_in == latex_out
