#!/usr/bin/env python3
"""
sobel_golden.py — Software golden model for Sobel edge detection.

Bit-exact arithmetic matching the Verilog sobel module (sobel.v):

    Window layout (p-notation matches sobel.v register names):
        p00 p01 p02   <- top row    (row r)
        p10 p11 p12   <- middle row (row r+1)
        p20 p21 p22   <- bottom row (row r+2)

    Gx = (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20)    [right col - left col]
    Gy = (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02)    [bottom row - top row]
    G  = |Gx| + |Gy|
    out = 255 if G > threshold else 0   [strictly-greater, matching Verilog]

Output image size: (WIDTH-2) x (HEIGHT-2)

Usage:
    python3 sobel_golden.py <input.hex> -W <width> -H <height> [-T <threshold>] [-o <prefix>]
    python3 sobel_golden.py photo_gray.png [-T 80] [-o prefix]
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def load_image(filepath: str, width: int = None, height: int = None) -> np.ndarray:
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


def sobel_cross(img: np.ndarray, threshold: int = 80) -> tuple[np.ndarray, np.ndarray]:
    """
    Apply Sobel edge detection with bit-exact Verilog-matching arithmetic.

    Returns:
        gradient: saturated |Gx|+|Gy| magnitude image, uint8 [0..255]
        binary:   thresholded edge map (0 or 255), uint8
    """
    h, w = img.shape
    out_h, out_w = h - 2, w - 2

    src = img.astype(np.int32)

    gradient = np.zeros((out_h, out_w), dtype=np.uint8)
    binary   = np.zeros((out_h, out_w), dtype=np.uint8)

    for r in range(out_h):
        for c in range(out_w):
            p00 = int(src[r,     c    ])
            p01 = int(src[r,     c + 1])
            p02 = int(src[r,     c + 2])
            p10 = int(src[r + 1, c    ])
            p12 = int(src[r + 1, c + 2])
            p20 = int(src[r + 2, c    ])
            p21 = int(src[r + 2, c + 1])
            p22 = int(src[r + 2, c + 2])

            gx = (p02 + 2 * p12 + p22) - (p00 + 2 * p10 + p20)
            gy = (p20 + 2 * p21 + p22) - (p00 + 2 * p01 + p02)

            mag = abs(gx) + abs(gy)

            gradient[r, c] = min(mag, 255)
            # Verilog uses strictly-greater-than: (mag > THRESHOLD)
            binary[r, c]   = 255 if mag > threshold else 0

    return gradient, binary


def save_hex(pixels: np.ndarray, filepath: str) -> None:
    h, w = pixels.shape
    with open(filepath, "w") as f:
        for r in range(h):
            for c in range(w):
                f.write(f"{pixels[r, c]:02X}\n")
    print(f"  Wrote {h * w} pixels -> {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Sobel edge detection golden model (bit-exact Verilog reference)"
    )
    parser.add_argument("input", help="Input image (.hex, .png, .jpg, .bmp)")
    parser.add_argument("--width",  "-W", type=int, default=None)
    parser.add_argument("--height", "-H", type=int, default=None)
    parser.add_argument("--threshold", "-T", type=int, default=80,
                        help="Edge threshold, strictly greater-than (default: 80)")
    parser.add_argument("--output-prefix", "-o", type=str, default=None,
                        help="Output filename prefix (default: input stem)")
    args = parser.parse_args()

    img = load_image(args.input, args.width, args.height)
    h, w = img.shape
    print(f"Input: {w}x{h}, range [{img.min()}, {img.max()}]")

    gradient, binary = sobel_cross(img, args.threshold)
    out_h, out_w = gradient.shape
    print(f"Output: {out_w}x{out_h} (threshold > {args.threshold})")

    if args.output_prefix:
        out_dir = Path(args.output_prefix).parent
        prefix  = Path(args.output_prefix).name
    else:
        out_dir = Path(args.input).parent
        prefix  = Path(args.input).stem

    save_hex(gradient, str(out_dir / f"{prefix}_sobel_grad.hex"))
    save_hex(binary,   str(out_dir / f"{prefix}_sobel_bin.hex"))

    Image.fromarray(gradient, "L").save(str(out_dir / f"{prefix}_sobel_grad.png"))
    Image.fromarray(binary,   "L").save(str(out_dir / f"{prefix}_sobel_bin.png"))

    params_path = str(out_dir / f"{prefix}_sobel.params")
    with open(params_path, "w") as f:
        f.write(f"{out_w}\n{out_h}\n")
    print(f"  Output params: {params_path}")

    print(f"\nGradient stats: min={gradient.min()}, max={gradient.max()}, "
          f"mean={gradient.mean():.1f}")
    edge_pct = 100.0 * np.count_nonzero(binary) / binary.size
    print(f"Edge pixels: {np.count_nonzero(binary)}/{binary.size} ({edge_pct:.1f}%)")


if __name__ == "__main__":
    main()
