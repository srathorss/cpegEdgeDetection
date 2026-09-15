# ============================================================
# Makefile — Roberts & Sobel Edge Detection HDL Simulation
# Requires: GNU Make, Icarus Verilog (iverilog/vvp), GTKWave
# ============================================================

# ── Configurable parameters (override on the command line) ───
WIDTH       ?= 64
HEIGHT      ?= 64
THRESHOLD   ?= 30     # Roberts binary threshold
S_THRESHOLD ?= 80     # Sobel binary threshold
IMAGE       ?= ../input/4.1.01.jpg

# ── Tools ────────────────────────────────────────────────────
IVERILOG := iverilog
VVP      := vvp
GTKWAVE  := gtkwave
PYTHON   := python

SCRIPTS  := ../scripts

# ── Source lists ──────────────────────────────────────────────
ROBERTS_SRC := tb_roberts.v roberts_top.v roberts_core.v line_buffer.v
SOBEL_SRC   := sobel_tb.v sobel.v

# ── Default target ────────────────────────────────────────────
.PHONY: all roberts sobel both view-roberts view-sobel hex clean

all: both

# ── Hex input generation ──────────────────────────────────────
# Converts IMAGE to grayscale hex files the testbenches can read.
# Both aliases point at the same converted data.

image.hex input.hex: $(IMAGE)
	$(PYTHON) $(SCRIPTS)/img_to_hex.py $(IMAGE) \
	    --width $(WIDTH) --height $(HEIGHT) --output image.hex
	cp image.hex input.hex

hex: image.hex input.hex

# ── Roberts Cross ─────────────────────────────────────────────
roberts_sim.vvp: $(ROBERTS_SRC)
	$(IVERILOG) -g2001 \
	    -DIMG_WIDTH=$(WIDTH) \
	    -DIMG_HEIGHT=$(HEIGHT) \
	    -DIMG_THRESHOLD=$(THRESHOLD) \
	    -o roberts_sim.vvp $(ROBERTS_SRC)

roberts.vcd: roberts_sim.vvp image.hex
	$(VVP) roberts_sim.vvp

roberts: roberts.vcd
	@echo ""
	@echo "Roberts simulation done."
	@echo "  VCD waveform : roberts.vcd"
	@echo "  Pixel output : output_roberts.hex"
	@echo "  Run 'make view-roberts' to open in GTKWave."

view-roberts: roberts.vcd
	$(GTKWAVE) roberts.vcd &

# ── Sobel ─────────────────────────────────────────────────────
sobel_sim.vvp: $(SOBEL_SRC)
	$(IVERILOG) -g2001 \
	    -DIMG_WIDTH=$(WIDTH) \
	    -DIMG_HEIGHT=$(HEIGHT) \
	    -o sobel_sim.vvp $(SOBEL_SRC)

sobel.vcd: sobel_sim.vvp input.hex
	$(VVP) sobel_sim.vvp

sobel: sobel.vcd
	@echo ""
	@echo "Sobel simulation done."
	@echo "  VCD waveform : sobel.vcd"
	@echo "  Pixel output : output.hex"
	@echo "  Run 'make view-sobel' to open in GTKWave."

view-sobel: sobel.vcd
	$(GTKWAVE) sobel.vcd &

# ── Both methods ──────────────────────────────────────────────
both: roberts sobel

# ── Clean ─────────────────────────────────────────────────────
clean:
	rm -f *.vvp *.vcd *.hex *.params output_roberts.hex output.hex
