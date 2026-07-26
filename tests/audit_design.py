"""Audit the app stylesheet: unstyled classes, dead rules, duplicate declarations,
and real WCAG contrast ratios for every text colour actually used on a surface."""
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
src = open(os.path.join(ROOT, "multi_toolkit.py")).read()
i = src.index('PAGE = r"""')
j = src.index('\n"""', i)
page = src[i + 11:j]
css = page[page.index("<style>"):page.index("</style>")]
html = page.split("<script>")[0]
js = page.split("<script>")[1]

problems = []


def note(ok, label, detail=""):
    print(f"  {'ok  ' if ok else 'WARN'} {label}{' — ' + detail if detail else ''}")
    if not ok:
        problems.append(f"{label}: {detail}")


# ---------------------------------------------------------------- classes ----
used = set()
for m in re.findall(r'class="([^"]+)"', html):
    used.update(m.split())
for m in re.findall(r"classList\.(?:add|remove|toggle)\('([\w-]+)'", js):
    used.add(m)
for m in re.findall(r"className\s*=\s*'([^']+)'", js):
    used.update(w for w in m.replace("+", " ").split() if w.isidentifier() or "-" in w)
for m in re.findall(r'class=\\"([^\\"]+)\\"', js):
    used.update(w for w in m.split() if "$" not in w)

styled = set(re.findall(r"\.([A-Za-z][\w-]*)", css))
dynamic = {"hide", "active", "on", "off", "show", "ok", "err", "hot", "big",
           "slim", "dragging", "wait", "cut", "reorderable", "danger", "primary",
           "check", "empty", "nw", "ne", "sw", "se", "h"}

missing = sorted(c for c in used if c not in styled and c not in dynamic)
note(not missing, "every class in the markup has a rule", ", ".join(missing))

print()
# ------------------------------------------------------- duplicate blocks ----
# Same selector declared twice is legal but usually accidental.
# Rules inside @media are deliberate overrides, so compare only within a scope.
base = re.sub(r"@media[^{]*\{(?:[^{}]*\{[^{}]*\})*[^{}]*\}", "", css)
sels = [re.sub(r"\s+", " ", x).strip()
        for x in re.findall(r"(?:^|\})\s*([^{}@/][^{}]*?)\{", base, re.M)]
dupes = sorted({x for x in sels if sels.count(x) > 1})
note(not dupes, "no selector declared twice outside media queries", "; ".join(dupes))

print()
# ------------------------------------------------------------- contrast -----
tok = dict(re.findall(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})", css))


def rgb(h):
    h = h.lstrip("#")
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


# fg, bg, min ratio, what it is
pairs = [
    ("paper", "void",  4.5, "body text on chassis"),
    ("paper", "bench", 4.5, "body text on panel"),
    ("paper", "riser", 4.5, "body text on raised control"),
    ("dim",   "void",  4.5, "secondary text on chassis"),
    ("dim",   "bench", 4.5, "secondary text on panel"),
    ("faint", "bench", 3.5, "silkscreen labels on panel"),
    ("faint", "void",  3.5, "silkscreen labels on chassis"),
    ("amber", "void",  4.5, "READOUT — the signature element"),
    ("amber", "bench", 4.5, "readout value on panel"),
    ("steel", "void",  4.5, "interactive accent on chassis"),
    ("steel", "bench", 4.5, "interactive accent on panel"),
    ("rust",  "bench", 4.5, "destructive/error on panel"),
    ("ok",    "bench", 4.5, "success on panel"),
]
for fg, bg, need, what in pairs:
    if fg not in tok or bg not in tok:
        note(False, f"token missing for {fg}/{bg}")
        continue
    r = ratio(tok[fg], tok[bg])
    note(r >= need, f"{what:48s} {tok[fg]} on {tok[bg]}",
         f"{r:.2f}:1 (needs {need})" if r < need else f"{r:.2f}:1")

# The primary button reverses: dark ink on the steel fill.
r = ratio("#0B1219", tok["steel"])
note(r >= 4.5, f"{'primary button ink on steel fill':48s} #0B1219 on {tok['steel']}",
     f"{r:.2f}:1")

print()
# --------------------------------------------------------- accent hygiene ---
# Amber = machine-reported fact. Steel = actionable. Nothing else may use them.
amber_rules = re.findall(r"([^{}]+)\{[^{}]*var\(--amber\)[^{}]*\}", css)
steel_rules = re.findall(r"([^{}]+)\{[^{}]*var\(--steel\)[^{}]*\}", css)
amber_ok = ("readout", "ro-cell", "bar", "cut", "sz", "rng", "qrwarn", "range",
            "cropbox", "mark", "group.active", "amber")
steel_ok = ("tab", "chip", "pcard", "primary", "focus", "selection", "pg",
            "drop", "logodrop", "input", "select", "textarea", "files li",
            "checkbox", "cropwrap", "steel", "cut:hover")
stray_a = [s.strip() for s in amber_rules
           if not any(k in s for k in amber_ok)]
stray_s = [s.strip() for s in steel_rules
           if not any(k in s for k in steel_ok)]
note(not stray_a, "amber used only for machine-reported data", "; ".join(stray_a))
note(not stray_s, "steel used only for interactive state", "; ".join(stray_s))

print()
# -------------------------------------------------------------- floor -------
note("prefers-reduced-motion" in css, "reduced motion respected")
note(":focus-visible" in css, "visible keyboard focus")
note("max-width:720px" in css, "collapses to a mobile layout")
note("tabular-nums" in css, "numbers use tabular figures")
note(html.count("aria-") >= 2, "some ARIA present", f"{html.count('aria-')} attrs")

print("\n" + ("DESIGN AUDIT CLEAN" if not problems
              else f"{len(problems)} ISSUE(S):\n  " + "\n  ".join(problems)))
sys.exit(1 if problems else 0)
