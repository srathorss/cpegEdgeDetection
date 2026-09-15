#!/usr/bin/env python3
"""
edge_detection.py  —  FPGA-verified edge detection pipeline.

Converts an input image to grayscale, runs it through Roberts Cross and/or
Sobel Verilog simulations via Icarus Verilog, verifies each output against a
bit-exact Python golden model, and writes the results to an output directory.

Usage
-----
    py edge_detection.py -i input/photo.jpg -o output/run1 --method both
    py edge_detection.py -i input/photo.jpg -o output/run1 --method sobel
    py edge_detection.py -i input/photo.jpg -o output/run1 --method roberts

Options
-------
    -i / --input              Input image (JPEG, PNG, BMP, ...)
    -o / --output             Output directory (created if absent)
    --method                  sobel | roberts | both  (default: both)
    --sobel-threshold INT     Sobel binary threshold 0-255     (default: 80)
    --roberts-threshold INT   Roberts gradient threshold 0-255 (default: 30)
    --max-size INT            Resize longest edge to N pixels before
                              processing (default: 256, 0 = no resize).
                              Larger values increase simulation time.
"""

import argparse
import shutil
import subprocess
import sys
import tempfile
import textwrap
from datetime import datetime
from pathlib import Path

import numpy as np
from PIL import Image

# ── Project paths ─────────────────────────────────────────────────────────────
ROOT    = Path(__file__).parent.resolve()
SCRIPTS = ROOT / "scripts"
HDL     = ROOT / "hdl"

sys.path.insert(0, str(SCRIPTS))
from img_to_hex      import rgb_to_grayscale   # noqa: E402
from roberts_golden  import roberts_cross       # noqa: E402
from sobel_golden    import sobel_cross         # noqa: E402


# ── Utilities ─────────────────────────────────────────────────────────────────

def _check_tools() -> None:
    missing = [t for t in ("iverilog", "vvp") if not shutil.which(t)]
    if missing:
        sys.exit("ERROR: Missing tools: {}. Install Icarus Verilog.".format(", ".join(missing)))


def _load_gray(path: Path, max_size: int) -> np.ndarray:
    """Open image, auto-correct EXIF rotation, resize if needed, return H×W uint8."""
    img = Image.open(path)
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    w, h = img.size
    if max_size and max(w, h) > max_size:
        scale = max_size / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    return rgb_to_grayscale(np.array(img))


def _write_hex(pixels: np.ndarray, path: Path) -> None:
    h, w = pixels.shape
    with open(path, "w") as f:
        for r in range(h):
            for c in range(w):
                f.write(f"{pixels[r, c]:02X}\n")


def _read_hex(path: Path, width: int, height: int) -> np.ndarray:
    with open(path) as f:
        vals = [int(ln.strip(), 16) for ln in f if ln.strip()]
    return np.array(vals[: width * height], dtype=np.uint8).reshape(height, width)


def _iverilog(out: Path, defines: dict, sources: list) -> None:
    cmd = (
        ["iverilog", "-o", str(out)]
        + [f"-D{k}={v}" for k, v in defines.items()]
        + [str(s) for s in sources]
    )
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode:
        sys.exit(f"iverilog compilation failed:\n{r.stderr}")


def _vvp(sim: Path, cwd: Path) -> str:
    r = subprocess.run(["vvp", str(sim)], capture_output=True, text=True, cwd=cwd)
    if r.returncode:
        sys.exit(f"Simulation failed:\n{r.stderr}")
    return r.stdout


def _parse_sim_log(log: str) -> str:
    for line in log.splitlines():
        if "complete" in line.lower():
            return line.strip()
    return ""


def _verify(golden: np.ndarray, vlog: np.ndarray) -> tuple[int, int]:
    return int(np.sum(golden != vlog)), golden.size


# ── Per-method pipeline steps ─────────────────────────────────────────────────

def run_sobel(gray: np.ndarray, threshold: int, tmp: Path, out_dir: Path) -> dict:
    height, width = gray.shape
    out_w, out_h = width - 2, height - 2

    print("    compiling...", end=" ", flush=True)
    _iverilog(
        tmp / "sim_sobel",
        {"IMG_WIDTH": width, "IMG_HEIGHT": height, "NO_VCD": 1},
        [HDL / "sobel_tb.v", HDL / "sobel.v"],
    )
    print("done")

    _write_hex(gray, tmp / "input.hex")

    print("    simulating...", end=" ", flush=True)
    log = _vvp(tmp / "sim_sobel", tmp)
    print("done")
    msg = _parse_sim_log(log)
    if msg:
        print(f"    {msg}")

    vlog = _read_hex(tmp / "output.hex", out_w, out_h)
    Image.fromarray(vlog, "L").save(out_dir / "sobel_edges.png")

    # Python golden — binary output matching Verilog's > threshold comparison
    _grad, golden_bin = sobel_cross(gray, threshold)
    Image.fromarray(golden_bin, "L").save(out_dir / "sobel_golden.png")

    mismatches, total = _verify(golden_bin, vlog)
    edge_pct = 100.0 * int(np.count_nonzero(vlog)) / total
    return {
        "output_size":  f"{out_w}x{out_h}",
        "edge_pixels":  f"{int(np.count_nonzero(vlog))}/{total} ({edge_pct:.1f}%)",
        "verification": "PASS" if mismatches == 0
                        else f"FAIL ({mismatches}/{total} pixels differ)",
    }


