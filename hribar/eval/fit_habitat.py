#!/usr/bin/env python3
"""Sprint A2: one learned habitat model per species from all habitat features (data/features.json for Romania,
eval/data/features_wide.json for the wider training region).

Features at each record (0.01° cell): land-cover shares, elevation (+ squared), slope, heat load, soil clay / sand /
organic carbon / pH (+ squared), 11 tree-species probabilities, and the species' own host availability (literature host
genera from data/traits.json x tree-species probability). Per species with enough finds: L2 logistic regression,
presence vs all other macrofungus / catalogue records (target-group background), standardised features.
Species with few finds borrow from their genus: the genus model's logit enters as an extra feature (partial pooling).

    python3 eval/fit_habitat.py --train 2024,2025 [--wide] [--C 0.3] --out eval/data/hab_prefs_train2425.json
    python3 eval/fit_habitat.py --train 2024,2025,2026 --wide --out data/hab_prefs.json      # ship
"""
import argparse, base64, gzip, json, os, sys, zlib
import numpy as np
from sklearn.linear_model import LogisticRegression
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0

HERE = os.path.dirname(os.path.abspath(__file__))
TREES = ['abies_alba', 'castanea_sativa', 'corylus_avellana', 'fagus_sylvatica', 'picea_abies', 'pinus_nigra', 'pinus_sylvestris',
         'prunus_avium', 'quercus_cerris', 'quercus_robur', 'salix_caprea']
GENUS_TREES = {'Abies': ['abies_alba'], 'Castanea': ['castanea_sativa'], 'Corylus': ['corylus_avellana'], 'Fagus': ['fagus_sylvatica'],
               'Picea': ['picea_abies'], 'Pinus': ['pinus_nigra', 'pinus_sylvestris'], 'Prunus': ['prunus_avium'],
               'Quercus': ['quercus_cerris', 'quercus_robur'], 'Salix': ['salix_caprea']}
BASE = ['tree', 'grass', 'crop', 'built', 'water', 'elev', 'slope', 'hli', 'clay', 'sand', 'soc', 'ph']
KEYS = ['tree', 'grass', 'crop', 'built', 'water', 'elev_km', 'elev_km2', 'slope', 'hli', 'clay', 'sand', 'log_soc', 'ph', 'ph2'] + ['t_' + t for t in TREES] + ['host']


class Grids:
    def __init__(self, files):
        self.g = []
        for f in files:
            if not os.path.exists(f):
                continue
            d = json.load(open(f))
            G = {}
            for k, x in d.items():
                if k == 'meta' or not isinstance(x, dict) or 'b' not in x:
                    continue
                a = np.frombuffer(zlib.decompress(base64.b64decode(x['b'])), dtype='<i2').astype(np.int32).reshape(x['h'], x['w'])
                G[k] = (x, np.cumsum(a, axis=1).astype(np.float32))
            self.g.append(G)

    def raw(self, lon, lat):
        """dict of raw layer values at a point from the first grid set that covers it (None if no data)."""
        for G in self.g:
            x, _ = next(iter(G.values()))
            c = int((lon - x['lo0']) / x['st']); r = int((lat - x['la0']) / x['st'])
            if not (0 <= r < x['h'] and 0 <= c < x['w']):
                continue
            v = {k: a[r, c] for k, (x, a) in G.items()}
            if v.get('elev', -32768) <= -32768 or v.get('tree', -1) < 0:
                continue
            return v
        return None


def featurize(v, hosts=None):
    if v is None:
        return None
    g = lambda k, d=0.0: float(v[k]) if k in v and v[k] >= 0 else d
    e = (float(v['elev']) if v.get('elev', -32768) > -32768 else 300.0) / 1000
    ph = g('ph', 60) / 10
    t = [g('t_' + k) / 100 for k in TREES]
    host = 0.0
    if hosts:
        for gen, w in hosts.items():
            for tk in GENUS_TREES.get(gen, []):
                host = max(host, w * g('t_' + tk) / 100)
    return [g('tree') / 100, g('grass') / 100, g('crop') / 100, g('built') / 100, g('water') / 100, e, e * e,
            g('slope') / 100, g('hli', 700) / 1000, g('clay', 200) / 1000, g('sand', 400) / 1000, np.log1p(g('soc', 300) / 10),
            ph, ph * ph] + t + [host]


def records(train_years, wide):
    """[(name, lon, lat, year, region)] for RO iNaturalist (macrofungi) and, optionally, GBIF neighbour-country finds."""
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    out = []
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
            continue
        if o[3][:4] not in train_years:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        out.append((nm, o[4], o[5], o[3][:4], 'RO'))
    if wide:
        p = os.path.join(HERE, 'data', 'records_cee.json.gz')
        if os.path.exists(p):
            for r in json.load(gzip.open(p, 'rt'))['rows']:
                if r[1][:4] in train_years and (r[5] is None or r[5] <= 2000):
                    out.append((r[0], r[2], r[3], r[1][:4], r[4]))
    return out, cat


