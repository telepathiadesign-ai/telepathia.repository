#!/usr/bin/env python3
"""Merge the literature research (research/batch*_traits.json) into data/traits.json, the per-species
overrides the app reads. Months are only taken from the literature when GBIF records from Central-East
Europe (research/gbif_months_2026-10-02.json) support them at least as well as the catalogue."""
import json, glob, os
HERE = os.path.dirname(os.path.abspath(__file__))
rows = []
for f in sorted(glob.glob(os.path.join(HERE, 'batch*_traits.json'))):
    rows += json.load(open(f))
cat = {r[0]: r for r in json.load(open(os.path.join(HERE, '..', 'data', 'catalog.json')))}
alias = {}
for r in cat.values():
    for x in r[1]:
        alias[x] = r[0]
gb = {}
for g in json.load(open(os.path.join(HERE, 'gbif_months_2026-10-02.json'))):
    gb[alias.get(g['nm'], g['nm'])] = g
W = {'primary': 1.0, 'secondary': 0.7, 'occasional': 0.35}
OPEN = {'grassland_pasture', 'meadow_unimproved', 'park_garden_lawn', 'steppe_dry_grassland', 'orchard', 'urban_ruderal'}
FOREST = {'broadleaf_forest', 'conifer_forest', 'mixed_forest', 'plantation', 'bog_wet', 'alpine_subalpine'}
EDGE = {'forest_edge_clearing', 'riparian_floodplain'}
PH = {'acid': 5.0, 'neutral': 6.5, 'calcareous': 7.3}


def season_score(months, share):
    """GBIF share of records inside the season, minus a small penalty per month so a wider season must earn it."""
    inside = sum(share[i] for i in range(12) if months[i] == '1')
    return inside - 0.03 * months.count('1')


out, log = {}, []
for r in rows:
    s = r['latin']
    if s not in cat:
        log.append(f'{s}: not in catalogue, skipped'); continue
    src = len(r.get('sources') or [])
    trusted = src >= 2 and r.get('confidence') in ('medium', 'high')
    t = {'conf': r.get('confidence'), 'src': src, 'urls': (r.get('sources') or [])[:3]}
    if r.get('soil_ph'):
        t['soil'] = r['soil_ph']
    if r.get('hosts') and trusted:
        t['hosts'] = {h['genus']: W.get(h.get('strength'), 0.5) for h in r['hosts'] if h.get('genus')}
    sub = r.get('substrate')
    if sub:
        t['substrate'] = sub
    hab = set(r.get('habitats') or [])
    if hab and trusted:
        o, f, e = bool(hab & OPEN), bool(hab & FOREST), bool(hab & EDGE)
        code = ('W' if f else '') + ('G' if o else '') + ('D' if sub and sub.startswith('wood') else '')
        if e and not o:
            code = code.replace('W', 'WG') if 'W' in code else 'WG'
        if not f and not o and e:
            code = 'WG'
        t['hab'] = code or cat[s][17]
        t['habitats'] = sorted(hab)
    if r.get('soil_ph') in PH and trusted:
        t['ph'] = PH[r['soil_ph']]
    elif r.get('soil_ph') == 'indifferent' and trusted:
        t['ph'] = None
    m = r.get('months')
    g = gb.get(s)
    if m and len(m) == 12 and g and g['n'] >= 50:
        a, b = season_score(m, g['share']), season_score(cat[s][8], g['share'])
        if a > b + 0.01:
            t['months_lit'] = m; log.append(f'{s}: months {cat[s][8]} -> {m} (GBIF score {b:.2f} -> {a:.2f})')
    elif m and len(m) == 12 and not g:
        log.append(f'{s}: literature months {m} not checked (no GBIF records)')
    out[s] = t
json.dump({'source': 'Literature review 3 Oct 2026 (research/batch*_traits.json: de/en Wikipedia, first-nature, tintling, fungiversum, 123pilzsuche, pilzmuseum, ciupercar.ro and others); literature months kept as months_lit only: they lowered the season backtest (0.668 -> 0.662)',
           'species': out}, open(os.path.join(HERE, '..', 'data', 'traits.json'), 'w'), ensure_ascii=False, separators=(',', ':'))
open(os.path.join(HERE, 'traits_merge_log.md'), 'w').write('# Traits merge log\n\n' + '\n'.join('- ' + l for l in log) + '\n')
print(len(out), 'species;', sum('hosts' in v for v in out.values()), 'hosts;', sum('ph' in v for v in out.values()), 'ph;', sum('hab' in v for v in out.values()), 'hab;', sum('months' in v for v in out.values()), 'months changed')
