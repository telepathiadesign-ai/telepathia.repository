#!/usr/bin/env python3
"""Sprint A4: fit the weather timing (soil-temperature optimum and rain delay) per feeding group, in whichever weather
space the backtest runs in (WX_FILE=era5_land.json or hist_forecast.json).

Groups: M = mycorrhizal, SS = soil / litter / dung saprotrophs, SW = wood saprotrophs and parasites (species.json flag +
literature substrate). For each group, grid search over (T mean, T sd, rain window) maximising the mean per-species
weather AUC on the training years, with the same water term as the app (lag, scale 25, wr 0.7, floor 0.15, frost trigger).
Optional per-species temperature optimum, shrunk toward the group value by n / (n + K).

    WX_FILE=hist_forecast.json python3 eval/fit_timing.py --train 2024,2025 --out eval/data/timing_fc_2425.json
    then: python3 eval/backtest.py --years 2026 --params eval/data/timing_fc_2425.json ...  and compare.py
"""
import argparse, json, math, os, sys, itertools
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import backtest as B

HERE = os.path.dirname(os.path.abspath(__file__))
WOOD = {'wood_dead', 'wood_living', 'wood_buried', 'cones'}
LAGS = [(3, 10), (5, 12), (7, 14), (5, 18), (7, 21), (10, 21), (10, 28), (14, 28)]
TMS = list(range(6, 21))  # plausible soil-temperature optima; wider grids chased noise (SW ran to 26 °C) and lost the hold-out gain
TSS = [3, 4, 5, 6, 8]


