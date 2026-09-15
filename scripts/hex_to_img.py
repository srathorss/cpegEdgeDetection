#!/usr/bin/env python3
"""
hex_to_img.py — Reconstruct an image from Verilog simulation hex output.

Usage:
    python3 hex_to_img.py <hex_file> --width W --height H [--output FILE]
    python3 hex_to_img.py <hex_file> --params <params_file>

Examples:
    python3 hex_to_img.py output_roberts.hex --width 62 --height 62
    python3 hex_to_img.py output_roberts.hex --params image.params -o edges.png

Note: For a Roberts filter on a WxH image, the output is (W-1)x(H-1).
      For a Sobel filter on a WxH image, the output is (W-2)x(H-2).
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_hex(filepath: str) -> list[int]:
    """Read hex file (one value per line) and return list of integers."""
    pixels = []
    with open(filepath) as f:
        for line_num, line in enumerate(f, 1):
            token = line.strip()
            if not token or token.startswith("//"):
                continue  # skip blank lines and Verilog-style comments
            try:
                val = int(token, 16)
                pixels.append(val)
            except ValueError:
                print(f"WARNING: Skipping invalid hex on line {line_num}: '{token}'",
                      file=sys.stderr)
    return pixels


def main():
    parser = argparse.ArgumentParser(
        description="Reconstruct an image from Verilog simulation hex output"
    )
    parser.add_argument("hex_file", help="Path to hex output file")
    parser.add_argument("--width",  "-W", type=int, default=None)
    parser.add_argument("--height", "-H", type=int, default=None)
    parser.add_argument("--params", "-p", type=str, default=None,
                        help="Path to .params file (contains width and height)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output image path (default: <hex_stem>.png)")
    args = parser.parse_args()

    # ── Determine dimensions ────────────────────────────────────────
    width, height = args.width, args.height
    if args.params:
        with open(args.params) as f:
            lines = f.read().strip().split("\n")
            width  = int(lines[0])
            height = int(lines[1])

    if width is None or height is None:
        print("ERROR: Must specify --width and --height, or --params file",
              file=sys.stderr)
        sys.exit(1)

    # ── Load hex data ───────────────────────────────────────────────
    pixels = load_hex(args.hex_file)
    expected = width * height
    actual = len(pixels)

    if actual != expected:
        print(f"WARNING: Expected {expected} pixels ({width}x{height}), "
              f"got {actual}.")
        if actual < expected:
            # Pad with black
            pixels.extend([0] * (expected - actual))
        else:
            pixels = pixels[:expected]

    # ── Reconstruct image ───────────────────────────────────────────
    arr = np.array(pixels, dtype=np.uint8).reshape((height, width))

    out_path = args.output or str(Path(args.hex_file).with_suffix(".png"))
    Image.fromarray(arr, mode="L").save(out_path)

    print(f"Reconstructed {width}x{height} image -> {out_path}")
    print(f"  Pixel range: [{arr.min()}, {arr.max()}], mean={arr.mean():.1f}")


if __name__ == "__main__":
    main()
