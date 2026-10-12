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
  clim  c_bio1, c_bio10 (degC x10), c_bio12, c_bio18 (mm), c_bio15 (x10)            CHELSA V2.1 1981-2010, CC0
"""
import base64, json, math, os, sys, time, zlib
import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.transform import from_origin
from rasterio.warp import reproject, transform_bounds
from rasterio.windows import from_bounds

REG = os.environ.get('REGION', 'ro')
LO0, LA0, W, H = {'ro': (20.2, 43.6, 960, 470), 'wide': (13.0, 41.0, 1800, 1400)}[REG]
ST = 0.01
PARTS = os.environ.get('PARTS', 'dem,soil,lc,trees,clim').split(',')
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


def part_clim(out):
    """CHELSA V2.1 bioclimatic climatologies 1981-2010 (Karger et al. 2017, CC0), ~1 km: bio1 annual mean T, bio10 mean T of the
    warmest quarter, bio12 annual precipitation, bio15 precipitation seasonality, bio18 precipitation of the warmest quarter."""
    bases = ['https://os.zhdk.cloud.switch.ch/chelsav2/GLOBAL/climatologies/1981-2010/bio/CHELSA_{v}_1981-2010_V.2.1.tif',
             'https://os.zhdk.cloud.switch.ch/envicloud/chelsa/chelsa_V2/GLOBAL/climatologies/1981-2010/bio/CHELSA_{v}_1981-2010_V.2.1.tif']
    wc = None   # fallback: WorldClim 2.1 bioclim at 2.5 arc-min (~4.6 km), one zip
    for v, conv in (('bio1', 'T'), ('bio10', 'T'), ('bio12', 'P'), ('bio15', 'S'), ('bio18', 'P')):
        g = None
        for base in bases:
            try:
                g = warp_to_grid('/vsicurl/' + base.format(v=v), 1000)
                g = (g * 0.1 - 273.15) * 10 if conv == 'T' else g * 0.1 if conv == 'P' else g   # CHELSA: K x10 / kg m-2 x10 / x10
                log('clim ok', v, 'CHELSA', round(float(np.nanmean(g)), 1)); break
            except Exception as e:
                log('clim try', v, base.split('/')[3], str(e)[:100]); g = None
        if g is None:
            try:
                if wc is None:
                    import urllib.request, zipfile
                    urllib.request.urlretrieve('https://geodata.ucdavis.edu/climate/worldclim/2_1/base/wc2.1_2.5m_bio.zip', '/tmp/wc.zip')
                    zipfile.ZipFile('/tmp/wc.zip').extractall('/tmp/wc'); wc = '/tmp/wc'
                g = warp_to_grid(f'{wc}/wc2.1_2.5m_bio_{v[3:]}.tif', 1000)
                g = g * 10 if conv in ('T', 'S') else g      # WorldClim: degC / mm / unitless -> same units as above
                log('clim ok', v, 'WorldClim 2.5m', round(float(np.nanmean(g)), 1))
            except Exception as e:
                log('clim fail', v, str(e)[:160]); continue
        out['c_' + v] = enc(g, -32768)
    if REG == 'ro':   # the app's copy: only the layers the learned habitat model uses
        json.dump({'source': 'bioclim 1981-2010 (CHELSA V2.1, CC0, or WorldClim 2.1 fallback): bio10 mean T warmest quarter (degC x10), bio12 annual precipitation (mm), bio15 precipitation seasonality (x10)',
                   **{k: out[k] for k in ('c_bio10', 'c_bio12', 'c_bio15') if k in out}}, open('data/climate.json', 'w'), separators=(',', ':'))


def part_dlt(out):
    """Copernicus HRL Dominant Leaf Type 2018 (10 m; 1 broadleaf, 2 coniferous), public EEA ImageServer, no login.
    Fetched per 1° tile at ~100 m (nearest), aggregated to the share of broadleaf and coniferous pixels per 0.01° cell."""
    import urllib.request, urllib.parse, io
    hosts = ['https://copernicus.discomap.eea.europa.eu', 'https://image.discomap.eea.europa.eu']
    SUBD = 10
    bl = np.full((H, W), np.nan, np.float32); co = np.full((H, W), np.nan, np.float32)
    for la in range(int(math.floor(LA0)), int(math.ceil(LA0 + H * ST))):
        for lo in range(int(math.floor(LO0)), int(math.ceil(LO0 + W * ST))):
            w0, s0, e0, n0 = max(lo, LO0), max(la, LA0), min(lo + 1, LO0 + W * ST), min(la + 1, LA0 + H * ST)
            c0, c1 = int(round((w0 - LO0) / ST)), int(round((e0 - LO0) / ST)); r0, r1 = int(round((s0 - LA0) / ST)), int(round((n0 - LA0) / ST))
            if c1 <= c0 or r1 <= r0:
                continue
            q = urllib.parse.urlencode(dict(bbox=f'{w0},{s0},{e0},{n0}', bboxSR=4326, imageSR=4326, size=f'{(c1 - c0) * SUBD},{(r1 - r0) * SUBD}',
                                            format='tiff', pixelType='U8', interpolation='RSP_NearestNeighbor', f='image'))
            a = None
            for h in hosts:
                for k in range(3):
                    try:
                        with urllib.request.urlopen(f'{h}/arcgis/rest/services/GioLandPublic/HRL_DominantLeafType2018/ImageServer/exportImage?{q}', timeout=120) as r:
                            data = r.read()
                        with rasterio.MemoryFile(data) as mf, mf.open() as src:
                            a = src.read(1)
                        break
                    except Exception as e:
                        log('dlt retry', lo, la, h.split('/')[2], str(e)[:80]); time.sleep(5 * (k + 1))
                if a is not None:
                    break
            if a is None or a.shape != ((r1 - r0) * SUBD, (c1 - c0) * SUBD):
                log('dlt skip', lo, la, None if a is None else a.shape); continue
            blk = a[::-1].reshape(r1 - r0, SUBD, c1 - c0, SUBD)
            valid = (blk <= 2).sum(axis=(1, 3))
            with np.errstate(all='ignore'):
                bl[r0:r1, c0:c1] = np.where(valid > 0, 100 * (blk == 1).sum(axis=(1, 3)) / valid, np.nan)
                co[r0:r1, c0:c1] = np.where(valid > 0, 100 * (blk == 2).sum(axis=(1, 3)) / valid, np.nan)
        log('dlt row ok', la)
    out['dlt_broad'] = enc(bl); out['dlt_conif'] = enc(co)
    log('dlt ok', 'broadleaf mean', round(float(np.nanmean(bl)), 1), 'conifer mean', round(float(np.nanmean(co)), 1), 'cells', int(np.isfinite(bl).sum()))
    if REG == 'ro':
        json.dump({'source': 'Copernicus HRL Dominant Leaf Type 2018 (10 m), % of pixels per 0.01° cell, © EU Copernicus Land Monitoring Service',
                   'broad': out['dlt_broad'], 'conif': out['dlt_conif']}, open('data/leaftype.json', 'w'), separators=(',', ':'))


def part_chm(out):
    """ETH Global Canopy Height 2020 (Lang et al. 2023, 10 m, Sentinel-2 + GEDI lidar, CC BY 4.0), 3° cloud-optimised tiles.
    Per 0.01° cell: mean canopy height of forest pixels (height >= 3 m) in dm, and share of pixels taller than 20 m (%)."""
    import urllib.request, re
    if REG != 'ro':
        log('chm: Romania only (the shared server rate-limits)'); return
    def fetch(u):
        for k in range(6):
            try:
                return urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'hribar-research'}), timeout=60).read().decode(errors='replace')
            except Exception as e:
                log('chm retry', k, str(e)[:80]); time.sleep(60 * (k + 1))
        raise RuntimeError('chm index unreachable')
    base = 'https://share.phys.ethz.ch/~pf/nlangdata/ETH_GlobalCanopyHeight_10m_2020_version1/'
    idx = fetch(base)
    subs = sorted(set(re.findall(r'href="([^"?]*3deg[^"]*/)"', idx))) or ['3deg_cogs/']
    log('chm subdirs', subs)
    sub = base + subs[0]
    names = sorted(set(re.findall(r'href="([^"]*_Map\.tif)"', fetch(sub))))
    log('chm tiles listed', len(names), names[:3])
    tiles = {}
    for n in names:
        m = re.search(r'([NS])(\d{2})([EW])(\d{3})', n)
        if m:
            la = int(m.group(2)) * (1 if m.group(1) == 'N' else -1); lo = int(m.group(4)) * (1 if m.group(3) == 'E' else -1)
            tiles[(la, lo)] = sub + n.split('/')[-1]
    SUBC = 5   # ~200 m samples per 0.01° cell edge... read at 20 m effective via average of 10 m pixels below
    hsum = np.zeros((H, W), np.float32); hcnt = np.zeros((H, W), np.float32); tall = np.zeros((H, W), np.float32); allc = np.zeros((H, W), np.float32)
    for (la, lo), url in sorted(tiles.items()):
        w0, s0, e0, n0 = max(lo, LO0), max(la, LA0), min(lo + 3, LO0 + W * ST), min(la + 3, LA0 + H * ST)
        if w0 >= e0 or s0 >= n0:
            continue
        c0, c1 = int(round((w0 - LO0) / ST)), int(round((e0 - LO0) / ST)); r0, r1 = int(round((s0 - LA0) / ST)), int(round((n0 - LA0) / ST))
        try:
            with rasterio.Env(**ENV), rasterio.open('/vsicurl/' + url) as src:
                a = src.read(1, window=from_bounds(w0, s0, e0, n0, src.transform), out_shape=((r1 - r0) * SUBC, (c1 - c0) * SUBC),
                             resampling=Resampling.nearest).astype(np.float32)
        except Exception as e:
            log('chm skip', la, lo, str(e)[:120]); continue
        time.sleep(5)
        a[a >= 255] = np.nan
        blk = a[::-1].reshape(r1 - r0, SUBC, c1 - c0, SUBC)
        fin = np.isfinite(blk); fo = fin & (blk >= 3)
        hsum[r0:r1, c0:c1] += np.where(fo, blk, 0).sum(axis=(1, 3)); hcnt[r0:r1, c0:c1] += fo.sum(axis=(1, 3))
        tall[r0:r1, c0:c1] += (fin & (blk >= 20)).sum(axis=(1, 3)); allc[r0:r1, c0:c1] += fin.sum(axis=(1, 3))
        log('chm ok', la, lo)
    with np.errstate(all='ignore'):
        out['chm_mean'] = enc(np.where(hcnt > 0, 10 * hsum / hcnt, np.where(allc > 0, 0, np.nan)))
        out['chm_tall'] = enc(np.where(allc > 0, 100 * tall / allc, np.nan))
    log('chm done', 'cells', int((allc > 0).sum()), 'mean forest height m', round(float(np.nansum(hsum) / max(1, np.nansum(hcnt))), 1))
    if REG == 'ro':
        json.dump({'source': 'ETH Global Canopy Height 2020 (10 m), mean forest height (dm) and share of pixels taller than 20 m, CC BY 4.0',
                   'mean': out['chm_mean'], 'tall': out['chm_tall']}, open('data/canopy.json', 'w'), separators=(',', ':'))


def part_gfc(out):
    """Global Forest Change (Hansen et al., UMD/Google, 30 m, CC BY 4.0): year of tree-cover loss. Per 0.01° cell: % of pixels
    lost in the last 10 years (gfc_loss) and in the last 4 years (gfc_loss4): clear-cuts, windthrow, bark-beetle dieback."""
    import urllib.request
    vers = [('GFC-2024-v1.12', 24), ('GFC-2023-v1.11', 23), ('GFC-2022-v1.10', 22)]
    SUBG = 20
    l10 = np.zeros((H, W), np.float32); l4 = np.zeros((H, W), np.float32); n = np.zeros((H, W), np.float32)
    for lat_top in range(int(math.ceil((LA0 + H * ST) / 10) * 10), int(LA0), -10):
        for lon_l in range(int(math.floor(LO0 / 10) * 10), int(LO0 + W * ST), 10):
            w0, s0, e0, n0 = max(lon_l, LO0), max(lat_top - 10, LA0), min(lon_l + 10, LO0 + W * ST), min(lat_top, LA0 + H * ST)
            if w0 >= e0 or s0 >= n0:
                continue
            tname = f"{lat_top:02d}N_{lon_l:03d}E"
            a = None
            for v, last in vers:
                url = f'https://storage.googleapis.com/earthenginepartners-hansen/{v}/Hansen_{v}_lossyear_{tname}.tif'
                try:
                    c0, c1 = int(round((w0 - LO0) / ST)), int(round((e0 - LO0) / ST)); r0, r1 = int(round((s0 - LA0) / ST)), int(round((n0 - LA0) / ST))
                    with rasterio.Env(**ENV), rasterio.open('/vsicurl/' + url) as src:
                        a = src.read(1, window=from_bounds(w0, s0, e0, n0, src.transform), out_shape=((r1 - r0) * SUBG, (c1 - c0) * SUBG),
                                     resampling=Resampling.nearest)
                    log('gfc ok', tname, v); break
                except Exception as e:
                    log('gfc try', tname, v, str(e)[:100])
            if a is None:
                continue
            blk = a[::-1].reshape(r1 - r0, SUBG, c1 - c0, SUBG)
            l10[r0:r1, c0:c1] += ((blk >= last - 9) & (blk > 0)).sum(axis=(1, 3)); l4[r0:r1, c0:c1] += ((blk >= last - 3) & (blk > 0)).sum(axis=(1, 3))
            n[r0:r1, c0:c1] += SUBG * SUBG
    with np.errstate(all='ignore'):
        out['gfc_loss'] = enc(np.where(n > 0, 100 * l10 / n, np.nan) * 10)   # per-mille
        out['gfc_loss4'] = enc(np.where(n > 0, 100 * l4 / n, np.nan) * 10)
    log('gfc done', 'mean loss 10 y %', round(float(np.nansum(l10) / max(1, np.nansum(n)) * 100), 2))


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
