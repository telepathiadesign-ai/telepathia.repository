#!/usr/bin/env python3
"""Habitat features on a 0.01° grid for the learned habitat model (Sprint A2). One pipeline for any region so the
model is trained and applied on identical inputs.

    REGION=ro   -> data/features.json        (app; lo 20.2-29.8, la 43.6-48.3)
    REGION=wide -> eval/data/features_wide.json  (training; lo 13-31, la 41-55: Romania + neighbours)
    PARTS=dem,soil,lc,trees (default all)

Layers (all south-first rows, int16 row-delta + zlib + base64, -1 / -32768 = no data):
  dem   elev (m), slope (0.1°), hli (heat load index x1000, McCune & Keon 2002)   Copernicus DEM GLO-90, © ESA/DLR/Airbus
  soil  clay, sand (g/kg), soc (dg/kg), ph (pH x10), 0-5 cm                      SoilGrids 2.0, ISRIC, CC BY 4.0
  lc    tree, grass, crop, built, water (% of cell)                              ESA WorldCover 2021, CC BY 4.0
  trees one layer per species, mean realized probability %                     Bonannella et al. 2022, CC BY 4.0
"""
import base64, json, math, os, sys, zlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds

REG = os.environ.get('REGION', 'ro')
LO0, LA0, W, H = {'ro': (20.2, 43.6, 960, 470), 'wide': (13.0, 41.0, 1800, 1400)}[REG]
ST = 0.01
PARTS = os.environ.get('PARTS', 'dem,soil,lc,trees').split(',')
OUT = 'data/features.json' if REG == 'ro' else 'eval/data/features_wide.json'
ENV = dict(GDAL_DISABLE_READDIR_ON_OPEN='EMPTY_DIR', CPL_VSIL_CURL_ALLOWED_EXTENSIONS='.tif,.vrt', GDAL_HTTP_MAX_RETRY='5',
           GDAL_HTTP_RETRY_DELAY='3', VSI_CACHE='TRUE', GDAL_CACHEMAX=512)
log = lambda *a: print(*a, file=sys.stderr, flush=True)


def enc(g, nod=-1):
    v = np.where(np.isfinite(g), np.round(g), nod).astype(np.int16)
    d = np.concatenate([v[:, :1], np.diff(v, axis=1)], axis=1).astype('<i2')
    return {'lo0': LO0, 'la0': LA0, 'st': ST, 'w': W, 'h': H, 'b': base64.b64encode(zlib.compress(d.tobytes(), 9)).decode()}


def warp_to_grid(url, read_res_m, scale=1.0, valid=None, resampling=Resampling.average):
    """Read the region from any raster at ~read_res_m, reproject to the 0.01° grid (mean). Returns south-first rows."""
    dst = np.full((H, W), np.nan, np.float32)
    dst_tf = from_origin(LO0, LA0 + H * ST, ST, ST)
    with rasterio.Env(**ENV), rasterio.open(url) as src:
        l, b, r, t = transform_bounds('EPSG:4326', src.crs, LO0, LA0, LO0 + W * ST, LA0 + H * ST, densify_pts=41)
        win = from_bounds(l, b, r, t, src.transform)
        res = abs(src.transform.a)
        if src.crs.is_geographic:
            res *= 111000 * math.cos(math.radians(LA0 + H * ST / 2))
        f = max(1.0, read_res_m / res)
        shape = (max(1, int(win.height / f)), max(1, int(win.width / f)))
        a = src.read(1, window=win, out_shape=shape, resampling=Resampling.average if f > 1 else Resampling.nearest,
                     boundless=True, masked=True).astype(np.float32)
        a = a.filled(np.nan)
        if valid:
            a[(a < valid[0]) | (a > valid[1])] = np.nan
        tf = rasterio.windows.transform(win, src.transform) * rasterio.Affine.scale(win.width / shape[1], win.height / shape[0])
        reproject(a, dst, src_transform=tf, src_crs=src.crs, src_nodata=np.nan, dst_transform=dst_tf, dst_crs='EPSG:4326',
                  dst_nodata=np.nan, resampling=resampling)
    return dst[::-1] * scale


def part_soil(out):
    for k, valid in (('clay', (0, 1000)), ('sand', (0, 1000)), ('soc', (0, 5000)), ('phh2o', (30, 110))):
        url = f'/vsicurl/https://files.isric.org/soilgrids/latest/data/{k}/{k}_0-5cm_mean.vrt'
        try:
            g = warp_to_grid(url, 500, valid=valid)
            out['ph' if k == 'phh2o' else k] = enc(g)
            log('soil ok', k, int(np.isfinite(g).sum()), round(float(np.nanmean(g)), 1))
        except Exception as e:
            log('soil fail', k, e)


