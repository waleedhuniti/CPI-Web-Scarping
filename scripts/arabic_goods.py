"""English search specs for the basket lines whose official name is Arabic only, and their prices from the day's catalogue.

    python scripts/arabic_goods.py data/catalogue/<date> out.csv

The 355 lines (clothes, shoes, drinks, household, personal care, perfume) have no barcode and no Latin model name, so
match_catalogue_items.py cannot read them. spec_for(item) writes for each line what a shop would call it:
  any    alternatives; a title is a candidate when it has every word of at least one alternative
  none   words that make a title another product
  brand  words that must all be in the title (Nike, Colgate ...): the line is that brand's product
  demo   men / women / boys / girls / baby  (checked against the catalogue category and the title; Zara and Max name the
         section, not the person, in the category: 'Girls > Jeans')
  mode   'set'   any brand and any size: a product SET (price per kg / litre / piece), like the food lines
         'exact' brand and exact pack size (perfume 90 ml, toothpaste 100 ml): a different size is a different price
A line is priced only when its candidates are at least MIN_LISTINGS products; the price is the median.
"""
import csv
import json
import re
import statistics
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))
from cpi.quantity import all_quantities, parse_quantity, same_quantity  # noqa: E402
from scrapling_category import has_word, words  # noqa: E402

MIN_LISTINGS = 2
GENDER = [(r"للأولاد|أولاد|بنين|ولاد", "boys"), (r"للبنات|بنات|بناتى|بناتي|بنت", "girls"), (r"نسائي|نسائية|نسائى", "women")]
# garment words (Arabic -> English alternatives); first match wins
GARMENT = [
    (r"كندور", [["thobe"], ["kandura"], ["dishdasha"]]),
    (r"وزار|إزار", [["izar"], ["sarong"], ["lungi"]]),
    (r"جاكيت بدل|جاكت بدل|سترة|اكليرك", [["blazer"], ["suit", "jacket"]]),
    (r"بدل[هة] رياض|تراك سوت", [["tracksuit"], ["track", "suit"], ["jogging", "suit"]]),
    (r"بدل[هة] رسمي|بدلة بنات|بدله كامله|بدلة كامل|طقم أنيق", [["suit", "set"], ["two", "piece", "suit"], ["2", "piece", "suit"], ["3", "piece", "suit"]]),
    (r"جاكيت دنيم|جاكيت جينز", [["denim", "jacket"]]),
    (r"بومبر", [["bomber"]]),
    (r"رين كوت", [["trench"], ["raincoat"], ["coat"]]),
    (r"جاكيت صوف", [["knit", "jacket"], ["cardigan"], ["knitted", "jacket"]]),
    (r"جاكيت|جاكت|فليس|سبورتسوير", [["jacket"], ["hoodie"], ["sweatshirt"], ["cardigan"]]),
    (r"ليقنز|ليجنز", [["leggings"], ["legging"]]),
    (r"جينز", [["jeans"], ["jean"]]),
    (r"بنطلون|بنطال|سروال", [["trousers"], ["pants"], ["chinos"]]),
    (r"شورت", [["shorts"]]),
    (r"بولو", [["polo"]]),
    (r"تي ?شيرت|تيشيرت|تيشرت|تيشِرت", [["t-shirt"], ["tshirt"], ["tee"], ["t", "shirt"]]),
    (r"جلابية نوم|جلابيه نوم", [["nightdress"], ["nightgown"], ["night", "gown"]]),
    (r"جلابية|جلابيه", [["jalabiya"], ["kaftan"], ["galabiya"]]),
    (r"بيجام|بجام", [["pyjama"], ["pyjamas"], ["pajama"], ["pajamas"], ["pjs"]]),
    (r"فانل|فيست|صدريات", [["vest"], ["undershirt"], ["singlet"], ["camisole"], ["bralette"]]),
    (r"بوكس", [["boxer"], ["brief"], ["trunk"]]),
    (r"ملابس سباحة", [["swimsuit"], ["swimwear"], ["burkini"], ["swim"]]),
    (r"ملابس داخل|سراويل داخل|سلبس", [["underwear"], ["briefs"], ["knickers"], ["panties"], ["boxer"]]),
    (r"فستان", [["dress"]]),
    (r"تنورة طويلة|تنوره طويلة", [["long", "skirt"], ["maxi", "skirt"], ["midi", "skirt"]]),
    (r"تنورة محاكة قصيرة|تنورة قصيرة", [["mini", "skirt"], ["short", "skirt"]]),
    (r"تنور", [["skirt"]]),
    (r"مريول", [["pinafore"], ["school", "dress"]]),
    (r"بلوزة", [["blouse"], ["shirt"]]),
    (r"قميص", [["shirt"]]),
    (r"إسلامي ساده|عباية|عباءة", [["abaya"], ["jilbab"]]),
    (r"جوارب", [["socks"], ["sock"]]),
    (r"حزام", [["belt"]]),
    (r"طاقيه|طاقية", [["kufi"], ["prayer", "cap"], ["skull", "cap"]]),
    (r"كاب", [["cap"]]),
    (r"شيلة|شيله", [["scarf"], ["shayla"], ["hijab"], ["shawl"]]),
    (r"نعال", [["sandals"], ["slippers"], ["slides"]]),
    (r"حذاء|سنيكرز", [["shoes"], ["sneakers"], ["trainers"]]),
]
BRAND = [(r"نايك|نايكي", ["nike"]), (r"اديداس|ايداس|أديداس|اديدا|ايديداس", ["adidas"]), (r"سكتشرز", ["skechers"])]
GENDER_BY_CLASS = {"0312101": "men", "0312102": "men", "0312103": "men", "0312104": "men", "0312105": "men", "0312106": "men",
                   "0312107": "men", "0312108": "men", "0312109": "men", "0312110": "men", "0312111": "men",
                   "0312113": "boys", "0312114": "boys", "0312115": "boys", "0312117": "boys", "0312118": "boys", "0312119": "boys",
                   "0312213": "girls", "0312214": "girls", "0312215": "girls", "0312216": "girls", "0312217": "girls",
                   "0312218": "girls", "0312219": "girls", "0312220": "girls", "0312221": "girls",
                   "0321102": "men", "0321201": "women", "0321301": "kids", "0312201": "women", "0312202": "women",
                   "0312203": "women", "0312204": "women", "0312205": "women", "0312206": "women", "0312207": "women",
                   "0312208": "women", "0312209": "women", "0312210": "women", "0312211": "women"}

