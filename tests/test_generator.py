from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest

from src.generator import (
    ValidationError,
    generate_cover_letter_body,
    generate_cover_letter_preamble,
    generate_cv_latex,
    load_json,
    validate_and_resolve_inputs,
)


ROOT = Path(__file__).resolve().parent.parent


def _education_entry(start_date, end_date, degree, institution, location, items=None):
    entry = {
        "start_date": start_date,
        "end_date": end_date,
        "degree": degree,
        "institution": institution,
        "location": location,
    }
    if items is not None:
        entry["items"] = items
    return entry


def _load_inputs(personal_name: str = "personal_data.json", app_name: str = "application.json"):
    personal = load_json(ROOT / "data" / personal_name)
    application = load_json(ROOT / "data" / app_name)
    return personal, application


def test_valid_input_without_email_succeeds():
    personal, application = _load_inputs()

    resolved = validate_and_resolve_inputs(personal, application)

    assert resolved.personal_required_values["first_name"] == "Max"
    assert "email" not in resolved.personal_required_values


@pytest.mark.parametrize(
    ("language", "expected_labels"),
    [
        ("de", ["Name", "Geburtsdatum/-ort", "Addresse"]),
        ("en", ["Name", "Date / Place of birth", "Address"]),
    ],
)
def test_grouped_required_personal_data_rows_are_exact(language, expected_labels):
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = language
    personal["required_fields"]["birth_date"] = "1985-03-05"

    resolved = validate_and_resolve_inputs(personal, application)

    required_rows = resolved.personal_required_rows
    assert [label for label, _ in required_rows] == expected_labels
    assert len(required_rows) == 3
    assert required_rows[0][1] == f"{personal['required_fields']['first_name']} {personal['required_fields']['last_name']}"
    if language == "de":
        assert required_rows[1][1] == "05 Maerz 1985, Budapest"
    else:
        assert required_rows[1][1] == "05 March 1985, Budapest"
    assert required_rows[2][1] == "Musterstrasse 41\\par 80331, Muenchen"


def test_required_personal_data_row_order_is_fixed_independent_of_json_key_order():
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    personal["required_fields"] = {
        "city": personal["required_fields"]["city"],
        "postal_code": personal["required_fields"]["postal_code"],
        "address": personal["required_fields"]["address"],
        "birth_place": personal["required_fields"]["birth_place"],
        "birth_date": personal["required_fields"]["birth_date"],
        "last_name": personal["required_fields"]["last_name"],
        "first_name": personal["required_fields"]["first_name"],
    }

    resolved = validate_and_resolve_inputs(personal, application)

    assert [label for label, _ in resolved.personal_required_rows] == ["Name", "Geburtsdatum/-ort", "Addresse"]


def test_optional_email_renders_when_supplied_and_empty_optional_email_is_omitted():
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    personal["optional_fields"]["E-Mail"] = "max.mustermann@example.com"
    personal["optional_fields"]["Leeres Feld"] = ""
    personal["optional_fields"]["Null Feld"] = None

    resolved = validate_and_resolve_inputs(personal, application)
    optional_rows = resolved.personal_optional_rows
    assert optional_rows[-1] == ("E-Mail", "max.mustermann@example.com")

    optional_labels = [label for label, _ in resolved.personal_optional_rows]
    assert "E-Mail" in optional_labels
    assert "Leeres Feld" not in optional_labels
    assert "Null Feld" not in optional_labels

    personal["optional_fields"]["E-Mail"] = ""
    resolved_without_email = validate_and_resolve_inputs(personal, application)
    optional_labels_without_email = [label for label, _ in resolved_without_email.personal_optional_rows]
    assert "E-Mail" not in optional_labels_without_email


def test_required_fields_are_not_rendered_as_separate_rows_and_optional_rows_follow_them():
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    personal["optional_fields"] = {
        "Alpha": "1",
        "Beta": "2",
    }

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert tex.count(r"\CVPersonalDataRow{") == 5
    assert r"\CVPersonalDataRow{Name}{" in tex
    assert r"\CVPersonalDataRow{Geburtsdatum/-ort}{" in tex
    assert r"\CVPersonalDataRow{Addresse}{" in tex
    assert "Vorname" not in tex
    assert "Nachname" not in tex
    assert "birth_date" not in tex
    assert tex.index(r"\CVPersonalDataRow{Name}{") < tex.index(r"\CVPersonalDataRow{Geburtsdatum/-ort}{") < tex.index(r"\CVPersonalDataRow{Addresse}{")
    assert tex.index(r"\CVPersonalDataRow{Addresse}{") < tex.index(r"\CVPersonalDataRow{Alpha}{") < tex.index(r"\CVPersonalDataRow{Beta}{")


