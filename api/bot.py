
import os
import io
import httpx
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from telegram import Bot, Update
from groq import Groq

# Caricamento delle chiavi da variabili d'ambiente
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

bot = Bot(token=TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)
app = FastAPI()

# URL dei Google Sheet CSV pubblici
URL_RISPOSTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
URL_DISPONIBILITA = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
URL_SERVIZI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

def carica_csv_sicuro(url):
    r = httpx.get(url, follow_redirects=True)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))

def costruisci_prompt():
    disponibilita = carica_csv_sicuro(URL_DISPONIBILITA)
    servizi = carica_csv_sicuro(URL_SERVIZI)

    blocco_disp = ""
    for _, row in disponibilita.iterrows():
        blocco_disp += f"- {row['Hotel']}:
"
        blocco_disp += f"   • Camere famiglia: {row['Famiglia']}
"
        blocco_disp += f"   • Camere coppia: {row['Coppia']}
"

    blocco_servizi = ""
    for s in servizi["Servizio"]:
        blocco_servizi += f"- {s}
"

    return {
        "role": "system",
        "content": (
            "Agisci come un assistente AI per Devira Hotels, un gruppo di hotel a Rimini, Riolo, Bologna e Firenze.\n\n"
            f"📅 **Disponibilità attuale:**\n{blocco_disp}\n"
            f"🛎️ **Servizi attivi oggi:**\n{blocco_servizi}\n\n"
            "Se il cliente chiede qualcosa fuori da questi dati, rispondi in modo cortese, proponi alternative, "
            "oppure offri la possibilità di parlare con un operatore umano."
        )
    }

@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.strip()

            df_risposte = carica_csv_sicuro(URL_RISPOSTE)

            risposta_custom = df_risposte.loc[df_risposte["Domanda"].str.lower() == user_text.lower()]
            if not risposta_custom.empty:
                risposta = risposta_custom.iloc[0]["Risposta"]
                bot.send_message(chat_id=chat_id, text=risposta)
            else:
                prompt = costruisci_prompt()
                completion = groq_client.chat.completions.create(
                    model="llama3-8b-8192",
                    messages=[prompt, {"role": "user", "content": user_text}],
                )
                reply = completion.choices[0].message.content.strip()
                bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
