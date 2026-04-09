import os
import requests
from flask import Flask, request, jsonify
from groq import Groq

app = Flask(__name__)

PAGE_ACCESS_TOKEN = os.environ.get("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "sylas_bot_token")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")

groq_client = Groq(api_key=GROQ_API_KEY)

# conversation history per user (in-memory)
conversations = {}

SYSTEM_PROMPT = """You are the friendly and professional assistant for the Sylas Facebook page.
Always respond in English using correct grammar and a warm, helpful tone.
Keep your answers clear, concise, and conversational.
If someone asks about Sylas, be helpful and engaging.
Never switch to another language unless the user specifically requests it."""


def get_ai_response(user_id: str, user_message: str) -> str:
    if user_id not in conversations:
        conversations[user_id] = []

    conversations[user_id].append({"role": "user", "content": user_message})

    # keep last 10 messages to save memory
    if len(conversations[user_id]) > 10:
        conversations[user_id] = conversations[user_id][-10:]

    try:
        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}] + conversations[user_id],
            max_tokens=500,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        conversations[user_id].append({"role": "assistant", "content": reply})
        return reply
    except Exception as e:
        print(f"Groq error: {e}")
        return "Sorry, I'm unable to respond right now. Please try again later."


def send_message(recipient_id: str, text: str):
    url = "https://graph.facebook.com/v19.0/me/messages"
    params = {"access_token": PAGE_ACCESS_TOKEN}
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": text},
        "messaging_type": "RESPONSE",
    }
    r = requests.post(url, json=payload, params=params)
    if r.status_code != 200:
        print(f"Facebook send error: {r.status_code} {r.text}")


@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verified!")
        return challenge, 200
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

            # ignore messages sent by the page itself
            if event.get("message", {}).get("is_echo"):
                continue

            text = event.get("message", {}).get("text")
            if text:
                reply = get_ai_response(sender_id, text)
                send_message(sender_id, reply)

    return "OK", 200


@app.route("/", methods=["GET"])
def index():
    return "Sylas Messenger Bot is running!", 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=False)
