# Nâng cấp chương trình tải Facebook Reel

Bạn là Senior Python Automation Engineer, chuyên về Playwright và Browser Automation.

Tôi đã có chương trình tải Facebook Reel bằng Chrome (Playwright kết nối với Chrome thông qua Remote Debugging). Hãy bổ sung chức năng **thu thập tiêu đề (caption)** và **toàn bộ bình luận** của Reel mà **không làm thay đổi chức năng tải video hiện có**.

## Yêu cầu

Sau khi tải video thành công:

### 1. Lấy tiêu đề (Caption)

Thu thập toàn bộ nội dung bài viết (caption) của Reel.

Yêu cầu:

* Giữ nguyên định dạng.
* Hỗ trợ Unicode và Emoji.
* Nếu caption bị rút gọn, tự động nhấn **"Xem thêm" (See more)** để lấy đầy đủ nội dung.

---

### 2. Lấy toàn bộ bình luận

Tự động thu thập tất cả bình luận mà tài khoản Facebook hiện tại có quyền xem.

Yêu cầu:

* Tự động nhấn **"Xem thêm bình luận"** cho đến khi không còn bình luận mới.
* Tự động cuộn trang nếu cần để tải thêm bình luận.
* Không thu thập trùng lặp.
* Chỉ lưu nội dung bình luận, không cần thông tin người bình luận hoặc số lượt thích.

Ví dụ:

```json
[
    "Hay quá!",
    "Video rất hữu ích.",
    "Cảm ơn đã chia sẻ.",
    "Đã lưu lại để xem sau."
]
```

---

### 3. Lưu dữ liệu

Sau khi hoàn thành, tạo một file JSON cùng tên với video.

Ví dụ:

```json
{
    "video": "reel_001.mp4",
    "caption": "Đây là nội dung đầy đủ của Reel...",
    "comments": [
        "Hay quá!",
        "Video rất hữu ích.",
        "Cảm ơn đã chia sẻ."
    ]
}
```

Mỗi video chỉ có một file JSON tương ứng.

---

### 4. Browser

* Sử dụng Chrome hiện tại của tôi thông qua Playwright CDP (Remote Debugging).
* Không đăng nhập Facebook lại.
* Chỉ thu thập dữ liệu mà tài khoản hiện tại có quyền truy cập.

---

### 5. Logging

Hiển thị log rõ ràng:

```text
Opening Reel
Downloading video
Extracting caption
Loading comments
Saving metadata
Completed
```

---

### 6. Code Quality

* Không thay đổi logic tải video hiện tại.
* Tách riêng phần lấy caption và comment thành module độc lập.
* Sử dụng Type Hint, Logging, Docstring và Exception Handling.
* Ưu tiên Explicit Wait thay vì `time.sleep()`.
* Có cơ chế Retry khi Facebook tải nội dung chậm.

---

## Deliverables

Hãy trả về:

1. Mã nguồn hoàn chỉnh cho chức năng lấy caption.
2. Mã nguồn hoàn chỉnh cho chức năng lấy toàn bộ bình luận.
3. Các thay đổi cần bổ sung vào `main.py`.
4. Cấu trúc file JSON đầu ra.
5. Đảm bảo code có thể tích hợp trực tiếp vào dự án hiện tại mà không ảnh hưởng đến chức năng tải video.