# explicit specs for goods that are not clothes: code -> (mode, any, none, brand, basis)
S = {}


def add(codes, mode, any_, none=(), brand=(), basis="pc", cats=""):
    for c in codes.split():
        S[c] = dict(mode=mode, any=[list(a) for a in any_], none=list(none), brand=list(brand), basis=basis, cats=cats)


# ---- drinks (price per litre / kg) ----
add("012100101 012100102", "set", [["orange", "juice"]], ["concentrate", "drink", "powder", "fresh"], basis="l")
add("012100103", "set", [["berry", "juice"], ["berries", "juice"], ["mixed", "berry"]], ["powder"], basis="l")
add("012100105", "set", [["avocado", "juice"], ["avocado", "drink"]], [], basis="l")
add("012100108", "set", [["lemon", "mint"]], ["powder", "tea"], basis="l")
add("012100110", "set", [["apple", "juice"]], ["concentrate", "powder", "vinegar"], basis="l")
add("012100112", "set", [["mango", "juice"], ["mango", "drink"]], ["powder"], basis="l")
add("012100113", "set", [["mango", "nectar"], ["fruit", "nectar"]], ["powder"], basis="l")
add("012100114", "set", [["mixed", "fruit", "juice"], ["multi", "fruit", "juice"], ["tropical", "juice"], ["mixed", "fruit", "nectar"]], ["powder"], basis="l")
add("012100301", "set", [["orange", "powder"], ["tang", "orange"], ["orange", "drink", "mix"], ["orange", "instant", "drink"]], [], basis="kg")
add("012100305", "set", [["mango", "powder"], ["mango", "drink", "mix"], ["mango", "instant", "drink"], ["tang", "mango"]], [], basis="kg")
add("012100306", "set", [["pineapple", "powder"], ["pineapple", "drink", "mix"], ["pineapple", "instant", "drink"], ["tang", "pineapple"]], [], basis="kg")
add("012200101 012200102", "set", [["arabic", "coffee"], ["gahwa"], ["qahwa"], ["khawlani"], ["saudi", "coffee"], ["emirati", "coffee"]], ["capsule", "capsules", "instant", "pods", "3in1", "turkish", "grounded", "espresso", "latte"], basis="kg")
add("012200103 012200104", "set", [["arabic", "coffee"], ["gahwa"], ["qahwa"], ["khawlani"], ["saudi", "coffee"], ["emirati", "coffee"]], ["capsule", "capsules", "instant", "pods", "3in1", "turkish", "grounded", "espresso", "latte"], basis="kg")
add("012200201 012200202 012200203", "set", [["instant", "coffee"]], ["3in1", "3", "stick", "sticks", "mix", "latte", "cappuccino", "capsule"], basis="kg")
add("012300201 012300202 012300203", "set", [["black", "tea", "bags"], ["tea", "bags", "black"], ["red", "tea", "bags"], ["black", "tea", "bag"]], ["green", "herbal", "ginger", "lemon", "mint", "chamomile"], basis="bag100")
add("012300205", "set", [["green", "tea", "bags"], ["green", "tea", "bag"]], ["lemon", "mint", "ginger", "jasmine"], basis="bag100")
add("012300302", "set", [["slimming", "tea"], ["diet", "tea"], ["detox", "tea"], ["weight", "tea"]], [], basis="bag100")
add("012300303 012300304", "set", [["ginger", "lemon", "tea"], ["lemon", "ginger", "tea"], ["ginger", "lemon", "infusion"], ["lemon", "ginger", "infusion"]], [], basis="bag100")
add("012500101 012500102 012500103 012500104", "set", [["drinking", "water"], ["mineral", "water"], ["bottled", "water"], ["natural", "water"]], ["sparkling", "carbonated", "flavoured", "flavored", "baby", "alkaline", "hydrogen", "gallon", "cooler"], basis="l")
add("012500203", "set", [["sparkling", "water"], ["carbonated", "water"], ["sparkling", "mineral"]], ["flavoured", "flavored", "juice"], basis="l")
add("012600101 012600102", "set", [["cola"]], ["zero", "diet", "light", "chocolate", "milk", "yoghurt", "cashew", "nuts", "ice", "cream", "cherry", "limited", "edition", "assorted", "vanilla"], basis="l")
add("012600103", "set", [["orange", "soft", "drink"], ["orange", "carbonated"], ["fanta", "orange"], ["mirinda", "orange"], ["orange", "soda"]], ["juice", "zero", "diet"], basis="l")
add("012900101 012900105", "set", [["energy", "drink"]], ["powder", "sugar", "free", "zero", "shot", "edition"], basis="l")
add("012900104", "set", [["vitamin", "energy", "drink"], ["energy", "drink", "vitamin"], ["energy", "drink"]], ["powder", "pack"], basis="l")
# ---- household ----
add("045300102 045300103", "set", [["charcoal", "lighter"], ["fire", "starter"], ["charcoal", "starter"], ["lighter", "fluid"]], ["gas", "cigarette"], basis="l")
add("045490104", "set", [["candles"], ["candle"]], ["scented", "jar", "led", "cake", "birthday"], basis="pc")
add("054010101", "set", [["oval", "glass", "dish"], ["glass", "roasting", "dish"], ["glass", "baking", "dish"]], [], basis="pc")
add("054010103", "set", [["glass", "food", "container"], ["glass", "container", "lid"], ["pyrex", "container"], ["glass", "storage"]], [], basis="pc")
add("054010201", "set", [["soup", "ladle"], ["ladle"]], [], basis="pc")
add("054020201", "set", [["fruit", "forks"], ["dessert", "forks"], ["cake", "forks"]], [], basis="pc")
add("054020202", "set", [["knife", "set"], ["knives", "set"], ["3", "knives"], ["paring", "knife"]], [], basis="pc")
add("054020203", "set", [["knife", "set", "scissors"], ["knife", "block", "set"], ["knife", "set"]], [], basis="pc")
add("054030101 054030104", "set", [["frying", "pan"], ["fry", "pan"]], ["electric", "air"], basis="pc")
add("054030201", "set", [["laundry", "basket"]], [], basis="pc")
add("054030402", "set", [["clothes", "airer"], ["drying", "rack"], ["clothes", "dryer", "rack"], ["clothes", "rack"]], [], basis="pc")
add("054030404", "set", [["clothes", "pegs"], ["clothespins"], ["clothes", "pins"], ["pegs"]], [], basis="pc")
add("054030502", "set", [["vacuum", "flask"], ["dallah"]], [], basis="pc")
add("054030503", "set", [["feeding", "bottle"], ["baby", "bottle"]], ["cleaner", "brush"], basis="pc")
add("055100101", "exact", [["grundfos"]], [], basis="pc")
add("055100102", "exact", [["espa"]], [], basis="pc")
add("055220102", "set", [["energy", "saving", "bulb"], ["spiral", "bulb"], ["cfl", "bulb"]], ["led"], basis="pc")
add("056110106 056110108", "set", [["automatic", "detergent", "powder"], ["automatic", "laundry", "powder"], ["automatic", "washing", "powder"]], ["liquid", "gel", "capsules", "pods"], basis="kg")
add("056110107 056110110", "set", [["laundry", "powder"], ["washing", "powder"], ["detergent", "powder"]], ["liquid", "gel", "capsules", "pods", "automatic", "dishwasher"], basis="kg")
add("056110202", "exact", [["comfort", "softener"], ["comfort", "fabric", "softener"]], [], brand=["comfort"], basis="l")
add("056110301", "set", [["air", "freshener", "apple"], ["air", "freshener", "cinnamon"], ["apple", "cinnamon"]], [], basis="pc")
add("056110302", "set", [["lavender", "cleaner"], ["lavender", "multi", "purpose"], ["lavender", "surface"], ["lavender", "disinfectant"]], [], basis="l")
add("056110402", "set", [["broom"], ["sweeping", "brush"]], ["vacuum"], basis="pc")
add("056110501", "exact", [["fairy"]], ["lemon"], brand=["fairy"], basis="l")
add("056110502", "exact", [["fairy", "lemon"]], [], brand=["fairy"], basis="l")
add("056110601", "set", [["floor", "cleaner", "lavender"], ["lavender", "floor"]], [], basis="l")
add("056110602", "set", [["floor", "cleaner", "rose"], ["rose", "floor"], ["rose", "cleaner"]], [], basis="l")
add("056110603 056110604", "set", [["disinfectant"], ["germicide"], ["antibacterial", "cleaner"]], ["spray", "wipes", "hand", "air"], basis="l")
add("056190102", "set", [["insect", "killer", "crawling"], ["crawling", "insect"], ["ant", "cockroach"], ["insecticide", "crawling"]], [], basis="l")
add("056190301 056190302 056190303", "set", [["paper", "plates"], ["paper", "plate"]], ["cups", "napkins"], basis="pc")
add("093220102 093220105", "set", [["sunflower", "seeds", "bird"], ["bird", "food"], ["bird", "seed"], ["cockatiel"]], ["dog", "cat", "fish"], basis="kg")
add("093220103", "set", [["mixed", "bird", "seed"], ["bird", "food", "mix"], ["bird", "seed"]], ["dog", "cat", "fish"], basis="kg")
# ---- perfume and personal care (exact: brand + size) ----
add("131200101", "exact", [["gucci", "guilty", "absolute"]], ["femme", "women"], brand=["gucci"], basis="pc")
add("131200102", "exact", [["mon", "paris"]], ["couture"], brand=["yves"], basis="pc")
add("131200103", "exact", [["black", "opium"]], [], brand=["opium"], basis="pc")
add("131200104", "exact", [["la", "vie", "est", "belle"]], ["intense", "rose", "soleil", "elixir"], brand=["lancome"], basis="pc")
add("131200108", "exact", [["hawas", "for", "her"], ["hawas", "her"]], [], brand=["hawas"], basis="pc")
add("131200109", "exact", [["burooz"], ["al", "burooz"], ["musk", "tabriz"]], [], basis="pc")
add("131200110", "exact", [["wesam", "dubai"], ["al", "wesam", "dubai"], ["wesam", "pour", "homme"]], [], basis="pc")
add("131200111", "exact", [["qurashi"], ["al", "qurashi"]], [], basis="pc")
add("131200112", "exact", [["pink", "essence"], ["pink", "sugar"], ["pink", "sensation"]], [], basis="pc")
add("131200113", "exact", [["the", "black"]], [], basis="pc")
add("131200114", "exact", [["haramain", "adventure"], ["al", "haramain", "adventure"], ["adventure", "spray"]], [], brand=["haramain"], basis="pc")
add("131200115", "exact", [["urbanist", "fame"], ["haramain", "urbanist"]], [], brand=["haramain"], basis="pc")
add("131200116", "exact", [["signature", "silver"], ["haramain", "signature"]], [], brand=["haramain"], basis="pc")
add("131200201 131200204 131200207", "set", [["oud", "oil"], ["dehn", "oud"], ["dhan", "oud"], ["agarwood", "oil"], ["cambodian", "oud"]], [], basis="pc")
add("131200202 131200205 131200208", "set", [["bakhoor"], ["bukhoor"], ["bakhour"]], [], basis="pc")
add("131200203 131200206 131200209 131200211 131200213", "set", [["oud", "chips"], ["agarwood", "chips"], ["mubathath"], ["incense", "wood"]], [], basis="pc")
add("131200210", "set", [["dokhoon"], ["dukhoon"], ["dakhoon"]], [], basis="pc")
add("131200212", "set", [["oud", "oil"], ["dehn", "oud"]], [], basis="pc")
add("131200401", "exact", [["fusion"]], ["blades", "refill"], brand=["gillette"], basis="pc")
add("131200503", "exact", [["body", "lotion"], ["body", "milk"], ["body", "spray"], ["deodorant"]], ["men"], brand=["nivea"], basis="pc")
add("131200601", "exact", [["amla", "hair", "oil"], ["amla", "oil"]], ["kids", "detangler"], brand=["dabur"], basis="pc")
add("131200604", "exact", [["hair", "oil"]], [], brand=["parachute"], basis="pc")
add("131200701", "exact", [["cream"]], ["men", "sun", "hand"], brand=["nivea"], basis="pc")
add("131200704", "exact", [["clay", "face", "wash"], ["clay", "wash"], ["pure", "clay"]], [], brand=["garnier"], basis="pc")
add("131200803", "exact", [["toothbrush"]], [], brand=["oral"], basis="pc")
add("131200804", "exact", [["toothpaste", "mint"], ["toothpaste", "fresh"], ["toothpaste"]], [], brand=["colgate"], basis="pc")
add("131200806", "exact", [["toothpaste"]], [], brand=["signal"], basis="pc")
add("131200807", "exact", [["toothpaste"]], [], brand=["colgate"], basis="pc")
add("131200808", "exact", [["toothbrush", "extra", "soft"], ["toothbrush", "ultra", "soft"], ["toothbrush"]], [], brand=["colgate"], basis="pc")
add("131200901", "exact", [["shampoo"]], [], brand=["sunsilk"], basis="pc")
add("131200902", "exact", [["shampoo"]], [], brand=["pantene"], basis="pc")
add("131200903", "exact", [["shampoo"]], [], brand=["head"], basis="pc")
add("131201001", "exact", [["soap"]], [], brand=["lux"], basis="pc")
add("131201002", "exact", [["soap"], ["beauty", "bar"]], [], brand=["dove"], basis="pc")
add("131201003", "exact", [["soap"]], [], brand=["dettol"], basis="pc")
add("131201004", "exact", [["body", "wash"]], [], brand=["lifebuoy"], basis="pc")
add("131201102 131201103 131201104", "exact", [["pads"], ["pad"], ["napkins"]], ["liners", "liner", "panty", "aloe"], brand=["always"], basis="pc")
add("131201204", "exact", [["diapers"], ["diaper"], ["pants"]], [], brand=["pampers"], basis="pc")
add("131201206", "exact", [["diapers"], ["diaper"]], [], brand=["baby", "joy"], basis="pc")
add("131201207", "exact", [["diapers"], ["diaper"]], [], brand=["bambi"], basis="pc")
add("131201301", "exact", [["facial", "tissue"], ["facial", "tissues"]], [], brand=["fine"], basis="pc")
add("131201302", "exact", [["facial", "tissue"], ["facial", "tissues"]], [], brand=["masafi"], basis="pc")
add("131201303", "set", [["facial", "tissue"], ["facial", "tissues"]], [], basis="pc")
add("131201402", "exact", [["baby", "wipes"], ["wet", "wipes"], ["wipes"]], [], brand=["johnson"], basis="pc")
add("131201403", "set", [["baby", "wipes"], ["wet", "wipes"]], [], basis="pc")
add("131201501", "set", [["toilet", "tissue"], ["toilet", "paper"], ["toilet", "rolls"], ["toilet", "roll"]], [], basis="pc")
add("132910310", "exact", [["rb3778"], ["rb", "3778"]], [], brand=["ray", "ban"], basis="pc")


