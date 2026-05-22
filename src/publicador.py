import os
import sys
import json
import time
import base64
import requests
from pathlib import Path

# Credenciais
IG_USER_ID = os.environ["INSTAGRAM_USER_ID"]
IG_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IMGBB_KEY = os.environ["IMGBB_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DB_DIR = Path("database")
DATA_FILE = DB_DIR / "posts_do_dia.json"

def avisar_telegram(texto):
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": texto})

def hospedar_imgbb(caminho_imagem):
    with open(caminho_imagem, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    resp = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_KEY, "image": img_b64})
    return resp.json()["data"]["url"]

def publicar_meta(image_url, caption):
    base_url = "https://graph.instagram.com/v20.0"
    resp = requests.post(f"{base_url}/{IG_USER_ID}/media", params={"image_url": image_url, "caption": caption, "access_token": IG_TOKEN})
    container_id = resp.json().get("id")
    
    for _ in range(12):
        status = requests.get(f"{base_url}/{container_id}", params={"fields": "status_code", "access_token": IG_TOKEN}).json().get("status_code", "")
        if status == "FINISHED": break
        time.sleep(5)
        
    requests.post(f"{base_url}/{IG_USER_ID}/media_publish", params={"creation_id": container_id, "access_token": IG_TOKEN})

def rodar_fila():
    if not DATA_FILE.exists():
        print("Arquivo JSON não encontrado. O coletor rodou?")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    post_da_vez = next((p for p in dados["posts"] if not p["publicado"]), None)
    
    if not post_da_vez:
        print("Todos os posts de hoje já foram publicados!")
        return

    print(f"Iniciando publicação do Post {post_da_vez['id']}...")
    caminho_img = DB_DIR / post_da_vez["imagem"]
    
    try:
        url_publica = hospedar_imgbb(caminho_img)
        publicar_meta(url_publica, post_da_vez["legenda"])
        
        post_da_vez["publicado"] = True
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            
        avisar_telegram(f"✅ Instagram Autônomo: Post {post_da_vez['id']}/3 publicado com sucesso!")
        
    except Exception as e:
        avisar_telegram(f"❌ Erro ao publicar Post {post_da_vez['id']}: {e}")
        sys.exit(1)

if __name__ == "__main__":
    rodar_fila()
