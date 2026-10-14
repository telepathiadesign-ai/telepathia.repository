#!/usr/bin/env python3
"""Per-species audit: catches species whose map is wrong even when the aggregate scores look fine.

Inputs: the app's habitat exported at the evaluation points (finds) and on a regular 0.1° grid over Romania
(test/export_hab.js), plus Romanian finds.

Checks per species:
  1. finds vs map  - percentile of the species' habitat score at its own Romanian finds, against all land cells of the grid.
                     A good map puts finds high (median percentile well above 0.5). Flag < 0.6 with 3+ finds.
  2. spread        - share of Romanian land the map calls High (>= 0.68). Flag > 40 % (paints everything) or 0 % with finds.
  3. rules vs learned (when a learned model exists) - rank correlation, over the grid, between the habitat without the
                     learned model and with it. Flag < 0: the rules and the data disagree on where the species lives.
Outputs: eval/AUDIT.md (table, flags first) and eval/audit_sheet_<n>.png contact sheets (one small habitat map per species).

    python3 eval/audit.py --grid eval/data/habitat_grid.json --grid-nolearn eval/data/habitat_grid_nolc.json
"""
import argparse, json, os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from backtest import load, MACRO, D0

HERE = os.path.dirname(os.path.abspath(__file__))


def rankcorr(a, b):
    ra = np.argsort(np.argsort(a)); rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1]) if np.std(ra) and np.std(rb) else float('nan')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grid', required=True); ap.add_argument('--grid-nolearn', default=''); ap.add_argument('--grid-pts', default=os.path.join(HERE, 'data', 'grid_points.json'))
    ap.add_argument('--out', default=os.path.join(HERE, 'AUDIT.md'))
    a = ap.parse_args()
    G = json.load(open(a.grid)); GN = json.load(open(a.grid_nolearn)) if a.grid_nolearn else None
    gpts = np.array(json.load(open(a.grid_pts)))
    land = np.array([f[3] == 1 for f in G['feat']])
    hab = load('habitat_at_points.json'); feat = hab['feat']
    pts = [tuple(p) for p in load('eval_points.json')]; pidx = {p: k for k, p in enumerate(pts)}
    cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
    names = {r[0]: r[2] for r in json.load(open(os.path.join(HERE, '..', 'data', 'species.json')))}
    alias = {x: r[0] for r in cat.values() for x in r[1] if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower()}
    lcp = json.load(open(os.path.join(HERE, '..', 'data', 'lc_prefs.json')))['species']
    finds = {}
    for o in load('inat_ro_fungi_2020_2026.json'):
        anc = o[9].split('.')
        if o[3] < D0.isoformat() or len(anc) < 6 or anc[5] not in MACRO or o[2] not in ('species', 'subspecies', 'variety', 'form'):
            continue
        k = pidx.get((round(o[4], 3), round(o[5], 3)))
        if k is None or not feat[k][3]:
            continue
        nm = alias.get(' '.join(o[1].split()[:2]), ' '.join(o[1].split()[:2]))
        finds.setdefault(nm, []).append(k)
    rows = []
    for s, sp in G['sp'].items():
        g = np.array(sp['h'])[land]
        if not len(g) or g.max() <= 0:
            rows.append(dict(sp=s, n=len(finds.get(s, [])), pct=None, high=0.0, rc=None, flags=['empty map'])); continue
        ks = finds.get(s, [])
        ph = np.array(hab['sp'][s]['h'])[ks] if ks and s in hab['sp'] else np.array([])
        pct = float(np.median([(g < v).mean() for v in ph])) if len(ph) else None
        high = float((g >= 0.68).mean())
        rc = rankcorr(np.array(GN['sp'][s]['h'])[land], g) if GN and s in GN['sp'] and s in lcp else None
        fl = []
        if pct is not None and len(ks) >= 3 and pct < 0.6:
            fl.append(f'finds sit low on the map ({pct:.2f})')
        if high > 0.4:
            fl.append(f'paints {high:.0%} of Romania High')
        if high == 0 and len(ks) >= 3:
            fl.append('no High anywhere despite finds')
        if rc is not None and rc < 0:
            fl.append(f'rules and learned model disagree (r = {rc:.2f})')
        rows.append(dict(sp=s, n=len(ks), pct=pct, high=high, rc=rc, flags=fl, model=(lcp.get(s) or {}).get('src', 'ro' if s in lcp else 'rules')))
    rows.sort(key=lambda r: (-len(r['flags']), r['sp']))
    nflag = sum(1 for r in rows if r['flags'])
    L = ['# Hribar per-species audit', '', f'{len(rows)} species; {nflag} flagged. Percentile = where the species\' own Romanian finds fall on its habitat map '
         '(0.5 = no better than chance, 1 = always in the best cells). High = share of Romanian land at habitat >= 0.68.', '',
         '| Species | Model | RO finds | Finds percentile | High share | Rules vs learned | Flags |', '| --- | --- | --- | --- | --- | --- | --- |']
    for r in rows:
        L.append(f"| *{r['sp']}* {names.get(r['sp'], '')} | {r.get('model', '')} | {r['n']} | {'' if r['pct'] is None else f'{r[\"pct\"]:.2f}'} | "
                 f"{r['high']:.0%} | {'' if r['rc'] is None else f'{r[\"rc\"]:.2f}'} | {'; '.join(r['flags'])} |")
    open(a.out, 'w').write('\n'.join(L) + '\n')
    print(f'{nflag} of {len(rows)} species flagged -> {a.out}')
    # contact sheets
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    order = sorted(G['sp'])
    per = 48
    for page in range(0, len(order), per):
        sub = order[page:page + per]
        fig, axs = plt.subplots(6, 8, figsize=(24, 15))
        for ax, s in zip(axs.flat, sub):
            g = np.array(G['sp'][s]['h']); m = land
            ax.scatter(gpts[m, 0], gpts[m, 1], c=g[m], s=3, cmap='YlGn', vmin=0, vmax=0.9, marker='s', linewidths=0)
            ks = finds.get(s, [])
            if ks:
                fp = np.array([pts[k] for k in ks]); ax.scatter(fp[:, 0], fp[:, 1], s=6, c='#C2185B', marker='o', linewidths=0)
            r = next(x for x in rows if x['sp'] == s)
            ax.set_title(('⚑ ' if r['flags'] else '') + s, fontsize=8, color='#B00020' if r['flags'] else '#222')
            ax.set_xticks([]); ax.set_yticks([]); ax.set_aspect(1.4)
        for ax in list(axs.flat)[len(sub):]:
            ax.axis('off')
        fig.suptitle('Habitat suitability per species (green), Romanian finds (pink); flagged species in red', fontsize=12)
        fig.tight_layout(); fig.savefig(os.path.join(HERE, f'audit_sheet_{page // per + 1}.png'), dpi=70); plt.close(fig)
    print('contact sheets written')


if __name__ == '__main__':
    main()
