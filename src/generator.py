from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any


REQUIRED_PERSONAL_KEYS = (
    "first_name",
    "last_name",
    "address",
    "postal_code",
    "city",
    "email",
)

REQUIRED_LABELS = {
    "de": {
        "first_name": "Vorname",
        "last_name": "Nachname",
        "address": "Adresse",
        "postal_code": "Postleitzahl",
        "city": "Ort",
        "email": "E-Mail",
    },
    "en": {
        "first_name": "First name",
        "last_name": "Last name",
        "address": "Address",
        "postal_code": "Postal code",
        "city": "City",
        "email": "Email",
    },
}

GENERAL_LEVELS = {
    "de": {1: "Grundkenntnisse", 2: "Gute Kenntnisse", 3: "Fortgeschritten", 4: "Experte"},
    "en": {1: "Basic", 2: "Intermediate", 3: "Advanced", 4: "Expert"},
}

LANGUAGE_LEVELS = {
    "de": {1: "Anfaenger", 2: "Grundkenntnisse", 3: "Gute Kenntnisse", 4: "Fliessend", 5: "Verhandlungssicher", 6: "Muttersprache"},
    "en": {1: "Beginner", 2: "Basic", 3: "Intermediate", 4: "Advanced", 5: "Fluent", 6: "Native speaker"},
}

I18N = {
    "de": {
        "latex_language": "ngerman",
        "document_title": "Lebenslauf",
        "personal_data": "Persoenliche Daten",
        "experience": "Berufserfahrung",
        "education": "Ausbildung",
        "skills": "Kenntnisse",
        "responsibilities": "Meine Aufgaben waren:",
        "present": "heute",
        "additional_default": "Weitere Angaben",
        "email_label": "E-Mail",
        "cover_letter_closing": "Freundliche Gruesse",
        "cover_letter_salutation": "Sehr geehrte Damen und Herren,",
        "cover_letter_reference": "Ref.",
    },
    "en": {
        "latex_language": "english",
        "document_title": "Curriculum Vitae",
        "personal_data": "Personal Data",
        "experience": "Professional Experience",
        "education": "Education",
        "skills": "Skills",
        "responsibilities": "Responsibilities:",
        "present": "present",
        "additional_default": "Additional Information",
        "email_label": "Email",
        "cover_letter_closing": "Yours sincerely",
        "cover_letter_salutation": "Dear Sir or Madam,",
        "cover_letter_reference": "Ref.",
    },
}

IMAGE_EXTENSIONS = (".jpeg", ".jpg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif")
PHOTO_NAMES = ("profile_photo", "photo")
SIGNATURE_NAMES = ("signature", "signatur")


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class BuildInputs:
    language: str
    personal_required_rows: list[tuple[str, str]]
    personal_optional_rows: list[tuple[str, str]]
    personal_required_values: dict[str, str]
    personal_optional_values: dict[str, str]
    signing_place: str
    cv: dict[str, Any]
    cover_letter: dict[str, Any] | None
    i18n: dict[str, str]


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        value = json.load(fh)
    if not isinstance(value, dict):
        raise ValidationError(f"Expected JSON object in {path}")
    return value


