`timescale 1ns/1ps

module tb_irq_router_negative;
  logic [3:0] irq_req;
  logic [3:0] irq_mask;
  logic irq_valid;
  logic [1:0] irq_id;

  irq_router dut (
    .irq_req(irq_req),
    .irq_mask(irq_mask),
    .irq_valid(irq_valid),
    .irq_id(irq_id)
  );

  initial begin
    $dumpfile("irq_router_negative.vcd");
    $dumpvars(0, tb_irq_router_negative);

    irq_req = 4'b1010;
    irq_mask = 4'b0000;
    #1;

    if (!(irq_valid && irq_id == 2'd3)) begin
      $display("ASSERTION FAILED: irq priority mismatch");
      $fatal(1);
    end

    $display("TEST_PASS: irq negative");
    $finish;
  end
endmodule

