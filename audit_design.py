"""Design audit for the app UI and the project page.

Checks the things a screenshot would not tell you reliably:
  * every class in the markup actually has a rule
  * no selector declared twice outside a media query
  * real WCAG contrast for every text-on-surface pair, in BOTH themes
  * the two-accent rule holds (amber = measured fact, steel = interactive)
  * markup integrity — in particular, an attribute value containing a raw ">",
    which is exactly how an SVG data-URI favicon once broke the whole <head>.
"""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
problems = []


def note(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'WARN'} {label}{' — ' + detail if detail else ''}")
    if not ok:
        problems.append(f"{label}: {detail}")


# --------------------------------------------------------------- colour ------
def rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[k:k + 2], 16) for k in (0, 2, 4))


def lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    r, g, b = rgb(c)
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def ratio(a, b):
    x, y = lum(a), lum(b)
    hi, lo = max(x, y), min(x, y)
    return (hi + 0.05) / (lo + 0.05)


def tokens(css, block=r":root\{"):
    m = re.search(block + r"(.*?)\}", css, re.S)
    if not m:
        return {}
    return dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{3,6})\b", m.group(1)))


# fg, bg, minimum ratio, what it is
PAIRS = [
    ("paper", "void",  4.5, "body text on chassis"),
    ("paper", "bench", 4.5, "body text on panel"),
    ("paper", "riser", 4.5, "body text on raised control"),
    ("dim",   "void",  4.5, "secondary text on chassis"),
    ("dim",   "bench", 4.5, "secondary text on panel"),
    ("faint", "void",  3.5, "silkscreen labels on chassis"),
    ("faint", "bench", 3.5, "silkscreen labels on panel"),
    ("amber", "void",  4.5, "measured data on chassis"),
    ("amber", "bench", 4.5, "measured data on panel"),
    ("steel", "void",  4.5, "interactive accent on chassis"),
    ("steel", "bench", 4.5, "interactive accent on panel"),
    ("rust",  "bench", 4.5, "destructive / error"),
    ("ok",    "bench", 4.5, "success"),
    ("on-steel",  "steel",     4.5, "ink on a solid steel fill"),
    ("on-amber",  "amber",     4.5, "ink on a solid amber fill"),
    ("steel-ink", "steel-dim", 4.5, "text on a steel-tinted chip"),
    ("warn-ink",  "warn-bg",   4.5, "warning text"),
    ("err-ink",   "err-bg",    4.5, "error text"),
]

AMBER_OK = ("readout", "ro-cell", "bar", "cut", "sz", "rng", "qrwarn", "range",
            "cropbox", "mark", "group.active", "amber", "pct", "warnline",
            "caption", "spec-head", "tagl", "note", "cmd")
STEEL_OK = ("tab", "chip", "pcard", "primary", "focus", "selection", "pg",
            "drop", "logodrop", "input", "select", "textarea", "files li",
            "checkbox", "cropwrap", "steel", "cut:hover", "grab", "ghost",
            "theme", "a{")


def check(name, css, html):
    print(f"\n=== {name} ===")

    # ---- class coverage ----
    used = set()
    for m in re.findall(r'class="([^"]+)"', html):
        used.update(w for w in m.split() if "$" not in w)
    dynamic = {"hide", "active", "on", "off", "show", "ok", "err", "hot", "big",
               "slim", "dragging", "wait", "cut", "reorderable", "danger",
               "primary", "check", "empty", "nw", "ne", "sw", "se", "h"}
    styled = set(re.findall(r"\.([A-Za-z][\w-]*)", css))
    missing = sorted(c for c in used if c not in styled and c not in dynamic)
    note(not missing, "every class in the markup has a rule", ", ".join(missing))

    # ---- duplicate selectors (media / theme blocks are deliberate overrides) --
    base = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
    base = re.sub(r':root\[data-theme[^{]*\{[^{}]*\}', "", base)
    sels = [re.sub(r"\s+", " ", x).strip()
            for x in re.findall(r"(?:^|\})\s*([^{}@/][^{}]*?)\{", base, re.M)]
    dupes = sorted({x for x in sels if sels.count(x) > 1})
    note(not dupes, "no selector declared twice outside overrides", "; ".join(dupes))

    # ---- markup integrity ----
    bad = [v[:50] for v in re.findall(r'="([^"]*)"', html) if ">" in v]
    note(not bad, "no attribute value contains a raw '>'", "; ".join(bad))
    note(html.count("<style") == html.count("</style>"), "style tags balanced")

    # ---- contrast in every theme ----
    dark = tokens(css)
    light = dict(dark)
    light.update(tokens(css, r':root\[data-theme="light"\]\{'))
    themes = [("dark", dark)] + ([("light", light)] if light != dark else [])
    for theme, tok in themes:
        print(f"  -- {theme} chassis --")
        for fg, bg, need, what in PAIRS:
            if fg not in tok or bg not in tok:
                continue
            r = ratio(tok[fg], tok[bg])
            note(r >= need, f"{what:36s} {tok[fg]} on {tok[bg]}",
                 f"{r:.2f}:1 (needs {need})")
        if "amber-lit" in tok:      # the readout keeps a dark ground in both
            r = ratio(tok["amber-lit"], "#0C0A08")
            note(r >= 4.5, f"{'READOUT value on its display':36s} "
                           f"{tok['amber-lit']} on #0C0A08", f"{r:.2f}:1")

    # ---- accent hygiene ----
    for tokname, allow in (("amber", AMBER_OK), ("steel", STEEL_OK)):
        rules = re.findall(r"([^{}]+)\{[^{}]*var\(--%s\)[^{}]*\}" % tokname, css)
        stray = [x.strip() for x in rules
                 if x.strip() != "a" and not any(k in x for k in allow)]
        note(not stray, f"{tokname} used only for its one job", "; ".join(stray))

    # ---- quality floor ----
    note("prefers-reduced-motion" in css, "reduced motion respected")
    note("focus-visible" in css, "visible keyboard focus")
    note("tabular-nums" in css, "numbers use tabular figures")
    note('data-theme="light"' in css, "a light chassis exists")
    note("aria-label" in html, "controls labelled for screen readers")


src = open(os.path.join(ROOT, "multi_toolkit.py")).read()
i = src.index('PAGE = r"""')
j = src.index('\n"""', i)
page = src[i + 11:j]
def markup(doc):
    """Everything but script bodies — the head now carries a theme script."""
    return re.sub(r"<script[^>]*>.*?</script>", "", doc, flags=re.S)


check("app UI", page[page.index("<style>"):page.index("</style>")], markup(page))

doc = open(os.path.join(ROOT, "docs", "index.html")).read()
check("project page", doc[doc.index("<style>"):doc.index("</style>")], markup(doc))

print("\n" + ("DESIGN AUDIT CLEAN" if not problems
              else f"{len(problems)} ISSUE(S):\n  " + "\n  ".join(problems)))
sys.exit(1 if problems else 0)
