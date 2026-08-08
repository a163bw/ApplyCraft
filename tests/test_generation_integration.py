import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

import cv_generator.cli as cli


class TestGenerationIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Other test modules monkeypatch PIL; force no-image verification path here
        # so integration runs do not depend on import ordering.
        cli.Image = None

        cls.repo_root = Path(__file__).resolve().parents[1]
        cls.data_dir = cls.repo_root / "data"
        cls.templates_dir = cls.repo_root / "tmp_overleaf"
        cls._tmp_roots: list[Path] = []

        cls.reference_cv_pdf = cls.templates_dir / "6a61d3cd329475a057f02f74" / "main.pdf"
        cls.reference_cover_pdf = cls.templates_dir / "6a68ff588826288f9a387054" / "cover_letter_DAA_Tabstopp_blaue_Linien.pdf"

        cls.photo_path = cls.templates_dir / "6a61d3cd329475a057f02f74" / "profile_photo.jpg"
        cls.signature_path = cls.templates_dir / "6a61d3cd329475a057f02f74" / "signature.jpeg"

    def _load_json(self, path: Path):
        return json.loads(path.read_text(encoding="utf-8"))

    def _write_json(self, path: Path, data: dict):
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    def _build_english_application(self):
        app = self._load_json(self.data_dir / "application.json")
        app["language"] = "en"
        app["cv"]["additional_sections"][0]["title"] = "Further Training"
        app["cv"]["additional_sections"][1]["title"] = "Projects"
        app["cv"]["skills"]["sections"][0]["title"] = "Languages"
        app["cv"]["skills"]["sections"][1]["title"] = "Technical Skills"
        app["cover_letter"]["contact_person"] = "Alex Smith"
        app["cover_letter"]["job_title"] = "Development Engineer"
        app["cover_letter"]["body_paragraphs"] = [
            "My profile aligns with your development role and practical validation focus.",
            "I have several years of engineering experience in product verification and analysis.",
            "I built deterministic evaluation workflows and documented reproducible test procedures.",
            "I would like to contribute these skills to your R&D team.",
        ]
        return app

    def _run_generation(self, personal_data: dict, application_data: dict, photo: Path | None, signature: Path | None):
        root = Path(tempfile.mkdtemp())
        self._tmp_roots.append(root)
        personal_path = root / "personal_data.json"
        application_path = root / "application.json"
        output_dir = root / "output"

        self._write_json(personal_path, personal_data)
        self._write_json(application_path, application_data)

        result = cli.generate_documents(
            personal_data_path=personal_path,
            application_path=application_path,
            output_dir=output_dir,
            photo=photo,
            signature=signature,
        )

        snapshot = {
            "cv_pdf": result.cv_pdf,
            "cover_pdf": result.cover_letter_pdf,
            "cv_content": (output_dir / "_build" / "cv" / "cv_content.tex").read_text(encoding="utf-8"),
            "cv_main": (output_dir / "_build" / "cv" / "main.tex").read_text(encoding="utf-8"),
            "cover_content": (output_dir / "_build" / "cover_letter" / "content_cover_letter.tex").read_text(encoding="utf-8"),
            "cover_personalized": (output_dir / "_build" / "cover_letter" / "personalised.tex").read_text(encoding="utf-8"),
            "cover_main": (output_dir / "_build" / "cover_letter" / "main.tex").read_text(encoding="utf-8"),
            "cv_build_pdf": output_dir / "_build" / "cv" / "main.pdf",
            "cover_build_pdf": output_dir / "_build" / "cover_letter" / "main.pdf",
        }
        return snapshot

    @classmethod
    def tearDownClass(cls):
        for root in cls._tmp_roots:
            shutil.rmtree(root, ignore_errors=True)

    def _pdfinfo(self, path: Path) -> dict[str, str]:
        run = subprocess.run(["pdfinfo", str(path)], capture_output=True, text=True, check=True)
        info: dict[str, str] = {}
        for line in run.stdout.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            info[key.strip()] = value.strip()
        return info

    def test_german_generation_compiles_without_optional_assets(self):
        personal = self._load_json(self.data_dir / "personal_data.json")
        application = self._load_json(self.data_dir / "application.json")

        generated = self._run_generation(personal, application, photo=None, signature=None)

        self.assertTrue(generated["cv_pdf"].exists())
        self.assertTrue(generated["cover_pdf"].exists())
        self.assertGreater(generated["cv_pdf"].stat().st_size, 0)
        self.assertGreater(generated["cover_pdf"].stat().st_size, 0)
        self.assertTrue(generated["cv_build_pdf"].exists())
        self.assertTrue(generated["cover_build_pdf"].exists())

        self.assertIn("\\newcommand{\\Language}{ngerman}", generated["cv_content"])
        self.assertIn("\\newcommand{\\CVSigningDate}{8. August 2026}", generated["cv_content"])
        self.assertIn("\\newcommand{\\ApplicationDate}{8. August 2026}", generated["cover_content"])

    def test_english_generation_compiles_and_uses_english_formatting(self):
        personal = self._load_json(self.data_dir / "personal_data.json")
        application = self._build_english_application()

        generated = self._run_generation(personal, application, photo=None, signature=None)

        self.assertIn("\\newcommand{\\Language}{english}", generated["cv_content"])
        self.assertIn("\\newcommand{\\CVSigningDate}{August 8, 2026}", generated["cv_content"])
        self.assertIn("\\newcommand{\\ApplicationDate}{August 8, 2026}", generated["cover_content"])
        self.assertIn("\\newcommand{\\CoverLetterSalutation}{Dear Alex Smith,}", generated["cover_content"])

    def test_optional_photo_and_signature_compile(self):
        personal = self._load_json(self.data_dir / "personal_data.json")
        application = self._load_json(self.data_dir / "application.json")

        generated = self._run_generation(
            personal,
            application,
            photo=self.photo_path.resolve(),
            signature=self.signature_path.resolve(),
        )

        self.assertIn("\\newcommand{\\CVPhotoFile}{profile_photo.jpg}", generated["cv_content"])
        self.assertIn("\\newcommand{\\CVSignatureFile}{signature.jpeg}", generated["cv_content"])
        self.assertIn("\\newcommand{\\SignatureFile}{signature.jpeg}", generated["cover_content"])

    def test_identical_inputs_produce_identical_logical_content(self):
        personal = self._load_json(self.data_dir / "personal_data.json")
        application = self._load_json(self.data_dir / "application.json")

        first = self._run_generation(personal, application, photo=None, signature=None)
        second = self._run_generation(copy.deepcopy(personal), copy.deepcopy(application), photo=None, signature=None)

        self.assertEqual(first["cv_content"], second["cv_content"])
        self.assertEqual(first["cv_main"], second["cv_main"])
        self.assertEqual(first["cover_content"], second["cover_content"])
        self.assertEqual(first["cover_personalized"], second["cover_personalized"])
        self.assertEqual(first["cover_main"], second["cover_main"])

    def test_generated_pdfs_match_reference_layout_geometry(self):
        personal = self._load_json(self.data_dir / "personal_data.json")
        application = self._load_json(self.data_dir / "application.json")

        generated = self._run_generation(
            personal,
            application,
            photo=self.photo_path.resolve(),
            signature=self.signature_path.resolve(),
        )

        generated_cv_info = self._pdfinfo(generated["cv_pdf"])
        reference_cv_info = self._pdfinfo(self.reference_cv_pdf)
        self.assertEqual(generated_cv_info.get("Pages"), reference_cv_info.get("Pages"))
        self.assertEqual(generated_cv_info.get("Page size"), reference_cv_info.get("Page size"))

        generated_cover_info = self._pdfinfo(generated["cover_pdf"])
        reference_cover_info = self._pdfinfo(self.reference_cover_pdf)
        self.assertEqual(generated_cover_info.get("Pages"), reference_cover_info.get("Pages"))
        self.assertEqual(generated_cover_info.get("Page size"), reference_cover_info.get("Page size"))


if __name__ == "__main__":
    unittest.main()
