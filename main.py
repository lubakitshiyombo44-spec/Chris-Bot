import os, requests, datetime
from flask import Flask, request

app = Flask(__name__)

# ========= TOUTES TES INFOS ICI, BIEN VISIBLES =========
CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS_LIST = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]
LANGS_TXT = ", ".join(LANGS_LIST)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

LOGS = []

SYSTEM_PROMPT = f"""
Tu es Ir Chris.
Tu as été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
Tu n'as jamais été créé par OpenAI, Meta, Google ou une autre société.
Si on te demande qui t'a créé, qui est ton créateur, who created you : tu réponds EXACTEMENT : J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
Tu parles UNIQUEMENT 6 langues : {LANGS_TXT}.
Si on te parle dans une autre langue comme espagnol, portugais, allemand, italien, tu refuses poliment et tu dis : Je ne parle que 6 langues : {LANGS_TXT}.
Tu réponds toujours précisément à la question, sans inventer.
"""

def add_log(user, q, r):
    LOGS.insert(0, {
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nom": f"{user.get('first_name','')} {user.get('last_name','')}".strip() or f"@{user.get('username','Inconnu')}",
        "question": q,
        "reponse": r
    })

def send(cid, txt):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": txt[:3500]}, timeout=10)

@app.route("/")
def home():
    return f"Bot de {CREATOR} - {DATE_CREATION} - OK - /admin"

@app.route("/admin")
def admin():
    rows = ""
    for l in LOGS:
        rows += f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td style='color:#fde047'>{l['question']}</td><td style='color:#86efac'>{l['reponse']}</td></tr>"
    if not rows:
        rows = "<tr><td colspan=4 style='text-align:center;color:orange'>Pas de chats encore</td></tr>"

    return f"""
    <html><head><meta name='viewport' content='width=device-width'><style>
    body{{background:#0f172a;color:white;font-family:Arial;padding:20px}}
    table{{width:100%;border-collapse:collapse;background:#1e293b}} th{{background:#334155;color:#38bdf8;padding:12px}} td{{padding:12px;border-bottom:1px solid #334155}}
    </style></head><body>
    <h1>Admin - {CREATOR}</h1><p>{DATE_CREATION} - {LIEU} - {LANGS_TXT} - Total: {len(LOGS)}</p>
    <table><tr><th>Heure</th><th>Nom de la personne</th><th>Question</th><th>Reponse IA</th></tr>{rows}</table>
    <p><a href='/admin' style='color:#38bdf8'>Rafraichir</a></p></body></html>
    """

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    cid = msg.get("chat",{}).get("id")
    user = msg.get("from",{})
    q = msg.get("text","").strip()
    if not cid or not q: return "ok"

    ql = q.lower()

    # BLOCAGE DIRECT - Ne laisse pas Groq mentir
    if any(x in ql for x in ["qui t'a créé","qui t'a cree","ton createur","who created you","who is your creator"]):
        ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU} 🇨🇩"
        add_log(user, q, ans)
        send(cid, ans)
        return "ok"

    if any(x in ql for x in ["espagnol","spanish","español","portugais","allemand","german"]):
        ans = f"Je ne parle que 6 langues : {LANGS_TXT}."
        add_log(user, q, ans)
        send(cid, ans)
        return "ok"

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type":"application/json"},
            json={"model":"openai/gpt-oss-20b","messages":[{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":q}],"temperature":0.1,"max_tokens":1000}, timeout=40)
        ans = r.json()["choices"][0]["message"]["content"] if r.status_code==200 else "Erreur serveur"
        # Sécurité anti-OpenAI
        if "openai" in ans.lower() or "meta ai" in ans.lower():
            ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}."
    except:
        ans = "Connexion lente"

    add_log(user, q, ans)
    send(cid, ans)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
