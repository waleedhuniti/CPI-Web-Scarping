"""Polite fetching with Scrapling: robots.txt first, one host at a time, no challenge solving, every request logged.

  * HTTP pages go through ``scrapling.fetchers.Fetcher`` (curl_cffi, Chrome TLS fingerprint).
  * Pages that only render in a browser go through ``StealthyFetcher`` (Chromium). It renders the page and nothing
    more: ``solve_cloudflare`` is never switched on. A Cloudflare / bot wall is recorded as ``blocked_bot_protection``
    and the source has to be priced another way (official PDF, another publisher, or the survey).
  * robots.txt is read with protego (Google's matching rules). 2xx -> obeyed; 4xx -> no rules (Google convention);
    5xx or unreachable -> treated as disallowed, because we could not read the rules.
  * Redirects are followed by hand so robots.txt is checked again on every new host.
"""
import hashlib
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from urllib.parse import urljoin, urlsplit

from protego import Protego

ROBOTS_AGENT = "*"
DEFAULT_DELAY = 2.0          # seconds between two requests to the same host (robots Crawl-delay wins if larger)
MAX_REDIRECTS = 5
SERVER_ERROR_RETRIES = 2
BOT_WALL_MARKERS = ("Just a moment...", "challenges.cloudflare.com", "cf-chl-", "Attention Required! | Cloudflare",
                    "captcha-delivery.com", "/_Incapsula_Resource", "px-captcha")


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


@dataclass
class FetchResult:
    url: str
    final_url: str = ""
    status: int = 0
    body: bytes = b""
    content_type: str = ""
    fetched_at: str = ""
    seconds: float = 0.0
    mode: str = "http"
    robots: str = ""            # allowed / disallowed / no_rules (4xx) / unreadable
    outcome: str = ""           # ok / http_error / robots_disallowed / blocked_bot_protection / fetch_error
    note: str = ""
    redirects: list = field(default_factory=list)
    tag: str = ""               # which configured page the request belongs to

    @property
    def ok(self) -> bool:
        return self.outcome == "ok"

    @property
    def sha256(self) -> str:
        return sha256(self.body)

    def text(self) -> str:
        return self.body.decode("utf-8", "replace")


def is_bot_wall(status: int, body: bytes) -> bool:
    if status not in (403, 429, 503):
        return False
    head = body[:20000].decode("utf-8", "replace")
    return any(m in head for m in BOT_WALL_MARKERS)


def default_browser_path() -> str | None:
    """Chromium to drive with StealthyFetcher: $SPPI_CHROMIUM, else the cloud sandbox's copy, else Scrapling's own."""
    path = os.environ.get("SPPI_CHROMIUM")
    if path:
        return path
    return "/opt/pw-browsers/chromium" if os.path.exists("/opt/pw-browsers/chromium") else None


