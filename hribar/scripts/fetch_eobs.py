#!/usr/bin/env python3
"""Observed daily rain (E-OBS, gridded from rain gauges, 0.1°, ECA&D / Copernicus, no login) at the 40 evaluation nodes
-> eval/data/eobs_rain.json {node: {t0, P: [mm/day ...]}}. Used by the backtest (RAIN_FILE) to test whether observed rain
beats modelled rain as the timing driver. Each node's value is the mean over the 0.5° box around it, matching the
ERA5 node scale. Runs on GitHub Actions.
"""
import datetime as dt, json, os, re, sys, urllib.request
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'eval', 'data', 'eobs_rain.json')
BUCKET = 'https://knmi-ecad-assets-prd.s3.amazonaws.com'
PREFIX = 'ensembles/data/Grid_0.1deg_reg_ensemble/'
T0 = dt.date(2023, 12, 1)
log = lambda *a, **k: print(*a, file=sys.stderr, flush=True, **k)


def listing():
    keys, token = [], None
    while True:
        u = f'{BUCKET}/?list-type=2&prefix={PREFIX}' + (f'&continuation-token={urllib.request.quote(token)}' if token else '')
        x = urllib.request.urlopen(u, timeout=60).read().decode()
        keys += re.findall(r'<Key>([^<]+)</Key>', x)
        m = re.search(r'<NextContinuationToken>([^<]+)</NextContinuationToken>', x)
        if not m:
            return keys
        token = m.group(1)


def main():
    import xarray as xr
    def exists(k):
        try:
            urllib.request.urlopen(urllib.request.Request(f'{BUCKET}/{k}', method='HEAD'), timeout=30); return True
        except Exception:
            return False
    cands = [f'{PREFIX}rr_ens_mean_0.1deg_reg_{per}_v{v}.0e.nc' for v in (33, 32, 31, 30) for per in ('2011-2025', '2011-2024')]
    cands += [f'{PREFIX}rr_ens_mean_0.1deg_reg_v{v}.0e.nc' for v in (33, 32, 31, 30)]
    found = [k for k in cands if exists(k)]
    log('E-OBS candidates found:', *found, sep='\n  ')
    if not found:
        sys.exit('no E-OBS rain file found at the known names')
    picks = found[:1]
    nodes = json.load(open(os.path.join(ROOT, 'eval', 'data', 'era5_nodes.json')))
    series = {f'{lon:g},{lat:g}': {} for lon, lat in nodes}
    for k in picks:
        fn = '/tmp/' + os.path.basename(k)
        log('download', k)
        urllib.request.urlretrieve(f'{BUCKET}/{k}', fn)
        ds = xr.open_dataset(fn)
        ds = ds.sel(time=slice(T0.isoformat(), None), longitude=slice(12, 32), latitude=slice(40, 50))
        if ds.sizes.get('time', 0) == 0:
            log('  no days after', T0); os.remove(fn); continue
        rr = ds['rr'].load()
        times = [str(t)[:10] for t in rr['time'].values]
        for lon, lat in nodes:
            box = rr.sel(longitude=slice(lon - 0.25, lon + 0.25), latitude=slice(lat - 0.25, lat + 0.25)).mean(dim=('longitude', 'latitude'), skipna=True).values
            for t, v in zip(times, box):
                series[f'{lon:g},{lat:g}'][t] = None if np.isnan(v) else round(float(v), 2)
        log('  days', times[0], '..', times[-1]); ds.close(); os.remove(fn)
    out = {}
    for key, s in series.items():
        if not s:
            continue
        end = max(s); n = (dt.date.fromisoformat(end) - T0).days + 1
        out[key] = {'t0': T0.isoformat(), 'end': end, 'P': [s.get((T0 + dt.timedelta(days=i)).isoformat()) for i in range(n)]}
    out['_source'] = 'E-OBS daily precipitation (rr, ensemble mean, 0.1°), ECA&D / Copernicus C3S; files: ' + ', '.join(os.path.basename(k) for k in picks)
    json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    log('wrote', OUT, len(out) - 1, 'nodes, through', max(v['end'] for k, v in out.items() if k != '_source'))


if __name__ == '__main__':
    main()
