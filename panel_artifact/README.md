# Scraping Projects panel (claude.ai Artifact)

Live page: https://claude.ai/artifact/FSURninVx3TmNCeFYDyxUn

`scraping-panel.html` is the published page. It lists projects (CPI basket, TrendX commodities); inside each one you
run Apify actors through the Apify connector, edit the basket and the actors, change the daily run time, and browse
saved results. Everything is kept in the artifact's database (`projects/<id>`, `projects/<id>/basket`,
`projects/<id>/runs`).

Daily runs are claude.ai Routines (Dubai time): CPI at 08:00 (`trig_018GydPXyp4MkLmnMj8dAoqY`), TrendX at 03:00
(`trig_01FWxfp4cQQtbe3CJxqw9EH4`). The scripts they run are stored in the artifact's `system` collection; copies are
in `routines/`. After changing a script here, write it back to `system/cpi_daily` (`code`) or `system/te_daily`.
