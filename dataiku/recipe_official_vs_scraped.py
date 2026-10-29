"""Dataiku Python recipe: scraped item prices against the official monthly prices, by CPI group.
The same steps as the visual flow in docs/dataiku_flow_official_vs_scraped.md and as scripts/compare_official_month.py.

In Dataiku: a Python recipe with inputs crawl_basket (CPI_basket_12-29_Oct.csv) and official_prices (the official prices
workbook), outputs item_compare and group_compare; paste this file as the recipe's code.
Locally (to check the numbers): python dataiku/recipe_official_vs_scraped.py <crawl.csv> <official.xlsx> [month]
"""
import sys

import pandas as pd

MONTH = "أكتوبر"
WEIGHT = r"(?i)(?:^|[\d\s*x×.])\s*(?:كغم?|كجم?|كيلو(?:غرام)?|غم?|غرام|جرام|جم|ملل?|لتر|ليتر|kg|gm?|gr|ml|cl|ltr|lt|l)(?![^\W\d_])"
FAR = 3.0


def pad(s):
    return s.astype(str).str.strip().str.replace(r"\.0$", "", regex=True).str.zfill(9)


def compare(crawl, off, month=MONTH):
    off = off.iloc[:, :3].join(off[month]).set_axis(["item_code", "official_desc", "official_unit", "official_price"], axis=1)
    off["item_code"] = pad(off["item_code"])
    off["official_price"] = pd.to_numeric(off["official_price"], errors="coerce")
    off = off[off["official_price"] > 0]
    off["by_weight"] = off["official_unit"].fillna("").astype(str).str.contains(WEIGHT, regex=True)
    c = crawl[crawl["accepted"].astype(str) == "yes"].copy()
    c["item_code"] = pad(c["item_code"])
    c = c.merge(off[["item_code", "by_weight"]], on="item_code")
    price, spec = pd.to_numeric(c["price"], errors="coerce"), pd.to_numeric(c["price_spec"], errors="coerce")
    c["price_cmp"] = price.where(~c["by_weight"] | spec.isna(), spec)
    c = c[c["price_cmp"] > 0]
    day = c.groupby(["item_code", "cpi_group", "run_date"], as_index=False)["price_cmp"].mean()
    item = day.groupby(["item_code", "cpi_group"], as_index=False).agg(crawl_avg=("price_cmp", "mean"), days_observed=("run_date", "count"))
    item = item.merge(off, on="item_code")
    item["price_difference"] = item["crawl_avg"] - item["official_price"]
    item["gap_pct"] = (item["crawl_avg"] / item["official_price"] - 1) * 100
    ratio = item["crawl_avg"] / item["official_price"]
    item["far"] = ~ratio.between(1 / FAR, FAR)
    ok = item[~item["far"]]
    grp = ok.groupby("cpi_group", as_index=False).agg(
        matched_items=("item_code", "count"), crawl_avg_price=("crawl_avg", "mean"), official_avg_price=("official_price", "mean"),
        median_item_gap_pct=("gap_pct", "median"), avg_days_observed=("days_observed", "mean"))
    grp = grp.merge(item.groupby("cpi_group")["far"].sum().rename("items_left_out").reset_index(), on="cpi_group")
    grp["price_difference"] = grp["crawl_avg_price"] - grp["official_avg_price"]
    grp["group_gap_pct"] = (grp["crawl_avg_price"] / grp["official_avg_price"] - 1) * 100
    grp = grp[["cpi_group", "matched_items", "crawl_avg_price", "official_avg_price", "price_difference", "group_gap_pct",
               "median_item_gap_pct", "avg_days_observed", "items_left_out"]].sort_values("matched_items", ascending=False)
    return item.round(2), grp.round(2)


if __name__ == "__main__" and len(sys.argv) > 2:
    item, grp = compare(pd.read_csv(sys.argv[1], dtype=str), pd.read_excel(sys.argv[2], dtype={0: str}), *sys.argv[3:4])
    print(len(item), "items,", int(item["far"].sum()), "left out")
    print(grp.to_string(index=False))
else:
    import dataiku
    item, grp = compare(dataiku.Dataset("crawl_basket").get_dataframe(),
                        dataiku.Dataset("official_prices").get_dataframe())
    dataiku.Dataset("item_compare").write_with_schema(item)
    dataiku.Dataset("group_compare").write_with_schema(grp)
