from typing import Literal

from lq.graph.data_model import ExtractedReference
from lq.latex_interface.data_model import LatexContent, LatexLabel
from lq.latex_interface.s6_content_helpers import (
    _iter_required_group_arguments_in_text,
)

ReferenceCommandName = Literal[
    "ref",
    "eqref",
    "vref",
    "autoref",
    "pageref",
    "nameref",
    "cref",
    "Cref",
]

SUPPORTED_REFERENCE_COMMAND_NAMES: frozenset[ReferenceCommandName] = frozenset(
    {
        "ref",
        "eqref",
        "vref",
        "autoref",
        "pageref",
        "nameref",
        "cref",
        "Cref",
    }
)


def extract_references(content: LatexContent) -> tuple[ExtractedReference, ...]:
    references: list[ExtractedReference] = []

    for required_group_arguments in _iter_required_group_arguments_in_text(
        content,
        SUPPORTED_REFERENCE_COMMAND_NAMES,
    ):
        references.extend(
            ExtractedReference(referenced_label=referenced_label)
            for referenced_label in _extract_label_arguments(required_group_arguments)
        )

    return tuple(references)


def _extract_label_arguments(
    arguments: tuple[LatexContent, ...],
) -> tuple[LatexLabel, ...]:
    if not arguments:
        return tuple()

    return tuple(
        label
        for label in (part.strip() for part in arguments[0].split(","))
        if label != ""
    )
