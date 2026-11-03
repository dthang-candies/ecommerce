"""Rule-based assistant: answers the common questions without any AI, using the very same tools as the Gemini path.

Used when GEMINI_API_KEY is missing or Gemini is down/slow (NFR-12), so promotions, order tracking and return help
keep working. Deliberately simple keyword intents; free-form product wishes go to the shop search."""
from __future__ import annotations

import re

from ..ai.query_parser import fold_chars
from .chat_tools import ChatToolbox, LOGIN_NEEDED

GREETING = ("Xin chào! Mình là trợ lý mua sắm của UniCart. Mình có thể giúp bạn tìm sản phẩm, xem mã giảm giá hôm nay, "
            "tra cứu đơn hàng và hướng dẫn đổi trả. Bạn cần gì nào?")

_PATTERNS = {
    "return": r"\b(doi tra|tra hang|doi hang|hoan tien|hoan hang|tra lai|bao hanh|hang loi|bi loi|loi san pham|sai size|sai mau|giao sai|doi size)\b",
    "promo": r"\b(giam gia|khuyen mai|khuyen mai|uu dai|voucher|coupon|ma giam|sale|deal|giam bao nhieu)\b",
    "cancel": r"\b(huy don|huy hang|khong muon mua|dung giao)\b",
    "order": r"\b(don hang|don cua toi|ma don|kiem tra don|tra cuu|tracking|van don|giao toi dau|bao gio (?:nhan|giao|toi)|dang o dau)\b",
    "shipping": r"\b(phi ship|phi van chuyen|phi giao|tien ship|mien phi (?:ship|van chuyen|giao)|freeship|van chuyen|ship)\b",
    "payment": r"\b(thanh toan|cod|tra tien|the tin dung|the ngan hang|vi dien tu|quet ma)\b",
    "hello": r"^\s*(xin chao|chao|hello|hi|alo|helo|co ai khong|ban lam duoc gi|giup|help)\b",
}
_BARE_ORDER = re.compile(r"\W*(?:don(?:\s+hang)?\s*)?#?\s*\d{1,9}\W*")
_ORDER_NO = re.compile(r"(?:#|\bdon(?:\s+hang)?(?:\s+(?:so|ma|id))?\s*)(\d{1,9})\b")


def _intent(folded: str) -> str | None:
    for name in ("return", "cancel", "promo", "order"):
        if re.search(_PATTERNS[name], folded):
            return name
    if _ORDER_NO.search(folded):                         # "đơn #12", "đơn 12": an explicit order reference
        return "order"
    for name in ("shipping", "payment", "hello"):
        if re.search(_PATTERNS[name], folded):
            return name
    return None


def _order_number(folded: str, loose: bool) -> int | None:
    m = _ORDER_NO.search(folded)
    if m:
        return int(m.group(1))
    if loose:
        m = re.search(r"\b(\d{1,9})\b", folded)
        return int(m.group(1)) if m else None
    return None


def is_quick_question(text: str, previous_user_text: str, max_words: int) -> bool:
    """A short message with a clear shop-service intent (promotions, shipping, orders, returns...): the rule engine
    answers it completely and instantly, so the (slow, quota-limited) model is kept for open-ended questions."""
    return answers_by_rules(text, previous_user_text) and len(text.split()) <= max_words


def answers_by_rules(text: str, previous_user_text: str = "") -> bool:
    folded = fold_chars(text)
    if _intent(folded) is not None:
        return True
    return bool(previous_user_text) and bool(_BARE_ORDER.fullmatch(folded)) and _intent(fold_chars(previous_user_text)) is not None


def suggestions(is_customer: bool) -> list[str]:
    base = ["Hôm nay có mã giảm giá nào?", "Phí vận chuyển thế nào?"]
    if is_customer:
        return base + ["Đơn hàng của tôi đến đâu rồi?", "Tôi muốn đổi trả hàng"]
    return base + ["Chính sách đổi trả", "Gợi ý laptop dưới 25 triệu"]


def answer(box: ChatToolbox, text: str, previous_user_text: str = "") -> str:
    """Return the reply text; cards and actions are collected on the toolbox."""
    folded = fold_chars(text)
    intent = _intent(folded)
    if intent is None and previous_user_text and _BARE_ORDER.fullmatch(folded):
        intent = _intent(fold_chars(previous_user_text)) or "order"      # the shopper just typed the order number we asked for
    if intent == "hello":
        return GREETING
    if intent == "promo":
        return _promotions(box)
    if intent == "shipping":
        return box.call("get_shop_policy", {"topic": "shipping"})["policy"]
    if intent == "payment":
        return box.call("get_shop_policy", {"topic": "payment"})["policy"]
    if intent == "cancel":
        return _cancel(box, _order_number(folded, True))
    if intent == "return":
        return _return(box, _order_number(folded, True), text)
    if intent == "order":
        return _orders(box, _order_number(folded, True))
    return _products(box, text)


