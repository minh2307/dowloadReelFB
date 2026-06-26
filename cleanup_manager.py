import os
import logging
from pathlib import Path
from datetime import datetime, timedelta
from metadata_manager import MetadataManager

logger = logging.getLogger("fb_downloader")

class CleanupManager:
    """Quản lý việc tự động xóa các file video đã tải quá 24 giờ."""

    VALID_EXTENSIONS = {".mp4", ".mkv", ".webm"}

    @classmethod
    def cleanup(cls, download_dir: Path, metadata_mgr: MetadataManager, max_age_hours: int = 24) -> None:
        """
        Quét thư mục download và xóa các file video đã tồn tại hơn 24 giờ.
        Chỉ xóa các file video (mp4, mkv, webm) và xóa record tương ứng trong metadata.
        """
        if not download_dir.exists():
            logger.warning(f"Download directory {download_dir} does not exist. Skipping cleanup.")
            return

        logger.info("Scanning download directory for expired reels...")
        now = datetime.now()
        metadata_list = metadata_mgr.load()
        metadata_dict = {item["filename"]: item["download_time"] for item in metadata_list}
        
        # Danh sách các file cần xóa khỏi metadata
        files_to_remove_from_metadata = []
        
        # Duyệt qua các file trong thư mục download
        try:
            for file_path in download_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in cls.VALID_EXTENSIONS:
                    filename = file_path.name
                    is_expired = False
                    
                    # Nếu có trong metadata, kiểm tra download_time
                    if filename in metadata_dict:
                        try:
                            download_time = datetime.fromisoformat(metadata_dict[filename])
                            if now - download_time > timedelta(hours=max_age_hours):
                                is_expired = True
                        except ValueError:
                            # Nếu parse thất bại, dùng mtime của file
                            mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                            if now - mtime > timedelta(hours=max_age_hours):
                                is_expired = True
                    else:
                        # Nếu không có trong metadata, dùng mtime của file
                        mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                        if now - mtime > timedelta(hours=max_age_hours):
                            is_expired = True

                    if is_expired:
                        try:
                            file_path.unlink()
                            logger.info(f"Delete expired reel: {filename}")
                            files_to_remove_from_metadata.append(filename)
                        except Exception as e:
                            logger.error(f"Cannot delete expired file {filename}: {e}")
        except Exception as e:
            logger.error(f"Error during directory scanning: {e}")

        # Đồng thời dọn dẹp các record mồ côi trong metadata (file vật lý không tồn tại)
        for item in metadata_list:
            filename = item["filename"]
            phys_file = download_dir / filename
            if not phys_file.exists() and filename not in files_to_remove_from_metadata:
                files_to_remove_from_metadata.append(filename)

        # Xóa record trong metadata
        for filename in files_to_remove_from_metadata:
            metadata_mgr.remove_record(filename)
