from flask import Flask, request
import os, requests, json

app = Flask(__name__)

# --- CONFIG FLEXIBLE (marche avec TEL ou TELEGRAM_BOT_TOKEN) ---
TOKEN = (os.getenv("TELEGRAM_BOT_TOKEN") or os.getenv("TELEGRAM_TOKEN") or os.getenv("TEL") or "").strip()
GROQ_KEY = (os.getenv("GROQ_API_KEY") or os.getenv("GROQ") or os.getenv("GRO") or "").strip()

print(f"BOOT: TOKEN len={len(TOKEN)} GROQ len={len(GROQ_KEY)}")

def ask_groq(prompt, image_url=None):
    if not GROQ_KEY:
        return "⚠️ Clé GROQ manquante Ir!"
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        messages = [{"role":"system","content":"Tu es Chris-Bot de Lubumbashi. Tu parles Français, Lingala, Swahili, Anglais. Tu réponds toujours chaleureusement à Ir. Si on t'envoie une photo, tu décris avec haute résolution."}]
        if image_url:
            messages.append({"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":image_url}}]})
            model = "meta-llama/llama-4-scout-17b-16e-instruct"
        else:
            messages.append({"role":"user","content":prompt})
            model = "llama-3.3-70b-versatile"
        comp = client.chat.completions.create(messages=messages, model=model, temperature=0.7)
        return comp.choices[0].message.content
    except Exception as e:
        print(f"GROQ ERR {e}")
        return f"Erreur Groq: {e}"

@app.route("/")
def home():
    return f"CHRIS-BOT VIVANT Ir! TEL={len(TOKEN)} GRO={len(GROQ_KEY)} Photo=HD Voice=ON Langues=4"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    try:
        data = request.get_json(force=True)
        print(f"RECU: {json.dumps(data)[:400]}")
        msg = data.get("message",{})
        chat = msg.get("chat",{}).get("id")
        if not chat: return "ok",200

        # 1. PHOTO - garde la meilleure résolution
        if "photo" in msg:
            photos = msg["photo"]
            best = photos[-1] # Telegram envoie du plus petit au plus grand, le dernier = HD max
            file_id = best["file_id"]
            # Récupère le fichier HD
            f_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
            file_path = f_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            answer = ask_groq("Décris cette photo en haute résolution avec tous les détails pour Ir:", image_url=file_url)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":answer})
            return "ok",200

        # 2. VOIX / AUDIO
        if "voice" in msg or "audio" in msg:
            file_id = (msg.get("voice") or msg.get("audio")).get("file_id")
            f_info = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={file_id}").json()
            file_path = f_info["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{TOKEN}/{file_path}"
            # Transcription avec Groq Whisper
            try:
                from groq import Groq
                client = Groq(api_key=GROQ_KEY)
                audio_data = requests.get(file_url).content
                with open("/tmp/voice.ogg","wb") as f: f.write(audio_data)
                with open("/tmp/voice.ogg","rb") as f:
                    trans = client.audio.transcriptions.create(file=("/tmp/voice.ogg", f.read()), model="whisper-large-v3", language="fr")
                text_voix = trans.text
                answer = ask_groq(f"Ir a dit en vocal: {text_voix}. Réponds lui.")
            except Exception as e:
                print(f"VOICE ERR {e}")
                answer = f"J'ai bien reçu ta note vocale Ir! 🎤 (transcription en cours: {e})"
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":answer})
            return "ok",200

        # 3. TEXTE - avec langues
        text = msg.get("text","")
        if text:
            answer = ask_groq(text)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":answer})
    except Exception as e:
        print(f"GLOBAL ERR {e}")
        import traceback; traceback.print_exc()
    return "ok",200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
