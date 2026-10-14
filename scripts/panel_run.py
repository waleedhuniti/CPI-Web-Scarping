"""Turn one run folder into the documents the Scraping Projects panel stores (and Dataiku downloads).

    python scripts/panel_run.py data/runs/<run> <started ISO time>      # -> <run>/panel/run.json, c000.json ..., last.json

Reads <retailer>_matched.csv (barcode search) and category_matches.csv (bulk category crawl) when present. Every row
has the same columns as data/exports/cpi_prices_long.csv, so the panel's download is ready for Dataiku.
Prints RUN_ID <id> and the number of row documents.
"""
import csv
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from cpi.decision import barcode_found, category_found  # noqa: E402

LABEL = {"carrefour": "Carrefour UAE", "lulu": "Lulu Hypermarket UAE"}
GROUP = {"0111": "Bread & cereals", "0112": "Meat", "0113": "Fish & seafood", "0114": "Milk, cheese & eggs",
         "0115": "Oils & fats", "0116": "Fruit & nuts", "0117": "Vegetables", "0118": "Sugar, jam, honey & sweets",
         "0119": "Other food products"}
BASIS = {"kg": "kg", "l": "litre", "pc": "piece", "bunch": "bunch"}


def listing_info(run_dir):
    """Product URL -> pack size and retailer section from the run's catalog.csv (bulk listings)."""
    info = {}
    cat = run_dir / "catalog.csv"
    if cat.exists():
        for r in csv.DictReader(open(cat, encoding="utf-8-sig")):
            info[r["url"]] = dict(size=(r.get("size") or "").split(" - ")[0], section=r.get("category", ""),
                                  note=r.get("price_note", ""))
    return info


def retailer_id(url):
    import re
    m = re.search(r"/p/([^/?]+)", url or "")
    return m.group(1).strip("/") if m else ""


def num(v):
    try:
        return float(v) if v not in (None, "") else ""
    except ValueError:
        return ""


def photos(run_dir):
    """Product URL -> photo URL: data/photos.json plus the run's own catalog.csv photo_url column."""
    f = ROOT / "data/photos.json"
    cache = json.loads(f.read_text()) if f.exists() else {}
    cat = run_dir / "catalog.csv"
    if cat.exists():
        for r in csv.DictReader(open(cat, encoding="utf-8-sig")):
            if r.get("photo_url"):
                cache[r["url"]] = r["photo_url"]
    return cache


REASON = {"name": "no barcode: priced from the catalogue by product name/model (not yet matched)",
          "service": "service: no shelf price on the web (restaurant, repair, laundry, hotel, hairdresser)",
          "market": "priced from a market rate (gold per gram), not a shop listing"}


def pending_rows(date):
    """One row per basket item that no search or category crawl covers (match_mode name / service / market), so every
    day's file lists the whole basket: status not_found, source 'pending', and why."""
    f, g = ROOT / "data/basket/basket.json", ROOT / "config/cpi_groups.json"
    if not f.exists() or not g.exists():
        return []
    groups = json.loads(g.read_text(encoding="utf-8"))["groups"]
    out = []
    for it in json.loads(f.read_text(encoding="utf-8")):
        mode = it.get("match_mode")
        if mode not in REASON:
            continue
        out.append(dict(run_date=date, source="pending", retailer="", actor="", item_code=it["item_code"], group_code=it["group_code"],
                        name=it["name_ar"], brand=it.get("brand_ar", ""), basket_qty=it.get("qty_raw", ""), barcode="",
                        status="service" if mode == "service" else "not_found", detail=REASON[mode], accepted="no", title="",
                        price="", regular_price="", currency="AED", url="", photo="", size="",
                        group_name=groups.get(it["group_code"], {}).get("en", ""), retailer_id="", in_stock=""))
    return out


