// IMG_WIDTH, IMG_HEIGHT, IMG_THRESHOLD can be set via iverilog -D flags.
// NO_VCD disables VCD generation (faster; recommended for production use).
`ifndef IMG_WIDTH
  `define IMG_WIDTH 64
`endif
`ifndef IMG_HEIGHT
  `define IMG_HEIGHT 64
`endif
`ifndef IMG_THRESHOLD
  `define IMG_THRESHOLD 30
`endif

`timescale 1ns / 1ps

module tb_roberts;

    // Constant multiply used to size localparams without a * operator
    function integer multiply;
        input integer a, b;
        integer i;
        begin
            multiply = 0;
            for (i = 0; i < b; i = i + 1)
                multiply = multiply + a;
        end
    endfunction

    localparam WIDTH      = `IMG_WIDTH;
    localparam HEIGHT     = `IMG_HEIGHT;
    localparam THRESHOLD  = `IMG_THRESHOLD;
    localparam TOTAL_PX   = multiply(WIDTH, HEIGHT);
    localparam OUT_WIDTH  = WIDTH  - 1;
    localparam OUT_HEIGHT = HEIGHT - 1;
    localparam OUT_PIXELS = multiply(OUT_WIDTH, OUT_HEIGHT);

    // ── Clock ──────────────────────────────────────────────────────
    reg clk;
    always #5 clk = ~clk;

    // ── DUT signals ────────────────────────────────────────────────
    reg        rst;
    reg        valid_in;
    reg  [7:0] pixel_in;
    wire       valid_out;
    wire [7:0] gradient_out;
    wire [7:0] binary_out;

    reg [7:0] pixel_mem [0:TOTAL_PX-1];

    integer out_file;
    integer out_count;
    integer i;

    roberts_top #(
        .WIDTH(WIDTH),
        .HEIGHT(HEIGHT),
        .THRESHOLD(THRESHOLD)
    ) dut (
        .clk(clk),
        .rst(rst),
        .valid_in(valid_in),
        .pixel_in(pixel_in),
        .valid_out(valid_out),
        .gradient_out(gradient_out),
        .binary_out(binary_out)
    );

    // ── Stimulus ───────────────────────────────────────────────────
    initial begin
`ifndef NO_VCD
        $dumpfile("roberts.vcd");
        $dumpvars(0, tb_roberts);
`endif
        $readmemh("image.hex", pixel_mem);
        $display("Loaded %0d pixels from image.hex", TOTAL_PX);

        out_file = $fopen("output_roberts.hex", "w");
        if (out_file == 0) begin
            $display("ERROR: Could not open output_roberts.hex");
            $finish;
        end
        out_count = 0;

        clk      = 0;
        rst      = 1;
        valid_in = 0;
        pixel_in = 8'd0;

        @(posedge clk); #1;
        @(posedge clk); #1;
        @(posedge clk); #1;
        rst = 0;
        @(posedge clk); #1;

        for (i = 0; i < TOTAL_PX; i = i + 1) begin
            @(posedge clk); #1;
            valid_in = 1;
            pixel_in = pixel_mem[i];
        end

        @(posedge clk); #1;
        valid_in = 0;
        pixel_in = 8'd0;
        repeat (10) @(posedge clk);

        $fclose(out_file);
        $display("Simulation complete: %0d output pixels written to output_roberts.hex", out_count);
        $display("Expected: %0d  (= %0d x %0d)", OUT_PIXELS, OUT_WIDTH, OUT_HEIGHT);
        if (out_count == OUT_PIXELS)
            $display("STATUS: PIXEL COUNT OK");
        else
            $display("STATUS: PIXEL COUNT MISMATCH");
        $finish;
    end

    // ── Output capture ─────────────────────────────────────────────
    always @(posedge clk) begin
        if (valid_out && !rst) begin
            $fwrite(out_file, "%02X\n", gradient_out);
            out_count = out_count + 1;
        end
    end

endmodule
