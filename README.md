# muscle-svg

Turn flat anatomical line art into clean SVG with **individually named,
fillable muscle regions** - 90 on the front, 67 on the back, across 41
muscle groups.

The whole thing is deterministic. No GPU, no manual path drawing, and the
pipeline itself uses no AI: it is raster analysis plus
[potrace](http://potrace.sourceforge.net/), so running it twice gives you
the same bytes twice.

```bash
pip install -r requirements.txt
sudo apt-get install potrace
make check      # confirm the toolchain
# drop your reference art into input/ (see "Using your own reference art")
make all        # build everything
```

## Why I built this

I wanted a body diagram where JavaScript can do this:

```js
document.getElementById('quadriceps-left-2').setAttribute('fill', '#e63946');
document.getElementById('trapezius').setAttribute('fill', '#457b9d');  // whole group
```

Auto-tracing an anatomy image gives you thousands of anonymous paths, which
is useless for that. This pipeline recovers the real anatomical structure
from the drawing instead.

## About the reference art

The art is not distributed with this repo - the pipeline runs on whatever
you put in `input/`. It expects three kinds of image, and here is the
honest story of mine:

- **Line art** (`ART` in the config): a flat two-colour drawing - white
  background, one fill colour, one line colour - where every muscle is
  separated by white gaps. This is what the named regions come from. Mine
  was AI-generated on purpose: potrace needs sharp, clean separations to
  get fingers and overlapping muscles right, and generating the art was the
  fastest way to that cleanliness.
- **Teal style reference** (`TEAL`): the look I wanted the output to have.
  AI generated the image; I gave it the outline and some of the shading,
  and then matched the pipeline's output to it.
- **Photoreal renders** (`RENDER`): optional, used only by the standalone
  autotrace stage. Also AI-generated.

The region counts and names in this README are from my reference set;
yours will differ.

## The idea that makes it work

The line art already separates muscles with white gaps. So the muscles are
literally the connected components of the fill colour. No segmentation
model, no redrawing: classify each pixel by its nearest palette colour,
open by 3x3 to break accidental bridges, and label.

The one manual step is naming those components, once, by eye, from a
numbered overlay the pipeline renders for you. Everything after that is
automatic.

## The pipeline

Nine numbered stages, all in `src/`:

| Stage | Script | Does |
|---|---|---|
| vvg1 | `vvg1_trace.py` | Plain two-layer trace. Validates the trace params. |
| vvg2 | `vvg2_segment.py` | Connected components -> the individual muscles |
| vvg3 | `vvg3_mapview.py` | Numbered overlay maps **(the manual naming step)** |
| vvg4 | `vvg4_regions.py` | Named, fillable region SVGs |
| vvg5 | `vvg5_verify.py` | Recolour each group and render, to check the naming |
| vvg6 | `vvg6_silhouettes.py` | Extract the style-reference silhouettes |
| vvg7 | `vvg7_teal.py` | Restyle in the teal palette (2 variants) |
| vvg8 | `vvg8_autotrace.py` | Standalone: autotrace the photoreal renders |
| vvg9 | `vvg9_combine.py` | Side-by-side sheets + `REGIONS.md` |

vvg1 through vvg7 plus vvg9 form one chain. vvg8 is independent and solves
a different problem - see the outputs table.

```
make regions      # vvg2, vvg4, vvg9  -> the named fillable SVGs
make verify       # vvg5              -> naming QA render
make hybrid       # vvg6, vvg7, vvg9  -> recommended teal output
make teal         # vvg6, vvg7, vvg9  -> warped variant
make render       # vvg8, vvg9        -> photoreal autotrace
```

## Outputs

Everything lands in `out/`.

**Named and fillable** - the useful ones:

| File | Contents |
|---|---|
| `body-front-regions.svg` | 90 regions in 24 groups (my set) |
| `body-back-regions.svg` | 67 regions in 17 groups |
| `hybrid-body-front.svg` | the same regions in the teal style + teal head - **recommended** |
| `hybrid-body-back.svg` | back view, teal style |
| `teal-body-*.svg` | the regions morphed onto the teal body's proportions |
| `REGIONS.md` | every region id, grouped |

**Not named** - looks best, addresses worst:

| File | Contents |
|---|---|
| `render-front.svg` | shading-tone layers autotraced from the photoreal render |
| `render-back.svg` | same, back view |

The render files carry ids like `tone-04`. Those are quantized shading
bands, not anatomy - there is no `#biceps-left` in them. That is the
tradeoff: photoreal appearance costs you addressability.

## The demo tool

`tools/demo.html` is a single self-contained page that proves the whole
point of the project. Open it in any browser (no server needed), click the
file picker, and load any SVG from `out/`. Then:

- **Hover** any muscle and the panel shows its id and group -
  `quadriceps-left-2`, group `quadriceps`.
- **Click** it and it fills with the selected swatch colour. Switch the
  scope dropdown to "Whole muscle group" and one click paints every region
  of that group at once.
- The **group list** shows every group with its region count; clicking a
  group name paints the whole group.
- **Reset all fills** puts every original colour back.

Under the hood it does nothing clever - literally
`el.setAttribute('fill', color)` - which is the proof: if a plain
setAttribute works, the regions are genuinely fillable from any JavaScript,
framework or none.

## How the regions are named

`{group}-{side}` for a single region, `{group}-{side}-{n}` numbered
top-to-bottom when a group has several.

**Sides are anatomical**, so they flip between views. On the front,
viewer-left is the subject's RIGHT. On the back, viewer-left is the
subject's LEFT.

Front groups (24): abdomen, adductor, ankle, biceps, brachialis, calf,
chest, clavicle, deltoid, fingers, foot, forearm, hand, head, hip-flexor,
knee, neck, oblique, quadriceps, sartorius, serratus, shin, throat,
trapezius

Back groups (17): achilles, calf, deltoid, erector-spinae, fingers, forearm,
glutes, hamstring, hand, head, heel, it-band, latissimus, lower-back, neck,
trapezius, triceps

The mapping from component integer to name lives in `src/vvg_names.py`. To
fix a mislabel, edit that file and re-run `make regions`.

## Using your own reference art

1. Drop your images in `input/`, point `ART` in `src/vvg_config.py` at them
2. Update `ART_RGB` to your art's three colours (white, fill, linework)
3. `make mapview`, open `out/map_front_{upper,mid,lower}.png`
4. Rewrite `src/vvg_names.py` from what you see
5. `make regions && make verify`

Step 4 is the only labour, and you pay it once per reference image.

## Requirements

- Python 3.10+, `numpy`, `scipy`, `Pillow`, `CairoSVG`
- `potrace` on `PATH`

CPU only. The full build takes a couple of minutes on 2 cores.

## Hard-won details

The full write-up is in [`docs/NOTES.md`](docs/NOTES.md). The short version:

- **potrace traces BLACK pixels.** Invert every mask before writing the PBM.
- **Upscale, blur, then re-threshold.** Skip the blur and outlines come out
  jagged.
- **Verify with CairoSVG, never ImageMagick.** ImageMagick's SVG renderer
  drops strokes and only matches trivial CSS selectors. Three debugging
  rounds went into learning that.
- **The empty `<style></style>` is deliberate.** CSS beats presentation
  attributes, so a stylesheet fill would permanently block
  `setAttribute("fill")`.
- **Never `binary_fill_holes` a whole figure.** It bridges the gap between
  the legs. Fill by hole area instead.

## License

MIT for the pipeline code. Reference images are not included; you supply
your own art in `input/`.
