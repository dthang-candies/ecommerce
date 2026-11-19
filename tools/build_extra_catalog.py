"""Extra products for the four specialised groups of the data model: Book, Laptop, other Electronic (mobile, tablet,
accessories) and Shoes. Dev tool, run by hand:  python tools/build_extra_catalog.py

Writes data/catalog_extra.json (same format as data/catalog.json) and one generated SVG picture per product in
images/products/x-<sku>.svg (a book cover, or a plain card with the brand and name - no third-party photo is used).
`python -m unicart.import_catalog` then loads the file into MySQL.

Names are real titles / models; prices, stock and technical specifications are illustrative demo values.
Books sold in the original English edition carry that edition's ISBN; Vietnamese editions have none."""
from __future__ import annotations

import json
import random
import textwrap
import zlib
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent.parent
IMG, OUT = ROOT / "images" / "products", ROOT / "data" / "catalog_extra.json"
SOURCE = "unicart-extra"
EN, VI = "Tiếng Anh", "Tiếng Việt"

# title, author, publisher, price, isbn, pages, language, description
BOOKS = [
    ("The Pragmatic Programmer (20th Anniversary Edition)", "David Thomas, Andrew Hunt", "Addison-Wesley", 890000, "9780135957059", 352, EN,
     "Kinh nghiệm thực chiến giúp lập trình viên viết mã linh hoạt, dễ bảo trì."),
    ("Design Patterns: Elements of Reusable Object-Oriented Software", "Erich Gamma, Richard Helm, Ralph Johnson, John Vlissides", "Addison-Wesley", 1150000, "9780201633610", 395, EN,
     "23 mẫu thiết kế hướng đối tượng kinh điển của nhóm Gang of Four."),
    ("Refactoring (2nd Edition)", "Martin Fowler", "Addison-Wesley", 980000, "9780134757599", 448, EN,
     "Cải thiện thiết kế của mã nguồn hiện có qua từng bước tái cấu trúc an toàn."),
    ("Introduction to Algorithms (3rd Edition)", "Thomas H. Cormen, Charles E. Leiserson, Ronald L. Rivest, Clifford Stein", "MIT Press", 1890000, "9780262033848", 1312, EN,
     "Giáo trình thuật toán toàn diện, dùng rộng rãi ở các trường đại học."),
    ("Designing Data-Intensive Applications", "Martin Kleppmann", "O'Reilly Media", 1050000, "9781449373320", 616, EN,
     "Nguyên lý xây dựng hệ thống dữ liệu tin cậy, mở rộng được và dễ bảo trì."),
    ("Code Complete (2nd Edition)", "Steve McConnell", "Microsoft Press", 990000, "9780735619678", 960, EN,
     "Cẩm nang thực hành về xây dựng phần mềm chất lượng."),
    ("Head First Design Patterns", "Eric Freeman, Elisabeth Robson", "O'Reilly Media", 920000, "9780596007126", 694, EN,
     "Học mẫu thiết kế qua hình ảnh và ví dụ trực quan, dễ nhớ."),
    ("Domain-Driven Design", "Eric Evans", "Addison-Wesley", 1250000, "9780321125217", 560, EN,
     "Giải quyết độ phức tạp của phần mềm bằng mô hình miền nghiệp vụ."),
    ("Cracking the Coding Interview", "Gayle Laakmann McDowell", "CareerCup", 780000, "9780984782857", 687, EN,
     "189 câu hỏi phỏng vấn lập trình kèm lời giải chi tiết."),
    ("Artificial Intelligence: A Modern Approach (4th Edition)", "Stuart Russell, Peter Norvig", "Pearson", 2350000, "9780134610993", 1136, EN,
     "Giáo trình trí tuệ nhân tạo chuẩn mực cho sinh viên và người nghiên cứu."),
    ("Effective Java (3rd Edition)", "Joshua Bloch", "Addison-Wesley", 950000, "9780134685991", 416, EN,
     "90 lời khuyên để viết mã Java rõ ràng, đúng đắn và hiệu quả."),
    ("The Mythical Man-Month", "Frederick P. Brooks Jr.", "Addison-Wesley", 690000, "9780201835953", 336, EN,
     "Những tiểu luận kinh điển về quản lý dự án phần mềm."),
    ("Python Crash Course (2nd Edition)", "Eric Matthes", "No Starch Press", 720000, "9781593279288", 544, EN,
     "Nhập môn Python nhanh qua các dự án thực hành."),
    ("Fluent Python (2nd Edition)", "Luciano Ramalho", "O'Reilly Media", 1390000, "9781492056355", 1012, EN,
     "Khai thác các tính năng nâng cao để viết Python gọn gàng, hiệu quả."),
    ("Sapiens: A Brief History of Humankind", "Yuval Noah Harari", "Harper", 420000, "9780062316097", 464, EN,
     "Lược sử loài người từ thời săn bắt hái lượm đến kỷ nguyên công nghệ."),
    ("Atomic Habits", "James Clear", "Avery", 390000, "9780735211292", 320, EN,
     "Thay đổi nhỏ mỗi ngày để tạo nên thói quen tốt bền vững."),
    ("Thinking, Fast and Slow", "Daniel Kahneman", "Farrar, Straus and Giroux", 380000, "9780374533557", 499, EN,
     "Hai hệ thống tư duy chi phối cách con người phán đoán và ra quyết định."),
    ("Deep Work", "Cal Newport", "Grand Central Publishing", 360000, "9781455586691", 304, EN,
     "Quy tắc làm việc tập trung cao độ trong một thế giới đầy xao nhãng."),
    ("Zero to One", "Peter Thiel", "Crown Business", 340000, "9780804139298", 224, EN,
     "Ghi chép về khởi nghiệp và cách tạo ra những điều chưa từng có."),
    ("The Lean Startup", "Eric Ries", "Crown Business", 350000, "9780307887894", 336, EN,
     "Phương pháp khởi nghiệp tinh gọn: xây dựng, đo lường, học hỏi."),
    ("1984", "George Orwell", "Signet Classic", 190000, "9780451524935", 328, EN,
     "Tiểu thuyết phản địa đàng kinh điển về một xã hội bị giám sát toàn diện."),
    ("The Great Gatsby", "F. Scott Fitzgerald", "Scribner", 210000, "9780743273565", 180, EN,
     "Câu chuyện về giấc mơ Mỹ và nước Mỹ thập niên 1920."),
    ("Dế Mèn phiêu lưu ký", "Tô Hoài", "NXB Kim Đồng", 65000, None, None, VI,
     "Truyện đồng thoại nổi tiếng về chuyến phiêu lưu của chú Dế Mèn."),
    ("Tôi thấy hoa vàng trên cỏ xanh", "Nguyễn Nhật Ánh", "NXB Trẻ", 125000, None, None, VI,
     "Câu chuyện tuổi thơ trong trẻo ở một làng quê nghèo."),
    ("Mắt biếc", "Nguyễn Nhật Ánh", "NXB Trẻ", 110000, None, None, VI,
     "Mối tình đơn phương day dứt của Ngạn dành cho Hà Lan."),
    ("Cho tôi xin một vé đi tuổi thơ", "Nguyễn Nhật Ánh", "NXB Trẻ", 90000, None, None, VI,
     "Tấm vé trở về tuổi thơ dành cho những ai từng là trẻ con."),
    ("Số đỏ", "Vũ Trọng Phụng", "NXB Văn Học", 75000, None, None, VI,
     "Tiểu thuyết trào phúng đặc sắc của văn học Việt Nam hiện đại."),
    ("Truyện Kiều", "Nguyễn Du", "NXB Văn Học", 95000, None, None, VI,
     "Kiệt tác truyện thơ Nôm của đại thi hào Nguyễn Du."),
    ("Đất rừng phương Nam", "Đoàn Giỏi", "NXB Kim Đồng", 85000, None, None, VI,
     "Hành trình của cậu bé An giữa thiên nhiên và con người Nam Bộ."),
    ("Tắt đèn", "Ngô Tất Tố", "NXB Văn Học", 60000, None, None, VI,
     "Số phận người nông dân trước Cách mạng qua hình tượng chị Dậu."),
    ("Tuổi trẻ đáng giá bao nhiêu", "Rosie Nguyễn", "NXB Hội Nhà Văn", 99000, None, None, VI,
     "Chia sẻ về học tập, trải nghiệm và định hướng cho người trẻ."),
    ("Cà phê cùng Tony", "Tony Buổi Sáng", "NXB Trẻ", 105000, None, None, VI,
     "Những câu chuyện dí dỏm về cách sống và làm việc của người trẻ."),
    ("Dạy con làm giàu (Tập 1)", "Robert T. Kiyosaki", "NXB Trẻ", 115000, None, None, VI,
     "Bài học về tư duy tài chính qua câu chuyện cha giàu, cha nghèo."),
    ("Hoàng tử bé", "Antoine de Saint-Exupéry", "Nhã Nam", 79000, None, None, VI,
     "Chuyện về hoàng tử bé đến từ một tiểu tinh cầu, dành cho mọi lứa tuổi."),
    ("Lược sử thời gian", "Stephen Hawking", "NXB Trẻ", 135000, None, None, VI,
     "Vũ trụ học cho mọi người: từ Vụ nổ lớn đến lỗ đen."),
    ("Harry Potter và Hòn đá Phù thủy", "J.K. Rowling", "NXB Trẻ", 165000, None, None, VI,
     "Tập đầu tiên trong bộ truyện về cậu bé phù thủy Harry Potter."),
]

