"""Oracle Cloud Infrastructure list prices from Oracle's public price-list API, in AED.

    https://apexapps.oracle.com/pls/apex/cetools/api/v1/products/?currencyCode=AED

This is the same data behind https://www.oracle.com/cloud/price-list/ (whose HTML table cells are empty until
JavaScript fills them), but already in AED. They are global pay-as-you-go LIST prices, not what Oracle UAE charges
its contract customers - usable for an SPPI list-price series, not as transaction prices.
"""
import json


def _num(v) -> str:
    return str(int(v)) if float(v).is_integer() else str(v)


def parse(body: bytes) -> tuple[list[dict], str]:
    """(records, lastUpdated) - one record per price tier."""
    data = json.loads(body)
    updated = (data.get("lastUpdated") or "")[:10]
    out = []
    for it in data.get("items", []):
        for loc in it.get("currencyCodeLocalizations", []):
            prices = loc.get("prices", [])
            for p in prices:
                tier = ""
                if "rangeMin" in p:
                    tier = f"; tier {_num(p['rangeMin'])}-{_num(p['rangeMax'])} {it.get('metricName', '')}"
                out.append(dict(item=f"OCI - {it.get('displayName', '')}",
                                spec=f"{it.get('partNumber', '')}; {it.get('serviceCategory', '')}{tier}",
                                price=float(p.get("value", 0)), currency=loc.get("currencyCode", ""),
                                unit=it.get("metricName", ""), price_type=f"list price ({p.get('model', '')})",
                                price_text=json.dumps(p, separators=(",", ":")), vat="excl. VAT",
                                effective_date=updated, note=""))
    return out, updated
