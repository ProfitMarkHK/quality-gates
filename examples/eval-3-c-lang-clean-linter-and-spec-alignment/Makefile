.PHONY: build test lint check clean

build:
	cmake -S . -B build && cmake --build build

test: build
	ctest --test-dir build --output-on-failure

lint:
	clang-tidy src/*.c -- -Iinclude

check: build lint test

clean:
	rm -rf build
