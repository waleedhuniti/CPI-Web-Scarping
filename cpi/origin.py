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
