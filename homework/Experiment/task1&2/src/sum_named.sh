#!/usr/bin/env bash
# 思考与实践：复用 sum.sh 的输入、日志与求和逻辑，再询问输出文件名。
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd) || exit 1
exec bash "$script_dir/sum.sh" --choose-output
