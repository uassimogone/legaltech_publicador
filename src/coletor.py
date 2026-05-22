import os
import json
import asyncio
from pathlib import Path
from telethon import TelegramClient
from telethon.tl.types import MessageMediaPhoto

# Aqui só puxamos as chaves da API (sem o BOT_TOKEN)
API_ID = int(os.environ["TELEGRAM_API_ID"])
API_HASH = os.environ["TELEGRAM_API_HASH"]
CHAT_ID = int(os.environ["TELEGRAM_CHAT_ID"])

DB_DIR = Path("database")
DB_DIR.mkdir(exist_ok=True)
DATA_FILE = DB_DIR / "posts_do_dia.json"

async def coletar_posts():
    print("Iniciando coleta no Telegram via User Session...")
    # Usando o arquivo de sessão descompactado
    async with TelegramClient('telegram_session', API_ID, API_HASH) as client:
        mensagens = []
        async for msg in client.iter_messages(CHAT_ID, limit=30):
            mensagens.append(msg)
        
        mensagens.reverse()
        pares = []
        
        for i, msg in enumerate(mensagens):
            if not msg.media or not isinstance(msg.media, MessageMediaPhoto):
                continue
            
            legenda = msg.text or ""
            if not legenda:
                for j in range(i + 1, min(i + 4, len(mensagens))):
                    if mensagens[j].text and len(mensagens[j].text) > 30:
                        legenda = mensagens[j].text
                        break

            if "---" in legenda:
                legenda = legenda.split("---", 1)[1].strip()
            if legenda.endswith("---"):
                legenda = legenda[:-3].strip()

            pares.append({"msg_obj": msg, "legenda": legenda})

        pares = pares[-3:]
        
        fila_posts = []
        for index, par in enumerate(pares, 1):
            img_path = str(DB_DIR / f"slide_0{index}.png")
            print(f"Baixando imagem {index}...")
            await client.download_media(par["msg_obj"], file=img_path)
            
            fila_posts.append({
                "id": index,
                "imagem": f"slide_0{index}.png",
                "legenda": par["legenda"],
                "publicado": False
            })
            
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"posts": fila_posts}, f, ensure_ascii=False, indent=2)
            
        print(f"Coleta finalizada. {len(fila_posts)} posts na fila.")

if __name__ == "__main__":
    asyncio.run(coletar_posts())
