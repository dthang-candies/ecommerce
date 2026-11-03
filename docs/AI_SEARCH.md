# Tìm kiếm AI (text · giọng nói · hình ảnh)

Cài đặt phần "Multi-Modal Search" của Chương 3 (FR-20…FR-23, UC-03 `<<extend>>`) bằng **Google Gemini API (gói miễn phí)**. Không chạy model cục bộ nên không cần GPU và không tải model về máy.

## Mô hình dùng và lý do (đã đo trên catalogue demo)
| Việc | Model | Ghi chú |
|---|---|---|
| Hiểu ngữ nghĩa văn bản | `gemini-embedding-001` (768 chiều) | Đã so với `gemini-embedding-2`: bản `-2` sai ở "áo mặc mùa đông", "ao khoac"; bản `-001` đúng cả hai. |
| Nhận diện ảnh, chép giọng nói | `gemini-flash-lite-latest` (dự phòng `gemini-3.5-flash-lite`) | ~2 s cho ảnh và âm thanh, đúng cả tiếng Việt lẫn tiếng Anh. `gemini-2.5-flash` đã bị Google đóng với key mới; `gemini-flash-latest` hay quá tải (503/chậm). |

## Luồng xử lý
```
text  ─────────────────────────────┐
voice ─ Gemini chép lời ───────────┤→ query_parser (giá, thương hiệu, màu, size, từ đệm)
image ─ Gemini nhận diện sản phẩm ─┘        │
                                            ▼
              embed câu truy vấn (cache LRU) → cosine với vector sản phẩm (MySQL → bộ nhớ)
                                            ▼
        điểm = 0.8·ngữ nghĩa + 0.2·từ khóa (từ nguyên vẹn) + thưởng thương hiệu/màu/size
                                            ▼
        lọc cứng theo giá/danh mục → sắp xếp → phân trang   (hết hàng bị xếp thấp, không bị ẩn)
```
- **Bộ phân tích truy vấn** (`unicart/business/extended/ai/query_parser.py`, không gọi mạng): "dưới 300 nghìn", "từ 10 triệu đến 20 triệu", "khoảng 2tr", "một triệu rưỡi", "1,5 triệu trở xuống", "under 500k"; màu (phân biệt "đỏ" với "đồ", "kem" màu với kem chống nắng); `size 42`; bỏ phần đệm "tôi muốn tìm…".
- **Tự sửa chính tả (FR-20):** khi không có kết quả mà có từ sản phẩm gần giống ("laptp" → "Laptop") thì tìm lại với từ đã sửa, báo cho người dùng và cho phép tìm đúng từ gốc. Gõ không dấu ("giay chay bo") không bị coi là lỗi.
- **Ngưỡng liên quan** (`business/extended/search_service.py`) hiệu chỉnh bằng cosine thật: sản phẩm không liên quan nằm quanh 0,60–0,64, đúng ≥ 0,67. Nếu kết quả tốt nhất < 0,655 thì không trả gì ("xyz asdf", "đồ ăn vặt", "xe ô tô" → rỗng). Ngưỡng tính trên **toàn bộ catalogue trước khi lọc giá**, để khi hàng đúng bị loại bởi giá thì hàng nhiễu không trồi lên.
- **Chỉ mục vector:** bảng `product_embedding` (22 bảng). Khi khởi động chỉ nạp từ MySQL; tác vụ nền chỉ nhúng sản phẩm mới hoặc đã đổi nội dung (băm MD5). Admin tạo/sửa/xóa sản phẩm sẽ kích hoạt cập nhật nền; `POST /api/admin/ai/reindex` để chạy tay; `python -m unicart.migrate` tạo bảng cho CSDL cũ.

## Dự phòng khi AI lỗi (NFR-12)
Hết hạn mức, mất mạng, timeout 2 s hoặc chưa có key → tìm theo từ khóa như cũ, phản hồi có `mode: "keyword"` (và `degraded: true` nếu AI đang bật nhưng lỗi); giao diện báo "tìm kiếm thông minh tạm thời không khả dụng". Ảnh/giọng nói không có phương án từ khóa nên trả 503 kèm thông báo rõ. Nếu một client vượt ngân sách (60 tìm chữ, 10 ảnh, 10 giọng nói mỗi phút) thì tìm chữ tự chuyển sang từ khóa, ảnh/giọng nói trả 429 — bảo vệ hạn mức miễn phí dùng chung.

## API
`GET /api/search?q&category_id&min_price&max_price&sort(relevance|…)&page&size&autocorrect` · `GET /api/search/status` · `POST /api/search/image` (thân = byte ảnh JPEG/PNG/WebP ≤ 4 MB) · `POST /api/search/voice` (thân = byte WAV/MP3/OGG/FLAC/AIFF ≤ 3 MB) · `POST /api/admin/ai/reindex`.
Phản hồi tìm kiếm có `mode`, `degraded`, `corrected`, `suggestion`, `interpreted` (giá/thương hiệu/màu/size đã hiểu), `recognized` (ảnh), `items[].score`.

## Giao diện
Nút 🎤 và 📷 trong ô tìm kiếm (chỉ hiện khi AI bật). Giọng nói: ghi tối đa 12 s bằng `MediaRecorder`, đổi sang WAV 16 kHz mono ngay trên trình duyệt (mọi trình duyệt đều tạo được, Gemini nhận được). Ảnh: chọn / kéo thả / dán / chụp, thu nhỏ ≤ 1024 px JPEG (không gửi kèm EXIF/vị trí). Trang kết quả hiển thị huy hiệu "Tìm kiếm AI", các chip "Hiểu là: …" và thông báo tự sửa.

## Quyền riêng tư (mục 3.5.2)
Ảnh và âm thanh chỉ xử lý trong bộ nhớ rồi bỏ, không ghi đĩa, không ghi log, không lưu CSDL (có test). Khóa API chỉ nằm trong header `x-goog-api-key`, không vào URL/log. **Gói miễn phí của Google có thể dùng dữ liệu gửi lên để cải thiện sản phẩm của họ** — giao diện đã nói rõ khi dùng ảnh/giọng nói; không nên dùng ảnh hoặc giọng nói có thông tin cá nhân. Tìm bằng chữ gửi câu truy vấn và nội dung mô tả sản phẩm tới Gemini.

## Giới hạn đã biết
- Cosine của embedding dồn trong dải hẹp nên không thể tách "liên quan" và "nhiễu" tuyệt đối: một số truy vấn mơ hồ ("đồ để chạy bộ") vẫn có 1–2 kết quả thứ yếu ở cuối.
- Tìm bằng ảnh dựa vào mô tả của Gemini rồi so khớp với **văn bản** sản phẩm, không so ảnh với ảnh (catalogue demo chưa có ảnh thật); ảnh sản phẩm lạ hoặc quá đặc thù có thể không khớp, khi đó hệ thống thử lại bằng loại sản phẩm chung.
- Gemini gói miễn phí đôi lúc chậm hoặc 503; mỗi lần gọi chờ tối đa 12 s rồi thử model dự phòng, nên ảnh/giọng nói có thể mất tới ~25 s trong trường hợp xấu.
- So khớp vector bằng Python thuần O(số sản phẩm × 768): ~vài chục ms cho vài trăm sản phẩm; cần chỉ mục ANN nếu catalogue lên hàng chục nghìn.
- Chatbot đã có riêng (`CHATBOT.md`). Chưa có tìm kiếm theo ảnh chụp lại nhiều sản phẩm một lúc, và A/B test (đã ghi ở `PROGRESS.md`).
