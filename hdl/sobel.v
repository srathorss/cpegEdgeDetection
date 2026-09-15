// ============================================================
// sobel.v — Streaming Sobel Edge Detector
// ============================================================
// Pixels stream in one-per-clock, row-major (left to right, top to bottom).
// Two line buffers store previous rows so we always have a 3x3 window.
//
//  Pipeline (2-stage):
//
//  Stage 0: Window Load (clocked)
//  ──────────────────────────────
//  pixel_in ──┬──> [line_buf1] ──> [line_buf0]
//             |        |                |
//           row2     row1             row0
//             └────────┴────────────────┘
//                     3x3 window regs
//
//  Stage 1: Compute + Threshold (comb -> registered output)
//  ────────────────────────────────────────────────────────
//                    Gx, Gy  (combinational)
//                  |Gx|+|Gy| (combinational)
//                  threshold -> pixel_out, out_valid (registered)
//
// After the window fills (row >= 2, col >= 2), the output becomes
// valid one cycle later.  Output image is (IMG_W-2) x (IMG_H-2).
// ============================================================

module sobel #(
    parameter IMG_W     = 64,
    parameter IMG_H     = 64,
    parameter THRESHOLD = 80
)(
    input  wire        clk,
    input  wire        rst,
    input  wire [7:0]  pixel_in,
    input  wire        pixel_valid,
    output reg  [7:0]  pixel_out,
    output reg         out_valid
);

    // -- Position counters --
    reg [15:0] col_cnt;
    reg [15:0] row_cnt;

    // -- Line buffers (RAM) --
    reg [7:0] lb0 [0:IMG_W-1];   // row from 2 rows ago
    reg [7:0] lb1 [0:IMG_W-1];   // row from 1 row  ago

    // -- 3x3 window registers --
    //   p00 p01 p02    <- row 0 (oldest)
    //   p10 p11 p12    <- row 1
    //   p20 p21 p22    <- row 2 (newest / current)
    reg [7:0] p00, p01, p02;
    reg [7:0] p10, p11, p12;
    reg [7:0] p20, p21, p22;

    // -- Pipeline valid flag --
    // Registered so output fires 1 cycle after window loads,
    // giving the combinational gx/gy/mag time to settle on
    // the updated window values.
    reg win_filled;

    // -- Gradient computation (combinational) --
    // Max |Gx| or |Gy| = 255+510+255 = 1020 -> 11 bits + sign
    wire signed [11:0] gx;
    wire signed [11:0] gy;
    wire        [11:0] abs_gx;
    wire        [11:0] abs_gy;
    wire        [11:0] mag;

    // Gx = right_col - left_col
    //     (p02 + 2*p12 + p22) - (p00 + 2*p10 + p20)
    assign gx = ({4'd0, p02} + ({4'd0, p12} << 1) + {4'd0, p22})
              - ({4'd0, p00} + ({4'd0, p10} << 1) + {4'd0, p20});

    // Gy = bottom_row - top_row
    //     (p20 + 2*p21 + p22) - (p00 + 2*p01 + p02)
    assign gy = ({4'd0, p20} + ({4'd0, p21} << 1) + {4'd0, p22})
              - ({4'd0, p00} + ({4'd0, p01} << 1) + {4'd0, p02});

    // Absolute value (two's complement negate if negative)
    assign abs_gx = gx[11] ? (~gx + 12'd1) : gx;
    assign abs_gy = gy[11] ? (~gy + 12'd1) : gy;

    // Hardware-friendly magnitude: |Gx| + |Gy|
    assign mag = abs_gx + abs_gy;

    // -- Stage 0: Window load + line buffer update --
    integer i;

    always @(posedge clk) begin
        if (rst) begin
            col_cnt <= 0;
            row_cnt <= 0;
            p00 <= 0; p01 <= 0; p02 <= 0;
            p10 <= 0; p11 <= 0; p12 <= 0;
            p20 <= 0; p21 <= 0; p22 <= 0;
            win_filled <= 0;
            for (i = 0; i < IMG_W; i = i + 1) begin
                lb0[i] <= 0;
                lb1[i] <= 0;
            end
        end else if (pixel_valid) begin
            // Shift 3x3 window: new column enters from the right
            p00 <= p01;  p01 <= p02;  p02 <= lb0[col_cnt];
            p10 <= p11;  p11 <= p12;  p12 <= lb1[col_cnt];
            p20 <= p21;  p21 <= p22;  p22 <= pixel_in;

            // Cascade line buffers down
            lb0[col_cnt] <= lb1[col_cnt];
            lb1[col_cnt] <= pixel_in;

            // Advance position
            if (col_cnt == IMG_W - 1) begin
                col_cnt <= 0;
                row_cnt <= row_cnt + 1;
            end else begin
                col_cnt <= col_cnt + 1;
            end

            // Flag: the window will be valid after this cycle's
            // non-blocking assignments complete, so we register
            // the flag — the output stage reads it next cycle.
            win_filled <= (row_cnt >= 2) && (col_cnt >= 2);
        end else begin
            win_filled <= 0;
        end
    end

    // -- Stage 1: Threshold + output register --
    // Fires one cycle after win_filled, so gx/gy/mag
    // are computed from the fully-updated window.
    always @(posedge clk) begin
        if (rst) begin
            pixel_out <= 0;
            out_valid <= 0;
        end else begin
            out_valid <= win_filled;
            if (win_filled) begin
                pixel_out <= (mag > THRESHOLD) ? 8'hFF : 8'h00;
            end
        end
    end

endmodule
