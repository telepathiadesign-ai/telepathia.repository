#!/usr/bin/env python3
"""Spatial-block check for the learned land-cover preferences: train on 2024-25 finds outside a set of
1° blocks, score 2026 finds inside them (5 folds), so a model cannot win by memorising hotspots."""
import json, os, sys, datetime as dt
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, auc, MACRO, D0
from fit_landcover import lc_grids, features

G = lc_grids(); hab = load('habitat_at_points.json'); feat = hab['feat']
pts = [tuple(p) for p in load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
cat = {r[0]: r for r in json.load(open(os.path.join(os.path.dirname(__file__), '..', 'data', 'catalog.json')))}
alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
R = []
for o in load('inat_ro_fungi_2020_2026.json'):
    anc = o[9].split('.')
    if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
        continue
    k = pidx.get((round(o[4], 3), round(o[5], 3)))
    if k is None or not feat[k][3]:
        continue
    nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
    blk = (int(o[4]) * 7 + int(o[5]) * 13) % 5
    R.append(dict(nm=nm, y=o[3][:4], k=k, blk=blk, x=features(G, o[4], o[5], feat[k][0])))
X = np.array([r['x'] for r in R]); NM = np.array([r['nm'] for r in R], dtype=object)
Y = np.array([r['y'] for r in R]); B = np.array([r['blk'] for r in R]); K = np.array([r['k'] for r in R])
rows = []
for s in sorted(set(n for n in NM if n)):
    if s not in hab['sp']:
        continue
    tr_all = np.isin(Y, ['2024', '2025']); te_all = Y == '2026'
    if (NM[te_all] == s).sum() < 10 or (NM[tr_all] == s).sum() < 15:
        continue
    learned = np.full(len(R), np.nan)
    for f in range(5):
        tr = tr_all & (B != f); te = te_all & (B == f)
        if (NM[tr] == s).sum() < 10 or not te.any():
            continue
        m = LogisticRegression(class_weight='balanced', max_iter=500).fit(X[tr], NM[tr] == s)
        learned[te] = m.predict_proba(X[te])[:, 1]
    ok = te_all & ~np.isnan(learned)
    pos = ok & (NM == s); neg = ok & (NM != s)
    if pos.sum() < 5:
        continue
    H = np.array(hab['sp'][s]['h'])[K]
    rows.append((s, int(pos.sum()), auc(H[pos], H[neg]), auc((H * (0.3 + 0.7 * learned))[pos], (H * (0.3 + 0.7 * learned))[neg])))
d = np.array([r[3] - r[2] for r in rows])
rng = np.random.default_rng(1); bs = [rng.choice(d, len(d)).mean() for _ in range(5000)]
print(f'species {len(rows)}  habitat AUC rule-based median {np.median([r[2] for r in rows]):.3f} -> with learned land cover {np.median([r[3] for r in rows]):.3f}')
print(f'mean diff {d.mean():+.4f}  95% CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]  better {(d > 0.005).sum()} worse {(d < -0.005).sum()}')
