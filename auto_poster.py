"""
Sylas Auto-Poster v5.0 — Professional Card Edition
Posts 3x/day with viral content + branded Pillow-generated images
"""

import os, io, re, random, textwrap
import requests
import feedparser
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

PAGE_ID      = "971519402721984"
PAGE_TOKEN   = os.environ.get("PAGE_ACCESS_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

groq_client = Groq(api_key=GROQ_API_KEY)

# Font file stored next to this script
_DIR       = os.path.dirname(os.path.abspath(__file__))
FONT_PATH  = os.path.join(_DIR, "RobotoBold.ttf")
FONT_URL   = "https://github.com/googlefonts/roboto/raw/main/fonts/ttf/Roboto-Bold.ttf"
FONT_REG_PATH = os.path.join(_DIR, "RobotoRegular.ttf")
FONT_REG_URL  = "https://github.com/googlefonts/roboto/raw/main/fonts/ttf/Roboto-Regular.ttf"

# ── RSS feeds ─────────────────────────────────────────────────────
RSS_FEEDS = [
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://feeds.feedburner.com/venturebeat/SZYF",
    "https://hnrss.org/frontpage",
    "https://www.wired.com/feed/rss",
]

# ── Post formats ──────────────────────────────────────────────────
POST_FORMATS = ["listicle", "howto", "news", "tool", "myth", "stat"]

# ── Fallback topics ───────────────────────────────────────────────
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

# ── Per-format prompts ────────────────────────────────────────────
FORMAT_PROMPTS = {
    "listicle": """Write a high-quality Facebook post in a LISTICLE format.

Topic: {topic}

Structure:
- Attention-grabbing headline starting with a number (e.g. "5 AI Tools...")
- Short 1-sentence hook explaining why this matters
- Numbered list: 5 specific, actionable, surprising items (not generic)
- Each item: bold title + 1 sentence explanation
- Closing question to drive comments
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Be SPECIFIC (real tool names, real numbers). No fluff. Max 350 words. English only.
IMPORTANT: First line must be the headline only — no emoji clutter, make it punchy.""",

    "howto": """Write a high-quality Facebook post as a HOW-TO GUIDE.

Topic: {topic}

Structure:
- Headline starting with "How to..." that promises a clear result
- 1-sentence hook (pain point or opportunity)
- Step-by-step: 4 clear numbered steps, each with a bold step title + 1 sentence
- 1 pro tip at the end
- Question CTA for comments
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Steps must be concrete. Use real tools/examples. Max 350 words. English only.
IMPORTANT: First line must be the headline only — make it a strong promise.""",

    "news": """Write a high-quality Facebook post breaking down RECENT NEWS.

Topic/News: {topic}

Structure:
- Punchy headline summarizing the big news in 1 line (no emojis in headline)
- What happened (2 sentences, simple and clear)
- Why it matters to regular people / business owners (2-3 sentences)
- What you should do about it (1-2 practical sentences)
- Opinion question to drive engagement
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Make complex news simple. Focus on impact. Max 300 words. English only.
IMPORTANT: First line must be the headline only.""",

    "tool": """Write a high-quality Facebook post spotlighting an AI TOOL.

Topic: {topic}

Structure:
- Headline: "This AI Tool [does something impressive]" — bold, specific
- What the tool does (1-2 sentences)
- 3 best use cases with specific real-world examples
- Pricing: free or paid?
- Who should use it?
- Question CTA
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Be specific. Give real examples. Max 300 words. English only.
IMPORTANT: First line must be the headline only.""",

    "myth": """Write a high-quality Facebook post busting a MYTH about AI or tech.

Topic: {topic}

Structure:
- First line: "MYTH: [common misconception]"
- Second line: "REALITY: [surprising truth]"
- Why the myth exists (1 sentence)
- 3 specific facts that prove the reality (with numbers/examples)
- What this means for the reader practically
- Opinion question to spark debate
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Pick real misconceptions. Be bold. Max 300 words. English only.""",

    "stat": """Write a high-quality Facebook post built around a SURPRISING STATISTIC.

Topic: {topic}

Structure:
- First line: 1 shocking statistic as the headline (e.g. "75% of marketers now use AI daily")
- What this stat means in plain English (2 sentences)
- 2-3 more supporting facts or trends
- What action the reader should take
- Question to drive comments
- "Follow Sylas for daily AI & tech insights!"
- 5 hashtags

Rules: Statistics must feel real. Be specific. Max 300 words. English only.
IMPORTANT: First line is the stat/headline — make it shocking and specific.""",
}

# ── Card themes per format ────────────────────────────────────────
CARD_THEMES = {
    "listicle": {
        "bg1": (10, 18, 45),   "bg2": (22, 48, 110),
        "accent": (96, 165, 250), "label": "TOP LIST",
        "text_color": (255, 255, 255),
    },
    "howto": {
        "bg1": (5, 55, 45),    "bg2": (8, 95, 72),
        "accent": (52, 211, 153), "label": "HOW TO",
        "text_color": (255, 255, 255),
    },
    "news": {
        "bg1": (65, 8, 8),     "bg2": (120, 28, 28),
        "accent": (248, 113, 113), "label": "AI NEWS",
        "text_color": (255, 255, 255),
    },
    "tool": {
        "bg1": (38, 8, 88),    "bg2": (65, 28, 138),
        "accent": (192, 132, 252), "label": "AI TOOL",
        "text_color": (255, 255, 255),
    },
    "myth": {
        "bg1": (18, 18, 18),   "bg2": (38, 38, 38),
        "accent": (250, 204, 21), "label": "MYTH vs FACT",
        "text_color": (255, 255, 255),
    },
    "stat": {
        "bg1": (8, 55, 95),    "bg2": (15, 95, 130),
        "accent": (103, 232, 249), "label": "STATISTICS",
        "text_color": (255, 255, 255),
    },
}


# ── Font management ───────────────────────────────────────────────
def _download_font(url: str, path: str) -> bool:
    if os.path.exists(path):
        return True
    try:
        print(f"[Card] Downloading font from {url[:60]}...")
        r = requests.get(url, timeout=25)
        if r.status_code == 200 and len(r.content) > 50_000:
            with open(path, "wb") as f:
                f.write(r.content)
            print(f"[Card] Font saved: {path} ({len(r.content)//1024}KB)")
            return True
    except Exception as e:
        print(f"[Card] Font download failed: {e}")
    return False


def _get_font_path() -> str | None:
    """Return a valid TTF font path, trying Roboto first then system fonts."""
    if _download_font(FONT_URL, FONT_PATH):
        return FONT_PATH
    # System font fallbacks
    for fp in [
        "C:/Windows/Fonts/arialbd.ttf",
        "C:/Windows/Fonts/verdanab.ttf",
        "C:/Windows/Fonts/calibrib.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
    ]:
        if os.path.exists(fp):
            return fp
    return None


def _get_reg_font_path() -> str | None:
    """Return a valid regular (non-bold) TTF path."""
    if _download_font(FONT_REG_URL, FONT_REG_PATH):
        return FONT_REG_PATH
    for fp in [
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/verdana.ttf",
        "C:/Windows/Fonts/calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]:
        if os.path.exists(fp):
            return fp
    return None


# ── Card image generator ──────────────────────────────────────────
def create_card_image(post_text: str, fmt: str) -> bytes | None:
    """
    Generate a 1200x630 branded Facebook post image using Pillow.
    Layout:
      - Gradient background (format-specific dark theme)
      - Left accent stripe
      - Format badge (TOP LIST / HOW TO / AI NEWS ...)
      - Large headline text (extracted from post first line)
      - Accent divider
      - Subtitle (second meaningful line)
      - Bottom bar: SYLAS brand + tagline
    """
    try:
        from PIL import Image, ImageDraw, ImageFont

        W, H = 1200, 630
        theme = CARD_THEMES.get(fmt, CARD_THEMES["listicle"])

        # ── Background gradient ──
        img  = Image.new("RGB", (W, H))
        draw = ImageDraw.Draw(img)
        bg1, bg2 = theme["bg1"], theme["bg2"]
        for y in range(H):
            t = y / H
            r = int(bg1[0] + (bg2[0] - bg1[0]) * t)
            g = int(bg1[1] + (bg2[1] - bg1[1]) * t)
            b = int(bg1[2] + (bg2[2] - bg1[2]) * t)
            draw.line([(0, y), (W, y)], fill=(r, g, b))

        # ── Subtle diagonal decorative lines ──
        ac = theme["accent"]
        dim = (max(0, ac[0] - 170), max(0, ac[1] - 170), max(0, ac[2] - 170))
        for i in range(-H, W + H, 100):
            draw.line([(i, 0), (i + H, H)], fill=dim, width=1)

        # ── Left accent stripe ──
        draw.rectangle([0, 0, 10, H], fill=ac)

        # ── Load fonts ──
        bold_path = _get_font_path()
        reg_path  = _get_reg_font_path() or bold_path

        def mkfont(path, size):
            if path and os.path.exists(path):
                return ImageFont.truetype(path, size)
            return ImageFont.load_default()

        f_headline = mkfont(bold_path, 66)
        f_subtitle = mkfont(reg_path,  34)
        f_badge    = mkfont(bold_path, 24)
        f_brand    = mkfont(bold_path, 42)
        f_tagline  = mkfont(reg_path,  24)

        # ── Extract headline & subtitle from post text ──
        raw_lines = [l.strip() for l in post_text.split("\n") if l.strip()]

        def clean(text):
            """Strip emojis and non-ASCII, keep printable ASCII."""
            return re.sub(r'[^\x20-\x7E]+', '', text).strip()

        headline = ""
        for ln in raw_lines[:3]:
            c = clean(ln)
            # Skip lines that are obviously not a headline
            if len(c) >= 10 and not c.startswith("#"):
                headline = c
                break
        if not headline:
            headline = "AI & Tech Insights"

        # Subtitle: next meaningful line after headline
        subtitle = ""
        found_hl = False
        for ln in raw_lines:
            c = clean(ln)
            if not found_hl:
                if c == headline:
                    found_hl = True
                continue
            if len(c) >= 15 and not c.startswith("#") and not c.startswith("Follow"):
                subtitle = c[:110]
                break

        # ── Measure helper ──
        def text_h(txt, font):
            try:
                bb = draw.textbbox((0, 0), txt, font=font)
                return bb[3] - bb[1]
            except Exception:
                return 30

        # ── Format badge ──
        badge_label = theme["label"]
        try:
            bb = draw.textbbox((0, 0), badge_label, font=f_badge)
            bw = bb[2] - bb[0] + 36
            bh = bb[3] - bb[1] + 16
        except Exception:
            bw, bh = len(badge_label) * 16 + 36, 40

        bx, by = 40, 44
        draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=7, fill=ac)
        draw.text((bx + 18, by + 8), badge_label, font=f_badge, fill=(10, 10, 10))

        # ── Headline (wrapped, max 3 lines) ──
        hl_wrapped = textwrap.wrap(headline, width=26)[:3]
        hl_x, hl_y = 42, by + bh + 32

        for line in hl_wrapped:
            draw.text((hl_x, hl_y), line, font=f_headline, fill=(255, 255, 255))
            hl_y += text_h(line, f_headline) + 10

        # ── Accent divider ──
        div_y = hl_y + 16
        draw.rectangle([42, div_y, 340, div_y + 5], fill=ac)

        # ── Subtitle ──
        if subtitle:
            sub_wrapped = textwrap.wrap(subtitle, width=52)[:2]
            sub_y = div_y + 24
            for sl in sub_wrapped:
                draw.text((42, sub_y), sl, font=f_subtitle, fill=(200, 215, 225))
                sub_y += text_h(sl, f_subtitle) + 8

        # ── Bottom bar ──
        bar_y = H - 78
        draw.rectangle([0, bar_y, W, H], fill=(8, 8, 15))

        # Thin accent line on top of bar
        draw.rectangle([0, bar_y, W, bar_y + 3], fill=ac)

        # Brand name
        draw.text((42, bar_y + 16), "SYLAS", font=f_brand, fill=ac)

        # Tagline
        draw.text((180, bar_y + 22), "Daily AI & Tech Insights", font=f_tagline, fill=(160, 175, 190))

        # Handle on right
        handle = "facebook.com/SylasPage"
        try:
            hbb = draw.textbbox((0, 0), handle, font=f_tagline)
            hw  = hbb[2] - hbb[0]
        except Exception:
            hw = len(handle) * 12
        draw.text((W - hw - 42, bar_y + 22), handle, font=f_tagline, fill=(90, 105, 120))

        # ── Save ──
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=95, optimize=True)
        size_kb = buf.tell() // 1024
        print(f"[Card] Image generated: {size_kb}KB")
        return buf.getvalue()

    except Exception as e:
        import traceback
        print(f"[Card] Error: {e}")
        traceback.print_exc()
        return None


