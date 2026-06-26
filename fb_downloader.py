#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════╗
║         FACEBOOK REELS DOWNLOADER - CDHA Pipeline        ║
║         Tác giả: Senior Python Dev                        ║
║         Mô tả: Download video CDHA từ Facebook Reels      ║
╚══════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import logging
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional, List

from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn, TimeRemainingColumn
)
from rich.panel import Panel

# Import các module refactored để đảm bảo cấu trúc Clean Code và SOLID
from metadata_manager import MetadataManager
from cleanup_manager import CleanupManager
from reel_validator import is_facebook_reel
from clipboard_monitor import ClipboardMonitor
from duplicate_checker import DuplicateChecker
from browser_manager import BrowserManager
from scraper import ReelScraper
from logger import log_exception
import download_manager
from download_manager import (
    VideoInfo, build_ydl_opts, get_video_info, download_single,
    download_batch, save_log, print_report, OUTPUT_DIR, COOKIES_FILE,
    USER_AGENT, VIDEO_QUALITY, MAX_WORKERS, DOWNLOAD_LOG_JSON, console, logger
)

# Danh sách lưu trữ kết quả download trong phiên làm việc hiện tại
all_results: List[VideoInfo] = []
all_results_lock = threading.Lock()
metadata_mgr = MetadataManager()
duplicate_checker = DuplicateChecker(DOWNLOAD_LOG_JSON)

def process_and_download_reel(url: str, progress=None, task_id=None) -> VideoInfo:
    """
    Điều phối toàn bộ quá trình:
    1. Opening Reel
    2. Downloading video
    3. Extracting caption
    4. Loading comments
    5. Saving metadata
    6. Completed
    """
    # Khởi tạo scraper
    scraper = ReelScraper()
    
    # Tiến hành tải video
    logger.info("Downloading video")
    video = VideoInfo(url=url)
    result = download_single(video, progress, task_id, metadata_mgr=metadata_mgr)
    
    if result.status == "done" and result.file_path:
        # Trích xuất caption & comments qua Playwright CDP
        # Log "Extracting caption" và "Loading comments" nằm bên trong scraper.scrape()
        scrape_data = scraper.scrape(url)
        
        # Lưu metadata dạng JSON cùng tên với file video
        logger.info("Saving metadata")
        file_path_obj = Path(result.file_path)
        json_path = file_path_obj.with_suffix(".json")
        
        metadata_payload = {
            "video": file_path_obj.name,
            "caption": scrape_data.get("caption", ""),
            "comments": scrape_data.get("comments", [])
        }
        
        try:
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(metadata_payload, f, ensure_ascii=False, indent=4)
        except Exception as e:
            log_exception(logger, "Error saving video metadata JSON", e)
            
        logger.info("Completed")
    else:
        logger.error("Downloading video failed or file path not found. Skipping metadata extraction.")
        
    return result

def on_clipboard_reel_detected(url: str):
    """Callback xử lý khi phát hiện URL Facebook Reel hợp lệ từ clipboard."""
    console.print(f"\n[bold green]📋 Phát hiện Reel từ Clipboard, tự động tải xuống:[/] [cyan]{url}[/]")
    
    # Gọi hàm điều phối tải video & cào metadata
    result = process_and_download_reel(url)
    
    # Ghi nhận kết quả
    with all_results_lock:
        all_results.append(result)
    
    # Lưu log tiến trình tải xuống
    save_log([result])
    
    if result.status == "done":
        console.print(
            f"  [green]✓ Tải tự động thành công:[/] [bold]{result.title[:60]}[/]\n"
            f"     📁 {result.file_path}  [dim]({result.file_size_mb} MB)[/]\n"
        )
    else:
        # Giải phóng link nếu gặp lỗi để có thể tải lại sau
        duplicate_checker.unmark_active(url)
        console.print(
            f"  [red]✗ Tải tự động thất bại:[/] {result.error_msg or 'Không xác định'}\n"
        )
    
    # Vẽ lại prompt nhập tay để người dùng tiếp tục thao tác
    console.print("[bold yellow]🔗 Nhập URL Facebook (Ctrl+C để dừng):[/]")
    sys.stdout.write("  > ")
    sys.stdout.flush()

