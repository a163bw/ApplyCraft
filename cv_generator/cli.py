from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    from PIL import Image, UnidentifiedImageError
except ImportError:
    Image = None

    class UnidentifiedImageError(Exception):
        pass


LANGUAGE_MAP = {"de": "ngerman", "en": "english"}

FIXED_TEXT = {
    "de": {
        "cv": {
            "title": "Lebenslauf",
            "personal_details": "Persoenliche Daten",
            "professional_experience": "Beruflicher Werdegang",
            "education": "Ausbildung",
            "skills": "Kenntnisse",
            "tasks": "Meine Aufgaben waren:",
            "at": "bei",
            "present": "heute",
            "name": "Name:",
            "birth": "Geburtsdatum/-ort:",
            "address": "Adresse:",
            "phone": "Telefon:",
            "mobile": "Mobil:",
            "email": "E-Mail:",
            "marital_status": "Familienstand:",
        },
        "cover_letter": {
            "default_salutation_no_contact": "Sehr geehrte Damen und Herren,",
            "default_salutation_with_contact": "Sehr geehrte/r {contact},",
            "default_closing": "Freundliche Gruesse",
            "reference_label": "Ref.",
            "mobile": "Mobil",
            "email": "E-Mail",
            "application_subject_prefix": "Bewerbung als ",
            "initiative_subject": "Initiativbewerbung",
        },
        "skill_levels": {
            "general": {
                1: "Grundkenntnisse",
                2: "Gute Kenntnisse",
                3: "Fortgeschritten",
                4: "Experte",
            },
            "language": {
                1: "Anfaenger",
                2: "Grundkenntnisse",
                3: "Gute Kenntnisse",
                4: "Fliessend",
                5: "Verhandlungssicher",
                6: "Muttersprache",
            },
        },
    },
    "en": {
        "cv": {
            "title": "Curriculum Vitae",
            "personal_details": "Personal Details",
            "professional_experience": "Professional Experience",
            "education": "Education",
            "skills": "Skills",
            "tasks": "Responsibilities:",
            "at": "at",
            "present": "present",
            "name": "Name:",
            "birth": "Date/place of birth:",
            "address": "Address:",
            "phone": "Phone:",
            "mobile": "Mobile:",
            "email": "Email:",
            "marital_status": "Marital status:",
        },
        "cover_letter": {
            "default_salutation_no_contact": "Dear Recruiting Team,",
            "default_salutation_with_contact": "Dear {contact},",
            "default_closing_no_contact": "Yours faithfully",
            "default_closing_with_contact": "Yours sincerely",
            "reference_label": "Ref.",
            "mobile": "Mobile",
            "email": "Email",
            "application_subject_prefix": "Application as ",
            "initiative_subject": "Initiative Application",
        },
        "skill_levels": {
            "general": {
                1: "Basic",
                2: "Intermediate",
                3: "Advanced",
                4: "Expert",
            },
            "language": {
                1: "Beginner",
                2: "Basic",
                3: "Intermediate",
                4: "Advanced",
                5: "Fluent",
                6: "Native speaker",
            },
        },
    },
}

MONTHS = {
    "de": [
        "Januar",
        "Februar",
        "Maerz",
        "April",
        "Mai",
        "Juni",
        "Juli",
        "August",
        "September",
        "Oktober",
        "November",
        "Dezember",
    ],
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
}

DEFAULT_ASSET_EXTENSIONS = [".jpeg", ".jpg", ".png", ".webp", ".bmp", ".gif", ".tiff", ".tif"]


class ValidationError(Exception):
    pass


@dataclass(frozen=True)
class GeneratedPaths:
    cv_pdf: Path
    cover_letter_pdf: Path


@dataclass(frozen=True)
class PersonalDataModel:
    name: str
    street: str
    postal_code: str
    city: str
    phone: str
    mobile: str
    email: str
    birth_date: str
    birth_place: str
    marital_status: str
    signing_place: str


@dataclass(frozen=True)
class CVEntryModel:
    start: str
    end: str | None
    title: str
    organization: str
    location: str
    description: str
    tasks: list[str]


@dataclass(frozen=True)
class CVAdditionalSectionModel:
    title: str
    entries: list[CVEntryModel]


@dataclass(frozen=True)
class CVSkillItemModel:
    name: str
    level: int


@dataclass(frozen=True)
class CVSkillSectionModel:
    title: str
    type: str
    items: list[CVSkillItemModel]


@dataclass(frozen=True)
class CVModel:
    professional_experience: list[CVEntryModel]
    education: list[CVEntryModel]
    additional_sections: list[CVAdditionalSectionModel]
    skills_sections: list[CVSkillSectionModel]
    signing_date: str


@dataclass(frozen=True)
class CoverLetterModel:
    company: str
    company_city: str
    company_postal_code: str
    company_street: str
    division: str
    job_title: str
    reference_number: str
    subject: str
    contact_person: str
    application_date: str
    body_paragraphs: list[str]
    salutation: str
    closing: str


@dataclass(frozen=True)
class ApplicationModel:
    language: str
    cv: CVModel
    cover_letter: CoverLetterModel
    photo: str
    signature: str


@dataclass(frozen=True)
class NormalizedCVEntryModel:
    start: str
    end: str
    title: str
    organization: str
    location: str
    description: str
    tasks: list[str]


@dataclass(frozen=True)
class NormalizedCVAdditionalSectionModel:
    title: str
    entries: list[NormalizedCVEntryModel]


@dataclass(frozen=True)
class NormalizedCVSkillItemModel:
    name: str
    level_text: str


