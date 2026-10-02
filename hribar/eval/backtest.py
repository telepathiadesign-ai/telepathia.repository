#!/usr/bin/env python3
"""Hribar backtest: does the model rank real finds above other fungus records?

Test A (where + when, per species): presences = iNaturalist research/needs-id records of a
catalogue species in Romania since Dec 2023; background = every other macrofungus record in the
same window (target-group background, so observer bias cancels). Score = model index at the
record's place and date. Metric = AUC per species (0.5 = no skill), summarised as median and
record-weighted mean over species with >= MIN_N records.

Test B (is it a fruiting day): weekly share of fungus records among fungus + plant records in
Romania vs the model's generic weather index averaged over the weather nodes, after removing the
calendar-month mean (so it measures weather, not season).

Inputs (eval/data/): inat_ro_fungi_2020_2026.json, habitat_at_points[_v03].json (exported from the
app with test/export_hab.js), era5_nodes.json + era5_land.json (Open-Meteo archive, ERA5-Land
daily), inat_daily_counts_ro.json.

    python3 eval/backtest.py [--variant v03|v04] [--water old|new] [--json out.json]
"""
import argparse, json, math, os, datetime as dt
from collections import defaultdict
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(HERE, 'data')
MACRO = {'1094814', '48341', '47380', '47350', '50815', '48717', '891028', '52526'}  # iNat classes of catalogue species
MIN_N = 15
D0 = dt.date(2023, 12, 1)


def load(name):
    return json.load(open(os.path.join(DATA, name)))


def auc(pos, neg):
    """Mann-Whitney AUC with ties."""
    if not len(pos) or not len(neg):
        return None
    allv = np.concatenate([pos, neg])
    order = allv.argsort(kind='mergesort')
    ranks = np.empty(len(allv))
    sv = allv[order]
    i = 0
    while i < len(sv):
        j = i
        while j + 1 < len(sv) and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = (i + j) / 2 + 1
        i = j + 1
    rp = ranks[:len(pos)].sum()
    return (rp - len(pos) * (len(pos) + 1) / 2) / (len(pos) * len(neg))


def gauss(x, m, s):
    return math.exp(-((x - m) ** 2) / (2 * s * s))


class Weather:
    """ERA5-Land daily series at 0.5° nodes; nearest-node lookup with a lapse-rate correction for soil temperature."""
    def __init__(self):
        p = os.path.join(DATA, 'era5_land.json')
        self.ok = os.path.exists(p)
        if not self.ok:
            return
        raw = load('era5_land.json')
        self.nodes = {}
        for k, v in raw.items():
            lon, lat = map(float, k.split(','))
            t0 = dt.date.fromisoformat(v['t0'])
            arr = {name: np.array([np.nan if x is None else x for x in vals], dtype=float) for name, vals in v['d'].items()}
            if v.get('P'):  # ERA5-Land daily precipitation is empty in the archive API; ERA5 (0.25°) is used for rain
                arr['precipitation_sum'] = np.array([np.nan if x is None else x for x in v['P']], dtype=float)
            sm = arr['soil_moisture_0_to_7cm_mean']; arr['_p10'] = float(np.nanpercentile(sm, 10)); arr['_p90'] = float(np.nanpercentile(sm, 90))
            if np.isnan(arr['precipitation_sum']).all():
                continue
            self.nodes[(lon, lat)] = (t0, v['elev'], arr)

    def at(self, lon, lat):
        key = (round(lon * 2) / 2, round(lat * 2) / 2)
        return self.nodes.get(key)


def season_f(months, date):
    m = date.month - 1
    if months[m]:
        return 1.0
    if months[(m + 11) % 12] or months[(m + 1) % 12]:
        return 0.35
    return 0.0


def weather_f(sp, node, date, elev, water='old'):
    """Weather factors exactly as the app computes them (water='old'), or a candidate replacement."""
    t0, nelev, a = node
    i = (date - t0).days
    if i < 30 or i >= len(a['precipitation_sum']):
        return None
    T = a['soil_temperature_0_to_7cm_mean'][i] - 0.0055 * (elev - nelev)
    temp = 1.0 if os.environ.get('NOTEMP') else gauss(T, sp['t'][0], sp['t'][1] + 1)
    lag0, lag1 = sp['lag']
    rainmm = np.nansum(a['precipitation_sum'][i - lag1:i - lag0 + 1])
    th = a['soil_moisture_0_to_7cm_mean'][i]
    if water == 'old':
        rain = min(1, rainmm / 35)
        moist = min(1, max(0, (th - 0.12) / 0.18))
        w = math.sqrt(rain * moist)
    else:
        w = water(a, i, sp)
    cold = sum(1 for k in range(3) if a['temperature_2m_min'][i - k] <= -2)
    frost = 0 if (cold >= 2 and not sp['frostTol']) else 1
    snow = 0 if a['snow_depth_max'][i] > 0.02 else 1
    return temp * w * frost * snow, dict(T=T, temp=temp, water=w, rainmm=rainmm, theta=th)


