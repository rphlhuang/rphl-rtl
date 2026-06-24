import random

import cocotb
from cocotb.clock import Clock
from cocotb.queue import Queue
from cocotb.triggers import ClockCycles, ReadOnly, RisingEdge, FallingEdge

SEED = 42
WIDTH = 8
MAX = 1 << (WIDTH - 1)
NUM_MSGS = 200
DRIVER_DELAY_POOL = [0, 0, 0, 0, 1, 2, 4, 7]
TIMEOUT_CYCLES = 1000
CLOCK_PERIOD = 20

async def reset(dut):
    dut.rst_i.value = 1
    dut.s_valid_i.value = 0
    dut.s_data_i.value = 0
    dut.m_ready_i.value = 0
    await ClockCycles(dut.clk_i, 5)
    await FallingEdge(dut.clk_i)
    dut.rst_i.value = 0
    await FallingEdge(dut.clk_i)

async def driver(dut, rng, always_valid=False):
    for i in range(NUM_MSGS):
        # delay semi-random amount
        if not always_valid:
            for _ in range(rng.choice(DRIVER_DELAY_POOL)):
                await RisingEdge(dut.clk_i)
                dut.s_valid_i.value = 0
        
        # drive random data and valid_i high
        await RisingEdge(dut.clk_i)
        dut.s_valid_i.value = 1
        dut.s_data_i.value = rng.randint(0, MAX)

        # wait until handshake (ready_o), then repeat
        cycles_until_timeout = TIMEOUT_CYCLES
        while True:
            assert (cycles_until_timeout != 0), "Timed out while waiting for s_ready_o."
            await ReadOnly()
            if (dut.s_ready_o.value == 1):
                break
            await RisingEdge(dut.clk_i)
            cycles_until_timeout -= 1
    
    # deassert when done!
    await RisingEdge(dut.clk_i)
    dut.s_valid_i.value = 0

async def receiver(dut, rng, always_ready=False):
    # drive m_ready_i with random probability
    while True:
        await RisingEdge(dut.clk_i)
        dut.m_ready_i.value = 1 if ((rng.random() > 0.7) or always_ready) else 0

async def monitor(dut, ready, valid, data, q, name="UNKNOWN"):
    while True:
        await FallingEdge(dut.clk_i)
        await ReadOnly()
        if (ready.value == 1 and valid.value == 1):
            q.put_nowait(int(data.value))
            # dut._log.info(f"Monitor for {name} found handshake with value {int(data.value):02x}")

@cocotb.test()
async def test_single_transfer(dut):
    Clock(dut.clk_i, CLOCK_PERIOD, unit="ns").start()
    await reset(dut)

    await RisingEdge(dut.clk_i)
    dut.s_valid_i.value = 1
    dut.s_data_i.value = 0xFF
    
    await RisingEdge(dut.clk_i)
    dut.s_valid_i.value = 0
    dut.s_data_i.value = 0x00

    await ClockCycles(dut.clk_i, 5)
    await RisingEdge(dut.clk_i)
    dut.m_ready_i.value = 1

    await FallingEdge(dut.clk_i)
    got = dut.m_data_o.value
    expected = 0xFF
    assert (got == expected), f"Single cycle smoke test: got {got} but expected {expected}"


@cocotb.test()
async def test_fuzz(dut):
    rng = random.Random(SEED)
    Clock(dut.clk_i, CLOCK_PERIOD, unit="ns").start()
    await reset(dut)

    sent_q, received_q = Queue(), Queue()
    cocotb.start_soon(monitor(dut, dut.s_ready_o, dut.s_valid_i, dut.s_data_i, sent_q, name="UPSTREAM"))
    cocotb.start_soon(monitor(dut, dut.m_ready_i, dut.m_valid_o, dut.m_data_o, received_q, name="DOWNSTREAM"))
    cocotb.start_soon(receiver(dut, rng))
    driver_out = cocotb.start_soon(driver(dut, rng))

    for i in range(NUM_MSGS):
        expected = await sent_q.get()
        got = await received_q.get()
        # dut._log.info(f"On msg # {i}, remaining sent_q contents: {list(sent_q._queue)}")
        # dut._log.info(f"On msg # {i}, remaining received_q contents: {list(received_q._queue)}")
        assert got == expected, f"Message #{i}: sent 0x{expected:02x}, got 0x{got:02x}."

    await driver_out
    await ClockCycles(dut.clk_i, 10)

    assert received_q.empty(), "DUT produced more msgs than were sent."
    dut._log.info(f"{NUM_MSGS} messages passed!")


@cocotb.test()
async def test_max_throughput(dut):
    rng = random.Random(SEED)
    Clock(dut.clk_i, CLOCK_PERIOD, unit="ns").start()
    await reset(dut)

    t_start = cocotb.utils.get_sim_time(unit='ns')

    sent_q, received_q = Queue(), Queue()
    cocotb.start_soon(monitor(dut, dut.s_ready_o, dut.s_valid_i, dut.s_data_i, sent_q, name="UPSTREAM"))
    cocotb.start_soon(monitor(dut, dut.m_ready_i, dut.m_valid_o, dut.m_data_o, received_q, name="DOWNSTREAM"))
    cocotb.start_soon(receiver(dut, rng, always_ready=True))
    driver_out = cocotb.start_soon(driver(dut, rng, always_valid=True))

    for i in range(NUM_MSGS):
        expected = await sent_q.get()
        got = await received_q.get()
        # dut._log.info(f"On msg # {i}, remaining sent_q contents: {list(sent_q._queue)}")
        # dut._log.info(f"On msg # {i}, remaining received_q contents: {list(received_q._queue)}")
        assert got == expected, f"Message #{i}: sent 0x{expected:02x}, got 0x{got:02x}."

    await driver_out
    t_end = cocotb.utils.get_sim_time(unit='ns')
    await ClockCycles(dut.clk_i, 10)
    assert received_q.empty(), "DUT produced more msgs than were sent."

    num_cycles = (t_end - t_start) / CLOCK_PERIOD
    assert (num_cycles == (NUM_MSGS * 2)), f"Max throughput must be 1 message per 2 cycle, took {num_cycles} instead."
    dut._log.info(f"Max throughput test passed: took {num_cycles} cycles to pass {NUM_MSGS} msgs.")