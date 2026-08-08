import sys
import types
import unittest
from pathlib import Path


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

from cv_generator.cli import ValidationError, _validate_inputs


class TestModelsValidation(unittest.TestCase):
    def _personal(self):
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

    def _entry(self, idx: int):
        return {
            "start": f"202{idx % 10}-01",
            "end": f"202{idx % 10}-12",
            "title": f"Role {idx}",
            "organization": f"Company {idx}",
            "location": "Munich",
            "description": "",
            "tasks": [f"Task {idx}.1", f"Task {idx}.2"],
        }

    def _application(self, language: str = "de"):
        jobs = [self._entry(i) for i in range(1, 9)]
        education = [self._entry(i) for i in range(9, 12)]
        additional_entries = [self._entry(i) for i in range(12, 20)]

        app = {
            "language": language,
            "cv": {
                "professional_experience": jobs,
                "education": education,
                "additional_sections": [
                    {
                        "title": "Weiterbildungen" if language == "de" else "Further Training",
                        "entries": additional_entries,
                    }
                ],
                "skills": {
                    "sections": [
                        {
                            "title": "Sprachen" if language == "de" else "Languages",
                            "type": "language",
                            "items": [
                                {"name": "Deutsch" if language == "de" else "German", "level": 6},
                                {"name": "Englisch" if language == "de" else "English", "level": 5},
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
        return app

    def test_validate_inputs_maps_levels_dates_and_dynamic_counts_de(self):
        validated = _validate_inputs(self._personal(), self._application("de"), Path.cwd())

        self.assertEqual(validated["language"], "de")
        self.assertEqual(validated["language_babel"], "ngerman")
        self.assertEqual(len(validated["cv"]["professional_experience"]), 8)
        self.assertEqual(len(validated["cv"]["additional_sections"][0]["entries"]), 8)
        self.assertEqual(validated["cv"]["skills"][0]["items"][0]["level_text"], "Muttersprache")
        self.assertEqual(validated["cv"]["skills"][1]["items"][0]["level_text"], "Experte")
        self.assertEqual(validated["cv"]["signing_date"], "8. August 2026")
        self.assertEqual(validated["cover_letter"]["application_date"], "1. August 2026")

    def test_validate_inputs_formats_english_present_and_closing_defaults(self):
        app = self._application("en")
        app["cv"]["professional_experience"][0]["end"] = None
        app["cover_letter"]["contact_person"] = "Alex Smith"
        validated = _validate_inputs(self._personal(), app, Path.cwd())

        self.assertEqual(validated["language_babel"], "english")
        self.assertEqual(validated["cv"]["professional_experience"][0]["end"], "present")
        self.assertEqual(validated["cover_letter"]["application_date"], "August 1, 2026")
        self.assertEqual(validated["cover_letter"]["salutation"], "Dear Alex Smith,")
        self.assertEqual(validated["cover_letter"]["closing"], "Yours sincerely")

    def test_validate_inputs_formats_english_no_contact_defaults(self):
        app = self._application("en")
        validated = _validate_inputs(self._personal(), app, Path.cwd())

        self.assertEqual(validated["cover_letter"]["salutation"], "Dear Recruiting Team,")
        self.assertEqual(validated["cover_letter"]["closing"], "Yours faithfully")

    def test_invalid_general_skill_level_raises_clear_error(self):
        app = self._application("de")
        app["cv"]["skills"]["sections"][1]["items"][0]["level"] = 5

        with self.assertRaises(ValidationError) as ctx:
            _validate_inputs(self._personal(), app, Path.cwd())

        self.assertIn("Invalid skill level 5", str(ctx.exception))
        self.assertIn("type 'general'", str(ctx.exception))

    def test_invalid_language_skill_level_raises_clear_error(self):
        app = self._application("en")
        app["cv"]["skills"]["sections"][0]["items"][1]["level"] = 7

        with self.assertRaises(ValidationError) as ctx:
            _validate_inputs(self._personal(), app, Path.cwd())

        self.assertIn("Invalid skill level 7", str(ctx.exception))
        self.assertIn("type 'language'", str(ctx.exception))

    def test_invalid_language_code_raises_clear_error(self):
        app = self._application("de")
        app["language"] = "fr"

        with self.assertRaises(ValidationError) as ctx:
            _validate_inputs(self._personal(), app, Path.cwd())

        self.assertIn("Unsupported language 'fr'", str(ctx.exception))

    def test_empty_cover_letter_paragraph_rejected(self):
        app = self._application("de")
        app["cover_letter"]["body_paragraphs"][2] = "   "

        with self.assertRaises(ValidationError) as ctx:
            _validate_inputs(self._personal(), app, Path.cwd())

        self.assertIn("application.cover_letter.body_paragraphs[2]", str(ctx.exception))

    def test_optional_photo_and_signature_paths_are_validated(self):
        app = self._application("de")
        app["photo"] = "missing-photo.png"

        with self.assertRaises(ValidationError) as ctx:
            _validate_inputs(self._personal(), app, Path.cwd())

        self.assertIn("photo file does not exist", str(ctx.exception))

    def test_json_text_is_preserved_not_translated(self):
        app = self._application("de")
        custom_title = "Spezialrolle QA-42"
        app["cv"]["professional_experience"][0]["title"] = custom_title
        validated = _validate_inputs(self._personal(), app, Path.cwd())

        self.assertEqual(validated["cv"]["professional_experience"][0]["title"], custom_title)


if __name__ == "__main__":
    unittest.main()
