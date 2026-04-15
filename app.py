import os
import time
import threading
import requests
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "sylas_bot_token")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
PAGE_ID = "971519402721984"

groq_client = Groq(api_key=GROQ_API_KEY)

# Conversation history per user
conversations = {}

# Rate limiting
last_message_time = {}
RATE_LIMIT_SECONDS = 1.5

# Page posts cache
_page_posts_cache = []
_posts_last_fetched = 0
POSTS_CACHE_TTL = 3600  # refresh every 1 hour


def fetch_page_posts() -> list:
    """Fetch recent posts from Sylas Facebook page."""
    global _page_posts_cache, _posts_last_fetched

    now = time.time()
    if _page_posts_cache and (now - _posts_last_fetched) < POSTS_CACHE_TTL:
        return _page_posts_cache

    try:
        url = f"https://graph.facebook.com/v19.0/{PAGE_ID}/posts"
        params = {
            "fields": "message,created_time,story",
            "limit": 20,
            "access_token": PAGE_ACCESS_TOKEN,
        }
        r = requests.get(url, params=params, timeout=10)
        if r.status_code == 200:
            data = r.json().get("data", [])
            posts = []
            for post in data:
                msg = post.get("message") or post.get("story", "")
                if msg and len(msg.strip()) > 10:
                    posts.append(msg.strip())
            _page_posts_cache = posts
            _posts_last_fetched = now
            print(f"[Posts] Fetched {len(posts)} posts from Sylas page.")
        else:
            print(f"[Posts] Failed to fetch: {r.status_code} — {r.text}")
    except Exception as e:
        print(f"[Posts] Error fetching posts: {e}")

    return _page_posts_cache


def build_system_prompt() -> str:
    """Build system prompt with latest page posts as context."""
    posts = fetch_page_posts()

    posts_context = ""
    if posts:
        posts_text = "\n\n".join([f"- {p}" for p in posts[:10]])
        posts_context = f"""

SYLAS PAGE RECENT POSTS (use these to answer questions about page topics):
{posts_text}
"""

    return f"""You are the assistant of a Facebook educational page called "Sylas".

SYLAS PAGE IDENTITY:
Sylas is a purely educational Facebook page. It is NOT related to any game, character, or fandom.
The page teaches people about:
1. Artificial Intelligence (AI) — tools, art generation, prompt engineering
2. Technology and gadgets
3. Social media growth and strategy
4. AI photo and video generation
5. Starting and building a business from zero
6. Digital skills and online income
{posts_context}
RULES:
- Only answer questions related to the topics above (AI, tech, social media, business, digital skills).
- If someone asks about something unrelated (games, sports, politics, entertainment, etc.) — politely say: "I can only help with topics covered by the Sylas educational page: AI, technology, social media, and business."
- If someone asks "what is Sylas?" — answer: "Sylas is an educational Facebook page focused on AI, technology, social media, and business skills."
- NEVER mention games or fictional characters.
- NEVER use words like "fans" — the page has "followers" or "learners".
- Always respond in English only.
- Style: 2-3 sentences maximum. Be clear, helpful, and educational.
- Identity: You are the Sylas page assistant. Never claim to be ChatGPT, Claude, or any other named AI.
"""


ENGLISH_ERROR = "Sorry, I couldn't respond right now. Please try again in a moment. 🙏"
ENGLISH_WELCOME = "Hello! 👋 Welcome to Sylas — your source for AI, technology, and business education. How can I help you learn something today?"

RESET_KEYWORDS = ["/reset", "/start", "reset", "restart", "გადატვირთვა", "თავიდან"]
HELP_KEYWORDS = ["/help", "help", "დახმარება", "help me", "რა შეგიძლია"]


