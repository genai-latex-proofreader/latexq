# `lq flatten`

`lq flatten` loads a main LaTeX manuscript (and any `\input` files), combines all content into one LaTeX document, and writes the result to one output `.tex` file.

Without a `--query`, `lq flatten` emits the entire manuscript.
If a `--query` is provided, the output document will only include structural nodes (sections and subsections) that match the query.

The output file from `lq flatten` is intended to remain a document that can be compiled with LaTeX.
In special cases, this may not be true: For example, if a filtered-out section defines macros used by retained sections, the flattened output may no longer compile.

If `--query` is used, the generated `.tex` file should be considered a derived read-only artifact, say, for generating a smaller PDF file.
Modifications to the manuscript should likely only be done to the source.

`lq flatten` can be seen as a more flexible version of LaTeX's internal `\includeonly` command.

#### Notes
- `lq flatten` is intended as the inverse operation of `lq split`: flattening split output should reconstruct a single-file input manuscript.
- All `latexq` commands parse LaTeX using the same parser.
  This shared parser assumes a certain structure for input LaTeX files; see [docs/latex-subset.md](latex-subset.md).
  For example, if a label contains `..` or if there are duplicate labels, `latexq` will not load the input LaTeX file.
- `--query` uses the shared `latexq` query language described in [query-language.md](query-language.md).


## Syntax

```text
usage: lq flatten [-h] --input-file INPUT_FILE --output-file OUTPUT_FILE
                    [--query QUERY]

options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE
                        Input main LaTeX file
  --output-file OUTPUT_FILE
                        Output LaTeX filename
  --query QUERY         Optional lq query selecting which structural nodes to
                        keep
```

Behavior:

- `--input-file` must point to the main manuscript file.
- Relative `\input{...}` references are resolved from the input file directory.
  This is the directory where `--input-file` is located.
- `--output-file` is the flattened output path.
- If `--query` is omitted, the entire flattened manuscript is emitted, including non-structural content.
- If `--query` is provided, only selected structural nodes are emitted, as a full LaTeX document (not a fragment).

## Example

#### Example input project

```text
paper/
  main.tex
  intro.tex
  methods.tex
```

`paper/main.tex`:

```tex
\documentclass{article}
\begin{document}
\maketitle
\input{intro}
\input{methods}
\end{document}
```

`paper/intro.tex`:

```tex
\section{Introduction}
\label{sec:intro}
This is the introduction.
```

`paper/methods.tex`:

```tex
\section{Methods}
\label{sec:methods}
This is the methods section.
```

#### Flatten without query

```bash
lq flatten \
  --input-file paper/main.tex \
  --output-file out/full.tex
```

Output (`out/full.tex`):

```tex
\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the introduction.
\section{Methods}
\label{sec:methods}
This is the methods section.
\end{document}
```

Using `lq flatten` again on `full.tex` this will produce the same output.

#### Flatten with query

```bash
lq flatten \
  --input-file paper/main.tex \
  --output-file out/intro-methods-outline.tex \
  --query '@sec:intro @sec:methods[p0]'
```

Output (`out/intro-methods-outline.tex`):

```tex
\documentclass{article}
\begin{document}
\maketitle
\section{Introduction}
\label{sec:intro}
This is the introduction.
\section{Methods}
\label{sec:methods}

(lq: the rest of this section has been truncated)
\end{document}
```
