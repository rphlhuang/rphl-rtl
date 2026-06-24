module elastic #(
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

typedef enum logic [0:0] { IDLE, FULL } state_t;
state_t state_r, state_n;
logic [WIDTH-1:0] data_r, data_n;

assign m_data_o = data_r;

always_ff @( posedge clk_i ) begin : ff_elastic
    if (rst_i) begin
        state_r <= IDLE;
        data_r <= '0;
    end else begin
        state_r <= state_n;
        data_r <= data_n;
    end
end

always_comb begin
    state_n = state_r;
    data_n = data_r;

    case (state_r)
        IDLE: begin
            s_ready_o = 1'b1;
            m_valid_o = 1'b0;
            if (s_valid_i) begin
                state_n = FULL;
                data_n = s_data_i;
            end else begin
                state_n = IDLE;
            end
        end

        FULL: begin
            s_ready_o = 1'b0;
            m_valid_o = 1'b1;
            if (m_ready_i) begin
                state_n = IDLE;
            end else begin
                state_n = FULL;
            end
        end
    endcase
end

endmodule