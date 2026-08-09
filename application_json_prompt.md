# Purpose
Generate one valid application.json for the ApplyCraft project from supplied CV and cover-letter content plus structured context.

The output must be directly consumable by the current Python validator and generator.

# Inputs
Use only these inputs:
- Structured information explicitly provided in the conversation/context.
- Supplied CV content.
- Supplied cover-letter content.
- Explicit project input constraints included in this prompt.

Do not use external knowledge, web search, or assumptions.

# Authoritative Data Sources
Use this priority order for each field value:
1. Explicit structured data provided in the current prompt/context.
2. Exact value found in supplied CV content.
3. Exact value found in supplied cover-letter content.
4. Deterministic project defaults explicitly defined in this prompt.
5. If still unavailable: apply the missing-data rule for that field.

If two sources conflict:
- Prefer higher-priority source.
- Do not merge conflicting values.
- Do not invent a compromise value.

# Separation of Responsibilities
application.json must contain application-level language, CV content, and optionally cover-letter content.

Do not duplicate personal sender data from personal_data.json into application.json. In particular, do not add first_name, last_name, address, postal_code, city, email, or signing_place to application.json.

Do not add layout, LaTeX, rendering, formatting, spacing, or PDF configuration keys.

# Exact application.json Structure
Top-level object keys:
- language: required string, must be de or en.
- cv: required object.
- cover_letter: optional object (required only when cover-letter output is intended).
- photo: optional string path (only if explicitly provided).
- signature: optional string path (only if explicitly provided).

Required cv object keys:
- signing_date: required string, format YYYY-MM-DD.
- professional_experience: required array.
- education: required array.
- skills: required object.

Optional cv object key:
- additional_sections: optional array. If unavailable, use empty array.

Required skills object keys:
- sections: required array.

# Field-by-Field Extraction Rules
language:
- Must be de or en.
- Use explicit structured value when provided.
- If missing and language cannot be determined unambiguously from supplied text, treat as missing required field.

cv.signing_date:
- Required.
- Format YYYY-MM-DD.
- Use explicit structured value when provided.
- No project default is defined. Do not auto-fill current date.
- The application generator later renders this date in the document as DD Month YYYY, localized by language.

cv.professional_experience:
- Required array.
- Preserve source order from provided content.
- Each entry should use canonical keys:
  - start: required string YYYY-MM.
  - end: optional string YYYY-MM or null for ongoing role.
  - title: optional non-empty string.
  - organization: optional non-empty string.
  - location: optional non-empty string.
  - tasks: optional array of non-empty strings.
- Entry must contain at least one visible content field beyond dates (for example title, organization, location, tasks).
- Do not fabricate tasks, employers, roles, dates, or locations.

cv.education:
- Required array.
- Preserve source order.
- Each entry must use only these keys:
  - start_date: required string YYYY-MM.
  - end_date: optional string YYYY-MM or null.
  - degree: optional non-empty string.
  - institution: optional non-empty string.
  - location: optional non-empty string.
  - items: optional array of non-empty strings.
- Do not add any other education keys.
- Entry must have at least one visible field among degree, institution, location, items.

cv.additional_sections:
- Optional array.
- Use empty array when no additional section content is provided.
- Preserve section order and entry order.
- Each section object:
  - title: required non-empty string.
  - entries: required array.
- Each entries element may be:
  - a non-empty string, or
  - an object.
- Canonical object-entry keys:
  - start: optional string YYYY-MM.
  - end: optional string YYYY-MM or null.
  - title: optional non-empty string.
  - organization: optional non-empty string.
  - location: optional non-empty string.
  - description: optional non-empty string.
  - text: optional non-empty string.
- If start is present, end may be null or YYYY-MM.

cv.skills.sections:
- Required array.
- Preserve section order and item order.
- Each section object canonical keys:
  - title: required non-empty string.
  - type: required, one of general or language.
  - items: required array.
- Each item object:
  - name: required non-empty string.
  - level: required integer.
- Allowed level range by section type:
  - general: 1 to 4.
  - language: 1 to 6.

cover_letter:
- Include this object when cover-letter generation is required by inputs.
- If cover-letter generation is not required and no cover-letter content is supplied, omit cover_letter.
- If included, required keys:
  - company: non-empty string.
  - company_street: non-empty string.
  - company_postal_code: non-empty string.
  - company_city: non-empty string.
  - job_title: non-empty string.
  - application_date: string YYYY-MM-DD.
  - body_paragraphs: array of non-empty strings.
- Optional keys:
  - division: non-empty string when known; otherwise null or omit.
  - contact_person: non-empty string when known; otherwise null or omit.
  - reference_number: non-empty string when known; otherwise null or omit.
- Preserve paragraph boundaries from supplied cover-letter text.
- The application generator later renders application_date in the document as DD Month YYYY, localized by language.

photo and signature:
- Optional top-level string paths.
- Include only when explicitly provided in structured input.
- Do not invent file paths.

# Required vs Optional Fields
Required:
- language
- cv
- cv.signing_date
- cv.professional_experience
- cv.education
- cv.skills
- cv.skills.sections

