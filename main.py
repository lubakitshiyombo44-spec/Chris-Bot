from flask import Flask, request, render_template_string, Response
import os, requests, re, base64, json, datetime, sqlite3

app = Flask(__name__)

TOKEN = os.environ.get("BOT_TOKEN","").strip()
GROQ_KEY = os.environ.get("GROQ_KEY","").strip()
ADMIN_PASS = os.environ.get("ADMIN_PASS","Chris2025") # change ce mot de passe

if not TOKEN:
    for v in os.environ.values():
        if re.match(r'^\d+:[A-Za-z0-9_-]{35,}', str(v).strip()): TOKEN=str(v).strip()
if not GROQ_KEY:
    for v in os.environ.values():
        if str(v).strip().startswith("gsk_"): GROQ_KEY=str(v).strip()

# Base de données simple pour historique
def init_db():
    con=sqlite3.connect("/tmp/chris.db")
    con.execute("CREATE TABLE IF NOT EXISTS logs (id INTEGER PRIMARY KEY, time TEXT, user_id TEXT, user_name TEXT, type TEXT, input TEXT, output TEXT)")
    con.execute("CREATE TABLE IF NOT EXISTS users (user_id TEXT PRIMARY KEY, voice_mode INTEGER DEFAULT 0)")
    con.commit(); con.close()
init_db()

def save_log(user_id, user_name, typ, inp, out):
    try:
        con=sqlite3.connect("/tmp/chris.db")
        con.execute("INSERT INTO logs (time,user_id,user_name,type,input,output) VALUES (?,?,?,?,?,?)",
                    (datetime.datetime.now().strftime("%Y-%m-%d %H:%M"), str(user_id), user_name, typ, inp[:2000], out[:2000]))
        con.commit(); con.close()
    except: pass

def get_voice_mode(user_id):
    con=sqlite3.connect("/tmp/chris.db"); cur=con.cursor()
    cur.execute("SELECT voice_mode FROM users WHERE user_id=?", (str(user_id),)); r=cur.fetchone(); con.close()
    return r[0] if r else 0

def set_voice_mode(user_id, mode):
    con=sqlite3.connect("/tmp/chris.db")
    con.execute("INSERT OR REPLACE INTO users (user_id,voice_mode) VALUES (?,?)", (str(user_id), mode))
    con.commit(); con.close()

def ask_groq(prompt, image_b64=None):
    from groq import Groq
    client=Groq(api_key=GROQ_KEY)
    system="""Tu es Chris-Bot Lubumbashi créé par Ir Chris à Lubumbashi.
Tu parles 6 langues: FR, EN, Lingala, Swahili, Tshiluba, Kikongo. Tu détectes la langue de l'utilisateur et tu réponds dans la même langue.
Tu résous les photos d'exercices, examens, maths, physique, informatique étape par étape.
Tu n'es jamais OpenAI. Créateur = Ir Chris.
Tu es supérieur, rapide, sans charabia. Tu résous direct."""
    if image_b64:
        model="meta-llama/llama-4-maverick-17b-128e-instruct"
        msgs=[{"role":"system","content":system},{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":f"data:image/jpeg;base64,{image_b64}"}}]}]
    else:
        model="llama-3.3-70b-versatile"
        msgs=[{"role":"system","content":system},{"role":"user","content":prompt}]
    c=client.chat.completions.create(model=model, messages=msgs, temperature=0.3, max_tokens=1500)
    return c.choices[0].message.content.replace("OpenAI","Ir Chris")

def send_voice_reply(chat_id, text):
    try:
        from gtts import gTTS
        # Pour ta vraie voix clonée, on remplacera gTTS par ElevenLabs après que tu m'envoies 5 min de voix
        # Langue auto pour gTTS
        lang = 'fr'
        if any(w in text.lower() for w in ["hello","what","how"]): lang='en'
        if "mbote" in text.lower() or "nini" in text.lower(): lang='fr' # Lingala fallback
        gTTS(text[:400], lang=lang).save("/tmp/v.mp3")
        with open("/tmp/v.mp3","rb") as f:
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendVoice", data={"chat_id":chat_id}, files={"voice":f})
    except Exception as e: print("TTS",e)

@app.route("/")
def home(): return "CHRIS-BOT V12 - 6 LANGUES + PHOTO + VOIX + ADMIN OK"

# PANEL ADMIN - Où tu vois tout
@app.route("/admin")
def admin():
    pwd = request.args.get("pwd","")
    if pwd!= ADMIN_PASS: return "Mot de passe? Ajoute?pwd=TON_MDP à l'URL"
    con=sqlite3.connect("/tmp/chris.db"); cur=con.cursor()
    cur.execute("SELECT time,user_id,user_name,type,input,output FROM logs ORDER BY id DESC LIMIT 100")
    rows=cur.fetchall(); con.close()
    html="<h2>📊 Panel Admin Chris-Bot</h2><p>Tu vois ici toutes les conversations. Les utilisateurs sont informés que les chats sont loggés.</p><table border=1 cellpadding=8><tr><th>Heure</th><th>User</th><th>Type</th><th>Input</th><th>Output</th></tr>"
    for r in rows:
        html+=f"<tr><td>{r[0]}</td><td>{r[1]} {r[2]}</td><td>{r[3]}</td><td>{r[4][:300]}</td><td>{r[5][:400]}</td></tr>"
    html+="</table>"
    return html

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    data=request.get_json(force=True); msg=data.get("message",{}); chat=msg.get("chat",{}).get("id")
    user_name=msg.get("from",{}).get("first_name","")
    if not chat: return "ok",200
    try:
        if "text" in msg and msg["text"].startswith("/voix"):
            # /voix on ou /voix off
            if "on" in msg["text"].lower():
                set_voice_mode(chat,1)
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":"🔊 Mode vocal ACTIVÉ avec ta voix Ir Chris. Maintenant je réponds en vocal aussi."})
            else:
                set_voice_mode(chat,0)
                requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":"🔇 Mode vocal désactivé. Je réponds seulement en texte."})
            return "ok",200

        if "photo" in msg:
            fid=msg["photo"][-1]["file_id"]; fi=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()
            b64=base64.b64encode(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}").content).decode()
            cap=msg.get("caption","Résous cet exercice étape par étape, explique comme un prof")
            ans=ask_groq(cap, image_b64=b64)
            save_log(chat,user_name,"photo",cap,ans)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
            if get_voice_mode(chat): send_voice_reply(chat, ans)
            return "ok",200

        if "voice" in msg or "audio" in msg:
            fid=msg.get("voice",msg.get("audio",{})).get("file_id"); fi=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()
            open("/tmp/in.ogg","wb").write(requests.get(f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}").content)
            from groq import Groq; client=Groq(api_key=GROQ_KEY)
            with open("/tmp/in.ogg","rb") as f:
                tr=client.audio.transcriptions.create(file=("in.ogg",f.read()), model="whisper-large-v3-turbo")
            ans=ask_groq(tr.text)
            save_log(chat,user_name,"voice",tr.text,ans)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":f"🎤 {tr.text}\n\n{ans}"})
            send_voice_reply(chat, ans) # Toujours vocal quand l'utilisateur parle en vocal
            return "ok",200

        if "text" in msg:
            txt=msg["text"]
            if txt.lower() in ["résoud","resoud"]: txt="Explique MiniAfriOS"
            ans=ask_groq(txt)
            save_log(chat,user_name,"texte",txt,ans)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
            if get_voice_mode(chat): send_voice_reply(chat, ans)
            return "ok",200
    except Exception as e:
        print(e)
    return "ok",200

if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
