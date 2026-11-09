from scripts.scrapling_product_pages import extract_json_ld, html_to_text, is_human_verification, validate_url


def test_html_to_text_preserves_labels_and_skips_scripts():
    html = """
    <html><body><h1>Apples</h1><p>Pack Size</p><p>1 kg</p>
    <script>secret challenge text</script><div>Origin</div><div>Jordan</div></body></html>
    """
    text = html_to_text(html)
    assert "Apples" in text and "Pack Size" in text and "1 kg" in text and "Jordan" in text
    assert "secret challenge text" not in text


def test_extract_json_ld():
    html = '<script type="application/ld+json">{"@type":"Product","name":"Rice"}</script>'
    assert extract_json_ld(html) == [{"@type": "Product", "name": "Rice"}]


def test_human_verification_detection():
    assert is_human_verification(403, "<html></html>")
    assert is_human_verification(200, "<title>Verify you are human</title>")
    assert not is_human_verification(200, "<title>Product page</title>", "Rice 5 kg AED 20")


def test_retailer_url_allowlist():
    validate_url("lulu", "https://gcc.luluhypermarket.com/en-ae/p/rice")
    try:
        validate_url("lulu", "https://example.com/product")
    except ValueError:
        pass
    else:
        raise AssertionError("non-retailer host should be rejected")