# ---------------------------------------------------------------- clothes: spec from the Arabic name
def pack_count(unit):
    m = re.search(r"(\d+)\s*قطع", unit or "")
    if m:
        return int(m.group(1))
    if "قطعتين" in (unit or ""):
        return 2
    return 1


def spec_for(it):
    c = it["item_code"]
    if c in S:
        return S[c]
    name, cls = it["name_ar"], it["class_code"]
    if not (c.startswith("0312") or c.startswith("0313") or c.startswith("0321")):
        return None
    garment = next((alts for pat, alts in GARMENT if re.search(pat, name)), None)
    if garment is None:
        return None
    demo = GENDER_BY_CLASS.get(cls)
    for pat, d in GENDER:
        if re.search(pat, name):
            demo = d
            break
    brand = next((b for pat, b in BRAND if re.search(pat, name)), [])
    school = cls in ("0312401", "0312402")
    any_ = [["school", *a] if school else a for a in garment]
    if school:                                          # school uniform: only titles that say so (a plain shirt is another quality)
        any_ = [["school"], ["uniform"]]
        any_ = [[w] + a for w in ("school", "uniform") for a in garment]
        demo = demo or None
        for pat, d in GENDER:
            if re.search(pat, name):
                demo = d
    if demo is None and c.startswith("0313"):
        demo = "any"
    none = []
    if re.search(r"حزام|كاب", name):
        none += ["dress", "with", "culottes", "trousers", "jacket", "coat", "skirt", "shorts", "pants", "shirt", "polo", "sleeve", "sleeves", "t-shirt"]
    if re.search(r"بولو|قميص|بلوزة|شورت|بنطلون|جينز|فستان", name):
        none += ["dress", "sleeve", "sleeves"] if re.search(r"شورت", name) else (["dress"] if not re.search(r"فستان", name) else [])
        if re.search(r"شورت", name):
            none += ["set", "t-shirt"]
    return dict(mode="set", any=any_, none=none, brand=brand, basis="pc", demo=demo, packs=pack_count(it.get("unit", "")), cats="")


