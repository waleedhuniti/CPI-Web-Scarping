"""The portal's engine: basket and actor settings on disk, Apify runs, parsing and matching.

Everything here is plain functions so it can be tested without Flask or the network:

* `load_basket` / `save_basket`   data/basket/basket.json (+ basket.csv), derived fields recomputed on save
* `load_actors` / `save_actors`   config/actors.json - which Apify actor each retailer uses and its input
* `build_runs`                     basket items -> batches -> actor input for each batch
* `ApifyClient.run`                start a run, wait for it, return its dataset items
* `PARSERS`                        actor dataset items -> common rows (searched_barcode, title, price, ...)
* `match_rows`                     common rows -> one result per basket line (cpi.matcher rules)
"""
import copy
import csv
import json
import re
import time
from dataclasses import asdict, fields
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import requests

from cpi import gtin
from cpi.basket import FRESH_GROUPS, BasketItem
from cpi.matcher import ACCEPTED, Listing, match
from cpi.origin import origin_iso
from cpi.quantity import parse_quantity
from cpi.retailers import carrefour, lulu

ROOT = Path(__file__).resolve().parent.parent
BASKET_JSON = ROOT / "data/basket/basket.json"
BASKET_CSV = ROOT / "data/basket/basket.csv"
ACTORS_JSON = ROOT / "config/actors.json"
RUNS_DIR = ROOT / "data/runs"
ENV_FILE = ROOT / ".env"

ITEM_FIELDS = [f.name for f in fields(BasketItem)]
EDITABLE = ["item_code", "class_code", "class_name", "group_code", "group_name", "name_ar", "brand_ar",
            "barcode_raw", "origin_raw", "qty_raw"]


# ---------------------------------------------------------------- basket

def normalize_item(d: dict) -> dict:
    """A basket line with its derived fields (GTIN, quantity, origin, match mode) recomputed from the editable ones."""
    e = {k: str(d.get(k) or "").strip() for k in EDITABLE}
    if not re.fullmatch(r"\d{4,12}", e["item_code"]):
        raise ValueError(f"item_code must be digits: {e['item_code']!r}")
    e["group_code"] = e["group_code"] or e["item_code"][:4]
    e["class_code"] = e["class_code"] or e["item_code"][:7]
    q = parse_quantity(e["qty_raw"])
    kind = gtin.classify_barcode(e["barcode_raw"]) if e["barcode_raw"] else "none"
    item = BasketItem(
        **e, gtin=gtin.canonical(e["barcode_raw"]) if kind == "gtin" else "", barcode_kind=kind,
        origin_iso=origin_iso(e["origin_raw"]) if e["origin_raw"] else "",
        qty_unit=q.unit, qty_total=q.total, qty_count=q.count, qty_flag=q.flag,
        match_mode="barcode" if kind == "gtin" else "spec",
        fresh_type=FRESH_GROUPS.get(e["group_code"], "") if kind != "gtin" else "",
    )
    return asdict(item)


def load_basket(path=BASKET_JSON) -> list:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_basket(items, json_path=BASKET_JSON, csv_path=BASKET_CSV) -> list:
    out = [normalize_item(i) for i in items]
    codes = [i["item_code"] for i in out]
    dup = sorted({c for c in codes if codes.count(c) > 1})
    if dup:
        raise ValueError("duplicate item_code: " + ", ".join(dup))
    Path(json_path).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    with open(csv_path, "w", newline="", encoding="utf-8-sig") as f:   # BOM so Excel shows Arabic
        w = csv.DictWriter(f, fieldnames=ITEM_FIELDS)
        w.writeheader()
        w.writerows(out)
    return out


# ---------------------------------------------------------------- actors

PARSER_NAMES = ["carrefour_actor", "lulu_search_markdown", "lulu_page_function", "generic"]
MODES = ["barcodes", "search_urls"]


def load_actors(path=ACTORS_JSON) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def validate_actor(key: str, cfg: dict) -> dict:
    if not re.fullmatch(r"[a-z0-9_]{1,40}", key):
        raise ValueError(f"retailer key must be lower-case letters/digits/_: {key!r}")
    if not re.fullmatch(r"[\w.-]+[/~][\w.-]+", str(cfg.get("actor", ""))):
        raise ValueError(f"{key}: actor must look like 'username/actor-name'")
    if cfg.get("mode") not in MODES:
        raise ValueError(f"{key}: mode must be one of {MODES}")
    if cfg.get("parser") not in PARSER_NAMES:
        raise ValueError(f"{key}: parser must be one of {PARSER_NAMES}")
    if not isinstance(cfg.get("input"), dict):
        raise ValueError(f"{key}: input must be a JSON object")
    if cfg["mode"] == "search_urls" and "{barcode}" not in str(cfg.get("url_template", "")):
        raise ValueError(f"{key}: url_template must contain {{barcode}}")
    for n in ("batch_size", "parallel_runs"):
        v = int(cfg.get(n) or 1)
        if not 1 <= v <= 1000:
            raise ValueError(f"{key}: {n} must be 1-1000")
        cfg[n] = v
    cfg["enabled"] = bool(cfg.get("enabled", True))
    return cfg


