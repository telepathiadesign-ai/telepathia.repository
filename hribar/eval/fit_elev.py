#!/usr/bin/env python3
"""Elevation preference per species from finds instead of the catalogue's min-max range.

Per species with 15+ finds (Romania iNaturalist + GBIF neighbour countries): logistic regression of presence vs the
other records on elevation and elevation² (target-group background, so "people record low down" cancels). A concave
curve gives an optimum e* = -w1 / (2 w2) and a width σ = sqrt(-1 / (2 w2)); the app's factor is
max(floor, gauss(e, elev[0], elev[1] * 1.6)), so elev = [e*, σ / 1.6]. Monotonic curves (no interior optimum) keep
the catalogue optimum but with the width clipped. Output merges into data/params.json {species: {elev: [opt, s], n_elev}}.

    python3 eval/fit_elev.py --out data/params.json
"""
import argparse, gzip, json, os, sys
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0
from fit_habitat import Grids

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--out', default=os.path.join(HERE, '..', 'data', 'params.json')); ap.add_argument('--min', type=int, default=15)
    ap.add_argument('--smin', type=float, default=150); ap.add_argument('--smax', type=float, default=700)
    a = ap.parse_args()
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    feat = load('habitat_at_points.json')['feat']; pts = [tuple(p) for p in load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
    E, Y, SRC = [], [], []
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
            continue
        k = pidx.get((round(o[4], 3), round(o[5], 3)))
        if k is None or not feat[k][3]:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        E.append(feat[k][0]); Y.append(nm); SRC.append('RO')
    G = Grids([os.path.join(HERE, 'data', 'features_wide.json')])
    p = os.path.join(HERE, 'data', 'records_cee.json.gz')
    if os.path.exists(p):
        for r in json.load(gzip.open(p, 'rt'))['rows']:
            if r[4] == 'RO' or (r[5] is not None and r[5] > 2000):
                continue
            v = G.raw(r[2], r[3])
            if v is None:
                continue
            E.append(float(v['elev'])); Y.append(r[0]); SRC.append(r[4])
    E = np.array(E) / 1000.0; Y = np.array(Y, dtype=object)
    X = np.column_stack([E, E * E]); mu, sd = X.mean(0), X.std(0)
    Z = (X - mu) / sd
    out = json.load(open(a.out)) if os.path.exists(a.out) else {'species': {}}
    out.setdefault('species', {})
    fitted = kept = 0
    for s in sorted(set(y for y in Y if y)):
        pos = Y == s
        if pos.sum() < a.min or s not in cat:
            continue
        m = LogisticRegression(C=1.0, class_weight='balanced', max_iter=1000).fit(Z, pos)
        # back to raw units: z1 = (e - mu1)/sd1, z2 = (e² - mu2)/sd2  ->  logit = w1/sd1 · e + w2/sd2 · e² + const
        w1, w2 = m.coef_[0][0] / sd[0], m.coef_[0][1] / sd[1]
        lo, hi = cat[s][6] if len(cat[s]) > 7 else None, cat[s][7] if len(cat[s]) > 7 else None
        rec = out['species'].setdefault(s, {})
        if w2 < 0:
            opt = -w1 / (2 * w2) * 1000; sig = np.sqrt(-1 / (2 * w2)) * 1000
            opt = float(np.clip(opt, 50, 2400)); sig = float(np.clip(sig, a.smin, a.smax))
            rec['elev'] = [round(opt), round(sig / 1.6)]; rec['elev_src'] = 'fitted'; fitted += 1
        else:
            # monotonic within the data: the optimum sits at the rising end of the finds' range; keep the curve wide
            ep = E[pos]; q10, q50, q90 = np.percentile(ep, [10, 50, 90]) * 1000
            rising = (w1 + 2 * w2 * q50 / 1000) > 0
            rec['elev'] = [round(float(q90 if rising else q10)), round(a.smax / 1.6)]; rec['elev_src'] = 'rising' if rising else 'falling'; kept += 1
        rec['n_elev'] = int(pos.sum())
    out['source_elev'] = 'eval/fit_elev.py: logistic on elevation, elevation² vs target-group background (Romania iNaturalist + GBIF neighbours)'
    json.dump(out, open(a.out, 'w'), indent=1)
    print(f'elevation: {fitted} species with a fitted optimum, {kept} from quantiles -> {a.out}')


if __name__ == '__main__':
    main()
