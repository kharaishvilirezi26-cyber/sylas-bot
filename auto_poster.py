"""
Sylas Auto-Poster — High Quality Edition
Posts 3x/day with viral-worthy content + professional visuals
"""

import os, random, urllib.parse, re
import requests
import feedparser
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

PAGE_ID      = "971519402721984"
PAGE_TOKEN   = os.environ.get("PAGE_ACCESS_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

groq_client = Groq(api_key=GROQ_API_KEY)

# ── RSS feeds (AI / Tech / Business) ─────────────────────────────
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://hnrss.org/frontpage",          # Hacker News top stories
    "https://www.wired.com/feed/rss",
]

# ── Post formats — one chosen at random each time ────────────────
POST_FORMATS = [
    "listicle",     # "5 things you didn't know about X"
    "howto",        # step-by-step guide
    "news",         # breaking news breakdown
    "tool",         # spotlight on an AI tool
    "myth",         # myth vs reality
    "stat",         # surprising statistics + insight
]

# ── Fallback topics if RSS fails ──────────────────────────────────
FALLBACK_TOPICS = [
    "ChatGPT vs Claude vs Gemini — which AI is best in 2026?",
    "How to grow from 0 to 10,000 followers using AI content",
    "Top 5 free AI tools that save you 10 hours a week",
    "How to make $1,000/month with a faceless AI YouTube channel",
    "AI image generation: Midjourney vs Stable Diffusion vs Flux",
    "The best AI tools for small business owners in 2026",
    "How to write viral social media posts using ChatGPT",
    "Passive income with AI: 7 realistic methods that actually work",
    "Google's new AI vs ChatGPT: what changed?",
    "How to automate your entire social media with AI (free tools)",
]

# ── Prompts by format ─────────────────────────────────────────────
FORMAT_PROMPTS = {
    "listicle": """Write a high-quality Facebook post in a LISTICLE format.

Topic: {topic}

Structure:
- 🔥 Attention-grabbing headline (make people stop scrolling)
- Short 1-sentence hook explaining why this matters
- Numbered list: 5 specific, actionable, surprising items (not generic)
- Each item: bold title + 1 sentence explanation
- Closing line with a question to drive comments
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Be SPECIFIC (real tool names, real numbers). No fluff. Max 350 words. English only.""",

    "howto": """Write a high-quality Facebook post as a HOW-TO GUIDE.

Topic: {topic}

Structure:
- 💡 Headline that promises a clear result (e.g. "How to do X in 10 minutes")
- 1-sentence hook (pain point or opportunity)
- Step-by-step: 4 clear steps, each with emoji + bold step title + 1 sentence
- Real tip or shortcut at the end
- Question CTA for comments
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Steps must be concrete and actionable. Use real tools/examples. Max 350 words. English only.""",

    "news": """Write a high-quality Facebook post breaking down RECENT NEWS.

Topic/News: {topic}

Structure:
- 🚨 or 📢 Headline summarizing the big news in 1 line
- What happened (2 sentences, simple and clear)
- Why it matters to regular people / business owners (2-3 sentences)
- What you should do about it (1-2 practical sentences)
- Opinion question to drive engagement
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Make complex news simple. Focus on impact. Max 300 words. English only.""",

    "tool": """Write a high-quality Facebook post spotlighting an AI TOOL.

Topic: {topic}

Structure:
- 🛠️ Headline: "This AI tool is [doing something impressive]"
- What the tool does (1-2 sentences, simple)
- 3 best use cases with specific examples
- Is it free or paid? (mention pricing if known)
- Who should use it?
- Question CTA
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Be specific. Give real examples. Max 300 words. English only.""",

    "myth": """Write a high-quality Facebook post busting a MYTH about AI or tech.

Topic: {topic}

Structure:
- ❌ Myth headline: "MYTH: [common misconception]"
- ✅ Truth headline: "REALITY: [surprising truth]"
- Explain why the myth exists (1 sentence)
- 3 specific facts that prove the reality (with numbers/examples)
- What this means for the reader practically
- Opinion question to spark debate
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Pick real misconceptions. Be bold. Max 300 words. English only.""",

    "stat": """Write a high-quality Facebook post built around a SURPRISING STATISTIC.

Topic: {topic}

Structure:
- 📊 Open with 1 shocking statistic related to the topic (make it specific and credible)
- What does this stat mean in plain English? (2 sentences)
- 2-3 more supporting facts or trends
- What action should the reader take based on this?
- Question to drive comments
- "Follow Sylas for daily AI & tech insights! 🚀"
- 5 hashtags

Rules: Statistics must feel real and sourced. Be specific. Max 300 words. English only.""",
}

# ── Image style templates ─────────────────────────────────────────
IMAGE_STYLES = [
    "sleek dark tech dashboard infographic, neon blue and purple accents, white sans-serif typography, geometric patterns, professional, 4K quality",
    "modern flat design infographic, coral and deep navy color scheme, clean icons, bold typography, social media optimized",
    "vibrant gradient background from electric blue to violet, 3D floating elements, glassmorphism cards, futuristic minimal",
    "professional business infographic, bold yellow and black, clean grid layout, data visualization style, high contrast",
    "editorial tech magazine cover style, deep teal and gold, large bold headline font, minimalist premium design",
]


