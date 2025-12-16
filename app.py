from flask import Flask, Response
import requests
from PIL import Image
import io
import struct

app = Flask(__name__)

TRONBYT_URL = "https://tronbyt-server-biwe.onrender.com/8a073afe/next"

@app.route("/matrix")
def matrix():
    r = requests.get(TRONBYT_URL, timeout=5)
    img = Image.open(io.BytesIO(r.content)).convert("RGB")
    img = img.resize((64, 32), Image.BILINEAR)

    buf = bytearray()
    for y in range(32):
        for x in range(64):
            r, g, b = img.getpixel((x, y))
            rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
            buf += struct.pack(">H", rgb565)

    return Response(
        buf,
        mimetype="application/octet-stream",
        headers={
            "Cache-Control": "no-store",
            "Content-Length": str(len(buf))
        }
    )

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
