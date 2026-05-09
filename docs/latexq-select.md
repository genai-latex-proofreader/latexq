# `lq select`

`lq select` loads a main LaTeX manuscript (and any `\input` files), selects structural nodes determined by a required `--query` string, and outputs the result as a raw LaTeX fragment.

Unlike `lq flatten`, `lq select` does not emit a LaTeX file that can be compiled.
Instead the output is a **LaTeX fragment**.
This includes only the sections and subsections that are selected via the `--query` argument.

A primary use case of `lq select` is to extract parts of a manuscript in a format that can be sent to an AI.

For example, given a `main.tex`:
```tex
\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the intro.
\section{Methods}
\label{sec:methods}
This is the methods.
\end{document}
```

Running:
```bash
lq select \
  --input-file main.tex \
  --query '@sec:intro'
```

Emits the LaTeX fragment to stdout:
```tex
\section{Introduction}
\label{sec:intro}
This is the intro.
```

The required `--query` argument uses the shared `latexq` query language defined in [query-language.md](query-language.md).

As in the above example, use single quotes around `--query` strings in shell commands (e.g., `'@sec:intro..@sec:methods'`, `'*sec'`, `'*sec/!app'`).
This ensures that wildcard and scopes are passed literally to `latexq`.


#### Notes
- All `latexq` commands parse LaTeX using the same parser.
  This shared parser assumes a certain structure for input LaTeX files; see [docs/latex-subset.md](latex-subset.md).
  For example, if a label contains `..` or if there are duplicate labels, `latexq` will not load the input LaTeX file.
- Output goes to stdout by default. Use `--output-file` when you want to save the selected fragment to disk.

## Syntax

```text
usage: lq select [-h] --input-file INPUT_FILE
                   [--output-file OUTPUT_FILE | --stdout]
                   --query QUERY

options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE
                        Input main LaTeX file
  --output-file OUTPUT_FILE
                        Output fragment filename
  --stdout              Write selected fragment to stdout
  --query QUERY         lq query selecting which structural nodes to emit
```

Behavior:

- `--input-file` must point to the main manuscript file.
- Relative `\input{...}` references are resolved from the input file directory.
- `--query` is required.
- Output goes to stdout by default; use `--output-file` to write a file instead.

## Examples

#### Query syntax examples

- see [query-language.md](query-language.md)
- see acceptance tests [tests/acceptance/query_specs/test_fragment_queries.py](../tests/acceptance/query_specs/test_fragment_queries.py)

#### Copy selected fragment to clipboard

When extracting content for an interactive AI chat, it can be convenient to copy the selection directly to the clipboard.
On macOS, this can be done using `pbcopy`.

```bash
lq select \
  --input-file main.tex \
  --query '@sec:definitions @sec:background @sec:main-result' | pbcopy
```
