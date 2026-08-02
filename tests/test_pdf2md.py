"""Measure PDF->Markdown extraction against a paper whose contents we know.

This is the suite that matters for research papers: it checks that text
survives, that reading order does not zig-zag across columns, that each figure
is bound to its own caption, that tables come out as tables, and that page
furniture is dropped.
"""
import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

HERE = os.path.dirname(os.path.abspath(__file__))
if not os.path.exists("/tmp/paper.pdf"):
    subprocess.run([sys.executable, os.path.join(HERE, "make_test_paper.py")],
                   check=True, capture_output=True)

from multi_toolkit import op_pdf2md  # noqa: E402

truth = json.load(open("/tmp/paper_truth.json"))
raw = open("/tmp/paper.pdf", "rb").read()
fails = []


def check(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'FAIL'} {label}{' — ' + detail if detail else ''}")
    if not ok:
        fails.append(f"{label}{' — ' + detail if detail else ''}")


files, summary = op_pdf2md(raw, "paper.pdf")
md = files[0][1].decode()
imgs = {n for n, _ in files[1:]}
open("/tmp/paper_out.md", "w").write(md)

print("=== output shape ===")
check(files[0][0] == "paper.md", "markdown named after the source", files[0][0])
check(len(files) - 1 == summary["images"], "image count matches summary",
      f"{len(files)-1} files, summary says {summary['images']}")
print(f"       {len(md)} chars of markdown, {len(files)-1} images, "
      f"{summary['figures']} figures, {summary['tables']} tables, "
      f"{summary['page_images']} page images")

print("\n=== text survived ===")
for frag in truth["must_contain"]:
    flat = re.sub(r"\s+", " ", md)
    check(frag in flat, f"kept: {frag[:52]}")

print("\n=== page furniture dropped ===")
body = md.split("-->", 1)[-1]
for frag in truth["must_not_contain"]:
    check(frag not in body, f"dropped running header/footer: {frag}")
check(md.count("Latency-Aware Scheduling") <= 2,
      "running header not repeated on every page",
      f"appears {md.count('Latency-Aware Scheduling')}x")

print("\n=== reading order (two columns must not interleave) ===")
flat = re.sub(r"\s+", " ", md)
pairs = [
    ("deadline-aware ordering", "shader compilation is non-preemptible"),
    ("shader compilation is non-preemptible", "residual budget"),
    ("captured with a hardware probe", "cuts dropped frames by 77%"),
]
for a, b in pairs:
    ia, ib = flat.find(a), flat.find(b)
    check(ia != -1 and ib != -1 and ia < ib,
          f"'{a[:30]}' precedes '{b[:30]}'", f"{ia} vs {ib}")

print("\n=== headings ===")
heads = re.findall(r"^#{1,4} (.+)$", md, re.M)
for h in truth["headings"]:
    check(any(h.lower() in x.lower() for x in heads), f"heading: {h}",
          "" if any(h.lower() in x.lower() for x in heads) else str(heads[:8]))

print("\n=== figures: cropped, anchored, captioned ===")
found = {f["label"]: f for f in summary["figure_list"] if f["label"]}
for want in truth["figures"]:
    if want["label"]:
        f = found.get(want["label"])
        check(f is not None, f"{want['label']} detected and labelled",
              f"got {sorted(found)}")
        if f:
            check(want["caption_has"].lower() in (f["caption"] or "").lower(),
                  f"{want['label']} bound to its own caption",
                  (f["caption"] or "")[:60])
            check(f["file"] in imgs, f"{want['label']} image written", f["file"])
            check(f"({f['file']})" in md, f"{want['label']} anchored in the md")
            # the anchor must sit next to its caption, not elsewhere
            i = md.find(f"({f['file']})")
            near = md[i:i + 400]
            check(want["caption_has"][:24].lower() in near.lower(),
                  f"{want['label']} caption sits with its image")
    else:
        check(summary["page_images"] >= 1, "scanned page exported as a full page")

print("\n=== figures are CROPS, not whole pages ===")
crops = [n for n in imgs if "_fig" in n]
check(len(crops) >= 2, f"at least two cropped figures", str(sorted(crops)))
try:
    from PIL import Image
    import io
    sizes = {}
    for n, d in files[1:]:
        im = Image.open(io.BytesIO(d))
        sizes[n] = im.size
    page_h = max(h for _, h in sizes.values())
    for n in crops:
        w, h = sizes[n]
        check(h < page_h * 0.55, f"{n} is a crop, not a full page",
              f"{w}x{h} vs page height {page_h}")
except ImportError:
    print("       (Pillow missing — skipped size check)")

