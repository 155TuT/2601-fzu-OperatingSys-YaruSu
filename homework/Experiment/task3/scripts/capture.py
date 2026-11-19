#!/usr/bin/env python3
"""在真实的白底 xterm 内执行交互命令，同时保存窗口像素和终端记录。"""
import os
from pathlib import Path
import select
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[1]
CASES = {
    "01-build": (108, 11, [("uname -smr", "$ "), ("gcc -dumpfullversion", "$ "),
                          ("make -B", "$ ")]),
    "02-ring": (67, 30, [("./build/pc 3 7", "Warehouse capacity"),
                         ("3", "Initial stock"), ("1", "$ ")]),
    "03-waits": (63, 15, [("python3 scripts/verify.py --waits", "$ ")]),
    "04-check": (65, 15, [("make check", "$ ")]),
}


def terminal(name, tmp):
    # script 分配伪终端，Bash 和实验程序均从此终端读取输入。
    shell = "env PS1='$ ' TERM=dumb HISTFILE=/dev/null bash --noprofile --norc -i"
    with subprocess.Popen(["script", "-qe", "--echo", "always", "-c", shell, "/dev/null"],
                          cwd=ROOT, stdin=subprocess.PIPE, stdout=subprocess.PIPE) as proc:
        transcript = bytearray()

        def read_until(marker):
            start = len(transcript)
            until = time.monotonic() + 20
            while marker.encode() not in transcript[start:]:
                if not select.select([proc.stdout], [], [], max(0, until - time.monotonic()))[0]:
                    raise TimeoutError(marker)
                data = os.read(proc.stdout.fileno(), 8192)
                if not data:
                    raise RuntimeError(f"terminal ended before {marker!r}")
                transcript.extend(data)
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()

        try:
            read_until("$ ")
            for command, marker in CASES[name][2]:
                proc.stdin.write((command + "\n").encode())
                proc.stdin.flush()
                read_until(marker)
            log = transcript.decode().replace("\r", "").rstrip() + "\n"
            (ROOT / "logs" / (name + ".txt")).write_text(log)
            (tmp / "ready").touch()
            until = time.monotonic() + 30
            while not (tmp / "captured").exists() and time.monotonic() < until:
                time.sleep(.05)
        finally:
            proc.stdin.write(b"exit\n")
            proc.stdin.flush()


def capture(display, name, cols, rows, tmp):
    from PIL import Image
    from Xlib import X

    title = f"OS EX3 {name} {os.getpid()}"
    command = ["xterm", "-title", title, "-bg", "white", "-fg", "black", "+sb",
               "-fa", "DejaVu Sans Mono", "-fs", "13", "-b", "12",
               "-geometry", f"{cols}x{rows}+10+10", "-e", sys.executable,
               str(Path(__file__).resolve()), "--terminal", name, str(tmp)]
    with subprocess.Popen(command, cwd=ROOT) as proc:
        try:
            deadline = time.monotonic() + 35
            while not (tmp / "ready").exists():
                if proc.poll() is not None or time.monotonic() >= deadline:
                    raise RuntimeError(f"xterm did not finish {name}")
                time.sleep(.05)
            # 只查找并读取此次创建的终端窗口。
            windows = [display.screen().root]
            while windows:
                window = windows.pop()
                if window.get_wm_name() == title:
                    break
                windows.extend(window.query_tree().children)
            else:
                raise RuntimeError(f"xterm not found: {title}")
            time.sleep(.2)
            g = window.get_geometry()
            pixels = window.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xffffffff)
            img = Image.frombytes("RGB", (g.width, g.height), pixels.data, "raw", "BGRX")
            img.save(ROOT / "screenshots" / (name + ".png"))
        finally:
            (tmp / "captured").touch()
            if proc.poll() is None:
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.terminate()


if __name__ == "__main__":
    if sys.argv[1:2] == ["--terminal"]:
        terminal(sys.argv[2], Path(sys.argv[3]))
    else:
        from Xlib.display import Display
        (ROOT / "logs").mkdir(exist_ok=True)
        (ROOT / "screenshots").mkdir(exist_ok=True)
        d = Display()
        try:
            for name, (cols, rows, _) in CASES.items():
                with tempfile.TemporaryDirectory(prefix="ex3-window-") as path:
                    capture(d, name, cols, rows, Path(path))
        finally:
            d.close()
