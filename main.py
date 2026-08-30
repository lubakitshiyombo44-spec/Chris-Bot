import os, requests, base64, json
from flask import Flask, request, jsonify

app = Flask(__name__)

# Accepte tous les noms que tu as mis dans Render
TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TEL") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ_KEY") or os.getenv("GRO") or os.getenv("GROQ") or "").strip()
BOT_API = f"https://api.telegram.org/bot{TOKEN}"

SYSTEM = """Tu es Ir Chris, créé par Ir Chris, jeune congolais ingénieur de Lubumbashi.
Tu as en toi un système intelligent de 6 langues, vision HD et voix.
Tu parles: Français, Lingala, Swahili, English, Tshiluba, Kiluba.
RÈGLE: Réponds toujours dans la langue de l'utilisateur. Résous les exercices étape par étape de façon pédagogique."""

def send(chat_id, text):
    try:
        txt = str(text) if text else "Réessaie Ir!"
        for i in range(0, len(txt), 4000):
            requests.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": txt[i:i+4000]}, timeout=20)
    except Exception as e:
        print(f"SEND ERR {e}")

def groq_text(prompt):
    if not GROQ_KEY: return "⚠️ GROQ_KEY vide dans Render Ir!"
    try:
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={"model": "llama-3.3-70b-versatile", "messages": [{"role":"system","content":SYSTEM},{"role":"user","content":prompt}]}, timeout=60)
        return r.json()["choices"][0]["message"]["content"] if r.status_code==200 else f"Erreur Groq: {r.text[:300]}"
    except Exception as e: return f"Erreur: {e}"

def groq_vision(prompt, b64_image):
    if not GROQ_KEY: return "⚠️ GROQ_KEY vide Ir!"
    try:
        # Modèle vision qui marche chez Groq
        r = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                "messages": [{
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"{SYSTEM}\n\n{prompt}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64_image}"}}
                    ]
                }]
            }, timeout=90)
        if r.status_code==200:
            return r.json()["choices"][0]["message"]["content"]
        # Si scout échoue, essaie 90b
        r2 = requests.post("https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_KEY}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.2-90b-vision-preview",
                "messages": [{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64_image}"}}]}]
            }, timeout=90)
        return r2.json()["choices"][0]["message"]["content"] if r2.status_code==200 else f"Erreur Vision: {r.text[:300]}"
    except Exception as e: return f"Erreur Vision: {e}"

def transcribe_voice(file_url):
    try:
        audio_data = requests.get(file_url, timeout=30).content
        r = requests.post("https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {GROQ_KEY}"},
            files={"file": ("voice.ogg", audio_data, "audio/ogg")},
            data={"model": "whisper-large-v3", "language": "fr"}, timeout=60)
        return r.json().get("text","") if r.status_code==200 else ""
    except Exception as e:
        print(f"TRANSCRIBE ERR {e}")
        return ""

@app.route("/")
def home():
    return jsonify({"status": "Ir Chris V18 - PHOTO HD + VOICE + 6 LANGUES OK", "token_len": len(TOKEN), "groq_len": len(GROQ_KEY)})

@app.route("/telegram/<path:path>", methods=["POST"])
def webhook(path):
    try:
        data = request.get_json(force=True) or {}
        msg = data.get("message") or {}
        chat_id = msg.get("chat",{}).get("id")
        if not chat_id: return "ok"

        # 1. PHOTO D'EXERCICE / EXAMEN - GARDE HD MAX
        if "photo" in msg:
            send(chat_id, "🖼️ Photo reçue Ir! Je lis en HD...")
            best_photo = msg["photo"][-1] # Dernier = plus grande résolution
            file_id = best_photo["file_id"]
            file_info = requests.get(f"{BOT_API}/getFile?file_id={file_id}", timeout=15).json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            img_bytes = requests.get(file_url, timeout=30).content
            b64 = base64.b64encode(img_bytes).decode('utf-8')
            answer = groq_vision("Résous complètement cet exercice/examen étape par étape. Explique chaque étape clairement:", b64)
            send(chat_id, answer)
            return "ok"

        # 2. NOTE VOCALE
        if "voice" in msg or "audio" in msg:
            send(chat_id, "🎧 Vocal reçu Ir! Je transcris...")
            fid = (msg.get("voice") or msg.get("audio"))["file_id"]
            file_info = requests.get(f"{BOT_API}/getFile?file_id={fid}", timeout=15).json()
            file_path = file_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            text_transcrit = transcribe_voice(file_url)
            if text_transcrit:
                send(chat_id, f"📝 Tu as dit: {text_transcrit}\n\n" + groq_text(text_transcrit))
            else:
                send(chat_id, "❌ Je n'ai pas pu transcrire le vocal Ir, réenvoie stp.")
            return "ok"

        # 3. TEXTE
        if "text" in msg:
            t = msg["text"]
            if t == "/start":
                send(chat_id, "Mbote Ir! 👋 C'est Ir Chris \n\n✅ Photo d'examen HD = je résous\n✅ Vocal = je transcris + je réponds\n✅ 6 Langues auto\n\nEnvoie ce que tu veux!")
            else:
                send(chat_id, groq_text(t))

        return "ok"
    except Exception as e:
        print(f"WEBHOOK ERR {e}")
        import traceback; traceback.print_exc()
        return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
