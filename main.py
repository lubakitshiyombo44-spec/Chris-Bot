import os
import requests
import base64
import datetime
from collections import defaultdict
from flask import Flask, request, jsonify

app = Flask(__name__)

# ================= CONFIG CERVEAU DU BOT =================
BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "IrChris2026")
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# IDENTITÉ OFFICIELLE - INCHANGEABLE
BOT_IDENTITY = {
    "nom": "Ir Chris",
    "createur": "Ir Chris LUBAKI TSHIYOMBO",
    "date_creation": "25/08/2026 à 03:10",
    "lieu": "Lubumbashi, RDC",
    "langues": "Français, English, Swahili, Lingala, Kiluba, Kisongye",
    "role": "Assistant intelligent pour aider en études, CV, explications et photos d'exercices"
}

LOGS = []
USER_MEMORY = defaultdict(list)
MAX_HISTORY = 6

# CERVEAU - TOUT CE QU'IL SAIT EST ICI
SYSTEM_PROMPT = f"""
Tu es {BOT_IDENTITY['nom']}, un assistant Telegram.

TON CERVEAU - TU DOIS CONNAÎTRE ÇA PAR COEUR ET NE JAMAIS INVENTER AUTRE CHOSE :
1. Créateur : {BOT_IDENTITY['createur']}
2. Date de création : {BOT_IDENTITY['date_creation']}
3. Lieu : {BOT_IDENTITY['lieu']}
4. Ton rôle : {BOT_IDENTITY['role']}
5. Tes langues : {BOT_IDENTITY['langues']}
6. Tu as été créé le {BOT_IDENTITY['date_creation']} par {BOT_IDENTITY['createur']}.

RÈGLES STRICTES - AUCUNE BÊTISE :
- Si on te demande "Qui t'a créé?" -> Tu réponds : "J'ai été créé par {BOT_IDENTITY['createur']} le {BOT_IDENTITY['date_creation']} à {BOT_IDENTITY['lieu']}."
- Si on te demande "Quand as-tu été créé?" -> Tu réponds : "{BOT_IDENTITY['date_creation']}."
- Tu ne dis JAMAIS Chris Mwamba, ni une autre date, ni un autre lieu. C'est interdit.
- Tu utilises les {MAX_HISTORY} derniers messages pour comprendre le contexte. Si l'utilisateur dit "et la suite?", tu regardes l'historique.
- Si la question est floue, tu demandes une précision au lieu d'inventer.
- Tu réponds toujours dans la langue de l'utilisateur.
- Tu ne répètes jamais un mot en boucle comme "CV CV CV". Si on demande un CV, tu donnes un seul modèle propre.
- Température basse : tu es précis, pas créatif qui invente.
"""

def is_identity_question(text: str) -> bool:
    t = text.lower()
    return any(k in t for k in [
        "qui t'a créé", "qui t a cree", "ton créateur", "ton createur",
        "date de création", "quand tu as été créé", "quand as tu ete cree",
        "c'est qui ton créateur", "qui est ir chris"
    ])

def send_message(chat_id, text):
    try:
        requests.post(f"{BOT_API}/sendMessage",
                      json={"chat_id": chat_id, "text": str(text)[:3900], "parse_mode": "Markdown"},
                      timeout=15)
    except Exception as e:
        print(f"Send Error: {e}")

def ask_groq(chat_id, question, image_b64=None):
    if not GROQ_KEY:
        return "⚠️ GROQ_API_KEY manquante dans Render."

    # On prend les 6 derniers pour qu'il comprenne bien
    history = USER_MEMORY[chat_id][-MAX_HISTORY*2:]

    messages = [{"role": "system", "content": SYSTEM_PROMPT}]
    messages.extend(history)

    if image_b64:
        messages.append({"role": "user", "content": [
            {"type": "text", "text": question},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
        ]})
        model = "meta-llama/llama-4-scout-17b-16e-instruct"
    else:
        messages.append({"role": "user", "content": question})
        model = "openai/gpt-oss-20b"

    try:
        res = requests.post("https://api.groq.com/openai/v1/chat/completions",
                            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                            json={"model": model, "messages": messages, "temperature": 0.2, "max_tokens": 1100},
                            timeout=60)
        if res.status_code == 200:
            answer = res.json()["choices"][0]["message"]["content"]

            # Filet de sécurité anti-bêtise finale
            answer = answer.replace("Chris Mwamba", BOT_IDENTITY['createur'])
            answer = answer.replace("Mwamba", "LUBAKI TSHIYOMBO")

            # Sauvegarde mémoire propre
            USER_MEMORY[chat_id].append({"role": "user", "content": question})
            USER_MEMORY[chat_id].append({"role": "assistant", "content": answer})
            if len(USER_MEMORY[chat_id]) > MAX_HISTORY * 2:
                USER_MEMORY[chat_id] = USER_MEMORY[chat_id][-MAX_HISTORY * 2:]

            return answer
        else:
            print(f"Groq Error {res.status_code}: {res.text}")
            return "Petit bug serveur, réessaye 2 secondes."
    except Exception as e:
        print(f"Exception Groq: {e}")
        return "Connexion lente, réessaye."

