import os
import time
import logging
from typing import Dict, Any, List
from playwright.sync_api import sync_playwright

logger = logging.getLogger("fb_downloader")

class ReelScraper:
    """
    Quản lý việc thu thập caption và comments từ Facebook Reels.
    Kết nối với trình duyệt Chrome đang chạy qua giao thức Chrome DevTools Protocol (CDP).
    """

    def __init__(self, cdp_url: str = "http://localhost:9222"):
        """
        Khởi tạo ReelScraper.
        
        Args:
            cdp_url (str): Địa chỉ CDP kết nối tới trình duyệt Chrome đang chạy (mặc định http://localhost:9222).
        """
        self.cdp_url = cdp_url

    def scrape_reel(self, url: str) -> Dict[str, Any]:
        """
        Mở hoặc chuyển đến trang Reel, lấy caption và toàn bộ comments.
        
        Args:
            url (str): Đường dẫn URL của Facebook Reel.
            
        Returns:
            dict: Chứa thông tin caption và danh sách comments.
        """
        result = {
            "caption": "",
            "comments": []
        }

        logger.info("Opening Reel")
        try:
            with sync_playwright() as p:
                # Kết nối tới Chrome đang mở
                browser = p.chromium.connect_over_cdp(self.cdp_url)
                # Lấy context mặc định của Chrome đang mở
                context = browser.contexts[0]
                
                # Tìm xem có tab nào đang mở URL này hoặc facebook.com chưa
                page = None
                for p_page in context.pages:
                    if url in p_page.url or (("facebook.com/reel" in p_page.url or "fb.watch" in p_page.url) and url.split("?")[0] in p_page.url):
                        page = p_page
                        logger.info("Reusing existing tab for Reel")
                        break
                
                if not page:
                    # Nếu chưa có tab nào mở Reel này, mở tab mới
                    page = context.new_page()
                    page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    # Đợi thêm chút để giao diện hiển thị
                    page.wait_for_timeout(3000)
                else:
                    # Chuyển tab đó lên phía trước
                    page.bring_to_front()
                    
                # 1. Trích xuất caption
                logger.info("Extracting caption")
                result["caption"] = self._extract_caption(page)
                
                # 2. Tải toàn bộ bình luận (bấm nút xem thêm + cuộn)
                logger.info("Loading comments")
                self._load_all_comments(page)
                
                # 3. Thu thập bình luận
                result["comments"] = self._extract_comments(page)
                
                logger.info("Completed extraction")
                
        except Exception as e:
            logger.error(f"Error scraping Reel data: {e}")
            
        return result

    def _extract_caption(self, page) -> str:
        """Nhấn Xem thêm và trích xuất Caption bài viết."""
        try:
            # Tìm và click nút "Xem thêm" hoặc "See more" của Caption
            page.evaluate("""() => {
                const seeMoreBtns = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], span'))
                    .filter(el => /^(Xem thêm|See more)$/i.test(el.innerText.trim()));
                seeMoreBtns.forEach(btn => {
                    try { btn.click(); } catch(e) {}
                });
            }""")
            # Đợi 1 giây để text mở rộng ra
            page.wait_for_timeout(1000)
            
            # Trích xuất caption bằng selector linh hoạt
            caption = page.evaluate(r"""() => {
                let captionText = "";
                
                // Thử tìm thẻ h2 của Reels và tìm span dir="auto" anh em
                const h2s = Array.from(document.querySelectorAll('h2'));
                for (let h2 of h2s) {
                    let parent = h2.parentElement;
                    if (parent) {
                        const spans = Array.from(parent.querySelectorAll('span[dir="auto"]'));
                        for (let span of spans) {
                            if (!h2.contains(span) && span.innerText.trim().length > 0) {
                                captionText = span.innerText.trim();
                                break;
                            }
                        }
                    }
                    if (captionText) break;
                }
                
                // Fallback: Tìm thẻ span[dir="auto"] có độ dài lớn nhất trong pagelet Reels
                if (!captionText) {
                    const reelsContainer = document.querySelector('div[data-pagelet="Reels"]') || document.body;
                    const spans = Array.from(reelsContainer.querySelectorAll('span[dir="auto"]'));
                    let longestText = "";
                    for (let span of spans) {
                        const text = span.innerText.trim();
                        // Bỏ qua text quá ngắn hoặc là tên nút/thời gian
                        if (text.length > longestText.length && 
                            text.length > 5 && 
                            !/^(Thích|Like|Phản hồi|Reply|Chia sẻ|Share|Xem thêm|See more)$/i.test(text) &&
                            !/^\d+\s*(giờ|phút|ngày|tuần|tháng|năm|hr|min|day|week|mon|ago)/i.test(text)) {
                            longestText = text;
                        }
                    }
                    captionText = longestText;
                }
                
                return captionText;
            }""")
            return caption or ""
        except Exception as e:
            logger.error(f"Error extracting caption: {e}")
            return ""

    def _load_all_comments(self, page, timeout_seconds: int = 45) -> None:
        """Tự động cuộn trang và bấm các nút mở rộng bình luận."""
        start_time = time.time()
        last_comment_count = 0
        no_change_count = 0
        
        while time.time() - start_time < timeout_seconds:
            try:
                # 1. Bấm tất cả nút "Xem thêm bình luận", "Xem các bình luận trước", "Xem thêm phản hồi", v.v.
                clicked_count = page.evaluate("""() => {
                    const btns = Array.from(document.querySelectorAll('div[role="button"], span[role="button"], span'))
                        .filter(el => /(Xem thêm bình luận|Xem các bình luận trước|Xem thêm phản hồi|Xem các bình luận khác|View more comments|View previous comments|View more replies|phản hồi|replies)/i.test(el.innerText.trim()));
                    
                    let clicked = 0;
                    btns.forEach(btn => {
                        if (btn.offsetWidth > 0 && btn.offsetHeight > 0) {
                            try {
                                btn.click();
                                clicked++;
                            } catch(e) {}
                        }
                    });
                    return clicked;
                }""")
                
                # 2. Cuộn trang hoặc cuộn sidebar bình luận xuống cuối cùng
                page.evaluate("""() => {
                    // Cuộn window chính
                    window.scrollBy(0, 800);
                    
                    // Cuộn các div sidebar có thuộc tính cuộn
                    const scrollableDivs = Array.from(document.querySelectorAll('div'))
                        .filter(div => {
                            const style = window.getComputedStyle(div);
                            return (style.overflowY === 'auto' || style.overflowY === 'scroll') && div.scrollHeight > div.clientHeight;
                        });
                        
                    scrollableDivs.forEach(div => {
                        div.scrollTop = div.scrollHeight;
                    });
                }""")
                
                # Đợi load dữ liệu
                page.wait_for_timeout(1500)
                
                # 3. Đếm số lượng bình luận hiện có để kiểm tra điểm dừng
                current_count = page.evaluate(r"""() => {
                    const profileLinks = Array.from(document.querySelectorAll('a[href*="facebook.com/"], a[role="link"]'))
                        .filter(a => {
                            const name = a.innerText.trim();
                            return name.length >= 2 && 
                                   !/^\d+\s*(giờ|phút|ngày|tuần|tháng|năm|hr|min|day|week|mon|ago)/i.test(name) && 
                                   !/^https?:\/\//.test(name) &&
                                   !/(Thích|Like|Phản hồi|Reply|Chia sẻ|Share)/i.test(name);
                        });
                    return profileLinks.length;
                }""")
                
                if current_count == last_comment_count:
                    if clicked_count == 0:
                        no_change_count += 1
                    if no_change_count >= 4:
                        # Đã cuộn 4 lần không tăng số bình luận và không click thêm được nút nào
                        break
                else:
                    last_comment_count = current_count
                    no_change_count = 0
            except Exception as e:
                logger.error(f"Error during comments expanding iteration: {e}")
                break

    def _extract_comments(self, page) -> List[str]:
        """Thu thập nội dung các bình luận, loại bỏ trùng lặp và lọc thông tin thừa."""
        try:
            comments = page.evaluate(r"""() => {
                const results = [];
                
                // Lấy tất cả các profile links để định vị comment
                const profileLinks = Array.from(document.querySelectorAll('a[href*="facebook.com/"], a[role="link"]'))
                    .filter(a => {
                        const name = a.innerText.trim();
                        return name.length >= 2 && 
                               !/^\d+\s*(giờ|phút|ngày|tuần|tháng|năm|hr|min|day|week|mon|ago)/i.test(name) && 
                               !/^https?:\/\//.test(name) &&
                               !/(Thích|Like|Phản hồi|Reply|Chia sẻ|Share)/i.test(name);
                    });
                    
                profileLinks.forEach(link => {
                    let parent = link.parentElement;
                    // Đi lên tối đa 4 cấp để tìm container chứa comment text
                    for (let i = 0; i < 4; i++) {
                        if (!parent) break;
                        
                        // Tìm các thẻ span[dir="auto"] chứa text comment
                        const textSpans = Array.from(parent.querySelectorAll('span[dir="auto"]'));
                        for (let span of textSpans) {
                            const text = span.innerText.trim();
                            // Loại bỏ tên người bình luận, thời gian, nút thích/phản hồi
                            if (text && 
                                text !== link.innerText.trim() && 
                                !/^(Thích|Like|Phản hồi|Reply|Chia sẻ|Share|\d+k?|Xem thêm|View more.*)$/i.test(text) &&
                                !/^\d+\s*(giờ|phút|ngày|tuần|tháng|năm|hr|min|day|week|mon|ago)/i.test(text)) {
                                
                                results.push(text);
                                break;
                            }
                        }
                        if (results.length > 0 && results[results.length - 1]) break;
                        parent = parent.parentElement;
                    }
                });
                
                return results;
            }""")
            
            # Loại bỏ trùng lặp và giữ nguyên thứ tự xuất hiện
            unique_comments = []
            seen = set()
            for c in comments:
                c_clean = c.strip()
                if c_clean and c_clean not in seen:
                    seen.add(c_clean)
                    unique_comments.append(c_clean)
                    
            return unique_comments
        except Exception as e:
            logger.error(f"Error extracting comments text: {e}")
            return []
