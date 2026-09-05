import os, requests, base64, datetime
from collections import defaultdict
from flask import Flask, request

app = Flask(__name__)

BOT_TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("BOT_TOKEN") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or "").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

CREATOR = "Ir Chris LUBAKI TSHIYOMBO"
DATE_CREATION = "25/08/2026 à 03:10"
LIEU = "Lubumbashi, RDC"
LANGS = ["Français", "English", "Swahili", "Lingala", "Kiluba", "Kisongye"]

MEMORY = defaultdict(list)
LOGS = []
MAX_MEMORY = 6

SYSTEM_PROMPT = f"""
Tu es Ir Chris.
Créateur: {CREATOR}
Date de création: {DATE_CREATION}
Lieu: {LIEU}
Tu parles UNIQUEMENT ces 6 langues: {', '.join(LANGS)}.
RÈGLES STRICTES:
- Tu réponds EXACTEMENT à la question posée, sans inventer.
- Si on te demande qui t'a créé: Tu réponds: J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}.
- Tu n'es jamais créé par OpenAI, Meta ou Google.
- Si on te parle en espagnol, portugais, allemand ou autre langue hors des 6: Tu refuses poliment: Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye.
"""

def add_log(user, question, reponse):
    LOGS.insert(0, {
        "heure": datetime.datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "nom": f"{user.get('first_name','')} {user.get('last_name','')}".strip() or "Anonyme",
        "question": question,
        "reponse": reponse
    })
    if len(LOGS) > 1000: LOGS.pop()

def send(cid, text):
    requests.post(f"{BOT_API}/sendMessage", json={"chat_id": cid, "text": text[:3900]}, timeout=15)

def get_answer(cid, user, question, image_b64=None):
    q_low = question.lower()

    # Filtre 1: Identité - on ne laisse pas Groq mentir
    if any(x in q_low for x in ["qui t'a créé", "qui t'a cree", "ton créateur", "who created you", "who is your creator"]):
        ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU} 🇨🇩."
        add_log(user, question, ans)
        return ans

    # Filtre 2: Langues interdites
    if any(x in q_low for x in ["espagnol", "spanish", "español", "portugais", "portuguese", "allemand", "german", "italien", "italian"]):
        ans = "Je ne parle que 6 langues : Français, English, Swahili, Lingala, Kiluba, Kisongye."
        add_log(user, question, ans)
        return ans

    history = MEMORY[cid][-MAX_MEMORY*2:]
    messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history + [{"role": "user", "content": question}]
    model = "openai/gpt-oss-20b"

    if image_b64:
        messages[-1] = {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}]}
        model = "meta-llama/llama-4-scout-17b-16e-instruct"

    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": model, "messages": messages, "temperature": 0.1, "max_tokens": 1000}, timeout=60)

        if r.status_code!= 200:
            ans = "Erreur serveur, réessaye."
            add_log(user, question, ans)
            return ans

        ans = r.json()["choices"][0]["message"]["content"]

        # Sécurité anti-hallucination OpenAI
        if "openai" in ans.lower():
            ans = f"J'ai été créé par {CREATOR} le {DATE_CREATION} à {LIEU}."
        ans = ans.replace("Chris Mwamba", CREATOR)

        MEMORY[cid].append({"role": "user", "content": question})
        MEMORY[cid].append({"role": "assistant", "content": ans})
        if len(MEMORY[cid]) > MAX_MEMORY*2:
            MEMORY[cid] = MEMORY[cid][-MAX_MEMORY*2:]

        add_log(user, question, ans)
        return ans
    except Exception as e:
        print(e)
        ans = "Connexion lente, réessaye."
        add_log(user, question, ans)
        return ans

@app.route("/")
def home():
    return f"Bot de {CREATOR} actif - {DATE_CREATION} - {len(LOGS)} logs - /admin pour le panneau"

@app.route("/admin")
def admin():
    html = f"""
    <html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1">
    <title>Admin - {CREATOR}</title>
    <style>
        body{{background:#0f172a;color:#fff;font-family:Arial;padding:20px}}
        h1{{color:#38bdf8}} table{{width:100%;border-collapse:collapse;background:#1e293b;border-radius:10px;overflow:hidden}}
        th{{background:#334155;color:#38bdf8;padding:12px;text-align:left}} td{{padding:12px;border-bottom:1px solid #334155;vertical-align:top}}
      .q{{color:#fde047}}.r{{color:#86efac}}.n{{font-weight:bold}}.h{{font-size:12px;color:#94a3b8}}
    </style></head><body>
    <h1>🤖 Panneau Admin</h1>
    <p><b>Créateur:</b> {CREATOR}<br><b>Date:</b> {DATE_CREATION} - {LIEU}<br><b>Total:</b> {len(LOGS)} conversations<br><b>Langues:</b> {', '.join(LANGS)}</p>
    <table><tr><th>Heure</th><th>Nom de la personne</th><th>Question posée</th><th>Réponse de l'IA</th></tr>
    """
    if not LOGS:
        html += "<tr><td colspan=4 style='text-align:center;color:orange'>Aucune question encore. Parle à ton bot sur Telegram puis actualise.</td></tr>"
    else:
        for l in LOGS:
            html += f"<tr><td class=h>{l['heure']}</td><td class=n>{l['nom']}</td><td class=q>{l['question']}</td><td class=r>{l['reponse']}</td></tr>"
    html += "</table><p><a href='/admin' style='color:#38bdf8'>🔄 Rafraîchir</a></p></body></html>"
    return html

@app.route("/telegram/<path:p>", methods=["POST"])
def webhook(p):
    data = request.get_json(force=True) or {}
    msg = data.get("message") or {}
    cid = msg.get("chat", {}).get("id")
    user = msg.get("from", {})
    if not cid: return "ok"
    if "text" in msg:
        q = msg["text"].strip()
        if q.lower() in ["/start", "start"]:
            MEMORY[cid].clear()
            ans = f"Mbote! 👋 Je suis Ir Chris\nCréé par {CREATOR} le {DATE_CREATION} à {LIEU}\nJe parle: {', '.join(LANGS)}"
            add_log(user, q, ans)
            send(cid, ans)
        else:
            send(cid, get_answer(cid, user, q))
    elif "photo" in msg:
        best = msg["photo"][-1]
        fi = requests.get(f"{BOT_API}/getFile?file_id={best['file_id']}", timeout=10).json()
        url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fi['result']['file_path']}"
        b64 = base64.b64encode(requests.get(url, timeout=20).content).decode()
        send(cid, get_answer(cid, user, "Résous cet exercice étape par étape:", b64))
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
