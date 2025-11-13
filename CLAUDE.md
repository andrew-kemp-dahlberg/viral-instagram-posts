# CLAUDE.md

This file provides guidance to Claude Code when working with this repository.

## Project Overview

A Python toolkit that scrapes trending tweets from Twitter/X using Apify, transforms them into viral Instagram content, and generates Instagram Reel videos. The project searches for tweets on customizable topics, ranks them by engagement metrics, generates AI-powered media descriptions and Instagram hooks, enables team selection via Slack, and produces final video content.

**Key Feature:** The `orchestrator.py` script automates the entire workflow end-to-end with a single command.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your API tokens

# Run the complete pipeline
python orchestrator.py

# Skip Slack integration and auto-select hooks
python orchestrator.py --skip-slack
```

## Pipeline Stages

The orchestrator chains 7 pipeline stages:

1. **Scraper** - Collects trending tweets using Apify (requires tweets with media using `filter:media`)
2. **Media Descriptions** - Adds AI descriptions (GPT-4o for images + Gemini for videos)
3. **Hook Generation** - Creates 10 viral hooks per tweet (Claude 4.5 Sonnet)
4. **Slack Integration** - Collects user selections or auto-selects (users can skip/cancel off-brand tweets)
5. **Media Download** - Downloads and caches all media files with MD5-based caching
6. **Asset Setup** - Validates FFmpeg, fonts, tweet boxes for video generation
7. **Video Generation** - Creates Instagram Reel videos using FFmpeg

## Configuration

**Primary config:** `orchestrator_config.json`

Key settings:
- `scraper.topics` - Search topics array
- `scraper.max_tweets_per_topic` - Number of tweets per topic (default: 20)
- `scraper.min_engagement` - Engagement thresholds (likes, retweets, replies, total_score)
- `slack_integration.enabled` - Enable/disable Slack (default: true)
- `slack_integration.auto_select_indices` - Auto-select hooks [0, 4, 9]
- `video_generation.enabled` - Enable/disable video generation (default: true)
- `output.save_intermediate_files` - Save stage outputs for debugging (default: true)
- `resume.enabled` - Enable checkpoint/resume (default: true)

**Video config:** `video_config.json`

Key settings:
- `resolution` - Video dimensions (default: 2160x3840, 4K vertical 9:16)
- `encoding.crf` - Quality level 0-51, lower = better (default: 18)
- `effects.background_blur.sigma` - Blur strength (default: 20)
- `timing.media_duration` - Duration for static images (default: 5.0 seconds for Instagram Reels)
- `positions.hook_text.y` - Vertical position of hook text (default: 150)

## Core Components

**PipelineOrchestrator** (orchestrator.py:46-608)
- Automates entire workflow with error handling and checkpointing
- Validates prerequisites before execution (API keys, directories)
- Saves checkpoint after each stage to `orchestrator_checkpoint.json`
- Outputs final dataset with video paths to `orchestrator_output_{timestamp}.json`

**TwitterTrendingScraper** (scraper.py:17-152)
- Uses Apify's `web.harvester/easy-twitter-search-scraper` actor
- Appends `filter:media` to search queries (only returns tweets with media)
- Filters out retweets to focus on original content
- Calculates engagement score: `likes + (retweets * 2) + replies`

**MediaDescriptionGenerator** (add_media_descriptions.py:18-160)
- GPT-4o Vision API for images (1-2 sentence descriptions)
- Gemini 1.5 Flash API for videos

**HookGenerator** (hook_creation.py:23-154)
- Uses Claude 4.5 Sonnet to generate 10 viral hooks per tweet
- Parker Doyle style: casual, confident, uses "bro", emojis, 5-15 words

**SlackIntegration** (slack_integration.py:23-450)
- Posts tweets to Slack with Block Kit formatting
- Polls for user selections (3 numbers: "1, 5, 9") or exclusions ("skip", "cancel", "off brand")
- Marks excluded tweets with `excluded: true` and `excluded_reason: "off_brand_or_cancelled"`

**MediaDownloader** (media_downloader.py:20-520)
- Downloads media with MD5-based cache keys to prevent duplicates
- TTL-based expiration (default: 24 hours)
- Retry logic: 3 attempts with exponential backoff
- Atomic writes with file validation using magic numbers

**FFmpegGenerator** (ffmpeg_generator.py:29-540)
- Generates Instagram Reels using single-pass filter_complex
- Auto-detects media type (image/video) and adjusts parameters
- Auto-selects tweet box based on hook line count (1, 2, or 3 lines)
- Cross-platform font detection (macOS, Linux, Windows)

**Video Processing Pipeline:**
1. Blurred background: Scale media to fill 9:16 + Gaussian blur
2. Clear media overlay: Scale to fit (90% width, 70% height) + center on background
3. Sharpening: unsharp filter (11:11:1.5)
4. Clarity: eq filter (brightness=0.02, contrast=1.2)
5. Tweet box overlay: PNG at configured position
6. Hook text: 72pt black text, centered

## Key Implementation Details

**Media Filtering** (scraper.py:56)
- Constructs search query: `search_query = f"{topic} filter:media"`
- Twitter API filters at source before data reaches scraper
- All returned tweets guaranteed to have media URLs

**Retweet Filtering** (scraper.py:62-65)
- Skips all retweets using `isRetweet` field
- Focuses exclusively on original content

**Image Duration Control** (ffmpeg_generator.py:366-382)
- For images: Both media input AND tweet box PNG get `-loop 1 -t 5.0` parameters
- Critical fix: Previously tweet box looped infinitely, causing multi-hour videos
- Prevents massive file sizes (390 MB → 1.6 MB after fix)

**FFmpeg Drawtext Filter Fix** (ffmpeg_generator.py:425-432)
- Fixed parsing error: `line_spacing=10[final]` caused FFmpeg to interpret `10[final]` as expression
- Error: "Invalid chars '[final]' at the end of expression '10[final]'"
- Fix: Separated parameter from output label by removing `line_spacing` and appending `[final]` separately
- Prevents "Invalid argument" errors during video generation (return code 234)

**Tweet Exclusion Feature**
- Users reply "skip", "cancel", or "off brand" in Slack to exclude tweets
- Orchestrator automatically skips excluded tweets in video generation stage
- Statistics track excluded vs active tweets separately

## Environment Variables

`.env` file (never committed):
- `APIFY_API_TOKEN` - Apify API token (scraper)
- `OPENAI_API_KEY` - OpenAI API key (image descriptions)
- `GEMINI_API_KEY` - Google Gemini API key (video descriptions)
- `ANTHROPIC_API_KEY` - Anthropic API key (hook generation)
- `SLACK_BOT_TOKEN` - Slack Bot OAuth Token starting with `xoxb-` (optional)
- `SLACK_CHANNEL_ID` - Slack channel ID like `C1234567890` (optional)

## Output Files

All excluded from git via .gitignore:

**Orchestrator:**
- `orchestrator_output_{timestamp}.json` - Final dataset with video paths
- `orchestrator.log` - Execution log
- `orchestrator_checkpoint.json` - Resume state
- `intermediate/*.json` - Stage outputs (if enabled)

**Manual Pipeline:**
- `trending_tweets_{timestamp}.json` - Raw scraped tweets
- `*_described.json` - With AI media descriptions
- `*_with_hooks.json` - With 10 hooks per tweet
- `*_selected.json` - With 3 selected hooks per tweet

**Video Generation:**
- `cache/media/*` - Downloaded media files (MD5-based filenames)
- `output/videos/*.mp4` - Generated Instagram Reel videos
- `video_generation.log` - Video generation logs

## Manual Commands

```bash
# Individual pipeline stages (if not using orchestrator)
python scraper.py
python add_media_descriptions.py trending_tweets_*.json
python hook_creation.py *_described.json
python slack_integration.py *_with_hooks.json

# Asset validation
python setup_assets.py

# Generate single video
python ffmpeg_generator.py <media_path> <hook_text> <output_path>

# Dry-run (preview FFmpeg command)
python ffmpeg_generator.py <media_path> <hook_text> <output_path> --dry-run
```

## Dependencies

```txt
apify-client>=1.0.0        # Twitter scraping
python-dotenv>=1.0.0       # Environment variables
openai>=1.0.0              # GPT-4o Vision (images)
google-generativeai>=0.3.0 # Gemini (videos)
anthropic>=0.39.0          # Claude 4.5 Sonnet (hooks)
slack-sdk>=3.0.0           # Slack integration
requests>=2.31.0           # Media downloads
tqdm>=4.66.0               # Progress bars
```

## External Services

**Apify Platform**
- Actor: `web.harvester/easy-twitter-search-scraper`
- Get token: https://console.apify.com/account/integrations
- Free tier: $5/month platform credits
- Cost: ~$0.01-$0.40 per 1,000 tweets

**Alternative Apify Actors:**
- `scraper_one/x-posts-search`
- `powerai/twitter-search-scraper`
- `easyapi/twitter-trending-topics-scraper`
