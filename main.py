from flask import Flask, request
import os, requests
app = Flask(__name__)
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN","").strip()

@app.route("/")
def home(): return "BOT VIVANT"

@app.route("/telegram/<t>", methods=["POST"])
def bot(t):
    data = request.json
    print(data)  # pour voir dans les Logs
    chat = data.get("message", {}).get("chat", {}).get("id")
    if chat:
        requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id": chat, "text": "✅ Ça marche Ir! Je suis vivant! Envoie-moi un exercice!"})
    return "ok"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