Conditionally required:
- cover_letter and its required internal fields when cover-letter output is required.

Optional:
- cv.additional_sections
- cover_letter.division
- cover_letter.contact_person
- cover_letter.reference_number
- photo
- signature

# Defaults
Deterministic defaults allowed by current contract:
- cv.additional_sections: [] when absent.

No deterministic default is defined for:
- language
- cv.signing_date
- cover_letter.application_date

Do not insert current date automatically for any date field.

# Missing-Data Rules
For required fields without defaults:
- Do not invent values.
- If missing after applying source priority, return an extraction error instead of fabricating data.

For optional fields:
- Use null or omit only where explicitly allowed above.
- Never use empty string as a substitute for missing optional metadata.

Arrays:
- Keep required arrays present.
- Use empty arrays only when semantically valid and content is truly unavailable.

# Professional-Experience Rules
- Dates must use YYYY-MM.
- Ongoing role must use end: null.
- Preserve entry order from source.
- Preserve task order from source.
- Keep wording faithful to supplied content; do not rewrite claims.

# Education Rules
- Dates must use YYYY-MM.
- Use only allowed education keys.
- Preserve order of entries and items.
- Do not add inferred schools, degrees, or thesis details.

# Additional-Section Rules
- Section titles are dynamic and content-driven.
- Do not hard-code fixed section names.
- Keep all provided sections in provided order.
- Keep each section entries array in provided order.

# Skills Rules
- Skills are numeric-level based.
- Validate type-specific numeric ranges.
- Do not convert numeric levels to localized text in JSON.
- Do not add unsupported skill sections or skill items.

# Cover-Letter Rules
- Separate job/application metadata from body content.
- Keep body_paragraphs as plain text paragraphs.
- Do not insert LaTeX commands.
- Keep optional metadata null or omitted when unavailable.
- Do not use empty strings for unavailable optional metadata.

# Language Rules
- language controls project-side deterministic localization and formatting.
- Allowed values: de, en.
- Do not translate user-provided CV or cover-letter content.
- Keep supplied text in its original form.
- JSON date fields stay in ISO format; localized month names and long-date display belong to downstream document generation, not to this JSON prompt.

# No-Fabrication Rules
Do not fabricate or alter facts, including:
- employers, organizations, schools
- job titles or degree names
- dates, locations, reference numbers
- achievements, metrics, responsibilities
- cover-letter claims
- contact persons or company address details

If a fact is not explicitly present in allowed sources, treat it as missing.

# JSON Output Constraints
Output requirements:
- Return valid JSON only.
- No Markdown code fences.
- No explanatory text before or after JSON.
- Use double quotes.
- No trailing commas.
- No comments.
- Do not add undocumented keys.
- Keep canonical key names defined in this prompt.

# Complete Output Skeleton/Example
{
  "language": "de",
  "cv": {
    "signing_date": "2026-08-09",
    "professional_experience": [
      {
        "start": "2024-01",
        "end": null,
        "title": "Role title",
        "organization": "Organization name",
        "location": "City",
        "tasks": [
          "Task sentence 1",
          "Task sentence 2"
        ]
      }
    ],
    "education": [
      {
        "start_date": "2020-10",
        "end_date": "2024-09",
        "degree": "Degree name",
        "institution": "Institution name",
        "location": "City",
        "items": [
          "Education item 1"
        ]
      }
    ],
    "additional_sections": [
      {
        "title": "Section title",
        "entries": [
          {
            "start": "2023-03",
            "end": "2023-04",
            "title": "Entry title",
            "organization": "Entry organization",
            "location": "Entry location",
            "description": "Entry description"
          },
          "Single-line entry text"
        ]
      }
    ],
    "skills": {
      "sections": [
        {
          "title": "Languages",
          "type": "language",
          "items": [
            {
              "name": "English",
              "level": 5
            }
          ]
        },
        {
          "title": "Technical Skills",
          "type": "general",
          "items": [
            {
              "name": "Python",
              "level": 4
            }
          ]
        }
      ]
    }
  },
  "cover_letter": {
    "company": "Company name",
    "company_street": "Street and number",
    "company_postal_code": "12345",
    "company_city": "City",
    "division": null,
    "contact_person": null,
    "job_title": "Target role",
    "reference_number": null,
    "application_date": "2026-08-09",
    "body_paragraphs": [
      "Paragraph 1.",
      "Paragraph 2."
    ]
  }
}

# Validation Checklist
Before finalizing output, verify all checks:
- language is exactly de or en.
- cv exists and contains signing_date, professional_experience, education, skills.
- signing_date uses YYYY-MM-DD.
- experience start/end use YYYY-MM, with end null only for ongoing role.
- education uses only allowed keys and YYYY-MM date format.
- additional_sections is array when present; each section has title and entries.
- skills.sections items use allowed type and integer level ranges.
- cover_letter required fields are present when cover_letter is included.
- cover_letter optional metadata is null or omitted when unavailable, never empty string.
- body_paragraphs preserves paragraph boundaries and contains only plain text.
- no personal_data.json fields are duplicated into application.json.
- no fabricated facts were introduced.
- output is strict valid JSON only.