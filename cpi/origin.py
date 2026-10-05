"""Map the many Arabic spellings of a country of origin ('الإمارات', 'الامارات', 'uae', 'امريكي'...) to ISO-2."""
from .text import norm_text

_RAW = {
    "AE": "الامارات الإمارات امارات الامات uae emirates",
    "SA": "السعودية سعودية السعوديه",
    "IN": "الهند هندي india",
    "OM": "عمان عماني",
    "EG": "مصر مصري egypt",
    "US": "امريكا أمريكا امريكي usa",
    "PK": "باكستان باكستاني ياكستان",
    "NL": "هولندا",
    "TR": "تركيا",
    "BR": "برازيل البرازيل",
    "LB": "لبنان",
    "IR": "ايران إيران",
    "CN": "الصين",
    "JO": "الاردن",
    "MY": "ماليزيا",
    "FR": "فرنسا",
    "AU": "استراليا استرالي",
    "BE": "بلجيكا",
    "TH": "تايلاند تايلند",
    "PH": "الفلبين",
    "GR": "اليونان",
    "GB": "انجلترا بريطانيا",
    "DK": "الدنمارك دنمارك",
    "KW": "الكويت",
    "MT": "مالطا",
    "VN": "فيتنام",
    "SG": "سنغافورة",
    "BH": "البحرين",
    "IT": "ايطاليا إيطاليا",
    "ES": "اسبانيا إسبانيا اسباني اسبيانيا",
    "AT": "النمسا",
    "TN": "تونس",
    "IE": "ايرلندا إيرلندا",
    "EC": "الاكوادور الإكوادور",
    "KE": "كينيا",
        "YE": "يمني",
    "ID": "اندونيسيا إندونيسيا",
    "ET": "اثيوبيا أثيوبيا",
    "NZ": "نيوزلندا نيوزلاند نيوزلاندي",
    "NO": "نرويج",
    "CZ": "تشيكي",
    "MA": "مغربي",
    "MX": "مكسيك المكسيك",
    "CL": "شيلي",
    "AF": "افغانستان",
    "SY": "سوريا",
    "AR": "الارجنتين الأرجنتين",
    "CH": "سويسرا",
    "DE": "المانيا",
    "PL": "بولندا",
    # continent only - the basket does not say which country; kept distinct so it is never treated as ZA
    "AFRICA": "افريقيا",
}


def _build():
    # multi-word names ('جنوب افريقيا', 'المملكة المتحدة') are matched first, so register them as phrases
    phrases = {"جنوب افريقيا": "ZA", "جنوب أفريقيا": "ZA", "المملكة المتحدة": "GB"}
    table = {norm_text(p): iso for p, iso in phrases.items()}
    for iso, words in _RAW.items():
        for w in words.split():
            table.setdefault(norm_text(w), iso)
    return table


ORIGINS = _build()


def origin_iso(raw) -> str:
    """ISO-2 code (or 'AFRICA'); '' if blank; 'UNKNOWN' when the spelling is not in the table."""
    key = norm_text(raw)
    if not key:
        return ""
    return ORIGINS.get(key, "UNKNOWN")


# Country names as retailers print them in English ('Origin: South Africa', 'Country of origin: Egypt', titles like
# 'Orange Navel South Africa 1 kg').
_EN = {
    "AE": "united arab emirates|uae", "SA": "saudi arabia|ksa", "IN": "india", "OM": "oman", "EG": "egypt",
    "US": "united states|usa|u.s.a", "PK": "pakistan", "NL": "netherlands|holland", "TR": "turkey|turkiye|türkiye",
    "BR": "brazil", "LB": "lebanon", "IR": "iran", "CN": "china", "JO": "jordan", "MY": "malaysia", "FR": "france",
    "AU": "australia", "BE": "belgium", "TH": "thailand", "PH": "philippines", "GR": "greece",
    "GB": "united kingdom|uk|england", "DK": "denmark", "KW": "kuwait", "VN": "vietnam", "SG": "singapore",
    "BH": "bahrain", "IT": "italy", "ES": "spain", "AT": "austria", "TN": "tunisia", "IE": "ireland", "EC": "ecuador",
    "KE": "kenya", "YE": "yemen", "ID": "indonesia", "ET": "ethiopia", "NZ": "new zealand", "NO": "norway",
    "CZ": "czech republic|czechia", "MA": "morocco", "MX": "mexico", "CL": "chile", "AF": "afghanistan", "SY": "syria",
    "AR": "argentina", "CH": "switzerland", "DE": "germany", "PL": "poland", "ZA": "south africa", "PE": "peru",
    "CO": "colombia", "CR": "costa rica", "GT": "guatemala", "LK": "sri lanka", "BD": "bangladesh", "UZ": "uzbekistan",
    "SD": "sudan", "SO": "somalia", "TZ": "tanzania", "UG": "uganda", "ZW": "zimbabwe", "NA": "namibia", "QA": "qatar",
    "IQ": "iraq", "PT": "portugal", "UA": "ukraine", "RU": "russia", "CA": "canada", "JP": "japan", "KR": "south korea|korea",
    "IL": "israel", "PS": "palestine", "CY": "cyprus", "MU": "mauritius", "YT": "mayotte", "NG": "nigeria", "GH": "ghana",
    "CI": "ivory coast|cote d'ivoire", "ZM": "zambia", "MZ": "mozambique", "MG": "madagascar", "SN": "senegal",
}
# basket 'افريقيا' lines sit next to separate Egypt / Morocco / Tunisia lines for the same fruit, so it means Africa
# south of the Sahara (in practice South Africa for citrus and grapes)
_AFRICA = {"ZA", "KE", "ET", "SD", "SO", "TZ", "UG", "ZW", "NA", "NG", "GH", "CI", "ZM", "MZ", "MG", "SN", "MU", "YT"}


def origin_iso_en(text) -> str:
    """ISO-2 for the first country named in English text, longest names first ('South Africa' before 'Africa'); ''."""
    t = " " + " ".join(str(text or "").lower().replace(",", " ").split()) + " "
    names = sorted(((n, iso) for iso, ns in _EN.items() for n in ns.split("|")), key=lambda p: -len(p[0]))
    for n, iso in names:
        if f" {n} " in t:
            return iso
    return ""


def same_origin(basket_iso: str, seen_iso: str) -> bool:
    """Basket 'افريقيا' (continent only) accepts any African country; otherwise the ISO codes must be equal."""
    if not basket_iso or not seen_iso:
        return False
    if basket_iso == "AFRICA":
        return seen_iso in _AFRICA
    return basket_iso == seen_iso