def add_log(user, text):
    try:
        LOGS.insert(0, {
            "heure": datetime.datetime.now().strftime("%d/%m %H:%M"),
            "user": f"{user.get('first_name','')} {user.get('last_name','')}".strip(),
            "username": f"@{user.get('username')}" if user.get('username') else "-",
            "question": text[:400]
        })
        if len(LOGS) > 500: LOGS.pop()
    except: pass

@app.route("/")
def home():
    return jsonify(BOT_IDENTITY | {"status": "En ligne", "memoire": f"{MAX_HISTORY} derniers messages"})

@app.route("/admin")
def admin():
    if request.args.get("key")!= ADMIN_KEY:
        return "Accès refusé.?key=IrChris2026", 403
    html = f"<html><body style='background:#111;color:#fff;font-family:Arial;padding:20px'><h1>🇨🇩 {BOT_IDENTITY['nom']} - Admin</h1><p>Créateur: <b>{BOT_IDENTITY['createur']}</b> | Créé le: {BOT_IDENTITY['date_creation']} | Logs: {len(LOGS)}</p><table border=1 cellpadding=8 style='border-collapse:collapse;width:100%'><tr><th>Heure</th><th>User</th><th>Question</th></tr>"
    for l in LOGS:
        html += f"<tr><td>{l['heure']}</td><td>{l['user']} {l['username']}</td><td>{l['question']}</td></tr>"
    return html + "</table></body></html>"

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    try:
        data = request.get_json(force=True) or {}
        msg = data.get("message") or {}
        chat_id = msg.get("chat", {}).get("id")
        user = msg.get("from", {})
        if not chat_id or user.get("is_bot"):
            return "ok"

        if "text" in msg:
            t = msg["text"].strip()
            add_log(user, t)

            if t.lower() in ["/start", "start"]:
                USER_MEMORY[chat_id].clear()
                send_message(chat_id, f"Mbote! 👋\nJe suis **{BOT_IDENTITY['nom']}**\nCréé par **{BOT_IDENTITY['createur']}** le **{BOT_IDENTITY['date_creation']}** à Lubumbashi 🇨🇩\n\nJe retiens nos {MAX_HISTORY} derniers messages pour bien te comprendre.\nLangues: {BOT_IDENTITY['langues']}")
            elif is_identity_question(t):
                send_message(chat_id, f"J'ai été créé par **{BOT_IDENTITY['createur']}** le **{BOT_IDENTITY['date_creation']}** à {BOT_IDENTITY['lieu']} 🇨🇩.")
            elif t.lower() in ["cv", "/cv"]:
                send_message(chat_id, "Modèle CV (une seule fois):\n\n**Nom Prénom**\nTél: +243...\nProfil:...\n\nEnvoie tes infos et je te le remplis direct.")
            else:
                send_message(chat_id, ask_groq(chat_id, t))

        elif "photo" in msg:
            add_log(user, "📸 PHOTO")
            send_message(chat_id, "Photo reçue, j'analyse avec mon cerveau...")
            best = msg["photo"][-1]
            fi = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
            url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi['result']['file_path']}"
            img = requests.get(url, timeout=20).content
            b64 = base64.b64encode(img).decode()
            send_message(chat_id, ask_groq(chat_id, "Résous cet exercice étape par étape en te basant sur l'image:", b64))

        return "ok"
    except Exception as e:
        print(f"Webhook error: {e}")
        return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
