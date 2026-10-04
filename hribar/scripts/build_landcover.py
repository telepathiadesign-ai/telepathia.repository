#!/usr/bin/env python3
"""ESA WorldCover 2021 (10 m) -> data/landcover.json: per 0.01° cell over Romania, the share of tree cover,
grassland+shrubland, cropland and built-up land. Reads the public cloud-optimised GeoTIFFs at a reduced overview
(~80 m) so only a few hundred MB are transferred. Runs on GitHub Actions (open internet).

Grid matches data/terrain.json wetness: lo0 20.2, la0 43.6, st 0.01, 960 x 470, south-first rows.
Licence: ESA WorldCover © ESA WorldCover project 2021, contains modified Copernicus Sentinel data, CC BY 4.0.
"""
import base64, json, math, sys, zlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.windows import from_bounds

LO0, LA0, ST, W, H = 20.2, 43.6, 0.01, 960, 470
URL = 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif'
SUB = 8  # samples per 0.01° cell edge -> ~140 m sampling
CLASSES = {'tree': [10], 'grass': [20, 30], 'crop': [40], 'built': [50], 'water': [80, 90]}

acc = {k: np.zeros((H, W), np.float32) for k in CLASSES}
cnt = np.zeros((H, W), np.float32)
tiles = []
for la in range(42, 49, 3):
    for lo in range(18, 31, 3):
        tiles.append((la, lo))
for la, lo in tiles:
    tile = f"N{la:02d}E{lo:03d}"
    w0, s0, e0, n0 = max(lo, LO0), max(la, LA0), min(lo + 3, LO0 + W * ST), min(la + 3, LA0 + H * ST)
    if w0 >= e0 or s0 >= n0:
        continue
    url = URL.format(tile=tile)
    try:
        with rasterio.Env(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif'):
            with rasterio.open(url) as src:
                win = from_bounds(w0, s0, e0, n0, src.transform)
                c0 = int(round((w0 - LO0) / ST)); c1 = int(round((e0 - LO0) / ST))
                r0 = int(round((s0 - LA0) / ST)); r1 = int(round((n0 - LA0) / ST))
                out = (max(1, (r1 - r0) * SUB), max(1, (c1 - c0) * SUB))
                a = src.read(1, window=win, out_shape=out, resampling=Resampling.nearest)
    except Exception as e:
        print('skip', tile, e, file=sys.stderr); continue
    a = a[::-1]  # north-first raster -> south-first rows
    hh, ww = (r1 - r0), (c1 - c0)
    blk = a[:hh * SUB, :ww * SUB].reshape(hh, SUB, ww, SUB)
    valid = (blk > 0)
    cnt[r0:r1, c0:c1] += valid.sum(axis=(1, 3))
    for k, cl in CLASSES.items():
        acc[k][r0:r1, c0:c1] += np.isin(blk, cl).sum(axis=(1, 3))
    print('ok', tile, a.shape, file=sys.stderr)


def enc(g):
    v = g.astype(np.int16)
    d = np.concatenate([v[:, :1], np.diff(v, axis=1)], axis=1).astype('<i2')
    return base64.b64encode(zlib.compress(d.tobytes(), 9)).decode()


out = {'source': 'ESA WorldCover 2021 v200 (10 m), shares per 0.01° cell, CC BY 4.0', 'classes': CLASSES}
for k in CLASSES:
    pct = np.where(cnt > 0, np.round(100 * acc[k] / np.maximum(cnt, 1)), -1)
    out[k] = {'lo0': LO0, 'la0': LA0, 'st': ST, 'w': W, 'h': H, 'b': enc(pct)}
json.dump(out, open('data/landcover.json', 'w'), separators=(',', ':'))
print('cells with data', int((cnt > 0).sum()), 'of', W * H, file=sys.stderr)
