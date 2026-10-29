"""Price-visibility probe for pages without a dedicated parser.

It does not produce index prices. It lists every money amount printed on the page (and in image alt texts) with
the text around it, so an officer can see at a glance whether a page shows prices at all and which ones. Those go
to price_mentions.csv; a page with zero mentions is evidence for the 'price publicly visible' criterion (= لا).
"""
import re

from scrapling.parser import Selector

from ..parse import clean

AMOUNT_RE = re.compile(
    r"(?P<cur>AED|USD|EUR|GBP|INR|SAR|Dhs?|درهم|\$|€|£)\s?(?P<a>\d[\d,]*(?:\.\d+)?)"
    r"|(?P<b>\d[\d,]*(?:\.\d+)?)\s?(?P<cur2>AED|USD|EUR|SAR|dirhams?|درهم)\b", re.I)


def mentions(html: str, context: int = 70) -> list[dict]:
    page = Selector(html)
    texts = [("page text", page.get_all_text(separator="\n", strip=True))]
    texts += [("image alt: " + (img.attrib.get("src") or img.attrib.get("data-src") or "")[:200], img.attrib["alt"])
              for img in page.css("img[alt]") if img.attrib.get("alt")]
    out, seen = [], set()
    for where, text in texts:
        for m in AMOUNT_RE.finditer(text):
            cur = (m.group("cur") or m.group("cur2") or "").upper()
            amount = (m.group("a") or m.group("b")).replace(",", "")
            snippet = clean(text[max(0, m.start() - context): m.end() + context])
            key = (where, cur, amount, snippet)
            if key in seen:
                continue
            seen.add(key)
            out.append(dict(where=where, currency=cur, amount=float(amount), snippet=snippet))
    return out
