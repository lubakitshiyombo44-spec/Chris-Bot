import os, requests, datetime
from flask import Flask, request

app = Flask(__name__)

# --- TES INFOS OFFICIELLES ---
CREATOR = "Ir Chris Lubaki Tshiombo"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS_AUTORISEES = "Français, English, Swahili, Lingala, Kiluba, Kisongye"

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

LOGS = [] # Stocke les conversations

def add_log(user, question, reponse):
    nom_complet = f"{user.get('first_name','')} {user.get('last_name','')}".strip()
    if not nom_complet:
        nom_complet = f"@{user.get('username','Anonyme')}"
    LOGS.insert(0, {
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nom": nom_complet,
        "question": question,
        "reponse": reponse
    })
    if len(LOGS) > 100: LOGS.pop()

@app.route("/")
def home():
    return f"Bot de {CREATOR} est en ligne. Admin: /admin"

@app.route("/admin")
def admin():
    html_logs = ""
    for l in LOGS:
        html_logs += f"<tr><td>{l['heure']}</td><td><b>{l['nom']}</b></td><td>{l['question']}</td><td>{l['reponse']}</td></tr>"
    if not html_logs:
        html_logs = "<tr><td colspan=4 style='text-align:center'>Aucune conversation encore. Parlez au bot sur Telegram.</td></tr>"

    return f"""
    <html><head><title>Admin - {CREATOR}</title></head>
    <body style='background:#0f172a;color:white;font-family:Arial;padding:20px'>
    <h1>Panel Admin - {CREATOR}</h1>
    <p>Créé le {DATE_CREATION} à {LIEU} | Langues: {LANGS_AUTORISEES} | Total: {len(LOGS)} | <a href='/admin' style='color:yellow'>Rafraichir</a></p>
    <table border=1 cellpadding=10 style='width:100%;border-collapse:collapse;background:#1e293b'>
    <tr style='background:#334155'><th>Heure</th><th>Nom de la personne</th><th>Question posée</th><th>Réponse de l'IA</th></tr>
    {html_logs}
    </table></body></html>
    """

@app.route("/telegram/<path:p>", methods=["POST"])
def telegram_webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    chat_id = msg.get("chat",{}).get("id")
    user = msg.get("from",{})
    question = msg.get("text","").strip()
    if not chat_id or not question: return "ok"

    ql = question.lower()
    reponse = ""

    # 1. Qui t'a créé?
    if "qui t'a créé" in ql or "who created you" in ql or "nani alikuumba" in ql:
        reponse = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}."
    # 2. Start / Salut
    elif ql in ["/start", "salut", "hello", "mbote", "jambo"]:
        reponse = f"Mbote {user.get('first_name','')}! Je suis l'assistant de {CREATOR}. Je parle uniquement: {LANGS_AUTORISEES}. Pose ta question."
    # 3. Intelligence avec GROQ
    else:
        try:
            prompt_system = f"Tu es Ir Chris, une IA créée par {CREATOR} le {DATE_CREATION} à {LIEU}. Tu dois parler UNIQUEMENT dans ces 6 langues: {LANGS_AUTORISEES}. Si on te parle dans une autre langue, réponds poliment que tu ne parles que ces 6 langues. Ne parle jamais d'autre créateur."
            r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
                json={"model": "llama-3.1-8b-instant", "messages": [{"role": "system", "content": prompt_system}, {"role": "user", "content": question}]},
                timeout=20)
            if r.status_code == 200:
                reponse = r.json()["choices"][0]["message"]["content"]
            else:
                reponse = f"Erreur technique Groq ({r.status_code}). Vérifie ta clé GROQ_API_KEY sur Render."
        except Exception as e:
            reponse = f"Désolé, connexion lente. Réessaie. ({e})"

    add_log(user, question, reponse)
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": reponse[:4000]}, timeout=10)
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT",10000)))
