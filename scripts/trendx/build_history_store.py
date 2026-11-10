"""TrendX unified monthly store with a 2024 = 100 base, from free official history plus our own daily collection.

    python3 scripts/trendx/build_history_store.py <WB CMO-Historical-Data-Monthly.xlsx> <EIA xls dir> <ECB eurofxref-hist.csv> <TE days dir> <out dir> [additions dir = data/trendx/raw/additions]

Sources (all read from files downloaded from the publisher; nothing is typed by hand):
- World Bank Commodity Price Data (Pink Sheet), monthly, CC BY 4.0: the long history for most commodities.
- US EIA daily spot prices (public domain): WTI, Brent, Henry Hub, NY Harbor gasoline and heating oil, Mont Belvieu propane,
  averaged to months.
- ECB euro reference rates (free with citation): monthly mean rates to convert $ series to the TE quote currency.
- Our own Trading Economics capture (data/portal/te/days or the Commodity Price Log): daily closes averaged to months, from
  Oct 2026; these are the ONLY observations of source "te".

Rules (the manager's note of 5 Nov 2026):
- Every series is rebased to the mean of its 2024 monthly values = 100 (base_method "actual" when 2024 comes from external
  history, "carried_back" when the first collected price was held constant back to Jan 2024).
- A carried-back value is flagged obs_status "E" (estimated), backfilled = 1, logged in backfill_log.csv, and must be excluded
  from correlation and modelling; it is replaced by real history when a source is found.
- A proxy series (a related product, another quality or market) is marked proxy = 1 with the proxy named; it is real history of
  a different thing, not an estimate of ours.
- Daily series become monthly means over the days quoted; a month with no quote is left out (never carried).
Outputs (long format, UTF-8 CSV): series.csv, observations.csv, backfill_log.csv, splice_check.csv, index_2024.csv, README.md
"""
import csv
import glob
import json
import statistics
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

import openpyxl
import xlrd

LB_PER_KG = 2.2046226218
BU_KG = {"soy": 27.2155, "wheat": 27.2155, "corn": 25.4012, "oat": 14.515}
MMBTU_PER_MWH = 3.412142
THERM_MMBTU = 0.1

