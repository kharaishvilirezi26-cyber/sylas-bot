"""
Sylas Auto-Poster
Posts 3x/day to the Sylas Facebook page:
- Fetches latest AI/tech news from RSS feeds
- Generates engaging post content with Groq
- Creates an image with Pollinations AI
- Posts to Facebook page
"""

import os, time, random, urllib.parse, io, textwrap, json
import requests
import feedparser
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

PAGE_ID        = "971519402721984"
PAGE_TOKEN     = os.environ.get("PAGE_ACCESS_TOKEN", "")
GROQ_API_KEY   = os.environ.get("GROQ_API_KEY", "")

groq_client = Groq(api_key=GROQ_API_KEY)

# ── RSS News Sources ──────────────────────────────────────────────
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://rss.beehiiv.com/feeds/theneurips.rss",
]

FALLBACK_TOPICS = [
    "The top AI tools transforming productivity in 2026",
    "How to grow your Instagram to 10,000 followers using AI",
    "5 ways to make money online with AI tools",
    "Best AI image generators compared: which one to use?",
    "How small businesses are using AI to compete with big brands",
    "The future of AI video generation — what's possible now",
    "Top 5 free AI tools everyone should know about",
    "How to write better prompts for ChatGPT and other AI",
    "AI tools that will replace these jobs (and which ones it won't)",
    "How to start a faceless YouTube channel using AI in 2026",
]


def fetch_latest_news() -> list[str]:
    """Fetch latest headlines from RSS feeds."""
    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:3]:
                title = entry.get("title", "")
                summary = entry.get("summary", "")[:200]
                if title:
                    headlines.append(f"{title}. {summary}")
        except Exception as e:
            print(f"[RSS] Error fetching {feed_url}: {e}")
    return headlines[:8] if headlines else []


def pick_topic() -> str:
    """Pick a topic from news or fallback list."""
    news = fetch_latest_news()
    if news:
        topic = random.choice(news)
        print(f"[AutoPost] Topic from news: {topic[:80]}...")
    else:
        topic = random.choice(FALLBACK_TOPICS)
        print(f"[AutoPost] Fallback topic: {topic}")
    return topic


def generate_post(topic: str) -> str:
    """Generate Facebook post content with Groq."""
    prompt = f"""You are writing a Facebook post for "Sylas" — a Georgian educational page about AI, technology, social media growth, and online business.

Topic to write about: {topic}

Requirements:
- Start with a bold attention-grabbing headline (use emoji)
- Write 2-3 short, punchy paragraphs
- Be educational, practical, and inspiring
- End with: "Follow Sylas for daily tips! 🚀"
- Add 4-5 relevant hashtags at the very end
- Write in English
- Maximum 300 words total
- Make it feel fresh and relevant to 2026

Only write the post text. No extra commentary."""

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=500,
            temperature=0.85
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        print(f"[AutoPost] Groq error: {e}")
        return f"🤖 Exciting things happening in AI and tech! Stay tuned to Sylas for the latest updates.\n\nFollow Sylas for daily tips! 🚀\n\n#AI #Technology #Business #SocialMedia #Sylas"


def generate_image(topic: str) -> bytes | None:
    """Generate image using Pollinations AI (free, no API key)."""
    # Build a clean image prompt
    image_prompt = (
        f"Modern professional infographic social media post about: {topic[:80]}. "
        "Style: clean minimalist design, vibrant blue and purple gradient background, "
        "white text, icons, tech aesthetic, 2026 style, high quality"
    )
    encoded = urllib.parse.quote(image_prompt)

    # Try multiple seeds for variety
    seed = random.randint(1, 9999)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1200&height=630&seed={seed}&model=flux&nologo=true&enhance=true"
    )

    print(f"[AutoPost] Generating image...")
    try:
        r = requests.get(url, timeout=90)
        if r.status_code == 200 and len(r.content) > 5000:
            print(f"[AutoPost] Image ready ({len(r.content)//1024}KB)")
            return r.content
        print(f"[AutoPost] Image failed: status={r.status_code} size={len(r.content)}")
    except Exception as e:
        print(f"[AutoPost] Image error: {e}")
    return None


def post_with_image(message: str, image_bytes: bytes) -> dict:
    """Post photo + caption to Facebook page."""
    url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
    files = {"source": ("post.jpg", image_bytes, "image/jpeg")}
    data  = {"message": message, "access_token": PAGE_TOKEN}
    r = requests.post(url, files=files, data=data, timeout=60)
    return r.json()


def post_text_only(message: str) -> dict:
    """Post text-only to Facebook page (fallback)."""
    url  = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
    data = {"message": message, "access_token": PAGE_TOKEN}
    r = requests.post(url, json=data, timeout=30)
    return r.json()


def run_auto_post():
    """Main entry point — called by scheduler 3x/day."""
    print("\n" + "="*50)
    print("[AutoPost] Starting scheduled post...")

    # Reload token in case it was updated
    global PAGE_TOKEN
    PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", PAGE_TOKEN)

    try:
        # 1. Pick topic
        topic   = pick_topic()

        # 2. Generate post text
        message = generate_post(topic)
        print(f"[AutoPost] Post ({len(message)} chars):\n{message[:120]}...")

        # 3. Generate image
        image = generate_image(topic)

        # 4. Post to Facebook
        if image:
            result = post_with_image(message, image)
        else:
            print("[AutoPost] No image — posting text only")
            result = post_text_only(message)

        if result.get("id") or result.get("post_id"):
            print(f"[AutoPost] ✅ Posted! Result: {result}")
        else:
            print(f"[AutoPost] ❌ Post failed: {result}")

        return result

    except Exception as e:
        print(f"[AutoPost] ❌ Exception: {e}")
        import traceback; traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    # Test run
    print("Running test post...")
    result = run_auto_post()
    print("Result:", result)
