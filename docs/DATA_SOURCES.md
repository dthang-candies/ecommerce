# Nguồn dữ liệu sản phẩm và ảnh

## Vì sao không lấy từ Shopee
Điều khoản sử dụng và `robots.txt` của Shopee không cho phép thu thập dữ liệu tự động; tên, mô tả và ảnh là nội dung có bản quyền của từng người bán; và trang này chặn bot bằng token chống bot/captcha — vượt qua lớp chặn đó là lách kiểm soát truy cập. Dự án **không** lấy dữ liệu từ Shopee hay bất kỳ sàn thương mại nào khác.

## Nguồn đang dùng: DummyJSON
[DummyJSON](https://dummyjson.com/) là API công khai tạo ra để làm dữ liệu giả cho thử nghiệm/prototype.
- Lấy 189/194 sản phẩm (bỏ nhóm `vehicle` — ô tô giá hàng tỷ đồng không hợp cửa hàng); 23 nhóm gốc gộp thành 10 danh mục tiếng Việt.
- **Tên và mô tả dịch sang tiếng Việt bằng Gemini** (giữ nguyên thương hiệu, mã model); các tên model dịch sai/để nguyên tiếng Anh đã sửa tay (`FIXES` trong `tools/fetch_catalog.py`).
- **Giá:** USD × 25.000 làm tròn (nghìn đồng, hoặc chục nghìn từ 1 triệu); chỉ là giá minh họa. Tồn kho lấy ngẫu nhiên từ nguồn (4 sản phẩm hết hàng để demo); ngưỡng cảnh báo 5.
- **Thuộc tính:** bảo hành, thời gian giao, đổi trả (đã Việt hóa); bỏ "bảo hành" cho thực phẩm và chăm sóc cá nhân vì dữ liệu nguồn vô nghĩa.
- **Ảnh:** 189 thumbnail `.webp` (~2 MB) lưu tại `images/products/dj-XXX.webp`, phục vụ ở `/images/products/…`; `product.image_url` lưu đường dẫn tương đối đó.
- Ứng dụng **không gọi DummyJSON khi chạy**: dữ liệu đã chốt trong `data/catalog.json` + `images/`.

## Quy trình
```bash
python tools/fetch_catalog.py          # (tùy chọn) dựng lại catalog.json + ảnh; cần GEMINI_API_KEY để dịch; chạy lại được
python -m unicart.import_catalog       # nhập vào MySQL: idempotent, không ghi đè sản phẩm đã có
python -m unicart.import_catalog --update-text   # chỉ cập nhật tên/mô tả của các dòng DJ-… do chính lần nhập này tạo
# khởi động lại server để tạo vector AI cho sản phẩm mới (gói free: ~100 embedding/phút, tự chờ khi gặp 429)
```
SKU dạng `DJ-001…DJ-194` (khớp id nguồn).

## Ảnh cho 34 sản phẩm mẫu cũ (`schema.sql` / `seed.py`)
`python tools/attach_sample_images.py` rồi `python -m unicart.import_catalog` (chỉ điền chỗ còn trống, không ghi đè `image_url` admin đã đặt). Kết quả ghi ở `data/sample_images.json`.
- **17 sản phẩm** dùng ảnh DummyJSON **cùng loại** (laptop, điện thoại, tai nghe, sạc dự phòng, áo, váy, giày, ba lô, đồng hồ, kính, cốc, sữa tắm), chọn một góc chụp khác với ảnh đã nhập. Ảnh có thể là thương hiệu khác với tên sản phẩm (ví dụ "Laptop Pro 14 – ABC" hiện ảnh Dell XPS): chỉ là ảnh minh họa cho demo.
- **5 cuốn sách** có bìa **SVG tự tạo** (tên sách, tác giả, nhà xuất bản), không dùng ảnh bìa thật.
- **12 sản phẩm chưa có ảnh** (chuột, màn hình, áo khoác gió, quần jeans, áo len, dép sandal, nồi chiên, máy hút bụi, chăn ga, kem chống nắng, máy sấy tóc, ví da) vì nguồn không có ảnh đúng loại; vẫn hiện biểu tượng theo danh mục. Gemini gói miễn phí không tạo được ảnh và Wikimedia Commons chặn truy cập tự động nên không dùng.

## Lưu ý bản quyền
Dữ liệu và ảnh của DummyJSON thuộc về chủ sở hữu tương ứng và được cung cấp cho mục đích thử nghiệm. Chỉ dùng cho đồ án học tập/demo; **không** dùng cho cửa hàng thật hoặc phát hành lại. Muốn dùng thật hãy thay bằng ảnh và dữ liệu bạn có quyền sử dụng (admin có thể sửa `image_url` từng sản phẩm).
