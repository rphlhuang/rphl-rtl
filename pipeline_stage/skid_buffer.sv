module skid_buffer #(
    parameter int WIDTH = 8
) (
    input  wire clk_i,
    input  wire rst_i,

    input  wire              s_valid_i,
    output logic             s_ready_o,
    input  wire  [WIDTH-1:0] s_data_i,

    output logic             m_valid_o,
    input  wire              m_ready_i,
    output logic [WIDTH-1:0] m_data_o
);

typedef enum logic [1:0] {
    IDLE,
    PASS,
    HOLD
} state_t;

state_t state_r, state_n;
logic [0:0] valid_ol, ready_ol;
logic [WIDTH-1:0] data_r, data_n;


always @(posedge clk_i) begin
    if (rst_i) begin
        state_r <= IDLE;
        data_r <= '0;
    end else begin
        state_r <= state_n;
        data_r <= data_n;
    end
end

always_comb begin
    state_r = state_n;
    data_r = data_n;
    case (state_r)
        IDLE: begin
            valid_ol = 1'b0;
            ready_ol = 1'b1;
            if (s_valid_i) begin
                state_n = BUSY;
                data_n = s_data_i;
            end else begin
                state_n = IDLE;
            end
        end

        BUSY: begin
            valid_ol = 1'b1;
            ready_ol = 1'b0;
            if (m_ready_i) begin
                state_n = IDLE;
            end else begin
                state_n = BUSY;
            end
        end

        default: begin
            state_n = IDLE;
        end
    endcase
end

assign m_data_o = data_r;
assign m_valid_o = valid_ol;
assign s_ready_o = ready_ol;

endmodule