def _promotions(box: ChatToolbox) -> str:
    res = box.call("list_active_promotions", {})
    promos = res["promotions"]
    if not promos:
        return "Hôm nay UniCart chưa có mã giảm giá nào đang áp dụng. Bạn có thể xem sản phẩm mới ở trang chủ nhé."
    lines = "\n".join(f"• {p['code']}: {p['description']}" for p in promos)
    return (f"Hôm nay ({res['today']}) UniCart có {len(promos)} mã giảm giá đang áp dụng:\n{lines}\n"
            "Lưu ý: hiện chưa có giá giảm riêng cho từng sản phẩm. Mã được nhập ở bước thanh toán và áp dụng cho cả đơn hàng.")


def _products(box: ChatToolbox, text: str) -> str:
    res = box.call("search_products", {"query": text})
    if res.get("error") or not res["products"]:
        hint = f" Có phải bạn muốn tìm “{res['did_you_mean']}”?" if res.get("did_you_mean") else ""
        return ("Mình chưa tìm thấy sản phẩm phù hợp." + hint +
                " Bạn thử mô tả khác (loại hàng, màu, khoảng giá), hoặc hỏi về mã giảm giá, đơn hàng, đổi trả nhé.")
    note = f" (đã tìm theo “{res['searched_instead_for']}”)" if res.get("searched_instead_for") else ""
    return f"Mình tìm được {res['total_found']} sản phẩm phù hợp{note}, đây là những gợi ý hàng đầu:"


def _orders(box: ChatToolbox, order_id: int | None) -> str:
    if box.customer_id is None:
        return LOGIN_NEEDED + " Bạn đăng nhập rồi hỏi lại mình nhé."
    if order_id is not None:
        res = box.call("get_order_status", {"order_id": order_id})
        if "error" in res:
            return res["error"] + ". Bạn kiểm tra lại mã đơn giúp mình nhé."
        extra = ""
        if res.get("shipment") and res["shipment"].get("tracking_number"):
            extra = f" Mã vận đơn {res['shipment']['tracking_number']} ({res['shipment']['carrier'] or 'đơn vị vận chuyển'})."
        total = f"{res['total_vnd']:,}".replace(",", ".")
        return f"Đơn #{res['order_id']} đang ở trạng thái “{res['status']}”, tổng {total}đ." + extra
    res = box.call("get_my_orders", {})
    if not res["orders"]:
        return "Tài khoản của bạn chưa có đơn hàng nào."
    return "Đây là các đơn gần đây của bạn. Bạn muốn xem chi tiết đơn nào thì gõ mã đơn, ví dụ “đơn #" + str(res["orders"][0]["order_id"]) + "”."


def _cancel(box: ChatToolbox, order_id: int | None) -> str:
    policy = box.call("get_shop_policy", {"topic": "cancel"})["policy"]
    if box.customer_id is None:
        return policy + " Đăng nhập để xem đơn của bạn và hủy trong mục Đơn hàng của tôi."
    if order_id is None:
        box.call("get_my_orders", {})
        return policy + " Mình không tự hủy đơn thay bạn được; hãy mở đơn trong mục Đơn hàng của tôi và bấm Hủy đơn."
    res = box.call("get_order_status", {"order_id": order_id})
    if "error" in res:
        return res["error"]
    if res["can_cancel"]:
        return f"Đơn #{order_id} đang “{res['status']}” nên vẫn hủy được. Bạn mở đơn trong mục Đơn hàng của tôi và bấm Hủy đơn nhé."
    return f"Đơn #{order_id} đang “{res['status']}” nên không thể hủy nữa. " + policy


def _return(box: ChatToolbox, order_id: int | None, text: str) -> str:
    policy = box.call("get_shop_policy", {"topic": "return"})["policy"]
    if box.customer_id is None:
        return policy + " Bạn đăng nhập để mình kiểm tra đơn và soạn sẵn yêu cầu đổi trả giúp bạn."
    if order_id is None:
        orders = box.call("get_my_orders", {})["orders"]
        example = f", ví dụ “đơn #{orders[0]['order_id']}”" if orders else ""
        return policy + f"\nBạn muốn đổi trả đơn nào? Hãy gõ mã đơn{example}."
    res = box.call("check_return_eligibility", {"order_id": order_id})
    if "error" in res:
        return res["error"]
    if res["eligible"] is False:
        dates = f" (đơn giao ngày {res['delivered_on']}, hạn đổi trả {res['deadline']})" if res.get("deadline") else ""
        return f"Đơn #{order_id}: {res['reason']}{dates}"
    box.call("propose_support_request", {"content": f"Tôi muốn đổi/trả hàng của đơn #{order_id}. Lý do: ", "order_id": order_id})
    when = f" Đơn giao ngày {res['delivered_on']}, hạn đổi trả đến {res['deadline']}." if res.get("deadline") else ""
    return (f"Đơn #{order_id} đủ điều kiện gửi yêu cầu đổi trả.{when} Mình đã soạn sẵn yêu cầu bên dưới: "
            "bạn ghi rõ lý do (sản phẩm lỗi, sai size, sai mẫu…) rồi bấm Gửi, nhân viên chăm sóc khách hàng sẽ phản hồi.")
