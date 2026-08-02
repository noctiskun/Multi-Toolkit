"""Drive the real server over HTTP: every route, happy path and error path."""
import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

from PIL import Image, ImageDraw
from pypdf import PdfWriter
from pyzbar.pyzbar import decode as zbar

PORT = 8777
BASE = f"http://127.0.0.1:{PORT}"
fails = []


def post(path, body, raw=False):
    req = urllib.request.Request(
        BASE + path, data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
            return r.status, (data if raw else json.loads(data)), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), dict(e.headers)


def check(name, cond, detail=""):
    print(f"  {'ok  ' if cond else 'FAIL'} {name}{' — ' + detail if detail else ''}")
    if not cond:
        fails.append(name + (" — " + detail if detail else ""))


def logo_b64():
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([170, 30, 230, 90], fill=(20, 20, 20, 255))
    d.rectangle([160, 95, 240, 240], fill=(20, 20, 20, 255))
    d.polygon([(160, 100), (60, 200), (85, 225), (165, 140)], fill=(20, 20, 20, 255))
    d.polygon([(240, 100), (340, 200), (315, 225), (235, 140)], fill=(20, 20, 20, 255))
    d.rectangle([168, 240, 195, 370], fill=(20, 20, 20, 255))
    d.rectangle([205, 240, 232, 370], fill=(20, 20, 20, 255))
    b = io.BytesIO(); im.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def photo_b64(w=1600, h=1000):
    im = Image.new("RGB", (w, h), (40, 60, 120))
    d = ImageDraw.Draw(im)
    for i in range(0, w, 80):
        d.rectangle([i, 0, i + 40, h], fill=(200, 120, 40))
    d.ellipse([w // 2 - 200, h // 2 - 200, w // 2 + 200, h // 2 + 200], fill=(250, 250, 250))
    b = io.BytesIO(); im.save(b, "JPEG", quality=92)
    return base64.b64encode(b.getvalue()).decode(), b.getvalue()


def pdf_b64(pages=4):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=595, height=842)
    b = io.BytesIO(); w.write(b)
    return base64.b64encode(b.getvalue()).decode()


def decode_qr(b64):
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.getchannel("A"))
    r = zbar(bg)
    return r[0].data.decode() if r else ""


