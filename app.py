import os, sqlite3, base64, requests
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, send_file
from groq import Groq

app = Flask(__name__)

# CONFIG SECURISE - 100% Lushi
GROQ_KEY = os.getenv("GROQ_API_KEY")
ELEVEN_KEY = os.getenv("sk_83d6c3f7f0dc6f789056cffa191a05c6ccb232e22e70fb30")
VOICE_ID = os.getenv("ELEVEN_VOICE_ID", "21m00Tcm4TlvDq8ikWAM")
ADMIN_PASS = os.getenv("ADMIN_PASS", "Lushi2026")

client = Groq(api_key=GROQ_KEY) if GROQ_KEY else None

# DB - Pour voir qui pose des questions
def init_db():
    conn = sqlite3.connect('/tmp/lushi.db')
    c = conn.cursor()
    c.execute("""CREATE TABLE IF NOT EXISTS chats
                 (id INTEGER PRIMARY KEY, date TEXT, nom TEXT, question TEXT, reponse TEXT, ip TEXT)""")
    conn.commit()
    conn.close()
init_db()

def save_chat(nom, question, reponse, ip):
    try:
        conn = sqlite3.connect('/tmp/lushi.db')
        c = conn.cursor()
        c.execute("INSERT INTO chats (date, nom, question, reponse, ip) VALUES (?,?,?,?,?)",
                  (datetime.now().strftime("%d/%m %H:%M"), nom, question[:500], reponse[:1000], ip))
        conn.commit()
        conn.close()
    except: pass

HTML_BOT = """
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<title>Chris Lushi Bot V14 - Made in Lushi</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{font-family:Arial;background:#0f0f0f;color:white;padding:15px}
.box{max-width:650px;margin:auto;background:#1a1a1a;padding:20px;border-radius:15px;border:1px solid #00ff88}
input,textarea,button{width:100%;padding:12px;margin:8px 0;border-radius:8px;border:none;box-sizing:border-box}
button{background:#00ff88;color:black;font-weight:bold;font-size:16px;cursor:pointer}
#rep{margin-top:15px;background:#222;padding:12px;border-radius:8px;white-space:pre-wrap;min-height:50px}
small{color:#00ff88}
</style>
</head><body>
<div class="box">
<h2>🤖 Chris Lushi Bot V14</h2>
<p><small>100% Made in Lubumbashi - ISTAM - Ir Chris</small><br>
🗣️ 6 Langues: FR/EN/Lingala/Swahili/Kiluba/Kisongye + 📸 Photo Exercices + 🔊 Voix</p>
<input id="nom" placeholder="Ton nom (ex: Ir Chris)">
<textarea id="q" rows="3" placeholder="Pose ta question ici..."></textarea>
<input type="file" id="img" accept="image/*">
<button onclick="envoyer()">🚀 Envoyer</button>
<div id="rep">En attente de ta question...</div>
<audio id="audio" controls style="width:100%;margin-top:10px;display:none"></audio>
<p style="text-align:center;margin-top:10px"><a href="/admin?pass=Lushi2026" style="color:#555;font-size:12px">Admin</a></p>
</div>
<script>
async function envoyer(){
  let nom=document.getElementById('nom').value || 'Anonyme';
  let text=document.getElementById('q').value;
  if(!text){alert('Écris une question!'); return;}
  let file=document.getElementById('img').files[0];
  let fd=new FormData(); fd.append('nom',nom); fd.append('text',text);
  if(file) fd.append('image',file);
  document.getElementById('rep').innerText='⏳ Lushi réfléchit...';
  let r=await fetch('/webhook',{method:'POST',body:fd});
  let j=await r.json();
  document.getElementById('rep').innerText=j.reply;
  if(j.audio_url){ let a=document.getElementById('audio'); a.src=j.audio_url+'?t='+Date.now(); a.style.display='block'; a.play(); }
}
</script></body></html>
"""

