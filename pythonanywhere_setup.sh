#!/bin/bash
# ======================================================
# Sylas Bot - PythonAnywhere Setup Script
# Run this in PythonAnywhere Bash Console after login
# ======================================================

echo "=== Sylas Bot PythonAnywhere Setup ==="

# 1. Clone the repo
cd ~
rm -rf sylas-bot
git clone https://github.com/kharaishvilirezi26-cyber/sylas-bot.git
cd sylas-bot

# 2. Install dependencies in virtualenv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

echo ""
echo "=== Setup complete! ==="
echo "Now go to the Web tab in PythonAnywhere dashboard and:"
echo "1. Click 'Add a new web app'"
echo "2. Choose 'Manual configuration'"
echo "3. Choose Python 3.10"
echo "4. Set source code to: /home/sylasbot/sylas-bot"
echo "5. Set virtualenv to: /home/sylasbot/sylas-bot/venv"
echo "6. Edit WSGI file (see wsgi_config.py)"
echo ""
echo "Webhook URL will be: https://sylasbot.pythonanywhere.com/webhook"