def save_actors(actors: dict, path=ACTORS_JSON) -> dict:
    clean = {k: validate_actor(k, dict(v)) for k, v in actors.items()}
    Path(path).write_text(json.dumps(clean, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return clean


def search_form(raw) -> str:
    """The barcode as typed into a retailer's search box (restores the leading zero Excel dropped from UPC-A)."""
    d = gtin.digits_only(raw)
    return "0" + d if len(d) == 11 else d


def _fill(value, subs):
    """Replace the placeholders in an actor input: a string that is exactly '{name}' becomes subs[name] (any type)."""
    if isinstance(value, dict):
        return {k: _fill(v, subs) for k, v in value.items()}
    if isinstance(value, list):
        return [_fill(v, subs) for v in value]
    if isinstance(value, str):
        m = re.fullmatch(r"\{(\w+)\}", value)
        if m and m.group(1) in subs:
            return subs[m.group(1)]
    return value


def build_runs(cfg: dict, items: list) -> list:
    """[(barcodes, actor_input)] - one entry per actor run. Only basket lines with a real barcode are searched."""
    codes = list(dict.fromkeys(search_form(i["barcode_raw"]) for i in items if i.get("barcode_kind") == "gtin"))
    size = int(cfg.get("batch_size") or 10)
    runs = []
    for k in range(0, len(codes), size):
        batch = codes[k:k + size]
        urls = [cfg.get("url_template", "").format(barcode=c) for c in batch]
        subs = {
            "barcodes": batch, "barcodes_json": json.dumps(batch), "barcodes_text": "\n".join(batch),
            "start_urls": [{"url": u, "userData": {"ean": c}} for u, c in zip(urls, batch)], "urls": urls,
        }
        runs.append((batch, _fill(copy.deepcopy(cfg["input"]), subs)))
    return runs


# ---------------------------------------------------------------- Apify

class ApifyError(RuntimeError):
    pass


class ApifyClient:
    def __init__(self, token: str, base="https://api.apify.com/v2", session=None, poll=5.0, timeout=3600):
        if not token:
            raise ApifyError("No Apify token: set it under Settings or as APIFY_TOKEN")
        self.token, self.base, self.http = token, base.rstrip("/"), session or requests.Session()
        self.poll, self.timeout = poll, timeout

    def _req(self, method, path, **kw):
        r = self.http.request(method, self.base + path, headers={"Authorization": f"Bearer {self.token}"},
                              timeout=60, **kw)
        if r.status_code >= 400:
            raise ApifyError(f"Apify {method} {path}: HTTP {r.status_code} {r.text[:300]}")
        return r.json()

    def run(self, actor: str, actor_input: dict, stop=lambda: False) -> tuple:
        """Start `actor`, wait until it finishes, return (run_id, dataset items)."""
        run = self._req("POST", f"/acts/{actor.replace('/', '~')}/runs", json=actor_input)["data"]
        start = time.time()
        while run["status"] in ("READY", "RUNNING"):
            if stop():
                self._req("POST", f"/actor-runs/{run['id']}/abort")
                raise ApifyError("stopped by user")
            if time.time() - start > self.timeout:
                raise ApifyError(f"run {run['id']} still running after {self.timeout}s")
            time.sleep(self.poll)
            run = self._req("GET", f"/actor-runs/{run['id']}")["data"]
        if run["status"] != "SUCCEEDED":
            raise ApifyError(f"run {run['id']} ended {run['status']}")
        items, offset = [], 0
        while True:
            page = self._req("GET", f"/datasets/{run['defaultDatasetId']}/items",
                             params={"clean": "true", "format": "json", "offset": offset, "limit": 1000})
            items += page
            if len(page) < 1000:
                return run["id"], items
            offset += 1000


# ---------------------------------------------------------------- parsers: dataset items -> common rows
# A row: searched_barcode, title, price, regular_price, in_stock, url.  `searched` = barcodes whose page was really read
# (a searched barcode with no row is 'not carried', not an error).

def _row(code, title, price, regular, in_stock, url):
    price = float(price or 0)
    return dict(searched_barcode=code, title=title or "", price=price, regular_price=float(regular or price) or price,
                in_stock=in_stock, url=url or "")


def parse_carrefour_actor(items, batch, cfg):
    rows = [_row(lst.searched_barcode, lst.title, lst.price, lst.regular_price, lst.in_stock, lst.url)
            for lst in map(carrefour.from_actor_item, items) if lst.searched_barcode]
    return rows, set(batch)          # the actor searched every barcode it was given


def parse_lulu_search_markdown(items, batch, cfg):
    rows, searched = [], set()
    for it in items:
        q = parse_qs(urlparse(it.get("url") or "").query).get("search_text", [""])[0]
        md = it.get("markdown") or it.get("text") or ""
        if not q or ("All Products" not in md and "No results found" not in md):
            continue                  # page did not render a result list: not searched
        searched.add(q)
        rows += [_row(q, lst.title, lst.price, lst.regular_price, None, lst.url) for lst in lulu.parse_search_markdown(md, q)]
    return rows, searched


def parse_lulu_page_function(items, batch, cfg):
    """Rows of actors/lulu_search/page_function.js run with apify/web-scraper."""
    rows, searched = [], set()
    for it in items:
        code = str(it.get("ean") or "")
        searched.add(code)
        if it.get("found"):
            rows.append(_row(code, it.get("title"), it.get("price"), it.get("wasPrice"), None, it.get("url")))
    return rows, searched


def _get(item, path):
    for part in str(path or "").split("."):
        if not part:
            return None
        item = item.get(part) if isinstance(item, dict) else None
    return item


def parse_generic(items, batch, cfg):
    """Any actor: `fields` in the actor settings names the dataset field for each column (dots for nested fields)."""
    f = cfg.get("fields") or {}
    rows = []
    for it in items:
        code = search_form(_get(it, f.get("searched_barcode", "searchQuery")) or "")
        if code:
            rows.append(_row(code, _get(it, f.get("title", "title")), _get(it, f.get("price", "price")),
                             _get(it, f.get("regular_price", "regularPrice")), _get(it, f.get("in_stock", "inStock")),
                             _get(it, f.get("url", "url"))))
    return rows, set(batch)


PARSERS = {"carrefour_actor": parse_carrefour_actor, "lulu_search_markdown": parse_lulu_search_markdown,
           "lulu_page_function": parse_lulu_page_function, "generic": parse_generic}


# ---------------------------------------------------------------- matching

RESULT_FIELDS = ["retailer", "item_code", "group_code", "name_ar", "brand_ar", "basket_qty", "barcode", "status",
                 "accepted", "score", "reasons", "title", "price", "regular_price", "in_stock", "url"]


def match_rows(retailer, items, rows, searched, failed=()) -> list:
    """One result per barcoded basket line: the best listing found for its barcode, judged by cpi.matcher."""
    by_code = {}
    for r in rows:
        by_code.setdefault(r["searched_barcode"], {})[r["url"] or r["title"]] = r
    out = []
    for d in items:
        if d.get("barcode_kind") != "gtin":
            continue
        code = search_form(d["barcode_raw"])
        base = dict(retailer=retailer, item_code=d["item_code"], group_code=d["group_code"], name_ar=d["name_ar"],
                    brand_ar=d["brand_ar"], basket_qty=d["qty_raw"], barcode=code, score="", title="", price="",
                    regular_price="", in_stock="", url="", accepted="no")
        hits = list(by_code.get(code, {}).values())
        if not hits:
            if code in failed:
                out.append(dict(base, status="error", reasons="actor run failed"))
            elif code in searched:
                out.append(dict(base, status="not_found", reasons="no product for this barcode"))
            else:
                out.append(dict(base, status="not_searched", reasons="search page not read"))
            continue
        item = BasketItem(**{k: d[k] for k in ITEM_FIELDS})
        best = None
        for h in hits:
            lst = Listing(retailer, h["title"], price=h["price"], regular_price=h["regular_price"], searched_barcode=code,
                          result_count=len(hits), in_stock=h.get("in_stock"), url=h["url"])
            res = match(item, lst)
            if best is None or (res.accepted, res.score) > (best[1].accepted, best[1].score):
                best = (h, res)
        h, res = best
        out.append(dict(base, status=res.status, accepted="yes" if res.status in ACCEPTED else "no",
                        score=round(res.score, 2), reasons="; ".join(res.reasons), title=h["title"], price=h["price"],
                        regular_price=h["regular_price"], in_stock=h.get("in_stock"), url=h["url"]))
    return out


def write_results(path, results):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=RESULT_FIELDS)
        w.writeheader()
        w.writerows(results)


# ---------------------------------------------------------------- token

def get_token() -> str:
    import os
    if os.environ.get("APIFY_TOKEN"):
        return os.environ["APIFY_TOKEN"]
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
            if line.startswith("APIFY_TOKEN="):
                return line.split("=", 1)[1].strip()
    return ""


def set_token(token: str):
    lines = [l for l in (ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else [])
             if not l.startswith("APIFY_TOKEN=")]
    ENV_FILE.write_text("\n".join(lines + [f"APIFY_TOKEN={token.strip()}"]) + "\n", encoding="utf-8")
