#!/usr/bin/env python3
"""
Test script to verify LLM API keys are working correctly.
Run this after adding your API keys to .env file.
"""

import asyncio
import os

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


async def test_openai_key():
    """Test OpenAI API key."""
    try:
        import openai

        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key or openai_key == "your-openai-api-key-here":
            print("❌ OPENAI_API_KEY not set or using placeholder value")
            return False

        # Test API call
        client = openai.OpenAI(api_key=openai_key)
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": "Say 'API key works!'"}],
            max_tokens=10,
        )

        print("✅ OpenAI API key working!")
        print(f"   Response: {response.choices[0].message.content}")
        return True

    except ImportError:
        print("⚠️  OpenAI library not installed. Run: pip install openai")
        return False
    except Exception as e:
        print(f"❌ OpenAI API key failed: {e}")
        return False


async def test_anthropic_key():
    """Test Anthropic API key."""
    try:
        import anthropic

        anthropic_key = os.getenv("ANTHROPIC_API_KEY")
        if not anthropic_key or anthropic_key == "your-anthropic-api-key-here":
            print("❌ ANTHROPIC_API_KEY not set or using placeholder value")
            return False

        # Test API call
        client = anthropic.Anthropic(api_key=anthropic_key)
        response = client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=10,
            messages=[{"role": "user", "content": "Say 'API key works!'"}],
        )

        print("✅ Anthropic API key working!")
        print(f"   Response: {response.content[0].text}")
        return True

    except ImportError:
        print("⚠️  Anthropic library not installed. Run: pip install anthropic")
        return False
    except Exception as e:
        print(f"❌ Anthropic API key failed: {e}")
        return False


async def main():
    """Main test function."""
    print("🔑 Testing LLM API Keys...")
    print("=" * 40)

    openai_ok = await test_openai_key()
    anthropic_ok = await test_anthropic_key()

    print("=" * 40)
    if openai_ok and anthropic_ok:
        print("🎉 All API keys working! WebAgent Planner is ready.")
    elif openai_ok or anthropic_ok:
        print("⚠️  One API key working. WebAgent will use available provider.")
    else:
        print("❌ No API keys working. WebAgent Planner won't function.")
        print("\nPlease:")
        print(
            "1. Get API keys from https://platform.openai.com and https://console.anthropic.com"
        )
        print("2. Add them to .env file")
        print("3. Run this test again")


if __name__ == "__main__":
    asyncio.run(main())
