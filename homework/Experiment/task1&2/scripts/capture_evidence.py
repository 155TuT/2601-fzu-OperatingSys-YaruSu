#!/usr/bin/env python3
"""在真正的白底 xterm 中执行命令，并直接截取 X11 窗口。

需要 Xvfb、xterm、Pillow、python-xlib、nano；OS_LAB_TOOL_ROOT 可指向解包工具。
此脚本会在真实用户主目录创建实验文件，已存在同名文件时拒绝覆盖。
"""
from pathlib import Path
import getpass
import hashlib
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
import time

BASE = Path(__file__).resolve().parents[1]


def terminal_session(path):
    spec = json.loads(Path(path).read_text())
    os.chdir(spec["cwd"])
    log = []
    for item in spec["commands"]:
        if isinstance(item, dict):
            command = "nano " + shlex.quote(item["nano"])
            print("$ " + command, flush=True)
            Path(spec["signal"]).write_text("nano")
            result = subprocess.run(["nano", "-I", "-L", item["nano"]])
            log.append(f"$ {command}\n[nano exited {result.returncode}]\n")
        else:
            print("$ " + item, flush=True)
            result = subprocess.run(["bash", "-o", "pipefail", "-c", item],
                                    text=True, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT)
            print(result.stdout, end="", flush=True)
            log.append(f"$ {item}\n{result.stdout}[exit {result.returncode}]\n")
    Path(spec["log"]).write_text("".join(log))
    Path(spec["signal"]).write_text("done")
    # 窗口保留到截图完成；父进程随后终止这个终端进程组。
    while True:
        time.sleep(1)


