# Twitter Trending Topics Scraper & Instagram Hook Generator

A Python toolkit to find trending tweets on customizable topics using Apify's Twitter scraper actors, then transform them into viral Instagram reel hooks. Filters out retweets to focus on original content, extracts media URLs, generates AI-powered descriptions for images and videos, creates scroll-stopping text hooks in Parker Doyle's viral style, and sends them to Slack for team review and hook selection.

## Features

- 🔍 Search for tweets on any topic
- 📊 Filter for "Top" (trending/popular) or "Latest" tweets
- 🚫 Automatically filters out retweets to focus on original content
- 🖼️ Extract media URLs (images, videos) from tweets
- 🤖 AI-powered media descriptions using GPT-4o (images) and Gemini (videos)
- 🎣 Generate viral Instagram reel hooks using Claude 4.5 Sonnet in Parker Doyle's style
- 💬 Extract tweet text, engagement metrics (likes, retweets, replies)
- 👤 Get user information (username, followers, verified status)
- 📁 Save results to JSON format
- 🎯 Calculate engagement scores to rank tweets
- 📲 Send tweets to Slack for team review with rich formatting
- ✅ Select top 3 hooks via Slack thread replies for each tweet

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Apify Account** (free tier available)
   - Sign up at: https://console.apify.com/sign-up
3. **Apify API Token**
   - Get it from: https://console.apify.com/account/integrations
4. **Optional: AI API Keys**
   - **OpenAI API Key** - For image descriptions (GPT-4o Vision)
     - Get it from: https://platform.openai.com/api-keys
   - **Google Gemini API Key** - For video descriptions
     - Get it from: https://aistudio.google.com/app/apikey
   - **Anthropic API Key** - For Instagram hook generation (Claude 4.5 Sonnet)
     - Get it from: https://console.anthropic.com/settings/keys
5. **Optional: Slack Bot** (for hook selection workflow)
   - **Slack Bot Token** - For posting tweets and collecting user selections
     - Create a Slack App at: https://api.slack.com/apps
     - Add bot scopes: `chat:write`, `channels:history`, `channels:read`
     - Install to workspace and get Bot User OAuth Token (starts with `xoxb-`)
   - **Slack Channel ID** - Channel where tweets will be posted
     - Right-click channel in Slack → View channel details → Copy ID

## Installation

Install the required Python packages:
```bash
pip install -r requirements.txt
```

This will install:
- `apify-client` - For Twitter scraping
- `python-dotenv` - For environment variable management
- `openai` - For GPT-4o image descriptions (optional)
- `google-generativeai` - For Gemini video descriptions (optional)
- `anthropic` - For Claude 4.5 Sonnet hook generation (optional)
- `slack-sdk` - For Slack integration and hook selection (optional)

## Setup

1. **Create a `.env` file** in the project directory (copy from `.env.example`):
```bash
cp .env.example .env
```

2. **Add your API tokens** to the `.env` file:
```
APIFY_API_TOKEN=your_actual_token_here
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
SLACK_BOT_TOKEN=xoxb-your-slack-bot-token-here
SLACK_CHANNEL_ID=C1234567890
```
   - **APIFY_API_TOKEN** (required): Get from https://console.apify.com/account/integrations
   - **OPENAI_API_KEY** (optional): Get from https://platform.openai.com/api-keys
   - **GEMINI_API_KEY** (optional): Get from https://aistudio.google.com/app/apikey
   - **ANTHROPIC_API_KEY** (optional): Get from https://console.anthropic.com/settings/keys
   - **SLACK_BOT_TOKEN** (optional): Your Slack Bot User OAuth Token from https://api.slack.com/apps
   - **SLACK_CHANNEL_ID** (optional): Your Slack channel ID (right-click channel → View details → Copy ID)
   - **Important:** Never commit your `.env` file to version control!

3. **Customize the topics** you want to search in `scraper.py`:
```python
topics = [
    "artificial intelligence",
    "climate change",
    "cryptocurrency"
]
```

## Usage

### Step 1: Scrape Tweets

Run the scraper to collect tweets:
```bash
python scraper.py
```

This will create a JSON file: `trending_tweets_YYYYMMDD_HHMMSS.json`

### Step 2: Add Media Descriptions (Optional)

