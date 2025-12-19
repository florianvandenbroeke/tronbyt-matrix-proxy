import asyncio
import aiohttp
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import PlainTextResponse
from PIL import Image
import io
import logging

# === CONFIG ===
FRAME_URL = "https://tronbyt-server-biwe.onrender.com/19cedf89/next"
FRAME_WIDTH = 64
FRAME_HEIGHT = 32
FRAME_INTERVAL = 1.0  # seconden tussen frames
FRAME_SIZE = FRAME_WIDTH * FRAME_HEIGHT * 2  # 4096 bytes
WS_PING_INTERVAL = 10  # seconden

# === LOGGER CONFIG ===
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tronbyt-proxy")

# === FASTAPI APP ===
app = FastAPI()

@app.get("/")
async def root():
    return PlainTextResponse("tronbyt matrix proxy running")

async def fetch_frame(session: aiohttp.ClientSession) -> bytes | None:
    """Download en decodeer een WebP frame naar raw RGB565 bytes"""
    try:
        async with session.get(FRAME_URL) as resp:
            if resp.status != 200:
                logger.warning(f"Frame fetch failed: {resp.status}")
                return None

            webp_bytes = await resp.read()
            img = Image.open(io.BytesIO(webp_bytes)).convert("RGB")

            # Resize als nodig
            if img.width != FRAME_WIDTH or img.height != FRAME_HEIGHT:
                img = img.resize((FRAME_WIDTH, FRAME_HEIGHT))

            raw = bytearray()
            for y in range(FRAME_HEIGHT):
                for x in range(FRAME_WIDTH):
                    r, g, b = img.getpixel((x, y))
                    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                    raw += rgb565.to_bytes(2, "big")

            if len(raw) != FRAME_SIZE:
                logger.warning(f"Frame size mismatch: {len(raw)}")
                return None

            return raw

    except (aiohttp.ClientError, asyncio.TimeoutError) as e:
        logger.warning(f"Frame fetch error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error fetching frame: {e}")
        return None

async def websocket_sender(websocket: WebSocket):
    """Hoofdloop voor het versturen van frames + keepalive"""
    await websocket.accept()
    logger.info("ESP32 connected")

    timeout = aiohttp.ClientTimeout(total=3)
    async with aiohttp.ClientSession(timeout=timeout) as session:
        try:
            while True:
                # Frame ophalen
                frame = await fetch_frame(session)
                if frame:
                    try:
                        await websocket.send_bytes(frame)
                        logger.debug("Frame sent")
                    except Exception as e:
                        logger.warning(f"Send frame failed: {e}")
                        break

                # Ping/keepalive
                try:
                    await websocket.send_json({"ping": "keepalive"})
                except Exception:
                    pass

                await asyncio.sleep(FRAME_INTERVAL)

        except WebSocketDisconnect:
            logger.info("ESP32 disconnected")
        except Exception as e:
            logger.error(f"WebSocket loop error: {e}")
        finally:
            await websocket.close()

@app.websocket("/ws")
async def ws_matrix(websocket: WebSocket):
    await websocket_sender(websocket)