@pytest.mark.parametrize(
    "missing_key",
    ["first_name", "last_name", "birth_date", "birth_place", "address", "postal_code", "city"],
)
def test_missing_required_personal_data_fields_fail(missing_key):
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    del personal["required_fields"][missing_key]

    with pytest.raises(ValidationError):
        validate_and_resolve_inputs(personal, application)


def test_invalid_skill_level_is_rejected():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["cv"]["skills"]["sections"][0]["items"][0]["level"] = 99

    with pytest.raises(ValidationError):
        validate_and_resolve_inputs(personal, application)


def test_cv_latex_contains_expected_dynamic_macros_and_texts():
    personal, application = _load_inputs()
    resolved = validate_and_resolve_inputs(personal, application)

    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert "\\selectlanguage{ngerman}" in tex
    assert "\\CVDocumentTitle{Lebenslauf}" in tex
    assert "\\CVPersonalDataNoPhoto{Persoenliche Daten}" in tex
    assert "\\CVSection{Berufserfahrung}" in tex
    assert "\\CVSection{Ausbildung}" in tex
    assert "\\CVSection{Kenntnisse}" in tex
    assert "\\CVJobEntry{" in tex
    assert "\\CVActivityEntry{" in tex
    assert "\\CVSkillRow{" in tex
    assert "Meine Aufgaben waren:" in tex
    assert "heute" in tex


def test_education_entries_and_items_preserve_json_order_and_render_literals():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            ["First item", "Second item"],
        ),
        _education_entry(
            "2021-10",
            "2023-03",
            "Master of Science",
            "Another University",
            "Hamburg",
            ["Third item"],
        ),
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert tex.index("Bachelor of Science") < tex.index("Master of Science")
    assert tex.index("First item") < tex.index("Second item")
    assert tex.index("Second item") < tex.index("Third item")
    assert "Example University" in tex
    assert "Berlin" in tex


def test_single_education_entry_with_one_item_renders_correctly():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            ["Main subject: Math"],
        )
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert "\\CVSection{Education}" in tex
    assert "\\CVActivityEntry{10.2018 -- 09.2021}{%" in tex
    assert "Bachelor of Science, Example University, Berlin\\par" in tex
    assert "\\vspace{0.05292cm}" in tex
    assert "\\CVTask{Main subject: Math}" in tex


def test_single_education_entry_with_multiple_items_preserves_item_order():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            ["First item", "Second item", "Third item"],
        )
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert tex.index("\\CVTask{First item}") < tex.index("\\CVTask{Second item}") < tex.index("\\CVTask{Third item}")


def test_missing_or_empty_education_items_emit_no_item_content():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
        )
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)
    education_segment = tex.split("\\CVSection{Education}", 1)[1].split("\\CVSection{Skills}", 1)[0]

    assert "Main subject:" not in tex
    assert "\\CVTask{" not in education_segment

    application["cv"]["education"][0]["items"] = []
    resolved = validate_and_resolve_inputs(personal, application)
    tex_with_empty_items = generate_cv_latex(resolved, photo_path=None, signature_path=None)
    empty_education_segment = tex_with_empty_items.split("\\CVSection{Education}", 1)[1].split("\\CVSection{Skills}", 1)[0]

    assert "Main subject:" not in tex_with_empty_items
    assert "\\CVTask{" not in empty_education_segment


def test_invalid_education_items_are_rejected():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            "not-an-array",
        )
    ]

    with pytest.raises(ValidationError):
        validate_and_resolve_inputs(personal, application)


def test_invalid_education_item_values_are_rejected():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            ["Valid item", 123],
        )
    ]

    with pytest.raises(ValidationError):
        validate_and_resolve_inputs(personal, application)


