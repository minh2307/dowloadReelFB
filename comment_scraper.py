import time
import logging
from playwright.sync_api import Page
from logger import log_exception

logger = logging.getLogger("fb_downloader")

class CommentScraper:
    """Chịu trách nhiệm cuộn trang, click mở rộng và thu thập comments từ Facebook Reels."""

    @staticmethod
    def scrape(page: Page, timeout_seconds: int = 45) -> list:
        logger.info("Loading Comments")
        start_time = time.time()
        last_comment_count = 0
        no_change_count = 0
        
        while time.time() - start_time < timeout_seconds:
            try:
                # 1. Bấm tất cả nút "Xem thêm bình luận", "Xem các bình luận trước", "Xem thêm phản hồi", v.v.
                clicked_count = page.evaluate(r"""() => {
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
                page.evaluate(r"""() => {
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
                        break
                else:
                    last_comment_count = current_count
                    no_change_count = 0
            except Exception as e:
                logger.error(f"Error during comments expanding iteration: {e}")
                break

        # Thu thập dữ liệu bình luận từ DOM
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
            
            # Loại bỏ bình luận trùng
            unique_comments = []
            seen = set()
            for c in comments:
                c_clean = c.strip()
                if c_clean and c_clean not in seen:
                    seen.add(c_clean)
                    unique_comments.append(c_clean)
            
            logger.info(f"Loaded {len(unique_comments)} Comments")
            return unique_comments
        except Exception as e:
            log_exception(logger, "Error extracting comments", e)
            return []
