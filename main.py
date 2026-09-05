import os, requests, datetime
from flask import Flask, request
app = Flask(__name__)

CREATOR = "Ir Chris Lubaki Tshiombo"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOGS = []

def add_log(user, q, r):
    nom = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or f"@{user.get('username','Anonyme')}"
    LOGS.insert(0,{"heure":datetime.datetime.now().strftime("%d/%m %H:%M"),"nom":nom,"question":q,"reponse":r})
    if len(LOGS)>100: LOGS.pop()

@app.route("/")
def home():
    return f"Bot de {CREATOR} OK. <a href='/setwebhook'>CLIQUE ICI POUR REVEILLER LE BOT</a> | <a href='/admin'>ADMIN</a>"

@app.route("/setwebhook")
def setwebhook():
    if not BOT_TOKEN: return "ERREUR: TELEGRAM_BOT_TOKEN vide sur Render"
    url = f"https://chris-bot-19jt.onrender.com/telegram/webhook"
    r = requests.get(f"{BOT_API}/setWebhook?url={url}")
    return f"<h1>{r.text}</h1><p>Si tu vois ok:true, retourne sur Telegram et tape /start</p>"

@app.route("/admin")
def admin():
    rows="".join([f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td>{l['question']}</td><td>{l['reponse']}</td></tr>" for l in LOGS]) or "<tr><td colspan=4 style='text-align:center'>Pas encore de messages</td></tr>"
    return f"<body style='background:#0f172a;color:white;font-family:Arial;padding:20px'><h1>Admin - {CREATOR}</h1><p><a href='/admin' style='color:yellow'>Rafraichir</a> | <a href='/setwebhook' style='color:cyan'>Reveiller le bot</a></p><table border=1 cellpadding=10 style='width:100%;border-collapse:collapse;background:#1e293b'><tr style='background:#334155'><th>Heure</th><th>Nom</th><th>Question</th><th>Reponse</th></tr>{rows}</table></body>"

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data=request.get_json(force=True) or {}
    msg=data.get("message") or {}
    chat_id=msg.get("chat",{}).get("id")
    user=msg.get("from",{})
    q=msg.get("text","").strip()
    if not chat_id or not q: return "ok"
    ql=q.lower()
    if "qui t'a créé" in ql or "who created" in ql:
        rep=f"J'ai été créé par {CREATOR} le 25/08/2026 à Lubumbashi."
    elif ql in ["/start","salut","bonjour","hello","mbote","jambo"]:
        rep=f"Mbote {user.get('first_name','')}! Je suis Ir Chris, créé par {CREATOR}. Je parle 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye."
    else:
        try:
            sys=f"Tu es Ir Chris créé par {CREATOR} le 25/08/2026 à Lubumbashi. Parle UNIQUEMENT en Français, English, Swahili, Lingala, Kiluba, Kisongye."
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},json={"model":"llama-3.1-8b-instant","messages":[{"role":"system","content":sys},{"role":"user","content":q}]},timeout=20)
            rep=r.json()["choices"][0]["message"]["content"] if r.status_code==200 else f"Erreur Groq {r.status_code}"
        except Exception as e:
            rep=f"Connexion lente, réessaie. ({e})"
    add_log(user,q,rep)
    requests.post(f"{BOT_API}/sendMessage",json={"chat_id":chat_id,"text":rep[:4000]},timeout=10)
    return "ok"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
