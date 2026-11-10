# Sources: usda_norway_canada (collected 9 Nov 2026)

All files were downloaded from this machine with curl, one request at a time, >= 3 s apart per host.
Raw files are in `raw/`; the normalisation script is `scripts/normalise.py` (run with `python3 -I`);
output is `monthly.csv` (value in the SOURCE unit, `conv_note` gives the path to the TE unit).

## 1. USDA Economic Research Service (ERS) and Agricultural Marketing Service (AMS)

### Files downloaded (all HTTP 200)
| raw file | URL |
|---|---|
| raw/ers_livestock-prices.xlsx | https://www.ers.usda.gov/media/5536/livestock-prices.xlsx?v=48695 (from https://www.ers.usda.gov/data-products/livestock-and-meat-domestic-data) |
| raw/ers_wholesale-prices.xlsx | https://www.ers.usda.gov/media/5538/wholesale-prices.xlsx?v=37798 (same page) |
| raw/ers_us-dairy-situation-at-a-glance-monthly-and-annual.csv / .xlsx | https://www.ers.usda.gov/media/5501/us-dairy-situation-at-a-glance-monthly-and-annual.csv?v=82320 and /media/5500/...xlsx?v=90125 (from https://www.ers.usda.gov/data-products/dairy-data) |
| raw/ers_feed-grains-yearbook-tables-all-years.csv | https://www.ers.usda.gov/media/5766/feed-grains-yearbook-tables-all-years.csv?v=82499 (from https://www.ers.usda.gov/data-products/feed-grains-database/feed-grains-yearbook-tables) |
| raw/ers_us-bioenergy-statistics.csv | https://www.ers.usda.gov/media/6478/us-bioenergy-statistics.csv?v=90008 (from https://www.ers.usda.gov/data-products/us-bioenergy-statistics) |
| raw/ams_datamart_reports.json | https://mpr.datamart.ams.usda.gov/services/v1.1/reports (report list) |
| raw/ams_report_2991.json, raw/ams_report_2991_detail.json | https://mpr.datamart.ams.usda.gov/services/v1.1/reports/2991 and .../reports/2991/Detail ("Announcement of Class and Component Prices", slug DYMCLASSPRICES, Dairy MMR, Washington DC; 176 monthly rows 2012-04..2026-10) |

### Series taken
- live_cattle: ERS livestock-prices.xlsx, sheet Historical, "Nebraska slaughter steers, 65-80 percent Choice, Dollars/cwt" 2024-01..2026-09, plus the sheet Current column "Oct-26/*" (= "Current month estimates", preliminary) for 2026-10.
- feeder_cattle: same file, "Steers: medium and large #1, 750-800 lbs" (Oklahoma City), Dollars/cwt, same months.
- lean_hogs: same file, "Barrows and gilts, producer sold, average net price (live equivalent = carcass x 0.74)", Dollars/cwt live. TE Lean Hogs is a carcass price: divide by 0.74.
- poultry: ERS wholesale-prices.xlsx, "Broilers, National composite, Cents/lb" (proxy for TE Poultry BRL/kg, Brazil).
- eggs_us: same file, "Eggs, Grade A, large, New York, Cents/doz".
- milk: AMS report 2991 Detail field `class_3_Price` (Class III, $/cwt), 2024-01..2026-10.
- cheese: AMS report 2991 Detail field `cheese_monthly_avg_Price` ($/lb; NDPSR monthly average cheese price used in the class price formulas), 2024-01..2026-10. (ERS "dairy situation at a glance" also has Cheddar 40-lb blocks but only from 2025-08, so it is not used.)
- butter: AMS report 2991 Detail field `butter_monthly_avg_Price` ($/lb, NDPSR Grade AA) as a proxy for TE Butter EUR/T.
- oat: ERS Feed Grains Table 10, Oats, price received by farmers, United States, $/bu, 2024-01..2026-08; oat_cash: Table 14, Oats No. 2 or better white heavy, Minneapolis, $/bu, 2024-01..2026-09 (alternative).
- barley_us: ERS Feed Grains Table 10, Barley (all), price received by farmers, United States, $/bu, 2024-01..2026-08 (proxy for TE Barley INR/T).
- ethanol: ERS U.S. Bioenergy Statistics Table 14, Fuel ethanol, "Freight-on-board, truck and/or rail delivery price", Midwest (IA, MN, NE, SD, [WI,] IL, KS, IN), $/gallon, 2024-01..2026-10. (No AMS ethanol report exists in the datamart report list, see below.)

### Licence / terms
- REFUSED: https://www.usda.gov/about-usda/policies-and-links answered HTTP 403 "Access Denied" (Akamai, reference 18.1f53d117.1794206335.2de7a449; body saved as raw/usda_policies.html). It was requested once and not retried; the public-domain sentence therefore could NOT be downloaded and is not quoted here.
- Searched for an equivalent statement on ERS-hosted pages (all 200, saved): https://www.ers.usda.gov/about-ers/policies-and-standards, .../information-quality, .../website, https://www.ers.usda.gov/help. None contains the words "public domain" or "copyright"; the policies index only links back to the refused https://www.usda.gov/policies-and-links.
- Tried the data.gov catalogue API for the dataset's licence field: https://catalog.data.gov/api/3/action/package_search?q=... answered 404 {"message":"Not Found"} (twice, different query) — not reachable at that path, not pursued further.
- What the files themselves say (quoted from the downloaded workbooks): livestock-prices.xlsx: "Source: USDA, Economic Research Service calculations using data from USDA, National Agricultural Statistics Service and USDA, Agricultural Marketing Service." wholesale-prices.xlsx: "Source: USDA Economic Research Service calculations using data from USDA, Agricultural Marketing Service." The AMS datamart JSON carries no terms text.
- Status for the panel: US federal government work (ERS/AMS) — licence sentence not verified by download in this run; mark "US Government work, terms page refused 403 on 9 Nov 2026" until a later run can read usda.gov.