Generate AI-powered descriptions for images and videos:
```bash
python add_media_descriptions.py trending_tweets_20251109_164707.json
```

This will create a new file: `trending_tweets_20251109_164707_described.json`

You can specify a custom output file:
```bash
python add_media_descriptions.py input.json output.json
```

### Step 3: Generate Instagram Hooks (Optional)

Transform tweets into viral Instagram reel hooks using Claude AI:
```bash
python hook_creation.py trending_tweets_20251109_164707_described.json
```

This will create a new file: `trending_tweets_20251109_164707_with_hooks.json`

Each tweet will receive 10 text hook options in Parker Doyle's viral style:
- Casual, confident language ("bro," "dude," "man")
- Strategic emoji usage (💀 and 😭)
- 5-15 words for maximum scroll-stopping impact
- Socially calibrated for relatability

You can specify a custom output file:
```bash
python hook_creation.py input.json output_with_hooks.json
```

### Step 4: Select Hooks via Slack (Optional)

Send tweets to Slack for team review and collect hook selections:
```bash
python slack_integration.py trending_tweets_20251109_164707_with_hooks.json
```

This will:
1. **Post to Slack**: Send all tweets to your configured Slack channel, grouped by topic
2. **Format richly**: Display tweet text, engagement metrics, media with descriptions, and all 10 hooks
3. **Wait for selections**: Poll threads for your replies with 3 hook numbers (e.g., "1, 5, 9")
4. **Save selections**: Create a new file with your top 3 chosen hooks for each tweet

The script will poll for selections every 10 seconds with a 1-hour timeout by default.

Output file: `trending_tweets_20251109_164707_selected.json`

You can specify a custom output file:
```bash
python slack_integration.py input_with_hooks.json output_selected.json
```

**How to select hooks in Slack:**
1. Find the tweet message in your Slack channel
2. Click "Reply in thread" or hover and click the message icon
3. Type 3 numbers corresponding to your favorite hooks (e.g., "1, 5, 9" or "2 7 10")
4. The script will automatically detect your selection and save it

### Customization Options

**Change topics to search:**
```python
topics = ["AI", "machine learning", "deep learning"]
```

**Adjust number of tweets per topic:**
```python
results = scraper.search_trending_tweets(
    topics=topics,
    max_tweets=100,  # Get more tweets
    search_type="Top"
)
```

**Choose search type:**
- `"Top"` - Get trending/popular tweets (most engaging)
- `"Latest"` - Get most recent tweets

**Display more/fewer results:**
```python
scraper.display_results(results, top_n=10)  # Show top 10 tweets
```

## Output

The script will:
1. Display trending tweets in the console
2. Save all results to a JSON file: `trending_tweets_TIMESTAMP.json`

### Sample Output Format:

```
📊 TOP TRENDING TWEETS FOR: ARTIFICIAL INTELLIGENCE
================================================================================

1. @elonmusk (150M followers)
   ✓ Verified Account
   AI is both the best and worst thing for our civilization...
   📎 Media attached: 1 item(s)
      - image: https://pbs.twimg.com/media/...
   ❤️  50,234 | 🔄 12,456 | 💬 3,210
   🔗 https://twitter.com/elonmusk/status/...
```

**Note:** The scraper automatically filters out retweets, showing only original tweets.

### Media Descriptions Output

After running `add_media_descriptions.py`, each media object will include a `description` field:

```json
{
  "media": [
    {
      "type": "image",
      "url": "https://pbs.twimg.com/media/...",
      "description": "A graph showing AI adoption trends over the past decade with an upward trajectory."
    }
  ]
}
```

### Instagram Hooks Output

After running `hook_creation.py`, each tweet will include a `hooks` array with 10 viral hook options:

```json
{
  "text": "Just witnessed the most insane basketball shot of the year...",
  "media": [...],
  "hooks": [
    "Bro just casually made the shot of the year 😭",
    "This really happened in a high school game 💀",
    "Never forget when he did the impossible",
    "Man woke up and chose greatness 😭",
    "This shot broke the internet for a reason",
    "Bro really defied physics with this one",
    "The audacity to even attempt this 💀",
    "High school basketball just peaked",
    "This is why we watch sports 😭",
    "Bro said let me go viral real quick"
  ]
}
```

### Selected Hooks Output (Slack)