def fetch_latest_news() -> list[str]:
    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]:
                title = entry.get("title", "").strip()
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", ""))[:150].strip()
                if title and len(title) > 20:
                    headlines.append(f"{title}. {summary}" if summary else title)
        except Exception as e:
            print(f"[RSS] {feed_url}: {e}")
    random.shuffle(headlines)
    return headlines[:10]


def pick_topic_and_format() -> tuple[str, str]:
    news = fetch_latest_news()
    topic = random.choice(news) if news else random.choice(FALLBACK_TOPICS)
    fmt   = random.choice(POST_FORMATS)
    print(f"[AutoPost] Format={fmt} | Topic={topic[:70]}...")
    return topic, fmt


def generate_post(topic: str, fmt: str) -> str:
    prompt_template = FORMAT_PROMPTS.get(fmt, FORMAT_PROMPTS["listicle"])
    prompt = prompt_template.format(topic=topic)

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class social media content writer. "
                        "You write viral, engaging Facebook posts that get high reach and engagement. "
                        "Your posts are specific, practical, and make people feel smarter after reading them. "
                        "You NEVER write generic fluff. Every sentence must earn its place."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=600,
            temperature=0.82
        )
        text = resp.choices[0].message.content.strip()
        # Remove any meta commentary the model might add
        text = re.sub(r'^(Here is|Here\'s|Sure|Absolutely|Of course)[^:]*:\n*', '', text, flags=re.IGNORECASE)
        return text
    except Exception as e:
        print(f"[AutoPost] Groq error: {e}")
        return (
            "🤖 AI is changing everything — and fast.\n\n"
            "Follow Sylas to stay ahead of the curve every day.\n\n"
            "Follow Sylas for daily AI & tech insights! 🚀\n\n"
            "#AI #Technology #Business #DigitalSkills #Sylas"
        )


def build_image_prompt(topic: str, fmt: str) -> str:
    style = random.choice(IMAGE_STYLES)
    topic_short = topic[:60]

    format_visual = {
        "listicle":  f"numbered list infographic about '{topic_short}'",
        "howto":     f"step-by-step guide visual about '{topic_short}'",
        "news":      f"breaking news graphic about '{topic_short}'",
        "tool":      f"product showcase graphic for AI tool related to '{topic_short}'",
        "myth":      f"myth vs reality comparison graphic about '{topic_short}'",
        "stat":      f"data visualization / statistics infographic about '{topic_short}'",
    }

    visual_desc = format_visual.get(fmt, f"infographic about '{topic_short}'")
    return f"Professional social media {visual_desc}, {style}, NO watermarks, NO text overlays, photorealistic quality"


def generate_image(topic: str, fmt: str) -> bytes | None:
    img_prompt = build_image_prompt(topic, fmt)
    encoded    = urllib.parse.quote(img_prompt)
    seed       = random.randint(100, 99999)
    url = (
        f"https://image.pollinations.ai/prompt/{encoded}"
        f"?width=1200&height=630&seed={seed}&model=flux-pro&nologo=true&enhance=true"
    )
    print(f"[AutoPost] Generating image (seed={seed})...")
    try:
        r = requests.get(url, timeout=120)
        if r.status_code == 200 and len(r.content) > 10_000:
            print(f"[AutoPost] Image OK — {len(r.content)//1024}KB")
            return r.content
        # Fallback to standard flux model
        url2 = url.replace("flux-pro", "flux")
        r2 = requests.get(url2, timeout=90)
        if r2.status_code == 200 and len(r2.content) > 10_000:
            print(f"[AutoPost] Image OK (fallback) — {len(r2.content)//1024}KB")
            return r2.content
    except Exception as e:
        print(f"[AutoPost] Image error: {e}")
    print("[AutoPost] Image generation failed — will post text only")
    return None


def post_to_facebook(message: str, image_bytes: bytes | None) -> dict:
    if image_bytes:
        url   = f"https://graph.facebook.com/v19.0/{PAGE_ID}/photos"
        files = {"source": ("post.jpg", image_bytes, "image/jpeg")}
        data  = {"message": message, "access_token": PAGE_TOKEN}
        r = requests.post(url, files=files, data=data, timeout=60)
    else:
        url  = f"https://graph.facebook.com/v19.0/{PAGE_ID}/feed"
        data = {"message": message, "access_token": PAGE_TOKEN}
        r = requests.post(url, json=data, timeout=30)
    return r.json()


def run_auto_post() -> dict:
    """Called by scheduler 3x/day — or via /post-now endpoint."""
    print("\n" + "=" * 55)
    print("[AutoPost] ▶ Scheduled post starting...")

    global PAGE_TOKEN
    PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", PAGE_TOKEN)

    try:
        topic, fmt  = pick_topic_and_format()
        message     = generate_post(topic, fmt)
        print(f"[AutoPost] Post ready ({len(message)} chars)")

        image       = generate_image(topic, fmt)
        result      = post_to_facebook(message, image)

        if result.get("id") or result.get("post_id"):
            print(f"[AutoPost] ✅ Success — {result}")
        else:
            print(f"[AutoPost] ❌ Failed — {result}")

        return result

    except Exception as e:
        import traceback
        print(f"[AutoPost] ❌ Exception: {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    result = run_auto_post()
    print("Result:", result)
