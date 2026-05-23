import os
import sys
import json
import time
import base64
import requests
from pathlib import Path

# Credenciais do cofre
IG_USER_ID = os.environ["INSTAGRAM_USER_ID"]
IG_TOKEN = os.environ["INSTAGRAM_ACCESS_TOKEN"]
IMGBB_KEY = os.environ["IMGBB_API_KEY"]
BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]

DB_DIR = Path("database")
DATA_FILE = DB_DIR / "posts_do_dia.json"

def avisar_telegram(texto):
    try:
        requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={"chat_id": CHAT_ID, "text": texto}, timeout=10)
    except Exception as e:
        print(f"Erro ao avisar Telegram: {e}")

def hospedar_imgbb(caminho_imagem):
    with open(caminho_imagem, "rb") as f:
        img_b64 = base64.b64encode(f.read()).decode("utf-8")
    
    resp = requests.post("https://api.imgbb.com/1/upload", data={"key": IMGBB_KEY, "image": img_b64}, timeout=30)
    
    # Tratamento defensivo se a API falhar ou der bloqueio de limite
    if resp.status_code != 200:
        raise Exception(f"ImgBB retornou erro {resp.status_code}: {resp.text[:100]}")
        
    try:
        return resp.json()["data"]["url"]
    except Exception:
        raise Exception(f"Resposta inválida do ImgBB: {resp.text[:100]}")

def publicar_meta(image_url, caption):
    base_url = "https://graph.instagram.com/v20.0"
    
    # Passo 1: Cria o container do post
    resp = requests.post(f"{base_url}/{IG_USER_ID}/media", params={"image_url": image_url, "caption": caption, "access_token": IG_TOKEN}, timeout=30)
    res_json = resp.json()
    container_id = res_json.get("id")
    
    if not container_id:
        raise Exception(f"Erro ao criar container Meta: {res_json}")
    
    # Passo 2: Aguarda a Meta processar a imagem
    for i in range(12):
        time.sleep(10) # 10 segundos entre checagens para dar fôlego à API
        status_resp = requests.get(f"{base_url}/{container_id}", params={"fields": "status_code", "access_token": IG_TOKEN}, timeout=20).json()
        status = status_resp.get("status_code", "")
        if status == "FINISHED": 
            break
        if status == "ERROR":
            raise Exception(f"Meta falhou no processamento do container: {status_resp}")
        
    # Passo 3: Publica de fato no Feed
    pub_resp = requests.post(f"{base_url}/{IG_USER_ID}/media_publish", params={"creation_id": container_id, "access_token": IG_TOKEN}, timeout=30)
    if pub_resp.status_code != 200:
        raise Exception(f"Erro na publicação final Meta: {pub_resp.text[:100]}")

def rodar_fila():
    if not DATA_FILE.exists():
        print("Arquivo JSON não encontrado. O coletor rodou?")
        sys.exit(1)

    with open(DATA_FILE, "r", encoding="utf-8") as f:
        dados = json.load(f)

    # Captura o próximo post da fila diária que não foi publicado
    post_da_vez = next((p for p in dados["posts"] if not p["publicado"]), None)
    
    if not post_da_vez:
        print("Todos os posts de hoje já foram publicados!")
        return

    print(f"Iniciando publicação do Post {post_da_vez['id']}...")
    caminho_img = DB_DIR / post_da_vez["imagem"]
    
    if not caminho_img.exists():
        avisar_telegram(f"❌ Erro: Arquivo de imagem {post_da_vez['imagem']} não foi encontrado na pasta database.")
        sys.exit(1)
    
    try:
        url_publica = hospedar_imgbb(caminho_img)
        publicar_meta(url_publica, post_da_vez["legenda"])
        
        # Salva o estado atualizado imediatamente no JSON para travar a fila
        post_da_vez["publicado"] = True
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(dados, f, ensure_ascii=False, indent=2)
            
        avisar_telegram(f"✅ Instagram Autônomo: Post {post_da_vez['id']}/3 publicado com sucesso!")
        print(f"Post {post_da_vez['id']} finalizado.")
        
    except Exception as e:
        avisar_telegram(f"❌ ERRO ao publicar slide {post_da_vez['id']}:\n{e}")
        sys.exit(1)

if __name__ == "__main__":
    rodar_fila()
