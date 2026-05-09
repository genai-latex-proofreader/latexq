# latexq — query language specification

## Introduction

This document describes the `latexq` query language for selecting and extracting structural nodes from a LaTeX document.
This query language controls structural filtering in the `lq flatten` and `lq select` CLI commands.

A query is a whitespace-separated sequence of selectors.
Each selector names one or more structural nodes and may limit how much of each matched node is emitted.
The evaluator unions selector results, deduplicates matched nodes, and returns them in document order.
The order selectors are written is irrelevant.

Whitespace separates selectors, so `@a..@b` is one range selector while `@a.. @b` is two selectors.

Output mode is supplied out-of-band by the caller rather than by the query grammar.
The output modes are:

- `fragment`: emit only the matched nodes in document order.
  This is the output mode used by `lq select`.
- `latex`: emit the matched nodes embedded in a full LaTeX document suitable for compilation and preview.
  This is the output mode used by `lq flatten` when `--query` is present.

## Scope

Supported features:

- Node types: `sec`, `sub`, `app`
- Selectors: `@label`, `@@label`, `@..label`, `@label..`, `@label..@label`, `*sec`, `*sub`, bare `app`
- Scopes: `/app`, `/!app`
- Brackets: `[pN]`
- Output modes: `fragment`, `latex`

Not supported: theorem discovery, reference expansion, proof attachment, source-line windows, and editor SyncTeX integration.

## Terminology

Terminology follows `latexq`'s canonical glossary in [docs/latex-subset.md](docs/latex-subset.md).

Recall:

- **structural node:** one selectable structural unit in `latexq`: a section or subsection.

- **structural part:** the main body or the appendix.

- **label:** a LaTeX `\label{...}` name used in the source document.

Query language specific terminology:

- **node:** shorthand in this spec for `structural node` (see above) unless stated otherwise.

- **selector:** one query expression that determines a set of structural nodes, such as `@intro`, `@@proof-label`, `*sec`, or `app`.

- **scope:** a filter attached to one selector that narrows that selector's result set, such as `/app` or `/!app`.

## Node types

**`sec`:** matches section nodes only.

**`sub`:** matches subsection nodes only.

**`app`:** special selector for all structural nodes in the appendix. The appendix is not itself a structural node.

`app` is the only valid bare type.

A **section node** is the structural node introduced by one `\section{...}` heading together with its direct content before the first `\subsection{...}`.
It does not include following subsection nodes.

Selecting a section node does not implicitly select its subsection nodes.

## Labels and querying

A label is query-addressable only if its name can be written in the query language grammar:

- it matches `[a-zA-Z0-9:_.-]+`, and
- it does not contain the reserved substring `..`.

The evaluator does not invent synthetic labels for sections without a label.
Commented-out `\label{...}` commands are ignored during parsing.
All parsed LaTeX labels must be globally unique.

For each section or subsection node, `latexq` recognizes at most one queryable direct label: the first direct `\label{...}` attached to that node.
Direct-label recognition follows [docs/latex-subset.md](docs/latex-subset.md).
Additional labels later in the same node are preserved in the source document but are not queryable through `@label`.

**`@label`:** selects only a queryable direct label of a section or subsection node.

**`@@label`:** looks up any parsed source label whose name is representable in the query grammar and selects the nearest containing structural node:

- if the label is itself the direct label of a section or subsection node, `@@label` selects that node,
  - if the label occurs within a subsection, `@@label` selects that subsection,
  - otherwise, if the label occurs within section-level content, `@@label` selects that section.

Example query:

```text
% Select the subsection containing eq:maxwell if there is one, otherwise select
% the containing section.
@@eq:maxwell
```

This includes labels on equations, theorems, figures, tables, and additional later labels inside a section or subsection.

Consequences:

- `@label` queries can target only the first direct label of a section or subsection.
- `@@label` queries can target any parsed source label whose name is allowed in the query grammar.
- Range endpoints such as `@label..@label` must both be queryable structural labels.
- Unlabeled sections or subsections may by selected using wildcards or in range results if they fall inside the selected content.
- If a section or subsection needs direct querying, it must have a label it in the source LaTeX document.
- Using a label that exists in the source but does not identify a queryable section or subsection is a hard error.
- A label that exists in the source but lies outside all selectable section and subsection content is a hard error for `@@label`.

---

## Formal grammar

```text
query      := WS?
           | selector (WS+ selector)* WS?

selector   := expr scope* bracket?

expr       := '@' label
            | '@@' label
            | '@..' label
            | '@' label '..'
            | '@' label '..' '@' label
            | '*' type
            | 'app'

scope      := '/' '!'? 'app'

bracket    := '[' 'p' INT ']'

label      := [a-zA-Z0-9:_.-]+  ; with the reserved substring '..' forbidden

type       := sec | sub

INT        := [0-9]+

WS         := (' ' | '\t' | '\n' | '\r' | comment)+

comment    := '%' [^\n]* ('\n' | EOF)
```

