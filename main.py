import os, sqlite3, base64, requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from groq import Groq

app = Flask(__name__)

# CONFIG
GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("ELEVENLABS_API_KEY")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ADMIN_PASS = os.getenv("ADMIN_PASS", "Lushi2026")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

def init_db():
    conn = sqlite3.connect('/tmp/lushi.db')
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS chats (id INTEGER PRIMARY KEY, date TEXT, nom TEXT, question TEXT, reponse TEXT, ip TEXT)")
    conn.commit(); conn.close()
init_db()

def save_chat(nom, question, reponse, ip):
    try:
        conn = sqlite3.connect('/tmp/lushi.db')
        c = conn.cursor()
        c.execute("INSERT INTO chats (date, nom, question, reponse, ip) VALUES (?,?,?,?,?)", (datetime.now().strftime("%d/%m %H:%M"), nom, question, reponse, ip))
        conn.commit(); conn.close()
    except: pass

def ia_reply(text, img=None):
    system_prompt = "Tu es Chris Lushi Bot V14 - Made in Lubumbashi - ISTAM - 100% congolais. Tu parles 6 langues: FR, EN, Lingala, Swahili, Kiluba, Kisonde. Tu aides pour les exercices avec photo. Createur: Ir Chris Lubaki."
    messages=[{"role":"system","content":system_prompt}]
    if img:
        try:
            b64 = base64.b64encode(img.read()).decode()
            messages.append({"role":"user","content":[{"type":"text","text": text},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}]})
        except:
            messages.append({"role":"user","content": text})
    else:
        messages.append({"role":"user","content": text})
    try:
        comp = client.chat.completions.create(model="llama-3.1-8b-instant", messages=messages)
        return comp.choices[0].message.content
    except Exception as e:
        return f"Erreur IA: {e}"

@app.route("/")
def home(): return "OK V14 Lushi - Made in Lushi - Web + Telegram OK"

@app.route("/health")
def health(): return "OK V14 Lushi"

@app.route("/webhook", methods=["POST"])
def webhook():
    nom = request.form.get("nom","Anonyme")
    text = request.form.get("text","")
    img = request.files.get("image")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if not client: return jsonify({"reply":"Cle Groq manquante"})
    reponse = ia_reply(text, img)
    save_chat(nom, text, reponse, ip)
    return jsonify({"reply": reponse, "audio_url": "/audio"})

@app.route(f"/telegram/{TELEGRAM_TOKEN}", methods=["POST"])
def telegram_webhook():
    data = request.get_json()
    if data and "message" in data and "text" in data["message"]:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"]["text"]
        reponse = ia_reply(text)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": chat_id, "text": reponse})
    return "ok"

@app.route("/audio")
def audio():
    try: return send_file("/tmp/voice.mp3", mimetype="audio/mpeg")
    except: return "", 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
