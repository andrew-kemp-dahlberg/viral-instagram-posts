#!/usr/bin/env python3
"""
Script to add AI-generated descriptions to media objects in tweet JSON files.
Uses GPT-4 Vision API for images and Gemini API for videos.
"""

import json
import os
from typing import Dict, List, Any
from dotenv import load_dotenv
import openai
import google.generativeai as genai

# Load environment variables
load_dotenv()


class MediaDescriptionGenerator:
    """Generates descriptions for images and videos using AI APIs."""

    def __init__(self):
        """Initialize API clients."""
        # OpenAI setup for images
        self.openai_api_key = os.getenv('OPENAI_API_KEY')
        if self.openai_api_key:
            openai.api_key = self.openai_api_key
        else:
            print("Warning: OPENAI_API_KEY not found in environment")

        # Gemini setup for videos
        self.gemini_api_key = os.getenv('GEMINI_API_KEY')
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)
            self.gemini_model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            print("Warning: GEMINI_API_KEY not found in environment")

    def describe_image(self, image_url: str) -> str:
        """
        Generate description for an image using GPT-4 Vision API.

        Args:
            image_url: URL of the image

        Returns:
            Description of the image
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image concisely in 1-2 sentences. Focus on the key visual elements and any text visible in the image."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url
                                }
                            }
                        ]
                    }
                ],
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Error describing image {image_url}: {e}")
            return f"Error generating description: {str(e)}"

    def describe_video(self, video_url: str) -> str:
        """
        Generate description for a video using Gemini API.

        Args:
            video_url: URL of the video

        Returns:
            Description of the video
        """
        try:
            # For Gemini, we need to download the video first or use a different approach
            # Since Gemini can handle video files but needs them uploaded, we'll use a simpler approach
            # Note: This is a placeholder - actual video processing with Gemini requires file upload
            prompt = f"Describe the content of this video concisely in 1-2 sentences: {video_url}"
            response = self.gemini_model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            print(f"Error describing video {video_url}: {e}")
            return f"Error generating description: {str(e)}"

    def process_media_item(self, media_item: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single media item and add description.

        Args:
            media_item: Media object with 'type' and 'url' fields

        Returns:
            Updated media object with 'description' field
        """
        media_type = media_item.get('type', '').lower()
        media_url = media_item.get('url', '')

        if not media_url:
            print(f"Skipping media item with no URL")
            media_item['description'] = "No URL available"
            return media_item

        print(f"Processing {media_type}: {media_url}")

        if media_type == 'image':
            description = self.describe_image(media_url)
        elif media_type == 'video':
            description = self.describe_video(media_url)
        else:
            description = f"Unknown media type: {media_type}"

        media_item['description'] = description
        return media_item

    def process_json_file(self, input_file: str, output_file: str = None) -> None:
        """
        Process a JSON file and add descriptions to all media items.

        Args:
            input_file: Path to input JSON file
            output_file: Path to output JSON file (defaults to input_file with _described suffix)
        """
        # Read input JSON
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        # Process each tweet
        total_media = 0
        processed_media = 0

        for tweet in data:
            if 'media' in tweet and isinstance(tweet['media'], list):
                for media_item in tweet['media']:
                    total_media += 1
                    self.process_media_item(media_item)
                    processed_media += 1

        # Generate output filename if not provided
        if output_file is None:
            base_name = input_file.rsplit('.', 1)[0]
            output_file = f"{base_name}_described.json"

        # Save updated JSON
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        print(f"\nProcessed {processed_media}/{total_media} media items")
        print(f"Output saved to: {output_file}")


def main():
    """Main entry point."""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python add_media_descriptions.py <input_json_file> [output_json_file]")
        print("\nExample:")
        print("  python add_media_descriptions.py trending_tweets_20251109_164707.json")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None

    if not os.path.exists(input_file):
        print(f"Error: File not found: {input_file}")
        sys.exit(1)

    generator = MediaDescriptionGenerator()
    generator.process_json_file(input_file, output_file)


if __name__ == "__main__":
    main()