@dataclass(frozen=True)
class NormalizedCVSkillSectionModel:
    title: str
    type: str
    items: list[NormalizedCVSkillItemModel]


@dataclass(frozen=True)
class NormalizedCVModel:
    professional_experience: list[NormalizedCVEntryModel]
    education: list[NormalizedCVEntryModel]
    additional_sections: list[NormalizedCVAdditionalSectionModel]
    skills: list[NormalizedCVSkillSectionModel]
    signing_date: str


@dataclass(frozen=True)
class NormalizedCoverLetterModel:
    company: str
    company_city: str
    company_postal_code: str
    company_street: str
    division: str
    job_title: str
    reference_number: str
    subject: str
    contact_person: str
    application_date: str
    paragraphs: list[str]
    salutation: str
    closing: str


@dataclass(frozen=True)
class NormalizedRenderModel:
    language: str
    language_babel: str
    personal: PersonalDataModel
    cv: NormalizedCVModel
    cover_letter: NormalizedCoverLetterModel
    photo: Path | None
    signature: Path | None


def _latex_escape(value: str) -> str:
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
    return "".join(replacements.get(c, c) for c in value)


def _latex_cmd(name: str, value: str) -> str:
    return f"\\newcommand{{\\{name}}}{{{_latex_escape(value)}}}"


def _latex_cmd_raw(name: str, value: str) -> str:
    return f"\\newcommand{{\\{name}}}{{{value}}}"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ValidationError(f"Cannot read JSON file: {path} ({exc})") from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Malformed JSON in {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ValidationError(f"Top-level JSON object expected in {path}")
    return data


def _require_string(obj: dict[str, Any], key: str, context: str) -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"Missing required non-empty string: {context}.{key}")
    return value.strip()


