from dataclasses import dataclass
from typing import Literal

from lq.latex_interface.data_model import LatexLabel


# Graph node ids are labels of selectable structural nodes, i.e. sections/subsections.
GraphNodeId = LatexLabel

GraphNodeKind = Literal["section", "subsection"]

GraphWarningCode = Literal[
    "unlabeled_source_node",
    "unlabeled_target_node",
    "missing_reference_label",
    "reference_label_without_selectable_node",
]


@dataclass(frozen=True)
class ExtractedReference:
    referenced_label: LatexLabel


@dataclass(frozen=True)
class GraphNode:
    """Selectable structural node (section/subsection) in the reference graph.

    node_id is the direct structural label of that section/subsection.
    """

    node_id: GraphNodeId
    parent_node_id: GraphNodeId | None
    document_order: int
    sibling_order: int
    title: str
    kind: GraphNodeKind
    in_appendix: bool


@dataclass(frozen=True)
class GraphEdge:
    """Directed edge between two graph nodes via one or more target labels."""

    source_node_id: GraphNodeId
    target_node_id: GraphNodeId
    target_referenced_labels: tuple[LatexLabel, ...]

    def __post_init__(self) -> None:
        if len(self.target_referenced_labels) == 0:
            raise ValueError("GraphEdge must include at least one target label.")

    @property
    def count(self) -> int:
        return len(self.target_referenced_labels)


@dataclass(frozen=True)
class GraphWarning:
    code: GraphWarningCode
    message: str
    source_node_id: GraphNodeId | None
    source_node_title: str
    source_node_kind: GraphNodeKind
    referenced_label: LatexLabel | None
    target_node_label: LatexLabel | None
    target_node_title: str | None
    target_node_kind: GraphNodeKind | None


@dataclass(frozen=True)
class ReferenceGraph:
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    warnings: tuple[GraphWarning, ...]
