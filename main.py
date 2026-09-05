import os
import requests
import base64
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= CONFIG =================
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS_OK = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]

MEMORY = defaultdict(list)
MAX_HISTORY = 6

# ================= CERVEAU =================
SYSTEM_PROMPT = f"""
Tu es Ir Chris.
- Tu n'es PAS créé par OpenAI, Meta, Google.
- Créateur unique : {CREATOR}
- Date de création : {DATE_CREATION}
- Lieu : {LIEU}
- Tu parles UNIQUEMENT ces 6 langues : {', '.join(LANGS_OK)}.

Règles :
1. Si on te demande qui t'a créé, tu réponds : J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
2. Si on te demande de parler une autre langue (espagnol, portugais, allemand...), tu refuses avec : Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye.
3. Tu n'inventes jamais. Tu utilises les {MAX_HISTORY} derniers messages pour comprendre.
"""

# Mots qui déclenchent les filtres
FORBIDDEN_LANGS = ["espagnol","spanish","español","portugais","portuguese","português","allemand","german","deutsch","italien","italian","arabe","arabic","russe","russian","chinois","chinese","japonais","¡","¿"]
IDENTITY_WORDS = ["qui t'a créé", "ton créateur", "who created you", "who is your creator"]

def is_forbidden_lang(text: str) -> bool:
    return any(w in text.lower() for w in FORBIDDEN_LANGS)

def is_identity(text: str) -> bool:
    return any(w in text.lower() for w in IDENTITY_WORDS)

def send(chat_id, text):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": text[:3800]}, timeout=15)

def get_answer(chat_id, question, image_b64=None):
    # FILTRE 1 - Langue interdite : on ne demande même pas à Groq
    if is_forbidden_lang(question):
        return "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye. Je ne peux pas répondre dans une autre langue."

    # FILTRE 2 - Identité : on répond direct sans passer par Groq pour éviter le mensonge OpenAI
    if is_identity(question):
        return f"J'ai été créé par **{CREATOR}** le **{DATE_CREATION}** à **{LIEU}** 🇨🇩."

    history = MEMORY[chat_id][-MAX_HISTORY*2:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": question}]

    model = "openai/gpt-oss-20b"
    if image_b64:
        messages[-1] = {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}
        model = "meta-llama/llama-4-scout-17b-16e-instruct"

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 1000}, timeout=60)

        if res.status_code!= 200:
            return "Petit bug serveur, réessaye."

        ans = res.json()["choices"][0]["message"]["content"]

        # FILTRE 3 - Si Groq a quand même menti
        if "openai" in ans.lower() or "je suis un modèle créé par openai" in ans.lower():
            ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}."

        ans = ans.replace("Chris Mwamba", CREATOR)

        MEMORY[chat_id].append({"role": "user", "content": question})
        MEMORY[chat_id].append({"role": "assistant", "content": ans})
        if len(MEMORY[chat_id]) > MAX_HISTORY*2:
            MEMORY[chat_id] = MEMORY[chat_id][-MAX_HISTORY*2:]

        return ans
    except Exception as e:
        print(e)
        return "Connexion lente, réessaye."

# ================= ROUTES =================
@app.route("/")
def home():
    return jsonify({"bot": "Ir Chris", "creator": CREATOR, "date": DATE_CREATION, "langues": LANGS_OK, "status": "En ligne"})

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    if not chat_id: return "ok"

    if "text" in msg:
        t = msg["text"].strip()
        if t.lower() in ["/start", "start"]:
            MEMORY[chat_id].clear()
            send(chat_id, f"Mbote! 👋 Je suis Ir Chris\nCréé par {CREATOR} le {DATE_CREATION}\n\nJe parle uniquement : {', '.join(LANGS_OK)}")
        else:
            send(chat_id, get_answer(chat_id, t))

    elif "photo" in msg:
        best = msg["photo"][-1]
        file_info = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
        img_bytes = requests.get(file_url, timeout=20).content
        b64 = base64.b64encode(img_bytes).decode()
        send(chat_id, get_answer(chat_id, "Résous cet exercice étape par étape :", b64))

    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
