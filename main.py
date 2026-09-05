import os, requests, datetime
from flask import Flask, request
app = Flask(__name__)

CREATOR = "Ir Chris Lubaki Tshiombo"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOGS = []

# 6 langues autorisées
LANGS_AUTORISEES = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]
MESSAGE_REFUS = "Désolé {name}, je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye. Pose ta question dans une de ces langues."

def add_log(user, q, r):
    nom = f"{user.get('first_name','')} {user.get('last_name','')}".strip() or f"@{user.get('username','Anonyme')}"
    LOGS.insert(0,{"heure":datetime.datetime.now().strftime("%d/%m %H:%M"),"nom":nom,"question":q,"reponse":r})
    if len(LOGS)>100: LOGS.pop()

@app.route("/")
def home():
    return f"Bot de {CREATOR} OK | <a href='/setwebhook'>REVEILLER</a> | <a href='/admin'>ADMIN</a>"

@app.route("/setwebhook")
def setwebhook():
    if not BOT_TOKEN: return "ERREUR: TELEGRAM_BOT_TOKEN vide sur Render"
    r = requests.get(f"{BOT_API}/setWebhook?url=https://chris-bot-19jt.onrender.com/telegram/webhook")
    return r.text

@app.route("/admin")
def admin():
    rows="".join([f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td>{l['question']}</td><td>{l['reponse'][:400]}</td></tr>" for l in LOGS]) or "<tr><td colspan=4 style='text-align:center'>Aucun message encore</td></tr>"
    return f"""
    <body style='background:#0f172a;color:white;font-family:Arial;padding:20px'>
    <h1>📊 ADMIN - Bot de {CREATOR}</h1>
    <p><a href='/admin' style='color:yellow'>🔄 Rafraichir</a> | <a href='/setwebhook' style='color:cyan'>⚡ Reveiller bot</a></p>
    <table border=1 cellpadding=10 style='width:100%;border-collapse:collapse;background:#1e293b'>
    <tr style='background:#334155'><th>Heure</th><th>Nom Personne</th><th>Question</th><th>Réponse du bot</th></tr>
    {rows}
    </table></body>"""

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data=request.get_json(force=True) or {}
    msg=data.get("message") or {}
    chat_id=msg.get("chat",{}).get("id")
    user=msg.get("from",{})
    q=msg.get("text","").strip()
    if not chat_id or not q: return "ok"

    first_name = user.get('first_name','ami')
    ql = q.lower()

    # 1. Qui t'a créé?
    if any(x in ql for x in ["qui t'a créé","qui t'a cree","who created you","nani alikupang","nani akelaki","ani wakubumba"]):
        rep = f"J'ai été créé par {CREATOR} le 25/08/2026 à Lubumbashi."

    # 2. Salutations -> salue avec le nom Telegram
    elif ql in ["/start","salut","bonjour","hello","mbote","jambo","moyo","salam","habari","bote"]:
        rep = f"Mbote {first_name}! Je suis Ir Chris, créé par {CREATOR}. Je parle 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye."

    else:
        if not GROQ_KEY:
            rep = "Mon cerveau n'est pas configuré (GROQ_API_KEY manquant sur Render)."
        else:
            try:
                # Instruction stricte pour les 6 langues uniquement
                system_prompt = f"""
Tu es Ir Chris, un assistant créé par {CREATOR} le 25/08/2026 à Lubumbashi.
REGLE ABSOLUE: Tu ne parles QUE 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye.
Si l'utilisateur parle une AUTRE langue (espagnol, portugais, arabe, chinois etc), tu dois répondre EXACTEMENT ceci: "Désolé {first_name}, je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
Ne jamais répondre dans une autre langue. Sois bref, chaleureux, et salue toujours par le prénom {first_name} si possible.
"""
                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                    json={
                        "model":"llama-3.3-70b-versatile",
                        "messages":[{"role":"system","content":system_prompt},{"role":"user","content":q}],
                        "temperature":0.6
                    }, timeout=25)
                if r.status_code==200:
                    rep = r.json()["choices"][0]["message"]["content"]
                else:
                    rep = f"Désolé {first_name}, petite panne ({r.status_code}), réessaie."
            except Exception as e:
                rep = f"Désolé {first_name}, connexion lente, réessaie."

    add_log(user, q, rep)
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id":chat_id,"text":rep[:4000]}, timeout=10)
    return "ok"

if __name__=="__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT",10000)))
