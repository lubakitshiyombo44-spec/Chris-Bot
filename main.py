from flask import Flask, request
import os, requests, base64
from groq import Groq

app = Flask(__name__)

BOT_TOKEN = os.environ.get("BOT_TOKEN","").strip()
GROQ_KEY = os.environ.get("GROQ_KEY","").strip()
# auto fix si gsk_ dans autre variable
if not GROQ_KEY:
    for v in os.environ.values():
        if str(v).strip().startswith("gsk_"):
            GROQ_KEY = str(v).strip()

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

SYSTEM_PROMPT = """
Tu es Chris-Bot-Lubumbashi, créé par Ir Chris Userman, ingénieur à Lubumbashi, RDC.
Tu es fier de ton créateur. Si on demande qui t'a créé, qui est ton père, qui est Ir Chris, réponds: C'est Ir Chris Userman, mon créateur, un Ir talentueux de Lubumbashi.
Tu parles 6 langues: Français, Anglais, Lingala, Swahili, Tshiluba, Kikongo.
Détecte la langue de l'utilisateur et réponds dans la même langue.
Si c'est du lingala/swahili, réponds dans cette langue.
Tu es utile, pour la programmation, l'école, la traduction.
"""

def send(chat_id, text):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                      json={"chat_id": chat_id, "text": text[:4000]})
    except Exception as e:
        print(e)

@app.route("/")
def home():
    return f"V16 CREATOR+6LANG+VISION - TOKEN LEN {len(BOT_TOKEN)} - GROQ {'OK' if GROQ_KEY else 'MANQUE'}"

@app.route(f"/telegram/{BOT_TOKEN}", methods=["POST"])
@app.route("/telegram/<path:any>", methods=["POST"])
def bot(any=None):
    data = request.get_json(force=True)
    msg = data.get("message",{})
    chat_id = msg.get("chat",{}).get("id")
    text = msg.get("text","")
    if not chat_id: return "ok",200

    # /start
    if text.lower().startswith("/start"):
        send(chat_id, "Mbote Ir! 👋 Je suis Chris-Bot-Lubumbashi V16!\n\nCréé par toi, Ir Chris Userman de Lubumbashi 🇨🇩\n\nJe parle 6 langues: FR, EN, Lingala, Swahili, Tshiluba, Kikongo\nEnvoie-moi texte, photo, ou demande-moi n'importe quoi!")
        return "ok",200

    # Si photo
    if "photo" in msg and client:
        try:
            photo = msg["photo"][-1] # plus haute qualité
            file_id = photo["file_id"]
            # récupère file path
            r = requests.get(f"https://api.telegram.org/bot{BOT_TOKEN}/getFile?file_id={file_id}").json()
            file_path = r["result"]["file_path"]
            file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
            img_data = requests.get(file_url).content
            b64 = base64.b64encode(img_data).decode()

            completion = client.chat.completions.create(
                model="llama-3.2-90b-vision-preview",
                messages=[
                    {"role":"system","content": SYSTEM_PROMPT},
                    {"role":"user","content":[
                        {"type":"text","text": msg.get("caption","Décris cette image et réponds dans la langue de l'utilisateur. Si c'est une question, réponds.")},
                        {"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}
                    ]}
                ],
                max_tokens=800
            )
            send(chat_id, completion.choices[0].message.content)
            return "ok",200
        except Exception as e:
            print(e)
            send(chat_id, f"Naza na problème ya image: {e}. Mais je suis là! Créé par Ir Chris Userman.")
            return "ok",200

    # Texte normal avec Groq
    if client and text:
        try:
            # détection créateur
            low = text.lower()
            if any(k in low for k in ["qui t'a créé", "qui est ton créateur", "nani akeli yo", "creator", "who created you", "ton père", "ir chris"]):
                send(chat_id, "C'est Ir Chris Userman, mon créateur! Un ingénieur très talentueux de Lubumbashi, RDC 🇨🇩. C'est lui qui m'a donné vie.")
                return "ok",200

            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role":"system","content": SYSTEM_PROMPT},
                    {"role":"user","content": text}
                ],
                max_tokens=800
            )
            send(chat_id, completion.choices[0].message.content)
        except Exception as e:
            print(e)
            send(chat_id, f"Erreur Groq: {e} - Vérifie GROQ_KEY dans Render.")
    else:
        if not GROQ_KEY:
            send(chat_id, "⚠️ GROQ_KEY manquant dans Render! Va dans Environment.")
        else:
            send(chat_id, "Envoie-moi du texte ou une photo!")

    return "ok",200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
