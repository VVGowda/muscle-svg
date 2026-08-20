PY := python3
SRC := src
export PYTHONPATH := $(SRC)

.PHONY: all trace segment mapview regions verify silhouettes teal hybrid render \
        combine clean distclean check

## full pipeline: named regions, naming QA, recommended teal output, render autotrace
all: regions verify hybrid render

## vvg1 - plain trace of the reference art
trace:
	$(PY) $(SRC)/vvg1_trace.py

## vvg2 - connected-component segmentation
segment:
	$(PY) $(SRC)/vvg2_segment.py

## vvg3 - numbered overlay maps for manual naming
mapview: segment
	$(PY) $(SRC)/vvg3_mapview.py

## vvg4 + vvg9 - named fillable region SVGs and the combined sheet
regions: segment
	$(PY) $(SRC)/vvg4_regions.py
	$(PY) $(SRC)/vvg9_combine.py regions

## vvg5 - recolour every group and render, to check the naming
verify:
	$(PY) $(SRC)/vvg5_verify.py

## vvg6 - teal reference silhouettes
silhouettes:
	$(PY) $(SRC)/vvg6_silhouettes.py

## vvg7 warped - muscles morphed onto the teal body shape
teal: silhouettes
	$(PY) $(SRC)/vvg7_teal.py warped
	$(PY) $(SRC)/vvg9_combine.py teal

## vvg7 hybrid - source geometry, teal palette and head (recommended)
hybrid: silhouettes
	$(PY) $(SRC)/vvg7_teal.py hybrid
	$(PY) $(SRC)/vvg9_combine.py hybrid

## vvg8 - autotrace the photoreal renders
render:
	$(PY) $(SRC)/vvg8_autotrace.py
	$(PY) $(SRC)/vvg9_combine.py render

## confirm the external toolchain is present
check:
	@command -v potrace >/dev/null && echo "potrace: ok" || echo "potrace: MISSING"
	@$(PY) -c "import numpy, scipy, PIL, cairosvg; print('python deps: ok')"

## drop intermediates, keep the SVGs
clean:
	rm -rf out/tmp out/*.npy out/_verify_*.png

## drop everything generated
distclean:
	rm -rf out
