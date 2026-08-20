"""vvg_config - one place for every path, palette and tunable.

Every vvg stage imports this. If a number feels magic, it lives here with a
note about why it has that value. Nothing else in src/ should hard-code a
file path.
"""
import os

# ---------------------------------------------------------------------------
# folders
# ---------------------------------------------------------------------------
IN = "input"
OUT = "out"
TMP = os.path.join(OUT, "tmp")

# The flat two-colour line art. This is where all the named muscle
# regions come from.
ART = {"front": f"{IN}/art-front.jpg",
        "back":  f"{IN}/art-back.jpg"}

# Style reference: teal palette, chunkier body, solid head with hair.
TEAL = {"front": f"{IN}/teal-front.jpg",
        "back":  f"{IN}/teal-back.jpg"}

# Photoreal anatomy renders. Only vvg8 touches these.
RENDER = {"front": f"{IN}/render-front.jpg",
          "back":  f"{IN}/render-back.jpg"}

# ---------------------------------------------------------------------------
# palettes
# ---------------------------------------------------------------------------
ART_FILL = "#3FBCEA"      # muscle fill in the source art
ART_LINE  = "#076599"      # linework in the source art
ART_RGB   = [(255, 255, 255), (63, 188, 234), (7, 101, 153)]   # white / fill / line

TEAL_FILL = "#5FB3A6"
TEAL_LINE = "#1E5B53"

# ---------------------------------------------------------------------------
# tracing
# ---------------------------------------------------------------------------
TRACE_SCALE = 3         # upscale factor before potrace; smoother curves
POTRACE_U   = 10        # potrace -u; output units per bitmap pixel
BLUR        = 1.2       # gaussian sigma applied before re-thresholding
MIN_AREA    = 60        # drop connected components smaller than this (px)

# potrace space -> source-image pixel space divisor
PT_DIV = POTRACE_U * TRACE_SCALE      # == 30

# ---------------------------------------------------------------------------
# teal output geometry
# ---------------------------------------------------------------------------
# Both views get rescaled so crown-to-sole is the same number of source
# pixels before the unit multiplier. Without this the front and back figures
# come out at visibly different heights on the combined sheet.
TARGET_BODY_PX = 537
UNIT = 4.0              # output SVG units per source pixel at reference height

# Two-pass muscle styling, in absolute output units:
#   pass 1 (.edge) is stroked at G + S  -> the dark rim
#   pass 2 (.m)    is stroked at G      -> the teal body of the muscle
# Absolute units on purpose: line weight must match between front and back
# even though the two source images differ in size.
GAP_SPREAD = 8.0        # G
RIM        = 10.4       # S
OUTLINE_W  = RIM * 1.15 # body silhouette stroke

# ---------------------------------------------------------------------------
# autotrace (photoreal renders, vvg8 only)
# ---------------------------------------------------------------------------
AT_UPSCALE = 3
AT_COLORS  = 16         # adaptive palette size
AT_PAD     = 6          # px of padding around the extracted figure
AT_MIN_PX  = 260        # drop palette entries / masks smaller than this
AT_HOLE_PX = 1500       # fill interior holes below this area; never bridge legs

# ---------------------------------------------------------------------------
# fonts (only the overlay stages need one)
# ---------------------------------------------------------------------------
# First match wins. Covers Linux (DejaVu) and Windows (Arial); anything else
# falls back to PIL's built-in bitmap font, which is ugly but never fails.
FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
]


def load_font(size):
    from PIL import ImageFont
    for cand in FONT_CANDIDATES:
        if os.path.exists(cand):
            return ImageFont.truetype(cand, size)
    return ImageFont.load_default()


def ensure_dirs():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
