import time
import logging
import threading
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page
from config import CHROME_CDP_URL
from logger import log_exception

logger = logging.getLogger("fb_downloader")

class BrowserManager:
    """
    Quản lý vòng đời kết nối trình duyệt Chrome qua CDP (Singleton).
    Chỉ khởi tạo trình duyệt 1 lần, chỉ tạo/đóng các trang (pages) cho mỗi Reel.
    """
    _instance = None
    _lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(BrowserManager, cls).__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    def __init__(self, cdp_url: str = CHROME_CDP_URL):
        if self._initialized:
            return
        self.cdp_url = cdp_url
        self.playwright = None
        self.browser: Browser = None
        self.context: BrowserContext = None
        self._lock = threading.Lock()
        self._initialized = True

    def start(self) -> bool:
        """
        Kết nối tới trình duyệt Chrome qua CDP.
        Chỉ thực hiện một lần duy nhất. Nếu mất kết nối, tự động reconnect.
        """
        with self._lock:
            if self.browser is not None:
                # Kiểm tra kết nối còn sống hay không bằng cách gọi API của browser
                try:
                    self.browser.contexts
                    return True
                except Exception:
                    logger.warning("Browser disconnected. Trying reconnect...")
                    self._cleanup_resources()
            
            logger.info("Starting Browser Manager")
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.connect_over_cdp(self.cdp_url)
                self.context = self.browser.contexts[0]
                logger.info("Connected to Chrome")
                return True
            except Exception as e:
                log_exception(logger, "Failed to connect to Chrome via CDP", e)
                self._cleanup_resources()
                return False

    def create_page(self) -> Page:
        """Tạo trang (page) mới từ context trình duyệt."""
        if not self.context:
            if not self.start():
                raise Exception("Cannot create Page: Browser Manager failed to connect to Chrome.")
        
        try:
            logger.info("Creating Page")
            return self.context.new_page()
        except Exception as e:
            logger.warning("Error creating page, trying to reconnect to Chrome...")
            if self.start():
                try:
                    logger.info("Creating Page")
                    return self.context.new_page()
                except Exception as retry_err:
                    raise Exception(f"Failed to create page after reconnecting: {retry_err}")
            raise Exception(f"Cannot create Page due to browser connection error: {e}")

    def _cleanup_resources(self):
        """Dọn dẹp tài nguyên khi mất kết nối hoặc dừng chương trình."""
        if self.browser:
            try:
                self.browser.close()
            except:
                pass
            self.browser = None
        if self.playwright:
            try:
                self.playwright.stop()
            except:
                pass
            self.playwright = None
        self.context = None

    def stop(self):
        """Đóng kết nối trình duyệt khi kết thúc chương trình."""
        with self._lock:
            logger.info("Closing Browser connection")
            self._cleanup_resources()
            logger.info("Browser Manager stopped")
