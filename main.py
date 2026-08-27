from flask import Flask, request
import os, requests, json

app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()
print(f"TOKEN LOADED: {len(TOKEN)} chars, starts with {TOKEN[:10]}")

@app.route("/")
def home():
    return f"BOT VIVANT - Token ok: {len(TOKEN)>20}"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    try:
        data = request.get_json(force=True)
        print("RECU:", json.dumps(data)[:500])
        msg = data.get("message") or data.get("edited_message") or {}
        chat = msg.get("chat", {}).get("id")
        text = msg.get("text","")
        print(f"CHAT={chat} TEXT={text}")
        if not chat:
            return "no chat", 200
        if not TOKEN:
            print("ERREUR: TOKEN VIDE DANS ENV!")
            return "no token", 200
        
        url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
        payload = {"chat_id": chat, "text": f"✅ Ir, reçu: {text}\nJe suis vivant! Token ok!"}
        r = requests.post(url, json=payload, timeout=10)
        print(f"SEND STATUS: {r.status_code} - {r.text[:300]}")
    except Exception as e:
        print(f"EXCEPTION: {e}")
        import traceback; traceback.print_exc()
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
