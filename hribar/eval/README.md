# Backtest

Every model change is accepted only if it improves these scores. Run from `hribar/`.

| Script | Question | Metric |
| --- | --- | --- |
| `backtest.py` | Does the model rank each species' real finds above other fungus records? | AUC per species (0.5 = no skill); median and record-weighted mean over species with 15+ finds |
| `timing.py` | Does the weather term rise when fungi are being found? | Spearman of weekly fungus share of iNaturalist records vs the weather term, calendar-month means removed |

Data (`data/`): iNaturalist fungus records in Romania 2020–2026 (`inat_ro_fungi_2020_2026.json`), daily iNaturalist fungus and plant counts (`inat_daily_counts_ro.json`), ERA5-Land daily weather at the 40 busiest 0.5° nodes with ERA5 rain (`era5_land.json`). `habitat_at_points.json` is regenerated from the app (not committed).

## Results, 2 Oct 2026

| Change | Habitat AUC (median / weighted) | Habitat × season | Full model | Timing (anomaly ρ) |
| --- | --- | --- | --- | --- |
| Model 0.3 (before) | 0.548 / 0.558 | 0.680 / 0.648 | 0.671 / 0.655 | 0.28* |
| + catalogue fixes, host lists read, habitat codes | 0.592 / 0.589 | 0.685 / 0.673 | | |
| + wood decayers follow trees outside forest | 0.582 / 0.602 | 0.689 / 0.687 | | |
| + new water term (lagged rain 70%, relative moisture 30%, floor 0.15) | | | 0.687 / 0.668 | 0.30 |

*With ERA5-Land soil moisture the old formula behaves as rain-only, because ERA5-Land moisture (~0.36) saturates the old 12–30% scale. In the app, Open-Meteo ICON moisture (~0.10–0.25) instead drove it to zero — the failure the September 2026 check showed.

Live check against the 184 iNaturalist finds of September 2026: finds rated Unlikely fell from 86% to 33%; fruiting percentile at finds rose from 0.60 to 0.73.

Not shipped: soil-temperature optima fitted to finds (`data/fitted_soilT_2024_2026.json`). They helped on the 2026 holdout in ERA5 space (weather AUC 0.566 → 0.583) but hurt in the app (0.73 → 0.67), most likely because ERA5-Land and ICON soil temperatures differ; needs a bias correction first.

## Literature traits, 3 Oct 2026

8 research agents read de/en Wikipedia, first-nature, tintling, fungiversum, 123pilzsuche, pilzmuseum, ciupercar.ro and others for all 254 species (`research/batch*_traits.json`; 171 medium, 9 high, 74 low confidence; mostly 2 sources each; almost no numeric temperatures, rain lags or elevations exist in these sources). Each trait was tested on its own:

| Variant | Habitat AUC (median / weighted) | Season AUC | Habitat × season | Full |
| --- | --- | --- | --- | --- |
| No literature traits | 0.582 / 0.602 | 0.668 / 0.643 | 0.689 / 0.687 | 0.687 / 0.668 |
| Hosts only | 0.596 / 0.600 | 0.668 / 0.643 | 0.694 / 0.685 | 0.694 / 0.667 |
| Soil pH only | 0.589 / 0.603 | — | 0.693 / 0.688 | 0.687 / 0.668 |
| Habitat types only | 0.578 / 0.603 | — | 0.685 / 0.692 | 0.687 / 0.668 |
| Literature months only (GBIF-checked) | — | 0.662 / 0.637 | 0.688 / 0.684 | 0.675 / 0.665 |
| **Shipped: hosts + pH + habitat types** | 0.582 / 0.600 | 0.668 / 0.643 | **0.694 / 0.689** | 0.687 / 0.668 |

Literature months were rejected (wider seasons lowered the season score). Host, pH and habitat traits change the score by about ±0.01, within noise: the model cannot yet see what they describe (forest type is mapped for ~3% of cells, parks and grassland not at all). They become useful with tree-species and land-cover maps.

## Round 3, 4 Oct 2026 — judged with `compare.py` (paired per-species differences, 95% bootstrap CI)

| Change | Result | Shipped |
| --- | --- | --- |
| Literature traits (hosts, pH, habitat) | no clear change (CI spans 0) | yes, for transparency |
| Cooling trigger (night temperatures falling) | full −0.002, CI below 0 | no |
| Frost trigger (≥2 nights ≤ 0 °C in 10 days) | weather +0.005, CI above 0; full unchanged | yes |
| Degree days (spring), deep soil moisture | no clear change | no |
| Recent iNaturalist reports, 60 km / 14 days, boost ×(1 + 2·min(1, n/3)) | full +0.014, CI +0.010..+0.018; 49 species better, 10 worse | yes |
| Topographic wetness index from the DEM | no clear change (+0.002) | yes (replaces a cruder proxy) |
| Measured tree cover (ESA WorldCover) instead of the heuristic | habitat +0.016, CI −0.002..+0.034 | yes |
| Rule-based grassland / town cover from land cover | habitat × season −0.012, CI below 0 | no |
| **Learned land-cover preference per species** (`fit_landcover.py`), trained 2024–25, tested on 2026 and on held-out 1° blocks | **habitat +0.054, CI +0.034..+0.075; 24 better, 3 worse; full +0.022** | yes (refit on all years) |

