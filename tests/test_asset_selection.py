import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from cv_generator.cli import GeneratedPaths, generate_documents


class TestAssetSelection(unittest.TestCase):
    def _write_json(self, path: Path, data: dict):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

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

    def _application(self):
        return {
            "language": "de",
            "cv": {
                "professional_experience": [],
                "education": [],
                "additional_sections": [],
                "skills": {
                    "sections": [
                        {
                            "title": "Tools",
                            "type": "general",
                            "items": [{"name": "Python", "level": 4}],
                        }
                    ]
                },
                "signing_date": "2026-08-08",
            },
            "cover_letter": {
                "company": "Beispiel GmbH",
                "company_city": "Muenchen",
                "application_date": "2026-08-01",
                "body_paragraphs": ["Paragraph one"],
            },
        }

    def _run_with_capture(self, root: Path, personal: dict, application: dict, photo=None, signature=None):
        personal_path = root / "personal_data.json"
        application_path = root / "application.json"
        output_dir = root / "output"
        self._write_json(personal_path, personal)
        self._write_json(application_path, application)

        captured = {}

        def fake_validate(personal_data, application_data, base_dir):
            captured["application_data"] = application_data
            return {
                "language": "de",
                "language_babel": "ngerman",
                "personal": personal_data,
                "cv": {},
                "cover_letter": {},
                "photo": None,
                "signature": None,
            }

        with patch("cv_generator.cli._validate_inputs", side_effect=fake_validate), patch(
            "cv_generator.cli._stage_and_generate",
            return_value=GeneratedPaths(cv_pdf=output_dir / "cv.pdf", cover_letter_pdf=output_dir / "cover_letter.pdf"),
        ):
            generate_documents(
                personal_data_path=personal_path,
                application_path=application_path,
                output_dir=output_dir,
                photo=photo,
                signature=signature,
            )

        return captured["application_data"]

    def test_defaults_pick_data_dir_jpeg(self):
        personal = self._personal()
        application = self._application()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "profile_photo.jpeg").write_bytes(b"fake")
            (root / "signature.jpeg").write_bytes(b"fake")

            app_data = self._run_with_capture(root, personal, application)

            self.assertEqual(app_data["photo"], str((root / "profile_photo.jpeg").resolve()))
            self.assertEqual(app_data["signature"], str((root / "signature.jpeg").resolve()))

    def test_defaults_support_non_jpeg_formats(self):
        personal = self._personal()
        application = self._application()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            (root / "profile_photo.png").write_bytes(b"fake")
            (root / "signature.webp").write_bytes(b"fake")

            app_data = self._run_with_capture(root, personal, application)

            self.assertEqual(app_data["photo"], str((root / "profile_photo.png").resolve()))
            self.assertEqual(app_data["signature"], str((root / "signature.webp").resolve()))

    def test_personal_data_custom_paths_override_defaults(self):
        personal = self._personal()
        personal["photo"] = "my_photo.bmp"
        personal["signature"] = "my_signature.gif"
        application = self._application()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_data = self._run_with_capture(root, personal, application)

            self.assertEqual(app_data["photo"], "my_photo.bmp")
            self.assertEqual(app_data["signature"], "my_signature.gif")

    def test_cli_overrides_personal_data(self):
        personal = self._personal()
        personal["photo"] = "my_photo.bmp"
        personal["signature"] = "my_signature.gif"
        application = self._application()

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            app_data = self._run_with_capture(
                root,
                personal,
                application,
                photo=Path("override_photo.jpg"),
                signature=Path("override_signature.png"),
            )

            self.assertEqual(app_data["photo"], "override_photo.jpg")
            self.assertEqual(app_data["signature"], "override_signature.png")


if __name__ == "__main__":
    unittest.main()
