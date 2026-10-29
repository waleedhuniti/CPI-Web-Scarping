// ------------------------------------------------------------ COICOP 2018 price tree (division > group > class > subclass > item type > products)
// Codes and English titles: UN COICOP 2018. Arabic titles: the Dubai Statistics Center CPI basket names where it has the
// class (4-digit codes such as 0112 = 01.1.2), otherwise a translation of the COICOP title. Item types (the last level, e.g.
// red meat / poultry) are the elementary aggregates under a COICOP subclass, coded "<subclass>-<letter>".
const COICOP = [
  ["01", "الأغذية والمشروبات غير الكحولية", "Food and non-alcoholic beverages"],
  ["01.1", "الأغذية", "Food"],
  ["01.1.1", "الحبوب ومنتجاتها", "Cereals and cereal products"],
  ["01.1.1.1", "الحبوب", "Cereals"], ["01.1.1.1-a", "الأرز", "Rice"],
  ["01.1.1.2", "دقيق الحبوب", "Flour of cereals"], ["01.1.1.2-a", "الدقيق والسميد", "Flour and semolina"],
  ["01.1.1.3", "الخبز والمخبوزات", "Bread and bakery products"], ["01.1.1.3-a", "الخبز والمخبوزات", "Bread and bakery products"],
  ["01.1.1.4", "حبوب الإفطار", "Breakfast cereals"], ["01.1.1.4-a", "حبوب الإفطار والشوفان", "Breakfast cereals and oats"],
  ["01.1.1.5", "المعكرونة والشعيرية والكسكس", "Macaroni, noodles, couscous and similar pasta products"],
  ["01.1.1.5-a", "المعكرونة", "Pasta"], ["01.1.1.5-b", "الشعيرية والنودلز", "Noodles and vermicelli"],
  ["01.1.2", "اللحوم", "Live animals, meat and other parts of slaughtered land animals"],
  ["01.1.2.2", "لحوم طازجة أو مبرّدة أو مجمّدة", "Meat, fresh, chilled or frozen"],
  ["01.1.2.2-a", "اللحوم الحمراء (بقري، ضأن، ماعز)", "Red meat (beef, lamb, goat)"], ["01.1.2.2-b", "الدواجن", "Poultry"],
  ["01.1.2.4", "الأحشاء والأجزاء الأخرى من الذبائح", "Offal, blood and other parts of slaughtered animals"], ["01.1.2.4-a", "الكبدة والأحشاء", "Liver and offal"],
  ["01.1.2.5", "مستحضرات اللحوم", "Meat, offal and other parts' preparations"], ["01.1.2.5-a", "لحوم مصنّعة ومحضّرة (نقانق، برجر، ناجتس)", "Processed meat (sausages, burgers, nuggets)"],
  ["01.1.3", "الأسماك والأغذية البحرية", "Fish and other seafood"],
  ["01.1.3.1", "أسماك طازجة أو مبرّدة أو مجمّدة", "Fish, live, fresh, chilled or frozen"], ["01.1.3.1-a", "الأسماك الطازجة والمجمّدة", "Fresh and frozen fish"],
  ["01.1.3.2", "أسماك مجففة أو مملّحة أو مدخّنة", "Fish, dried, salted, in brine or smoked"], ["01.1.3.2-a", "أسماك مدخّنة ومجففة", "Smoked and dried fish"],
  ["01.1.3.3", "مستحضرات الأسماك", "Fish preparations"], ["01.1.3.3-a", "التونة والسردين والأسماك المحضّرة", "Tuna, sardines and prepared fish"],
  ["01.1.3.4", "أغذية بحرية أخرى طازجة أو مجمّدة", "Other seafood, live, fresh, chilled or frozen"], ["01.1.3.4-a", "الروبيان والأغذية البحرية", "Shrimp and seafood"],
  ["01.1.4", "اللبن والجبن والبيض", "Milk, other dairy products and eggs"],
  ["01.1.4.1", "الحليب الخام وكامل الدسم", "Raw and whole milk"], ["01.1.4.1-a", "الحليب الطازج", "Fresh milk"],
  ["01.1.4.2", "الحليب منزوع الدسم", "Skimmed milk"], ["01.1.4.2-a", "حليب قليل أو خالي الدسم", "Low-fat and skimmed milk"],
  ["01.1.4.3", "أنواع أخرى من الحليب والقشطة", "Other milk and cream"], ["01.1.4.3-a", "الحليب المجفف والمكثف والقشطة", "Powdered and condensed milk, cream"],
  ["01.1.4.4", "الحليب النباتي", "Non-animal milk"], ["01.1.4.4-a", "الحليب النباتي", "Plant-based milk"],
  ["01.1.4.5", "الأجبان", "Cheese"], ["01.1.4.5-a", "الأجبان", "Cheese"],
  ["01.1.4.6", "الزبادي والمنتجات المشابهة", "Yoghurt and similar products"], ["01.1.4.6-a", "الزبادي واللبن", "Yoghurt and laban"],
  ["01.1.4.7", "حلويات ومشروبات الحليب", "Milk-based dessert and beverages"], ["01.1.4.7-a", "الحليب المنكّه", "Flavoured milk"], ["01.1.4.7-b", "حلويات الألبان", "Dairy desserts"],
  ["01.1.4.8", "البيض", "Eggs"], ["01.1.4.8-a", "البيض", "Eggs"],
  ["01.1.5", "الزيوت والدهون", "Oils and fats"],
  ["01.1.5.1", "الزيوت النباتية", "Vegetable oils"], ["01.1.5.1-a", "زيوت الطبخ والزيتون", "Cooking and olive oils"],
  ["01.1.5.2", "الزبدة والدهون المشتقة من الحليب", "Butter and other fats derived from milk"], ["01.1.5.2-a", "الزبدة والسمن", "Butter and ghee"],
  ["01.1.5.3", "المارجرين والمستحضرات المشابهة", "Margarine and similar preparations"], ["01.1.5.3-a", "المارجرين", "Margarine"],
  ["01.1.6", "الفواكه والمكسرات", "Fruits and nuts"],
  ["01.1.6.1", "التمور والتين والفواكه الاستوائية", "Dates, figs and tropical fruits, fresh"], ["01.1.6.1-a", "التمور", "Dates"], ["01.1.6.1-b", "الموز والمانجو والفواكه الاستوائية", "Bananas, mangoes and tropical fruit"],
  ["01.1.6.2", "الحمضيات", "Citrus fruits, fresh"], ["01.1.6.2-a", "البرتقال والليمون والحمضيات", "Oranges, lemons and citrus"],
  ["01.1.6.3", "الفواكه ذات النواة والتفاحيات", "Stone fruits and pome fruits, fresh"], ["01.1.6.3-a", "التفاح والكمثرى والخوخ", "Apples, pears and stone fruit"],
  ["01.1.6.4", "العنب والتوت", "Berries, fresh"], ["01.1.6.4-a", "العنب والفراولة والتوت", "Grapes, strawberries and berries"],
  ["01.1.6.5", "فواكه طازجة أخرى", "Other fruits, fresh"], ["01.1.6.5-a", "البطيخ والرمان وفواكه أخرى", "Melons, pomegranates and other fruit"],
  ["01.1.6.6", "الفواكه المجمّدة", "Frozen fruit"], ["01.1.6.6-a", "الفواكه المجمّدة", "Frozen fruit"],
  ["01.1.6.7", "الفواكه المجففة", "Fruit, dried and dehydrated"], ["01.1.6.7-a", "الفواكه المجففة", "Dried fruit"],
  ["01.1.6.8", "المكسرات", "Nuts, in shell or shelled"], ["01.1.6.8-a", "المكسرات", "Nuts"],
  ["01.1.7", "البقول والخضروات", "Vegetables, tubers, plantains, cooking bananas and pulses"],
  ["01.1.7.1", "الخضروات الورقية والساقية", "Leafy or stem vegetables, fresh or chilled"], ["01.1.7.1-a", "الخس والسبانخ والخضار الورقية", "Lettuce, spinach and leafy vegetables"],
  ["01.1.7.2", "الخضروات الثمرية", "Fruit-bearing vegetables, fresh or chilled"], ["01.1.7.2-a", "الطماطم والخيار والفلفل", "Tomatoes, cucumbers and peppers"],
  ["01.1.7.3", "البقول الخضراء", "Green leguminous vegetables, fresh or chilled"], ["01.1.7.3-a", "الفاصوليا والبازلاء الخضراء", "Green beans and peas"],
  ["01.1.7.4", "خضروات أخرى", "Other vegetables, fresh or chilled"], ["01.1.7.4-a", "البصل والثوم والجزر والفطر", "Onions, garlic, carrots and mushrooms"],
  ["01.1.7.5", "الدرنيات", "Tubers, plantains and cooking bananas"], ["01.1.7.5-a", "البطاطس والدرنيات", "Potatoes and tubers"],
  ["01.1.7.6", "البقوليات الجافة", "Pulses"], ["01.1.7.6-a", "العدس والحمص والفول", "Lentils, chickpeas and beans"],
  ["01.1.7.8", "الخضروات المجمّدة", "Vegetables, tubers, plantains and cooking bananas, frozen"], ["01.1.7.8-a", "الخضار والبطاطس المجمّدة", "Frozen vegetables and fries"],
  ["01.1.7.9", "مستحضرات الخضروات والبقول", "Vegetables and pulses ground and other preparations"], ["01.1.7.9-a", "الخضار والبقول المعلّبة", "Canned vegetables and pulses"],
  ["01.1.8", "السكر والمربى والعسل والشوكولاتة والحلوى", "Sugar, confectionery and desserts"],
  ["01.1.8.1", "سكر القصب والبنجر", "Cane and beet sugar"], ["01.1.8.1-a", "السكر", "Sugar"],
  ["01.1.8.2", "بدائل السكر", "Other sugar and sugar substitutes"], ["01.1.8.2-a", "المحليات وبدائل السكر", "Sweeteners"],
  ["01.1.8.3", "المربى والعسل", "Jams, fruit jellies, marmalades, honey"], ["01.1.8.3-a", "العسل", "Honey"], ["01.1.8.3-b", "المربى", "Jam"],
  ["01.1.8.4", "زبدة المكسرات والطحينة", "Nut purée, nut butter and nut pastes"], ["01.1.8.4-a", "زبدة الفول السوداني والطحينة", "Peanut butter and tahini"],
  ["01.1.8.5", "الشوكولاتة والكاكاو", "Chocolate, cocoa, and cocoa-based food products"], ["01.1.8.5-a", "الشوكولاتة والكاكاو", "Chocolate and cocoa"],
  ["01.1.8.6", "المثلجات والآيس كريم", "Ice, ice cream and sorbet"], ["01.1.8.6-a", "الآيس كريم", "Ice cream"],
  ["01.1.8.9", "حلويات أخرى", "Other sugar confectionery and desserts n.e.c."], ["01.1.8.9-a", "الحلويات والجيلي والكاسترد", "Sweets, jelly and custard"],
  ["01.1.9", "منتجات غذائية غير مصنّفة في مكان آخر", "Ready-made food and other food products n.e.c."],
  ["01.1.9.1", "الأطعمة الجاهزة", "Ready-made food"], ["01.1.9.1-a", "الأطعمة الجاهزة والمجمّدة", "Ready and frozen meals"],
  ["01.1.9.3", "الملح والصلصات", "Salt, condiments and sauces"], ["01.1.9.3-a", "الملح", "Salt"], ["01.1.9.3-b", "الصلصات والخل", "Sauces and vinegar"],
  ["01.1.9.4", "البهارات والأعشاب", "Spices, culinary herbs and seeds"], ["01.1.9.4-a", "البهارات", "Spices"],
  ["01.1.9.9", "منتجات غذائية أخرى", "Other food products n.e.c."], ["01.1.9.9-a", "مستلزمات الطبخ والخبز الأخرى", "Other cooking and baking products"],
  ["01.2", "المشروبات غير الكحولية", "Non-alcoholic beverages"],
  ["01.2.1", "العصائر", "Fruit and vegetable juices"], ["01.2.1.0", "العصائر", "Fruit and vegetable juices"], ["01.2.1.0-a", "العصائر", "Juices"],
  ["01.2.2", "البن", "Coffee and coffee substitutes"], ["01.2.2.0", "البن", "Coffee and coffee substitutes"], ["01.2.2.0-a", "البن والقهوة", "Coffee"],
  ["01.2.3", "الشاي", "Tea, maté and other plant products for infusion"], ["01.2.3.0", "الشاي", "Tea, maté and other plant products for infusion"], ["01.2.3.0-a", "الشاي", "Tea"],
  ["01.2.5", "المياه المعدنية", "Water"], ["01.2.5.0", "المياه المعدنية", "Water"], ["01.2.5.0-a", "مياه الشرب", "Drinking water"],
  ["01.2.6", "المشروبات الغازية", "Soft drinks"], ["01.2.6.0", "المشروبات الغازية", "Soft drinks"], ["01.2.6.0-a", "المشروبات الغازية", "Soft drinks"],
  ["01.2.9", "مشروبات أخرى (الطاقة وغيرها)", "Other non-alcoholic beverages"], ["01.2.9.0", "مشروبات أخرى", "Other non-alcoholic beverages"], ["01.2.9.0-a", "مشروبات الطاقة", "Energy drinks"],
  ["03", "الملابس والأحذية", "Clothing and footwear"],
  ["03.1", "الملابس", "Clothing"],
  ["03.1.2", "الملابس الجاهزة", "Garments"],
  ["03.1.2.1", "ملابس الرجال والأولاد", "Garments for men or boys"],
  ["03.1.2.1-a", "القمصان والتيشيرتات", "Shirts and T-shirts"], ["03.1.2.1-b", "الجينز والبناطيل", "Jeans and trousers"], ["03.1.2.1-c", "الجاكيتات والبدلات والتريكو", "Jackets, suits and knitwear"], ["03.1.2.1-d", "الملابس الداخلية والجوارب", "Underwear and socks"], ["03.1.2.1-e", "ملابس أخرى", "Other garments"],
  ["03.1.2.2", "ملابس النساء والبنات", "Garments for women or girls"],
  ["03.1.2.2-a", "البلوزات والقمصان والتيشيرتات", "Tops, shirts and T-shirts"], ["03.1.2.2-b", "الجينز والبناطيل", "Jeans and trousers"], ["03.1.2.2-c", "الفساتين والعبايات", "Dresses and abayas"], ["03.1.2.2-d", "الجاكيتات والتريكو", "Jackets and knitwear"], ["03.1.2.2-e", "الملابس الداخلية والجوارب", "Underwear and socks"], ["03.1.2.2-f", "ملابس أخرى", "Other garments"],
  ["03.1.2.3", "ملابس الرضّع (حتى سنتين)", "Garments for infants (0 to under 2 years)"], ["03.1.2.3-a", "ملابس الرضّع", "Infant clothing"],
  ["03.2", "الأحذية", "Footwear"],
  ["03.2.1", "الأحذية", "Shoes and other footwear"],
  ["03.2.1.1", "أحذية الرجال", "Footwear for men"], ["03.2.1.1-a", "أحذية الرجال", "Men's shoes"],
  ["03.2.1.2", "أحذية النساء", "Footwear for women"], ["03.2.1.2-a", "أحذية النساء", "Women's shoes"],
  ["03.2.1.3", "أحذية الرضّع والأطفال", "Footwear for infants and children"], ["03.2.1.3-a", "أحذية الأطفال", "Children's shoes"],
  ["05", "الأثاث والتجهيزات المنزلية", "Furnishings, household equipment and routine household maintenance"],
  ["05.2", "المنسوجات المنزلية", "Household textiles"], ["05.2.1", "المنسوجات المنزلية", "Household textiles"],
  ["05.2.1.2", "مفارش وأغطية السرير", "Bed linen and bedding"], ["05.2.1.2-a", "مفارش السرير", "Bed sheets"],
  ["05.3", "الأجهزة المنزلية", "Household appliances"],
  ["05.3.1", "الأجهزة المنزلية الكبيرة", "Major household appliances, whether electric or not"],
  ["05.3.1.1", "أجهزة المطبخ الكبيرة", "Major kitchen appliances"], ["05.3.1.1-a", "الثلاجات والمجمّدات", "Refrigerators and freezers"], ["05.3.1.1-b", "غسالات الصحون", "Dishwashers"],
  ["05.3.1.2", "أجهزة الغسيل الكبيرة", "Major laundry appliances"], ["05.3.1.2-a", "غسالات الملابس", "Washing machines"],
  ["05.3.1.3", "المدافئ والمكيفات", "Heaters, air conditioners"], ["05.3.1.3-a", "المكيفات", "Air conditioners"],
  ["05.3.1.4", "أجهزة التنظيف", "Cleaning equipment"], ["05.3.1.4-a", "المكانس الكهربائية", "Vacuum cleaners"],
  ["05.3.2", "الأجهزة المنزلية الصغيرة", "Small household appliances"],
  ["05.3.2.1", "أجهزة الطبخ وتحضير الطعام الصغيرة", "Small appliances for cooking and processing of food"], ["05.3.2.1-a", "الخلاطات وأجهزة المطبخ الصغيرة", "Blenders and small kitchen appliances"],
  ["05.3.2.2", "أجهزة تحضير المشروبات", "Small appliances for preparing beverages"], ["05.3.2.2-a", "الغلايات وآلات القهوة", "Kettles and coffee machines"],
  ["05.3.2.9", "أجهزة منزلية صغيرة أخرى", "Other small household appliances"], ["05.3.2.9-a", "المكاوي والمراوح وأجهزة أخرى", "Irons, fans and other appliances"],
  ["05.4", "الأواني وأدوات المائدة والمطبخ", "Glassware, tableware and household utensils"], ["05.4.0", "الأواني وأدوات المائدة والمطبخ", "Glassware, tableware and household utensils"],
  ["05.4.0.1", "الأواني الزجاجية والخزفية", "Glassware, crystal-ware, ceramic ware and chinaware"], ["05.4.0.1-a", "الأطباق وأواني المائدة", "Plates and tableware"],
  ["05.4.0.3", "أدوات المطبخ", "Kitchen utensils and articles"], ["05.4.0.3-a", "أواني الطبخ", "Cookware"],
  ["05.5", "الأدوات والمعدات للمنزل والحديقة", "Tools and equipment for house and garden"], ["05.5.2", "الأدوات الصغيرة ومستلزمات المنزل", "Non-motorized tools and miscellaneous accessories"],
  ["05.5.2.2", "مستلزمات متنوعة", "Miscellaneous accessories"], ["05.5.2.2-a", "البطاريات والمصابيح", "Batteries and light bulbs"],
  ["05.6", "السلع والخدمات للصيانة المنزلية الاعتيادية", "Goods and services for routine household maintenance"],
  ["05.6.1", "السلع المنزلية غير المعمّرة", "Non-durable household goods"],
  ["05.6.1.1", "منتجات التنظيف والصيانة المنزلية", "Household cleaning and maintenance products"], ["05.6.1.1-a", "منظفات الغسيل", "Laundry detergents"], ["05.6.1.1-b", "منظفات الصحون", "Dishwashing products"], ["05.6.1.1-c", "منظفات المنزل والمطهرات", "Household cleaners and disinfectants"],
  ["05.6.1.9", "سلع منزلية غير معمّرة أخرى", "Other non-durable household goods"], ["05.6.1.9-a", "المعطّرات ومبيدات الحشرات", "Air fresheners and insecticides"], ["05.6.1.9-b", "مناديل المطبخ الورقية", "Kitchen paper towels"],
  ["06", "الصحة", "Health"],
  ["06.1", "الأدوية والمنتجات الصحية", "Medicines and health products"],
  ["06.1.1", "الأدوية", "Medicines"], ["06.1.1.1", "الأدوية واللقاحات والمستحضرات الصيدلانية", "Medicines, vaccines and other pharmaceutical preparations"], ["06.1.1.1-a", "المسكّنات (باراسيتامول)", "Painkillers (paracetamol)"], ["06.1.1.1-b", "الفيتامينات والمكمّلات", "Vitamins and supplements"],
  ["06.1.2", "المنتجات الطبية", "Medical products"], ["06.1.2.1", "منتجات التشخيص الطبي", "Medical diagnostic products"], ["06.1.2.1-a", "موازين الحرارة", "Thermometers"],
  ["06.1.2.3", "أدوات العلاج للاستخدام الشخصي", "Treatment devices for personal use"], ["06.1.2.3-a", "مستلزمات الإسعافات الأولية", "First aid supplies"],
  ["07", "النقل", "Transport"],
  ["07.1", "شراء المركبات", "Purchase of vehicles"], ["07.1.3", "الدراجات الهوائية", "Bicycles"], ["07.1.3.0", "الدراجات الهوائية", "Bicycles"], ["07.1.3.0-a", "الدراجات الهوائية", "Bicycles"],
  ["07.2", "تشغيل معدات النقل الشخصية", "Operation of personal transport equipment"],
  ["07.2.1", "قطع غيار وإكسسوارات المركبات", "Parts and accessories for personal transport equipment"],
  ["07.2.1.2", "قطع غيار المركبات", "Parts for personal transport equipment"], ["07.2.1.2-a", "بطاريات السيارات", "Car batteries"],
  ["07.2.1.3", "إكسسوارات المركبات", "Accessories for personal transport equipment"], ["07.2.1.3-a", "إكسسوارات السيارات", "Car accessories"],
  ["07.2.2", "الوقود ومواد التشحيم", "Fuels and lubricants for personal transport equipment"], ["07.2.2.4", "مواد التشحيم", "Lubricants"], ["07.2.2.4-a", "زيوت المحركات", "Engine oil"],
  ["08", "الاتصالات والمعلومات", "Information and communication"],
  ["08.1", "أجهزة المعلومات والاتصالات", "Information and communication equipment"],
  ["08.1.2", "الهواتف المحمولة", "Mobile telephone equipment"], ["08.1.2.0", "الهواتف المحمولة", "Mobile telephone equipment"], ["08.1.2.0-a", "الهواتف المحمولة", "Mobile phones"],
  ["08.1.3", "أجهزة الحاسوب واللوحية", "Information processing equipment"],
  ["08.1.3.1", "الحواسيب المحمولة واللوحية", "Computers, laptops and tablets"], ["08.1.3.1-a", "الحواسيب المحمولة", "Laptops"], ["08.1.3.1-b", "الأجهزة اللوحية", "Tablets"],
  ["08.1.3.2", "الملحقات الطرفية ومستهلكاتها", "Peripheral equipment and its consumable components"], ["08.1.3.2-a", "الشاشات والطابعات والتخزين والشبكات", "Monitors, printers, storage and networking"],
  ["08.1.4", "أجهزة التلفاز والصوت", "Equipment for the reception, recording and reproduction of sound and vision"], ["08.1.4.0", "أجهزة التلفاز والصوت", "Equipment for the reception, recording and reproduction of sound and vision"],
  ["08.1.4.0-a", "أجهزة التلفاز", "Televisions"], ["08.1.4.0-b", "السماعات وأجهزة الصوت", "Headphones, earphones and speakers"],
  ["08.1.9", "أجهزة اتصالات وصوت أخرى", "Other information and communication equipment and accessories"],
  ["08.1.9.1", "أجهزة اتصالات أخرى", "Other information and communication equipment"], ["08.1.9.1-a", "الساعات الذكية", "Smartwatches"],
  ["08.1.9.2", "ملحقات أجهزة الاتصالات", "Other information and communication accessories"], ["08.1.9.2-a", "الشواحن والكوابل والأغطية", "Chargers, cables, power banks and cases"],
  ["09", "الترفيه والرياضة والثقافة", "Recreation, sport and culture"],
  ["09.1", "السلع المعمّرة للترفيه", "Recreational durables"], ["09.1.1", "معدات التصوير والأجهزة البصرية", "Photographic and cinematographic equipment and optical instruments"],
  ["09.1.1.1", "الكاميرات", "Cameras"], ["09.1.1.1-a", "الكاميرات", "Cameras"],
  ["09.2", "سلع ترفيهية أخرى", "Other recreational goods"], ["09.2.1", "الألعاب", "Games, toys and hobbies"],
  ["09.2.1.1", "أجهزة وألعاب الفيديو", "Video game computers, game consoles, game apps and software"], ["09.2.1.1-a", "أجهزة وألعاب الفيديو", "Game consoles and video games"],
  ["09.2.1.2", "ألعاب أخرى", "Other games, toys and hobbies"], ["09.2.1.2-a", "ألعاب الأطفال", "Toys"],
  ["09.2.1.3", "مستلزمات الاحتفالات", "Celebration articles"], ["09.2.1.3-a", "الأزياء التنكرية ومستلزمات الحفلات", "Costumes and party articles"],
  ["09.3", "منتجات الحدائق والحيوانات الأليفة", "Garden products and pets"],
  ["09.3.1", "منتجات الحدائق والنباتات والزهور", "Garden products, plants and flowers"], ["09.3.1.1", "منتجات الحدائق", "Garden products"], ["09.3.1.1-a", "مستلزمات الحدائق", "Garden supplies"],
  ["09.3.2", "مستلزمات الحيوانات الأليفة", "Pets and products for pets"], ["09.3.2.2", "منتجات الحيوانات الأليفة", "Products for pets and other household animals"], ["09.3.2.2-a", "أغذية الحيوانات الأليفة", "Pet food"],
  ["09.7", "الصحف والكتب والقرطاسية", "Newspapers, books and stationery"],
  ["09.7.1", "الكتب", "Books"], ["09.7.1.9", "كتب أخرى", "Other books"], ["09.7.1.9-a", "الكتب", "Books"],
  ["09.7.4", "القرطاسية ومواد الرسم", "Stationery and drawing materials"], ["09.7.4.0", "القرطاسية ومواد الرسم", "Stationery and drawing materials"], ["09.7.4.0-a", "الدفاتر والأقلام والقرطاسية", "Notebooks, pens and stationery"],
  ["13", "العناية الشخصية والسلع والخدمات المتنوعة", "Personal care, social protection and miscellaneous goods and services"],
  ["13.1", "العناية الشخصية", "Personal care"],
  ["13.1.1", "أجهزة العناية الشخصية الكهربائية", "Electric appliances for personal care"], ["13.1.1.1", "أجهزة العناية الشخصية الكهربائية", "Electric appliances for personal care"], ["13.1.1.1-a", "مجففات الشعر وماكينات الحلاقة", "Hair dryers, shavers and trimmers"],
  ["13.1.2", "أجهزة أخرى (غير كهربائية) وأصناف ومنتجات معدة للعناية الشخصية", "Other appliances, articles and products for personal care"],
  ["13.1.2.0", "منتجات العناية الشخصية", "Other appliances, articles and products for personal care"],
  ["13.1.2.0-a", "العطور", "Perfumes"], ["13.1.2.0-b", "مزيلات العرق", "Deodorants"], ["13.1.2.0-c", "الشامبو والصابون", "Shampoo and soap"], ["13.1.2.0-d", "العناية بالبشرة", "Skin care"],
  ["13.1.2.0-e", "معجون الأسنان", "Toothpaste"], ["13.1.2.0-f", "المناديل الورقية", "Facial tissues"], ["13.1.2.0-g", "أدوات الحلاقة", "Razors"], ["13.1.2.0-h", "الفوط الصحية والحفاضات", "Sanitary pads and diapers"],
  ["13.2", "مقتنيات شخصية أخرى", "Other personal effects"], ["13.2.9", "سلع شخصية أخرى", "Other personal effects n.e.c."],
  ["13.2.9.1", "حقائب السفر ومستلزمات الأطفال وسلع شخصية أخرى", "Travel goods and articles for babies and other personal effects n.e.c."], ["13.2.9.1-a", "الحقائب المدرسية", "School bags"],
];
const COICOP_SKIP = ["06", "07"];                 // health and transport: outside this team's scope
const CNODE = Object.fromEntries(COICOP.map(([c, ar, en]) => [c, { code: c, ar, en }]));
const cParent = (c) => c.includes("-") ? c.slice(0, c.indexOf("-")) : c.includes(".") ? c.slice(0, c.lastIndexOf(".")) : "";

