import os, requests, base64, datetime
from flask import Flask, request, jsonify

app = Flask(__name__)

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or os.getenv("GROQ") or "").strip()
ADMIN_KEY = os.getenv("ADMIN_KEY", "IrChris2026") # Change le mot de passe si tu veux
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

# --- STOCKAGE DES QUESTIONS ---
LOGS = [] # Mémoire (max 500)

SYSTEM_PROMPT = """
Tu es Ir Chris, créé par Ir Chris jeune congolais de Lubumbashi.
Langues: Français, English, Swahili, Lingala, Kiluba, Kisongye.
Réponds toujours dans la langue de l'utilisateur.
"""

def send_message(chat_id, text):
    try:
        for i in range(0, len(str(text)), 4000):
            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": str(text)[i:i+4000]}, timeout=15)
    except: pass

def ask_groq(text, image_b64=None):
    if not GROQ_KEY: return "GROQ_KEY manquante"
    headers = {"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"}
    if image_b64:
        payload = {"model": "meta-llama/llama-4-scout-17b-16e-instruct", "messages": [{"role":"user","content":[{"type":"text","text":text},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{image_b64}"}}]}]}
    else:
        payload = {"model": "openai/gpt-oss-20b", "messages": [{"role":"system","content":SYSTEM_PROMPT},{"role":"user","content":text}]}
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=60)
        if r.status_code==200:
            return r.json()["choices"][0]["message"]["content"]
        return f"Erreur {r.status_code}"
    except Exception as e:
        return f"Erreur: {e}"

def add_log(user, question):
    try:
        log = {
            "heure": datetime.datetime.now().strftime("%d/%m %H:%M:%S"),
            "user": user.get("first_name","") + " " + user.get("last_name","") if user else "Inconnu",
            "username": "@" + user.get("username","") if user and user.get("username") else "Pas de @",
            "id": user.get("id",""),
            "question": question[:500]
        }
        LOGS.insert(0, log)
        if len(LOGS) > 500: LOGS.pop()
        print(f"LOG: {log}") # Aussi dans les logs Render
    except: pass

@app.route("/")
def home():
    return jsonify({"status":"Ir Chris - En ligne", "bot":"@IrChrisLubumbashiBot", "admin_link":"/admin?key="+ADMIN_KEY})

# --- TON LIEN ADMIN ---
@app.route("/admin")
def admin():
    key = request.args.get("key","")
    if key!= ADMIN_KEY:
        return "Accès refusé. Ajoute?key=IrChris2026", 403

    html = f"""
    <html><head><meta charset='utf-8'><title>Admin Ir Chris</title>
    <style>
    body{{font-family:Arial;background:#111;color:#fff;padding:20px}}
    table{{width:100%;border-collapse:collapse;background:#222}}
    th,td{{border:1px solid #444;padding:10px;text-align:left}}
    th{{background:#0a84ff}}
    tr:nth-child(even){{background:#2a2a2a}}
   .header{{background:linear-gradient(90deg,#007AFF,#00C6FF);padding:20px;border-radius:10px;margin-bottom:20px}}
    </style></head><body>
    <div class='header'><h1>🇨🇩 Ir Chris - Panneau Admin</h1><p>Bot: @IrChrisLubumbashiBot | Total: {len(LOGS)} questions</p></div>
    <table><tr><th>Heure</th><th>Nom</th><th>Username</th><th>ID</th><th>Question posée</th></tr>
    """
    for l in LOGS:
        html += f"<tr><td>{l['heure']}</td><td>{l['user']}</td><td>{l['username']}</td><td>{l['id']}</td><td>{l['question']}</td></tr>"

    if not LOGS:
        html += "<tr><td colspan=5>Aucune question pour l'instant. Envoie /start dans le bot.</td></tr>"

    html += "</table><br><a href='' onclick='location.reload()' style='color:#0a84ff'>🔄 Actualiser</a></body></html>"
    return html

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    try:
        data=request.get_json(force=True) or {}
        msg=data.get("message") or {}
        chat_id=msg.get("chat",{}).get("id")
        user=msg.get("from",{})
        if not chat_id: return "ok"

        if "text" in msg:
            t=msg["text"]
            add_log(user, t) # <-- ON ENREGISTRE ICI
            if t=="/start":
                send_message(chat_id,"Mbote! 👋\n\nJe suis **Ir Chris**\nCréé par Ir Chris, jeune congolais de Lubumbashi 🇨🇩\n\n✅ 6 langues: Français, English, Swahili, Lingala, Kiluba, Kisongye\n✅ Photos d'exercices\n\nEnvoie ce que tu veux!")
            else:
                send_message(chat_id, ask_groq(t))
        elif "photo" in msg:
            add_log(user, "📸 A envoyé une PHOTO d'exercice")
            send_message(chat_id,"🖼️ Photo reçue...")
            best=msg["photo"][-1]
            fi=requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
            url=f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi['result']['file_path']}"
            img=requests.get(url, timeout=20).content
            b64=base64.b64encode(img).decode()
            send_message(chat_id, ask_groq("Résous cet exercice étape par étape:", b64))
        return "ok"
    except Exception as e:
        print(e); return "ok"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
