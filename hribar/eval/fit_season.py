#!/usr/bin/env python3
"""D11: fruiting season per species from the dates of finds (Romania iNaturalist + GBIF elsewhere) instead of catalogue
months. Season curve = smoothed day-of-year density of the species' finds divided by the density of all finds (observer
effort), normalised to a max of 1. Only countries in the Carpathian-Pannonian-Balkan band are used, so no latitude shift.

    python3 eval/fit_season.py --before 2026-01-01 --out eval/data/season_pre26.json
    SEASON_FILE=season_pre26.json python3 eval/backtest.py ...
"""
import argparse, gzip, json, os, sys, datetime as dt
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0

HERE = os.path.dirname(os.path.abspath(__file__))
BAND = {'RO', 'HU', 'SK', 'CZ', 'PL', 'UA', 'MD', 'BG', 'RS', 'AT', 'SI', 'HR', 'BA', 'ME', 'MK', 'AL', 'GR'}


def smooth(counts, bw=12):
    k = np.exp(-0.5 * (np.arange(-3 * bw, 3 * bw + 1) / bw) ** 2)
    x = np.concatenate([counts[-3 * bw:], counts, counts[:3 * bw]])   # circular year
    return np.convolve(x, k, mode='same')[3 * bw:-3 * bw]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--before', default='2026-01-01'); ap.add_argument('--out', required=True)
    ap.add_argument('--min', type=int, default=30); ap.add_argument('--floor', type=float, default=0.05)
    a = ap.parse_args()
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    rows = []
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if len(anc) < 6 or anc[5] not in MACRO or o[3] >= a.before:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2])) if o[2] in ('species', 'subspecies', 'variety', 'form') else None
        rows.append((nm, o[3]))
    p = os.path.join(HERE, 'data', 'records_cee.json.gz')
    if os.path.exists(p):
        for r in json.load(gzip.open(p, 'rt'))['rows']:
            if r[4] in BAND and r[4] != 'RO' and r[1] < a.before:
                rows.append((r[0], r[1]))
    doy = lambda d: min(364, dt.date.fromisoformat(d).timetuple().tm_yday - 1)
    allc = np.zeros(365)
    by = {}
    for nm, d in rows:
        try:
            k = doy(d)
        except ValueError:
            continue
        allc[k] += 1
        if nm:
            by.setdefault(nm, np.zeros(365))[k] += 1
    eff = smooth(allc) + 1e-9
    out = {}
    for s, c in by.items():
        if c.sum() < a.min or s not in cat:
            continue
        r = smooth(c) / eff
        r = r / r.max()
        out[s] = [round(float(max(a.floor, v)), 3) for v in r]
    json.dump({'source': f'eval/fit_season.py: day-of-year density of finds / density of all finds, before {a.before}', 'species': out}, open(a.out, 'w'), separators=(',', ':'))
    print('season curves for', len(out), 'species ->', a.out)


if __name__ == '__main__':
    main()