# name, brand, price, cpu, ram, storage, screen (inch), warranty (months), description
LAPTOPS = [
    ("Laptop Apple MacBook Air 13 M3", "Apple", 27990000, "Apple M3", "8GB", "256GB SSD", 13.6, 12, "Mỏng nhẹ, không quạt, pin dùng cả ngày."),
    ("Laptop Apple MacBook Pro 16 M3 Pro", "Apple", 64990000, "Apple M3 Pro", "18GB", "512GB SSD", 16.2, 12, "Màn hình Liquid Retina XDR, hiệu năng cho công việc chuyên nghiệp."),
    ("Laptop Dell XPS 15 9530", "Dell", 52990000, "Core i7-13700H", "16GB", "1TB SSD", 15.6, 12, "Thiết kế cao cấp, màn hình viền mỏng cho người sáng tạo nội dung."),
    ("Laptop Dell Inspiron 15 3520", "Dell", 13490000, "Core i5-1235U", "8GB", "512GB SSD", 15.6, 12, "Laptop văn phòng bền bỉ, giá hợp lý cho học tập."),
    ("Laptop Dell Latitude 7440", "Dell", 34900000, "Core i7-1365U", "16GB", "512GB SSD", 14.0, 36, "Dòng doanh nhân bảo mật cao, bảo hành 3 năm."),
    ("Laptop HP Pavilion 15", "HP", 17990000, "Core i5-1335U", "16GB", "512GB SSD", 15.6, 12, "Vỏ kim loại, đa dụng cho học tập và giải trí."),
    ("Laptop HP Envy x360 14", "HP", 26990000, "Ryzen 7 7730U", "16GB", "512GB SSD", 14.0, 12, "Xoay gập 360 độ, màn hình cảm ứng kèm bút."),
    ("Laptop HP Victus 16", "HP", 23490000, "Core i5-13500H", "16GB", "512GB SSD", 16.1, 12, "Laptop gaming tầm trung, màn hình 144Hz."),
    ("Laptop Lenovo ThinkPad X1 Carbon Gen 11", "Lenovo", 45990000, "Core i7-1355U", "16GB", "512GB SSD", 14.0, 36, "Siêu nhẹ, bàn phím ThinkPad trứ danh cho doanh nhân."),
    ("Laptop Lenovo IdeaPad Slim 5 14", "Lenovo", 18490000, "Ryzen 5 7530U", "16GB", "512GB SSD", 14.0, 24, "Mỏng nhẹ, pin bền, phù hợp sinh viên."),
    ("Laptop Lenovo Legion 5 Pro 16", "Lenovo", 38990000, "Ryzen 7 7745HX", "16GB", "1TB SSD", 16.0, 24, "Gaming hiệu năng cao, tản nhiệt tốt, màn hình 165Hz."),
    ("Laptop ASUS Vivobook 15", "ASUS", 12990000, "Core i5-1235U", "8GB", "512GB SSD", 15.6, 24, "Gọn nhẹ, đủ dùng cho văn phòng và học online."),
    ("Laptop ASUS ROG Strix G16", "ASUS", 41990000, "Core i7-13650HX", "16GB", "1TB SSD", 16.0, 24, "Chiến mọi tựa game với hệ thống tản nhiệt ROG."),
    ("Laptop ASUS TUF Gaming F15", "ASUS", 21990000, "Core i5-12500H", "16GB", "512GB SSD", 15.6, 24, "Độ bền chuẩn quân đội, gaming giá tốt."),
    ("Laptop Acer Aspire 7", "Acer", 16990000, "Core i5-12450H", "8GB", "512GB SSD", 15.6, 12, "Có card đồ họa rời, cân bằng giữa học tập và giải trí."),
    ("Laptop Acer Nitro 5", "Acer", 22490000, "Core i5-12500H", "16GB", "512GB SSD", 15.6, 12, "Laptop gaming quốc dân, dễ nâng cấp."),
    ("Laptop Acer Swift 3", "Acer", 17490000, "Core i5-1240P", "16GB", "512GB SSD", 14.0, 12, "Vỏ nhôm mỏng nhẹ, màn hình sắc nét."),
    ("Laptop MSI Modern 14", "MSI", 11990000, "Core i3-1215U", "8GB", "512GB SSD", 14.0, 24, "Nhỏ gọn, giá dễ tiếp cận cho nhu cầu cơ bản."),
    ("Laptop MSI Katana 15", "MSI", 27990000, "Core i7-13620H", "16GB", "1TB SSD", 15.6, 24, "Gaming mạnh mẽ, bàn phím đèn nền RGB."),
    ("Laptop LG Gram 16", "LG", 36990000, "Core i7-1360P", "16GB", "512GB SSD", 16.0, 12, "Màn hình 16 inch nhưng chỉ nặng khoảng 1,2 kg."),
]

