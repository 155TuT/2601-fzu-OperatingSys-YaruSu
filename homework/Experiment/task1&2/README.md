# 操作系统实验一、实验二

两次实验放在同一份 [Word 报告](学号待填写_姓名待填写_OSEX12.docx) 中，按 `task-requirement/计算机操作系统实验要求.docx` 第 2、3 页的栏目编写，具体内容对应 PPT 第 2—9 页。实验二另起一页。学号、姓名、班级均按要求保留“待填写”；提交前补全并修改文件名。

- `src/`：有注释的 C 程序、基本求和脚本、自选输出脚本和文件清单脚本。
- `Makefile`：编译、链接、依赖关系、检查和清理目标。
- `screenshots/`：真实 X11 终端和图形程序截图；终端背景为白色。
- `evidence/home/`：实际压缩包、文件清单、错误日志和计算结果的副本。
- `logs/`：执行命令、原始输出、退出状态、验证结果及报告插图信息。
- `preview/`：与 Word 内容相同的 PDF 预览，便于检查分页。
- `scripts/`：验证、截图和生成报告的脚本。

## 编译与验证

在本目录执行：

```bash
make
make check
printf '10\n' | ./build/sum
```

`make check` 使用临时目录检查文件行为，不会覆盖主目录中的实验结果。严格编译开启 `-std=c11 -Wall -Wextra -Wpedantic -Werror`。本次 30 项检查全部通过，详见 [verification.log](logs/verification.log)。

为查看增量构建行为，可执行：

```bash
make -q
make -n -W src/sum.c
```

前者在目标已更新时返回 0；后者只展示假设源码更新后需要执行的编译和链接命令。

## 运行脚本

脚本将结果写入**当前工作目录**。建议在空的练习目录中运行，先查看非法输入，再查看正确输入：

```bash
printf '%s\n' -1 | /绝对路径/src/sum.sh
code=$?
printf 'exit status = %s\n' "$code"
cat error.log

printf '10\n' | /绝对路径/src/sum.sh
code=$?
printf 'exit status = %s\n' "$code"
cat sum.r
```

必测结果：`-1` 追加 `<当前时间> Input Error！ n = -1` 并退出 5；`10` 写入 `55` 至 `sum.r` 并退出 0，保留原有错误日志。默认结果文件为 `sum.r`；自选文件可运行 `src/sum_named.sh`，或运行 `src/sum.sh --choose-output`。后者依次询问整数和文件名，支持文件名中含空格。

C 程序接受 0 至 2147483647，0 的和为 0；Shell 脚本按题目要求只接受正整数，范围为 1 至 2147483647。两者使用 64 位乘法计算 `n(n+1)/2`，避免 32 位求和溢出。

文件清单步骤可用以下脚本重复执行。默认读取用户主目录和根目录，将三份清单写入用户主目录；参数可改为独立练习目录及测试目录：

```bash
bash src/collect_lists.sh /练习目录 /
```

日期管道采用 `LC_ALL=C ls -lA --time-style=+%m-%d / | awk '$6 == "04-16"'`，筛选根目录一级条目的修改月份和日期，不限制年份。当前系统没有符合条件的条目，所以本次 `list2.txt` 为 0 字节；`list1.txt` 和 `list.txt` 均为 15 行。验证程序用临时样例检验了不同年份的 4 月 16 日、4 月 17 日及无匹配情况。

## 实际环境与文件操作

本次在 WSL2 的 Ubuntu 24.04.2 LTS（x86_64）上执行，使用 GCC 13.3.0、Bash 5.2、GNU Make 4.3 和 nano 7.2。PPT 中的 Ubuntu 12.4（32 位）及 `/home/osstudy` 是参考环境；实际登录用户主目录为 `/home/ovo155`，没有模拟或冒称旧系统。

实验步骤实际在用户主目录执行：建立 A、bin，通过 nano 保存源码，编译后复制到 bin，将 A 的全部内容压缩到 `sum.tar.gz`，设置 755 权限，删除本次创建的 A，再实际解压并校验恢复结果。原始主目录的 bin、压缩包、恢复目录及实验二输出仍保留。`logs/evidence-checks.json` 记录了 A 删除、755 权限及 nano 保存内容与提交源码一致的检查。

WSL 环境根目录有许多附加条目，图1展示清单节选；完整输出和 A、bin 的创建记录均保存在 `logs/01-root-and-directories.log`。当前未接入供实验使用的 U 盘，报告中的挂载命令为操作说明，未把实际挂载写作已经完成。

## 报告与截图的复现

生成 Word 报告需要 `python-docx`、`Pillow`，然后执行：

```bash
python3 scripts/build_report.py
```

此命令读取既有截图和证据，复用课程模板的段落及页面设置，不重新执行主目录实验。PDF 预览由 LibreOffice 导出。

`capture_evidence.py` 需要 Xvfb、xterm、nano、Pillow 和 python-xlib，会实际创建主目录实验文件；若已有同名文件，默认拒绝覆盖。`--root-only` 只补拍根目录只读步骤，`--lists-only` 会重新生成三份清单，`--shell-only` 重新打开本次已有的 `sum.sh` 并拍摄完整编辑器画面。`capture_gui.py` 打开文件管理器、浏览器、文字处理及图形软件包管理器，只进行查看。截图由 X11 窗口直接获取，未重绘或用生成图片替代运行证据。`OS_LAB_TOOL_ROOT` 可用于指定临时解包的工具目录。

课程提供的要求文件保持原样；本目录没有包含实验三、四的未完成报告。
