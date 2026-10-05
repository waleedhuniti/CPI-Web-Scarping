"""Text normalisation shared by the basket loader and the matcher."""
import re

_ARABIC_INDIC = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
_DIACRITICS = re.compile("[ً-ٰٟـ]")  # harakat + tatweel
_ALEF = re.compile("[أإآٱ]")


def norm_text(value) -> str:
    """Lower-case, strip diacritics, unify alef/ya/ta-marbuta and Arabic-Indic digits."""
    if value is None:
        return ""
    s = str(value).translate(_ARABIC_INDIC)
    s = _DIACRITICS.sub("", s)
    s = _ALEF.sub("ا", s)
    s = s.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"\s+", " ", s).strip().lower()
