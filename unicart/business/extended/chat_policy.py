"""Shop policies the assistant may quote. One place to edit; numbers come from config / business rules so the chatbot
never contradicts the checkout (BR-04, BR-06, BR-08). The return policy is a DEMO policy: the source documents define
no return flow, so it is stated here and handled through a support request (UC-23)."""
from __future__ import annotations

from ... import config


def _vnd(n: int) -> str:
    return f"{n:,}".replace(",", ".") + "đ"


def policies() -> dict[str, str]:
    return {
        "return": (
            f"Đổi trả trong {config.RETURN_WINDOW_DAYS} ngày kể từ ngày đơn được giao, áp dụng khi sản phẩm bị lỗi, "
            "sai mẫu/sai size hoặc không đúng mô tả; sản phẩm cần còn nguyên tình trạng, kèm hộp và phụ kiện. "
            "Khách gửi yêu cầu đổi trả (kèm mã đơn) qua mục Hỗ trợ, nhân viên chăm sóc khách hàng sẽ phản hồi cách gửi hàng về "
            "và phương án đổi sản phẩm hoặc hoàn tiền. Chatbot không tự quyết định đổi trả hay hoàn tiền."),
        "cancel": (
            "Khách tự hủy đơn khi đơn đang chờ thanh toán, chờ xác nhận hoặc đã xác nhận. Từ khi đơn được đóng gói thì "
            "không thể hủy; lúc đó nếu không muốn nhận hàng hãy dùng quy trình đổi trả sau khi nhận. Đơn hủy được hoàn lại tồn kho."),
        "shipping": (
            f"Phí vận chuyển đồng giá {_vnd(config.FLAT_SHIPPING_FEE)}; miễn phí cho đơn từ {_vnd(config.FREE_SHIPPING_THRESHOLD)} "
            "(tính trên tiền hàng, trước khi trừ mã giảm giá). Trạng thái đơn: chờ xác nhận → đã xác nhận → đã đóng gói → đang giao → đã giao."),
        "payment": (
            "Thanh toán khi nhận hàng (COD) hoặc thanh toán trực tuyến bằng ví/thẻ. Đơn thanh toán trực tuyến phải được "
            f"thanh toán trong {config.UNPAID_ORDER_TIMEOUT_MINUTES} phút, quá hạn đơn tự hủy. Số thẻ không được lưu trên hệ thống."),
        "promotion": (
            "Hiện cửa hàng chưa có giá giảm riêng theo từng sản phẩm. Ưu đãi là mã giảm giá nhập ở bước thanh toán; "
            "mỗi đơn dùng được một mã, phải đạt giá trị đơn tối thiểu và còn trong thời hạn."),
    }


TOPICS = tuple(policies())
