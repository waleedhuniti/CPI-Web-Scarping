Carrefour barcode search for 3 Nov 2026, run by hand from a separate cloud session (the daily routine was refused by Carrefour: 1 of 363 pages).
`python scripts/scrapling_search.py carrefour <dir> --delay 2.5`: 363 pages read, 0 failed after the retry rounds (43 HTTP 429 answers recovered); 197 lines accepted (170 barcode, 5 unit label, 22 name search).
The same session re-crawled the Carrefour catalogue (5,833 products, 99/99 categories) and put it into the panel catalogue of 3 Nov.
Not in the panel run of 3 Nov.
