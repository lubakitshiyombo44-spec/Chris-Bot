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
def home(): return f"Bot {CREATOR} OK <a href='/setwebhook'>Reveiller</a> <a href='/admin'>ADMIN</a>"

@app.route("/setwebhook")
def setwebhook():
    if not BOT_TOKEN: return "TOKEN vide"
    r = requests.get(f"{BOT_API}/setWebhook?url=https://chris-bot-19jt.onrender.com/telegram/webhook")
    return r.text

@app.route("/admin")
def admin():
    rows="".join([f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td>{l['question']}</td><td>{l['reponse'][:500]}</td></tr>" for l in LOGS]) or "<tr><td colspan=4>Aucun</td></tr>"
    return f"<body style='background:#0f172a;color:white;font-family:Arial;padding:20px'><h1>ADMIN</h1><table border=1 cellpadding=8 style='width:100%;background:#1e293b'><tr><th>Heure</th><th>Nom</th><th>Question</th><th>Reponse</th></tr>{rows}</table></body>"

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data=request.get_json(force=True) or {}
    msg=data.get("message") or {}
    chat_id=msg.get("chat",{}).get("id")
    user=msg.get("from",{})
    q=msg.get("text","").strip()
    if not chat_id or not q: return "ok"
    first_name = user.get('first_name','ami')
    ql=q.lower()

    if any(x in ql for x in ["qui t'a créé","who created"]):
        rep=f"J'ai été créé par {CREATOR} le 25/08/2026 à Lubumbashi."
    elif ql in ["/start","salut","bonjour","hello","mbote","jambo","moyo"]:
        rep=f"Mbote {first_name}! Je suis Ir Chris, créé par {CREATOR}. Je parle 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye."
    else:
        try:
            sys=f"Tu es Ir Chris créé par {CREATOR} le 25/08/2026 à Lubumbashi. Tu parles UNIQUEMENT Français, English, Swahili, Lingala, Kiluba, Kisongye. Si autre langue, réponds: Désolé {first_name}, je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
            # NOUVEAUX MODELES 2026
            r=requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization":f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                json={"model":"llama-3.3-70b-versatile","messages":[{"role":"system","content":sys},{"role":"user","content":q}],"temperature":0.6},
                timeout=25)
            if r.status_code==200:
                rep=r.json()["choices"][0]["message"]["content"]
            else:
                rep=f"Erreur Groq {r.status_code}: {r.text[:300]}"
        except Exception as e:
            rep=f"Connexion lente {e}"
    add_log(user,q,rep)
    requests.post(f"{BOT_API}/sendMessage",json={"chat_id":chat_id,"text":rep[:4000]},timeout=10)
    return "ok"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
