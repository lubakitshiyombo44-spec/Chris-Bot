import os
import requests
import base64
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- CONFIG ---
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

# --- IDENTITÉ IR CHRIS - 6 LANGUES ---
SYSTEM_PROMPT = """
Tu es Ir Chris, créé par Ir Chris, jeune congolais ingénieur de Lubumbashi en RDC.

Tu possèdes un système intelligent multilingue, vision HD et voix.

TES 6 LANGUES OFFICIELLES:
1. Français
2. English
3. Swahili (Kiswahili)
4. Lingala
5. Kiluba
6. Kisongye

RÈGLES:
- Réponds TOUJOURS dans la même langue que l'utilisateur a utilisée.
- Si l'utilisateur parle en Kiluba, réponds en Kiluba.
- Si l'utilisateur parle en Kisongye, réponds en Kisongye.
- Sois pédagogique, clair, amical.
- Si on te demande qui t'a créé, réponds: J'ai été créé par Ir Chris, jeune congolais de Lubumbashi.
- Tu sais résoudre les exercices et examens à partir des photos.
"""

# --- FONCTIONS ---
def send_message(chat_id, text):
    try:
        msg = str(text) if text else "Message vide"
        for i in range(0, len(msg), 4000):
            requests.post(
                f"{BOT_API}/sendMessage",
                json={"chat_id": chat_id, "text": msg[i:i+4000]},
                timeout=15
            )
    except Exception as e:
        print(f"SEND ERROR: {e}")

def ask_groq(text, image_b64=None):
    if not GROQ_KEY:
        return "Erreur: GROQ_KEY manquante dans Render."

    headers = {
        "Authorization": f"Bearer {GROQ_KEY}",
        "Content-Type": "application/json"
    }

    # Modèle qui marche en 2026 sur compte gratuit
    if image_b64:
        payload = {
            "model": "meta-llama/llama-4-scout-17b-16e-instruct",
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": text},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }]
        }
    else:
        payload = {
            "model": "openai/gpt-oss-20b",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text}
            ]
        }

    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"]
        else:
            # Fallback si scout ne marche pas, essaie avec gpt-oss
            if image_b64:
                payload["model"] = "openai/gpt-oss-20b"
                r2 = requests.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                if r2.status_code == 200:
                    return r2.json()["choices"][0]["message"]["content"]
            return f"Erreur Groq {r.status_code}: {r.text[:300]}"
    except Exception as e:
        return f"Erreur connexion: {e}"

# --- ROUTES ---
@app.route("/")
def home():
    return jsonify({
        "status": "Ir Chris - En ligne",
        "bot_token": len(BOT_TOKEN) > 10,
        "groq_key": len(GROQ_KEY) > 10,
        "langues": ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]
    })

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    try:
        data = request.get_json(force=True) or {}
        msg = data.get("message") or {}
        chat_id = msg.get("chat", {}).get("id")

        if not chat_id:
            return "ok"

        # COMMANDE /start
        if "text" in msg:
            t = msg["text"]
            if t == "/start":
                send_message(chat_id,
                    "Mbote! 👋\n\n"
                    "Je suis **Ir Chris**\n"
                    "Créé par Ir Chris, jeune congolais de Lubumbashi 🇨🇩\n\n"
                    "✅ Je parle 6 langues:\n"
                    "• Français\n"
                    "• English\n"
                    "• Swahili\n"
                    "• Lingala\n"
                    "• Kiluba\n"
                    "• Kisongye\n\n"
                    "✅ Je lis les photos d'exercices\n"
                    "✅ Je comprends les vocaux\n\n"
                    "Envoie-moi ce que tu veux!"
                )
            else:
                answer = ask_groq(t)
                send_message(chat_id, answer)

        # PHOTO D'EXERCICE
        elif "photo" in msg:
            send_message(chat_id, "🖼️ Photo reçue, je lis en HD...")
            best_photo = msg["photo"][-1]
            file_id = best_photo["file_id"]

            file_info = requests.get(
                f"{BOT_API}/getFile?file_id={file_id}",
                timeout=10
            ).json()

            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"

            img_data = requests.get(file_url, timeout=20).content
            b64_image = base64.b64encode(img_data).decode()

            answer = ask_groq(
                "Résous complètement cet exercice/examen étape par étape avec explications claires et pédagogiques:",
                b64_image
            )
            send_message(chat_id, answer)

        return "ok"

    except Exception as e:
        print(f"WEBHOOK ERROR: {e}")
        return "ok"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
