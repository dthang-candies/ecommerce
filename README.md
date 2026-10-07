# Multimodal Search System for E-Commerce (Assignment 05 & 06)

## 1. Overview
This project implements an AI-oriented Multimodal Search System prototype for e-commerce, developed as part of **Information System Analysis and Design**.

The architecture adheres strictly to the **Three-Layer Software Architecture**:
```
User Interface (Presentation) ---> Application / AI Logic ---> Data Layer
```
No direct dependency exists from Presentation to Data (e.g., `SearchUI` never directly calls `ProductRepository` or `ProductDatabase`).

The central design principle implemented is:
```
Different Inputs (Text, Voice, Image) 
   --> Common Query Representation 
   --> Candidate Retrieval 
   --> Multi-Signal Ranking 
   --> Results
```

---

## 2. Directory Structure
```
assigment05/
│
├── main.py                          # Program entry point & demonstration runner
├── README.md                        # Documentation & execution instructions
│
├── presentation/                    # Layer 1: Presentation Layer
│   ├── __init__.py
│   └── search_ui.py                 # SearchUI, VoiceInput, ImageUpload, SearchResultView
│
├── application/                     # Layer 2: Application / Intelligence Layer
│   ├── __init__.py
│   ├── query_service.py             # Transforms modalities to common query representation
│   ├── speech_service.py            # Simulated Speech-to-Text (STT) transcription
│   ├── image_service.py             # Image feature extraction f_theta(I) & cosine similarity
│   ├── search_service.py            # Retrieval for text, voice, image, order, and multimodal
│   └── ranking_service.py           # Multi-signal ranking: S(x|q) = alpha*S_text + beta*S_img + gamma*S_biz
│
├── data/                            # Layer 3: Data Layer
│   ├── __init__.py
│   ├── db_config.py                 # MySQL database configuration & env loader
│   ├── db_connection.py             # Database connection manager (mysql.connector / pymysql)
│   ├── product_repository.py        # Product repository (MySQL live + JSON fallback)
│   ├── order_repository.py          # Customer order repository (MySQL live + memory fallback)
│   ├── vector_index.py              # Vector index for fast cosine similarity search
│   ├── products.json                # JSON dataset of products with embeddings (fallback)
│   └── images/                      # Directory for image assets
│
├── schema.sql                       # Complete MySQL schema & seed data for MySQL Workbench
├── init_db.py                       # Database test & automatic schema executor script
└── .env                             # Database connection credentials (host, user, password, db)
```

---

## 3. Database Setup with MySQL Workbench

The project connects to a local **MySQL** database (managed easily with **MySQL Workbench**):

### Bước 1: Mở và chạy script trong MySQL Workbench
1. Mở **MySQL Workbench** trên máy và kết nối vào MySQL Server của bạn (Local instance 3306).
2. Vào menu **File** -> **Open SQL Script...** (hoặc bấm `Ctrl+Shift+O` / `Cmd+Shift+O`).
3. Chọn file `schema.sql` nằm ở thư mục gốc của dự án:
   `assigment05/schema.sql`
4. Bấm biểu tượng tia sét **Execute (⚡)** trên thanh công cụ để thực thi script.
5. Script sẽ tự động:
   - Tạo database `multimodal_search_db`.
   - Tạo các bảng `products`, `orders`, `order_items`.
   - Insert toàn bộ dữ liệu mẫu (12 sản phẩm với vector embedding, 4 đơn hàng mẫu).
6. Bấm nút **Refresh** ở bảng điều khiển *Navigator / Schemas* bên trái, bạn sẽ thấy `multimodal_search_db` đã sẵn sàng!

### Bước 2: Cấu hình thông tin kết nối trong dự án
Mở file `.env` ở thư mục gốc dự án và điền mật khẩu MySQL của bạn:
```env
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=mat_khau_mysql_cua_ban
DB_NAME=multimodal_search_db
```

### Bước 3: Kiểm tra kết nối từ terminal (Tùy chọn)
Chạy script kiểm tra kết nối:
```bash
python3 init_db.py
```
Nếu mật khẩu chính xác, script sẽ báo `[SUCCESS] MySQL is fully configured and ready for the application.`

