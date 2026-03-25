module irq_router (
  input  logic [3:0] irq_req,
  input  logic [3:0] irq_mask,
  output logic       irq_valid,
  output logic [1:0] irq_id
);
  logic [3:0] masked_req;

  always_comb begin
    masked_req = irq_req & ~irq_mask;
    irq_valid = 1'b0;
    irq_id = 2'd0;

    if (masked_req[0]) begin
      irq_valid = 1'b1;
      irq_id = 2'd0;
    end else if (masked_req[1]) begin
      irq_valid = 1'b1;
      irq_id = 2'd1;
    end else if (masked_req[2]) begin
      irq_valid = 1'b1;
      irq_id = 2'd2;
    end else if (masked_req[3]) begin
      irq_valid = 1'b1;
      irq_id = 2'd3;
    end
  end
endmodule

