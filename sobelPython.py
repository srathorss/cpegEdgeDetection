"""
Sobel Edge Detection — From Scratch with NumPy
================================================
No OpenCV. Every step is explicit so you can see exactly
what the hardware (Verilog) version would be doing in software.

Pipeline:
  1. Load / generate a grayscale image
  2. Pad the image (so the 3×3 kernel can reach border pixels)
  3. Slide the 3×3 window and apply Gx, Gy kernels (convolution)
  4. Compute gradient magnitude: |Gx| + |Gy|  (hardware-friendly)
  5. Threshold to produce a binary edge map
  6. Save & display results
"""

import numpy as np
from PIL import Image, ImageDraw
import matplotlib.pyplot as plt


# ──────────────────────────────────────────────
# STEP 1 — Generate a synthetic test image
# ──────────────────────────────────────────────
# We draw simple shapes with sharp edges so the
# Sobel filter has clear features to detect.

def make_test_image(width=256, height=256):
    """Create a grayscale test image with rectangles, a circle, and a gradient."""
    img = Image.new("L", (width, height), color=30)   # dark background
    draw = ImageDraw.Draw(img)

    # Bright rectangle
    draw.rectangle([40, 40, 120, 120], fill=200)

    # Medium-gray rectangle (partially overlapping)
    draw.rectangle([80, 80, 180, 180], fill=140)

    # Bright circle
    draw.ellipse([150, 30, 230, 110], fill=220)

    # Horizontal gradient bar at the bottom
    for x in range(width):
        brightness = int(255 * x / width)
        draw.line([(x, 210), (x, 245)], fill=brightness)

    return np.array(img, dtype=np.float64)


# ──────────────────────────────────────────────
# STEP 2 — Define the Sobel kernels
# ──────────────────────────────────────────────
# These are the same two 3×3 matrices you learned about:
#
#  Gx (horizontal edges)      Gy (vertical edges)
#  ┌──────────────────┐       ┌──────────────────┐
#  │ -1   0   +1      │       │ -1  -2  -1       │
#  │ -2   0   +2      │       │  0   0   0       │
#  │ -1   0   +1      │       │ +1  +2  +1       │
#  └──────────────────┘       └──────────────────┘

SOBEL_GX = np.array([
    [-1,  0,  1],
    [-2,  0,  2],
    [-1,  0,  1]
], dtype=np.float64)

SOBEL_GY = np.array([
    [-1, -2, -1],
    [ 0,  0,  0],
    [ 1,  2,  1]
], dtype=np.float64)


# ──────────────────────────────────────────────
# STEP 3 — Pad the image
# ──────────────────────────────────────────────
# The 3×3 kernel needs 1 pixel of padding on each
# side so it doesn't run off the edge of the image.
# This mirrors what the line buffers handle in the
# Verilog version — except here we just add zeros.

def pad_image(image, pad=1):
    """Zero-pad the image by `pad` pixels on every side."""
    h, w = image.shape
    padded = np.zeros((h + 2 * pad, w + 2 * pad), dtype=image.dtype)
    padded[pad:pad + h, pad:pad + w] = image
    return padded


# ──────────────────────────────────────────────
# STEP 4 — Convolution (the core operation)
# ──────────────────────────────────────────────
# Slide a 3×3 window across every pixel, multiply
# element-wise with the kernel, and sum.
#
# In Verilog you'd do this with shift registers and
# adders running in parallel. Here we do it with a
# nested loop so each step is transparent.

def convolve_3x3(image, kernel):
    """
    Apply a 3×3 kernel to every pixel of `image`.
    Returns a result the same size as the *original*
    (un-padded) image.
    """
    padded = pad_image(image, pad=1)
    h, w = image.shape
    result = np.zeros((h, w), dtype=np.float64)

    for row in range(h):
        for col in range(w):
            # Extract the 3×3 neighbourhood
            window = padded[row:row + 3, col:col + 3]

            # Element-wise multiply and sum — this IS the convolution
            result[row, col] = np.sum(window * kernel)

    return result


# ──────────────────────────────────────────────
# STEP 5 — Gradient magnitude
# ──────────────────────────────────────────────
# True magnitude is  sqrt(Gx² + Gy²)  but in hardware
# we use the approximation  |Gx| + |Gy|  because it
# avoids a square root (expensive in logic gates).
# We'll compute both so you can compare.

def gradient_magnitude(gx, gy, method="abs_sum"):
    """
    Combine horizontal and vertical gradients.
      'abs_sum'   — |Gx| + |Gy|   (hardware-friendly)
      'euclidean' — sqrt(Gx² + Gy²)
    """
    if method == "abs_sum":
        mag = np.abs(gx) + np.abs(gy)
    else:
        mag = np.sqrt(gx ** 2 + gy ** 2)

    # Clamp to 0–255 range
    mag = np.clip(mag, 0, 255)
    return mag


# ──────────────────────────────────────────────
# STEP 6 — Threshold to binary edge map
# ──────────────────────────────────────────────
# Just like the comparator in the Verilog pipeline:
# if gradient > threshold → edge (white), else → no edge (black)

def threshold(image, thresh=80):
    """Binary threshold: pixels above `thresh` become 255, rest become 0."""
    return np.where(image > thresh, 255, 0).astype(np.uint8)


# ──────────────────────────────────────────────
# PUTTING IT ALL TOGETHER
# ──────────────────────────────────────────────

def sobel_edge_detect(image, thresh=80):
    """
    Full Sobel pipeline on a 2-D grayscale numpy array.
    Returns: gx, gy, magnitude, edges
    """
    # Apply each kernel
    gx = convolve_3x3(image, SOBEL_GX)
    gy = convolve_3x3(image, SOBEL_GY)

    # Combine gradients (hardware-friendly way)
    mag = gradient_magnitude(gx, gy, method="abs_sum")

    # Threshold
    edges = threshold(mag, thresh)

    return gx, gy, mag, edges


# ──────────────────────────────────────────────
# RUN & DISPLAY
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # 1. Create test image
    print("Generating test image...")
    img = make_test_image()

    # 2. Run the Sobel pipeline
    print("Running Sobel edge detection...")
    gx, gy, mag, edges = sobel_edge_detect(img, thresh=80)

    # 3. Plot everything side by side
    fig, axes = plt.subplots(2, 3, figsize=(14, 9))

    panels = [
        (img,   "Original (grayscale)",  "gray"),
        (gx,    "Gx (horizontal edges)", "gray"),
        (gy,    "Gy (vertical edges)",   "gray"),
        (mag,   "|Gx| + |Gy| magnitude", "gray"),
        (edges, "Thresholded edges",     "gray"),
    ]

    for ax, (data, title, cmap) in zip(axes.flat, panels):
        ax.imshow(data, cmap=cmap, vmin=data.min(), vmax=data.max())
        ax.set_title(title, fontsize=12)
        ax.axis("off")

    # Hide the unused 6th subplot
    axes[1, 2].axis("off")

    plt.tight_layout()
    plt.savefig("/home/claude/sobel_results.png", dpi=150)
    print("Results saved to sobel_results.png")
    plt.close()

    # Also save the edge map on its own
    edge_img = Image.fromarray(edges)
    edge_img.save("/home/claude/edges_only.png")
    print("Binary edge map saved to edges_only.png")
    print("Done!")