def resolve_language_value(value: Any, language: str, context: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        if set(value.keys()) != {"de", "en"}:
            raise ValidationError(f"{context}: language dictionary must contain exactly de and en")
        de_val = value.get("de")
        en_val = value.get("en")
        if not isinstance(de_val, str) or not isinstance(en_val, str):
            raise ValidationError(f"{context}: de and en values must both be strings")
        return value[language]
    raise ValidationError(f"{context}: expected string or language dictionary")


def _require_dict(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValidationError(f"{context}: expected object")
    return value


def _require_list(value: Any, context: str) -> list[Any]:
    if not isinstance(value, list):
        raise ValidationError(f"{context}: expected array")
    return value


def _require_non_empty_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"{context}: expected non-empty string")
    return value


def _require_date(value: Any, context: str) -> str:
    text = _require_non_empty_string(value, context)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        raise ValidationError(f"{context}: expected YYYY-MM-DD")
    date.fromisoformat(text)
    return text


def _resolve_required_fields(required_fields: dict[str, Any], language: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    missing_required = [key for key in REQUIRED_PERSONAL_KEYS if key not in required_fields]
    if missing_required:
        raise ValidationError(f"required_fields missing keys: {', '.join(missing_required)}")

    unknown_required = [key for key in required_fields if key not in REQUIRED_PERSONAL_KEYS]
    if unknown_required:
        raise ValidationError(f"required_fields contains unknown key: {', '.join(unknown_required)}")

    resolved_rows: list[tuple[str, str]] = []
    resolved_values: dict[str, str] = {}
    for key, raw_value in required_fields.items():
        resolved = resolve_language_value(raw_value, language, f"required_fields.{key}")
        if resolved is None or not resolved.strip():
            raise ValidationError(f"required_fields.{key} must resolve to a non-empty string")
        resolved_values[key] = resolved
        resolved_rows.append((REQUIRED_LABELS[language][key], resolved))

    return resolved_rows, resolved_values


def _resolve_optional_fields(optional_fields: dict[str, Any], language: str) -> tuple[list[tuple[str, str]], dict[str, str]]:
    resolved_rows: list[tuple[str, str]] = []
    resolved_values: dict[str, str] = {}
    for key, raw_value in optional_fields.items():
        _require_non_empty_string(key, "optional_fields key")
        resolved = resolve_language_value(raw_value, language, f"optional_fields.{key}")
        if resolved is None or not resolved.strip():
            continue
        resolved_values[key] = resolved
        resolved_rows.append((key, resolved))
    return resolved_rows, resolved_values


def _resolve_additional_information(additional_information: dict[str, Any], language: str) -> str:
    allowed_keys = {"signing_place"}
    unknown_keys = [key for key in additional_information if key not in allowed_keys]
    if unknown_keys:
        raise ValidationError(f"additional_information contains unknown key: {', '.join(unknown_keys)}")

    if "signing_place" not in additional_information:
        raise ValidationError("additional_information.signing_place is required")

    resolved = resolve_language_value(additional_information["signing_place"], language, "additional_information.signing_place")
    if resolved is None or not resolved.strip():
        raise ValidationError("additional_information.signing_place must resolve to a non-empty string")
    return resolved


def validate_and_resolve_inputs(personal_data: dict[str, Any], application: dict[str, Any]) -> BuildInputs:
    if set(personal_data.keys()) != {"required_fields", "optional_fields", "additional_information"}:
        raise ValidationError("personal_data.json must contain exactly required_fields, optional_fields, and additional_information")

    language = application.get("language")
    if language not in ("de", "en"):
        raise ValidationError("application.language must be de or en")

    required_fields = _require_dict(personal_data["required_fields"], "required_fields")
    optional_fields = _require_dict(personal_data["optional_fields"], "optional_fields")
    additional_information = _require_dict(personal_data["additional_information"], "additional_information")

    personal_required_rows, personal_required_values = _resolve_required_fields(required_fields, language)
    personal_optional_rows, personal_optional_values = _resolve_optional_fields(optional_fields, language)
    signing_place = _resolve_additional_information(additional_information, language)

    cv = _require_dict(application.get("cv"), "application.cv")
    _validate_cv(cv)

    cover_letter_raw = application.get("cover_letter")
    cover_letter = None
    if cover_letter_raw is not None:
        cover_letter = _require_dict(cover_letter_raw, "application.cover_letter")
        _validate_cover_letter(cover_letter)

    return BuildInputs(
        language=language,
        personal_required_rows=personal_required_rows,
        personal_optional_rows=personal_optional_rows,
        personal_required_values=personal_required_values,
        personal_optional_values=personal_optional_values,
        signing_place=signing_place,
        cv=cv,
        cover_letter=cover_letter,
        i18n=I18N[language],
    )


def _validate_cv(cv: dict[str, Any]) -> None:
    _require_date(cv.get("signing_date"), "application.cv.signing_date")

    professional_experience = _require_list(cv.get("professional_experience"), "application.cv.professional_experience")
    for index, raw_entry in enumerate(professional_experience):
        _validate_professional_experience_entry(_require_dict(raw_entry, f"professional_experience[{index}]"), f"professional_experience[{index}]")

    education = _require_list(cv.get("education"), "application.cv.education")
    for index, raw_entry in enumerate(education):
        _validate_education_entry(_require_dict(raw_entry, f"education[{index}]"), f"education[{index}]")

    additional_sections = cv.get("additional_sections", [])
    if additional_sections is not None:
        for index, raw_section in enumerate(_require_list(additional_sections, "application.cv.additional_sections")):
            _validate_additional_section(_require_dict(raw_section, f"additional_sections[{index}]"), f"additional_sections[{index}]")

    skills = _require_dict(cv.get("skills"), "application.cv.skills")
    sections = _require_list(skills.get("sections"), "application.cv.skills.sections")
    _validate_skill_sections(sections)


def _validate_professional_experience_entry(entry: dict[str, Any], context: str) -> None:
    _require_month_string(entry.get("start"), f"{context}.start")
    _validate_optional_month(entry.get("end"), f"{context}.end")
    if entry.get("tasks") is not None:
        _validate_string_list(entry.get("tasks"), f"{context}.tasks")
    if entry.get("bullets") is not None:
        _validate_string_list(entry.get("bullets"), f"{context}.bullets")
    if not _entry_has_display_content(entry):
        raise ValidationError(f"{context}: entry must contain at least one visible field")


def _validate_education_entry(entry: dict[str, Any], context: str) -> None:
    _require_month_string(entry.get("start"), f"{context}.start")
    _validate_optional_month(entry.get("end"), f"{context}.end")
    if not _entry_has_display_content(entry):
        raise ValidationError(f"{context}: entry must contain at least one visible field")


def _validate_additional_section(section: dict[str, Any], context: str) -> None:
    title = section.get("title") or section.get("name")
    _require_non_empty_string(title, f"{context}.title")
    entries = _require_list(section.get("entries"), f"{context}.entries")
    for index, raw_entry in enumerate(entries):
        _validate_additional_entry(raw_entry, f"{context}.entries[{index}]")


def _validate_additional_entry(entry: Any, context: str) -> None:
    if isinstance(entry, str):
        _require_non_empty_string(entry, context)
        return

    entry_dict = _require_dict(entry, context)
    if "start" in entry_dict:
        _require_month_string(entry_dict.get("start"), f"{context}.start")
        _validate_optional_month(entry_dict.get("end"), f"{context}.end")
    if not _entry_has_display_content(entry_dict, allow_tasks=False):
        raise ValidationError(f"{context}: entry must contain at least one visible field")


def _validate_skill_sections(sections: list[Any]) -> None:
    for index, raw_section in enumerate(sections):
        section = _require_dict(raw_section, f"application.cv.skills.sections[{index}]")
        section_type = section.get("type")
        if section_type not in ("general", "language"):
            raise ValidationError(f"skills section {index}: type must be general or language")
        section_title = section.get("title") or section.get("name")
        _require_non_empty_string(section_title, f"skills section {index}.title")

        items = section.get("items")
        if items is None:
            items = section.get("skills")
        items_list = _require_list(items, f"skills section {index}.items")
        for skill_idx, raw_skill in enumerate(items_list):
            skill = _require_dict(raw_skill, f"skills section {index}.items[{skill_idx}]")
            _require_non_empty_string(skill.get("name"), f"skills section {index}.items[{skill_idx}].name")
            level = skill.get("level")
            if not isinstance(level, int):
                raise ValidationError(f"skills section {index}.items[{skill_idx}].level must be int")
            if section_type == "general" and level not in GENERAL_LEVELS["en"]:
                raise ValidationError(f"skills section {index}.items[{skill_idx}].level invalid for general")
            if section_type == "language" and level not in LANGUAGE_LEVELS["en"]:
                raise ValidationError(f"skills section {index}.items[{skill_idx}].level invalid for language")


def _validate_cover_letter(cover_letter: dict[str, Any]) -> None:
    required_fields = (
        "company",
        "company_street",
        "company_postal_code",
        "company_city",
        "job_title",
        "application_date",
        "body_paragraphs",
    )
    for field_name in required_fields:
        if field_name not in cover_letter:
            raise ValidationError(f"application.cover_letter missing field: {field_name}")

    for field_name in ("company", "company_street", "company_postal_code", "company_city", "job_title"):
        _require_non_empty_string(cover_letter.get(field_name), f"application.cover_letter.{field_name}")

    _require_date(cover_letter.get("application_date"), "application.cover_letter.application_date")
    _validate_string_list(cover_letter.get("body_paragraphs"), "application.cover_letter.body_paragraphs")

    for optional_name in ("division", "contact_person", "reference_number"):
        optional_value = cover_letter.get(optional_name)
        if optional_value is not None:
            _require_non_empty_string(optional_value, f"application.cover_letter.{optional_name}")


def _require_month_string(value: Any, context: str) -> str:
    text = _require_non_empty_string(value, context)
    if not re.fullmatch(r"\d{4}-\d{2}", text):
        raise ValidationError(f"{context}: expected YYYY-MM")
    year, month = text.split("-")
    month_int = int(month)
    if month_int < 1 or month_int > 12:
        raise ValidationError(f"{context}: invalid month")
    return f"{year}-{month}"


def _validate_optional_month(value: Any, context: str) -> None:
    if value is None:
        return
    _require_month_string(value, context)


def _validate_string_list(value: Any, context: str) -> list[str]:
    values = _require_list(value, context)
    return [_require_non_empty_string(item, f"{context}[{index}]") for index, item in enumerate(values)]


def _entry_has_display_content(entry: dict[str, Any], *, allow_tasks: bool = True) -> bool:
    display_fields = (
        entry.get("title"),
        entry.get("organization"),
        entry.get("company"),
        entry.get("institution"),
        entry.get("location"),
        entry.get("description"),
        entry.get("text"),
        entry.get("name"),
        entry.get("main_subjects"),
    )
    if any(isinstance(value, str) and value.strip() for value in display_fields):
        return True

    if allow_tasks:
        for key in ("tasks", "bullets"):
            values = entry.get(key)
            if isinstance(values, list) and any(isinstance(item, str) and item.strip() for item in values):
                return True

    return False


def latex_escape(value: str) -> str:
    replacements = {
        "\\": r"\textbackslash{}",
        "&": r"\&",
        "%": r"\%",
        "$": r"\$",
        "#": r"\#",
        "_": r"\_",
        "{": r"\{",
        "}": r"\}",
        "~": r"\textasciitilde{}",
        "^": r"\textasciicircum{}",
    }
    return "".join(replacements.get(ch, ch) for ch in value)


def format_month(value: str, context: str) -> str:
    _require_month_string(value, context)
    year, month = value.split("-")
    return f"{month}.{year}"


def format_signing_date(value: str, language: str) -> str:
    parsed = date.fromisoformat(_require_date(value, "date"))
    if language == "de":
        return parsed.strftime("%d.%m.%Y")
    return parsed.isoformat()


def _first_existing_file(paths: list[Path]) -> Path | None:
    for path in paths:
        if path.is_file():
            return path
    return None


def discover_optional_asset(
    root: Path,
    cli_override: str | None,
    app_value: Any,
    stem_candidates: tuple[str, ...],
) -> Path | None:
    candidates: list[Path] = []
    if cli_override:
        override_path = Path(cli_override)
        candidates.append((root / override_path).resolve() if not override_path.is_absolute() else override_path)
    if isinstance(app_value, str) and app_value.strip():
        app_path = Path(app_value.strip())
        candidates.append((root / app_path).resolve() if not app_path.is_absolute() else app_path)

    for folder_name in ("assets", "data"):
        folder = root / folder_name
        for stem in stem_candidates:
            for ext in IMAGE_EXTENSIONS:
                candidates.append(folder / f"{stem}{ext}")

    selected = _first_existing_file(candidates)
    if selected is None:
        return None
    if selected.suffix.lower() not in IMAGE_EXTENSIONS:
        raise ValidationError(f"Unsupported asset extension: {selected.suffix}")
    return selected


def _entry_right_column_text(entry: dict[str, Any], language: str, for_experience: bool) -> str:
    pieces: list[str] = []

    title = entry.get("title")
    organization = entry.get("organization") or entry.get("company") or entry.get("institution")
    location = entry.get("location")
    description = entry.get("description") or entry.get("main_subjects")

    heading_parts = [part for part in (title, organization, location) if isinstance(part, str) and part.strip()]
    if heading_parts:
        pieces.append(latex_escape(", ".join(heading_parts)) + r"\par")

    if isinstance(description, str) and description.strip():
        pieces.append(latex_escape(description) + r"\par")

    if for_experience:
        tasks = entry.get("tasks") or entry.get("bullets") or []
        if tasks:
            if not isinstance(tasks, list):
                raise ValidationError("professional_experience tasks/bullets must be an array")
            pieces.append(latex_escape(I18N[language]["responsibilities"]) + r"\par")
            pieces.append(r"\vspace{0.05292cm}")
            for task in tasks:
                task_text = _require_non_empty_string(task, "professional_experience task")
                pieces.append(r"\CVTask{" + latex_escape(task_text) + "}")

    if not pieces:
        raise ValidationError("Entry must contain at least one non-empty displayable field")

    return "\n".join(pieces)


def _date_range_for_entry(entry: dict[str, Any], language: str, context: str) -> str:
    start = _require_non_empty_string(entry.get("start"), f"{context}.start")
    start_text = format_month(start, f"{context}.start")
    end = entry.get("end")
    if end is None:
        return f"{start_text} -- {I18N[language]['present']}"
    end_text = format_month(_require_non_empty_string(end, f"{context}.end"), f"{context}.end")
    return f"{start_text} -- {end_text}"


def _render_additional_entry(entry: Any, language: str, context: str) -> tuple[str, str]:
    if isinstance(entry, str):
        return "", latex_escape(_require_non_empty_string(entry, context)) + r"\par"

    entry_dict = _require_dict(entry, context)
    left = _date_range_for_entry(entry_dict, language, context) if "start" in entry_dict else ""

    title = entry_dict.get("title")
    description = entry_dict.get("description")
    organization = entry_dict.get("organization")
    location = entry_dict.get("location")
    text = entry_dict.get("text") or entry_dict.get("name")

    components: list[str] = []
    heading_parts = [part for part in (title, organization, location) if isinstance(part, str) and part.strip()]
    if heading_parts:
        components.append(latex_escape(", ".join(heading_parts)) + r"\par")
    if isinstance(description, str) and description.strip():
        components.append(latex_escape(description) + r"\par")
    if isinstance(text, str) and text.strip():
        components.append(latex_escape(text) + r"\par")

    if not components:
        raise ValidationError(f"{context}: entry must contain at least one visible field")

    return left, "\n".join(components)


def _build_skills_rows(cv: dict[str, Any], language: str) -> str:
    sections = cv["skills"]["sections"]
    lines: list[str] = []
    for section_index, section in enumerate(sections):
        section_label = section.get("title") or section.get("name") or ""
        if section_index > 0:
            lines.append(r"\CVSkillSubsectionGap")

        section_type = section["type"]
        items = section.get("items")
        if items is None:
            items = section.get("skills")

        for item_index, item in enumerate(items):
            skill_name = _require_non_empty_string(item.get("name"), "skill name")
            level = item["level"]
            level_text = GENERAL_LEVELS[language][level] if section_type == "general" else LANGUAGE_LEVELS[language][level]
            first_col = section_label if item_index == 0 else ""
            lines.append(
                r"\CVSkillRow{"
                + latex_escape(first_col)
                + "}{"
                + latex_escape(skill_name)
                + "}{"
                + latex_escape(level_text)
                + "}"
            )

    return "\n".join(lines)


def _latex_asset_path(path: Path) -> str:
    return r"\detokenize{" + path.as_posix() + "}"


def generate_cv_latex(
    resolved: BuildInputs,
    photo_path: Path | None,
    signature_path: Path | None,
) -> str:
    cv = resolved.cv
    lang = resolved.language
    i18n = resolved.i18n

    lines: list[str] = []
    lines.append(r"\selectlanguage{" + i18n["latex_language"] + "}")
    lines.append(r"\CVDocumentTitle{" + latex_escape(i18n["document_title"]) + "}")

    rows = [
        r"\CVPersonalDataRow{" + latex_escape(label) + "}{" + latex_escape(value) + "}"
        for label, value in (resolved.personal_required_rows + resolved.personal_optional_rows)
    ]
    rows_block = "\n".join(rows)
    if photo_path is None:
        lines.append(r"\CVPersonalDataNoPhoto{" + latex_escape(i18n["personal_data"]) + "}{%\n" + rows_block + "\n}")
    else:
        lines.append(
            r"\CVPersonalDataWithPhoto{" + latex_escape(i18n["personal_data"]) + "}{"
            + _latex_asset_path(photo_path)
            + "}{%\n"
            + rows_block
            + "\n}"
        )

    lines.append(r"\CVSection{" + latex_escape(i18n["experience"]) + "}")
    for index, raw_entry in enumerate(cv["professional_experience"]):
        entry = _require_dict(raw_entry, f"professional_experience[{index}]")
        date_text = _date_range_for_entry(entry, lang, f"professional_experience[{index}]")
        right_text = _entry_right_column_text(entry, lang, for_experience=True)
        lines.append(r"\CVJobEntry{" + latex_escape(date_text) + "}{%\n" + right_text + "\n}")

    lines.append(r"\CVSection{" + latex_escape(i18n["education"]) + "}")
    for index, raw_entry in enumerate(cv["education"]):
        entry = _require_dict(raw_entry, f"education[{index}]")
        date_text = _date_range_for_entry(entry, lang, f"education[{index}]")
        right_text = _entry_right_column_text(entry, lang, for_experience=False)
        lines.append(r"\CVActivityEntry{" + latex_escape(date_text) + "}{%\n" + right_text + "\n}")

    for sec_index, raw_section in enumerate(cv.get("additional_sections", [])):
        section = _require_dict(raw_section, f"additional_sections[{sec_index}]")
        section_title = section.get("title") or section.get("name") or i18n["additional_default"]
        lines.append(r"\CVSection{" + latex_escape(_require_non_empty_string(section_title, "additional section title")) + "}")
        entries = _require_list(section.get("entries"), f"additional_sections[{sec_index}].entries")
        for entry_index, raw_entry in enumerate(entries):
            left, right = _render_additional_entry(raw_entry, lang, f"additional_sections[{sec_index}].entries[{entry_index}]")
            lines.append(r"\CVActivityEntry{" + latex_escape(left) + "}{%\n" + right + "\n}")

    lines.append(r"\CVSection{" + latex_escape(i18n["skills"]) + "}")
    lines.append(r"\CVSkillsTable{%")
    lines.append(_build_skills_rows(cv, lang))
    lines.append("}")

    signing_place = resolved.signing_place
    signing_date = format_signing_date(cv["signing_date"], lang)
    lines.append(r"\CVClosingLine{" + latex_escape(signing_place) + "}{" + latex_escape(signing_date) + "}")
    if signature_path is not None:
        lines.append(r"\CVSignatureImage{" + _latex_asset_path(signature_path) + "}")

    return "\n".join(lines) + "\n"


def generate_cover_letter_preamble(resolved: BuildInputs) -> str:
    if resolved.cover_letter is None:
        raise ValidationError("application.cover_letter is required for cover-letter generation")

    cover_letter = resolved.cover_letter
    sender_name = resolved.personal_required_values["first_name"] + " " + resolved.personal_required_values["last_name"]
    sender_street = resolved.personal_required_values["address"]
    sender_postal_city = resolved.personal_required_values["postal_code"] + r"~" + resolved.personal_required_values["city"]
    subject = latex_escape(_require_non_empty_string(cover_letter.get("job_title"), "application.cover_letter.job_title"))
    reference = cover_letter.get("reference_number")
    if isinstance(reference, str) and reference.strip():
        subject += r"\par\normalfont[" + latex_escape(resolved.i18n["cover_letter_reference"]) + ": " + latex_escape(reference) + "]"

    signing_place = resolved.signing_place
    application_date = format_signing_date(_require_non_empty_string(cover_letter.get("application_date"), "application.cover_letter.application_date"), resolved.language)

    header_lines = [
        r"\begingroup",
        r"\sffamily\color{TemplateBlack}%",
        r"\noindent",
        r"\makebox[\linewidth][r]{\bfseries\fontsize{11pt}{13.2pt}\selectfont " + latex_escape(sender_name) + r"}%",
        r"\par\vspace{-0.45ex}%",
        r"{\color{TemplateBlue}\rule{\linewidth}{0.8pt}}%",
        r"\par\vspace{4.0mm}%",
        r"\raggedleft\fontsize{11pt}{13.2pt}\selectfont",
        latex_escape(sender_street) + r"\par",
        sender_postal_city + r"\par",
        latex_escape(resolved.i18n["email_label"]) + ": " + latex_escape(resolved.personal_required_values["email"]) + r"\par",
        r"\endgroup",
    ]

    preamble_lines = [
        r"\selectlanguage{" + resolved.i18n["latex_language"] + "}",
        r"\setkomavar{firsthead}{%",
        *header_lines,
        "}",
        r"\setkomavar{backaddress}{" + latex_escape(sender_name) + ", " + latex_escape(sender_street) + ", " + latex_escape(resolved.personal_required_values["postal_code"]) + r"~" + latex_escape(resolved.personal_required_values["city"]) + "}",
        r"\setkomavar{date}{" + latex_escape(application_date) + "}",
        r"\setkomavar{place}{" + latex_escape(signing_place) + "}",
        r"\setkomavar{subject}{" + subject + "}",
    ]
    return "\n".join(preamble_lines) + "\n"


def generate_cover_letter_body(resolved: BuildInputs, signature_path: Path | None) -> str:
    if resolved.cover_letter is None:
        raise ValidationError("application.cover_letter is required for cover-letter generation")

    cover_letter = resolved.cover_letter
    sender_name = resolved.personal_required_values["first_name"] + " " + resolved.personal_required_values["last_name"]

    address_lines = []
    if isinstance(cover_letter.get("division"), str) and cover_letter["division"].strip():
        address_lines.append(latex_escape(cover_letter["division"]))
    if isinstance(cover_letter.get("contact_person"), str) and cover_letter["contact_person"].strip():
        address_lines.append(latex_escape(cover_letter["contact_person"]))
    address_lines.extend(
        [
            latex_escape(cover_letter["company"]),
            latex_escape(cover_letter["company_street"]),
            latex_escape(cover_letter["company_postal_code"]) + r"~" + latex_escape(cover_letter["company_city"]),
        ]
    )
    address_block = r"\\".join(address_lines)

    salutation = _cover_letter_salutation(resolved.language, cover_letter.get("contact_person"))
    closing = _cover_letter_closing(resolved.language, cover_letter.get("contact_person"))
    paragraphs = [
        r"\CoverParagraph{" + latex_escape(paragraph) + "}"
        for paragraph in _validate_string_list(cover_letter.get("body_paragraphs"), "application.cover_letter.body_paragraphs")
    ]

    body_lines = [
        r"\begin{letter}{" + address_block + "}",
        r"\opening{" + latex_escape(salutation) + "}",
        r"\setstretch{1.08}",
        *paragraphs,
        r"\vspace{1.2\baselineskip}",
        latex_escape(closing) + r"\par",
        r"\vspace{0.9\baselineskip}",
        latex_escape(sender_name) + r"\par",
    ]
    if signature_path is not None:
        body_lines.extend(
            [
                r"\vspace{1.5mm}",
                r"\includegraphics[height=13mm]{" + _latex_asset_path(signature_path) + "}",
            ]
        )
    body_lines.append(r"\end{letter}")
    return "\n".join(body_lines) + "\n"


def _cover_letter_salutation(language: str, contact_person: Any) -> str:
    if language == "en" and isinstance(contact_person, str) and contact_person.strip():
        return f"Dear {contact_person},"
    return I18N[language]["cover_letter_salutation"]


def _cover_letter_closing(language: str, contact_person: Any) -> str:
    if language == "en" and not (isinstance(contact_person, str) and contact_person.strip()):
        return "Yours faithfully"
    return I18N[language]["cover_letter_closing"]
