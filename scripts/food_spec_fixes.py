"""One-off corrections of English specs for food lines whose spec asked for words a shop title never carries
('whole', 'loose', 'short/local', 'fresh ginger' as an exclusion ...). Run once; it rewrites data/basket/specs_en.json.

    python scripts/food_spec_fixes.py
Each entry: code(s) -> must_have, must_not, optional size / query_en / keep. Lines whose product the two shops do not sell
(live sheep, pork, tandoor bread, Omani halwa, frozen lamb cuts, beef liver) are left as they are: they stay 'no match'.
"""
import json
from pathlib import Path

SPECS = Path(__file__).resolve().parent.parent / "data/basket/specs_en.json"
JUNK = ["juice", "jam", "cake", "pie", "tart", "dried", "canned", "sauce", "paste", "yoghurt", "yogurt", "flavour", "flavor", "chocolate",
        "candy", "syrup", "soup", "salad", "frozen", "ice", "biscuit", "cookie"]
FIX = {
    "011130101": dict(q="frozen paratha", must=["paratha"], no=["aloo", "paneer", "mix", "veg", "vegetable", "stuffed", "cheese", "methi", "onion", "gobi", "chicken", "egg", "garlic", "keema", "mooli", "masala"], size="per kg"),
    "011130801": dict(must=["baklawa/baklava"], no=["frozen", "cake", "ice", "cream", "chocolate", "bar", "biscuit", "cookie"]),
    "011130802": dict(must=["baklawa/baklava"], no=["frozen", "cake", "ice", "cream", "chocolate", "bar", "biscuit", "cookie"]),
    "011130803": dict(must=["baklawa/baklava"], no=["frozen", "cake", "ice", "cream", "chocolate", "bar", "biscuit", "cookie"]),
    "011130901": dict(must=["kunafa/knafeh/kunafeh/kanafeh"], no=["bites", "spread", "kitkat", "speculoos", "nestle", "pistachio", "cake", "chocolate", "ice", "cream", "bar", "dough", "kataifi", "frozen", "bread"]),
    "011130902": dict(must=["kunafa/knafeh/kunafeh/kanafeh"], no=["bites", "spread", "kitkat", "speculoos", "nestle", "pistachio", "cake", "chocolate", "ice", "bar", "dough", "kataifi", "frozen", "bread"]),
    "011131001": dict(q="frozen cheese sambousek", must=["cheese", "sambousek/sambousak/fatayer/fatayar/pie/rolls/roll"], no=["zaatar", "spinach", "meat", "chicken", "mini", "spring"], size="per kg"),
    "011131002": dict(q="frozen zaatar fatayer", must=["zaatar/zatar", "sambousek/sambousak/fatayer/fatayar/pie/manakish"], no=["meat", "chicken", "cheese"], size="per kg"),
    "011220104": dict(must=["mutton/lamb", "bone/bones"], no=["boneless", "minced", "mince", "frozen", "liver", "kebab", "burger", "lamb bones"]),
    "011310301": dict(must=["sheri/shaari/shaeri/shari"], no=["fillet", "frozen", "cheese", "safi"]),
    "011310302": dict(must=["sheri/shaari/shaeri/shari"], no=["fillet", "frozen", "cheese", "safi"]),
    "011310701": dict(must=["seabream/bream"], no=["fillet", "frozen", "sea bass", "marinated", "flavors", "flavours", "lemon", "herbs"]),
    "011310702": dict(must=["seabream/bream"], no=["fillet", "frozen", "sea bass", "marinated", "flavors", "flavours", "lemon", "herbs"]),
    "011340101": dict(must=["shrimp/shrimps/prawn/prawns"], no=["frozen", "peeled", "cooked", "breaded", "cleaned", "cocktail", "tempura", "skewers", "herb", "marinated", "mediterranean", "sauce", "curry", "soup", "salad", "sushi", "dumpling", "chips", "tandoori", "crackers"]),
    "011610203": dict(must=["banana/bananas"], no=["baby", "sweetio", "red", "plantain", "flower", "blossom", "chips", "milk", "bread", "cake", "smoothie", "dried", "peel", "shake", "dessert", "strawberry", "organic"] + JUNK),
    "011630106": dict(must=["apple/apples", "green/granny"], no=["red", "pink", "golden", "gala", "fuji", "dazzle", "ambrosia", "cider", "vinegar"] + JUNK, keep=["green"]),
    "011630107": dict(must=["apple/apples", "green/granny"], no=["red", "pink", "golden", "gala", "fuji", "dazzle", "ambrosia", "cider", "vinegar"] + JUNK, keep=["green"]),
    "011630201": dict(must=["apricot/apricots"], no=["tartlets", "crostata", "crostatina", "glazed", "leather", "kernel", "compote", "nectar", "dried"] + JUNK),
    "011630202": dict(must=["apricot/apricots"], no=["tartlets", "crostata", "crostatina", "glazed", "leather", "kernel", "compote", "nectar", "dried"] + JUNK),
    "011630501": dict(must=["cherries/cherry"], no=["tomato", "tomatoes", "plum", "bucket", "tea", "jelly", "compote", "soda", "cola", "brandy"] + JUNK),
    "011630502": dict(must=["cherries/cherry"], no=["tomato", "tomatoes", "plum", "bucket", "tea", "jelly", "compote", "soda", "cola", "brandy"] + JUNK),
    "011630503": dict(must=["cherries/cherry"], no=["tomato", "tomatoes", "plum", "bucket", "tea", "jelly", "compote", "soda", "cola", "brandy"] + JUNK),
    "011710101": dict(basis="kg", must=["spinach"], no=["baby", "cheese", "manakish", "rucola", "mix", "dip", "paneer", "puree", "pasta", "ravioli", "ready", "tortilla", "wrap"] + JUNK, size="per kg"),
    "011720101": dict(must=["tomato/tomatoes"], no=["cherry", "plum", "shaker", "bucket", "candy", "ketchup", "pickle", "seed", "sun"] + JUNK, size="per kg"),
    "011720201": dict(must=["cucumber/cucumbers"], no=["long", "english", "snack", "mini", "baby", "pickled", "pickle", "family", "dip", "sandwich"] + JUNK),
    "011720202": dict(must=["cucumber/cucumbers"], no=["long", "english", "snack", "mini", "baby", "pickled", "pickle", "family", "dip", "sandwich"] + JUNK),
    "011720203": dict(must=["cucumber/cucumbers", "long/english"], no=["snack", "mini", "baby", "pickled", "pickle", "family", "dip", "sandwich"] + JUNK, keep=["long"]),
    "011750201": dict(must=["sweet", "potato/potatoes"], no=["chips", "fries", "crisps", "fried", "grilled", "chicken", "roast", "mash", "purple", "wedges", "puree", "bread", "mix", "noodles", "vermicelli", "pasta"] + JUNK),
    "011750202": dict(must=["sweet", "potato/potatoes"], no=["chips", "fries", "crisps", "fried", "grilled", "chicken", "roast", "mash", "purple", "wedges", "puree", "bread", "mix", "noodles", "vermicelli", "pasta"] + JUNK),
    "011760201": dict(must=["chickpeas/chickpea"], no=["flour", "sev", "masala", "boondi", "fried", "roasted", "snack", "pop", "crunch", "boiled", "hummus", "tahini", "tin", "can", "curry", "dal", "spicy", "noodles", "pasta", "falafel", "black"]),
    "011760202": dict(must=["chickpeas/chickpea"], no=["flour", "sev", "masala", "boondi", "fried", "roasted", "snack", "pop", "crunch", "boiled", "hummus", "tahini", "tin", "can", "curry", "dal", "spicy", "noodles", "pasta", "falafel", "black"]),
    "011760403": dict(must=["beans", "white/navy/cannellini/haricot"], no=["tin", "can", "baked", "tomato", "green", "fine", "kidney", "red", "black", "butter", "soup", "salad", "mix", "kit", "curry", "hummus", "coffee", "vanilla", "paste", "burrito"] + JUNK, keep=["white"]),
    "011760405": dict(must=["beans", "white/navy/cannellini/haricot"], no=["tin", "can", "baked", "tomato", "green", "fine", "kidney", "red", "black", "butter", "soup", "salad", "mix", "kit", "curry", "hummus", "coffee", "vanilla", "paste", "burrito"] + JUNK, keep=["white"]),
    "011790701": dict(must=["olives/olive", "green"], no=["oil", "bread", "manakish", "fougasse", "stuffed", "pizza", "sourdough", "tapenade", "spread", "crackers", "cheese", "black", "pitted", "zaatar", "garlic", "chili", "chilli"] + JUNK, keep=["green"]),
    "011790703": dict(must=["olives/olive", "black"], no=["oil", "bread", "manakish", "fougasse", "stuffed", "pizza", "sourdough", "tapenade", "spread", "crackers", "cheese", "green", "pitted"] + JUNK, keep=["black"]),
    "011790801": dict(must=["mixed", "pickles/pickle/pickled"], no=["spicy", "chili", "chilli", "onion", "lemon", "cornichon"] + JUNK),
    "011790802": dict(must=["pickled/pickles/pickle", "onion/onions"], no=["spicy", "chili", "chilli"] + JUNK),
    "011790803": dict(must=["mixed", "pickles/pickle/pickled"], no=["spicy", "chili", "chilli", "onion", "lemon", "cornichon"] + JUNK),
    "011940701": dict(must=["ginger", "powder/ground/grounded"], no=["paste", "garlic", "tea", "ale", "beer", "instant", "drink", "bread", "sauce", "capsules"]),
    "011940702": dict(must=["ginger", "powder/ground/grounded"], no=["paste", "garlic", "tea", "ale", "beer", "instant", "drink", "bread", "sauce", "capsules"]),
    "011941002": dict(must=["shawarma", "spices/spice/seasoning/mix"], no=["bread", "sandwich", "wrap", "sauce", "garlic", "marinated"]),
}

