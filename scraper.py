import logging
from browser_manager import BrowserManager
from caption_scraper import CaptionScraper
from comment_scraper import CommentScraper
from logger import log_exception

logger = logging.getLogger("fb_downloader")

class ReelScraper:
    """Điều phối toàn bộ quá trình mở page, cào caption, comments và tự đóng page."""

    def __init__(self):
        self.browser_manager = BrowserManager()

    def scrape(self, url: str) -> dict:
        """
        Thực hiện cào thông tin Reel.
        
        Args:
            url (str): URL của Facebook Reel.
            
        Returns:
            dict: Chứa 'caption' và 'comments'.
        """
        result = {
            "caption": "",
            "comments": []
        }
        page = None
        try:
            # 1. Khởi chạy / Kết nối tới Chrome nếu chưa có
            self.browser_manager.start()
            
            # 2. Tạo một tab (page) mới cho lượt tải này
            page = self.browser_manager.create_page()
            
            # 3. Mở Reel
            logger.info("Opening Reel")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)
            
            # 4. Trích xuất caption
            result["caption"] = CaptionScraper.scrape(page)
            
            # 5. Thu thập bình luận
            result["comments"] = CommentScraper.scrape(page)
            
        except Exception as e:
            log_exception(logger, "Scraper failed to extract data", e)
        finally:
            if page:
                try:
                    logger.info("Closing Page")
                    page.close()
                except Exception as pe:
                    logger.error(f"Error closing page: {pe}")
                    
        return result
