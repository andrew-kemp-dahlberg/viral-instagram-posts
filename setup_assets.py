#!/usr/bin/env python3
"""
Asset Setup and Validation for Video Generation

This script validates the environment and assets needed for Instagram Reel video generation:
- Checks FFmpeg installation
- Validates system fonts
- Creates required directory structure
- Provides instructions for creating tweet box assets

Usage:
    python setup_assets.py
"""

import os
import sys
import json
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class AssetSetup:
    """Handles asset validation and setup for video generation."""

    def __init__(self, config_file: str = "video_config.json"):
        """
        Initialize asset setup with configuration.

        Args:
            config_file: Path to video configuration JSON file
        """
        self.config_file = config_file
        self.config = self._load_config()
        self.validation_results = {
            "ffmpeg": False,
            "fonts": False,
            "directories": False,
            "tweet_boxes": False
        }

    def _load_config(self) -> Dict:
        """Load video configuration from JSON file."""
        if not os.path.exists(self.config_file):
            raise FileNotFoundError(
                f"Configuration file not found: {self.config_file}\n"
                "Please ensure video_config.json exists in the project directory."
            )

        with open(self.config_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def check_ffmpeg(self) -> Tuple[bool, str]:
        """
        Check if FFmpeg is installed and accessible in PATH.

        Returns:
            Tuple of (is_installed, version_or_error_message)
        """
        print("\n🔍 Checking FFmpeg installation...")

        try:
            # Check if ffmpeg is in PATH
            result = subprocess.run(
                ['ffmpeg', '-version'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                # Extract version from first line
                version_line = result.stdout.split('\n')[0]
                print(f"   ✅ FFmpeg found: {version_line}")
                self.validation_results["ffmpeg"] = True
                return True, version_line
            else:
                error_msg = "FFmpeg command failed"
                print(f"   ❌ {error_msg}")
                return False, error_msg

        except FileNotFoundError:
            error_msg = "FFmpeg not found in PATH"
            print(f"   ❌ {error_msg}")
            print("\n   Installation instructions:")
            print("   • macOS: brew install ffmpeg")
            print("   • Ubuntu/Debian: sudo apt install ffmpeg")
            print("   • Windows: Download from https://ffmpeg.org/download.html")
            return False, error_msg

        except subprocess.TimeoutExpired:
            error_msg = "FFmpeg check timed out"
            print(f"   ❌ {error_msg}")
            return False, error_msg

        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            print(f"   ❌ {error_msg}")
            return False, error_msg

    def check_fonts(self) -> Tuple[bool, List[str]]:
        """
        Check for available system fonts matching configuration.

        Returns:
            Tuple of (fonts_available, list_of_available_fonts)
        """
        print("\n🔍 Checking system fonts...")

        font_config = self.config.get("assets", {}).get("fonts", {}).get("hook_text", {})
        primary_font = font_config.get("family", "Arial")
        fallback_fonts = font_config.get("fallbacks", [])
        all_fonts = [primary_font] + fallback_fonts

        available_fonts = []

        # Try to get font list using fc-list (Linux/macOS)
        try:
            result = subprocess.run(
                ['fc-list', ':', 'family'],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                installed_fonts = set()
                for line in result.stdout.split('\n'):
                    # Extract font families (can have multiple per line)
                    families = line.split(',')
                    for family in families:
                        installed_fonts.add(family.strip().lower())

                # Check which configured fonts are available
                for font in all_fonts:
                    if font.lower() in installed_fonts:
                        available_fonts.append(font)
                        print(f"   ✅ Font available: {font}")

        except (FileNotFoundError, subprocess.TimeoutExpired):
            # fc-list not available, try alternative methods
            print("   ⚠️  fc-list not available, checking for common fonts...")

            # On macOS, check common font directories
            if sys.platform == "darwin":
                font_dirs = [
                    "/System/Library/Fonts",
                    "/Library/Fonts",
                    os.path.expanduser("~/Library/Fonts")
                ]

                for font_dir in font_dirs:
                    if os.path.exists(font_dir):
                        for font in all_fonts:
                            # Check for .ttf or .otf files matching font name
                            font_files = list(Path(font_dir).glob(f"**/{font}*.ttf")) + \
                                       list(Path(font_dir).glob(f"**/{font}*.otf"))
                            if font_files and font not in available_fonts:
                                available_fonts.append(font)
                                print(f"   ✅ Font available: {font}")

        # Provide status and recommendations
        if available_fonts:
            print(f"\n   ✅ Found {len(available_fonts)} usable font(s)")
            self.validation_results["fonts"] = True
            return True, available_fonts
        else:
            print("\n   ⚠️  No configured fonts found on system")
            print(f"   Recommended: Install one of {all_fonts}")
            print("\n   Installation instructions:")
            print("   • macOS: Fonts usually pre-installed")
            print("   • Ubuntu/Debian: sudo apt install fonts-liberation")
            print("   • Or download from Google Fonts: https://fonts.google.com")
            return False, []

    def create_directories(self) -> bool:
        """
        Create required directory structure from configuration.

        Returns:
            True if all directories created successfully
        """
        print("\n🔍 Creating directory structure...")

        paths = self.config.get("paths", {})
        dirs_to_create = [
            paths.get("assets_dir", "assets"),
            paths.get("tweet_boxes_dir", "assets/tweet_boxes"),
            paths.get("fonts_dir", "assets/fonts"),
            paths.get("cache_dir", "cache"),
            paths.get("media_cache_dir", "cache/media"),
            paths.get("output_dir", "output")
        ]

        try:
            for directory in dirs_to_create:
                Path(directory).mkdir(parents=True, exist_ok=True)
                print(f"   ✅ Created/verified: {directory}/")

            self.validation_results["directories"] = True
            return True

        except Exception as e:
            print(f"   ❌ Error creating directories: {str(e)}")
            return False

    def check_tweet_boxes(self) -> Tuple[bool, List[str]]:
        """
        Check for tweet box PNG assets.

        Returns:
            Tuple of (all_boxes_present, list_of_missing_boxes)
        """
        print("\n🔍 Checking tweet box assets...")

        tweet_boxes = self.config.get("assets", {}).get("tweet_boxes", {})
        missing_boxes = []

        for box_name, box_path in tweet_boxes.items():
            if os.path.exists(box_path):
                # Check if it's a valid PNG (case-insensitive)
                if box_path.lower().endswith('.png'):
                    file_size = os.path.getsize(box_path)
                    print(f"   ✅ Found: {box_path} ({file_size:,} bytes)")
                else:
                    print(f"   ⚠️  Found but not PNG: {box_path}")
                    missing_boxes.append(box_name)
            else:
                print(f"   ❌ Missing: {box_path}")
                missing_boxes.append(box_name)

        if not missing_boxes:
            self.validation_results["tweet_boxes"] = True
            return True, []
        else:
            return False, missing_boxes

    def generate_tweet_box_instructions(self):
        """
        Print detailed instructions for creating tweet box PNG assets.
        """
        print("\n" + "=" * 60)
        print("📋 TWEET BOX CREATION INSTRUCTIONS")
        print("=" * 60)

        video_res = self.config.get("video", {}).get("resolution", {})
        width = video_res.get("width", 2160)
        height = video_res.get("height", 3840)

        print(f"\nYou need to create 3 PNG images for tweet boxes:")
        print(f"Video resolution: {width}x{height} (9:16 vertical)")
        print("\nRecommended tweet box specs:")
        print(f"  • Size: {int(width * 0.9)}x{int(height * 0.2)} pixels (approx)")
        print("  • Format: PNG with transparency")
        print("  • Background: White with rounded corners")
        print("  • Border: Optional subtle shadow/border")
        print("  • Text area: Leave space for tweet text")

        tweet_boxes = self.config.get("assets", {}).get("tweet_boxes", {})
        print("\nRequired files:")
        for box_name, box_path in tweet_boxes.items():
            lines = box_name.replace('_', ' ').title()
            print(f"\n  {box_name}:")
            print(f"    Path: {box_path}")
            print(f"    Purpose: {lines} tweet box")
            print(f"    Height: Adjust based on {lines} of text")

        print("\n" + "=" * 60)
        print("📐 Creation Tools:")
        print("=" * 60)
        print("  • Figma (recommended): https://figma.com")
        print("  • Photoshop: Use artboard tool")
        print("  • GIMP: Free alternative")
        print("  • Canva: Online design tool")

        print("\n" + "=" * 60)
        print("💡 Tips:")
        print("=" * 60)
        print("  • Use Twitter/X UI as reference")
        print("  • Keep design clean and minimal")
        print("  • Ensure text is readable at small sizes")
        print("  • Save as PNG with transparency")
        print("  • Test with different text lengths")
        print("=" * 60 + "\n")

    def run_full_check(self) -> bool:
        """
        Run all validation checks and print summary.

        Returns:
            True if all checks pass
        """
        print("=" * 60)
        print("🚀 Video Generation Asset Setup & Validation")
        print("=" * 60)

        # Run all checks
        self.check_ffmpeg()
        self.check_fonts()
        self.create_directories()
        boxes_ok, missing_boxes = self.check_tweet_boxes()

        # Print summary
        print("\n" + "=" * 60)
        print("📊 VALIDATION SUMMARY")
        print("=" * 60)

        all_passed = True
        for check_name, passed in self.validation_results.items():
            status = "✅ PASS" if passed else "❌ FAIL"
            print(f"  {check_name.replace('_', ' ').title()}: {status}")
            if not passed:
                all_passed = False

        # Generate instructions for missing assets
        if missing_boxes:
            self.generate_tweet_box_instructions()

        print("\n" + "=" * 60)
        if all_passed:
            print("✨ All checks passed! Ready for video generation.")
        else:
            print("⚠️  Some checks failed. Please address issues above.")
        print("=" * 60 + "\n")

        return all_passed


def main():
    """Main entry point for asset setup."""
    try:
        setup = AssetSetup()
        success = setup.run_full_check()
        sys.exit(0 if success else 1)

    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
