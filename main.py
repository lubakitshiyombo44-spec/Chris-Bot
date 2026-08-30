import os
import requests
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIG - Accepte tous les noms possibles ---
BOT_TOKEN = (
    os.getenv("TELEGRAM_BOT_TOKEN") or
    os.getenv("BOT_TOKEN") or
    os.getenv("TELEGRAM_TOKEN") or
    os.getenv("TEL") or ""
).strip()

GROQ_KEY = (
    os.getenv("GROQ_API_KEY") or
    os.getenv("GROQ_KEY") or
    os.getenv("GROQ") or
    os.getenv("GRO") or ""
).strip()

BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- IDENTITÉ DU BOT ---
SYSTEM_PROMPT = """Tu es Ir Chris, un assistant IA créé par Ir Chris, un jeune congolais ingénieur de Lubumbashi.
Tu es intelligent, pédagogique et amical.
Tu parles 6 langues: Français, English, Lingala, Kiswahili, Tshiluba, Kiluba.
Règle: Réponds toujours dans la même langue que l'utilisateur.
Si on te demande qui t'a créé, réponds: J'ai été créé par Ir Chris, un jeune congolais qui a développé en moi un système avancé de langues, vision et voix."""

# --- FONCTIONS ---
def send_message(chat_id, text):
    try:
        url = f"{BOT_API}/sendMessage"
        # Coupe en morceaux de 4000 caractères
        message = str(text) if text else "Message vide"
        for i in range(0, len(message), 4000):
            requests.post(url, json={
                "chat_id": chat_id,
                "text": message[i:i+4000]
            }, timeout=15)
    except Exception as e:
        print(f"Erreur envoi: {e}")

def ask_groq_text(question):
    if not GROQ_KEY:
        return "⚠️ Clé GROQ manquante. Ajoute GROQ_API_KEY dans Render."

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama-3.1-8b-instant",
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": question}
                ]
            },
            timeout=30
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erreur Groq {response.status_code}: {response.text[:200]}"

    except Exception as e:
        return f"Erreur de connexion: {e}"

def ask_groq_vision(question, b64_image):
    if not GROQ_KEY:
        return "⚠️ Clé GROQ manquante."

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": question},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }]
            },
            timeout=60
        )

        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Erreur Vision: {response.text[:200]}"

    except Exception as e:
        return f"Erreur Vision: {e}"

# --- ROUTES ---
@app.route("/")
def home():
    return jsonify({
        "status": "Ir Chris - PROPRE",
        "bot_token_ok": len(BOT_TOKEN) > 20,
        "groq_key_ok": len(GROQ_KEY) > 20
    })

@app.route("/telegram/<path:token>", methods=["POST"])
def webhook(token):
    try:
        data = request.get_json(force=True) or {}
        message = data.get("message") or {}
        chat_id = message.get("chat", {}).get("id")

        if not chat_id:
            return "ok"

        # Commande /start
        if "text" in message:
            text = message["text"]
            if text == "/start":
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
                answer = ask_groq_text(text)
                send_message(chat_id, answer)

        # Photo d'exercice
        elif "photo" in message:
            send_message(chat_id, "🖼️ Photo reçue, je lis en HD...")
            photo = message["photo"][-1] # Meilleure qualité
            file_id = photo["file_id"]

            file_info = requests.get(f"{BOT_API}/getFile?file_id={file_id}", timeout=10).json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

            img_data = requests.get(file_url, timeout=20).content
            b64 = base64.b64encode(img_data).decode()

            answer = ask_groq_vision("Résous cet exercice étape par étape:", b64)
            send_message(chat_id, answer)

        return "ok"

    except Exception as e:
        print(f"Erreur webhook: {e}")
        return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
