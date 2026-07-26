import base64
import io
import os
import sys

import cv2
import numpy as np
from PIL import Image, ImageDraw
from pyzbar.pyzbar import decode as zbar_decode

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from multi_toolkit import (op_qr, qr_payload,  # noqa: E402
                           op_img_process, img_describe)


def make_logo():
    """A chunky opaque-black figure on transparency — stands in for the Ronaldo cut-out."""
    im = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([170, 30, 230, 90], fill=(10, 10, 10, 255))          # head
    d.rectangle([160, 95, 240, 240], fill=(10, 10, 10, 255))       # torso
    d.polygon([(160, 100), (60, 200), (85, 225), (165, 140)], fill=(10, 10, 10, 255))
    d.polygon([(240, 100), (340, 200), (315, 225), (235, 140)], fill=(10, 10, 10, 255))
    d.rectangle([168, 240, 195, 370], fill=(10, 10, 10, 255))      # legs
    d.rectangle([205, 240, 232, 370], fill=(10, 10, 10, 255))
    b = io.BytesIO()
    im.save(b, "PNG")
    return base64.b64encode(b.getvalue()).decode()


def _on_white(b64):
    """Flatten to RGB on white — a QR is always scanned against a real surface."""
    im = Image.open(io.BytesIO(base64.b64decode(b64))).convert("RGBA")
    bg = Image.new("RGB", im.size, (255, 255, 255))
    bg.paste(im, mask=im.getchannel("A"))
    return bg


def decode(b64):
    """zbar is the reference decoder (what phone scanners behave like)."""
    r = zbar_decode(_on_white(b64))
    return r[0].data.decode("utf-8") if r else ""


def decode_cv(b64):
    """OpenCV too — stricter, and weak above ~v20. A second opinion, not a gate."""
    a = np.array(_on_white(b64))[:, :, ::-1].copy()
    txt, _, _ = cv2.QRCodeDetector().detectAndDecode(a)
    return txt


LOGO = make_logo()
URL = "https://github.com/noctis/multi-toolkit"
fails = []

cases = [
    ("plain",            dict(data=URL)),
    ("dots",             dict(data=URL, style="dots")),
    ("rounded",          dict(data=URL, style="rounded")),
    ("logo original",    dict(data=URL, logo_data=LOGO, logo_pct=22)),
    ("logo silhouette",  dict(data=URL, logo_data=LOGO, logo_pct=22,
                              logo_style="silhouette")),
    ("logo no pad",      dict(data=URL, logo_data=LOGO, logo_pct=20, pad=False,
                              logo_style="silhouette")),
    ("logo circle pad",  dict(data=URL, logo_data=LOGO, logo_pct=24,
                              pad_shape="circle")),
    ("logo + dots",      dict(data=URL, logo_data=LOGO, logo_pct=20, style="dots",
                              logo_style="silhouette")),
    ("coloured",         dict(data=URL, fg="#1b1035", bg="#f5f2ff")),
    ("transparent bg",   dict(data=URL, bg="transparent")),
    ("ec L",             dict(data=URL, ec="L")),
    ("small target",     dict(data=URL, target_px=256)),
    ("big target",       dict(data=URL, target_px=2048)),
    ("long text",        dict(data="x" * 900)),
    ("unicode",          dict(data="café ☕ 東京 — naïve")),
    ("border 0",         dict(data=URL, border=0)),
]

for name, kw in cases:
    try:
        r = op_qr(**kw)
    except Exception as e:                                        # noqa: BLE001
        fails.append(f"{name}: RAISED {e!r}")
        continue
    got = decode(r["image"])
    want = kw["data"]
    ok = got == want
    if not ok:
        fails.append(f"{name}: decoded {got[:40]!r} != {want[:40]!r}")
    cv = "cv2" if decode_cv(r["image"]) == want else "   "
    print(f"  {'ok ' if ok else 'FAIL'} {cv} {name:18s} v{r['version']:<3} "
          f"{r['modules']}mod {r['size']}px {r['bytes']//1024}KB "
          f"{'| ' + r['warn'][:60] if r['warn'] else ''}")

print("\n-- payload builders --")
for kind, fields, expect in [
    ("url", {"text": "example.com"}, "https://example.com"),
    ("url", {"text": "https://a.b"}, "https://a.b"),
    ("wifi", {"ssid": "My Net", "password": "p;w", "security": "WPA"}, None),
    ("email", {"to": "a@b.com", "subject": "hi there"}, None),
    ("sms", {"phone": "+1555", "message": "yo"}, None),
    ("phone", {"phone": "+1555"}, "tel:+1555"),
    ("geo", {"lat": "35.7", "lon": "-78.6"}, "geo:35.7,-78.6"),
    ("vcard", {"name": "Ada Lovelace", "email": "a@b.com", "org": "X"}, None),
]:
    out = qr_payload(kind, fields)
    if expect and out != expect:
        fails.append(f"payload {kind}: {out!r} != {expect!r}")
    print(f"  {kind:7s} {out[:70]!r}")
    r = op_qr(data=out)
    if decode(r["image"]) != out:
        fails.append(f"payload {kind}: did not round-trip through a QR")

print("\n-- empty input --")
try:
    op_qr(data="  ")
    fails.append("empty data should raise")
except Exception as e:                                            # noqa: BLE001
    print(f"  ok raises: {e}")

print("\n-- image pipeline --")
src = Image.new("RGB", (1600, 900))
for x in range(1600):
    for y in range(0, 900, 300):
        pass
src = Image.linear_gradient("L").resize((1600, 900)).convert("RGB")
b = io.BytesIO()
src.save(b, "JPEG", quality=92)
raw = b.getvalue()
info = img_describe(raw, "grad.jpg")
print(f"  describe: {info['width']}x{info['height']} {info['format']} "
      f"preview {len(info['preview'])//1024}KB")
for label, kw in [
    ("crop+resize", dict(crop={"x": 100, "y": 50, "w": 800, "h": 450}, out_w=400)),
    ("jpg q60", dict(fmt="jpg", quality=60)),
    ("webp", dict(fmt="webp", quality=80)),
    ("rotate 90", dict(rotate=90)),
    ("flip+gray", dict(flip=True, grayscale=True)),
    ("clamped crop", dict(crop={"x": 1500, "y": 800, "w": 9999, "h": 9999})),
    ("upscale", dict(out_w=3200)),
]:
    res, note = op_img_process(raw, "grad.jpg", **kw)
    nm, data = res[0]
    im2 = Image.open(io.BytesIO(data))
    print(f"  ok {label:14s} -> {nm:28s} {im2.size} {im2.format} {len(data)//1024}KB")

print("\n" + ("ALL PASS" if not fails else "FAILURES:\n  " + "\n  ".join(fails)))
sys.exit(1 if fails else 0)
