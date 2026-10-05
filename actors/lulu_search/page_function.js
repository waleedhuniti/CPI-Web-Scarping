// Apify "web-scraper" page function: Lulu Hypermarket (UAE) barcode search.
// Start URL per basket barcode:  https://gcc.luluhypermarket.com/en-ae/list/?search_text=<EAN>
// with userData {"ean": "<EAN>"}.  One dataset row per product card found (none -> found:false).
async function pageFunction(context) {
    const $ = context.jQuery;
    const ean = (context.request.userData || {}).ean || null;
    try {
        await context.waitFor('[data-testid="product-price"]', { timeoutMillis: 20000 });
    } catch (e) { /* no results for this barcode */ }

    const rows = [];
    $('[data-testid="product-price"]').each(function (i) {
        // climb to the product card: first ancestor that holds a product link
        let card = $(this).parent();
        for (let up = 0; up < 8 && card.find('a[href*="/p/"]').length === 0; up++) card = card.parent();
        const link = card.find('a[href*="/p/"]').filter(function () { return $(this).text().trim().length > 0; }).first();
        const num = (t) => { const m = (t || '').replace(/,/g, '').match(/\d+(\.\d+)?/); return m ? parseFloat(m[0]) : null; };
        rows.push({
            ean: ean,
            found: true,
            rank: i + 1,
            title: link.text().trim(),
            path: link.attr('href') || null,
            url: link.attr('href') ? new URL(link.attr('href'), 'https://gcc.luluhypermarket.com').href.split('?')[0] : null,
            price: num($(this).text()),
            wasPrice: num(card.find('[class*="line-through"]').first().text()),
            brandChip: card.find('span[class*="rounded-v2-xs"]').first().text().trim() || null,
            searchUrl: context.request.url,
        });
    });
    if (rows.length === 0) return [{ ean: ean, found: false, searchUrl: context.request.url, pageTitle: $('title').text() }];
    return rows;
}
