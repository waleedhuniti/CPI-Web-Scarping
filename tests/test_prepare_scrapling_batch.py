import pytest

from scripts.prepare_scrapling_batch import extract_urls, prepare_batch


def test_extract_urls_accepts_strings_and_objects_and_deduplicates():
    values = extract_urls([
        "https://www.carrefouruae.com/a/p/123",
        {"url": "https://www.carrefouruae.com/a/p/123"},
        {"url": "https://www.carrefouruae.com/a/p/456"},
    ])
    assert values == [
        "https://www.carrefouruae.com/a/p/123",
        "https://www.carrefouruae.com/a/p/456",
    ]


def test_extract_urls_accepts_items_envelope():
    assert extract_urls({"items": [{"url": "https://gcc.luluhypermarket.com/en-ae/p/123"}]}) == [
        "https://gcc.luluhypermarket.com/en-ae/p/123"
    ]


def test_prepare_batch_applies_offset_and_limit():
    urls = [f"https://www.carrefouruae.com/a/p/{i}" for i in range(5)]
    assert prepare_batch("carrefour", urls, offset=1, limit=2) == urls[1:3]


def test_prepare_batch_rejects_other_domains():
    with pytest.raises(ValueError, match="approved HTTPS"):
        prepare_batch("carrefour", ["https://example.com/p/1"], offset=0, limit=1)


def test_prepare_batch_rejects_too_large_batch():
    with pytest.raises(ValueError, match="between 1 and 200"):
        prepare_batch("carrefour", ["https://www.carrefouruae.com/p/1"], offset=0, limit=201)
