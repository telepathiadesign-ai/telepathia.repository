#!/usr/bin/env python3
"""Spatial-block check, A2: train on 2024-25 finds outside a set of 1° blocks (optionally plus GBIF neighbour-country
finds), score 2026 finds inside them (5 folds). Compares rule-based habitat, x learned land cover (fit_landcover features),
and x learned habitat (fit_habitat features) on identical folds.

    python3 eval/spatial_habitat.py [--wide] [--C 0.3]
"""
import argparse, json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, auc, MACRO, D0
from fit_landcover import lc_grids, features
from fit_habitat import Grids, featurize, records

ap = argparse.ArgumentParser(); ap.add_argument('--wide', action='store_true'); ap.add_argument('--C', type=float, default=0.3)
ap.add_argument('--floor', type=float, default=0.3); ap.add_argument('--wx', type=float, default=1.0); ap.add_argument('--cols', default=''); ap.add_argument('--exonly', action='store_true')
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
LG = lc_grids(); FG = Grids([os.path.join(HERE, '..', 'data', 'features.json'), os.path.join(HERE, 'data', 'features_wide.json')])
traits = json.load(open(os.path.join(HERE, '..', 'data', 'traits.json'))); traits = traits.get('species', traits)
hab = load('habitat_at_points.json'); feat = hab['feat']
pts = [tuple(p) for p in load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
R = []
for o in load('inat_ro_fungi_2020_2026.json'):
    anc = o[9].split('.')
    if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
        continue
    k = pidx.get((round(o[4], 3), round(o[5], 3)))
    if k is None or not feat[k][3]:
        continue
    v = FG.raw(o[4], o[5])
    if v is None:
        continue
    nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
    R.append(dict(nm=nm, y=o[3][:4], k=k, blk=(int(o[4]) * 7 + int(o[5]) * 13) % 5, xl=features(LG, o[4], o[5], feat[k][0]), v=v))
EX = []  # extra training rows (neighbour countries), never tested
if a.wide:
    recs, _ = records({'2018', '2019', '2020', '2021', '2022', '2023', '2024', '2025'}, True)
    for nm, lon, lat, y, reg in recs:
        if reg == 'RO':
            continue
        v = FG.raw(lon, lat)
        if v is not None:
            EX.append(dict(nm=nm, v=v))
print(len(R), 'RO records,', len(EX), 'extra training records', file=sys.stderr)
NM = np.array([r['nm'] for r in R], dtype=object); Y = np.array([r['y'] for r in R]); B = np.array([r['blk'] for r in R]); K = np.array([r['k'] for r in R])
XL = np.array([r['xl'] for r in R]); XB = np.array([featurize(r['v']) for r in R])
NX = np.array([r['nm'] for r in EX], dtype=object); XBX = np.array([featurize(r['v']) for r in EX]) if EX else np.zeros((0, XB.shape[1]))
from fit_habitat import KEYS as FK
COLS = [FK.index(c) for c in a.cols.split(',')] if a.cols else list(range(len(FK)))
rows = []
for s in sorted(set(n for n in NM if n)):
    if s not in hab['sp']:
        continue
    tr_all = np.isin(Y, ['2024', '2025']); te_all = Y == '2026'
    if (NM[te_all] == s).sum() < 10 or (NM[tr_all] == s).sum() < 15:
        continue
    hosts = (traits.get(s) or {}).get('hosts') or {}
    hostc = np.array([featurize(r['v'], hosts)[-1] for r in R]); hostx = np.array([featurize(r['v'], hosts)[-1] for r in EX])
    XH = XB.copy(); XH[:, -1] = hostc
    XHX = XBX.copy()
    if len(EX):
        XHX[:, -1] = hostx
    lc = np.full(len(R), np.nan); hb = np.full(len(R), np.nan)
    for f in range(5):
        tr = tr_all & (B != f); te = te_all & (B == f)
        if (NM[tr] == s).sum() < 10 or not te.any():
            continue
        m = LogisticRegression(class_weight='balanced', max_iter=500).fit(XL[tr], NM[tr] == s)
        p = m.predict_proba(XL)[:, 1]; lc[te] = np.minimum(1, p[te] / np.percentile(p[tr & (NM == s)], 90))
        trh = tr & (not a.exonly)
        Xtr = np.vstack([XH[trh], XHX]); ytr = np.concatenate([NM[trh] == s, NX == s]) if len(EX) else NM[trh] == s
        Xtr = Xtr[:, COLS]; mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
        if ytr.sum() < 10:
            continue
        swt = np.concatenate([np.ones(trh.sum()), np.full(len(EX), a.wx)])
        swt = swt * np.where(ytr, 0.5 / (swt * ytr).sum(), 0.5 / (swt * ~ytr).sum()) * len(ytr)
        m = LogisticRegression(C=a.C, max_iter=1000).fit((Xtr - mu) / sd, ytr, sample_weight=swt)
        p = m.predict_proba((XH[:, COLS] - mu) / sd)[:, 1]; hb[te] = np.minimum(1, p[te] / np.percentile(p[tr & (NM == s)], 90))
    ok = te_all & ~np.isnan(lc) & ~np.isnan(hb)
    pos = ok & (NM == s); neg = ok & (NM != s)
    if pos.sum() < 5:
        continue
    H = np.array(hab['sp'][s]['h'])[K]; fl = a.floor
    rows.append((s, int(pos.sum()), auc(H[pos], H[neg]), auc((H * (fl + (1 - fl) * lc))[pos], (H * (fl + (1 - fl) * lc))[neg]),
                 auc((H * (fl + (1 - fl) * hb))[pos], (H * (fl + (1 - fl) * hb))[neg]), auc(hb[pos], hb[neg])))
rng = np.random.default_rng(1)
print(f'species {len(rows)}  habitat AUC median: rule {np.median([r[2] for r in rows]):.3f} | x land cover {np.median([r[3] for r in rows]):.3f} '
      f'| x learned habitat {np.median([r[4] for r in rows]):.3f} | learned habitat alone {np.median([r[5] for r in rows]):.3f}')
for i, lab in ((4, 'learned habitat vs land cover'), (5, 'habitat alone vs land cover'), (-4, 'learned habitat vs rule')):
    d = np.array([(r[4] - r[2]) if i == -4 else (r[i] - r[3]) for r in rows]); bs = [rng.choice(d, len(d)).mean() for _ in range(5000)]
    print(f'{lab}: mean {d.mean():+.4f}  95% CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]  better {(d > 0.005).sum()} worse {(d < -0.005).sum()}')
