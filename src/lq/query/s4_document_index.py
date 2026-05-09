from collections.abc import Mapping
from dataclasses import dataclass
from functools import cached_property
from types import MappingProxyType

from lq.latex_interface.data_model import (
    LatexBlockKind,
    LatexDocument,
    LatexLabel,
    LatexStructuralBlock,
)


@dataclass(frozen=True)
class DocumentIndex:
    """Compact query-evaluation view over LatexDocument structural content.

    This helper keeps the canonical ordered structural block stream plus the
    set of all labels seen anywhere in the parsed document. Everything else is
    derived from those two pieces of state so the representation stays small.
    Derived properties are computed once for each DocumentIndex and reused on
    later access. Lookup mappings are exposed as immutable views so callers
    cannot mutate cached index state.
    """

    blocks: tuple[LatexStructuralBlock, ...]
    all_source_labels: frozenset[LatexLabel]

    @cached_property
    def direct_label_lookup(self) -> Mapping[LatexLabel, LatexStructuralBlock]:
        """Map queryable direct structural labels to their structural blocks.

        The returned mapping is immutable.
        """
        return MappingProxyType(
            {block.label: block for block in self.blocks if block.label is not None}
        )

    @cached_property
    def containing_label_lookup(self) -> Mapping[LatexLabel, LatexStructuralBlock]:
        """Map any in-node source label to its nearest selectable container.

        The returned mapping is immutable.
        """
        return MappingProxyType(_build_containing_label_lookup(self.blocks))

    @cached_property
    def section_blocks(self) -> tuple[LatexStructuralBlock, ...]:
        """Return only section blocks from the ordered structural stream."""
        return tuple(
            block for block in self.blocks if block.kind is LatexBlockKind.section
        )

    @cached_property
    def subsection_blocks(self) -> tuple[LatexStructuralBlock, ...]:
        """Return only subsection blocks from the ordered structural stream."""
        return tuple(
            block for block in self.blocks if block.kind is LatexBlockKind.subsection
        )

    @cached_property
    def _appendix_start_index(self) -> int | None:
        """Return the first appendix block position, if the document has appendix blocks."""
        return next(
            (index for index, block in enumerate(self.blocks) if block.in_appendix),
            None,
        )

    @cached_property
    def _main_block_count(self) -> int:
        """Count how many selectable blocks belong to the main body."""
        appendix_start_index = self._appendix_start_index
        return (
            appendix_start_index
            if appendix_start_index is not None
            else len(self.blocks)
        )

    @cached_property
    def main_blocks(self) -> tuple[LatexStructuralBlock, ...]:
        """Return the main-body slice of the structural block stream."""
        return self.blocks[: self._main_block_count]

    @cached_property
    def appendix_blocks(self) -> tuple[LatexStructuralBlock, ...]:
        """Return the appendix slice of the structural block stream."""
        if self._appendix_start_index is None:
            return ()
        return self.blocks[self._appendix_start_index :]

    @cached_property
    def _block_positions(self) -> Mapping[int, int]:
        return MappingProxyType(
            {id(block): index for index, block in enumerate(self.blocks)}
        )

    def prefix_through(
        self, block: LatexStructuralBlock
    ) -> tuple[LatexStructuralBlock, ...]:
        """Return the selectable prefix ending at block within its document part."""
        end_index = self._position_of(block)
        start_index = self._main_block_count if block.in_appendix else 0
        return self.blocks[start_index : end_index + 1]

    def suffix_from(
        self, block: LatexStructuralBlock
    ) -> tuple[LatexStructuralBlock, ...]:
        """Return the selectable suffix starting at block within its document part."""
        start_index = self._position_of(block)
        end_index = len(self.blocks) if block.in_appendix else self._main_block_count
        return self.blocks[start_index:end_index]

    def between(
        self,
        start_block: LatexStructuralBlock,
        end_block: LatexStructuralBlock,
    ) -> tuple[LatexStructuralBlock, ...]:
        """Return the inclusive block range between start_block and end_block."""
        start_index = self._position_of(start_block)
        end_index = self._position_of(end_block)
        if end_index < start_index:
            raise ValueError("end block must not precede start block")
        return self.blocks[start_index : end_index + 1]

    def _position_of(self, block: LatexStructuralBlock) -> int:
        try:
            position = self._block_positions[id(block)]
        except KeyError as error:
            raise ValueError("block is not part of this document index") from error
        if self.blocks[position] is not block:
            raise ValueError("block identity does not match this document index")
        return position


def build_document_index(document: LatexDocument) -> DocumentIndex:
    """Build the query-facing structural index for one parsed document."""
    return DocumentIndex(
        blocks=tuple(document.iter_structural_blocks()),
        all_source_labels=document.all_source_labels,
    )


def _build_containing_label_lookup(
    blocks: tuple[LatexStructuralBlock, ...],
) -> dict[LatexLabel, LatexStructuralBlock]:
    """Map each in-node label to the nearest structural section/subsection node."""
    containing_label_lookup: dict[LatexLabel, LatexStructuralBlock] = {}

    # In LatexBlock, the all_labels attribute lists all labels in that
    # section/subsection. A subsection label is therefore listed twice: Both
    # in the subsection, and in the parent section. Therefore we traverse nodes in
    # reverse order (starting with subsections). This way, each label resolves to the
    # nearest structural node.
    for block in reversed(blocks):
        for label in block.all_labels:
            if label not in containing_label_lookup:
                containing_label_lookup[label] = block

    return containing_label_lookup
