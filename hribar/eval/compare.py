#!/usr/bin/env python3
"""Is a change real or noise? Paired comparison of two backtest runs (backtest.py --json).

For each metric: per-species difference (B - A), its mean and median, how many species got better or
worse, and a 95% bootstrap interval over species (5,000 resamples). A change counts as real only if the
interval of the mean difference excludes zero.

    python3 eval/compare.py runA.json runB.json [--metric auc_full]
"""
import argparse, json
import numpy as np


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('a'); ap.add_argument('b')
    ap.add_argument('--metric', action='append')
    a = ap.parse_args()
    A = {r['species']: r for r in json.load(open(a.a))['rows']}
    B = {r['species']: r for r in json.load(open(a.b))['rows']}
    metrics = a.metric or ['auc_hab', 'auc_season', 'auc_hab_season', 'auc_weather', 'auc_full']
    rng = np.random.default_rng(7)
    out = {}
    for m in metrics:
        d = np.array([B[s][m] - A[s][m] for s in A if s in B and A[s].get(m) is not None and B[s].get(m) is not None])
        if not len(d):
            continue
        boots = np.array([rng.choice(d, len(d)).mean() for _ in range(5000)])
        lo, hi = np.percentile(boots, [2.5, 97.5])
        verdict = 'better' if lo > 0 else 'worse' if hi < 0 else 'no clear change'
        out[m] = dict(n=len(d), mean=round(float(d.mean()), 4), median=round(float(np.median(d)), 4), ci95=[round(float(lo), 4), round(float(hi), 4)],
                      better=int((d > 0.005).sum()), worse=int((d < -0.005).sum()), verdict=verdict)
        print(f"{m:16} mean {d.mean():+.4f}  95% CI [{lo:+.4f}, {hi:+.4f}]  better {out[m]['better']:3} worse {out[m]['worse']:3}  -> {verdict}")
    return out


if __name__ == '__main__':
    main()
