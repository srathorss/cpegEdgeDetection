# Edge Detection — Roberts Cross & Sobel

Hardware implementations of two edge detection filters in Verilog, simulated with Icarus Verilog and verified against Python reference models.

---

## What it does

Takes a grayscale image, streams it pixel-by-pixel through a Verilog hardware simulation, and outputs an edge-detected image. Two filters are implemented:

- **Roberts Cross** — detects edges using a 2×2 pixel window. Fast, simple, sensitive to noise.
- **Sobel** — detects edges using a 3×3 pixel window with weighted kernels. Smoother, more robust.

Both produce a binary output image: white pixels (255) where edges are detected, black (0) everywhere else.

---

## Files

```
edge_detection.py          — main script: runs the full pipeline end to end

hdl/
  roberts_core.v           — combinational gradient computation for Roberts
  roberts_top.v            — Roberts streaming controller + line buffer wiring
  line_buffer.v            — shift-register delay line (shared by Roberts)
  sobel.v                  — complete Sobel module with 3x3 window logic
  tb_roberts.v             — Roberts testbench
  sobel_tb.v               — Sobel testbench
  Makefile                 — compile and simulate from the command line

scripts/
  img_to_hex.py            — converts an image to hex format for the Verilog testbench
  hex_to_img.py            — converts simulation hex output back to a PNG
  roberts_golden.py        — Python reference implementation of Roberts
  sobel_golden.py          — Python reference implementation of Sobel
  compare_outputs.py       — pixel-by-pixel comparison of Verilog vs golden output

input/                     — source images
output/                    — results written here
```

---

## How to run

**All-in-one (recommended):**

```
python edge_detection.py -i input/house.jpg -o output/house --method both
```

Options: `--method sobel`, `--method roberts`, or `--method both`. Results go in the output folder as PNGs.

**Using Make (from `hdl/`):**

```
cd hdl
make              # compile and simulate both filters
make view-roberts # open roberts.vcd in GTKWave
make view-sobel   # open sobel.vcd in GTKWave
make clean        # remove generated files
```

---

## Requirements

- Python 3.10+ with `pillow` and `numpy` (`pip install pillow numpy`)
- [Icarus Verilog](http://bleyer.org/icarus/) — provides `iverilog` and `vvp`
- [GTKWave](https://gtkwave.sourceforge.net) — for waveform viewing
