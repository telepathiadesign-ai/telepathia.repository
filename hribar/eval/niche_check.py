#!/usr/bin/env python3
"""Spatial-block hold-out for the climate-niche model: Romanian 2026 finds inside 1° blocks are scored with models
trained on 2024-25 Romanian finds outside those blocks (+ other countries, weighted), 5 folds. Compared on identical
folds with the shipped land-cover model (fit_landcover features) and the rule-based habitat.

    python3 eval/niche_check.py [--wx 0.3] [--C 0.5] [--ro-only]
"""
import argparse, json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, auc, MACRO, D0
from fit_landcover import lc_grids, features
from fit_habitat import Grids
from fit_niche import niche_feats, records

ap = argparse.ArgumentParser(); ap.add_argument('--wx', type=float, default=0.3); ap.add_argument('--C', type=float, default=0.5)
ap.add_argument('--ro-only', action='store_true'); ap.add_argument('--exonly', action='store_true', help='train the niche model on other countries only (transfer test)'); ap.add_argument('--floor', type=float, default=0.3); ap.add_argument('--min-test', type=int, default=10)
a = ap.parse_args()
HERE = os.path.dirname(os.path.abspath(__file__))
LG = lc_grids(); FG = Grids([os.path.join(HERE, '..', 'data', 'features.json'), os.path.join(HERE, 'data', 'features_wide.json')])
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
    nf = niche_feats(FG.raw(o[4], o[5]))
    if nf is None:
        continue
    nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
    R.append(dict(nm=nm, y=o[3][:4], k=k, blk=(int(o[4]) * 7 + int(o[5]) * 13) % 5, xl=features(LG, o[4], o[5], feat[k][0]), xn=nf))
EX = []
if not a.ro_only:
    for nm, lon, lat, cc, y in records(None, None, False)[0]:
        if cc == 'RO':
            continue
        nf = niche_feats(FG.raw(lon, lat))
        if nf is not None:
            EX.append(dict(nm=nm, xn=nf))
print(len(R), 'RO records,', len(EX), 'other-country records', file=sys.stderr)
NM = np.array([r['nm'] for r in R], dtype=object); Y = np.array([r['y'] for r in R]); B = np.array([r['blk'] for r in R]); K = np.array([r['k'] for r in R])
XL = np.array([r['xl'] for r in R]); XN = np.array([r['xn'] for r in R])
NX = np.array([r['nm'] for r in EX], dtype=object); XNX = np.array([r['xn'] for r in EX]) if EX else np.zeros((0, XN.shape[1]))
rows = []
for s in sorted(set(n for n in NM if n)):
    if s not in hab['sp']:
        continue
    tr_all = np.isin(Y, ['2024', '2025']); te_all = Y == '2026'
    if (NM[te_all] == s).sum() < a.min_test or ((NM[tr_all] == s).sum() + (NX == s).sum()) < 15:
        continue
    lc = np.full(len(R), np.nan); nc = np.full(len(R), np.nan)
    for f in range(5):
        tr = tr_all & (B != f); te = te_all & (B == f)
        if not te.any():
            continue
        ntr_ro = (NM[tr] == s).sum()
        if ntr_ro >= 10:
            m = LogisticRegression(class_weight='balanced', max_iter=500).fit(XL[tr], NM[tr] == s)
            p = m.predict_proba(XL)[:, 1]; lc[te] = np.minimum(1, p[te] / np.percentile(p[tr & (NM == s)], 90))
        trn = tr & (not a.exonly)
        Xtr = np.vstack([XN[trn], XNX]); ytr = np.concatenate([NM[trn] == s, NX == s]); wtr = np.concatenate([np.ones(trn.sum()), np.full(len(EX), a.wx)])
        if ytr.sum() < 10:
            continue
        sw = wtr * np.where(ytr, 0.5 / wtr[ytr].sum(), 0.5 / wtr[~ytr].sum()) * len(ytr)
        mu, sd = Xtr.mean(0), Xtr.std(0) + 1e-6
        m = LogisticRegression(C=a.C, max_iter=1000).fit((Xtr - mu) / sd, ytr, sample_weight=sw)
        p = m.predict_proba((XN - mu) / sd)[:, 1]
        pref = np.percentile(p[tr & (NM == s)], 90) if (tr & (NM == s)).sum() >= 5 and not a.exonly else np.percentile(m.predict_proba((Xtr - mu) / sd)[:, 1][ytr], 90)
        nc[te] = np.minimum(1, p[te] / pref)
    ok = te_all & ~np.isnan(nc)
    pos = ok & (NM == s); neg = ok & (NM != s)
    if pos.sum() < 5:
        continue
    H = np.array(hab['sp'][s]['h'])[K]; fl = a.floor
    has_lc = not np.isnan(lc[ok]).all()
    okl = ok & ~np.isnan(lc); mix = fl + (1 - fl) * np.sqrt(np.maximum(0, lc) * np.maximum(0, nc))
    rows.append((s, int(pos.sum()), auc(H[pos], H[neg]),
                 auc((H * (fl + (1 - fl) * lc))[pos & ~np.isnan(lc)], (H * (fl + (1 - fl) * lc))[neg & ~np.isnan(lc)]) if has_lc else None,
                 auc((H * (fl + (1 - fl) * nc))[pos], (H * (fl + (1 - fl) * nc))[neg]), auc(nc[pos], nc[neg]),
                 auc((H * mix)[pos & okl], (H * mix)[neg & okl]) if has_lc else None))
rng = np.random.default_rng(1)
both = [r for r in rows if r[3] is not None]
print(f'species {len(rows)} (with a Romanian land-cover model: {len(both)})')
print(f'  median habitat AUC: rule {np.median([r[2] for r in rows]):.3f} | rule x niche {np.median([r[4] for r in rows]):.3f} | niche alone {np.median([r[5] for r in rows]):.3f}')
if both:
    print(f'  on the {len(both)} with a land-cover model: rule x land cover {np.median([r[3] for r in both]):.3f} | rule x niche {np.median([r[4] for r in both]):.3f}')
for lab, d in (('rule x niche vs rule (all)', np.array([r[4] - r[2] for r in rows])), ('rule x niche vs rule x land cover', np.array([r[4] - r[3] for r in both])),
               ('rule x sqrt(land cover x niche) vs rule x land cover', np.array([r[6] - r[3] for r in both]))):
    if len(d):
        bs = [rng.choice(d, len(d)).mean() for _ in range(5000)]
        print(f'  {lab}: mean {d.mean():+.4f}  95% CI [{np.percentile(bs, 2.5):+.4f}, {np.percentile(bs, 97.5):+.4f}]  better {(d > 0.005).sum()} worse {(d < -0.005).sum()}')
only = [r for r in rows if r[3] is None]
if only:
    d = np.array([r[4] - r[2] for r in only]); print(f'  species without a Romanian model ({len(only)}): rule x niche vs rule mean {d.mean():+.4f}, better {(d > 0.005).sum()} worse {(d < -0.005).sum()}')
