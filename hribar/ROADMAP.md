# Hribar roadmap — from 12 Oct 2026

Rule for every item: it ships only if `eval/compare.py` shows a gain whose 95% interval excludes zero on held-out data (2026 finds, and held-out 1° map squares for anything learned).

Where we are (held-out): habitat AUC ~0.68 median for the 28 species with enough 2026 finds; full forecast ~0.70; 75 of 254 species testable; weather-timing correlation 0.30.

## Sprint A — model accuracy (no blockers, ~1 week)

| # | Work | How | Done when |
| --- | --- | --- | --- |
| A1 | Tree-species maps | GitHub Actions job reads the OpenGeoHub 30 m maps (16 species: spruce, fir, pines, larch, beech, oaks, birch, hornbeam, chestnut, …) for Romania at 0.01° -> `data/trees.json`; host factor uses the literature host genera × tree probability | habitat AUC +0.02 or more, CI above 0 |
| A2 | One learned habitat model | extend `fit_landcover.py`: land cover + trees + soil (SoilGrids texture, organic carbon, pH) + wetness + heat load + elevation; regularised per species, with genus/feeding-group pooling so rare species borrow strength | median held-out habitat AUC ≥ 0.70; testable species keep or gain |
| A3 | More records | GBIF + iNaturalist for HU, SK, PL, CZ, west UA, MD, BG, RS 2018–2026, fetched by an Actions job over several nights (API limits) | species with 15+ finds: 75 -> 150 |
| A4 | Timing per species group | ERA5 vs ICON bias correction from the overlapping weeks we now have; refit rain delay and soil-temperature optimum per group (soil-mycorrhizal, litter, wood, grassland), then per species where data allow | weather AUC +0.01 with CI above 0, or timing ρ ≥ 0.35 |
| A5 | Weekly retrain + report | Actions job: pull new finds, refit A2, rerun the backtest, regenerate `reliability.json`, commit a dated report; About page shows the current scores | runs unattended for 2 weeks |

## Sprint B — ground truth and independence (needs your decisions)

| # | Work | Needs | Done when |
| --- | --- | --- | --- |
| B1 | Host outside Claude (VPS or Cloudflare Pages) + daily refresh with no Mac | your choice of host | Mac scheduled task switched off |
| B2 | "Found it / searched, nothing" logging, coordinates blurred | storage: VPS, or the Claude app's built-in shared database (works today, but only for people you share the app with) | first 50 visits logged |
| B3 | Calibrated levels ("Good = found on X% of visits") | ~200 logged visits from B2 | levels shown as measured hit rates |

## Sprint C — product (after A)

| # | Work |
| --- | --- |
| C1 | Alerts for saved spots ("peak in 5–7 days"), needs B1 |
| C2 | Offline mode for the mountains (PWA cache of the area you're in) |
| C3 | Species photos from iNaturalist (CC BY), with credits |
| C4 | "Why here, why now" one-liner on each cell, from the factor table |

## Decisions needed

1. Host: VPS (private, already has nginx + certificate) or Cloudflare Pages.
2. Logged finds: shared and anonymous, or private per person.
3. Scope: confirm using neighbouring countries' records to train (recommended).

## Status, 12 Oct 2026

- A1 tree maps: built (10 of 11 species; chestnut timed out). Tested; no gain on Romanian finds. Not shipped.
- A2 learned habitat: built and tested (`eval/fit_habitat.py`, `eval/spatial_habitat.py`). No gain over learned land cover; target 0.70 not met.
- A3 records: met (species with 15+ finds 75 → 186 after one night; job continues nightly). Shipped as neighbour-trained land-cover models for 128 more species (habitat +0.027..+0.030, full +0.012..+0.016, CI above 0 on two periods).
- A4, A5: next.
- 12 Oct, later: climate-niche habitat model shipped for the 128 species without a Romanian model (transfer test +0.041 vs rules, equal to a Romania-trained model). Field log live (B2). Reliability now a true hold-out (56 species). A4 waits for the archived-forecast file.

## Sprint D — new data sources (planned 12 Oct 2026)

Rule for every item: build as a GitHub job, test with the backtest (2024-25 and 2026, spatial blocks for habitat), ship only if the CI excludes zero.

### D-I Where people look (bias), not just where fungi grow
| # | Source | What it fixes | Done when |
| --- | --- | --- | --- |
| D1 | Access layer: distance to roads, trails, huts, car parks (OSM, already in the app) | finds cluster on trails; the models learn "near a path" as habitat. Fit with access as a covariate, predict with it held constant | habitat AUC gain on spatial blocks |
| D2 | Observer effort: all iNaturalist records (any taxon) per cell and month | separates "nobody went" from "nothing grows" | used as background weights |

### D-II Better rain (the strongest weather signal)
| # | Source | What it fixes | Done when |
| --- | --- | --- | --- |
| D3 | GPM IMERG satellite precipitation (0.1°, half-hourly, free) | model rain misses mountain showers; past 30 days from observation instead of model | weather AUC up in backtest |
| D4 | ANM / OPERA radar composites (if obtainable) | same, at 1 km | as D3 |

### D-III Satellite habitat
| # | Source | What it fixes | Done when |
| --- | --- | --- | --- |
| D5 | ETH canopy height 10 m (GEDI lidar + Sentinel-2) | stand age: mature vs young forest | habitat CI > 0 |
| D6 | Global Forest Watch tree-cover loss by year, 30 m | clear-cuts, windthrow, bark-beetle dieback (dead wood; lost mycorrhiza) | habitat CI > 0 |
| D7 | Copernicus grassland + Sentinel-2 mowing detection | grazed pasture vs hay meadow vs crop | grassland species habitat CI > 0 |
| D8 | Snow cover (Sentinel-2 / MODIS), melt date per cell | spring species timing (morels, St George's) | spring species weather AUC up |
| D9 | Sentinel-1 surface soil moisture, 1 km daily | measured vs modelled wetness | weather AUC up, or dropped |

### D-IV Timing signals from people
| # | Source | What it fixes | Done when |
| --- | --- | --- | --- |
| D10 | Google Trends, Romania by county: "hribi", "ciuperci", "gălbiori" | when flushes happen, county by county, years back | timing correlation with finds; candidate live "flush is on" signal |
| D11 | European phenology from GBIF dates (latitude, elevation, year) | season curves per species instead of catalogue months | season AUC up |
| D12 | Mushroom buying-centre volumes / prices (needs a partner) | commercial flush timing for ceps, chanterelles | partner found |

### D-V Ground truth
| # | Source | What it fixes | Done when |
| --- | --- | --- | --- |
| D13 | Field log (live) + planned "nothing here" visits | true absences; calibrated levels (B3) | 200 visits |
| D14 | Romanian forest management data (Romsilva stand age/species per compartment), herbarium records not in GBIF | best possible forest map; old records | access obtained |

### Order
1. D1 access bias + D3 satellite rain (biggest expected gains, both cheap)
2. D5 canopy height, D6 disturbance
3. D10 search trends, D11 European phenology
4. D7 grassland, D8 snow, D9 radar moisture
5. D12, D14 need people outside the project; D13 is ongoing

- 13 Oct: VPS move parked (owner). Setup kept on the VPS at /root/hribar (repo clone, venv, memory-capped run.sh); deploy key not added; no jobs scheduled. All jobs stay on GitHub Actions.