def main():
    global all_results
    
    console.print(Panel(
        "[bold magenta]🎬 Facebook Reels Downloader — CDHA Pipeline[/]\n\n"
        "[dim]• [Tự động] Sao chép link Reel vào Clipboard → Tải ngầm lập tức\n"
        "• [Thủ công] Nhập URL Facebook rồi nhấn [bold white]Enter[/] → download ngay\n"
        "• Nhấn [bold white]Ctrl + C[/] bất kỳ lúc nào để dừng và xem báo cáo[/]",
        border_style="magenta",
        title="[bold cyan]Chạy Vô Hạn & Giám Sát Clipboard[/]",
    ))

    # 1. Khởi chạy Browser Manager kết nối tới Chrome
    browser_mgr = BrowserManager()
    browser_mgr.start()

    # 2. Tự động quét dọn file quá 24h khi khởi động chương trình
    CleanupManager.cleanup(OUTPUT_DIR, metadata_mgr)

    # 3. Khởi chạy Clipboard monitor ở background thread
    monitor = ClipboardMonitor(callback=on_clipboard_reel_detected, duplicate_checker=duplicate_checker, interval_seconds=0.5)
    monitor.start()

    try:
        while True:
            # ── Nhập URL thủ công từ bàn phím ──────────────────────────────
            try:
                console.print("\n[bold yellow]🔗 Nhập URL Facebook (Ctrl+C để dừng):[/]")
                url = input("  > ").strip()
            except (EOFError, KeyboardInterrupt):
                raise KeyboardInterrupt

            if not url:
                console.print("[dim]  ← Bỏ qua dòng trống[/]")
                continue

            # Kiểm tra URL hợp lệ
            if not is_facebook_reel(url) and "facebook.com" not in url and "fb.watch" not in url:
                console.print("[red]  ⚠  Không phải URL Facebook Reel hợp lệ, bỏ qua.[/]")
                continue

            # Kiểm tra trùng lặp (đang tải hoặc đã tải thành công và file vẫn tồn tại)
            if duplicate_checker.is_duplicate(url):
                console.print("[yellow]  ⚠  URL này đang được tải hoặc đã tải thành công trước đó (file vẫn tồn tại). Bỏ qua.[/]")
                continue

            duplicate_checker.mark_active(url)

            # ── Thực hiện tải video thủ công ─────────────────
            console.print(f"[cyan]  ⬇  Đang download...[/]")

            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeRemainingColumn(),
                console=console,
                transient=True,
            ) as progress:
                task_id = progress.add_task("[yellow]Đang tải...", total=100)
                result  = process_and_download_reel(url, progress, task_id)

            if result.status == "done":
                console.print(
                    f"  [green]✓ Thành công:[/] [bold]{result.title[:60]}[/]\n"
                    f"     📁 {result.file_path}  "
                    f"[dim]({result.file_size_mb} MB)[/]"
                )
            else:
                # Giải phóng link nếu gặp lỗi để có thể tải lại
                duplicate_checker.unmark_active(url)
                console.print(
                    f"  [red]✗ Lỗi:[/] {result.error_msg or 'Không xác định'}"
                )

            with all_results_lock:
                all_results.append(result)

    except KeyboardInterrupt:
        console.print("\n\n[bold yellow]⏹  Đã dừng chương trình. Đang dọn dẹp tài nguyên và xuất báo cáo...[/]\n")
        monitor.stop()

    finally:
        if 'monitor' in locals():
            monitor.stop()
        
        # Đóng kết nối Browser Manager
        BrowserManager().stop()

        # In báo cáo & lưu log
        with all_results_lock:
            current_results = list(all_results)
            
        if current_results:
            print_report(current_results)
            save_log(current_results)

            done_files = [r.file_path for r in current_results if r.status == "done" and r.file_path]
            with open("done_files.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(done_files))

            console.print(
                f"[bold green]✅ Tổng cộng {len(done_files)} file đã download "
                f"→ done_files.txt[/]"
            )
        else:
            console.print("[dim]Chưa download file nào trong phiên này.[/]")


if __name__ == "__main__":
    main()
