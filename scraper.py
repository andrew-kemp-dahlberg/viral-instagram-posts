#!/usr/bin/env python3
"""
Twitter Trending Topics Scraper using Apify
This script searches for tweets on customizable topics and filters for trending/popular content.
Modified to filter out retweets and extract media URLs.
"""

from apify_client import ApifyClient
import json
import os
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()


class TwitterTrendingScraper:
    def __init__(self, api_token):
        """
        Initialize the scraper with your Apify API token.
        
        Args:
            api_token (str): Your Apify API token from Settings > Integrations
        """
        self.client = ApifyClient(api_token)
    
    def search_trending_tweets(self, topics, max_tweets=50, search_type="Top"):
        """
        Search for trending tweets on specific topics.
        
        Args:
            topics (list): List of topics/keywords to search for
            max_tweets (int): Maximum number of tweets to retrieve per topic
            search_type (str): "Top" for trending/popular tweets, "Latest" for most recent
            
        Returns:
            dict: Dictionary with topics as keys and tweet data as values
        """
        all_results = {}
        
        for topic in topics:
            print(f"\n🔍 Searching for trending tweets about: {topic}")
            
            # Prepare the search input for web.harvester/easy-twitter-search-scraper
            # This actor works without authentication
            run_input = {
                "searchQueries": [topic],
                "maxTweets": max_tweets,
                "searchType": search_type,  # "Top" or "Latest"
            }
            
            try:
                # Run the Twitter Search actor (no authentication required)
                print(f"   Running search for '{topic}'...")
                run = self.client.actor("web.harvester/easy-twitter-search-scraper").call(run_input=run_input)
                
                # Fetch results from the dataset
                tweets = []
                dataset_items = self.client.dataset(run["defaultDatasetId"]).list_items()
                
                for item in dataset_items.items:
                    # Skip retweets
                    is_retweet = item.get("isRetweet", False)
                    if is_retweet:
                        continue
                    
                    # Extract tweet text - skip if not available
                    tweet_text = item.get("text", item.get("full_text", ""))
                    if not tweet_text:
                        continue
                    
                    # Extract media data if available
                    media_data = []
                    media_list = item.get("media", [])
                    if media_list:
                        for media_item in media_list:
                            media_info = {
                                "type": media_item.get("type", "unknown"),
                                "url": media_item.get("url", "")
                            }
                            if media_info["url"]:  # Only add if URL is available
                                media_data.append(media_info)
                    
                    # Also check for images field (alternative field name)
                    images_list = item.get("images", [])
                    if images_list and not media_data:
                        for image_url in images_list:
                            if image_url:
                                media_data.append({
                                    "type": "image",
                                    "url": image_url
                                })
                    
                    # Extract tweet data with safe fallbacks
                    tweet_data = {
                        "text": tweet_text,
                        "created_at": item.get("created_at", item.get("createdAt", item.get("timestamp", ""))),
                        "likes": item.get("likes", item.get("favorite_count", item.get("likeCount", 0))),
                        "retweets": item.get("retweets", item.get("retweet_count", item.get("retweetCount", 0))),
                        "replies": item.get("replies", item.get("reply_count", item.get("replyCount", 0))),
                        "views": item.get("views", item.get("viewCount", 0)),
                        "media": media_data,  # Add media array
                        "user": {
                            "name": item.get("author", {}).get("name", item.get("user", {}).get("name", item.get("userFullName", ""))),
                            "username": item.get("author", {}).get("userName", item.get("user", {}).get("screen_name", item.get("username", ""))),
                            "followers": item.get("author", {}).get("followers", item.get("user", {}).get("followers_count", item.get("totalFollowers", 0))),
                            "verified": item.get("author", {}).get("isVerified", item.get("user", {}).get("verified", item.get("verified", False)))
                        },
                        "url": item.get("url", item.get("tweetUrl", "")),
                    }
                    
                    # Calculate engagement score
                    tweet_data["engagement_score"] = (
                        tweet_data["likes"] + 
                        tweet_data["retweets"] * 2 + 
                        tweet_data["replies"]
                    )
                    
                    tweets.append(tweet_data)
                
                # Sort by engagement to get most trending
                tweets.sort(key=lambda x: x["engagement_score"], reverse=True)
                
                all_results[topic] = tweets
                print(f"   ✅ Found {len(tweets)} tweets for '{topic}' (retweets filtered out)")
                
            except Exception as e:
                print(f"   ❌ Error searching for '{topic}': {str(e)}")
                all_results[topic] = []
        
        return all_results
    
    def display_results(self, results, top_n=10):
        """
        Display the trending tweets in a readable format.
        
        Args:
            results (dict): Results from search_trending_tweets
            top_n (int): Number of top tweets to display per topic
        """
        for topic, tweets in results.items():
            print(f"\n{'='*80}")
            print(f"📊 TOP TRENDING TWEETS FOR: {topic.upper()}")
            print(f"{'='*80}")
            
            if not tweets:
                print("No tweets found.")
                continue
            
            for i, tweet in enumerate(tweets[:top_n], 1):
                print(f"\n{i}. @{tweet['user']['username']} ({tweet['user']['followers']:,} followers)")
                if tweet['user']['verified']:
                    print("   ✓ Verified Account")
                
                # Display tweet text (truncated if too long)
                text = tweet['text']
                if len(text) > 200:
                    text = text[:200] + "..."
                print(f"   {text}")
                
                # Display media information
                if tweet.get('media'):
                    print(f"   📎 Media attached: {len(tweet['media'])} item(s)")
                    for media_item in tweet['media']:
                        media_type = media_item.get('type', 'unknown')
                        media_url = media_item.get('url', '')
                        if media_url:
                            print(f"      - {media_type}: {media_url}")
                
                # Display engagement metrics
                metrics = f"   ❤️  {tweet['likes']:,} | 🔄 {tweet['retweets']:,} | 💬 {tweet['replies']:,}"
                if tweet.get('views', 0) > 0:
                    metrics += f" | 👁️  {tweet['views']:,}"
                print(metrics)
                
                if tweet['url']:
                    print(f"   🔗 {tweet['url']}")
    
    def save_to_json(self, results, filename=None):
        """
        Save results to a JSON file.
        
        Args:
            results (dict): Results from search_trending_tweets
            filename (str): Output filename (default: trending_tweets_TIMESTAMP.json)
        """
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"trending_tweets_{timestamp}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Results saved to: {filename}")


def main():
    """
    Example usage of the Twitter Trending Scraper
    """
    # Load API token from environment variable
    API_TOKEN = os.getenv("APIFY_API_TOKEN")
    
    if not API_TOKEN:
        raise ValueError(
            "APIFY_API_TOKEN not found in environment variables.\n"
            "Please create a .env file with your API token.\n"
            "Example: APIFY_API_TOKEN=your_token_here"
        )
    
    # Initialize the scraper
    scraper = TwitterTrendingScraper(API_TOKEN)
    
    # Define your topics of interest (customize these!)
    topics = [
        "artificial intelligence",
        "climate change",
        "cryptocurrency"
    ]
    
    print("🚀 Starting Twitter Trending Scraper...")
    print(f"📋 Topics to search: {', '.join(topics)}")
    
    # Search for trending tweets
    results = scraper.search_trending_tweets(
        topics=topics,
        max_tweets=100,  # Adjust as needed
        search_type="Top"  # Use "Top" for trending, "Latest" for most recent
    )
    
    # Display the results
    scraper.display_results(results, top_n=5)
    
    # Save to JSON file
    scraper.save_to_json(results)
    
    print("\n✅ Scraping complete!")


if __name__ == "__main__":
    main()