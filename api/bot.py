from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telegram
import os
import httpx

# Variabili ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

# Dati dinamici finti per demo
DISPONIBILITA = {
    "eurhotel": {
        "famiglia": "✅ disponibili",
        "coppia": "⚠️ ultime 3 camere",
    },
    "san_paolo": {
        "famiglia": "❌ esaurite",
        "coppia": "✅ disponibili",
    }
}

SERVIZI_ATTIVI = [
    "animazione per bambini (10-12 e 16-19)",
    "spiaggia convenzionata (Bagno Vittorio 134)",
    "parcheggio gratuito coperto",
    "cani ammessi (max 1 per camera)",
]

# Prompt dinamico
SYSTEM_PROMPT = {
    "role": "system",
    "content": (
        "Agisci come un assistente AI per Devira Hotels, un gruppo di due hotel a Rimini: Eurhotel e San Paolo.\n\n"
        f"📅 **Disponibilità attuale:**\n"
        f"- Eurhotel:\n"
        f"   • Camere famiglia: {DISPONIBILITA['eurhotel']['famiglia']}\n"
        f"   • Camere coppia: {DISPONIBILITA['eurhotel']['coppia']}\n"
        f"- San Paolo:\n"
        f"   • Camere famiglia: {DISPONIBILITA['san_paolo']['famiglia']}\n"
        f"   • Camere coppia: {DISPONIBILITA['san_paolo']['coppia']}\n\n"
        f"🛎️ **Servizi attivi oggi:**\n"
        f"{chr(10).join(f'- {s}' for s in SERVIZI_ATTIVI)}\n\n"
        "Se il cliente chiede qualcosa fuori da questi dati, rispondi in modo cortese, proponi alternative, "
        "oppure offri la possibilità di parlare con un operatore umano."
    )
}

@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text
            print(f"[Telegram] Messaggio ricevuto: {user_text}")

            # Chiamata Groq
            response = await call_groq_api(user_text)
            reply = response or "Al momento non riesco a rispondere, prova a contattarci direttamente 😊"

            # Invia messaggio
            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)


async def call_groq_api(user_text: str) -> str:
    try:
        async with httpx.AsyncClient() as client:
            res = await client.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "llama3-70b-8192",
                    "messages": [SYSTEM_PROMPT, {"role": "user", "content": user_text}],
                    "temperature": 0.7
                }
            )
            res.raise_for_status()
            data = res.json()
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[Errore Groq] {str(e)}")
        return None