def main(run_dir, started):
    run_dir = Path(run_dir)
    pics = photos(run_dir)
    info = listing_info(run_dir)
    rows, summary, log = [], {}, []
    for retailer in LABEL:
        f = run_dir / f"{retailer}_matched.csv"
        if not f.exists():
            continue
        res = []
        for r in csv.DictReader(open(f, encoding="utf-8-sig")):
            if r["status"] == "not_searched":
                continue
            ok = barcode_found(r["status"])
            res.append(dict(run_date=started[:10], source="barcode", retailer=retailer, actor=LABEL[retailer],
                            item_code=r["item_code"], group_code=r.get("group", ""), name=r["name_ar"],
                            brand=r["brand_ar"], basket_qty=r["basket_qty"], barcode=r["barcode"],
                            status="found" if ok else "not_found", detail=r["status"],
                            accepted="yes" if ok else "no", title=r["title"] if ok else "",
                            price=num(r["price"]) if ok else "", regular_price=num(r["regular_price"]) if ok else "",
                            currency="AED", url=r["url"] if ok else "", photo=pics.get(r["url"], "") if ok else "",
                            size=r["basket_qty"] if ok else "", group_name=GROUP.get(r.get("group", ""), ""),
                            retailer_id=retailer_id(r["url"]) if ok else "", in_stock=r.get("in_stock", "") if ok else ""))
        failed = json.loads((run_dir / f"{retailer}_failed.json").read_text()) if (run_dir / f"{retailer}_failed.json").exists() else []
        searched = json.loads((run_dir / f"{retailer}_searched.json").read_text()) if (run_dir / f"{retailer}_searched.json").exists() else []
        log.append(f"{LABEL[retailer]} barcode: {len(searched)} pages read, {len(failed)} failed")
        rows += res
    cat = run_dir / "category_matches.csv"
    if cat.exists():
        crows = list(csv.DictReader(open(cat, encoding="utf-8-sig")))
        lines = {}
        for r in crows:
            lines.setdefault((r["retailer"], r["name_ar"]), set()).add(r["item_code"])
        for r in crows:
            ok = category_found(r["status"], len(lines[(r["retailer"], r["name_ar"])]) == 1)
            rows.append(dict(run_date=started[:10], source="category", retailer=r["retailer"],
                             actor=LABEL[r["retailer"]] + " (category)", item_code=r["item_code"],
                             group_code=r["group"], name=r["name_ar"], brand="", basket_qty=r["basket_qty"], barcode="",
                             status="found" if ok else "not_found", detail=r["status"], accepted="yes" if ok else "no",
                             title=r["title"] if ok else "", price=num(r["price"]) if ok else "",
                             regular_price=num(r["regular_price"]) if ok else "", unit_price=num(r["unit_price"]) if ok else "",
                             price_basis=r["price_basis"], basket_origin=r["basket_origin"],
                             origin_seen=r["origin_seen"] if ok else "", currency="AED", url=r["url"] if ok else "",
                             photo=pics.get(r["url"], "") if ok else "",
                             size=info.get(r["url"], {}).get("size", "") if ok else "",
                             group_name=GROUP.get(r["group"], ""), section=info.get(r["url"], {}).get("section", "") if ok else "",
                             retailer_id=retailer_id(r["url"]) if ok else "",
                             note=(f"AED {r['unit_price']} per {BASIS.get(r['price_basis'], r['price_basis'])}"
                                   + (f" · {info[r['url']]['note']}" if info.get(r["url"], {}).get("note") else "")) if ok and r["unit_price"] else ""))
        cl = run_dir / "crawl_log.txt"
        if cl.exists():
            log += cl.read_text(encoding="utf-8").strip().splitlines()
    for key in {(r["retailer"], r["source"]) for r in rows}:
        mine = [r for r in rows if (r["retailer"], r["source"]) == key]
        st = {}
        for r in mine:
            st[r["status"]] = st.get(r["status"], 0) + 1
        summary[f"{key[0]}_{key[1]}"] = dict(label=f"{LABEL[key[0]]} ({'barcode' if key[1] == 'barcode' else 'category'})",
                                              lines=len(mine), accepted=sum(r["accepted"] == "yes" for r in mine),
                                              statuses=st)
    if os.environ.get("CPI_PENDING_ROWS"):          # off by default: the export adds these rows (they are the same every day)
        rows += pending_rows(started[:10])
    out = run_dir / "panel"
    out.mkdir(exist_ok=True)
    chunks, cur, size = [], [], 0
    for r in rows:
        s = len(json.dumps(r, ensure_ascii=False))
        if size + s > 40_000 and cur:
            chunks.append(cur)
            cur, size = [], 0
        cur.append(r)
        size += s
    chunks.append(cur)
    for i, c in enumerate(chunks):
        (out / f"c{i:03d}.json").write_text(json.dumps({"rows": c, "i": i}, ensure_ascii=False), encoding="utf-8")
    # thumbnails of the found products (data/thumbs, scripts/fetch_thumbs.py) for the panel's Excel download
    import base64
    import hashlib
    pairs, seen = [], set()
    for r in rows:
        u = r.get("photo")
        if r["accepted"] == "yes" and u and u not in seen:
            seen.add(u)
            f = ROOT / "data/thumbs" / (hashlib.sha1(u.encode()).hexdigest() + ".jpg")
            if f.exists():
                pairs.append([u, base64.b64encode(f.read_bytes()).decode()])
    tchunks, cur, size = [], [], 0
    for pr in pairs:
        n = len(pr[0]) + len(pr[1]) + 8
        if size + n > 200_000 and cur:
            tchunks.append(cur)
            cur, size = [], 0
        cur.append(pr)
        size += n
    if cur:
        tchunks.append(cur)
    # one file, uploaded as an artifact asset (the panel database is capped at 100 MB); the run document then gets
    # {"thumbs_asset": <asset id>}
    (out / "thumbs.json").write_text(json.dumps({"pairs": pairs}), encoding="utf-8")
    acc = sum(r["accepted"] == "yes" for r in rows)
    failed_any = any("failed" in line and not line.endswith(" 0 failed") for line in log if "barcode" in line)
    status = "error" if failed_any else "done"
    (out / "run.json").write_text(json.dumps(dict(
        startedAt=started, finishedAt=datetime.now(timezone.utc).isoformat(timespec="seconds"), status=status,
        summary=summary, chunks=len(chunks), count=len(rows), accepted=acc, log=log), ensure_ascii=False), encoding="utf-8")
    (out / "last.json").write_text(json.dumps({"lastRun": {"at": started, "status": status, "accepted": acc}}))
    run_id = datetime.fromisoformat(started).strftime("%Y%m%dT%H%M") + "-auto"
    print("RUN_ID", run_id, "chunks", len(chunks), "photos", len(pairs), "rows", len(rows), "accepted", acc, "status", status)
    for v in summary.values():
        print(" ", v["label"], v["accepted"], "/", v["lines"])


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
