#!/usr/bin/env python3
"""Tree-species probability maps -> data/trees.json.

Source: Bonannella et al. 2022, "Forest tree species distribution for Europe 2000-2020" (PeerJ 10:e13728),
30 m realized-distribution probability per species, Cloud Optimized GeoTIFFs on Zenodo, EPSG:3035, CC BY 4.0.
For each species we take the most recent realized ("anv") probability file, read the Romania window at a
reduced overview (~240 m), reproject to the app's 0.01° grid (lo0 20.2, la0 43.6, 960 x 470, south-first rows)
and store the mean probability in percent. Runs on GitHub Actions (open internet).
"""
import base64, json, re, sys, time, urllib.parse, urllib.request, zlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import reproject, transform_bounds
from rasterio.transform import from_origin
from rasterio.windows import from_bounds

LO0, LA0, ST, W, H = 20.2, 43.6, 0.01, 960, 470
SPECIES = ['abies.alba', 'castanea.sativa', 'corylus.avellana', 'fagus.sylvatica', 'picea.abies', 'pinus.nigra',
           'pinus.sylvestris', 'prunus.avium', 'quercus.cerris', 'quercus.robur', 'salix.caprea']
READ_RES = 240.0  # metres, source read resolution before reprojection


def get(url):
    for k in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'hribar-research'}), timeout=60) as r:
                return json.load(r)
        except Exception as e:
            print('retry', url, e, file=sys.stderr); time.sleep(5 * (k + 1))
    raise RuntimeError(url)


KNOWN = {
    'abies.alba': (6953790, '2018..2020'),
    'castanea.sativa': (6951628, '2018..2020'),
    'corylus.avellana': (6951687, '2002..2006'),
    'fagus.sylvatica': (6956944, '2018..2020'),
    'picea.abies': (6961187, '2018..2020'),
    'pinus.nigra': (6964167, '2018..2020'),
    'pinus.sylvestris': (6966804, '2018..2020'),
    'prunus.avium': (6966847, '2018..2020'),
    'quercus.cerris': (6967119, '2018..2020'),
    'quercus.robur': (6967309, '2018..2020'),
    'salix.caprea': (6967538, '2018..2020'),
}


def find_records():
    try:
        found = _search()
    except Exception as e:
        print('zenodo search failed, using known record ids:', e, file=sys.stderr); found = {}
    for sp, (rid, yrs) in KNOWN.items():
        if sp not in found:
            key = f'veg_{sp}_anv.eml_p_30m_0..0cm_{yrs}_eumap_epsg3035_v0.3.tif'
            found[sp] = (int(yrs[-4:]), key, f'https://zenodo.org/records/{rid}/files/{key}')
    return found


def _search():
    q = urllib.parse.quote('"realized distribution at 30m"')
    found = {}
    for page in (1, 2, 3):
        d = get(f'https://zenodo.org/api/records?q={q}&size=25&page={page}&all_versions=false')
        hits = d.get('hits', {}).get('hits', [])
        for h in hits:
            for f in h.get('files', []):
                m = re.search(r'veg_([a-z]+\.[a-z]+)_anv\.eml_p_30m_.*?_(\d{4})\.\.(\d{4})_', f['key'])
                if not m or m.group(1) not in SPECIES or not f['key'].endswith('.tif'):
                    continue
                sp, y1 = m.group(1), int(m.group(3))
                url = f"https://zenodo.org/records/{h['id']}/files/{f['key']}"
                if sp not in found or y1 > found[sp][0]:
                    found[sp] = (y1, f['key'], url)
        if len(hits) < 25:
            break
    return found


def read_species(url):
    dst = np.full((H, W), np.nan, np.float32)
    dst_tf = from_origin(LO0, LA0 + H * ST, ST, ST)
    with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif',
                      GDAL_HTTP_MAX_RETRY='4', GDAL_HTTP_RETRY_DELAY='3'):
        with rasterio.open('/vsicurl/' + url if not url.startswith('/vsi') else url) as src:
            l, b, r, t = transform_bounds('EPSG:4326', src.crs, LO0, LA0, LO0 + W * ST, LA0 + H * ST, densify_pts=41)
            win = from_bounds(l, b, r, t, src.transform)
            res = abs(src.transform.a)
            shape = (max(1, int(win.height * res / READ_RES)), max(1, int(win.width * res / READ_RES)))
            a = src.read(1, window=win, out_shape=shape, resampling=Resampling.average, boundless=True, fill_value=255).astype(np.float32)
            nod = src.nodata
            tf = rasterio.windows.transform(win, src.transform) * rasterio.Affine.scale(win.width / shape[1], win.height / shape[0])
            if nod is not None:
                a[a == nod] = np.nan
            a[a > 100] = np.nan
            reproject(a, dst, src_transform=tf, src_crs=src.crs, src_nodata=np.nan, dst_transform=dst_tf, dst_crs='EPSG:4326',
                      dst_nodata=np.nan, resampling=Resampling.average)
    return dst[::-1]  # north-first -> south-first rows


def enc(g):
    v = np.where(np.isfinite(g), np.round(g), -1).astype(np.int16)
    d = np.concatenate([v[:, :1], np.diff(v, axis=1)], axis=1).astype('<i2')
    return base64.b64encode(zlib.compress(d.tobytes(), 9)).decode()



def main():
    recs = find_records()
    print('records found:', {k: v[1] for k, v in recs.items()}, file=sys.stderr)
    missing = [s for s in SPECIES if s not in recs]
    if missing:
        print('missing species:', missing, file=sys.stderr)
    out = {'source': 'Bonannella et al. 2022, realized distribution probability (30 m, EPSG:3035), mean % per 0.01° cell, CC BY 4.0',
           'species': {}}
    for sp, (y1, key, url) in sorted(recs.items()):
        try:
            g = read_species(url)
        except Exception as e:
            print('fail', sp, e, file=sys.stderr); continue
        ok = np.isfinite(g)
        print('ok', sp, key, 'cells', int(ok.sum()), 'mean', round(float(np.nanmean(g)), 1), file=sys.stderr)
        out['species'][sp] = {'file': key, 'lo0': LO0, 'la0': LA0, 'st': ST, 'w': W, 'h': H, 'b': enc(g)}
    if not out['species']:
        sys.exit('no species read')
    json.dump(out, open('data/trees.json', 'w'), separators=(',', ':'))
    print('wrote', len(out['species']), 'species', file=sys.stderr)


if __name__ == '__main__':
    main()
