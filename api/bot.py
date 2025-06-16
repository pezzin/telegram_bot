from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telegram
import openai
import os

# Caricamento variabili d'ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o OPENAI_API_KEY mancante")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY
app = FastAPI()

@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text

            # Log del messaggio ricevuto
            print(f"[Telegram] Messaggio ricevuto: {user_text}")

            # Chiamata a OpenAI
            response = openai.ChatCompletion.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "Rispondi come un assistente amichevole e utile."},
                    {"role": "user", "content": user_text}
                ]
            )
            reply = response.choices[0].message["content"].strip()

            # Risposta su Telegram
            bot.send_message(chat_id=chat_id, text=reply)

        # Risposta necessaria per Telegram
        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
