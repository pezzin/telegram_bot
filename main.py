from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Funzione per inviare messaggio Telegram
def send_telegram_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print("[Telegram] Messaggio inviato:", response.text)

# Funzione per inviare messaggio a OpenAI
def ask_openai(message: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Rispondi come receptionist di un hotel a Rimini, in italiano."},
            {"role": "user", "content": message}
        ]
    }
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[ERRORE AI]", e)
        return "Mi dispiace, al momento il servizio non è disponibile."

# Webhook Telegram
@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    print("[Telegram] Update ricevuto:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        reply = ask_openai(user_text)
        send_telegram_message(chat_id, reply)

    return JSONResponse(content={"ok": True})

# Test locale con: uvicorn telegram_bot:app --reload
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import requests
import os

app = FastAPI()

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_API_URL = "https://api.openai.com/v1/chat/completions"

# Funzione per inviare messaggio Telegram
def send_telegram_message(chat_id: int, text: str):
    url = f"https://api.telegram.org/bot7844644488:AAEzVEPRC934ydktv6X674O4sLIXehwAEn4/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print("[Telegram] Messaggio inviato:", response.text)

# Funzione per inviare messaggio a OpenAI
def ask_openai(message: str) -> str:
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role": "system", "content": "Rispondi come receptionist di un hotel a Rimini, in italiano."},
            {"role": "user", "content": message}
        ]
    }
    try:
        response = requests.post(OPENAI_API_URL, headers=headers, json=data)
        result = response.json()
        return result["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print("[ERRORE AI]", e)
        return "Mi dispiace, al momento il servizio non è disponibile."

# Webhook Telegram
@app.post("/telegram")
async def telegram_webhook(req: Request):
    data = await req.json()
    print("[Telegram] Update ricevuto:", data)

    if "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        user_text = data["message"]["text"]

        reply = ask_openai(user_text)
        send_telegram_message(chat_id, reply)

    return JSONResponse(content={"ok": True})

# Test locale con: uvicorn telegram_bot:app --reload