# name, brand, price, screen (inch), storage, battery (mAh), description
MOBILES = [
    ("Điện thoại iPhone 15 128GB", "Apple", 19990000, 6.1, "128GB", 3349, "Dynamic Island, camera 48MP, cổng USB-C."),
    ("Điện thoại iPhone 15 Pro Max 256GB", "Apple", 31990000, 6.7, "256GB", 4441, "Khung titan, chip A17 Pro, zoom quang 5x."),
    ("Điện thoại Samsung Galaxy S24 Ultra 256GB", "Samsung", 28990000, 6.8, "256GB", 5000, "Bút S Pen, camera 200MP, tính năng Galaxy AI."),
    ("Điện thoại Samsung Galaxy Z Flip5 256GB", "Samsung", 19990000, 6.7, "256GB", 3700, "Màn hình gập nhỏ gọn, màn hình phụ lớn."),
    ("Điện thoại Xiaomi Redmi Note 13 Pro", "Xiaomi", 7490000, 6.67, "256GB", 5100, "Màn hình AMOLED 120Hz, camera 200MP, sạc nhanh."),
    ("Điện thoại Xiaomi 14", "Xiaomi", 22990000, 6.36, "512GB", 4610, "Flagship nhỏ gọn, ống kính Leica."),
    ("Điện thoại OPPO Reno11 F 5G", "OPPO", 8990000, 6.7, "256GB", 5000, "Thiết kế mỏng nhẹ, chụp chân dung đẹp."),
    ("Điện thoại OPPO Find N3 Flip", "OPPO", 22990000, 6.8, "256GB", 4300, "Điện thoại gập với cụm ba camera Hasselblad."),
    ("Điện thoại Vivo V30 5G", "Vivo", 11990000, 6.78, "256GB", 5000, "Màn hình cong, đèn Aura cho ảnh chân dung."),
    ("Điện thoại Realme 12 Pro+ 5G", "Realme", 10990000, 6.7, "256GB", 5000, "Camera tele tiềm vọng, mặt lưng da sang trọng."),
    ("Điện thoại Google Pixel 8", "Google", 16990000, 6.2, "128GB", 4575, "Android thuần, nhiếp ảnh điện toán, cập nhật lâu dài."),
    ("Điện thoại Nokia G22", "Nokia", 3490000, 6.52, "128GB", 5050, "Pin lớn, dễ tự sửa chữa, giá phổ thông."),
]

