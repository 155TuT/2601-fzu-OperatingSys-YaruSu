#!/usr/bin/env bash
# 实验二：重定向、管道和文件合并。参数可用于在临时目录复现实验。
set -euo pipefail
target=${1:-"$HOME"}
root_dir=${2:-/}

# 重定向先创建 list1.txt，故它也会出现在这次文件清单里。
ls -l -- "$target" > "$target/list1.txt"
# 固定月份/日期格式，按字段精确过滤任意年份的 4 月 16 日。
# -A 包含隐藏条目、排除 . 和 ..；不递归遍历整棵文件系统。
LC_ALL=C ls -lA --time-style=+%m-%d -- "$root_dir" |
    awk '$6 == "04-16"' > "$target/list2.txt"
cat -- "$target/list1.txt" "$target/list2.txt" > "$target/list.txt"
printf 'Saved list1.txt, list2.txt and list.txt in %s\n' "$target"
wc -l -- "$target/list1.txt" "$target/list2.txt" "$target/list.txt"
