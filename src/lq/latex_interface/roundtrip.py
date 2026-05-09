from lq.latex_interface.data_model import LatexContent, to_latex
from lq.latex_interface.parser import parse_from_latex


class LatexRoundtripValidationError(Exception):
    """Raised when generated LaTeX does not survive parser roundtrip validation."""


def validate_latex_roundtrip(latex_content: LatexContent) -> None:
    """Validate that generated LaTeX survives parse -> to_latex unchanged."""
    try:
        parsed_document = parse_from_latex(latex_content)
    except Exception as error:
        raise LatexRoundtripValidationError(
            f"generated LaTeX could not be parsed during roundtrip validation: {error}"
        ) from error

    if to_latex(parsed_document) != latex_content:
        raise LatexRoundtripValidationError(
            "generated LaTeX changed during parse -> to_latex roundtrip validation"
        )
