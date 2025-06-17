
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import os
import pandas as pd
import httpx
import io
from groq import Groq
import telegram

# Config
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = "llama3-70b-8192"

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("TELEGRAM_BOT_TOKEN o GROQ_API_KEY mancante")

app = FastAPI()
bot = telegram.Bot(token=TELEGRAM_TOKEN)
groq_client = Groq(api_key=GROQ_API_KEY)

# Sheet URLs
URL_RISPOSTE = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
URL_DISP = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
URL_SERVIZI = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

def carica_csv(url):
    r = httpx.get(url, follow_redirects=True)
    r.raise_for_status()
    return pd.read_csv(io.StringIO(r.text))

@app.post("/telegram")
async def telegram_webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.lower()

            df_risp = carica_csv(URL_RISPOSTE)
            df_disp = carica_csv(URL_DISP)
            df_serv = carica_csv(URL_SERVIZI)

            # Match da sheet Risposte
            risposta_trovata = df_risp[df_risp["Domanda Chiave"].str.lower() == user_text]
            if not risposta_trovata.empty:
                reply = risposta_trovata.iloc[0]["Risposta"]
            else:
                # Genera blocco disponibilità
                blocco_disp = ""
                for _, row in df_disp.iterrows():
                    blocco_disp += (
                        f"- {row['Hotel']}:
"
                        f"   • Camere famiglia: {row['Camere Famiglia']}
"
                        f"   • Camere coppia: {row['Camere Coppia']}
"
                    )

                blocco_servizi = "\n".join(f"- {s}" for s in df_serv["Servizi Attivi"].dropna())

                system_prompt = (
                    "Agisci come un assistente AI per Devira Hotels, un gruppo di hotel a Rimini, Riolo, Bologna e Firenze.\n\n"
                    f"📅 **Disponibilità attuale:**\n{blocco_disp}\n"
                    f"🛎️ **Servizi attivi oggi:**\n{blocco_servizi}\n\n"
                    "Se il cliente chiede qualcosa fuori da questi dati, rispondi in modo cortese, proponi alternative o offri la possibilità di parlare con un operatore umano."
                )

                completion = groq_client.chat.completions.create(
                    model=GROQ_MODEL,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_text}
                    ]
                )
                reply = completion.choices[0].message.content.strip()

            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {str(e)}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
