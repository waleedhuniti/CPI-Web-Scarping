# IMF Primary Commodity Price System (PCPS) -- sources, terms, downloads (label: imf, 2026-11-09)

## Licence / terms

Page read: https://www.imf.org/en/About/copyright-and-terms (saved as raw/terms.html, HTTP 200).
The dataset's own LICENSE attribute points to https://www.imf.org/external/terms.htm, which returned an empty
NOINDEX stub (raw/terms_external.html, 392 bytes); the live terms are on the first URL.

Data-reuse sentences, quoted from the "Special Terms for Statistical Data" section:

> For the purposes of these special terms, "Data" refers to published statistical data produced or curated by the IMF, including: [...] Primary Commodity Prices; [...]
> Users may download, extract, copy, create derivative works, publish, distribute, and use Data obtained from IMF Sites subject to these conditions:
> Distributed or reproduced Data must appear accurately with attribution to the IMF as the source, e.g. "Source: International Monetary Fund, Database Name, <<link to the dataset>>."
> Users shall not infringe upon the integrity of the Data and shall refrain from any act of alteration of the Data that intentionally affects its nature or accuracy. If material transformation occurs, it must be stated explicitly along with the required source citation.
> If IMF Data is sold by Users as a standalone product, sellers must inform purchasers that the Data is available free of charge from the IMF.
> For any potential commercial reuse of IMF Data, email copyright@imf.org to request permission.

Restrictions on bulk / automated download, quoted from "Prohibitions and Restrictions":

> The IMF prohibits bulk download of information by automated technology without explicit permission and reserves the right to terminate access to its Sites or Content.
> The IMF does not permit use of its Content or Sites for the training of large language models (LLMs) without explicit permission.

General (non-Data) content clause, for completeness:

> Free non-systematic downloading and/or printing of Content for personal, noncommercial usage only is permitted [...]. IMF written permission must be obtained for other uses, including: Copying or downloading IMF Content in any systematic way.

