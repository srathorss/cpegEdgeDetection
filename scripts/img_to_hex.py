#!/usr/bin/env python3
"""
img_to_hex.py — Convert a color image to 8-bit grayscale and export
                as a hex file readable by Verilog's $readmemh.

Usage:
    python3 img_to_hex.py <input_image> [--width W] [--height H] [--output FILE]

Examples:
    python3 img_to_hex.py photo.jpg                          # auto-size, outputs image.hex
    python3 img_to_hex.py photo.png --width 64 --height 64   # resize to 64x64
    python3 img_to_hex.py photo.bmp -o my_input.hex          # custom output name

The output .hex file contains one 8-bit pixel value per line in uppercase
hexadecimal (e.g., "A3"), row-major order (top-left pixel first).

A companion _params.txt file is also written with WIDTH and HEIGHT so the
Verilog testbench and reconstruction script know the image dimensions.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image


def rgb_to_grayscale(img_array: np.ndarray) -> np.ndarray:
    """
    Convert an RGB image to grayscale using the ITU-R BT.601 luma formula:
        Y = 0.299*R + 0.587*G + 0.114*B

    This is the same formula used by PIL's .convert('L') and by most
    image-processing textbooks.  We do it explicitly here so you can
    see (and modify) the exact weights used—important for bit-exact
    matching against a Verilog implementation if you ever move to
    hardware-side grayscale conversion.
    """
    if img_array.ndim == 2:
        # Already grayscale
        return img_array

    if img_array.ndim == 3 and img_array.shape[2] == 4:
        # RGBA → drop alpha
        img_array = img_array[:, :, :3]

    r = img_array[:, :, 0].astype(np.float64)
    g = img_array[:, :, 1].astype(np.float64)
    b = img_array[:, :, 2].astype(np.float64)

    gray = 0.299 * r + 0.587 * g + 0.114 * b
    return np.clip(np.round(gray), 0, 255).astype(np.uint8)


def save_hex(pixels: np.ndarray, filepath: str) -> None:
    """Write a 2D uint8 array as one hex value per line (row-major)."""
    h, w = pixels.shape
    with open(filepath, "w") as f:
        for row in range(h):
            for col in range(w):
                f.write(f"{pixels[row, col]:02X}\n")
    print(f"  Wrote {h * w} pixels to {filepath}")


def save_params(width: int, height: int, filepath: str) -> None:
    """Write image dimensions so other scripts/testbenches can read them."""
    with open(filepath, "w") as f:
        f.write(f"{width}\n{height}\n")
    print(f"  Params file: {width}x{height} -> {filepath}")


def save_grayscale_png(pixels: np.ndarray, filepath: str) -> None:
    """Save the grayscale image as PNG for visual reference."""
    Image.fromarray(pixels, mode="L").save(filepath)
    print(f"  Grayscale preview: {filepath}")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a color image to grayscale hex for Verilog simulation"
    )
    parser.add_argument("input", help="Path to input image (PNG, JPG, BMP, etc.)")
    parser.add_argument("--width",  "-W", type=int, default=None,
                        help="Resize width  (default: keep original)")
    parser.add_argument("--height", "-H", type=int, default=None,
                        help="Resize height (default: keep original)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output hex filename (default: image.hex)")
    args = parser.parse_args()

    # ── Load image ──────────────────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    img = Image.open(input_path)
    print(f"Loaded: {input_path}  ({img.size[0]}x{img.size[1]}, mode={img.mode})")

    # ── Resize if requested ─────────────────────────────────────────
    target_w = args.width  or img.size[0]
    target_h = args.height or img.size[1]
    if (target_w, target_h) != img.size:
        img = img.resize((target_w, target_h), Image.LANCZOS)
        print(f"Resized to: {target_w}x{target_h}")

    # ── Convert to grayscale ────────────────────────────────────────
    img_array = np.array(img)
    gray = rgb_to_grayscale(img_array)
    print(f"Grayscale: min={gray.min()}, max={gray.max()}, "
          f"mean={gray.mean():.1f}")

    # ── Determine output paths ──────────────────────────────────────
    out_dir = input_path.parent
    stem = input_path.stem

    hex_path    = args.output or str(out_dir / f"{stem}.hex")
    params_path = str(Path(hex_path).with_suffix(".params"))
    preview_path = str(out_dir / f"{stem}_gray.png")

    # ── Write outputs ───────────────────────────────────────────────
    save_hex(gray, hex_path)
    save_params(target_w, target_h, params_path)
    save_grayscale_png(gray, preview_path)

    print(f"\nDone! Next steps:")
    print(f"  1. Copy {hex_path} to your Verilog project's data/ folder")
    print(f"  2. In your testbench:  $readmemh(\"{Path(hex_path).name}\", pixel_mem);")
    print(f"  3. Set parameters:     WIDTH={target_w}, HEIGHT={target_h}")


if __name__ == "__main__":
    main()
