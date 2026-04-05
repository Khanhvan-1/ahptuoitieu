# ☕ Smart Coffee Farm - AI DSS Irrigation System

Hệ thống hỗ trợ ra quyết định tưới cà phê thông minh sử dụng:
- **Django**
- **PostgreSQL**
- **AHP**
- **AI (Machine Learning)**
- **Leaflet Map**
- **Realtime Dashboard**
- **AI Chatbot hỗ trợ phân tích vườn**

---

## 🚀 Tính năng chính

### 1. Dashboard AI
- Hiển thị dữ liệu thời tiết và độ ẩm đất
- AI dự đoán mức tưới:
  - Tưới nhiều
  - Tưới vừa
  - Tưới ít
  - Không tưới
- Xác suất dự đoán của AI
- Gợi ý giải thích từ AI

### 2. Phân tích AHP
- Xếp hạng mức ưu tiên tưới của các vườn
- So sánh 2 hoặc nhiều vườn
- AI giải thích lý do ưu tiên

### 3. Bản đồ 40 vườn cà phê
- Hiển thị phân bố các vườn trên bản đồ
- Click marker để xem chi tiết vườn
- Tích hợp AI chatbot để hỏi theo ngữ cảnh vườn

### 4. AI Chatbot
- Hỏi đáp thông minh về:
  - Vườn nào khô nhất
  - Top vườn cần tưới
  - Vườn có nguy cơ úng
  - So sánh giữa các vườn
  - AI đang ưu tiên gì

### 5. Cập nhật dữ liệu tự động
- Dữ liệu 40 vườn được mô phỏng cập nhật định kỳ
- AI và dashboard tự cập nhật theo dữ liệu mới

---

# ⚙️ Yêu cầu hệ thống

- Python **3.11+** hoặc **3.12+**
- PostgreSQL **15+ / 16+ / 17+**
- pip
- Git

---

# 📦 Cài đặt project

## 1. Clone project

```bash
git clone https://github.com/Khanhvan-1/ahptuoitieu.git
cd ahptuoitieu

# Setup project
1/ Mở postgre tạo bảng 
CREATE DATABASE smart_coffee_farm;
2/ python manage.py migrate
3/ python manage.py seed_gardens
4/ python manage.py update_gardens
5/ python manage.py runserver
