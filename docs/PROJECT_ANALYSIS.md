# Phân tích dự án UniCart

Nguồn: `PTTK_HTTT (2).pdf` (101 trang, báo cáo Phân tích & Thiết kế HTTT – ABC Online Shop, mã nguồn mẫu tên "UniCart"), `sql/schema.sql`, mã mẫu Flask đã có trong repo, và chỉ dẫn mới của chủ dự án về stack. Tài liệu gốc không bị sửa.

## 1. Xác nhận từ tài liệu
- B2C, web responsive, 11 quy tắc nghiệp vụ BR-01…BR-11, 34 FR, 18 NFR, 26 UC; vai trò RBAC: CUSTOMER, ADMIN, SERVICE, SALES, WAREHOUSE, MARKETING, MANAGER.
- **Giai đoạn 1 (cài đặt đầy đủ):** UC-01…UC-15, UC-21…UC-26. **Giai đoạn 2 (AI):** chỉ cài tập con: ghi log hành vi, sửa lỗi chính tả khi tìm kiếm, gợi ý cơ bản, lọc hàng hết; tìm bằng ảnh/giọng nói và chatbot ban đầu dừng ở mức thiết kế (mục 1.7.2); sau đó đã cài bằng Gemini (`AI_SEARCH.md`, `CHATBOT.md`).
- Kiến trúc 4 tầng Presentation → Business → Persistence → MySQL, Domain dùng chung; 21 bảng; trừ kho nguyên tử bằng UPDATE có điều kiện; mỗi service method = 1 transaction; đối tác thanh toán/vận chuyển là sandbox cùng hợp đồng dữ liệu.

## 2. Quyết định kỹ thuật (do người dùng chỉ định / tôi đề xuất)
| Nội dung | Quyết định | Lý do |
|---|---|---|
| Backend | **FastAPI** (tài liệu dùng Flask) | Người dùng yêu cầu. Giữ nguyên domain/persistence/business; chỉ viết lại Presentation (routers = controllers). |
| Frontend | **React + TypeScript + Tailwind** (Vite, react-router) | Người dùng yêu cầu; không thêm thư viện state/chart. |
| Xác thực | JWT HS256 (PyJWT) + kiểm tra tài khoản trong DB ở mỗi request | Thay xác thực giả bằng header (ghi chú ở 4.4.10/4.5.9). Khóa tài khoản có hiệu lực ngay. |
| Băm mật khẩu | PBKDF2-SHA256 240k vòng (stdlib) | NFR-03; bỏ phụ thuộc werkzeug/Flask. |
| Tìm kiếm AI | Google **Gemini API** (gói miễn phí): embedding + nhận diện ảnh + chép giọng nói | Người dùng yêu cầu dùng API Gemini; thay cho CNN/ANN/Speech-to-Text tự host ở 3.2.1. Chi tiết: `AI_SEARCH.md`. |
| Đối tác | `SandboxPaymentGateway`, `SandboxCarrier` + webhook có `X-Partner-Secret` | Phạm vi 1.7.2. Token kết thúc `0000` bị từ chối. |

## 3. Bổ sung / lệch so với tài liệu (có chủ ý)
1. `support_request.response` (TEXT): schema gốc không có chỗ lưu phản hồi, trong khi UC-23 yêu cầu "phản hồi gửi lại khách".
2. `EventType.REC_IMPRESSION`: công thức CTR (3.3) cần số lượt hiển thị, enum gốc không có.
3. Hai thay đổi trên được áp bằng `python -m unicart.migrate` (idempotent, không xóa dữ liệu) và đã ghi vào `schema.sql`.
4. Bảng `product_embedding` (ProductEmbedding, mục 3.6.2) lưu vector tìm kiếm AI.
5. `OrderItem.product` và cascade `Product → Inventory` (composition 4.3) được thêm vào domain.
6. Endpoint bổ sung ngoài bảng 4.5.6 (cần cho các UC): auth, hồ sơ/địa chỉ, quote, thanh toán sandbox, vận chuyển, nhập hàng, hỗ trợ, quản trị, báo cáo, AI (xem `API_SPECIFICATION.md`).

## 4. Mâu thuẫn trong tài liệu và cách xử lý
| Mâu thuẫn | Xử lý |
|---|---|
| Tên CSDL: `abc_shop` (4.4–4.5) / `ecommerce` (4.2.6) / `unicart` (schema.sql, README) | Dùng `unicart` (schema.sql là nguồn có thẩm quyền cho CSDL). |
| Số hiệu UC trong 4.4–4.5 (UC-05 Place order, UC-08 Track…) khác Chương 2 (UC-06 Check out, UC-25 Track/Cancel) | Dùng số hiệu Chương 2. |
| FR-15 "trừ kho khi đơn được xác nhận" vs BR-03/UC-06 "khi đơn được tạo" | Trừ khi tạo đơn (BR-03 + NFR-15 + mã mẫu); hoàn khi hủy/hết hạn. |
| 1.4.3 liệt kê trạng thái "Processing" | Dùng 7 trạng thái của BR-07. |
| 4.4.6 mô tả `POST /inventory/{id}/restock` nhập trực tiếp vs BR-11 (chỉ tăng khi yêu cầu được xác nhận) | Giữ endpoint như tài liệu (hàng đã về kho) nhưng giao diện dùng luồng yêu cầu nhập hàng → NCC xác nhận → nhập kho. |
| Dữ liệu mẫu `schema.sql` không dấu, danh mục tiếng Anh | Giữ nguyên; dữ liệu demo bổ sung có dấu (`seed.py`). |

## 5. Thông tin còn thiếu → giả định
- Định nghĩa "doanh thu": giả định doanh số ghi nhận = đơn từ PENDING đến DELIVERED; doanh thu đã giao = DELIVERED.
- Điểm thân thiết: 1 điểm/10.000đ của đơn đã giao; ≥200 điểm REGULAR, ≥1000 VIP (theo `Customer.add_points` mẫu).
- Phí vận chuyển: 30.000đ, miễn phí từ 500.000đ (config mẫu). Hoàn tiền đơn online đã thanh toán bị hủy nằm ngoài phạm vi (kế toán).
- Conversion (3.5) tính xấp xỉ: dòng hàng mua từ gợi ý / lượt hiển thị; chưa có A/B test.
- Nhật ký thao tác quản trị (NFR-17) ghi qua logger `unicart.audit`, không có bảng riêng vì schema không định nghĩa.
