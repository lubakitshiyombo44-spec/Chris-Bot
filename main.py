import os
import requests
import base64
import datetime
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= CONFIG =================
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "IrChris2026")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS_OK = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]

MEMORY = defaultdict(list)
LOGS = [] # Pour l'admin
MAX_HISTORY = 6

# ================= CERVEAU =================
SYSTEM_PROMPT = f"""
Tu es Ir Chris.
- Tu n'es PAS créé par OpenAI, Meta, Google.
- Créateur unique : {CREATOR}
- Date : {DATE_CREATION} - Lieu : {LIEU}
- Tu parles UNIQUEMENT ces 6 langues : {', '.join(LANGS_OK)}.
Si on te demande qui t'a créé : J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
Si on te parle en espagnol ou autre langue interdite : Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye.
"""

FORBIDDEN_LANGS = ["espagnol","spanish","español","portugais","portuguese","português","allemand","german","deutsch","italien","italian","arabe","arabic","russe","russian","chinois","chinese","japonais","¡","¿"]
IDENTITY_WORDS = ["qui t'a créé", "ton créateur", "who created you", "who is your creator", "c'est qui ton créateur"]

def is_forbidden_lang(text: str) -> bool:
    return any(w in text.lower() for w in FORBIDDEN_LANGS)

def is_identity(text: str) -> bool:
    return any(w in text.lower() for w in IDENTITY_WORDS)

def add_log(user_obj, question, answer):
    LOGS.insert(0, {
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "user": f"{user_obj.get('first_name','')} {user_obj.get('last_name','')}".strip() + f" (@{user_obj.get('username','')})",
        "user_id": user_obj.get('id',''),
        "question": question[:1000],
        "answer": answer[:1000]
    })
    if len(LOGS) > 1000:
        LOGS.pop()

def send(chat_id, text):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": text[:3800]}, timeout=15)

def get_answer(chat_id, user_obj, question, image_b64=None):
    if is_forbidden_lang(question):
        ans = "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye. Je ne peux pas répondre dans une autre langue."
        add_log(user_obj, question, ans)
        return ans

    if is_identity(question):
        ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU} 🇨🇩."
        add_log(user_obj, question, ans)
        return ans

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
            ans = "Bug serveur, réessaye."
            add_log(user_obj, question, ans)
            return ans

        ans = res.json()["choices"][0]["message"]["content"]
        if "openai" in ans.lower():
            ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}."
        ans = ans.replace("Chris Mwamba", CREATOR)

        MEMORY[chat_id].append({"role": "user", "content": question})
        MEMORY[chat_id].append({"role": "assistant", "content": ans})
        if len(MEMORY[chat_id]) > MAX_HISTORY*2:
            MEMORY[chat_id] = MEMORY[chat_id][-MAX_HISTORY*2:]

        add_log(user_obj, question, ans)
        return ans
    except Exception as e:
        print(e)
        ans = "Connexion lente."
        add_log(user_obj, question, ans)
        return ans

# ================= ROUTES =================
@app.route("/")
def home():
    return jsonify({"bot": "Ir Chris", "creator": CREATOR, "date": DATE_CREATION, "langues": LANGS_OK, "total_logs": len(LOGS)})

@app.route("/admin")
def admin():
    if request.args.get("key")!= ADMIN_KEY:
        return "Accès refusé. Ajoute?key=IrChris2026", 403

    html = f"""
    <html><head><title>Admin - {CREATOR}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
    body{{font-family:Arial;background:#0f172a;color:white;padding:20px}}
    h1{{color:#38bdf8}}.card{{background:#1e293b;padding:15px;border-radius:10px;margin-bottom:15px;border-left:4px solid #38bdf8}}
   .q{{color:#facc15;font-weight:bold}}.a{{color:#a7f3d0}}.meta{{color:#94a3b8;font-size:12px}}
    table{{width:100%}}.top{{display:flex;justify-content:space-between;align-items:center}}
    a{{color:#38bdf8}}
    </style></head><body>
    <div class="top"><h1>🤖 Panneau Admin - Ir Chris</h1><div>Créé par {CREATOR}<br>{DATE_CREATION} - {len(LOGS)} conversations</div></div>
    <p>Langues autorisées : {', '.join(LANGS_OK)} | <a href='/admin?key={ADMIN_KEY}&clear=1'>Vider les logs</a></p>
    """

    if request.args.get("clear") == "1":
        LOGS.clear()
        html += "<p style='color:lime'>Logs vidés.</p>"

    if not LOGS:
        html += "<p>Aucune question pour l'instant.</p>"
    else:
        for log in LOGS[:200]:
            html += f"""
            <div class="card">
                <div class="meta">{log['heure']} | {log['user']} | ID: {log['user_id']}</div>
                <div class="q">❓ Question : {log['question']}</div>
                <div class="a">🤖 Réponse : {log['answer']}</div>
            </div>
            """

    html += "</body></html>"
    return html

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")
    user = msg.get("from", {})
    if not chat_id: return "ok"

    if "text" in msg:
        t = msg["text"].strip()
        if t.lower() in ["/start", "start"]:
            MEMORY[chat_id].clear()
            send(chat_id, f"Mbote! 👋 Je suis Ir Chris\nCréé par {CREATOR} le {DATE_CREATION}\n\nJe parle uniquement : {', '.join(LANGS_OK)}")
        else:
            send(chat_id, get_answer(chat_id, user, t))
    elif "photo" in msg:
        best = msg["photo"][-1]
        file_info = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info['result']['file_path']}"
        img_bytes = requests.get(file_url, timeout=20).content
        b64 = base64.b64encode(img_bytes).decode()
        send(chat_id, get_answer(chat_id, user, "Résous cet exercice :", b64))
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
