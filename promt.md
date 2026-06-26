# Nhiệm vụ

Bạn là Senior Python Developer.

Hãy nâng cấp chương trình tải Facebook Reel hiện tại mà **không làm thay đổi các chức năng đang hoạt động**.

## Chức năng 1: Theo dõi Clipboard

Thêm một background worker để theo dõi Clipboard của hệ điều hành.

Yêu cầu:

* Kiểm tra clipboard mỗi 500ms (hoặc 1 giây).
* Chỉ xử lý khi nội dung clipboard thay đổi.
* Nếu clipboard chứa URL Facebook Reel hợp lệ thì:

  * Tự động bắt đầu tải.
  * Không cần người dùng bấm nút Download.
* Không tải lại cùng một URL nếu URL đó vừa được xử lý.
* Không ảnh hưởng tới hiệu năng chương trình.

Các dạng URL cần hỗ trợ:

```
https://www.facebook.com/reel/...
https://fb.watch/...
https://www.facebook.com/share/r/...
https://m.facebook.com/reel/...
```

Nếu URL không phải Reel thì bỏ qua.

---

## Chức năng 2: Kiểm tra URL Reel

Viết hàm riêng:

```python
is_facebook_reel(url: str) -> bool
```

Yêu cầu:

* Validate URL.
* Dùng regex hoặc urllib.parse.
* Trả về True nếu là Reel.
* False nếu không phải.

Không được hardcode theo đúng một mẫu URL.

---

## Chức năng 3: Tự động xóa Reel cũ

Sau khi tải video thành công:

* Lưu thời gian tải của video.
* Mỗi lần chương trình khởi động:

  * Quét thư mục Download.
  * Nếu file video đã tồn tại hơn 24 giờ thì tự động xóa.
* Chỉ xóa:

  * mp4
  * mkv
  * webm

Không xóa các file khác.

---

## Chức năng 4: Metadata

Tạo file metadata dạng JSON:

```json
[
    {
        "filename":"abc.mp4",
        "download_time":"2026-06-26T10:30:00"
    }
]
```

Mỗi lần tải thành công:

* cập nhật metadata.

Khi xóa file:

* cũng xóa record trong metadata.

Nếu metadata bị mất:

* tự tạo lại.

---

## Chức năng 5: Threading

Việc theo dõi clipboard phải chạy ở background thread.

Không được block UI.

Nếu chương trình đang tải video:

* clipboard watcher vẫn hoạt động.

---

## Chức năng 6: Logging

Thêm log:

```
Clipboard changed
Facebook Reel detected
Start downloading...
Download completed
Delete expired reel
Metadata updated
```

---

## Chức năng 7: Clean Code

Yêu cầu refactor thành các module:

```
clipboard_monitor.py
reel_validator.py
download_manager.py
cleanup_manager.py
metadata_manager.py
```

Không viết toàn bộ logic trong một file.

Áp dụng:

* SOLID
* DRY
* Type Hint
* Docstring
* Exception Handling
* Logging

---

## Chức năng 8: Không phá vỡ code cũ

Không sửa logic download hiện tại.

Chỉ bổ sung các chức năng mới.

Nếu cần thay đổi thì phải tương thích ngược (backward compatible).

---

## Deliverables

Hãy trả về:

1. Kiến trúc thư mục sau khi refactor.
2. Giải thích ngắn gọn luồng hoạt động.
3. Mã nguồn hoàn chỉnh cho từng file mới.
4. Các thay đổi cần thực hiện trong file main.
5. Hướng dẫn chạy chương trình.
6. Giải thích vì sao lựa chọn cách triển khai này thay vì các phương án khác.
7. Đảm bảo code có thể chạy ngay sau khi copy vào dự án hiện tại.
