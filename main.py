from flask import Flask, request
import os, requests, re

app = Flask(__name__)

# --- DETECTION AUTO TEL=46 GRO=56 ---
TOKEN=""; GROQ_KEY=""
for k,v in os.environ.items():
    v=str(v).strip()
    if re.match(r'^\d+:[A-Za-z0-9_-]{30,}', v): TOKEN=v
    if v.startswith("gsk_"): GROQ_KEY=v
print(f"BOOT FINAL: TEL={len(TOKEN)} GRO={len(GROQ_KEY)}")

def ask_groq(prompt, image_url=None):
    from groq import Groq
    client = Groq(api_key=GROQ_KEY)
    # Les 6 langues que tu as demandées
    system = """Tu es Chris-Bot de Lubumbashi créé pour Ir Chris.
    Tu parles et détectes automatiquement 6 langues:
    1. Français 2. Anglais 3. Lingala 4. Swahili 5. Tshiluba 6. Kikongo.
    - Si on t'envoie une PHOTO: tu l'analyses en Haute Résolution HD, tu donnes tous les détails.
    - Si on t'envoie une NOTE VOCALE: tu comprends et tu réponds dans la même langue.
    - Toujours chaleureux, comme un frère de Lubumbashi."""

    msgs=[{"role":"system","content":system}]
    if image_url:
        msgs.append({"role":"user","content":[
            {"type":"text","text":prompt},
            {"type":"image_url","image_url":{"url":image_url}}
        ]})
        # MODELE VISION QUI MARCHE EN 2026
        model="meta-llama/llama-4-maverick-17b-128e-instruct"
    else:
        msgs.append({"role":"user","content":prompt})
        # MODELE TEXTE QUI MARCHE - répare erreur 404
        model="llama-3.1-8b-instant"

    c=client.chat.completions.create(messages=msgs, model=model, temperature=0.7)
    return c.choices[0].message.content

@app.route("/")
def home():
    return f"CHRIS-BOT FINAL VIVANT! TEL={len(TOKEN)} GRO={len(GROQ_KEY)} | 6 LANGUES OK | PHOTO HD OK | VOIX OK"

@app.route("/telegram/<path:t>", methods=["POST"])
def bot(t):
    try:
        data=request.get_json(force=True)
        msg=data.get("message",{})
        chat=msg.get("chat",{}).get("id")
        if not chat or not TOKEN: return "ok",200

        # 1. PHOTO -> HAUTE RÉSOLUTION
        if "photo" in msg:
            best = msg["photo"][-1] # Le dernier = résolution max HD
            f=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={best['file_id']}").json()
            url=f"https://api.telegram.org/file/bot{TOKEN}/{f['result']['file_path']}"
            ans=ask_groq("Analyse cette photo en haute résolution avec tous les détails, résous le problème si c'est un exercice:", image_url=url)
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})
            return "ok",200

        # 2. VOIX -> TA VOIX INTÉGRÉE
        if "voice" in msg or "audio" in msg:
            fid=(msg.get("voice") or msg.get("audio")).get("file_id")
            f=requests.get(f"https://api.telegram.org/bot{TOKEN}/getFile?file_id={fid}").json()
            file_url=f"https://api.telegram.org/file/bot{TOKEN}/{f['result']['file_path']}"
            try:
                from groq import Groq
                client=Groq(api_key=GROQ_KEY)
                audio=requests.get(file_url).content
                open("/tmp/v.ogg","wb").write(audio)
                with open("/tmp/v.ogg","rb") as af:
                    tr=client.audio.transcriptions.create(file=("/tmp/v.ogg", af.read()), model="whisper-large-v3", language="fr")
                texte_voix=tr.text
                ans=ask_groq(f"Ir a dit en vocal: '{texte_voix}'. Réponds dans la même langue avec les 6 langues.")
            except Exception as e:
                ans=f"J'ai reçu ta voix Ir! 🎤 Transcription: {e}"

            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":f"🎤 Tu as dit: {texte_voix}\n\n{ans}"})
            return "ok",200

        # 3. TEXTE -> 6 LANGUES
        if "text" in msg:
            ans=ask_groq(msg["text"])
            requests.post(f"https://api.telegram.org/bot{TOKEN}/sendMessage", json={"chat_id":chat,"text":ans})

    except Exception as e:
        print(f"ERR {e}")
    return "ok",200
