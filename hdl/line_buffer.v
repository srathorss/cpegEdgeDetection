//============================================================================
// line_buffer.v — Parameterized shift-register line buffer
//
// Delays an input pixel stream by exactly WIDTH clock cycles.
// Used to provide simultaneous access to pixels from adjacent rows
// in a streaming image processing pipeline.
//
// When valid_in is high, data shifts through a WIDTH-deep chain of
// flip-flops. The output presents the pixel that entered WIDTH clocks ago.
//============================================================================

module line_buffer #(
    parameter WIDTH  = 64,
    parameter DATA_W = 8
)(
    input  wire              clk,
    input  wire              rst,
    input  wire              valid_in,
    input  wire [DATA_W-1:0] data_in,
    output wire [DATA_W-1:0] data_out
);

    // Shift register array — exactly WIDTH stages
    reg [DATA_W-1:0] sr [0:WIDTH-1];
    integer i;

    always @(posedge clk) begin
        if (rst) begin
            for (i = 0; i < WIDTH; i = i + 1)
                sr[i] <= {DATA_W{1'b0}};
        end else if (valid_in) begin
            // New pixel enters stage 0
            sr[0] <= data_in;
            // All other stages shift forward
            for (i = 1; i < WIDTH; i = i + 1)
                sr[i] <= sr[i-1];
        end
        // When valid_in is low, all registers hold their current values
    end

    // Output is the oldest pixel in the chain
    assign data_out = sr[WIDTH-1];

endmodule