def demo_of(row):
    t = set(re.findall(r"[a-z]+", (row["category"] + " " + row["title"]).lower()))
    if "unisex" in t:
        return "unisex"
    if t & {"women", "womens", "ladies", "woman"}:
        return "women"
    if t & {"men", "mens", "man"}:
        return "men"
    if t & {"girls", "girl"}:
        return "girls"
    if t & {"boys", "boy"}:
        return "boys"
    if t & {"baby", "infant", "newborn", "toddler"}:
        return "baby"
    if "kids" in t or "kid" in t:
        return "kids"
    return ""


def row_pack(title):
    m = re.search(r"(?:pack|set|pair|pairs|pieces|pcs)\s*of\s*(\d+)|(\d+)\s*[- ]?(?:pack|pcs|pieces|pairs)", title.lower())
    return int(next(g for g in m.groups() if g)) if m else 1


STORES_CLOTHES = {"zara", "max", "centrepoint"}      # Carrefour / Lulu fashion listings are mostly third-party junk (costumes, bags)
STORES_GOODS = {"carrefour", "lulu", "sharafdg"}
JUNK = ["costume", "cosplay", "doll", "toy", "toys", "garment", "hanger", "cover", "ointment", "thermometer", "refrigerator", "freezer",
        "freshener", "refill", "uniform_x"]