def test_education_text_is_preserved_without_rewrite_or_translation():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["education"] = [
        _education_entry(
            "2018-10",
            "2021-09",
            "Bachelor of Science",
            "Example University",
            "Berlin",
            ["Main subject: Math"],
        )
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert "Bachelor of Science" in tex
    assert "Example University" in tex
    assert "Berlin" in tex
    assert "Main subject: Math" in tex
    assert "\\CVTask{Main subject: Math}" in tex


def test_cv_layout_does_not_use_content_dependent_conditionals_for_education():
    main_tex = (ROOT / "latex" / "cv" / "main.tex").read_text(encoding="utf-8")

    assert "\\CVActivityEntry" in main_tex
    for token in ("\\ifdefempty", "\\ifblank", "\\ifthenelse", "\\ifdefined", "\\newif", "\\isempty"):
        assert token not in main_tex


def test_additional_section_title_and_description_render_in_separate_columns():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["additional_sections"] = [
        {
            "title": "interests",
            "entries": [
                {
                    "title": "Programming",
                    "description": "Ongoing development of programming skills through personal projects.",
                }
            ],
        }
    ]

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert r"\CVActivityEntry{Programming}{%" in tex
    assert "Ongoing development of programming skills through personal projects." in tex


def test_deterministic_output_for_identical_inputs():
    personal, application = _load_inputs()
    resolved = validate_and_resolve_inputs(personal, application)

    tex_1 = generate_cv_latex(resolved, photo_path=None, signature_path=None)
    tex_2 = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert tex_1 == tex_2


def test_valid_english_generation_uses_additional_information_signing_place():
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    personal["additional_information"] = {"signing_place": {"de": "Muenchen", "en": "Munich"}}
    application = deepcopy(application)
    application["language"] = "en"
    application["cv"]["signing_date"] = "2026-03-08"

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert resolved.signing_place == "Munich"
    assert "Munich" in tex
    assert "08 March 2026" in tex


def test_long_date_format_switches_between_languages_for_birth_and_today():
    personal, application = _load_inputs()
    personal = deepcopy(personal)
    application = deepcopy(application)
    personal["required_fields"]["birth_date"] = "1985-03-05"
    application["cv"]["signing_date"] = "2026-03-08"
    application["cover_letter"]["application_date"] = "2026-03-08"

    application["language"] = "en"
    resolved_en = validate_and_resolve_inputs(personal, application)
    tex_en = generate_cv_latex(resolved_en, photo_path=None, signature_path=None)
    preamble_en = generate_cover_letter_preamble(resolved_en)

    assert "05 March 1985, Budapest" in "\n".join(value for _, value in resolved_en.personal_required_rows)
    assert "08 March 2026" in tex_en
    assert "08 March 2026" in preamble_en

    application["language"] = "de"
    resolved_de = validate_and_resolve_inputs(personal, application)
    tex_de = generate_cv_latex(resolved_de, photo_path=None, signature_path=None)
    preamble_de = generate_cover_letter_preamble(resolved_de)

    assert "05 Maerz 1985, Budapest" in "\n".join(value for _, value in resolved_de.personal_required_rows)
    assert "08 Maerz 2026" in tex_de
    assert "08 Maerz 2026" in preamble_de


def test_valid_english_generation_localizes_labels_and_levels():
    personal, application = _load_inputs()
    application = deepcopy(application)
    application["language"] = "en"

    resolved = validate_and_resolve_inputs(personal, application)
    tex = generate_cv_latex(resolved, photo_path=None, signature_path=None)

    assert "\\selectlanguage{english}" in tex
    assert "\\CVDocumentTitle{Curriculum Vitae}" in tex
    assert "\\CVPersonalDataNoPhoto{Personal Data}" in tex
    assert "Expert" in tex


def test_cover_letter_generation_emits_literal_content_blocks():
    personal, application = _load_inputs()
    resolved = validate_and_resolve_inputs(personal, application)

    preamble = generate_cover_letter_preamble(resolved)
    body = generate_cover_letter_body(resolved, signature_path=None)

    assert "\\selectlanguage{ngerman}" in preamble
    assert "\\setkomavar{subject}{Entwicklungsingenieur" in preamble
    assert "\\setkomavar{place}{Muenchen}" in preamble
    assert "\\begin{letter}{Forschung und Entwicklung" in body
    assert "\\opening{Sehr geehrte Damen und Herren,}" in body
    assert "datengetriebener Auswertung entspricht genau meinem Profil." in body
    assert "Freundliche Gruesse" in body


def test_cover_letter_requires_required_structure():
    personal, application = _load_inputs()
    application = deepcopy(application)
    del application["cover_letter"]["job_title"]

    with pytest.raises(ValidationError):
        validate_and_resolve_inputs(personal, application)
