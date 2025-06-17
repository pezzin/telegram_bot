from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telegram
import os
import openai

# Caricamento variabili d'ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = FastAPI()

# Client OpenAI ma con endpoint Groq
client = openai.OpenAI(
    api_key=GROQ_API_KEY,
    base_url="https://api.groq.com/openai/v1"
)

@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text

            print(f"[Telegram] Messaggio ricevuto: {user_text}")

            # Chiamata al modello Groq (puoi usare llama3-70b o mixtral-8x7b)
            response = client.chat.completions.create(
                # model="mixtral-8x7b-32768",  oppure "llama3-70b-8192"
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": "Rispondi in modo utile e amichevole."},
                    {"role": "user", "content": user_text}
                ]
            )

            reply = response.choices[0].message.content.strip()
            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
