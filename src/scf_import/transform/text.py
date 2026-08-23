import re
import unicodedata
from typing import Any

_PAIR_LEN = 2
_THOUSANDS_LEN = 3


def clean_str(val: Any) -> str:
    if val is None:
        return ""
    text = str(val).strip(" \t\n\r\ufeff\"'")
    collapsed = re.sub(r"\s+", " ", text)
    return collapsed.strip(" \t\n\r\ufeff\"'")


def normalize_key(val: Any) -> str:
    text = clean_str(val)
    if not text:
        return ""
    # Normalize unicode to NFKD and remove combining characters (accents)
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(c for c in decomposed if not unicodedata.combining(c))
    # Replace common symbols with whitespace or equivalents
    normalized = re.sub(r"[/_\-\.,;:()\"']", " ", without_accents)
    # Collapse whitespace and lowercase
    return re.sub(r"\s+", " ", normalized).strip().lower()


def parse_number_ve(val: Any) -> int | float | None:
    text = clean_str(val)
    if not text:
        return None

    text = text.replace(" ", "")

    # If format has both '.' and ',' like 1.234,56
    if "." in text and "," in text:
        text = text.replace(".", "").replace(",", ".")
    elif "," in text:
        parts = text.split(",")
        if len(parts) == _PAIR_LEN and len(parts[1]) in (1, 2):
            text = text.replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "." in text:
        parts = text.split(".")
        if len(parts) == _PAIR_LEN and len(parts[1]) == _THOUSANDS_LEN:
            text = text.replace(".", "")
        elif len(parts) > _PAIR_LEN:
            text = "".join(parts)

    try:
        num = float(text)
    except ValueError:
        return None
    else:
        return int(num) if num.is_integer() else num


def normalize_code(val: Any) -> str:
    text = clean_str(val).upper()
    return re.sub(r"\s+", "", text)


def title_case(val: Any) -> str:
    text = clean_str(val)
    if not text:
        return ""
    words = text.split(" ")
    out_words: list[str] = []
    for word in words:
        upper = word.upper()
        if upper in ("S/E", "S / E", "S.E.", "S.E"):
            out_words.append("S. E.")
        elif upper in ("C.A.", "C.A", "S.A.", "S.A", "SAP", "MPPEE", "INTT", "VIN", "GPS"):
            out_words.append(upper if upper.endswith(".") else f"{upper}")
        elif re.match(r"^F-\d+$", upper) or re.match(r"^300-\d+$", upper):
            out_words.append(upper)
        else:
            out_words.append(word.capitalize())
    return " ".join(out_words).strip()
