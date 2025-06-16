from fastapi import FastAPI, Request
import telegram
import openai
import os

# Carica token
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Setup
bot = telegram.Bot(token=TELEGRAM_TOKEN)
openai.api_key = OPENAI_API_KEY

app = FastAPI()

def get_gpt_reply(prompt: str) -> str:
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Rispondi in modo amichevole, sintetico e chiaro."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=200,
            temperature=0.7,
        )
        return response.choices[0].message["content"].strip()
    except Exception as e:
        return f"Errore durante la risposta AI: {e}"

@app.post("/telegram")
async def receive_webhook(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, bot)

    if update.message:
        chat_id = update.message.chat.id
        user_text = update.message.text
        reply = get_gpt_reply(user_text)
        bot.send_message(chat_id=chat_id, text=reply)

    return {"ok": True}