> **Lưu ý tính năng Graceful Fallback**: Nếu MySQL chưa bật hoặc sai mật khẩu, hệ thống sẽ tự động dùng dữ liệu fallback (`products.json`) để ứng dụng vẫn hoạt động bình thường mà không bị crash.

---

## 4. Requirements & Environment
- **Python Version**: Python 3.9+ (Tested on Python 3.13)
- **Required Packages**:
  - `numpy`
  - `mysql-connector-python` hoặc `pymysql`
  - Python standard library (`json`, `sys`, `os`, `typing`)

Install dependencies if needed:
```bash
pip install numpy mysql-connector-python pymysql
```


---

## 4. How to Run the Program

### 1. Launch Interactive Web UI (Recommended):
Runs the Flask interactive server and automatically opens your web browser at `http://127.0.0.1:5050`:
```bash
python3 main.py
```
**Features of the Interactive Web UI:**
- **Text Search**: Real-time keyword search with instant candidate scoring.
- **Voice Search (VoiceInput)**: Click the 🎙️ mic button to speak using your browser's Web Speech API (or type spoken queries).
- **Image Search (ImageUpload)**: Upload image files or select visual prototype embeddings for vector similarity search.
- **Multimodal Fusion**: Combine text keywords + image embeddings with a dynamic weight slider ($\lambda_t$ vs $\lambda_i$).
- **View Product**: Click any product card to view full specifications, stock status, and vector embedding coordinates $[z_1, z_2, z_3]$.
- **Order Tracking (Search Order & View Order)**: Search orders by ID (e.g., `O001`, `O002`, `20261001`) with order details and status timeline.
- **Architecture & Evaluation Tab**: Live view of the Three-Layer diagram and automated evaluation metrics.

### 2. Launch Native Desktop GUI (Tkinter):
If you prefer a native desktop window:
```bash
python3 main.py --gui
```

### 3. Run Console Interactive Menu:
To run the interactive prompt in your terminal:
```bash
python3 main.py --cli
```

### 4. Run Automated Demo & Evaluation:
To run the automated test suite without opening a browser:
```bash
python3 main.py --demo
```

---

## 5. Supported Search Modalities & Examples

| Search Mode | Input Example | Processing Flow |
|-------------|---------------|-----------------|
| **Text Search** | `"black shoes"` | Text normalization -> Keyword matching -> Candidate scoring |
| **Voice Search** | `"find running shoes"` | Speech input -> Simulated STT transcription -> Query representation -> Candidate retrieval |
| **Image Search** | `[0.9, 0.1, 0.2]` or `"shoes"` | Visual feature vector $z_q = f_\theta(I_q)$ -> Cosine similarity against product embeddings -> Top-K |
| **Multimodal Search** | Text: `"running"`, Image: `[0.9, 0.1, 0.2]` | Multimodal Query fusion: $S(p\|q) = \lambda_t S_t(p\|q_t) + \lambda_i S_i(p\|q_i)$ -> Business-aware ranking |
| **Order Search** | `"O001"` | Order lookup by Order ID -> Returns customer ID, status, items, total |

---

## 6. Experimental Evaluation Results
As specified in Section 22 (Table 3), the prototype is evaluated against standard test queries:

| Query | Mode | Top-1 Result | Success |
|---|---|---|---|
| `black shoes` | Text | Nike Running Shoes | **Yes** |
| `running shoes` | Voice | Nike Running Shoes | **Yes** |
| `shoe image [0.9, 0.1, 0.2]` | Image | Nike Running Shoes | **Yes** |
| `order O001` | Order | Order O001 | **Yes** |

**Success Rate**: $100\%$ ($4 / 4$ successful test queries).

---

## 7. Limitations of the Prototype
1. **Simulated Speech Recognition**: In this prototype, audio input is simulated by text transcription rather than decoding raw `.wav`/`.mp3` audio via acoustic neural networks (e.g., Whisper).
2. **Artificial Feature Vectors**: Image embeddings are represented by predefined normalized vectors (e.g., 3-dimensional prototypes) rather than deep neural network encoders (e.g., CLIP / ResNet).
3. **In-Memory Storage**: Products and orders are loaded in memory from JSON / dictionaries rather than an external SQL / NoSQL database.