# barcoded lines the shops never listed with the basket's brand and pack: moved to a product set (any brand, any pack, price per kg / litre)
FLIP = ["011340501", "011340502", "011340503", "011510501", "011510502", "011990301", "011990302", "011110901", "011110902", "011110904"]
FIX.update({
    **{c: dict(q="frozen peeled shrimp", must=["shrimp/shrimps/prawn/prawns", "peeled/cleaned/deveined", "frozen"], no=["breaded", "cooked", "tempura", "sauce", "curry", "soup", "salad", "sushi", "dumpling", "chips", "crackers", "skewers", "marinated", "fried", "popcorn", "tandoori"], size="per kg") for c in ("011340501", "011340502", "011340503")},
    **{c: dict(must=["palm", "oil/olein"], no=["kernel", "fruit", "sugar", "soap", "shampoo", "cream", "ghee", "butter", "sunflower", "corn"], size="per l", basis="l") for c in ("011510501", "011510502")},
    **{c: dict(must=["yeast"], no=["extract", "marmite", "nutritional", "free", "cheesy", "seasoning", "stock", "cubes", "bread", "beer", "cake", "biscuit", "pizza", "flavour", "vegemite", "fresh"], size="per kg") for c in ("011990301", "011990302")},
    **{c: dict(must=["bulgur/burghol/burgul/bulghur/burghul/burghul"], no=["salad", "tabbouleh", "tabouli", "mix", "ready", "kibbeh"], size="per kg") for c in ("011110901", "011110902", "011110904")},
})


