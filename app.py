import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket
from fastapi.responses import PlainTextResponse

# === CONFIG ===
FRAME_URL = "https://tronbyt-server-biwe.onrender.com/b55b0077/next"
FRAME_SIZE = 64 * 32 * 2  # 4096 bytes
FRAME_INTERVAL = 5       # seconden

app = FastAPI()

@app.get("/")
async def root():
    return PlainTextResponse("tronbyt matrix proxy running")

@app.websocket("/ws")
async def ws_matrix(websocket: WebSocket):
    await websocket.accept()
    print("ESP32 connected")

    async with aiohttp.ClientSession() as session:
        try:
            while True:
                async with session.get(FRAME_URL) as resp:
                    frame = await resp.read()

                    if len(frame) == FRAME_SIZE:
                        await websocket.send_bytes(frame)
                    else:
                        print(f"Invalid frame size: {len(frame)}")

                await asyncio.sleep(FRAME_INTERVAL)

        except Exception as e:
            print("Client disconnected:", e)
