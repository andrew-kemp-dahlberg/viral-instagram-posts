# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python toolkit that scrapes trending tweets from Twitter/X using the Apify platform, transforms them into viral Instagram content, and prepares for video generation. The project searches for tweets on customizable topics, ranks them by engagement metrics (likes, retweets, replies), generates AI-powered media descriptions and Instagram hooks, enables team selection via Slack, and provides infrastructure for Instagram Reel video generation. Filters out retweets to focus on original content and extracts media URLs (images, videos) from tweets.

**Key Feature:** The `orchestrator.py` script automates the entire workflow end-to-end with a single command, handling scraping, AI descriptions, hook generation, selection, media download, asset validation, and video generation with comprehensive error handling, checkpointing, and resume capability.

## Development Commands

### Automated Pipeline (Recommended)

The orchestrator automates the entire workflow from scraping to media download:

```bash
# Run the complete pipeline with defaults
python orchestrator.py

# Validate prerequisites without executing
python orchestrator.py --dry-run

# Skip Slack integration and auto-select hooks
python orchestrator.py --skip-slack

# Use custom configuration file
python orchestrator.py --config my_config.json

# Resume from a specific stage after failure
python orchestrator.py --resume-from media_download
```

The orchestrator chains all 7 pipeline stages:
1. **Scraper** - Collects trending tweets using Apify
2. **Media Descriptions** - Adds AI descriptions (GPT-4o + Gemini)
3. **Hook Generation** - Creates 10 viral hooks per tweet (Claude)
4. **Slack Integration** - Collects user selections or auto-selects
5. **Media Download** - Downloads and caches all media files
6. **Asset Setup** - Validates FFmpeg, fonts, tweet boxes for video generation
7. **Video Generation** - Creates Instagram Reel videos for all selected hooks

Configuration via `orchestrator_config.json`:
- `scraper.topics` - List of topics to search
- `scraper.max_tweets_per_topic` - Number of tweets per topic
- `scraper.min_engagement` - Engagement thresholds (likes, retweets, replies)
- `slack_integration.enabled` - Enable/disable Slack selection
- `slack_integration.auto_select_indices` - Which hooks to auto-select [0, 4, 9]
- `asset_setup.enabled` - Enable/disable asset validation
- `asset_setup.strict_validation` - Stop pipeline if assets missing (default: true)
- `video_generation.enabled` - Enable/disable video generation
- `video_generation.output_dir` - Where to save generated videos
- `output.save_intermediate_files` - Save stage outputs for debugging

Output:
- `orchestrator_output_{timestamp}.json` - Final dataset with local media paths and video paths
- `orchestrator.log` - Detailed execution log
- `cache/media/*` - Downloaded media files
- `output/videos/*.mp4` - Generated Instagram Reel videos
- `intermediate/*` - Stage outputs (if enabled)
- `orchestrator_checkpoint.json` - Resume state (auto-saved)

### Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Then edit .env and add your APIFY_API_TOKEN
```

### Running the Scraper
```bash
# Run the main script
python scraper.py

# Make the script executable (already set)
chmod +x scraper.py
./scraper.py
```

### Adding Media Descriptions
```bash
# Add AI-generated descriptions to media in tweet JSON files
python add_media_descriptions.py trending_tweets_20251109_164707.json

# Specify custom output file
python add_media_descriptions.py input.json output_described.json
```

### Generating Instagram Hooks
```bash
# Generate 10 viral Instagram reel hooks in Parker Doyle's style
python hook_creation.py trending_tweets_20251109_164707_described.json

# Specify custom output file
python hook_creation.py input_described.json output_with_hooks.json
```

### Selecting Hooks via Slack
```bash
# Send tweets to Slack and allow users to select their top 3 hooks
python slack_integration.py trending_tweets_20251109_164707_with_hooks.json

# Specify custom output file
python slack_integration.py input_with_hooks.json output_selected.json
```

### Video Generation Setup
```bash
# Validate environment and set up assets for video generation
python setup_assets.py

# This checks:
# - FFmpeg installation
# - System fonts (Arial, Helvetica, etc.)
# - Directory structure (assets/, cache/, output/)
# - Tweet box PNG assets
```

### Media Download & Caching
```bash
# Download media from tweets with intelligent caching
# (typically used within video generation pipeline, but can be used standalone)

from media_downloader import MediaDownloader

# Initialize downloader
downloader = MediaDownloader(config_path='video_config.json')

# Download single media file (will cache automatically)
local_path = downloader.download_media('https://pbs.twimg.com/media/example.jpg')

# Download with custom cache directory
local_path = downloader.download_media(
    'https://video.twimg.com/ext_tw_video/example.mp4',
    cache_dir='./cache/media'
)

