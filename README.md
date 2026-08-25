# ApplyCraft

ApplyCraft generates application documents as PDFs from reusable personal data and application-specific LaTeX content. It supports standard and academic CVs, cover letters, and a combined application package.

## Requirements

- Python 3.12 or newer
- A LaTeX distribution with `pdflatex` on `PATH` (MiKTeX or TeX Live)

## Build PDFs

From the repository root, run:

```powershell
python build_pdfs.py
```

The command builds all four documents and copies them to the current directory:

- `cv.pdf`
- `cv_academic.pdf`
- `cover_letter.pdf`
- `onepdf.pdf`

Useful options:

```powershell
python build_pdfs.py --projects CV cover_letter
python build_pdfs.py --output-dir .\output
python build_pdfs.py --onepdf-cv CV_academic
```

## Project Layout

- `src_personal/` contains stable personal data and asset paths.
- `src/` contains application-specific CV, cover-letter, and package content.
- `LaTeX/` contains the document templates and shared LaTeX helpers.
- `build_pdfs.py` compiles the templates and assembles the combined PDF.

See [`LaTeX/PROJECT_STRUCTURE.md`](LaTeX/PROJECT_STRUCTURE.md) for the detailed structure and editing workflow.