def group_of(latin, flag, traits):
    sub = (traits.get(latin) or {}).get('substrate', 'soil')
    if flag == 'm' and sub not in WOOD:
        return 'M'
    return 'SW' if sub in WOOD else 'SS'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--train', default='2024,2025'); ap.add_argument('--min', type=int, default=15)
    ap.add_argument('--scale', type=float, default=25); ap.add_argument('--wr', type=float, default=0.7); ap.add_argument('--floor', type=float, default=0.15)
    ap.add_argument('--K', type=float, default=40, help='shrinkage for per-species T optimum (0 = group only)')
    ap.add_argument('--out', required=True)
    a = ap.parse_args()
    years = set(a.train.split(','))
    hab = B.load('habitat_at_points.json'); feat = hab['feat']
    pts = [tuple(p) for p in B.load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    flags = {r[0]: r[10] for r in json.load(open(os.path.join(HERE, '..', 'data', 'species.json')))}
    traits = json.load(open(os.path.join(HERE, '..', 'data', 'traits.json'))); traits = traits.get('species', traits)
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    W = B.Weather()
    recs = []
    for o in B.load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3] < B.D0.isoformat() or len(anc) < 6 or anc[5] not in B.MACRO or (o[6] is not None and o[6] > 2000) or o[3][:4] not in years:
            continue
        k = pidx.get((round(o[4], 3), round(o[5], 3)))
        if k is None or not feat[k][3]:
            continue
        node = W.at(o[4], o[5])
        if node is None:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        recs.append((nm, node, B.dt.date.fromisoformat(o[3]), feat[k][0]))
    # per-record weather pieces, independent of species parameters
    N = len(recs); T = np.full(N, np.nan); moist = np.full(N, np.nan); cold = np.zeros(N); snow = np.ones(N); frost10 = np.zeros(N)
    rainF = {lag: np.full(N, np.nan) for lag in LAGS}
    for j, (nm, node, date, elev) in enumerate(recs):
        t0, nelev, arr = node; i = (date - t0).days
        if i < 30 or i >= len(arr['precipitation_sum']):
            continue
        T[j] = arr['soil_temperature_0_to_7cm_mean'][i] - 0.0055 * (elev - nelev)
        th = arr['soil_moisture_0_to_7cm_mean']
        moist[j] = min(1, max(0, (th[i] - arr['_p10']) / max(0.01, arr['_p90'] - arr['_p10'])))
        cold[j] = sum(1 for k in range(3) if arr['temperature_2m_min'][i - k] <= -2)
        snow[j] = 0 if arr['snow_depth_max'][i] > 0.02 else 1
        frost10[j] = sum(1 for k in range(10) if arr['temperature_2m_min'][i - k] <= 0)
        for lag in LAGS:
            rainF[lag][j] = 1 - math.exp(-np.nansum(arr['precipitation_sum'][i - lag[1]:i - lag[0] + 1]) / a.scale)
    ok = ~np.isnan(T) & ~np.isnan(moist)
    names = np.array([r[0] for r in recs], dtype=object)
    counts = {s: int(((names == s) & ok).sum()) for s in set(n for n in names if n)}
    species = [s for s, n in counts.items() if n >= a.min and s in hab['sp']]
    groups = {}
    for s in species:
        groups.setdefault(group_of(s, flags.get(s, 's'), traits), []).append(s)
    print({g: len(v) for g, v in groups.items()}, 'species;', int(ok.sum()), 'records', file=sys.stderr)

    def wv(tm, ts, lag, frostTol):
        f = (0.6 if not frostTol else 1.0)
        fr = np.where(frost10 >= 2, f, 1.0) if not frostTol else 1.0
        cf = np.where((cold >= 2) & (not frostTol), 0.0, 1.0)
        water = a.floor + (1 - a.floor) * (a.wr * rainF[lag] + (1 - a.wr) * moist)
        return np.exp(-0.5 * ((T - tm) / (ts + 1)) ** 2) * water * cf * snow * fr

    def score(sp_list, tm, ts, lag):
        v = []
        for s in sp_list:
            x = wv(tm, ts, lag, hab['sp'][s]['frostTol'])
            pos = ok & (names == s); neg = ok & (names != s)
            v.append(B.auc(x[pos], x[neg]))
        return float(np.mean(v))

    out = {'source': f'eval/fit_timing.py, train {a.train}, weather {os.environ.get("WX_FILE", "era5_land.json")}, scale {a.scale} wr {a.wr}', 'groups': {}, 'species': {}}
    for g, sp_list in groups.items():
        base = float(np.mean([B.auc(wv(hab['sp'][s]['t'][0], hab['sp'][s]['t'][1], tuple(hab['sp'][s]['lag']) if tuple(hab['sp'][s]['lag']) in rainF else (7, 14), hab['sp'][s]['frostTol'])[ok & (names == s)],
                                    wv(hab['sp'][s]['t'][0], hab['sp'][s]['t'][1], tuple(hab['sp'][s]['lag']) if tuple(hab['sp'][s]['lag']) in rainF else (7, 14), hab['sp'][s]['frostTol'])[ok & (names != s)]) for s in sp_list]))
        best = max(((score(sp_list, tm, ts, lag), tm, ts, lag) for tm, ts, lag in itertools.product(TMS, TSS, LAGS)))
        out['groups'][g] = {'t': [best[1], best[2]], 'lag': list(best[3]), 'n_species': len(sp_list), 'train_auc_weather': round(best[0], 4), 'app_params_auc_weather': round(base, 4)}
        keep = best[0] >= base + 0.005
        out['groups'][g]['used'] = keep
        print(f'{g}: {len(sp_list)} species, app params {base:.3f} -> group fit {best[0]:.3f}  T {best[1]}±{best[2]} rain window {best[3]}' + ('' if keep else '  (no gain: app parameters kept)'), file=sys.stderr)
        for s in (sp_list if keep else []):
            tm, ts, lag = best[1], best[2], best[3]
            if a.K > 0:
                # per-species optimum: the T at which this species' records most exceed the background, shrunk toward the group
                pos = ok & (names == s)
                sc = [(score([s], t2, ts, lag), t2) for t2 in TMS]
                t_sp = max(sc)[1]; n = counts[s]
                tm = round(n / (n + a.K) * t_sp + a.K / (n + a.K) * best[1], 1)
            out['species'][s] = {'t': [tm, ts], 'lag': list(lag), 'group': g, 'n': counts[s]}
    json.dump(out, open(a.out, 'w'), indent=1)
    print('wrote', a.out, len(out['species']), 'species')


if __name__ == '__main__':
    main()
