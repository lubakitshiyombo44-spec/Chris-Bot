import os, requests, datetime
from flask import Flask, request

app = Flask(__name__)

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS = "Français, English, Swahili, Lingala, Kiluba, Kisongye"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

LOGS = []

def add_log(user, q, r):
    nom = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or f"@{user.get('username','')}"
    LOGS.insert(0, {"heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"), "nom": nom, "question": q, "reponse": r})

@app.route("/")
def home(): return f"Bot {CREATOR} OK - <a href='/admin'>ADMIN</a>"

@app.route("/admin")
def admin():
    rows = "".join([f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td style='color:yellow'>{l['question']}</td><td style='color:#86efac'>{l['reponse']}</td></tr>" for l in LOGS])
    if not rows: rows = "<tr><td colspan=4>Pas de messages</td></tr>"
    return f"<html><body style='background:#0f172a;color:white;font-family:Arial;padding:20px'><h1>Admin - {CREATOR}</h1><p>{DATE} - {LIEU} - Total:{len(LOGS)} <a href='/admin'>Rafraichir</a></p><table border=1 style='width:100%;background:#1e293b'><tr><th>Heure</th><th>Nom de la personne</th><th>Question</th><th>Reponse</th></tr>{rows}</table></body></html>"

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    cid = msg.get("chat",{}).get("id")
    user = msg.get("from",{})
    q = msg.get("text","").strip()
    if not cid or not q: return "ok"

    ql = q.lower()

    # REPONSES DIRECTES SANS GROQ - pour ne plus avoir Erreur serveur
    if ql in ["/start", "salut", "bonjour", "hello"]:
        ans = f"Mbote {user.get('first_name','')} 👋 Je suis Ir Chris, créé par {CREATOR} le {DATE} à {LIEU}. Je parle: {LANGS}."
    elif "qui t'a créé" in ql or "who created" in ql:
        ans = f"J'ai été créé par {CREATOR} le {DATE} à {LIEU} 🇨🇩"
    elif "importance" in ql:
        ans = "Mon importance est d'être un assistant conversationnel créé par Ir Chris LUBAKI pour répondre dans les 6 langues autorisées."
    else:
        # APPEL GROQ CORRIGE
        try:
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={
                    "model": "llama-3.1-8b-instant",
                    "messages": [
                        {"role": "system", "content": f"Tu es Ir Chris cree par {CREATOR}. Tu parles seulement {LANGS}."},
                        {"role": "user", "content": q}
                    ]
                }, timeout=20)
            if r.status_code == 200:
                ans = r.json()["choices"][0]["message"]["content"]
            else:
                ans = f"Erreur Groq {r.status_code}: Verifie ta GROQ_API_KEY sur Render. Details: {r.text[:200]}"
        except Exception as e:
            ans = f"Connexion lente: {e}"

    add_log(user, q, ans)
    # ENVOI TELEGRAM OBLIGATOIRE
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": ans[:3500]}, timeout=10)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
