from dataclasses import dataclass

from lq.query import LatexQueryText, QueryOutputMode


@dataclass(frozen=True)
class SelectionQueryRequest:
    query_text: LatexQueryText
    output_mode: QueryOutputMode
