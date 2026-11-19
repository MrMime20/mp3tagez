from flask import Flask, request, send_file
from flask_cors import CORS
from PIL import Image
import yt_dlp, mutagen.id3 as id3, tempfile, os, io, urllib.request

app = Flask(__name__)
CORS(app)

def crop_square_jpeg(url, size=600):
    raw = urllib.request.urlopen(url).read()
    img = Image.open(io.BytesIO(raw)).convert("RGB")
    w, h = img.size
    side = min(w, h)
    left = (w - side) // 2
    top = (h - side) // 2
    img = img.crop((left, top, left + side, top + side)).resize((size, size), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=92)
    return buf.getvalue()

@app.post("/download")
def download_mp3():
    data = request.json
    meta = data.get("metadata", {})
    with tempfile.TemporaryDirectory() as tmp:
        opts = {
            "format": "bestaudio/best",
            "outtmpl": os.path.join(tmp, "track.%(ext)s"),
            "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}],
        }
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([data["url"]])
        mp3_path = os.path.join(tmp, "track.mp3")
        tags = id3.ID3(mp3_path)
        if meta.get("title"): tags.add(id3.TIT2(encoding=3, text=meta["title"]))
        if meta.get("artist"): tags.add(id3.TPE1(encoding=3, text=meta["artist"]))
        if meta.get("album"): tags.add(id3.TALB(encoding=3, text=meta["album"]))
        if meta.get("year"): tags.add(id3.TDRC(encoding=3, text=str(meta["year"])))
        if meta.get("trackNumber"): tags.add(id3.TRCK(encoding=3, text=str(meta["trackNumber"])))
        if meta.get("genre"): tags.add(id3.TCON(encoding=3, text=meta["genre"]))
        if meta.get("lyrics"): tags.add(id3.USLT(encoding=3, lang="eng", text=meta["lyrics"]))
        if meta.get("coverUrl"):
            tags.add(id3.APIC(encoding=3, mime="image/jpeg", type=3, desc="Cover", data=crop_square_jpeg(meta["coverUrl"])))
        tags.save()
        name = f"{meta.get('title') or 'track'}.mp3"
        return send_file(mp3_path, as_attachment=True, download_name=name)
