"""
Sylas Messenger Bot - Auto Startup Script
Run this file to start the bot: python run.py
"""
import os
import sys
import threading
import time

def check_env():
    missing = []
    if not os.environ.get("PAGE_ACCESS_TOKEN"):
        missing.append("PAGE_ACCESS_TOKEN")
    if not os.environ.get("GROQ_API_KEY"):
        missing.append("GROQ_API_KEY")
    return missing

def load_env():
    env_file = os.path.join(os.path.dirname(__file__), ".env")
    if not os.path.exists(env_file):
        return
    with open(env_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

def start_ngrok():
    try:
        from pyngrok import ngrok, conf
        ngrok_token = os.environ.get("NGROK_AUTH_TOKEN")
        if ngrok_token:
            conf.get_default().auth_token = ngrok_token
        tunnel = ngrok.connect(5000, "http")
        url = tunnel.public_url
        if url.startswith("http://"):
            url = url.replace("http://", "https://")
        print("\n" + "="*60)
        print("BOT WEBHOOK URL:")
        print(f"  {url}/webhook")
        print("="*60)
        print("\nAdd this URL to Facebook Developer App Webhook.")
        print("Verify Token: sylas_bot_token")
        print("="*60 + "\n")
        return url
    except Exception as e:
        print(f"\nngrok error: {e}")
        print("Bot running locally only: http://localhost:5000")
        return None

if __name__ == "__main__":
    load_env()

    missing = check_env()
    if missing:
        print("\n" + "="*60)
        print("Missing keys in .env:")
        for key in missing:
            print(f"  - {key}")
        print("="*60)
        sys.exit(1)

    print("Sylas Messenger Bot starting...")

    # start ngrok in background thread
    ngrok_thread = threading.Thread(target=start_ngrok, daemon=True)
    ngrok_thread.start()
    time.sleep(2)

    # start Flask app
    from app import app
    app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False)
