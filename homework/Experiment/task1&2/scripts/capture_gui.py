#!/usr/bin/env python3
"""打开并截取本实验实际使用的图形工具；不执行软件安装或更新。"""
from pathlib import Path
import os
import subprocess
import time

from PIL import Image
from Xlib import X, XK, display
from Xlib.ext import xtest

BASE = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ.get("OS_LAB_TOOL_ROOT", "/"))
TMP = Path("/tmp/oslab-gui")
TMP.mkdir(exist_ok=True)
os.environ.update(DISPLAY=":92", LC_ALL="C.UTF-8", TZ="Asia/Shanghai",
                  NETSURFRES=str(ROOT / "usr/share/netsurf"),
                  XDG_DATA_DIRS=str(ROOT / "usr/share") + ":/usr/share",
                  GSETTINGS_BACKEND="memory", GDK_BACKEND="x11")
os.environ.pop("WAYLAND_DISPLAY", None)
os.environ.pop("SAL_USE_VCLPLUGIN", None)
server = subprocess.Popen([str(ROOT / "usr/bin/Xvfb"), ":92", "-screen", "0",
                           "1600x1200x24", "-nolisten", "tcp", "-ac"],
                          stdout=(TMP / "xvfb.log").open("w"), stderr=subprocess.STDOUT)
time.sleep(0.7)
d = display.Display(":92")
processes = []


def launch(command, label):
    log = (TMP / (label + ".log")).open("w")
    p = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT)
    processes.append(p)
    time.sleep(1.8)


def title(w):
    text = w.get_wm_name()
    if text:
        return text
    prop = w.get_full_property(d.intern_atom("_NET_WM_NAME"), X.AnyPropertyType)
    if prop is not None and len(prop.value) > 0:
        return prop.value.decode("utf-8", errors="replace")
    classes = w.get_wm_class()
    return " ".join(classes) if classes else f"window-{w.id}"


def windows():
    result = []
    for w in d.screen().root.query_tree().children:
        try:
            if w.get_attributes().map_state == X.IsViewable and title(w):
                result.append(w)
        except Exception:
            pass
    return result


try:
    notes = TMP / "notes.html"
    notes.write_text('''<!DOCTYPE html><meta charset="utf-8"><title>OS Experiments 1 and 2</title>
    <h1>OS Experiments 1 and 2</h1><h2>Linux basic operations</h2>
    <p>Compiled sum.c, copied the executable, archived files and checked permissions.</p>
    <h2>Shell scripts</h2><p>Input -1: exit 5 and append error.log.</p>
    <p>Input 10: sum.r contains 55 and exit status is 0.</p>
    <p>This local page is opened in NetSurf for the graphical-tools practice.</p>''')
    launch([str(ROOT / "usr/bin/thunar"), str(Path.home() / "restore-ex1")], "thunar")
    launch([str(ROOT / "usr/bin/netsurf-gtk"), notes.as_uri()], "browser")
    launch([str(ROOT / "usr/lib/libreoffice/program/soffice"),
            "-env:UserInstallation=file:///tmp/oslab-tools/gui-lo-profile", "--norestore",
            str(BASE.parent / "task-requirement/计算机操作系统实验要求.docx")], "writer")
    launch([str(ROOT / "usr/sbin/synaptic"), "--display=:92"], "synaptic")
    time.sleep(2)
    print([(w.id, title(w)) for w in windows()], flush=True)
    # 先关闭只读模式提示；这不发起软件包操作。
    for _ in range(3):
        for w in windows():
            name = title(w)
            g = w.get_geometry()
            if (name in ["Warning", "Information"] or "Tip of the Day" in name
                    or "Quick Introduction" in name
                    or ("synaptic" in name.lower() and g.width < 900 and g.height < 300)):
                w.set_input_focus(X.RevertToParent, X.CurrentTime)
                code = d.keysym_to_keycode(XK.XK_Return)
                xtest.fake_input(d, X.KeyPress, code)
                xtest.fake_input(d, X.KeyRelease, code)
                d.sync()
                time.sleep(0.5)
    time.sleep(8)
    time.sleep(15)
    for w in windows():
        if "Quick Introduction" in title(w):
            w.set_input_focus(X.RevertToParent, X.CurrentTime)
            code = d.keysym_to_keycode(XK.XK_Return)
            xtest.fake_input(d, X.KeyPress, code)
            xtest.fake_input(d, X.KeyRelease, code)
            d.sync()
            time.sleep(0.6)
    print("Process status:", [(p.args[0], p.poll()) for p in processes], flush=True)
    for w in windows():
        g = w.get_geometry()
        if "synaptic" in title(w).lower() and g.width < 700 and g.height < 400:
            data = w.get_image(0, 0, g.width, g.height, X.ZPixmap, 0xFFFFFFFF)
            Image.frombytes("RGB", (g.width, g.height), data.data, "raw", "BGRX").save(TMP / "package-dialog.png")
    placement = [("restore-ex1", 0, 0), ("NetSurf", 800, 0),
                 ("libreoffice", 0, 600), ("synaptic", 800, 600)]
    for token, x, y in placement:
        for w in sorted(windows(), key=lambda x: x.get_geometry().width * x.get_geometry().height, reverse=True):
            if token.lower() in title(w).lower():
                w.configure(x=x, y=y, width=800, height=600)
                w.configure(stack_mode=X.Above)
                d.sync()
                break
    time.sleep(1.5)
    print([(w.id, title(w), w.get_geometry().width,
            w.get_geometry().height) for w in windows()], flush=True)
    image = d.screen().root.get_image(0, 0, 1600, 1200, X.ZPixmap, 0xFFFFFFFF)
    Image.frombytes("RGB", (1600, 1200), image.data, "raw", "BGRX").save(
        BASE / "screenshots/12-graphical-tools.png")
    (BASE / "logs/graphical-tools.log").write_text("\n".join(
        f"{title(w)} ({w.get_geometry().width}x{w.get_geometry().height})"
        for w in windows()) + "\n")
finally:
    for process in processes:
        if process.poll() is None:
            process.terminate()
    d.close()
    server.terminate()
    server.wait(timeout=5)
