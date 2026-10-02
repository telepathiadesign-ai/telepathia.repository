# Hribar

Mushroom fruiting forecast for Romania (academic research prototype). One self-contained page (`index.html`, built from `app.template.html`) plus data files in `data/`.

## Build

    python3 build.py          # writes index.html
    python3 build.py --test   # also index.test.html for headless tests

## Data refresh

`.github/workflows/hribar-weather.yml` (repo root) fetches the Open-Meteo grid daily with `scripts/fetch_weather.py` and commits `data/weather.json`. Hosting is not switched on yet; the app is currently published as a Claude artifact.

## Layout

- `app.template.html` — the whole app (CSS, markup, JS). Edit this, never `index.html`.
- `mlcss.txt` — MapLibre CSS, inlined at build time.
- `data/` — grids and catalogues the app loads (`dem`, `weather`, `terrain`, `leaf`, `soil`, `species`, `catalog`, Natural Earth and OSM layers).
- `scripts/` — data pipelines.
- `eval/` — the backtest: scores the model against dated iNaturalist/GBIF finds.
- `test/` — Playwright walkthroughs.

## Data sources and licences

Elevation: Mapzen Terrarium (SRTM, GMTED2010, ETOPO1). Weather: Open-Meteo (CC BY 4.0). Soil pH: SoilGrids 2.0 (CC BY 4.0). Map data: © OpenStreetMap contributors (ODbL), Natural Earth. Occurrences: GBIF, iNaturalist (per-record licences).