def get_ai_response(user_id: str, user_message: str) -> str:
    # Rate limiting
    now = time.time()
    if user_id in last_message_time:
        elapsed = now - last_message_time[user_id]
        if elapsed < RATE_LIMIT_SECONDS:
            time.sleep(RATE_LIMIT_SECONDS - elapsed)
    last_message_time[user_id] = time.time()

    # Special commands
    msg_lower = user_message.strip().lower()

    if any(kw in msg_lower for kw in RESET_KEYWORDS):
        conversations[user_id] = []
        return "Conversation reset! ✅ How can I help you learn today?"

    if any(kw in msg_lower for kw in HELP_KEYWORDS):
        return (
            "🤖 I'm the Sylas page assistant!\n\n"
            "I can help you with:\n"
            "• Artificial Intelligence & AI tools\n"
            "• Technology & gadgets\n"
            "• Social media growth\n"
            "• AI image & video generation\n"
            "• Starting a business online\n"
            "• Digital skills & online income\n\n"
            "Just ask your question!\n"
            "Reset conversation: /reset"
        )

    # Init conversation
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": user_message})

    # Keep last 10 messages only
    if len(conversations[user_id]) > 10:
        conversations[user_id] = conversations[user_id][-10:]

    try:
        system_prompt = build_system_prompt()
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": system_prompt}] + conversations[user_id],
            max_tokens=200,
            temperature=0.7,
        )
        reply = response.choices[0].message.content.strip()
        conversations[user_id].append({"role": "assistant", "content": reply})
        return reply

    except Exception as e:
        print(f"[Groq error] {e}")
        return ENGLISH_ERROR


def send_typing_on(recipient_id: str):
    url = "https://graph.facebook.com/v19.0/me/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "sender_action": "typing_on",
    }
    try:
        requests.post(url, json=payload, params={"access_token": PAGE_ACCESS_TOKEN}, timeout=5)
    except Exception:
        pass


def send_message(recipient_id: str, text: str):
    url = "https://graph.facebook.com/v19.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}

    chunks = [text[i:i+2000] for i in range(0, len(text), 2000)]

    for chunk in chunks:
        payload = {
            "recipient": {"id": recipient_id},
            "message": {"text": chunk},
            "messaging_type": "RESPONSE",
        }
        try:
            r = requests.post(url, json=payload, params=params, timeout=10)
            if r.status_code != 200:
                print(f"[Facebook send error] {r.status_code} — {r.text}")
        except Exception as e:
            print(f"[send_message exception] {e}")


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("[Webhook] Verified successfully.")
        return challenge, 200
    print(f"[Webhook] Verification failed. token={token}")
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    if not data or data.get("object") != "page":
        return "OK", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            sender_id = event.get("sender", {}).get("id")
            if not sender_id:
                continue

            # Ignore echo messages from page itself
            if event.get("message", {}).get("is_echo"):
                continue

            # Handle postback (Get Started button)
            postback = event.get("postback")
            if postback:
                payload = postback.get("payload", "")
                if payload in ("GET_STARTED", "RESTART"):
                    send_message(sender_id, ENGLISH_WELCOME)
                continue

            # Handle text messages
            msg = event.get("message", {})
            text = msg.get("text")
            if text:
                send_typing_on(sender_id)
                reply = get_ai_response(sender_id, text)
                send_message(sender_id, reply)

    return "OK", 200


@app.route("/", methods=["GET"])
def index():
    return "✅ Sylas Educational Bot is running!", 200


@app.route("/health", methods=["GET"])
def health():
    posts_count = len(_page_posts_cache)
    return jsonify({
        "status": "ok",
        "bot": "sylas-educational",
        "version": "3.0",
        "cached_posts": posts_count
    }), 200


@app.route("/refresh-posts", methods=["GET"])
def refresh_posts():
    """Manual endpoint to refresh page posts cache."""
    global _posts_last_fetched
    _posts_last_fetched = 0  # Force refresh
    posts = fetch_page_posts()
    return jsonify({"status": "ok", "posts_fetched": len(posts)}), 200


if __name__ == "__main__":
    # Pre-load page posts on startup
    print("[Startup] Loading Sylas page posts...")
    fetch_page_posts()
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
