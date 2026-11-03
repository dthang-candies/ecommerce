# Tiến độ

| Phase | Trạng thái |
|---|---|
| 1 Audit repo & tài liệu | ✅ |
| 2 Phân tích & kiến trúc | ✅ |
| 3 Setup (FastAPI, Vite/React/TS/Tailwind) | ✅ |
| 4 DB & backend | ✅ migration, seed, 18 service |
| 5 Frontend | ✅ 12 trang khách + 8 trang nhân viên |
| 6 Tích hợp end-to-end | ✅ E2E trình duyệt đạt |
| 7 Test, debug, build | ✅ 49 pytest, tsc, build, E2E |
| 8 Tài liệu | ✅ |

## Tìm kiếm AI (Gemini) — đã xong
Search text ngữ nghĩa + giọng nói + hình ảnh, chi tiết ở `AI_SEARCH.md`. Đã thử và bỏ hướng chạy model cục bộ (torch/Whisper) theo yêu cầu.

## Chatbot hỗ trợ người mua (UC-18/19) — đã xong
Widget chat React + `POST /api/chat`: mã giảm giá hôm nay, gợi ý sản phẩm, tra cứu đơn (chỉ đơn của khách), hướng dẫn đổi trả. Gemini function-calling với 8 công cụ chỉ đọc, đường nhanh bằng bộ luật cho câu ngắn, dự phòng khi AI lỗi. 31 test mới (tổng 131). Chi tiết, số đo độ trễ và giới hạn: `CHATBOT.md`.

## Dữ liệu sản phẩm đa dạng + ảnh — đã xong
189 sản phẩm / 10 danh mục / ảnh thật trong `images/products/` từ DummyJSON (không phải Shopee, lý do ở `DATA_SOURCES.md`); tên và mô tả dịch bằng Gemini.

## Lỗi đã gặp và xử lý trong quá trình làm
- Method `list` che builtin trong annotation → `from __future__ import annotations`.
- Lọc trạng thái ở trang quản trị áp dụng sau phân trang (tổng sai) → đưa vào truy vấn.
- Xóa vật lý sản phẩm lỗi vì thiếu cascade tới `inventory` → cascade theo composition.
- Seed: thứ tự INSERT `cart`/`customer` (FK không mô hình hóa quan hệ) → `flush` giữa các bước.
- So khớp từ khóa theo chuỗi con khiến "ăn" khớp "nhẹ"/"Samsung" (truy vấn vô nghĩa trả 13 kết quả rác) → so khớp theo từ nguyên vẹn + test hồi quy.
- Ngưỡng liên quan tính trên phần còn lại sau khi lọc giá làm hàng nhiễu trồi lên → tính trên toàn catalogue.
- Màu "đỏ" bị nhầm với "đồ", "kem" (màu) với kem chống nắng → khớp màu trên chữ có dấu.
- Nhúng 189 sản phẩm một lúc làm Gemini free trả 429 và đồng bộ bỏ dở (chỉ mục không nạp lại dù DB đã lưu) → chờ-và-thử-lại theo khung quota + luôn nạp lại tiến độ đã lưu.
- Gemini dịch để nguyên tiếng Anh cả nhóm thực phẩm và hỏng vài tên → sửa tay + test chặn.
- Tailwind v4 không `@apply` class tự định nghĩa → `@utility`.

## Còn tồn đọng / ngoài phạm vi
- A/B test (Giai đoạn 2, thiết kế). UC-18/19 chatbot và FR-21/22/23 đã cài bằng Gemini. Chatbot chưa có giá giảm theo sản phẩm và quy trình đổi trả đầy đủ (xem `CHATBOT.md`).
- Đăng xuất chỉ xóa token phía client (JWT stateless, hết hạn sau 8 giờ); token lưu `localStorage` (cần CSP/HttpOnly cookie nếu triển khai công khai).
- Hoàn tiền đơn online đã hủy, kế toán, đa kho/đa tiền tệ (ngoài phạm vi theo 1.7.2).
- Khóa Gemini được dán vào cuộc trò chuyện để cấu hình: nên **thu hồi và tạo khóa mới** tại https://aistudio.google.com/apikey rồi cập nhật `.env`.
- Nhật ký quản trị chỉ ghi ra logger; tên danh mục mẫu (Books/Electronics/Clothes/Shoes) giữ tiếng Anh theo `schema.sql`.
- CSDL dev hiện có thêm dữ liệu từ lần chạy E2E (khách `e2e…@example.com` và 3 đơn).
- 12/34 sản phẩm mẫu gốc (chuột, màn hình, quần jeans, máy hút bụi…) vẫn hiện biểu tượng vì không có ảnh đúng loại; 17 dùng ảnh cùng loại (có thể khác thương hiệu) và 5 sách dùng bìa SVG tự tạo. Mọi ảnh là dữ liệu mẫu, không dùng cho bán thật.
