from dataclasses import dataclass

from lq.latex_interface.data_model import LatexLabel, LatexStructuralBlock
from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    InvertedRangeError,
    LabelRangeExpr,
    MissingLabelError,
    NonQueryableDirectLabelError,
    NoSelectableContainerError,
    PrefixExpr,
    Query,
    QueryNodeType,
    Selector,
    SelectorScope,
    SelectorScopeKind,
    SourceSpan,
    SuffixExpr,
    WildcardExpr,
)
from lq.query.s4_document_index import DocumentIndex


@dataclass(frozen=True)
class EvaluatedSelector:
    """One selector together with its evaluated structural-block result set."""

    selector: Selector
    blocks: tuple[LatexStructuralBlock, ...]


def evaluate_query(
    document_index: DocumentIndex,
    query: Query,
) -> tuple[EvaluatedSelector, ...]:
    """Evaluate a parsed query into per-selector results.

    This is the main evaluator entry point intended for later query phases.
    """

    evaluated_selectors: list[EvaluatedSelector] = []
    for selector in query.selectors:
        blocks = _evaluate_expression(document_index, selector)
        for scope in selector.scopes:
            blocks = _apply_scope(blocks, scope)
        evaluated_selectors.append(EvaluatedSelector(selector=selector, blocks=blocks))

    return tuple(evaluated_selectors)


def _apply_scope(
    blocks: tuple[LatexStructuralBlock, ...],
    scope: SelectorScope,
) -> tuple[LatexStructuralBlock, ...]:
    if scope.kind is SelectorScopeKind.appendix_only:
        return tuple(block for block in blocks if block.in_appendix)
    if scope.kind is SelectorScopeKind.main_only:
        return tuple(block for block in blocks if not block.in_appendix)
    raise TypeError(f"Unsupported selector scope: {scope.kind!r}")


def _evaluate_expression(
    document_index: DocumentIndex,
    selector: Selector,
) -> tuple[LatexStructuralBlock, ...]:
    expression = selector.expression
    span = expression.span

    if isinstance(expression, DirectLabelExpr):
        return (_resolve_direct_label(document_index, expression.label, span=span),)

    if isinstance(expression, ContainingLabelExpr):
        return (_resolve_containing_label(document_index, expression.label, span=span),)

    if isinstance(expression, PrefixExpr):
        end_block = _resolve_direct_label(
            document_index, expression.end_label, span=span
        )
        return document_index.prefix_through(end_block)

    if isinstance(expression, SuffixExpr):
        start_block = _resolve_direct_label(
            document_index,
            expression.start_label,
            span=span,
        )
        return document_index.suffix_from(start_block)

    if isinstance(expression, LabelRangeExpr):
        try:
            return document_index.between(
                start_block=_resolve_direct_label(
                    document_index,
                    expression.start_label,
                    span=span,
                ),
                end_block=_resolve_direct_label(
                    document_index, expression.end_label, span=span
                ),
            )
        except ValueError as error:
            raise InvertedRangeError(
                expression.start_label,
                expression.end_label,
                span=span,
            ) from error

    if isinstance(expression, WildcardExpr):
        if expression.node_type is QueryNodeType.section:
            return document_index.section_blocks
        return document_index.subsection_blocks

    if isinstance(expression, AppendixExpr):
        return document_index.appendix_blocks

    raise TypeError(f"Unsupported selector expression: {type(expression)!r}")


def _resolve_direct_label(
    document_index: DocumentIndex,
    label: LatexLabel,
    *,
    span: SourceSpan | None,
) -> LatexStructuralBlock:
    node = document_index.direct_label_lookup.get(label)
    if node is not None:
        return node
    if label in document_index.all_source_labels:
        raise NonQueryableDirectLabelError(label, span=span)
    raise MissingLabelError(label, span=span)


def _resolve_containing_label(
    document_index: DocumentIndex,
    label: LatexLabel,
    *,
    span: SourceSpan | None,
) -> LatexStructuralBlock:
    node = document_index.containing_label_lookup.get(label)
    if node is not None:
        return node
    if label in document_index.all_source_labels:
        raise NoSelectableContainerError(label, span=span)
    raise MissingLabelError(label, span=span)