## 2. Statistics Norway (SSB), table 03024

- Metadata: GET https://data.ssb.no/api/v0/en/table/03024 (200) -> raw/ssb_03024_meta.json. Title: "03024: Export of salmon, fish-farm bred, by commodity group, contents and week"; variables VareGrupper2 (01 = Fresh or chilled fish-farm bred salmon), ContentsCode (Vekt = Weight (tonnes), Kilopris = Price per kg (NOK)), Tid weekly 2000U01..2026U44.
- Data: POST https://data.ssb.no/api/v0/en/table/03024 with scripts/ssb_query.json (VareGrupper2=01; ContentsCode=Kilopris,Vekt; Tid=2024U01..2026U44, 148 weeks; json-stat2) -> raw/ssb_03024_salmon_weekly.json (200, 8485 bytes, "updated": "2026-11-04T07:00:00Z").
- Monthly mean: simple arithmetic mean of the weekly NOK/kg prices whose ISO-week Thursday falls in the month (4-5 weeks per month); 2026-10 covers weeks 40-44.
- Licence: https://www.ssb.no/en/diverse/copyright answered 404 (page moved); the footer of SSB pages links to https://www.ssb.no/en/diverse/lisens (200, saved as raw/ssb_lisens.html), which says: "We use the licence Creative Commons Attribution 4.0 International (CC BY 4.0)" and "You are free to: Share — copy and redistribute the material in any medium or format Adapt — remix, transform, and build upon the material for any purpose, even commercially." and "Data containing personal data, and which is confidential, are not covered by this licence and cannot be distributed for further use." Attribution: "Statistics Norway" (source field of the JSON-stat response).

## 3. Statistics Canada, table 32-10-0077-01 (Farm product prices, crops and livestock)

- WDS: GET https://www150.statcan.gc.ca/t1/wds/rest/getFullTableDownloadCSV/32100077/en -> {"status":"SUCCESS","object":"https://www150.statcan.gc.ca/n1/tbl/csv/32100077-eng.zip"} (raw/statcan_wds_32100077.json).
- Download: https://www150.statcan.gc.ca/n1/tbl/csv/32100077-eng.zip (200, 1,512,559 bytes) -> raw/statcan_32100077-eng.zip, extracted to raw/statcan_32100077/32100077.csv (+ 32100077_MetaData.csv). Monthly, 1980-01..2026-08, by province only (no Canada total in this table).
- Series taken (Saskatchewan, the largest producing province, "Dollars per metric tonne"): canola = "Canola (including rapeseed) [113111]" 2024-01..2026-08; barley_ca = "Barley [1151141]" (proxy for TE Barley INR/T); oat_ca = "Oats [115113111]" (alternative for TE Oat). Other provinces (AB, MB, ON, QC, BC) are in the raw CSV if a different reference is wanted.
- Licence: https://www.statcan.gc.ca/en/reference/licence redirects (301) to https://www.statcan.gc.ca/en/terms-conditions/open-licence (200, saved as raw/statcan_licence.html), "Statistics Canada Open Licence": "Subject to this licence, Statistics Canada grants you a worldwide, royalty-free, non-exclusive licence to: use, reproduce, publish, freely distribute, or sell the Information; use, reproduce, publish, freely distribute, or sell Value-added Products; and, sublicence any or all such rights, under terms consistent with this licence." Conditions include: "reproduce the Information accurately; not use the Information in a way that suggests that Statistics Canada endorses you or your use of the Information; not misrepresent the Information or its source".

## Refused or missing
- https://www.usda.gov/about-usda/policies-and-links : HTTP 403 Access Denied (Akamai). Not retried. Public-domain sentence not downloaded.
- https://www.ssb.no/en/diverse/copyright : HTTP 404 (replaced by /en/diverse/lisens, which was used).
- https://catalog.data.gov/api/3/action/package_search : HTTP 404 "Not Found" (API path not served).
- USDA AMS ethanol reports: the AMS datamart report list (154 reports, markets LMR and FMMOS/dairy only) has no ethanol report; AMS "National Weekly Ethanol Summary" exists only as PDF via Market News and was not pursued. ERS Bioenergy Table 14 (Midwest FOB plant price, $/gal, monthly) was used instead.
- ERS Dairy Data "U.S. dairy situation at a glance" monthly series start only in 2025-08 (annual 2024/2025 before that), so it could not supply 2024-01..2025-07; AMS report 2991 was used for milk/cheese/butter.
- StatCan table 32-10-0077 ends 2026-08 (latest release 9 Oct 2026 per file dates); ERS Feed Grains Table 10 ends 2026-08, Table 14 ends 2026-09.
- TE "Eggs US" is quoted by TrendX at about 0.36 USD/dozen (2024 base), which does not match the New York Grade A large wholesale quote (~1.6-3.5 USD/dozen in 2024). The series delivered is the ERS/AMS New York wholesale price in cents/dozen; the mapping to the TE quote needs checking before linking.
