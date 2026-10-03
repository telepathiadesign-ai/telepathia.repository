You are researching the ecology of European macrofungi for a mushroom fruiting-forecast model focused on Romania (Carpathians, Transylvania, lowlands). Accuracy matters more than coverage: leave a field null rather than guess.

INPUT: {INPUT} — a JSON list of species, each with its current catalogue entry (hosts_text, months bitstring Jan..Dec, elev [lo,hi] m, habitat_code W/G/D, trophic m/s/p, edibility). Treat the catalogue as a hypothesis to check, not a source.

For EACH species, research with WebSearch and WebFetch. Prefer, in order: Romanian or Central/Eastern European sources (Romanian, Hungarian, Czech, Slovak, Polish, German mycological sites and atlases, e.g. 123pilze.de, pilzforum, gombanet.hu, houbareni.cz, nahuby.sk, grzyby.pl, ciuperci sites), then European references (first-nature.com, Wikipedia in de/ro/hu/en, Funga Nordica quotes, species fact sheets of mycological societies, peer-reviewed papers). Open the page you cite; a search snippet is not a source. Spend about 3-5 page fetches per species; stop when the fields are filled from at least 2 independent sources where possible.

Record per species (exact JSON keys):
{
 "latin": "<as given>",
 "accepted_name": "<current accepted name if different, else same>",
 "hosts": [{"genus": "Picea", "strength": "primary|secondary|occasional"}],   // ECM partner trees for mycorrhizal species; host trees/wood for wood decayers and parasites; [] for grassland/dung/litter species with no host
 "substrate": "soil|litter|wood_dead|wood_living|wood_buried|dung|cones|moss|burnt|other",
 "habitats": [ any of "broadleaf_forest","conifer_forest","mixed_forest","forest_edge_clearing","grassland_pasture","meadow_unimproved","park_garden_lawn","riparian_floodplain","orchard","bog_wet","alpine_subalpine","steppe_dry_grassland","urban_ruderal","plantation" ],
 "soil_ph": "acid|neutral|calcareous|indifferent|null",
 "soil_moisture": "dry|mesic|wet|indifferent|null",
 "elevation_m": [lo, hi] or null,              // Romania/Carpathians if stated, else Central Europe; say which in notes
 "months": "000001111100" or null,             // Central/Eastern European fruiting months, main season only
 "peak_months": [9,10] or null,
 "triggers": "short factual text: rain amount and lag, soil/air temperature thresholds, after first frosts, spring snowmelt, etc. Numbers only if a source states them",
 "temp_c": [lo, hi] or null,                    // only if a source gives a fruiting temperature range
 "rain_lag_days": [lo, hi] or null,             // only if a source gives it
 "abundance_ro": "common|frequent|occasional|rare|unknown",
 "conflicts_with_catalogue": "what the sources contradict in the catalogue entry, or empty",
 "confidence": "high|medium|low",
 "sources": ["https://...", "https://..."]
}

Rules: never invent a URL, number or host; if sources disagree, give the majority and note the disagreement in conflicts_with_catalogue; keep text fields under 300 characters; do not include edibility advice.

OUTPUT: write the JSON list (one object per input species, same order) to {OUTPUT} with the Write tool, then reply with only: the number of species written, how many have >= 2 sources, and the 5 most important catalogue conflicts you found.
