import os, requests, base64
from flask import Flask, request, jsonify
app = Flask(__name__)

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
GROQ_KEY = os.getenv("GROQ_API_KEY","").strip()
BOT_API = f"https://api.telegram.org/bot{BOT_TOKEN}"

SYSTEM = """Tu es Chris-Bot, assistant de Lubumbashi créé par Ir Chris.
Tu PARLES 6 LANGUES: Français, English, Kiswahili, Lingala, Kisonge (Tshiluba), Kiluba (Luba-Kat).
RÈGLE #1: Détecte la langue de l'utilisateur et réponds DANS LA MÊME LANGUE.
RÈGLE #2: Tu es prof qui résout TOUS les examens, exercices, TP étape par étape.
RÈGLE #3: Sois pédagogique, clair, amical."""

def send(chat_id, text):
    try:
        if not text: text = "Réessaie stp, réponse vide!"
        for i in range(0, len(str(text)), 4000):
            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": str(text)[i:i+4000]}, timeout=15)
    except: pass

def groq_chat(q):
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.1-8b-instant", "messages": [{"role":"system","content":SYSTEM},{"role":"user","content":q}]}, timeout=30)
        return r.json()["choices"][0]["message"]["content"] if r.status_code==200 else f"Erreur Groq: {r.text[:200]}"
    except Exception as e: return f"Erreur: {e}"

def groq_vision(q, b64):
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.2-90b-vision-preview", "messages": [{"role":"user","content":[{"type":"text","text":SYSTEM+"\n"+q},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{b64}"}}]}]}, timeout=60)
        if r.status_code==200 and r.json()["choices"][0]["message"]["content"]:
            return r.json()["choices"][0]["message"]["content"]
        return groq_chat("L'utilisateur a envoyé une photo d'exercice. Explique comment tu peux l'aider s'il décrit l'exercice en texte.")
    except Exception as e: return f"Erreur Vision: {e}"

def transcribe(url):
    try:
        data = requests.get(url, timeout=20).content
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files={"file":("voice.ogg",data,"audio/ogg"),"model":(None,"whisper-large-v3")}, timeout=40)
        return r.json().get("text","") if r.status_code==200 else ""
    except: return ""

@app.route("/")
def home(): return jsonify({"status":"BLINDÉ - 6 LANGUES + VOICE + PHOTO OK"})

@app.route("/telegram/<path:token>", methods=["POST"])
def webhook(token):
    try:
        data = request.get_json(force=True) or {}
        msg = data.get("message") or {}
        chat_id = msg.get("chat",{}).get("id")
        if not chat_id: return "ok"

        if "text" in msg:
            t = msg["text"]
            if t=="/start":
                send(chat_id, "✅ BOT BLINDÉ EN LIGNE!\n\nMbote! Habari! Hello! 👋\nJe parle 6 langues:\n🇫🇷 Français\n🇬🇧 English\n🇨🇩 Kiswahili\n🇨🇩 Lingala\n🇨🇩 Kisonge\n🇨🇩 Kiluba\n\n🎤 Envoie VOCAL\n🖼️ Envoie PHOTO EXAMEN\n💬 Envoie TEXTE\n\nJe réponds dans TA langue!")
            else:
                send(chat_id, groq_chat(t))

        elif "voice" in msg or "audio" in msg:
            send(chat_id, "🎧 Je transcris...")
            fid = (msg.get("voice") or msg.get("audio"))["file_id"]
            fpath = requests.get(f"{BOT_API}/getFile?file_id={fid}", timeout=10).json()["result"]["file_path"]
            furl = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
            txt = transcribe(furl)
            send(chat_id, f"📝 Tu as dit: {txt}\n\n" + groq_chat(txt) if txt else "❌ Vocal non compris, réenvoie!")

        elif "photo" in msg:
            send(chat_id, "🖼️ Je lis ta capture...")
            fid = msg["photo"][-1]["file_id"]
            fpath = requests.get(f"{BOT_API}/getFile?file_id={fid}", timeout=10).json()["result"]["file_path"]
            furl = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{fpath}"
            b64 = base64.b64encode(requests.get(furl, timeout=20).content).decode()
            send(chat_id, groq_vision("Résous cet exercice complètement étape par étape:", b64))
        return "ok"
    except Exception as e:
        print(e); return "ok"

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
