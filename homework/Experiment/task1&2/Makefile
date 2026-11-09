CC = gcc
CFLAGS = -std=c11 -Wall -Wextra -Wpedantic -Werror -O2
CPPFLAGS =
LDFLAGS =
LDLIBS =

.PHONY: all check clean
all: build/sum

# $< 表示第一个依赖，$@ 表示当前目标；命令行以真正的 TAB 开头。
build/sum.o: src/sum.c
	mkdir -p build
	$(CC) $(CPPFLAGS) $(CFLAGS) -c $< -o $@

build/sum: build/sum.o
	$(CC) $(LDFLAGS) $< $(LDLIBS) -o $@

check: all
	bash -n src/sum.sh src/sum_named.sh
	python3 scripts/verify.py

# 仅删除本目录中的编译产物，不删除报告、截图和实验原始记录。
clean:
	rm -f build/sum.o build/sum
