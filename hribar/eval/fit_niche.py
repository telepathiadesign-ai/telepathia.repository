#!/usr/bin/env python3
"""Climate-niche habitat model per species (the Sporecast-style "where"): logistic regression on climate and land cover,
trained on Romanian iNaturalist finds plus GBIF finds from other countries, target-group background. Elevation is left
out on purpose: it is a proxy for climate that does not transfer between countries (Amanita muscaria is a lowland species
in Poland and a montane one in Romania). Climate does transfer.

Features: tree, grass, crop, built, water shares (ESA WorldCover); bio10 mean temperature of the warmest quarter and its
square; bio12 annual precipitation (m) and its square; bio15 precipitation seasonality; bio1 annual mean temperature
(CHELSA V2.1). Output: data/lc_prefs.json-compatible entries with keys 'niche' so the app can tell them apart:
{species: {w: [...], b, mx, n, src: 'niche', mu: [...], sd: [...]}}, applied as 0.3 + 0.7 * min(1, p / mx).

    python3 eval/fit_niche.py --out eval/data/niche.json [--wx 0.3] [--ro-only] [--before 2026-01-01] [--train 2024,2025]
    python3 eval/niche_check.py   # spatial-block hold-out vs the shipped land-cover model
"""
import argparse, gzip, json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0
from fit_habitat import Grids

HERE = os.path.dirname(os.path.abspath(__file__))
KEYS = ['tree', 'grass', 'crop', 'built', 'water', 'bio10', 'bio10_2', 'bio12', 'bio12_2', 'bio15', 'bio1']


def niche_feats(v):
    if v is None or v.get('c_bio10', -32768) <= -32768 or v.get('c_bio12', -32768) <= -32768:
        return None
    g = lambda k: max(0.0, float(v.get(k, 0))) / 100.0
    t10 = v['c_bio10'] / 10.0; p = v['c_bio12'] / 1000.0; s15 = v.get('c_bio15', 0) / 10.0; t1 = v.get('c_bio1', 0) / 10.0
    return [g('tree'), g('grass'), g('crop'), g('built'), g('water'), t10, t10 * t10, p, p * p, s15 / 100.0, t1]


def records(train_years=None, before=None, ro_only=False):
    """[(name, lon, lat, country, year)] for RO iNaturalist macrofungi (+ GBIF other countries)."""
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    out = []
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
            continue
        if (train_years and o[3][:4] not in train_years) or (before and o[3] >= before):
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        out.append((nm, o[4], o[5], 'RO', o[3][:4]))
    p = os.path.join(HERE, 'data', 'records_cee.json.gz')
    if not ro_only and os.path.exists(p):
        for r in json.load(gzip.open(p, 'rt'))['rows']:
            if r[4] == 'RO' or (r[5] is not None and r[5] > 2000):
                continue
            out.append((r[0], r[2], r[3], r[4], r[1][:4]))
    return out, cat


def fit(recs, cat, G, C=0.5, wx=0.3, min_n=15, verbose=True):
    X, Y, W = [], [], []
    for nm, lon, lat, cc, y in recs:
        f = niche_feats(G.raw(lon, lat))
        if f is None:
            continue
        X.append(f); Y.append(nm); W.append(1.0 if cc == 'RO' else wx)
    X = np.array(X); Y = np.array(Y, dtype=object); W = np.array(W)
    mu, sd = X.mean(0), X.std(0) + 1e-6; Z = (X - mu) / sd
    counts = {s: int((Y == s).sum()) for s in set(y for y in Y if y)}
    out = {}
    for s, n in counts.items():
        if n < min_n or s not in cat:
            continue
        pos = Y == s
        sw = W * np.where(pos, 0.5 / W[pos].sum(), 0.5 / W[~pos].sum()) * len(Y)
        m = LogisticRegression(C=C, max_iter=1000).fit(Z, pos, sample_weight=sw)
        p = m.predict_proba(Z)[:, 1]
        out[s] = {'w': [round(float(v), 4) for v in m.coef_[0]], 'b': round(float(m.intercept_[0]), 4), 'mx': round(float(np.percentile(p[pos], 90)), 4),
                  'n': n, 'n_ro': int((pos & (W == 1.0)).sum()), 'src': 'niche'}
    if verbose:
        print(f'{len(X)} records with features; {len(out)} species fitted', file=sys.stderr)
    return {'keys': KEYS, 'mu': [round(float(v), 5) for v in mu], 'sd': [round(float(v), 5) for v in sd], 'species': out}


def predict(model, s, v):
    c = model['species'].get(s); f = niche_feats(v)
    if c is None or f is None:
        return None
    z = (np.array(f) - np.array(model['mu'])) / np.array(model['sd'])
    return float(1 / (1 + np.exp(-(z @ np.array(c['w']) + c['b']))))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', required=True); ap.add_argument('--wx', type=float, default=0.3); ap.add_argument('--C', type=float, default=0.5)
    ap.add_argument('--train', default=''); ap.add_argument('--before', default=''); ap.add_argument('--ro-only', action='store_true'); ap.add_argument('--min', type=int, default=15)
    a = ap.parse_args()
    G = Grids([os.path.join(HERE, '..', 'data', 'features.json'), os.path.join(HERE, 'data', 'features_wide.json')])
    recs, cat = records(set(a.train.split(',')) if a.train else None, a.before or None, a.ro_only)
    m = fit(recs, cat, G, a.C, a.wx, a.min)
    m['source'] = f'eval/fit_niche.py: logistic climate-niche model (C={a.C}, other-country weight {a.wx}); ESA WorldCover 2021 + CHELSA V2.1 bioclim; target-group background'
    json.dump(m, open(a.out, 'w'), separators=(',', ':'))
    print('wrote', a.out, len(m['species']), 'species')


if __name__ == '__main__':
    main()
