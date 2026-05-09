# `lq split`

`lq split` loads a LaTeX manuscript (and any `\input`s) and rewrites the manuscript into a new directory structure where each section and subsection is written to an individual file.

This breaks down larger manuscripts into smaller files, so each file maps to one section or subsection.
If the manuscript contains an appendix, it is separated into its own subdirectory.

The advantages of this layout include:
- When making edits to the manuscript using AI, this makes it easier for the AI to navigate and to manage edits proposed by an AI.
- Version control history becomes easier to interpret since each file is mapped to one section.
- File names include numbering so that ordered filenames match manuscript order.
  In editors, this makes it easier to navigate from the file names.

`lq flatten` is intended as the inverse operation of `lq split`: flattening split output should reconstruct a single-file manuscript representation.

When running `lq split`, it is also possible to indicate that some `\input{..}` files should not be expanded.
This is done by listing **supporting files** and those files are copied as-is into the output directory.
This can be used to keep macros and programmatically generated files (like tables) as separate files, see below.

#### Notes
- All `latexq` commands parse LaTeX using the same parser.
  This shared parser assumes a certain structure for input LaTeX files; see [docs/latex-subset.md](latex-subset.md).
  For example, if a label contains `..` or if there are duplicate labels, `latexq` will not load the input LaTeX file.

## Syntax

```text
usage: lq split [-h] --input-file INPUT_FILE [--output-dir OUTPUT_DIR]
                  --config-file CONFIG_FILE [--validate]

options:
  -h, --help            show this help message and exit
  --input-file INPUT_FILE
                        Input main LaTeX file
  --output-dir OUTPUT_DIR
                        Output directory
  --config-file CONFIG_FILE
                        Split config file path
  --validate            Validate that split-managed .tex files match lq split output
```

`lq split` normally writes files and requires `--output-dir`.

In validation mode (enabled with `--validate`)
- `lq split` will exit with error if `lq split` on the main input file would modify the output;
- that is, the split pipeline is run in memory from an existing `--input-file` and the generated split-generated output is compared against the `.tex` files on disk under the manuscript root (determined by the location of `--input-file`).
- `lq split` runs in read-only mode and only reports drift between expected output and files on disk.
- `--output-dir` is not used and no files are modified or written.


### Configuration file
The `lq split` command uses the `split` configuration block provided using `--config-file`:

```yaml
split:
  # `granularity` (required):
  #   `section`: output one file per section
  #   `subsection`: output one file per subsection
  granularity: subsection

  # `main_sections_dir` (required)
  # subdirectory name under `--output-dir` for main-body files
  main_sections_dir: sections

  # `appendix_sections_dir` (required)
  # subdirectory name under `--output-dir` for appendix files
  appendix_sections_dir: appendix

  # `supporting_files` (optional)
  # files to keep as external dependencies during split:
  # - matching `\input{...}` entries are left unexpanded
  # - matching files are copied into the output directory
  # Patterns are matched as provided (exact or wildcard).
  supporting_files:
    - mymacros.tex
    - tables/*.tex
    - journal.sty

```

## Example

#### Example input manuscript

```tex
\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\section{Introduction}
\label{sec:intro}
Hello World!
\section{Methods}
\label{sec:methods}
Methods overview.
\subsection{Setup}
\label{sec:methods:setup}
Setup details.
\appendix
\section{Proofs}
\label{sec:proofs}
Proof details.
\end{document}
```

#### Command configuration

```bash
lq split \
  --input-file paper.tex \
  --output-dir out \
  --config-file latexq.yaml
```

Example `latexq.yaml`:

```yaml
split:
  granularity: subsection
  main_sections_dir: sections
  appendix_sections_dir: appendix
```

From the input `paper.tex` and the YAML configuration, the command `lq split` will output five .tex files in the following directory structure:

```text
out/
  paper.tex
  sections/
    s01_00_sec_intro.tex
    s02_00_sec_methods.tex
    s02_01_sec_methods_setup.tex
  appendix/
    a01_00_sec_proofs.tex
```

Generated output files:

```tex
% out/paper.tex
\documentclass{article}
\begin{document}
\begin{abstract}
An abstract.
\end{abstract}
\maketitle
\input{sections/s01_00_sec_intro.tex}
\input{sections/s02_00_sec_methods.tex}
\input{sections/s02_01_sec_methods_setup.tex}
\appendix
\input{appendix/a01_00_sec_proofs.tex}
\end{document}

% out/sections/s01_00_sec_intro.tex
\section{Introduction}
\label{sec:intro}
Hello World!

% out/sections/s02_00_sec_methods.tex
\section{Methods}
\label{sec:methods}
Methods overview.

% out/sections/s02_01_sec_methods_setup.tex
\subsection{Setup}
\label{sec:methods:setup}
Setup details.

% out/appendix/a01_00_sec_proofs.tex
\section{Proofs}
\label{sec:proofs}
Proof details.
```

We can now run `lq flatten` on the output and check that this recovers the original input file.

```bash
lq flatten \
  --input-file out/paper.tex \
  --output-file out/roundtrip.tex
diff paper.tex out/roundtrip.tex
# no output, the files are the same
```

We can also validate that the split-managed files in `out/` still match what `lq split` would generate from `out/paper.tex`:

```bash
lq split \
  --input-file out/paper.tex \
  --config-file latexq.yaml \
  --validate
```

If validation finds drift, it emits one warning per issue and exits with an error.
Current warning indicators are:

| Warning indicator | Meaning |
| --- | --- |
| content drift | Same managed path exists in both places, but the file content differs. |
| path drift | File content matches generated output, but under a different managed path. |
| orphan file | Managed `.tex` file exists on disk but is not part of the generated split output. |
| missing file | Generated managed `.tex` file is missing on disk. |

## Output directory structure

Output directory conventions:

- `--output-dir` is the root for all split output.
- The rewritten main manuscript is written to `<output-dir>/<input-file filename>`.
- Main-body split files are written under `<output-dir>/<main_sections_dir>/`.
- Appendix split files are written under `<output-dir>/<appendix_sections_dir>/`.
- Output filenames always contain a section number.
- For `granularity: subsection`, filenames also contain a subsection slot (`00` for section files, `01`, `02`, ... for subsection files).

When labels are present, `lq split` uses them to create readable filename slugs.
Examples:

- A main-body `\section{...}` with `\label{sec:intro}`:
  - written to `sections/s01_sec_intro.tex` when `granularity: section`
  - written to `sections/s01_00_sec_intro.tex` when `granularity: subsection`
- An appendix `\section{...}` with `\label{sec:proofs}`:
  - written to `appendix/a01_sec_proofs.tex` when `granularity: section`
  - written to `appendix/a01_00_sec_proofs.tex` when `granularity: subsection`
- A `\subsection{...}` with `\label{sec:methods:setup}`:
  - kept inside its parent section file when `granularity: section`
  - written to `sections/s02_01_sec_methods_setup.tex` when `granularity: subsection`

These rules ensure that filenames are unique even for (sub)sections without a label.
