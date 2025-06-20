from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import httpx
import pandas as pd
import io
from groq import Groq
from telegram import Bot
from telegram.request import HTTPXRequest

# --- Config ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

# Telegram Bot asincrono con HTTPXRequest
request_con = HTTPXRequest(pool_maxsize=100, connect_timeout=10, read_timeout=10)
bot = Bot(token=TELEGRAM_TOKEN, request=request_con)

# Groq client
client = Groq(api_key=GROQ_API_KEY)

app = FastAPI()

# --- Link ai CSV ---
URL_RISPOSTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
URL_DISPONIBILITA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
URL_SERVIZI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

# --- Helpers ---
def carica_csv_pandas(url):
    try:
        response = httpx.get(url, follow_redirects=True)
        response.raise_for_status()
        return pd.read_csv(io.StringIO(response.text))
    except Exception as e:
        print(f"[Errore CSV] {e}")
        return pd.DataFrame()

# --- Webhook ---
@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        chat_id = data['message']['chat']['id']
        user_text = data['message']['text'].strip().lower()

        df_risposte = carica_csv_pandas(URL_RISPOSTE)
        df_disp = carica_csv_pandas(URL_DISPONIBILITA)
        df_servizi = carica_csv_pandas(URL_SERVIZI)

        risposta_match = None
        if not df_risposte.empty and "Domanda" in df_risposte.columns:
            for _, row in df_risposte.iterrows():
                if row["Domanda"].strip().lower() in user_text:
                    risposta_match = row["Risposta"]
                    break

        blocco_disp = ""
        if not df_disp.empty and {"Hotel", "Famiglia", "Coppia"}.issubset(df_disp.columns):
            for _, row in df_disp.iterrows():
                blocco_disp += f"- {row['Hotel']}: Famiglia: {row['Famiglia']}, Coppia: {row['Coppia']}\n"

        blocco_servizi = ""
        if not df_servizi.empty and "Servizio" in df_servizi.columns:
            for s in df_servizi["Servizio"]:
                blocco_servizi += f"- {s}\n"

        system_prompt = {
            "role": "system",
            "content": (
                "Sei un assistente AI per Devira Hotels.\n"
                "📅 Disponibilità attuale:\n"
                f"{blocco_disp}\n"
                "🛎️ Servizi attivi oggi:\n"
                f"{blocco_servizi}\n"
                "Se non sai rispondere, invita a contattare un operatore umano."
            )
        }

        if risposta_match:
            reply = risposta_match
        else:
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[system_prompt, {"role": "user", "content": user_text}]
            )
            reply = response.choices[0].message.content.strip()

        await bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)})
