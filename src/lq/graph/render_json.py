import json
from pathlib import Path

from lq.graph.data_model import GraphEdge, GraphNode, GraphWarning, ReferenceGraph
from lq.latex_interface.data_model import LatexLabel


def render_json(
    reference_graph: ReferenceGraph,
    label_source_files: dict[LatexLabel, Path],
) -> str:
    return json.dumps(
        {
            "nodes": [
                _node_to_json(node, label_source_files)
                for node in reference_graph.nodes
            ],
            "edges": [_edge_to_json(edge) for edge in reference_graph.edges],
            "warnings": [
                _warning_to_json(warning) for warning in reference_graph.warnings
            ],
        },
        indent=2,
    )


def _node_to_json(
    node: GraphNode,
    label_source_files: dict[LatexLabel, Path],
) -> dict[str, object]:
    source_file_path = label_source_files.get(node.node_id)
    return {
        "kind": node.kind,
        "label": node.node_id,
        "parent": node.parent_node_id,
        "document_order": node.document_order,
        "sibling_order": node.sibling_order,
        "title": node.title,
        "in_appendix": node.in_appendix,
        "source_file": str(source_file_path) if source_file_path is not None else None,
    }


def _edge_to_json(edge: GraphEdge) -> dict[str, object]:
    return {
        "source": edge.source_node_id,
        "target": edge.target_node_id,
        "count": edge.count,
        "target_referenced_labels": list(edge.target_referenced_labels),
    }


def _warning_to_json(warning: GraphWarning) -> dict[str, object]:
    return {
        "code": warning.code,
        "message": warning.message,
        "source_node_id": warning.source_node_id,
        "source_node_title": warning.source_node_title,
        "source_node_kind": warning.source_node_kind,
        "referenced_label": warning.referenced_label,
        "target_node_label": warning.target_node_label,
        "target_node_title": warning.target_node_title,
        "target_node_kind": warning.target_node_kind,
    }
