# Transcription guide — one Aladtec schedule page

Stage 2 of the pipeline. After `preprocess.py`, each page is 7 column images
(`pNN_c0.png` … `pNN_c6.png`, where `c0`=Sunday … `c6`=Saturday). Read each
image and emit structured JSON. Images are high-resolution and clearly legible.

## What a column image shows
That weekday's cells for several weeks, stacked top-to-bottom. A small `Sun`/`Mon`/…
label sits at the very top — ignore it. Each **day cell** starts with a **bold day
number** (e.g. `29`, `6`, `15`); on the 1st of a month the number includes a month
abbreviation (`Jul 1`) — record it.

**Top continuation fragment:** pages split a week across the page break, so above the
first bold day number there is often a fragment of entries with NO day number. It is
the continuation of the previous page's last week — capture it separately in
`top_continuation` (one object per column 0–6; empty list if none). Never merge it
into the first numbered cell.

**Bottom cell** is often cut by the image edge — transcribe what's visible, invent nothing.

## Sections inside a cell (bold underlined headers)
- `MEDIC 1`..`MEDIC 4` — first sub-line is the VEHICLE (`Ambulance 803`, `Medic 802`, …)
  with its own time (usually `07:00-07:00`). **That time belongs to the vehicle, not the
  first person.** Each following line is `Name` + a time on the SAME row. Do not shift the
  time column; do not drop anyone; read vehicle last-digit (2/3/4) carefully.
- `Trades` — `X For Y` + time.
- `Time Off` — `Name` + time, with a subtype line (`Personal Time`/`Vacation Time`/`Booked Shift`).
- `Events Crew` — location + vehicle + names/roles + times.

Times: `07:00-19:00` day, `19:00-07:00` night (spans midnight — keep as one), `07:00-07:00` 24h.
A small `*`/arrow by a time → `flag:"*"`.

## OCR-correction roster (prefer these spellings)
Beach, Kiana · Buda, James · Ciccone, Wesley · Curley, Michael · Gulick, Ashley · Manzi, Justin ·
Merchant, Justin · Montanaro, Michael · Nieliwocki, Michael · Rahmlow, Christopher (Chris) ·
Steines, Christopher (Chris) · Tucker, Ethan · Williams, John  (full-time bargaining unit)
Part-time/per-diem also appear (Rondina, DeAngelis, Holdridge, Nolan, DeFrance, Hughes, Croteau,
Conners, Vargoshe, Dale, White Carpenter, Donovan, Bergers, D'Agostino, Puciato, Jensen, Licata,
Noyes, Ducat, Gonsalves, Anderson, Reed, Pierson, Allen, Ebersole, Balsamo, Hooks, …). If a name
is genuinely unreadable, give your best guess and set `"uncertain": true`.

## Output  (write `out/pNN.json`)
```json
{
  "page": NN,
  "top_continuation": [ {"col_index":0,"entries":[ ... ]}, ... {"col_index":6,"entries":[]} ],
  "cells": [
    {"col_index":0,"day_number":29,"month_abbrev":null,"entries":[
       {"section":"MEDIC 1","vehicle":"Ambulance 804","employee":"Rebecca DeFrance",
        "start":"07:00","end":"17:00","entry_type":"Regular","notes":"","flag":"","uncertain":false}
    ]}
  ]
}
```
- One entry **per person** (never emit the vehicle line as a person; put it in `vehicle`).
- `entry_type` ∈ Regular, Trade, Time Off, Booked Shift, Events Crew, Vacation, Personal Time.
  Map Time-Off subtype: Vacation Time→Vacation, Personal Time→Personal Time, Booked Shift→Booked Shift, else Time Off.
- `notes`: Trades→`For <name>`; Time Off→the subtype text; Events→location; else "".
- Include every cell with a visible day number, all 7 columns.

> Accuracy note: spot-check a few cells against the column images after assembly. In testing,
> the per-cell error source was time/name misalignment under MEDIC headers — re-read those carefully.
