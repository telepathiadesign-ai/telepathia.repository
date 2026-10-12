#!/usr/bin/env python3
"""Append new iNaturalist fungus observations in Romania to eval/data/inat_ro_fungi_2020_2026.json (the training and
evaluation archive). Row format, as in the archive:
    [id, taxon name, rank, observed_on, lon, lat, positional_accuracy_m, quality_grade[0], obscured 0/1, ancestry 'id.id...', user_id]
Fetches everything observed in the last --days (default 45) that is not yet in the file; observations are often added or
identified weeks after the find, so the window overlaps. Runs weekly on GitHub Actions.
"""
import argparse, datetime as dt, json, os, sys, time
import requests

HERE = os.path.dirname(os.path.abspath(__file__))
PATH = os.path.join(HERE, '..', 'eval', 'data', 'inat_ro_fungi_2020_2026.json')
ap = argparse.ArgumentParser(); ap.add_argument('--days', type=int, default=45)
a = ap.parse_args()
rows = json.load(open(PATH))
ids = {r[0] for r in rows}
d1 = (dt.date.today() - dt.timedelta(days=a.days)).isoformat()
id_above, added, updated = 0, 0, 0
byid = {r[0]: k for k, r in enumerate(rows)}
for page in range(200):
    url = ('https://api.inaturalist.org/v1/observations?place_id=8858&iconic_taxa=Fungi&geo=true&per_page=200&order_by=id&order=asc'
           f'&d1={d1}&id_above={id_above}')
    for attempt in range(6):
        try:
            r = requests.get(url, timeout=60, headers={'User-Agent': 'hribar-forecast (academic research)'})
            if r.status_code == 200:
                break
            print('HTTP', r.status_code, file=sys.stderr)
        except requests.RequestException as e:
            print(e, file=sys.stderr)
        time.sleep(15)
    else:
        sys.exit('iNaturalist unreachable')
    res = r.json()['results']
    if not res:
        break
    for o in res:
        id_above = max(id_above, o['id'])
        t = o.get('taxon') or {}
        if not t or not o.get('geojson') or not o.get('observed_on'):
            continue
        anc = [str(x) for x in (t.get('ancestor_ids') or []) if x != t.get('id')]
        lon, lat = o['geojson']['coordinates']
        row = [o['id'], t.get('name', ''), t.get('rank', ''), o['observed_on'], round(lon, 4), round(lat, 4), o.get('positional_accuracy'),
               (o.get('quality_grade') or '')[:1], 1 if o.get('obscured') else 0, '.'.join(anc), (o.get('user') or {}).get('id')]
        if o['id'] in byid:
            if rows[byid[o['id']]][1:3] != row[1:3] or rows[byid[o['id']]][7] != row[7]:
                rows[byid[o['id']]] = row; updated += 1   # re-identified or promoted to research grade
        else:
            byid[o['id']] = len(rows); rows.append(row); added += 1
    if len(res) < 200:
        break
    time.sleep(1.2)
rows.sort(key=lambda r: r[0])
json.dump(rows, open(PATH, 'w'), separators=(',', ':'), ensure_ascii=False)
print(f'iNat RO archive: +{added} new, {updated} updated, total {len(rows)}, latest {max(r[3] for r in rows)}', file=sys.stderr)
