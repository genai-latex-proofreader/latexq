"""Roundtrip testing

Test that sending a LaTeX document through

  parser -> lq internal data model -> to_latex

reproduces the original LaTeX string exactly, for a large number of structurally
different documents."""

import itertools as it
from collections.abc import Callable, Iterator
from dataclasses import dataclass, replace

from tests.acceptance.latex_roundtrip.latex_generator import (
    ContentRegion,
    LatexBlueprint,
    SectionSpec,
    SubsectionSpec,
    render,
)
from lq.latex_interface.data_model import to_latex
from lq.latex_interface.parser import parse_from_latex

# ---------------------------------------------------------------------------
# Fixed content used across all blueprints
# ---------------------------------------------------------------------------

PRE_MATTER = r"""\documentclass[12pt, a4paper]{amsart}

\usepackage{mathrsfs}

\title[short]{A Title}"""

ABSTRACT = r"""
\begin{abstract}
An abstract.
\end{abstract}"""

# ---------------------------------------------------------------------------
# Axis value holders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AxisValue:
    id: str


@dataclass(frozen=True)
class RegionAxis(AxisValue):
    region: ContentRegion | None


@dataclass(frozen=True)
class LabelTransform(AxisValue):
    """Callable label strategy: ContentRegion | None -> ContentRegion | None."""

    fn: Callable[[ContentRegion], ContentRegion]

    def __call__(self, region: ContentRegion | None) -> ContentRegion | None:
        if region is None:
            return None
        return self.fn(region)


@dataclass(frozen=True)
class BibliographyAxis(AxisValue):
    text: str


@dataclass(frozen=True)
class AppendixTransform(AxisValue):
    """Callable placement strategy: str -> str."""

    fn: Callable[[str], str]

    def __call__(self, latex_str: str) -> str:
        return self.fn(latex_str)


# ---------------------------------------------------------------------------
# Composable region generators
# ---------------------------------------------------------------------------


def _make_subsections(count: int, sec_prefix: str) -> Iterator[SubsectionSpec]:
    """Yield *count* subsections with deterministic titles/labels."""
    for j in range(count):
        yield SubsectionSpec(
            title=f"Subsection {sec_prefix}.{j + 1}",
            label=f"sec:sub:{sec_prefix}.{j + 1}",
            content_lines=(f"Subsection {sec_prefix}.{j + 1} content.",),
        )


def _make_sections(
    n_sections: int,
    n_subsections: int,
    prefix: str,
) -> Iterator[SectionSpec]:
    """Yield *n_sections* sections, each with *n_subsections* subsections."""
    for i in range(n_sections):
        yield SectionSpec(
            title=f"Section {prefix}{i + 1}",
            label=f"sec:{prefix}{i + 1}",
            content_lines=(f"Section {prefix}{i + 1} content.",),
            subsections=tuple(_make_subsections(n_subsections, f"{prefix}{i + 1}")),
        )


def _make_region(
    n_sections: int,
    n_subsections: int,
    prefix: str,
) -> ContentRegion:
    """Build a ContentRegion with *n_sections* sections x *n_subsections* each."""
    pre = (f"Pre-section text ({prefix}).",) if n_sections == 0 else ()
    return ContentRegion(
        pre_section_content=pre,
        sections=tuple(_make_sections(n_sections, n_subsections, prefix)),
    )


def region_cases(prefix: str) -> Iterator[RegionAxis]:
    r"""Yield region axis values: None + all valid section-first combos."""
    yield RegionAxis(id="none", region=None)
    for n_sec in range(3):
        for n_sub in range(3):
            if n_sec == 0 and n_sub > 0:
                continue
            yield RegionAxis(
                id=f"{n_sec}sec_{n_sub}sub",
                region=_make_region(n_sec, n_sub, prefix),
            )


# ---------------------------------------------------------------------------
# Other axis factories
# ---------------------------------------------------------------------------


