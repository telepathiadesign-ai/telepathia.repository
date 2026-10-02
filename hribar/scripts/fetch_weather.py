#!/usr/bin/env python3
"""Fetch Open-Meteo weather for a grid over Romania and write data/weather.json
for the Hribar app. Free tier counts each grid point as an API call (limits:
600/min, 5000/hour, 10000/day), so requests are paced.

Run on a machine whose network reaches api.open-meteo.com (e.g. the user's Mac
directly, not through the agent proxy):

    python3 scripts/fetch_weather.py --grid 0.1 --out data/weather.json

Deps: requests, numpy   (pip install requests numpy)
"""
import argparse, base64, json, sys, time, zlib
import numpy as np
import requests

LO0, LA0, LO1, LA1 = 20.2, 43.6, 29.8, 48.3        # Romania bounding box
HOURLY = "soil_temperature_6cm,soil_moisture_3_to_9cm,snow_depth"
DAILY = "precipitation_sum,temperature_2m_min"
URL = "https://api.open-meteo.com/v1/forecast"

def enc(arr, days, h, w):
    """Int16 row-delta within each (day,row), concat, deflate, base64."""
    out = np.empty_like(arr)
    NP = w * h
    for d in range(days):
        for r in range(h):
            row = arr[d*NP + r*w : d*NP + r*w + w]
            out[d*NP + r*w : d*NP + r*w + w] = np.concatenate(([row[0]], np.diff(row)))
    raw = out.astype('<i2').tobytes()
    co = zlib.compressobj(9, zlib.DEFLATED, -zlib.MAX_WBITS)  # raw deflate (matches DecompressionStream('deflate'))
    comp = co.compress(raw) + co.flush()
    # DecompressionStream('deflate') expects zlib-wrapped; use wbits 15
    comp = zlib.compress(raw, 9)
    return base64.b64encode(comp).decode()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grid', type=float, default=0.1)
    ap.add_argument('--out', default='data/weather.json')
    ap.add_argument('--batch', type=int, default=100)
    ap.add_argument('--sleep', type=float, default=10.0, help='seconds between batches (>=10 keeps under 600 calls/min)')
    a = ap.parse_args()

    st = a.grid
    W = int(round((LO1 - LO0) / st)) + 1
    H = int(round((LA1 - LA0) / st)) + 1
    NP = W * H
    DAYS = 41
    clamp = lambda v: int(max(-32000, min(32000, round(v))))
    rain = np.full(DAYS*NP, -32768, dtype=np.int32); tsoil = rain.copy()
    smoist = rain.copy(); tmin = rain.copy(); snow = rain.copy()
    for a2 in (rain, tsoil, smoist, tmin, snow):
        pass

    pts = [(r, c) for r in range(H) for c in range(W)]
    t0 = None
    MISSING = -32768
    print(f"grid {st}° -> {W}x{H} = {NP} points, {len(pts)//a.batch + 1} batches", file=sys.stderr)
    for b in range(0, len(pts), a.batch):
        batch = pts[b:b+a.batch]
        lats = ",".join(f"{LA0 + r*st:.2f}" for r, c in batch)
        lons = ",".join(f"{LO0 + c*st:.2f}" for r, c in batch)
        params = dict(latitude=lats, longitude=lons, hourly=HOURLY, daily=DAILY,
                      past_days=30, forecast_days=11, timezone="UTC", models="icon_seamless")
        for attempt in range(12):
            rr = requests.get(URL, params=params, timeout=60)
            if rr.status_code == 429:
                time.sleep(45); continue
            rr.raise_for_status()
            j = rr.json(); break
        else:
            sys.exit(f"batch {b} failed")
        arr = j if isinstance(j, list) else [j]
        if t0 is None:
            t0 = arr[0]["daily"]["time"][0]
        for m, (r, c) in enumerate(batch):
            k = r*W + c; A = arr[m]
            if not A or "daily" not in A: continue
            st6 = A["hourly"]["soil_temperature_6cm"]; sm = A["hourly"]["soil_moisture_3_to_9cm"]
            sd = A["hourly"]["snow_depth"]; pr = A["daily"]["precipitation_sum"]; tn = A["daily"]["temperature_2m_min"]
            for d in range(DAYS):
                o = d*NP + k; h0 = d*24
                hs = st6[h0:h0+24]; ms = sm[h0:h0+24]; ss = sd[h0:h0+24]
                ht = [x for x in hs if x is not None]; mt = [x for x in ms if x is not None]
                # missing values stay MISSING (sentinel) and are filled from the nearest valid day below; no invented constants
                rain[o] = clamp(pr[d]*10) if pr[d] is not None else MISSING
                tmin[o] = clamp(tn[d]*10) if tn[d] is not None else MISSING
                tsoil[o] = clamp(sum(ht)/len(ht)*10) if ht else MISSING
                smoist[o] = clamp(sum(mt)/len(mt)*1000) if mt else MISSING
                sv = [x for x in ss if x is not None]
                snow[o] = clamp(max(sv)*100) if sv else MISSING
        print(f"  batch {b//a.batch+1} ok", file=sys.stderr)
        time.sleep(a.sleep)

    gaps = 0
    for arr_ in (rain, tsoil, smoist, tmin, snow):
        for k in range(NP):
            for d in range(DAYS):
                if arr_[d*NP + k] != MISSING: continue
                gaps += 1; fill = 0
                for e in range(1, DAYS):
                    if d-e >= 0 and arr_[(d-e)*NP + k] != MISSING: fill = arr_[(d-e)*NP + k]; break
                    if d+e < DAYS and arr_[(d+e)*NP + k] != MISSING: fill = arr_[(d+e)*NP + k]; break
                arr_[d*NP + k] = fill
    grid = dict(lo0=LO0, la0=LA0, st=st, w=W, h=H)
    obj = dict(t0=t0, issued=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               model="icon_seamless", src=f"Open-Meteo (ICON-EU/D2), {time.strftime('%Y-%m-%d')}",
               grid=grid, days=DAYS, gaps=gaps,
               rain=enc(rain, DAYS, H, W), tsoil=enc(tsoil, DAYS, H, W),
               smoist=enc(smoist, DAYS, H, W), tmin=enc(tmin, DAYS, H, W), snow=enc(snow, DAYS, H, W))
    with open(a.out, "w") as f:
        json.dump(obj, f, separators=(",", ":"))
    print(f"wrote {a.out}: t0={t0}, {W}x{H}x{DAYS}", file=sys.stderr)

if __name__ == "__main__":
    main()
