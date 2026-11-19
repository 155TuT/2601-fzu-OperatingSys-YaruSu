CC = gcc
CFLAGS = -std=c11 -O2 -Wall -Wextra -Wpedantic -Werror
CPPFLAGS = -D_POSIX_C_SOURCE=200809L

build/pc: build/pc.o build/mysem.o
	$(CC) $(LDFLAGS) $^ $(LDLIBS) -o $@

build/%.o: src/%.c src/mysem.h | build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build:
	mkdir -p $@

.PHONY: check clean
check: build/pc
	python3 scripts/verify.py

clean:
	$(RM) build/pc build/pc.o build/mysem.o
