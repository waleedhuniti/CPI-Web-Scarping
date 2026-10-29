# فلو Dataiku: أسعار السحب مقابل الأسعار الرسمية حسب مجموعة CPI

النتيجة في الآخر هي داتاسيت `group_compare`، وفيه سطر لكل مجموعة: متوسط سعر السلعة من السحب، والمتوسط الرسمي، والفرق.
الشارت بيُبنى عليه.
نفس المنطق مكتوب كبايثون في `scripts/compare_official_month.py` وفي `dataiku/recipe_official_vs_scraped.py`، وأرقام الثلاثة متطابقة (698 سلعة، 43 مستبعدة، 29 مجموعة لـ 12-29 أكتوبر).

```
crawl_basket ──► crawl_prepared ─┐
                                 ├─► (Join) crawl_matched ──► crawl_priced ──► (Group) item_day ──► (Group) item_avg ─┐
official_prices ─► official_prepared ─┘                                                                             │
                                 └──────────────────────────────────────────────► (Join) item_compare ◄────────────┘
                                                                                         │
                                                                              (Group) group_compare ──► الشارت
```

## 1. الداتاسيتات الداخلة

| الاسم في Dataiku | الملف | ملاحظة |
|---|---|---|
| `crawl_basket` | `CPI_basket_12-29_Oct.csv` | ‏*+ Dataset → Upload your files*. في **Schema** خلّي `item_code` و`run_date` من نوع **string**. |
| `official_prices` | ملف الأسعار الرسمية (xlsx) | أعمدته: رمز السلعة، وصف السلعة، وحدة بيع السلعة، أغسطس، سبتمبر، أكتوبر. خلّي «رمز السلعة» **string** لحتى ما يروح الصفر من أوله. |

## 2. Prepare: `crawl_basket` → `crawl_prepared`

1. **Filter rows/cells on value**: العمود `accepted`، القيمة `yes`، والإجراء *Keep matching rows only*.
2. **Formula**: خانة الإخراج `item_code` (بتكتب فوق نفس العمود):
   ```
   if(length(toString(item_code)) == 8, "0" + toString(item_code), toString(item_code))
   ```
3. **Delete/Keep columns**: احتفظ بـ `run_date, item_code, cpi_group, retailer, title, price, price_spec`.

## 3. Prepare: `official_prices` → `official_prepared`

1. **Rename columns**:
   - رمز السلعة ← `item_code`
   - وصف السلعة ← `official_desc`
   - وحدة بيع السلعة ← `official_unit`
   - أكتوبر ← `official_price`

   احذف أغسطس وسبتمبر. لشهر ثاني، غيّر العمود اللي بتسمّيه `official_price`.
2. **Formula** لـ `item_code`: نفس معادلة الخطوة 2.2.
3. **Filter rows/cells on formula**: `toNumber(official_price) > 0`، والإجراء *Keep*.
4. **Extract with regular expression**: العمود `official_unit`، والـ prefix هو `wv_`.
   - الـ regex:
     ```
     (?i)(?:^|[\d\s*x×.])\s*(كغم?|كجم?|كيلو(?:غرام)?|غم?|غرام|جرام|جم|ملل?|لتر|ليتر|kg|gm?|gr|ml|cl|ltr|lt|l)(?!\p{L})
     ```
   - النتيجة عمود جديد اسمه `wv_1` تقريباً، وهو بيتعبّى بس لما الوحدة وزن أو حجم.
5. **Formula**: الإخراج `by_weight`:
   ```
   if(isNonBlank(wv_1), 1, 0)
   ```
   تأكد من الـ preview:
   - «400 غ» و«1.5 ليتر» و«6 * 125 ml» و«ا لتر» لازم تطلع **1**.
   - «قطعة» و«حبة» و«غسالة» و«غرفه / الليله» و«150 ملم» لازم تطلع **0**.

   بعدها احذف `wv_1`.

ليش هالخطوة؟ إذا الوحدة الرسمية وزن أو حجم، منقارن بسعر السحب محوّلاً لنفس الكمية (`price_spec`). غير هيك (حبة، عبوة، عدد) منقارن بسعر الرف (`price`).
`price_spec` لعبوات العدد بيضرب سعر العبوة بالعدد، فما بيصلح هناك.

## 4. Join: `crawl_prepared` × `official_prepared` → `crawl_matched`

- **Inner join** على `item_code` = `item_code`.
- من `official_prepared` خذ بس العمود `by_weight`.

## 5. Prepare: `crawl_matched` → `crawl_priced`

1. **Formula**: الإخراج `price_cmp`، والنوع double:
   ```
   if(by_weight == 1 && isNonBlank(price_spec), toNumber(price_spec), toNumber(price))
   ```
