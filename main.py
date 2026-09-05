import os, requests, datetime
from flask import Flask, request
app = Flask(__name__)

CREATOR = "Ir Chris Lubaki Tshiombo"
CREATION_DATE = "25/08/2026 à 03:01 à Lubumbashi"
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"
LOGS = []

def add_log(user, q, r):
    # Récupère le vrai nom du profil Telegram
    first = user.get('first_name','')
    last = user.get('last_name','')
    username = user.get('username','')
    full_name = f"{first} {last}".strip() or f"@{username}" or "Anonyme"
    LOGS.insert(0,{
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nom": full_name,
        "question": q,
        "reponse": r
    })
    if len(LOGS) > 100: LOGS.pop()

@app.route("/")
def home(): return f"Bot de {CREATOR} - {CREATION_DATE} - <a href='/setwebhook'>REVEILLER</a> - <a href='/admin'>ADMIN</a>"

@app.route("/setwebhook")
def setwebhook():
    if not BOT_TOKEN: return "TOKEN vide sur Render"
    r = requests.get(f"{BOT_API}/setWebhook?url=https://chris-bot-19jt.onrender.com/telegram/webhook")
    return r.text

@app.route("/admin")
def admin():
    rows = ""
    for l in LOGS:
        rows += f"<tr><td>{l['heure']}</td><td style='color:#38bdf8;font-weight:bold'>{l['nom']}</td><td>{l['question']}</td><td style='color:#22c55e'>{l['reponse'][:600]}</td></tr>"
    if not rows: rows = "<tr><td colspan=4 style='text-align:center'>Aucun message encore. Envoie un message sur Telegram.</td></tr>"
    return f"""
    <html><head><meta charset='utf-8'><style>
    body{{background:#0f172a;color:white;font-family:Arial;padding:20px}}
    table{{width:100%;border-collapse:collapse;background:#1e293b}}
    th{{background:#334155;padding:12px}} td{{padding:10px;border-bottom:1px solid #334155;vertical-align:top}}
    </style></head>
    <body>
    <h1>🤖 ADMIN - Créé par {CREATOR}</h1>
    <p>Date de création: {CREATION_DATE} | Total logs: {len(LOGS)}</p>
    <table><tr><th>Heure</th><th>Nom du Profil</th><th>Message Envoyé</th><th>Réponse de l'IA</th></tr>{rows}</table>
    <p><a href='/' style='color:#38bdf8'>Accueil</a> | <a href='/setwebhook' style='color:#38bdf8'>Reveiller le bot</a></p>
    </body></html>
    """

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    chat_id = msg.get("chat",{}).get("id")
    user = msg.get("from",{}) or {}
    q = msg.get("text","").strip()
    if not chat_id or not q: return "ok"

    first_name = user.get('first_name','ami').strip() or "ami"
    ql = q.lower()

    # Réponses directes sans Groq (pas d'hallucination)
    if any(x in ql for x in ["qui t'a créé","qui ta cree","who created you","nani alikupa","nani we","who made you"]):
        rep = f"J'ai été créé par {CREATOR} le {CREATION_DATE}."
    elif ql in ["/start","salut","bonjour","hello","mbote","jambo","moyo","oyo","salam"]:
        rep = f"Mbote {first_name}! 👋 Je suis Ir Chris, créé par {CREATOR} le {CREATION_DATE}. Je parle 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye. Comment puis-je t'aider?"
    else:
        # Appel Groq avec modèle 2026 qui marche
        if not GROQ_KEY:
            rep = f"Désolé {first_name}, GROQ_API_KEY manquant sur Render."
        else:
            try:
                system_prompt = f"""Tu es Ir Chris, un assistant intelligent créé par {CREATOR} le {CREATION_DATE}.

REGLES STRICTES (ne jamais violer):
1. Tu as été créé par {CREATOR} le {CREATION_DATE}. Ne dis jamais un autre créateur.
2. Tu parles UNIQUEMENT 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye. Si on te parle dans une autre langue (arabe, portugais, etc), réponds exactement: "Désolé {first_name}, je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
3. Tu t'adresses à l'utilisateur par son prénom: {first_name}
4. Pas d'hallucination. Réponds calmement, correctement, pas pressé. Si tu ne sais pas, dis que tu ne sais pas.
5. Tu es poli, respectueux, utile."""

                r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {GROQ_KEY}","Content-Type":"application/json"},
                    json={
                        "model": "openai/gpt-oss-20b",
                        "messages": [
                            {"role":"system","content": system_prompt},
                            {"role":"user","content": q}
                        ],
                        "temperature": 0.5,
                        "max_tokens": 800
                    },
                    timeout=30)

                if r.status_code == 200:
                    rep = r.json()["choices"][0]["message"]["content"].strip()
                else:
                    rep = f"Désolé {first_name}, petite panne technique ({r.status_code}). Réessaie dans 10 secondes."
                    # Log l'erreur complète dans admin
                    add_log(user, q, f"ERREUR GROQ {r.status_code}: {r.text[:500]}")
                    requests.post(f"{BOT_API}/sendMessage", json={"chat_id":chat_id,"text":rep}, timeout=10)
                    return "ok"

            except Exception as e:
                rep = f"Désolé {first_name}, connexion lente. Réessaie."

    add_log(user, q, rep)
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id":chat_id,"text":rep[:4000]}, timeout=10)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
