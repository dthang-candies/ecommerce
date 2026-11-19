# Thiết kế cơ sở dữ liệu

Theo mục 4.2 của báo cáo: 21 bảng, cộng `product_embedding` cho tìm kiếm AI và 4 bảng con của `product` (kế thừa) và `password_reset` (quên mật khẩu) = 27 bảng. MySQL 8, `DECIMAL(12,2)` cho tiền, bảng con cho thuộc tính riêng của từng loại sản phẩm (JSON cho thuộc tính tự do còn lại), ràng buộc CHECK/UNIQUE/FK cài trực tiếp quy tắc nghiệp vụ (xem `sql/schema.sql`).

| Nhóm | Bảng |
|---|---|
| Tài khoản | `role`, `account`, `customer` (id = FK account), `address` |
| Danh mục & kho | `category`, `product`, `inventory`, `stock_movement`, `promotion` |
| Kế thừa sản phẩm | `book`, `electronics`, `fashion`, `furniture` (PK = FK `product.id`, ON DELETE CASCADE) |
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
| Bảng mới `password_reset` | liên kết đặt lại mật khẩu dùng một lần: chỉ lưu SHA-256 của mã, hạn dùng, thời điểm đã dùng |
| Bảng mới `book`, `electronics`, `fashion`, `furniture` | kế thừa Product: thuộc tính riêng của từng loại sản phẩm có cột và kiểu dữ liệu rõ ràng (xem mục dưới) |

Áp cho CSDL đang có: `python -m unicart.migrate` (kiểm tra `information_schema`, chạy lại an toàn). CSDL mới: `schema.sql` đã gồm các thay đổi này.

`product.image_url` lưu đường dẫn tương đối tới ảnh trong thư mục `images/` của dự án (ví dụ `/images/products/dj-001.webp`) hoặc một URL tùy ý do admin nhập.

## Kế thừa sản phẩm

`Product` là lớp cha; mỗi lớp con là một bảng riêng (class-table inheritance). Dòng của bảng con dùng chung khóa với dòng `product` của nó: `product_id` vừa là khóa chính vừa là khóa ngoại tới `product(id)`, nên quan hệ là 1–1 và xóa sản phẩm thì dòng con tự mất (`ON DELETE CASCADE`).

| Bảng con | Cột (ngoài `product_id`) | Danh mục |
|---|---|---|
| `book` | `isbn`, `author`, `publisher`, `page_count`, `language` | Books |
| `electronics` | `brand`, `model_number`, `warranty_months` | Electronics |
| `fashion` | `size`, `color`, `material` | Clothes, Shoes |
| `furniture` | `material`, `width_cm`, `depth_cm`, `height_cm`, `weight_kg`, `assembly_required` | Nội thất & trang trí |

- **Kế thừa không toàn phần:** sản phẩm thuộc danh mục khác (Gia dụng, Phụ kiện, Thực phẩm…) không có dòng con, chỉ là `Product`.
- **Kiểu dữ liệu:** chuỗi là `VARCHAR(255)`, số là `INT`, `assembly_required` là `BOOLEAN`. Mọi cột của bảng con cho phép NULL vì dữ liệu nguồn không đủ.
- **Loại sản phẩm xác định theo tên danh mục**, không có cột phân loại riêng trong `product`. CSDL không tự chặn một sản phẩm có dòng ở hai bảng con; ứng dụng đảm bảo điều đó.
- **Đồng bộ:** hàm `sync_subtype` (`unicart/business/extended/catalog_service.py`) được gọi mỗi khi tạo hoặc sửa sản phẩm — từ trang quản trị, `unicart.seed` và `unicart.import_catalog`. Nó tạo hoặc cập nhật dòng con, và khi sản phẩm đổi danh mục thì xóa dòng ở bảng con cũ.
- **Nguồn giá trị:** các khóa trong `product.attributes`, nhận cả camelCase lẫn snake_case (`pageCount` hoặc `page_count`); cỡ giày `shoesSize` vào `fashion.size`. Khóa không gửi lên thì cột giữ giá trị cũ; số sai kiểu bị từ chối (400).
- **Lấy từ `product.brand`:** `electronics.brand` luôn chép từ đây; `book.publisher` lấy từ đây khi `attributes` không có `publisher`.
- **Bảo hành:** khi không có `warrantyMonths`, `electronics.warranty_months` quy đổi từ chuỗi `warranty` ("6 tháng" → 6, "2 năm" → 24, "Không bảo hành" → 0, "Trọn đời" → NULL).
- **`product.brand` và `product.attributes` được giữ lại:** tìm kiếm, gợi ý và chatbot vẫn đọc hai cột này, nên một số giá trị có ở cả `product` lẫn bảng con.
- **CSDL đang có:** `python -m unicart.migrate` tạo 4 bảng và đổ dữ liệu một lần từ các sản phẩm hiện có; chạy lại không tạo trùng.

## Lưu ý vận hành
- `schema.sql` bắt đầu bằng `DROP DATABASE IF EXISTS unicart` — **chỉ chạy cho CSDL mới**. Bộ test dùng riêng `unicart_test`.
- `python -m unicart.seed` idempotent: băm mật khẩu mẫu `Abc@12345`, thêm tài khoản `sales/marketing/manager@abc.vn`, 3 khách hàng, 3 danh mục, 27 sản phẩm có dấu, và (chỉ khi chưa có đơn nào) ~45 đơn lịch sử 30 ngày, đánh giá, log gợi ý.
- Chỉ mục: `idx_product_category`, `idx_product_name`, `idx_order_customer`, `idx_order_status`, `idx_log_customer`; truy vấn danh sách dùng `joinedload/selectinload` để tránh N+1.
- Múi giờ: máy chủ MySQL và ứng dụng cùng UTC+7 (NFR-18); thời gian lưu dạng DATETIME không múi giờ.
