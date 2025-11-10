# Twitter Trending Topics Scraper

A Python script to find trending tweets on customizable topics using Apify's Twitter scraper actors. Filters out retweets to focus on original content, extracts media URLs, and optionally generates AI-powered descriptions for images and videos.

## Features

- 🔍 Search for tweets on any topic
- 📊 Filter for "Top" (trending/popular) or "Latest" tweets
- 🚫 Automatically filters out retweets to focus on original content
- 🖼️ Extract media URLs (images, videos) from tweets
- 🤖 AI-powered media descriptions using GPT-4o (images) and Gemini (videos)
- 💬 Extract tweet text, engagement metrics (likes, retweets, replies)
- 👤 Get user information (username, followers, verified status)
- 📁 Save results to JSON format
- 🎯 Calculate engagement scores to rank tweets

## Prerequisites

1. **Python 3.7+** installed on your system
2. **Apify Account** (free tier available)
   - Sign up at: https://console.apify.com/sign-up
3. **Apify API Token**
   - Get it from: https://console.apify.com/account/integrations
4. **Optional: AI API Keys** (for media descriptions)
   - **OpenAI API Key** - For image descriptions (GPT-4o Vision)
     - Get it from: https://platform.openai.com/api-keys
   - **Google Gemini API Key** - For video descriptions
     - Get it from: https://aistudio.google.com/app/apikey

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
```
   - **APIFY_API_TOKEN** (required): Get from https://console.apify.com/account/integrations
   - **OPENAI_API_KEY** (optional): Get from https://platform.openai.com/api-keys
   - **GEMINI_API_KEY** (optional): Get from https://aistudio.google.com/app/apikey
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

## Security Best Practices

- ✅ **DO** use the `.env` file for all API tokens (Apify, OpenAI, Gemini)
- ✅ **DO** add `.env` to your `.gitignore` file (already included)
- ✅ **DO** use `.env.example` as a template to share with others
- ❌ **DON'T** commit your `.env` file to version control
- ❌ **DON'T** share your API tokens publicly
- ❌ **DON'T** hardcode your API tokens in any scripts

## Additional Resources

### Scraping APIs
- Apify API Documentation: https://docs.apify.com/api/v2
- Python Client Documentation: https://docs.apify.com/api/client/python
- Twitter Scraper Options: https://apify.com/scrapers/twitter

### AI APIs
- OpenAI GPT-4o Vision API: https://platform.openai.com/docs/guides/vision
- Google Gemini API: https://ai.google.dev/gemini-api/docs
- OpenAI API Pricing: https://openai.com/api/pricing/
- Gemini API Pricing: https://ai.google.dev/pricing

## Legal Notice

This script only collects publicly available data from Twitter. Please ensure your use complies with:
- Twitter's Terms of Service
- Apify's Terms of Use
- Applicable data protection regulations (GDPR, CCPA, etc.)

## License

This script is provided as-is for educational and research purposes.