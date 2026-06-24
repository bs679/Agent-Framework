---
description: Convert a scanned Aladtec EMS schedule PDF into a structured Excel workbook
argument-hint: <path-to-pdf> [output.xlsx]
allowed-tools: Bash, Read, Write, Edit, Agent, Glob
---

You are extracting a scanned, image-only Aladtec monthly-calendar schedule PDF into a
structured Excel spreadsheet. Tooling lives in `tools/ems-schedule-extract/`.

Input PDF: **$1**   (output name: **$2**, default `EMS_Schedules.xlsx`)

Work through these steps. Do not skip validation.

1. **Setup** — ensure deps exist (install if missing, quietly):
   `pdftoppm`/`tesseract` (apt: `poppler-utils tesseract-ocr`) and python `pillow numpy pandas openpyxl`.
   Pick a work dir, e.g. `WORK=$(mktemp -d)`.

2. **Preprocess** — `python3 tools/ems-schedule-extract/preprocess.py --pdf "$1" --out "$WORK"`.
   This rasterizes, orients, and crops 7 weekday column images per page into `$WORK/cols/`.

3. **Transcribe** — read `tools/ems-schedule-extract/transcription_guide.md` and follow it exactly.
   For EACH page, transcribe its 7 column images (`$WORK/cols/pNN_c0.png` … `_c6.png`) into
   `$WORK/out/pNN.json`. Pages are independent, so **dispatch one Agent per page in parallel**
   (subagent type `claude`), each writing its own JSON and capturing the `top_continuation` fragment.
   The column images are clear; read carefully — the main error source is time/name alignment under
   MEDIC headers (the vehicle's `07:00-07:00` is NOT the first person's time) and dropped crew.

4. **Assemble** — `python3 tools/ems-schedule-extract/assemble.py --work "$WORK" [--base-year YYYY]`.
   It chains dates from the first printed month label, assigns every cell an absolute date, merges
   page-break continuations, and prints validation. **`issues` must be 0 and `missing` empty.**
   If a date is missing, it is almost always a bottom-of-column cell a transcriber skipped — find it
   in the column image and add it to that page's JSON, then re-run.

5. **Excel** — `python3 tools/ems-schedule-extract/to_excel.py --work "$WORK" --out "${2:-EMS_Schedules.xlsx}" --pdf-name "$(basename "$1")"`.
   (Add `--orig-page-offset N` if this PDF was extracted from a larger response doc.)

6. **Validate** — spot-check 4–6 cells across different pages against the column images
   (first/last dates, plus a mid-month cell from a few pages). Confirm crews, vehicles, times,
   Time Off, Trades, and Events match. Report row count, date coverage, validation result, and the
   count of `OCR uncertain` cells.

Deliver the path to the finished `.xlsx`. If anything is ambiguous (e.g. base year, or a page that
fails validation), say so explicitly rather than guessing.
