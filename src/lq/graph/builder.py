from dataclasses import dataclass

from lq.graph.data_model import (
    GraphEdge,
    GraphNode,
    GraphNodeId,
    GraphNodeKind,
    GraphWarning,
    ReferenceGraph,
)
from lq.graph.reference_extractor import extract_references
from lq.latex_interface.data_model import (
    LatexBlockKind,
    LatexDocument,
    LatexLabel,
    LatexStructuralBlock,
)
from lq.query.s4_document_index import build_document_index


@dataclass
class _EdgeAccumulator:
    target_referenced_labels: list[LatexLabel]


def build_reference_graph(document: LatexDocument) -> ReferenceGraph:
    document_index = build_document_index(document)
    nodes = _build_nodes(document_index.blocks)
    node_positions = {node.node_id: position for position, node in enumerate(nodes)}

    edge_accumulators: dict[tuple[GraphNodeId, GraphNodeId], _EdgeAccumulator] = {}
    warnings: list[GraphWarning] = []

    for block in document_index.blocks:
        references = extract_references(block.body)
        if not references:
            continue

        if block.label is None:
            warnings.append(_build_unlabeled_source_warning(block))
            continue

        source_node_id = block.label

        for reference in references:
            target_block = document_index.containing_label_lookup.get(
                reference.referenced_label
            )
            if target_block is None:
                if reference.referenced_label in document_index.all_source_labels:
                    warnings.append(
                        _build_label_without_selectable_node_warning(
                            block,
                            reference.referenced_label,
                        )
                    )
                    continue

                warnings.append(
                    _build_missing_reference_label_warning(
                        block,
                        reference.referenced_label,
                    )
                )
                continue

            if target_block.label is None:
                warnings.append(
                    _build_unlabeled_target_warning(
                        block,
                        reference.referenced_label,
                        target_block,
                    )
                )
                continue

            _accumulate_edge(
                edge_accumulators,
                source_node_id,
                target_block.label,
                reference.referenced_label,
            )

    edges = _build_edges(edge_accumulators, node_positions)

    return ReferenceGraph(
        nodes=nodes,
        edges=edges,
        warnings=tuple(warnings),
    )


def _build_nodes(blocks: tuple[LatexStructuralBlock, ...]) -> tuple[GraphNode, ...]:
    nodes: list[GraphNode] = []
    current_section_node_id: GraphNodeId | None = None
    section_sibling_order = 0
    subsection_sibling_order = 0

    for block in blocks:
        if not block.is_selectable_structural_node:
            continue

        node_id = _require_block_label(block)
        block_kind = _graph_block_kind(block)

        if block_kind == "section":
            current_section_node_id = node_id
            parent_node_id = None
            sibling_order = section_sibling_order
            section_sibling_order += 1
            subsection_sibling_order = 0
        elif current_section_node_id is None:
            raise ValueError(
                "Expected subsection node to have a parent section in graph builder."
            )
        else:
            parent_node_id = current_section_node_id
            sibling_order = subsection_sibling_order
            subsection_sibling_order += 1

        nodes.append(
            GraphNode(
                node_id=node_id,
                parent_node_id=parent_node_id,
                document_order=len(nodes),
                sibling_order=sibling_order,
                title=_require_block_title(block),
                kind=block_kind,
                in_appendix=block.in_appendix,
            )
        )

    return tuple(nodes)


def _accumulate_edge(
    edge_accumulators: dict[tuple[GraphNodeId, GraphNodeId], _EdgeAccumulator],
    source_node_id: GraphNodeId,
    target_node_id: GraphNodeId,
    referenced_label: LatexLabel,
) -> None:
    edge_key = (source_node_id, target_node_id)
    edge_accumulator = edge_accumulators.get(edge_key)

    if edge_accumulator is None:
        edge_accumulator = _EdgeAccumulator(
            target_referenced_labels=[],
        )
        edge_accumulators[edge_key] = edge_accumulator

    edge_accumulator.target_referenced_labels.append(referenced_label)


