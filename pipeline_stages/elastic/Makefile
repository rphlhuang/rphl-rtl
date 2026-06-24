SIM ?= icarus
TOPLEVEL_LANG ?= verilog
WAVES = 1

VERILOG_SOURCES = $(PWD)/elastic.sv
COCOTB_TOPLEVEL = elastic
COCOTB_TEST_MODULES = test_elastic

export PYTHONPATH := $(PWD)/tb:$(PYTHONPATH)

COMPILE_ARGS += -g2012

include $(shell cocotb-config --makefiles)/Makefile.sim