# sku prefix kind, name, brand, price, warranty (months), extra attributes, description
GADGETS = [
    ("tablet", "Máy tính bảng iPad Air 11 inch M2", "Apple", 16990000, 12, {"screenSize": 11, "storage": "128GB"}, "Chip M2 mạnh mẽ, hỗ trợ Apple Pencil Pro."),
    ("tablet", "Máy tính bảng Samsung Galaxy Tab S9 FE", "Samsung", 9990000, 12, {"screenSize": 10.9, "storage": "128GB"}, "Kèm bút S Pen, kháng nước IP68."),
    ("tablet", "Máy tính bảng Xiaomi Pad 6", "Xiaomi", 7990000, 18, {"screenSize": 11, "storage": "128GB"}, "Màn hình 144Hz, bốn loa, giá tốt."),
    ("audio", "Tai nghe chống ồn Sony WH-1000XM5", "Sony", 7490000, 12, {}, "Chống ồn hàng đầu, pin 30 giờ."),
    ("audio", "Tai nghe Apple AirPods Pro 2", "Apple", 5990000, 12, {}, "Chống ồn chủ động, âm thanh không gian, hộp sạc USB-C."),
    ("audio", "Tai nghe Bluetooth JBL Tune 520BT", "JBL", 1190000, 12, {}, "Âm bass JBL Pure Bass, pin 57 giờ."),
    ("audio", "Loa Bluetooth JBL Charge 5", "JBL", 3690000, 12, {}, "Chống nước IP67, pin 20 giờ, kiêm sạc dự phòng."),
    ("device", "Bàn phím cơ Keychron K2", "Keychron", 1890000, 12, {}, "Layout 75%, kết nối Bluetooth và có dây, dùng được cho Mac và Windows."),
    ("device", "Chuột không dây Logitech MX Master 3S", "Logitech", 2290000, 12, {}, "Cảm biến 8000 DPI, click êm, cuộn siêu nhanh."),
    ("device", "Màn hình gaming LG UltraGear 27GP850", "LG", 8490000, 24, {"screenSize": 27}, "Tấm nền Nano IPS 2K, tần số quét 165Hz."),
    ("device", "Ổ cứng SSD di động Samsung T7 1TB", "Samsung", 2590000, 36, {"storage": "1TB"}, "Nhỏ gọn, tốc độ đọc đến 1.050 MB/s."),
    ("device", "Webcam Logitech C920 HD Pro", "Logitech", 1790000, 24, {}, "Quay Full HD 1080p, micro kép cho họp trực tuyến."),
    ("device", "Smart TV Samsung Crystal UHD 55 inch", "Samsung", 12490000, 24, {"screenSize": 55}, "Độ phân giải 4K, hệ điều hành Tizen nhiều ứng dụng."),
    ("device", "Máy ảnh Sony Alpha a6400", "Sony", 21990000, 24, {}, "Máy ảnh không gương lật, lấy nét theo mắt nhanh và chính xác."),
    ("device", "Router Wi-Fi 6 TP-Link Archer AX55", "TP-Link", 1690000, 24, {}, "Wi-Fi 6 tốc độ AX3000, phủ sóng rộng cho gia đình."),
]

