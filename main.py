from flask import Flask, request
import os, requests, re
app=Flask(__name__)
TOKEN=""; GROQ_KEY=""
for k,v in os.environ.items():
 vv=str(v).strip()
 if re.match(r'^\d+:[A-Za-z0-9_-]{30,}', vv): TOKEN=vv
 if vv.startswith("gsk_"): GROQ_KEY=vv
 print(f"BOOT TEL={len(TOKEN)} GRO={len(GROQ_KEY)}")

def ask_groq(prompt, image_url=None):
 from groq import Groq
 client=Groq(api_key=GROQ_KEY)
 # MODELES 2026 VALIDES CHEZ GROQ - testé aujourd'hui
 MODELS=["qwen/qwen3-32b","openai/gpt-oss-20b","llama-3.3-70b-versatile","llama-3.1-8b-instant","groq/compound-mini","llama3-8b-8192"]
 # Pour vision on utilise Qwen qui fait texte + image maintenant
 if image_url:
  MODELS=["qwen/qwen3-32b","groq/compound-mini"]
  msgs=[{"role":"user","content":[{"type":"text","text":prompt},{"type":"image_url","image_url":{"url":image_url}}]}]
 else:
  msgs=[{"role":"system","content":"Tu es Chris-Bot Lubumbashi. 6 langues FR EN Lingala Swahili Tshiluba Kikongo. Reponds court et utile."},{"role":"user","content":prompt}]
 for m in MODELS:
  try:
   c=client.chat.completions.create(messages=msgs, model=m, temperature=0.7)
   return c.choices[0].message.content
  except Exception as e:
   print(f"Model {m} fail: {e}")
   continue
 return "Mbote Ir! Groq bloque tous les modeles, regenere ta clé sur console.groq.com"

@app.route("/")
def home(): return f"CHRIS-BOT VIVANT {len(TOKEN)}/{len(GROQ_KEY)}"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
 try:
  d=request.get_json(force=True); m=d.get("message",{}); chat=m.get("chat",{}).get("id")
  if not chat: return "ok",200
  if "photo" in m:
   best=m["photo"][-1]; fi=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={best['file_id']}").json()
   url=f"https://api.telegram.org/file/bot{TOKEN}/{fi['result']['file_path']}"
   ans=ask_groq("Decris image HD en FR:", image_url=url)
   requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans}); return "ok",200
  if "text" in m:
   ans=ask_groq(m["text"]); requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
 except Exception as e: print(e)
 return "ok",200

if __name__=="__main__": app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)))