Assessment: PCPS prices are "Data" under the special terms, so organisational use, derivative works (rebasing to 2024 = 100,
unit conversion) and republication are allowed with the attribution line
"Source: International Monetary Fund, Primary Commodity Price System (PCPS), https://data.imf.org/en/datasets//IMF.RES:PCPS"
(the dataset's SUGGESTED_CITATION attribute). Any transformation (rebasing, FX conversion, proxy use) must be stated.
What was done here is a one-time pull of the public SDMX API, the channel the IMF publishes for machine access:
4 structure requests, 4 codelist requests and 6 data requests in total (the first 5 data requests were key-order/
key-code probes that returned an empty dataset of 2.9 kB each), all >= 2.5 s apart, ~80 price series in one
385 kB response. This is not a bulk crawl of the site; if the office considers it "bulk download by automated
technology", or if the use becomes commercial, permission is requested at copyright@imf.org.

Dataset-level attributes in the download: ACCESS_SHARING_LEVEL=PUBLIC_OPEN, SECURITY_CLASSIFICATION=PUB on every
observation; LICENSE="(c) International Monetary Fund Copyright. All Rights Reserved. https://www.imf.org/external/terms.htm";
UPDATE_DATE=2026-10-06 (latest month 2026-M09).

## Exact download URLs (all HTTP 200, saved under raw/)

| file | URL |
|---|---|
| dataflow_PCPS.xml | https://api.imf.org/external/sdmx/2.1/dataflow/IMF.RES/PCPS |
| dsd_PCPS_children.xml | https://api.imf.org/external/sdmx/2.1/datastructure/IMF.RES/DSD_PCPS/10.0.0?references=children |
| codelist_IMF.RES_CL_PCPS_INDICATOR_3.0.0.xml | https://api.imf.org/external/sdmx/2.1/codelist/IMF.RES/CL_PCPS_INDICATOR/3.0.0 |
| codelist_IMF.RES_CL_PCPS_DATA_TRANSFORMATION_4.0.0.xml | https://api.imf.org/external/sdmx/2.1/codelist/IMF.RES/CL_PCPS_DATA_TRANSFORMATION/4.0.0 |
| codelist_IMF_CL_FREQ_1.2.0.xml | https://api.imf.org/external/sdmx/2.1/codelist/IMF/CL_FREQ/1.2.0 |
| codelist_IMF_CL_UNIT_2.11.2.xml | https://api.imf.org/external/sdmx/2.1/codelist/IMF/CL_UNIT/2.11.2 |
| data_M_W00_all_USD_2024.xml (empty: wrong key order) | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/M.W00..USD?startPeriod=2024 |
| data_W00_all_USD_M_2024.xml (empty: W00 is not a PCPS code) | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/W00..USD.M?startPeriod=2024 |
| test_M_W00_PURAN_USD.xml (empty) | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/M.W00.PURAN.USD?startPeriod=2024 |
| test_W00_PURAN_USD_M.xml (empty) | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/W00.PURAN.USD.M?startPeriod=2024 |
| test_all_2026-09.xml (key discovery; COUNTRY=G001) | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/all?startPeriod=2026-09 |
| **data_G001_all_USD_M_2024.xml (THE data, 93 series, 80 with observations)** | https://api.imf.org/external/sdmx/2.1/data/IMF.RES,PCPS/G001..USD.M?startPeriod=2024 |
| terms.html | https://www.imf.org/en/About/copyright-and-terms |
| terms_external.html (empty stub) | https://www.imf.org/external/terms.htm |

Key structure (DSD_PCPS 10.0.0): COUNTRY.INDICATOR.DATA_TRANSFORMATION.FREQUENCY; COUNTRY is always `G001` (world),
DATA_TRANSFORMATION in {INDEX, INDEX_PCH, INDEX_PCHY, USD}, FREQUENCY in {M, Q, A}. The example key in the task
(`M.W00.PURAN.USD`) returns an empty dataset; the working single-series key would be `G001.PURAN.USD.M`.

## Normalisation

monthly.csv: one row per (IMF code, month), value exactly as OBS_VALUE in the XML (IMF already publishes monthly averages
of daily/weekly quotes, per the dataset FULL_DESCRIPTION), unit = the SOURCE unit (resolved from the code description and
the value magnitude where the code name disagrees: PCOBA is USD/t not USD/lb; PMILK is USD/cwt which equals USc/lb
numerically). conv_note gives the arithmetic to the TE unit; FX factors are NOT in this download (the PCPS exchange-rate
codes T...EREP return zero observations for 2024+), so CNY/INR/AUD/NOK/BRL/EUR conversions need the project's own
monthly FX source. all_pcps_usd_monthly.csv holds every one of the 80 price series (2024-01..2026-09) unmapped, for later use.

## Mapping to TE series (carried-back ones)

| TE series | TE unit | IMF code | IMF unit | relation |
|---|---|---|---|---|
| Uranium | USD/Lbs | PURAN | USD/lb | direct |
| Cobalt | USD/T | PCOBA | USD/t | direct |
| Cobalt Hydroxide | USD/MT | PCOBA | USD/t | proxy (metal) |
| Palladium | USD/t.oz | PPALLA | USD/troy oz | direct |
| Molybdenum | CNY/Kg | PLMMODY | USD/t | proxy market (LME) + FX |
| Oat | USd/Bu | POATS | USD/bu | direct, x100 |
| Wool | AUD/100Kg | PWOOLF (19 micron), PWOOLC (23 micron) | USc/kg | proxy grade + FX (1 USc/kg = 1 USD/100kg) |
| Barley | INR/T | PBARL | USD/t | proxy market (Canada) + FX |
| Milk | USD/CWT | PMILK | USD/cwt | direct |
| Lean Hogs | USd/Lbs | PPORK | USc/lb | direct |
| Live Cattle | USd/Lbs | PBEEF | USc/lb | weak proxy (beef import price) |
| Salmon | NOK/KG | PSALM | USD/kg | same product + FX |
| Lithium | CNY/T | PLITH | USD/t | weak proxy (metal vs carbonate) + FX |
| Silicon | CNY/T | PSILLUMP | USD/t | proxy market + FX |
| Neodymium | CNY/T | PREODOM | USD/t | weak proxy (RE carbonate) + FX |
| Manganese | CNY/mtu | PMANGELE | USD/t | weak proxy (metal vs ore) |

Also included as cross-checks for series that already have WB history: Sunflower Oil (PSUNO), Rapeseed (PROIL, oil not
seed), Beef (PBEEF), Poultry (PPOULT).

## Refused / missing

- Nothing was refused: every request returned HTTP 200, no Retry-After, no challenge.
- Kraft Pulp: code PWPULP exists in CL_PCPS_INDICATOR but has no USD monthly observations in the dataset -> not available.
- No PCPS series for: Methanol, Coking Coal, Naphtha, Ethanol, Steel, HRC Steel, Scrap Steel, Scrap Aluminum, Titanium,
  Aluminum Alloy, Butter, Cheese, Canola (seed), Feeder Cattle (only the PBEEF proxy), Eggs US, Eggs CH, Rhodium, Bitumen,
  Phosphorus, Polyethylene, Polyvinyl, Polypropylene, Synthetic Rubber, Soda Ash, Styrene, Sulfur, Tellurium, Magnesium,
  Gallium, Germanium, Indium, and the five electricity series (UK, Germany, France, Italy, Spain).
- Lamb (PLAMB, PLAMB_L) is in PCPS but TrendX has no Lamb series, so it was not mapped.
- PCPS exchange-rate codes (T111ESN, T...EREP) returned zero observations for 2024+, so no FX factors from this source.
- Latest month is 2026-09 (dataset updated 2026-10-06); 2026-10 is not yet published.
