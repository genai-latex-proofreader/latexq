# `lq graph`

`lq graph` reads a main LaTeX manuscript (and any `\input` files), extracts supported `\ref`-style links within the manuscript, and builds a graph that models LaTeX references between sections and subsections.
The primary use case is helping AI processes understand dependencies inside a larger manuscript.
The dependencies can help determine what context to bring in for proofreading a section.
The output from `lq graph` can also be used as input for graph visualization tools.

#### Graph structure

- **Graph nodes:** directly labeled `\section{...}` and `\subsection{...}` structural nodes.

- **Graph edges:** represent LaTeX references from one structural node to a label in another structural node (using one of the recognized commands such as `\ref`, `\eqref`, etc.; see the list below).

- The graph is weighted with an integer **edge count** > 0.
Repeated references between the same source and target nodes collapse into one graph edge; the edge count is the total number of references.

  Example: if an equation `eq:einstein` is defined inside section `sec:background`, and section `sec:intro` contains `In Section \ref{sec:background} we will prove equation \eqref{eq:einstein}.`, then the graph will contain a directed edge `sec:intro -> sec:background` with edge count 2.

- **Edge metadata (JSON):** `target_referenced_labels` records which referenced labels contributed to that edge.

- **Node metadata:** `source_file` records the source tex file where the node was defined.

#### Notes
- All `latexq` commands parse LaTeX using the same parser.
  This shared parser assumes a certain structure for input LaTeX files; see [docs/latex-subset.md](latex-subset.md).
  For example, if a label contains `..` or if there are duplicate labels, `latexq` will not load the input LaTeX file.
- Warnings are always emitted to stderr in encounter order.
- In JSON mode, warnings are also included in the `warnings` field.

## Syntax

```text
usage: lq graph [-h] --input-file INPUT_FILE
                  [--output-file OUTPUT_FILE | --stdout]
                  --format {text,json}

options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE
                        Input main LaTeX file
  --output-file OUTPUT_FILE
                        Output graph filename
  --stdout              Write graph output to stdout
  --format {text,json}  Graph output format
```

Behavior:

- `--input-file` must point to the main manuscript file.
- Relative `\input{...}` references are resolved from the input file directory.
- `--format` is required and must be `text` or `json`.
- Output goes to stdout by default; use `--output-file` to write a file instead.

## Example

#### Example input manuscript

```tex
\documentclass{article}
\title{Example}
\begin{document}
\maketitle

\section{Introduction}
\label{sec:intro}
In Section \ref{sec:background} we will prove equation \eqref{eq:einstein}.

\section{Background}
\label{sec:background}
Background text.

\begin{equation}
  E = mc^2
\label{eq:einstein}
\end{equation}

\subsection{Details}
\label{sub:details}
See \ref{sec:intro}.

\end{document}
```

#### Text output

```bash
lq graph \
  --input-file paper.tex \
  --stdout \
  --format text
```

```text
Nodes:
Main body:
- Introduction (sec:intro in paper.tex)
- Background (sec:background in paper.tex)
  - Details (sub:details in paper.tex)
Appendix:
  (none)

Edges:
sec:intro -> sec:background (x2)
sub:details -> sec:intro (x1)
```

#### JSON output

```bash
lq graph \
  --input-file paper.tex \
  --stdout \
  --format json
```

The JSON output listing nodes and edges (and ordering fields omitted for brevity):

```json
{
  "nodes": [
    {
      "kind": "section",
      "label": "sec:intro",
      "parent": null,
      "title": "Introduction",
      "in_appendix": false,
      "source_file": "paper.tex"
    },
    {
      "kind": "section",
      "label": "sec:background",
      "parent": null,
      "title": "Background",
      "in_appendix": false,
      "source_file": "paper.tex"
    },
    {
      "kind": "subsection",
      "label": "sub:details",
      "parent": "sec:background",
      "title": "Details",
      "in_appendix": false,
      "source_file": "paper.tex"
    }
  ],
  "edges": [
    {
      "source": "sec:intro",
      "target": "sec:background",
      "count": 2,
      "target_referenced_labels": ["sec:background", "eq:einstein"]
    },
    {
      "source": "sub:details",
      "target": "sec:intro",
      "count": 1,
      "target_referenced_labels": ["sec:intro"]
    }
  ],
  "warnings": []
}
```

### Node resolution

- Section or subsections without labels are not included in the graph.
- References resolve to the nearest containing structural node.
  - Labels inside subsection content resolve to that subsection node.
  - Labels inside section-level content resolve to that section node.
- Links are retained only when both source and resolved target nodes are directly labeled.


### List of supported LaTeX reference commands

| Command | Notes |
| --- | --- |
| `\ref{...}` | Standard cross-reference command; usually prints a number. |
| `\eqref{...}` | Equation reference command; usually prints the equation number in parentheses. |
| `\autoref{...}` | Auto-named reference (for example, "Section 2"), typically provided by the `hyperref` package. |
| `\pageref{...}` | Page reference command; prints the page number where the label appears. |
| `\nameref{...}` | Name/title reference command; prints the labeled element's title text (commonly via `hyperref`). |
| `\vref{...}` | Verbose reference command (commonly from `varioref`) that can include page-aware context; `lq graph` treats it as a standard single-label reference command. |
| `\cref{...}` | Cross-reference command from `cleveref` that chooses an appropriate type name (for example, "section" or "equation"). Supports single-label and multi-label forms. In LaTeX, `cleveref` supports lists such as `\cref{sec:intro,sec:methods}` so it can render combined references in one phrase (for example, "sections 1 and 2"). In `lq graph`, each label in a multi-label `\cref` contributes an individual reference during extraction. |
| `\Cref{...}` | Same as `\cref`, but capitalized at the start (for example, "Section" instead of "section"). Multi-label forms are handled the same way as `\cref`. |
