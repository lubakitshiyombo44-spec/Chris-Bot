from flask import Flask, request
import os, requests, re

app = Flask(__name__)

TOKEN = ""
GROQ_KEY = ""
for k, v in os.environ.items():
    vv = str(v).strip()
    if re.match(r'^\d+:[A-Za-z0-9_-]{30,}', vv):
        TOKEN = vv
    if vv.startswith("gsk_"):
        GROQ_KEY = vv

print(f"BOOT OK: TEL={len(TOKEN)} GRO={len(GROQ_KEY)}")

def ask_groq(prompt, image_url=None):
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_KEY)
        system = "Tu es Chris-Bot de Lubumbashi pour Ir Chris. 6 langues: FR, EN, Lingala, Swahili, Tshiluba, Kikongo. Photo HD ON, Voix ON, Langues ON."
        msgs = [{"role": "system", "content": system}]
        if image_url:
            msgs.append({"role": "user", "content": [{"type": "text", "text": prompt}, {"type": "image_url", "image_url": {"url": image_url}}]})
            model = "meta-llama/llama-4-maverick-17b-128e-instruct"
        else:
            msgs.append({"role": "user", "content": prompt})
            model = "llama-3.1-8b-instant"
        c = client.chat.completions.create(messages=msgs, model=model)
        return c.choices[0].message.content
    except Exception as e:
        return f"Mbote Ir! Erreur: {e}"

@app.route("/")
def home():
    return f"CHRIS-BOT VIVANT Ir! TEL={len(TOKEN)} GRO={len(GROQ_KEY)} | Photo HD | Voix | 6 Langues OK"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    try:
        data = request.get_json(force=True)
        msg = data.get("message", {})
        chat = msg.get("chat", {}).get("id")
        if not chat:
            return "ok", 200
        if "photo" in msg:
            best = msg["photo"][-1]
            fi = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={best['file_id']}").json()
            url = f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}"
            ans = ask_groq("Decris photo HD:", image_url=url)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat, "text": ans})
            return "ok", 200
        if "voice" in msg:
            fid = msg["voice"]["file_id"]
            fi = requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()
            furl = f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}"
            from groq import Groq
            client = Groq(api_key=GROQ_KEY)
            audio = requests.get(furl).content
            open("/tmp/v.ogg", "wb").write(audio)
            with open("/tmp/v.ogg", "rb") as af:
                tr = client.audio.transcriptions.create(file=("/tmp/v.ogg", af.read()), model="whisper-large-v3")
            ans = ask_groq(f"Vocal: {tr.text}")
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat, "text": f"Tu as dit: {tr.text}\n\n{ans}"})
            return "ok", 200
        if "text" in msg:
            ans = ask_groq(msg["text"])
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat, "text": ans})
    except Exception as e:
        print(e)
    return "ok", 200

# CORRECTION PORT RENDER
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