# name, brand, price, size, type, colour, material, description
SHOES = [
    ("Giày chạy bộ Nike Air Zoom Pegasus 40", "Nike", 3290000, 42, "running", "đen", "vải mesh", "Đệm Zoom Air êm ái cho các buổi chạy hằng ngày."),
    ("Giày Nike Air Force 1 '07", "Nike", 2890000, 41, "sneaker", "trắng", "da", "Mẫu sneaker trắng kinh điển, dễ phối đồ."),
    ("Giày chạy bộ Nike Revolution 7", "Nike", 1790000, 40, "running", "xanh navy", "vải mesh", "Nhẹ, êm, phù hợp người mới tập chạy."),
    ("Giày chạy bộ Adidas Ultraboost Light", "Adidas", 4500000, 42, "running", "trắng", "vải Primeknit", "Đệm Boost hoàn trả năng lượng, thân giày ôm chân."),
    ("Giày Adidas Stan Smith", "Adidas", 2500000, 40, "sneaker", "trắng xanh", "da", "Thiết kế tối giản huyền thoại từ sân quần vợt."),
    ("Giày Adidas Samba OG", "Adidas", 2700000, 41, "sneaker", "đen trắng", "da", "Phong cách retro đang được ưa chuộng."),
    ("Giày Puma Suede Classic XXI", "Puma", 2100000, 42, "sneaker", "đen", "da lộn", "Biểu tượng đường phố với chất liệu da lộn mềm."),
    ("Giày New Balance 574", "New Balance", 2390000, 41, "sneaker", "xám", "da lộn phối lưới", "Kiểu dáng cổ điển, đế ENCAP êm ái."),
    ("Giày New Balance 530", "New Balance", 2690000, 39, "sneaker", "trắng bạc", "vải lưới", "Phong cách chạy bộ thập niên 2000."),
    ("Giày Converse Chuck Taylor All Star cổ cao", "Converse", 1500000, 40, "sneaker", "đen", "vải canvas", "Đôi giày vải cổ cao kinh điển cho mọi phong cách."),
    ("Giày Vans Old Skool", "Vans", 1750000, 41, "sneaker", "đen trắng", "vải canvas phối da lộn", "Sọc Jazz đặc trưng, đế waffle bám tốt."),
    ("Giày chạy bộ Asics Gel-Kayano 30", "Asics", 4290000, 42, "running", "xanh dương", "vải mesh", "Hỗ trợ ổn định bàn chân cho quãng đường dài."),
    ("Giày thể thao Biti's Hunter X", "Biti's", 899000, 41, "sneaker", "đen cam", "vải dệt", "Đế LiteFlex siêu nhẹ, thương hiệu Việt."),
    ("Giày thể thao Biti's Hunter Street", "Biti's", 799000, 40, "sneaker", "trắng", "vải canvas", "Trẻ trung, năng động, giá học sinh sinh viên."),
    ("Giày vải Ananas Track 6", "Ananas", 990000, 41, "sneaker", "kem", "da tổng hợp", "Phong cách tối giản từ thương hiệu giày Việt."),
    ("Giày tây nam Oxford da bò", "Đông Hải", 1650000, 41, "formal", "nâu", "da bò", "Giày công sở lịch lãm, khâu đế chắc chắn."),
    ("Giày lười nam da thật", "Laforce", 1350000, 42, "loafer", "đen", "da bò", "Đi làm, đi tiệc đều hợp, dễ xỏ chân."),
    ("Giày cao gót mũi nhọn 7cm", "Juno", 550000, 37, "heel", "đen", "da tổng hợp", "Tôn dáng, thanh lịch nơi công sở."),
    ("Giày búp bê nữ mũi tròn", "Vascara", 620000, 36, "flat", "be", "da tổng hợp", "Êm chân, đi cả ngày không mỏi."),
    ("Giày sandal nữ quai mảnh", "Juno", 450000, 37, "sandal", "trắng", "da tổng hợp", "Thoáng mát, hợp váy và quần ống rộng."),
    ("Dép Crocs Classic Clog", "Crocs", 1190000, 40, "clog", "xanh navy", "nhựa Croslite", "Nhẹ, êm, thoáng khí, dễ vệ sinh."),
    ("Dép quai ngang Adidas Adilette Comfort", "Adidas", 750000, 42, "slide", "đen", "cao su", "Đế đệm mềm, lý tưởng sau khi tập luyện."),
    ("Giày bóng đá Mizuno Monarcida Neo TF", "Mizuno", 1990000, 41, "football", "trắng xanh", "da tổng hợp", "Giày sân cỏ nhân tạo, ôm chân, bám sân tốt."),
    ("Giày leo núi Columbia Newton Ridge", "Columbia", 3190000, 42, "hiking", "nâu", "da chống thấm", "Chống thấm, bám đường tốt cho các chuyến trekking."),
    ("Giày thể thao trẻ em Biti's", "Biti's", 380000, 30, "kids", "hồng", "vải lưới", "Quai dán tiện lợi, nhẹ và êm cho bé."),
]