2. **Filter rows/cells on formula**: `price_cmp > 0`، والإجراء *Keep*.

## 6. Group: `crawl_priced` → `item_day` (متوسط المتاجر لكل يوم)

- **Keys**: `item_code`، `cpi_group`، `run_date`.
- **Aggregations**: `price_cmp` ← **Avg**، فبيطلع العمود `price_cmp_avg`.

## 7. Group: `item_day` → `item_avg` (متوسط الأيام لكل سلعة)

- **Keys**: `item_code`، `cpi_group`.
- **Aggregations**:
  - `price_cmp_avg` ← **Avg**
  - `run_date` ← **Count**
- بخطوة **Rename** بعدها (أو من *Output* بالريسيبي):
  - `price_cmp_avg_avg` ← `crawl_avg`
  - `run_date_count` ← `days_observed`

## 8. Join + Prepare: `item_avg` × `official_prepared` → `item_compare`

1. **Join** (inner على `item_code`): خذ `official_desc`، `official_unit`، `official_price`.
2. بنفس الريسيبي أو بـ Prepare بعده، ضيف **Formula**:

   | العمود | المعادلة |
   |---|---|
   | `price_difference` | `crawl_avg - official_price` |
   | `gap_pct` | `(crawl_avg / official_price - 1) * 100` |
   | `far` | `if(crawl_avg / official_price < 1/3 \|\| crawl_avg / official_price > 3, 1, 0)` |

`far = 1` يعني السحب أقل من ثلث الرسمي أو أكثر من ثلاث أضعافه. هاد غالباً منتج أو حجم ثاني انطابق.
بيظل بـ `item_compare` للمراجعة، بس بيطلع برا متوسطات المجموعات.

## 9. Group: `item_compare` → `group_compare`

- **Pre-filter**: `far == 0`.
- **Key**: `cpi_group`.
- **Aggregations**:
  - `item_code` ← **Count**، وبعدين بتسميه `matched_items`
  - `crawl_avg` ← **Avg**
  - `official_price` ← **Avg**
  - `days_observed` ← **Avg**
  - `gap_pct` ← **Median** إذا موجود بقائمة التجميع، وإلا خذه من ريسيبي البايثون

بعدها **Prepare** على الناتج:

| العمود | المعادلة |
|---|---|
| `price_difference` | `crawl_avg_avg - official_price_avg` |
| `group_gap_pct` | `(crawl_avg_avg / official_price_avg - 1) * 100` |
| `cpi_group_short` | `replace(cpi_group, "ـ", "")`، وبعدين **Find and replace** للأسماء الطويلة (الجدول تحت) |

| الاسم الطويل | الاسم القصير |
|---|---|
| أجهزة أخرى (غير كهربائية) وأصناف ومنتجات معدة للعناية الشخصية | منتجات العناية الشخصية |
| منتجات الاغذية غير المصنفة تحت بند اخر | أغذية أخرى |
| السكر والمربي والعسل والشوكلاتة والحلوي | السكر والحلويات |
| مشروبات أخرى (الطاقة وغيرها) | مشروبات أخرى |
| الأسماك والاغذية البحرية | الأسماك |
| اللبن و الجبن و البيض | الألبان والبيض |
| مستلزمات الملابس وإكسسواراتها | إكسسوارات الملابس |
| الأدوات الصغيرة ومستلزمات المنزل | أدوات صغيرة للمنزل |

## 10. الشارت (من `group_compare`)

**الشارت الأول: متوسط السعر، السحب مقابل الرسمي**
- **Vertical bars**.
- X = `cpi_group_short`.
- Y = `crawl_avg_avg` و`official_price_avg`، كمقياسين جنب بعض.
- فلتر: `official_price_avg < 100` و`matched_items >= 3`. هيك بتظل الأغذية والمشروبات والسلع المنزلية، بدون ما الأجهزة الغالية تخرّب المحور.

**الشارت الثاني: الفرق٪**
- **Horizontal bars**.
- Y = `cpi_group_short`.
- X = `median_item_gap_pct`، أو `group_gap_pct`.
- فلتر: `matched_items >= 3`.

## بديل أسرع: ريسيبي بايثون واحد

`dataiku/recipe_official_vs_scraped.py` بيعمل الخطوات 2-9 كلها مع الوسيط:
- **Inputs**: `crawl_basket` و`official_prices`.
- **Outputs**: `item_compare` و`group_compare`.

لشهر ثاني، غيّر `MONTH` بأول الملف.
محلياً: `python dataiku/recipe_official_vs_scraped.py <crawl.csv> <official.xlsx>` بيطبع جدول المجموعات للمطابقة.
