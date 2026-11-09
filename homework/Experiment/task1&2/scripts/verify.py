#!/usr/bin/env python3
"""用独立的临时工作目录验证作业的计算结果、文件和退出状态。"""
from pathlib import Path
import os
import re
import subprocess
import tempfile

BASE = Path(__file__).resolve().parents[1]
checks = 0


def run(args, data="", cwd=None):
    return subprocess.run(args, input=data, text=True, capture_output=True,
                          cwd=cwd, timeout=10)


def check(condition, name):
    global checks
    if not condition:
        raise AssertionError(name)
    checks += 1
    print(f"PASS {checks:02d}: {name}")


for n in [0, 1, 10, 65536, 2147483647]:
    r = run([str(BASE / "build/sum")], f"{n}\n")
    check(r.returncode == 0 and f"= {n * (n + 1) // 2}\n" in r.stdout,
          f"C sum n={n}")
for value in ["-1", "abc", "10abc", "1.5", "", "2147483648", "9" * 200]:
    r = run([str(BASE / "build/sum")], value + "\n")
    check(r.returncode != 0 and "Input Error!" in r.stderr,
          f"C rejects {value[:18]!r}")

with tempfile.TemporaryDirectory(prefix="os-ex12-check-") as tmp:
    work = Path(tmp)
    script = ["bash", str(BASE / "src/sum.sh")]
    r = run(script, "-1\n", work)
    log = (work / "error.log").read_text()
    check(r.returncode == 5 and not (work / "sum.r").exists()
          and re.fullmatch(r"\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2} Input Error！ n = -1\n", log),
          "n=-1 appends a dated log, exits 5 and creates no result")
    r = run(script, "10\n", work)
    check(r.returncode == 0 and (work / "sum.r").read_text() == "55\n"
          and (work / "error.log").read_text() == log,
          "n=10 writes 55, exits 0 and keeps error.log unchanged")
    r = run(script, "0\n", work)
    check(r.returncode == 5 and (work / "sum.r").read_text() == "55\n"
          and (work / "error.log").read_text().startswith(log)
          and len((work / "error.log").read_text().splitlines()) == 2,
          "invalid input appends rather than overwrites and preserves prior result")
    for value in ["abc", "1.5", "", "2147483648", "9" * 100]:
        r = run(script, value + "\n", work)
        check(r.returncode == 5, f"shell rejects {value[:18]!r}")
    for value, n in [("08", 8), ("+10", 10), ("00010", 10), ("65536", 65536),
                     ("2147483647", 2147483647)]:
        r = run(script, value + "\n", work)
        check(r.returncode == 0 and (work / "sum.r").read_text() == f"{n * (n + 1) // 2}\n",
              f"shell decimal/range handling n={value}")
    r = run(["bash", str(BASE / "src/sum_named.sh")], "10\nmy result.txt\n", work)
    check(r.returncode == 0 and (work / "my result.txt").read_text() == "55\n",
          "extension asks for a filename and supports spaces")
    (work / "blocked").mkdir()
    r = run(script + ["--choose-output"], "10\nblocked\n", work)
    check(r.returncode == 1 and "saved to" not in r.stdout,
          "output failure returns an error")

    root = work / "fixture-root"
    dest = work / "lists"
    root.mkdir()
    dest.mkdir()
    for name, date in [("april16-old", "2024-04-16 12:00:00"),
                       ("april16-new", "2026-04-16 23:59:00"),
                       ("april17", "2026-04-17 00:00:00")]:
        path = root / name
        path.touch()
        subprocess.run(["touch", "-d", date, str(path)], check=True)
    r = run(["bash", str(BASE / "src/collect_lists.sh"), str(dest), str(root)])
    selected = (dest / "list2.txt").read_text()
    check(r.returncode == 0 and "april16-old" in selected
          and "april16-new" in selected and "april17" not in selected,
          "pipeline matches April 16 across years and excludes April 17")
    check((dest / "list.txt").read_bytes() == (dest / "list1.txt").read_bytes()
          + (dest / "list2.txt").read_bytes(), "list concatenation is byte-exact")
    for path in root.iterdir():
        os.utime(path, (0, 0))
    r = run(["bash", str(BASE / "src/collect_lists.sh"), str(dest), str(root)])
    check(r.returncode == 0 and (dest / "list2.txt").stat().st_size == 0,
          "no April 16 entries is a successful empty result")

print(f"All {checks} checks passed.")
