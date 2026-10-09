#!/usr/bin/env python3
"""Topographic wetness index (TWI = ln(a / tan b)) from the app's own DEM (data/dem.json, 'ro' grid, 0.005°),
replacing the distance-to-water proxy in data/terrain.json. Output on the terrain grid (0.01°, 960 x 470,
south-first), scaled 0-1000 where 1000 = the 98th-percentile TWI over Romania.

    python3 scripts/build_twi.py   (needs numpy, pysheds)
"""
import base64, json, zlib
import numpy as _np
if not hasattr(_np, "in1d"):
    _np.in1d = _np.isin  # pysheds 0.5 on numpy 2
import numpy as np
from pysheds.sview import Raster, ViewFinder
from pysheds.grid import Grid
from affine import Affine

dem = json.load(open('data/dem.json'))['ro']
a = np.frombuffer(zlib.decompress(base64.b64decode(dem['b'])), dtype='<i2').astype(np.int32).reshape(dem['h'], dem['w'])
z = np.cumsum(a, axis=1).astype(np.float64)          # south-first rows
zn = z[::-1].copy()                                    # north-first for pysheds
st = dem['st']; west = dem['lo0']; north = dem['la0'] + dem['h'] * st
aff = Affine(st, 0, west, 0, -st, north)
vf = ViewFinder(affine=aff, shape=zn.shape, crs='EPSG:4326', nodata=-32768)
r = Raster(zn, viewfinder=vf)
g = Grid.from_raster(r)
filled = g.fill_depressions(g.fill_pits(r))
inflated = g.resolve_flats(filled)
fdir = g.flowdir(inflated)
acc = g.accumulation(fdir)
# slope in metres per metre on the 0.005° grid
lat = north - (np.arange(zn.shape[0]) + 0.5) * st
dy = st * 111320.0; dx = st * 111320.0 * np.cos(np.radians(lat))[:, None]
gy, gx = np.gradient(zn)
slope = np.sqrt((gx / dx) ** 2 + (gy / dy) ** 2)
cell = np.sqrt(dx * dy)
twi = np.log((np.asarray(acc) + 1) * cell / np.maximum(np.tan(np.arctan(slope)), 0.001))
twi = twi[::-1]                                        # back to south-first
# aggregate 2x2 onto the 0.01° terrain grid
T = json.load(open('data/terrain.json'))['wet']
H, W = T['h'], T['w']
r0 = int(round((T['la0'] - dem['la0']) / st)); c0 = int(round((T['lo0'] - dem['lo0']) / st))
sub = twi[r0:r0 + 2 * H, c0:c0 + 2 * W]
sub = sub[:2 * H, :2 * W].reshape(H, 2, W, 2).mean(axis=(1, 3))
lo, hi = np.percentile(sub, 2), np.percentile(sub, 98)
v = np.clip((sub - lo) / (hi - lo), 0, 1) * 1000
v = (np.round(v / 25) * 25).astype(np.int16)  # steps of 25 keep the file small
d = np.concatenate([v[:, :1], np.diff(v, axis=1)], axis=1).astype('<i2')
out = json.load(open('data/terrain.json'))
out['wet_dist'] = out['wet']
out['wet'] = {'lo0': T['lo0'], 'la0': T['la0'], 'st': T['st'], 'w': W, 'h': H, 'b': base64.b64encode(zlib.compress(d.tobytes(), 9)).decode()}
out['wet_source'] = 'TWI ln(a/tan b) from the app DEM (0.005°, pysheds D8), 2nd-98th percentile scaled to 0-1000; wet_dist = previous distance-to-water proxy'
json.dump(out, open('data/terrain.json', 'w'), separators=(',', ':'))
print('TWI range', float(lo), float(hi), 'share of cells > 500:', float((v > 500).mean()))
