import os
import base64
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GROQ_KEY = os.getenv("GROQ_API_KEY", "")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}" if BOT_TOKEN else ""

SYSTEM_PROMPT = """Tu es Chris-Bot de Lubumbashi. Tu parles 6 langues: Français, English, Kiswahili, Lingala, Kisonge/Tshiluba, Kiluba/Luba-Kat. DETECTE la langue de l'utilisateur et REPONDS dans la MEME langue. Tu es prof expert qui résout examens étape par étape, pédagogique, amical. Si mélange, réponds en Français."""

def send_message(chat_id, text):
    try:
        for i in range(0, len(text), 4000):
            chunk = text[i:i+4000]
            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": chunk}, timeout=15)
    except Exception as e:
        print(f"Send error: {e}")

def ask_groq_text(user_text):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": user_text}]}
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    return r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else f"Erreur Groq: {r.text[:300]}"

def ask_groq_vision(user_text, image_b64):
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    payload = {"model": "meta-llama/llama-4-maverick-17b-128e-instruct", "messages": [{"role": "user", "content": [{"type": "text", "text": f"{SYSTEM_PROMPT}\n{user_text}"}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}]}
    r = requests.post(url, json=payload, headers=headers, timeout=50)
    return r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else f"Erreur Vision: {r.text[:300]}"

def transcribe_audio(file_url):
    try:
        audio_bytes = requests.get(file_url, timeout=20).content
        headers = {"Authorization": f"Bearer {GROQ_KEY}"}
        files = {"file": ("voice.ogg", audio_bytes, "audio/ogg"), "model": (None, "whisper-large-v3")}
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions", headers=headers, files=files, timeout=40)
        return r.json().get("text", "") if r.status_code == 200 else ""
    except: return ""

@app.route("/")
def home(): return jsonify({"status": "Chris-Bot LIVE", "bot": bool(BOT_TOKEN), "groq": bool(GROQ_KEY), "langues": 6})

@app.route("/telegram/<token>", methods=["POST"])
def webhook(token):
    # Sécurité: vérifie token
    if token!= BOT_TOKEN: return "ok"
    try:
        data = request.get_json()
        if not data or "message" not in data: return "ok"
        msg = data["message"]
        chat_id = msg["chat"]["id"]

        if "text" in msg:
            text = msg["text"]
            if text == "/start":
                send_message(chat_id, "Mbote! Habari! Hello! 👋\nJe suis Chris-Bot!\n6 langues: FR, EN, Swahili, Lingala, Kisonge, Kiluba\n\n🎤 Envoie vocal\n🖼️ Envoie photo examen\n💬 Envoie question\nJe résous étape par étape!")
            else:
                send_message(chat_id, "⏳ Nazoluka...")
                send_message(chat_id, ask_groq_text(text))
        elif "voice" in msg or "audio" in msg:
            send_message(chat_id, "🎧 Je transcris...")
            file_id = (msg.get("voice") or msg.get("audio"))["file_id"]
            info = requests.get(f"{BOT_API}/getFile?file_id={file_id}", timeout=10).json()
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{info['result']['file_path']}"
            txt = transcribe_audio(file_url)
            if txt:
                send_message(chat_id, f"📝 Tu as dit: {txt}")
                send_message(chat_id, ask_groq_text(txt))
            else: send_message(chat_id, "❌ Vocal non compris, renvoie stp!")
        elif "photo" in msg:
            send_message(chat_id, "🖼️ Je lis la capture...")
            file_id = msg["photo"][-1]["file_id"]
            info = requests.get(f"{BOT_API}/getFile?file_id={file_id}", timeout=10).json()
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{info['result']['file_path']}"
            img_b64 = base64.b64encode(requests.get(file_url, timeout=20).content).decode()
            send_message(chat_id, ask_groq_vision("Résous cet exercice complètement:", img_b64))
        return "ok"
    except Exception as e:
        print(f"ERROR: {e}"); return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
