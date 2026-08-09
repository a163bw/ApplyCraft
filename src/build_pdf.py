from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path

from .generator import (
    PHOTO_NAMES,
    SIGNATURE_NAMES,
    ValidationError,
    discover_optional_asset,
    generate_cover_letter_body,
    generate_cover_letter_preamble,
    generate_cv_latex,
    load_json,
    validate_and_resolve_inputs,
)


def _cv_layout_file(root: Path) -> Path:
    preferred = root / "latex" / "cv" / "main.tex"
    if preferred.is_file():
        return preferred
    fallback = root / "tmp_overleaf" / "cv" / "main.tex"
    if fallback.is_file():
        return fallback
    raise FileNotFoundError("Could not find CV layout file (latex/cv/main.tex or tmp_overleaf/cv/main.tex)")


def _cover_letter_layout_file(root: Path) -> Path:
    preferred = root / "latex" / "cover_letter" / "main.tex"
    if preferred.is_file():
        return preferred
    fallback = root / "tmp_overleaf" / "6a68ff588826288f9a387054" / "main.tex"
    if fallback.is_file():
        return fallback
    raise FileNotFoundError("Could not find cover-letter layout file (latex/cover_letter/main.tex or tmp_overleaf/.../main.tex)")


def _compile_pdf(layout_file: Path, output_dir: Path, target_name: str) -> None:
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError("pdflatex not found in PATH")

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        pdflatex,
        "-interaction=nonstopmode",
        "-halt-on-error",
        "-output-directory",
        str(output_dir),
        str(layout_file),
    ]
    subprocess.run(command, check=True, cwd=layout_file.parent)

    produced_pdf = output_dir / f"{layout_file.stem}.pdf"
    target_pdf = output_dir / target_name
    if not produced_pdf.is_file():
        raise RuntimeError(f"Expected compiled PDF at {produced_pdf}")
    produced_pdf.replace(target_pdf)


def build(
    root: Path,
    personal_data_path: Path,
    application_path: Path,
    generated_tex_path: Path,
    output_dir: Path,
    skip_pdf: bool,
    photo_override: str | None,
    signature_override: str | None,
    build_cover_letter: bool,
    generated_cover_letter_preamble_path: Path,
    generated_cover_letter_body_path: Path,
) -> None:
    personal_data = load_json(personal_data_path)
    application = load_json(application_path)
    resolved = validate_and_resolve_inputs(personal_data, application)

    photo_path = discover_optional_asset(root, photo_override, application.get("photo"), PHOTO_NAMES)
    signature_path = discover_optional_asset(root, signature_override, application.get("signature"), SIGNATURE_NAMES)

    latex_text = generate_cv_latex(resolved, photo_path=photo_path, signature_path=signature_path)
    generated_tex_path.parent.mkdir(parents=True, exist_ok=True)
    generated_tex_path.write_text(latex_text, encoding="utf-8")

    if build_cover_letter:
        if resolved.cover_letter is None:
            raise ValidationError("application.cover_letter is required when --cover-letter is used")
        generated_cover_letter_preamble_path.parent.mkdir(parents=True, exist_ok=True)
        generated_cover_letter_preamble_path.write_text(generate_cover_letter_preamble(resolved), encoding="utf-8")
        generated_cover_letter_body_path.write_text(generate_cover_letter_body(resolved, signature_path=signature_path), encoding="utf-8")

    if skip_pdf:
        return

    _compile_pdf(_cv_layout_file(root), output_dir, "cv.pdf")
    if build_cover_letter:
        _compile_pdf(_cover_letter_layout_file(root), output_dir, "cover_letter.pdf")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Build deterministic CV LaTeX and optional PDF")
    parser.add_argument("--personal-data", default="data/personal_data.json", help="Path to personal_data.json")
    parser.add_argument("--application", default="data/application.json", help="Path to application.json")
    parser.add_argument("--generated-tex", default="generated/generated_cv_content.tex", help="Output .tex path")
    parser.add_argument("--output-dir", default="output", help="Directory for PDF build outputs")
    parser.add_argument("--skip-pdf", action="store_true", help="Only generate LaTeX; do not compile PDF")
    parser.add_argument("--photo", default=None, help="Optional photo override path")
    parser.add_argument("--signature", default=None, help="Optional signature override path")
    parser.add_argument("--cover-letter", action="store_true", help="Also generate and optionally compile the cover letter")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    root = Path(__file__).resolve().parent.parent

    try:
        build(
            root=root,
            personal_data_path=(root / args.personal_data).resolve(),
            application_path=(root / args.application).resolve(),
            generated_tex_path=(root / args.generated_tex).resolve(),
            output_dir=(root / args.output_dir).resolve(),
            skip_pdf=bool(args.skip_pdf),
            photo_override=args.photo,
            signature_override=args.signature,
            build_cover_letter=bool(args.cover_letter),
            generated_cover_letter_preamble_path=(root / "generated" / "generated_cover_letter_preamble.tex").resolve(),
            generated_cover_letter_body_path=(root / "generated" / "generated_cover_letter_body.tex").resolve(),
        )
    except (ValidationError, FileNotFoundError, RuntimeError, subprocess.CalledProcessError) as exc:
        print(f"Error: {exc}")
        return 1

    print("Build completed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