After running `slack_integration.py`, each tweet will include the user's selected hooks:

```json
{
  "text": "Just witnessed the most insane basketball shot of the year...",
  "media": [...],
  "hooks": [...],
  "selected_hooks": [
    "Bro just casually made the shot of the year 😭",
    "Man woke up and chose greatness 😭",
    "This shot broke the internet for a reason"
  ],
  "selected_hook_indices": [1, 4, 5],
  "selection_timestamp": "2025-11-09T14:32:15.123456"
}
```

The `selected_hooks` array contains the actual text of the 3 chosen hooks, while `selected_hook_indices` stores which numbers were selected (1-10), and `selection_timestamp` records when the selection was made.

## Cost Information

### Twitter Scraping Costs

The Easy Twitter Search Scraper used in this script is cost-effective. The free Apify tier includes:
- $5 of free platform credits per month
- Sufficient for thousands of tweets per month depending on the actor used

Typical costs range from $0.01 to $0.40 per 1,000 tweets depending on the complexity and features of the actor.

### AI Media Description Costs

**OpenAI GPT-4o (Images):**
- Pricing: ~$0.00015 per image (based on GPT-4o pricing at 150 tokens)
- Free tier: New accounts get $5 credit (expires after 3 months)
- Example: ~33,000 image descriptions for $5

**Google Gemini 1.5 Flash (Videos):**
- Pricing: Free tier available with rate limits
- Free tier: 15 requests per minute, 1,500 requests per day
- Paid tier: Very low cost per request (~$0.00001 per request)

**Anthropic Claude 4.5 Sonnet (Instagram Hooks):**
- Pricing: ~$0.003 per hook generation (based on Claude 4.5 Sonnet pricing at ~1,000 tokens)
- Free tier: New accounts get $5 credit
- Example: ~1,600 hook generations for $5
- Generates 10 hook options per tweet

### Slack Integration Costs

**Slack API:**
- **Free tier**: Completely free for most use cases
- The Slack SDK used in this project only makes basic API calls (posting messages, reading threads)
- No costs unless you exceed Slack's generous rate limits (typically thousands of requests per minute)
- Works with any Slack workspace (free or paid)

## API Reference

This script uses the following Apify actor:
- **Actor ID:** `web.harvester/easy-twitter-search-scraper`
- **Features:** Works without authentication, extracts tweets from search results
- Documentation: https://apify.com/web.harvester/easy-twitter-search-scraper

Alternative actors you can try:
- `scraper_one/x-posts-search` - X (Twitter) Posts Search
- `powerai/twitter-search-scraper` - Twitter Search Scraper with multiple tabs support
- `easyapi/twitter-trending-topics-scraper` - Twitter Trending Topics Scraper (for country-specific trends)

## Troubleshooting

### Scraper Issues

**Error: "APIFY_API_TOKEN not found in environment variables"**
- Make sure you've created a `.env` file in the project directory
- Verify the file contains: `APIFY_API_TOKEN=your_token_here`
- Don't include quotes around the token value

**Error: "Invalid API token"**
- Verify your token at: https://console.apify.com/account/integrations
- Make sure there are no extra spaces in the `.env` file

**No tweets found:**
- Try different search terms
- Increase `max_tweets` parameter
- Change `search_type` from "Top" to "Latest"

**Rate limiting:**
- Apify API has a rate limit of 250,000 requests per minute globally
- Free tier accounts may have additional limitations

### Media Description Issues

**Warning: "OPENAI_API_KEY not found in environment"**
- Add your OpenAI API key to the `.env` file
- Get a key from: https://platform.openai.com/api-keys
- This is only needed if you want to generate image descriptions

**Warning: "GEMINI_API_KEY not found in environment"**
- Add your Gemini API key to the `.env` file
- Get a key from: https://aistudio.google.com/app/apikey
- This is only needed if you want to generate video descriptions

**Error describing media:**
- Check your API keys are valid and have available credits
- Verify the media URLs are accessible
- Check rate limits for your API tier

### Hook Generation Issues

**Error: "ANTHROPIC_API_KEY not found in environment variables"**
- Add your Anthropic API key to the `.env` file
- Get a key from: https://console.anthropic.com/settings/keys
- This is only needed if you want to generate Instagram hooks