def main():
    from PIL import Image
    from Xlib import X, XK, display
    from Xlib.ext import xtest

    home = Path.home()
    required = ["A", "bin", "sum.tar.gz", "restore-ex1", "sum.sh", "sum_named.sh",
                "list1.txt", "list2.txt", "list.txt", "sum.r", "error.log",
                "custom result.txt"]
    lists_only = "--lists-only" in sys.argv
    root_only = "--root-only" in sys.argv
    shell_only = "--shell-only" in sys.argv
    occupied = [] if lists_only or root_only or shell_only else [str(home / x) for x in required if (home / x).exists()]
    if occupied:
        raise SystemExit("Refusing to overwrite: " + ", ".join(occupied))
    tools = Path(os.environ.get("OS_LAB_TOOL_ROOT", "/"))
    xterm = str(tools / "usr/bin/xterm")
    xvfb = str(tools / "usr/bin/Xvfb")
    screen_dir = BASE / "screenshots"
    screen_dir.mkdir(exist_ok=True)
    logs = BASE / "logs"
    logs.mkdir(exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix="os-ex12-capture-"))
    server = subprocess.Popen([xvfb, ":91", "-screen", "0", "1600x1400x24",
                               "-nolisten", "tcp", "-ac"],
                              stdout=(tmp / "xvfb.log").open("w"),
                              stderr=subprocess.STDOUT)
    os.environ["DISPLAY"] = ":91"
    os.environ["TZ"] = "Asia/Shanghai"
    os.environ["LC_ALL"] = "C.UTF-8"
    time.sleep(0.6)
    d = display.Display(":91")

    def key(name, ctrl=False):
        symbol = XK.string_to_keysym(name)
        code = d.keysym_to_keycode(symbol)
        if ctrl:
            xtest.fake_input(d, X.KeyPress, d.keysym_to_keycode(XK.XK_Control_L))
        xtest.fake_input(d, X.KeyPress, code)
        xtest.fake_input(d, X.KeyRelease, code)
        if ctrl:
            xtest.fake_input(d, X.KeyRelease, d.keysym_to_keycode(XK.XK_Control_L))
        d.sync()

    def type_ascii(value):
        for char in value:
            keysym = ord(char)
            mapping = list(d.keysym_to_keycodes(keysym))
            if not mapping:
                raise ValueError(char)
            code, level = mapping[0]
            if level & 1:
                xtest.fake_input(d, X.KeyPress, d.keysym_to_keycode(XK.XK_Shift_L))
            xtest.fake_input(d, X.KeyPress, code)
            xtest.fake_input(d, X.KeyRelease, code)
            if level & 1:
                xtest.fake_input(d, X.KeyRelease, d.keysym_to_keycode(XK.XK_Shift_L))
        d.sync()

    def capture(name, commands, rows=32, cwd=home):
        signal = tmp / (name + ".signal")
        manifest = tmp / (name + ".json")
        manifest.write_text(json.dumps({"cwd": str(cwd), "commands": commands,
                                        "signal": str(signal),
                                        "log": str(logs / (name + ".log"))}))
        err = (tmp / (name + ".stderr")).open("w")
        process = subprocess.Popen([xterm, "-title", name, "-bg", "white", "-fg", "black",
                                    "-fa", "DejaVu Sans Mono", "-fs", "12",
                                    "-geometry", f"102x{rows}+0+0", "-b", "12", "-sb",
                                    "-e", sys.executable, str(Path(__file__).resolve()),
                                    "--terminal", str(manifest)], stderr=err,
                                   start_new_session=True)
        window = None
        for _ in range(100):
            for w in d.screen().root.query_tree().children:
                if w.get_wm_name() == name:
                    window = w
                    break
            if window is not None:
                break
            if process.poll() is not None:
                raise RuntimeError((tmp / (name + ".stderr")).read_text())
            time.sleep(0.1)
        if window is None:
            raise RuntimeError("xterm window not found")
        window.set_input_focus(X.RevertToParent, X.CurrentTime)
        d.sync()
        nano = next((x for x in commands if isinstance(x, dict)), None)
        if nano:
            while not signal.exists():
                time.sleep(0.1)
            time.sleep(0.4)
            # Ctrl+R 将源码读入 nano 新文件，再用 Ctrl+O 保存。
            if not nano.get("existing"):
                key("r", ctrl=True)
                time.sleep(0.2)
                type_ascii(nano["source"])
                key("Return")
                time.sleep(0.3)
            key("o", ctrl=True)
            time.sleep(0.2)
            key("Return")
            time.sleep(0.3)
            key("Home")
            # 移到文件第一行，以便截图显示代码开头。
            # Alt+\ 是 GNU nano 的“文件开头”。
            key("Escape")
            key("backslash")
            time.sleep(0.3)
        else:
            for _ in range(300):
                if signal.exists() and signal.read_text() == "done":
                    break
                time.sleep(0.1)
            else:
                raise RuntimeError(f"commands timed out: {name}")
        time.sleep(0.4)
        geometry = window.get_geometry()
        pixels = window.get_image(0, 0, geometry.width, geometry.height,
                                  X.ZPixmap, 0xFFFFFFFF)
        Image.frombytes("RGB", (geometry.width, geometry.height), pixels.data,
                        "raw", "BGRX").save(screen_dir / (name + ".png"))
        if nano:
            key("x", ctrl=True)
            for _ in range(50):
                if signal.read_text() == "done":
                    break
                time.sleep(0.1)
        os.killpg(process.pid, 15)
        process.wait(timeout=5)
        print("Captured", name, flush=True)

    try:
        if shell_only:
            capture("07-nano-shell", [{"nano": "sum.sh", "existing": True}], rows=58)
            return
        if root_only:
            capture("00-root-summary", ["pwd", "uname -m", "ls -x / | sed -n '1,8p'",
                    "ls -ld /bin /etc /home /dev /mnt"], rows=24)
            hashes = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(BASE)}"
                      for p in sorted(screen_dir.glob("*.png"))]
            (logs / "screenshots.sha256").write_text("\n".join(hashes) + "\n")
            return
        if lists_only:
            capture("06-pipes-and-lists", [
                "ls -l > list1.txt",
                "LC_ALL=C ls -lA --time-style=+%m-%d / | awk '$6 == \"04-16\"' > list2.txt",
                "cat list1.txt list2.txt > list.txt", "cat list1.txt", "cat list2.txt",
                "wc -l list1.txt list2.txt list.txt",
                "cmp list.txt <(cat list1.txt list2.txt) && echo 'Concatenation verified.'"], rows=34)
            dest = BASE / "evidence/home"
            for name in ["list1.txt", "list2.txt", "list.txt"]:
                shutil.copy2(home / name, dest / name)
            hashes = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(BASE)}"
                      for p in sorted(screen_dir.glob("*.png"))]
            (logs / "screenshots.sha256").write_text("\n".join(hashes) + "\n")
            return
        capture("01-root-and-directories", [
            "pwd", "uname -m", "ls -C /", "ls -ld /bin /etc /home /dev /mnt",
            "mkdir A bin", "ls -ld A bin"], rows=24)
        capture("02-nano-c", [{"nano": "A/sum.c", "source": str(BASE / "src/sum.c")}], rows=52)
        capture("03-source-c", ["cat A/sum.c"], rows=51)
        capture("04-build-archive-permissions", [
            "gcc -std=c11 -Wall -Wextra -Wpedantic -Werror -O2 A/sum.c -o A/sum",
            r"printf '10\n' | ./A/sum", "cp A/sum bin/",
            "tar -czvf sum.tar.gz -C A .", "chmod 755 sum.tar.gz",
            "stat -c '%A %a %n' sum.tar.gz", "rm -r -- A",
            "test ! -e A && echo 'A has been deleted.'",
            r"printf '10\n' | ./bin/sum"], rows=28)
        capture("05-extract-and-owner", [
            "mkdir restore-ex1", "tar -xzvf sum.tar.gz -C restore-ex1",
            "cmp restore-ex1/sum.c " + shlex.quote(str(BASE / "src/sum.c")) + " && echo 'Source matches.'",
            r"printf '10\n' | ./restore-ex1/sum",
            "stat -c '%U:%G %A %n' restore-ex1/sum.c",
            'chown "$(id -un):$(id -gn)" restore-ex1/sum.c',
            "stat -c '%U:%G %A %n' restore-ex1/sum.c", "lsblk -o NAME,TYPE,SIZE,MOUNTPOINTS | head -12"], rows=29)
        for name in ["sum.sh", "sum_named.sh"]:
            if name == "sum_named.sh":
                shutil.copy2(BASE / "src" / name, home / name)
        capture("06-pipes-and-lists", [
            "ls -l > list1.txt",
            "LC_ALL=C ls -lA --time-style=+%m-%d / | awk '$6 == \"04-16\"' > list2.txt",
            "cat list1.txt list2.txt > list.txt", "cat list1.txt", "cat list2.txt",
            "wc -l list1.txt list2.txt list.txt",
            "cmp list.txt <(cat list1.txt list2.txt) && echo 'Concatenation verified.'"], rows=28)
        capture("07-nano-shell", [{"nano": "sum.sh", "source": str(BASE / "src/sum.sh")}], rows=50)
        capture("08-shell-required-cases", [
            "chmod +x sum.sh sum_named.sh",
            r'''printf '%s\n' -1 | ./sum.sh; code=$?; printf 'exit status = %s\n' "$code"''',
            "cat error.log", "if [ -e sum.r ]; then cat sum.r; else echo 'sum.r does not exist.'; fi",
            r'''printf '10\n' | ./sum.sh; code=$?; printf 'exit status = %s\n' "$code"''',
            "cat sum.r", "cat error.log"], rows=25)
        capture("09-named-output", [
            r'''printf '10\ncustom result.txt\n' | ./sum_named.sh; code=$?; echo "exit status = $code"''',
            "cat 'custom result.txt'", "cat sum.r", "cat error.log"], rows=17)
        capture("10-make-dependencies", [
            "make clean", "make", "make", "make -q; code=$?; echo \"make -q status = $code\"",
            "make -n -W src/sum.c"], rows=24, cwd=BASE)
        capture("11-verification", ["tail -18 logs/verification.log"], rows=23, cwd=BASE)

        dest = BASE / "evidence/home"
        dest.mkdir(parents=True, exist_ok=True)
        for name in ["sum.tar.gz", "list1.txt", "list2.txt", "list.txt", "error.log", "sum.r", "custom result.txt"]:
            shutil.copy2(home / name, dest / name)
        check = {"real_home": str(home), "user": getpass.getuser(),
                 "A_deleted": not (home / "A").exists(),
                 "archive_mode": oct((home / "sum.tar.gz").stat().st_mode & 0o777),
                 "nano_c_matches_source": (home / "restore-ex1/sum.c").read_bytes() == (BASE / "src/sum.c").read_bytes(),
                 "nano_shell_matches_source": (home / "sum.sh").read_bytes() == (BASE / "src/sum.sh").read_bytes()}
        (BASE / "logs/evidence-checks.json").write_text(json.dumps(check, indent=2))
        print(json.dumps(check, indent=2))
        hashes = [f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(BASE)}"
                  for p in sorted(screen_dir.glob("*.png"))]
        (BASE / "logs/screenshots.sha256").write_text("\n".join(hashes) + "\n")
    finally:
        d.close()
        server.terminate()
        server.wait(timeout=5)


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--terminal":
        terminal_session(sys.argv[2])
    else:
        main()
