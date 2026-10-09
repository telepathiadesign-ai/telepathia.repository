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