proc = subprocess.Popen([sys.executable, "-c",
                         f"import multi_toolkit as m,http.server,threading;"
                         f"s=http.server.ThreadingHTTPServer(('127.0.0.1',{PORT}),m.Handler);"
                         f"s.serve_forever()"],
                        cwd=os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
for _ in range(60):
    try:
        urllib.request.urlopen(BASE + "/capabilities", timeout=2).read()
        break
    except Exception:
        time.sleep(0.5)
else:
    print("server never came up:\n", proc.communicate(timeout=5)[0])
    sys.exit(1)

try:
    print("\n== page + capabilities ==")
    with urllib.request.urlopen(BASE + "/") as r:
        page = r.read().decode()
    check("index served", r.status == 200 and "Multi Toolkit" in page)
    for frag in ('data-tab="qr"', 'data-tab="reels"', 'data-tab="image"',
                 'id="cropBox"', 'id="qrLogoDrop"', 'data-g="media"'):
        check(f"page contains {frag}", frag in page)
    with urllib.request.urlopen(BASE + "/capabilities") as r:
        caps = json.load(r)
    check("capabilities json", set(caps) == {"libreoffice", "ghostscript", "ffmpeg"},
          str(caps))

    print("\n== /qr ==")
    LOGO = logo_b64()
    cases = [
        ("plain link", {"kind": "url", "fields": {"text": "example.com"}},
         "https://example.com"),
        ("logo silhouette", {"kind": "url", "fields": {"text": "https://siu.example"},
                             "logo_data": LOGO, "logo_pct": 25,
                             "logo_style": "silhouette", "pad": False},
         "https://siu.example"),
        ("logo + plate", {"kind": "url", "fields": {"text": "https://siu.example"},
                          "logo_data": LOGO, "pad": True, "pad_shape": "circle"},
         "https://siu.example"),
        ("dots + colour", {"kind": "text", "fields": {"text": "hello dots"},
                           "style": "dots", "fg": "#1b1035", "bg": "#f5f2ff"},
         "hello dots"),
        ("transparent", {"kind": "text", "fields": {"text": "clear bg"},
                         "bg": "transparent"}, "clear bg"),
        ("wifi", {"kind": "wifi", "fields": {"ssid": "Lab 5G", "password": "hunter2",
                                             "security": "WPA"}}, None),
        ("vcard", {"kind": "vcard", "fields": {"name": "Ada Lovelace",
                                               "email": "a@b.com"}}, None),
        ("raw data override", {"data": "direct payload"}, "direct payload"),
        ("jpg out", {"kind": "text", "fields": {"text": "jpeg me"}, "fmt": "jpg"},
         "jpeg me"),
        ("4096 px", {"kind": "text", "fields": {"text": "big"}, "target_px": 4096}, "big"),
    ]
    for name, body, expect in cases:
        st, j, _ = post("/qr", body)
        if st != 200:
            check(name, False, f"HTTP {st}: {str(j)[:90]}")
            continue
        got = decode_qr(j["image"])
        ok = (got == expect) if expect else bool(got)
        check(name, ok, f"v{j['version']} {j['size']}px ec{j['ec']} -> {got[:38]!r}")

    st, j, _ = post("/qr", {"kind": "url", "fields": {"text": ""}})
    check("empty input rejected", st == 400, f"HTTP {st}")
    st, j, _ = post("/qr", {"kind": "url", "fields": {"text": "x"},
                            "logo_data": "not-an-image"})
    check("bad logo rejected", st == 400, f"HTTP {st}")
    st, j, _ = post("/qr", {"kind": "url", "fields": {"text": "https://a.b"},
                            "ec": "L", "logo_data": LOGO})
    check("logo forces EC H", st == 200 and j["ec"] == "H", str(j.get("ec")))

    print("\n== /img_fetch + /img_process ==")
    pb64, praw = photo_b64()
    st, j, _ = post("/img_fetch", {"file": {"name": "shot.jpg", "data": pb64}})
    check("img_fetch local", st == 200 and j["width"] == 1600 and j["height"] == 1000,
          str(j)[:80] if st != 200 else f"{j['width']}x{j['height']} {j['format']}")
    token = j.get("token")
    check("preview returned", bool(j.get("preview")))

    for name, body, want in [
        ("crop 1:1 + resize",
         {"file": {"token": token, "name": "shot.jpg"},
          "crop": {"x": 300, "y": 0, "w": 1000, "h": 1000},
          "out_w": 512, "out_h": 512, "fmt": "png"}, (512, 512)),
        ("9:16 jpg",
         {"file": {"token": token, "name": "shot.jpg"},
          "crop": {"x": 500, "y": 0, "w": 562, "h": 1000},
          "out_w": 1080, "out_h": 1920, "fmt": "jpg", "quality": 85}, (1080, 1920)),
        ("webp + gray",
         {"file": {"token": token, "name": "shot.jpg"}, "fmt": "webp",
          "quality": 80, "grayscale": True}, (1600, 1000)),
        ("rotate 90",
         {"file": {"token": token, "name": "shot.jpg"}, "rotate": 90}, (1000, 1600)),
        ("flip", {"file": {"token": token, "name": "shot.jpg"}, "flip": True},
         (1600, 1000)),
    ]:
        st, data, hdr = post("/img_process", body, raw=True)
        if st != 200:
            check(name, False, f"HTTP {st}: {str(data)[:90]}")
            continue
        im = Image.open(io.BytesIO(data))
        check(name, im.size == want,
              f"{im.size} {im.format} {len(data)//1024}KB {hdr.get('X-Info','')}")

    st, data, _ = post("/img_process",
                       {"file": {"token": "deadbeef", "name": "x.jpg"}}, raw=True)
    check("stale token -> 409", st == 409, f"HTTP {st}")
    st, j, _ = post("/img_fetch", {"url": "notaurl"})
    check("bad url rejected", st == 400, f"HTTP {st}")
    st, j, _ = post("/img_fetch", {"file": {"name": "x.txt",
                                            "data": base64.b64encode(b"hello").decode()}})
    check("non-image rejected", st == 400, f"HTTP {st}")

    print("\n== PDF routes still work ==")
    p4 = pdf_b64(4)
    st, j, _ = post("/inspect", {"file": {"name": "a.pdf", "data": p4},
                                 "thumbs": "cover"})
    check("inspect", st == 200 and j["pages"] == 4, str(j)[:80])
    st, data, hdr = post("/merge", {"files": [{"name": "a.pdf", "data": p4},
                                              {"name": "b.pdf", "data": pdf_b64(2)}]},
                         raw=True)
    check("merge", st == 200 and data[:4] == b"%PDF", f"{len(data)}B")
    st, data, hdr = post("/split", {"file": {"name": "a.pdf", "data": p4},
                                    "mode": "ranges", "ranges": "1-2,3-4"}, raw=True)
    check("split", st == 200 and data[:2] == b"PK", f"{len(data)}B zip")
    st, j, _ = post("/compress_preview", {"files": [{"name": "a.pdf", "data": p4}]})
    check("compress_preview", st == 200 and "presets" in j, str(j)[:70])
    st, data, _ = post("/convert", {"files": [{"name": "p.jpg", "data": pb64}],
                                    "route": "img2pdf"}, raw=True)
    check("img2pdf", st == 200 and data[:4] == b"%PDF", f"{len(data)}B")

    print("\n== /pdf2md ==")
    import base64 as _b64, subprocess as _sp, sys as _sys, os as _os
    _here = _os.path.dirname(_os.path.abspath(__file__))
    if not _os.path.exists("/tmp/paper.pdf"):
        _sp.run([_sys.executable, _os.path.join(_here, "make_test_paper.py")],
                check=True, capture_output=True)
    paper = _b64.b64encode(open("/tmp/paper.pdf", "rb").read()).decode()

    st, data, hdr = post("/pdf2md", {"file": {"name": "paper.pdf", "data": paper}},
                         raw=True)
    check("converts a pdf", st == 200, f"HTTP {st}: {str(data)[:80]}")
    check("returns a zip of md + figures", data[:2] == b"PK", f"{len(data)}B")
    if data[:2] == b"PK":
        import zipfile as _zf
        z = _zf.ZipFile(io.BytesIO(data))
        names = z.namelist()
        check("zip holds the markdown", any(n.endswith(".md") for n in names),
              str(names))
        check("zip holds cropped figures",
              sum(1 for n in names if "_fig" in n) >= 2, str(names))
        md = z.read([n for n in names if n.endswith(".md")][0]).decode()
        check("figures anchored in the markdown", md.count("![") >= 2)
        check("table came through", "| Round-robin |" in md)
        check("header present by default", "How to read this file" in md)
        check("no _INDEX.md unless asked",
              not any(n.endswith("_INDEX.md") for n in names), str(names))

    st, data, _ = post("/pdf2md", {"file": {"name": "paper.pdf", "data": paper},
                                   "index": True}, raw=True)
    if st == 200 and data[:2] == b"PK":
        import zipfile as _zf2
        names = _zf2.ZipFile(io.BytesIO(data)).namelist()
        check("index written when asked",
              any(n.endswith("_INDEX.md") for n in names), str(names))

    st, data, _ = post("/pdf2md", {"file": {"name": "paper.pdf", "data": paper},
                                   "images": False, "header": False}, raw=True)
    check("text-only mode returns a bare .md",
          st == 200 and data[:2] != b"PK", f"HTTP {st}, {len(data)}B")
    if st == 200 and data[:2] != b"PK":
        check("header suppressed", b"How to read this file" not in data)

    st, j, _ = post("/pdf2md", {"file": {"name": "x.pdf",
                                         "data": _b64.b64encode(b"nope").decode()}})
    check("garbage pdf rejected", st == 400, f"HTTP {st}")

    print("\n== error handling ==")
    st, j, _ = post("/nope", {})
    check("unknown route 404", st == 404, f"HTTP {st}")
    st, j, _ = post("/merge", {"files": []})
    check("empty merge 400", st == 400, f"HTTP {st}")
    st, j, _ = post("/yt_info", {"url": "notaurl"})
    check("yt_info bad url", st == 400, f"HTTP {st}")

finally:
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURES:\n  "
                                           + "\n  ".join(fails)))
sys.exit(1 if fails else 0)
