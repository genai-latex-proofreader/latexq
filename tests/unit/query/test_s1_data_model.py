from lq.query.s1_data_model import (
    AppendixExpr,
    ContainingLabelExpr,
    DirectLabelExpr,
    InvalidBareTypeError,
    LabelRangeExpr,
    MissingLabelError,
    NoSelectableContainerError,
    NonQueryableDirectLabelError,
    PrefixExpr,
    Query,
    QueryErrorCode,
    QueryNodeType,
    RenderModifier,
    Selector,
    SelectorScope,
    SourcePosition,
    SourceSpan,
    SuffixExpr,
    WildcardExpr,
)


def test_query_preserves_selector_order_and_shape():
    query = Query(
        selectors=(
            Selector(
                expression=DirectLabelExpr(label="sec:intro"),
                scopes=(SelectorScope.appendix_only(),),
                render_modifier=RenderModifier(preview_paragraph_limit=3),
            ),
            Selector(expression=AppendixExpr()),
        )
    )

    assert query.selectors == (
        Selector(
            expression=DirectLabelExpr(label="sec:intro"),
            scopes=(SelectorScope.appendix_only(),),
            render_modifier=RenderModifier(preview_paragraph_limit=3),
        ),
        Selector(expression=AppendixExpr()),
    )
    assert query.selectors[1].expression.kind.value == "appendix"


def test_expression_dataclasses_build_expected_variants():
    assert DirectLabelExpr(label="sec:intro").kind.value == "direct_label"
    assert ContainingLabelExpr(label="eq:key").kind.value == "containing_label"
    assert PrefixExpr(end_label="sec:end").end_label == "sec:end"
    assert SuffixExpr(start_label="sec:start").start_label == "sec:start"
    assert LabelRangeExpr(
        start_label="sec:start", end_label="sec:end"
    ) == LabelRangeExpr(
        start_label="sec:start",
        end_label="sec:end",
    )
    assert (
        WildcardExpr(node_type=QueryNodeType.section).node_type is QueryNodeType.section
    )
    assert AppendixExpr().kind.value == "appendix"


def test_source_locations_are_preserved_on_ast_nodes():
    span = SourceSpan(
        start=SourcePosition(offset=2, line=1, column=3),
        end=SourcePosition(offset=11, line=1, column=12),
    )

    selector = Selector(
        expression=DirectLabelExpr(label="sec:intro", span=span),
        scopes=(SelectorScope.main_only(span=span),),
        render_modifier=RenderModifier(preview_paragraph_limit=0, span=span),
        span=span,
    )

    assert selector.span == span
    assert selector.expression.span == span
    assert selector.scopes[0].span == span
    assert selector.render_modifier is not None
    assert selector.render_modifier.span == span


def test_render_modifier_rejects_negative_preview_limit():
    try:
        RenderModifier(preview_paragraph_limit=-1)
    except ValueError as exc:
        assert "preview_paragraph_limit" in str(exc)
    else:
        raise AssertionError("RenderModifier accepted a negative preview limit")


def test_source_position_rejects_invalid_coordinates():
    try:
        SourcePosition(offset=-1, line=1, column=1)
    except ValueError as exc:
        assert "offset" in str(exc)
    else:
        raise AssertionError("SourcePosition accepted a negative offset")


def test_missing_label_error_has_stable_code_and_message():
    error = MissingLabelError("sec:missing")

    assert error.code is QueryErrorCode.missing_label
    assert error.label == "sec:missing"
    assert str(error) == "E1: Missing label 'sec:missing'."


def test_semantic_query_errors_preserve_specific_context():
    e6 = NonQueryableDirectLabelError("eq:main")
    e7 = NoSelectableContainerError("front:intro")

    assert e6.code is QueryErrorCode.non_queryable_direct_label
    assert e6.label == "eq:main"
    assert "direct-label selector family" in e6.message
    assert e7.code is QueryErrorCode.no_selectable_container
    assert e7.label == "front:intro"
    assert "@@label" in e7.message


def test_invalid_bare_type_error_uses_e3_code():
    error = InvalidBareTypeError("sec")

    assert error.code is QueryErrorCode.invalid_bare_type
    assert str(error) == "E3: Invalid bare type 'sec'. Only bare 'app' is allowed."
