# LaTeX Application Project Structure

## Purpose

The repository separates data by lifetime and responsibility:

- `src_personal/`: stable user-specific facts and stable asset/PDF paths;
- `src/`: application-dependent content and selection;
- `helper/`: shared functions and settings used by multiple LaTeX projects;
- project folders (`CV`, `CV_academic`, `cover_letter`, `onePDF`): project-specific rendering and pure project logic only.

This separation is designed for safe LLM-assisted application tailoring without accidental changes to stable facts or rendering logic.

## Directory structure

```text
/
├── CV/
│   └── main.tex
├── CV_academic/
│   └── main.tex
├── cover_letter/
│   ├── main.tex
│   └── personalised.tex
├── src/
│   ├── content_CV.tex
│   ├── content_cover_letter.tex
│   └── content_onePDF.tex
├── src_personal/
│   ├── personal_data.tex
│   ├── pdf_paths.tex
│   ├── profile_photo.png
│   ├── profile_photo.jpg
│   └── signature.png
├── helper/
│   ├── common_commands.tex
│   ├── style.tex
│   └── document_options.tex
└── onePDF/
    ├── main.tex
    ├── application_config.tex
    ├── application_documents.tex
    ├── application_commands.tex
    └── documents/
```

## Responsibility rules

### `src_personal/personal_data.tex`

Stable user facts only: identity/contact data, professional-role metadata, education facts, project/publication facts, language levels, activities/interests, reference-person facts, supporting-document facts and personal asset paths.

Normal job tailoring must treat this file as read-only.

### `src_personal/pdf_paths.tex`

Stable user-specific PDF paths and stable source-page mappings for the collected application package. This includes generated core document paths and supporting evidence paths.

Application-dependent visibility or order must not be stored here.

### `src/content_CV.tex`

Primary AI-editable CV content and the **single source of truth for output language**.

It owns:

- `\Language` (`english` / `ngerman`);
- PDF language metadata derived from the same setting;
- CV section/role/task visibility;
- profile highlights;
- education emphasis;
- skills;
- tailored role tasks/project descriptions;
- ATS keyword support.

CV, cover letter and onePDF all load this file to obtain the shared language setting. No other file may define `\Language`.

### `src/content_cover_letter.tex`

Application-dependent target metadata and cover-letter prose only. It does not define language.

The onePDF package reuses its target metadata for the collected-package cover so target position/organisation are not duplicated.

### `src/content_onePDF.tex`

Application-dependent onePDF decisions only:

- complete-section visibility;
- individual-document visibility;
- collected-package document order;
- onePDF section titles;
- onePDF-only presentation choices such as cover/standalone TOC/generated page-number visibility.

No stable personal facts, PDF paths, language definition or rendering functions belong here.

## Helper files

### `helper/common_commands.tex`

Shared reusable functions only, including bilingual selection and LLM-readable key/value/flag infrastructure.

### `helper/style.tex`

Shared static visual system: font family, colors and reusable typography commands.

### `helper/document_options.tex`

Shared static base document font-size settings.

## Project folders

Project folders contain only project-specific rendering/assembly logic and derived adapters. They must not own stable user facts or application-dependent user decisions.

### `CV/main.tex` / `CV_academic/main.tex`

CV rendering entry points. Both load `common_commands.tex` and `content_CV.tex` before `\documentclass` so the shared PDF language metadata is available at the required point.

### `cover_letter/main.tex`

Cover-letter rendering/assembly only. It loads `content_CV.tex` for the shared language and `content_cover_letter.tex` for application-dependent letter content.

### `onePDF/main.tex`

Collected-package assembly only. It loads:

- `content_CV.tex` for shared language/metadata;
- `content_cover_letter.tex` for shared target metadata;
- `personal_data.tex` for stable user facts;
- `pdf_paths.tex` for stable PDF paths;
- `content_onePDF.tex` for application-dependent selection/order/titles.

### `onePDF/application_config.tex`

Project-local aliases and derived values only. It is not a user-editable configuration source.

### `onePDF/application_documents.tex`

Project-local document registry/composition logic only. It consumes visibility flags from `content_onePDF.tex`, facts from `personal_data.tex`, and paths from `pdf_paths.tex`.

### `onePDF/application_commands.tex`

Pure onePDF rendering/inclusion/order-dispatch functions only.

## Stable IDs and LLM-readable keys

Keys may contain digits and dots. Use `\SetValue`/`\Value` and `\SetFlag`/`\Flag`; do not create raw LaTeX control-sequence names containing digits.

Professional role IDs remain chronological and stable: `Role01` is oldest, `Role06` is newest. Never renumber existing IDs when a newer item is added.

## Recommended application workflow

1. Read `src_personal/` as stable source data; do not rewrite facts or paths unless the user explicitly requests a factual/path correction.
2. Set language and tailor CV content in `src/content_CV.tex`.
3. Tailor target metadata and prose in `src/content_cover_letter.tex`.
4. Configure collected-package visibility, order and section titles in `src/content_onePDF.tex`.
5. Compile the required CV renderer.
6. Compile the cover letter.
7. Refresh the generated core PDFs in `onePDF/documents/application/`.
8. Compile `onePDF` twice after TOC/document-selection changes.
9. Inspect the final package for missing-document warnings, reading order and ATS extraction.
