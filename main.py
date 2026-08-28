from flask import Flask, request
import os, requests, re
app=Flask(__name__)
TOKEN=""; GROQ_KEY=""
for k,v in os.environ.items():
 vv=str(v).strip()
 if re.match(r'^\d+:[A-Za-z0-9_-]{30,}', vv): TOKEN=vv
 if vv.startswith("gsk_"): GROQ_KEY=vv

def ask_groq(prompt, image_url=None):
 from groq import Groq
 client=Groq(api_key=GROQ_KEY)
 # MODELE EXACT DE TON CURL QUI MARCHE
 try:
  msgs=[{"role":"system","content":"Tu es Chris-Bot Lubumbashi, 6 langues. Reponds utile."},{"role":"user","content":prompt}]
  c=client.chat.completions.create(messages=msgs, model="openai/gpt-oss-120b", temperature=0.7)
  return c.choices[0].message.content
 except Exception as e:
  try:
   c=client.chat.completions.create(messages=msgs, model="qwen/qwen3-32b")
   return c.choices[0].message.content
  except Exception as e2:
   return f"Erreur: {e} | {e2}"

@app.route("/")
def home(): return f"CHRIS-BOT OK {len(TOKEN)}/{len(GROQ_KEY)}"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
 try:
  d=request.get_json(force=True); m=d.get("message",{}); chat=m.get("chat",{}).get("id")
  if not chat: return "ok",200
  if "text" in m:
   ans=ask_groq(m["text"])
   requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
 except Exception as e: print(e)
 return "ok",200

if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
