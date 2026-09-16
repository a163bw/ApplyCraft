"""Batch-compile every application source folder found under the configured parents.

Each folder named SRC_FOLDER_NAME holds the `LaTeX/src` content of one application.
Its files replace `LaTeX/src`, the matching projects are compiled, and the resulting
PDF is written to the folder's parent directory (overwriting an existing file).
"""

from __future__ import annotations

import re
import shutil
import sys
import unicodedata
from pathlib import Path

from build_pdfs import (
    LATEX_ROOT,
    clean_aux,
    compile_project,
    find_pdflatex,
    stage_onepdf_documents,
)

# --------------------------------------------------------------------------
# Configuration - edit these two values.
# --------------------------------------------------------------------------

# Directories that are searched recursively for SRC_FOLDER_NAME.
PARENT_FOLDERS: list[Path] = [
    # Path(r"H:\My Drive\Munka\00_open"),
    Path(r"H:\My Drive\Munka\99_test\x_musterman"),
]

# Exact (case-sensitive) name of the folders holding the src content.
SRC_FOLDER_NAME = "LaTeX_src"

# --------------------------------------------------------------------------

SRC_DIR = LATEX_ROOT / "src"
PERSONAL_DATA = LATEX_ROOT / "src_personal" / "personal_data.tex"
ONEPDF_CV = "CV_academic"
# The onePDF table of contents shifts its own page numbers, so it needs a third pass.
ONEPDF_PASSES = 3
PDF_PREFIX = {
    "CV": "cv",
    "CV_academic": "cv",
    "cover_letter": "cover_letter",
    "onePDF": "application",
}


def pdf_output_name(project_name: str, stem: str) -> str:
    """Return the final PDF file name for a built project and applicant stem."""
    prefix = PDF_PREFIX.get(project_name, project_name)
    return f"{prefix}_{stem}.pdf"


def copy_pdf_to_output(source_pdf: Path, output_dir: Path, project_name: str, stem: str) -> Path:
    """Copy a generated PDF into the final output directory using the applicant-stem naming."""
    target = output_dir / pdf_output_name(project_name, stem)
    if source_pdf.exists():
        shutil.copy2(source_pdf, target)
    return target


def sanitize_filename_stem(first_name: str, last_name: str) -> str:
    """Return an ASCII-safe, file-system-friendly stem for the final PDF name."""
    raw = f"{first_name.strip()}_{last_name.strip().upper()}"
    normalized = unicodedata.normalize("NFKD", raw)
    ascii_only = "".join(ch for ch in normalized if not unicodedata.combining(ch) and ch.isascii())
    result = re.sub(r"[^A-Za-z0-9._-]+", "_", ascii_only)
    return result.strip("_")


def read_applicant_stem() -> str:
    text = PERSONAL_DATA.read_text(encoding="utf-8")
    parts = []
    for command in ("ApplicantFirstName", "ApplicantLastName"):
        match = re.search(r"\\def\\" + command + r"\{([^}]*)\}", text)
        if match is None or not match.group(1).strip():
            raise RuntimeError(f"\\{command} is missing or empty in {PERSONAL_DATA}.")
        parts.append(match.group(1).strip())

    return sanitize_filename_stem(parts[0], parts[1])


def find_src_folders() -> list[Path]:
    folders: list[Path] = []
    seen: set[Path] = set()
    for root in PARENT_FOLDERS:
        for path in sorted(root.rglob("*")):
            if not path.is_dir() or path.name != SRC_FOLDER_NAME:
                continue
            resolved = path.resolve()
            if resolved == SRC_DIR.resolve() or resolved in seen:
                continue
            seen.add(resolved)
            folders.append(path)
    return folders


def sync_src(folder: Path) -> None:
    for existing in sorted(SRC_DIR.iterdir()):
        if existing.is_file():
            existing.unlink()
    for source in sorted(folder.iterdir()):
        if source.is_file():
            shutil.copy2(source, SRC_DIR / source.name)


def process_folder(pdflatex: str, folder: Path, stem: str) -> bool:
    print(f"\n=== {folder} ===")
    if not (folder / "content_CV.tex").is_file():
        print("SKIP: content_CV.tex is missing.")
        return True

    sync_src(folder)
    parent = folder.parent
    onepdf_mode = (folder / "content_onePDF.tex").is_file()
    if onepdf_mode:
        projects = [ONEPDF_CV, "cover_letter", "onePDF"]
    else:
        projects = ["CV"]
        if (folder / "content_cover_letter.tex").is_file():
            projects.append("cover_letter")

    results: dict[str, bool] = {}
    for name in projects:
        project_dir = LATEX_ROOT / name
        clean_aux(project_dir)
        if name == "onePDF":
            if not stage_onepdf_documents(ONEPDF_CV, results):
                return False
            ok = compile_project(pdflatex, name, parent, pdf_output_name(name, stem), ONEPDF_PASSES)
        elif onepdf_mode:
            # Keep academic outputs available at the end location using the standard applicant stem naming.
            ok = compile_project(pdflatex, name, parent, pdf_output_name(name, stem))
        else:
            ok = compile_project(pdflatex, name, parent, pdf_output_name(name, stem))
        results[name] = ok
        if not ok:
            return False
    return True


def validate_config() -> str | None:
    if not SRC_FOLDER_NAME.strip():
        return "SRC_FOLDER_NAME is empty."
    if not PARENT_FOLDERS:
        return "PARENT_FOLDERS is empty."
    for root in PARENT_FOLDERS:
        if not root.is_dir():
            return f"PARENT_FOLDERS entry is not an existing directory: {root}"
    return None


def main() -> int:
    error = validate_config()
    if error is not None:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2

    try:
        pdflatex = find_pdflatex()
        stem = read_applicant_stem()
    except (RuntimeError, OSError) as config_error:
        print(f"ERROR: {config_error}", file=sys.stderr)
        return 1

    folders = find_src_folders()
    if not folders:
        print(f"No folder named {SRC_FOLDER_NAME!r} was found.")
        return 1

    results = {folder: process_folder(pdflatex, folder, stem) for folder in folders}

    print("\nSummary:")
    for folder, ok in results.items():
        parent = Path(folder).resolve().parent
        link = f"\033]8;;{parent.as_uri()}\033\\{parent}\033]8;;\033\\"
        print(f"  {'OK    ' if ok else 'FAILED'} {link}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
