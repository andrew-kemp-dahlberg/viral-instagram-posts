#!/usr/bin/env python3
"""
Media Downloader with Caching
Downloads tweet videos/images with MD5-based caching, retry logic, and progress tracking.
"""

import hashlib
import json
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Tuple
import tempfile
import shutil

import requests
from tqdm import tqdm


class MediaDownloader:
    """
    Robust media downloader with caching for tweet videos and images.

    Features:
    - MD5-based cache keys to avoid re-downloads
    - Progress bars using tqdm
    - Retry logic (3 attempts with exponential backoff)
    - File validation
    - Metadata storage (JSON sidecar)
    - Cache hit detection with TTL support
    """

    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    SUPPORTED_VIDEO_FORMATS = {'.mp4', '.mov', '.avi', '.webm', '.m4v'}
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1  # seconds
    CHUNK_SIZE = 8192  # bytes

    def __init__(self, config_path: str = 'video_config.json'):
        """
        Initialize MediaDownloader with configuration.

        Args:
            config_path: Path to video_config.json configuration file
        """
        # Set up logging
        self._setup_logging()

        # Load configuration
        self.config = self._load_config(config_path)
        self.cache_dir = Path(self.config['paths']['media_cache_dir'])
        self.cache_ttl_hours = self.config['processing'].get('cache_ttl_hours', 24)

        # Create cache directory if it doesn't exist
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        self.logger.info(f"MediaDownloader initialized with cache_dir: {self.cache_dir}")
        self.logger.info(f"Cache TTL: {self.cache_ttl_hours} hours")

    def _setup_logging(self):
        """Configure logging to file and console."""
        self.logger = logging.getLogger('MediaDownloader')
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler
        file_handler = logging.FileHandler('media_download.log')
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.WARNING)  # Only warnings and errors to console
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _load_config(self, config_path: str) -> dict:
        """Load video configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            self.logger.error(f"Configuration file not found: {config_path}")
            raise
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in configuration file: {e}")
            raise

    def _generate_cache_key(self, url: str) -> str:
        """
        Generate MD5-based cache key from URL.

        Args:
            url: Media URL

        Returns:
            MD5 hash of the URL
        """
        return hashlib.md5(url.encode('utf-8')).hexdigest()

    def _get_file_extension(self, url: str, content_type: Optional[str] = None) -> str:
        """
        Determine file extension from URL or content type.

        Args:
            url: Media URL
            content_type: HTTP Content-Type header (optional)

        Returns:
            File extension (e.g., '.mp4', '.jpg')
        """
        # Try to get extension from URL
        url_path = url.split('?')[0]  # Remove query parameters
        ext = Path(url_path).suffix.lower()

        if ext in self.SUPPORTED_IMAGE_FORMATS or ext in self.SUPPORTED_VIDEO_FORMATS:
            return ext

        # Fallback to content type
        if content_type:
            content_type_map = {
                'image/jpeg': '.jpg',
                'image/png': '.png',
                'image/gif': '.gif',
                'image/webp': '.webp',
                'video/mp4': '.mp4',
                'video/quicktime': '.mov',
                'video/webm': '.webm',
            }
            return content_type_map.get(content_type, '.bin')

        # Default fallback
        return '.bin'

    def _get_cache_path(self, cache_key: str, extension: str) -> Path:
        """Get path to cached media file."""
        return self.cache_dir / f"{cache_key}{extension}"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """Get path to metadata JSON sidecar file."""
        return self.cache_dir / f"{cache_key}.json"

    def _is_cached(self, cache_key: str, extension: str) -> bool:
        """
        Check if media is cached and still valid (within TTL).

        Args:
            cache_key: MD5 cache key
            extension: File extension

        Returns:
            True if cached and valid, False otherwise
        """
        cache_path = self._get_cache_path(cache_key, extension)
        metadata_path = self._get_metadata_path(cache_key)

        # Check if both files exist
        if not cache_path.exists() or not metadata_path.exists():
            return False

        # Check if file is empty or corrupted
        if cache_path.stat().st_size == 0:
            self.logger.warning(f"Cached file is empty: {cache_path}")
            return False

        # Check TTL
        try:
            with open(metadata_path, 'r') as f:
                metadata = json.load(f)

            download_time = datetime.fromisoformat(metadata['download_time'])
            expiry_time = download_time + timedelta(hours=self.cache_ttl_hours)

            if datetime.now() > expiry_time:
                self.logger.info(f"Cache expired for {cache_key}")
                return False

            self.logger.info(f"Cache hit: {cache_key}{extension}")
            return True

        except (json.JSONDecodeError, KeyError, ValueError) as e:
            self.logger.warning(f"Invalid metadata file: {metadata_path} - {e}")
            return False

    def _save_metadata(self, cache_key: str, url: str, file_type: str, file_size: int):
        """
        Save metadata to JSON sidecar file.

        Args:
            cache_key: MD5 cache key
            url: Original media URL
            file_type: 'image' or 'video'
            file_size: File size in bytes
        """
        metadata_path = self._get_metadata_path(cache_key)

        metadata = {
            'cache_key': cache_key,
            'url': url,
            'file_type': file_type,
            'file_size': file_size,
            'download_time': datetime.now().isoformat(),
            'ttl_hours': self.cache_ttl_hours,
        }

        try:
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            self.logger.info(f"Metadata saved: {metadata_path}")
        except IOError as e:
            self.logger.error(f"Failed to save metadata: {e}")

    def _validate_file(self, file_path: Path) -> bool:
        """
        Validate that downloaded file is complete and not corrupted.

        Args:
            file_path: Path to downloaded file

        Returns:
            True if valid, False otherwise
        """
        if not file_path.exists():
            self.logger.error(f"File does not exist: {file_path}")
            return False

        file_size = file_path.stat().st_size
        if file_size == 0:
            self.logger.error(f"File is empty: {file_path}")
            return False

        # Basic magic number validation for common formats
        try:
            with open(file_path, 'rb') as f:
                magic = f.read(12)

            # Check for common file signatures
            valid_signatures = [
                b'\xFF\xD8\xFF',  # JPEG
                b'\x89PNG',        # PNG
                b'GIF8',           # GIF
                b'RIFF',           # WEBP (and AVI)
                b'\x00\x00\x00\x14ftypmp4',  # MP4 (partial)
                b'\x00\x00\x00\x18ftypmp4',  # MP4 (partial)
                b'\x00\x00\x00\x1Cftypmp4',  # MP4 (partial)
                b'\x00\x00\x00\x20ftypmp4',  # MP4 (partial)
            ]

            # Check if file starts with any known signature
            for sig in valid_signatures:
                if magic.startswith(sig):
                    self.logger.info(f"File validated: {file_path} ({file_size} bytes)")
                    return True

            # If we can't identify it but it has content, assume it's valid
            self.logger.warning(f"Unknown file signature, but file has content: {file_path}")
            return True

        except IOError as e:
            self.logger.error(f"Failed to validate file: {e}")
            return False

    def _download_with_retry(
        self,
        url: str,
        cache_path: Path,
        extension: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Download file with retry logic and exponential backoff.

        Args:
            url: Media URL
            cache_path: Destination path for cached file
            extension: File extension

        Returns:
            Tuple of (success: bool, error_message: Optional[str])
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                self.logger.info(f"Download attempt {attempt}/{self.MAX_RETRIES}: {url}")

                # Make HTTP request with streaming
                response = requests.get(
                    url,
                    stream=True,
                    timeout=30,
                    headers={'User-Agent': 'Mozilla/5.0 (compatible; MediaDownloader/1.0)'}
                )
                response.raise_for_status()

                # Get total file size for progress bar
                total_size = int(response.headers.get('content-length', 0))

                # Download to temporary file (atomic write)
                temp_fd, temp_path = tempfile.mkstemp(
                    suffix=extension,
                    dir=self.cache_dir,
                    prefix='download_'
                )

                try:
                    with os.fdopen(temp_fd, 'wb') as temp_file:
                        # Create progress bar
                        with tqdm(
                            total=total_size,
                            unit='B',
                            unit_scale=True,
                            unit_divisor=1024,
                            desc=f"Downloading {cache_path.name}",
                            disable=total_size == 0  # Disable if size unknown
                        ) as pbar:
                            for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                                if chunk:
                                    temp_file.write(chunk)
                                    pbar.update(len(chunk))

                    # Validate temporary file
                    temp_path_obj = Path(temp_path)
                    if not self._validate_file(temp_path_obj):
                        os.unlink(temp_path)
                        raise ValueError("Downloaded file failed validation")

                    # Atomic rename to final location
                    shutil.move(temp_path, cache_path)
                    self.logger.info(f"Download successful: {cache_path}")
                    return True, None

                except Exception as e:
                    # Clean up temp file on error
                    if os.path.exists(temp_path):
                        os.unlink(temp_path)
                    raise e

            except requests.exceptions.HTTPError as e:
                error_msg = f"HTTP error: {e.response.status_code} - {url}"
                self.logger.error(error_msg)

                # Don't retry on 404 or 403
                if e.response.status_code in [403, 404]:
                    return False, error_msg

            except requests.exceptions.ConnectionError as e:
                error_msg = f"Connection error: {str(e)}"
                self.logger.error(error_msg)

            except requests.exceptions.Timeout as e:
                error_msg = f"Request timeout: {str(e)}"
                self.logger.error(error_msg)

            except Exception as e:
                error_msg = f"Unexpected error: {str(e)}"
                self.logger.error(error_msg)

            # Exponential backoff before retry
            if attempt < self.MAX_RETRIES:
                delay = self.INITIAL_RETRY_DELAY * (2 ** (attempt - 1))
                self.logger.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)

        # All retries failed
        final_error = f"Failed to download after {self.MAX_RETRIES} attempts: {url}"
        self.logger.error(final_error)
        return False, final_error

    def download_media(
        self,
        url: str,
        cache_dir: Optional[str] = None
    ) -> Optional[str]:
        """
        Download media from URL with caching support.

        Args:
            url: Media URL (image or video)
            cache_dir: Optional custom cache directory (overrides config)

        Returns:
            Local file path if successful, None if failed

        Example:
            downloader = MediaDownloader(config_path='video_config.json')
            local_path = downloader.download_media('https://video.twimg.com/...')
        """
        # Override cache directory if provided
        if cache_dir:
            original_cache_dir = self.cache_dir
            self.cache_dir = Path(cache_dir)
            self.cache_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Generate cache key
            cache_key = self._generate_cache_key(url)

            # Get file extension (quick HEAD request to check content type)
            try:
                head_response = requests.head(url, timeout=10, allow_redirects=True)
                content_type = head_response.headers.get('content-type', '')
                extension = self._get_file_extension(url, content_type)
            except Exception:
                # Fallback to URL-based extension
                extension = self._get_file_extension(url)

            # Check cache
            if self._is_cached(cache_key, extension):
                cache_path = self._get_cache_path(cache_key, extension)
                self.logger.info(f"Returning cached file: {cache_path}")
                return str(cache_path)

            # Download file
            cache_path = self._get_cache_path(cache_key, extension)
            success, error = self._download_with_retry(url, cache_path, extension)

            if not success:
                print(f"ERROR: {error}")
                return None

            # Determine file type
            file_type = 'video' if extension in self.SUPPORTED_VIDEO_FORMATS else 'image'
            file_size = cache_path.stat().st_size

            # Save metadata
            self._save_metadata(cache_key, url, file_type, file_size)

            return str(cache_path)

        finally:
            # Restore original cache directory if it was overridden
            if cache_dir:
                self.cache_dir = original_cache_dir

    def clear_expired_cache(self):
        """Remove expired cached files based on TTL."""
        removed_count = 0

        for metadata_path in self.cache_dir.glob('*.json'):
            try:
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)

                download_time = datetime.fromisoformat(metadata['download_time'])
                expiry_time = download_time + timedelta(hours=self.cache_ttl_hours)

                if datetime.now() > expiry_time:
                    # Remove media file
                    cache_key = metadata['cache_key']
                    for cache_file in self.cache_dir.glob(f"{cache_key}.*"):
                        if cache_file != metadata_path:
                            cache_file.unlink()
                            self.logger.info(f"Removed expired cache: {cache_file}")

                    # Remove metadata file
                    metadata_path.unlink()
                    removed_count += 1

            except Exception as e:
                self.logger.warning(f"Failed to process {metadata_path}: {e}")

        self.logger.info(f"Cleared {removed_count} expired cache entries")
        return removed_count


def main():
    """Example usage of MediaDownloader."""
    # Example URLs (replace with actual URLs)
    example_urls = [
        "https://pbs.twimg.com/media/example.jpg",
        "https://video.twimg.com/ext_tw_video/example.mp4",
    ]

    # Initialize downloader
    downloader = MediaDownloader(config_path='video_config.json')

    # Download media
    for url in example_urls:
        print(f"\nDownloading: {url}")
        local_path = downloader.download_media(url)

        if local_path:
            print(f"✓ Downloaded to: {local_path}")
        else:
            print(f"✗ Failed to download")

    # Clear expired cache
    print(f"\nClearing expired cache...")
    removed = downloader.clear_expired_cache()
    print(f"Removed {removed} expired entries")


if __name__ == '__main__':
    main()