# TE commodity -> how its 2024.. monthly history is built.
# kind: wb (World Bank column), eia (EIA sourcekey), none. f: multiplier applied to the source value after FX. fx: TE currency
# whose monthly rate per USD multiplies the value (ECB table gives units per EUR; per USD = rate / USD rate). proxy: name of
# the proxy series when the source is not the same product/market as TE's quote. unit_note explains the conversion.
MAP = {
    # Energy
    "Crude Oil": dict(kind="eia", key="RWTC", f=1, note="EIA WTI Cushing spot $/bbl (daily mean); WB WTI as fallback", wb="Crude oil, WTI"),
    "Brent": dict(kind="eia", key="RBRTE", f=1, note="EIA Europe Brent spot $/bbl (daily mean)", wb="Crude oil, Brent"),
    "Natural gas": dict(kind="eia", key="RNGWHHD", f=1, note="EIA Henry Hub spot $/mmbtu (daily mean)", wb="Natural gas, US"),
    "Gasoline": dict(kind="eia", key="EER_EPMRU_PF4_Y35NY_DPG", f=1, note="EIA NY Harbor conventional gasoline spot $/gal (daily mean); TE quotes RBOB futures", proxy="NYH conventional gasoline spot"),
    "Heating Oil": dict(kind="eia", key="EER_EPD2F_PF4_Y35NY_DPG", f=1, note="EIA NY Harbor No.2 heating oil spot $/gal (daily mean)"),
    "Propane": dict(kind="eia", key="EER_EPLLPA_PF4_Y44MB_DPG", f=1, note="EIA Mont Belvieu propane spot $/gal (daily mean)"),
    "Coal": dict(kind="wb", col="Coal, Australian", f=1, note="WB Coal Australian (Newcastle) $/mt"),
    "EU Gas": dict(kind="wb", col="Natural gas, Europe", f=MMBTU_PER_MWH, fx="EUR", note="WB Natural gas Europe (TTF) $/mmbtu x 3.412 mmbtu/MWh / USD per EUR = EUR/MWh"),
    "German Gas": dict(kind="wb", col="Natural gas, Europe", f=MMBTU_PER_MWH, fx="EUR", proxy="TTF (WB Europe gas)", note="THE hub tracks TTF closely; TTF used as proxy"),
    "UK Gas": dict(kind="wb", col="Natural gas, Europe", f=THERM_MMBTU * 100, fx="GBP", proxy="TTF (WB Europe gas)", note="$/mmbtu x 0.1 mmbtu/therm / USD per GBP x 100 = GBp/therm; NBP proxied by TTF"),
    "LNG JKM": dict(kind="wb", col="Liquefied natural gas, Japan", f=1, proxy="WB LNG Japan import price", note="Japan LNG import (contract) price $/mmbtu as proxy for JKM spot"),
    "Urals Oil": dict(kind="wb", col="Crude oil, Dubai", f=1, proxy="WB Dubai crude", note="medium sour benchmark as proxy; Urals carries a discount since 2022"),
    "Uranium": dict(kind="none", note="not in WB; IMF PCPS has a monthly uranium series (to add)"),
    "Methanol": dict(kind="none", note="China NBS 10-day prices (to add)"),
    "Coking Coal": dict(kind="none", note="no free licensed monthly series verified"),
    "Naphtha": dict(kind="none", note="no free history found"),
    "Ethanol": dict(kind="none", note="USDA AMS ethanol reports (to add)"),
    # Metals
    "Gold": dict(kind="wb", col="Gold", f=1, note="WB gold $/troy oz"),
    "Silver": dict(kind="wb", col="Silver", f=1, note="WB silver $/troy oz"),
    "Platinum": dict(kind="wb", col="Platinum", f=1, note="WB platinum $/troy oz"),
    "Copper": dict(kind="wb", col="Copper", f=1 / 2204.6226, note="WB copper $/mt / 2204.62 = $/lb"),
    "Iron Ore": dict(kind="wb", col="Iron ore, cfr spot", f=1, note="WB iron ore cfr China $/dmt (the sheet header says $/dmtu, the values are per tonne of 62% fines)"),
    "Iron Ore CNY": dict(kind="wb", col="Iron ore, cfr spot", f=1, fx="CNY", proxy="WB iron ore cfr China in CNY", note="$/dmt x CNY per USD; Dalian futures proxied by the seaborne spot"),
    "Steel": dict(kind="none", note="Shanghai rebar: NBS 10-day 螺纹钢 (to add)"),
    "HRC Steel": dict(kind="none", note="no free licensed series verified"),
    "Scrap Steel": dict(kind="none", note="no free licensed series verified"),
    "Scrap Aluminum": dict(kind="none", note="no free licensed series verified"),
    "Lithium": dict(kind="none", note="no free licensed monthly series (USGS annual only)"),
    "Silicon": dict(kind="none", note="no free licensed monthly series"),
    "Titanium": dict(kind="none", note="USGS annual only"),
    "Aluminum Alloy": dict(kind="none", note="no free licensed series"),
    "Cobalt Hydroxide": dict(kind="none", note="no free licensed series"),
    # Agricultural
    "Soybeans": dict(kind="wb", col="Soybeans", f=BU_KG["soy"] / 1000 * 100, note="WB soybeans $/mt x 0.0272 t/bu x 100 = US cents/bu"),
    "Wheat": dict(kind="wb", col="Wheat, US SRW", f=BU_KG["wheat"] / 1000 * 100, note="WB US SRW $/mt x 0.0272 x 100 = cents/bu (CBOT contract is SRW)"),
    "Corn": dict(kind="wb", col="Maize", f=BU_KG["corn"] / 1000 * 100, note="WB maize (US Gulf) $/mt x 0.0254 x 100 = cents/bu"),
    "Oat": dict(kind="none", note="IMF PCPS oats (to add)"),
    "Rice": dict(kind="wb", col="Rice, Thai 5% ", f=1 / 22.0462, proxy="WB Thai 5% white rice", note="$/mt / 22.046 = $/cwt; TE quotes CBOT rough rice"),
    "Palm Oil": dict(kind="wb", col="Palm oil", f=1, fx="MYR", note="WB palm oil $/mt x MYR per USD = MYR/t"),
    "Rubber": dict(kind="wb", col="Rubber, TSR20 **", f=100, note="WB TSR20 $/kg x 100 = US cents/kg"),
    "Coffee": dict(kind="wb", col="Coffee, Arabica", f=100 / LB_PER_KG, note="WB arabica $/kg / 2.2046 x 100 = cents/lb"),
    "Cotton": dict(kind="wb", col="Cotton, A Index", f=100 / LB_PER_KG, note="WB cotton A index $/kg -> cents/lb"),
    "Sugar": dict(kind="wb", col="Sugar, world", f=100 / LB_PER_KG, note="WB sugar world (ISA) $/kg -> cents/lb"),
    "Cocoa": dict(kind="wb", col="Cocoa", f=1000, note="WB cocoa $/kg x 1000 = $/t"),
    "Tea": dict(kind="wb", col="Tea, Kolkata", f=1, fx="INR", note="WB tea Kolkata $/kg x INR per USD = INR/kg"),
    "Sunflower Oil": dict(kind="wb", col="Sunflower oil", f=1 / 100, fx="INR", proxy="WB sunflower oil (world) in INR", note="$/mt / 100 = $/10kg x INR per USD; TE quotes an Indian market"),
    "Barley": dict(kind="wb", col="Barley", f=1, fx="INR", proxy="WB barley (world) in INR", note="$/mt x INR per USD; TE quotes an Indian market"),
    "Rapeseed": dict(kind="wb", col="Rapeseed oil", f=1, fx="EUR", proxy="WB rapeseed OIL", note="oil, not seed: a proxy for Euronext rapeseed EUR/t"),
    "Orange Juice": dict(kind="wb", col="Orange", f=100 / LB_PER_KG, proxy="WB oranges (fruit)", note="fruit price as proxy for FCOJ cents/lb"),
    "Lumber": dict(kind="wb", col="Sawnwood, Malaysian", f=1, proxy="WB sawnwood Malaysian $/m3", note="different product and unit; movement proxy only"),
    "Butter": dict(kind="none", note="EC agri-food portal butter EUR/100kg (to add)"),
    "Milk": dict(kind="none", note="USDA AMS / IMF dairy (to add)"),
    "Cheese": dict(kind="none", note="USDA AMS cheddar (to add)"),
    "Canola": dict(kind="none", note="StatCan canola CAD/t (to add)"),
    "Wool": dict(kind="none", note="IMF PCPS wool (to add)"),
    # Livestock
    "Beef": dict(kind="wb", col="Beef **", f=15, fx="BRL", proxy="WB beef (Australia/US import) in BRL", note="$/kg x 15 kg x BRL per USD = BRL/15kg (arroba); TE quotes Brazilian fed cattle"),
    "Poultry": dict(kind="wb", col="Chicken **", f=1, fx="BRL", proxy="WB chicken (Brazil wholesale) in BRL", note="$/kg x BRL per USD = BRL/kg"),
    "Live Cattle": dict(kind="none", note="USDA AMS fed steers (to add)"),
    "Feeder Cattle": dict(kind="none", note="USDA AMS feeder steers (to add)"),
    "Lean Hogs": dict(kind="none", note="USDA AMS hogs (to add)"),
    "Eggs US": dict(kind="none", note="USDA AMS egg markets (to add)"),
    "Eggs CH": dict(kind="none", note="no free licensed series"),
    "Salmon": dict(kind="none", note="Statistics Norway table 03024 weekly NOK/kg (to add)"),
    # Industrial
    "Aluminum": dict(kind="wb", col="Aluminum", f=1, note="WB aluminum (LME) $/mt"),
    "Lead": dict(kind="wb", col="Lead", f=1, note="WB lead $/mt"),
    "Tin": dict(kind="wb", col="Tin", f=1, note="WB tin $/mt"),
    "Zinc": dict(kind="wb", col="Zinc", f=1, note="WB zinc $/mt"),
    "Nickel": dict(kind="wb", col="Nickel", f=1, note="WB nickel $/mt"),
    "Urea": dict(kind="wb", col="Urea ", f=1, note="WB urea (E. Europe bulk) $/mt; TE quotes Middle East granular", proxy="WB urea E. Europe"),
    "Di-ammonium": dict(kind="wb", col="DAP", f=1, note="WB DAP $/mt"),
    "Cobalt": dict(kind="none", note="IMF PCPS cobalt (to add)"),
    "Palladium": dict(kind="none", note="IMF PCPS palladium (to add)"),
    "Molybdenum": dict(kind="none", note="IMF PCPS molybdenum in USD (to add); TE quotes CNY/kg"),
    "Rhodium": dict(kind="none", note="USGS annual only"),
    "Bitumen": dict(kind="none", note="no free licensed series"),
    "Phosphorus": dict(kind="none", note="no free licensed series"),
    "Polyethylene": dict(kind="none", note="NBS 10-day (to add)"),
    "Polyvinyl": dict(kind="none", note="NBS 10-day (to add)"),
    "Polypropylene": dict(kind="none", note="NBS 10-day (to add)"),
    "Synthetic Rubber": dict(kind="none", note="NBS 10-day (to add)"),
    "Soda Ash": dict(kind="none", note="USGS annual only"),
    "Neodymium": dict(kind="none", note="USGS annual only"),
    "Styrene": dict(kind="none", note="NBS 10-day (to add)"),
    "Sulfur": dict(kind="none", note="USGS annual only"),
    "Tellurium": dict(kind="none", note="USGS annual only"),
    "Magnesium": dict(kind="none", note="USGS annual only"),
    "Gallium": dict(kind="none", note="USGS annual only"),
    "Germanium": dict(kind="none", note="USGS annual only"),
    "Manganese": dict(kind="none", note="no free licensed series"),
    "Indium": dict(kind="none", note="USGS annual only"),
    "Kraft Pulp": dict(kind="none", note="no free licensed series"),
    # Electricity (excluded from the index; kept in the store)
    "United Kingdom": dict(kind="none", note="electricity: no free licensed day-ahead history verified"),
    "Germany": dict(kind="none", note="electricity: ENTSO-E transparency platform (registration; to assess)"),
    "France": dict(kind="none", note="electricity: ENTSO-E (to assess)"),
    "Italy": dict(kind="none", note="electricity: GME publishes PUN (terms to check)"),
    "Spain": dict(kind="none", note="electricity: OMIE (terms to check)"),
}
BASE_FROM, BASE_TO = "2024-01", "2024-12"

