"""Compile the LaTeX projects with pdflatex and collect the PDFs."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

LATEX_ROOT = Path(__file__).resolve().parent / "LaTeX"
PROJECTS = ("CV", "CV_academic", "cover_letter", "onePDF")
# onePDF embeds the PDFs these projects produce, so it must be compiled last.
ONEPDF = "onePDF"
ONEPDF_STAGING = LATEX_ROOT / ONEPDF / "documents" / "application"
# hyperref/longtable/tocloft need a second run to settle references.
PASSES = 2
LOG_EXCERPT_LINES = 40


def find_pdflatex() -> str:
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError(
            "pdflatex was not found on PATH. Install MiKTeX (or TeX Live) and make "
            "sure its bin directory is on PATH."
        )
    return pdflatex


def compile_project(pdflatex: str, name: str, out_dir: Path) -> bool:
    project_dir = LATEX_ROOT / name
    main_tex = project_dir / "main.tex"
    if not main_tex.is_file():
        print(f"[{name}] SKIP: {main_tex} does not exist.")
        return False

    for run in range(1, PASSES + 1):
        print(f"[{name}] pdflatex pass {run}/{PASSES} ...")
        result = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "-file-line-error",
                "main.tex",
            ],
            cwd=project_dir,
            shell=False,
            capture_output=True,
            text=True,
            errors="replace",
        )
        if result.returncode != 0:
            print(f"[{name}] FAILED with exit code {result.returncode}.")
            excerpt = (result.stdout or "").splitlines()[-LOG_EXCERPT_LINES:]
            for line in excerpt:
                print(f"    {line}")
            print(f"[{name}] full log: {project_dir / 'main.log'}")
            return False

    produced = project_dir / "main.pdf"
    if not produced.is_file():
        print(f"[{name}] FAILED: pdflatex reported success but {produced} is missing.")
        return False

    target = out_dir / f"{name.lower()}.pdf"
    if not (target.exists() and target.samefile(produced)):
        shutil.copy2(produced, target)
    print(f"[{name}] OK -> {target}")
    return True


def stage_onepdf_documents(cv_project: str, results: dict[str, bool]) -> bool:
    """Refresh the core PDFs onePDF embeds; keeps existing files if a source was not built."""
    sources = {
        "cv.pdf": cv_project,
        "cover_letter.pdf": "cover_letter",
    }
    for target_name, project in sources.items():
        if not results.get(project, False):
            print(f"[{ONEPDF}] {project} was not built in this run; keeping existing {target_name}.")
            continue
        source = LATEX_ROOT / project / "main.pdf"
        if not source.is_file():
            print(f"[{ONEPDF}] FAILED: {source} is missing.")
            return False
        shutil.copy2(source, ONEPDF_STAGING / target_name)
        print(f"[{ONEPDF}] staged {project} -> {ONEPDF_STAGING / target_name}")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.cwd(),
        help="Directory the generated PDFs are copied to (default: current directory).",
    )
    parser.add_argument(
        "--projects",
        nargs="+",
        choices=PROJECTS,
        default=list(PROJECTS),
        help="Subset of projects to compile (default: all).",
    )
    parser.add_argument(
        "--onepdf-cv",
        choices=("CV", "CV_academic"),
        default="CV",
        help="Which CV renderer is embedded into onePDF (default: CV).",
    )
    args = parser.parse_args(argv)

    try:
        pdflatex = find_pdflatex()
    except RuntimeError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1

    out_dir = args.output_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    ordered = [name for name in PROJECTS if name in args.projects]
    results: dict[str, bool] = {}
    for name in ordered:
        if name == ONEPDF and not stage_onepdf_documents(args.onepdf_cv, results):
            results[name] = False
            continue
        results[name] = compile_project(pdflatex, name, out_dir)

    print("\nSummary:")
    for name, ok in results.items():
        print(f"  {name:<12} {'OK' if ok else 'FAILED'}")

    return 0 if all(results.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
