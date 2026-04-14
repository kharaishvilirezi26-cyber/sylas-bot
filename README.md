---
title: Sylas Messenger Bot
emoji: 🤖
colorFrom: blue
colorTo: cyan
sdk: docker
pinned: false
app_port: 7860
---

# Sylas — Facebook Messenger AI Bot

A Facebook Messenger chatbot powered by **Groq (Llama 3.3-70b)**.

## Features
- Multilingual: Georgian 🇬🇪 and English 🇬🇧 (auto-detects language)
- Conversation memory per user (last 12 messages)
- Typing indicator
- Special commands: `/reset`, `/help`
- Rate limiting built-in

## Environment Variables (set in HuggingFace Space secrets)

| Variable | Description |
|---|---|
| `PAGE_ACCESS_TOKEN` | Facebook Page Access Token |
| `VERIFY_TOKEN` | Webhook verify token (e.g. `sylas_bot_token`) |
| `GROQ_API_KEY` | Groq API key |

## Webhook URL
```
https://<your-space-url>/webhook
```
