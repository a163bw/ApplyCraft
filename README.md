# ApplyCraft deterministic CV + cover letter generator

This project generates:

- `output/cv.pdf`
- `output/cover_letter.pdf`

from:

- `personal_data.json`
- `application.json`
- optional photo image
- optional signature image

The visual layout is reused from the supplied Overleaf projects in `tmp_overleaf/` and compiled locally with `pdflatex` (MiKTeX compatible).

## Install

```powershell
python -m pip install -e .
```

## Generate

```powershell
python -m cv_generator generate --personal-data data/personal_data.json --application data/application.json --output-dir output
```

Default convenience runner (no arguments):

```powershell
python applycraft.py
```

This uses:

- `data/personal_data.json`
- `data/application.json`
- `output/`

Optional image overrides:

```powershell
python -m cv_generator generate --personal-data data/personal_data.json --application data/application.json --photo data/profile_photo.jpg --signature data/signature.png --output-dir output
```

## JSON rules

- `application.language` supports `de` or `en` only.
- User-provided text is passed through as-is (only LaTeX escaping is applied).
- CV professional experience, education, additional sections, skill subsections, and cover-letter paragraphs are all dynamic arrays.
- Skill section `type` is explicit: `general` (levels 1-4) or `language` (levels 1-6).
- Invalid levels, dates, image files, or missing required fields fail with clear validation errors.
- Cover letter date always comes from JSON (`application.cover_letter.application_date`).

## Optional Photo And Signature

Deterministic source precedence for optional assets:

1. CLI flags: `--photo`, `--signature`
2. `personal_data.json`: `photo`, `signature`
3. `application.json`: `photo`, `signature`
4. Auto-discovered defaults in the data directory (same folder as `application.json`)

Auto-discovered file names:

- Photo: `profile_photo.*` then `photo.*`
- Signature: `signature.*` then `signatur.*`

Supported default extensions (in order):

- `.jpeg`, `.jpg`, `.png`, `.webp`, `.bmp`, `.gif`, `.tiff`, `.tif`

## Required JSON fields

### personal_data.json

Required strings:

- `name`
- `street`
- `postal_code`
- `city`
- `phone`
- `mobile`
- `email`
- `birth_date` (`YYYY-MM-DD`)
- `birth_place`
- `marital_status`

Optional:

- `signing_place`
- `photo`
- `signature`

### application.json

Required top-level:

- `language`
- `cv`
- `cover_letter`

`cv` requires:

- `professional_experience` (array)
- `education` (array)
- `skills.sections` (array)
- `signing_date` (`YYYY-MM-DD`)

`cover_letter` requires:

- `company`
- `company_city`
- `application_date` (`YYYY-MM-DD`)
- `body_paragraphs` (non-empty array)

Optional cover-letter fields include:

- `company_postal_code`, `company_street`, `division`
- `contact_person`, `job_title`, `reference_number`, `subject`
- `salutation`, `closing`