def _build_edges(
    edge_accumulators: dict[tuple[GraphNodeId, GraphNodeId], _EdgeAccumulator],
    node_positions: dict[GraphNodeId, int],
) -> tuple[GraphEdge, ...]:
    edge_items = sorted(
        edge_accumulators.items(),
        key=lambda item: (
            node_positions[item[0][0]],
            node_positions[item[0][1]],
        ),
    )

    return tuple(
        GraphEdge(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            target_referenced_labels=tuple(edge_accumulator.target_referenced_labels),
        )
        for (source_node_id, target_node_id), edge_accumulator in edge_items
    )


def _build_unlabeled_source_warning(block: LatexStructuralBlock) -> GraphWarning:
    title = _require_block_title(block)
    node_kind = _graph_block_kind(block)
    return GraphWarning(
        code="unlabeled_source_node",
        message=(f"Skipped outgoing references from unlabeled {node_kind} '{title}'."),
        source_node_id=None,
        source_node_title=title,
        source_node_kind=node_kind,
        referenced_label=None,
        target_node_label=None,
        target_node_title=None,
        target_node_kind=None,
    )


def _build_unlabeled_target_warning(
    source_block: LatexStructuralBlock,
    referenced_label: LatexLabel,
    target_block: LatexStructuralBlock,
) -> GraphWarning:
    source_label = _require_block_label(source_block)
    source_title = _require_block_title(source_block)
    target_title = _require_block_title(target_block)

    source_kind = _graph_block_kind(source_block)
    target_kind = _graph_block_kind(target_block)

    return GraphWarning(
        code="unlabeled_target_node",
        message=(
            f"Skipped reference '{referenced_label}' from {source_label} "
            f"because its containing {target_kind} node '{target_title}' is unlabeled."
        ),
        source_node_id=source_label,
        source_node_title=source_title,
        source_node_kind=source_kind,
        referenced_label=referenced_label,
        target_node_label=target_block.label,
        target_node_title=target_title,
        target_node_kind=target_kind,
    )


def _build_missing_reference_label_warning(
    source_block: LatexStructuralBlock,
    referenced_label: LatexLabel,
) -> GraphWarning:
    source_label = _require_block_label(source_block)

    return GraphWarning(
        code="missing_reference_label",
        message=(
            f"Skipped reference '{referenced_label}' from {source_label} "
            "because the label does not exist in the parsed document."
        ),
        source_node_id=source_label,
        source_node_title=_require_block_title(source_block),
        source_node_kind=_graph_block_kind(source_block),
        referenced_label=referenced_label,
        target_node_label=None,
        target_node_title=None,
        target_node_kind=None,
    )


def _build_label_without_selectable_node_warning(
    source_block: LatexStructuralBlock,
    referenced_label: LatexLabel,
) -> GraphWarning:
    source_label = _require_block_label(source_block)

    return GraphWarning(
        code="reference_label_without_selectable_node",
        message=(
            f"Skipped reference '{referenced_label}' from {source_label} "
            "because the label exists but is outside selectable structural nodes."
        ),
        source_node_id=source_label,
        source_node_title=_require_block_title(source_block),
        source_node_kind=_graph_block_kind(source_block),
        referenced_label=referenced_label,
        target_node_label=None,
        target_node_title=None,
        target_node_kind=None,
    )


def _require_block_title(block: LatexStructuralBlock) -> str:
    if block.title is None:
        raise ValueError(
            f"Expected {block.kind.value} block to have a title in graph builder."
        )
    return block.title


def _require_block_label(block: LatexStructuralBlock) -> LatexLabel:
    if block.label is None:
        raise ValueError(
            f"Expected {block.kind.value} block to have a direct label in graph builder."
        )
    return block.label


def _graph_block_kind(block: LatexStructuralBlock) -> GraphNodeKind:
    if block.kind is LatexBlockKind.section:
        return "section"
    if block.kind is LatexBlockKind.subsection:
        return "subsection"
    raise ValueError("pre_section blocks are not graph nodes")
