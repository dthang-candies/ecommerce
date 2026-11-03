# Chatbot hỗ trợ người mua (UC-18 Chatbot, UC-19 Chatbot đơn hàng)

Trợ lý mua sắm dạng cửa sổ chat nổi ở góc phải mọi trang khách hàng (ẩn với tài khoản nhân viên). Làm được 4 việc:

| Khách hỏi | Trợ lý làm gì | Nguồn dữ liệu |
|---|---|---|
| "Hôm nay có giảm giá gì?" | Liệt kê **mã giảm giá còn hiệu lực hôm nay** (đang bật, trong thời hạn), kèm điều kiện đơn tối thiểu, nút sao chép mã | bảng `promotion` |
| "Tìm giúp mình laptop dưới 25 triệu" | Gợi ý tối đa 5 sản phẩm (thẻ có ảnh, giá, tồn kho) | tìm kiếm AI/từ khóa có sẵn (`SearchService`) |
| "Đơn của mình đến đâu rồi?", "đơn #12" | Danh sách đơn gần đây hoặc trạng thái, thanh toán, mã vận đơn của một đơn | `customer_order` — **chỉ đơn của chính khách đăng nhập** |
| "Muốn đổi trả hàng" | Nêu chính sách, kiểm tra đơn còn trong hạn đổi trả không, **soạn sẵn** yêu cầu hỗ trợ để khách sửa và bấm Gửi | `support_request` (UC-23) do khách xác nhận |

Ngoài ra trả lời phí vận chuyển, thanh toán, hủy đơn theo đúng quy tắc BR-04/06/08 (số liệu lấy từ `config`, không gõ cứng trong câu trả lời).

## Hai quyết định phạm vi (đã thống nhất)
1. **"Sản phẩm giảm giá" = mã giảm giá đang hiệu lực.** Hệ thống chưa có giá giảm riêng cho từng sản phẩm (chỉ có `Promotion` áp dụng cho cả đơn khi thanh toán). Chatbot nói rõ điều này thay vì giả vờ có sản phẩm đang giảm. Nếu sau này thêm giá khuyến mại theo sản phẩm, chỉ cần thêm một công cụ `list_discounted_products` và sửa pricing/cart/checkout.
2. **Đổi trả = giải thích + tạo yêu cầu hỗ trợ.** Tài liệu gốc không có quy trình đổi trả (không có trạng thái đơn, hoàn kho hay hoàn tiền khi trả). Chatbot không thể đổi/trả/hoàn tiền; nhân viên SALES xử lý yêu cầu ở màn hình Hỗ trợ có sẵn.

> **Chính sách đổi trả là chính sách MẪU của đồ án**: 7 ngày kể từ ngày giao (`RETURN_WINDOW_DAYS`), áp dụng khi hàng lỗi/sai mẫu/sai mô tả. Nội dung nằm trong `business/extended/chat_policy.py` — sửa ở đó cho đúng chính sách thật. Nếu báo cáo gốc có quy định khác thì lấy theo báo cáo.

## Kiến trúc
```
ChatWidget (React) ── POST /api/chat {messages} ──▶ routers/chat.py (rate limit, JWT tùy chọn)
                                                        │
                                                   ChatService.reply(actor, messages)
                          câu ngắn có ý định rõ ───────┤──────────────── câu dài / mở
                          (≤ 12 từ: mã giảm giá,        │                 Gemini function-calling, tối đa 4 vòng
                          phí ship, "đơn #12"...)      │                 (25 s/lần gọi, 50 s tổng)
                                  ▼                    │                         │ lỗi / chậm / chưa có key
                           chat_rules (luật)  ◀────────┴─────────────────────────┘
                                  │  dùng chung
                                  ▼
                           ChatToolbox (8 công cụ CHỈ ĐỌC) ──▶ SearchService, PromotionRepository, OrderRepository
```
- **Công cụ:** `search_products`, `get_product_details`, `list_active_promotions`, `get_my_orders`, `get_order_status`, `get_shop_policy`, `check_return_eligibility`, `propose_support_request`.
- **Phản hồi:** `{reply, mode: "ai"|"rules", degraded, suggestions[], products[], promotions[], orders[], actions[]}`. Giao diện vẽ thẻ sản phẩm/mã/đơn từ **dữ liệu công cụ**, nên giá hiển thị luôn lấy từ CSDL, không phải do model viết.
- **Không lưu gì trên máy chủ:** hội thoại nằm ở trình duyệt (`sessionStorage`, gắn với tài khoản, tự bỏ khi đổi tài khoản) và được gửi lại mỗi lượt (12 lượt gần nhất). Không có bảng lịch sử chat; nội dung tin nhắn không được ghi log.

## Vì sao có "đường nhanh" (đo trên Gemini gói miễn phí, 2026-11-03)
Một lệnh gọi Gemini mất **7–17 s** (cùng ngày, buổi tối, đo lại một câu "Chào" trơn mất **20–28 s**, tức đổi theo tải của Google), mà trả lời có dùng công cụ cần ≥ 2 lệnh (một câu mở thật mất ~30 s). Tắt/giảm "thinking" không cải thiện (đã thử `thinkingLevel` minimal/low và `thinkingBudget: 0` — cái cuối bị từ chối). Vì vậy:
- Câu hỏi ngắn thuộc nhóm dịch vụ (mã giảm giá, phí ship, thanh toán, hủy/đổi trả, tra đơn) do **bộ luật** trả lời trong ~20 ms và không tốn hạn mức. Các nút gợi ý nằm trong nhóm này.
- Gemini dành cho câu dài/mở ("tư vấn laptop cho sinh viên lập trình, tầm 25 triệu…"); quá `CHAT_TIMEOUT` hoặc lỗi thì bộ luật trả lời và phản hồi có `degraded: true` (NFR-12). Nếu bộ luật cũng không có gì để đưa ra (câu dài, không có ý định rõ) thì bot nói thẳng "AI đang bận, hãy hỏi ngắn hơn" thay vì báo "không tìm thấy sản phẩm". Lần gọi đầu bị timeout thì **không** thử model dự phòng (cùng backend, chỉ nhân đôi thời gian chờ). Giao diện hiện "Mình đang tra cứu…" sau 6 s.
- Chỉnh bằng biến môi trường: `CHAT_CALL_TIMEOUT` (25), `CHAT_TIMEOUT` (50), `CHAT_FAST_PATH_WORDS` (12; đặt 0 để luôn dùng model), `GEMINI_TEXT_MODEL`.