Notes:

- Bare `app` is valid.
- Bare `sec` or `sub` is invalid.
- `[pN]` means the first `N` paragraphs of each matched node body.
- `[p0]` means no body paragraphs for `sec` and `sub` nodes.
  The rendered heading is still included, and the first direct label is preserved in `[p0]` and `[pN]`.
- Label-name constraints are defined in the Labels and querying section above.
- No whitespace is allowed inside a single selector.
  In particular, `@a..@b` is a range, while `@a.. @b` is a suffix selector followed by a direct selector.

## Multi-line formatting

Whitespace including newlines is insignificant.

Multi-line queries may use one selector per line, with an optional `%` comment on the same line.

Example query:

```text
*sec[p2]    % section openings
*sub[p0]    % select subsection headings
@sec:main   % select sec:main in full
```

Comments may appear anywhere whitespace is valid.

A trailing end-of-file comment without a final newline is valid.

## Semantic rules

### Document order

Output always follows document order regardless of the order selectors appear in the query.

### Empty query

An empty query selects no nodes.
In `fragment` mode, output is the empty string.
In `latex` mode, output is an empty rendered document body: wrappers such as preamble, `\begin{document}`, `\maketitle`, optional bibliography, and `\end{document}` are preserved, with no selected structural nodes.
In particular, because no structural nodes are selected, main-body prematter, `\appendix`, and appendix prematter are not included.

### Selector result sets

Each selector first computes a result set of nodes:

- `@label` selects the section or subsection node identified by `label`.
- `@@label` selects the nearest containing structural node for `label`: if `label` is itself the direct label of a section or subsection node, it selects that node; otherwise it selects the containing subsection if one exists, and otherwise the containing section.
- `@..label` selects all nodes from the beginning of the structural part containing `label` through the node identified by `label`, inclusive.
- `@label..` selects all nodes from the node identified by `label` through the end of the structural part containing `label`.
- `@label..@label` selects all nodes in the contiguous document range between the two labeled endpoints, inclusive.
  Range selectors may cross from the main body into the appendix.
- `*sec` selects all section nodes and does not include subsection nodes.
- `*sub` selects all subsection nodes and does not include section nodes.
- `app` selects all structural nodes in the appendix.

After the base result set is computed, each scope filters that selector's result set.

Example queries:

```text
% Select from the start of the structural part through sec:prelim.
@..sec:prelim

% Select from sec:contributions to the end of its structural part.
@sec:contributions..

% Select all nodes from sec:setup through sec:verification.
@sec:setup..@sec:verification
```

The document has two structural parts: the main body and the appendix.
Prefix and suffix selectors do not cross between those parts.
Range selectors do follow document order across the full node stream and may cross from the main body into the appendix.

Document order is the order of the rendered structural nodes within one structural part, with all main-body structural nodes before all appendix structural nodes.

### Scope filtering

Two scopes are supported:

- `/app`: keep only nodes in the appendix.
- `/!app`: keep only nodes not in the appendix.

Multiple scopes on the same selector are applied left to right.
Since only `app` is supported, repeated or contradictory appendix scopes are allowed syntactically but may produce an empty result set.

For example, `@sec:intro/app/!app` and `app/!app` select nothing.

Scopes are local to the selector they are attached to.
They do not globally remove nodes selected by other selectors.

Example query:

```text
% Render appendix section nodes as headings only.
*sec/app[p0]
% Select sec:results in full even though it is in the main body.
@sec:results
```

### Precedence

Precedence matters when more than one selector matches the same node.

Example query:

```text
% Select intro through results, with matched nodes truncated to one paragraph.
@sec:intro..@sec:results[p1]

% Select sec:results again, now with four body paragraphs.
@sec:results[p4]
```

Without a precedence rule, it is unclear whether `sec:results` should render with `[p1]` or `[p4]`.

Precedence order:

```text
@label, @@label
  > @..label, @label.., @label..@label
  > *type/app, *type/!app
  > *type
```

The render modifier from the more specific selector applies.

A bare `@label` or `@@label` with no bracket means include the node in full.

`app` expands before precedence is applied, so it does not introduce a separate precedence tier.

### Equal-precedence resolution

When two selectors of equal precedence match the same node, the larger paragraph limit wins.

```text
% Select sec:main twice; the larger paragraph limit wins.
@sec:main[p1] @sec:main[p2]
```

The node is rendered as `[p2]`.

If one matching selector at that precedence has no bracket, the node is rendered in full.

### Bare `app`

Bare `app` selects all appendix structural nodes.

Example query:

```text
% Select all structural nodes in the appendix.
app
```

It expands to all structural nodes in the appendix.
Equivalently, `app[pN]` means `*sec/app[pN] *sub/app[pN]`, and bare `app` means `*sec/app *sub/app`.

`app` does not select appendix prematter. Prematter is not a structural node.

