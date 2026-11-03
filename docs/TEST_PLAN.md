# Kế hoạch & kết quả kiểm thử

| Lớp | Công cụ | Phạm vi | Cách chạy |
|---|---|---|---|
| Domain | pytest | 7 test quy tắc một đối tượng (giỏ, khuyến mại, trạng thái, phí ship…) | `pytest` |
| Tích hợp API | pytest + FastAPI TestClient + **MySQL thật** (`unicart_test` dựng lại từ `schema.sql` cho từng test) | 16 test gốc (tồn kho, rollback, đồng thời, hủy/hoàn kho, idempotent, hết hạn 15 phút, RBAC) + 26 test chức năng + 20 test tìm kiếm AI (Gemini giả xác định: đồng bộ chỉ mục, xếp hạng, lọc giá, tự sửa chính tả, dự phòng khi AI lỗi, ảnh/giọng nói: magic bytes, giới hạn kích thước, rate limit, không lưu dữ liệu) | `pytest` |
| Catalogue & ảnh | pytest | nhập idempotent, không ghi đè dữ liệu admin, ảnh thiếu không tạo link hỏng, file `catalog.json` hợp lệ (SKU/tên duy nhất, ảnh thật tồn tại, không còn tên thực phẩm tiếng Anh), phục vụ `/images` và chặn path traversal | `pytest` |
| Chatbot | pytest, Gemini giả có kịch bản | 31 test: mã giảm giá hôm nay, cô lập đơn giữa khách, không gửi địa chỉ/SĐT cho model, đổi trả chỉ đề xuất, vòng công cụ bị chặn, dự phòng, đường nhanh, timeout | `pytest tests/test_chatbot.py` |
| Phân tích truy vấn | pytest | 24 ca giá/màu/thương hiệu/size/từ đệm tiếng Việt & Anh | `pytest` |
| Kiểu dữ liệu FE | `tsc` (strict, noUnused*) | toàn bộ `frontend/src` | `npm run typecheck` |
| Build | Vite | bản production | `npm run build` |
| E2E trình duyệt | Playwright/Chromium headless | hành trình đầy đủ: đăng ký → tìm kiếm (không dấu, gõ sai) → giỏ → địa chỉ → mã giảm → thanh toán online (thẻ bị từ chối rồi thành công) → nhân viên xác nhận/đóng gói/giao → đánh giá → hỗ trợ → báo cáo; chặn quyền; mobile 390px không tràn ngang; không lỗi console/5xx | `tests/e2e/run.mjs` |

## Kết quả lần chạy cuối (pytest, tsc, build: 2026-11-03; E2E gốc: 2026-10-28)
- `pytest`: **131 passed** (7 domain + 16 API gốc + 26 chức năng + 45 tìm kiếm AI/parser + 6 nhập catalogue/ảnh + 31 chatbot). Chạy lần cuối 2026-11-03.
- `tsc --noEmit`: 0 lỗi (đã kiểm chứng bằng lỗi cố ý rằng nó thực sự bắt lỗi). `npm run build`: thành công (JS 440 kB / 126 kB gzip).
- E2E: 21/21 bước đạt, không có lỗi console, page error hay HTTP 5xx.

- Gemini thật (không tính vào pytest để khỏi tốn hạn mức): chạy tay trên catalogue demo — 18 truy vấn văn bản (~400 ms), 6 ảnh sản phẩm, 2 đoạn giọng nói (vi/en) đều đúng; E2E trình duyệt `tests/e2e/ai.mjs` đạt (nút micro/camera, chip "Hiểu là", tự sửa chính tả, tìm bằng ảnh tải lên, tìm bằng giọng nói với micro giả, mobile).

## Chưa kiểm thử / giới hạn
- Chất lượng tìm kiếm AI mới được đo trên 27 sản phẩm demo, chưa có bộ truy vấn chuẩn/đánh giá nDCG; kết quả Gemini có thể đổi theo thời điểm (đã thấy một lần nghe nhầm "giày" thành "dài").
- Không có test tải (NFR-01/02/10/11 chưa đo); không đo SLA 99,9% (NFR-08); HTTPS (NFR-04) do hạ tầng triển khai cung cấp, chưa cấu hình.
- Chưa kiểm thử trên Safari/Firefox, chưa kiểm thử trình đọc màn hình (chỉ áp dụng nhãn ARIA, focus-visible, modal Esc).
- E2E tạo dữ liệu thật trong CSDL dev (khách `e2e…@example.com`, đơn hàng) và cần chạy tay.
