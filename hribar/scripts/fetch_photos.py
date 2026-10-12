#!/usr/bin/env python3
"""One openly licensed iNaturalist photo per catalogue species -> data/photos/<slug>.jpg (small, ~240 px) and
data/thumbs.json {latin: data-URI of the 75 px square, credit, license, page}. Only CC0 / CC BY / CC BY-SA / CC BY-NC /
CC BY-NC-SA photos; the photographer's attribution is kept and shown in the app. Prefers the taxon's default photo."""
import base64, json, os, re, sys, time, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..')
OK = {'cc0', 'cc-by', 'cc-by-sa', 'cc-by-nc', 'cc-by-nc-sa'}
UA = {'User-Agent': 'hribar-forecast (academic research)'}
log = lambda *a: print(*a, file=sys.stderr, flush=True)
slug = lambda s: re.sub(r'[^a-z0-9]+', '-', s.lower()).strip('-')


def get(url, raw=False):
    for k in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                b = r.read(); return b if raw else json.loads(b)
        except Exception as e:
            log('retry', k, url[:90], str(e)[:60]); time.sleep(5 * (k + 1))
    return None


species = [r[0] for r in json.load(open(os.path.join(ROOT, 'data', 'species.json')))]
os.makedirs(os.path.join(ROOT, 'data', 'photos'), exist_ok=True)
outp = os.path.join(ROOT, 'data', 'thumbs.json')
out = json.load(open(outp)) if os.path.exists(outp) else {}
for sp in species:
    if sp in out:
        continue
    d = get('https://api.inaturalist.org/v1/taxa?' + urllib.parse.urlencode({'q': sp, 'is_active': 'true', 'per_page': 10}))
    time.sleep(1.1)
    t = next((x for x in (d or {}).get('results', []) if x.get('name', '').lower() == sp.lower()), None)
    if not t:
        log('no taxon', sp); continue
    full = get(f"https://api.inaturalist.org/v1/taxa/{t['id']}"); time.sleep(1.1)
    photos = [tp['photo'] for tp in ((full or {}).get('results') or [{}])[0].get('taxon_photos', [])]
    p = next((ph for ph in photos if (ph.get('license_code') or '').lower() in OK), None)
    if not p:
        log('no open photo', sp); continue
    sq = p.get('square_url') or p['url']; small = re.sub(r'/square\.', '/small.', sq)
    img_sq = get(sq, raw=True); img_sm = get(small, raw=True)
    if not img_sq or not img_sm:
        log('download failed', sp); continue
    open(os.path.join(ROOT, 'data', 'photos', slug(sp) + '.jpg'), 'wb').write(img_sm)
    out[sp] = {'thumb': 'data:image/jpeg;base64,' + base64.b64encode(img_sq).decode(), 'file': 'photos/' + slug(sp) + '.jpg',
               'credit': p.get('attribution', ''), 'license': p['license_code'].upper(), 'page': f"https://www.inaturalist.org/taxa/{t['id']}"}
    log('ok', sp, p['license_code'])
    json.dump(out, open(outp, 'w'), separators=(',', ':'), ensure_ascii=False)
log('photos', len(out), 'of', len(species))
