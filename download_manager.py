import os
import sys
import json
import logging
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any

import yt_dlp
from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn,
    BarColumn, TaskProgressColumn, TimeRemainingColumn
)
from rich.table import Table
from rich.panel import Panel
from dotenv import load_dotenv

from metadata_manager import MetadataManager

# Load biến môi trường
load_dotenv()

# ─────────────────────────────────────────────
# CẤU HÌNH
# ─────────────────────────────────────────────
OUTPUT_DIR   = Path(os.getenv("OUTPUT_DIR", "downloads"))
COOKIES_FILE = os.getenv("FB_COOKIES_FILE", "cookies.txt")
USER_AGENT   = os.getenv("USER_AGENT", "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36")
VIDEO_QUALITY = os.getenv("VIDEO_QUALITY", "best")
MAX_WORKERS  = int(os.getenv("MAX_WORKERS", "2"))
LOG_FILE     = "download_log.json"

console = Console()

# ─────────────────────────────────────────────
# DATA CLASS
# ─────────────────────────────────────────────
@dataclass
class VideoInfo:
    url: str
    title: str           = ""
    video_id: str        = ""
    duration: int        = 0          # giây
    file_path: str       = ""
    status: str          = "pending"  # pending | downloading | done | error
    error_msg: str       = ""
    downloaded_at: str   = ""
    file_size_mb: float  = 0.0


# ─────────────────────────────────────────────
# LOGGER
# ─────────────────────────────────────────────
def setup_logger() -> logging.Logger:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        handlers=[
            logging.FileHandler("downloader.log", encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )
    return logging.getLogger("fb_downloader")

logger = setup_logger()


# ─────────────────────────────────────────────
# HÀM BUILD OPTIONS cho yt-dlp
# ─────────────────────────────────────────────
def build_ydl_opts(output_path: Path, quiet: bool = True) -> dict:
    """Tạo cấu hình yt-dlp tối ưu cho Facebook."""
    
    # Format chất lượng
    if VIDEO_QUALITY == "best":
        fmt = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best"
    elif VIDEO_QUALITY == "worst":
        fmt = "worstvideo+worstaudio/worst"
    else:
        fmt = f"bestvideo[height<={VIDEO_QUALITY}][ext=mp4]+bestaudio[ext=m4a]/best[height<={VIDEO_QUALITY}]/best"

    opts = {
        "format": fmt,
        "outtmpl": str(output_path / "%(upload_date)s_%(id)s_%(title).50s.%(ext)s"),
        "quiet": quiet,
        "no_warnings": quiet,
        "ignoreerrors": True,
        "retries": 5,
        "fragment_retries": 10,
        "concurrent_fragment_downloads": 4,
        "http_headers": {
            "User-Agent": USER_AGENT,
            "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8",
            "Referer": "https://www.facebook.com/",
        },
        "socket_timeout": 30,
        "extractor_args": {
            "facebook": {
                "api_version": "v18.0",
            }
        },
    }

    # Thêm cookies nếu có
    if os.path.exists(COOKIES_FILE):
        opts["cookiefile"] = COOKIES_FILE
        console.print(f"[green]✓ Dùng cookies từ file:[/] {COOKIES_FILE}")
    else:
        console.print(f"[yellow]⚠ Không tìm thấy {COOKIES_FILE}, download không cần đăng nhập[/]")

    return opts


# ─────────────────────────────────────────────
# LẤY THÔNG TIN VIDEO (không download)
# ─────────────────────────────────────────────
def get_video_info(url: str) -> Optional[VideoInfo]:
    """Trích xuất metadata của video mà không download."""
    opts = build_ydl_opts(OUTPUT_DIR, quiet=True)
    opts["skip_download"] = True

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(url, download=False)
            if not info:
                return None

            return VideoInfo(
                url=url,
                title=info.get("title", "Unknown"),
                video_id=info.get("id", ""),
                duration=info.get("duration", 0),
            )
    except Exception as e:
        logger.error(f"Lỗi lấy info: {url} → {e}")
        return VideoInfo(url=url, status="error", error_msg=str(e))


# ─────────────────────────────────────────────
# DOWNLOAD MỘT VIDEO
# ─────────────────────────────────────────────
def download_single(video: VideoInfo, progress=None, task_id=None, metadata_mgr: Optional[MetadataManager] = None) -> VideoInfo:
    """Download một video Facebook, trả về VideoInfo đã cập nhật và ghi vào metadata."""
    if metadata_mgr is None:
        metadata_mgr = MetadataManager()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    video.status = "downloading"
    logger.info("Start downloading...")

    downloaded_files = []

    def progress_hook(d):
        if d["status"] == "downloading" and progress and task_id is not None:
            total   = d.get("total_bytes") or d.get("total_bytes_estimate", 0)
            current = d.get("downloaded_bytes", 0)
            if total > 0:
                progress.update(task_id, completed=current, total=total)
        elif d["status"] == "finished":
            downloaded_files.append(d.get("filename", ""))

    opts = build_ydl_opts(OUTPUT_DIR, quiet=True)
    opts["progress_hooks"] = [progress_hook]

    try:
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(video.url, download=True)
            if info:
                # Lấy đường dẫn file thực tế
                filename = ydl.prepare_filename(info)
                # Thử các extension phổ biến
                for ext in [".mp4", ".mkv", ".webm", ""]:
                    candidate = Path(filename).with_suffix(ext) if ext else Path(filename)
                    if candidate.exists():
                        video.file_path = str(candidate)
                        video.file_size_mb = round(candidate.stat().st_size / 1024 / 1024, 2)
                        break

                video.title       = info.get("title", video.title)
                video.video_id    = info.get("id", video.video_id)
                video.duration    = info.get("duration", 0)
                video.status      = "done"
                video.downloaded_at = datetime.now().isoformat()

                logger.info(f"✓ Done: {video.title} ({video.file_size_mb} MB) | URL: {video.url}")
                logger.info("Download completed")
                
                # Lưu metadata record
                if video.file_path:
                    filename_only = Path(video.file_path).name
                    metadata_mgr.add_record(filename_only, video.downloaded_at)

    except Exception as e:
        video.status    = "error"
        video.error_msg = str(e)
        logger.error(f"✗ Lỗi download {video.url}: {e}")

    return video


# ─────────────────────────────────────────────
# DOWNLOAD NHIỀU VIDEO
# ─────────────────────────────────────────────
def download_batch(urls: List[str], max_workers: int = MAX_WORKERS, metadata_mgr: Optional[MetadataManager] = None) -> List[VideoInfo]:
    """Download nhiều video song song."""
    if metadata_mgr is None:
        metadata_mgr = MetadataManager()

    results: List[VideoInfo] = []

    console.print(Panel(
        f"[bold cyan]🎬 CDHA Facebook Reels Downloader[/]\n"
        f"📂 Lưu vào : [yellow]{OUTPUT_DIR.resolve()}[/]\n"
        f"🎯 Số URL  : [green]{len(urls)}[/]\n"
        f"⚡ Luồng   : [blue]{max_workers}[/]",
        title="Bắt đầu Download",
        border_style="cyan"
    ))

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console,
        expand=True,
    ) as progress:

        overall = progress.add_task("[cyan]Tổng tiến độ...", total=len(urls))

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}

            for url in urls:
                video = VideoInfo(url=url)
                task_id = progress.add_task(
                    f"[yellow]⏳ {url[:60]}...", total=100
                )
                future = executor.submit(download_single, video, progress, task_id, metadata_mgr)
                futures[future] = (video, task_id)

            for future in as_completed(futures):
                _, task_id = futures[future]
                result = future.result()
                results.append(result)

                if result.status == "done":
                    progress.update(task_id, description=f"[green]✓ {result.title[:50]}", completed=100)
                else:
                    progress.update(task_id, description=f"[red]✗ Lỗi: {result.url[:40]}", completed=100)

                progress.advance(overall)

    return results


