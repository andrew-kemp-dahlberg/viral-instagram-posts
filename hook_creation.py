#!/usr/bin/env python3
"""
Generate Instagram reel text hooks in Parker Doyle's style using Claude AI.

This script takes a JSON file with tweet data (including descriptions from add_media_descriptions.py)
and uses Claude 4.5 Sonnet to generate 10 viral text hook options for each tweet in Parker Doyle's
signature casual, confident style.

Usage:
    python hook_creation.py input_described.json
    python hook_creation.py input_described.json output_with_hooks.json
"""

import json
import os
import sys
from datetime import datetime
from typing import Dict, List, Any
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


class HookGenerator:
    """Generates Instagram reel text hooks in Parker Doyle's style using Claude AI."""

    def __init__(self):
        """Initialize the hook generator with Claude API client."""
        api_key = os.getenv('ANTHROPIC_API_KEY')
        if not api_key:
            raise ValueError(
                "ANTHROPIC_API_KEY not found in environment variables. "
                "Please add it to your .env file."
            )
        self.client = Anthropic(api_key=api_key)
        self.model = "claude-sonnet-4-5-20250929"

    def generate_hooks(self, tweet_text: str, media_descriptions: List[str]) -> List[str]:
        """
        Generate 10 text hooks for a tweet using Claude AI.

        Args:
            tweet_text: The original tweet text
            media_descriptions: List of media descriptions from the tweet

        Returns:
            List of 10 hook options
        """
        # Construct the situation/context from tweet and media
        situation_parts = [f"Tweet: {tweet_text}"]
        if media_descriptions:
            situation_parts.append(f"Media context: {' | '.join(media_descriptions)}")
        situation = "\n".join(situation_parts)

        # Construct the prompt
        prompt = f"""Write text hooks in Parker Doyle's exact style for Instagram reels. Use this tone:

PARKER'S STYLE:
• Casual language: "bro," "dude," "man"
• Confident energy: Direct, no hesitation
• Emojis: 💀 and 😭 frequently
• Often starts with "Bro" for maximum relatability
• Uses "really" for emphasis ("Bro really did...")
• References specific situations that feel universal
• Creates "can't believe this happened" energy
• Keep hooks between 5-15 words for maximum impact

SITUATION:
{situation}

Give me 10 text hook options that would make people stop scrolling immediately.

VIRAL EXAMPLES:
"Bro just casually made the throw of the year 😭" (15.8M views)
"Never forget when the Tigers sacrificed a game just to get back at an umpire" (9.8M views)
"Opening Day baseball has already surpassed every other sport" (4.4M views)

However be sure not to do it if the related tweet does not make sense. Don't force relatability - go for socially calibrated 1st, relatability/funny second.

Format your response as a numbered list (1-10), one hook per line."""

        try:
            # Call Claude API
            message = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                messages=[
                    {"role": "user", "content": prompt}
                ]
            )

            # Extract hooks from response
            response_text = message.content[0].text
            hooks = self._parse_hooks(response_text)

            # Ensure we have exactly 10 hooks
            if len(hooks) < 10:
                print(f"  Warning: Only generated {len(hooks)} hooks (expected 10)")

            return hooks[:10]  # Return first 10 if more were generated

        except Exception as e:
            print(f"  Error generating hooks: {str(e)}")
            return []

    def _parse_hooks(self, response_text: str) -> List[str]:
        """
        Parse hooks from Claude's response.

        Args:
            response_text: The raw response from Claude

        Returns:
            List of hook strings
        """
        hooks = []
        lines = response_text.strip().split('\n')

        for line in lines:
            line = line.strip()
            # Skip empty lines
            if not line:
                continue

            # Remove numbering (handles formats like "1.", "1)", "1 -", etc.)
            for i in range(1, 11):
                prefixes = [f"{i}.", f"{i})", f"{i} -", f"{i}-"]
                for prefix in prefixes:
                    if line.startswith(prefix):
                        line = line[len(prefix):].strip()
                        break

            # Add the hook if it's not empty
            if line:
                hooks.append(line)

        return hooks

    def process_json_file(self, input_path: str, output_path: str = None) -> None:
        """
        Process a JSON file and add hooks to all tweets.
        Expects a flat list of tweet objects.

        Args:
            input_path: Path to input JSON file (must be a list of tweets)
            output_path: Path to output JSON file (optional)
        """
        # Load the JSON data
        print(f"Loading tweets from {input_path}...")
        with open(input_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(f"Expected a list of tweets, got {type(data).__name__}")

        total_tweets = len(data)
        print(f"Found {total_tweets} tweets")

        # Process each tweet
        processed_count = 0
        for i, tweet in enumerate(data, 1):
            topic = tweet.get('topic', 'unknown')
            print(f"  [{i}/{total_tweets}] Generating hooks (topic: {topic})...", end=" ")

            # Extract tweet text
            tweet_text = tweet.get('text', tweet.get('full_text', ''))

            # Extract media descriptions
            media_descriptions = []
            if 'media' in tweet and isinstance(tweet['media'], list):
                for media_item in tweet['media']:
                    if isinstance(media_item, dict) and 'description' in media_item:
                        media_descriptions.append(media_item['description'])

            # Generate hooks
            hooks = self.generate_hooks(tweet_text, media_descriptions)

            if hooks:
                tweet['hooks'] = hooks
                print(f"✓ Generated {len(hooks)} hooks")
                processed_count += 1
            else:
                print("✗ Failed to generate hooks")

        # Determine output path
        if output_path is None:
            base_name = input_path.replace('.json', '')
            if base_name.endswith('_described'):
                base_name = base_name[:-10]  # Remove '_described'
            output_path = f"{base_name}_with_hooks.json"

        # Save the updated data
        print(f"\nSaving results to {output_path}...")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\n✓ Complete! Successfully added hooks to {processed_count}/{total_tweets} tweets")
        print(f"Output saved to: {output_path}")


def main():
    """Main entry point for the script."""
    if len(sys.argv) < 2:
        print("Usage: python hook_creation.py <input_json_file> [output_json_file]")
        print("\nExample:")
        print("  python hook_creation.py trending_tweets_20251109_164707_described.json")
        print("  python hook_creation.py input.json output_with_hooks.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    # Check if input file exists
    if not os.path.exists(input_file):
        print(f"Error: Input file '{input_file}' not found")
        sys.exit(1)

    # Initialize generator and process file
    try:
        generator = HookGenerator()
        generator.process_json_file(input_file, output_file)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
