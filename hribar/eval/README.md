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
