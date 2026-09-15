//============================================================================
// roberts_top.v — Roberts Cross edge detection top-level module
//
// Streaming architecture: one pixel in per clock, one pixel out per clock
// (after initial pipeline fill latency).
//
// Pipeline structure:
//   pixel_in → [line_buffer] → [2x2 sliding window regs] → [roberts_core] → outputs
//
// The line buffer delays by WIDTH clocks, giving access to row R (older)
// while the current input provides row R+1 (newer). Two-deep shift registers
// on each row provide the column-adjacent pixels for the 2x2 window.
//
// Output image dimensions: (WIDTH-1) x (HEIGHT-1)
// First valid output appears after WIDTH+1 valid input pixels.
//============================================================================

module roberts_top #(
    parameter WIDTH     = 64,
    parameter HEIGHT    = 64,
    parameter THRESHOLD = 30
)(
    input  wire       clk,
    input  wire       rst,
    input  wire       valid_in,
    input  wire [7:0] pixel_in,
    output reg        valid_out,
    output wire [7:0] gradient_out,
    output wire [7:0] binary_out
);

    // ── Line buffer: delays input stream by WIDTH clocks ───────────
    // Input:  current pixel (row R+1)
    // Output: pixel from same column, one row earlier (row R)
    wire [7:0] lb_out;

    line_buffer #(
        .WIDTH(WIDTH),
        .DATA_W(8)
    ) lb_inst (
        .clk(clk),
        .rst(rst),
        .valid_in(valid_in),
        .data_in(pixel_in),
        .data_out(lb_out)
    );

    // ── Sliding window shift registers (2 deep per row) ────────────
    // Each row has a 2-stage shift register.
    // Stage [0] = newest pixel (column c+1 in output terms)
    // Stage [1] = previous pixel (column c in output terms)
    //
    // row0 = older row (from line buffer = row R)
    // row1 = current row (direct input = row R+1)

    reg [7:0] row0_sr0, row0_sr1;   // row R:   sr0=newest, sr1=oldest
    reg [7:0] row1_sr0, row1_sr1;   // row R+1: sr0=newest, sr1=oldest

    always @(posedge clk) begin
        if (rst) begin
            row0_sr0 <= 8'd0;
            row0_sr1 <= 8'd0;
            row1_sr0 <= 8'd0;
            row1_sr1 <= 8'd0;
        end else if (valid_in) begin
            // Row R (from line buffer): shift
            row0_sr1 <= row0_sr0;
            row0_sr0 <= lb_out;

            // Row R+1 (current input): shift
            row1_sr1 <= row1_sr0;
            row1_sr0 <= pixel_in;
        end
    end

    // ── Window-to-core pixel mapping ───────────────────────────────
    //
    // Golden model:  gx = pixel[r][c]   - pixel[r+1][c+1]
    //                gy = pixel[r][c+1] - pixel[r+1][c]
    //
    // Register mapping:
    //   row0_sr1 = pixel[r][c]       (row R, older column)
    //   row0_sr0 = pixel[r][c+1]     (row R, newer column)
    //   row1_sr1 = pixel[r+1][c]     (row R+1, older column)
    //   row1_sr0 = pixel[r+1][c+1]   (row R+1, newer column)

    roberts_core #(
        .THRESHOLD(THRESHOLD)
    ) core_inst (
        .p00(row0_sr1),   // pixel[r][c]
        .p01(row0_sr0),   // pixel[r][c+1]
        .p10(row1_sr1),   // pixel[r+1][c]
        .p11(row1_sr0),   // pixel[r+1][c+1]
        .gradient_out(gradient_out),
        .binary_out(binary_out)
    );

    // ── Valid output control ───────────────────────────────────────
    // We track:
    //   pixel_count: total valid_in pulses received (0-based)
    //   col_count:   column position in current input row (0 to WIDTH-1)
    //
    // The line buffer needs WIDTH valid inputs to fill completely.
    // After that, lb_out presents valid row R data.
    // The shift registers need 1 additional clock to have 2 valid columns.
    // So: first valid output at pixel_count == WIDTH+1 (0-indexed), i.e.
    // after receiving the (WIDTH+2)th pixel... but let's think in terms of
    // when the window is fully populated:
    //
    //   - After WIDTH inputs: lb_out is valid (row 0, col 0)
    //   - That lb_out enters row0_sr0 on the same clock
    //   - On the NEXT clock (input WIDTH+1): row0_sr1 gets the first lb_out,
    //     row0_sr0 gets the second lb_out. Now we have 2 columns from row 0.
    //   - At this moment col_count = (WIDTH+1) % WIDTH = 1
    //
    // Output is valid when:
    //   1. pixel_count >= WIDTH + 1  (pipeline filled)
    //   2. col_count >= 1            (have 2 columns in shift registers)
    //
    // Output is NOT valid on the first column of each row (col_count == 0)
    // because the shift register only contains one column value.
    //
    // Total output pixels per row: WIDTH - 1
    // Total output rows: HEIGHT - 1
    // Total output pixels: (WIDTH-1) repeated (HEIGHT-1) times via addition

    reg [31:0] pixel_count;
    reg [15:0] col_count;

    always @(posedge clk) begin
        if (rst) begin
            pixel_count <= 32'd0;
            col_count   <= 16'd0;
            valid_out   <= 1'b0;
        end else if (valid_in) begin
            pixel_count <= pixel_count + 1;

            // Column counter: wraps at WIDTH
            if (col_count == WIDTH - 1)
                col_count <= 16'd0;
            else
                col_count <= col_count + 1;

            // Assert valid_out when pipeline is full and we have 2 columns
            if (pixel_count >= WIDTH && col_count != 0)
                valid_out <= 1'b1;
            else
                valid_out <= 1'b0;
        end else begin
            valid_out <= 1'b0;
        end
    end

endmodule
