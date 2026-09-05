import os
import requests
import base64
import datetime
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# ============ CONFIG ============
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "IrChris2026")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS_OK = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]

MEMORY = defaultdict(list)
LOGS = [] # Ici on stocke tout pour l'admin

SYSTEM_PROMPT = f"""
Tu es Ir Chris, créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
Tu n'es PAS créé par OpenAI.
Tu parles UNIQUEMENT ces 6 langues : {', '.join(LANGS_OK)}.
Si on te parle en espagnol ou autre langue interdite, tu refuses : Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye.
Si on te demande qui t'a créé, tu réponds : J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
"""

# ============ FONCTIONS ============
def add_log(user, question, answer):
    LOGS.insert(0, {
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nom": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
        "username": f"@{user.get('username','')}" if user.get('username') else "",
        "question": question,
        "reponse": answer
    })
    if len(LOGS) > 1000:
        LOGS.pop()

def send(chat_id, text):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": text[:3900]}, timeout=15)

def get_answer(chat_id, user, question, image_b64=None):
    # Bloque les autres langues
    if any(w in question.lower() for w in ["espagnol","spanish","español","portuguais","portuguese","allemand","german"]):
        ans = "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
        add_log(user, question, ans)
        return ans

    # Bloque le mensonge OpenAI - réponse directe
    if "qui t'a créé" in question.lower() or "who created you" in question.lower() or "ton créateur" in question.lower():
        ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU} 🇨🇩."
        add_log(user, question, ans)
        return ans

    history = MEMORY[chat_id][-12:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": question}]
    model = "openai/gpt-oss-20b"

    if image_b64:
        messages[-1] = {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}
        model = "meta-llama/llama-4-scout-17b-16e-instruct"

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 1000}, timeout=60)

        ans = r.json()["choices"][0]["message"]["content"] if r.status_code == 200 else "Erreur serveur."
        if "openai" in ans.lower():
            ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION}."
        ans = ans.replace("Chris Mwamba", CREATOR)

        MEMORY[chat_id].append({"role": "user", "content": question})
        MEMORY[chat_id].append({"role": "assistant", "content": ans})

        add_log(user, question, ans)
        return ans
    except:
        ans = "Connexion lente, réessaye."
        add_log(user, question, ans)
        return ans

# ============ ROUTES ============
@app.route("/")
def home():
    return jsonify({"bot": "Ir Chris", "creator": CREATOR, "date": DATE_CREATION, "total_chats": len(LOGS)})

@app.route("/admin")
@app.route("/admin/")
def admin_panel():
    # Pour sécuriser, tu peux remettre le test de clé après. Pour l'instant on laisse ouvert pour que tu testes.
    # if request.args.get("key")!= ADMIN_KEY: return "Accès refusé", 403

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Admin - {CREATOR}</title>
        <style>
            body{{background:#0f172a;color:white;font-family:Arial;padding:20px}}
            h1{{color:#38bdf8}}
            table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden}}
            th{{background:#334155;color:#38bdf8;padding:12px;text-align:left}}
            td{{padding:12px;border-bottom:1px solid #334155;vertical-align:top}}
            tr:hover{{background:#2d3748}}
           .q{{color:#fde047}}.r{{color:#86efac}}.h{{color:#94a3b8;font-size:12px}}.n{{color:white;font-weight:bold}}
           .top{{display:flex;justify-content:space-between;flex-wrap:wrap}}
        </style>
    </head>
    <body>
        <div class="top">
            <h1>🤖 Panneau Admin - Ir Chris</h1>
            <div>Créateur: {CREATOR}<br>Date: {DATE_CREATION}<br>Total: {len(LOGS)} chats</div>
        </div>
        <p><a href="/admin" style="color:#38bdf8">🔄 Rafraîchir</a> | Langues: {', '.join(LANGS_OK)}</p>
        <table>
            <tr><th>Heure</th><th>Nom de la personne</th><th>Question</th><th>Réponse de l'IA</th></tr>
    """

    if not LOGS:
        html += "<tr><td colspan='4' style='text-align:center;color:orange'>Aucune conversation encore. Parle à ton bot sur Telegram.</td></tr>"
    else:
        for log in LOGS[:300]:
            html += f"""
            <tr>
                <td class="h">{log['heure']}</td>
                <td class="n">{log['nom']}<br><span class="h">{log['username']}</span></td>
                <td class="q">{log['question']}</td>
                <td class="r">{log['reponse']}</td>
            </tr>
            """

    html += "</table></body></html>"
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
            send(chat_id, f"Mbote! Je suis Ir Chris créé par {CREATOR} le {DATE_CREATION}\n6 langues: {', '.join(LANGS_OK)}")
        else:
            send(chat_id, get_answer(chat_id, user, t))
    elif "photo" in msg:
        best = msg["photo"][-1]
        fi = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi['result']['file_path']}"
        b64 = base64.b64encode(requests.get(url, timeout=20).content).decode()
        send(chat_id, get_answer(chat_id, user, "Résous:", b64))
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
