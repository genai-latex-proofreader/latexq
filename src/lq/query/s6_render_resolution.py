from lq.latex_interface.data_model import LatexStructuralBlock
from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    LabelRangeExpr,
    PrefixExpr,
    RenderModifier,
    Selector,
    SuffixExpr,
    WildcardExpr,
)
from lq.query.s4_document_index import DocumentIndex
from lq.query.s5_evaluator import EvaluatedSelector

type ResolvedRenderDecision = tuple[LatexStructuralBlock, RenderModifier | None]


def resolve_render_decisions(
    document_index: DocumentIndex,
    evaluated_selectors: tuple[EvaluatedSelector, ...],
) -> tuple[ResolvedRenderDecision, ...]:
    """Resolve selector precedence and render modifiers per node."""

    winners: dict[int, tuple[int, ResolvedRenderDecision]] = {}
    for evaluated_selector in evaluated_selectors:
        candidate_selector = evaluated_selector.selector
        candidate_tier = _selector_precedence_tier(candidate_selector)
        for block in evaluated_selector.blocks:
            block_key = id(block)
            candidate = (block, candidate_selector.render_modifier)
            winner = winners.get(block_key)
            if winner is None or _candidate_wins(
                candidate,
                candidate_tier,
                winner[1],
                winner[0],
            ):
                winners[block_key] = (candidate_tier, candidate)

    return tuple(
        winners[id(block)][1] for block in document_index.blocks if id(block) in winners
    )


def _candidate_wins(
    candidate: ResolvedRenderDecision,
    candidate_tier: int,
    incumbent: ResolvedRenderDecision,
    incumbent_tier: int,
) -> bool:
    if candidate_tier != incumbent_tier:
        return candidate_tier < incumbent_tier

    return _render_modifier_wins(
        candidate[1],
        incumbent[1],
    )


def _selector_precedence_tier(selector: Selector) -> int:
    expression = selector.expression

    if isinstance(expression, DirectLabelExpr | ContainingLabelExpr):
        return 0

    if isinstance(expression, PrefixExpr | SuffixExpr | LabelRangeExpr):
        return 1

    if isinstance(expression, AppendixExpr):
        return 2

    if isinstance(expression, WildcardExpr):
        return 2 if selector.scopes else 3

    raise TypeError(f"Unsupported selector expression: {type(expression)!r}")


def _render_modifier_wins(
    candidate: RenderModifier | None,
    incumbent: RenderModifier | None,
) -> bool:
    if candidate is None:
        return incumbent is not None

    if incumbent is None:
        return False

    return candidate.preview_paragraph_limit > incumbent.preview_paragraph_limit
