from flask import Flask, request
import os, requests, re

app = Flask(__name__)

TOKEN=""; GROQ_KEY=""
for k,v in os.environ.items():
 vv=str(v).strip()
 if re.match(r'^\d+:[A-Za-z0-9_-]{30,}', vv): TOKEN=vv
 if vv.startswith("gsk_"): GROQ_KEY=vv

def ask_groq(prompt, image_url=None):
 from groq import Groq
 client=Groq(api_key=GROQ_KEY)
 system="Tu es Chris-Bot de Lubumbashi pour Ir Chris. 6 langues: FR, EN, Lingala, Swahili, Tshiluba, Kikongo. Photo HD, Voix ON."

 # 3 modèles qui marchent en 2026, on essaie un par un
 MODELS_TEXT=["llama3-8b-8192","gemma2-9b-it","llama-3.1-8b-instant"]
 MODELS_VISION=["meta-llama/llama-4-maverick-17b-128e-instruct","meta-llama/llama-4-scout-17b-16e-instruct"]

 msgs=[{"role":"system","content":system}]
 if image_url:
  msgs.append({"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":image_url}}]})
  models=MODELS_VISION
 else:
  msgs.append({"role":"user","content":prompt})
  models=MODELS_TEXT

 last_err=""
 for m in models:
  try:
   c=client.chat.completions.create(messages=msgs, model=m)
   return c.choices[0].message.content
  except Exception as e:
   last_err=str(e); continue
 return f"Mbote Ir! Tous les modèles bloqués: {last_err}"

@app.route("/")
def home(): return f"CHRIS-BOT VIVANT! TEL={len(TOKEN)} GRO={len(GROQ_KEY)}"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
 try:
  data=request.get_json(force=True); msg=data.get("message",{}); chat=msg.get("chat",{}).get("id")
  if not chat: return "ok",200
  if "photo" in msg:
   best=msg["photo"][-1]; fi=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={best['file_id']}").json()
   url=f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}"
   ans=ask_groq("Decris HD:", image_url=url)
   requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans}); return "ok",200
  if "voice" in msg:
   fid=msg["voice"]["file_id"]; fi=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()
   furl=f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}"
   from groq import Groq; client=Groq(api_key=GROQ_KEY); audio=requests.get(furl).content
   open("/tmp/v.ogg","wb").write(audio)
   with open("/tmp/v.ogg","rb") as af: tr=client.audio.transcriptions.create(file=("/tmp/v.ogg",af.read()), model="whisper-large-v3")
   ans=ask_groq(f"Vocal: {tr.text}"); requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":f"Tu as dit: {tr.text}\n\n{ans}"}); return "ok",200
  if "text" in msg:
   ans=ask_groq(msg["text"]); requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
 except Exception as e: print(e)
 return "ok",200

if __name__=="__main__":
 app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