In `fragment` mode this emits only those nodes.
In `latex` mode it emits a full LaTeX document containing those nodes, with `\appendix` and appendix prematter added by the `latex` rendering rules.

## Output modes

### `fragment` output mode

`fragment` output emits only the matched nodes in document order.

Properties:

- emits selected nodes only
- does not attempt to be a full standalone LaTeX document
- may begin with `\section{...}` or `\subsection{...}`
- excludes preserved wrappers such as the preamble, abstract, `\maketitle`, `\appendix`, and trailing bibliography block
- preserves document order and truncation markers
- reconstructs selected headings as `\section{...}` and `\subsection{...}` from the source section and subsection titles; exact original heading syntax is not preserved

### `latex` output mode

`latex` output emits the matched nodes embedded in a full LaTeX document.
It aims to be a valid LaTeX document, but `latexq` does not guarantee this.
A subset may omit required macro definitions.

Properties:

- preserves the original preamble
- preserves `\begin{document}` and `\end{document}`
- preserves any post-document content after `\end{document}`, including trailing comments
- preserves `\maketitle`
- preserves content between `\begin{document}` and `\maketitle`
- preserves main-body prematter if at least one selected structural node is in the main body
- preserves `\appendix` if at least one selected structural node is in the appendix
- preserves appendix prematter if at least one selected structural node is in the appendix
- preserves the trailing bibliography block if present
- emits only the selected document body content between those preserved wrappers

Comments are treated as part of input and are not stripped by `latexq`.

### Content truncation

Attach `[pN]` to a selector to truncate each structural node matched by that selector.
For each matched node, the renderer keeps at most the first `N` body paragraphs.

For example, `*sec[p2]` truncates each matched section node to at most two body paragraphs.
Likewise, `app[p1]` truncates each appendix section and subsection node matched by `app` to at most one body paragraph.

The paragraph count applies only to node-body content.
Heading lines introduced by the renderer for `sec` and `sub` are not counted toward `N`.
If the emitted extract contains no `\label{...}` and the node has a direct structural label, that direct structural label is appended to the output.

Paragraphs are determined from the LaTeX source of the matched node body as follows:

- A paragraph is a maximal run of body content not interrupted by a paragraph separator.
- A paragraph separator is one or more empty lines in the LaTeX source.
- Comment-only lines may appear inside that separator region without starting a new paragraph.
  In other words, empty-line runs still separate paragraphs even if comment lines occur between the empty lines.
- A leading direct `\label{...}` attached to the node is preserved but does not itself count as a paragraph.
- When a node is truncated, the output also includes a truncation marker. See the example output below.
- If truncation occurs and a direct structural label must be appended, it is inserted immediately before the truncation marker.
- If `N` is larger than the number of paragraphs in the node body, the full node body is emitted.

Examples:

- `[p0]` keeps no body paragraphs.
- `[p1]` keeps at most the first body paragraph.
- `[p2]` keeps at most the first two body paragraphs.
- `[p9999]` keeps the full node body unless it has more than 9999 paragraphs.

Example query:

```text
% Select the first paragraphs from all section nodes.
*sec[p1]
% Select subsection headings only, with the first direct label preserved.
*sub[p0]
```

Example output for the above query (with output mode = `fragment`):

```latex
\section{Results}
\label{sec:results}
The main contribution of this chapter is presented in this section.

(lq: the rest of this section has been truncated)

\subsection{Hypothesis 1}
\label{sec:hypothesis:1}

(lq: the rest of this subsection has been truncated)

\subsection{Hypothesis 2}
\label{sec:hypothesis:2}

(lq: the rest of this subsection has been truncated)

\subsection{Hypothesis 3}
\label{sec:hypothesis:3}

(lq: the rest of this subsection has been truncated)
```

## Hard errors

The evaluator must fail with a hard error for any of the following conditions.

| Code | Condition | Example query |
|------|-----------|---------------|
| E1 | A label used in `@label`, `@@label`, `@..label`, `@label..`, or `@label..@label` does not exist in the document | `@sec:does-not-exist` |
| E2 | The end label in `@label..@label` precedes the start label in document order, even when document order crosses from the main body into the appendix | `@sec:results..@sec:introduction` |
| E3 | Bare type used for any token other than `app` | `sec` |
| E4 | A bracket other than `[pN]` is used | `*sec[l50]` |
| E5 | A scope other than `/app` or `/!app` is used | `@sec:results/@sec:intro` |
| E6 | A label used in a direct, prefix, suffix, or range selector exists in the source document but is not the first direct label of a section or subsection node | `@eq:maxwell` |
| E7 | A label used in `@@label` exists in the source document but lies outside all selectable section and subsection content | `@@frontmatter:dedication` |

Before a LaTeX can be queried it must also be parsed into the `latexq` LaTeX data model.
This may also fail, for example if labels are duplicated or contain the reserved substring `..`.
For details, see the separate [docs/latex-subset.md](docs/latex-subset.md) document.
