# Collected Application PDF (`onePDF`)

This project assembles generated application documents and selected evidence into one PDF. It owns rendering and project-specific assembly logic only.

## Data sources

- `../src/content_CV.tex` — single shared language/PDF-language-metadata source.
- `../src/content_cover_letter.tex` — application target metadata reused by the package cover.
- `../src/content_onePDF.tex` — application-dependent onePDF visibility, document order and section titles.
- `../src_personal/personal_data.tex` — stable user facts.
- `../src_personal/pdf_paths.tex` — stable PDF paths and source-page mappings.
- `../helper/` — shared functions and static shared settings.

## Files in this project

- `main.tex` — rendering/assembly entry point.
- `application_commands.tex` — pure inclusion, cover-page, section-rendering and order-dispatch functions.
- `application_documents.tex` — pure document registry/composition logic consuming external data/flags.
- `application_config.tex` — derived aliases for project-local use; not a user-editable configuration source.
- `documents/` — generated core PDFs and supporting evidence.

## Editing policy

For a normal application, edit application-dependent data only in `../src/`:

- CV language/content: `content_CV.tex`;
- target/cover-letter content: `content_cover_letter.tex`;
- onePDF visibility/order/titles: `content_onePDF.tex`.

Stable facts and PDF paths remain in `../src_personal/` and should be changed only for factual/path corrections.

Do not tailor an application by editing `main.tex`, `application_config.tex`, `application_documents.tex` or `application_commands.tex`.

## Core generated inputs

The paths are defined in `../src_personal/pdf_paths.tex`; the default generic locations are:

```text
documents/application/cover_letter.pdf
documents/application/cv.pdf
```

Refresh them after compiling the source CV and cover-letter projects.

## Compilation

Missing evidence PDFs are skipped with warnings so the wrapper can still compile. Before submission, verify selected evidence exists. Compile twice whenever TOC-relevant order or document selection changes.
