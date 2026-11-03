# Kiến trúc

```
React SPA (Vite, Tailwind)  ──REST/JSON + Bearer JWT──▶  FastAPI
                                                          presentation/  routers (controller), schemas, serializers, deps (JWT, RBAC)
                                                              │ gọi
                                                          business/      *_service (1 method công khai = 1 transaction, @transactional)
                                                              │ gọi
                                                          persistence/   repositories (chỉ tầng này chứa truy vấn)
                                                              │
                                                          MySQL 8 (InnoDB)         domain/  models + enums (không phụ thuộc tầng nào)
```
Quy tắc phụ thuộc theo 4.4.3: Presentation → Business → Persistence → MySQL; Controller không gọi Repository; lỗi nghiệp vụ là `BusinessError` → mã HTTP (400/401/403/404/409/429).

## Quyết định chính
- **Không bán vượt tồn (NFR-15):** `UPDATE inventory SET quantity = quantity - :q WHERE quantity >= :q`, khóa dòng theo thứ tự `product_id`, rollback toàn bộ khi một dòng hết hàng; có test 6 luồng tranh 3 sản phẩm cuối.
- **Giá chốt (BR-05):** `order_item.unit_price`, địa chỉ chụp lại vào đơn; giỏ luôn lấy giá hiện tại.
- **Vòng đời đơn (BR-07/08):** `OrderStatusPolicy` quyết định *ai* chuyển trạng thái nào; mỗi lần chuyển ghi `order_status_history`; hủy hoàn kho.
- **Hết hạn thanh toán (BR-04):** tác vụ nền trong `lifespan` quét mỗi 30 giây (`EXPIRY_SWEEP_SECONDS`), và `pay()` tự kiểm tra trước khi thanh toán. Máy chủ trả `pay_seconds_left` để đồng hồ đếm ngược không phụ thuộc múi giờ trình duyệt.
- **Thanh toán idempotent (UC-07 A3):** `payment.transaction_id` UNIQUE + kiểm tra trước khi áp dụng.
- **Đối tác:** adapter sandbox trong `business/integrations.py`; webhook `/api/payments|shipping|suppliers/callback` yêu cầu `X-Partner-Secret` (so sánh hằng thời gian).
- **Bảo mật:** JWT + tra DB mỗi request (khóa tài khoản tức thì); RBAC `require_roles` ở mọi endpoint riêng tư; chống dò mật khẩu (8 lần sai / 5 phút / email+IP → 429); thông báo đăng nhập sai không lộ email tồn tại; khách không xem được đơn người khác (404); `LIKE` thoát ký tự đặc biệt; không lưu số thẻ.
- **Tìm kiếm tiếng Việt:** collation `utf8mb4_unicode_ci` cho phép "ao khoac" khớp "Áo khoác"; gợi ý chính tả dùng `difflib` trên tên/thương hiệu đã bỏ dấu.
- **Gợi ý (3.3):** `score = α·CF + (1-α)·CB (+ độ phổ biến, độ mới)`; α = min(0.8, số tương tác / 25) nên khách mới dùng "bán chạy/mới"; luôn loại hàng ẩn/hết (FR-25). Tính trong bộ nhớ trên tối đa 500 sản phẩm còn hàng — đủ cho quy mô đồ án, cần chỉ mục/ANN nếu catalogue lớn.
- **Cá nhân hóa tắt được (NFR-13):** công tắc ở trang Tài khoản; khi tắt, trình duyệt không gửi sự kiện và gợi ý không dùng lịch sử.
- **Frontend:** `useFetch` (bỏ qua phản hồi cũ), Context cho Auth/Cart/Toast/Prefs, 401 tự đăng xuất, route guard theo vai trò (máy chủ vẫn kiểm tra lại).
- **Chatbot:** `business/chat_service.py` (Gemini function-calling hoặc bộ luật `chat_rules.py`) + `chat_tools.py` (8 công cụ chỉ đọc, danh tính lấy từ JWT). Model không có quyền ghi; yêu cầu hỗ trợ do khách xác nhận trên giao diện. Xem `CHATBOT.md`.
- **Tìm kiếm AI (Gemini):** gói `unicart/ai/` (client REST, bộ phân tích truy vấn, runtime giữ chỉ mục vector đồng bộ với MySQL) + `business/search_service.py`. Tách sau giao diện `AiRuntime` để có thể đưa ra thành vi dịch vụ riêng như 3.1.2; khi AI lỗi thì tự về tìm từ khóa (NFR-12). Xem `AI_SEARCH.md`.
