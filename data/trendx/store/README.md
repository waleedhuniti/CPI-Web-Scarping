# TrendX monthly store, base 2024 = 100

Built 2026-11-09 by scripts/trendx/build_history_store.py. World Bank file: "Updated on November 03, 2026". Span 2024-01 to 2026-11.

- series.csv: 95 series (90 in the index, 5 electricity kept outside it). 42 have real 2024 history (base_method actual; 14 of them through a proxy series), 53 are carried back (first collected price held constant to Jan 2024, flagged E / backfilled = 1).
- observations.csv: one row per series and month: value in the TE unit as observed by its source, value_2024eq100, source (wb, eia, te, carried_back), obs_status (A actual, E estimated), backfilled, proxy, linked (1 = a TE month chained onto the external level at link_month, so a spot/futures or market level gap does not appear as a jump).
- backfill_log.csv: the carried-back series with the first actual price, its date and source, as the manager asked; replaced_by stays empty until a history source is added.
- splice_check.csv: months where external history and our own TE monthly mean overlap (Oct 2026): ratio_te_over_external shows the level gap (spot vs futures, market, quality) before the two are chained.
- index_2024.csv: equal-weight geometric mean of the series indices, over the series with actual history and over all series.
Rules: no price carried forward; carried-back values are excluded from correlation and modelling; proxies are real history of a related series and are marked.
Licences: World Bank Pink Sheet CC BY 4.0; EIA public domain (spot prices carry a third-party caveat, internal use); ECB rates free with citation; our TE capture is internal.
Missing TE names (not in the capture): []
