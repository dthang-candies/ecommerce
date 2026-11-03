# UniCart — sàn thương mại điện tử (đồ án PTTK HTTT, PTIT)

**Stack:** React 19 + TypeScript + Tailwind CSS 4 (Vite) · FastAPI + SQLAlchemy 2 (Python 3.11+) · MySQL 8.
Kiến trúc 4 tầng theo báo cáo (`PTTK_HTTT (2).pdf`, mục 4.4): presentation → business → persistence → MySQL, domain dùng chung.
Tài liệu: `docs/` (phân tích, kế hoạch, kiến trúc, CSDL, API, test, tiến độ).

## Cài đặt & chạy
```bash
# 1. Backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env            # điền DATABASE_URL, JWT_SECRET, PARTNER_SECRET, GEMINI_API_KEY (tùy chọn)

# 2. CSDL — CSDL MỚI: tạo bằng schema.sql (cảnh báo: có DROP DATABASE unicart)
mysql -u root -p < sql/schema.sql
#    CSDL ĐÃ CÓ dữ liệu: KHÔNG chạy schema.sql, chỉ nâng cấp cộng thêm:
python -m unicart.migrate
python -m unicart.seed          # mật khẩu mẫu + dữ liệu demo (idempotent), mật khẩu: Abc@12345
python -m unicart.import_catalog  # (tùy chọn) 189 sản phẩm có ảnh, tiếng Việt

# 3. Frontend
cd frontend && npm install && npm run build && cd ..

# 4. Chạy (API + giao diện đã build): http://127.0.0.1:8000   (Swagger: /docs)
python -m unicart.main
```
Phát triển giao diện với hot reload: chạy API như trên, rồi `cd frontend && npm run dev` → http://localhost:5173 (proxy `/api` sang :8000).

## Tài khoản demo (mật khẩu `Abc@12345`)
| Email | Vai trò |
|---|---|
| an@gmail.com, binh@gmail.com, chi@/dung@/em@gmail.com | Khách hàng |
| admin@abc.vn | Quản trị (sản phẩm, danh mục, khuyến mại, tài khoản) |
| service@abc.vn | Xử lý đơn (xác nhận/hủy) |
| warehouse@abc.vn | Kho (đóng gói, tồn kho, nhập hàng, mô phỏng vận chuyển/NCC) |
| sales@abc.vn | Hỗ trợ khách hàng |
| marketing@abc.vn | Khuyến mại, hiệu quả gợi ý AI |
| manager@abc.vn | Báo cáo kinh doanh, hiệu quả AI, kho |

Thanh toán online dùng cổng sandbox: số thẻ kết thúc `0000` bị từ chối, còn lại thành công. Số thẻ không bao giờ gửi lên máy chủ.

## Dữ liệu sản phẩm
`python -m unicart.import_catalog` nhập 189 sản phẩm (10 danh mục, tên tiếng Việt, ảnh thật trong `images/products/`) từ `data/catalog.json`. Nguồn là DummyJSON (dữ liệu mẫu công khai), **không** phải Shopee — xem `docs/DATA_SOURCES.md` để biết lý do, giá quy đổi và lưu ý bản quyền.

## Tìm kiếm AI (văn bản · giọng nói · hình ảnh)
Dùng Google Gemini API miễn phí ([lấy khóa](https://aistudio.google.com/apikey), điền `GEMINI_API_KEY` vào `.env`). Có khóa: ô tìm kiếm hiểu câu tự nhiên ("giày chạy bộ màu đen dưới 1 triệu"), tự sửa chính tả, có nút 🎤 và 📷. Không có khóa hoặc Gemini lỗi: tự về tìm từ khóa. Lần khởi động đầu tự tạo vector sản phẩm (vài giây). Chi tiết, giới hạn và lưu ý riêng tư: `docs/AI_SEARCH.md`.

## Chatbot hỗ trợ người mua
Nút "Hỏi trợ lý" ở góc phải mọi trang: mã giảm giá đang hiệu lực hôm nay, gợi ý sản phẩm, tra cứu đơn hàng của chính khách, hướng dẫn đổi trả (soạn sẵn yêu cầu hỗ trợ, khách bấm Gửi mới tạo). Câu ngắn trả lời tức thì bằng bộ luật; câu mở dùng Gemini (function-calling) và tự về bộ luật khi AI chậm/lỗi hoặc chưa có khóa. Trợ lý chỉ đọc dữ liệu, không tự hủy/đổi/hoàn tiền. Thiết kế, giới hạn và lưu ý: `docs/CHATBOT.md` (chính sách đổi trả 7 ngày là chính sách mẫu, chỉnh trong `business/extended/chat_policy.py`).

## Kiểm thử
```bash
export TEST_DB_USER=root TEST_DB_PASSWORD=...     # hoặc đặt trong .env; dùng CSDL riêng unicart_test
pytest -v                                         # 131 test trên MySQL thật (Gemini được giả lập, không tốn hạn mức)
cd frontend && npm run typecheck && npm run build
```
E2E trình duyệt: xem đầu `tests/e2e/run.mjs` (Playwright, cài ngoài dự án).

## Phạm vi
Giai đoạn 1 (UC-01…15, 21…26) cài đầy đủ; Giai đoạn 2: ghi log, gợi ý hybrid, báo cáo CTR/Add-to-Cart/Conversion, và tìm kiếm AI đa phương thức (văn bản, giọng nói, hình ảnh). Chatbot hỗ trợ người mua (UC-18/19) đã cài ở dạng đọc-chỉ, xem `docs/CHATBOT.md`. Chi tiết và giới hạn: `docs/PROJECT_ANALYSIS.md`, `docs/PROGRESS.md`.