def fit(train_years, wide, C, min_n, pool=True, verbose=True):
    G = Grids([os.path.join(HERE, '..', 'data', 'features.json'), os.path.join(HERE, 'data', 'features_wide.json')])
    traits = json.load(open(os.path.join(HERE, '..', 'data', 'traits.json')))
    traits = traits.get('species', traits)
    recs, cat = records(set(train_years), wide)
    raws, names = [], []
    for nm, lon, lat, y, reg in recs:
        v = G.raw(lon, lat)
        if v is None:
            continue
        raws.append(v); names.append(nm)
    names = np.array(names, dtype=object)
    Xb = np.array([featurize(v) for v in raws])
    mu, sd = Xb.mean(0), Xb.std(0) + 1e-6
    counts = {s: int((names == s).sum()) for s in set(n for n in names if n)}
    if verbose:
        print(f'{len(raws)} records with features, {sum(1 for n in counts.values() if n >= min_n)} species with >= {min_n} finds', file=sys.stderr)
    # genus models (pooling)
    genus_m = {}
    if pool:
        gen = np.array([n.split()[0] if n else None for n in names], dtype=object)
        Z = (Xb - mu) / sd
        for g_ in set(x for x in gen if x):
            pos = gen == g_
            if pos.sum() >= 30:
                m = LogisticRegression(C=C, class_weight='balanced', max_iter=1000).fit(Z, pos)
                genus_m[g_] = (m.coef_[0], float(m.intercept_[0]))
    out = {}
    for s, n in counts.items():
        if n < min_n or s not in cat:
            continue
        hosts = (traits.get(s) or {}).get('hosts') or {}
        X = np.array([featurize(v, hosts) for v in raws]); X[:, :-1] = Xb[:, :-1]
        m_host = X[:, -1].mean(); s_host = X[:, -1].std() + 1e-6
        Z = np.column_stack([(X[:, :-1] - mu[:-1]) / sd[:-1], (X[:, -1] - m_host) / s_host])
        gk = s.split()[0]
        if gk in genus_m:
            gw, gb = genus_m[gk]; Z = np.column_stack([Z, Z[:, :-1] @ gw[:-1] + gb])
        pos = names == s
        m = LogisticRegression(C=C, class_weight='balanced', max_iter=1000).fit(Z, pos)
        p = m.predict_proba(Z)[:, 1]
        out[s] = {'w': [round(float(v), 4) for v in m.coef_[0]], 'b': round(float(m.intercept_[0]), 4), 'mx': round(float(np.percentile(p[pos], 90)), 4),
                  'n': n, 'hostmu': round(float(m_host), 4), 'hostsd': round(float(s_host), 4), 'hosts': hosts,
                  'genus': [[round(float(v), 4) for v in genus_m[gk][0][:-1]], round(genus_m[gk][1], 4)] if gk in genus_m else None}
    return {'keys': KEYS, 'mu': [round(float(v), 5) for v in mu[:-1]], 'sd': [round(float(v), 5) for v in sd[:-1]], 'species': out}


def predict(model, s, v):
    """Habitat probability for species s at raw feature dict v (None if not modelled / no data)."""
    c = model['species'].get(s)
    if c is None or v is None:
        return None
    x = np.array(featurize(v, c['hosts']))
    z = np.append((x[:-1] - np.array(model['mu'])) / np.array(model['sd']), (x[-1] - c['hostmu']) / c['hostsd'])
    if c['genus']:
        z = np.append(z, z[:-1] @ np.array(c['genus'][0]) + c['genus'][1])
    return float(1 / (1 + np.exp(-(z @ np.array(c['w']) + c['b']))))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', default='2024,2025'); ap.add_argument('--wide', action='store_true')
    ap.add_argument('--C', type=float, default=0.3); ap.add_argument('--min', type=int, default=15); ap.add_argument('--nopool', action='store_true')
    ap.add_argument('--out', default=os.path.join(HERE, 'data', 'hab_prefs.json'))
    a = ap.parse_args()
    m = fit(a.train.split(','), a.wide, a.C, a.min, pool=not a.nopool)
    m['source'] = (f'L2 logistic regression (C={a.C}) on finds {a.train}' + (' incl. GBIF neighbour countries' if a.wide else '') +
                   '; target-group background; features: ESA WorldCover 2021, Copernicus DEM, SoilGrids 2.0, Bonannella et al. 2022 tree maps')
    json.dump(m, open(a.out, 'w'), separators=(',', ':'))
    print('fitted', len(m['species']), 'species ->', a.out)


if __name__ == '__main__':
    main()
