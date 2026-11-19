#!/usr/bin/env python3
"""逐次回放仓库操作，并从 Linux 内核核对信号量等待队列和资源回收。"""
from concurrent.futures import ThreadPoolExecutor
import ctypes
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
PC = ROOT / "build" / "pc"
IPC = re.compile(r"IPC: shm=(\d+) empty=(\d+) full=(\d+) mutex=(\d+)")
START = re.compile(r"([PC]) (\d+) started\.")
STATE = re.compile(r"  item=(\d+) stock=(\d+)/(\d+) in=(\d+) out=(\d+)")
END = re.compile(r"([PC]) (\d+) (put an item to|got an item from) (\d+)\.")
LIBC = ctypes.CDLL(None, use_errno=True)
GETVAL, GETNCNT = 12, 14  # Linux <sys/sem.h>


def ipc_ids(text):
    match = IPC.search(text)
    assert match, text
    return tuple(map(int, match.groups()))


def listed_ids(kind):
    lines = Path("/proc/sysvipc", kind).read_text().splitlines()
    return {int(line.split()[1]) for line in lines[1:]}


def released(ids):
    assert ids[0] not in listed_ids("shm"), ids
    assert set(ids[1:]).isdisjoint(listed_ids("sem")), ids


def replay(text, capacity, initial, pairs):
    """根据初始库存独立计算每一步的产品、位置、库存及读写游标。"""
    slots = list(range(1, initial + 1)) + [0] * (capacity - initial)
    stock, put, got = initial, 0, 0
    w, r = initial % capacity, 0
    started, finished = {}, set()
    assert f"Initial: capacity={capacity} stock={initial} in={w} out=0 pairs={pairs} " in text
    state = None
    for line in text.splitlines():
        if match := START.fullmatch(line):
            role, pid = match.groups()
            assert pid not in started, line
            started[pid] = role
        elif match := STATE.fullmatch(line):
            assert state is None, line
            state = tuple(map(int, match.groups()))
        elif match := END.fullmatch(line):
            role, pid, action, slot = match.groups()
            assert started.get(pid) == role and pid not in finished, line
            finished.add(pid)
            if role == "P":
                assert action == "put an item to" and int(slot) == w and slots[w] == 0, line
                put += 1
                item = initial + put
                slots[w] = item
                w = (w + 1) % capacity
                stock += 1
            else:
                assert action == "got an item from" and int(slot) == r and slots[r] != 0, line
                got += 1
                item = slots[r]
                assert item == got, (line, "FIFO")
                slots[r] = 0
                r = (r + 1) % capacity
                stock -= 1
            assert state == (item, stock, capacity, w, r), (line, state)
            state = None
    assert state is None and len(started) == len(finished) == 2 * pairs
    assert (put, got, stock) == (pairs, pairs, initial)
    assert f"Final: produced={put} consumed={got} stock={stock} in={w} out={r}" in text
    assert f"Semaphores: empty={capacity - stock} full={stock} mutex=1" in text
    ids = ipc_ids(text)
    released(ids)
    return ids


def simulate(capacity, initial, pairs=4, seed=None):
    args = [str(pairs), str(seed)] if seed is not None else []
    run = subprocess.run([PC, *args], input=f"{capacity}\n{initial}\n", text=True,
                         capture_output=True, check=True, timeout=10)
    return replay(run.stdout, capacity, initial, pairs)


def observe(initial, *, interrupt=None, verbose=False):
    """用空仓先到 C、满仓先到 P 的种子，读取正在等待的内核进程数。"""
    seed, role, name = (13, "C", "full") if initial == 0 else (11, "P", "empty")
    with subprocess.Popen([PC, "4", str(seed)], text=True, stdin=subprocess.PIPE,
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          start_new_session=True) as process:
        try:
            process.stdin.write(f"1\n{initial}\n")
            process.stdin.close()
            process.stdin = None
            prefix = []
            match = None
            for line in process.stdout:
                prefix.append(line)
                if match := START.fullmatch(line.rstrip()):
                    break
            assert match and match[1] == role, prefix
            pid = int(match[2])
            ids = ipc_ids("".join(prefix))
            sem = ids[2] if role == "C" else ids[1]
            assert ids[0] in listed_ids("shm") and set(ids[1:]) <= listed_ids("sem")
            deadline = time.monotonic() + 1
            while (waiting := LIBC.semctl(sem, 0, GETNCNT)) == 0 and time.monotonic() < deadline:
                time.sleep(.001)
            value = LIBC.semctl(sem, 0, GETVAL)
            assert waiting > 0 and value == 0, (name, waiting, value)
            if interrupt == "parent":
                process.send_signal(signal.SIGINT)
            elif interrupt == "child":
                os.kill(pid, signal.SIGKILL)
            rest, _ = process.communicate(timeout=6)
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
        text = "".join(prefix) + rest
        if interrupt:
            expected = 128 + signal.SIGINT if interrupt == "parent" else 1
            assert process.returncode == expected, text
            released(ids)
            return
        assert process.returncode == 0, text
        replay(text, 1, initial, 4)
        if not verbose:
            return
        print(f"capacity=1 stock={initial} pairs=4 seed={seed}")
        print(f"  {role} {pid} started.")
        print(f"  semctl({name}): GETVAL={value} GETNCNT={waiting}")
        ends = [line for line in text.splitlines() if END.fullmatch(line)]
        print("  " + ends[0])  # 唤醒等待者的反向操作
        print("  " + next(line for line in ends if line.startswith(f"{role} {pid} ")))
        print("  " + next(line for line in text.splitlines() if line.startswith("Final:")))


def invalid_input():
    cases = [([], "0\n"), ([], "1025\n"), ([], "a\n"), ([], "2\n-1\n"),
             ([], "2\n3\n"), ([], "2\n"), ([], "2\n1.5\n"), (["0"], ""),
             (["33"], ""), (["4", "-1"], ""), (["4", "x"], "")]
    for args, data in cases:
        run = subprocess.run([PC, *args], input=data, text=True, capture_output=True, timeout=3)
        assert run.returncode != 0 and run.stderr and "IPC:" not in run.stdout, (args, data)


def concurrent():
    with ThreadPoolExecutor(max_workers=2) as pool:
        a = pool.submit(simulate, 2, 0, 8, 1)
        b = pool.submit(simulate, 3, 3, 8, 2)
        first, second = a.result(), b.result()
    assert first[0] != second[0] and set(first[1:]).isdisjoint(second[1:])


if __name__ == "__main__":
    if sys.argv[1:] == ["--waits"]:
        observe(0, verbose=True)
        observe(1, verbose=True)
    elif sys.argv[1:]:
        sys.exit("Usage: verify.py [--waits]")
    else:
        checks = [
            ("interactive defaults", lambda: simulate(3, 1)),
            ("FIFO and wrapping at capacity 3", lambda: simulate(3, 1, 8, 7)),
            ("single slot and one pair", lambda: simulate(1, 1, 1, 0)),
            ("maximum capacity and 64 children", lambda: simulate(1024, 1023, 32, 19)),
            ("empty warehouse blocks a consumer", lambda: observe(0)),
            ("full warehouse blocks a producer", lambda: observe(1)),
            ("parallel warehouses use separate IPC objects", concurrent),
            ("invalid input and EOF", invalid_input),
            ("Ctrl-C reaps children and releases IPC", lambda: observe(0, interrupt="parent")),
            ("failed child releases blocked peers and IPC", lambda: observe(0, interrupt="child")),
        ]
        for title, check in checks:
            check()
            print("PASS  " + title)
        print(f"All {len(checks)} checks passed.")