class Net:
    """One instance per run. Remembers robots.txt per host and when each host was last hit."""

    def __init__(self, delay: float = DEFAULT_DELAY, timeout: int = 60, log=None):
        self.delay = delay
        self.timeout = timeout
        self.log = log if log is not None else []     # list of FetchResult, in request order
        self._robots = {}                              # host -> (Protego | None, state)
        self._last_hit = {}

    # ---- robots.txt ------------------------------------------------------------------------------------
    def robots_state(self, url: str) -> tuple[str, float]:
        """('allowed' | 'disallowed' | 'no_rules' | 'unreadable', crawl_delay)."""
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            self._robots[host] = self._read_robots(host)
        rules, state = self._robots[host]
        if rules is None:
            return state, 0.0
        allowed = rules.can_fetch(url, ROBOTS_AGENT)
        return ("allowed" if allowed else "disallowed"), float(rules.crawl_delay(ROBOTS_AGENT) or 0)

    def _read_robots(self, host: str):
        url = host + "/robots.txt"
        for _ in range(MAX_REDIRECTS + 1):
            try:
                status, body, headers, _final = self._http(url)
            except Exception:  # noqa: BLE001 - any network failure means we could not read the rules
                return None, "unreadable"
            location = headers.get("location") or headers.get("Location")
            if status in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)
                continue
            if 200 <= status < 300:
                return Protego.parse(body.decode("utf-8", "replace")), "allowed"
            if 400 <= status < 500:
                return None, "no_rules"
            return None, "unreadable"
        return None, "unreadable"

    def _wait_for_host(self, url: str, crawl_delay: float):
        host = urlsplit(url).netloc
        gap = max(self.delay, crawl_delay)
        last = self._last_hit.get(host)
        if last is not None and time.monotonic() - last < gap:
            time.sleep(gap - (time.monotonic() - last))
        self._last_hit[host] = time.monotonic()

    # ---- fetching --------------------------------------------------------------------------------------
    def get(self, url: str, mode: str = "http", tag: str = "", **browser_kwargs) -> FetchResult:
        res = FetchResult(url=url, mode=mode, fetched_at=now_utc(), tag=tag)
        t0 = time.monotonic()
        try:
            self._get(res, url, mode, browser_kwargs)
        finally:
            res.seconds = round(time.monotonic() - t0, 1)
            self.log.append(res)
        return res

    def _get(self, res: FetchResult, url: str, mode: str, browser_kwargs: dict):
        for _ in range(MAX_REDIRECTS + 1):
            state, crawl_delay = self.robots_state(url)
            res.robots = state
            if state in ("disallowed", "unreadable"):
                res.final_url = url
                res.outcome = "robots_disallowed" if state == "disallowed" else "robots_unreadable"
                res.note = f"robots.txt of {urlsplit(url).netloc}: {state}; not fetched"
                return
            self._wait_for_host(url, crawl_delay)
            try:
                status, body, headers, final = (self._browser(url, browser_kwargs) if mode == "browser"
                                                else self._http(url))
            except Exception as e:  # noqa: BLE001
                res.final_url, res.outcome, res.note = url, "fetch_error", f"{type(e).__name__}: {str(e)[:200]}"
                return
            location = headers.get("location") or headers.get("Location")
            if mode == "http" and status in (301, 302, 303, 307, 308) and location:
                url = urljoin(url, location)
                res.redirects.append(f"{status} -> {url}")
                continue
            res.final_url, res.status, res.body = final or url, status, body
            res.content_type = headers.get("content-type") or headers.get("Content-Type") or ""
            if is_bot_wall(status, body):
                res.outcome = "blocked_bot_protection"
                res.note = "bot/challenge page returned; not bypassed (no challenge solving by policy)"
            elif 200 <= status < 300:
                res.outcome = "ok"
            else:
                res.outcome = "http_error"
            return
        res.final_url, res.outcome, res.note = url, "fetch_error", f"more than {MAX_REDIRECTS} redirects"

    def _http(self, url: str):
        """One GET without following redirects; a 5xx answer is retried twice (proxies and CDNs fail transiently)."""
        from scrapling.fetchers import Fetcher
        for attempt in range(1 + SERVER_ERROR_RETRIES):
            r = Fetcher.get(url, timeout=self.timeout, impersonate="chrome", follow_redirects=False, retries=2)
            if r.status < 500 or attempt == SERVER_ERROR_RETRIES:
                return r.status, r.body, dict(r.headers or {}), r.url
            time.sleep(3)

    def _browser(self, url: str, kwargs: dict):
        from scrapling.fetchers import StealthyFetcher
        opts = dict(headless=True, network_idle=True, timeout=self.timeout * 1000)
        path = default_browser_path()
        if path:
            opts["executable_path"] = path
        if os.environ.get("HTTPS_PROXY"):
            opts["proxy"] = os.environ["HTTPS_PROXY"]
        opts.update(kwargs)
        opts.pop("solve_cloudflare", None)      # never: see module docstring
        r = StealthyFetcher.fetch(url, **opts)
        return r.status, r.body, dict(r.headers or {}), r.url
