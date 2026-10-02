#!/usr/bin/env python3
"""Test B: does the weather term track when fungi are actually fruiting?

Signal: the weekly share of fungus records among fungus + plant records on iNaturalist in Romania
(plants act as a measure of how many people are out recording). Model: the weather term averaged over
the ERA5-Land nodes, weighted by where fungus records come from. Both series have their calendar-month
mean removed, so a high score means the model explains wet and dry spells, not just autumn.

    python3 eval/timing.py --water old|abs|rel [--k .. --scale .. --wr .. --floor ..]
"""
import argparse, json, math, os, datetime as dt
from collections import Counter, defaultdict
import numpy as np
from backtest import load, Weather, make_water, gauss, DATA


def spearman(x, y):
    rx = np.argsort(np.argsort(x)); ry = np.argsort(np.argsort(y))
    return float(np.corrcoef(rx, ry)[0, 1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--water', default='old'); ap.add_argument('--k', type=float, default=0.85); ap.add_argument('--scale', type=float, default=15)
    ap.add_argument('--wr', type=float, default=0.5); ap.add_argument('--floor', type=float, default=0.15)
    ap.add_argument('--start', default='2024-01-01'); ap.add_argument('--end', default='2026-09-25'); ap.add_argument('--quiet', action='store_true')
    a = ap.parse_args()
    W = Weather()
    hist = load('inat_daily_counts_ro.json')
    obs = load('inat_ro_fungi_2020_2026.json')
    weight = Counter((round(o[4] * 2) / 2, round(o[5] * 2) / 2) for o in obs if o[3] >= '2023-12-01')
    nodes = [(k, weight[k]) for k in W.nodes if weight[k] > 0]
    wf = None if a.water == 'old' else make_water(a.water, a.k, a.scale, a.wr, a.floor)
    d0, d1 = dt.date.fromisoformat(a.start), dt.date.fromisoformat(a.end)
    days, share, model = [], [], []
    d = d0
    while d <= d1:
        f = hist['all_Fungi'].get(d.isoformat(), 0); p = hist['all_Plantae'].get(d.isoformat(), 0)
        num = den = 0.0
        for key, w in nodes:
            t0, el, arr = W.nodes[key]; i = (d - t0).days
            if i < 30 or i >= len(arr['precipitation_sum']):
                continue
            if wf is None:
                rain = min(1, np.nansum(arr['precipitation_sum'][i - 14:i - 6]) / 35)
                moist = min(1, max(0, (arr['soil_moisture_0_to_7cm_mean'][i] - 0.12) / 0.18))
                water = math.sqrt(rain * moist)
            else:
                water = wf(arr, i, None)
            T = arr['soil_temperature_0_to_7cm_mean'][i]
            v = water * gauss(T, 13, 6) * (0 if arr['snow_depth_max'][i] > 0.02 else 1)
            num += w * v; den += w
        if den and p >= 15:
            days.append(d); share.append(f / (f + p)); model.append(num / den)
        d += dt.timedelta(days=1)
    # weekly means, then remove calendar-month means
    wk = defaultdict(list)
    for d, s, m in zip(days, share, model):
        wk[(d.isocalendar()[0], d.isocalendar()[1])].append((d, s, m))
    rows = [(v[0][0], np.mean([x[1] for x in v]), np.mean([x[2] for x in v])) for v in wk.values() if len(v) >= 4]
    bym = defaultdict(list)
    for d, s, m in rows:
        bym[d.month].append((s, m))
    mm = {k: (np.mean([x[0] for x in v]), np.mean([x[1] for x in v])) for k, v in bym.items()}
    xs = np.array([s - mm[d.month][0] for d, s, m in rows]); ys = np.array([m - mm[d.month][1] for d, s, m in rows])
    raw = spearman(np.array([r[1] for r in rows]), np.array([r[2] for r in rows]))
    anom = spearman(xs, ys)
    out = dict(water=a.water, weeks=len(rows), spearman_raw=round(raw, 3), spearman_anomaly=round(anom, 3))
    print(json.dumps(out))
    return out


if __name__ == '__main__':
    main()
