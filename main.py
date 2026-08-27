import os
import base64
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GROQ_KEY = os.getenv("GROQ_API_KEY")

if not BOT_TOKEN:
    print("❌ ERREUR: TELEGRAM_BOT_TOKEN manquant!")
if not GROQ_KEY:
    print("❌ ERREUR: GROQ_API_KEY manquant!")

BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

# PROMPT MULTILINGUE MASTER
SYSTEM_PROMPT = """Tu es Chris-Bot, l'assistant intelligent de Lubumbashi créé par Ir Chris.

Tu maîtrises 6 langues PARFAITEMENT:
1. Français
2. Anglais (English)
3. Kiswahili
4. Lingala
5. Kisonge / Tshiluba
6. Kiluba / Luba-Katanga

RÈGLES OBLIGATOIRES:
- Détecte automatiquement la langue du message (texte, vocal transcrit, ou image)
- Réponds TOUJOURS dans la MÊME langue que l'utilisateur
- Si l'utilisateur mélange les langues, réponds en Français
- Tu es un professeur expert qui résout les examens, exercices, TP, interrogations
- Explique TOUJOURS étape par étape, clair, simple, pédagogique
- Pour les photos de captures d'examens: lis l'énoncé, résous tout, donne la réponse finale
- Sois amical, utilise des emojis
"""

def send_message(chat_id, text):
    try:
        # Telegram limite à 4096 caractères
        for i in range(0, len(text), 4000):
            chunk = text[i:i+4000]
            requests.post(f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": chunk, "parse_mode": "Markdown"},
                timeout=15)
    except Exception as e:
        print(f"Send error: {e}")

def ask_groq_text(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "llama-3.1-8b-instant",
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text}
        ],
        "temperature": 0.7
    }
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ Erreur Groq ({r.status_code}): {r.text[:500]}"

def ask_groq_vision(user_text, image_b64):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {
        "model": "meta-llama/llama-4-maverick-17b-128e-instruct",
        "messages": [{
            "role": "user",
            "content": [
                {"type": "text", "text": f"{SYSTEM_PROMPT}\n\nConsigne utilisateur: {user_text}\nLis l'image et résous l'exercice:"},
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
            ]
        }],
        "temperature": 0.5
    }
    r = requests.post(url, json=payload, headers=headers, timeout=50)
    if r.status_code == 200:
        return r.json()["choices"][0]["message"]["content"]
    else:
        return f"❌ Erreur Vision Groq ({r.status_code}): {r.text[:500]}"

def transcribe_audio(file_url):
    try:
        audio_bytes = requests.get(file_url, timeout=20).content
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
        files = {
            "file": ("voice.ogg", audio_bytes, "audio/ogg"),
            "model": (None, "whisper-large-v3")
        }
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
                          headers=headers, files=files, timeout=40)
        if r.status_code == 200:
            return r.json().get("text", "")
        print(f"Transcribe fail: {r.text}")
        return ""
    except Exception as e:
        print(f"Transcribe error: {e}")
        return ""

@app.route("/")
def home():
    return jsonify({
        "status": "Chris-Bot LIVE",
        "bot_configured": bool(BOT_TOKEN),
        "groq_configured": bool(GROQ_KEY),
        "languages": ["Français", "English", "Kiswahili", "Lingala", "Kisonge", "Kiluba"],
        "features": ["texte", "vocal", "photo-examen"]
    })

@app.route("/health")
def health():
    return jsonify({"bot": bool(BOT_TOKEN), "groq": bool(GROQ_KEY)})

@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
@app.route("/telegram/webhook", methods=["POST"]) # fallback
def webhook():
    try:
        data = request.get_json()
        if not data or "message" not in data:
            return "ok"

        msg = data["message"]
        chat_id = msg["chat"]["id"]

        # 1. TEXTE
        if "text" in msg:
            text = msg["text"]
            if text == "/start":
                welcome = (
                    "Mbote! Habari! Hello! 👋\n\n"
                    "Je suis **Chris-Bot** ton prof perso!\n\n"
                    "Je parle 6 langues:\n"
                    "🇫🇷 Français | 🇬🇧 English | 🇨🇩 Kiswahili\n"
                    "🇨🇩 Lingala | 🇨🇩 Kisonge | 🇨🇩 Kiluba\n\n"
                    "Envoie-moi:\n"
                    "🎤 *Vocal* - pose ta question\n"
                    "🖼️ *Photo* - capture d'examen / exercice\n"
                    "💬 *Texte* - n'importe quelle question\n\n"
                    "Je réponds dans ta langue et je résous étape par étape!"
                )
                send_message(chat_id, welcome)
            else:
                send_message(chat_id, "⏳ Nazo luka
