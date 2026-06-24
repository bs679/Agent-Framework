# EMS schedule extractor

Converts a **scanned, image-only Aladtec monthly-calendar PDF** (e.g. Madison EMS RFI
responses) into a structured Excel workbook — one row per person per shift entry, with
dates validated against the printed calendar.

This is the reusable version of the one-off Madison EMS extraction. It's wired as a Claude
Code slash command so it can be re-run on each new RFI response.

## Pipeline
| stage | script | does |
|-------|--------|------|
| 1 | `preprocess.py` | rasterize @400 DPI, fix orientation (tesseract OSD), detect the 7 day columns, crop column images |
| 2 | *(Claude, vision)* | transcribe each column image → `out/pNN.json` per `transcription_guide.md` |
| 3 | `assemble.py` | chain dates, merge page-break continuations, validate, write `rows.json` |
| 4 | `to_excel.py` | formatted workbook + `Source & Notes` sheet + `PDF Reference` for uncertain cells |

Stage 2 needs vision (an LLM) — that's why the whole thing runs as a **Claude Code prompt**,
not a pure script. Stages 1/3/4 are deterministic Python.

## Run it (slash command)
From the repo root in Claude Code:
```
/extract-ems-schedule /path/to/NewRFIResponse.pdf  Madison_EMS_Schedules.xlsx
```
The command (`.claude/commands/extract-ems-schedule.md`) preprocesses, fans out one subagent
per page to transcribe, assembles, validates (issues must be 0, no missing dates), and writes
the `.xlsx`.

## Run it headless (for the always-on SB3 box)
Claude Code CLI in print mode:
```bash
claude -p "/extract-ems-schedule '$PDF' '$OUT'" \
       --allowedTools Bash Read Write Edit Agent Glob
```

### Trigger on new files in the RFI Responses folder
Claude Code on the web has **no** OneDrive/SharePoint folder trigger (only cron, GitHub events,
and an API endpoint). On an always-on machine with the OneDrive folder synced locally, watch it
instead. Example with `inotifywait`:
```bash
#!/usr/bin/env bash
WATCH="$HOME/OneDrive/1. Dave's Folder/Madison EMS/RFI Responses"
OUTDIR="$HOME/OneDrive/1. Dave's Folder/Madison EMS"
inotifywait -m -e close_write -e moved_to --format '%f' "$WATCH" | while read -r f; do
  [[ "$f" == *.pdf ]] || continue
  out="$OUTDIR/${f%.pdf}.xlsx"
  claude -p "/extract-ems-schedule '$WATCH/$f' '$out'" \
         --allowedTools Bash Read Write Edit Agent Glob
done
```
**Cron / Task-Scheduler (no inotify):** `watch_rfi.sh` polls the folder and extracts any PDF whose
`.xlsx` is missing or older than the PDF, then exits (a `flock` prevents overlap):
```bash
# every 15 min
*/15 * * * * /path/to/repo/tools/ems-schedule-extract/watch_rfi.sh \
             "/sync/Madison EMS/RFI Responses" "/sync/Madison EMS" >/dev/null 2>&1
```
Run `watch_rfi.sh <watch_dir> <out_dir>` once by hand first to confirm it works; it logs to
`<out_dir>/.extract.log`. (On Windows, point Task Scheduler at the same command via WSL/Git-Bash.)

Because the output lands in the synced folder, it round-trips back to OneDrive automatically — no
Graph write access needed.

## Dependencies
One-time install (auto-detects apt / dnf / yum / apk / brew / opkg):
```bash
bash tools/ems-schedule-extract/setup.sh
```
It installs the system tools (`poppler-utils`, `tesseract-ocr`), the Python libs
(`pillow numpy pandas openpyxl`), and verifies the `claude` CLI is present (needed for the
vision/transcription stage — install separately: https://docs.claude.com/en/docs/claude-code).

## Assumptions / limits
- Built for the Aladtec "monthly calendar, Sun–Sat columns, vehicle + crew + Time Off/Trades/Events"
  layout. A very different print layout would need the prompt/guide adjusted.
- `assemble.py` derives the start date from the first printed month label; pass `--base-year` (or
  `--start-date`) if the year is ambiguous.
- Re-validate each run: the assembler prints `issues` and `missing` — both must be clean.
