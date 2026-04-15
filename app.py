import os
import time
import requests
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz

load_dotenv()

app = Flask(__name__)

# ---- Config ----
PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN", "")
VERIFY_TOKEN      = os.environ.get("VERIFY_TOKEN", "sylas_bot_token")
GROQ_API_KEY      = os.environ.get("GROQ_API_KEY", "")
PAGE_ID           = "971519402721984"

groq_client = Groq(api_key=GROQ_API_KEY)

# ---- Memory ----
conversations     = {}
last_msg_time     = {}

# ---- System prompt ----
SYSTEM_PROMPT = """You are the assistant of the Sylas Facebook educational page.

Sylas is an educational page about:
- Artificial Intelligence (AI tools, prompts, art generation)
- Technology and gadgets
- Social media growth
- Starting a business online
- Digital skills and online income

Rules:
- Only answer questions related to these topics.
- For off-topic questions say: "I can only help with AI, tech, social media, and business topics covered by Sylas page."
- If asked "what is Sylas?": "Sylas is an educational Facebook page about AI, technology, social media, and business."
- Never mention games or fictional characters.
- Always respond in English only.
- Keep answers to 2-3 sentences max.
- You are the Sylas assistant. Never say you are ChatGPT, Claude, or any other AI.
"""

# ---- Facebook helpers ----
def fb_post(endpoint, payload):
    """POST to Facebook Graph API."""
    url = f"https://graph.facebook.com/v19.0/{endpoint}"
    try:
        r = requests.post(
            url,
            json=payload,
            params={"access_token": PAGE_ACCESS_TOKEN},
            timeout=10
        )
        if r.status_code != 200:
            print(f"[FB ERROR] {endpoint}: {r.status_code} {r.text[:200]}")
        return r
    except Exception as e:
        print(f"[FB EXCEPTION] {endpoint}: {e}")
        return None


def send_typing(psid):
    fb_post("me/messages", {
        "recipient": {"id": psid},
        "sender_action": "typing_on"
    })


def send_text(psid, text):
    # Split into 2000-char chunks
    for chunk in [text[i:i+2000] for i in range(0, len(text), 2000)]:
        fb_post("me/messages", {
            "recipient": {"id": psid},
            "message": {"text": chunk},
            "messaging_type": "RESPONSE"
        })


# ---- AI response ----
def get_reply(psid, user_text):
    # Rate limit: 1.5s between messages
    now = time.time()
    if psid in last_msg_time and (now - last_msg_time[psid]) < 1.5:
        time.sleep(1.5 - (now - last_msg_time[psid]))
    last_msg_time[psid] = time.time()

    msg = user_text.strip().lower()

    if msg in ("/reset", "reset", "restart"):
        conversations.pop(psid, None)
        return "Conversation reset! How can I help you learn today?"

    if msg in ("/help", "help"):
        return (
            "I'm the Sylas page assistant!\n\n"
            "Topics I can help with:\n"
            "• AI & AI tools\n"
            "• Technology\n"
            "• Social media growth\n"
            "• Online business\n"
            "• Digital income\n\n"
            "Just ask your question!"
        )

    if psid not in conversations:
        conversations[psid] = []

    conversations[psid].append({"role": "user", "content": user_text})
    if len(conversations[psid]) > 10:
        conversations[psid] = conversations[psid][-10:]

    try:
        resp = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversations[psid],
            max_tokens=200,
            temperature=0.7
        )
        reply = resp.choices[0].message.content.strip()
        conversations[psid].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"[GROQ ERROR] {e}")
        return "Sorry, I couldn't respond right now. Please try again."


# ---- Webhook ----
@app.route("/webhook", methods=["GET"])
def webhook_verify():
    if (request.args.get("hub.mode") == "subscribe" and
            request.args.get("hub.verify_token") == VERIFY_TOKEN):
        print("[Webhook] Verified")
        return request.args.get("hub.challenge"), 200
    return "Forbidden", 403


@app.route("/webhook", methods=["POST"])
def webhook_receive():
    data = request.get_json(silent=True)
    if not data or data.get("object") != "page":
        return "OK", 200

    for entry in data.get("entry", []):
        for event in entry.get("messaging", []):
            psid = event.get("sender", {}).get("id")
            if not psid:
                continue

            # Skip echo
            if event.get("message", {}).get("is_echo"):
                continue

            # Get Started / postback
            postback = event.get("postback")
            if postback:
                if postback.get("payload") in ("GET_STARTED", "RESTART"):
                    send_text(psid, "Hello! I'm the Sylas assistant. Ask me about AI, tech, social media, or business!")
                continue

            # Text message
            text = event.get("message", {}).get("text")
            if text:
                print(f"[MSG] from {psid}: {text[:50]}")
                send_typing(psid)
                reply = get_reply(psid, text)
                print(f"[REPLY] to {psid}: {reply[:50]}")
                send_text(psid, reply)

    return "OK", 200


# ---- Utility routes ----
@app.route("/", methods=["GET"])
def index():
    return "Sylas Bot v4.0 running!", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "version": "4.0", "page": PAGE_ID}), 200


@app.route("/debug", methods=["GET"])
def debug():
    try:
        r = requests.get("https://graph.facebook.com/v19.0/me",
                         params={"access_token": PAGE_ACCESS_TOKEN}, timeout=5)
        identity = r.json()
    except Exception as e:
        identity = {"error": str(e)}
    return jsonify({
        "token_ok": identity.get("id") == PAGE_ID,
        "page_name": identity.get("name"),
        "token_prefix": PAGE_ACCESS_TOKEN[:25] + "..." if PAGE_ACCESS_TOKEN else "MISSING",
        "groq_key_set": bool(GROQ_API_KEY)
    }), 200


@app.route("/test-send/<psid>", methods=["GET"])
def test_send(psid):
    send_text(psid, "Test message from Sylas bot! If you see this, the bot is working.")
    return jsonify({"sent_to": psid}), 200


@app.route("/post-now", methods=["GET"])
def post_now():
    """Manually trigger an auto-post (for testing)."""
    from auto_poster import run_auto_post
    result = run_auto_post()
    return jsonify(result), 200


# ── Auto-Poster Scheduler ─────────────────────────────────────────
def start_scheduler():
    from auto_poster import run_auto_post
    georgia = pytz.timezone("Asia/Tbilisi")
    sched = BackgroundScheduler(timezone=georgia)
    # Post at 12:00, 15:00, 18:00 Georgia time
    sched.add_job(run_auto_post, CronTrigger(hour=12, minute=0, timezone=georgia))
    sched.add_job(run_auto_post, CronTrigger(hour=15, minute=0, timezone=georgia))
    sched.add_job(run_auto_post, CronTrigger(hour=18, minute=0, timezone=georgia))
    sched.start()
    print("[Scheduler] Auto-poster started: 12:00, 15:00, 18:00 Georgia time")

start_scheduler()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
