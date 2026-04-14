import sys
import os

# Add project to path
project_home = '/home/sylasbot/sylas-bot'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

# Set environment variables
# Set these in PythonAnywhere → Web tab → Environment variables section
# os.environ['PAGE_ACCESS_TOKEN'] = 'your_token_here'
# os.environ['VERIFY_TOKEN'] = 'sylas_bot_token'
# os.environ['GROQ_API_KEY'] = 'your_groq_key_here'

# Activate virtualenv
activate_this = '/home/sylasbot/sylas-bot/venv/bin/activate_this.py'
with open(activate_this) as f:
    exec(f.read(), {'__file__': activate_this})

from app import app as application
