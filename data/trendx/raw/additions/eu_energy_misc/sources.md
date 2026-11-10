# eu_energy_misc: sources, terms, downloads, refusals (run 9 Nov 2026)

All values in `monthly.csv` were parsed by `scripts/build_monthly.py` from files in `raw/`. Nothing was typed.
Requests were made with curl from this machine, one at a time, >= 2.6 s apart per host, default curl identity.

## 1. Ember: European wholesale electricity price data (DONE: UK, Germany, France, Italy, Spain)
- Page: https://ember-energy.org/data/european-wholesale-electricity-price-data/ (raw/ember_index.html)
- Download used: https://files.ember-energy.org/public-downloads/price/outputs/european_wholesale_electricity_price_data_monthly.csv (raw/ember_monthly.csv, 200 OK, 120,961 bytes). Daily CSV and hourly ZIP exist at the same path.
- Licence sentence on the page: "All content is released under a Creative Commons Attribution Licence (CC-BY-4.0)."
- Content: monthly average day-ahead price, EUR/MWhe, 2015-01 .. 2026-11 for each country. 2024-01..2026-11 = 35 rows per country. 2026-11 is a PARTIAL month (today is 9 Nov 2026): flagged in conv_note; drop or refresh at month end.
- United Kingdom is given in EUR/MWh; TE unit is GBP/MWh. Helper file for the conversion: ECB reference rate GBP per EUR, monthly average, 2024-01..2026-10: https://data-api.ecb.europa.eu/service/data/EXR/M.GBP.EUR.SP00.A?format=csvdata&startPeriod=2024-01 (raw/ecb_eur_gbp_monthly.csv). ECB data: free reuse with attribution (ECB copyright notice).
- Not needed because of Ember: GME (Italy PUN), OMIE (Spain), Elexon/Ofgem (UK) were not contacted. ENTSO-E Transparency needs a registered token: not used.

## 2. USDA ERS, U.S. Bioenergy Statistics, table 14 (DONE: Ethanol)
- Page: https://www.ers.usda.gov/data-products/us-bioenergy-statistics (raw/usda_ers_bioenergy.html; page says "Updated: 10/20/2026")
- Download used: https://www.ers.usda.gov/media/6478/us-bioenergy-statistics.csv?v=90008 (raw/usda_ers_bioenergy.csv, 200 OK, 3.19 MB; xlsx also offered at /media/6477/us-bioenergy-statistics.xlsx).
- Series: table 14 "Monthly prices for corn, fuel ethanol, and gasoline", Fuel ethanol, Price, "Freight-on-board, truck and/or rail delivery price", location "IA, MN, NE, SD, (WI,) IL, KS, IN", Dollars per gallon. 2024-01..2026-10 (34 months). The older Omaha FOB rack series in the same table stops before 2024.
- Terms: USDA ERS is a US federal agency; its data products are US Government works (public domain, 17 U.S.C. 105). The ERS page HTML fetched here carried no separate licence sentence; cite "USDA, Economic Research Service, U.S. Bioenergy Statistics".
- USDA AMS My Market News API (weekly ethanol reports) needs a registered API key: not used.

