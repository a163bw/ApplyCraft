# ApplyCraft

Deterministic CV and cover-letter generation from JSON input and static LaTeX layouts.

## Run

Generate the CV LaTeX only:

```powershell
.venv\bin\python.exe applycraft.py --skip-pdf
```

Run with defaults (uses `data/personal_data.json` and `data/application.json`):

```powershell
.venv\bin\python.exe applycraft.py
```

Run by absolute script path (defaults still resolve from the project root):

```powershell
& D:/Documents/GitRepos/ApplyCraft/.venv/bin/python.exe D:/Documents/GitRepos/ApplyCraft/applycraft.py
```

Generate the CV PDF:

```powershell
.venv\bin\python.exe applycraft.py
```

Run with user-provided JSON and image paths:

```powershell
.venv\bin\python.exe applycraft.py `
	--personal-data data/personal_data_Horvath.json `
	--application data/application_.json `
	--photo data/profile_photo.jpg `
	--signature data/signature.png
```

The same command with absolute input paths:

```powershell
.venv\bin\python.exe applycraft.py `
	--personal-data "D:/input/personal_data.json" `
	--application "D:/input/application.json" `
	--photo "D:/input/profile_photo.jpg" `
	--signature "D:/input/signature.png"
```

Generate CV plus cover-letter LaTeX:

```powershell
.venv\bin\python.exe applycraft.py --skip-pdf --cover-letter
```

Generate CV plus cover-letter PDFs:

```powershell
.venv\bin\python.exe applycraft.py --cover-letter
```

Generated outputs:

- `generated/generated_cv_content.tex`
- `generated/generated_cover_letter_preamble.tex`
- `generated/generated_cover_letter_body.tex`
- `output/cv.pdf`
- `output/cover_letter.pdf`

## Tests

```powershell
.venv\bin\python.exe -m pytest -q
```