AR_UNITS = [(r"ليتر|لتر|ltr|lt|l", "ml", 1000), (r"مل|ml|ملم", "ml", 1), (r"كغ|كج|كيلو|كلغ|kg", "g", 1000), (r"غرام|جرام|غم|غ|gm|g", "g", 1)]


def basket_size(it):
    """(unit, size of one pack) of a basket line from its unit text, Arabic units included ('1.5 ليتر', '190 غ')."""
    t = (it.get("unit") or it.get("qty_raw") or "").lower().replace(",", ".")
    m = re.search(r"(\d+(?:\.\d+)?)\s*([^\d\s.*xX]+)", t)
    if not m or not any(re.fullmatch(p, m.group(2).strip(". ")) for p, _, _ in AR_UNITS):
        m = re.search(r"(\d+(?:\.\d+)?)\s*(ml|مل|ملم|ml|g|غ|غرام|جرام|كغ|كج|كيلو|kg|لتر|ليتر|ltr)", (it.get("name_ar") or "").lower().replace(",", "."))
    if not m:
        return None
    num, u = float(m.group(1)), m.group(2).strip(". ")
    for pat, base, mult in AR_UNITS:
        if re.fullmatch(pat, u):
            return base, num * mult
    return None


def size_class_ok(it, title):
    """The title states the basket's size as a unit size (a 1.5 L line takes 1.5 L bottles, also sold as 'Pack of 6'), so like is compared with like."""
    want = basket_size(it)
    if want is None:
        return False                                    # a line whose size cannot be read is not compared by price per kg / litre
    unit, per = want
    t = title.lower().replace(",", "")
    for num, u in re.findall(r"(\d+(?:\.\d+)?)\s*(ml|l|ltr|litre|litres|liter|liters|g|gm|kg)\b", t):
        base, mult = {"ml": ("ml", 1), "l": ("ml", 1000), "ltr": ("ml", 1000), "litre": ("ml", 1000), "litres": ("ml", 1000),
                      "liter": ("ml", 1000), "liters": ("ml", 1000), "g": ("g", 1), "gm": ("g", 1), "kg": ("g", 1000)}[u]
        if base == unit and abs(float(num) * mult - per) <= 0.015 * per + 0.5:
            return True
    return False


