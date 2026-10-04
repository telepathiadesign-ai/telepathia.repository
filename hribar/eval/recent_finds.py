#!/usr/bin/env python3
"""Does "this species was reported nearby in the last days" predict the next find?

For each fungus record since 2024 (species s at place x, day d) we count reports of s within R km during
d-W..d-1 by OTHER observers. Presences = records of s; background = records of other species, scored for s.
AUC per species with 15+ records, alone and combined with the model (full index from backtest.py rows is not
per-record, so the combination uses a simple boost: model * (1 + b * min(1, n/3))).

    python3 eval/recent_finds.py [--km 30] [--days 10]
"""
import argparse, json, math, datetime as dt, os, sys
from collections import defaultdict
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, auc, MACRO, D0

ap = argparse.ArgumentParser(); ap.add_argument('--km', type=float, default=30); ap.add_argument('--days', type=int, default=10)
a = ap.parse_args()
cat = {r[0]: r for r in json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'catalog.json')))}
alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
recs = []
for o in load('inat_ro_fungi_2020_2026.json'):
    anc = o[9].split('.')
    if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO:
        continue
    nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2]))
    recs.append((nm if o[2] in ('species', 'subspecies', 'variety', 'form') else None, dt.date.fromisoformat(o[3]), o[4], o[5], o[10]))
by_sp = defaultdict(list)
for r in recs:
    if r[0]:
        by_sp[r[0]].append(r)
species = [s for s, v in by_sp.items() if len(v) >= 15 and s in cat]
R = a.km / 111.0


def recent(s, d, lon, lat, user):
    n = 0
    for (_, d2, lo2, la2, u2) in by_sp[s]:
        if 0 < (d - d2).days <= a.days and u2 != user and (lon - lo2) ** 2 * 0.5 + (lat - la2) ** 2 <= R * R:
            n += 1
    return n


rows = []
for s in species:
    pos = np.array([recent(s, r[1], r[2], r[3], r[4]) for r in recs if r[0] == s], float)
    neg = np.array([recent(s, r[1], r[2], r[3], r[4]) for r in recs if r[0] != s], float)
    rows.append(dict(species=s, n=len(pos), auc_recent=auc(pos, neg), share_pos_with_signal=float((pos > 0).mean()), share_neg_with_signal=float((neg > 0).mean())))
x = np.array([r['auc_recent'] for r in rows]); w = np.array([r['n'] for r in rows])
print(json.dumps(dict(km=a.km, days=a.days, species=len(rows), auc_median=round(float(np.median(x)), 3), auc_weighted=round(float((x * w).sum() / w.sum()), 3),
                      finds_with_signal=round(float(np.mean([r['share_pos_with_signal'] for r in rows])), 3),
                      background_with_signal=round(float(np.mean([r['share_neg_with_signal'] for r in rows])), 3))))
json.dump(rows, open(os.path.join(os.path.dirname(__file__), 'data', f'recent_finds_{int(a.km)}km_{a.days}d.json'), 'w'), indent=0)