## 3. US BLS Producer Price Index, retrieved via FRED fredgraph CSV (DONE as proxies: Kraft Pulp, Scrap Steel, Scrap Aluminum, HRC Steel)
- Downloads (each 200 OK): https://fred.stlouisfed.org/graph/fredgraph.csv?id=WPU0911&cosd=2024-01-01 (Wood Pulp), ...id=WPU1012... (Iron and Steel Scrap), ...id=WPU102302... (Aluminum Base Scrap), ...id=WPU1017... (Steel Mill Products), ...id=WPU101704... (Hot Rolled Steel Bars, Plates, and Structural Shapes). Series titles verified from the FRED series pages (raw/fred_*_page.html). Data 2024-01..2026-09 (33 months), index 1982=100.
- Also downloaded but NOT usable: WPU10170301 and WPU101703 (Hot Rolled Steel Sheet and Strip) end in 2022-02 (discontinued), so HRC has no direct PPI; WPU1017 (all steel mill products) is the primary proxy, WPU101704 the alternative (series_key hrc_steel_alt).
- Terms: BLS data are US Government public domain. FRED labels these series "Public Domain: Citation requested". FRED Legal (https://fred.stlouisfed.org/legal/, raw/fred_legal.html) says: "Commercial Use Series with the following copyright labels—Public Domain: Citation requested and Copyrighted: Citation required—may be used for internal commercial uses and may be displayed in textbooks, newsletters, or reports to clients provided that appropriate attribution is given to FRED as well as the original source of the data." BUT the same page's prohibited uses include "(p) Store, cache, or archive any portion of the FRED® Services or FRED® Content; ... or incorporate any FRED® Content in any database, compilation, archive, cache, or other medium." The underlying BLS data are public domain; to avoid the FRED clause the series should be re-pulled from BLS directly (api.bls.gov v1 or download.bls.gov/pub/time.series/wp/) before being stored in the panel.
- BLS direct attempts: POST https://api.bls.gov/publicAPI/v1/timeseries/data/ returned "REQUEST_NOT_PROCESSED ... daily threshold for total number of requests ... has been reached" (shared IP quota; raw/bls_ppi_v1.json). https://www.bls.gov/bls/linksite.htm returned 403 (refused; not retried).

## 4. IMF Primary Commodity Prices, monthly workbook (DONE: Cobalt; proxies: Cobalt Hydroxide, Lithium)
- Page: https://www.imf.org/en/Research/commodity-prices (raw/imf_commodity_page.html). The older link .../Monthly/external-data.ashx now returns 404.
- Download used: https://www.imf.org/-/media/files/research/commodityprices/monthly/external-data.xlsx (raw/imf_pcps_external_data.xlsx, 200 OK, 619 KB). Sheet "External", monthly, USD.
- Series: PCOBA "Cobalt, minimum 99.80% purity, LME spot price, USD/ton" and the column headed "Lithium Metal =99%, Battery Grade" (USD, monthly; the code cell is empty in the file). Both 2024-01..2026-08 (32 months; IMF publishes with a lag).
- Terms (https://www.imf.org/en/About/copyright-and-terms, raw/imf_copyright.html): "Users may download, extract, copy, create derivative works, publish, distribute, and use Data obtained from IMF Sites subject to these conditions: Distributed or reproduced Data must appear accurately with attribution to the IMF as the source ..."
- Proxy notes: Cobalt Hydroxide (TE USD/mt) = metal price x payable share; splice on TE level. Lithium (TE CNY/t lithium carbonate China): IMF series is lithium METAL in USD, a different product: use as an index only.
- Note: series.csv already marks cobalt as "IMF PCPS (to add)"; if another worker covers IMF, deduplicate on series_key cobalt.

## 5. US EIA (WEAK proxy for Naphtha)
- EIA has no naphtha price series: https://www.eia.gov/dnav/pet/pet_pri_refoth_dcu_nus_m.htm (raw/eia_refoth.html) lists refiner prices for kerosene, jet fuel, propane, residual fuel etc. but no naphtha/petrochemical feedstock.
- Download used instead: https://www.eia.gov/dnav/pet/hist_xls/EER_EPMRU_PF4_Y35NY_DPGm.xls (raw/eia_gasoline_nyh_m.xls, 200 OK): "New York Harbor Conventional Gasoline Regular Spot Price FOB (Dollars per Gallon)", monthly, 2024-01..2026-10 (34 months). Light-distillate proxy only; use as an index.
- Terms (https://www.eia.gov/about/copyrights_reuse.php, raw/eia_copyright.html): "U.S. government publications are in the public domain and are not subject to copyright protection. You may use and/or distribute any of our data, files, databases, reports, graphs, charts, and other information products that are on our website ..."

## 6. European Commission agri-food data portal (NOT OBTAINED: Butter EUR/100kg, Rapeseed EUR/t)
- Portal: https://agridata.ec.europa.eu/extensions/DataPortal/home.html ; API documentation https://agridata.ec.europa.eu/extensions/DataPortal/API_Documentation.html (raw/agri_api_doc.html) and https://agridata.ec.europa.eu/extensions/API_Documentation/oilseeds.html (raw/agri_api_oilseeds_doc.html) which states "The base url for API endpoints is https://api.tech.ec.europa.eu/agrifood".
- www.ec.europa.eu/agrifood/api/... -> 302 to ec.europa.eu -> 302 to api.tech.ec.europa.eu (resolves and answers from this machine).
- OpenAPI spec downloaded OK: https://api.tech.ec.europa.eu/agrifood/v3/api-docs (raw/agri_openapi_root.json, 116 paths) and .../v3/api-docs/oilseeds (raw/agri_openapi_oilseeds.json). Relevant endpoints and parameters: GET /api/dairy/prices?memberStateCodes=&products=&years=&weeks=&beginDate=dd/mm/yyyy&endDate= ; GET /api/dairy/products ; GET /api/oilseeds/prices?memberStateCodes=&marketingYears=&weeks=&products=&productTypes=&markets=&marketStages=&beginDate=&endDate= ; GET /api/oilseeds/products, /markets.
- Every DATA call failed server-side (not a refusal of this machine): /api/dairy/prices, /api/oilseeds/products, /api/oilseeds/markets -> HTTP 500 {"technicalErrorMessage":"The API cannot provide results. Possibly it does not exist. Please contact us via AGRI-EXT-HELPDESK@ec.europa.eu"}; /api/dairy/products -> HTTP 500 {"code":"303001","description":"Currently , Address endpoint : [ Name : AgrifoodPublicData--vprod_APIproductionEndpoint ] [ State : SUSPENDED ]"}; /v3/api-docs/dairy -> 500. One call timed out at 60 s. Last single retry 07:5x UTC 9 Nov 2026 still 500. The portal's dashboard pages are JavaScript apps with no static CSV link found in the HTML.
- Licence (for when the API is back), https://commission.europa.eu/legal-notice_en (raw/ec_legal_notice.html): "The Commission's reuse policy is implemented by the Commission Decision of 12 December 2011 on the reuse of Commission documents." ... "Creative Commons Attribution 4.0 International (CC BY 4.0) licence. This means that reuse is allowed, provided appropriate credit is given and changes are indicated."
- Suggested retry later: https://api.tech.ec.europa.eu/agrifood/api/dairy/prices?products=butter&beginDate=01/01/2024&endDate=31/12/2026 and https://api.tech.ec.europa.eu/agrifood/api/oilseeds/prices?products=rapeseed&beginDate=01/01/2024&endDate=31/12/2026 (product codes to be confirmed from /api/dairy/products and /api/oilseeds/products).

## 7. USGS National Minerals Information Center (REFUSED: Rhodium, Cobalt, Lithium pages)
- https://www.usgs.gov/centers/national-minerals-information-center/platinum-group-metals-statistics-and-information, .../cobalt-statistics-and-information, .../lithium-statistics-and-information each returned HTTP 403 (raw/usgs_*.html, 919-byte block page). Not retried. Even when reachable, the Mineral Industry Surveys are monthly PDFs (not machine-readable) and USGS price tables are annual.

## Missing after this run
- Butter (EUR/100kg) and Rapeseed (EUR/t): EC API suspended server-side (section 6).
- Rhodium (USD/t oz): no free official monthly series found; USGS refused; Johnson Matthey/LPPM price data are commercial. Not obtained.
- Naphtha: only a weak gasoline proxy (section 5).
- Kraft Pulp (CNY/t), Scrap Steel, Scrap Aluminum, HRC Steel: US PPI indices (proxies), subject to the FRED storage clause unless re-pulled from BLS.
- Lithium (CNY/t carbonate): only IMF lithium metal USD proxy.

## Follow-up (same day, after session resume, ~10:03 UTC 9 Nov 2026)
- EC agri-food API, one more single pass (raw/*_r2.json): /api/dairy/products -> 500 "The API cannot provide results"; /api/oilseeds/products -> timed out at 60 s (no bytes); /api/dairy/prices?products=butter&beginDate=01/01/2024&endDate=09/11/2026 -> HTTP 429 {"code":"900802","message":"Message throttled out" ... "nextAccessTime":"2026-Nov-09 09:05:00+0000 UTC"} (gateway quota, apparently shared); /api/oilseeds/prices?products=rapeseed... -> 500 endpoint "SUSPENDED". After the 429 no further request was sent to api.tech.ec.europa.eu in this run. Butter and Rapeseed remain NOT obtained. Note: series.csv gives Butter's TE unit as EUR/T (the portal publishes EUR/100kg: multiply by 10 when the data become available); Rapeseed already carries a World Bank rapeseed-oil proxy in series.csv.
- BLS flat files: https://download.bls.gov/pub/time.series/wp/ -> HTTP 403 "Access Denied" (raw/bls_wp_dir.html). Refused; not retried. So the PPI proxies stay as pulled from FRED (section 3) with the FRED storage caveat.
- EIA series_name in monthly.csv corrected to the description cell ("New York Harbor Conventional Gasoline Regular Spot Price FOB (Dollars per Gallon)"); values unchanged.
- Ethanol: ERS table 14 location label changes from "IA, MN, NE, SD, WI, IL, KS, IN" (to 2025-04) to "IA, MN, NE, SD, IL, KS, IN" (from 2025-05); same ERS series, kept as one series_key.
