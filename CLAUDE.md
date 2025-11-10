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

## Output Files

All JSON outputs are excluded from git via .gitignore:
- `trending_tweets_*.json` - Raw scraped tweet data with media URLs
- `*_described.json` - Processed files with AI-generated media descriptions

## Dependencies

**Core dependencies** (requirements.txt):
- `apify-client>=1.0.0` - Apify API client for Twitter scraping
- `python-dotenv>=1.0.0` - Environment variable management
- `openai>=1.0.0` - OpenAI API client for GPT-4o Vision (image descriptions)
- `google-generativeai>=0.3.0` - Google Gemini API client (video descriptions)
