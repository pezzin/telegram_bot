from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telegram
import os
import httpx
import csv
from difflib import get_close_matches
from groq import Groq

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

CSV_RISPOSTE_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=0&single=true&output=csv"
CSV_DISPONIBILITA_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=2058363400&single=true&output=csv"
CSV_SERVIZI_URL = "https://docs.google.com/spreadsheets/d/e/2PACX-1vTfKTKUxwGGeVs6TXS9847PYesuANrJV7sg7Gxg3RTm45sDBUXpYx7YlOIM3i3d2B8HQluwU2mW-0A0/pub?gid=894447983&single=true&output=csv"

if not TELEGRAM_TOKEN or not GROQ_API_KEY:
    raise ValueError("Variabili richieste mancanti: TELEGRAM_BOT_TOKEN, GROQ_API_KEY")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = FastAPI()
groq_client = Groq(api_key=GROQ_API_KEY)

# === FUNZIONI UTILI ===
async def carica_risposte():
    risposte = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CSV_RISPOSTE_URL)
            response.raise_for_status()
            reader = csv.DictReader(response.text.splitlines())
            for row in reader:
                risposte[row["Intento"].strip().lower()] = row["Risposta"].strip()
    except Exception as e:
        print(f"[Errore CSV Risposte] {e}")
    return risposte

async def carica_disponibilita():
    struttura = {}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CSV_DISPONIBILITA_URL)
            response.raise_for_status()
            reader = csv.DictReader(response.text.splitlines())
            for row in reader:
                hotel = row["Hotel"].strip().lower()
                tipo = row["Tipo"].strip().lower()
                stato = row["Stato"].strip()
                struttura.setdefault(hotel, {})[tipo] = stato
    except Exception as e:
        print(f"[Errore CSV Disponibilità] {e}")
    return struttura

async def carica_servizi():
    servizi = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(CSV_SERVIZI_URL)
            response.raise_for_status()
            reader = csv.DictReader(response.text.splitlines())
            for row in reader:
                servizi.append(row["Servizio"].strip())
    except Exception as e:
        print(f"[Errore CSV Servizi] {e}")
    return servizi

def trova_risposta_automatica(testo_utente, knowledge_base):
    intenti = list(knowledge_base.keys())
    match = get_close_matches(testo_utente.lower(), intenti, n=1, cutoff=0.5)
    return knowledge_base.get(match[0]) if match else None

# === WEBHOOK ===
@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.strip()
            print(f"[Telegram] Messaggio ricevuto: {user_text}")

            # Caricamento dati da Sheet
            risposte = await carica_risposte()
            disponibilita = await carica_disponibilita()
            servizi = await carica_servizi()

            # Match intenti (Risposte statiche)
            risposta = trova_risposta_automatica(user_text, risposte)
            if risposta:
                bot.send_message(chat_id=chat_id, text=risposta)
                return JSONResponse(content={"status": "ok"}, status_code=200)

            # Prompt dinamico
            def formatta_disp(d):
                blocchi = []
                for hotel, camere in d.items():
                    righe = [f"   • Camere {tipo}: {stato}" for tipo, stato in camere.items()]
                    blocchi.append(f"- {hotel.title()}:\n" + "\n".join(righe))
                return "\n".join(blocchi)

            system_prompt = {
                "role": "system",
                "content": (
                    "Agisci come un assistente AI per Devira Hotels, un gruppo di hotel a Rimini, Riolo, Bologna e Firenze.\n\n"
                    f"📅 **Disponibilità attuale:**\n{formatta_disp(disponibilita)}\n\n"
                    f"🛎️ **Servizi attivi oggi:**\n{chr(10).join(f'- {s}' for s in servizi)}\n\n"
                    "Se il cliente chiede qualcosa fuori da questi dati, rispondi in modo cortese, proponi alternative, "
                    "oppure offri la possibilità di parlare con un operatore umano."
                )
            }

            # Chiamata Groq
            response = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[system_prompt, {"role": "user", "content": user_text}]
            )
            reply = response.choices[0].message.content.strip()
            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"}, status_code=200)

    except Exception as e:
        print(f"[Errore Webhook] {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)}, status_code=200)
