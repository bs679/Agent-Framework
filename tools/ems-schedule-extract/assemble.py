#!/usr/bin/env python3
"""
assemble.py — Stage 3. Turn per-page transcription JSON into a flat, dated,
validated row list (rows.json).

The pages tile a continuous Sunday-start calendar. Each page shows N week-rows;
the last week of a page is split, its lower half appearing as a `top_continuation`
fragment at the top of the NEXT page. We anchor page 1 from a printed month label
(e.g. "Jun 1"), chain grid_starts by week-count, assign every cell an absolute
date, and cross-check against every printed day number / month label.

Usage:
    python3 assemble.py --work WORKDIR [--base-year 2025] [--start-date YYYY-MM-DD]

--start-date, if given, is the Sunday of page-1's first numbered week (overrides
anchor detection). Otherwise the start is derived from page 1's month label +
--base-year (default: infer from the first label, assuming it is the earliest).
"""
import argparse, glob, json, os, datetime
from collections import defaultdict

MONTHS = {m: i for i, m in enumerate(
    ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'], 1)}
DOW = ['Sun','Mon','Tue','Wed','Thu','Fri','Sat']


def load(work):
    pages = {}
    for f in sorted(glob.glob(os.path.join(work, 'out', 'p*.json'))):
        p = int(os.path.basename(f)[1:3])
        pages[p] = json.load(open(f))
    return pages


def by_col(cells):
    d = defaultdict(list)
    for c in cells:
        d[c['col_index']].append(c)
    return d


def weeks(page):
    d = by_col(page.get('cells', []))
    return max((len(v) for v in d.values()), default=0)


def cont(page):
    d = {c: [] for c in range(7)}
    for g in page.get('top_continuation', []):
        d[g['col_index']] = g.get('entries', [])
    return d


def first_anchor(page):
    """(month, day, row, col) of the first cell carrying a month label."""
    for col, cells in sorted(by_col(page.get('cells', [])).items()):
        for row, c in enumerate(cells):
            ma, dn = c.get('month_abbrev'), c.get('day_number')
            if ma and dn and ma[:3].title() in MONTHS:
                return MONTHS[ma[:3].title()], dn, row, col
    return None


def map_entry(e, date):
    sec = (e.get('section') or '').strip()
    veh = e.get('vehicle')
    et = e.get('entry_type') or ''
    notes = (e.get('notes') or '').strip()
    extra = []
    is_medic = sec.upper().startswith('MEDIC') and any(ch.isdigit() for ch in sec)
    if is_medic:
        unit = sec
        if veh: extra.append(f'Unit: {veh}')
    elif sec.lower().startswith('events'):
        unit = 'Events Crew'
        if veh: extra.append(f'Unit: {veh}')
    elif sec.lower() in ('trades', 'time off', 'timeoff'):
        unit = ''
    elif veh or sec:
        unit = sec or veh
        if veh and sec and veh != sec: extra.append(f'Unit: {veh}')
    else:
        unit = ''
    if notes: extra.append(notes)
    if e.get('flag'): extra.append('marked *')
    if e.get('uncertain'): extra.append('OCR uncertain')
    return {'Date': date, 'Day': date.strftime('%a'),
            'Unit': unit, 'Employee': (e.get('employee') or '').strip(),
            'Start Time': e.get('start') or '', 'End Time': e.get('end') or '',
            'Entry Type': et, 'Notes': ' ; '.join(x for x in extra if x)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--work', required=True)
    ap.add_argument('--base-year', type=int, default=None)
    ap.add_argument('--start-date', default=None)
    a = ap.parse_args()

    pages = load(a.work)
    if not pages:
        raise SystemExit('no out/p*.json found — run transcription first')

    if a.start_date:
        G0 = datetime.date.fromisoformat(a.start_date)
    else:
        an = first_anchor(pages[min(pages)])
        if not an:
            raise SystemExit('page 1 has no month label; pass --start-date')
        mon, day, row, col = an
        year = a.base_year or datetime.date.today().year
        G0 = datetime.date(year, mon, day) - datetime.timedelta(days=7 * row + col)
    if G0.strftime('%w') != '0':
        print(f'WARNING: start {G0} is not a Sunday')

    gs = {}; cur = G0
    for p in sorted(pages):
        gs[p] = cur
        cur = cur + datetime.timedelta(days=7 * weeks(pages[p]))

    rows, issues = [], []
    for p in sorted(pages):
        g, nb, cb = gs[p], by_col(pages[p].get('cells', [])), cont(pages[p])
        for c in range(7):
            for k, cell in enumerate(nb[c]):
                d = g + datetime.timedelta(days=7 * k + c)
                dn, ma = cell.get('day_number'), cell.get('month_abbrev')
                if dn and not ma and d.day != dn:
                    issues.append(f'p{p} c{c} k{k}: computed {d} (day {d.day}) != reported {dn}')
                if ma and MONTHS.get(ma[:3].title()) not in (None, d.month):
                    issues.append(f'p{p} c{c} k{k}: label {ma} != month {d.month} ({d})')
                for e in cell.get('entries', []):
                    rows.append({**map_entry(e, d), '_p': p, '_src': 'cell'})
        for c in range(7):
            for e in cb[c]:
                d = g + datetime.timedelta(days=-7 + c)
                rows.append({**map_entry(e, d), '_p': p, '_src': 'cont'})

    rows.sort(key=lambda r: (r['Date'], r['Unit'], r['Employee']))
    dates = sorted(set(r['Date'] for r in rows))
    missing = []
    if dates:
        d = dates[0]
        while d <= dates[-1]:
            if d not in set(dates): missing.append(d.isoformat())
            d += datetime.timedelta(days=1)
    print(f'pages={len(pages)}  rows={len(rows)}  '
          f'dates={dates[0]}..{dates[-1]} ({len(dates)})  issues={len(issues)}  missing={missing}')
    for i in issues[:50]:
        print('  -', i)
    json.dump([{**r, 'Date': r['Date'].isoformat()} for r in rows],
              open(os.path.join(a.work, 'rows.json'), 'w'), indent=0, default=str)


if __name__ == '__main__':
    main()
