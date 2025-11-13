#!/usr/bin/env python3
"""
Orchestrator for Viral Instagram Posts Pipeline

This script automates the entire workflow for creating viral Instagram content:
1. Scrape trending tweets from Twitter/X using Apify
2. Add AI-generated descriptions to media (GPT-4o for images, Gemini for videos)
3. Generate 10 viral Instagram hooks per tweet using Claude AI
4. Collect user's top 3 hook selections via Slack (or auto-select)
5. Download and cache all media files locally
6. Validate video generation assets (FFmpeg, fonts, tweet boxes)
7. Generate Instagram Reel videos for all selected hooks

Usage:
    # Run full pipeline with defaults
    python orchestrator.py

    # Run with custom config
    python orchestrator.py --config orchestrator_config.json

    # Skip Slack selection (auto-select first 3 hooks)
    python orchestrator.py --skip-slack

    # Dry run (validate setup without executing)
    python orchestrator.py --dry-run

    # Resume from a specific stage
    python orchestrator.py --resume-from media_download

Example:
    python orchestrator.py --config my_config.json --skip-slack

Output:
    - orchestrator_output_{timestamp}.json: Final JSON with all data and local media paths
    - orchestrator.log: Detailed execution log
    - cache/media/*: Downloaded media files
    - intermediate/*: Intermediate JSON files from each stage (if enabled)
    - output/*.mp4: Generated Instagram Reel videos
"""

import os
import sys
import json
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dotenv import load_dotenv
from tqdm import tqdm

# Import existing pipeline components
from scraper import TwitterTrendingScraper
from add_media_descriptions import MediaDescriptionGenerator
from hook_creation import HookGenerator
from slack_integration import SlackIntegration
from media_downloader import MediaDownloader
from setup_assets import AssetSetup
from ffmpeg_generator import FFmpegGenerator


