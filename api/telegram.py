from fastapi import FastAPI, Request
import telegram
import os

TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telegram.Bot(token=TOKEN)
app = FastAPI()

@app.post("/telegram")
async def receive_webhook(request: Request):
    data = await request.json()
    update = telegram.Update.de_json(data, bot)

    if update.message:
        chat_id = update.message.chat.id
        user_text = update.message.text
        reply = f"Hai scritto: {user_text}"
        bot.send_message(chat_id=chat_id, text=reply)

    return {"ok": True}