# Clear expired cache entries (older than TTL)
removed_count = downloader.clear_expired_cache()
```

**Cache Features:**
- MD5-based cache keys prevent duplicate downloads
- TTL-based expiration (default: 24 hours, configurable in video_config.json)
- Metadata JSON sidecar files track download time, URL, file type, size
- Automatic validation using file signatures (magic numbers)
- Progress bars for download tracking

**Required Tweet Box Assets:**
Create 3 PNG files in `assets/tweet_boxes/`:
- `tweet_1liner.png` - For single-line tweets (recommended: 1900x500px)
- `tweet_2liner.png` - For two-line tweets (recommended: 1900x650px)
- `tweet_3liner.png` - For three-line tweets (recommended: 1900x800px)

See `assets/tweet_boxes/README.md` for detailed specifications.

**Video Configuration:**
Edit `video_config.json` to customize:
- Video resolution (default: 2160x3840 - 4K vertical 9:16)
- Encoding settings (CRF, preset, codec)
- Effect parameters (blur sigma, media scaling)
- Position settings (hook text, tweet box, media)
- Processing options (parallel workers, cache settings)

### Video Generation (FFmpeg)
```bash
# Generate a single Instagram Reel video with FFmpeg
python ffmpeg_generator.py <media_path> <hook_text> <output_path>

# Example with cached media
python ffmpeg_generator.py \
  ./cache/media/abc123.mp4 \
  "Bro just casually made the shot of the year 😭" \
  ./output/test/variant_1.mp4

# Dry-run mode (preview command without executing)
python ffmpeg_generator.py \
  ./cache/media/abc123.mp4 \
  "Hook text here" \
  ./output/test/variant_1.mp4 \
  --dry-run

# Programmatic usage
from ffmpeg_generator import FFmpegGenerator

