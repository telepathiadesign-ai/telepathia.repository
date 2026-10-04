#!/usr/bin/env python3
"""Recent iNaturalist fungus reports in Romania -> data/recent_finds.json for the app's "reported nearby" boost.

Backtest (eval/backtest.py with RECENT_KM=60 RECENT_D=14 RECENT_B=2): full-model AUC +0.014 (95% CI +0.010..+0.018),
49 species better, 10 worse. Keeps the last 21 days, species rank only, catalogue species only (accepted names + aliases).

    python3 scripts/fetch_recent.py [--days 21] [--out data/recent_finds.json]
"""
import argparse, datetime as dt, json, os, sys, time
import requests

ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=21); ap.add_argument('--out', default='data/recent_finds.json')
a = ap.parse_args()
here = os.path.dirname(os.path.abspath(__file__))
cat = json.load(open(os.path.join(here, '..', 'data', 'catalog.json')))
alias = {}
for r in cat:
    alias[r[0]] = r[0]
    for x in r[1]:
        if ' ' in x and x[:1].isupper() and x.split()[0][1:].islower():
            alias[x] = r[0]
d1 = (dt.date.today() - dt.timedelta(days=a.days)).isoformat()
rows, id_above = [], 0
for page in range(60):
    url = ('https://api.inaturalist.org/v1/observations?place_id=8858&iconic_taxa=Fungi&geo=true&per_page=200&order_by=id&order=asc'
           f'&d1={d1}&id_above={id_above}')
    for attempt in range(5):
        try:
            r = requests.get(url, timeout=60, headers={'User-Agent': 'hribar-forecast (academic research)'})
            if r.status_code == 200:
                break
            print('HTTP', r.status_code, file=sys.stderr)
        except requests.RequestException as e:
            print(e, file=sys.stderr)
        time.sleep(10)
    else:
        sys.exit('iNaturalist unreachable')
    res = r.json()['results']
    if not res:
        break
    for o in res:
        id_above = max(id_above, o['id'])
        t = o.get('taxon') or {}
        if t.get('rank') not in ('species', 'subspecies', 'variety', 'form') or not o.get('geojson') or not o.get('observed_on'):
            continue
        nm = alias.get(' '.join(t['name'].split()[:2]))
        if not nm:
            continue
        lon, lat = o['geojson']['coordinates']
        rows.append([nm, round(lon, 3), round(lat, 3), o['observed_on'], o.get('quality_grade', '')[:1]])
    if len(res) < 200:
        break
    time.sleep(1.2)
json.dump({'issued': dt.datetime.utcnow().replace(microsecond=0).isoformat() + 'Z', 'source': 'iNaturalist (place: Romania), CC licences per observation',
           'days': a.days, 'finds': rows}, open(a.out, 'w'), separators=(',', ':'), ensure_ascii=False)
print(f'wrote {a.out}: {len(rows)} catalogue-species reports since {d1}', file=sys.stderr)
