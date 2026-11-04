# قائمة المصادر (Sources): أسعار الويب في الرقم القياسي لأسعار المستهلك

اعتمد الملف `methodology_ar.md` على عشرة مصادر فقط، وكلها قُرئت قراءة معمّقة (deep read) في الملف `reads_all.json`. أي مصدر غير هذه العشرة لا يُستشهد به في المنهجية.

## أ) مصادر قُرئت ويُستشهد بها (10)

| # | المفتاح في النص | الجهة (Org) | العنوان (Title) | السنة | الرابط (URL) | حالة القراءة |
|---|---|---|---|---|---|---|
| 1 | Eurostat 2020 | Eurostat، الوحدة C-4 لإحصاءات الأسعار، بمشاركة النمسا وفنلندا وINSEE ولوكسمبورغ STATEC والنرويج وسلوفينيا SURS | Practical guidelines on web scraping for the HICP (November 2020) | 2020 | https://ec.europa.eu/eurostat/documents/272892/12032198/Guidelines-web-scraping-HICP-11-2020.pdf | قُرئ كاملاً (40 صفحة مع الملاحق) |
| 2 | HICP 2024 | Eurostat | Harmonised Index of Consumer Prices (HICP) Methodological Manual, 2024 edition (KS-GQ-24-003-EN-N) | 2024 | https://ec.europa.eu/eurostat/documents/3859598/18594110/KS-GQ-24-003-EN-N.pdf | قُرئ (الفصول 4 و5 و6 و8 والقسم 12.9) |
| 3 | Eurostat 2022 | Eurostat، فريق العمل المعني بالطرق متعددة الأطراف (Multilateral Methods)، تحرير Claude Lamboray | Guide on Multilateral Methods in the HICP, 2022 edition (KS-GQ-21-020-EN-N) | 2022 | https://ec.europa.eu/eurostat/documents/3859598/14503841/KS-GQ-21-020-EN-N.pdf | قُرئ. **تنبيه:** الدليل موجّه لبيانات الماسح الضوئي (scanner data)، ولا يذكر بيانات الويب إلا 4 مرات |
| 4 | CPI Manual 2020 | IMF وILO وOECD وEurostat وUNECE والبنك الدولي | Consumer Price Index Manual: Concepts and Methods (2020): الفقرات 5.191-5.206 والملحق 5.5 والملحق 5.6 والفقرات 4.76 و5.16 و6.34-6.35 | 2020 | https://www.ilo.org/sites/default/files/wcmsp5/groups/public/%40dgreports/%40stat/documents/publication/wcms_761444.pdf | قُرئت الأجزاء المذكورة فقط |
| 5 | ONS 2016 | ONS (المملكة المتحدة)، M. Mayhew | Imputing Web Scraped Prices | 2016 | https://www.ons.gov.uk/economy/inflationandpriceindices/methodologies/imputingwebscrapedprices | قُرئ كاملاً (ورقة PDF من 12 صفحة) |
| 6 | ONS 2017 | ONS، C. Payne (GSS Methodology Series) | Analysis of product turnover in web scraped clothing data, and its impact on methods for compiling price indices (مع تصحيح 2017/2018) | 2017 | https://www.ons.gov.uk/methodology/methodologicalpublications/generalmethodology/currentmethodologyarticles/analysisofproductturnoverinwebscrapedclothingdataanditsimpactonmethodsforcompilingpriceindices | قُرئ. البيانات ملابس جمعتها WGSN وليست أغذية |
| 7 | ONS 2020 | ONS | New index number methods in consumer price statistics | 2020 | https://www.ons.gov.uk/economy/inflationandpriceindices/articles/newindexnumbermethodsinconsumerpricestatistics/2020-09-01 | قُرئ. **تنبيه:** اختبارات الصيغ أُجريت على بيانات ماسح Dominick's |
| 8 | ONS 2022 | ONS، L. Greenhough وM. Spina | Outlier detection for rail fares and second-hand cars dynamic price data | 2022 | https://www.ons.gov.uk/economy/inflationandpriceindices/methodologies/outlierdetectionforrailfaresandsecondhandcarsdynamicpricedata | قُرئ كاملاً بـ curl لأن WebFetch لم يصل إلى الموقع. **تنبيه:** بيانات السيارات قوائم من Auto Trader بموجب اتفاقية تبادل بيانات وليست كشطاً، وبيانات القطارات بيانات معاملات |
| 9 | CBS 2016 | CBS هولندا، R. Griffioen وO. ten Bosch (ورقة لاجتماع UNECE/ILO) | On the use of internet data for the Dutch CPI | 2016 | https://olavtenbosch.github.io/pdf/2016_Session_2_Netherlands_on_the_use_of_internet_data_for_the_Dutch_CPI.pdf | قُرئ كاملاً (8 صفحات). المعادلتان وصلتا مشوّهتين وأُعيد بناؤهما من النص المحيط. النطاق ملابس فقط |
| 10 | Statbel 2018 | Statbel بلجيكا، D. Roels وK. Van Loon | Web scraping and online data collection and processing for the CPI (خبر 8 فبراير 2018)، والتحليل الكامل بالفرنسية: *Le webscraping, la collecte et le traitement de données en ligne pour l'IPC*، Analyse n°02 (55 صفحة) | 2018 | https://statbel.fgov.be/en/news/web-scraping-and-online-data-collection-and-processing-consumer-price-index | **الوصول جزئي:** ملف PDF على statbel.fgov.be أعاد صفحة CAPTCHA فلم يُتجاوز. قُرئ النص الكامل من نسخة Wayback Machine (HTTP 200). لا تصف الوثيقة طريقة السوبرماركت نفسها |