generator = FFmpegGenerator(config_path='video_config.json')
success = generator.generate_single_variant(
    media_path='./cache/media/abc123.mp4',
    hook_text='Bro just casually made the shot of the year 😭',
    output_path='./output/test/variant_1.mp4'
)
```

**Processing Pipeline:**
1. Auto-detects media type (image or video)
2. For images: adds `-loop 1 -t 10` for 10-second duration
3. Creates blurred background by scaling media to fill 9:16
4. Applies Gaussian blur (sigma=20)
5. Scales main media to fit within bounds (90% width, 70% height)
6. Overlays centered media on blurred background
7. Applies sharpening (unsharp: 11:11:1.5)
8. Applies clarity (eq: brightness=0.02:contrast=1.2)
9. Overlays tweet box PNG (auto-selected by line count)
10. Adds hook text overlay (72pt, black, centered at y=150)

**Features:**
- Single-pass filter_complex for optimal performance
- Auto-selects tweet box based on hook line count (1, 2, or 3 lines)
- Cross-platform font detection (macOS, Linux, Windows)
- Progress tracking during encoding
- Dry-run mode for command preview
- Comprehensive error handling and logging

**Output:**
- 4K vertical video (2160x3840, 9:16 aspect ratio)
- H.264 codec, CRF 18 (visually lossless)
- 30 fps, yuv420p pixel format
- AAC audio at 128kbps (if source has audio)

## Code Architecture

### Core Components

**PipelineOrchestrator class** (orchestrator.py:46-608)
- Main orchestrator that automates the entire viral Instagram posts workflow
- Chains all 5 pipeline stages sequentially with error handling and checkpointing
- Validates prerequisites before execution (API keys, directories, configuration)
- Nine primary methods:
  - `validate_prerequisites()`: Checks API keys, directories, and configuration values before execution
  - `run_pipeline()`: Main entry point - orchestrates all stages sequentially
  - `run_stage_scraper()`: Stage 1 - Scrapes tweets using TwitterTrendingScraper, applies engagement filters
  - `run_stage_media_descriptions()`: Stage 2 - Adds AI descriptions using MediaDescriptionGenerator
  - `run_stage_hook_generation()`: Stage 3 - Generates hooks using HookGenerator
  - `run_stage_slack_integration()`: Stage 4 - Collects selections via SlackIntegration or auto-selects
  - `run_stage_media_download()`: Stage 5 - Downloads media using MediaDownloader, adds local_path fields
  - `_save_checkpoint()`: Saves pipeline state after each stage for resume capability
  - `_print_summary()`: Displays execution statistics and final output location
- Key features:
  - **Prerequisite validation**: Checks all API keys exist before starting
  - **Engagement filtering**: Applies min_engagement thresholds from config
  - **Auto-selection fallback**: Falls back to auto-selection if Slack fails or is disabled
  - **Progress tracking**: Uses tqdm progress bars for long operations
  - **Error handling**: Graceful failures with detailed logging
  - **Checkpointing**: Saves state after each stage for resume capability
  - **Intermediate files**: Optional saving of stage outputs for debugging
  - **Statistics reporting**: Prints summary with tweet count, media count, duration
- Configuration loaded from orchestrator_config.json with sections for each stage
- Logs all operations to orchestrator.log with INFO level
- CLI interface with argparse: --dry-run, --skip-slack, --resume-from, --config
- Includes all 7 stages from scraping to video generation
- Output: orchestrator_output_{timestamp}.json with complete dataset, local media paths, and generated video paths

**TwitterTrendingScraper class** (scraper.py:17-152)
- Main orchestrator for Twitter data collection
- Uses Apify's `web.harvester/easy-twitter-search-scraper` actor (no Twitter auth required)
- Three primary methods:
  - `search_trending_tweets()`: Executes searches and processes results
  - `display_results()`: Formats output for console display
  - `save_to_json()`: Persists results to timestamped JSON files

**MediaDescriptionGenerator class** (add_media_descriptions.py:18-160)
- Adds AI-generated descriptions to media objects in tweet JSON files
- Uses two AI models for different media types:
  - **GPT-4o (OpenAI)**: Generates descriptions for images via Vision API
  - **Gemini 1.5 Flash (Google)**: Generates descriptions for videos
- Three primary methods:
  - `describe_image()`: Generates 1-2 sentence image descriptions using GPT-4o
  - `describe_video()`: Generates video descriptions using Gemini API
  - `process_json_file()`: Processes entire JSON files, adding descriptions to all media items

**HookGenerator class** (hook_creation.py:23-154)
- Generates Instagram reel text hooks in Parker Doyle's viral style using Claude AI
- Uses **Claude 4.5 Sonnet (Anthropic)** for hook generation
- Analyzes tweet content and media descriptions to create viral hooks
- Three primary methods:
  - `generate_hooks()`: Creates 10 hook options for a single tweet
  - `_parse_hooks()`: Parses Claude's response into a list of hooks
  - `process_json_file()`: Processes entire JSON files, adding hooks to all tweets

**SlackIntegration class** (slack_integration.py:23-370)
- Sends processed tweets to Slack for user review and hook selection
- Uses **Slack SDK (WebClient)** with polling-based user interaction
- Formats tweets with Slack Block Kit for rich presentation
- Five primary methods:
  - `send_tweets_to_slack()`: Posts tweets to Slack grouped by topic with formatted messages
  - `_format_tweet_message()`: Creates Block Kit message with tweet text, engagement metrics, media, and hooks
  - `poll_for_selections()`: Polls Slack threads for user replies containing hook selections
  - `_parse_selection()`: Parses user replies like "1, 5, 9" into hook numbers
  - `save_selected_hooks()`: Adds `selected_hooks` array to JSON with user's top 3 choices
  - `process_json_file()`: Main orchestrator for send → poll → save workflow

**AssetSetup class** (setup_assets.py:18-250)
- Validates environment and sets up infrastructure for Instagram Reel video generation
- Checks system dependencies and creates required directory structure
- Provides detailed instructions for missing assets
- Five primary methods:
  - `check_ffmpeg()`: Verifies FFmpeg installation in PATH and returns version info
  - `check_fonts()`: Searches for configured fonts (Arial, Helvetica, Liberation Sans) using fc-list or directory scanning
  - `create_directories()`: Creates assets/, cache/, output/ directory structure from video_config.json
  - `check_tweet_boxes()`: Validates presence of 3 required PNG files for tweet overlays
  - `generate_tweet_box_instructions()`: Prints detailed design specifications and tool recommendations
  - `run_full_check()`: Orchestrates all validation checks and displays summary report

**MediaDownloader class** (media_downloader.py:20-520)
- Downloads and caches media files (images/videos) from tweet URLs
- Uses **requests library** for HTTP downloads with **tqdm** for progress tracking
- Implements intelligent caching system to avoid duplicate downloads
- Four primary methods:
  - `download_media()`: Downloads media from URL with automatic caching
  - `_download_with_retry()`: Executes download with retry logic and exponential backoff
  - `_is_cached()`: Checks if media is already cached and within TTL
  - `clear_expired_cache()`: Removes cached files older than TTL
- Key features:
  - **MD5-based cache keys**: Generates unique cache keys from URLs to prevent duplicates
  - **Retry logic**: 3 attempts with exponential backoff (1s, 2s, 4s delays)
  - **File validation**: Verifies downloads using magic number checking
  - **Atomic writes**: Downloads to temp file then renames to prevent partial files
  - **Progress bars**: Shows download progress using tqdm
  - **Metadata storage**: JSON sidecar files track download time, URL, file type, size
  - **TTL support**: Cached files expire after configurable hours (default: 24)
  - **Error handling**: Clean messages for HTTP errors, timeouts, connection failures
- Supported formats:
  - Images: .jpg, .jpeg, .png, .gif, .webp
  - Videos: .mp4, .mov, .avi, .webm, .m4v
- Reads configuration from video_config.json (cache_dir, cache_ttl_hours)
- Logs all operations to media_download.log

**FFmpegGenerator class** (ffmpeg_generator.py:29-540)
- Core video processing engine that replicates CapCut workflow using FFmpeg
- Uses **FFmpeg** with single-pass filter_complex for optimal performance
- Generates Instagram Reels with professional effects and overlays
- Five primary methods:
  - `generate_single_variant()`: Main entry point - orchestrates full video generation
  - `_detect_media_type()`: Determines if input is image or video
  - `_select_tweet_box()`: Auto-selects tweet box PNG based on hook line count
  - `_build_ffmpeg_command()`: Constructs complete filter_complex command chain
  - `_run_ffmpeg_command()`: Executes FFmpeg with progress tracking
- Key features:
  - **Single-pass processing**: All effects in one filter_complex for efficiency
  - **Auto-detection**: Detects media type and adjusts parameters (adds -loop and duration for images)
  - **Configurable timing**: Image duration controlled by video_config.json timing.media_duration (default: 5 seconds for Instagram Reels)
  - **Smart tweet box selection**: Counts newlines in hook text (0=1-liner, 1=2-liner, 2=3-liner)
  - **Cross-platform fonts**: Searches system font directories on macOS/Linux/Windows
  - **Text escaping**: Properly escapes quotes, colons, backslashes for FFmpeg drawtext
  - **Progress tracking**: Parses FFmpeg output to show encoding progress
  - **Dry-run mode**: Preview command without execution
  - **Comprehensive logging**: All operations logged to video_generation.log
- Filter chain workflow (ffmpeg_generator.py:375-420):
  1. Scale media to fill 9:16 frame → crop to exact size [bg]
  2. Apply Gaussian blur (sigma=20) to background [blurred]
  3. Scale main media to fit bounds (max 90% width, 70% height) [media]
  4. Overlay centered media on blurred background [with_media]
  5. Apply sharpening with unsharp filter (11:11:1.5) [sharpened]
  6. Apply clarity with eq filter (brightness=0.02:contrast=1.2) [enhanced]
  7. Overlay tweet box PNG (centered) [with_box]
  8. Add drawtext overlay for hook (72pt, black, centered x, y=150) [final]
- Output specifications:
  - Resolution: 2160x3840 (4K vertical, 9:16 aspect ratio)
  - Codec: libx264 with preset=medium, CRF=18 (near-lossless)
  - Framerate: 30fps, pixel format: yuv420p
  - Audio: AAC at 128kbps (copied from source if available)
- Validates FFmpeg on initialization, raises error if not found in PATH
- Reads all configuration from video_config.json

### Data Flow

**Automated Pipeline Workflow (orchestrator.py):**

1. **Prerequisites Validation** (orchestrator.py:115-183):
   - Loads environment variables from .env file
   - Checks for required API keys: APIFY_API_TOKEN, OPENAI_API_KEY, GEMINI_API_KEY, ANTHROPIC_API_KEY
   - Optionally checks SLACK_BOT_TOKEN and SLACK_CHANNEL_ID if Slack integration enabled
   - Creates output directories: output/, cache/media/, intermediate/ (if enabled)
   - Validates configuration: topics not empty, max_tweets_per_topic > 0
   - Returns success/failure with list of error messages

2. **Stage 1: Twitter Scraping** (orchestrator.py:185-250):
   - Instantiates TwitterTrendingScraper class
   - Scrapes tweets for all topics in config
   - Applies engagement filters from config (min_likes, min_retweets, min_replies, total_score)
   - Adds `topic` field to each tweet
   - Saves to intermediate file: `intermediate_scraped_{timestamp}.json`
   - Returns file path or None on failure

3. **Stage 2: Media Descriptions** (orchestrator.py:252-287):
   - Skips if `media_descriptions.enabled` is false in config
   - Instantiates MediaDescriptionGenerator class
   - Processes all media items across all tweets
   - Saves to intermediate file: `intermediate_described_{timestamp}.json`
   - Returns file path or None on failure

4. **Stage 3: Hook Generation** (orchestrator.py:289-324):
   - Skips if `hook_generation.enabled` is false in config
   - Instantiates HookGenerator class
   - Generates 10 hooks per tweet (configurable)
   - Saves to intermediate file: `intermediate_with_hooks_{timestamp}.json`
   - Returns file path or None on failure

5. **Stage 4: Hook Selection** (orchestrator.py:326-396):
   - If Slack disabled or --skip-slack flag: calls `_auto_select_hooks()`
   - If Slack enabled: instantiates SlackIntegration and posts to channel
   - Auto-selection: selects hooks at indices from config (default: [0, 4, 9])
   - Adds `selected_hooks`, `selected_hook_indices`, `selection_method`, `selection_timestamp` to each tweet
   - Falls back to auto-selection on Slack failure
   - Saves to intermediate file: `intermediate_selected_{timestamp}.json`
   - Returns file path or None on failure

6. **Stage 5: Media Download** (orchestrator.py:490-561):
   - Skips if `media_download.enabled` is false in config
   - Instantiates MediaDownloader class
   - Downloads all media items across all tweets with progress bars
   - Adds `local_path` field to each media object
   - On download failure: adds `local_path: null` and `download_error` field
   - Saves to intermediate file: `intermediate_downloaded_{timestamp}.json`
   - Returns file path or None on failure

7. **Stage 6: Asset Setup** (orchestrator.py:570-628):
   - Skips if `asset_setup.enabled` is false in config
   - Instantiates AssetSetup class
   - Validates FFmpeg installation in PATH
   - Checks for system fonts (Arial, Helvetica, Liberation Sans)
   - Creates required directory structure (assets/, cache/, output/)
   - Validates presence of 3 tweet box PNG files (1-liner, 2-liner, 3-liner)
   - If `strict_validation` is true: stops pipeline if any validation fails
   - If `strict_validation` is false: continues with warnings
   - Returns input file path (pass-through) or None on failure

8. **Stage 7: Video Generation** (orchestrator.py:630-755):
   - Skips if `video_generation.enabled` is false in config
   - Instantiates FFmpegGenerator class
   - Loads tweets with selected hooks and local media paths
   - For each tweet with media:
     - Uses first media item as primary source
     - Generates video for each of the 3 selected hooks
     - Builds output filename: `{topic}_tweet{idx}_hook{idx}_{timestamp}.mp4`
     - Calls `generate_single_variant()` to create video with FFmpeg
     - Adds `generated_videos` array to tweet with video paths
   - Tracks successful and failed video generations
   - Saves final output file: `orchestrator_output_{timestamp}.json`
   - Returns file path or None on failure

9. **Checkpointing & Resume** (orchestrator.py:151-171, 635-642):
   - Saves checkpoint after each stage to `orchestrator_checkpoint.json`
   - Checkpoint contains: current_stage, completed_stages, failed_stages, intermediate_files
   - Resume from specific stage using --resume-from flag
   - Loads checkpoint on initialization if resume.enabled is true

10. **Output & Summary** (orchestrator.py:877-927):
    - Prints execution summary with duration, completed stages
    - Displays statistics: total tweets, media items, downloaded files, hooks generated/selected, videos generated
    - Final output contains complete dataset with video paths ready for publishing

**Tweet Scraping Workflow:**

1. **Input**: Topics list defined in `main()` function (scraper.py:173-177)
2. **Processing**: For each topic:
   - Constructs Apify actor run input with search parameters
   - Executes actor via `ApifyClient`
   - Fetches results from default dataset
   - **Filters out retweets** (scraper.py:62-65) - only processes original content
   - **Extracts media URLs** from tweets (scraper.py:72-92):
     - Checks `media` field for media items with type and URL
     - Falls back to `images` field if `media` is not available
     - Stores media data with type and URL in array
   - Normalizes tweet data (handles multiple field name variations)
   - Calculates engagement score: `likes + (retweets * 2) + replies`
   - Sorts by engagement score descending
3. **Output**:
   - Console display (top N tweets per topic) with media URLs shown
   - JSON file: `trending_tweets_YYYYMMDD_HHMMSS.json`

**Media Description Workflow:**

1. **Input**: JSON file from tweet scraper containing media objects
2. **Processing**: For each tweet with media (add_media_descriptions.py:142-147):
   - Iterates through media items in the `media` array
   - Determines media type (image/video)
   - **For images** (add_media_descriptions.py:116-117):
     - Calls OpenAI GPT-4o Vision API with prompt requesting 1-2 sentence description
     - Focuses on key visual elements and any visible text
     - Max tokens: 150
   - **For videos** (add_media_descriptions.py:118-119):
     - Calls Gemini 1.5 Flash API to generate video description
     - Note: Current implementation uses URL-based prompting (placeholder for full video upload)
   - Adds `description` field to each media object
3. **Output**:
   - New JSON file: `[original_name]_described.json`
   - Same structure as input but with added `description` field in each media item

**Hook Generation Workflow:**

1. **Input**: JSON file with descriptions (from add_media_descriptions.py)
2. **Processing**: For each tweet (hook_creation.py:131-165):
   - Extracts tweet text and media descriptions
   - Constructs context from tweet content and media
   - **Calls Claude 4.5 Sonnet API** (hook_creation.py:42-87):
     - Prompt includes Parker Doyle's style guidelines (casual, confident, uses "bro", emojis)
     - Provides tweet context and media descriptions
     - Requests 10 hook options between 5-15 words
     - Emphasizes social calibration over forced relatability
     - Max tokens: 1000
   - **Parses response** (hook_creation.py:89-115):
     - Extracts hooks from numbered list format
     - Handles various numbering formats (1., 1), 1-, etc.)
   - Adds `hooks` array to tweet object containing 10 hook options
3. **Output**:
   - New JSON file: `[original_name]_with_hooks.json`
   - Same structure as input but with added `hooks` array in each tweet

**Slack Hook Selection Workflow:**

1. **Input**: JSON file with hooks (from hook_creation.py)
2. **Processing** (slack_integration.py:100-370):
   - **Send to Slack** (slack_integration.py:100-155):
     - Groups tweets by topic/query for organized presentation
     - Sends topic header message with tweet count
     - For each tweet, creates Block Kit formatted message including:
       - Tweet text, author, and URL
       - Engagement metrics (likes, retweets, replies, score)
       - Media items with descriptions
       - All 10 hooks numbered 1-10
     - Stores message thread timestamps for polling
     - Adds context instruction: "Reply with 3 numbers (e.g., '1, 5, 9')"
   - **Poll for selections** (slack_integration.py:157-230):
     - Monitors each thread for user replies (default: check every 10 seconds)
     - Parses user text for hook numbers using regex
     - Validates selections (exactly 3 numbers, within hook range)
     - Continues until all tweets have selections or timeout (default: 1 hour)
   - **Save selections** (slack_integration.py:232-260):
     - Adds `selected_hooks` array with the 3 chosen hook texts
     - Adds `selected_hook_indices` array with the original numbers (1-indexed)
     - Adds `selection_timestamp` with ISO format timestamp
3. **Output**:
   - New JSON file: `[original_name]_selected.json`
   - Same structure as input but with added selection metadata in each tweet

**Video Generation Setup Workflow:**

1. **Input**: None (system environment check)
2. **Processing** (setup_assets.py:18-250):
   - **Check FFmpeg** (setup_assets.py:48-82):
     - Runs `ffmpeg -version` subprocess command
     - Parses version information from stdout
     - Provides platform-specific installation instructions if missing
   - **Check Fonts** (setup_assets.py:84-155):
     - Attempts to run `fc-list : family` to enumerate system fonts
     - Falls back to directory scanning on macOS (`/System/Library/Fonts`, `/Library/Fonts`, `~/Library/Fonts`)
     - Matches configured fonts from video_config.json (Arial → Helvetica → Liberation Sans fallbacks)
     - Returns list of available fonts
   - **Create Directories** (setup_assets.py:157-180):
     - Reads path configuration from video_config.json
     - Creates directory tree: assets/tweet_boxes, assets/fonts, cache/media, output/
     - Uses `Path.mkdir(parents=True, exist_ok=True)` for safe creation
   - **Check Tweet Boxes** (setup_assets.py:182-210):
     - Validates existence of tweet_1liner.png, tweet_2liner.png, tweet_3liner.png
     - Verifies files are PNG format
     - Reports file sizes
   - **Generate Instructions** (setup_assets.py:212-248):
     - Prints detailed specifications (dimensions, format, design tips)
     - Lists recommended tools (Figma, Photoshop, GIMP, Canva)
     - Provides step-by-step creation guide
3. **Output**:
   - Console validation report with pass/fail status for each check
   - Created directory structure if missing
   - Printed instructions for any missing components

**Media Download Workflow:**

1. **Input**: Media URL (image or video) from tweet data
2. **Processing** (media_downloader.py:20-520):
   - **Generate cache key** (media_downloader.py:112-119):
     - Creates MD5 hash of URL for unique cache identification
     - Prevents duplicate downloads of the same media
   - **Check cache** (media_downloader.py:169-200):
     - Verifies if file exists in cache directory
     - Checks metadata JSON sidecar for download timestamp
     - Validates file is not corrupted (non-zero size)
     - Compares age against TTL (default: 24 hours)
     - Returns cached path if valid, proceeds to download if not
   - **Download with retry** (media_downloader.py:281-365):
     - Makes HTTP GET request with streaming enabled
     - Displays tqdm progress bar based on Content-Length header
     - Downloads to temporary file for atomic write
     - Retries up to 3 times with exponential backoff on failure
     - Handles HTTP errors (404/403 = no retry, others = retry)
     - Handles network errors (connection timeout, read timeout)
   - **Validate file** (media_downloader.py:234-271):
     - Checks file exists and has non-zero size
     - Verifies magic number (file signature) for common formats
     - Detects JPEG (FF D8 FF), PNG (89 50 4E 47), GIF (47 49 46), MP4, WEBP
     - Removes invalid files
   - **Save metadata** (media_downloader.py:202-232):
     - Creates JSON sidecar file with same cache key
     - Stores original URL, file type (image/video), file size
     - Records download timestamp in ISO format
     - Includes TTL configuration for expiry checking
   - **Atomic rename** (media_downloader.py:342-345):
     - Moves validated temp file to final cache location
     - Prevents partial/corrupted files in cache
3. **Output**:
   - Local file path to cached media (e.g., `cache/media/a1b2c3d4.mp4`)
   - Metadata JSON file (e.g., `cache/media/a1b2c3d4.json`)
   - Log entries in `media_download.log`

### Key Implementation Details

**Retweet Filtering** (scraper.py:62-65)
Skips all retweets using the `isRetweet` field to focus exclusively on original content. This ensures the results highlight authentic viral content rather than redistributed posts.

**Media Extraction** (scraper.py:72-92)
Extracts media URLs with dual-field fallback strategy:
- Primary: `media` field (provides type + URL for images/videos)
- Fallback: `images` field (URLs only, typed as "image")
- Only stores media items with valid URLs in the `media` array

**Data Normalization** (scraper.py:94-110)
The scraper handles multiple field naming conventions from different Twitter API versions using safe fallbacks:
- Tweet text: `text` → `full_text`
- Timestamps: `created_at` → `createdAt` → `timestamp`
- Engagement metrics: `likes` → `favorite_count` → `likeCount`
- User data: nested under `author` or `user` objects, with additional fallbacks like `userFullName`, `username`, `totalFollowers`

**Engagement Scoring** (scraper.py:113-117)
Weighted formula prioritizes retweets (2x multiplier) as strongest signal of viral content.

**Image Video Duration Control** (ffmpeg_generator.py:366-382)
Ensures static images generate reel-length videos (5 seconds) instead of infinite loops:
- Reads `media_duration` from video_config.json timing section (default: 5.0 seconds)
- Applies duration limit (`-t`) to both the image input AND the tweet box PNG overlay
- Critical fix: Previously, only the image had a duration limit while the tweet box PNG looped infinitely, causing multi-hour videos (e.g., 9,904 seconds)
- For images: Both inputs get `-loop 1 -t 5.0` parameters
- For videos: Tweet box PNG loops without duration limit (trimmed by `-shortest` flag)
- Prevents accidental generation of massive file sizes (390 MB → 1.6 MB after fix)

## Configuration

### Orchestrator Configuration

**Primary configuration file:** `orchestrator_config.json`

Key configuration sections:
- `scraper.topics`: Array of search topics (e.g., ["viral sports moments", "funny animals"])
- `scraper.max_tweets_per_topic`: Number of tweets to scrape per topic (default: 20)
- `scraper.search_type`: "Top" for trending or "Latest" for most recent (default: "Top")
- `scraper.min_engagement`: Engagement thresholds for filtering tweets
  - `likes`: Minimum likes required (default: 1000)
  - `retweets`: Minimum retweets required (default: 100)
  - `replies`: Minimum replies required (default: 50)
  - `total_score`: Minimum engagement score (default: 1500)
- `scraper.time_range`: Time range for tweet search (default: "7 days")
- `media_descriptions.enabled`: Enable/disable AI descriptions (default: true)
- `hook_generation.enabled`: Enable/disable hook generation (default: true)
- `hook_generation.hooks_per_tweet`: Number of hooks to generate (default: 10)
- `slack_integration.enabled`: Enable/disable Slack selection (default: true)
- `slack_integration.poll_interval_seconds`: How often to check for Slack replies (default: 10)
- `slack_integration.timeout_minutes`: Max time to wait for selections (default: 60)
- `slack_integration.auto_select_if_disabled`: Auto-select if Slack disabled (default: true)
- `slack_integration.auto_select_indices`: Which hooks to auto-select (default: [0, 4, 9])
- `media_download.enabled`: Enable/disable media download (default: true)
- `media_download.parallel_downloads`: Number of concurrent downloads (default: 5)
- `output.save_intermediate_files`: Save stage outputs for debugging (default: true)
- `output.intermediate_directory`: Where to save intermediate files (default: "./intermediate")
- `logging.log_level`: Logging verbosity - DEBUG, INFO, WARNING, ERROR (default: "INFO")
- `resume.enabled`: Enable checkpoint/resume functionality (default: true)

Example minimal configuration:
```json
{
  "scraper": {
    "topics": ["trending tech", "viral content"],
    "max_tweets_per_topic": 15
  },
  "slack_integration": {
    "enabled": false
  }
}
```

### Topics Customization (Manual Scripts)
Edit the `topics` list in `main()` (scraper.py:173-177):
```python
topics = [
    "artificial intelligence",
    "climate change",
    "cryptocurrency"
]
```

### Search Parameters
Modify the `search_trending_tweets()` call (scraper.py:183-187):
- `max_tweets`: Number of tweets per topic (default: 100)
- `search_type`: "Top" for trending/popular, "Latest" for most recent
- `top_n`: Number displayed per topic in console (default: 5)

### Video Generation Configuration
Edit `video_config.json` to customize video generation settings:

**Video Quality** (video_config.json:27-39):
- `resolution`: Video dimensions (default: 2160x3840 for 4K vertical 9:16)
- `framerate`: FPS (default: 30)
- `encoding.crf`: Quality level 0-51, lower = better (default: 18 for near-lossless)
- `encoding.preset`: Speed vs compression (default: "medium")

**Effects** (video_config.json:41-53):
- `background_blur.sigma`: Gaussian blur strength (default: 20)
- `media_scaling.max_width_percent`: Max media width as % of video (default: 90%)
- `media_scaling.max_height_percent`: Max media height as % of video (default: 70%)

**Positions** (video_config.json:55-71):
- `hook_text.y`: Vertical position of hook text in pixels (default: 150)
- `hook_text.max_width`: Maximum width for text wrapping (default: 1900)
- `tweet_box.x/y`: Position of tweet overlay ("center" or pixel value)

**Timing** (video_config.json:86-90):
- `media_duration`: Duration in seconds for static images converted to video (default: 5.0 for Instagram Reels)
- `fade_in_duration`: Fade in effect duration (default: 0.3)
- `fade_out_duration`: Fade out effect duration (default: 0.3)

**Processing** (video_config.json:78-84):
- `parallel_workers`: Number of videos to generate concurrently (default: 4)
- `cache_ttl_hours`: How long to cache downloaded media (default: 24)

**Asset Paths** (video_config.json:7-14):
- `tweet_boxes_dir`: Directory containing tweet overlay PNGs
- `fonts_dir`: Directory for custom fonts (optional)
- `cache_dir`: Temporary storage for downloaded media
- `output_dir`: Final video output location

## External Dependencies

**Apify Platform**
- Actor used: `web.harvester/easy-twitter-search-scraper`
- Requires API token from https://console.apify.com/account/integrations
- Free tier: $5/month platform credits
- Cost: ~$0.01-$0.40 per 1,000 tweets depending on actor

**Alternative Apify Actors** (documented in README.md:123-127):
- `scraper_one/x-posts-search`
- `powerai/twitter-search-scraper`
- `easyapi/twitter-trending-topics-scraper`

## Environment Variables

`.env` file (never committed, in .gitignore):
- `APIFY_API_TOKEN`: Your Apify API token (required for scraper.py)
- `OPENAI_API_KEY`: Your OpenAI API key (required for add_media_descriptions.py image processing)
- `GEMINI_API_KEY`: Your Google Gemini API key (required for add_media_descriptions.py video processing)
- `ANTHROPIC_API_KEY`: Your Anthropic API key (required for hook_creation.py hook generation)
- `SLACK_BOT_TOKEN`: Your Slack Bot User OAuth Token starting with `xoxb-` (required for slack_integration.py)
- `SLACK_CHANNEL_ID`: Your Slack channel ID (e.g., `C1234567890`) where tweets will be posted (required for slack_integration.py)

## Output Files

All JSON outputs and video files are excluded from git via .gitignore:

**Orchestrator Output Files:**
- `orchestrator_output_*.json` - Complete dataset from automated pipeline with local media paths
- `orchestrator.log` - Detailed execution log with timestamps and error messages
- `orchestrator_checkpoint.json` - Pipeline state for resume capability (auto-saved after each stage)
- `intermediate/intermediate_scraped_*.json` - Stage 1 output (if save_intermediate_files enabled)
- `intermediate/intermediate_described_*.json` - Stage 2 output (if save_intermediate_files enabled)
- `intermediate/intermediate_with_hooks_*.json` - Stage 3 output (if save_intermediate_files enabled)
- `intermediate/intermediate_selected_*.json` - Stage 4 output (if save_intermediate_files enabled)

**Manual Pipeline Tweet Data Files:**
- `trending_tweets_*.json` - Raw scraped tweet data with media URLs
- `*_described.json` - Processed files with AI-generated media descriptions
- `*_with_hooks.json` - Processed files with viral Instagram reel hooks (10 options per tweet)
- `*_selected.json` - Final files with user-selected hooks (3 chosen hooks per tweet) from Slack

**Video Generation Files:**
- `cache/` - Cached downloaded media (images/videos from tweets)
- `cache/media/` - Downloaded media files with MD5-based filenames
- `cache/media/*.json` - Metadata sidecar files for cached media
- `output/` - Generated Instagram Reel videos (.mp4 files)
- `media_download.log` - Media downloader activity log
- `video_generation.log` - Video generation logs
- `video_config.json` - Configuration for video generation (committed to repo)

## Dependencies

**Core dependencies** (requirements.txt):
- `apify-client>=1.0.0` - Apify API client for Twitter scraping
- `python-dotenv>=1.0.0` - Environment variable management
- `openai>=1.0.0` - OpenAI API client for GPT-4o Vision (image descriptions)
- `google-generativeai>=0.3.0` - Google Gemini API client (video descriptions)
- `anthropic>=0.39.0` - Anthropic API client for Claude 4.5 Sonnet (hook generation)
- `slack-sdk>=3.0.0` - Slack SDK for posting messages and polling thread replies (hook selection)
- `requests>=2.31.0` - HTTP library for downloading media files with streaming support
- `tqdm>=4.66.0` - Progress bar library for download tracking and orchestrator progress

**Orchestrator uses all existing scripts:**
- `scraper.py` - TwitterTrendingScraper class for stage 1
- `add_media_descriptions.py` - MediaDescriptionGenerator class for stage 2
- `hook_creation.py` - HookGenerator class for stage 3
- `slack_integration.py` - SlackIntegration class for stage 4
- `media_downloader.py` - MediaDownloader class for stage 5
