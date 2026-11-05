# TrendX data architecture notes (research step, 5 Nov 2026)

## Recommended (Option A - lowest effort, fits what exists)
Daily cloud scrape (already running) -> build step (Python, same run) writes a tidy "data contract" folder:

data/trendx/
  series.csv          registry / data dictionary: series_id, name_en, name_ar, category, source, source_url,
                      unit, currency, freq (SDMX CL_FREQ: D, B, M), first_actual_date, in_index (0/1),
                      base_2024_mean, base_method ('actual'|'carried_back'), notes
  observations.csv    long format: series_id, period (YYYY-MM-DD or YYYY-MM), freq, value, value_2024eq100,
                      obs_status (SDMX CL_OBS_STATUS: A normal, E estimated, P provisional, R revised...),
                      backfilled (0/1), source, vintage (run_date), ingested_at
  backfill_log.csv    series_id, first_actual_date, first_actual_value, source, carried_back_from, carried_back_to,
                      replaced_on, replaced_by_source
  monthly.csv         month-end/month-mean aggregation of daily series + native monthly series (same columns)
  index.csv           TrendX index (daily + monthly), with method/version column

Rules
- primary key (series_id, period, vintage); latest vintage = current view; older vintages kept (git history + vintage col)
- backfilled values: obs_status='E', backfilled=1; excluded from correlations/models by filter backfilled=0
- 2024=100: value_2024eq100 = 100*value/mean(value over 2024 actual obs) ; if no 2024 actual -> base = first actual
  value (carried back) and base_method='carried_back'; recompute when real history arrives
- daily->monthly: monthly mean of business-day obs (matches TE/World Bank pink-sheet style monthly averages)
- QC before commit: pandera schema (MIT) - unique keys, non-null, value>0, |daily pct change|<threshold, unit unchanged
- CSV in git = versioning + audit; optional DuckDB (MIT) file or Parquet for fast local analysis

Linking to the prototype
- Dataiku (office tool): extend existing dataiku/recipe_github_feed.py pattern -> incremental pull of
  data/trendx/*.csv via GitHub API into SQL datasets (PostgreSQL if the instance has one; Dataiku supports full
  feature range on PostgreSQL); Scenario with time-based trigger daily after the scrape. Avoid Parquet in Dataiku
  (requires Hadoop integration per DSS docs).
- Power BI: read the same CSVs (or a PostgreSQL table). Power BI Parquet connector only reads local / Azure Blob /
  ADLS Gen2.
- Python notebook: pandas/duckdb read_csv of the same files.

## Option B (when volume/users grow)
Central PostgreSQL (PostgreSQL License) with the same 3 tables; scrape job upserts; Dataiku + Power BI connect
natively. Orchestrator only if many jobs: Prefect/Dagster/Airflow OSS are Apache-2.0 (cloud editions are paid).

## Official practice references
- EU Reg 2020/1148 Art.13: new sub-indices are LINKED forward (Dec of year t, used from Jan t+1), not backcast.
  Art.9: estimated price max 2 months. Art.16-19: provisional/revised flagged and released with explanation.
  => The carry-back-to-Jan-2024 rule is a modelling convenience; flag it, exclude from modelling, replace later.
- SDMX: CL_FREQ (D/B/M) and CL_OBS_STATUS (Estimated value, Imputed value, Provisional, Revised...) give
  standard codes for the flags.