print("\n=== tables ===")
check(summary["tables"] >= 1, "a table was detected", str(summary["tables"]))
check("|---" in md or "| ---" in md, "emitted as a markdown table")
for cell in truth["tables"][0]["cells"]:
    check(cell in md, f"table cell present: {cell}")
rowline = [l for l in md.splitlines() if l.startswith("|") and "EDF" in l]
check(bool(rowline), "EDF row is a real table row", rowline[0] if rowline else "")
if rowline:
    check(rowline[0].count("|") >= 4, "row has multiple columns", rowline[0])

print("\n=== footnotes and equations ===")
check(any(truth["footnotes"][0] in l for l in md.splitlines()),
      "footnote text kept")
check("$$" in md or "U =" in md, "equation line preserved")

print("\n=== self-describing header ===")
for frag in ["How to read this file", "<!-- page", "cropped from the page"]:
    check(frag in md, f"header explains: {frag}")
check("Lower confidence" in md, "warns about the scanned page")

print("\n=== header can be turned off ===")
f2, s2 = op_pdf2md(raw, "paper.pdf", want_header=False)
check("How to read this file" not in f2[0][1].decode(), "header suppressed")

print("\n=== options behave ===")
f3, s3 = op_pdf2md(raw, "paper.pdf", want_images=False)
check(len(f3) == 1, "images off -> markdown only", f"{len(f3)} files")
f4, s4 = op_pdf2md(raw, "paper.pdf", page_from=2, page_to=2)
check(s4["pages"] == 1, "page range honoured", str(s4["pages"]))
check("Overview of the rendering pipeline" in f4[0][1].decode(),
      "page range keeps that page's content")

print("\n=== other layouts ===")
import fitz  # noqa: E402

def _pdf(build):
    d = fitz.open()
    build(d)
    b = d.tobytes()
    d.close()
    return b

def _one_col(d):
    p = d.new_page()
    p.insert_textbox(fitz.Rect(60, 60, 530, 700),
                     "Single column body text that runs the full width. " * 22,
                     fontsize=10)

def _three_col(d):
    p = d.new_page()
    for i, x in enumerate((50, 220, 390)):
        p.insert_textbox(fitz.Rect(x, 80, x + 150, 700),
                         f"Column {i+1} sentence one here. " * 14, fontsize=9)

def _rotated(d):
    p = d.new_page()
    p.insert_textbox(fitz.Rect(60, 60, 530, 400),
                     "Rotated page body text that must survive intact. " * 8,
                     fontsize=11)
    p.set_rotation(90)

f5, s5 = op_pdf2md(_pdf(_one_col), "one.pdf")
flat5 = re.sub(r"\s+", " ", f5[0][1].decode())
check("Single column body text that runs the full width." in flat5,
      "single column: no phantom columns")

f6, s6 = op_pdf2md(_pdf(_three_col), "three.pdf")
flat6 = re.sub(r"\s+", " ", f6[0][1].decode())
i1, i2, i3 = (flat6.find(f"Column {k}") for k in (1, 2, 3))
check(-1 not in (i1, i2, i3) and i1 < i2 < i3,
      "three columns read left to right, not interleaved", f"{i1}, {i2}, {i3}")

f7, s7 = op_pdf2md(_pdf(_rotated), "rot.pdf")
check("must survive intact" in re.sub(r"\s+", " ", f7[0][1].decode()),
      "rotated page still extracts")

print("\n=== refuses to fail silently ===")
from multi_toolkit import FeatureError  # noqa: E402
for label, blob in [("garbage", b"not a pdf at all"), ("empty", b"")]:
    try:
        op_pdf2md(blob, "x.pdf")
        check(False, f"{label} rejected", "it was accepted")
    except FeatureError as e:
        check(True, f"{label} rejected", str(e)[:44])
d = fitz.open()
d.new_page().insert_text((70, 70), "secret")
enc = d.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="pw")
d.close()
try:
    op_pdf2md(enc, "enc.pdf")
    check(False, "encrypted rejected", "it was accepted")
except FeatureError as e:
    check(True, "encrypted rejected", str(e)[:44])

print("\n=== token economy ===")
pdf_kb = len(raw) / 1024
md_kb = len(md.encode()) / 1024
check(md_kb < pdf_kb, "markdown smaller than the pdf",
      f"{md_kb:.1f}KB vs {pdf_kb:.1f}KB")
print(f"       ~{len(md)//4} tokens of text (vs shipping a {pdf_kb:.0f}KB PDF)")

print("\n" + ("ALL PASS" if not fails else f"{len(fails)} FAILURE(S):\n  "
                                           + "\n  ".join(fails)))
sys.exit(1 if fails else 0)