**Warning: "Only generated X hooks (expected 10)"**
- This is informational - Claude may occasionally generate fewer than 10 hooks
- The script will still save whatever hooks were generated
- Usually happens when the tweet content doesn't match hook style guidelines

**Error generating hooks:**
- Check your Anthropic API key is valid and has available credits
- Verify you're passing a file with media descriptions (from `add_media_descriptions.py`)
- Check rate limits for your API tier
- Ensure the input JSON file has valid tweet data

### Slack Integration Issues

**Error: "SLACK_BOT_TOKEN not found in environment variables"**
- Add your Slack Bot Token to the `.env` file
- Create a Slack App at: https://api.slack.com/apps
- Install the app to your workspace and copy the Bot User OAuth Token (starts with `xoxb-`)
- Make sure the token is in `.env` as: `SLACK_BOT_TOKEN=xoxb-your-token`

**Error: "SLACK_CHANNEL_ID not found in environment variables"**
- Add your Slack channel ID to the `.env` file
- Right-click the channel in Slack → View channel details → Copy the channel ID
- Add to `.env` as: `SLACK_CHANNEL_ID=C1234567890`

**Error: "not_in_channel" or "channel_not_found"**
- Make sure you've invited your bot to the channel
- In Slack, go to the channel and type: `/invite @YourBotName`
- Or add the bot via channel settings → Integrations → Add apps

**Error: "missing_scope" or permission errors**
- Your Slack app needs these bot token scopes:
  - `chat:write` - To post messages
  - `channels:history` - To read thread replies
  - `channels:read` - To access channel information
- Add these scopes in your Slack App settings → OAuth & Permissions → Scopes
- Reinstall the app to your workspace after adding scopes

**No selections detected / timeout reached:**
- Make sure you're replying **in the thread** (not as a new message)
- Verify your reply contains 3 numbers (e.g., "1, 5, 9")
- The script checks every 10 seconds - give it time to detect your reply
- Check the console output to see if the script detected your selection
- Default timeout is 1 hour - you can adjust this in the script if needed

**Selections not saving correctly:**
- Verify the hook numbers you entered are valid (1-10)
- Make sure you entered exactly 3 numbers
- Check that the input JSON file has a `hooks` array with at least the numbers you selected
- The script will show warnings if hook numbers are out of range

## Security Best Practices

- ✅ **DO** use the `.env` file for all API tokens (Apify, OpenAI, Gemini, Anthropic, Slack)
- ✅ **DO** add `.env` to your `.gitignore` file (already included)
- ✅ **DO** use `.env.example` as a template to share with others
- ✅ **DO** use bot token scopes appropriately (only request permissions you need)
- ❌ **DON'T** commit your `.env` file to version control
- ❌ **DON'T** share your API tokens or Slack bot tokens publicly
- ❌ **DON'T** hardcode your API tokens in any scripts
- ❌ **DON'T** use user tokens for Slack - always use bot tokens (xoxb-) for automation

## Additional Resources

### Scraping APIs
- Apify API Documentation: https://docs.apify.com/api/v2
- Python Client Documentation: https://docs.apify.com/api/client/python
- Twitter Scraper Options: https://apify.com/scrapers/twitter

### AI APIs
- OpenAI GPT-4o Vision API: https://platform.openai.com/docs/guides/vision
- Google Gemini API: https://ai.google.dev/gemini-api/docs
- Anthropic Claude API: https://docs.anthropic.com/en/api/getting-started
- OpenAI API Pricing: https://openai.com/api/pricing/
- Gemini API Pricing: https://ai.google.dev/pricing
- Anthropic API Pricing: https://www.anthropic.com/pricing

### Slack APIs
- Slack API Documentation: https://api.slack.com/
- Creating a Slack App: https://api.slack.com/start/quickstart
- Slack Bot Token Scopes: https://api.slack.com/scopes
- Slack SDK for Python: https://slack.dev/python-slack-sdk/
- Block Kit Builder (for message formatting): https://app.slack.com/block-kit-builder/

## Legal Notice

This script only collects publicly available data from Twitter. Please ensure your use complies with:
- Twitter's Terms of Service
- Apify's Terms of Use
- Applicable data protection regulations (GDPR, CCPA, etc.)

## License

This script is provided as-is for educational and research purposes.