#!/usr/bin/env bash
# 实验二：默认写入 sum.r；--choose-output 实现“先询问输出文件名”。
# 输入限制为 32 位正整数，使 Bash 的 64 位整数运算不会溢出。
set -u

choose_output=0
if [[ $# -eq 1 && $1 == --choose-output ]]; then
    choose_output=1
elif [[ $# -ne 0 ]]; then
    printf 'Usage: %s [--choose-output]\n' "$0" >&2
    exit 2
fi

input_error() {
    local message
    message="$(date '+%Y-%m-%d %H:%M:%S') Input Error！ n = $raw"
    # >> 保留以前的错误记录；先检查日志写入结果。
    if ! printf '%s\n' "$message" >> error.log; then
        exit 1
    fi
    printf '%s\n' "$message" >&2
    exit 5
}

printf 'Please enter a positive integer n: '
raw=''
IFS= read -r raw || [[ -n $raw ]] || input_error
[[ $raw =~ ^[+]?[0-9]+$ ]] || input_error
digits=${raw#+}
# 去掉前导零后再检查范围，避免把 08 当成八进制或让超长数字回绕。
while [[ ${#digits} -gt 1 && $digits == 0* ]]; do
    digits=${digits#0}
done
[[ ${#digits} -le 10 ]] || input_error
[[ $digits -gt 0 && $digits -le 2147483647 ]] || input_error
n=$((10#$digits))
sum=$((n * (n + 1) / 2))

output='sum.r'
if ((choose_output)); then
    printf 'Output filename: '
    if ! IFS= read -r output || [[ -z $output ]]; then
        printf 'Output Error! A filename is required.\n' >&2
        exit 1
    fi
fi
# 引号保证文件名中含空格时仍是一个路径；写入失败不得报告成功。
if ! printf '%s\n' "$sum" > "$output"; then
    exit 1
fi
printf '1 + ... + %s = %s; saved to %s\n' "$n" "$sum" "$output"
exit 0
