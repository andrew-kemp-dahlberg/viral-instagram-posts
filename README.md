# Twitter Trending Topics Scraper

A Python script to find trending tweets on customizable topics using Apify's Twitter scraper actors. Filters out retweets to focus on original content and extracts media URLs for further analysis.

## Features

- 🔍 Search for tweets on any topic
- 📊 Filter for "Top" (trending/popular) or "Latest" tweets
- 🚫 Automatically filters out retweets to focus on original content
- 🖼️ Extract media URLs (images, videos) from tweets
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

## Installation

1. Install the required Python packages:
```bash
pip install apify-client python-dotenv
```

Or use the requirements file:
```bash
pip install -r requirements.txt
```

## Setup

1. **Create a `.env` file** in the project directory (copy from `.env.example`):
```bash
cp .env.example .env
```

2. **Add your Apify API token** to the `.env` file:
```
APIFY_API_TOKEN=your_actual_token_here
```
   - Get your token from: https://console.apify.com/account/integrations
   - **Important:** Never commit your `.env` file to version control!

3. **Customize the topics** you want to search in `twitter_trending_scraper.py`:
```python
topics = [
    "artificial intelligence",
    "climate change",
    "cryptocurrency"
]
```

## Usage

Run the script:
```bash
python twitter_trending_scraper.py
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

## Cost Information

Twitter scraping costs vary by actor. The Easy Twitter Search Scraper used in this script is cost-effective. The free Apify tier includes:
- $5 of free platform credits per month
- Sufficient for thousands of tweets per month depending on the actor used

Typical costs range from $0.01 to $0.40 per 1,000 tweets depending on the complexity and features of the actor.

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

## Security Best Practices

- ✅ **DO** use the `.env` file for your API token
- ✅ **DO** add `.env` to your `.gitignore` file (already included)
- ✅ **DO** use `.env.example` as a template to share with others
- ❌ **DON'T** commit your `.env` file to version control
- ❌ **DON'T** share your API token publicly
- ❌ **DON'T** hardcode your API token in the script

## Additional Resources

- Apify API Documentation: https://docs.apify.com/api/v2
- Python Client Documentation: https://docs.apify.com/api/client/python
- Twitter Scraper Options: https://apify.com/scrapers/twitter

## Legal Notice

This script only collects publicly available data from Twitter. Please ensure your use complies with:
- Twitter's Terms of Service
- Apify's Terms of Use
- Applicable data protection regulations (GDPR, CCPA, etc.)

## License

This script is provided as-is for educational and research purposes.