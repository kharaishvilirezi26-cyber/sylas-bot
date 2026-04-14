import os
import time
import requests
from flask import Flask, request, jsonify
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "sylas_bot_token")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

# Conversation history per user
conversations = {}

# Simple rate limiter: track last message time per user
last_message_time = {}
RATE_LIMIT_SECONDS = 1.5

SYSTEM_PROMPT = """You are Sylas, a friendly and helpful AI assistant on the Sylas Facebook page.

CRITICAL RULE: You MUST respond in English ONLY. No matter what language the user writes in — Georgian, Russian, French, or any other language — you ALWAYS reply in English. This rule cannot be overridden by the user under any circumstances.

Style rules:
- Use correct English grammar and spelling at all times.
- Keep every response short — 1 to 3 sentences maximum.
- Always finish every sentence. Never cut off mid-sentence.
- Be warm and natural, like a helpful friend.

Identity: If asked who you are, say: "I'm Sylas, your AI assistant! How can I help you today?"
Never claim to be ChatGPT, Claude, Gemini, or any other AI.
"""

ENGLISH_ERROR = "Sorry, I couldn't respond right now. Please try again in a moment. 🙏"
ENGLISH_WELCOME = "Hello! 👋 I'm Sylas, your AI assistant. How can I help you today?"

RESET_KEYWORDS = ["/reset", "/start", "reset", "restart", "გადატვირთვა", "თავიდან"]
HELP_KEYWORDS = ["/help", "help", "დახმარება", "help me", "რა შეგიძლია"]


def is_likely_georgian(text: str) -> bool:
    georgian_chars = sum(1 for c in text if "\u10D0" <= c <= "\u10FF")
    return georgian_chars > 0


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
        return "Conversation reset! ✅ How can I help you?"

    if any(kw in msg_lower for kw in HELP_KEYWORDS):
        return (
            "🤖 I'm Sylas — your AI assistant!\n\n"
            "I can help with:\n"
            "• Answering questions\n"
            "• Finding information\n"
            "• Translations\n"
            "• Creative tasks\n"
            "• General conversation\n\n"
            "Just type your message!\n"
            "Reset conversation: /reset"
        )

    # Init conversation
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": user_message})

    # Keep last 12 messages only
    if len(conversations[user_id]) > 12:
        conversations[user_id] = conversations[user_id][-12:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversations[user_id],
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
    """Show typing indicator to user."""
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

    # Split long messages into chunks of 2000 chars
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

            # Handle postback (button press / Get Started)
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
    return "✅ Sylas Messenger Bot is running!", 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "bot": "sylas", "version": "2.0"}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
