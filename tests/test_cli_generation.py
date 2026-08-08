import unittest
from pathlib import Path
import sys
import types


pil_stub = types.ModuleType("PIL")


class _StubImage:
    @staticmethod
    def open(_path):
        raise RuntimeError("Image.open should not be called in these tests")


class _StubImageError(Exception):
    pass


pil_stub.Image = _StubImage
pil_stub.UnidentifiedImageError = _StubImageError
sys.modules.setdefault("PIL", pil_stub)

from cv_generator.cli import _build_cover_letter_content, _build_cv_content, _validate_inputs


class TestDynamicGeneration(unittest.TestCase):
    def _base_personal_data(self):
        return {
            "name": "Max Mustermann",
            "street": "Musterstrasse 1",
            "postal_code": "80331",
            "city": "Muenchen",
            "phone": "+49 89 111111",
            "mobile": "+49 171 222222",
            "email": "max@example.com",
            "birth_date": "1990-01-15",
            "birth_place": "Muenchen",
            "marital_status": "ledig",
            "signing_place": "Muenchen",
        }

    def _cv_entry(self, idx: int):
        return {
            "start": f"202{idx % 10}-01",
            "end": f"202{idx % 10}-12",
            "title": f"Role {idx}",
            "organization": f"Company {idx}",
            "location": "Munich",
            "description": "",
            "tasks": [f"Task {idx}.1", f"Task {idx}.2"],
        }

    def _application_data(self):
        jobs = [self._cv_entry(i) for i in range(1, 9)]
        education = [self._cv_entry(i) for i in range(9, 12)]
        additional_entries = [self._cv_entry(i) for i in range(12, 20)]

        return {
            "language": "de",
            "cv": {
                "professional_experience": jobs,
                "education": education,
                "additional_sections": [
                    {
                        "title": "Weiterbildungen",
                        "entries": additional_entries,
                    }
                ],
                "skills": {
                    "sections": [
                        {
                            "title": "Sprachen",
                            "type": "language",
                            "items": [
                                {"name": "Deutsch", "level": 6},
                                {"name": "Englisch", "level": 5},
                            ],
                        },
                        {
                            "title": "Tools",
                            "type": "general",
                            "items": [
                                {"name": "Python", "level": 4},
                                {"name": "LaTeX", "level": 3},
                            ],
                        },
                    ]
                },
                "signing_date": "2026-08-08",
            },
            "cover_letter": {
                "company": "Beispiel GmbH",
                "company_city": "Muenchen",
                "application_date": "2026-08-01",
                "body_paragraphs": [
                    "Paragraph one",
                    "Paragraph two",
                    "Paragraph three",
                    "Paragraph four",
                    "Paragraph five",
                ],
                "reference_number": "ABC-42",
                "job_title": "Engineer",
            },
        }

    def test_cv_generation_supports_more_than_6_jobs(self):
        validated = _validate_inputs(self._base_personal_data(), self._application_data(), Path.cwd())
        cv_tex = _build_cv_content(validated)

        self.assertIn("\\newcommand{\\CVProfessionalExperienceEntries}", cv_tex)
        self.assertEqual(cv_tex.count("\\CVJob{"), 8)
        self.assertNotIn("\\CVJobOne", cv_tex)

    def test_cv_additional_sections_support_more_than_6_entries(self):
        validated = _validate_inputs(self._base_personal_data(), self._application_data(), Path.cwd())
        cv_tex = _build_cv_content(validated)

        self.assertIn("\\newcommand{\\CVAdditionalSections}", cv_tex)
        self.assertEqual(cv_tex.count("\\CVSection{Weiterbildungen}"), 1)

        section_start = cv_tex.index("\\newcommand{\\CVAdditionalSections}")
        section_text = cv_tex[section_start:]
        self.assertEqual(section_text.count("\\CVActivity{"), 8)

    def test_cv_education_supports_dynamic_entries(self):
        validated = _validate_inputs(self._base_personal_data(), self._application_data(), Path.cwd())
        cv_tex = _build_cv_content(validated)

        self.assertIn("\\newcommand{\\CVEducationEntries}", cv_tex)
        section_start = cv_tex.index("\\newcommand{\\CVEducationEntries}")
        section_end = cv_tex.index("\\newcommand{\\CVAdditionalSections}")
        education_section = cv_tex[section_start:section_end]
        self.assertEqual(education_section.count("\\CVActivity{"), 3)

    def test_cv_skills_support_dynamic_subsections_and_items(self):
        validated = _validate_inputs(self._base_personal_data(), self._application_data(), Path.cwd())
        cv_tex = _build_cv_content(validated)

        self.assertIn("\\newcommand{\\CVSkills}", cv_tex)
        # Two skill subsections with two skills each are rendered into four rows.
        self.assertEqual(cv_tex.count(" & "), 8)
        self.assertIn("Sprachen & Deutsch & Muttersprache", cv_tex)
        self.assertIn("Tools & Python & Experte", cv_tex)

    def test_cover_letter_generation_supports_dynamic_paragraph_count(self):
        validated = _validate_inputs(self._base_personal_data(), self._application_data(), Path.cwd())
        content_tex, personalized_tex = _build_cover_letter_content(validated)

        self.assertIn("\\newcommand{\\CoverLetterParagraphs}", content_tex)
        self.assertEqual(content_tex.count("\\CoverParagraph{"), 5)
        self.assertIn("\\newcommand{\\ApplicationDate}{1. August 2026}", content_tex)
        self.assertIn("\\newcommand{\\MyOpening}{Sehr geehrte Damen und Herren,}", personalized_tex)


if __name__ == "__main__":
    unittest.main()
