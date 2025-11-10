# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Python script that scrapes trending tweets from Twitter/X using the Apify platform. The project searches for tweets on customizable topics and ranks them by engagement metrics (likes, retweets, replies). Filters out retweets to focus on original content and extracts media URLs (images, videos) from tweets.

## Development Commands

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

## Code Architecture

### Core Components

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

### Data Flow

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

## Configuration

### Topics Customization
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

All JSON outputs are excluded from git via .gitignore:
- `trending_tweets_*.json` - Raw scraped tweet data with media URLs
- `*_described.json` - Processed files with AI-generated media descriptions
- `*_with_hooks.json` - Processed files with viral Instagram reel hooks (10 options per tweet)
- `*_selected.json` - Final files with user-selected hooks (3 chosen hooks per tweet) from Slack

## Dependencies

**Core dependencies** (requirements.txt):
- `apify-client>=1.0.0` - Apify API client for Twitter scraping
- `python-dotenv>=1.0.0` - Environment variable management
- `openai>=1.0.0` - OpenAI API client for GPT-4o Vision (image descriptions)
- `google-generativeai>=0.3.0` - Google Gemini API client (video descriptions)
- `anthropic>=0.39.0` - Anthropic API client for Claude 4.5 Sonnet (hook generation)
- `slack-sdk>=3.0.0` - Slack SDK for posting messages and polling thread replies (hook selection)
