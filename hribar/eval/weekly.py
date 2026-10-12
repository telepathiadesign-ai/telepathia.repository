#!/usr/bin/env python3
"""Sprint A5: weekly retrain and score report. Run by .github/workflows/hribar-weekly.yml after the data refresh and the
headless export of habitat_at_points.json. In forecast space (WX_FILE=hist_forecast.json) when that file exists.

1. Hold-out score: land-cover preferences fitted on Romanian finds before (today − 365 d), full forecast scored on the
   finds of the last 365 days -> data/reliability.json (good ≥ 0.75, useful ≥ 0.65, weak below; 15+ finds).
2. Ship: land-cover preferences refitted on all Romanian finds, plus climate-niche models (finds across Europe) for the rest.
3. eval/REPORT.md with the summary and the per-species table.
"""
import datetime as dt, json, os, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
env = dict(os.environ, TRIG='frost', RECENT_KM='60', RECENT_D='14', RECENT_B='2')
if os.path.exists(os.path.join(HERE, 'data', 'hist_forecast.json')):
    env['WX_FILE'] = 'hist_forecast.json'
run = lambda *cmd, **kw: subprocess.run([sys.executable] + list(cmd), cwd=ROOT, env={**env, **kw}, check=True)
today = dt.date.today()
years = [str(y) for y in range(2024, today.year + 1)]
timing = os.path.join(ROOT, 'data', 'timing.json')
extra = ['--params', timing] if os.path.exists(timing) else []

# cross-fitted hold-out: each year of finds (from 2025 on) is scored with habitat preferences fitted on the other years
rows = {}
for y in years:
    tmp = os.path.join(HERE, 'data', f'lc_prefs_holdout_{y}.json'); res = os.path.join(HERE, 'data', f'weekly_holdout_{y}.json')
    run('eval/fit_landcover.py', '--train', ','.join(v for v in years if v != y), '--out', tmp)
    run('eval/fit_niche.py', '--wx', '1', '--merge', tmp, '--out', tmp)
    run('eval/backtest.py', '--water', 'lag', '--scale', '25', '--wr', '0.7', '--years', y, '--json', res, *extra, LC_PREFS=tmp, MIN_N='5')
    for r in json.load(open(res))['rows']:
        if r.get('auc_full') is not None and r['n_wx'] >= 5:
            rows.setdefault(r['species'], []).append(r)
level = lambda a: 'good' if a >= 0.75 else 'useful' if a >= 0.65 else 'weak'
wmean = lambda rs, k: sum(r[k] * r['n_wx'] for r in rs) / sum(r['n_wx'] for r in rs)
R = {'rows': [], 'records': 0}
for s_, rs in rows.items():
    n = sum(r['n_wx'] for r in rs)
    if n < 15:
        continue
    R['rows'].append({'species': s_, 'n_wx': n, **{k: round(wmean(rs, k), 3) for k in ('auc_hab', 'auc_season', 'auc_hab_season', 'auc_weather', 'auc_full')}})
rel = {r['species']: {'auc': r['auc_full'], 'n': r['n_wx'], 'level': level(r['auc_full'])} for r in R['rows']}
import statistics
R['summary'] = {k: {'median': round(statistics.median(r[k] for r in R['rows']), 3),
                    'weighted': round(sum(r[k] * r['n_wx'] for r in R['rows']) / sum(r['n_wx'] for r in R['rows']), 3)} for k in ('auc_hab', 'auc_season', 'auc_hab_season', 'auc_weather', 'auc_full')}
cutoff = '2023-12-01'
json.dump({'source': f'eval/weekly.py: full-forecast AUC on iNaturalist finds in Romania {cutoff}..{today} (target-group background), each year scored with '
                     f'habitat preferences fitted on the other years; weather: {env.get("WX_FILE", "era5_land.json")}; species with 15+ finds',
           'updated': today.isoformat(), 'species': rel}, open(os.path.join(ROOT, 'data', 'reliability.json'), 'w'), indent=1)

run('eval/fit_season.py', '--before', '2099-01-01', '--out', 'data/season.json')
run('eval/fit_landcover.py', '--train', ','.join(years), '--out', 'data/lc_prefs.json')
run('eval/fit_niche.py', '--wx', '1', '--merge', 'data/lc_prefs.json', '--out', 'data/lc_prefs.json')
LC = json.load(open(os.path.join(ROOT, 'data', 'lc_prefs.json')))['species']

S = R['summary']; counts = {k: sum(1 for v in rel.values() if v['level'] == k) for k in ('good', 'useful', 'weak')}
lines = [f'# Hribar weekly report — {today}', '',
         f'Finds scored: iNaturalist records in Romania, {cutoff} to {today}; {len(rel)} species with 15+ finds. '
         f'Weather: {env.get("WX_FILE", "era5_land.json")}. Each year is scored with habitat preferences fitted on the other years (cross-fitted hold-out).', '',
         '| Term | Median AUC | Weighted AUC |', '| --- | --- | --- |']
for k, lab in (('auc_hab', 'Habitat'), ('auc_season', 'Season'), ('auc_hab_season', 'Habitat × season'), ('auc_weather', 'Weather'), ('auc_full', 'Full forecast')):
    if S.get(k):
        lines.append(f'| {lab} | {S[k]["median"]:.3f} | {S[k]["weighted"]:.3f} |')
lines += ['', f'Reliability: {counts["good"]} good, {counts["useful"]} useful, {counts["weak"]} weak. '
          f'Learned habitat shipped for {len(LC)} species ({sum(1 for v in LC.values() if v.get("src") != "neighbours")} Romanian models, '
          f'{sum(1 for v in LC.values() if v.get("src") in ("neighbours", "niche"))} climate-niche models from finds across Europe).', '',
          '| Species | Finds | Habitat | Weather | Full | Level |', '| --- | --- | --- | --- | --- | --- |']
for r in sorted(R['rows'], key=lambda r: -(r.get('auc_full') or 0)):
    if r['species'] in rel:
        lines.append(f"| {r['species']} | {r['n_wx']} | {r['auc_hab']:.2f} | {r['auc_weather']:.2f} | {r['auc_full']:.2f} | {rel[r['species']]['level']} |")
open(os.path.join(HERE, 'REPORT.md'), 'w').write('\n'.join(lines) + '\n')
print('\n'.join(lines[:12]))
