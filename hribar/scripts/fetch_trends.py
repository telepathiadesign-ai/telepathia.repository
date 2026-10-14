#!/usr/bin/env python3
"""Google Trends, Romania, weekly interest for mushroom search terms -> eval/data/trends_ro.json. Tests whether "people
are searching for ceps this week" adds a timing signal (D10). Uses pytrends (unofficial; Google rate-limits it).
Weekly series over the last 5 years, one request per term."""
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
    # one request per term: the last 5 years at weekly resolution (Google throttles the many short daily windows)
    df = None
    for k in range(6):
        try:
            py.build_payload([term], geo='RO', timeframe='today 5-y'); df = py.interest_over_time(); break
        except Exception as ex:
            log('retry', term, str(ex)[:80]); time.sleep(90 * (k + 1))
    if df is None or df.empty:
        log('no data', term); continue
    out[term] = {str(d.date()): round(float(v), 2) for d, v in df[term].astype(float).items()}
    log('ok', term, len(out[term]), 'weeks'); time.sleep(30)
json.dump(out, open(OUT, 'w'), separators=(',', ':'), ensure_ascii=False)
