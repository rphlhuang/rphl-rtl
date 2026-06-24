module cocotb_iverilog_dump();
initial begin
    $dumpfile("sim_build/elastic.fst");
    $dumpvars(0, elastic);
end
endmodule
