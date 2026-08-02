"""Build a synthetic two-column research paper whose exact contents we know,
so extraction accuracy can be measured instead of eyeballed.

Deliberately includes the things that break naive extractors:
  * two columns (reading order must not zig-zag across the gutter)
  * a vector figure and a raster figure, each with a caption BELOW
  * a table with a caption ABOVE (the opposite convention)
  * a figure spanning both columns at the top of a page
  * superscript footnote markers and a footnote block
  * an equation on its own line
  * running headers/footers that should be dropped
  * a page that is nothing but a full-page scan (no text layer)
"""
import json
import fitz

W, H = 595, 842                     # A4 points
M = 56                              # margin
GUT = 22                            # gutter
COLW = (W - 2 * M - GUT) / 2
LCOL = fitz.Rect(M, 96, M + COLW, H - 72)
RCOL = fitz.Rect(M + COLW + GUT, 96, W - M, H - 72)

truth = {"figures": [], "tables": [], "headings": [], "must_contain": [],
         "must_not_contain": [], "equations": [], "footnotes": []}

doc = fitz.open()


def furniture(page, n):
    """Running header and footer — extractors should drop these."""
    page.insert_text((M, 46), "Latency-Aware Scheduling for Interactive Rendering",
                     fontsize=8, fontname="helv", color=(.45, .45, .45))
    page.insert_text((W - M - 40, H - 40), f"Page {n} of 4",
                     fontsize=8, fontname="helv", color=(.45, .45, .45))


def flow(page, rect, blocks):
    """Insert a sequence of (kind, text) into a column, top-down."""
    y = rect.y0
    for kind, text in blocks:
        if kind == "h":
            size, font, gap = 11, "hebo", 14
        elif kind == "eq":
            size, font, gap = 10, "tiit", 16
        else:
            size, font, gap = 9.2, "helv", 10
        r = fitz.Rect(rect.x0, y, rect.x1, rect.y1)
        rc = page.insert_textbox(r, text, fontsize=size, fontname=font,
                                 align=fitz.TEXT_ALIGN_LEFT, lineheight=1.32)
        used = (r.height - rc) if rc >= 0 else r.height
        y += used + gap
    return y


# --------------------------------------------------------------- page 1 -----
p = doc.new_page(width=W, height=H)
furniture(p, 1)
p.insert_textbox(fitz.Rect(M, 62, W - M, 92),
                 "Latency-Aware Scheduling for Interactive Rendering",
                 fontsize=15, fontname="hebo", align=fitz.TEXT_ALIGN_CENTER)
truth["headings"].append("Latency-Aware Scheduling for Interactive Rendering")

flow(p, LCOL, [
    ("h", "1. Introduction"),
    ("p", "Interactive renderers must hit a frame deadline that users perceive "
          "directly. We study scheduling policies under a fixed budget and show "
          "that deadline-aware ordering reduces dropped frames substantially. "
          "Prior work assumes a static workload, which does not hold once "
          "geometry streaming is enabled.\u00b9"),
    ("h", "2. Background"),
    ("p", "Earliest-deadline-first is optimal for preemptive uniprocessor "
          "scheduling when utilisation stays below unity. Rendering violates "
          "that assumption because shader compilation is non-preemptible."),
])
truth["headings"] += ["1. Introduction", "2. Background"]
truth["must_contain"] += ["deadline-aware ordering reduces dropped frames",
                          "shader compilation is non-preemptible"]

y = flow(p, RCOL, [
    ("h", "3. Method"),
    ("p", "We model each frame as a task with release time r, service time c, "
          "and deadline d. The scheduler admits a task only when the residual "
          "budget satisfies the inequality below."),
    ("eq", "U = sum(c_i / p_i) <= n (2^(1/n) - 1)"),
    ("p", "Equation 1 is the classical utilisation bound. We extend it with a "
          "term for compilation stalls measured on device."),
])
truth["equations"].append("utilisation bound")
truth["must_contain"].append("residual budget satisfies the inequality")

# vector figure in the right column, caption BELOW
fx0, fy0 = RCOL.x0, y + 6
fig = fitz.Rect(fx0, fy0, RCOL.x1, fy0 + 118)
p.draw_rect(fig, color=(.25, .25, .25), width=.8)
for i in range(9):                     # a bar chart made of vector rects
    bx = fig.x0 + 12 + i * 24
    bh = 14 + (i * 11) % 74
    p.draw_rect(fitz.Rect(bx, fig.y1 - 12 - bh, bx + 15, fig.y1 - 12),
                fill=(.30, .42, .62), color=None)
p.insert_textbox(fitz.Rect(fig.x0, fig.y1 + 4, fig.x1, fig.y1 + 34),
                 "Figure 1: Dropped frames per policy across nine scenes. "
                 "Lower is better.", fontsize=8, fontname="helv")
truth["figures"].append({"page": 1, "label": "Figure 1",
                         "caption_has": "Dropped frames per policy",
                         "kind": "vector"})

# --------------------------------------------------------------- page 2 -----
p = doc.new_page(width=W, height=H)
furniture(p, 2)

# full-width raster figure across BOTH columns at the top
img = fitz.open()
ip = img.new_page(width=460, height=150)
ip.draw_rect(fitz.Rect(0, 0, 460, 150), fill=(.93, .93, .96), color=None)
for i in range(24):
    ip.draw_line(fitz.Point(i * 19, 150), fitz.Point(i * 19 + 40, 0),
                 color=(.55, .35, .30), width=1.1)
