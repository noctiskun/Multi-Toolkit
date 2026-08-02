# Tests

Four suites. The Python ones verify the app itself; the Node ones boot the real
HTML in a simulated DOM and drive the controls.

| File | What it proves |
|---|---|
| `test_qr.py` | QR + image engines. **Every generated code is decoded back with zbar**, the reference decoder — style variants, logos, colours, transparency, unicode and dense v34 codes. |
| `test_server.py` | Every HTTP route end-to-end against a live server, including error paths, cache-miss 409s, and regression cover for the PDF routes. |
| `test_ui.js` | Boots the app's page in jsdom, clicks every tab and control, checks panel visibility and the crop/aspect maths. |
| `test_docs.js` | Boots `docs/index.html` with a real canvas, renders the QR demo and writes PNGs to `/tmp/qrdemo` for independent decoding. |
| `test_pages_layout.js` | Serves the page over real HTTP in **both** GitHub Pages layouts (publishing `/docs`, and publishing the repo root) and checks the QR library resolves either way. Written after a live failure where Pages published the root and `vendor/qrcode.js` 404'd. |
| `test_pdf2md.py` | PDF → Markdown accuracy, measured against a synthetic paper with **known ground truth** (`make_test_paper.py`): text survival, column reading order, figure/caption binding, crop sizes, table cell values, footnotes, furniture removal, and the failure modes. |
| `make_test_paper.py` | Builds that fixture — a two-column paper with a spanning figure, a table captioned above, footnotes, running heads and a scanned page. |
| `audit_design.py` | Static design audit of **both** the app UI and `docs/index.html`, in **both** themes: every class has a rule, no accidental duplicate selectors, real WCAG contrast for each text-on-surface pair, the two-accent rule (amber = measured fact, steel = interactive), and markup integrity. Pure Python, no extra packages. |

The markup check exists because of a real bug: an SVG data-URI favicon contained
raw `>` characters, a regex edit truncated the tag, and the leftover fragment
broke `<head>` — leaving a stray `">` visible at the top of the page. The audit
now fails on any attribute value containing a raw `>`.

## Running them

Python suites need a few extra packages that the app itself does not:

```bash
pip install pyzbar opencv-python-headless numpy
# pyzbar also needs the zbar shared library:
#   macOS:  brew install zbar
#   Linux:  apt install libzbar0
python tests/audit_design.py     # no extra packages needed
python tests/test_pdf2md.py     # needs pymupdf
python tests/test_qr.py
python tests/test_server.py
```

Node suites:

```bash
npm install jsdom canvas
node tests/test_ui.js
node tests/test_docs.js
node tests/test_pages_layout.js
```

To confirm the docs demo produces scannable codes, decode what `test_docs.js`
wrote:

```bash
python - <<'PY'
import json, glob
from PIL import Image
from pyzbar.pyzbar import decode
for f in sorted(glob.glob('/tmp/qrdemo/*.png')):
    im = Image.open(f).convert('RGBA')
    bg = Image.new('RGB', im.size, (255, 255, 255))
    bg.paste(im, mask=im.getchannel('A'))
    r = decode(bg)
    print(f.split('/')[-1], '->', r[0].data.decode() if r else 'NO DECODE')
PY
```

## A note on decoders

OpenCV's `QRCodeDetector` fails on high-version codes (roughly v20+) that zbar
and real phone cameras read without trouble. `test_qr.py` therefore treats zbar
as the source of truth and reports OpenCV as a stricter second opinion, not a
gate. A code that zbar reads but OpenCV misses is not a broken code.


## Two bugs these suites exist to prevent

**A raw `>` inside an attribute value.** An SVG data-URI favicon contained `>`
characters; a regex edit truncated the tag and the leftover fragment broke
`<head>`, leaving a stray `">` visible at the top of the page. `audit_design.py`
now fails on any attribute value containing a raw `>`.

**A bare `[hidden]` attribute.** Author styles outrank the user-agent sheet, so
`.row{display:flex}` silently overrode the browser's `[hidden]{display:none}`
and the logo controls stayed visible. jsdom's cascade does not reproduce this,
so the audit checks statically that a `[hidden]{display:none!important}` reset
exists wherever the markup uses the attribute.


## Why the PDF→MD suite uses a synthetic paper

Extraction quality cannot be eyeballed — output can look plausible while the
reading order silently zig-zags across columns, or a caption binds to the wrong
figure. `make_test_paper.py` builds a document whose exact contents are known,
so the tests can assert that "A precedes B", that Figure 2's caption is bound to
Figure 2, and that a crop is a crop rather than a whole page.

That fixture caught five real bugs that all passed a visual skim: paragraphs
breaking after their first line, columns merging into one paragraph, the title
being deleted along with the running head, figures landing mid-paragraph, and
table captions swallowing their own cell text.

It also caught a bug in itself — `insert_textbox` silently inserts nothing when
the box is too short, so an early version of the fixture "tested" a table that
contained no text at all. If a fixture can lie, check the fixture too.