def main():
    specs = json.loads(SPECS.read_text(encoding="utf-8"))
    by = {s["c"]: s for s in specs}
    for code, f in FIX.items():
        s = by.get(code)
        if not s:
            continue
        s["must_have"], s["must_not"] = f["must"], f["no"]
        if "q" in f:
            s["query_en"] = f["q"]
        if "size" in f:
            s["size"] = f["size"]
            s["sold_by_weight"] = True
        if "basis" in f:
            s["basis"] = f["basis"]
        if "keep" in f:
            s["keep"] = f["keep"]
    SPECS.write_text(json.dumps(specs, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    bk = SPECS.parent / "basket.json"
    basket = json.loads(bk.read_text(encoding="utf-8"))
    n = 0
    for it in basket:
        if it["item_code"] in FLIP and it.get("barcode_raw"):
            it["barcode_orig"], it["barcode_raw"], it["gtin"], it["barcode_kind"] = it["barcode_raw"], "", "", "none"
            it["match_mode"], it["product_set_from_barcode"] = "spec", True
            n += 1
    bk.write_text(json.dumps(basket, ensure_ascii=False), encoding="utf-8")
    print(n, "barcoded lines moved to a product set")
    print(len(FIX), "specs corrected")


if __name__ == "__main__":
    main()