# Additions: free official monthly series for the commodities the Pink Sheet / EIA do not cover, normalised by the fetch scripts
# into data/trendx/raw/additions/<folder>/monthly.csv (series_key, commodity_te, period, value, unit, source, series_name, url).
# cur_from/cur_to: the value's currency and the TE quote currency (converted with the ECB monthly mean rates); f: multiplier after FX.
# proxy "" means the same product and market as the TE quote; otherwise the proxy is named and the series is flagged proxy = 1.
ADD_LICENCE = {"imf": "IMF Special Terms for Statistical Data: free reuse with attribution (Source: IMF Primary Commodity Price System)",
               "usda_norway_canada": "USDA ERS/AMS public domain; Statistics Norway (NLOD/CC BY 4.0); Statistics Canada Open Licence",
               "eu_energy_misc": "Ember CC BY 4.0; US BLS public domain; ECB rates free with citation",
               "nbs_china": "China NBS terms of service: free use of published statistics with citation of the NBS website"}
ADD_SRC = {"imf": "imf", "usda_norway_canada": "usda", "eu_energy_misc": "ember", "nbs_china": "nbs"}
ADD = {
    "Uranium": dict(folder="imf", key="imf_pcps_PURAN", f=1, cur_from="USD", cur_to="USD", proxy="", note="IMF PCPS uranium NUEXCO spot $/lb"),
    "Methanol": dict(folder="nbs_china", key="methanol", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day methanol (premium grade) CNY/t, monthly mean"),
    "Coking Coal": dict(folder="nbs_china", key="coking_coal", f=1, cur_from="CNY", cur_to="USD", proxy="NBS China domestic coking coal (TE quotes Australian futures)", note="CNY/t / CNY per USD = $/t"),
    "Ethanol": dict(folder="usda_norway_canada", key="ethanol", f=1, cur_from="USD", cur_to="USD", proxy="", note="USDA ERS fuel ethanol FOB $/gal"),
    "Steel": dict(folder="nbs_china", key="steel", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day rebar HRB400E 20mm CNY/t, monthly mean (TE quotes Shanghai rebar)"),
    "HRC Steel": dict(folder="nbs_china", key="热轧普通板卷", f=1, cur_from="CNY", cur_to="USD", proxy="NBS China hot-rolled coil Q235 (TE quotes US HRC)", note="CNY/t / CNY per USD = $/t", all_products=True, src="nbs"),
    "Scrap Steel": dict(folder="eu_energy_misc", key="scrap_steel", f=1, cur_from="USD", cur_to="USD", proxy="BLS PPI iron and steel scrap (index 1982 = 100, movement only)", note="an index level, not a $/t price", src="bls"),
    "Scrap Aluminum": dict(folder="eu_energy_misc", key="scrap_aluminum", f=1, cur_from="USD", cur_to="USD", proxy="BLS PPI aluminum base scrap (index 1982 = 100, movement only)", note="an index level, not a $/t price", src="bls"),
    "Lithium": dict(folder="imf", key="imf_pcps_PLITH", f=1, cur_from="USD", cur_to="CNY", proxy="IMF lithium metal battery grade (TE quotes China lithium carbonate)", note="$/t x CNY per USD; different product, movement only"),
    "Silicon": dict(folder="imf", key="imf_pcps_PSILLUMP", f=1, cur_from="USD", cur_to="CNY", proxy="IMF silicon lumps CIF NW Europe (TE quotes China silicon metal)", note="$/t x CNY per USD"),
    "Cobalt Hydroxide": dict(folder="imf", key="imf_pcps_PCOBA", f=1, cur_from="USD", cur_to="USD", proxy="IMF cobalt metal LME (TE quotes China CIF hydroxide)", note="$/t; hydroxide is priced as a payable % of metal"),
    "Oat": dict(folder="imf", key="imf_pcps_POATS", f=100, cur_from="USD", cur_to="USD", proxy="", note="IMF oats generic 1st future $/bu x 100 = cents/bu"),
    "Barley": dict(folder="imf", key="imf_pcps_PBARL", f=1, cur_from="USD", cur_to="INR", proxy="IMF Canadian feed barley (TE quotes an Indian market)", note="$/t x INR per USD = INR/t"),
    "Butter": dict(folder="usda_norway_canada", key="butter", f=LB_PER_KG * 1000, cur_from="USD", cur_to="EUR", proxy="USDA/CME butter (TE quotes EU butter)", note="$/lb x 2204.6 lb/t / USD per EUR = EUR/t"),
    "Milk": dict(folder="usda_norway_canada", key="milk", f=1, cur_from="USD", cur_to="USD", proxy="", note="USDA Class III milk $/cwt (the CME contract settles on it)"),
    "Cheese": dict(folder="usda_norway_canada", key="cheese", f=1, cur_from="USD", cur_to="USD", proxy="", note="USDA cheese price used in class formulas $/lb (CME cheese)"),
    "Canola": dict(folder="usda_norway_canada", key="canola", f=1, cur_from="CAD", cur_to="CAD", proxy="Statistics Canada Saskatchewan farm price (TE quotes ICE futures)", note="CAD/t", src="statcan"),
    "Wool": dict(folder="imf", key="imf_pcps_PWOOLF", f=1, cur_from="USD", cur_to="AUD", proxy="IMF AWEX 19-micron fine wool (TE quotes the Eastern Market Indicator)", note="US cents/kg = $/100kg, x AUD per USD = AUD/100kg"),
    "Live Cattle": dict(folder="usda_norway_canada", key="live_cattle", f=1, cur_from="USD", cur_to="USD", proxy="", note="USDA fed steers Nebraska $/cwt = cents/lb"),
    "Feeder Cattle": dict(folder="usda_norway_canada", key="feeder_cattle", f=1, cur_from="USD", cur_to="USD", proxy="", note="USDA feeder steers Oklahoma City $/cwt = cents/lb"),
    "Lean Hogs": dict(folder="usda_norway_canada", key="lean_hogs", f=1, cur_from="USD", cur_to="USD", proxy="USDA barrows and gilts live weight (TE quotes lean carcass basis)", note="$/cwt live = cents/lb"),
    "Eggs US": dict(folder="usda_norway_canada", key="eggs_us", f=0.01, cur_from="USD", cur_to="USD", proxy="", note="USDA New York wholesale grade A large cents/dozen / 100"),
    "Salmon": dict(folder="usda_norway_canada", key="salmon", f=1, cur_from="NOK", cur_to="NOK", proxy="", note="Statistics Norway export price fresh farmed salmon NOK/kg (weekly, monthly mean)", src="ssb"),
    "Cobalt": dict(folder="imf", key="imf_pcps_PCOBA", f=1, cur_from="USD", cur_to="USD", proxy="", note="IMF cobalt min 99.8% LME spot $/t"),
    "Palladium": dict(folder="imf", key="imf_pcps_PPALLA", f=1, cur_from="USD", cur_to="USD", proxy="", note="IMF palladium $/troy oz"),
    "Molybdenum": dict(folder="imf", key="imf_pcps_PLMMODY", f=1 / 1000, cur_from="USD", cur_to="CNY", proxy="IMF LME molybdenum concentrate (TE quotes China domestic)", note="$/t x CNY per USD / 1000 = CNY/kg"),
    "Polyethylene": dict(folder="nbs_china", key="polyethylene", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day LLDPE CNY/t"),
    "Polyvinyl": dict(folder="nbs_china", key="polyvinyl", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day PVC SG5 CNY/t (series ends Dec 2025 in the NBS tables)"),
    "Polypropylene": dict(folder="nbs_china", key="polypropylene", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day PP raffia CNY/t"),
    "Synthetic Rubber": dict(folder="nbs_china", key="synthetic_rubber", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day BR9000 CNY/t"),
    "Styrene": dict(folder="nbs_china", key="styrene", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day styrene CNY/t (series ends Dec 2025 in the NBS tables)"),
    "Sulfur": dict(folder="nbs_china", key="sulfur", f=1, cur_from="CNY", cur_to="CNY", proxy="NBS sulfuric acid 98% (TE quotes sulphur)", note="CNY/t, related product"),
    "Neodymium": dict(folder="imf", key="imf_pcps_PREODOM", f=1, cur_from="USD", cur_to="CNY", proxy="IMF rare-earth carbonate REO 42-45% (TE quotes Nd metal)", note="$/t x CNY per USD; movement only"),
    "Manganese": dict(folder="imf", key="imf_pcps_PMANGELE", f=1, cur_from="USD", cur_to="CNY", proxy="IMF electrolytic manganese metal (TE quotes 44% ore per mtu)", note="$/t x CNY per USD = CNY/t of metal; movement only"),
    "Kraft Pulp": dict(folder="nbs_china", key="kraft_pulp", f=1, cur_from="CNY", cur_to="CNY", proxy="", note="NBS 10-day imported softwood pulp CNY/t"),
    "United Kingdom": dict(folder="eu_energy_misc", key="united_kingdom", f=1, cur_from="EUR", cur_to="GBP", proxy="", note="Ember day-ahead monthly mean EUR/MWh / GBP per EUR"),
    "Germany": dict(folder="eu_energy_misc", key="germany", f=1, cur_from="EUR", cur_to="EUR", proxy="", note="Ember day-ahead monthly mean EUR/MWh"),
    "France": dict(folder="eu_energy_misc", key="france", f=1, cur_from="EUR", cur_to="EUR", proxy="", note="Ember day-ahead monthly mean EUR/MWh"),
    "Italy": dict(folder="eu_energy_misc", key="italy", f=1, cur_from="EUR", cur_to="EUR", proxy="", note="Ember day-ahead monthly mean EUR/MWh"),
    "Spain": dict(folder="eu_energy_misc", key="spain", f=1, cur_from="EUR", cur_to="EUR", proxy="", note="Ember day-ahead monthly mean EUR/MWh"),
}
# still without any free monthly source after the Nov 2026 search (kept carried back, flagged E): Naphtha (NY gasoline rejected as a
# different product), Titanium, Aluminum Alloy, Eggs CH, Rhodium, Bitumen, Phosphorus, Soda Ash, Tellurium, Magnesium, Gallium,
# Germanium, Indium (only paid Asian Metal / SMM quotes exist; USGS is annual).


def read_additions(d):
    """{(folder, series_key): {ym: value}} plus {(folder, key): meta} from the normalised monthly CSVs."""
    vals, meta = defaultdict(dict), {}
    for f in glob.glob(str(Path(d) / "*" / "monthly.csv")):
        folder = Path(f).parent.name
        for r in csv.DictReader(open(f, encoding="utf-8")):
            try: v = float(r["value"])
            except (ValueError, TypeError): continue
            k = (folder, r["series_key"]); vals[k][r["period"][:7]] = v
            meta.setdefault(k, dict(unit=r.get("unit", ""), source=r.get("source", ""), series_name=r.get("series_name", ""), url=r.get("url", "")))
    f = Path(d) / "nbs_china" / "monthly_all_products.csv"
    if f.exists():
        for r in csv.DictReader(open(f, encoding="utf-8")):
            try: v = float(r["value"])
            except (ValueError, TypeError): continue
            k = ("nbs_china", r["product"]); vals[k][r["period"][:7]] = v
            meta.setdefault(k, dict(unit=f"CNY/{r.get('unit_cn', '')}", source="China NBS, Market Prices of Important Means of Production in Circulation (10-day report)", series_name=r.get("specs", r["product"]), url="https://www.stats.gov.cn/sj/zxfb/"))
    return vals, meta



def months(a, b):
    y, m = map(int, a.split("-")); out = []
    while f"{y:04d}-{m:02d}" <= b:
        out.append(f"{y:04d}-{m:02d}"); m += 1
        if m > 12: y, m = y + 1, 1
    return out


def read_wb(path):
    ws = openpyxl.load_workbook(path, read_only=True, data_only=True)["Monthly Prices"]
    rows = list(ws.iter_rows(values_only=True))
    hdr, units = rows[4], rows[5]
    cols = {h: i for i, h in enumerate(hdr) if h}
    out = {h: {} for h in cols}
    for r in rows[6:]:
        if not r[0] or not str(r[0])[:4].isdigit(): continue
        ym = f"{str(r[0])[:4]}-{str(r[0])[5:7]}"
        for h, i in cols.items():
            v = r[i]
            if isinstance(v, (int, float)): out[h][ym] = float(v)
    return out, {h: units[i] for h, i in cols.items()}, str(rows[3][0])


def read_eia_dir(d):
    out = {}
    for f in glob.glob(str(Path(d) / "eia_*.xls")):
        b = xlrd.open_workbook(f); s = b.sheet_by_name("Data 1")
        key = str(s.row(1)[1].value).strip(); title = str(s.row(2)[1].value)
        daily = defaultdict(list)
        for i in range(3, s.nrows):
            d0, v = s.row(i)[0].value, s.row(i)[1].value
            if not isinstance(v, (int, float)) or not d0: continue
            y, m, *_ = xlrd.xldate_as_tuple(d0, b.datemode)
            daily[f"{y:04d}-{m:02d}"].append(float(v))
        out[key] = dict(title=title, monthly={k: statistics.fmean(v) for k, v in daily.items()}, days={k: len(v) for k, v in daily.items()})
    return out


def read_ecb(path):
    rows = list(csv.DictReader(open(path, encoding="utf-8")))
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        ym = r["Date"][:7]
        for cur, v in r.items():
            if cur in ("Date", "") or v in ("N/A", "", None): continue
            try: acc[ym][cur].append(float(v))
            except ValueError: pass
    per_eur = {ym: {c: statistics.fmean(v) for c, v in cs.items()} for ym, cs in acc.items()}
    def per_usd(ym, cur):
        r = per_eur.get(ym);
        if not r or "USD" not in r: return None
        if cur == "EUR": return 1 / r["USD"]
        return r[cur] / r["USD"] if cur in r else None
    return per_usd


def read_te_days(d):
    """daily TE closes -> {commodity: {ym: [prices]}}, plus unit and category per commodity."""
    series, meta = defaultdict(lambda: defaultdict(list)), {}
    for f in sorted(glob.glob(str(Path(d) / "**/*.json"), recursive=True)):
        doc = json.load(open(f, encoding="utf-8")); doc = doc.get("data", doc)
        if "rows" not in doc: continue
        cols = doc.get("cols"); run = doc.get("run_date", Path(f).stem)
        for r in doc["rows"]:
            r = dict(zip(cols, r)) if cols else r
            p = r.get("price")
            if p in (None, "") or r.get("category") == "Index": continue
            pd_ = r.get("price_date") or run
            series[r["commodity"]][pd_[:7]].append(float(p))
            meta[r["commodity"]] = dict(unit=r.get("unit", ""), category=r.get("category", ""))
    return series, meta


def main(wb_path, eia_dir, ecb_csv, te_dir, out_dir, add_dir="data/trendx/raw/additions"):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True)
    wb, wb_units, wb_stamp = read_wb(wb_path); eia = read_eia_dir(eia_dir); fx = read_ecb(ecb_csv); te, meta = read_te_days(te_dir)
    adds, add_meta = read_additions(add_dir) if add_dir and Path(add_dir).exists() else ({}, {})
    def conv_cur(ym, v, cur_from, cur_to):
        if cur_from == cur_to: return v
        a = 1.0 if cur_from == "USD" else fx(ym, cur_from); b = 1.0 if cur_to == "USD" else fx(ym, cur_to)
        return None if a is None or b is None or not a else v / a * b
    last_te = max((ym for s in te.values() for ym in s), default="2026-10")
    span = months(BASE_FROM, last_te)
    series_rows, obs, backfill, splice, missing, link_months = [], [], [], [], [], {}
    for name, m in MAP.items():
        if name not in meta: missing.append(name); continue
        unit, cat = meta[name]["unit"], meta[name]["category"]
        sid = name.lower().replace(" ", "_")
        ext = {}; src = ""; src_series = ""; licence = ""
        if m["kind"] == "wb":
            col = m["col"]; src, src_series, licence = "World Bank Pink Sheet", f"{col} {wb_units.get(col, '')}", "CC BY 4.0"
            ext = dict(wb.get(col, {}))
        elif m["kind"] == "eia":
            e = eia.get(m["key"]); src, licence = "US EIA spot price", "US Government public domain (third-party caveat)"
            if e: src_series = e["title"]; ext = dict(e["monthly"])
            elif m.get("wb"): col = m["wb"]; src, src_series, licence = "World Bank Pink Sheet", f"{col} {wb_units.get(col, '')}", "CC BY 4.0"; ext = dict(wb.get(col, {}))
        a = ADD.get(name) if (m["kind"] == "none" or not any(ym >= BASE_FROM for ym in ext)) else None   # a WB column that stopped before 2024 (barley) falls through to the additions
        if a and (a["folder"], a["key"]) in adds:
            am = add_meta[(a["folder"], a["key"])]; ext = dict(adds[(a["folder"], a["key"])])
            src, src_series, licence = am["source"], f"{am['series_name']} [{am['unit']}]", ADD_LICENCE.get(a["folder"], "")
            m = dict(m, kind="add", f=a["f"], proxy=a["proxy"], note=a["note"], add=a)
        conv = {}
        for ym, v in ext.items():
            if ym < BASE_FROM or ym > last_te: continue
            val = v * m["f"]
            if m.get("add"):
                val = conv_cur(ym, val, m["add"]["cur_from"], m["add"]["cur_to"])
                if val is None: continue
            elif m.get("fx"):
                r = fx(ym, m["fx"])
                if r is None: continue
                val *= r
            conv[ym] = val
        te_m = {ym: statistics.fmean(v) for ym, v in te[name].items() if ym >= BASE_FROM}
        base_vals = [conv[ym] for ym in months(BASE_FROM, BASE_TO) if ym in conv]
        if len(base_vals) >= 10:
            base, base_method = statistics.fmean(base_vals), "actual"
        else:
            first_ym = min(te_m) if te_m else None
            base = te_m[first_ym] if first_ym else None; base_method = "carried_back"
        proxy = 1 if m.get("proxy") else 0
        # chain link: external history up to the last month both sources cover (L), then our TE monthly means continue the
        # index from the external level at L (a futures/spot or market level gap never shows as a jump in the index)
        overlap = sorted(set(conv) & set(te_m)); L = overlap[-1] if overlap else None
        ext_src = (m["add"].get("src") or ADD_SRC[m["add"]["folder"]]) if m.get("add") else "wb" if m["kind"] == "wb" or not eia.get(m.get("key", "")) else "eia"
        # a proxy from an external source that has not yet published the first TE month cannot be chained: its TE months wait
        # for the overlap month instead of being rebased onto a different level (same-product sources need no link)
        wait_overlap = bool(m.get("add")) and bool(m.get("proxy")) and L is None
        for ym in span:
            linked = 0
            if ym in conv and (L is None or ym <= L):
                val, source, status, bf = conv[ym], ext_src, "A", 0
                idx = val / base * 100
            elif ym in te_m:
                if wait_overlap: continue
                val, source, status, bf = te_m[ym], "te", "A", 0
                if L is not None: idx = conv[L] / base * 100 * te_m[ym] / te_m[L]; linked = 1
                else: idx = val / base * 100 if base else None
            elif base_method == "carried_back" and base is not None and ym < min(te_m):
                val, source, status, bf = base, "carried_back", "E", 1; idx = 100.0
            else:
                continue
            obs.append(dict(series_id=sid, commodity=name, period=ym, freq="M", value=round(val, 6), unit=unit,
                            value_2024eq100=round(idx, 4) if idx is not None else "", source=source, obs_status=status,
                            backfilled=bf, proxy=proxy if source not in ("te", "carried_back") else 0, linked=linked, vintage=date.today().isoformat()))
        if L is not None: link_months[sid] = L
        if base_method == "carried_back" and te_m:
            backfill.append(dict(series_id=sid, commodity=name, first_actual_period=min(te_m), first_actual_value=round(te_m[min(te_m)], 6), unit=unit,
                                 carried_back_from=BASE_FROM, carried_back_to=months(BASE_FROM, min(te_m))[-2] if len(months(BASE_FROM, min(te_m))) > 1 else "",
                                 source_of_first_value="Trading Economics commodities table (our daily capture)", replaced_by="", note=m.get("note", "")))
        # splice: external vs our TE mean in the overlap months
        for ym in sorted(set(conv) & set(te_m)):
            splice.append(dict(series_id=sid, commodity=name, period=ym, external=round(conv[ym], 4), te_mean=round(te_m[ym], 4),
                               ratio_te_over_external=round(te_m[ym] / conv[ym], 4) if conv[ym] else "", proxy=proxy, source=src))
        series_rows.append(dict(series_id=sid, commodity=name, category=cat, unit=unit, in_index=0 if cat == "Electricity" else 1,
                                history_source=src if conv else "", history_series=src_series if conv else "", licence=licence if conv else "",
                                proxy=proxy if conv else 0, proxy_of=m.get("proxy", "") if conv else "", conversion=m.get("note", ""),
                                base_2024_mean=round(base, 6) if base else "", base_method=base_method, link_month=link_months.get(sid, ""), first_external=min(conv) if conv else "",
                                last_external=max(conv) if conv else "", first_te=min(te_m) if te_m else "", last_te=max(te_m) if te_m else ""))
    def w(name, rows):
        with open(out / name, "w", newline="", encoding="utf-8") as f:
            wr = csv.DictWriter(f, fieldnames=list(rows[0]) if rows else ["empty"]); wr.writeheader(); wr.writerows(rows)
    w("series.csv", series_rows); w("observations.csv", obs); w("backfill_log.csv", backfill); w("splice_check.csv", splice)
    # monthly index 2024 = 100: geometric mean of the series indices over the index series with ACTUAL 2024 history, plus a
    # second column with the carried-back series included (so the effect of the backfill rule is visible)
    byp = defaultdict(lambda: {"act": [], "all": []})
    sm = {s["series_id"]: s for s in series_rows}
    for o in obs:
        s = sm[o["series_id"]]
        if not s["in_index"] or o["value_2024eq100"] == "": continue
        byp[o["period"]]["all"].append(float(o["value_2024eq100"]))
        if s["base_method"] == "actual": byp[o["period"]]["act"].append(float(o["value_2024eq100"]))
    gm = lambda xs: round(statistics.geometric_mean(xs), 3) if xs else ""
    idx = [dict(period=p, trendx_2024eq100_actual_history=gm(v["act"]), n_series_actual=len(v["act"]), trendx_2024eq100_all_series=gm(v["all"]), n_series_all=len(v["all"])) for p, v in sorted(byp.items())]
    w("index_2024.csv", idx)
    # the portal file: everything in one JSON (uploaded as an asset; pointer projects/te/history/latest)
    obs_by = defaultdict(list)
    for o in obs: obs_by[o["series_id"]].append([o["period"], o["value"], o["value_2024eq100"] if o["value_2024eq100"] != "" else None, o["source"], o["backfilled"], o["linked"]])
    hist = dict(built=date.today().isoformat(), base="2024 mean = 100", span=[BASE_FROM, last_te], series=series_rows, obs=obs_by, index=idx, backfill=backfill,
                sources=dict(wb="World Bank Commodity Price Data (Pink Sheet), CC BY 4.0", eia="US EIA spot prices, public domain", fx="ECB euro reference rates", te="our daily Trading Economics capture, monthly mean",
                             imf="IMF Primary Commodity Price System (attribution)", usda="USDA ERS/AMS (public domain), Statistics Norway, Statistics Canada", nbs="China NBS 10-day market prices (citation)", ember="Ember European wholesale electricity (CC BY 4.0)", bls="US BLS producer price indexes (public domain)"))
    (out / "history_2024.json").write_text(json.dumps(hist, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    n_act = sum(1 for s in series_rows if s["base_method"] == "actual"); n_proxy = sum(1 for s in series_rows if s["proxy"]); n_idx = sum(1 for s in series_rows if s["in_index"])
    (out / "README.md").write_text(f"""# TrendX monthly store, base 2024 = 100

Built {date.today().isoformat()} by scripts/trendx/build_history_store.py. World Bank file: "{wb_stamp}". Span {BASE_FROM} to {last_te}.

- series.csv: {len(series_rows)} series ({n_idx} in the index, 5 electricity kept outside it). {n_act} have real 2024 history (base_method actual; {n_proxy} of them through a proxy series), {len(series_rows) - n_act} are carried back (first collected price held constant to Jan 2024, flagged E / backfilled = 1).
- observations.csv: one row per series and month: value in the TE unit as observed by its source, value_2024eq100, source (wb, eia, te, carried_back), obs_status (A actual, E estimated), backfilled, proxy, linked (1 = a TE month chained onto the external level at link_month, so a spot/futures or market level gap does not appear as a jump).
- backfill_log.csv: the carried-back series with the first actual price, its date and source, as the manager asked; replaced_by stays empty until a history source is added.
- splice_check.csv: months where external history and our own TE monthly mean overlap (Oct 2026): ratio_te_over_external shows the level gap (spot vs futures, market, quality) before the two are chained.
- index_2024.csv: equal-weight geometric mean of the series indices, over the series with actual history and over all series.
Rules: no price carried forward; carried-back values are excluded from correlation and modelling; proxies are real history of a related series and are marked.
Licences: World Bank Pink Sheet CC BY 4.0; EIA public domain (spot prices carry a third-party caveat, internal use); ECB rates free with citation; our TE capture is internal.
Missing TE names (not in the capture): {missing}
""", encoding="utf-8")
    print(f"{len(series_rows)} series, {n_act} with actual 2024 history ({n_proxy} proxy), {len(backfill)} carried back; {len(obs)} observations; {len(splice)} splice rows -> {out}")
    if missing: print("not in the TE capture:", missing)


if __name__ == "__main__":
    main(*sys.argv[1:7])
