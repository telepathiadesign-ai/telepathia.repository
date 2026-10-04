#!/usr/bin/env python3
"""Learn each species' land-cover preference from finds (target-group background) instead of hand rules.

Features at each record: shares of tree, grass+shrub, crop, built-up, water (ESA WorldCover, 0.01° cell) and
log-distance-free elevation bands. Per species with 15+ training finds: L2 logistic regression, presence vs
all other macrofungus records. Output: data/lc_prefs.json {species: {w: [...], b, mx}} used as a multiplier
0.3 + 0.7 * p / mx in the app and in backtest.py (LC_PREFS=1).

    python3 eval/fit_landcover.py --train 2024,2025 [--out data/lc_prefs.json]
"""
import argparse, base64, json, os, sys, zlib, datetime as dt
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = ['tree', 'grass', 'crop', 'built', 'water']


def lc_grids():
    d = json.load(open(os.path.join(HERE, '..', 'data', 'landcover.json')))
    out = {}
    for k in KEYS:
        x = d[k]
        a = np.frombuffer(zlib.decompress(base64.b64decode(x['b'])), dtype='<i2').astype(np.int32).reshape(x['h'], x['w'])
        out[k] = (x, np.cumsum(a, axis=1))
    return out


def features(G, lon, lat, elev):
    v = []
    for k in KEYS:
        x, a = G[k]
        c = int((lon - x['lo0']) / x['st']); r = int((lat - x['la0']) / x['st'])
        val = a[r, c] if 0 <= r < x['h'] and 0 <= c < x['w'] else -1
        v.append(max(0, val) / 100.0)
    e = elev / 1000.0
    return v + [e, e * e]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--train', default='2024,2025'); ap.add_argument('--out', default=os.path.join(HERE, '..', 'data', 'lc_prefs.json'))
    ap.add_argument('--C', type=float, default=1.0)
    a = ap.parse_args()
    years = set(a.train.split(','))
    G = lc_grids()
    feat = load('habitat_at_points.json')['feat']; pts = [tuple(p) for p in load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    X, Y = [], []
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3][:4] not in years or o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
            continue
        k = pidx.get((round(o[4], 3), round(o[5], 3)))
        if k is None or not feat[k][3]:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        X.append(features(G, o[4], o[5], feat[k][0])); Y.append(nm)
    X = np.array(X); Y = np.array(Y, dtype=object)
    out = {}
    for s in sorted(set(y for y in Y if y)):
        pos = Y == s
        if pos.sum() < 15 or s not in cat:
            continue
        m = LogisticRegression(C=a.C, class_weight='balanced', max_iter=500).fit(X, pos)
        p = m.predict_proba(X)[:, 1]
        out[s] = {'w': [round(float(v), 4) for v in m.coef_[0]], 'b': round(float(m.intercept_[0]), 4), 'mx': round(float(np.percentile(p[pos], 90)), 4), 'n': int(pos.sum())}
    json.dump({'source': f'Logistic regression on iNaturalist finds {a.train} (target-group background), features ' + ','.join(KEYS) + ',elev_km,elev_km^2; ESA WorldCover 2021', 'keys': KEYS + ['elev_km', 'elev_km2'], 'species': out}, open(a.out, 'w'), separators=(',', ':'))
    print('fitted', len(out), 'species on', len(X), 'records ->', a.out)


if __name__ == '__main__':
    main()
