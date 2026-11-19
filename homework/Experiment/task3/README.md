# 操作系统实验三

实验题目为“复杂 PC 问题——信号量与共享存储区”。[实验三报告](052403137_王智壹_OSEX3.docx) 采用课程要求第 4 页的模板。[实验一至三合订稿](052403137_王智壹_OSEX123.docx) 将实验三另起一页接在前两份报告后。正文也可在 [report.md](report.md) 中编辑。

## 编译和运行

在本目录执行以下命令。程序依次询问仓库容量和初始库存，分别输入 `3` 和 `1` 即为报告中的环形读写案例。

```sh
make
./build/pc 3 7
```

第一个参数是生产者和消费者各自的数量，范围为 1～32，默认各 4 个。第二个参数是随机种子，省略时按启动时间和进程号生成。种子控制角色抽取，进程号和唤醒顺序由 Linux 调度决定。容量可取 1～1024，初始库存可取 0 到容量。每个子进程执行一次存取，槽位从 0 编号。

父子进程、环形仓库和资源回收见 [pc.c](src/pc.c)。课程指定的四个信号量接口见 [mysem.h](src/mysem.h) 和 [mysem.c](src/mysem.c)。

## 验证和运行记录

```sh
make check
python3 scripts/verify.py --waits
```

`make check` 在 Linux 下用 Python 3 回放每次读写，核对产品顺序、库存和 IPC 对象回收，共 10 项检查。`--waits` 单独展示空仓、满仓时内核记录的等待进程数。

| 内容 | 白底终端截图 | 对应终端记录 |
| --- | --- | --- |
| 编译环境与构建 | [图 2](screenshots/01-build.png) | [01-build.txt](logs/01-build.txt) |
| 环形仓库存取 | [图 3](screenshots/02-ring.png) | [02-ring.txt](logs/02-ring.txt) |
| 空仓和满仓的等待 | [图 4](screenshots/03-waits.png) | [03-waits.txt](logs/03-waits.txt) |
| 10 项行为检查 | [图 5](screenshots/04-check.png) | [04-check.txt](logs/04-check.txt) |

## 生成报告

在有 X11 显示的 Linux 终端中运行 `python3 scripts/capture.py`，可用 xterm、Pillow 和 python-xlib 重新执行四组命令并截图。运行 `python3 scripts/build_report.py`，可用 python-docx 将 Markdown 正文和现有插图生成两份 Word 文档。

实验依据为[《计算机操作系统实验要求》第 4 页](../task-requirement/计算机操作系统实验要求.docx)、[《计算机操作系统上机作业》第 10—15 页](../task-requirement/计算机操作系统上机作业.pptx)和[《PC 问题相关 API》](../task-requirement/%284%29%20PC问题相关API.docx)。