## Round 4 (Sprint A), 12 Oct 2026

New inputs: `data/features.json` / `eval/data/features_wide.json` (`scripts/build_features.py`, GitHub job `hribar-features`):
Copernicus DEM (elevation, slope, heat load), SoilGrids 0–5 cm (clay, sand, organic carbon, pH), ESA WorldCover shares,
and 10 tree-species realized-probability maps (Bonannella et al. 2022). Training records from neighbouring countries:
`eval/data/records_cee.json.gz` (GBIF, nightly job `hribar-records`; 99k rows after the first night, 75% of species × country done).

| Test (habitat AUC, Romanian 2026 finds) | Result | Shipped |
| --- | --- | --- |
| Learned habitat on all features (land cover + DEM + soil + 10 tree species + host availability), spatial blocks | −0.006 vs learned land cover, CI spans 0 (overfits: ~26 features, 15–50 finds per species) | no |
| Land cover + host availability from tree maps | −0.002, CI spans 0 | no |
| Land cover + pH / heat load / slope | ±0.000, CI spans 0 | no |
| Land cover + 5 main tree species + host | −0.008, CI spans 0 | no |
| Neighbour-country records pooled into training (weights 0.03–1) | −0.002 to −0.009, CI spans 0 | no |
| **Land-cover model trained on neighbour countries only**, vs rule-based habitat (spatial blocks) | **+0.031, CI +0.009..+0.058, 16 better / 4 worse** | — |
| same, full backtest, 2026 | **habitat +0.027 (CI +0.010..+0.049), full +0.012 (CI +0.004..+0.021)** | yes |
| same, full backtest, 2024–25 (also unseen by this model) | **habitat +0.030 (CI +0.017..+0.046), full +0.016 (CI +0.011..+0.021)** | yes |
| App vs Python implementation, 2026 | −0.005, CI spans 0 (equivalent) | — |

Shipped: `data/lc_prefs.json` now covers 203 species. 75 use the Romanian model (15+ Romanian finds); 128 use the
neighbour-country model (`eval/fit_landcover_cee.py`, `src: neighbours`), which is worse than a Romanian model (−0.018)
but clearly better than the rules. The app labels which one a species uses.

Not shipped: tree maps, soil texture / carbon, heat load. With current find counts they do not add skill over land cover
and elevation. The A2 target (median held-out habitat AUC ≥ 0.70) is not met: best is 0.67–0.69 depending on the test.
Revisit once records reach ~50 finds per species, or with a model that shares strength across species.

## Round 5, 12 Oct 2026 — climate niche, field log, honest reliability

Prompted by a side-by-side with Sporecast for *Psilocybe semilanceata*: our habitat painted the whole Transylvanian
plateau "High" (catalogue elevation 1200 ± 1280 m, open land scored 1.0, no climate in the habitat term); theirs showed
only the montane pastures, which is the real ecology.

New inputs: CHELSA V2.1 bioclim (bio1, bio10, bio12, bio15, bio18) on both grids (`scripts/build_features.py` part `clim`);
`data/climate.json` carries bio10/bio12/bio15 to the app.

| Test | Result | Shipped |
| --- | --- | --- |
| Elevation optimum fitted on pooled RO + neighbour finds (`fit_elev.py`) | wrong on inspection: *Amanita muscaria* becomes lowland (Polish records). Elevation does not transfer between countries. | no |
| Climate-niche model (`fit_niche.py`: land cover + bio10, bio10², bio12, bio12², bio15; no elevation), spatial blocks, vs rule-based habitat | **+0.048, CI +0.025..+0.072; 30 better / 9 worse** | — |
| same, vs the Romania-trained land-cover model (34 species with both) | +0.004, CI −0.016..+0.027 (equal) | — |
| **Transfer: niche model trained on other countries only, scored on Romanian 2026 blocks**, vs rules | **+0.041, CI +0.021..+0.064; 25 better / 6 worse**; vs Romania-trained land cover +0.002 (equal) | **yes, for the 128 species without a Romanian model** |
| (for comparison) elevation-based neighbour model, same transfer test | +0.031 vs rules, −0.018 vs Romania-trained | replaced |
| Romanian land-cover × niche (geometric mean) | −0.002 vs land cover alone | no |