# ─────────────────────────────────────────────
# LƯU LOG KẾT QUẢ DẠNG JSON
# ─────────────────────────────────────────────
def save_log(results: List[VideoInfo]):
    """Lưu kết quả download vào file JSON."""
    log_path = Path(LOG_FILE)

    # Đọc log cũ nếu có
    existing = []
    if log_path.exists():
        try:
            with open(log_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            pass

    # Gộp và lưu
    all_results = existing + [asdict(r) for r in results]
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(all_results, f, ensure_ascii=False, indent=2)

    console.print(f"[green]💾 Đã lưu log vào:[/] {log_path.resolve()}")


# ─────────────────────────────────────────────
# IN BÁO CÁO KẾT QUẢ
# ─────────────────────────────────────────────
def print_report(results: List[VideoInfo]):
    """In bảng tóm tắt kết quả."""
    table = Table(title="📊 Kết Quả Download", border_style="blue", show_lines=True)
    table.add_column("STT", style="dim", width=4)
    table.add_column("Tiêu đề", style="cyan", max_width=40)
    table.add_column("Thời lượng", justify="right")
    table.add_column("Dung lượng", justify="right")
    table.add_column("Trạng thái", justify="center")

    done_count  = 0
    error_count = 0

    for i, r in enumerate(results, 1):
        duration_str = f"{int(r.duration) // 60}:{int(r.duration) % 60:02d}" if r.duration else "N/A"
        size_str     = f"{r.file_size_mb} MB" if r.file_size_mb else "N/A"

        if r.status == "done":
            status_str = "[green]✓ Thành công[/]"
            done_count += 1
        else:
            status_str = f"[red]✗ Lỗi[/]"
            error_count += 1

        table.add_row(str(i), r.title[:40] or r.url[:40], duration_str, size_str, status_str)

    console.print(table)
    console.print(
        f"\n[bold]Tổng kết:[/] "
        f"[green]✓ {done_count} thành công[/]  "
        f"[red]✗ {error_count} lỗi[/]  "
        f"📁 Thư mục: [yellow]{OUTPUT_DIR.resolve()}[/]\n"
    )
