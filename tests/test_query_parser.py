"""Query understanding (FR-23): prices, brands, colours, sizes, filler words - no network, no database."""
import pytest

from unicart.ai.query_parser import fold_chars, parse_query

BRANDS = ["Adidas", "Sony", "La Roche-Posay", "Samsung"]


@pytest.mark.parametrize("query, text, lo, hi", [
    ("áo thun nam dưới 300 nghìn", "áo thun nam", None, 300_000),
    ("giày chạy bộ dưới 1 triệu", "giày chạy bộ", None, 1_000_000),
    ("laptop từ 10 triệu đến 20 triệu", "laptop", 10_000_000, 20_000_000),
    ("Điện thoại trên 5.000.000", "Điện thoại", 5_000_000, None),
    ("tai nghe khoảng 2tr", "tai nghe", 1_500_000, 2_500_000),
    ("túi 200k - 400k", "túi", 200_000, 400_000),
    ("kem chống nắng dưới một triệu rưỡi", "kem chống nắng", None, 1_500_000),
    ("ao khoac 1,5 trieu tro xuong", "ao khoac", None, 1_500_000),
    ("tai nghe 2 triệu trở lên", "tai nghe", 2_000_000, None),
    ("black backpack under 500k", "black backpack", None, 500_000),
    ("laptop 16gb ram", "laptop 16gb ram", None, None),          # 16 is RAM, not a price
    ("áo nam", "áo nam", None, None),                             # 'nam' is male, not the number five
    ("dưới 500k", "", None, 500_000),                             # filters only
])
def test_price_phrases(query, text, lo, hi):
    p = parse_query(query, BRANDS)
    assert (p.text, p.min_price, p.max_price) == (text, lo, hi)


@pytest.mark.parametrize("query, colors", [
    ("áo thun nam đỏ", ["red"]), ("áo màu kem", ["cream"]), ("túi màu cam", ["orange"]),
    ("ao mau den", ["black"]), ("váy xanh lá", ["green"]), ("giày xanh dương", ["blue"]),
    ("kem chống nắng", []),          # 'kem' the product, not the colour
    ("đồ chạy bộ", []),              # 'đồ' (things) must not be read as 'đỏ' (red)
    ("black backpack", ["black"]),
])
def test_colours_are_not_confused_with_ordinary_words(query, colors):
    assert parse_query(query, BRANDS).colors == colors


def test_brand_size_and_filler():
    p = parse_query("tôi muốn tìm giày Adidas màu đen size 42 dưới 2 triệu", BRANDS)
    assert (p.text, p.brands, p.colors, p.sizes, p.max_price) == ("giày Adidas màu đen", ["Adidas"], ["black"], ["42"], 2_000_000)
    assert parse_query("áo sơ mi nam size L", BRANDS).sizes == ["L"]
    assert parse_query("kem La Roche-Posay", BRANDS).brands == ["La Roche-Posay"]
    assert parse_query("cho mình xem áo khoác", BRANDS).text == "áo khoác"
    assert parse_query("I am looking for a black backpack", BRANDS).text == "black backpack"
    assert parse_query("tìm kiếm", BRANDS).text == "tìm kiếm"       # not mangled


def test_fold_keeps_character_offsets():
    s = "Điện thoại Đẹp"
    assert len(fold_chars(s)) == len(s) and fold_chars(s) == "dien thoai dep"
