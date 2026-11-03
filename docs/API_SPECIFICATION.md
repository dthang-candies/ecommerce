# Đặc tả API

Base: `/api`. Tài liệu tương tác: `GET /docs` (Swagger) và `/openapi.json`. Xác thực: `Authorization: Bearer <token>`.
Lỗi: `{"error": "<CODE>", "message": "<tiếng Việt>"}` — 400 BUSINESS_ERROR/VALIDATION, 401 UNAUTHENTICATED, 403 FORBIDDEN, 404 NOT_FOUND, 409 OUT_OF_STOCK/INVALID_TRANSITION/CONFLICT, 422 VALIDATION_ERROR (kèm `fields`), 413 PAYLOAD_TOO_LARGE, 415 UNSUPPORTED_MEDIA, 429 TOO_MANY_ATTEMPTS/TOO_MANY_REQUESTS, 503 AI_UNAVAILABLE.
Danh sách phân trang: `{total, page, size, items}`. Tiền là số (VND).

| Nhóm | Phương thức & đường dẫn | Vai trò |
|---|---|---|
| Auth | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `POST /auth/change-password` | công khai / đã đăng nhập |
| Catalogue | `GET /categories`, `GET /products?q&category_id&min_price&max_price&sort&page&size` (kèm `suggestion`), `GET /products/{id}` (kèm đánh giá) | công khai |
| Tìm kiếm AI | `GET /search?q…` (kèm `mode`, `corrected`, `interpreted`), `GET /search/status`, `POST /search/image` (byte ảnh), `POST /search/voice` (byte âm thanh) — xem `AI_SEARCH.md`; `POST /admin/ai/reindex` (ADMIN) | công khai |
| Chatbot | `POST /chat` {messages:[{role,content}]} → `{reply, mode, degraded, suggestions, products, promotions, orders, actions}` — xem `CHATBOT.md` | công khai (đăng nhập để tra đơn) |
| Gợi ý & log | `POST /events`, `GET /recommendations/home`, `GET /recommendations/product/{id}`, `GET /recommendations/cart` | công khai (cart: CUSTOMER) |
| Hồ sơ | `GET/PUT /me/profile`, `GET/POST /me/addresses`, `PUT/DELETE /me/addresses/{id}` | CUSTOMER |
| Giỏ hàng | `GET /cart`, `POST /cart/items`, `PATCH/DELETE /cart/items/{product_id}` | CUSTOMER |
| Đặt hàng | `POST /checkout/quote`, `POST /orders`, `GET /orders`, `GET /orders/{id}`, `POST /orders/{id}/cancel`, `POST /orders/{id}/reviews` | CUSTOMER |
| Thanh toán | `POST /payments/orders/{id}/pay` (CUSTOMER, sandbox), `POST /payments/callback` (đối tác) | — |
| Hỗ trợ | `GET/POST /me/support-requests` (CUSTOMER); `GET /staff/support-requests`, `POST …/{id}/reply`, `POST …/{id}/resolve` (SALES, ADMIN) | — |
| Xử lý đơn | `GET /staff/orders`, `GET /staff/orders/{id}` (SERVICE, WAREHOUSE, SALES, ADMIN, MANAGER); `PATCH /orders/{id}/status` {CONFIRMED,CANCELLED → SERVICE; PACKED → WAREHOUSE} | — |
| Vận chuyển | `POST /shipping/callback` (đối tác), `POST /staff/sandbox/carrier/{order_id}` (WAREHOUSE, ADMIN, mô phỏng) | — |
| Kho | `GET /inventory`, `/inventory/low-stock`, `/inventory/summary`, `/inventory/{id}/movements` (WAREHOUSE, ADMIN, MANAGER); `POST /inventory/{id}/restock`, `PUT /inventory/{id}/threshold` (WAREHOUSE, ADMIN) | — |
| Nhập hàng | `GET /suppliers`, `GET/POST /restock-requests`, `POST /restock-requests/{id}/receive`, `POST /suppliers/callback` (đối tác), `POST /staff/sandbox/supplier/{id}` | WAREHOUSE, ADMIN |
| Quản trị | `/admin/products` (GET/POST/PUT, `POST …/visibility`, DELETE), `/admin/categories` (POST/PUT/DELETE), `/admin/promotions` (GET: ADMIN/MARKETING/MANAGER; ghi: ADMIN), `/admin/accounts` (GET/POST, `PATCH …/role`, `PATCH …/lock`), `GET /admin/roles` | ADMIN |
| Báo cáo | `GET /reports/business?start&end` (MANAGER, ADMIN); `GET /reports/recommendations` (MANAGER, MARKETING, ADMIN) | — |
| Hệ thống | `GET /health` | công khai |

Webhook đối tác gửi header `X-Partner-Secret` (biến `PARTNER_SECRET`).
Quy ước gợi ý: `keyword` của sự kiện `REC_IMPRESSION`/`CLICK_REC` là vị trí (`home|product|cart`); `ADD_TO_CART`/`PURCHASE` có `rec:<vị trí>` nếu xuất phát từ gợi ý.