Bộ luật (`business/extended/chat_rules.py`) là từ khóa tiếng Việt có/không dấu, không phải hiểu ngôn ngữ: câu ngắn nhưng nằm ngoài các nhóm trên sẽ được **tìm như sản phẩm** (đường nhanh chỉ áp dụng khi nhận ra ý định).

## Bảo mật & quyền riêng tư
- **Danh tính lấy từ JWT**, không từ tham số của model: công cụ đơn hàng chỉ đọc đơn có `customer_id` = khách đăng nhập; đơn của người khác và đơn không tồn tại trả **cùng một thông báo** (không dò được mã đơn). Khách chưa đăng nhập và tài khoản nhân viên không dùng được công cụ đơn hàng.
- **Model không bao giờ ghi dữ liệu.** Không có công cụ hủy đơn, đổi trả, hoàn tiền. `propose_support_request` chỉ tạo "đề xuất" hiện thành thẻ có ô soạn thảo; yêu cầu chỉ được tạo khi **khách bấm Gửi**, qua endpoint `POST /me/support-requests` có sẵn (kiểm tra quyền như thường).
- **Dữ liệu gửi cho Gemini được tối giản:** mã đơn, trạng thái, tên sản phẩm, tổng tiền, trạng thái/mã vận đơn. **Không** gửi địa chỉ, số điện thoại, tên người nhận, email (có test). Lưu ý như tìm kiếm AI: gói miễn phí của Google có thể dùng dữ liệu gửi lên để cải thiện sản phẩm của họ; giao diện nhắc khách không nhập mật khẩu/số thẻ.
- **Chống prompt injection:** kết quả công cụ được coi là dữ liệu (system prompt nói rõ), mô tả sản phẩm bị cắt 300 ký tự, văn bản trả về được làm sạch markdown và giới hạn 1.500 ký tự; vòng gọi công cụ tối đa 4 vòng × 4 lệnh, tên công cụ lạ/tham số sai trả lỗi chứ không làm sập.
- **Giới hạn tần suất:** 20 câu/phút theo tài khoản (hoặc IP nếu chưa đăng nhập) → 429. Tin nhắn ≤ 2.000 ký tự, ≤ 40 tin/lượt gửi.

## API
`POST /api/chat` — thân `{"messages":[{"role":"user|assistant","content":"…"}]}` (tin cuối phải của khách). Đăng nhập tùy chọn (`Authorization: Bearer`). Lỗi: 400 (tin cuối không phải của khách/rỗng), 422 (sai định dạng), 429.

## Kiểm thử
`tests/test_chatbot.py` — 31 test, Gemini giả có kịch bản (`tests/fake_ai.py: chat_script`), không tốn hạn mức: mã giảm giá chỉ gồm mã còn hiệu lực (loại hết hạn/chưa bắt đầu/đã tắt), chính sách dùng số thật từ config, khách không xem được đơn người khác, model không nhận địa chỉ/SĐT, đổi trả (đã giao/chưa giao/quá hạn) chỉ **đề xuất** và không tạo bản ghi, vòng công cụ vô hạn bị cắt, Gemini lỗi → dự phòng, đường nhanh không gọi model, timeout từng lần gọi, thought signature được gửi lại nguyên vẹn, chính sách thử model dự phòng của client.
Đã kiểm chứng tay với Gemini thật (2026-11-03): định dạng function-calling đúng (có `id` và `thoughtSignature`), câu hỏi mở gợi ý đúng "Laptop Pro 14 — 21.500.000đ" từ CSDL; E2E trình duyệt (Chrome): desktop và mobile 390 px, đăng nhập khách An thấy đúng đơn của mình, không lỗi console.

## Giới hạn đã biết
- Chưa có giá giảm theo sản phẩm; chưa có quy trình đổi trả đầy đủ (xem trên).
- Câu hỏi mở qua Gemini free tier chậm (15–35 s) và đôi khi timeout → bộ luật trả lời kém tinh tế hơn. Dùng gói có trả phí hoặc model nhanh hơn sẽ giảm đáng kể (`GEMINI_TEXT_MODEL`).
- Bộ luật chỉ nhận ý định bằng từ khóa; chưa nhớ ngữ cảnh ngoài trường hợp "khách vừa được hỏi mã đơn rồi gõ số".
- Chưa có giọng nói/ảnh trong chat (tìm kiếm AI đã có riêng), chưa có chuyển cuộc trò chuyện cho nhân viên theo thời gian thực — chỉ tạo yêu cầu hỗ trợ.
- Không đo chất lượng hội thoại có hệ thống (chưa có bộ câu hỏi chuẩn); không có thống kê sử dụng chatbot (chủ ý: không lưu tin nhắn).
