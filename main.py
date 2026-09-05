import os, requests, base64, datetime
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "IrChris2026")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LANGS_OK = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]

# TOUT CE QUI N'EST PAS DANS LES 6 = INTERDIT
MOTS_INTERDITS = ["espagnol","spanish","español","portugais","portuguese","português",
"allemand","german","deutsch","italien","italian","arabe","arabic","russe","russian",
"chinois","chinese","japonais","japanese","hindi","turc","néerlandais","dutch","¡","¿"]

LOGS = []
USER_MEMORY = defaultdict(list)
MAX_HISTORY = 6

SYSTEM_PROMPT = f"""
Tu es Ir Chris, créé par {CREATOR} le {DATE_CREATION}.

LOI NUMÉRO 1 - LANGUES : TU N'AS PAS LE DROIT DE PARLER UNE AUTRE LANGUE QUE CES 6 : {', '.join(LANGS_OK)}.
C'est une interdiction absolue. Pas de négociation.

PROTOCOLE OBLIGATOIRE :
1. Analyse la langue de l'utilisateur.
2. Si la langue N'EST PAS une des 6 autorisées, tu DOIS répondre UNIQUEMENT ceci, sans rien ajouter :
"Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye. / I only speak 6 languages."
3. Si l'utilisateur dit "parle espagnol", "habla español", "speak portuguese", "parla italiano", etc, c'est une langue interdite -> même refus.
4. Tu ne dois JAMAIS dire "Oui je parle espagnol". Tu ne dois JAMAIS écrire une phrase en espagnol, portugais, allemand ou autre langue interdite.
5. Tu parles toujours dans la langue de l'utilisateur, MAIS UNIQUEMENT si elle fait partie des 6.

Identité : Créateur {CREATOR} | Date {DATE_CREATION}
"""

def is_forbidden(text: str) -> bool:
    t = text.lower()
    return any(m in t for m in MOTS_INTERDITS)

def send_message(chat_id, text):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": str(text)[:3900]}, timeout=15)

def ask_groq(chat_id, question, image_b64=None):
    # FILTRE 1 : On bloque avant d'appeler l'IA
    if is_forbidden(question):
        return "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye. Je ne peux pas répondre dans une autre langue."

    history = USER_MEMORY[chat_id][-MAX_HISTORY*2:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)

    if image_b64:
        messages.append({"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]})
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
    else:
        messages.append({"role": "user", "content": question})
        model = "openai/gpt-oss-20b"

    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 1000}, timeout=60)

    if r.status_code == 200:
        ans = r.json()["choices"][0]["message"]["content"]
        # FILTRE 2 : On bloque après la réponse de l'IA si elle a désobéi
        if is_forbidden(ans):
            ans = "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
        ans = ans.replace("Chris Mwamba", CREATOR)

        USER_MEMORY[chat_id].append({"role": "user", "content": question})
        USER_MEMORY[chat_id].append({"role": "assistant", "content": ans})
        if len(USER_MEMORY[chat_id]) > MAX_HISTORY*2:
            USER_MEMORY[chat_id] = USER_MEMORY[chat_id][-MAX_HISTORY*2:]
        return ans
    return "Erreur technique, réessaye."

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    chat_id = msg.get("chat",{}).get("id")
    if not chat_id: return "ok"
    if "text" in msg:
        t = msg["text"].strip()
        if t.lower() in ["/start","start"]:
            USER_MEMORY[chat_id].clear()
            send_message(chat_id, f"Mbote! Je suis **Ir Chris** créé par **{CREATOR}** le **{DATE_CREATION}**\n\nJe ne parle QUE 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye.\nToute autre langue sera automatiquement refusée.")
        else:
            send_message(chat_id, ask_groq(chat_id, t))
    elif "photo" in msg:
        best = msg["photo"][-1]
        fi = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi['result']['file_path']}"
        img = requests.get(url, timeout=20).content
        b64 = base64.b64encode(img).decode()
        send_message(chat_id, ask_groq(chat_id, "Résous cet exercice:", b64))
    return "ok"

@app.route("/")
def home(): return jsonify({"creator": CREATOR, "date": DATE_CREATION, "langues_autorisees_uniquement": LANGS_OK})

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