def count_ok(unit_text, title):
    nums = [n for n in re.findall(r"\d+", unit_text or "") if int(n) >= 2]
    return all(re.search(rf"(?<![\d.]){n}(?![\d.]|\s*(?:ml|g|kg|l)\b)", title.lower()) for n in nums)


def candidate_price(spec, it, row, want_q):
    tw = words(row["title"])
    if spec["brand"] and not all(has_word(tw, w) for w in spec["brand"]):
        return None
    if not any(all(has_word(tw, w) for w in alt) for alt in spec["any"]):
        return None
    if any(has_word(tw, n) for n in spec["none"] + JUNK):
        return None
    if spec["mode"] == "set" and spec.get("demo") is not None and spec["basis"] == "pc":      # clothes: shirt is not a polo or t-shirt
        for alt in spec["any"]:
            if alt == ["shirt"] and re.search(r"t-?\s?shirt|\btees?\b|polo|sweatshirt|tank", row["title"].lower()):
                return None
    d = spec.get("demo")
    if d:
        got = demo_of(row)
        if d == "any":
            pass
        elif d == "kids":
            if got not in ("kids", "boys", "girls", "baby"):
                return None
        elif got != d:
            return None
    if spec["mode"] == "exact":
        if basket_size(it) is not None:
            if not size_class_ok(it, row["title"]) and not (want_q is not None and want_q.ok and any(same_quantity(q, want_q) for q in all_quantities(row["title"]))):
                return None
        elif want_q is not None and want_q.ok and not any(same_quantity(q, want_q) for q in all_quantities(row["title"])):
            return None
    if spec["basis"] == "pc" and spec.get("demo") is None and not count_ok(it.get("unit", ""), row["title"]):
        return None
    if spec.get("packs", 1) != 1 or (spec["mode"] == "set" and spec["basis"] == "pc" and spec.get("demo")):
        if row_pack(row["title"]) != spec.get("packs", 1):
            return None
    try:
        price = float(row["price"])
        if spec["basis"] in ("l", "kg"):
            if row["price_basis"] != spec["basis"] or not row.get("unit_price"):
                return None
            return float(row["unit_price"])
        if spec["basis"] == "bag100":
            m = re.search(r"(\d+)\s*(?:tea\s*)?bags?", row["title"].lower())
            return price / int(m.group(1)) * 100 if m and int(m.group(1)) > 0 else None
    except ValueError:
        return None
    return price


