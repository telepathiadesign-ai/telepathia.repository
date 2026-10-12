#!/usr/bin/env python3
"""Archived Open-Meteo forecasts at the 40 evaluation nodes -> eval/data/hist_forecast.json.

Same variables and daily aggregation as the app's weather file (scripts/fetch_weather.py), so the backtest can be run
in the space the app actually sees (the ICON-based "best match" forecast) instead of ERA5-Land. Written in the structure
of era5_land.json so eval/backtest.py loads it with WX_FILE=eval/data/hist_forecast.json. Runs on GitHub Actions.

Source: https://historical-forecast-api.open-meteo.com (archived model runs, CC BY 4.0).
"""
import json, os, sys, time, datetime as dt, urllib.parse, urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..')
OUT = os.path.join(ROOT, 'eval', 'data', 'hist_forecast.json')
URL = 'https://historical-forecast-api.open-meteo.com/v1/forecast'
HOURLY = 'soil_temperature_6cm,soil_moisture_3_to_9cm,soil_moisture_9_to_27cm,snow_depth'
DAILY = 'precipitation_sum,temperature_2m_min'
T0 = dt.date(2023, 12, 1)
END = dt.date.today() - dt.timedelta(days=3)


def get(params):
    for k in range(8):
        try:
            with urllib.request.urlopen(URL + '?' + urllib.parse.urlencode(params), timeout=180) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            body = e.read()[:300].decode(errors='replace')
            print('http', e.code, body, file=sys.stderr)
            if e.code == 400:
                raise
            time.sleep(70 if e.code == 429 else 20 * (k + 1))
        except Exception as e:
            print('retry', k, e, file=sys.stderr); time.sleep(15 * (k + 1))
    raise RuntimeError('gave up')


def dmean(xs):
    v = [x for x in xs if x is not None]
    return round(sum(v) / len(v), 3) if v else None


def main():
    nodes = json.load(open(os.path.join(ROOT, 'eval', 'data', 'era5_nodes.json')))
    out = json.load(open(OUT)) if os.path.exists(OUT) else {}
    model = os.environ.get('WX_MODEL', 'best_match')
    for lon, lat in nodes:
        key = f'{lon:g},{lat:g}'
        if key in out and out[key].get('end') == END.isoformat():
            continue
        d = {k: [] for k in ('precipitation_sum', 'temperature_2m_min', 'soil_temperature_0_to_7cm_mean',
                             'soil_moisture_0_to_7cm_mean', 'soil_moisture_7_to_28cm_mean', 'snow_depth_max')}
        elev = None
        s = T0
        while s <= END:
            e = min(END, dt.date(s.year, 12, 31))
            j = get(dict(latitude=lat, longitude=lon, start_date=s.isoformat(), end_date=e.isoformat(), hourly=HOURLY, daily=DAILY,
                         models=model, timezone='UTC'))
            elev = j.get('elevation', elev)
            H, D = j['hourly'], j['daily']
            n = len(D['time'])
            for i in range(n):
                h0 = i * 24
                d['precipitation_sum'].append(D['precipitation_sum'][i]); d['temperature_2m_min'].append(D['temperature_2m_min'][i])
                d['soil_temperature_0_to_7cm_mean'].append(dmean(H['soil_temperature_6cm'][h0:h0 + 24]))
                d['soil_moisture_0_to_7cm_mean'].append(dmean(H['soil_moisture_3_to_9cm'][h0:h0 + 24]))
                d['soil_moisture_7_to_28cm_mean'].append(dmean(H['soil_moisture_9_to_27cm'][h0:h0 + 24]))
                sv = [x for x in H['snow_depth'][h0:h0 + 24] if x is not None]
                d['snow_depth_max'].append(round(max(sv), 3) if sv else None)
            s = e + dt.timedelta(days=1)
            time.sleep(3)
        out[key] = dict(elev=elev, lat=lat, lon=lon, t0=T0.isoformat(), end=END.isoformat(), model=model, d=d)
        json.dump(out, open(OUT, 'w'), separators=(',', ':'))
        print('ok', key, 'days', len(d['precipitation_sum']), 'elev', elev,
              'missing soilT', sum(1 for x in d['soil_temperature_0_to_7cm_mean'] if x is None), file=sys.stderr)
    print('nodes', len(out), file=sys.stderr)


if __name__ == '__main__':
    main()
