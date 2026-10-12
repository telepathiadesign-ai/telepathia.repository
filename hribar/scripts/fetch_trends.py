#!/usr/bin/env python3
"""Google Trends, Romania, weekly interest for mushroom search terms -> eval/data/trends_ro.json. Tests whether "people
are searching for ceps this week" adds a timing signal (D10). Uses pytrends (unofficial; Google rate-limits it).
Daily series are built from overlapping 8-month windows (daily resolution) rescaled on their overlaps."""
import datetime as dt, json, os, sys, time
import pandas as pd
from pytrends.request import TrendReq

HERE = os.path.dirname(os.path.abspath(__file__)); OUT = os.path.join(HERE, '..', 'eval', 'data', 'trends_ro.json')
TERMS = ['hribi', 'ciuperci', 'gălbiori', 'ghebe', 'bureți']
log = lambda *a: print(*a, file=sys.stderr, flush=True)
py = TrendReq(hl='ro-RO', tz=-180, timeout=(10, 30), retries=3, backoff_factor=2)
out = json.load(open(OUT)) if os.path.exists(OUT) else {}
start, end = dt.date(2023, 6, 1), dt.date.today()
for term in TERMS:
    parts = []; s = start
    while s < end:
        e = min(end, s + dt.timedelta(days=240))
        for k in range(5):
            try:
                py.build_payload([term], geo='RO', timeframe=f'{s} {e}'); df = py.interest_over_time(); break
            except Exception as ex:
                log('retry', term, s, str(ex)[:80]); time.sleep(60 * (k + 1)); df = None
        if df is None or df.empty:
            log('no data', term, s); s = e - dt.timedelta(days=60); continue
        parts.append(df[term].astype(float)); s = e - dt.timedelta(days=60); time.sleep(8)
    if not parts:
        continue
    ser = parts[0]
    for p in parts[1:]:   # rescale each window on its overlap with what we have
        ov = ser.index.intersection(p.index)
        f = (ser[ov].mean() / p[ov].mean()) if len(ov) and p[ov].mean() > 0 else 1.0
        ser = pd.concat([ser, p[~p.index.isin(ser.index)] * f])
    ser = 100 * ser / ser.max()
    out[term] = {str(d.date()): round(float(v), 2) for d, v in ser.items()}
    log('ok', term, len(out[term]), 'days')
json.dump(out, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
