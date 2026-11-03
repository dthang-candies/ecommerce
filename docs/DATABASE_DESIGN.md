# Thiết kế cơ sở dữ liệu

Theo mục 4.2 của báo cáo: 21 bảng (+1 bảng `product_embedding` cho tìm kiếm AI = 22), MySQL 8, `DECIMAL(12,2)` cho tiền, JSON cho thuộc tính sản phẩm, ràng buộc CHECK/UNIQUE/FK cài trực tiếp quy tắc nghiệp vụ (xem `sql/schema.sql`).

| Nhóm | Bảng |
|---|---|
| Tài khoản | `role`, `account`, `customer` (id = FK account), `address` |
| Danh mục & kho | `category`, `product`, `inventory`, `stock_movement`, `promotion` |
| Giỏ hàng | `cart` (UNIQUE customer), `cart_item` |
| Đơn hàng | `customer_order`, `order_item`, `order_status_history`, `payment`, `shipment` |
| Hỗ trợ & cung ứng | `review` (UNIQUE order+product, CHECK 1..5), `support_request`, `supplier`, `restock_request` |
| AI | `interaction_log`, `product_embedding` (vector float32 768 chiều, `content_hash` để chỉ nhúng lại khi nội dung đổi, FK ON DELETE CASCADE) |

## Thay đổi so với báo cáo (cộng thêm, không phá hủy)
| Thay đổi | Lý do |
|---|---|
| `support_request.response TEXT NULL` | lưu phản hồi nhân viên (UC-23) |
| `interaction_log.ck_log_event` thêm `REC_IMPRESSION` | tính CTR (công thức 3.3) |
| Bảng mới `product_embedding` | vector tìm kiếm ngữ nghĩa (mục 3.6.2 nêu thực thể ProductEmbedding) |

Áp cho CSDL đang có: `python -m unicart.migrate` (kiểm tra `information_schema`, chạy lại an toàn). CSDL mới: `schema.sql` đã gồm hai thay đổi.

`product.image_url` lưu đường dẫn tương đối tới ảnh trong thư mục `images/` của dự án (ví dụ `/images/products/dj-001.webp`) hoặc một URL tùy ý do admin nhập.

## Lưu ý vận hành
- `schema.sql` bắt đầu bằng `DROP DATABASE IF EXISTS unicart` — **chỉ chạy cho CSDL mới**. Bộ test dùng riêng `unicart_test`.
- `python -m unicart.seed` idempotent: băm mật khẩu mẫu `Abc@12345`, thêm tài khoản `sales/marketing/manager@abc.vn`, 3 khách hàng, 3 danh mục, 27 sản phẩm có dấu, và (chỉ khi chưa có đơn nào) ~45 đơn lịch sử 30 ngày, đánh giá, log gợi ý.
- Chỉ mục: `idx_product_category`, `idx_product_name`, `idx_order_customer`, `idx_order_status`, `idx_log_customer`; truy vấn danh sách dùng `joinedload/selectinload` để tránh N+1.
- Múi giờ: máy chủ MySQL và ứng dụng cùng UTC+7 (NFR-18); thời gian lưu dạng DATETIME không múi giờ.