# ── News fetching ─────────────────────────────────────────────────
def fetch_latest_news() -> list[str]:
    headlines = []
    for feed_url in RSS_FEEDS:
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:4]:
                title   = entry.get("title", "").strip()
                summary = re.sub(r'<[^>]+>', '', entry.get("summary", ""))[:150].strip()
                if title and len(title) > 20:
                    headlines.append(f"{title}. {summary}" if summary else title)
        except Exception as e:
            print(f"[RSS] {feed_url}: {e}")
    random.shuffle(headlines)
    return headlines[:10]


def pick_topic_and_format() -> tuple[str, str]:
    news  = fetch_latest_news()
    topic = random.choice(news) if news else random.choice(FALLBACK_TOPICS)
    fmt   = random.choice(POST_FORMATS)
    print(f"[AutoPost] Format={fmt} | Topic={topic[:70]}...")
    return topic, fmt


# ── Content generation ────────────────────────────────────────────
def generate_post(topic: str, fmt: str) -> str:
    prompt = FORMAT_PROMPTS.get(fmt, FORMAT_PROMPTS["listicle"]).format(topic=topic)
    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a world-class social media content writer specializing in AI and tech. "
                        "You write viral, engaging Facebook posts with high reach and engagement. "
                        "Your posts are specific, practical, and make people feel smarter. "
                        "You NEVER write generic fluff. Every sentence earns its place. "
                        "CRITICAL: The VERY FIRST LINE of your response must be the post headline only — "
                        "no preamble, no 'Here is', no meta-commentary."
                    )
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=650,
            temperature=0.80
        )
        text = resp.choices[0].message.content.strip()
        text = re.sub(
            r'^(Here is|Here\'s|Sure|Absolutely|Of course|Below is)[^:\n]*[:\n]+\n*',
            '', text, flags=re.IGNORECASE
        )
        return text
    except Exception as e:
        print(f"[AutoPost] Groq error: {e}")
        return (
            "AI is changing everything fast.\n\n"
            "Follow Sylas to stay ahead of the curve every single day.\n\n"
            "Follow Sylas for daily AI & tech insights!\n\n"
            "#AI #Technology #Business #DigitalSkills #Sylas"
        )


# ── Facebook posting ──────────────────────────────────────────────
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


# ── Main entry ────────────────────────────────────────────────────
def run_auto_post() -> dict:
    """Called by scheduler 3x/day — or via /post-now endpoint."""
    print("\n" + "=" * 55)
    print("[AutoPost] >> Scheduled post starting...")

    global PAGE_TOKEN
    PAGE_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", PAGE_TOKEN)

    try:
        topic, fmt = pick_topic_and_format()
        message    = generate_post(topic, fmt)
        print(f"[AutoPost] Post ready ({len(message)} chars)")

        image  = create_card_image(message, fmt)
        result = post_to_facebook(message, image)

        if result.get("id") or result.get("post_id"):
            print(f"[AutoPost] SUCCESS -- {result}")
        else:
            print(f"[AutoPost] FAILED -- {result}")

        return result

    except Exception as e:
        import traceback
        print(f"[AutoPost] Exception: {e}")
        traceback.print_exc()
        return {"error": str(e)}


if __name__ == "__main__":
    result = run_auto_post()
    print("Result:", result)
