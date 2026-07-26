# Tests

Four suites. The Python ones verify the app itself; the Node ones boot the real
HTML in a simulated DOM and drive the controls.

| File | What it proves |
|---|---|
| `test_qr.py` | QR + image engines. **Every generated code is decoded back with zbar**, the reference decoder — style variants, logos, colours, transparency, unicode and dense v34 codes. |
| `test_server.py` | Every HTTP route end-to-end against a live server, including error paths, cache-miss 409s, and regression cover for the PDF routes. |
| `test_ui.js` | Boots the app's page in jsdom, clicks every tab and control, checks panel visibility and the crop/aspect maths. |
| `test_docs.js` | Boots `docs/index.html` with a real canvas, renders the QR demo and writes PNGs to `/tmp/qrdemo` for independent decoding. |
| `audit_design.py` | Static design audit of the app stylesheet: every class in the markup has a rule, no accidental duplicate selectors, real WCAG contrast ratios for each text-on-surface pair, and the two-accent rule (amber only for machine-reported data, steel only for interactive state). Pure Python, no extra packages. |

## Running them

Python suites need a few extra packages that the app itself does not:

```bash
pip install pyzbar opencv-python-headless numpy
# pyzbar also needs the zbar shared library:
#   macOS:  brew install zbar
#   Linux:  apt install libzbar0
python tests/audit_design.py     # no extra packages needed
python tests/test_qr.py
python tests/test_server.py
```

Node suites:

```bash
npm install jsdom canvas
node tests/test_ui.js
node tests/test_docs.js
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
