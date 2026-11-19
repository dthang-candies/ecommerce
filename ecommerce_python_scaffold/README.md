# E-commerce Python Scaffold

Bộ khung được dựng từ hai mô hình Visual Paradigm:
- `ClassDesgin.vpp`: mô hình miền (Customer, Product, Cart, Order, Payment, Shipment, các enum và lớp sản phẩm chuyên biệt).
- `Layer.vpp`: phân lớp Presentation / Business / Persistence / Domain, cùng các controller, service và repository.

## Cấu trúc

- `presentation/`: lớp điều khiển, nhận yêu cầu và gọi service.
- `business/`: xử lý nghiệp vụ, checkout, đơn hàng, thanh toán, tồn kho và tính giá.
- `persistence/`: repository và lớp Database ở dạng khung.
- `domain/`: entity, enum và lỗi nghiệp vụ.
- `main.py`: điểm khởi chạy thử.

## Cài đặt và chạy

```bash
python3 -m venv .venv
source .venv/bin/activate       # macOS/Linux
pip install -r requirements.txt
python main.py
```

Hiện tại đây là **skeleton**, không phải hệ thống hoàn chỉnh: repository đang dùng bộ nhớ tạm, các hàm nghiệp vụ quan trọng có `TODO`/`NotImplementedError`. Chưa có database thật, xác thực, giao diện web hoặc tích hợp cổng thanh toán.

## Các điểm cần rà soát trong mô hình gốc

1. `MovementTyoe`, `Inentoy`, `CarrtRepository`, `PromotionReposity`, `OrderReposity`, `PaymentReposity`, `BussinessError`, `Suplier` có tên/đánh máy chưa nhất quán. Bộ khung giữ tên miền chính dễ hiểu và ghi chú chỗ chuẩn hóa.
2. `ClassDesgin.vpp` có `CustomerVIP` và `CustomerNew`; chưa đủ thông tin quan hệ/kế thừa để tự quyết định cách triển khai. Hai lớp được giữ như biến thể độc lập.
3. `Layer.vpp` có một số lớp `Class7`, `Class9`, `R`, `Class20`, `Class21` chưa có thuộc tính/ngữ nghĩa rõ ràng nên không sinh lớp nghiệp vụ giả định.
4. Enum được lấy theo các literal có trong Class Design.
5. Các kiểu UML chưa xác định cụ thể được ánh xạ tạm sang `str`, `int`, `float` hoặc kiểu domain gần nhất; cần xác nhận lại trước khi kết nối CSDL.

## Quy ước

- Tên class Python dùng PascalCase.
- Tên thuộc tính và hàm dùng snake_case.
- Các method chưa có quy tắc nghiệp vụ để `TODO` thay vì tự suy diễn.