def part_dem(out):
    SUB = 6 if REG == 'ro' else 4  # fine samples per cell edge (~185 m / ~280 m)
    fine = np.full((H * SUB, W * SUB), np.nan, np.float32)
    for la in range(int(math.floor(LA0)), int(math.ceil(LA0 + H * ST))):
        for lo in range(int(math.floor(LO0)), int(math.ceil(LO0 + W * ST))):
            ns, ew = ('N' if la >= 0 else 'S'), ('E' if lo >= 0 else 'W')
            name = f'Copernicus_DSM_COG_30_{ns}{abs(la):02d}_00_{ew}{abs(lo):03d}_00_DEM'
            url = f'/vsicurl/https://copernicus-dem-90m.s3.amazonaws.com/{name}/{name}.tif'
            w0, s0, e0, n0 = max(lo, LO0), max(la, LA0), min(lo + 1, LO0 + W * ST), min(la + 1, LA0 + H * ST)
            c0, c1 = int(round((w0 - LO0) / ST * SUB)), int(round((e0 - LO0) / ST * SUB))
            r0, r1 = int(round((s0 - LA0) / ST * SUB)), int(round((n0 - LA0) / ST * SUB))
            try:
                with rasterio.Env(**ENV), rasterio.open(url) as src:
                    a = src.read(1, window=from_bounds(w0, s0, e0, n0, src.transform), out_shape=(r1 - r0, c1 - c0),
                                 resampling=Resampling.average).astype(np.float32)
                fine[r0:r1, c0:c1] = a[::-1]
            except Exception as e:  # sea tiles do not exist
                if 'No such file' not in str(e) and '404' not in str(e) and 'not recognized' not in str(e):
                    log('dem skip', name, str(e)[:120])
    fine[fine < -100] = np.nan
    # slope / aspect on the fine grid (south-first rows: +row = north)
    dy = ST / SUB * 111000.0
    lat = LA0 + (np.arange(H * SUB) + 0.5) * ST / SUB
    dx = (ST / SUB * 111000.0 * np.cos(np.radians(lat)))[:, None]
    gz_n, gz_e = np.gradient(fine, axis=0) / dy, np.gradient(fine, axis=1) / dx
    slope = np.degrees(np.arctan(np.hypot(gz_n, gz_e)))
    aspect = (np.degrees(np.arctan2(-gz_e, -gz_n)) + 360) % 360  # direction the slope faces, 0 = north
    # heat load index, McCune & Keon 2002 eq. 3 (folded aspect about NE-SW)
    L = np.radians(lat)[:, None] * np.ones_like(fine); S = np.radians(slope)
    A = np.radians(np.abs(180 - np.abs(aspect - 225)))
    hli = np.exp(-1.467 + 1.582 * np.cos(L) * np.cos(S) - 1.5 * np.cos(A) * np.sin(S) * np.sin(L)
                 - 0.262 * np.sin(L) * np.sin(S) + 0.607 * np.sin(A) * np.sin(S))
    blk = lambda x: np.nanmean(x.reshape(H, SUB, W, SUB), axis=(1, 3))
    with np.errstate(all='ignore'):
        out['elev'] = enc(blk(fine), -32768)
        out['slope'] = enc(blk(slope) * 10)
        out['hli'] = enc(blk(hli) * 1000)
    log('dem ok', int(np.isfinite(fine).sum()), 'fine cells')


def part_lc(out):
    SUB = 6
    URL = 'https://esa-worldcover.s3.eu-central-1.amazonaws.com/v200/2021/map/ESA_WorldCover_10m_2021_v200_{tile}_Map.tif'
    CL = {'tree': [10], 'grass': [20, 30], 'crop': [40], 'built': [50], 'water': [80, 90]}
    acc = {k: np.zeros((H, W), np.float32) for k in CL}; cnt = np.zeros((H, W), np.float32)
    for la in range(int(math.floor(LA0 / 3) * 3), int(LA0 + H * ST) + 1, 3):
        for lo in range(int(math.floor(LO0 / 3) * 3), int(LO0 + W * ST) + 1, 3):
            w0, s0, e0, n0 = max(lo, LO0), max(la, LA0), min(lo + 3, LO0 + W * ST), min(la + 3, LA0 + H * ST)
            if w0 >= e0 or s0 >= n0:
                continue
            tile = f"N{la:02d}E{lo:03d}"
            c0, c1 = int(round((w0 - LO0) / ST)), int(round((e0 - LO0) / ST))
            r0, r1 = int(round((s0 - LA0) / ST)), int(round((n0 - LA0) / ST))
            try:
                with rasterio.Env(**ENV), rasterio.open(URL.format(tile=tile)) as src:
                    a = src.read(1, window=from_bounds(w0, s0, e0, n0, src.transform), out_shape=((r1 - r0) * SUB, (c1 - c0) * SUB),
                                 resampling=Resampling.nearest)
            except Exception as e:
                log('lc skip', tile, str(e)[:100]); continue
            blk = a[::-1].reshape(r1 - r0, SUB, c1 - c0, SUB)
            cnt[r0:r1, c0:c1] += (blk > 0).sum(axis=(1, 3))
            for k, cl in CL.items():
                acc[k][r0:r1, c0:c1] += np.isin(blk, cl).sum(axis=(1, 3))
            log('lc ok', tile)
    for k in CL:
        out[k] = enc(np.where(cnt > 0, 100 * acc[k] / np.maximum(cnt, 1), np.nan))


def part_trees(out):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from build_trees import find_records  # noqa
    for sp, (y1, key, url) in sorted(find_records().items()):
        try:
            g = warp_to_grid('/vsicurl/' + url, 240, valid=(0, 100))
            out['t_' + sp.replace('.', '_')] = enc(g)
            log('trees ok', sp, key, round(float(np.nanmean(g)), 1))
        except Exception as e:
            log('trees fail', sp, str(e)[:160])


if __name__ == '__main__':
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    out.setdefault('meta', {})['region'] = REG
    for p in PARTS:
        log('== part', p)
        try:
            globals()['part_' + p](out)
            out['meta'][p] = 'ok'
        except Exception as e:
            log('part failed', p, e); out['meta'][p] = f'failed: {str(e)[:200]}'
        json.dump(out, open(OUT, 'w'), separators=(',', ':'))
    log('layers', sorted(k for k in out if k != 'meta'))
