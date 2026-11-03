"""Understands a Vietnamese/English shopping query without calling any model (fast and deterministic, FR-23).

"giày chạy bộ màu đen size 42 dưới 1 triệu" ->
    text="giày chạy bộ màu đen", max_price=1_000_000, colors=["black"], sizes=["42"]
Price phrases and size are removed from the text that goes to the semantic model; brand and colour words stay."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field


def fold_chars(s: str) -> str:
    """Lower-case and strip diacritics one character at a time, so offsets match the NFC original."""
    out = []
    for ch in unicodedata.normalize("NFC", s):
        if ch in "đĐ":
            out.append("d")
            continue
        base = "".join(c for c in unicodedata.normalize("NFD", ch) if unicodedata.category(c) != "Mn")
        out.append((base or ch)[0].lower())
    return "".join(out)


_WORDS = {"mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "lam": 5, "sau": 6, "bay": 7, "tam": 8, "chin": 9, "muoi": 10}
_NUM = r"(?:\d{1,3}(?:[.,]\d{3})+|\d+(?:[.,]\d+)?|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)"
_UNIT = r"(?:trieu|tr|nghin|ngan|k|m|dong|vnd|d)"
def _amount(p: str) -> str:
    """Regex of one amount whose groups are named <p>n (number), <p>u (unit), <p>h ('ruoi' = half)."""
    return f"(?P<{p}n>{_NUM})\\s*(?P<{p}u>{_UNIT})?(?P<{p}h>\\s*ruoi)?\\b"


_RANGE = re.compile(rf"\b(?:tu|trong khoang)\s*{_amount('a')}\s*(?:den|toi|-|–)\s*{_amount('b')}")
_RANGE2 = re.compile(rf"\b{_amount('a')}\s*(?:-|–|den)\s*{_amount('b')}")
_AROUND = re.compile(rf"\b(?:khoang|tam|quanh|xap xi)\s*{_amount('a')}")
_UNDER = re.compile(rf"\b{_amount('a')}\s*(?:tro xuong|do lai|tro lai|tro ve)\b")
_OVER = re.compile(rf"\b{_amount('a')}\s*(?:tro len|do len|tro di)\b")
_MAX = re.compile(rf"(?:\b(?:duoi|nho hon|it hon|khong qua|toi da|re hon|max|under|below|less than|up to)\b|<=?)\s*{_amount('a')}")
_MIN = re.compile(rf"(?:\b(?:tren|lon hon|toi thieu|it nhat|tu|min|over|above|more than|at least)\b|>=?)\s*{_amount('a')}")
_FILLER = re.compile(
    r"^\s*(?:(?:toi|minh|em|anh|chi|ban)\s+)?(?:(?:muon|can|dang|se)\s+)?(?:(?:tim(?!\s+kiem)|mua|xem|kiem|chon)(?:\s+(?:giup|cho))?|cho\s+(?:toi|minh)\s+xem)"
    r"(?:\s+(?:mot|may|cac|nhung|cai|chiec))*\b"
    r"|^\s*(?:i am|i'm|i want|i need|show me|find me)(?:\s+(?:looking for|to buy|to find))?(?:\s+(?:a|an|some|the))?\b", re.I)
_SIZE = re.compile(r"\b(?:size|co)\s*(xxl|xl|xs|s|m|l|\d{2})\b")

# Vietnamese colour words matched on the accented text (so 'đồ' is not 'đỏ'), canonical English as in product attributes.
COLORS_VI = {"đen": "black", "trắng": "white", "đỏ": "red", "xanh dương": "blue", "xanh lá": "green", "xanh": "blue",
             "vàng": "yellow", "hồng": "pink", "xám": "grey", "nâu": "brown", "tím": "purple"}
# Ambiguous with ordinary words (kem = cream the product, cam = orange / commit, ghi = note): need the word 'màu'.
COLORS_VI_WITH_PREFIX = {"kem": "cream", "cam": "orange", "ghi": "grey"}
# Unaccented typing: only after 'mau', or for the unambiguous two-word blues/greens.
COLORS_FOLDED = {"den": "black", "trang": "white", "do": "red", "xanh": "blue", "vang": "yellow", "hong": "pink", "xam": "grey",
                 "nau": "brown", "tim": "purple", "kem": "cream", "cam": "orange", "ghi": "grey"}
COLORS_EN = {"navy": "navy", "black": "black", "white": "white", "red": "red", "blue": "blue", "green": "green", "grey": "grey",
             "gray": "grey", "pink": "pink", "brown": "brown", "cream": "cream", "yellow": "yellow"}
COLOR_ALIASES = {"blue": {"blue", "navy"}, "grey": {"grey", "gray"}}


@dataclass
class ParsedQuery:
    original: str
    text: str                                    # what goes to the semantic model / keyword search
    min_price: int | None = None
    max_price: int | None = None
    brands: list[str] = field(default_factory=list)
    colors: list[str] = field(default_factory=list)
    sizes: list[str] = field(default_factory=list)

    @property
    def has_filters(self) -> bool:
        return self.min_price is not None or self.max_price is not None

    def tokens(self) -> list[str]:
        return [t for t in re.split(r"\W+", fold_chars(self.text)) if len(t) > 1]


def _value(num: str, unit: str | None, half: str | None) -> int | None:
    """Convert '1,5' 'trieu' 'ruoi' etc. to VND; None when it is not a plausible price."""
    if num in _WORDS:
        if not unit:
            return None                          # 'nam' alone is the word for male/5, not a price
        v = float(_WORDS[num])
    elif re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", num):
        v = float(re.sub(r"[.,]", "", num))
    else:
        v = float(num.replace(",", "."))
    if half:
        v += 0.5
    mult = {"trieu": 1e6, "tr": 1e6, "m": 1e6, "nghin": 1e3, "ngan": 1e3, "k": 1e3}.get(unit or "", 1)
    vnd = int(round(v * mult))
    return vnd if 1_000 <= vnd <= 2_000_000_000 else None


def parse_query(query: str, known_brands: list[str] | None = None) -> ParsedQuery:
    original = " ".join(unicodedata.normalize("NFC", query or "").split())
    folded = list(fold_chars(original))
    keep = [True] * len(original)

    def cut(m: re.Match) -> None:
        for i in range(*m.span()):
            keep[i] = False
            folded[i] = " "

    pq = ParsedQuery(original=original, text="")

    def val(m: re.Match, p: str) -> int | None:
        return _value(m.group(f"{p}n"), m.group(f"{p}u"), m.group(f"{p}h"))

    for pattern in (_RANGE, _RANGE2):
        m = pattern.search("".join(folded))
        if m and (a := val(m, "a")) and (b := val(m, "b")):
            # '1 - 3 trieu': a unit written only on the second number applies to both
            if m.group("au") is None and m.group("bu") and a < 1000:
                a = _value(m.group("an"), m.group("bu"), m.group("ah")) or a
            pq.min_price, pq.max_price = min(a, b), max(a, b)
            cut(m)
            break
    if pq.min_price is None:
        text = "".join(folded)
        if (m := _AROUND.search(text)) and (a := val(m, "a")):
            pq.min_price, pq.max_price = int(a * 0.75), int(a * 1.25)
            cut(m)
    for pattern, attr, current in ((_UNDER, "max_price", pq.max_price), (_OVER, "min_price", pq.min_price),
                                   (_MAX, "max_price", pq.max_price), (_MIN, "min_price", pq.min_price)):
        if getattr(pq, attr) is None and (m := pattern.search("".join(folded))) and (a := val(m, "a")):
            setattr(pq, attr, a)
            cut(m)
    if m := _SIZE.search("".join(folded)):
        pq.sizes.append(m.group(1).upper())
        cut(m)

    # leading filler of natural speech: "tôi muốn tìm ...", "cho mình xem ...", "I am looking for a ..."
    if m := _FILLER.match("".join(folded)):
        cut(m)

    ftext = "".join(folded)
    for brand in sorted(known_brands or [], key=len, reverse=True):
        if re.search(rf"(?<![a-z0-9]){re.escape(fold_chars(brand))}(?![a-z0-9])", ftext):
            pq.brands.append(brand)
    lowered = original.lower()

    def add_color(c: str) -> None:
        if c not in pq.colors:
            pq.colors.append(c)

    for word, c in sorted({**COLORS_VI, **{f"màu {k}": v for k, v in COLORS_VI_WITH_PREFIX.items()}}.items(), key=lambda kv: -len(kv[0])):
        if re.search(rf"(?<!\w){word}(?!\w)", lowered):
            add_color(c)
            lowered = re.sub(rf"(?<!\w){word}(?!\w)", " ", lowered)            # 'xanh dương' must not also hit 'xanh'
    if "xanh duong" in ftext:
        add_color("blue")
    if "xanh la" in ftext:
        add_color("green")
    for word, c in COLORS_FOLDED.items():
        if re.search(rf"\bmau\s+{word}\b", ftext):
            add_color(c)
    for word, c in COLORS_EN.items():
        if re.search(rf"(?<![a-z0-9]){word}(?![a-z0-9])", ftext):
            add_color(c)

    pq.text = " ".join("".join(c for c, k in zip(original, keep) if k).split())
    pq.text = re.sub(r"\b(?:gia|co gia|mau|size|co)\s*$", "", pq.text, flags=re.I).strip()
    return pq
