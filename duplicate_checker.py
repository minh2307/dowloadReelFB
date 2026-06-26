import json
import logging
from pathlib import Path
from typing import Set

logger = logging.getLogger("fb_downloader")

class DuplicateChecker:
    """
    Quản lý việc kiểm tra trùng lặp URL Facebook Reels.
    Tránh tải lại các video đang tải hoặc đã tải thành công và file vẫn còn tồn tại.
    """

    def __init__(self, log_file: str = "download_log.json"):
        self.log_file = Path(log_file)
        self.active_urls: Set[str] = set()

    def mark_active(self, url: str) -> None:
        """Đánh dấu URL đang/đã xử lý trong phiên hiện tại."""
        self.active_urls.add(url.strip())

    def unmark_active(self, url: str) -> None:
        """Xóa đánh dấu URL (ví dụ khi tải bị lỗi để cho phép tải lại)."""
        url_stripped = url.strip()
        if url_stripped in self.active_urls:
            self.active_urls.remove(url_stripped)

    def is_duplicate(self, url: str) -> bool:
        """
        Kiểm tra xem URL đã trùng lặp hay chưa.
        
        Args:
            url (str): URL cần kiểm tra.
            
        Returns:
            bool: True nếu trùng (đang tải hoặc đã tải thành công và file vẫn tồn tại), ngược lại False.
        """
        url = url.strip()
        
        # 1. Kiểm tra trùng trong phiên chạy hiện tại
        if url in self.active_urls:
            return True

        # 2. Kiểm tra trùng trong lịch sử download_log.json
        if self.log_file.exists():
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    logs = json.load(f)
                
                # Quét ngược từ dưới lên để lấy bản ghi mới nhất trước
                for entry in reversed(logs):
                    if entry.get("url") == url and entry.get("status") == "done":
                        file_path_str = entry.get("file_path")
                        if file_path_str:
                            file_path = Path(file_path_str)
                            # Chỉ coi là trùng nếu file video vật lý vẫn thực sự tồn tại
                            if file_path.exists():
                                return True
            except Exception as e:
                logger.error(f"Error reading download log for duplicate check: {e}")

        return False
