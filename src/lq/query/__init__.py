from lq.latex_interface.data_model import LatexContent
from lq.latex_interface.parser import parse_from_latex
from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    InvalidBareTypeError,
    InvalidBracketError,
    InvalidScopeError,
    InvertedRangeError,
    LabelRangeExpr,
    LatexQueryText,
    MissingLabelError,
    NonQueryableDirectLabelError,
    NoSelectableContainerError,
    PrefixExpr,
    Query,
    QueryError,
    QueryErrorCode,
    QueryExpressionKind,
    QueryNodeType,
    QueryOutputMode,
    QuerySyntaxError,
    RenderModifier,
    Selector,
    SelectorScope,
    SelectorScopeKind,
    SourcePosition,
    SourceSpan,
    SuffixExpr,
    WildcardExpr,
)
from lq.query.s2_tokenizer import QueryToken, QueryTokenKind, tokenize_query
from lq.query.s3_parser import parse_query, parse_query_tokens
from lq.query.s4_document_index import (
    DocumentIndex,
    build_document_index,
)
from lq.query.s5_evaluator import (
    EvaluatedSelector,
    evaluate_query,
)
from lq.query.s6_node_renderer import (
    SECTION_TRUNCATION_NOTICE,
    SUBSECTION_TRUNCATION_NOTICE,
    render_structural_node,
)
from lq.query.s6_render_resolution import (
    ResolvedRenderDecision,
    resolve_render_decisions,
)
from lq.query.s6_renderer import (
    render_query_fragment,
    render_query_latex,
    render_query_output,
)


def render_query_from_latex(
    document_latex: LatexContent,
    query_text: LatexQueryText,
    output_mode: QueryOutputMode,
) -> LatexContent:
    """Render one lq query directly from raw LaTeX input.

    This is the main public interface for applying the lq query pipeline to a
    LaTeX document string. It parses the LaTeX into the lq document model,
    parses and evaluates the query, resolves render precedence, and returns the
    rendered result in the requested output mode.
    """
    document = parse_from_latex(document_latex)
    document_index = build_document_index(document)
    evaluated = evaluate_query(document_index, parse_query(query_text))
    render_decisions = resolve_render_decisions(document_index, evaluated)
    return render_query_output(document, render_decisions, output_mode)


__all__ = [
    "AppendixExpr",
    "ContainingLabelExpr",
    "DocumentIndex",
    "DirectLabelExpr",
    "EvaluatedSelector",
    "InvalidBareTypeError",
    "InvalidBracketError",
    "InvalidScopeError",
    "InvertedRangeError",
    "LabelRangeExpr",
    "MissingLabelError",
    "NoSelectableContainerError",
    "NonQueryableDirectLabelError",
    "PrefixExpr",
    "QueryOutputMode",
    "Query",
    "QueryError",
    "QueryErrorCode",
    "QueryExpressionKind",
    "QueryNodeType",
    "QuerySyntaxError",
    "QueryToken",
    "QueryTokenKind",
    "RenderModifier",
    "ResolvedRenderDecision",
    "Selector",
    "SelectorScope",
    "SelectorScopeKind",
    "SourcePosition",
    "SourceSpan",
    "SuffixExpr",
    "SECTION_TRUNCATION_NOTICE",
    "SUBSECTION_TRUNCATION_NOTICE",
    "LatexQueryText",
    "WildcardExpr",
    "build_document_index",
    "evaluate_query",
    "parse_query",
    "parse_query_tokens",
    "render_query_fragment",
    "render_query_from_latex",
    "render_query_latex",
    "render_query_output",
    "render_structural_node",
    "resolve_render_decisions",
    "tokenize_query",
]
