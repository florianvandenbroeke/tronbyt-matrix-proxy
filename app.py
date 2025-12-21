import os
from flask import Flask, Response
import requests
from PIL import Image
import io
import struct

app = Flask(__name__)

TRONBYT_URL = "https://tronbyt-server-biwe.onrender.com/19cedf89/next"

@app.rout("/")
def home():
    return "Proxy server activated"

@app.route("/matrix")
def matrix():
    try:
        r = requests.get(TRONBYT_URL, timeout=5)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content)).convert("RGB")
        img = img.resize((64, 32), Image.BILINEAR)

        buf = bytearray()
        for y in range(32):
            for x in range(64):
                r_, g, b = img.getpixel((x, y))
                rgb565 = ((r_ & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
                buf += struct.pack(">H", rgb565)

        # Converteer naar bytes voor Response
        return Response(bytes(buf), mimetype="application/octet-stream")

    except Exception as e:
        return Response(f"Error: {e}", status=500)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
