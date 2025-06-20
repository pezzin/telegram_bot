from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telegram
import os
import httpx
import csv
import io
from groq import Groq

# --- Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
client = Groq(api_key=GROQ_API_KEY)
app = FastAPI()

# --- Link ai CSV ---
URL_RISPOSTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
URL_DISPONIBILITA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
URL_SERVIZI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

# --- Helpers ---
def leggi_csv_da_url(url):
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        decoded = response.content.decode("utf-8")
        reader = csv.DictReader(io.StringIO(decoded))
        return list(reader)
    except Exception as e:
        print(f"[Errore lettura CSV] {e}")
        return []

# --- Webhook ---
@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.strip().lower()

            print(f"[Telegram] Messaggio ricevuto: {user_text}")

            risposte = leggi_csv_da_url(URL_RISPOSTE)
            disponibilita = leggi_csv_da_url(URL_DISPONIBILITA)
            servizi = leggi_csv_da_url(URL_SERVIZI)

            # Risposta predefinita se match
            risposta_match = next(
                (r["Risposta"] for r in risposte if r["Domanda"].strip().lower() in user_text),
                None
            )

            # Blocchi da CSV
            blocco_disp = ""
            for row in disponibilita:
                blocco_disp += f"- {row['Hotel']}: Famiglia: {row['Famiglia']}, Coppia: {row['Coppia']}\n"

            blocco_servizi = ""
            for s in servizi:
                blocco_servizi += f"- {s['Servizio']}\n"

            system_prompt = {
                "role": "system",
                "content": (
                    "Sei un assistente AI per Devira Hotels.\n"
                    "📅 **Disponibilità attuale:**\n"
                    f"{blocco_disp}\n"
                    "🛎️ **Servizi attivi oggi:**\n"
                    f"{blocco_servizi}\n"
                    "Se non sai rispondere, rispondi cortesemente e proponi di parlare con un operatore umano."
                )
            }

            messages = [system_prompt, {"role": "user", "content": user_text}]

            if risposta_match:
                reply = risposta_match
            else:
                response = client.chat.completions.create(
                    model="llama3-70b-8192",
                    messages=messages
                )
                reply = response.choices[0].message.content.strip()

            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