Also this round: the field log (found it / nothing here) stored in the artifact database — the first source of true
absences; `reliability.json` is now cross-fitted (each year scored with habitat preferences fitted on the other years,
`eval/weekly.py`, weekly GitHub job): 56 species rated (24 good / 16 useful / 16 weak) instead of 75 partly in-sample.

Open: timing per feeding group in forecast space (A4) waits for `eval/data/hist_forecast.json` (archived Open-Meteo
forecasts at the 40 nodes). In ERA5 space the per-group fit gave full AUC +0.011 (CI +0.001..+0.022) on 2026.

### D3 observed rain, 12 Oct 2026
E-OBS v33 gauge-based daily rain (0.5° box mean at each node) in place of modelled rain, 2024-25: weather +0.004
(CI −0.003..+0.010), full +0.001 (CI −0.003..+0.005). No gain. Model and gauges disagree a lot locally (Brașov node:
874 vs 537 mm/yr, daily r = 0.45) yet the forecast does not care: timing is dominated by temperature, season and the
recent-reports signal, and the water term is relative per place. Satellite rain (IMERG) is less accurate than gauges in
mountains, so it was not pursued.

### D6 forest loss, 12 Oct 2026
Hansen Global Forest Change v1.12 (30 m): % of each 0.01° cell lost in the last 10 and 4 years, added to the Romanian
land-cover model. Held-out 2026: habitat −0.004 (CI −0.009..+0.001); 2025: +0.001 (CI −0.003..+0.006). No gain; not shipped.
Leaf type as a learned input (beyond its use in the host factor): +0.002 / −0.001, no gain.

### D11 learned fruiting season, 12 Oct 2026 — shipped
`eval/fit_season.py`: per species, smoothed day-of-year density of finds (Romania + GBIF in the Carpathian-Pannonian-
Balkan band) divided by the density of all finds, max = 1, floor 0.05; replaces catalogue months for 199 species.
Fitted only on finds before the test year:

| Held-out | Season AUC | Full forecast |
| --- | --- | --- |
| 2026 | +0.081 (CI +0.053..+0.108), 35 better / 5 worse | +0.017 (CI +0.006..+0.028) |
| 2025 | +0.065 (CI +0.041..+0.090), 41 better / 13 worse | +0.025 (CI +0.013..+0.039) |

App lookup checked equal to the file. Refit weekly.

### Europe-wide niche training, 13 Oct 2026
New grid `eval/data/features_eu.json` (land cover + CHELSA, 0.02°, Europe). Romania hold-out, spatial blocks, models trained
without any Romanian finds, rules-only baseline: Carpathian-Balkan model +0.047 (CI +0.032..+0.063), Europe-wide model +0.030
(CI +0.015..+0.044). Western European records dilute the regional signal, so the shipped file is a hybrid: regional model
for 140 species with 50+ finds in the region, Europe-wide for 35 rarer ones (e.g. *Psilocybe semilanceata*: 20 regional,
730 European finds). Bug fixed on the way: the grid lookup rejected cells without elevation, i.e. the whole Europe grid.

### 14 Oct 2026 — duplicate rules, audit, soft ceiling, grassland rule, pasture, search trends
| Test (held-out 2026 unless noted) | Result | Shipped |
| --- | --- | --- |
| Drop catalogue tree-cover + host rules where a learned habitat model applies | full −0.011 (CI −0.019..−0.003) | no: the rules still add information |
| … and elevation too | full −0.017 (CI −0.026..−0.008) | no |
| Soft ceiling (index above 0.8 approaches 1 instead of being cut off) | ±0.000 | no |
| Grassland species scored on mapped grassland instead of "not forest" | ±0.000 (5 species; field mushroom +0.026, shaggy ink cap −0.083) | no |
| OSM sheepfolds + pasture share as learned inputs | 2026 habitat −0.006 (CI below 0); 2025 ±0 | no |
| Google Trends (weekly, RO) as a timing boost, term per genus | 2024-25 ±0; 2026 −0.001 (CI below 0) | no: a nationwide weekly signal cannot tell one species' finds from other finds on the same day |

Per-species audit (`eval/audit.py`, `AUDIT.md`, `audit_sheet_*.png`): 60 of 254 species flagged. Forest species look
right (penny bun, fly agaric: finds at the 0.95 percentile of their own map). Open-country and generalist species
(Agaricus, puffballs, St George's mushroom, shaggy ink cap, jelly ear, velvet shank) paint 40–90 % of Romania High and
their finds sit near or below the map median. None of the rule fixes above helps them in the backtest, but only a
handful of these species have enough Romanian finds to test; better data on where they grow (field logs) is the lever.