## ب) مصادر رُشّحت ولم تُقرأ في هذه المراجعة (لا يُستشهد بها)

لا توجد لهذه المصادر قراءة في `reads_all.json`، فلا نعرف هل كانت قابلة للقراءة أم لا. لم يُبنَ عليها أي ادعاء في المنهجية.

| الجهة | العنوان | السنة | الرابط | الحالة |
|---|---|---|---|---|
| ONS | ONS methodology working paper series number 12: A comparison of index number methodology used on UK web scraped price data | 2017 | https://www.ons.gov.uk/methodology/methodologicalpublications/generalmethodology/onsworkingpaperseries/onsmethodologyworkingpaperseriesnumber12acomparisonofindexnumbermethodologyusedonukwebscrapedpricedata | لم يُقرأ |
| ONS | Research indices using web scraped price data: August 2017 update | 2017 | https://www.ons.gov.uk/economy/inflationandpriceindices/articles/researchindicesusingwebscrapedpricedata/latest | لم يُقرأ |
| CBS (Chessa & Griffioen)، نشر INSEE | Comparing Price Indices of Clothing and Footwear for Scanner Data and Web Scraped Data | 2019 | https://insee.fr/en/statistiques/fichier/4203548/509_Chessa-Griffioen-EN.pdf | لم يُقرأ |
| Eurostat / ESS | ESS Web content retrieval guidelines | 2022 | https://cros.ec.europa.eu/system/files/2025-03/web_content_retrieval_guidelines_20220401_0.pdf | لم يُقرأ |
| مكتب الإحصاء السلوفاكي (P. Knížat) | Web scraped data in consumer price indices | 2023 | https://doi.org/10.3233/SJI-220115 | لم يُقرأ |
| Destatis | Fortschritte beim Einsatz von Web Scraping in der amtlichen Verbraucherpreisstatistik | 2019 | https://www.destatis.de/DE/Methoden/WISTA-Wirtschaft-und-Statistik/2019/04/fortschritte-einsatz-web-scraping-042019.pdf?__blob=publicationFile | لم يُقرأ |
| Destatis | Dynamische Preissetzung im Onlinehandel | 2020 | https://www.econstor.eu/bitstream/10419/220340/1/wista-2020-3-014-023.pdf | لم يُقرأ |
| Statistics Austria | VPI/HVPI Standard-Dokumentation | 2026 | https://www.statistik.at/fileadmin/shared/QM/Standarddokumentationen/VW/std_v_vpi_hvpi.pdf | لم يُقرأ |
| Istat | The use of different web scraping techniques and API to estimate Italian price inflation | 2022 | https://www.istat.it/storage/17Meeting-Ottawa/Room-papers/Web-scraping-techniques-and-API-to-estimate-Italian-inflation.pdf | لم يُقرأ |
| Statistics Norway | The use of online prices in the Norwegian CPI | 2015 | https://www.stat.go.jp/english/info/meetings/og2015/pdf/t1s2p5_pap.pdf | لم يُقرأ |
| INE إسبانيا | Índice de Precios de Consumo. Base 2025. Metodología | 2026 | https://www.ine.es/metodologia/t25/metodologia_IPC_base_2025.pdf | لم يُقرأ |
| SCB مع CBS وBNSI (ESSnet Web Intelligence) | UC3: Report on methodology and results for online prices | 2025 | https://cros.ec.europa.eu/system/files/2025-04/D3_7_WP3_UC3.pdf | لم يُقرأ |

## ج) ملفات داخلية استُخدمت للسياق (ليست مصادر منهجية)

- `agents/itemreview/brief.md`: وقائع المشروع (متجران، يومي، السعر العادي، الأخطاء المعروفة، السياسة).
- `agents/itemreview/aggregates.json`: أحجام المشكلات (637 بنداً وتصنيفاتها).
- `agents/itemreview/items_compact.tsv`: الجدول التفصيلي للبنود، ومنه حُسبت التقاطعات بين الحالة والتشخيص والإصلاح. مثال: الـ170 بنداً "عينة ثابتة" كلها من الـ247 تقدير مجموعة، والـ141 "انجراف مجموعة" منها 140 من الـ247، والـ23 "وحدة أو عبوة" منها 22 إصلاحها تصحيح الوحدة.
- `agents/brainstorm/final_plan.md`: الإجراءات A1-A14، ويُشار إليها بالرمز فقط.
- `/home/user/CPI-Web-Scarping/docs/retailers.md`: وفيه أن Spinneys أعاد HTTP 403 في اختبار 2026-10-11.
