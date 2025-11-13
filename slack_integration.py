#!/usr/bin/env python3
"""
Slack Integration for Instagram Hook Selection

This script sends processed tweets (with media descriptions and hooks) to Slack,
allows users to select their top 3 hooks via Slack thread replies, and saves
the selections to a new JSON file.

Usage:
    python slack_integration.py trending_tweets_20251109_164707_with_hooks.json
    python slack_integration.py input.json output_selected.json
"""

import os
import sys
import json
import time
from typing import List, Dict, Any, Optional
from datetime import datetime
from dotenv import load_dotenv
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

# Load environment variables
load_dotenv()


class SlackIntegration:
    """Handles Slack posting and hook selection polling."""

    def __init__(self, input_file: str, output_file: Optional[str] = None):
        """
        Initialize Slack integration.

        Args:
            input_file: Path to JSON file with hooks (from hook_creation.py)
            output_file: Optional output path (defaults to [input]_selected.json)
        """
        self.input_file = input_file
        self.output_file = output_file or self._generate_output_filename()

        # Initialize Slack client
        slack_token = os.getenv("SLACK_BOT_TOKEN")
        if not slack_token:
            raise ValueError("SLACK_BOT_TOKEN not found in environment variables")

        self.slack_client = WebClient(token=slack_token)
        self.channel_id = os.getenv("SLACK_CHANNEL_ID")
        if not self.channel_id:
            raise ValueError("SLACK_CHANNEL_ID not found in environment variables")

        # Load tweet data
        with open(input_file, 'r', encoding='utf-8') as f:
            self.data = json.load(f)

        # Track message timestamps for polling
        self.message_threads = {}  # {tweet_index: {"ts": timestamp, "topic": topic}}

    def _generate_output_filename(self) -> str:
        """Generate output filename based on input filename."""
        base = self.input_file.replace('_with_hooks.json', '')
        base = base.replace('.json', '')
        return f"{base}_selected.json"

    def send_tweets_to_slack(self):
        """
        Send tweets to Slack grouped by topic with formatted messages.
        Returns message thread mapping for polling.
        """
        print(f"📤 Sending tweets to Slack channel: {self.channel_id}")

        # Group tweets by topic/query
        tweets_by_topic = {}
        for i, tweet in enumerate(self.data):
            query = tweet.get('query', 'Unknown Topic')
            if query not in tweets_by_topic:
                tweets_by_topic[query] = []
            tweets_by_topic[query].append((i, tweet))

        # Send tweets grouped by topic
        for topic, tweets in tweets_by_topic.items():
            try:
                # Send topic header
                header_response = self.slack_client.chat_postMessage(
                    channel=self.channel_id,
                    text=f"📊 *{topic.upper()}* ({len(tweets)} tweets)",
                    blocks=[
                        {
                            "type": "header",
                            "text": {
                                "type": "plain_text",
                                "text": f"📊 {topic.upper()}"
                            }
                        },
                        {
                            "type": "context",
                            "elements": [
                                {
                                    "type": "mrkdwn",
                                    "text": f"Found {len(tweets)} trending tweets"
                                }
                            ]
                        },
                        {
                            "type": "divider"
                        }
                    ]
                )

                # Send individual tweets
                for idx, tweet in tweets:
                    blocks = self._format_tweet_message(tweet, idx)
                    response = self.slack_client.chat_postMessage(
                        channel=self.channel_id,
                        text=f"Tweet #{idx + 1}: Select your top 3 hooks",
                        blocks=blocks
                    )

                    # Store thread timestamp for polling
                    self.message_threads[idx] = {
                        "ts": response["ts"],
                        "topic": topic
                    }

                    # Small delay to avoid rate limits
                    time.sleep(0.5)

                print(f"✅ Sent {len(tweets)} tweets for topic: {topic}")

            except SlackApiError as e:
                print(f"❌ Error sending to Slack: {e.response['error']}")
                raise

        print(f"\n✨ All tweets sent to Slack!")
        print(f"📝 Reply to each tweet thread with 3 hook numbers (e.g., '1, 5, 9')")
        return self.message_threads

    def _format_tweet_message(self, tweet: Dict[str, Any], index: int) -> List[Dict]:
        """
        Format tweet as Slack Block Kit message.

        Args:
            tweet: Tweet data dictionary
            index: Tweet index in the list

        Returns:
            List of Slack blocks for the message
        """
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"Tweet #{index + 1}"
                }
            }
        ]

        # Tweet text and author info
        tweet_text = tweet.get('text', 'No text available')
        author = tweet.get('author', 'Unknown')
        author_handle = tweet.get('author_handle', 'unknown')

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*@{author_handle}* ({author})\n\n{tweet_text}"
            }
        })

        # Engagement metrics
        likes = tweet.get('likes', 0)
        retweets = tweet.get('retweets', 0)
        replies = tweet.get('replies', 0)
        engagement_score = tweet.get('engagement_score', 0)

        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"❤️ *Likes:* {likes:,}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"🔄 *Retweets:* {retweets:,}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"💬 *Replies:* {replies:,}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"📊 *Score:* {engagement_score:,}"
                }
            ]
        })

        # Tweet URL
        tweet_url = tweet.get('url', '')
        if tweet_url:
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🔗 <{tweet_url}|View Tweet>"
                }
            })

        # Media and descriptions
        media = tweet.get('media', [])
        if media:
            blocks.append({
                "type": "divider"
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*📸 Media ({len(media)} items):*"
                }
            })

            for i, media_item in enumerate(media, 1):
                media_type = media_item.get('type', 'unknown')
                media_url = media_item.get('url', 'No URL')
                description = media_item.get('description', 'No description available')

                blocks.append({
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"*{i}. {media_type.upper()}*\n{description}\n<{media_url}|View Media>"
                    }
                })

        # Hooks section
        hooks = tweet.get('hooks', [])
        if hooks:
            blocks.append({
                "type": "divider"
            })
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": "*🎣 Generated Hooks (Select your top 3):*"
                }
            })

            # Format hooks as numbered list
            hooks_text = "\n".join([f"{i}. {hook}" for i, hook in enumerate(hooks, 1)])
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": hooks_text
                }
            })

            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "💡 Reply with 3 numbers (e.g., '1, 5, 9') to select hooks\n🚫 Reply with 'skip' or 'cancel' to exclude this tweet"
                    }
                ]
            })

        blocks.append({"type": "divider"})

        return blocks

    def poll_for_selections(self, timeout: int = 3600, check_interval: int = 10):
        """
        Poll Slack threads for user hook selections.

        Args:
            timeout: Maximum time to wait in seconds (default: 1 hour)
            check_interval: How often to check for replies in seconds

        Returns:
            Tuple of (selections, excluded_tweets)
            - selections: {tweet_index: [hook1, hook2, hook3]}
            - excluded_tweets: set of tweet indices to skip
        """
        print(f"\n⏳ Polling for selections (timeout: {timeout}s, checking every {check_interval}s)")
        print(f"📝 Waiting for {len(self.message_threads)} tweet selections...\n")
        print(f"💡 Reply with 3 numbers (e.g., '1, 5, 9') to select hooks")
        print(f"💡 Reply with 'skip' or 'cancel' to exclude off-brand tweets\n")

        selections = {}  # {tweet_index: [hook1, hook2, hook3]}
        excluded_tweets = set()  # Set of tweet indices to skip
        start_time = time.time()

        while (len(selections) + len(excluded_tweets)) < len(self.message_threads):
            if time.time() - start_time > timeout:
                print(f"⏰ Timeout reached. Got {len(selections)} selections and {len(excluded_tweets)} excluded.")
                break

            # Check each thread for replies
            for tweet_idx, thread_info in self.message_threads.items():
                if tweet_idx in selections or tweet_idx in excluded_tweets:
                    continue  # Already processed this tweet

                try:
                    # Get thread replies
                    response = self.slack_client.conversations_replies(
                        channel=self.channel_id,
                        ts=thread_info["ts"]
                    )

                    # Look for user replies (skip the bot's original message)
                    messages = response.get("messages", [])
                    for msg in messages[1:]:  # Skip first message (the tweet)
                        text = msg.get("text", "")
                        parsed = self._parse_selection(text)

                        if parsed == "SKIP":
                            # User wants to skip this tweet
                            excluded_tweets.add(tweet_idx)
                            print(f"🚫 Tweet #{tweet_idx + 1}: Excluded (off-brand/cancelled)")
                            break
                        elif parsed and len(parsed) == 3:
                            # Validate hook numbers
                            hooks = self.data[tweet_idx].get('hooks', [])
                            if all(1 <= num <= len(hooks) for num in parsed):
                                selections[tweet_idx] = parsed
                                print(f"✅ Tweet #{tweet_idx + 1}: Selected hooks {parsed}")
                                break
                            else:
                                print(f"⚠️  Tweet #{tweet_idx + 1}: Invalid hook numbers {parsed} (must be 1-{len(hooks)})")

                except SlackApiError as e:
                    print(f"❌ Error polling thread {tweet_idx}: {e.response['error']}")

            # Progress update
            remaining = len(self.message_threads) - len(selections) - len(excluded_tweets)
            if remaining > 0:
                print(f"⏳ Still waiting for {remaining} responses... ({int(time.time() - start_time)}s elapsed)")
                time.sleep(check_interval)

        return selections, excluded_tweets

    def _parse_selection(self, text: str) -> Optional[List[int]] | str:
        """
        Parse user selection from text like '1, 5, 9' or '1 5 9'.
        Also detects skip/cancel commands.

        Args:
            text: User's reply text

        Returns:
            List of hook numbers (1-indexed), "SKIP" for cancelled tweets, or None if invalid
        """
        import re

        # Check for skip/cancel keywords (case-insensitive)
        text_lower = text.lower().strip()
        skip_keywords = ['skip', 'cancel', 'pass', 'no', 'skip this', 'cancel this', 'off brand', 'offbrand']

        if any(keyword in text_lower for keyword in skip_keywords):
            return "SKIP"

        # Extract all numbers from the text
        numbers = re.findall(r'\d+', text)

        if len(numbers) >= 3:
            # Take first 3 numbers
            return [int(numbers[0]), int(numbers[1]), int(numbers[2])]

        return None

    def save_selected_hooks(self, selections: Dict[int, List[int]], excluded_tweets: set = None):
        """
        Save selected hooks to output JSON file.
        Marks excluded tweets so they can be filtered from further processing.

        Args:
            selections: Dictionary mapping tweet index to list of hook numbers
            excluded_tweets: Set of tweet indices that were cancelled/skipped
        """
        print(f"\n💾 Saving selections to {self.output_file}")

        if excluded_tweets is None:
            excluded_tweets = set()

        # Update data with selected hooks
        for tweet_idx, hook_numbers in selections.items():
            hooks = self.data[tweet_idx].get('hooks', [])
            selected = [hooks[num - 1] for num in hook_numbers if 1 <= num <= len(hooks)]
            self.data[tweet_idx]['selected_hooks'] = selected

            # Add selection metadata
            self.data[tweet_idx]['selected_hook_indices'] = hook_numbers
            self.data[tweet_idx]['selection_timestamp'] = datetime.now().isoformat()
            self.data[tweet_idx]['excluded'] = False

        # Mark excluded tweets
        for tweet_idx in excluded_tweets:
            self.data[tweet_idx]['excluded'] = True
            self.data[tweet_idx]['excluded_reason'] = 'off_brand_or_cancelled'
            self.data[tweet_idx]['excluded_timestamp'] = datetime.now().isoformat()
            self.data[tweet_idx]['selected_hooks'] = []  # Empty hooks list
            print(f"🚫 Marked tweet #{tweet_idx + 1} as excluded")

        # Save to file
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, indent=2, ensure_ascii=False)

        print(f"✅ Saved {len(selections)} selections and {len(excluded_tweets)} exclusions to {self.output_file}")
        return self.output_file

    def process_json_file(self, poll_timeout: int = 3600, check_interval: int = 10):
        """
        Main orchestrator: send tweets, poll for selections, save results.

        Args:
            poll_timeout: Maximum time to wait for selections (seconds)
            check_interval: How often to check for replies (seconds)

        Returns:
            Path to output file with selected hooks
        """
        print("=" * 60)
        print("🎣 Instagram Hook Selection via Slack")
        print("=" * 60)
        print(f"Input:  {self.input_file}")
        print(f"Output: {self.output_file}")
        print(f"Tweets: {len(self.data)}")
        print("=" * 60)

        # Step 1: Send tweets to Slack
        self.send_tweets_to_slack()

        # Step 2: Poll for user selections and exclusions
        selections, excluded_tweets = self.poll_for_selections(
            timeout=poll_timeout,
            check_interval=check_interval
        )

        # Step 3: Save selected hooks and excluded tweets
        if selections or excluded_tweets:
            return self.save_selected_hooks(selections, excluded_tweets)
        else:
            print("⚠️  No selections or exclusions received. Output file not created.")
            return None


def main():
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: python slack_integration.py <input_json> [output_json]")
        print("\nExample:")
        print("  python slack_integration.py trending_tweets_20251109_164707_with_hooks.json")
        print("  python slack_integration.py input.json output_selected.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Validate input file
    if not os.path.exists(input_file):
        print(f"❌ Error: Input file not found: {input_file}")
        sys.exit(1)

    # Run integration
    try:
        integration = SlackIntegration(input_file, output_file)
        result = integration.process_json_file()

        if result:
            print("\n" + "=" * 60)
            print("✨ Hook selection complete!")
            print(f"📁 Output saved to: {result}")
            print("=" * 60)
        else:
            print("\n⚠️  No selections were made.")

    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