def _optional_string(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValidationError(f"Field '{key}' must be a string when provided")
    return value.strip()


def _parse_cv_entry(entry: Any, context: str) -> CVEntryModel:
    if not isinstance(entry, dict):
        raise ValidationError(f"{context} entries must be objects")

    start = _require_string(entry, "start", context)
    end_raw = entry.get("end")
    if end_raw is None:
        end = None
    elif isinstance(end_raw, str):
        end = end_raw.strip()
    else:
        raise ValidationError(f"{context}.end must be a string or null")

    title = _require_string(entry, "title", context)
    organization = _optional_string(entry, "organization")
    location = _optional_string(entry, "location")
    description = _optional_string(entry, "description")

    raw_tasks = entry.get("tasks", [])
    if raw_tasks is None:
        raw_tasks = []
    if not isinstance(raw_tasks, list):
        raise ValidationError(f"{context}.tasks must be an array")

    tasks: list[str] = []
    for idx, task in enumerate(raw_tasks):
        if not isinstance(task, str) or not task.strip():
            raise ValidationError(f"{context}.tasks[{idx}] must be a non-empty string")
        tasks.append(task.strip())

    return CVEntryModel(
        start=start,
        end=end,
        title=title,
        organization=organization,
        location=location,
        description=description,
        tasks=tasks,
    )


def _parse_personal_data_model(personal: dict[str, Any]) -> PersonalDataModel:
    required = [
        "name",
        "street",
        "postal_code",
        "city",
        "phone",
        "mobile",
        "email",
        "birth_date",
        "birth_place",
        "marital_status",
    ]
    values: dict[str, str] = {}
    for key in required:
        values[key] = _require_string(personal, key, "personal_data")

    _parse_date(values["birth_date"], "personal_data.birth_date")

    return PersonalDataModel(
        name=values["name"],
        street=values["street"],
        postal_code=values["postal_code"],
        city=values["city"],
        phone=values["phone"],
        mobile=values["mobile"],
        email=values["email"],
        birth_date=values["birth_date"],
        birth_place=values["birth_place"],
        marital_status=values["marital_status"],
        signing_place=_optional_string(personal, "signing_place"),
    )


def _parse_cv_model(cv: Any) -> CVModel:
    if not isinstance(cv, dict):
        raise ValidationError("application.cv must be an object")

    exp = cv.get("professional_experience")
    edu = cv.get("education")
    add_sections = cv.get("additional_sections", [])
    skills = cv.get("skills")
    signing_date = _require_string(cv, "signing_date", "application.cv")

    if not isinstance(exp, list):
        raise ValidationError("application.cv.professional_experience must be an array")
    if not isinstance(edu, list):
        raise ValidationError("application.cv.education must be an array")
    if not isinstance(add_sections, list):
        raise ValidationError("application.cv.additional_sections must be an array")
    if not isinstance(skills, dict):
        raise ValidationError("application.cv.skills must be an object")

    _parse_date(signing_date, "application.cv.signing_date")

    exp_entries = [_parse_cv_entry(entry, f"application.cv.professional_experience[{idx}]") for idx, entry in enumerate(exp)]
    edu_entries = [_parse_cv_entry(entry, f"application.cv.education[{idx}]") for idx, entry in enumerate(edu)]

    additional_sections: list[CVAdditionalSectionModel] = []
    for sidx, section in enumerate(add_sections):
        if not isinstance(section, dict):
            raise ValidationError(f"application.cv.additional_sections[{sidx}] must be an object")
        title = _require_string(section, "title", f"application.cv.additional_sections[{sidx}]")
        entries_raw = section.get("entries", [])
        if not isinstance(entries_raw, list):
            raise ValidationError(f"application.cv.additional_sections[{sidx}].entries must be an array")
        entries = [
            _parse_cv_entry(entry, f"application.cv.additional_sections[{sidx}].entries[{eidx}]")
            for eidx, entry in enumerate(entries_raw)
        ]
        additional_sections.append(CVAdditionalSectionModel(title=title, entries=entries))

    skill_sections_raw = skills.get("sections")
    if not isinstance(skill_sections_raw, list):
        raise ValidationError("application.cv.skills.sections must be an array")

    skill_sections: list[CVSkillSectionModel] = []
    for sidx, section in enumerate(skill_sections_raw):
        if not isinstance(section, dict):
            raise ValidationError(f"application.cv.skills.sections[{sidx}] must be an object")
        title = _require_string(section, "title", f"application.cv.skills.sections[{sidx}]")
        skill_type = _require_string(section, "type", f"application.cv.skills.sections[{sidx}]")
        if skill_type not in {"general", "language"}:
            raise ValidationError(
                f"Invalid skill type '{skill_type}' in application.cv.skills.sections[{sidx}] (allowed: general, language)"
            )

        items_raw = section.get("items")
        if not isinstance(items_raw, list) or not items_raw:
            raise ValidationError(f"application.cv.skills.sections[{sidx}].items must be a non-empty array")

        items: list[CVSkillItemModel] = []
        for iidx, item in enumerate(items_raw):
            if not isinstance(item, dict):
                raise ValidationError(f"application.cv.skills.sections[{sidx}].items[{iidx}] must be an object")
            name = _require_string(item, "name", f"application.cv.skills.sections[{sidx}].items[{iidx}]")
            level = item.get("level")
            if not isinstance(level, int):
                raise ValidationError(f"application.cv.skills.sections[{sidx}].items[{iidx}].level must be an integer")
            max_level = 4 if skill_type == "general" else 6
            if level < 1 or level > max_level:
                raise ValidationError(
                    f"Invalid skill level {level} in application.cv.skills.sections[{sidx}].items[{iidx}] for type '{skill_type}'"
                )
            items.append(CVSkillItemModel(name=name, level=level))

        skill_sections.append(CVSkillSectionModel(title=title, type=skill_type, items=items))

    return CVModel(
        professional_experience=exp_entries,
        education=edu_entries,
        additional_sections=additional_sections,
        skills_sections=skill_sections,
        signing_date=signing_date,
    )


def _parse_cover_letter_model(cover_letter: Any) -> CoverLetterModel:
    if not isinstance(cover_letter, dict):
        raise ValidationError("application.cover_letter must be an object")

    company = _require_string(cover_letter, "company", "application.cover_letter")
    city = _require_string(cover_letter, "company_city", "application.cover_letter")
    postal_code = _optional_string(cover_letter, "company_postal_code")
    street = _optional_string(cover_letter, "company_street")
    division = _optional_string(cover_letter, "division")
    job_title = _optional_string(cover_letter, "job_title")
    reference_number = _optional_string(cover_letter, "reference_number")
    subject = _optional_string(cover_letter, "subject")
    contact_person = _optional_string(cover_letter, "contact_person")
    application_date = _require_string(cover_letter, "application_date", "application.cover_letter")
    _parse_date(application_date, "application.cover_letter.application_date")

    paragraphs_raw = cover_letter.get("body_paragraphs")
    if not isinstance(paragraphs_raw, list) or not paragraphs_raw:
        raise ValidationError("application.cover_letter.body_paragraphs must be a non-empty array")

    body_paragraphs: list[str] = []
    for idx, paragraph in enumerate(paragraphs_raw):
        if not isinstance(paragraph, str) or not paragraph.strip():
            raise ValidationError(f"application.cover_letter.body_paragraphs[{idx}] must be a non-empty string")
        body_paragraphs.append(paragraph.strip())

    return CoverLetterModel(
        company=company,
        company_city=city,
        company_postal_code=postal_code,
        company_street=street,
        division=division,
        job_title=job_title,
        reference_number=reference_number,
        subject=subject,
        contact_person=contact_person,
        application_date=application_date,
        body_paragraphs=body_paragraphs,
        salutation=_optional_string(cover_letter, "salutation"),
        closing=_optional_string(cover_letter, "closing"),
    )


def _parse_application_model(application_data: dict[str, Any]) -> ApplicationModel:
    language = _require_string(application_data, "language", "application")
    if language not in LANGUAGE_MAP:
        raise ValidationError(f"Unsupported language '{language}' (supported: de, en)")

    cv_raw = application_data.get("cv")
    cover_raw = application_data.get("cover_letter")
    if cv_raw is None:
        raise ValidationError("Missing required object: application.cv")
    if cover_raw is None:
        raise ValidationError("Missing required object: application.cover_letter")

    return ApplicationModel(
        language=language,
        cv=_parse_cv_model(cv_raw),
        cover_letter=_parse_cover_letter_model(cover_raw),
        photo=_optional_string(application_data, "photo"),
        signature=_optional_string(application_data, "signature"),
    )


def _parse_date(value: str, context: str) -> date:
    parts = value.split("-")
    if len(parts) != 3:
        raise ValidationError(f"Invalid date format for {context}: '{value}' (expected YYYY-MM-DD)")
    try:
        year = int(parts[0])
        month = int(parts[1])
        day = int(parts[2])
        return date(year, month, day)
    except ValueError as exc:
        raise ValidationError(f"Invalid date value for {context}: '{value}'") from exc


def _parse_year_month(value: str, context: str) -> tuple[int, int]:
    parts = value.split("-")
    if len(parts) != 2:
        raise ValidationError(f"Invalid month format for {context}: '{value}' (expected YYYY-MM)")
    try:
        year = int(parts[0])
        month = int(parts[1])
    except ValueError as exc:
        raise ValidationError(f"Invalid month value for {context}: '{value}'") from exc
    if month < 1 or month > 12:
        raise ValidationError(f"Invalid month value for {context}: '{value}'")
    return year, month


def _format_date(value: date, language: str) -> str:
    if language == "de":
        return f"{value.day}. {MONTHS['de'][value.month - 1]} {value.year}"
    return f"{MONTHS['en'][value.month - 1]} {value.day}, {value.year}"


def _format_year_month(value: str, language: str) -> str:
    year, month = _parse_year_month(value, "period")
    if language == "de":
        return f"{month:02d}.{year}"
    return f"{month:02d}/{year}"


def _validate_image(path: Path, label: str) -> None:
    if not path.exists():
        raise ValidationError(f"{label} file does not exist: {path}")
    if not path.is_file():
        raise ValidationError(f"{label} path is not a file: {path}")
    if Image is None:
        # Pillow is optional for no-asset generation; keep deterministic
        # validation for presence/type and skip content verification.
        return
    try:
        with Image.open(path) as img:
            img.verify()
    except (UnidentifiedImageError, OSError) as exc:
        raise ValidationError(f"Invalid supplied image file for {label}: {path}") from exc


def _resolve_optional_asset(value: str | None, label: str, base_dir: Path) -> Path | None:
    if not value:
        return None
    asset_path = Path(value)
    if not asset_path.is_absolute():
        asset_path = (base_dir / asset_path).resolve()
    _validate_image(asset_path, label)
    return asset_path


def _find_default_asset_in_data_dir(base_dir: Path, label: str) -> str:
    stems = {
        "photo": ["profile_photo", "photo"],
        "signature": ["signature", "signatur"],
    }
    for stem in stems[label]:
        for ext in DEFAULT_ASSET_EXTENSIONS:
            candidate = (base_dir / f"{stem}{ext}").resolve()
            if candidate.exists() and candidate.is_file():
                return str(candidate)
    return ""


def _select_asset_value(
    cli_value: Path | None,
    personal_data: dict[str, Any],
    application_data: dict[str, Any],
    key: str,
    base_dir: Path,
) -> str:
    if cli_value is not None:
        return str(cli_value)

    personal_value = _optional_string(personal_data, key)
    if personal_value:
        return personal_value

    app_value = _optional_string(application_data, key)
    if app_value:
        return app_value

    return _find_default_asset_in_data_dir(base_dir, key)


def _normalize_personal_data(personal: PersonalDataModel) -> PersonalDataModel:
    return personal


def _normalize_cv(cv: CVModel, language: str) -> NormalizedCVModel:
    def normalize_entry(entry: CVEntryModel, context: str) -> NormalizedCVEntryModel:
        _parse_year_month(entry.start, f"{context}.start")
        present = False
        end = ""
        if entry.end is None or entry.end == "":
            present = True
        else:
            end = entry.end
            if end.lower() == "present":
                present = True
            else:
                _parse_year_month(end, f"{context}.end")

        return NormalizedCVEntryModel(
            start=_format_year_month(entry.start, language),
            end=FIXED_TEXT[language]["cv"]["present"] if present else _format_year_month(end, language),
            title=entry.title,
            organization=entry.organization,
            location=entry.location,
            description=entry.description,
            tasks=entry.tasks,
        )

    exp_entries = [
        normalize_entry(entry, f"application.cv.professional_experience[{idx}]")
        for idx, entry in enumerate(cv.professional_experience)
    ]
    edu_entries = [normalize_entry(entry, f"application.cv.education[{idx}]") for idx, entry in enumerate(cv.education)]

    normalized_additional: list[NormalizedCVAdditionalSectionModel] = []
    for sidx, section in enumerate(cv.additional_sections):
        entries = [
            normalize_entry(entry, f"application.cv.additional_sections[{sidx}].entries[{eidx}]")
            for eidx, entry in enumerate(section.entries)
        ]
        if entries:
            normalized_additional.append(NormalizedCVAdditionalSectionModel(title=section.title, entries=entries))

    normalized_skill_sections: list[NormalizedCVSkillSectionModel] = []
    for section in cv.skills_sections:
        level_map = FIXED_TEXT[language]["skill_levels"][section.type]
        items = [NormalizedCVSkillItemModel(name=item.name, level_text=level_map[item.level]) for item in section.items]
        normalized_skill_sections.append(NormalizedCVSkillSectionModel(title=section.title, type=section.type, items=items))

    signing_date = _parse_date(cv.signing_date, "application.cv.signing_date")

    return NormalizedCVModel(
        professional_experience=exp_entries,
        education=edu_entries,
        additional_sections=normalized_additional,
        skills=normalized_skill_sections,
        signing_date=_format_date(signing_date, language),
    )


def _normalize_cover_letter(cover_letter: CoverLetterModel, language: str) -> NormalizedCoverLetterModel:
    application_date = _parse_date(cover_letter.application_date, "application.cover_letter.application_date")

    salutation = cover_letter.salutation
    closing = cover_letter.closing

    text = FIXED_TEXT[language]["cover_letter"]
    if not salutation:
        if cover_letter.contact_person:
            salutation = text.get("default_salutation_with_contact", text["default_salutation_no_contact"]).format(
                contact=cover_letter.contact_person
            )
        else:
            salutation = text["default_salutation_no_contact"]

    if not closing:
        if language == "de":
            closing = text["default_closing"]
        else:
            closing = (
                text["default_closing_with_contact"]
                if cover_letter.contact_person
                else text["default_closing_no_contact"]
            )

    subject = cover_letter.subject
    if not subject:
        if cover_letter.job_title:
            subject = f"{text['application_subject_prefix']}{cover_letter.job_title}"
        else:
            subject = text["initiative_subject"]

    return NormalizedCoverLetterModel(
        company=cover_letter.company,
        company_city=cover_letter.company_city,
        company_postal_code=cover_letter.company_postal_code,
        company_street=cover_letter.company_street,
        division=cover_letter.division,
        job_title=cover_letter.job_title,
        reference_number=cover_letter.reference_number,
        subject=subject,
        contact_person=cover_letter.contact_person,
        application_date=_format_date(application_date, language),
        paragraphs=cover_letter.body_paragraphs,
        salutation=salutation,
        closing=closing,
    )


def _validate_inputs(personal_data: dict[str, Any], application_data: dict[str, Any], base_dir: Path) -> dict[str, Any]:
    personal_model = _parse_personal_data_model(personal_data)
    application_model = _parse_application_model(application_data)

    normalized = NormalizedRenderModel(
        language=application_model.language,
        language_babel=LANGUAGE_MAP[application_model.language],
        personal=_normalize_personal_data(personal_model),
        cv=_normalize_cv(application_model.cv, application_model.language),
        cover_letter=_normalize_cover_letter(application_model.cover_letter, application_model.language),
        photo=_resolve_optional_asset(application_model.photo, "photo", base_dir),
        signature=_resolve_optional_asset(application_model.signature, "signature", base_dir),
    )

    return {
        "language": normalized.language,
        "language_babel": normalized.language_babel,
        "personal": asdict(normalized.personal),
        "cv": asdict(normalized.cv),
        "cover_letter": asdict(normalized.cover_letter),
        "photo": normalized.photo,
        "signature": normalized.signature,
    }


def _build_cv_content(data: dict[str, Any]) -> str:
    language = data["language"]
    cv_text = FIXED_TEXT[language]["cv"]
    personal = data["personal"]
    cv = data["cv"]

    lines: list[str] = []
    lines.append(_latex_cmd("Language", data["language_babel"]))
    lines.append(_latex_cmd("CVTitleText", cv_text["title"]))
    lines.append(_latex_cmd("CVName", personal["name"]))

    birth_dt = _parse_date(personal["birth_date"], "personal_data.birth_date")
    birth_formatted = _format_date(birth_dt, language)
    lines.append(_latex_cmd("CVBirthDate", birth_formatted))
    lines.append(_latex_cmd("CVBirthPlace", personal["birth_place"]))
    lines.append(_latex_cmd("CVStreet", personal["street"]))
    lines.append(_latex_cmd("CVCity", f"{personal['postal_code']} {personal['city']}"))
    lines.append(_latex_cmd("CVPhone", personal["phone"]))
    lines.append(_latex_cmd("CVMobile", personal["mobile"]))
    lines.append(_latex_cmd("CVEmail", personal["email"]))
    lines.append(_latex_cmd("CVMaritalStatus", personal["marital_status"]))
    lines.append(_latex_cmd_raw("CVPhotoFile", "profile_photo.jpg" if data["photo"] else ""))
    lines.append(_latex_cmd("CVHeadingPersonalDetails", cv_text["personal_details"]))
    lines.append(_latex_cmd("CVHeadingProfessionalExperience", cv_text["professional_experience"]))
    lines.append(_latex_cmd("CVHeadingEducation", cv_text["education"]))
    lines.append(_latex_cmd("CVHeadingSkills", cv_text["skills"]))
    lines.append(_latex_cmd("CVLabelName", cv_text["name"]))
    lines.append(_latex_cmd("CVLabelBirth", cv_text["birth"]))
    lines.append(_latex_cmd("CVLabelAddress", cv_text["address"]))
    lines.append(_latex_cmd("CVLabelPhone", cv_text["phone"]))
    lines.append(_latex_cmd("CVLabelMobile", cv_text["mobile"]))
    lines.append(_latex_cmd("CVLabelEmail", cv_text["email"]))
    lines.append(_latex_cmd("CVLabelMaritalStatus", cv_text["marital_status"]))
    lines.append(_latex_cmd("CVAtText", cv_text["at"]))
    lines.append(_latex_cmd("CVResponsibilitiesHeading", cv_text["tasks"]))

    def render_tasks(tasks: list[str]) -> str:
        if not tasks:
            return ""
        return "".join(f"\\CVTask{{{_latex_escape(task)}}}" for task in tasks)

    def render_job_macro(name: str, entries: list[dict[str, Any]]) -> None:
        blocks: list[str] = []
        for entry in entries:
            tasks_block = render_tasks(entry["tasks"])
            title_line = _latex_escape(entry["title"])
            if entry["description"]:
                title_line += " " + _latex_escape(entry["description"])
            blocks.append(
                "\\CVJob"
                f"{{{_latex_escape(entry['start'])}}}"
                f"{{{_latex_escape(entry['end'])}}}"
                f"{{{title_line}}}"
                f"{{{_latex_escape(entry['organization'])}}}"
                f"{{{_latex_escape(entry['location'])}}}"
                f"{{{tasks_block}}}"
            )
        lines.append(f"\\newcommand{{\\{name}}}{{{' '.join(blocks)}}}")

    def render_activity_macro(name: str, entries: list[dict[str, Any]]) -> None:
        blocks: list[str] = []
        for entry in entries:
            blocks.append(
                "\\CVActivity"
                f"{{{_latex_escape(entry['start'])}}}"
                f"{{{_latex_escape(entry['end'])}}}"
                f"{{{_latex_escape(entry['title'])}}}"
                f"{{{_latex_escape(entry['description'])}}}"
                f"{{{_latex_escape(entry['organization'])}}}"
                f"{{{_latex_escape(entry['location'])}}}"
            )
        lines.append(f"\\newcommand{{\\{name}}}{{{' '.join(blocks)}}}")

    render_job_macro("CVProfessionalExperienceEntries", cv["professional_experience"])
    render_activity_macro("CVEducationEntries", cv["education"])

    additional_blocks: list[str] = []
    for section in cv["additional_sections"]:
        section_entries: list[str] = []
        for entry in section["entries"]:
            section_entries.append(
                "\\CVActivity"
                f"{{{_latex_escape(entry['start'])}}}"
                f"{{{_latex_escape(entry['end'])}}}"
                f"{{{_latex_escape(entry['title'])}}}"
                f"{{{_latex_escape(entry['description'])}}}"
                f"{{{_latex_escape(entry['organization'])}}}"
                f"{{{_latex_escape(entry['location'])}}}"
            )
        additional_blocks.append(
            f"\\CVSection{{{_latex_escape(section['title'])}}}{''.join(section_entries)}"
        )
    lines.append(f"\\newcommand{{\\CVAdditionalSections}}{{{''.join(additional_blocks)}}}")

    skill_rows: list[str] = []
    for section_idx, section in enumerate(cv["skills"]):
        first = True
        for item in section["items"]:
            left_col = _latex_escape(section["title"]) if first else ""
            first = False
            skill_rows.append(
                f"{left_col} & {_latex_escape(item['name'])} & {_latex_escape(item['level_text'])}\\\\"
            )
        if section_idx < len(cv["skills"]) - 1 and skill_rows:
            skill_rows[-1] = skill_rows[-1] + "[0.28222cm]"

    lines.append(
        "\\newcommand{\\CVSkills}{%\n"
        "\\noindent{\\CVBodyFont\\renewcommand{\\arraystretch}{1.18}%\n"
        "\\begin{tabularx}{\\CVPersonalTextWidth}{@{}p{\\CVDateColumnWidth}@{}p{5.00062cm}@{}X@{}}\n"
        + "\n".join(skill_rows)
        + "\n\\end{tabularx}}%\n}"
    )

    signing_place = personal["signing_place"] or personal["city"]
    lines.append(_latex_cmd("CVSigningPlace", signing_place))
    lines.append(_latex_cmd("CVSigningDate", cv["signing_date"]))

    return "\n".join(lines) + "\n"


def _build_cover_letter_content(data: dict[str, Any]) -> tuple[str, str]:
    language = data["language"]
    cover = data["cover_letter"]
    personal = data["personal"]
    text = FIXED_TEXT[language]["cover_letter"]

    content_lines: list[str] = []
    content_lines.append(_latex_cmd("Language", data["language_babel"]))
    content_lines.append(_latex_cmd("JobTitel", cover["job_title"]))
    content_lines.append(_latex_cmd("InitiativeApplicationJobTitel", ""))
    content_lines.append(_latex_cmd("RefNum", cover["reference_number"]))
    content_lines.append(_latex_cmd("CompanyName", cover["company"]))
    content_lines.append(_latex_cmd("Division", cover["division"]))

    if cover["contact_person"]:
        parts = cover["contact_person"].split()
        if len(parts) == 1:
            first = ""
            last = parts[0]
        else:
            first = " ".join(parts[:-1])
            last = parts[-1]
        title = ""
    else:
        title = ""
        first = ""
        last = ""

    content_lines.append(_latex_cmd("ContactPersonTitle", title))
    content_lines.append(_latex_cmd("ContactPersonFirst", first))
    content_lines.append(_latex_cmd("ContactPersonLast", last))
    content_lines.append(_latex_cmd("Street", cover["company_street"]))
    content_lines.append(_latex_cmd("City", cover["company_city"]))
    content_lines.append(_latex_cmd("PostalCode", cover["company_postal_code"]))

    content_lines.append(_latex_cmd("ApplicationDate", cover["application_date"]))
    content_lines.append(_latex_cmd("ApplicationPlace", personal["city"]))
    content_lines.append(_latex_cmd("CoverLetterSubject", cover["subject"]))

    reference_label = text["reference_label"]
    reference_line = f"[{reference_label}: {cover['reference_number']}]" if cover["reference_number"] else ""
    content_lines.append(_latex_cmd("CoverLetterReferenceLine", reference_line))

    address_lines = [cover["company"]]
    contact_line = " ".join(part for part in [title, first, last] if part).strip()
    if contact_line:
        address_lines.append(contact_line)
    if cover["division"]:
        address_lines.append(cover["division"])
    if cover["company_street"]:
        address_lines.append(cover["company_street"])
        city_line = (
            f"{cover['company_postal_code']} {cover['company_city']}"
            if cover["company_postal_code"]
            else cover["company_city"]
        )
    else:
        city_line = cover["company_city"]
    address_lines.append(city_line)
    escaped_address_lines = [_latex_escape(line) for line in address_lines]
    content_lines.append(f"\\newcommand{{\\CoverLetterAddress}}{{{'\\\\'.join(escaped_address_lines)}}}")

    content_lines.append(_latex_cmd("CoverLetterSalutation", cover["salutation"]))
    content_lines.append(_latex_cmd("CoverLetterClosing", cover["closing"]))

    paragraph_lines = []
    for paragraph in cover["paragraphs"]:
        paragraph_lines.append(f"\\CoverParagraph{{{_latex_escape(paragraph)}}}")
    content_lines.append(f"\\newcommand{{\\CoverLetterParagraphs}}{{{''.join(paragraph_lines)}}}")

    if data["signature"] is not None:
        content_lines.append(_latex_cmd_raw("SignatureFile", "signature.jpeg"))
    else:
        content_lines.append(_latex_cmd_raw("SignatureFile", ""))

    personalized_lines: list[str] = []
    personalized_lines.append(_latex_cmd("SenderName", personal["name"]))
    personalized_lines.append(_latex_cmd("SenderStreet", personal["street"]))
    personalized_lines.append(_latex_cmd("SenderPostalCode", personal["postal_code"]))
    personalized_lines.append(_latex_cmd("SenderCity", personal["city"]))
    personalized_lines.append(_latex_cmd("SenderPhone", personal["mobile"]))
    personalized_lines.append(_latex_cmd("SenderEmail", personal["email"]))

    personalized_lines.append(_latex_cmd("LabelMobile", text["mobile"]))
    personalized_lines.append(_latex_cmd("LabelEmail", text["email"]))

    personalized_lines.append(
        "\\newcommand{\\MyHeader}{%\n"
        "\\begingroup\\sffamily\\color{TemplateBlack}%\n"
        "\\noindent\\makebox[\\linewidth][r]{\\bfseries\\fontsize{11pt}{13.2pt}\\selectfont\\SenderName}%\n"
        "\\par\\vspace{-0.45ex}{\\color{TemplateBlue}\\rule{\\linewidth}{0.8pt}}%\n"
        "\\par\\vspace{4.0mm}\\raggedleft\\fontsize{11pt}{13.2pt}\\selectfont\n"
        "\\SenderStreet\\par\\SenderPostalCode~\\SenderCity\\par\n"
        "\\LabelMobile: \\SenderPhone\\par\n"
        "\\LabelEmail: \\SenderEmail\\par\n"
        "\\endgroup\n"
        "}"
    )

    personalized_lines.append(_latex_cmd("MyOpening", cover["salutation"]))
    personalized_lines.append(_latex_cmd("MyClosing", cover["closing"]))
    personalized_lines.append(_latex_cmd("MyClosingSentence", ""))

    return "\n".join(content_lines) + "\n", "\n".join(personalized_lines) + "\n"


def _patch_cv_main(original_main: str) -> str:
        patched = original_main

        # Keep the template visual design intact while making Python the single
        # source of entry composition logic.
        replacements = {
                """\\providecommand{\\CVProfessionalExperienceEntries}{%
    \\CVJobOne
    \\CVJobTwo
    \\CVJobThree
    \\CVJobFour
    \\CVJobFive
    \\CVJobSix
}""": """\\providecommand{\\CVProfessionalExperienceEntries}{}""",
                """\\providecommand{\\CVEducationEntries}{%
    \\CVEducationOne
    \\CVEducationTwo
    \\CVEducationThree
}""": """\\providecommand{\\CVEducationEntries}{}""",
                """\\providecommand{\\CVAdditionalSections}{%
\\CVActivitySection
    {\\CVText{Weiterbildungen}{Further Training}}
    {\\CVTrainingOne}
    {\\CVTrainingTwo}
    {\\CVTrainingThree}
    {\\CVTrainingFour}
    {\\CVTrainingFive}
    {\\CVTrainingSix}

\\CVActivitySection
    {\\CVText{Ehrenamtliches Engagement}{Voluntary Work}}
    {\\CVVolunteeringOne}
    {\\CVVolunteeringTwo}
    {\\CVVolunteeringThree}
    {\\CVVolunteeringFour}
    {\\CVVolunteeringFive}
    {\\CVVolunteeringSix}

\\CVActivitySection
    {\\CVText{Auslandsaufenthalte}{International Experience}}
    {\\CVAbroadOne}
    {\\CVAbroadTwo}
    {\\CVAbroadThree}
    {\\CVAbroadFour}
    {\\CVAbroadFive}
    {\\CVAbroadSix}

\\CVActivitySection
    {\\CVText{Interessen}{Interests}}
    {\\CVInterestOne}
    {\\CVInterestTwo}
    {\\CVInterestThree}
    {\\CVInterestFour}
    {\\CVInterestFive}
    {\\CVInterestSix}
}""": """\\providecommand{\\CVAdditionalSections}{}""",
        }

        for old, new in replacements.items():
                patched = patched.replace(old, new)

        return patched


def _patch_cover_main(original_main: str) -> str:
    patched = original_main

    # Preserve layout while removing template-side fallback logic that can
    # introduce non-JSON defaults.
    replacements = {
        r"\providecommand{\CoverLetterReferenceLine}{\ifdefempty{\RefNum}{}{[Ref.: \RefNum]}}": r"\providecommand{\CoverLetterReferenceLine}{}",
        """\\providecommand{\\CoverLetterParagraphs}{%
  \\CoverParagraph{\\firstParagraph}
  \\CoverParagraph{\\secondParagraph}
  \\CoverParagraph{\\thirdParagraph}
  \\fourthParagraph~\\MyClosingSentence\\par
}""": r"\providecommand{\CoverLetterParagraphs}{}",
        r"\providecommand{\ApplicationDate}{\today}": r"\providecommand{\ApplicationDate}{}",
        r"\providecommand{\ApplicationPlace}{\SenderCity}": r"\providecommand{\ApplicationPlace}{}",
    }

    for old, new in replacements.items():
        patched = patched.replace(old, new)

    return patched


def _run_pdflatex(work_dir: Path) -> None:
    main_tex = work_dir / "main.tex"
    if not main_tex.exists():
        raise ValidationError(
            f"Missing LaTeX entry file: {main_tex}. "
            "This can happen if templates are incomplete or another generation run modified _build concurrently."
        )

    cmd = ["pdflatex", "-interaction=nonstopmode", "-halt-on-error", "main.tex"]
    for _ in range(2):
        result = subprocess.run(
            cmd,
            cwd=work_dir,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if result.returncode != 0:
            output = (result.stdout or "") + "\n" + (result.stderr or "")
            tail = "\n".join(output.splitlines()[-60:])
            raise ValidationError(f"LaTeX compilation error in {work_dir}:\n{tail}")


def _stage_and_generate(validated: dict[str, Any], output_dir: Path, template_root: Path) -> GeneratedPaths:
    cv_template_dir = template_root / "6a61d3cd329475a057f02f74"
    letter_template_dir = template_root / "6a68ff588826288f9a387054"

    if not cv_template_dir.exists() or not letter_template_dir.exists():
        raise ValidationError("Template directories are missing under tmp_overleaf")

    build_root = output_dir / "_build"
    cv_build = build_root / "cv"
    letter_build = build_root / "cover_letter"

    if build_root.exists():
        shutil.rmtree(build_root)
    cv_build.mkdir(parents=True, exist_ok=True)
    letter_build.mkdir(parents=True, exist_ok=True)

    for source in cv_template_dir.iterdir():
        if source.is_file() and source.suffix.lower() != ".pdf":
            shutil.copy2(source, cv_build / source.name)

    for source in letter_template_dir.iterdir():
        if source.is_file() and source.suffix.lower() != ".pdf":
            shutil.copy2(source, letter_build / source.name)

    if not (cv_build / "main.tex").exists():
        raise ValidationError(f"Template file missing after copy: {cv_build / 'main.tex'}")
    if not (letter_build / "main.tex").exists():
        raise ValidationError(f"Template file missing after copy: {letter_build / 'main.tex'}")

    cv_main_path = cv_build / "main.tex"
    cv_content_path = cv_build / "cv_content.tex"

    cv_main_original = cv_main_path.read_text(encoding="utf-8")
    cv_main_path.write_text(_patch_cv_main(cv_main_original), encoding="utf-8")

    cv_content = _build_cv_content(validated)
    if validated["signature"] is not None:
        cv_content += _latex_cmd_raw("CVSignatureFile", "signature.jpeg") + "\n"
        shutil.copy2(validated["signature"], cv_build / "signature.jpeg")
    else:
        cv_content += _latex_cmd_raw("CVSignatureFile", "") + "\n"

    cv_content_path.write_text(cv_content, encoding="utf-8")
    if validated["photo"] is not None:
        shutil.copy2(validated["photo"], cv_build / "profile_photo.jpg")

    letter_main_path = letter_build / "main.tex"
    content_cover_path = letter_build / "content_cover_letter.tex"
    personalized_path = letter_build / "personalised.tex"

    letter_main_original = letter_main_path.read_text(encoding="utf-8")
    letter_main_path.write_text(_patch_cover_main(letter_main_original), encoding="utf-8")

    content_cover, personalized = _build_cover_letter_content(validated)
    content_cover_path.write_text(content_cover, encoding="utf-8")
    personalized_path.write_text(personalized, encoding="utf-8")

    if validated["signature"] is not None:
        shutil.copy2(validated["signature"], letter_build / "signature.jpeg")

    _run_pdflatex(cv_build)
    _run_pdflatex(letter_build)

    output_dir.mkdir(parents=True, exist_ok=True)
    cv_pdf = output_dir / "cv.pdf"
    letter_pdf = output_dir / "cover_letter.pdf"

    shutil.copy2(cv_build / "main.pdf", cv_pdf)
    shutil.copy2(letter_build / "main.pdf", letter_pdf)

    return GeneratedPaths(cv_pdf=cv_pdf, cover_letter_pdf=letter_pdf)


def generate_documents(
    personal_data_path: Path,
    application_path: Path,
    output_dir: Path,
    photo: Path | None,
    signature: Path | None,
) -> GeneratedPaths:
    personal_data = _load_json(personal_data_path)
    application_data = _load_json(application_path)

    # Deterministic precedence for optional assets:
    # CLI flag > personal_data.json > application.json > defaults in data dir.
    base_dir = application_path.parent
    application_data["photo"] = _select_asset_value(photo, personal_data, application_data, "photo", base_dir)
    application_data["signature"] = _select_asset_value(signature, personal_data, application_data, "signature", base_dir)

    validated = _validate_inputs(personal_data, application_data, base_dir=application_path.parent)
    template_root = Path(__file__).resolve().parent.parent / "tmp_overleaf"
    resolved_output_dir = output_dir.resolve()
    resolved_output_dir.mkdir(parents=True, exist_ok=True)
    return _stage_and_generate(validated, output_dir=resolved_output_dir, template_root=template_root)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cv_generator",
        description="Deterministic CV + cover-letter generator using local Overleaf templates.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate cv.pdf and cover_letter.pdf")
    generate.add_argument("--personal-data", required=True, type=Path, help="Path to personal_data.json")
    generate.add_argument("--application", required=True, type=Path, help="Path to application.json")
    generate.add_argument("--output-dir", required=True, type=Path, help="Output directory")
    generate.add_argument("--photo", type=Path, default=None, help="Optional profile photo path")
    generate.add_argument("--signature", type=Path, default=None, help="Optional signature image path")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        try:
            paths = generate_documents(
                personal_data_path=args.personal_data,
                application_path=args.application,
                output_dir=args.output_dir,
                photo=args.photo,
                signature=args.signature,
            )
        except ValidationError as exc:
            print(f"ERROR: {exc}")
            return 2

        print(f"Generated: {paths.cv_pdf}")
        print(f"Generated: {paths.cover_letter_pdf}")
        return 0

    parser.print_help()
    return 1
