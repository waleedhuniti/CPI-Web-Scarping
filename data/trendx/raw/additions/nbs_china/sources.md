# nbs_china — China National Bureau of Statistics, 10-day market prices of important means of production

Collected 9 Nov 2026 from www.stats.gov.cn only (one request at a time, 2.6 s apart, curl default identity, no retries in a loop).

## Source
"流通领域重要生产资料市场价格变动情况" (Market Prices of Important Means of Production in Circulation), published three times a month
(上旬 / 中旬 / 下旬 = 1st, 2nd, 3rd ten-day period) by NBS under 最新发布 (latest releases): https://www.stats.gov.cn/sj/zxfb/ .
Each release carries one table: product (with specification), unit, price for the period in CNY, change vs previous period.
The price is the national average of the 10-day period, surveyed in about 50 (57 from Jan 2026) products across ~300 markets.

## Licence / terms of use (quoted)
Page: 服务条款 (Terms of service), https://www.stats.gov.cn/wzgl/202302/t20230217_1912857.html (saved as raw/terms_fwtk.html), dated 2022-09-02:

> 三、数据使用 1.用户可以在本网站下载和使用国家统计局发布的统计数据； 2.个人和组织机构应依法使用国家统计局网站发布的统计数据；
> (III. Data use: 1. Users may download and use the statistical data released by the NBS on this website; 2. Individuals and organisations shall use the statistical data released on the NBS website in accordance with the law.)

> 转载或引用本网内容，务必在显著位置注明转自（或引自）国家统计局网站（或中国统计信息网）字样，并标明本网网址：www.stats.gov.cn。
> (When reproducing or citing content of this site, you must state prominently that it is from the National Bureau of Statistics website and give the address www.stats.gov.cn.)

> 二、版权说明 1.本网所有内容，未经注明，版权一律归国家统计局网站（中国统计信息网）所有。 2.欢迎转载或引用本网所载内容 …
> 3.转载或引用本网内容必须是以新闻性或资料性公共免费信息为使用目的的合理、善意引用，不得对本网内容原意进行曲解、修改。
> (Copyright NBS; reproduction and citation welcome, as reasonable good-faith use for news or informational public free information, without distorting the meaning.)

Also: 四、安全要求 2. 严禁非法探测、扫描、测试本网系统 (no illegal probing/scanning of the site) — this collection read only published pages sequentially.

Attribution to use: "Source: National Bureau of Statistics of China (www.stats.gov.cn), 流通领域重要生产资料市场价格变动情况".
No robots.txt was consulted beyond the published release pages; no API exists, the releases are HTML pages.

## Exact download URLs
- Index pages walked: https://www.stats.gov.cn/sj/zxfb/index.html and index_1.html … index_38.html (saved raw/zxfb_index*.html; 15 releases per page; walked back until the page's oldest date was before 2024-01-01).
- 98 release pages found for 2023-12 下旬 … 2026-10 下旬: full list in report_links.json; each saved as raw/rep_<yyyymm>_t<date>_<id>.html with its response headers in the matching .hdr file. Pattern: https://www.stats.gov.cn/sj/zxfb/<yyyymm>/t<yyyymmdd>_<id>.html
- Terms: https://www.stats.gov.cn/wzgl/202302/t20230217_1912857.html

## Files produced
- tenday_all_products.csv — every product row of every parsed release (4,850 rows, 55 product families, 97 releases).
- monthly_all_products.csv — monthly mean of the 10-day prices for every product (useful for other TE series: copper, aluminium, zinc, lead, LNG, LPG, gasoline, diesel, thermal coal, coke, cement, glass, rice, wheat, corn, cotton, live hogs, soybean, soybean meal, natural rubber, corrugated paper, caustic soda, benzene, polyester yarn, glyphosate, compound fertiliser; from Jan 2026 also ethanol, acetic acid, LFP, polysilicon, sugar, MAP, potash).
- monthly.csv — TE-target subset, required columns. value = mean of the 10-day prices published for that calendar month, in CNY per source unit.

## TE targets covered (monthly.csv)
| series_key | TE commodity / unit | NBS product | status |
|---|---|---|---|
| steel | Steel, CNY/T | 螺纹钢（Φ20mm，HRB400E） rebar | 2024-01..2026-10, direct |
| methanol | Methanol, CNY/T | 甲醇（优等品） | 2024-01..2026-10, direct |
| styrene | Styrene, CNY/MT | 苯乙烯（一级品） | 2024-01..2025-12 only: NBS dropped styrene from the basket in Jan 2026 |
| polyethylene | Polyethylene, CNY/T | 聚乙烯（LLDPE，熔融指数2薄膜料） | 2024-01..2026-10, direct |
| polypropylene | Polypropylene, CNY/T | 聚丙烯（拉丝料） | 2024-01..2026-10, direct |
| polyvinyl | Polyvinyl, CNY/T | 聚氯乙烯（SG5） | 2024-01..2025-12 only: NBS dropped PVC from the basket in Jan 2026 |
| synthetic_rubber | Synthetic Rubber, CNY/T | 顺丁胶（BR9000） butadiene rubber | 2024-01..2026-10, direct |
| coking_coal | Coking Coal, USD/T | 焦煤（主焦煤） CNY/t | proxy (domestic CNY price; TE is USD futures) — convert with monthly CNY/USD |
| urea | Urea, USD/T | 尿素（小颗粒 / 中小颗粒） CNY/t | cross-check proxy (China domestic; TE Middle East granular USD) |
| sulfur | Sulfur, CNY/T | 硫酸（98%） sulphuric acid | proxy only, different product |
| kraft_pulp | Kraft Pulp, CNY/T | 纸浆（进口针叶浆） imported softwood kraft pulp | 2024-01..2026-10, direct |
| silicon | Silicon, CNY/T | 多晶硅（致密料） polysilicon, CNY/kg | proxy only, different product, 2026-01..2026-10 only |
| lithium | Lithium, CNY/T | 磷酸铁锂（普通动力型） LFP cathode, CNY/t | proxy only, different product, 2026-01..2026-10 only |

## Not available at NBS (searched all 97 tables)
Eggs CH, Soda Ash, Bitumen, metallurgical Silicon, Magnesium, Lithium carbonate, Titanium, rare earths, Manganese, Sulphur (element), HRC steel after May 2024 is present as 热轧普通板卷 (hot-rolled coil, CNY/t) if wanted — TE HRC Steel is USD/t.

## Refused / missing
- https://www.stats.gov.cn/english/PressRelease/ : the first request ended with "Connection reset by peer" (proxy relay log: tunnel closed after 3 s, 39 bytes received). Not a 403/429; not pursued further — the Chinese releases were used instead.
- https://www.stats.gov.cn/sj/zxfb/202407/t20240723_1955829.html (2024年7月中旬, 2nd ten-day period of July 2024): connection reset on both the first pass and the one second pass. Not retried further. July 2024 means therefore use 2 of 3 readings.
- Three other pages (index_5, 2025-01-03, 2025-12-12) reset once and were obtained on the second pass.
- No release exists (publication holidays, confirmed against the index pages) for: 2024-02 中旬, 2025-01 下旬, 2025-10 上旬, 2026-02 中旬, 2026-10 上旬 — those months have 2 readings.
- No HTTP 403/429/challenge was received from www.stats.gov.cn; every fetched page returned 200 with the data table. WAF header "WZWS-RAY" present but pages served normally.
