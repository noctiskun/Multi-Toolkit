# Multi Toolkit

**PDFs, video and QR codes in one browser tab — served by a single Python file running on your own machine.**

There is no account, no upload, no page limit and no build step. A small standard-library web server binds to `127.0.0.1`, your browser is the interface, and your files never leave your computer — because there is nowhere for them to go.

```bash
python multi_toolkit.py
```

That's the whole installation. Your browser opens automatically.

> **[Try the QR generator in your browser →](https://<your-username>.github.io/multi-toolkit/)**
> QR encoding needs no server, so that one feature runs live on the project page. Everything else needs the local app — see [Why the live page can't run everything](#why-the-live-page-cant-run-everything).

---

## Contents

- [Features](#features)
- [Quick start](#quick-start)
- [Optional extras](#optional-extras)
- [QR codes with a centre logo](#qr-codes-with-a-centre-logo)
- [Vertical video for Reels and Shorts](#vertical-video-for-reels-and-shorts)
- [Why the live page can't run everything](#why-the-live-page-cant-run-everything)
- [Privacy](#privacy)
- [Troubleshooting](#troubleshooting)
- [Project layout](#project-layout)
- [License](#license)

---

## Features

The interface is split into two groups. Each remembers the last tab you used, so switching back and forth doesn't lose your place.

### PDF

| Tab | What it does |
|---|---|
| **Merge** | Combine any number of PDFs. Drag rows to reorder; optionally add a bookmark per source file. |
| **Split** | A visual page grid. Click *between* pages to place cut points, or click pages to extract them. Also every-page, every-N, text ranges, and full drag-to-reorder with page deletion. |
| **Compress** | Four presets — lossless, quality, balanced, high — each showing a **real measured size** before you commit, not an estimate. Uses Ghostscript when available, pure Python otherwise. |
| **Convert** | Office → PDF, PDF → Word, PDF → PowerPoint, PDF → images (PNG/JPG), images → PDF. |

### Photo & Video

| Tab | What it does |
|---|---|
| **YouTube** | Pick resolution and container, watch live progress (%, speed, ETA). Optionally re-encodes to HEVC/H.264 with hardware acceleration so 4K actually plays in QuickTime. |
| **Reels** | The same engine pointed at Instagram, TikTok and Shorts, plus **9:16 reframing** — blurred backdrop, crop-to-fill, or black bars. Can borrow cookies from an installed browser for posts that need a signed-in session. |
| **Image** | Load from a URL or a local file. Drag a crop box (free, or locked to 1:1 / 4:5 / 9:16 / 16:9 / 3:2), rotate, flip, grayscale, resize, then export PNG / JPG / WebP. |
| **QR Code** | Links, text, Wi-Fi, email, SMS, phone, contact cards and coordinates — with a centre logo. Live preview. |

---

## Quick start

```bash
git clone https://github.com/<your-username>/multi-toolkit.git
cd multi-toolkit
python multi_toolkit.py
```

Requires **Python 3.8 or newer**. Nothing else is mandatory.

Python packages install themselves the first time a feature needs them, so the first merge or first QR code may pause for a few seconds. If you'd rather have everything ready up front:

```bash
pip install -r requirements.txt
```

Press <kbd>Ctrl</kbd>+<kbd>C</kbd> in the terminal to stop the server. If port 8000 is busy the app quietly moves to 8001, then 8080, then any free port, and prints the URL it settled on.

---

## Optional extras

The app runs without all of these. It detects what's present, shows the result as pills in the header, and only complains when you reach for a feature that genuinely needs something.

| Tool | Unlocks | Install |
|---|---|---|
| **ffmpeg** | Video above ~720p, and **all** 9:16 reframing | `brew install ffmpeg` · `winget install Gyan.FFmpeg` · `apt install ffmpeg` |
| **LibreOffice** | Office → PDF | [libreoffice.org/download](https://www.libreoffice.org/download) |
| **Ghostscript** | Much stronger PDF compression | `brew install ghostscript` · `winget install ArtifexSoftware.GhostScript` |

Restart the app after installing any of them so it re-detects.

Why ffmpeg matters for video: YouTube serves anything above 720p as *separate* video and audio streams. Without ffmpeg to merge them you are capped at whatever single combined stream exists, which is usually 720p.

---

## QR codes with a centre logo

The look where a figure or mark sits *inside* the code rather than on a white sticker comes down to three settings:

1. **Silhouette** for the logo look — flattens your image to a single colour matching the code, so it reads as part of the pattern.
2. **Backing plate off** — no white rectangle behind the logo.
3. **Error correction H** — set automatically the moment you add a logo.

Drop in any PNG (transparent background works best) and adjust the size slider. Under the hood:

- QR error correction level H recovers roughly **30%** of a damaged code, which is what buys you the room to cover the middle.
- **Finder patterns — the three big corner squares — are always drawn as crisp squares**, even in Dots or Rounded mode. Scanners lock onto those first, and rounding them is the quickest way to break an otherwise valid code.
- The app warns you when a choice costs you reliability: logo over ~25% coverage, quiet zone below 4 modules, low foreground/background contrast, light-on-dark, or a payload dense enough to need a clean print.

Payload types: link, plain text, Wi-Fi (WPA/WEP/open, with proper escaping), email, SMS, phone, vCard contact, and geo coordinates.

Output is PNG (with optional transparency) or JPG, at 512 / 1024 / 2048 / 4096 px.

> **Always scan a code with a real phone before you print it.** Every stylistic choice spends error-correction headroom, and a code that fails on a printed poster is expensive to discover late.

---

## Vertical video for Reels and Shorts

The Reels tab reframes any source aspect ratio onto a vertical canvas:

| Mode | Result | Use when |
|---|---|---|
| **Blurred backdrop** | Whole frame fits, blurred copy fills the gaps | Nothing may be cropped — the default |
| **Crop to fill** | Fills the frame, edges cut off | The subject is centred |
| **Black bars** | Whole frame fits, plain black padding | You want no invented detail |

Canvas sizes: 1080×1920 (Reels / Shorts / TikTok), 720×1280 (lighter file), 1080×1350 (Instagram feed 4:5).

Reframing re-encodes, so it uses hardware acceleration where available — VideoToolbox on Apple silicon, NVENC on NVIDIA — falling back to x264. The app verifies a hardware encoder actually works with a one-frame test encode before trusting it, because ffmpeg happily lists encoders for hardware you don't have.

**Sign-in cookies:** many Instagram posts require a logged-in session. The cookies dropdown borrows them from an installed browser. Leave it on *None* for public posts.

Only download videos you own or have permission to save.

---

## Why the live page can't run everything

**GitHub Pages serves static files only.** There is no Python process behind it, so merge, split, compress, convert, video download and image cropping genuinely cannot work there — they need code running on a machine.

The QR generator is the one exception, because QR encoding needs no server at all. The project page therefore ships a complete client-side implementation that mirrors the Python renderer: same module styles, same finder-pattern handling, same silhouette logic, same warnings.

To publish it: push the repo, then **Settings → Pages → Source: `main` branch, `/docs` folder**. That's it — no workflow file, no build step. The QR library is vendored in `docs/vendor/`, so the page has no external dependencies and works offline.

---

## Privacy

- The server binds to `127.0.0.1` and nothing else. It is not reachable from your network.
- Uploaded files live in memory under a random token, capped at 64 files / 600 MB, evicted oldest-first.
- Downloaded videos go to a temporary directory and are deleted immediately after being handed to your browser.
- No telemetry, no analytics, no network calls except the ones you explicitly ask for (fetching a video, fetching an image URL, or pip installing a dependency).

---

## Troubleshooting

**"Could not install 'X'"** — the app tries `pip install`, then `--user`, then `--break-system-packages`. On a managed Python you may need a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python multi_toolkit.py
```

**Video stops at 720p** — ffmpeg is missing. Install it and restart; the header pill will turn green.

**4K downloads won't play in QuickTime** — YouTube stores >1080p only as VP9/AV1, which QuickTime can't decode. Choose *QuickTime mp4* to re-encode, or *Original codec* and play it in VLC or IINA.

**Compression barely shrinks the file** — the PDF is mostly text and vectors with little raster imagery to recompress. Installing Ghostscript unlocks much stronger whole-file compression. The app tells you when it detects this.

**Instagram download fails** — the post likely needs a signed-in session. Pick your browser in the cookies dropdown. Make sure you're logged into Instagram in that browser first.

**QR code won't scan** — read the warning line under the preview. The usual causes are a logo over ~25% coverage, a quiet zone below 4, or low contrast. Raise error correction to H, shrink the logo, and re-test.

**Port already in use** — it falls back automatically. Check the terminal for the actual URL.

---

## Project layout

```
multi_toolkit.py        the entire application — server, engines and UI
requirements.txt        optional pre-install of the Python dependencies
docs/
  index.html            GitHub Pages landing page + live QR generator
  vendor/qrcode.js      vendored QR library (MIT, Kazuhiko Arase)
LICENSE
README.md
```

One file, no framework, no `node_modules`. Read it, audit it, change it.

---

## License

MIT — see [LICENSE](LICENSE).

QR rendering on the project page uses [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase (MIT). "QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

The bundled downloaders are thin wrappers around [yt-dlp](https://github.com/yt-dlp/yt-dlp). Respect the terms of service of any site you use them with, and only download material you own or have permission to save.
