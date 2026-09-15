#!/usr/bin/env python3
"""
roberts_golden.py — Software golden model for Roberts Cross edge detection.

This script applies the EXACT same arithmetic that the Verilog Roberts module
will use, so its output serves as a bit-exact reference for verification.

Arithmetic details (matching Verilog):
    Gx = pixel[r][c] - pixel[r+1][c+1]     (main diagonal)
    Gy = pixel[r][c+1] - pixel[r+1][c]     (anti-diagonal)
    G  = |Gx| + |Gy|                        (Manhattan approximation)
    G  = min(G, 255)                         (saturate to 8 bits)
    out = 255 if G >= threshold else 0       (binary thresholding)

Output image size: (WIDTH-1) x (HEIGHT-1)  — one pixel lost on right and bottom.

Usage:
    python3 roberts_golden.py <input_hex_or_image> --width W --height H [--threshold T]

Examples:
    python3 roberts_golden.py image.hex --width 64 --height 64 --threshold 30
    python3 roberts_golden.py photo_gray.png --threshold 50
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_image(filepath: str, width: int = None, height: int = None) -> np.ndarray:
    """Load an image from hex file or image file, return 2D uint8 array."""
    path = Path(filepath)

    if path.suffix.lower() == ".hex":
        if width is None or height is None:
            print("ERROR: --width and --height required for .hex input", file=sys.stderr)
            sys.exit(1)
        with open(filepath) as f:
            pixels = [int(line.strip(), 16) for line in f if line.strip()]
        return np.array(pixels, dtype=np.uint8).reshape((height, width))
    else:
        img = Image.open(filepath).convert("L")
        return np.array(img, dtype=np.uint8)


def roberts_cross(img: np.ndarray, threshold: int = 30) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply Roberts Cross edge detection with bit-exact Verilog-matching arithmetic.

    Returns:
        gradient:   The saturated |Gx| + |Gy| magnitude image (uint8)
        binary:     The thresholded binary edge map (uint8, values 0 or 255)
    """
    h, w = img.shape
    out_h, out_w = h - 1, w - 1

    # Work in signed int16 to match Verilog's signed arithmetic
    src = img.astype(np.int16)

    gradient = np.zeros((out_h, out_w), dtype=np.uint8)
    binary   = np.zeros((out_h, out_w), dtype=np.uint8)

    for r in range(out_h):
        for c in range(out_w):
            # Roberts Cross kernels
            gx = int(src[r, c])     - int(src[r + 1, c + 1])   # main diagonal
            gy = int(src[r, c + 1]) - int(src[r + 1, c])       # anti-diagonal

            # Manhattan approximation of gradient magnitude
            mag = abs(gx) + abs(gy)

            # Saturate to 8-bit unsigned
            mag = min(mag, 255)

            gradient[r, c] = mag
            binary[r, c]   = 255 if mag >= threshold else 0

    return gradient, binary


def save_hex(pixels: np.ndarray, filepath: str) -> None:
    """Write 2D array as hex file (one value per line)."""
    h, w = pixels.shape
    with open(filepath, "w") as f:
        for r in range(h):
            for c in range(w):
                f.write(f"{pixels[r, c]:02X}\n")
    print(f"  Wrote {h * w} pixels -> {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Roberts Cross golden model (bit-exact Verilog reference)"
    )
    parser.add_argument("input", help="Input image (.hex, .png, .jpg, .bmp)")
    parser.add_argument("--width",  "-W", type=int, default=None)
    parser.add_argument("--height", "-H", type=int, default=None)
    parser.add_argument("--threshold", "-T", type=int, default=30,
                        help="Edge threshold (default: 30)")
    parser.add_argument("--output-prefix", "-o", type=str, default=None,
                        help="Output filename prefix (default: input stem)")
    args = parser.parse_args()

    # ── Load input ──────────────────────────────────────────────────
    img = load_image(args.input, args.width, args.height)
    h, w = img.shape
    print(f"Input: {w}x{h}, range [{img.min()}, {img.max()}]")

    # ── Apply Roberts Cross ─────────────────────────────────────────
    gradient, binary = roberts_cross(img, args.threshold)
    out_h, out_w = gradient.shape
    print(f"Output: {out_w}x{out_h} (threshold={args.threshold})")

    # ── Save outputs ────────────────────────────────────────────────
    if args.output_prefix:
        out_dir = Path(args.output_prefix).parent
        prefix  = Path(args.output_prefix).name
    else:
        out_dir = Path(args.input).parent
        prefix  = Path(args.input).stem

    # Hex files (for Verilog comparison)
    save_hex(gradient, str(out_dir / f"{prefix}_roberts_grad.hex"))
    save_hex(binary,   str(out_dir / f"{prefix}_roberts_bin.hex"))

    # PNG images (for visual inspection)
    Image.fromarray(gradient, "L").save(str(out_dir / f"{prefix}_roberts_grad.png"))
    Image.fromarray(binary,   "L").save(str(out_dir / f"{prefix}_roberts_bin.png"))

    # Params for output dimensions
    params_path = str(out_dir / f"{prefix}_roberts.params")
    with open(params_path, "w") as f:
        f.write(f"{out_w}\n{out_h}\n")
    print(f"  Output params: {params_path}")

    print(f"\nGradient stats: min={gradient.min()}, max={gradient.max()}, "
          f"mean={gradient.mean():.1f}")
    edge_pct = 100.0 * np.count_nonzero(binary) / binary.size
    print(f"Edge pixels: {np.count_nonzero(binary)}/{binary.size} ({edge_pct:.1f}%)")


if __name__ == "__main__":
    main()