// which item type a scraped product belongs to, from the shop's category (our crawl) and the product title
function coicopOf(cat, title) {
  const c = String(cat || "").toLowerCase().trim(), t = " " + String(title || "").toLowerCase() + " ";
  const has = (re) => re.test(t);
  const gender = () => has(/\bwomen|\bwoman|\bladies|\blady\b|\bgirls?\b|\bfemale/) ? "f" : has(/\bmen\b|\bmen'?s\b|\bmens\b|\bboys?\b|\bmale\b|\bgents?\b/) ? "m" : has(/\bbaby\b|\binfants?\b|\bnewborn|\btoddler|\bmonths?\b|\b\d+\s?-\s?\d+\s?m\b/) ? "b" : has(/\bkids?\b|\bchildren|\bjunior|\byouth\b/) ? "k" : "";
  const garment = (g) => {                      // which garment type for men/boys (m) or women/girls (f)
    if (has(/costume|cosplay|halloween|fancy dress|party dress up/)) return "09.2.1.3-a";
    if (g === "b") return "03.1.2.3-a";
    const m = g !== "f";
    if (has(/underwear|brief|boxer|panty|panties|bra\b|vests?\b|socks?\b|sleepsuit|pyjama|pajama/)) return m ? "03.1.2.1-d" : "03.1.2.2-e";
    if (!m && has(/dress|abaya|skirt|kaftan|jumpsuit/)) return "03.1.2.2-c";
    if (has(/jeans|trouser|pants|chino|short|jogger|legging/)) return m ? "03.1.2.1-b" : "03.1.2.2-b";
    if (has(/jacket|coat|blazer|suit\b|knit|cardigan|jumper|sweater|hoodie|sweatshirt|gilet|bomber|parka/)) return m ? "03.1.2.1-c" : "03.1.2.2-d";
    if (has(/shirt|t-shirt|tee\b|top\b|polo|blouse/)) return m ? "03.1.2.1-a" : "03.1.2.2-a";
    return m ? "03.1.2.1-e" : "03.1.2.2-f";
  };
  const fish = () => has(/shrimp|prawn|crab\b|lobster|squid|calamari|mussel|clam\b|octopus|oyster|scallop|cuttlefish|seafood/) ? (has(/stick|breaded|tempura/) ? "01.1.3.3-a" : "01.1.3.4-a")
    : has(/tuna|sardine|canned|\btin\b|in oil|in brine|finger|breaded|fish cake|surimi|crab stick|mackerel in/) ? "01.1.3.3-a"
    : has(/smoked|salted|dried|anchov/) ? "01.1.3.2-a" : "01.1.3.1-a";
  const meat = (poultryCat) => has(/sausage|burger|nugget|kofta|kebab|kabab|mortadella|salami|hot ?dog|luncheon|frank|shawarma|popcorn|tender|strips|breaded|marinated|meat ?ball|pepperoni|bacon|pastrami|\bham\b|cold cut|tikka|samosa|crispy|cordon|escalope|schnitzel|sliced turkey|smoked|spicy|bbq|kibbeh|corned/) ? "01.1.2.5-a"
    : has(/liver|kidney|heart|gizzard|tripe|tongue|brain|\bfeet\b|trotter|offal|marrow/) ? "01.1.2.4-a"
    : poultryCat || has(/chicken|poultry|turkey|duck|quail|\bhen\b/) ? "01.1.2.2-b" : "01.1.2.2-a";
  const fruit = () => has(/frozen/) ? "01.1.6.6-a" : has(/dried|raisin|prune|dehydrated/) ? "01.1.6.7-a"
    : has(/orange|lemon|lime\b|mandarin|tangerine|grapefruit|clementine|pomelo|citrus|kumquat/) ? "01.1.6.2-a"
    : has(/apple|pear\b|pears|peach|plum|apricot|cherr|nectarine|quince/) ? "01.1.6.3-a"
    : has(/berr|grape/) ? "01.1.6.4-a"
    : has(/banana|mango|pineapple|papaya|kiwi|avocado|guava|passion|dragon|lychee|rambutan|coconut|\bfigs?\b|jackfruit|mangosteen|longan/) ? "01.1.6.1-b"
    : "01.1.6.5-a";
  const veg = () => has(/frozen/) ? "01.1.7.8-a" : has(/canned|\btin\b|paste|puree|pickle/) ? "01.1.7.9-a"
    : has(/lentil|chickpea|kidney bean|fava|\bfoul\b|\bdal\b|dhal|split pea|black eyed|moong|dried beans/) ? "01.1.7.6-a"
    : has(/potato|cassava|yam\b|taro|sweet potato|colocasia/) ? "01.1.7.5-a"
    : has(/lettuce|spinach|cabbage|parsley|coriander|\bmint|celery|broccoli|cauliflower|leek|rocket|arugula|kale|molokhia|mulukhiyah|dill|basil|asparagus|artichoke|chard|watercress|spring onion|herbs?\b/) ? "01.1.7.1-a"
    : has(/tomato|cucumber|pepper|capsicum|eggplant|aubergine|brinjal|zucchini|courgette|squash|pumpkin|okra|bhindi|chil+i|\bcorn\b|marrow|gourd/) ? "01.1.7.2-a"
    : has(/green beans?|\bpeas?\b|snow pea|beans/) ? "01.1.7.3-a" : "01.1.7.4-a";
  const fruitOrVeg = () => has(/apple|banana|orange|mango|grape|berr|melon|pear\b|peach|plum|lemon|lime\b|kiwi|avocado|pineapple|papaya|pomegranate|guava|fig\b|cherr|apricot|mandarin|fruit|dates?\b/) && !has(/tomato|pepper|aubergine|eggplant/) ? fruit() : veg();
  const cupboard = () => has(/tuna|sardine/) ? "01.1.3.3-a" : has(/tomato paste|canned|chickpea|baked beans|\bbeans\b|sweet corn|\bpeas\b|foul|fava/) ? "01.1.7.9-a"
    : has(/sauce|ketchup|mayo|mustard|vinegar|dressing|chutney|stock|bouillon|\bcubes?\b|soy/) ? "01.1.9.3-b"
    : has(/spice|cumin|turmeric|cardamom|cinnamon|masala|paprika|saffron|curry|black pepper|chil+i powder|clove|oregano|thyme|za.?atar|seasoning/) ? "01.1.9.4-a"
    : has(/\bsalt\b/) ? "01.1.9.3-a" : has(/\boil\b|ghee/) ? (has(/ghee/) ? "01.1.5.2-a" : "01.1.5.1-a")
    : has(/noodle|vermicelli/) ? "01.1.1.5-b" : has(/pasta|spaghetti|macaroni|penne|fusilli|lasagn/) ? "01.1.1.5-a" : has(/\brice\b/) ? "01.1.1.1-a"
    : has(/jam\b|marmalade/) ? "01.1.8.3-b" : has(/honey/) ? "01.1.8.3-a" : has(/chocolate|cocoa|nutella/) ? "01.1.8.5-a"
    : has(/oats|corn ?flakes|cereal|muesli|granola/) ? "01.1.1.4-a" : has(/soup|ready meal|instant/) ? "01.1.9.1-a"
    : has(/sweetener|stevia|sucralose/) ? "01.1.8.2-a" : has(/\bsugar\b/) ? "01.1.8.1-a" : has(/flour|semolina/) ? "01.1.1.2-a"
    : has(/cake mix|brownie mix|pancake mix|muffin mix/) ? "01.1.1.3-a" : has(/jelly|custard|pudding|caramel/) ? "01.1.8.9-a" : "01.1.9.9-a";
  switch (true) {
    // food
    case /^(beef|lamb|fresh food fresh meat poultry fresh beef veal)$/.test(c): return meat(false);
    case /^(chicken|fresh food fresh meat poultry fresh chicken)$/.test(c): return meat(true);
    case /^(fish|fresh food fresh fish seafoods)$/.test(c): return fish();
    case /^(milk|fresh food dairy eggs cheese fresh milk)$/.test(c):
      return has(/almond|\boat|soy|coconut|rice milk|plant/) ? "01.1.4.4-a" : has(/chocolate|strawberry|banana|flavou?r|milkshake|vanilla|mango|saffron|coffee/) ? "01.1.4.7-a"
        : has(/condensed|evaporated|powder|cream|creamer/) ? "01.1.4.3-a" : has(/laban|buttermilk|ayran/) ? "01.1.4.6-a"
        : has(/skim|fat free|low fat|light|\b0%|\b1%|half/) ? "01.1.4.2-a" : "01.1.4.1-a";
    case c === "cheese": return "01.1.4.5-a";
    case /^(yoghurt|fresh food dairy eggs cheese yoghurt chilled desserts)$/.test(c): return has(/dessert|pudding|custard|caramel|jelly|mousse/) ? "01.1.4.7-b" : "01.1.4.6-a";
    case /^(eggs|fresh food dairy eggs cheese eggs)$/.test(c): return has(/\beggs?\b/) ? "01.1.4.8-a" : null;
    case c === "butter": return has(/margarine|spread/) ? "01.1.5.3-a" : "01.1.5.2-a";
    case c === "oil": return has(/\boil\b|ghee/) ? (has(/ghee/) ? "01.1.5.2-a" : "01.1.5.1-a") : null;
    case c === "fruit": return fruitOrVeg();
    case c === "dates": return "01.1.6.1-a";
    case c === "nuts": return has(/peanut butter|nut butter|tahini|tahina/) ? "01.1.8.4-a" : "01.1.6.8-a";
    case c === "vegetables": return fruitOrVeg();
    case c === "fresh food fruits vegetables": return fruitOrVeg();
    case c === "rice": return "01.1.1.1-a";
    case c === "grocery food cupboard rice pasta noodles": return has(/\brice\b/) ? "01.1.1.1-a" : has(/noodle|vermicelli/) ? "01.1.1.5-b" : "01.1.1.5-a";
    case c === "flour": return "01.1.1.2-a";
    case c === "bread": return "01.1.1.3-a";
    case c === "pasta": return has(/noodle|vermicelli/) ? "01.1.1.5-b" : "01.1.1.5-a";
    case c === "sugar": return has(/sweetener|stevia|sucralose/) ? "01.1.8.2-a" : "01.1.8.1-a";
    case c === "honey": return has(/jam\b|marmalade/) ? "01.1.8.3-b" : "01.1.8.3-a";
    case c === "salt": return "01.1.9.3-a";
    case /^grocery food cupboard( cooking ingredients| home baking sweeteners)?$/.test(c): return cupboard();
    case c === "grocery food cupboard frozen food":
      return has(/fries|potato|vegetable|\bpeas\b|\bcorn\b|okra|spinach|beans|molokhia/) ? "01.1.7.8-a" : has(/fish|shrimp|prawn|fillet|seafood/) ? fish()
        : has(/chicken|nugget|burger|sausage|kofta|meat|beef|kebab/) ? "01.1.2.5-a" : has(/ice cream/) ? "01.1.8.6-a" : has(/fruit|berr|mango/) ? "01.1.6.6-a" : "01.1.9.1-a";
    case c === "coffee": return "01.2.2.0-a";
    case c === "tea": return "01.2.3.0-a";
    case c === "juice": return "01.2.1.0-a";
    case c === "water": return "01.2.5.0-a";
    case c === "soft drinks": return has(/energy/) ? "01.2.9.0-a" : "01.2.6.0-a";
    case c === "garden": return has(/canned|chickpea|\bcorn\b|\bpeas\b|beans|foul|fava|tahin|\d+\s?g\b|frozen|vegetable/) ? (has(/frozen/) ? "01.1.7.8-a" : "01.1.7.9-a") : "09.3.1.1-a";
    // clothing and footwear
    case /^(men > shoes|men shoes)$/.test(c): return "03.2.1.1-a";
    case /^(women > shoes|women shoes)$/.test(c): return "03.2.1.2-a";
    case /^(kids shoes|boys > shoes|girls > shoes)$/.test(c): return "03.2.1.3-a";
    case /^(shoes|sports shoes|sandals)$/.test(c):
      if (has(/shoe ?laces|\blaces\b|insoles?|inserts|shoe cleaner|polish|brush|stretcher|shoe horn|deodori[sz]er|massag|organi[sz]er|\brack\b|display|storage|shoe bag|cover|protector|spray|charm|shoe lifts|soap|incense|dhoop|cream/)) return null;
      { const g = gender(); return g === "f" ? "03.2.1.2-a" : g === "k" || g === "b" ? "03.2.1.3-a" : g === "m" ? "03.2.1.1-a" : null; }
    case /^(baby > t-shirts|baby clothing)$/.test(c): return garment("b");
    case /^(boys > |men > |men )/.test(c): return garment("m");
    case /^(girls > |women > |women )/.test(c) || c === "abaya": return garment("f");
    case /^(kids clothing|underwear|socks)$/.test(c): { const g = gender(); return g === "b" ? "03.1.2.3-a" : has(/costume|cosplay|halloween/) ? "09.2.1.3-a" : g === "f" ? garment("f") : g === "m" || c !== "kids clothing" ? garment("m") : null; }
    case c === "jeans": return has(/yarn|extender|button|patch|hanger|iron-on|fabric|sticker/) || !has(/\bjeans?\b|denim/) || has(/parfum|perfume|eau de|toilette/) ? null : garment(gender() === "f" ? "f" : gender() === "b" ? "b" : "m");
    // furnishings and household
    case /^(refrigerator|home appliances > fridges & freezers)$/.test(c): return "05.3.1.1-a";
    case c === "home appliances > dishwashers": return "05.3.1.1-b";
    case /^(washing machine|home appliances > laundry)$/.test(c): return "05.3.1.2-a";
    case /^(air conditioner|home appliances > cooling & heating)$/.test(c): return has(/\bfan\b/) ? "05.3.2.9-a" : "05.3.1.3-a";
    case /^(vacuum cleaner|home appliances > floorcare)$/.test(c): return "05.3.1.4-a";
    case /^(blender|home appliances > cooking)$/.test(c): return has(/kettle|coffee|espresso|tea maker/) ? "05.3.2.2-a" : "05.3.2.1-a";
    case c === "kettle": return "05.3.2.2-a";
    case /^(iron|fan|home appliances > small appliances)$/.test(c): return has(/blender|mixer|chopper|juicer|air fryer|toaster/) ? "05.3.2.1-a" : has(/kettle|coffee/) ? "05.3.2.2-a" : "05.3.2.9-a";
    case c === "bedsheet": return "05.2.1.2-a";
    case c === "plates": return "05.4.0.1-a";
    case c === "cookware": return "05.4.0.3-a";
    case /^(batteries|light bulb)$/.test(c): return has(/charger|tester/) ? null : "05.5.2.2-a";
    case /^(detergent|grocery household laundry essentials)$/.test(c): return "05.6.1.1-a";
    case /^(dishwashing|grocery household dishwashing liquids tablets)$/.test(c): return "05.6.1.1-b";
    case /^(cleaning|grocery household cleaning essentials|grocery household)$/.test(c): return "05.6.1.1-c";
    case /^(air freshener|insecticide)$/.test(c): return "05.6.1.9-a";
    case c === "towel": return "05.6.1.9-b";
    case c === "tissue": return "13.1.2.0-f";
    // health
    case c === "paracetamol": return "06.1.1.1-a";
    case c === "vitamins": return "06.1.1.1-b";
    case c === "thermometer": return "06.1.2.1-a";
    case c === "first aid": return "06.1.2.3-a";
    // transport
    case c === "bicycle": return has(/bicycle|cycle|bike/) && !has(/\block\b|pump|helmet|light|bell|stand|cover|glove|bottle|holder|rack/) ? "07.1.3.0-a" : null;
    case c === "car battery": return has(/charger|tester|connector|clamp|cable|jump/) ? null : "07.2.1.2-a";
    case c === "car accessories": return "07.2.1.3-a";
    case c === "engine oil": return "07.2.2.4-a";
    // information and communication
    case /^(mobile phone|mobiles & tablets > mobiles)$/.test(c): return has(/case|cover|protector|charger|cable|holder/) ? "08.1.9.2-a" : "08.1.2.0-a";
    case /^(laptop|computing > laptops)$/.test(c): return has(/bag|sleeve|stand|cooler|skin|charger/) ? "08.1.3.2-a" : "08.1.3.1-a";
    case /^(tablet|mobiles & tablets > tablets)$/.test(c): return has(/case|cover|protector|stylus|pen\b|keyboard/) ? "08.1.9.2-a" : "08.1.3.1-b";
    case /^(router|computing > (monitors|printers & ink|storage|computing accessories|networking & wireless))$/.test(c): return "08.1.3.2-a";
    case /^(television|tv, video & audio > tvs)$/.test(c): return has(/wall mount|bracket|remote control|tv stand|hdmi|cable/) && !has(/smart tv|oled|qled|uhd|television/) ? null : "08.1.4.0-a";
    case /^(headphones|earphones|speaker|tv, video & audio > (audio|home cinema & soundbars))$/.test(c): return "08.1.4.0-b";
    case /^(smart watch|wearables & smartwatches > smartwatches)$/.test(c): return has(/strap|band\b|protector|charger|case/) ? "08.1.9.2-a" : "08.1.9.1-a";
    case /^(charger|power bank|usb cable|phone case|screen protector|mobiles & tablets > (mobile|tablet) accessories)$/.test(c): return "08.1.9.2-a";
    // recreation
    case /^(camera|cameras & camcorders > digital cameras)$/.test(c): return "09.1.1.1-a";
    case /^(gaming console|video games|gaming > (games|gaming consoles|gaming accessories))$/.test(c): return has(/foam|sword|plush|figure|costume|poster|mug/) ? "09.2.1.2-a" : "09.2.1.1-a";
    case c === "toys": return "09.2.1.2-a";
    case c === "pet food": return "09.3.2.2-a";
    case c === "books": return "09.7.1.9-a";
    case /^(notebook|pens|stationery)$/.test(c): return "09.7.4.0-a";
    // personal care
    case /^(hair dryer|health, fitness & beauty > grooming appliances)$/.test(c): return "13.1.1.1-a";
    case /^(perfume|health, fitness & beauty > fragrances)$/.test(c): return "13.1.2.0-a";
    case c === "deodorant": return "13.1.2.0-b";
    case /^(shampoo|soap)$/.test(c): return "13.1.2.0-c";
    case /^(body lotion|face mask)$/.test(c): return "13.1.2.0-d";
    case c === "toothpaste": return "13.1.2.0-e";
    case c === "razor": return "13.1.2.0-g";
    case /^(sanitary pads|diapers)$/.test(c): return "13.1.2.0-h";
    case c === "school bag": return "13.2.9.1-a";
  }
  return null;
}

// Indices over the saved days. A product's daily price comes from the history change log; the item type's daily change is the
// geometric mean of its products' price relatives (same product, same shop, two consecutive days); each higher level's daily
// change is the weighted mean of its children's changes (Dubai CPI weights at class level and above, equal weights below);
// the index chains the daily changes, first day = 100. A child's impact is its weight share times its change, in index points.
function coicopBuild(hist, weights, opts = {}) {
  const days = hist.days, D = days.length, store = opts.store || "", weighted = opts.weighted !== false;
  const nodes = new Map(), node = (code) => {
    if (!nodes.has(code)) { const n = { ...(CNODE[code] || { code, ar: code, en: code }), kids: [], prods: [] }; nodes.set(code, n); const p = cParent(code); if (code) node(p).kids.push(n); }
    return nodes.get(code);
  };
  const root = node(""); root.ar = "كل الأقسام"; root.en = "All items";
  let unclassified = 0;
  for (const [k, p] of Object.entries(hist.p)) {
    if (store && p.o !== store) continue;
    const type = coicopOf(p.c, p.t);
    if (!type) { unclassified++; continue; }
    if (COICOP_SKIP.includes(type.slice(0, 2))) continue;
    const pr = new Array(D).fill(null); let cur = null, e = 0;
    for (let d = 0; d < D; d++) { while (e < p.h.length && p.h[e][0] <= d) { cur = p.h[e][1]; e++; } pr[d] = cur > 0 ? cur : null; }
    if (!pr.some((x) => x)) continue;
    node(type).prods.push({ k, t: p.t, o: p.o, u: p.u, c: p.c, g: p.g, pr });
  }
  // official weights (Dubai CPI basket, 7-digit codes) summed to COICOP classes (0112 -> 01.1.2)
  const cw = {};
  for (const [c7, w] of Object.entries(weights || {})) { const c4 = String(c7).slice(0, 4); const cls = `${c4.slice(0, 2)}.${c4[2]}.${c4[3]}`; cw[cls] = (cw[cls] || 0) + Number(w || 0); }
  // what the reader walks through: a division lists its classes directly (the COICOP group level, e.g. 01.1 Food, is folded
  // in), and a level with a single branch below it takes that branch's content, so every click opens a real choice
  for (const d of root.kids) d.kids = d.kids.flatMap((g) => (g.prods.length ? [g] : g.kids));
  (function squash(n) { while (n !== root && n.kids.length === 1 && !n.prods.length) { const c = n.kids[0]; n.kids = c.kids; n.prods = c.prods; } n.kids.forEach(squash); })(root);
  const LN3 = Math.log(3);
  (function calc(n) {
    n.rel = new Array(D).fill(null);
    if (n.prods.length) {
      n.count = new Array(D).fill(0);
      for (let d = 0; d < D; d++) {
        let s = 0, m = 0;
        for (const q of n.prods) {
          if (q.pr[d]) n.count[d]++;
          if (d && q.pr[d] && q.pr[d - 1]) { const l = Math.log(q.pr[d] / q.pr[d - 1]); if (Math.abs(l) <= LN3) { s += l; m++; } }
        }
        if (d && m) n.rel[d] = Math.exp(s / m);
      }
      n.ow = cw[n.code] || 0;                                             // a class whose single branch was folded in keeps its weight
    } else {
      n.kids.forEach(calc);
      n.kids = n.kids.filter((k) => k.count && k.count.some((x) => x));
      n.ow = n.kids.reduce((a, k) => a + k.ow, 0) || cw[n.code] || 0;      // official weight: the class figure, or the sum of the classes below
      if (cw[n.code]) n.ow = cw[n.code];
      const anyW = weighted && n.kids.some((k) => k.ow > 0);
      for (const k of n.kids) k.w = anyW ? k.ow : 1;                         // children without an official weight count 0 when the others have one
      n.count = new Array(D).fill(0);
      for (let d = 0; d < D; d++) {
        let sw = 0, sr = 0;
        for (const k of n.kids) { n.count[d] += k.count[d]; if (k.rel[d] && k.w > 0) { sw += k.w; sr += k.w * k.rel[d]; } }
        if (d && sw) n.rel[d] = sr / sw;
      }
    }
    n.first = n.count.findIndex((x) => x > 0);
    n.idx = n.rel.map(() => null); let I = 100;
    for (let d = Math.max(n.first, 0); d < D; d++) { if (d > n.first && n.rel[d]) I *= n.rel[d]; n.idx[d] = n.count[d] || d > n.first ? +I.toFixed(3) : null; }
    n.last = n.idx[D - 1]; n.chg = n.last - 100;
    const prev = n.idx[D - 2]; n.day = prev ? (n.last / prev - 1) * 100 : 0;
    n.products = n.count[D - 1];
  })(root);
  (function impact(n) {
    const sw = n.kids.reduce((a, k) => a + (k.w > 0 ? k.w : 0), 0);
    for (const k of n.kids) { k.share = sw && k.w > 0 ? k.w / sw : 0; k.imp = k.share * k.chg; impact(k); }
    n.kids.sort((a, b) => Math.abs(b.imp) - Math.abs(a.imp) || Math.abs(b.chg) - Math.abs(a.chg) || b.products - a.products);
    for (const q of n.prods) { const f = q.pr.find((x) => x), l = q.pr[D - 1]; q.first = f; q.lastp = l; q.chg = f && l ? (l / f - 1) * 100 : null; }
    n.prods.sort((a, b) => Math.abs(b.chg ?? -1) - Math.abs(a.chg ?? -1));
  })(root);
  return { root, nodes, days, unclassified };
}
if (typeof module !== "undefined") module.exports = { COICOP, CNODE, coicopOf, coicopBuild };
