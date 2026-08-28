from flask import Flask, request
import os, requests, re

app = Flask(__name__)
TOKEN = os.environ.get("BOT_TOKEN","").strip()
if not TOKEN:
    for v in os.environ.values():
        if ":" in str(v) and len(str(v))>40: TOKEN=str(v).strip()

@app.route("/")
def home(): return f"V14 TEST OK - LEN TOKEN {len(TOKEN)}"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    data = request.get_json(force=True)
    msg = data.get("message",{})
    chat_id = msg.get("chat",{}).get("id")
    text = msg.get("text","")
    if not chat_id: return "ok",200

    print(f"Message recu: {text} de {chat_id}")

    # REPONSE DIRECTE SANS GROQ POUR TESTER
    if text.lower() in ["/start","bonjour","hello"]:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id":chat_id,"text":"✅ YES Ir! Je suis en ligne V14! Webhook marche! Maintenant on ajoute Groq."})
        return "ok",200

    # Si autre texte, essaye Groq
    try:
        from groq import Groq
        GROQ_KEY = os.environ.get("GROQ_KEY","").strip()
        if not GROQ_KEY:
            for v in os.environ.values():
                if str(v).startswith("gsk_"): GROQ_KEY=str(v).strip()
        if not GROQ_KEY:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                          json={"chat_id":chat_id,"text":"⚠️ GROQ_KEY manquant dans Render! Va dans Environment et ajoute GROQ_KEY"})
            return "ok",200

        client = Groq(api_key=GROQ_KEY)
        res = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role":"user","content":text}],
            max_tokens=500
        )
        ans = res.choices[0].message.content
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id":chat_id,"text":ans})
    except Exception as e:
        print(e)
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage",
                      json={"chat_id":chat_id,"text":f"Erreur: {e}"})

    return "ok",200

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
