//============================================================================
// roberts_core.v — Roberts Cross gradient computation (combinational)
//
// Takes a 2x2 pixel window and computes:
//   Gx = p00 - p11   (main diagonal difference)
//   Gy = p01 - p10   (anti-diagonal difference)
//   magnitude = |Gx| + |Gy|   (Manhattan approximation)
//   magnitude = min(magnitude, 255)  (saturate to 8-bit)
//   binary = (magnitude >= THRESHOLD) ? 255 : 0
//
// Pixel layout:
//   p00  p01    ← row R   (older row, from line buffer)
//   p10  p11    ← row R+1 (current row, direct input)
//
// Arithmetic matches the Python golden model in roberts_golden.py exactly.
//============================================================================

module roberts_core #(
    parameter THRESHOLD = 30
)(
    input  wire [7:0] p00,    // pixel[r][c]     — top-left
    input  wire [7:0] p01,    // pixel[r][c+1]   — top-right
    input  wire [7:0] p10,    // pixel[r+1][c]   — bottom-left
    input  wire [7:0] p11,    // pixel[r+1][c+1] — bottom-right
    output wire [7:0] gradient_out,
    output wire [7:0] binary_out
);

    // ── Step 1: Signed gradient computation ────────────────────────
    // Extend 8-bit unsigned pixels to 9-bit signed before subtraction.
    // Range of gx, gy: [-255, +255] — fits in 9 bits signed.
    wire signed [8:0] gx;
    wire signed [8:0] gy;

    assign gx = {1'b0, p00} - {1'b0, p11};   // main diagonal
    assign gy = {1'b0, p01} - {1'b0, p10};   // anti-diagonal

    // ── Step 2: Absolute values ────────────────────────────────────
    // Two's complement negation when sign bit is set.
    // Result range: [0, 255] — fits in 8 bits unsigned.
    wire [7:0] abs_gx;
    wire [7:0] abs_gy;

    assign abs_gx = gx[8] ? (~gx[7:0] + 8'd1) : gx[7:0];
    assign abs_gy = gy[8] ? (~gy[7:0] + 8'd1) : gy[7:0];

    // ── Step 3: Manhattan magnitude with saturation ────────────────
    // Sum range: [0, 510] — needs 9 bits.
    // Saturate to 255 if bit 8 is set.
    wire [8:0] sum;
    assign sum = {1'b0, abs_gx} + {1'b0, abs_gy};

    assign gradient_out = sum[8] ? 8'hFF : sum[7:0];

    // ── Step 4: Binary thresholding ────────────────────────────────
    assign binary_out = (gradient_out >= THRESHOLD) ? 8'hFF : 8'h00;

endmodule