def run_roberts(gray: np.ndarray, threshold: int, tmp: Path, out_dir: Path) -> dict:
    height, width = gray.shape
    out_w, out_h = width - 1, height - 1

    print("    compiling...", end=" ", flush=True)
    _iverilog(
        tmp / "sim_roberts",
        {"IMG_WIDTH": width, "IMG_HEIGHT": height, "IMG_THRESHOLD": threshold, "NO_VCD": 1},
        [HDL / "tb_roberts.v", HDL / "roberts_top.v",
         HDL / "line_buffer.v",  HDL / "roberts_core.v"],
    )
    print("done")

    _write_hex(gray, tmp / "image.hex")

    print("    simulating...", end=" ", flush=True)
    log = _vvp(tmp / "sim_roberts", tmp)
    print("done")
    msg = _parse_sim_log(log)
    if msg:
        print(f"    {msg}")

    vlog = _read_hex(tmp / "output_roberts.hex", out_w, out_h)
    Image.fromarray(vlog, "L").save(out_dir / "roberts_edges.png")

    # Python golden — gradient magnitude, matching Roberts Verilog output
    golden_grad, _bin = roberts_cross(gray, threshold)
    Image.fromarray(golden_grad, "L").save(out_dir / "roberts_golden.png")

    mismatches, total = _verify(golden_grad, vlog)
    edge_pct = 100.0 * int(np.count_nonzero(vlog)) / total
    return {
        "output_size":  f"{out_w}x{out_h}",
        "edge_pixels":  f"{int(np.count_nonzero(vlog))}/{total} ({edge_pct:.1f}%)",
        "verification": "PASS" if mismatches == 0
                        else f"FAIL ({mismatches}/{total} pixels differ)",
    }


# ── Summary writer ────────────────────────────────────────────────────────────

def _write_summary(out_dir: Path, args, input_path: Path,
                   gray: np.ndarray, results: dict) -> None:
    h, w = gray.shape
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    lines = [
        "Edge Detection Summary",
        "=" * 42,
        f"Timestamp    : {ts}",
        f"Input        : {input_path.resolve()}",
        f"Processed    : {w}x{h} grayscale",
        f"Method(s)    : {args.method}",
        "",
    ]
    for method, stats in results.items():
        thr = getattr(args, f"{method}_threshold")
        lines += [f"[{method.capitalize()}]", f"  threshold      : {thr}"]
        for k, v in stats.items():
            lines.append(f"  {k:<14} : {v}")
        lines.append("")
    lines += [
        "Output files",
        "  gray_input.png     - grayscale version of the input",
    ]
    if "sobel" in results:
        lines += [
            "  sobel_edges.png    - binary edge map from Verilog",
            "  sobel_golden.png   - reference from Python golden model",
        ]
    if "roberts" in results:
        lines += [
            "  roberts_edges.png  - gradient magnitude from Verilog",
            "  roberts_golden.png - reference from Python golden model",
        ]
    (out_dir / "summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="edge_detection",
        description="FPGA-verified edge detection (Roberts / Sobel) via Icarus Verilog",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            examples:
              py edge_detection.py -i input/joey.jpg -o output/run1 --method both
              py edge_detection.py -i input/joey.jpg -o output/run1 --method sobel --sobel-threshold 60
              py edge_detection.py -i input/joey.jpg -o output/run1 --method roberts --max-size 512
        """),
    )
    parser.add_argument("-i", "--input",  required=True, metavar="PATH",
                        help="input image (JPEG, PNG, BMP, ...)")
    parser.add_argument("-o", "--output", required=True, metavar="DIR",
                        help="output directory (created if absent)")
    parser.add_argument("--method",
                        choices=["sobel", "roberts", "both"], default="both",
                        metavar="METHOD",
                        help="sobel | roberts | both  (default: both)")
    parser.add_argument("--sobel-threshold",   type=int, default=80,  metavar="N",
                        help="Sobel binary threshold 0-255     (default: 80)")
    parser.add_argument("--roberts-threshold", type=int, default=30,  metavar="N",
                        help="Roberts gradient threshold 0-255 (default: 30)")
    parser.add_argument("--max-size", type=int, default=256, metavar="N",
                        help="resize longest edge to N pixels before processing "
                             "(default: 256, 0 = no resize)")
    args = parser.parse_args()

    input_path = Path(args.input)
    out_dir    = Path(args.output)

    if not input_path.exists():
        sys.exit(f"ERROR: File not found: {input_path}")

    _check_tools()
    out_dir.mkdir(parents=True, exist_ok=True)

    print()
    print("Edge Detection Pipeline")
    print(f"  Input  : {input_path}")
    print(f"  Output : {out_dir}")
    print(f"  Method : {args.method}")

    gray = _load_gray(input_path, args.max_size)
    height, width = gray.shape
    print(f"  Size   : {width}x{height}")
    Image.fromarray(gray, "L").save(out_dir / "gray_input.png")

    results = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)

        if args.method in ("sobel", "both"):
            print(f"\n[Sobel]  threshold = {args.sobel_threshold}")
            results["sobel"] = run_sobel(gray, args.sobel_threshold, tmp, out_dir)

        if args.method in ("roberts", "both"):
            print(f"\n[Roberts] threshold = {args.roberts_threshold}")
            results["roberts"] = run_roberts(gray, args.roberts_threshold, tmp, out_dir)

    _write_summary(out_dir, args, input_path, gray, results)

    print()
    for method, stats in results.items():
        v = stats["verification"]
        tag = "[PASS]" if v == "PASS" else "[FAIL]"
        print(f"  {tag} {method.capitalize()}: {v}")

    print(f"\nOutputs saved to: {out_dir}")
    print()


if __name__ == "__main__":
    main()
