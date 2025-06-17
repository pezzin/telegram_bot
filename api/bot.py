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
    raise ValueError("Variabili richieste mancanti.")

bot = telegram.Bot(token=TELEGRAM_TOKEN)
app = FastAPI()
groq_client = Groq(api_key=GROQ_API_KEY)

# === CARICAMENTO DATI ===
async def carica_risposte():
    risposte = {}
    async with httpx.AsyncClient() as client:
        r = await client.get(CSV_RISPOSTE_URL)
        reader = csv.DictReader(r.text.splitlines())
        for row in reader:
            risposte[row["Intento"].strip().lower()] = row["Risposta"].strip()
    return risposte

async def carica_disponibilita():
    disp = {}
    async with httpx.AsyncClient() as client:
        r = await client.get(CSV_DISPONIBILITA_URL)
        reader = csv.DictReader(r.text.splitlines())
        for row in reader:
            hotel = row["Hotel"].strip().lower()
            tipo = row["Tipo"].strip().lower()
            stato = row["Stato"].strip()
            disp.setdefault(hotel, {})[tipo] = stato
    return disp

async def carica_servizi():
    servizi = []
    async with httpx.AsyncClient() as client:
        r = await client.get(CSV_SERVIZI_URL)
        reader = csv.DictReader(r.text.splitlines())
        for row in reader:
            servizi.append(row["Servizio"].strip())
    return servizi

def trova_match(messaggio: str, intenti: dict):
    match = get_close_matches(messaggio.lower(), list(intenti.keys()), n=1, cutoff=0.5)
    return intenti.get(match[0]) if match else None

def cerca_disponibilita(hotel: str, tipo: str, dati: dict):
    h = hotel.lower()
    t = tipo.lower()
    if h in dati and t in dati[h]:
        return f"{tipo.title()} a {hotel.title()}: {dati[h][t]}"
    return None

# === WEBHOOK ===
@app.post("/telegram")
async def webhook(request: Request):
    try:
        data = await request.json()
        update = telegram.Update.de_json(data, bot)

        if update.message and update.message.text:
            chat_id = update.message.chat.id
            user_text = update.message.text.strip().lower()

            # Carica dati
            risposte = await carica_risposte()
            disponibilita = await carica_disponibilita()
            servizi = await carica_servizi()

            # 1️⃣ Intelligenza: domanda su disponibilità?
            for hotel in disponibilita:
                for tipo in disponibilita[hotel]:
                    if hotel in user_text and tipo in user_text:
                        risposta = cerca_disponibilita(hotel, tipo, disponibilita)
                        if risposta:
                            bot.send_message(chat_id=chat_id, text=risposta)
                            return JSONResponse(content={"status": "ok"})

            # 2️⃣ Cerca risposta diretta da sheet Risposte
            risposta = trova_match(user_text, risposte)
            if risposta:
                bot.send_message(chat_id=chat_id, text=risposta)
                return JSONResponse(content={"status": "ok"})

            # 3️⃣ Prompt Groq con dati strutturati
            def formatta_disp(d):
                return "\n".join(
                    f"- {h.title()} | " + ", ".join(f"{k}: {v}" for k, v in d[h].items())
                    for h in d
                )

            prompt = {
                "role": "system",
                "content": (
                    "Rispondi come assistente Devira Hotels. "
                    "Se non sai qualcosa, dì 'non so'. "
                    "Non inventare. Ecco i dati veri:\n\n"
                    f"📅 DISPONIBILITÀ:\n{formatta_disp(disponibilita)}\n\n"
                    f"🛎️ SERVIZI ATTIVI:\n" + "\n".join(f"- {s}" for s in servizi)
                )
            }

            completion = groq_client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[prompt, {"role": "user", "content": user_text}]
            )
            reply = completion.choices[0].message.content.strip()
            bot.send_message(chat_id=chat_id, text=reply)

        return JSONResponse(content={"status": "ok"})

    except Exception as e:
        print(f"[Errore Webhook] {e}")
        return JSONResponse(content={"status": "error", "detail": str(e)})
