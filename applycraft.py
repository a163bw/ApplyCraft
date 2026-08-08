import sys

from cv_generator.cli import main


if __name__ == "__main__":
    if len(sys.argv) == 1:
        default_args = [
            "generate",
            "--personal-data",
            "data/personal_data.json",
            "--application",
            "data/application.json",
            "--output-dir",
            "output",
        ]
        raise SystemExit(main(default_args))
    raise SystemExit(main())
