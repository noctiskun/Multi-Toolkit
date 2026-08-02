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
- [PDF → Markdown, for LLMs](#pdf--markdown-for-llms)
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

## PDF → Markdown, for LLMs

Pasting a research paper into an LLM is expensive and lossy: the PDF is mostly
font tables and compression, and if you screenshot it you lose the text. This
converts it the other way round — **text stays text**, and only the figures
become images.

```bash
# one paper
python multi_toolkit.py md paper.pdf ./out

# a folder of them, with an audit index
python multi_toolkit.py md ~/papers ./out --index

# just the parts you need
python multi_toolkit.py md paper.pdf ./out --pages 3-12 --dpi 240
```

Or use the **PDF → MD** tab, which does the same thing and hands you a zip.

### What comes out

```
out/attention-is-all-you-need/
  attention-is-all-you-need.md          <- paste this
  attention-is-all-you-need_p003_fig01.png
  attention-is-all-you-need_p006_fig02.png
```

The `.md` opens with a short header explaining its own layout, so **you do not
need to write a covering instruction** when you hand it to a model:

```markdown
> **How to read this file.** It was converted from a PDF (`paper.pdf`).
> Text is real extracted text. Images are cropped from the page and appear at
> the point in the reading order where they occur, so the figure above a
> caption is the figure that caption describes. `<!-- page N -->` marks where
> each PDF page begins.
> **Lower confidence on page(s) 7** — little or no extractable text there, so
> trust the image over the text.
```

### Figures are cropped, not screenshotted

Each figure is cut to its own bounding box and placed at the point in the
reading order where it occurs, immediately above its own caption:

```markdown
![Figure 3](paper_p006_fig03.png)

*Figure 3: Attention weights across heads, layer 4.*
```

Captions are matched by proximity and searched both above and below the block,
because figures caption below and tables caption above. A figure in the right
column is emitted while reading the right column — not dropped into the middle
of a left-column paragraph.

### What survives

| | |
|---|---|
| **Reading order** | Column-aware. Gutters are found by projecting text onto the x-axis, so one, two and three-column layouts all read correctly. Titles and full-width figures act as barriers rather than confusing the sweep. |
| **Headings** | `#` levels from font size, weight and numbering (`3.1 Method`). |
| **Tables** | Real Markdown tables, rebuilt from ruling geometry plus text position — works for both full cell grids and booktabs-style rules. |
| **Equations** | Fenced in `$$` when a line is mostly mathematical. |
| **Footnotes** | Kept as blockquotes, with wrapped continuation lines joined. |
| **Running heads** | Dropped — detected by repetition across pages, with a size guard so a title that matches the running head survives. |

### When it is not sure, it says so

A page with no usable text layer is exported whole, marked in the body, and
listed in the header. That is the point: a mangled page you cannot see is worse
than a page image you can.

```markdown
<!-- page 7: no text layer; full page image -->
![Page 7 (scanned — no text layer)](paper_p007.png)
```

### Options

| CLI | Tab | Effect |
|---|---|---|
| `--no-images` | Extract figures | Text only, no PNGs at all |
| `--no-tables` | Tables as Markdown | Leave tables as loose text |
| `--no-math` | Equations as LaTeX | No `$$` fencing |
| `--no-header` | Explain-itself header | Omit the preamble |
| `--index` | Also write _INDEX.md | Batch audit table — **off by default** |
| `--pages 3-12` | Pages | Convert a range only |
| `--dpi 240` | Figure quality | Raster detail for the crops |

`_INDEX.md` is for *you* reviewing a batch — which papers converted, how many
figures each has, and which pages need your own eyes. A single paper does not
need it, because its own header already explains itself.

### Known limits

- **Heavily designed layouts** (magazines, posters, pull-quotes) will confuse the
  column sweep. Ordinary papers, reports and theses are the target.
- **RTL scripts are untested.** Arabic and Hebrew may come out in visual rather
  than logical order.
- **Equation detection is heuristic.** Inline maths inside a sentence stays
  inline text; only display equations get fenced.
- **Scanned PDFs are not OCR'd.** They are exported as page images and flagged —
  run OCR first if you need the text.

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

### Publishing it

**Settings → Pages → Build and deployment → Source: "Deploy from a branch" → Branch `main`, folder `/docs` → Save.** No workflow file, no build step.

If Pages is publishing the **repo root** instead, the root `index.html` is a small redirect into `docs/`, so the site still works. It is a pointer, not a second copy — there is only ever one real page, at `docs/index.html`.

Two symptoms and what they mean:

| What you see | What it means |
|---|---|
| Your README, rendered with a blue heading and a Contents list | Pages is publishing the root and found no `index.html` there, so Jekyll rendered `README.md` instead. Switch the source to `/docs`. |
| The page loads but says **"qr library did not load"** | `qrcode.js` 404'd. Open the Network tab and check the path it asked for — that tells you which folder Pages thinks it is serving. |

Both arrangements are covered by `tests/test_pages_layout.js`, which serves the page over real HTTP in each and checks a code actually renders.

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
index.html              redirect stub, used only if Pages publishes the root
docs/
  index.html            the project page + live QR generator
  vendor/qrcode.js      vendored QR library (MIT, Kazuhiko Arase)
tests/                  five suites — see tests/README.md
LICENSE
README.md
```

One file, no framework, no `node_modules`. Read it, audit it, change it.

---

## License

MIT — see [LICENSE](LICENSE).

QR rendering on the project page uses [qrcode-generator](https://github.com/kazuhikoarase/qrcode-generator) by Kazuhiko Arase (MIT). "QR Code" is a registered trademark of DENSO WAVE INCORPORATED.

The bundled downloaders are thin wrappers around [yt-dlp](https://github.com/yt-dlp/yt-dlp). Respect the terms of service of any site you use them with, and only download material you own or have permission to save.
