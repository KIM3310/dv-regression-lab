`timescale 1ns/1ps

module tb_irq_router_smoke;
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
    $dumpfile("irq_router_smoke.vcd");
    $dumpvars(0, tb_irq_router_smoke);

    irq_req = 4'b0000;
    irq_mask = 4'b0000;
    #1;

    irq_req = 4'b0100;
    #1;
    if (!(irq_valid && irq_id == 2'd2)) begin
      $display("ASSERTION FAILED: irq routing smoke expected id=2 valid=1");
      $fatal(1);
    end

    irq_mask = 4'b0100;
    #1;
    if (irq_valid) begin
      $display("ASSERTION FAILED: irq should be masked");
      $fatal(1);
    end

    $display("TEST_PASS: irq routing smoke");
    $finish;
  end
endmodule

