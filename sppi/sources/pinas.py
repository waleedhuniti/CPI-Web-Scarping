"""Pinas Express Cargo (pinascargo.com/pricing): rate cards published as images.

The page text has no prices; the rate cards are JPEGs. Prices come from the readings in
config/sppi_image_transcriptions.json, and only while the image on the site is byte-identical (sha256) to the one
that was read. tesseract, when installed, gives an independent cross-check (how many of the read values it finds).
"""
import io
import re
import shutil
import subprocess
import tempfile

from scrapling.parser import Selector


def image_urls(html: str) -> set[str]:
    page = Selector(html)
    return {img.attrib.get("src") or img.attrib.get("data-src") or "" for img in page.css("img")}


def records_from_reading(reading: dict) -> list[dict]:
    out = []
    base = dict(currency=reading["currency"], price_type="list price (image rate card)", vat="not stated",
                effective_date=reading.get("effective", ""))
    note = (f"read {reading['read_on']} from image sha256 {reading['sha256'][:12]}...; "
            f"currency: {reading['currency_basis']}")
    for row in reading["rows"]:
        for col, v in zip(reading["columns"], row["values"]):
            out.append(dict(base, item=f"{reading['title'].split(',')[0]} - {row['label']}",
                            spec=f"destination {col}", price=v, unit=row["unit"],
                            price_text=f"{row['label']} | {col} | {v:,.2f}", note=note))
    for ex in reading.get("extras", []):
        out.append(dict(base, item=f"{reading['title'].split(',')[0]} - {ex['label']}", spec="", price=ex["price"],
                        unit=ex["unit"], price_text=f"{ex['label']} | {ex['price']:,.2f}", note=note))
    return out


def ocr_numbers(image_bytes: bytes) -> list[float] | None:
    """Numbers tesseract reads from the white text of a rate card; None when tesseract is not installed."""
    if not shutil.which("tesseract"):
        return None
    from PIL import Image, ImageChops
    rgb = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    r, g, b = (ch.point(lambda v: 255 if v > 200 else 0) for ch in rgb.split())
    white = ImageChops.invert(ImageChops.multiply(ImageChops.multiply(r, g), b))   # white text -> black on white
    with tempfile.NamedTemporaryFile(suffix=".png") as f:
        white.save(f.name)
        text = subprocess.run(["tesseract", f.name, "-", "--psm", "6"], capture_output=True, text=True,
                              timeout=120).stdout
    return [float(x.replace(",", "")) for x in re.findall(r"\d[\d,]*\.\d\d", text)]


def ocr_agreement(reading: dict, numbers: list[float] | None) -> str:
    if numbers is None:
        return "OCR cross-check not run (tesseract not installed)"
    expected = [v for row in reading["rows"] for v in row["values"]]
    pool = list(numbers)
    found = 0
    for v in expected:
        if v in pool:
            pool.remove(v)
            found += 1
    return f"OCR cross-check: {found}/{len(expected)} read values also found by tesseract"
