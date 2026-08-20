"""vvg5 - verify the naming is actually correct.

Recolours every muscle group a distinct bright colour and renders the
result. A wrong name is obvious at a glance: a group that should be a
symmetric pair lights up on only one side, or a highlight lands somewhere
anatomically absurd.

Rendered with CairoSVG, never ImageMagick. ImageMagick's SVG renderer only
matches trivial single-class CSS selectors (.m does not match
class="m quadriceps") and silently drops strokes on large complex paths. It
burned three debugging rounds where the geometry was fine and only the
preview was broken.

Output: out/_verify_{view}.png
"""
import re

import cairosvg

import vvg_config as C

PAL = ["#e6194b", "#3cb44b", "#ffe119", "#4363d8", "#f58231", "#911eb4",
       "#00cec9", "#f032e6", "#bcf60c", "#fabebe", "#008080", "#e6beff",
       "#9a6324", "#d4b106", "#800000", "#55efc4", "#808000", "#ffd8b1",
       "#000075", "#a9a9a9", "#00b894", "#d63031", "#6c5ce7", "#fd79a8"]


def verify(view, width=780):
    src = f"{C.OUT}/body-{view}-regions.svg"
    t = open(src).read()
    grps = sorted(set(re.findall(r'<g id="([a-z\-]+)">', t)))
    col = {g: PAL[i % len(PAL)] for i, g in enumerate(grps)}

    def sub(m):
        return m.group(0).replace(f'fill="{C.ART_FILL}"', f'fill="{col[m.group(1)]}"')

    t2 = re.sub(r'<path id="[^"]+" class="region ([a-z\-]+)" fill="%s"' % C.ART_FILL, sub, t)
    tmp = f"{C.TMP}/_verify_{view}.svg"
    open(tmp, "w").write(t2)
    cairosvg.svg2png(url=tmp, write_to=f"{C.OUT}/_verify_{view}.png",
                     output_width=width, background_color="white")
    print(f"{view}: {len(grps)} groups recoloured -> out/_verify_{view}.png")


if __name__ == "__main__":
    C.ensure_dirs()
    for v in ("front", "back"):
        verify(v)
