#!/usr/bin/env python3
"""Learned land-cover preference from neighbour-country finds (GBIF, eval/data/records_cee.json.gz), for species with too
few Romanian finds. Same 7 features and output format as fit_landcover.py, so the app and backtest use it unchanged.
Features come from eval/data/features_wide.json (same ESA WorldCover classes; elevation from Copernicus DEM).

Tested (spatial_habitat.py --wide --exonly): trained on neighbours only, scored on Romanian 2026 finds, habitat AUC
+0.031 over the rule-based habitat (95% CI +0.009..+0.058), but -0.018 vs a Romania-trained model. So: Romanian model
where a species has 15+ Romanian finds, this one otherwise.

    python3 eval/fit_landcover_cee.py --ro data/lc_prefs.json --out data/lc_prefs.json [--only-cee out.json]
"""
import argparse, gzip, json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fit_habitat import Grids

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--ro', default=''); ap.add_argument('--out', required=True); ap.add_argument('--min', type=int, default=15)
    ap.add_argument('--C', type=float, default=1.0)
    a = ap.parse_args()
    G = Grids([os.path.join(HERE, 'data', 'features_wide.json')])
    cat = {r[0] for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    X, Y = [], []
    for r in json.load(gzip.open(os.path.join(HERE, 'data', 'records_cee.json.gz'), 'rt'))['rows']:
        if r[4] == 'RO' or (r[5] is not None and r[5] > 2000):
            continue
        v = G.raw(r[2], r[3])
        if v is None:
            continue
        e = float(v['elev']) / 1000
        X.append([max(0, v[k]) / 100 for k in ('tree', 'grass', 'crop', 'built', 'water')] + [e, e * e]); Y.append(r[0])
    X = np.array(X); Y = np.array(Y, dtype=object)
    base = json.load(open(a.ro)) if a.ro else {'species': {}, 'keys': ['tree', 'grass', 'crop', 'built', 'water', 'elev_km', 'elev_km2']}
    added = 0
    for s in sorted(set(Y)):
        pos = Y == s
        if s in base['species'] or pos.sum() < a.min or s not in cat:
            continue
        m = LogisticRegression(C=a.C, class_weight='balanced', max_iter=1000).fit(X, pos)
        p = m.predict_proba(X)[:, 1]
        base['species'][s] = {'w': [round(float(v), 4) for v in m.coef_[0]], 'b': round(float(m.intercept_[0]), 4),
                              'mx': round(float(np.percentile(p[pos], 90)), 4), 'n': int(pos.sum()), 'src': 'neighbours'}
        added += 1
    base['source'] = (base.get('source', '') + '; species with too few Romanian finds: fitted on GBIF finds in neighbouring countries '
                      '(src=neighbours)').lstrip('; ')
    json.dump(base, open(a.out, 'w'), separators=(',', ':'))
    print(f'{len(X)} neighbour records; added {added} species; total {len(base["species"])} -> {a.out}')


if __name__ == '__main__':
    main()
