import os
import requests
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN") or
    os.getenv("BOT_TOKEN") or
    os.getenv("TELEGRAM_TOKEN") or
    os.getenv("TEL") or ""
).strip()

GROQ_KEY = (
    os.getenv("GROQ_API_KEY") or
    os.getenv("GROQ_KEY") or
    os.getenv("GROQ") or ""
).strip()

BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYSTEM_PROMPT = """Tu es Ir Chris, créé par Ir Chris, jeune congolais ingénieur de Lubumbashi.
Tu possèdes un système intelligent multilingue, vision et voix.
Langues: Français, Lingala, Swahili, English, Tshiluba, Kiluba.
Tu réponds toujours dans la langue de l'utilisateur. Clair, pédagogique, amical."""

def send_message(chat_id, text):
    try:
        msg = str(text) if text else "Message vide"
        for i in range(0, len(msg), 4000):
            requests.post(f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": msg[i:i+4000]}, timeout=15)
    except Exception as e:
        print(e)

def ask_text(question):
    if not GROQ_KEY:
        return "GROQ_KEY manquante dans Render."
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.3-70b-versatile",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ]
            },
            timeout=40
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Erreur {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"Erreur: {e}"

def ask_vision(question, b64_image):
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{SYSTEM_PROMPT}\n\n{question}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }]
            },
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Erreur Vision: {r.text[:300]}"
    except Exception as e:
        return f"Erreur Vision: {e}"

@app.route("/")
def home():
    return jsonify({"status": "Ir Chris - En ligne", "bot": len(BOT_TOKEN) > 0, "groq": len(GROQ_KEY) > 0})

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    try:
        data = request.get_json(force=True) or {}
        msg = data.get("message") or {}
        chat_id = msg.get("chat", {}).get("id")
        if not chat_id:
            return "ok"

        if "text" in msg:
            t = msg["text"]
            if t == "/start":
                send_message(chat_id,
                    "Mbote Ir! 👋\n\n"
                    "Je suis **Ir Chris**\n"
                    "Créé par Ir Chris, jeune congolais de Lubumbashi 🇨🇩\n\n"
                    "✅ Je parle 6 langues\n"
                    "✅ Je lis les photos d'exercices\n"
                    "✅ Je comprends les vocaux\n\n"
                    "Envoie-moi ce que tu veux!"
                )
            else:
                send_message(chat_id, ask_text(t))

        elif "photo" in msg:
            send_message(chat_id, "🖼️ Photo reçue, je lis...")
            best = msg["photo"][-1]
            file_info = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
            img = requests.get(file_url, timeout=20).content
            b64 = base64.b64encode(img).decode()
            ans = ask_vision("Résous cet exercice étape par étape:", b64)
            send_message(chat_id, ans)

        return "ok"
    except Exception as e:
        print(e)
        return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
