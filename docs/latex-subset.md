# Supported LaTeX Subset

`latexq` makes strong assumptions about the structure of the input LaTeX document.

The following shows a small example document supported by `latexq`:

```tex
\documentclass{article}
\newtheorem{theorem}{Theorem}
\newcommand{\vect}[1]{\mathbf{#1}}
\title{Example document}
\begin{document}
\begin{abstract}
A short abstract.
\end{abstract}
\maketitle
\section{Introduction}
\label{sec:introduction}
\begin{theorem}
If $\vect{x} = 0$, then $\vect{x} = \vect{x}$.
\end{theorem}

\appendix

\section{Appendix A}
\label{sec:appendix:A}
Appendix text.
\subsection{Details}
\label{sec:details}

\bibliography{refs}
\end{document}
```

## Terminology

**preamble:** everything before `\begin{document}`.
This is typically where packages, macro definitions, title and author definitions are listed.

The preamble is outside the document body.
It is not part of any structural part and is distinct from prematter (see below).

**document body:** everything between `\begin{document}` and `\end{document}`.
The document body contains:

- **main body:** the structural part of the document body after `\maketitle` and before `\appendix`.
- **appendix:** the structural part of the document body after `\appendix` and before the bibliography.
- **bibliography:** the trailing bibliography material starting with `\bibliography{...}` or `thebibliography`.
  `latexq` assumes there is at most one bibliography and that it is the last document region.

In `latexq`, the document body has at most two structural parts: the main body and an optional appendix.
The bibliography is part of the document body, but it is not a structural part.

**structural part:** one of the two section-bearing parts of the document body: the main body or the appendix.

The main body and the appendix are structurally the same in `latexq`.
Each structural part consists of:

- optional **prematter**
- zero or more **sections** and **subsections**

**prematter:** text before the first `\section{...}` in a structural part.
- In the main body, this is text after `\maketitle` and before the first section.
- In the appendix, this is text after `\appendix` and before the first section.

Prematter is inside a structural part and inside the document body.
It is distinct from the preamble, which appears before `\begin{document}`.

**structural node:** is one selectable structural unit in `latexq`, namely a section or subsection.

- **section:** a top-level structural node introduced by `\section{...}`.
  In `latexq`, a section consists of its heading together with the direct content after that heading and before the first `\subsection{...}`.
  Subsections that follow are treated as separate structural nodes and not part of the parent section.

- **subsection:** a structural node inside a section, introduced by `\subsection{...}`.
  In `latexq`, a subsection consists of its heading together with the direct content after that heading and before the next subsection, the next section, or the end of the structural part.

For labels attached directly to section or subsection headings, `latexq` uses the first direct `\label{...}` as the queryable label.

Only `\section{...}` and `\subsection{...}` commands create structural nodes.
Unnumbered sectioning commands such as `\section*{...}` and `\subsection*{...}` are treated as ordinary content.

`latexq` detects direct `\label{...}`, `\section{...}`, and `\subsection{...}` commands in the source.
If these are emitted indirectly through user-defined macros, they are not recognized as structural commands or direct labels.

## Direct structural commands

The parser is source- and scanner-based, and `latexq` does not require `\section{...}`, `\subsection{...}`, or a direct structural `\label{...}` to appear on their own lines.
Therefore multiple commands can be on the same line.
For a section or subsection, the direct queryable label is the first top-level `\label{...}` encountered before any other command or environment.
Intervening plain text, new lines, or whitespace do not prevent a label from being treated as a direct label.

## Comments

`latexq` preserves LaTeX comments, and they are ignored for structural detection.

- Commented-out commands like `\label{...}`, `\section{...}` etc are not recognized.
- Leading comments or whitespace before `\documentclass` are not allowed.

Input documents may use either LF or CRLF line endings.
When `latexq` renders output, CRLF line endings from the input are not guaranteed to be preserved, so that CRLF may be converted to LF.

When query rendering truncates a selected node, comment-only lines inside paragraph-separator regions still affect paragraph boundaries as described in the query-language specification.

## Input commands

The LaTeX `\input{}` command allows one `.tex` file to include another, and this can be done recursively.
`latexq` supports `\input{...}` expansion with the following restrictions.

- `latexq` recognizes `\input{...}` only when it is the only non-whitespace content on an input line.
  So leading and trailing whitespaces are allowed on the same line as `\input{...}`, but no other text, commands or comments.
- Comments are preserved verbatim during input expansion.

In LaTeX, `\include{...}` and `\includeonly{...}` are similar to `\input{}` but these are not supported by `latexq`.
For example, in standard LaTeX, `\include{...}` also starts a new page by default, and includes coordination with `\includeonly{...}`.
If an input document includes `\include{...}` or `\includeonly{...}`, those commands are processed as normal text.

## Use of macros

`latexq` does not expand user-defined macros when deciding what counts as a direct `\label{...}`, `\section{...}`, or `\subsection{...}` command.

As a rule, define shared macros near the beginning of the document, typically in the preamble.

Avoid defining a macro inside one section and using it in a later section.
If `latexq` is used to extract only a subset of sections, the extracted output may omit the earlier macro definition and the later section may no longer compile.

## Required structure

Input must satisfy these expectations:

- The main document must begin with `\documentclass`
- after `\documentclass`, the document must contain one `\begin{document}`
- after `\begin{document}`, the document must contain one `\maketitle`
- the final LaTeX command must be `\end{document}`
- any content after the final `\end{document}` command is preserved as post-document content
- after `\maketitle`, structural content is defined using direct LaTeX `\section{..}` and `\subsection{..}` commands
- If the main body contains any structural content, its first structural command must be `\section{..}`, not `\subsection{..}`
- An optional `\appendix` marks the boundary between the main body and the appendix. If the appendix contains any structural content, its first structural command must be `\section{..}`
- An optional trailing bibliography block is preserved,
- all LaTeX `\label{...}` names must be globally unique across the input document,
- no LaTeX `\label{...}` may contain the reserved substring `..`.

## Unsupported cases

The following are currently outside the supported subset:

- leading comments or whitespace before `\documentclass`,
- documents without `\maketitle`,
- `\include{...}` and `\includeonly{...}`,
- `\label{...}`, `\section{...}`, or `\subsection{...}` emitted indirectly through macros,
- `\part{...}`, `\chapter{...}`, `\section*{...}`, `\subsection*{...}`, `\subsubsection{...}`, and deeper sectioning commands are not recognized as structural nodes,
- a main body that begins with `\subsection{..}` before any `\section{..}`,
- an appendix that begins with `\subsection{..}` before any `\section{..}`,
- inline `\input{...}` commands mixed with other content on the same line,
- `\input{...}` lines with trailing comments,
- For bibliography handling, the current parser preserves everything after the first `\bibliography{...}` command or `thebibliography` environment as the bibliography block.
  This implies that only one bibliography is supported.
  Documents with per-section bibliographies are not supported.

Unsupported sectioning commands that are not recognized structurally are currently treated as ordinary content rather than as structural boundaries.
In practice, `\part{...}`, `\chapter{...}`, starred sectioning commands, `\subsubsection{...}`, and deeper commands remain part of the surrounding prematter, section direct content, or subsection direct content rather than becoming separate structural units.

Other unsupported cases should ideally fail fast.