def make_water(kind, k=0.85, scale=15.0, wr=0.5, floor=0.15, lo=0.08, hi=0.30):
    """Candidate water terms. All use an antecedent precipitation index (API) instead of a hard window sum,
    and never multiply rain and moisture to zero."""
    def api(a, i):
        r = a['precipitation_sum']
        return sum(r[i - j] * k ** (j - 1) for j in range(1, 22) if not math.isnan(r[i - j]))
    def absolute(a, i, sp):
        rainF = 1 - math.exp(-api(a, i) / scale)
        th = a['soil_moisture_0_to_7cm_mean'][i]
        moistF = min(1, max(0, (th - lo) / (hi - lo)))
        return floor + (1 - floor) * (wr * rainF + (1 - wr) * moistF)
    def relative(a, i, sp):
        rainF = 1 - math.exp(-api(a, i) / scale)
        th = a['soil_moisture_0_to_7cm_mean']
        p10, p90 = a['_p10'], a['_p90']
        moistF = min(1, max(0, (th[i] - p10) / max(0.01, p90 - p10)))
        return floor + (1 - floor) * (wr * rainF + (1 - wr) * moistF)
    def lagged(a, i, sp):
        lag0, lag1 = sp['lag'] if sp else (7, 14)
        r = a['precipitation_sum'][i - lag1:i - lag0 + 1]
        rainF = 1 - math.exp(-np.nansum(r) / scale)
        th = a['soil_moisture_0_to_7cm_mean']
        moistF = min(1, max(0, (th[i] - a['_p10']) / max(0.01, a['_p90'] - a['_p10'])))
        return floor + (1 - floor) * (wr * rainF + (1 - wr) * moistF)
    return {'abs': absolute, 'rel': relative, 'lag': lagged}[kind]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--variant', default='v04', help='habitat export: v04 = habitat_at_points.json, v03 = habitat_at_points_v03.json')
    ap.add_argument('--water', default='old', help='old | abs | rel')
    ap.add_argument('--k', type=float, default=0.85); ap.add_argument('--scale', type=float, default=15); ap.add_argument('--wr', type=float, default=0.5)
    ap.add_argument('--floor', type=float, default=0.15); ap.add_argument('--years', default='')
    ap.add_argument('--fitT', default='', help='json of fitted soil-temperature optima {species: [mean, sd, n]}')
    ap.add_argument('--json')
    a = ap.parse_args()
    water = a.water if a.water == 'old' else make_water(a.water, a.k, a.scale, a.wr, a.floor)
    hab = load('habitat_at_points.json' if a.variant == 'v04' else 'habitat_at_points_v03.json')
    pts = [tuple(p) for p in load('eval_points.json')]
    pidx = {p: k for k, p in enumerate(pts)}
    feat = hab['feat']
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {}
    for r in cat.values():
        for x in r[1]:
            if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower():
                alias[x] = r[0]
    obs = load('inat_ro_fungi_2020_2026.json')
    recs = []
    for o in obs:
        anc = o[9].split('.')
        if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or (o[6] is not None and o[6] > 2000):
            continue
        k = pidx.get((round(o[4], 3), round(o[5], 3)))
        if k is None or not feat[k][3]:
            continue
        nm = ' '.join(o[1].split()[:2]); nm = alias.get(nm, nm)
        sp_rank = o[2] in ('species', 'subspecies', 'variety', 'form')
        if a.years and o[3][:4] not in a.years.split(','):
            continue
        recs.append(dict(nm=nm if sp_rank else None, k=k, date=dt.date.fromisoformat(o[3]), lon=o[4], lat=o[5], e=feat[k][0]))
    W = Weather()
    counts = defaultdict(int)
    for r in recs:
        if r['nm'] in hab['sp']:
            counts[r['nm']] += 1
    species = sorted([s for s, n in counts.items() if n >= MIN_N], key=lambda s: -counts[s])
    fitT = load(a.fitT) if a.fitT else {}
    rows = []
    for s in species:
        sp = dict(hab['sp'][s])
        if s in fitT:
            sp['t'] = [fitT[s][0], fitT[s][1] - 1]
        hv = np.array(sp["h"])
        months = [int(x) for x in sp['months']] if isinstance(sp['months'], str) else sp['months']
        isp = np.array([r['nm'] == s for r in recs])
        H = hv[[r['k'] for r in recs]]
        S = np.array([season_f(months, r['date']) for r in recs])
        res = dict(species=s, n=int(isp.sum()), auc_hab=auc(H[isp], H[~isp]), auc_season=auc(S[isp], S[~isp]), auc_hab_season=auc((H * S)[isp], (H * S)[~isp]))
        if W.ok:
            wv = np.full(len(recs), np.nan)
            for j, r in enumerate(recs):
                node = W.at(r['lon'], r['lat'])
                if node is None:
                    continue
                out = weather_f(sp, node, r['date'], r['e'], water)
                if out is not None:
                    wv[j] = out[0]
            ok = ~np.isnan(wv)
            F = H * S * np.nan_to_num(wv)
            res.update(n_wx=int((isp & ok).sum()), auc_weather=auc(wv[isp & ok], wv[~isp & ok]), auc_full=auc(F[isp & ok], F[~isp & ok]),
                       share_zero_water=float(np.mean(wv[isp & ok] < 0.05)) if (isp & ok).any() else None)
        rows.append(res)
    def summ(key):
        v = [(r[key], r['n']) for r in rows if r.get(key) is not None]
        if not v:
            return None
        x = np.array([a for a, _ in v]); w = np.array([b for _, b in v])
        return dict(median=round(float(np.median(x)), 3), weighted=round(float((x * w).sum() / w.sum()), 3), species=len(v))
    out = dict(variant=a.variant, water=str(a.water), records=len(recs), species=len(rows),
               summary={k: summ(k) for k in ['auc_hab', 'auc_season', 'auc_hab_season', 'auc_weather', 'auc_full']}, rows=rows)
    print(json.dumps(out['summary'], indent=1), 'records', len(recs), 'species', len(rows))
    if a.json:
        json.dump(out, open(a.json, 'w'), indent=1)


if __name__ == '__main__':
    main()