COVERS = [("#1e3a5f", "#f2b705"), ("#7a1f2b", "#f4e3c1"), ("#2f6b4f", "#fff4d6"), ("#b5651d", "#fff1d0"),
          ("#2d2d3a", "#4fc3f7"), ("#4a2c6d", "#ffd9a0"), ("#0f4c5c", "#ffe8b0"), ("#3b3b3b", "#ff8a65")]
CARDS = [("#e8f0fe", "#1a4fa3"), ("#fdecea", "#a3271a"), ("#e6f4ea", "#1a6b3a"), ("#fef7e0", "#8a5a00"),
         ("#f3e8fd", "#5b2a9d"), ("#e0f7fa", "#00626e"), ("#eceff1", "#37474f")]
GLYPHS = {
    "laptop": '<rect x="170" y="110" width="260" height="165" rx="12"/><path d="M130 300h340l-22 26H152z"/>',
    "mobile": '<rect x="235" y="85" width="130" height="245" rx="22"/><path d="M280 108h40"/>',
    "tablet": '<rect x="200" y="85" width="200" height="245" rx="18"/><circle cx="300" cy="306" r="6"/>',
    "audio": '<path d="M200 250v-30a100 100 0 0 1 200 0v30"/><rect x="180" y="245" width="44" height="80" rx="16"/><rect x="376" y="245" width="44" height="80" rx="16"/>',
    "device": '<rect x="165" y="105" width="270" height="170" rx="12"/><path d="M300 275v40M240 320h120"/>',
    "shoes": '<path d="M135 300V195q0-14 16-12l52 8q12 2 20 14l24 34q10 12 28 14l130 14q50 6 50 33z"/><path d="M130 326h340M236 226l-20 12M254 250l-20 12"/>',
}