def label_transforms() -> Iterator[LabelTransform]:
    r"""Yield label transforms that test \label{} roundtrip fidelity.

    Each transform adjusts which sections/subsections carry a \label{},
    verifying the parser extracts labels correctly and to_latex() reproduces
    them faithfully regardless of placement.

    - all_labeled:          every section and subsection keeps its label
    - no_labels:            all labels stripped — parser must not invent any
    - mixed_labels:         only the first visible section keeps its label
    - subsection_only:      sections unlabeled, subsections keep labels
    """
    # Identity — all labels preserved as generated
    yield LabelTransform(id="all_labeled", fn=lambda r: r)
    # Strip every label from sections and subsections
    yield LabelTransform(
        id="no_labels",
        fn=lambda r: replace(
            r,
            sections=tuple(
                replace(
                    sec,
                    label=None,
                    subsections=tuple(
                        replace(sub, label=None) for sub in sec.subsections
                    ),
                )
                for sec in r.sections
            ),
        ),
    )
    # Only the first visible section retains its label; all others stripped
    yield LabelTransform(
        id="mixed_labels",
        fn=lambda r: replace(
            r,
            sections=tuple(
                replace(
                    sec,
                    label=sec.label if i == 0 else None,
                    subsections=tuple(
                        replace(sub, label=None) for sub in sec.subsections
                    ),
                )
                for i, sec in enumerate(r.sections)
            ),
        ),
    )
    # Sections unlabeled, subsections keep their labels
    yield LabelTransform(
        id="subsection_only",
        fn=lambda r: replace(
            r,
            sections=tuple(replace(sec, label=None) for sec in r.sections),
        ),
    )


def bibliography_cases() -> Iterator[BibliographyAxis]:
    yield BibliographyAxis(id="no_bibliography", text="")
    yield BibliographyAxis(
        id="bibliography_cmd",
        text=r"""\bibliography{refs}
\bibliographystyle{amsalpha}""",
    )
    yield BibliographyAxis(
        id="bibliography_env",
        text=r"""\begin{thebibliography}{9}
\bibitem{ref1} A reference.
\end{thebibliography}""",
    )


def appendix_transforms() -> Iterator[AppendixTransform]:
    r"""Yield ``\appendix`` line-position variants.

    - own_line:     ``\appendix`` alone on its line (canonical)
    - end_of_line:  ``\appendix`` at end of previous content line
    - mid_line:     ``\appendix`` mid-line with text on both sides
    """
    yield AppendixTransform(id="own_line", fn=lambda s: s)
    yield AppendixTransform(
        id="end_of_line",
        fn=lambda s: s.replace(r"\n\appendix\n", " \\appendix\n", 1),
    )
    yield AppendixTransform(
        id="mid_line",
        fn=lambda s: s.replace(r"\n\appendix\n", r" \appendix ", 1),
    )


# ---------------------------------------------------------------------------
# Case generation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RoundtripCase:
    id: str
    blueprint: LatexBlueprint


def _validate_roundtrip(latex_str: str):
    doc = parse_from_latex(latex_str)
    assert to_latex(doc) == latex_str


def make_cases() -> Iterator[RoundtripCase]:
    for main_axis, app_axis, label_axis, bib_axis, app_tx in it.product(
        region_cases(prefix="m"),
        region_cases(prefix="a"),
        label_transforms(),
        bibliography_cases(),
        appendix_transforms(),
    ):
        main = label_axis(main_axis.region)
        appendix = label_axis(app_axis.region)
        bp = LatexBlueprint(
            pre_matter=PRE_MATTER,
            abstract=ABSTRACT,
            main_body=main,
            appendix=appendix,
            bibliography=bib_axis.text,
            post_render=app_tx.fn,
        )
        case_id = "--".join(
            [main_axis.id, app_axis.id, label_axis.id, bib_axis.id, app_tx.id]
        )
        yield RoundtripCase(id=case_id, blueprint=bp)


def test_roundtrip(subtests):
    for case in make_cases():
        with subtests.test(msg=case.id):
            latex_str = render(case.blueprint)
            _validate_roundtrip(latex_str)
