from collections.abc import Iterator
from pathlib import Path

from lq.graph.data_model import GraphEdge, GraphNode, ReferenceGraph
from lq.latex_interface.data_model import LatexLabel


def render_text(
    reference_graph: ReferenceGraph,
    label_source_files: dict[LatexLabel, Path],
) -> str:
    return "\n".join(_render_text_lines(reference_graph, label_source_files))


def _render_text_lines(
    reference_graph: ReferenceGraph,
    label_source_files: dict[LatexLabel, Path],
) -> Iterator[str]:
    yield "Nodes:"
    yield "Main body:"
    yield from _render_node_tree(
        nodes=reference_graph.nodes,
        in_appendix=False,
        label_source_files=label_source_files,
    )
    yield "Appendix:"
    yield from _render_node_tree(
        nodes=reference_graph.nodes,
        in_appendix=True,
        label_source_files=label_source_files,
    )

    yield ""
    yield "Edges:"
    yield from _render_edges(reference_graph.edges)


def _render_node_tree(
    *,
    nodes: tuple[GraphNode, ...],
    in_appendix: bool,
    label_source_files: dict[LatexLabel, Path],
) -> Iterator[str]:
    region_nodes = [node for node in nodes if node.in_appendix == in_appendix]

    if not region_nodes:
        yield "  (none)"
        return

    for node in region_nodes:
        source_file = _render_node_source_file(node, label_source_files)
        if node.parent_node_id is None:
            yield f"- {node.title} ({node.node_id} in {source_file})"
            continue

        yield f"  - {node.title} ({node.node_id} in {source_file})"


def _render_node_source_file(
    node: GraphNode,
    label_source_files: dict[LatexLabel, Path],
) -> str:
    source_file_path = label_source_files.get(node.node_id)
    if source_file_path is None:
        return "unknown"
    return str(source_file_path)


def _render_edges(edges: tuple[GraphEdge, ...]) -> Iterator[str]:
    if edges:
        yield from (_render_edge_line(edge) for edge in edges)
        return

    yield "(none)"


def _render_edge_line(edge: GraphEdge) -> str:
    return f"{edge.source_node_id} -> {edge.target_node_id} (x{edge.count})"