HTML_ADMIN = """
<!DOCTYPE html><html><head><meta charset="utf-8"><title>Admin Lushi</title>
<meta name="viewport" content="width=device-width">
<style>body{font-family:Arial;background:#111;color:white;padding:15px} table{width:100%;border-collapse:collapse;font-size:11px} th,td{border:1px solid #333;padding:6px;text-align:left;word-break:break-all} th{background:#00ff88;color:black} tr:nth-child(even){background:#1a1a1a}</style>
</head><body>
<h2>📊 Dashboard Admin - Chris Lushi Bot V14</h2>
<p>Total: {{rows|length}} | <a href="/" style="color:#00ff88">Retour Bot</a> | <a href="/admin?pass={{ap}}&clear=1" style="color:red" onclick="return confirm('Effacer?')">Vider</a></p>
<table><tr><th>Date</th><th>Nom</th><th>Question</th><th>Réponse</th><th>IP</th></tr>
{% for r in rows %}<tr><td>{{r[1]}}</td><td>{{r[2]}}</td><td>{{r[3]}}</td><td>{{r[4][:300]}}</td><td>{{r[5]}}</td></tr>{% endfor %}
</table></body></html>
"""

@app.route("/")
def home(): return render_template_string(HTML_BOT)

@app.route("/admin")
def admin():
    if request.args.get("pass")!= ADMIN_PASS: return "Acces refuse. /admin?pass=Lushi2026", 403
    if request.args.get("clear") == "1":
        conn = sqlite3.connect('/tmp/lushi.db'); conn.execute("DELETE FROM chats"); conn.commit(); conn.close()
    conn = sqlite3.connect('/tmp/lushi.db'); c = conn.cursor()
    c.execute("SELECT * FROM chats ORDER BY id DESC LIMIT 300"); rows = c.fetchall(); conn.close()
    return render_template_string(HTML_ADMIN, rows=rows, ap=ADMIN_PASS)

@app.route("/webhook", methods=["POST"])
def webhook():
    nom = request.form.get("nom","Anonyme")
    text = request.form.get("text","")
    img = request.files.get("image")
    ip = request.headers.get('X-Forwarded-For', request.remote_addr)[:50]

    if not client: return jsonify({"reply":"Erreur: GROQ_API_KEY manquante sur Render", "audio_url":None})

    system_prompt = """Tu es Chris Lushi Bot V14, cree par Ir Chris ingenieur Electromecanique ISTAM Lubumbashi, 100% Made in Katanga RDC.
Tu parles 6 langues: Francais, English, Lingala, Swahili, Kiluba, Kisongye.
Tu resous les exercices en photo etape par etape avec details tres clairs.
Tu es securise, respectueux, et tu representes la fierte Lushis.
Reponds TOUJOURS dans la langue de l'utilisateur. Sois concis mais complet."""

    messages=[{"role":"system","content":system_prompt}]
    if img:
        try:
            b64 = base64.b64encode(img.read()).decode()
            messages.append({"role":"user","content":[
                {"type":"text","text": text + ". Resous cet exercice en photo etape par etape, detaille chaque calcul."},
                {"type":"image_url","image_url":{"url": f"data:image/jpeg;base64,{b64}"}}
            ]})
        except: messages.append({"role":"user","content": text})
    else: messages.append({"role":"user","content": text})

    try:
        comp = client.chat.completions.create(model="llama-3.2-11b-vision-preview", messages=messages, max_tokens=1200, temperature=0.6)
        reponse = comp.choices[0].message.content
    except Exception as e: reponse = f"Erreur IA: {e}"

    save_chat(nom, text, reponse, ip)

    # VOIX: Essaye ElevenLabs, sinon gTTS gratuit
    audio_url = None
    try:
        if ELEVEN_KEY and VOICE_ID:
            url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
            headers = {"xi-api-key": ELEVEN_KEY, "Content-Type": "application/json"}
            data = {"text": reponse[:380], "model_id": "eleven_multilingual_v2", "voice_settings": {"stability":0.5,"similarity_boost":0.75}}
            r = requests.post(url, json=data, headers=headers, timeout=15)
            if r.status_code==200:
                open("/tmp/voice.mp3","wb").write(r.content); audio_url="/audio"
    except: pass

    if not audio_url:
        try:
            # Fallback GRATUIT avec gTTS (Google)
            from gtts import gTTS
            tts = gTTS(text=reponse[:380], lang='fr')
            tts.save("/tmp/voice.mp3"); audio_url="/audio"
        except: audio_url=None

    return jsonify({"reply": reponse, "audio_url": audio_url})

@app.route("/audio")
def audio():
    try: return send_file("/tmp/voice.mp3", mimetype="audio/mpeg")
    except: return "", 404

@app.route("/health")
def health(): return "OK V14 Lushi - Made in Lushi"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