ip.insert_text((14, 24), "pipeline overview (screenshot)", fontsize=11,
               fontname="hebo")
pix = ip.get_pixmap(dpi=150)
img.close()
span = fitz.Rect(M, 96, W - M, 96 + 150)
p.insert_image(span, pixmap=pix)
p.insert_textbox(fitz.Rect(M, span.y1 + 4, W - M, span.y1 + 30),
                 "Figure 2: Overview of the rendering pipeline, annotated with "
                 "the two stalls we target.", fontsize=8, fontname="helv")
truth["figures"].append({"page": 2, "label": "Figure 2",
                         "caption_has": "Overview of the rendering pipeline",
                         "kind": "raster"})

L2 = fitz.Rect(M, span.y1 + 40, M + COLW, H - 72)
R2 = fitz.Rect(M + COLW + GUT, span.y1 + 40, W - M, H - 72)

flow(p, L2, [
    ("h", "4. Evaluation"),
    ("p", "We evaluate on nine scenes drawn from three engines. Each scene runs "
          "for 600 frames after a warm-up period of 120 frames. Frame times are "
          "captured with a hardware probe rather than in-process timers, which "
          "would perturb the measurement."),
])
truth["headings"].append("4. Evaluation")
truth["must_contain"].append("captured with a hardware probe")

# table with caption ABOVE — the opposite convention from figures
p.insert_textbox(fitz.Rect(R2.x0, R2.y0, R2.x1, R2.y0 + 26),
                 "Table 1: Dropped frames by policy.", fontsize=8, fontname="helv")
ty = R2.y0 + 24
rows = [("Policy", "Drops", "p99 ms"),
        ("Round-robin", "412", "38.4"),
        ("Priority", "266", "29.1"),
        ("EDF (ours)", "94", "21.7")]
colx = [R2.x0, R2.x0 + 96, R2.x0 + 148, R2.x1]
rh = 17
for ri, row in enumerate(rows):
    for ci, cell in enumerate(row):
        cr = fitz.Rect(colx[ci], ty + ri * rh, colx[ci + 1], ty + (ri + 1) * rh)
        p.draw_rect(cr, color=(.4, .4, .4), width=.6)
        # insert_text, not insert_textbox: a textbox silently inserts nothing
        # when the cell is too short, which once made this fixture a lie.
        p.insert_text((cr.x0 + 3, cr.y0 + 12), cell, fontsize=8,
                      fontname="hebo" if ri == 0 else "helv")
truth["tables"].append({"page": 2, "label": "Table 1",
                        "cells": ["Round-robin", "412", "EDF (ours)", "94", "21.7"]})

flow(p, fitz.Rect(R2.x0, ty + len(rows) * rh + 14, R2.x1, R2.y1), [
    ("p", "The EDF variant cuts dropped frames by 77% relative to round-robin "
          "while holding p99 latency below the 22 ms target."),
])
truth["must_contain"].append("cuts dropped frames by 77%")

# footnote block at the bottom of the left column
p.draw_line(fitz.Point(M, H - 116), fitz.Point(M + 120, H - 116),
            color=(.4, .4, .4), width=.6)
p.insert_textbox(fitz.Rect(M, H - 112, M + COLW, H - 74),
                 "\u00b9 Streaming was disabled in the 2019 study, so its "
                 "conclusions do not transfer.", fontsize=7.4, fontname="helv")
truth["footnotes"].append("Streaming was disabled in the 2019 study")

# --------------------------------------------------------------- page 3 -----
# a scanned page: an image covering the whole page, no text layer at all
p = doc.new_page(width=W, height=H)
scan = fitz.open()
sp = scan.new_page(width=W, height=H)
sp.draw_rect(fitz.Rect(0, 0, W, H), fill=(.97, .96, .93), color=None)
sp.insert_text((70, 130), "hand-drawn Gantt chart", fontsize=20, fontname="tiit")
for i in range(7):
    sp.draw_rect(fitz.Rect(80 + i * 12, 190 + i * 34, 300 + i * 30, 214 + i * 34),
                 fill=(.72, .74, .80), color=(.3, .3, .3))
spix = sp.get_pixmap(dpi=96)
scan.close()
p.insert_image(fitz.Rect(0, 0, W, H), pixmap=spix)
truth["figures"].append({"page": 3, "label": None, "caption_has": None,
                         "kind": "full-page-scan"})

# --------------------------------------------------------------- page 4 -----
p = doc.new_page(width=W, height=H)
furniture(p, 4)
flow(p, LCOL, [
    ("h", "5. Conclusion"),
    ("p", "Deadline-aware admission is a small change to an existing renderer "
          "and pays for itself on constrained hardware."),
    ("h", "References"),
    ("p", "[1] A. Researcher and B. Coauthor. Frame pacing under load. "
          "Proc. Rendering, 2019.\n[2] C. Third. Streaming geometry at scale. "
          "TOG, 2021."),
])
truth["headings"] += ["5. Conclusion", "References"]
truth["must_contain"].append("Frame pacing under load")

# things that must NOT survive into the markdown body
truth["must_not_contain"] = ["Page 1 of 4", "Page 2 of 4", "Page 4 of 4"]

doc.save("/tmp/paper.pdf")
doc.close()
json.dump(truth, open("/tmp/paper_truth.json", "w"), indent=1)
print("wrote /tmp/paper.pdf  (4 pages) and /tmp/paper_truth.json")
print("figures:", len(truth["figures"]), " tables:", len(truth["tables"]),
      " headings:", len(truth["headings"]))
