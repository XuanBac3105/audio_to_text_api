# Audio to Text Transcriber - AssemblyAI API

## Setup

### 1. Tạo Virtual Environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

### 2. Cài Dependencies
```bash
pip install -r requirements.txt
```

### 3. Kiểm tra API Key
- Mở file `.env`
- Đảm bảo `ASSEMBLYAI_API_KEY` đúng

### 4. Chạy App
```bash
python app.py
```

### 5. Truy cập Web
- Mở browser: `http://localhost:5000`

## Tính Năng

✅ **Chuẩn nhất** - AssemblyAI có độ chính xác 97%+
✅ **Nhanh nhất** - Xử lý 10-30 giây bất kỳ độ dài nào
✅ **Không cần model** - Cloud-based, không download 2.88GB
✅ **Tự động fix lỗi** - Tự động sửa chính tả
✅ **Đa ngôn ngữ** - Hỗ trợ 99+ ngôn ngữ
✅ **Thời gian thực** - Hiện thị tiến độ & thời gian hoàn thành

## Giá

- **$0.000139/giây** (khoảng **$5 cho 10 giờ audio**)
- Miễn phí trial: 600 phút đầu tiên

## So sánh với faster-whisper

| Feature | faster-whisper | AssemblyAI |
|---------|---|---|
| Tốc độ | 1-2 phút/file | 10-30 giây/file |
| Độ chính xác | Cao | Rất cao (97%+) |
| Model size | 2.88GB | 0 (cloud) |
| RAM usage | 6GB | Minimal |
| Giá | Miễn phí | $0.000139/giây |
| Offline | ✅ Có | ❌ Không |

## Notes

- Lần đầu có thể mất 20-30 giây do upload file lên server
- Nếu API key hết hạn, thay đổi `.env`
- Support tiếng Việt rất tốt (nhưng AssemblyAI không "best" cho Vietnamese, cần "universal")