def match(cat_dir, out_csv):
    from cpi.basket import load_basket_any
    from dataclasses import asdict
    cat = list(csv.DictReader(open(Path(cat_dir) / "catalog.csv", encoding="utf-8-sig")))
    raw = {b["item_code"]: b for b in json.load(open(ROOT / "data/basket/basket.json", encoding="utf-8"))}
    out, nospec = [], 0
    for it in (asdict(i) for i in load_basket_any(ROOT)):
        r = raw[it["item_code"]]
        if r.get("match_mode") != "name" or re.search(r"[A-Za-z]{3,}", it["name_ar"]):
            continue
        it["unit"] = r.get("qty_raw", "")
        spec = spec_for(it)
        if spec is None:
            nospec += 1
            continue
        want_q = parse_quantity(it["qty_raw"]) if it["qty_raw"] else None
        stores = STORES_CLOTHES if it["item_code"].startswith(("0312", "0313", "0321")) else STORES_GOODS
        by = {}
        for row in cat:
            if row["store"] not in stores or not row["price"]:
                continue
            p = candidate_price(spec, it, row, want_q)
            if p is not None and p > 0:
                by.setdefault(row["store"], []).append((p, row))
        need = 2 if spec["mode"] == "set" else 1
        for store, lst in by.items():
            if len(lst) < need:
                continue
            ps = sorted(p for p, _ in lst)
            med = statistics.median(ps)
            rep = min(lst, key=lambda x: abs(x[0] - med))[1]
            out.append(dict(item_code=it["item_code"], retailer=store, status="found", title=rep["title"], price=round(med, 2),
                            regular_price=rep["regular_price"], url=rep["url"], photo=rep["photo_url"], retailer_id=rep["retailer_id"],
                            n_products=len(lst), price_basis=spec["basis"],
                            note=f"{spec['mode']} · {len(lst)} products ({ps[0]:.2f}-{ps[-1]:.2f} AED per {spec['basis']})"))
    with open(out_csv, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0]))
        w.writeheader()
        w.writerows(out)
    items = {r["item_code"] for r in out}
    print(f"{len(items)} lines priced ({len(out)} store rows); {nospec} lines without a spec -> {out_csv}")
    return out


if __name__ == "__main__":
    match(sys.argv[1], sys.argv[2])
