#!/usr/bin/env python3
"""
FFmpeg Video Generator - Core video processing engine

Replicates CapCut workflow using FFmpeg to create viral Instagram Reels:
- 9:16 aspect ratio (4K vertical)
- Blurred background effect
- Tweet box overlay with auto-selection based on line count
- Text overlay with styling
- Sharpening and clarity effects

Usage:
    generator = FFmpegGenerator(config_path='video_config.json')
    generator.generate_single_variant(
        media_path='./cache/media/abc123.mp4',
        hook_text='Bro just casually made the shot of the year 😭',
        output_path='./output/test/variant_1.mp4'
    )
"""

import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Dict, Optional, Tuple


class FFmpegGenerator:
    """
    FFmpeg-based video generator for Instagram Reels.

    Features:
    - Single-pass filter_complex for all effects
    - Auto-detects hook line count for tweet box selection
    - Handles both video and image inputs
    - Configurable via video_config.json
    - Progress output parsing
    - Dry-run mode for command preview
    """

    # Supported media formats
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.webm', '.m4v'}

    # Image duration when converting static images to video
    IMAGE_DURATION = 10.0  # seconds

    def __init__(self, config_path: str = 'video_config.json'):
        """
        Initialize FFmpegGenerator with configuration.

        Args:
            config_path: Path to video_config.json configuration file

        Raises:
            FileNotFoundError: If FFmpeg is not found in PATH
            RuntimeError: If configuration is invalid
        """
        # Set up logging
        self._setup_logging()

        # Load configuration
        self.config = self._load_config(config_path)

        # Validate FFmpeg availability
        self._validate_ffmpeg()

        # Extract commonly used config values
        self.video_width = self.config['video']['resolution']['width']
        self.video_height = self.config['video']['resolution']['height']
        self.framerate = self.config['video']['framerate']
        self.crf = self.config['video']['encoding'].get('crf', 18)
        self.preset = self.config['video']['encoding'].get('preset', 'medium')
        self.codec = self.config['video']['encoding']['codec']
        self.quality = self.config['video']['encoding'].get('quality', 65)
        self.bitrate = self.config['video']['encoding'].get('bitrate', '10M')

        # Effect parameters
        self.blur_sigma = self.config['effects']['background_blur']['sigma']
        self.media_max_width_pct = self.config['effects']['media_scaling']['max_width_percent']
        self.media_max_height_pct = self.config['effects']['media_scaling']['max_height_percent']

        # Position settings
        self.hook_text_y = self.config['positions']['hook_text']['y']
        self.hook_text_max_width = self.config['positions']['hook_text']['max_width']

        # Tweet box paths
        self.tweet_boxes = self.config['assets']['tweet_boxes']

        # Font settings
        self.font_config = self.config['assets']['fonts']['hook_text']

        self.logger.info("FFmpegGenerator initialized successfully")
        self.logger.info(f"Output resolution: {self.video_width}x{self.video_height} @ {self.framerate}fps")

    def _setup_logging(self):
        """Configure logging to file and console."""
        self.logger = logging.getLogger('FFmpegGenerator')
        self.logger.setLevel(logging.INFO)

        # Remove existing handlers to avoid duplicates
        self.logger.handlers.clear()

        # File handler
        log_file = 'video_generation.log'
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        self.logger.addHandler(file_handler)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        console_formatter = logging.Formatter('%(levelname)s: %(message)s')
        console_handler.setFormatter(console_formatter)
        self.logger.addHandler(console_handler)

    def _load_config(self, config_path: str) -> Dict:
        """Load video configuration from JSON file."""
        try:
            with open(config_path, 'r') as f:
                config = json.load(f)
            self.logger.info(f"Configuration loaded from {config_path}")
            return config
        except FileNotFoundError:
            raise FileNotFoundError(
                f"Configuration file not found: {config_path}\n"
                "Please ensure video_config.json exists in the project directory."
            )
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON in configuration file: {e}")

    def _validate_ffmpeg(self):
        """
        Validate that FFmpeg is installed and accessible.

        Raises:
            FileNotFoundError: If FFmpeg is not found in PATH
        """
        try:
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                version_line = result.stdout.split('\n')[0]
                self.logger.info(f"FFmpeg found: {version_line}")
            else:
                raise RuntimeError("FFmpeg command failed")

        except FileNotFoundError:
            raise FileNotFoundError(
                "FFmpeg not found in PATH. Please install FFmpeg:\n"
                "  • macOS: brew install ffmpeg\n"
                "  • Ubuntu/Debian: sudo apt install ffmpeg\n"
                "  • Windows: Download from https://ffmpeg.org/download.html"
            )
        except subprocess.TimeoutExpired:
            raise RuntimeError("FFmpeg validation timed out")

    def _detect_media_type(self, media_path: str) -> str:
        """
        Detect if media is an image or video.

        Args:
            media_path: Path to media file

        Returns:
            'image' or 'video'

        Raises:
            ValueError: If media format is not supported
        """
        ext = Path(media_path).suffix.lower()

        if ext in self.IMAGE_EXTENSIONS:
            return 'image'
        elif ext in self.VIDEO_EXTENSIONS:
            return 'video'
        else:
            raise ValueError(
                f"Unsupported media format: {ext}\n"
                f"Supported images: {self.IMAGE_EXTENSIONS}\n"
                f"Supported videos: {self.VIDEO_EXTENSIONS}"
            )

    def _count_lines(self, text: str) -> int:
        """
        Count number of lines in hook text.

        Args:
            text: Hook text

        Returns:
            Number of lines (1, 2, or 3)
        """
        # Count newlines and add 1
        newline_count = text.count('\n')
        line_count = newline_count + 1

        # Cap at 3 lines (use 3-liner box for anything longer)
        return min(line_count, 3)

    def _select_tweet_box(self, hook_text: str) -> str:
        """
        Select appropriate tweet box PNG based on line count.

        Args:
            hook_text: Hook text to analyze

        Returns:
            Path to tweet box PNG file

        Raises:
            FileNotFoundError: If tweet box file doesn't exist
        """
        line_count = self._count_lines(hook_text)

        # Map line count to config key
        box_key = f"{line_count}_liner"
        box_path = self.tweet_boxes.get(box_key)

        if not box_path:
            raise ValueError(f"No tweet box configured for {line_count} lines")

        if not os.path.exists(box_path):
            raise FileNotFoundError(
                f"Tweet box not found: {box_path}\n"
                f"Run 'python setup_assets.py' for setup instructions."
            )

        self.logger.info(f"Selected tweet box: {box_path} ({line_count} lines)")
        return box_path

    def _find_system_font(self) -> Optional[str]:
        """
        Find available system font from configuration.

        Searches common font directories for the configured font.
        Returns full path to font file if found, otherwise None.

        Returns:
            Path to font file or None if not found
        """
        primary_font = self.font_config.get('family', 'Arial')
        fallbacks = self.font_config.get('fallbacks', [])
        all_fonts = [primary_font] + fallbacks

        # Common font directories by platform
        font_dirs = []
        if sys.platform == 'darwin':  # macOS
            font_dirs = [
                '/System/Library/Fonts',
                '/Library/Fonts',
                os.path.expanduser('~/Library/Fonts'),
                '/System/Library/Fonts/Supplemental'
            ]
        elif sys.platform.startswith('linux'):
            font_dirs = [
                '/usr/share/fonts',
                '/usr/local/share/fonts',
                os.path.expanduser('~/.fonts'),
                os.path.expanduser('~/.local/share/fonts')
            ]
        elif sys.platform == 'win32':
            font_dirs = [
                'C:\\Windows\\Fonts',
                os.path.expanduser('~\\AppData\\Local\\Microsoft\\Windows\\Fonts')
            ]

        # Search for fonts
        for font_name in all_fonts:
            for font_dir in font_dirs:
                if not os.path.exists(font_dir):
                    continue

                # Search for .ttf and .otf files matching font name
                for ext in ['ttf', 'otf', 'TTF', 'OTF']:
                    # Try exact match
                    font_path = Path(font_dir) / f"{font_name}.{ext}"
                    if font_path.exists():
                        self.logger.info(f"Found font: {font_path}")
                        return str(font_path)

                    # Try case-insensitive glob search
                    matches = list(Path(font_dir).rglob(f"*{font_name}*.{ext}"))
                    if matches:
                        font_path = matches[0]
                        self.logger.info(f"Found font: {font_path}")
                        return str(font_path)

        # No font found
        self.logger.warning(
            f"No font found from {all_fonts}. "
            "Falling back to FFmpeg default font."
        )
        return None

    def _escape_text_for_ffmpeg(self, text: str) -> str:
        """
        Escape text for FFmpeg drawtext filter.

        FFmpeg drawtext requires specific escaping:
        - Single quotes: \\'
        - Colons: \\:
        - Backslashes: \\\\
        - Newlines: \\n (keep for line breaks)

        Args:
            text: Original text

        Returns:
            Escaped text safe for FFmpeg
        """
        # Replace in specific order to avoid double-escaping
        text = text.replace('\\', '\\\\')  # Backslashes first
        text = text.replace("'", "\\'")    # Single quotes
        text = text.replace(':', '\\:')    # Colons
        # Keep newlines as \n for line breaks in drawtext
        return text

    def _build_ffmpeg_command(
        self,
        media_path: str,
        hook_text: str,
        tweet_box_path: str,
        output_path: str,
        media_type: str
    ) -> list:
        """
        Build complete FFmpeg command with filter_complex.

        Args:
            media_path: Path to input media file
            hook_text: Hook text to overlay
            tweet_box_path: Path to tweet box PNG
            output_path: Path to output video file
            media_type: 'image' or 'video'

        Returns:
            List of command arguments for subprocess
        """
        # Calculate media scaling dimensions
        media_max_width = int(self.video_width * (self.media_max_width_pct / 100))
        media_max_height = int(self.video_height * (self.media_max_height_pct / 100))

        # Escape hook text for drawtext
        escaped_hook = self._escape_text_for_ffmpeg(hook_text)

        # Find system font
        font_path = self._find_system_font()

        # Build input arguments
        input_args = []

        # Input 0: Main media (with loop for images)
        if media_type == 'image':
            input_args.extend([
                '-loop', '1',
                '-t', str(self.IMAGE_DURATION),
                '-i', media_path
            ])
        else:
            input_args.extend(['-i', media_path])

        # Input 1: Tweet box PNG
        input_args.extend(['-loop', '1', '-i', tweet_box_path])

        # Build filter_complex chain
        # This replicates the CapCut workflow in a single pass
        filter_complex = (
            # Step 1: Create blurred background (scale to fill, then blur)
            f"[0:v]scale={self.video_width}:{self.video_height}:"
            f"force_original_aspect_ratio=increase,"
            f"crop={self.video_width}:{self.video_height}[bg];"

            # Step 2: Apply Gaussian blur to background
            f"[bg]gblur=sigma={self.blur_sigma}[blurred];"

            # Step 3: Scale main media to fit within bounds
            f"[0:v]scale={media_max_width}:{media_max_height}:"
            f"force_original_aspect_ratio=decrease[media];"

            # Step 4: Overlay media on blurred background (centered)
            f"[blurred][media]overlay=(W-w)/2:(H-h)/2[with_media];"

            # Step 5: Apply sharpening (unsharp: 11:11:1.5)
            f"[with_media]unsharp=11:11:1.5[sharpened];"

            # Step 6: Apply clarity (eq: brightness=0.02:contrast=1.2)
            f"[sharpened]eq=brightness=0.02:contrast=1.2[enhanced];"

            # Step 7: Overlay tweet box (centered)
            f"[enhanced][1:v]overlay=(W-w)/2:(H-h)/2[with_box];"

            # Step 8: Add hook text overlay
        )

        # Build drawtext filter
        drawtext_filter = "[with_box]drawtext="
        if font_path:
            drawtext_filter += f"fontfile={font_path}:"
        drawtext_filter += (
            f"text='{escaped_hook}':"
            f"fontsize=72:"
            f"fontcolor=black:"
            f"x=(w-text_w)/2:"
            f"y={self.hook_text_y}:"
            f"line_spacing=10[final]"
        )

        # Append drawtext to filter_complex
        filter_complex += drawtext_filter

        # Build complete command
        command = [
            'ffmpeg',
            '-y',  # Overwrite output file
            *input_args,
            '-filter_complex', filter_complex,
            '-map', '[final]',

            # Video encoding settings
            '-c:v', self.codec,
        ]

        # Add codec-specific parameters
        if 'videotoolbox' in self.codec.lower():
            # Hardware acceleration (VideoToolbox) uses quality and bitrate
            command.extend([
                '-q:v', str(self.quality),  # Quality: 1-100, higher=better
                '-b:v', self.bitrate,  # Bitrate for quality control
            ])
            self.logger.info(f"Using hardware acceleration: {self.codec} (quality={self.quality}, bitrate={self.bitrate})")
        else:
            # Software encoding (libx264) uses preset and CRF
            command.extend([
                '-preset', self.preset,
                '-crf', str(self.crf),
            ])
            self.logger.info(f"Using software encoding: {self.codec} (preset={self.preset}, crf={self.crf})")

        # Common encoding settings
        command.extend([
            '-r', str(self.framerate),
            '-pix_fmt', 'yuv420p',  # Compatibility with most players

            # Audio handling (copy if exists, otherwise no audio)
            '-c:a', 'aac',
            '-b:a', self.config['video']['audio']['bitrate'],
            '-shortest',  # Match shortest stream (important for looped inputs)

            output_path
        ])

        return command

    def _run_ffmpeg_command(
        self,
        command: list,
        dry_run: bool = False
    ) -> Tuple[bool, str]:
        """
        Execute FFmpeg command and parse output.

        Args:
            command: FFmpeg command as list of arguments
            dry_run: If True, only print command without executing

        Returns:
            Tuple of (success, error_message)
        """
        # Log command preview
        command_str = ' '.join(command)
        self.logger.info(f"FFmpeg command: {command_str}")

        if dry_run:
            print("\n" + "="*60)
            print("DRY RUN - Command Preview")
            print("="*60)
            print(command_str)
            print("="*60 + "\n")
            return True, ""

        try:
            # Run FFmpeg with real-time output
            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            # Parse and display progress
            output_lines = []
            for line in process.stdout:
                output_lines.append(line)

                # FFmpeg outputs progress to stderr, captured in stdout here
                # Look for time= to show progress
                if 'frame=' in line or 'time=' in line:
                    # Extract progress info
                    print(f"\r{line.strip()}", end='', flush=True)

            process.wait()

            if process.returncode == 0:
                print()  # New line after progress
                self.logger.info("FFmpeg command completed successfully")
                return True, ""
            else:
                error_msg = ''.join(output_lines[-20:])  # Last 20 lines
                self.logger.error(f"FFmpeg failed with return code {process.returncode}")
                self.logger.error(f"Error output:\n{error_msg}")
                return False, error_msg

        except FileNotFoundError:
            error_msg = "FFmpeg executable not found"
            self.logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"Unexpected error running FFmpeg: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg

    def generate_single_variant(
        self,
        media_path: str,
        hook_text: str,
        output_path: str,
        dry_run: bool = False
    ) -> bool:
        """
        Generate a single video variant with hook text overlay.

        This is the main entry point that orchestrates the entire workflow:
        1. Validate inputs
        2. Detect media type (image/video)
        3. Select appropriate tweet box based on line count
        4. Build FFmpeg filter_complex command
        5. Execute FFmpeg

        Args:
            media_path: Path to input media file (image or video)
            hook_text: Hook text to overlay on video
            output_path: Path to output video file
            dry_run: If True, only preview command without executing

        Returns:
            True if generation successful, False otherwise

        Example:
            generator = FFmpegGenerator()
            success = generator.generate_single_variant(
                media_path='./cache/media/abc123.mp4',
                hook_text='Bro just casually made the shot of the year 😭',
                output_path='./output/test/variant_1.mp4'
            )
        """
        self.logger.info("="*60)
        self.logger.info("Starting video generation")
        self.logger.info(f"Media: {media_path}")
        self.logger.info(f"Hook: {hook_text}")
        self.logger.info(f"Output: {output_path}")
        self.logger.info("="*60)

        # Validate inputs
        if not os.path.exists(media_path):
            self.logger.error(f"Media file not found: {media_path}")
            return False

        # Detect media type
        try:
            media_type = self._detect_media_type(media_path)
            self.logger.info(f"Detected media type: {media_type}")
        except ValueError as e:
            self.logger.error(str(e))
            return False

        # Select tweet box
        try:
            tweet_box_path = self._select_tweet_box(hook_text)
        except (ValueError, FileNotFoundError) as e:
            self.logger.error(str(e))
            return False

        # Create output directory if needed
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)

        # Build FFmpeg command
        command = self._build_ffmpeg_command(
            media_path=media_path,
            hook_text=hook_text,
            tweet_box_path=tweet_box_path,
            output_path=output_path,
            media_type=media_type
        )

        # Execute command
        success, error = self._run_ffmpeg_command(command, dry_run=dry_run)

        if success and not dry_run:
            # Verify output file was created
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path)
                self.logger.info(f"Video generated successfully: {output_path}")
                self.logger.info(f"File size: {file_size:,} bytes ({file_size/1024/1024:.2f} MB)")
            else:
                self.logger.error("Output file not created despite successful FFmpeg execution")
                return False

        return success


def main():
    """Example usage and testing."""
    import argparse

    parser = argparse.ArgumentParser(
        description='Generate Instagram Reel video with FFmpeg'
    )
    parser.add_argument(
        'media_path',
        help='Path to input media file (image or video)'
    )
    parser.add_argument(
        'hook_text',
        help='Hook text to overlay on video'
    )
    parser.add_argument(
        'output_path',
        help='Path to output video file'
    )
    parser.add_argument(
        '--config',
        default='video_config.json',
        help='Path to video_config.json (default: video_config.json)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview FFmpeg command without executing'
    )

    args = parser.parse_args()

    try:
        # Initialize generator
        generator = FFmpegGenerator(config_path=args.config)

        # Generate video
        success = generator.generate_single_variant(
            media_path=args.media_path,
            hook_text=args.hook_text,
            output_path=args.output_path,
            dry_run=args.dry_run
        )

        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
