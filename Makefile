# Top-level Makefile for taxi-on-ryusim
.PHONY: all test clean setup

all: test

setup:
	./setup_ryusim.sh

test:
	pytest src/ -v --junitxml=results/junit.xml

clean:
	find src/ -name sim_build -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name obj_dir -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find src/ -name results.xml -delete 2>/dev/null || true
	find src/ -name "*.fst" -delete 2>/dev/null || true
	find src/ -name "*.vcd" -delete 2>/dev/null || true
	rm -rf results/
