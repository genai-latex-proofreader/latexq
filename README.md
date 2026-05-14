# latexq

`latexq` is an experimental CLI for context management in LaTeX manuscripts.
`latexq` can query and reshape paper-like LaTeX manuscripts into smaller parts to improve AI-assisted review and editing workflows.


In practice, a common workflow when writing is to **review** and **revise** a smaller part of a manuscript at a time.
`latexq` is designed to help manage scope when this workflow is adapted with AI:

- For review, `lq select` helps extract only the parts that provide sufficient context for the review.
  This makes it easier to send only a portion of a manuscript to an AI for review, and with `lq select` one can automate (and script) context extraction into a repeatable process.

- For editing, `lq split` helps keep the manuscript organized so that each section (or subsection) is its own file.
  Limiting the content in each file makes it easier to keep AI-generated edits limited to the intended part; a common challenge with AI tools is that they are overeager to make edits.

The purpose of `latexq` is intentionally narrow.
It does not interact with GenAI endpoints and has no dependency on AI APIs.
AI-assisted editing is usually done interactively within an editor like VS Code or an agentic tool like Claude Code.

To extract structure in LaTeX manuscripts, `latexq` uses existing LaTeX commands like `\section`, `\subsection`, `\appendix`, `\ref` and `\label` commands.
For the full supported subset and parser constraints, see [docs/latex-subset.md](docs/latex-subset.md).


## 🚀 Getting started

#### Requirements

- Python 3.12+

#### 📦 Installation

`latexq` is available as a [pypi](https://pypi.org/project/latexq/) package:

```bash
$ pip install latexq   # or pip3 install latexq
```

#### Example command to extract one section

Input manuscript `main.tex`:
```tex
\documentclass{article}
\begin{document}
\section{Introduction}
\label{sec:intro}
This is the intro.
\section{Methods}
\label{sec:methods}
This is the methods section.
\end{document}
```

```bash
lq select \
  --input-file main.tex \
  --query '@sec:methods'
```

This emits the selected LaTeX fragment to stdout:

```tex
\section{Methods}
\label{sec:methods}
This is the methods section.
```

## 📚 Learn More

The core `latexq` commands are:

|     | Command | See |
| --- | --- | --- |
| 🔎  | `lq select` extracts parts of a manuscript for focused review or editing. | [docs/latexq-select.md](docs/latexq-select.md) |
| ✂️  | `lq split` splits a manuscript into smaller files so that each section or subsection is in its own file. | [docs/latexq-split.md](docs/latexq-split.md) |
| 📄  | `lq flatten` combines a manuscript into one `.tex` file. | [docs/latexq-flatten.md](docs/latexq-flatten.md) |
| 🔗  | `lq graph` builds a reference dependency graph showing which sections and subsections reference each other. | [docs/latexq-graph.md](docs/latexq-graph.md) |

Specifications:

- [docs/latex-subset.md](docs/latex-subset.md): the supported LaTeX subset, parser assumptions, and structural constraints.
- [docs/query-language.md](docs/query-language.md): Defines the query language used by `lq select` and `lq flatten` to extract part of a LaTeX manuscript.

Instructions for developing `latexq` can be found in [docs/development.md](docs/development.md).

Feedback and ideas is welcome.

## ⚖️ License

Copyright 2024-2026 Matias Dahl and contributors.
`latexq` is released under the [MIT License](https://opensource.org/license/mit), see [LICENSE.md](LICENSE.md).

Large parts of `latexq` (both code and documentation) have been created with the assistance of AI-powered tools.

An earlier version of this work is
https://github.com/genai-latex-proofreader/genai-latex-proofreader
