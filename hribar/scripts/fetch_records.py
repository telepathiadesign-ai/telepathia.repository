#!/usr/bin/env python3
"""More finds for training: GBIF occurrences (includes iNaturalist research-grade) of every catalogue species in
Romania's neighbours and the wider Carpathian region, 2018 onwards. Runs nightly on GitHub Actions with a time budget
and resumes where it stopped, until every species x country is done.

Output: eval/data/records_cee.json.gz  -> {"rows": [[species, date, lon, lat, country, uncertainty_m, source], ...]}
        eval/data/records_cee_state.json -> progress (done keys, GBIF taxon keys)
source: 'i' = iNaturalist, 'g' = other GBIF dataset. Duplicates (same species, date, ~100 m) are dropped.
"""
import gzip, json, os, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'eval', 'data', 'records_cee.json.gz')
STATE = os.path.join(ROOT, 'eval', 'data', 'records_cee_state.json')
COUNTRIES = ['HU', 'SK', 'PL', 'CZ', 'UA', 'MD', 'BG', 'RS', 'AT', 'SI', 'HR']
INAT = '50c9509d-22c7-4a22-a47d-8c48425ef4a7'
BUDGET = float(os.environ.get('BUDGET_MIN', '50')) * 60
MAX_PER = 20000  # per species x country cap
T0 = time.time()


def get(url):
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'hribar-research (academic)'}), timeout=90) as r:
                return json.load(r)
        except Exception as e:
            print('retry', k, e, file=sys.stderr); time.sleep(4 * (k + 1))
    raise RuntimeError(url)


def taxon_key(name):
    d = get('https://api.gbif.org/v1/species/match?' + urllib.parse.urlencode({'name': name, 'kingdom': 'Fungi', 'strict': 'true'}))
    if d.get('matchType') in ('EXACT', 'FUZZY') and d.get('rank') in ('SPECIES', 'SUBSPECIES', 'VARIETY', 'FORM'):
        return d.get('acceptedUsageKey') or d.get('usageKey')
    return None


def main():
    species = [r[0] for r in json.load(open(os.path.join(ROOT, 'data', 'species.json')))]
    st = json.load(open(STATE)) if os.path.exists(STATE) else {'keys': {}, 'done': [], 'counts': {}}
    rows = json.load(gzip.open(OUT, 'rt'))['rows'] if os.path.exists(OUT) else []
    seen = {(r[0], r[1], round(r[2], 3), round(r[3], 3)) for r in rows}
    done = set(st['done'])
    added = 0
    for sp in species:
        if sp not in st['keys']:
            st['keys'][sp] = taxon_key(sp)
        tk = st['keys'][sp]
        for cc in COUNTRIES:
            key = f'{sp}|{cc}'
            if key in done:
                continue
            if time.time() - T0 > BUDGET:
                break
            n = 0
            if tk:
                off = 0
                while off < MAX_PER:
                    q = {'taxonKey': tk, 'country': cc, 'year': '2018,2030', 'hasCoordinate': 'true', 'hasGeospatialIssue': 'false',
                         'occurrenceStatus': 'PRESENT', 'limit': 300, 'offset': off}
                    d = get('https://api.gbif.org/v1/occurrence/search?' + urllib.parse.urlencode(q))
                    for o in d.get('results', []):
                        date = (o.get('eventDate') or '')[:10]
                        if len(date) != 10 or o.get('decimalLongitude') is None:
                            continue
                        unc = o.get('coordinateUncertaintyInMeters')
                        r = [sp, date, round(o['decimalLongitude'], 4), round(o['decimalLatitude'], 4), cc,
                             None if unc is None else int(unc), 'i' if o.get('datasetKey') == INAT else 'g']
                        k2 = (r[0], r[1], round(r[2], 3), round(r[3], 3))
                        if k2 in seen:
                            continue
                        seen.add(k2); rows.append(r); n += 1
                    if d.get('endOfRecords', True):
                        break
                    off += 300
            done.add(key); st['counts'][key] = n; added += n
        else:
            continue
        break
    st['done'] = sorted(done)
    total = len(species) * len(COUNTRIES)
    st['progress'] = f'{len(done)}/{total} species x country'
    st['updated'] = time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with gzip.open(OUT, 'wt') as f:
        json.dump({'source': 'GBIF occurrence API (includes iNaturalist research grade), catalogue species, 2018+', 'countries': COUNTRIES,
                   'fields': ['species', 'date', 'lon', 'lat', 'country', 'uncertainty_m', 'source'], 'rows': rows}, f, separators=(',', ':'))
    json.dump(st, open(STATE, 'w'), separators=(',', ':'))
    print(f"added {added}, total rows {len(rows)}, progress {st['progress']}, no GBIF key: "
          f"{sum(1 for v in st['keys'].values() if not v)}", file=sys.stderr)


if __name__ == '__main__':
    main()
