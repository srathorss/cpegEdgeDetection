#!/usr/bin/env python3
"""
compare_outputs.py — Compare Verilog simulation output against golden model.

Reads two hex files (golden reference and Verilog output), compares them
pixel-by-pixel, and reports mismatches with their locations.

Usage:
    python3 compare_outputs.py <golden.hex> <verilog.hex> --width W --height H

Exit code 0 = perfect match, 1 = mismatches found.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_hex(filepath: str) -> list[int]:
    pixels = []
    with open(filepath) as f:
        for line in f:
            token = line.strip()
            if token and not token.startswith("//"):
                pixels.append(int(token, 16))
    return pixels


def main():
    parser = argparse.ArgumentParser(description="Compare golden vs Verilog hex output")
    parser.add_argument("golden",  help="Golden model hex file")
    parser.add_argument("verilog", help="Verilog simulation hex file")
    parser.add_argument("--width",  "-W", type=int, required=True)
    parser.add_argument("--height", "-H", type=int, required=True)
    parser.add_argument("--max-errors", type=int, default=20,
                        help="Max errors to print (default: 20)")
    args = parser.parse_args()

    gold_px = load_hex(args.golden)
    vlog_px = load_hex(args.verilog)
    expected = args.width * args.height

    print(f"Golden:  {len(gold_px)} pixels from {args.golden}")
    print(f"Verilog: {len(vlog_px)} pixels from {args.verilog}")
    print(f"Expected: {expected} pixels ({args.width}x{args.height})")

    if len(gold_px) != expected:
        print(f"WARNING: Golden file has {len(gold_px)} pixels, expected {expected}")
    if len(vlog_px) != expected:
        print(f"WARNING: Verilog file has {len(vlog_px)} pixels, expected {expected}")

    # Compare pixel-by-pixel
    compare_len = min(len(gold_px), len(vlog_px), expected)
    mismatches = 0
    max_diff = 0

    for i in range(compare_len):
        if gold_px[i] != vlog_px[i]:
            mismatches += 1
            diff = abs(gold_px[i] - vlog_px[i])
            max_diff = max(max_diff, diff)
            if mismatches <= args.max_errors:
                row = i // args.width
                col = i % args.width
                print(f"  MISMATCH at pixel {i} (row={row}, col={col}): "
                      f"golden=0x{gold_px[i]:02X} ({gold_px[i]:3d}), "
                      f"verilog=0x{vlog_px[i]:02X} ({vlog_px[i]:3d}), "
                      f"diff={diff}")

    if mismatches > args.max_errors:
        print(f"  ... and {mismatches - args.max_errors} more mismatches")

    print(f"\n{'='*50}")
    if mismatches == 0:
        print(f"PASS: All {compare_len} pixels match perfectly!")
        # Generate diff image (all black = perfect)
        diff_img = np.zeros((args.height, args.width), dtype=np.uint8)
    else:
        print(f"FAIL: {mismatches}/{compare_len} pixels differ (max diff = {max_diff})")
        # Generate visual diff image (amplified)
        gold_arr = np.array(gold_px[:expected], dtype=np.int16).reshape(args.height, args.width)
        vlog_arr = np.array(vlog_px[:expected], dtype=np.int16).reshape(args.height, args.width)
        diff_img = np.clip(np.abs(gold_arr - vlog_arr) * 10, 0, 255).astype(np.uint8)

    diff_path = Path(args.verilog).parent / "diff.png"
    Image.fromarray(diff_img, "L").save(str(diff_path))
    print(f"Diff image: {diff_path}")

    sys.exit(0 if mismatches == 0 else 1)


if __name__ == "__main__":
    main()
