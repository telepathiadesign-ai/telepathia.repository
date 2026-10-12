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