class PipelineOrchestrator:
    """
    Orchestrates the entire viral Instagram posts pipeline.

    Manages the execution of all pipeline stages, handles errors gracefully,
    provides progress updates, validates prerequisites, and ensures proper
    data flow between stages.
    """

    STAGES = [
        "scraper",
        "media_descriptions",
        "hook_generation",
        "slack_integration",
        "media_download",
        "asset_setup",
        "video_generation"
    ]

    def __init__(self, config_path: str = "orchestrator_config.json"):
        """
        Initialize the orchestrator with configuration.

        Args:
            config_path: Path to the configuration JSON file
        """
        self.config_path = config_path
        self.config = self._load_config()
        self.logger = self._setup_logging()
        self.checkpoint = self._load_checkpoint()
        self.start_time = datetime.now()

        # Track pipeline state
        self.current_stage = None
        self.completed_stages = []
        self.failed_stages = []
        self.data = {}
        self.intermediate_files = []

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            print(f"Error: Configuration file '{self.config_path}' not found.")
            sys.exit(1)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in configuration file: {e}")
            sys.exit(1)

    def _setup_logging(self) -> logging.Logger:
        """Set up logging configuration."""
        log_config = self.config.get("logging", {})
        log_file = log_config.get("log_file", "orchestrator.log")
        log_level = getattr(logging, log_config.get("log_level", "INFO"))

        # Create logger
        logger = logging.getLogger("orchestrator")
        logger.setLevel(log_level)

        # File handler
        fh = logging.FileHandler(log_file)
        fh.setLevel(log_level)
        fh.setFormatter(logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        ))
        logger.addHandler(fh)

        # Console handler (if enabled)
        if log_config.get("console_output", True):
            ch = logging.StreamHandler()
            ch.setLevel(log_level)
            ch.setFormatter(logging.Formatter(
                '%(levelname)s - %(message)s'
            ))
            logger.addHandler(ch)

        return logger

    def _load_checkpoint(self) -> Dict[str, Any]:
        """Load checkpoint data if resume is enabled."""
        resume_config = self.config.get("resume", {})
        if not resume_config.get("enabled", True):
            return {}

        checkpoint_file = resume_config.get("checkpoint_file", "./orchestrator_checkpoint.json")
        if os.path.exists(checkpoint_file):
            try:
                with open(checkpoint_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                self.logger.warning(f"Failed to load checkpoint: {e}")

        return {}

    def _save_checkpoint(self):
        """Save current pipeline state to checkpoint file."""
        resume_config = self.config.get("resume", {})
        if not resume_config.get("enabled", True):
            return

        checkpoint_file = resume_config.get("checkpoint_file", "./orchestrator_checkpoint.json")
        checkpoint_data = {
            "timestamp": datetime.now().isoformat(),
            "current_stage": self.current_stage,
            "completed_stages": self.completed_stages,
            "failed_stages": self.failed_stages,
            "intermediate_files": self.intermediate_files
        }

        try:
            with open(checkpoint_file, 'w') as f:
                json.dump(checkpoint_data, f, indent=2)
        except Exception as e:
            self.logger.warning(f"Failed to save checkpoint: {e}")

    def validate_prerequisites(self, dry_run: bool = False) -> Tuple[bool, List[str]]:
        """
        Validate that all prerequisites are met before running the pipeline.

        Args:
            dry_run: If True, only validate without executing

        Returns:
            Tuple of (success, list of error messages)
        """
        self.logger.info("Validating prerequisites...")
        errors = []

        # Load environment variables
        load_dotenv()

        # Check required API keys
        required_keys = {
            "APIFY_API_TOKEN": "Apify (for Twitter scraping)",
            "OPENAI_API_KEY": "OpenAI (for image descriptions)",
            "GEMINI_API_KEY": "Google Gemini (for video descriptions)",
            "ANTHROPIC_API_KEY": "Anthropic Claude (for hook generation)"
        }

        # Only require Slack keys if Slack integration is enabled
        if self.config.get("slack_integration", {}).get("enabled", True):
            required_keys["SLACK_BOT_TOKEN"] = "Slack Bot (for hook selection)"
            required_keys["SLACK_CHANNEL_ID"] = "Slack Channel (for posting tweets)"

        for key, service in required_keys.items():
            if not os.getenv(key):
                errors.append(f"Missing {key} environment variable (required for {service})")

        # Check output directories exist or can be created
        output_config = self.config.get("output", {})
        directories = [
            output_config.get("directory", "./output"),
            self.config.get("media_download", {}).get("cache_dir", "./cache/media")
        ]

        if output_config.get("save_intermediate_files", True):
            directories.append(output_config.get("intermediate_directory", "./intermediate"))

        for directory in directories:
            try:
                Path(directory).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create directory '{directory}': {e}")

        # Validate configuration values
        scraper_config = self.config.get("scraper", {})
        if not scraper_config.get("topics"):
            errors.append("No topics configured for scraping")

        if scraper_config.get("max_tweets_per_topic", 0) <= 0:
            errors.append("max_tweets_per_topic must be greater than 0")

        # Report results
        if errors:
            self.logger.error("Prerequisite validation failed:")
            for error in errors:
                self.logger.error(f"  - {error}")
            return False, errors
        else:
            self.logger.info("All prerequisites validated successfully ✓")
            return True, []

    def run_stage_scraper(self) -> Optional[str]:
        """
        Stage 1: Scrape trending tweets from Twitter/X.

        Returns:
            Path to output JSON file, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 1: Twitter Scraping")
        self.logger.info("=" * 80)

        try:
            scraper_config = self.config.get("scraper", {})
            topics = scraper_config.get("topics", [])
            max_tweets = scraper_config.get("max_tweets_per_topic", 20)
            search_type = scraper_config.get("search_type", "Top")

            self.logger.info(f"Topics: {', '.join(topics)}")
            self.logger.info(f"Max tweets per topic: {max_tweets}")
            self.logger.info(f"Search type: {search_type}")

            # Initialize scraper
            apify_token = os.getenv("APIFY_API_TOKEN")
            scraper = TwitterTrendingScraper(apify_token)

            # Scrape tweets for all topics
            all_results = {}
            for topic in tqdm(topics, desc="Scraping topics"):
                self.logger.info(f"Scraping tweets for topic: '{topic}'")
                results = scraper.search_trending_tweets(
                    topics=[topic],
                    max_tweets=max_tweets,
                    search_type=search_type
                )
                all_results[topic] = results.get(topic, [])

            # Apply engagement filters
            min_engagement = scraper_config.get("min_engagement", {})
            filtered_results = {}
            total_before = sum(len(tweets) for tweets in all_results.values())

            for topic, tweets in all_results.items():
                filtered = []
                for tweet in tweets:
                    if (tweet.get("likes", 0) >= min_engagement.get("likes", 0) and
                        tweet.get("retweets", 0) >= min_engagement.get("retweets", 0) and
                        tweet.get("replies", 0) >= min_engagement.get("replies", 0) and
                        tweet.get("engagement_score", 0) >= min_engagement.get("total_score", 0)):
                        filtered.append(tweet)
                filtered_results[topic] = filtered

            total_after = sum(len(tweets) for tweets in filtered_results.values())
            self.logger.info(f"Filtered tweets: {total_before} → {total_after} (removed {total_before - total_after})")

            # Flatten results into single list
            all_tweets = []
            for topic, tweets in filtered_results.items():
                for tweet in tweets:
                    tweet["topic"] = topic
                    all_tweets.append(tweet)

            # Save to file
            output_file = self._save_intermediate_file(all_tweets, "scraped")
            self.logger.info(f"Scraped {len(all_tweets)} tweets total")
            self.logger.info(f"Output saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 1 failed: {e}", exc_info=True)
            return None

    def run_stage_media_descriptions(self, input_file: str) -> Optional[str]:
        """
        Stage 2: Add AI-generated descriptions to media.

        Args:
            input_file: Path to JSON file from scraper stage

        Returns:
            Path to output JSON file, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 2: Media Descriptions")
        self.logger.info("=" * 80)

        try:
            desc_config = self.config.get("media_descriptions", {})
            if not desc_config.get("enabled", True):
                self.logger.info("Media descriptions disabled, skipping...")
                return input_file

            self.logger.info(f"Input file: {input_file}")

            # Initialize generator
            generator = MediaDescriptionGenerator()

            # Count media items to process
            with open(input_file, 'r') as f:
                tweets = json.load(f)

            total_media = sum(len(tweet.get("media", [])) for tweet in tweets)
            self.logger.info(f"Processing descriptions for {total_media} media items across {len(tweets)} tweets")

            # Process the file
            output_file = self._get_intermediate_path("described")
            generator.process_json_file(input_file, output_file)

            self.logger.info(f"Output saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 2 failed: {e}", exc_info=True)
            return None

    def run_stage_hook_generation(self, input_file: str) -> Optional[str]:
        """
        Stage 3: Generate viral Instagram hooks.

        Args:
            input_file: Path to JSON file from media descriptions stage

        Returns:
            Path to output JSON file, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 3: Hook Generation")
        self.logger.info("=" * 80)

        try:
            hook_config = self.config.get("hook_generation", {})
            if not hook_config.get("enabled", True):
                self.logger.info("Hook generation disabled, skipping...")
                return input_file

            self.logger.info(f"Input file: {input_file}")

            # Initialize generator
            generator = HookGenerator()

            # Count tweets to process
            with open(input_file, 'r') as f:
                tweets = json.load(f)

            hooks_per_tweet = hook_config.get("hooks_per_tweet", 10)
            self.logger.info(f"Generating {hooks_per_tweet} hooks for {len(tweets)} tweets")

            # Process the file
            output_file = self._get_intermediate_path("with_hooks")
            generator.process_json_file(input_file, output_file)

            self.logger.info(f"Output saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 3 failed: {e}", exc_info=True)
            return None

    def run_stage_slack_integration(self, input_file: str, skip_slack: bool = False) -> Optional[str]:
        """
        Stage 4: Collect hook selections via Slack or auto-select.

        Args:
            input_file: Path to JSON file from hook generation stage
            skip_slack: If True, auto-select hooks instead of using Slack

        Returns:
            Path to output JSON file, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 4: Hook Selection")
        self.logger.info("=" * 80)

        try:
            slack_config = self.config.get("slack_integration", {})

            # Check if we should skip Slack
            if skip_slack or not slack_config.get("enabled", True):
                self.logger.info("Slack integration disabled, auto-selecting hooks...")
                return self._auto_select_hooks(input_file)

            self.logger.info(f"Input file: {input_file}")

            # Process the file
            output_file = self._get_intermediate_path("selected")

            # Initialize Slack integration
            integration = SlackIntegration(input_file, output_file)
            poll_interval = slack_config.get("poll_interval_seconds", 10)
            timeout_minutes = slack_config.get("timeout_minutes", 60)

            self.logger.info(f"Posting tweets to Slack (polling every {poll_interval}s, timeout: {timeout_minutes}m)")
            integration.process_json_file(
                poll_timeout=timeout_minutes * 60,  # Convert minutes to seconds
                check_interval=poll_interval
            )

            self.logger.info(f"Output saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 4 failed: {e}", exc_info=True)
            # Fall back to auto-selection on error
            self.logger.info("Falling back to auto-selection due to error")
            return self._auto_select_hooks(input_file)

    def _auto_select_hooks(self, input_file: str) -> str:
        """
        Auto-select hooks instead of using Slack.

        Args:
            input_file: Path to JSON file with hooks

        Returns:
            Path to output JSON file with selected hooks
        """
        slack_config = self.config.get("slack_integration", {})
        auto_select_indices = slack_config.get("auto_select_indices", [0, 4, 9])

        with open(input_file, 'r') as f:
            tweets = json.load(f)

        self.logger.info(f"Auto-selecting hooks at indices: {auto_select_indices}")

        for tweet in tweets:
            hooks = tweet.get("hooks", [])
            selected = []
            selected_indices = []

            for idx in auto_select_indices:
                if idx < len(hooks):
                    selected.append(hooks[idx])
                    selected_indices.append(idx)

            tweet["selected_hooks"] = selected
            tweet["selected_hook_indices"] = selected_indices
            tweet["selection_method"] = "auto"
            tweet["selection_timestamp"] = datetime.now().isoformat()

        output_file = self._get_intermediate_path("selected")
        with open(output_file, 'w') as f:
            json.dump(tweets, f, indent=2)

        self.logger.info(f"Auto-selected hooks for {len(tweets)} tweets")
        self.logger.info(f"Output saved to: {output_file}")

        return output_file

    def run_stage_media_download(self, input_file: str) -> Optional[str]:
        """
        Stage 5: Download all media files and add local paths to JSON.

        Args:
            input_file: Path to JSON file with selected hooks

        Returns:
            Path to final output JSON file, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 5: Media Download")
        self.logger.info("=" * 80)

        try:
            download_config = self.config.get("media_download", {})
            if not download_config.get("enabled", True):
                self.logger.info("Media download disabled, skipping...")
                return input_file

            self.logger.info(f"Input file: {input_file}")

            # Initialize downloader
            downloader = MediaDownloader()

            # Load tweets
            with open(input_file, 'r') as f:
                tweets = json.load(f)

            # Count total media items
            total_media = sum(len(tweet.get("media", [])) for tweet in tweets)
            self.logger.info(f"Downloading {total_media} media files")

            # Download media for each tweet
            downloaded_count = 0
            failed_count = 0

            for tweet in tqdm(tweets, desc="Processing tweets"):
                media_items = tweet.get("media", [])

                for media in media_items:
                    url = media.get("url")
                    if not url:
                        continue

                    try:
                        # Download and get local path
                        local_path = downloader.download_media(url)
                        media["local_path"] = local_path
                        downloaded_count += 1
                    except Exception as e:
                        self.logger.warning(f"Failed to download media from {url}: {e}")
                        media["local_path"] = None
                        media["download_error"] = str(e)
                        failed_count += 1

            self.logger.info(f"Downloaded {downloaded_count} files successfully")
            if failed_count > 0:
                self.logger.warning(f"Failed to download {failed_count} files")

            # Save final output
            output_file = self._get_final_output_path()
            with open(output_file, 'w') as f:
                json.dump(tweets, f, indent=2)

            self.logger.info(f"Final output saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 5 failed: {e}", exc_info=True)
            return None

    def run_stage_asset_setup(self, input_file: str) -> Optional[str]:
        """
        Stage 6: Validate video generation assets and environment.

        Args:
            input_file: Path to JSON file from media download stage

        Returns:
            Path to input file (passed through), or None if validation failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 6: Asset Setup & Validation")
        self.logger.info("=" * 80)

        try:
            asset_config = self.config.get("asset_setup", {})
            if not asset_config.get("enabled", True):
                self.logger.info("Asset setup disabled, skipping...")
                return input_file

            self.logger.info("Validating video generation environment...")

            # Initialize asset setup
            video_config_path = asset_config.get("video_config_path", "video_config.json")
            asset_setup = AssetSetup(config_file=video_config_path)

            # Run validation checks
            ffmpeg_ok, ffmpeg_msg = asset_setup.check_ffmpeg()
            fonts_ok, available_fonts = asset_setup.check_fonts()
            dirs_ok = asset_setup.create_directories()
            boxes_ok, missing_boxes = asset_setup.check_tweet_boxes()

            # Check if all validations passed
            all_passed = all([ffmpeg_ok, fonts_ok, dirs_ok, boxes_ok])

            if not all_passed:
                self.logger.error("Asset validation failed!")
                if not ffmpeg_ok:
                    self.logger.error(f"  FFmpeg: {ffmpeg_msg}")
                if not fonts_ok:
                    self.logger.error("  Fonts: No configured fonts found")
                if not dirs_ok:
                    self.logger.error("  Directories: Failed to create required directories")
                if not boxes_ok:
                    self.logger.error(f"  Tweet boxes: Missing {len(missing_boxes)} box(es): {missing_boxes}")

                # If strict validation is enabled, fail the stage
                if asset_config.get("strict_validation", True):
                    self.logger.error("Strict validation enabled - stopping pipeline")
                    return None
                else:
                    self.logger.warning("Strict validation disabled - continuing despite warnings")

            self.logger.info("Asset validation completed successfully ✓")
            return input_file

        except Exception as e:
            self.logger.error(f"Stage 6 failed: {e}", exc_info=True)
            return None

    def run_stage_video_generation(self, input_file: str) -> Optional[str]:
        """
        Stage 7: Generate Instagram Reel videos for all selected hooks.

        Args:
            input_file: Path to JSON file with selected hooks and local media paths

        Returns:
            Path to final output file with video paths added, or None if failed
        """
        self.logger.info("=" * 80)
        self.logger.info("STAGE 7: Video Generation")
        self.logger.info("=" * 80)

        try:
            video_config = self.config.get("video_generation", {})
            if not video_config.get("enabled", True):
                self.logger.info("Video generation disabled, skipping...")
                return input_file

            self.logger.info(f"Input file: {input_file}")

            # Initialize video generator
            video_config_path = video_config.get("video_config_path", "video_config.json")
            generator = FFmpegGenerator(config_path=video_config_path)

            # Load tweets with selected hooks
            with open(input_file, 'r') as f:
                tweets = json.load(f)

            # Count total videos to generate
            total_videos = sum(len(tweet.get("selected_hooks", [])) for tweet in tweets)
            self.logger.info(f"Generating {total_videos} videos from {len(tweets)} tweets")

            # Get output directory from config
            output_dir = video_config.get("output_dir", "./output/videos")
            Path(output_dir).mkdir(parents=True, exist_ok=True)

            # Generate videos
            generated_count = 0
            failed_count = 0
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

            for tweet_idx, tweet in enumerate(tqdm(tweets, desc="Processing tweets")):
                # Get media with local path
                media_items = tweet.get("media", [])
                if not media_items:
                    self.logger.warning(f"Tweet {tweet_idx} has no media, skipping video generation")
                    continue

                # Use first media item (primary media)
                primary_media = media_items[0]
                media_local_path = primary_media.get("local_path")

                if not media_local_path or not os.path.exists(media_local_path):
                    self.logger.warning(f"Tweet {tweet_idx} has no valid local media path, skipping")
                    continue

                # Generate video for each selected hook
                selected_hooks = tweet.get("selected_hooks", [])
                tweet["generated_videos"] = []

                for hook_idx, hook_text in enumerate(selected_hooks):
                    # Build output filename
                    tweet_topic = tweet.get("topic", "unknown").replace(" ", "_")
                    video_filename = f"{tweet_topic}_tweet{tweet_idx}_hook{hook_idx}_{timestamp}.mp4"
                    video_output_path = os.path.join(output_dir, video_filename)

                    self.logger.info(f"Generating video {generated_count + 1}/{total_videos}: {video_filename}")

                    try:
                        # Generate video
                        success = generator.generate_single_variant(
                            media_path=media_local_path,
                            hook_text=hook_text,
                            output_path=video_output_path
                        )

                        if success:
                            # Add video path to tweet data
                            tweet["generated_videos"].append({
                                "hook_index": hook_idx,
                                "hook_text": hook_text,
                                "video_path": video_output_path,
                                "media_source": media_local_path,
                                "generated_at": datetime.now().isoformat()
                            })
                            generated_count += 1
                        else:
                            self.logger.error(f"Failed to generate video: {video_filename}")
                            tweet["generated_videos"].append({
                                "hook_index": hook_idx,
                                "hook_text": hook_text,
                                "video_path": None,
                                "error": "Video generation failed",
                                "media_source": media_local_path
                            })
                            failed_count += 1

                    except Exception as e:
                        self.logger.error(f"Error generating video {video_filename}: {e}")
                        tweet["generated_videos"].append({
                            "hook_index": hook_idx,
                            "hook_text": hook_text,
                            "video_path": None,
                            "error": str(e),
                            "media_source": media_local_path
                        })
                        failed_count += 1

            self.logger.info(f"Generated {generated_count} videos successfully")
            if failed_count > 0:
                self.logger.warning(f"Failed to generate {failed_count} videos")

            # Save final output with video paths
            output_file = self._get_final_output_path()
            with open(output_file, 'w') as f:
                json.dump(tweets, f, indent=2)

            self.logger.info(f"Final output with video paths saved to: {output_file}")

            return output_file

        except Exception as e:
            self.logger.error(f"Stage 7 failed: {e}", exc_info=True)
            return None

    def _save_intermediate_file(self, data: Any, stage_name: str) -> str:
        """Save intermediate data to a JSON file."""
        output_config = self.config.get("output", {})

        if output_config.get("save_intermediate_files", True):
            intermediate_dir = output_config.get("intermediate_directory", "./intermediate")
            Path(intermediate_dir).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intermediate_{stage_name}_{timestamp}.json"
            filepath = os.path.join(intermediate_dir, filename)
        else:
            # Use temporary file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"temp_{stage_name}_{timestamp}.json"
            filepath = filename

        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

        self.intermediate_files.append(filepath)
        return filepath

    def _get_intermediate_path(self, stage_name: str) -> str:
        """Get path for intermediate file."""
        output_config = self.config.get("output", {})

        if output_config.get("save_intermediate_files", True):
            intermediate_dir = output_config.get("intermediate_directory", "./intermediate")
            Path(intermediate_dir).mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"intermediate_{stage_name}_{timestamp}.json"
            return os.path.join(intermediate_dir, filename)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            return f"temp_{stage_name}_{timestamp}.json"

    def _get_final_output_path(self) -> str:
        """Get path for final output file."""
        output_config = self.config.get("output", {})
        output_dir = output_config.get("directory", "./output")
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        prefix = output_config.get("filename_prefix", "orchestrator_output")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{prefix}_{timestamp}.json"

        return os.path.join(output_dir, filename)

    def run_pipeline(self, skip_slack: bool = False, resume_from: Optional[str] = None) -> bool:
        """
        Run the complete pipeline.

        Args:
            skip_slack: If True, auto-select hooks instead of using Slack
            resume_from: Stage name to resume from (None to start from beginning)

        Returns:
            True if pipeline completed successfully, False otherwise
        """
        self.logger.info("=" * 80)
        self.logger.info("VIRAL INSTAGRAM POSTS PIPELINE - STARTING")
        self.logger.info("=" * 80)
        self.logger.info(f"Start time: {self.start_time.isoformat()}")

        # Determine starting stage
        if resume_from:
            if resume_from not in self.STAGES:
                self.logger.error(f"Invalid resume stage: {resume_from}")
                return False
            start_idx = self.STAGES.index(resume_from)
            self.logger.info(f"Resuming from stage: {resume_from}")
        else:
            start_idx = 0

        # Run stages
        current_file = None

        for stage_name in self.STAGES[start_idx:]:
            self.current_stage = stage_name
            self._save_checkpoint()

            try:
                if stage_name == "scraper":
                    current_file = self.run_stage_scraper()
                elif stage_name == "media_descriptions":
                    current_file = self.run_stage_media_descriptions(current_file)
                elif stage_name == "hook_generation":
                    current_file = self.run_stage_hook_generation(current_file)
                elif stage_name == "slack_integration":
                    current_file = self.run_stage_slack_integration(current_file, skip_slack)
                elif stage_name == "media_download":
                    current_file = self.run_stage_media_download(current_file)
                elif stage_name == "asset_setup":
                    current_file = self.run_stage_asset_setup(current_file)
                elif stage_name == "video_generation":
                    current_file = self.run_stage_video_generation(current_file)

                if current_file is None:
                    self.logger.error(f"Stage {stage_name} failed")
                    self.failed_stages.append(stage_name)
                    return False

                self.completed_stages.append(stage_name)
                self.logger.info(f"Stage {stage_name} completed successfully ✓")

            except KeyboardInterrupt:
                self.logger.warning("Pipeline interrupted by user")
                self._save_checkpoint()
                return False
            except Exception as e:
                self.logger.error(f"Unexpected error in stage {stage_name}: {e}", exc_info=True)
                self.failed_stages.append(stage_name)
                return False

        # Pipeline completed
        self._print_summary(current_file)
        return True

    def _print_summary(self, final_output: str):
        """Print pipeline execution summary."""
        end_time = datetime.now()
        duration = end_time - self.start_time

        self.logger.info("=" * 80)
        self.logger.info("PIPELINE COMPLETED SUCCESSFULLY")
        self.logger.info("=" * 80)
        self.logger.info(f"Total duration: {duration}")
        self.logger.info(f"Completed stages: {', '.join(self.completed_stages)}")

        # Load final output and print stats
        try:
            with open(final_output, 'r') as f:
                tweets = json.load(f)

            total_tweets = len(tweets)
            total_media = sum(len(tweet.get("media", [])) for tweet in tweets)
            downloaded_media = sum(
                1 for tweet in tweets
                for media in tweet.get("media", [])
                if media.get("local_path")
            )

            # Count generated videos
            generated_videos = sum(
                len(tweet.get("generated_videos", []))
                for tweet in tweets
            )
            successful_videos = sum(
                1 for tweet in tweets
                for video in tweet.get("generated_videos", [])
                if video.get("video_path") and os.path.exists(video.get("video_path"))
            )

            self.logger.info("")
            self.logger.info("Statistics:")
            self.logger.info(f"  Total tweets processed: {total_tweets}")
            self.logger.info(f"  Total media items: {total_media}")
            self.logger.info(f"  Media files downloaded: {downloaded_media}")
            self.logger.info(f"  Hooks generated: {total_tweets * 10}")
            self.logger.info(f"  Hooks selected: {total_tweets * 3}")
            self.logger.info(f"  Videos generated: {successful_videos}/{generated_videos}")
            self.logger.info("")
            self.logger.info(f"Final output: {final_output}")
            self.logger.info("")
            if successful_videos > 0:
                self.logger.info(f"All done! Generated {successful_videos} Instagram Reels!")
            else:
                self.logger.info("Pipeline completed!")

        except Exception as e:
            self.logger.warning(f"Could not load final output for statistics: {e}")


def main():
    """Main entry point for the orchestrator."""
    parser = argparse.ArgumentParser(
        description="Orchestrate the viral Instagram posts pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                              Run full pipeline with defaults
  %(prog)s --config my_config.json      Run with custom configuration
  %(prog)s --skip-slack                 Auto-select hooks instead of using Slack
  %(prog)s --dry-run                    Validate setup without executing
  %(prog)s --resume-from media_download Resume from a specific stage
        """
    )

    parser.add_argument(
        "--config",
        default="orchestrator_config.json",
        help="Path to configuration JSON file (default: orchestrator_config.json)"
    )

    parser.add_argument(
        "--skip-slack",
        action="store_true",
        help="Skip Slack integration and auto-select hooks"
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate prerequisites without executing pipeline"
    )

    parser.add_argument(
        "--resume-from",
        choices=PipelineOrchestrator.STAGES,
        help="Resume pipeline from a specific stage"
    )

    args = parser.parse_args()

    # Initialize orchestrator
    try:
        orchestrator = PipelineOrchestrator(config_path=args.config)
    except SystemExit:
        return 1

    # Validate prerequisites
    success, errors = orchestrator.validate_prerequisites(dry_run=args.dry_run)

    if not success:
        print("\nPrerequisite validation failed. Please fix the errors above and try again.")
        return 1

    if args.dry_run:
        print("\nDry run completed successfully. All prerequisites are met.")
        return 0

    # Run pipeline
    success = orchestrator.run_pipeline(
        skip_slack=args.skip_slack,
        resume_from=args.resume_from
    )

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