def _pick(palette, key: str):
    return palette[zlib.crc32(key.encode("utf-8")) % len(palette)]       # stable across runs (hash() is salted)


def cover_svg(title: str, author: str, publisher: str, bg: str, accent: str) -> str:
    lines = textwrap.wrap(title, 16) or [title]
    size = 60 if len(lines) <= 2 else 46 if len(lines) <= 4 else 36
    y0 = 300 - (len(lines) - 1) * (size + 10) // 2
    tspans = "".join(f'<tspan x="318" y="{y0 + i * (size + 10)}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    by = textwrap.shorten(author, 34, placeholder="…")
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 800" role="img" aria-label="{escape(title, {'"': "&quot;"})}">
<rect width="600" height="800" fill="{bg}"/><rect x="0" y="0" width="36" height="800" fill="#00000033"/>
<rect x="90" y="120" width="456" height="6" fill="{accent}"/><rect x="90" y="560" width="456" height="6" fill="{accent}"/>
<text font-family="Georgia, 'Times New Roman', serif" font-weight="700" font-size="{size}" fill="#ffffff" text-anchor="middle">{tspans}</text>
<text x="318" y="620" font-family="Georgia, 'Times New Roman', serif" font-size="26" fill="{accent}" text-anchor="middle">{escape(by)}</text>
<text x="318" y="740" font-family="Helvetica, Arial, sans-serif" font-size="22" letter-spacing="4" fill="#ffffffcc" text-anchor="middle">{escape(publisher.upper())}</text>
</svg>
'''


def card_svg(kind: str, name: str, brand: str) -> str:
    bg, ink = _pick(CARDS, brand)
    lines = textwrap.wrap(name, 26)[:3]
    tspans = "".join(f'<tspan x="300" y="{470 + i * 40}">{escape(t)}</tspan>' for i, t in enumerate(lines))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 600" role="img" aria-label="{escape(name, {'"': "&quot;"})}">
<rect width="600" height="600" fill="{bg}"/>
<g fill="none" stroke="{ink}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round">{GLYPHS[kind]}</g>
<text x="300" y="410" font-family="Helvetica, Arial, sans-serif" font-weight="700" font-size="30" letter-spacing="6" fill="{ink}" text-anchor="middle">{escape(brand.upper())}</text>
<text font-family="Helvetica, Arial, sans-serif" font-size="28" fill="#333333" text-anchor="middle">{tspans}</text>
</svg>
'''


def build() -> list[dict]:
    rnd = random.Random(2026)
    items: list[dict] = []

    def add(sku: str, category: str, name: str, brand: str, price: int, description: str, attributes: dict, svg: str, stock: int) -> None:
        image = f"images/products/x-{sku.lower()}.svg"
        (IMG / Path(image).name).write_text(svg, encoding="utf-8")
        items.append({"sku": sku, "category": category, "name": name, "description": description, "brand": brand, "price": price,
                      "stock": stock, "image": image, "attributes": {k: v for k, v in attributes.items() if v is not None},
                      "source": SOURCE})

    for n, (title, author, publisher, price, isbn, pages, language, desc) in enumerate(BOOKS, 6):       # BK-001..005 already exist
        add(f"BK-{n:03d}", "Books", title, publisher, price, desc,
            {"isbn": isbn, "author": author, "publisher": publisher, "pageCount": pages, "language": language},
            cover_svg(title, author, publisher, *_pick(COVERS, title)), rnd.randint(25, 150))
    for n, (name, brand, price, cpu, ram, storage, screen, warranty, desc) in enumerate(LAPTOPS, 3):     # LT-001..002 exist
        add(f"LT-{n:03d}", "Electronics", name, brand, price, desc,
            {"cpu": cpu, "ram": ram, "storage": storage, "screenSize": screen, "warrantyMonths": warranty,
             "modelNumber": name.removeprefix("Laptop ").removeprefix(brand + " ")},
            card_svg("laptop", name, brand), rnd.randint(6, 40))
    for n, (name, brand, price, screen, storage, battery, desc) in enumerate(MOBILES, 3):                # MB-001..002 exist
        add(f"MB-{n:03d}", "Electronics", name, brand, price, desc,
            {"screenSize": screen, "storage": storage, "batteryCapacity": battery, "warrantyMonths": 12},
            card_svg("mobile", name, brand), rnd.randint(10, 60))
    for n, (kind, name, brand, price, warranty, extra, desc) in enumerate(GADGETS, 7):                   # EL-003..006 exist
        add(f"EL-{n:03d}", "Electronics", name, brand, price, desc, {**extra, "warrantyMonths": warranty},
            card_svg(kind, name, brand), rnd.randint(8, 80))
    for n, (name, brand, price, size, kind, colour, material, desc) in enumerate(SHOES, 4):              # SH-001..003 exist
        add(f"SH-{n:03d}", "Shoes", name, brand, price, desc,
            {"shoesSize": size, "shoesType": kind, "color": colour, "material": material},
            card_svg("shoes", name, brand), rnd.randint(10, 90))
    return items


if __name__ == "__main__":
    IMG.mkdir(parents=True, exist_ok=True)
    built = build()
    OUT.write_text(json.dumps(built, ensure_ascii=False, indent=1), encoding="utf-8")
    groups: dict[str, int] = {}
    for it in built:
        groups[it["sku"][:2]] = groups.get(it["sku"][:2], 0) + 1
    print(f"{len(built)} products -> {OUT.relative_to(ROOT)}  {groups}")
