"""vvg9 - place front and back side by side, and write the region reference.

Handles two structurally different SVG shapes:

  * the named-region files wrap everything in <g transform="translate(...)
    scale(...)">, so the inner content is lifted out and the transform is
    reapplied per view
  * the teal/hybrid/render files have no wrapper, so the whole body is taken

Ids get prefixed with front- / back- so the combined file has no duplicates.
That matters: duplicate ids make getElementById and CSS id selectors
unreliable.

Usage:
    python vvg9_combine.py regions        # the named-region files
    python vvg9_combine.py teal|hybrid|render
"""
import os
import re
import sys

import vvg_config as C

KINDS = {
    "regions": ("body-{v}-regions.svg", "body-front-back-regions.svg", True),
    "teal":    ("teal-body-{v}.svg",    "teal-body-front-back.svg",    False),
    "hybrid":  ("hybrid-body-{v}.svg",  "hybrid-body-front-back.svg",  False),
    "render":  ("render-{v}.svg",       "render-front-back.svg",       False),
}


def prefix_ids(t, p):
    t = re.sub(r'<g id="([a-z0-9\-]+)"', lambda m: f'<g id="{p}-{m.group(1)}"', t)
    t = re.sub(r'<path id="([a-z0-9\-]+)"', lambda m: f'<path id="{p}-{m.group(1)}"', t)
    return t


def inner_wrapped(t):
    """Content inside the outer <g transform=...> wrapper."""
    return t[t.index(">", t.index("<g transform=")) + 1: t.rindex("</g>")]


def inner_plain(t):
    """Everything between <svg ...> and </svg>, minus any <style> block."""
    body = t[t.index(">", t.index("<svg")) + 1: t.rindex("</svg>")]
    return re.sub(r'<style>.*?</style>', '', body, flags=re.S)


def combine(kind):
    pat, outname, wrapped = KINDS[kind]
    svgs = {v: open(f"{C.OUT}/{pat.format(v=v)}").read() for v in ("front", "back")}

    m = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svgs["front"])
    W, H = float(m.group(1)), float(m.group(2))
    mb = re.search(r'viewBox="0 0 ([\d.]+) ([\d.]+)"', svgs["back"])
    Wb, Hb = float(mb.group(1)), float(mb.group(2))
    H = max(H, Hb)
    gap = W * 0.10
    tot = W + gap + Wb

    if wrapped:
        tr = f"translate(0,{H:g}) scale(0.1,-0.1)"
        front = f'  <g id="view-front" transform="{tr}">\n{inner_wrapped(svgs["front"])}\n  </g>'
        back = (f'  <g id="view-back" transform="translate({W + gap:g},0) {tr}">\n'
                f'{inner_wrapped(svgs["back"])}\n  </g>')
        style = ['  <style>',
                 f'    .region {{ fill: {C.ART_FILL}; transition: fill .15s; }}',
                 f'    .lines  {{ fill: {C.ART_LINE}; pointer-events: none; }}',
                 '  </style>']
        px = int(tot / C.PT_DIV), int(H / C.PT_DIV)
    else:
        front = f'  <g id="view-front">\n{inner_plain(svgs["front"])}\n  </g>'
        back = (f'  <g id="view-back" transform="translate({W + gap:g},0)">\n'
                f'{inner_plain(svgs["back"])}\n  </g>')
        style = ['  <style></style>']
        px = int(tot / 2), int(H / 2)

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {tot:g} {H:g}"'
           f' width="{px[0]}" height="{px[1]}">'] + style + \
          [prefix_ids(front, "front"), prefix_ids(back, "back"), '</svg>']

    fn = f"{C.OUT}/{outname}"
    open(fn, "w").write("\n".join(out))
    print(f"{kind}: -> {outname} ({os.path.getsize(fn) // 1024} KB)")


def write_reference():
    """Markdown sheet listing every region id, grouped by muscle."""
    lines = ["# Body Diagram - Region Reference", "",
             "Every region is a separate `<path>` with a unique `id`, wrapped in a named `<g>`.",
             "Set `fill` on a group to colour a whole muscle, or on one path for a single region.",
             "",
             "Sides are ANATOMICAL. On the front view, viewer-left is the subject's RIGHT.",
             ""]
    for v in ("front", "back"):
        t = open(f"{C.OUT}/body-{v}-regions.svg").read()
        lines += [f"## {v.capitalize()} view", ""]
        for g in sorted(set(re.findall(r'<g id="([a-z\-]+)">', t))):
            blk = re.search(r'<g id="%s">(.*?)</g>' % g, t, re.S).group(1)
            ids = re.findall(r'<path id="([^"]+)"', blk)
            lines.append(f"- **{g}** ({len(ids)}): " + ", ".join(f"`{i}`" for i in ids))
        lines.append("")
    open(f"{C.OUT}/REGIONS.md", "w").write("\n".join(lines))
    print("wrote out/REGIONS.md")


if __name__ == "__main__":
    C.ensure_dirs()
    kind = sys.argv[1] if len(sys.argv) > 1 else "regions"
    assert kind in KINDS, f"kind must be one of {list(KINDS)}"
    combine(kind)
    if kind == "regions":
        write_reference()
