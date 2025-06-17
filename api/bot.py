
import os
import csv
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, Update
from groq import Groq

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

bot = Bot(token=TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
app = FastAPI()

# URL dei CSV pubblici
URL_RISPOSTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
URL_DISPONIBILITA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
URL_SERVIZI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

def fetch_csv(url):
    response = httpx.get(url)
    response.raise_for_status()
    lines = response.text.strip().splitlines()
    return list(csv.DictReader(lines))

@app.post("/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            user_text = update.message.text
            chat_id = update.message.chat_id

            # Leggi dati
            risposte = fetch_csv(URL_RISPOSTE)
            disponibilita = fetch_csv(URL_DISPONIBILITA)
            servizi = fetch_csv(URL_SERVIZI)

            # Blocchi per prompt dinamico
            blocco_disp = ""
            for row in disponibilita:
                blocco_disp += f"- {row['Hotel']}: Famiglia: {row['Famiglia']}, Coppia: {row['Coppia']}
"

            blocco_servizi = ""
            for s in servizi:
                blocco_servizi += f"- {s['Servizio']}
"

            system_prompt = {
                "role": "system",
                "content": (
                    "Sei un assistente AI per Devira Hotels.
"
                    f"📅 **Disponibilità attuale:**
{blocco_disp}
"
                    f"🛎️ **Servizi attivi oggi:**
{blocco_servizi}
"
                    "Rispondi in modo amichevole e utile. Se non sai qualcosa, invita l’utente a contattare la reception."
                )
            }

            # Risposte predefinite
            risposta_custom = next((r["Risposta"] for r in risposte if r["Domanda"].lower() in user_text.lower()), None)

            if risposta_custom:
                bot.send_message(chat_id=chat_id, text=risposta_custom)
            else:
                chat_completion = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=[system_prompt, {"role": "user", "content": user_text}]
                )
                reply = chat_completion.choices[0].message.content.strip()
                bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
