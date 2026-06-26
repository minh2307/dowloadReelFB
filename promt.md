# Nhiệm vụ: Phân tích và sửa triệt để chương trình tải Facebook Reel

Bạn là Senior Python Software Engineer với hơn 10 năm kinh nghiệm về:

* Playwright
* Browser Automation
* Chrome DevTools Protocol (CDP)
* Selenium
* yt-dlp
* Python Architecture
* Debugging

Hiện tại chương trình có các chức năng:

* Theo dõi Clipboard.
* Tự động phát hiện URL Facebook Reel.
* Tải video bằng yt-dlp.
* Kết nối Chrome thông qua Playwright CDP.
* Thu thập Caption và Comment.

Tuy nhiên chương trình hoạt động không ổn định.

## Mục tiêu

Không vá lỗi tạm thời.

Hãy phân tích toàn bộ source code và **tìm nguyên nhân gốc (Root Cause)** của các lỗi, sau đó refactor để chương trình hoạt động ổn định.

---

# Các lỗi hiện tại

Ví dụ log:

```text
Opening Reel
Downloading video
Download completed
Metadata updated
Opening Reel
BrowserType.connect_over_cdp:
connect ECONNREFUSED 127.0.0.1:9222
Saving metadata
Completed
```

Caption không lấy được.

Comment không lấy được.

Có lúc Chrome kết nối được.

Có lúc mất kết nối.

---

# Yêu cầu

## 1. Phân tích kiến trúc

Đọc toàn bộ project.

Vẽ sơ đồ luồng hoạt động hiện tại.

Xác định:

* module nào chịu trách nhiệm mở browser
* module nào đóng browser
* module nào download video
* module nào scrape caption
* module nào scrape comment

Chỉ ra các điểm thiết kế chưa hợp lý.

---

## 2. Root Cause Analysis

Không được đoán.

Đối với mỗi lỗi:

* giải thích nguyên nhân
* chỉ rõ file
* chỉ rõ class
* chỉ rõ function
* chỉ rõ dòng code gây lỗi
* giải thích tại sao lỗi xảy ra

Ví dụ:

* connect_over_cdp bị gọi nhiều lần
* browser bị close quá sớm
* page bị đóng
* context bị dispose
* race condition giữa downloader và scraper
* retry sai
* selector lỗi
* timeout
* browser lifecycle sai

---

## 3. Browser Lifecycle

Thiết kế lại vòng đời của Browser.

Yêu cầu:

* Browser chỉ khởi tạo một lần.
* Không connect_over_cdp mỗi lần tải Reel.
* Dùng Browser Singleton hoặc Browser Manager.
* Chỉ tạo Page mới cho mỗi Reel.
* Sau khi hoàn thành chỉ đóng Page.
* Browser chỉ đóng khi chương trình kết thúc.

Không được đóng Browser giữa các lần tải.

---

## 4. Downloader

Không để yt-dlp ảnh hưởng tới Playwright.

Nếu Downloader chạy riêng process hoặc thread thì đảm bảo:

* không đóng Browser
* không kill Chrome
* không reset session

---

## 5. Caption

Refactor hoàn toàn.

Không hardcode selector.

Tự động:

* expand "Xem thêm"
* thử nhiều selector
* fallback selector
* retry

Nếu không tìm thấy:

* dump HTML
* screenshot
* log

Không làm crash chương trình.

---

## 6. Comment

Refactor hoàn toàn.

Yêu cầu:

* Scroll động.
* Click "Xem thêm bình luận".
* Click "Xem phản hồi".
* Dừng khi không còn comment mới.
* Không dùng số vòng lặp cố định.
* Loại bỏ comment trùng.

---

## 7. Error Handling

Không được dùng:

```python
except:
    pass
```

Mọi exception phải:

* log
* traceback
* file
* function
* line number

Nếu lỗi scraper:

* chương trình vẫn tiếp tục tải video.

Nếu lỗi downloader:

* scraper vẫn có thể chạy nếu phù hợp.

---

## 8. Logging

Thêm log chi tiết.

Ví dụ:

```text
Starting Browser Manager
Connected to Chrome
Creating Page
Opening Reel
Extracting Caption
Caption Found
Loading Comments
Loaded 50 Comments
Saving Metadata
Closing Page
Waiting Clipboard
```

Nếu lỗi:

```text
Browser disconnected
Trying reconnect...
Reconnect success
```

---

## 9. Refactor

Thiết kế lại các module:

```text
browser_manager.py
clipboard_monitor.py
download_manager.py
scraper.py
caption_scraper.py
comment_scraper.py
metadata_manager.py
logger.py
config.py
```

Áp dụng:

* SOLID
* DRY
* Dependency Injection
* Singleton (Browser Manager)
* Type Hint
* Docstring
* Retry
* Explicit Wait

---

## 10. Deliverables

Hãy trả về:

1. Phân tích kiến trúc hiện tại.
2. Root Cause của từng lỗi.
3. Danh sách bug.
4. Kế hoạch refactor.
5. Mã nguồn hoàn chỉnh cho từng file cần sửa.
6. Không tạo mã nguồn mới nếu không cần thiết.
7. Chỉ sửa những phần thực sự có vấn đề.
8. Đảm bảo chương trình hoạt động ổn định trong thời gian dài mà không bị mất kết nối Chrome hoặc lỗi khi thu thập Caption và Comment.
