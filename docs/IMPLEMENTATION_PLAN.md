# Kế hoạch triển khai

| Phase | Nội dung | Kết quả |
|---|---|---|
| 1 | Kiểm tra repo, đọc PDF (trích văn bản bằng PyMuPDF), đọc mã Flask mẫu | `PROJECT_ANALYSIS.md` |
| 2 | Phân tích yêu cầu, chọn kiến trúc, lập bảng bao phủ FR/UC | tài liệu này, `ARCHITECTURE.md` |
| 3 | Cài FastAPI/PyJWT/httpx, scaffold Vite + React + TS + Tailwind | `requirements.txt`, `frontend/` |
| 4 | Domain/persistence/business mới + migration + seed | 18 service, 17 repository |
| 5 | Presentation FastAPI (5 router, JWT, RBAC, lỗi tập trung, scheduler 15 phút) | 59 đường dẫn API |
| 6 | Frontend 12 trang khách + 8 trang nhân viên | `frontend/src` |
| 7 | Test: pytest (MySQL thật) + typecheck + build + E2E trình duyệt | `TEST_PLAN.md` |
| 8 | Tài liệu, README, hướng dẫn chạy | `docs/`, `README.md` |

## Thứ tự phụ thuộc
domain → persistence → business (auth → catalog → cart → checkout → payment → order/shipping → inventory/restock → support/review → report/AI) → routers → frontend (contexts → components → trang công khai → khách hàng → nhân viên).

## Bao phủ yêu cầu
| UC | Trạng thái | Nơi cài đặt |
|---|---|---|
| UC-01 Register, UC-26 Login/Logout | Xong | `auth_service`, `/api/auth/*`, `Auth.tsx` |
| UC-02/03/04 Duyệt, tìm, chi tiết | Xong (lọc danh mục, giá, sắp xếp, phân trang, "did you mean") | `product_service`, `Products.tsx`, `ProductDetail.tsx` |
| UC-05 Giỏ hàng | Xong | `cart_service`, `Cart.tsx` |
| UC-06 Check out (include Validate/Calculate) | Xong | `CheckoutService.quote/place_order`, `Checkout.tsx` |
| UC-07 Thanh toán online | Xong (sandbox) | `payment_service`, `Payment.tsx` |
| UC-08 Hồ sơ & địa chỉ | Xong | `customer_service`, `Account.tsx` |
| UC-09 Đánh giá | Xong | `review_service` |
| UC-10 Sản phẩm & danh mục | Xong | `catalog_service`, `staff/Catalogue.tsx` |
| UC-11 Khuyến mại | Xong | `promotion_service`, `staff/Promotions.tsx` |
| UC-12 Tồn kho | Xong | `inventory_service`, `staff/Inventory.tsx` |
| UC-13 Xử lý đơn | Xong | `order_service`, `staff/Orders.tsx` |
| UC-14 Cập nhật vận chuyển | Xong (webhook + mô phỏng) | `shipping_service` |
| UC-15 Báo cáo | Xong | `report_service`, `staff/Reports.tsx` |
| UC-21 Chuẩn bị đơn | Xong | `ShippingService.pack` |
| UC-22 Nhập hàng | Xong | `restock_service` |
| UC-23 Hỗ trợ khách | Xong | `support_service`, `Support.tsx`, `staff/SupportDesk.tsx` |
| UC-24 Tài khoản & vai trò | Xong | `account_service`, `staff/Accounts.tsx` |
| UC-25 Theo dõi/hủy đơn | Xong | `OrderDetail.tsx` |
| UC-16 Ghi log hành vi, UC-17 Gợi ý, UC-20 Hiệu quả gợi ý | Xong (tập con theo 1.7.2) | `interaction_service`, `recommendation_service`, `report_service` |
| UC-18 Chatbot, UC-19 Chatbot đơn hàng | Xong (chỉ đọc; đổi trả = soạn yêu cầu hỗ trợ) | `chat_service`, `chat_tools`, `chat_rules`, `ChatWidget.tsx` — `CHATBOT.md` |
| FR-21/22 ảnh & giọng nói; FR-23 ngữ nghĩa/thực thể | Xong bằng Gemini | `search_service`, `ai/` — `AI_SEARCH.md` |
