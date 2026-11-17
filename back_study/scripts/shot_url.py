# -*- coding: utf-8 -*-
"""对**已经在跑的**服务截图（dev server 或后端静态服务都行）。

和 smoke_paper.py 的分工：
  smoke_paper.py  自己起 run.py 打 dist 产物 —— 验的是「构建后的真样子」
  shot_url.py     打一个已存在的 base URL   —— 验的是「改一行 CSS 想看效果」

用法：
  python back_study/scripts/shot_url.py --base http://127.0.0.1:5173 --pages login
  python back_study/scripts/shot_url.py --pages login,docs --tag c1 --width 1440
  python back_study/scripts/shot_url.py --pages admin/system --height 1900

`别名=目标` 可以给一页起短名（默认名字就是目标）。非 login 的页面先过
/_seed.html 换 token 再跳。
"""
import argparse
import os
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
SHOT = os.path.join(ROOT, "back_study", "_shot")
# profile 放 _shot 下（而不是脚本旁边）：每页一个独立 profile，跑几次就几十个目录，
# 跟产物放一起方便一起清
PROF_ROOT = os.path.join(SHOT, "_prof")
CHROME = (r"C:/Users/wangh/AppData/Local/ms-playwright/"
          r"chromium_headless_shell-1208/chrome-headless-shell-win64/chrome-headless-shell.exe")


def shoot(url, png, profile, width, height, budget_ms, wait, hide_sb=True):
    os.makedirs(profile, exist_ok=True)
    args = [CHROME, "--disable-gpu", "--no-sandbox",
            "--user-data-dir=" + profile,
            # 本机 TUN 代理会劫持 127.0.0.1，必须显式绕开
            "--no-proxy-server", "--proxy-bypass-list=<-loopback>",
            # .rise 是 animation:...both，headless 不推进 CSS 动画，
            # 不加这个会截到 opacity:0 的起始态（菜单整片消失）
            "--force-prefers-reduced-motion",
            # ECharts 力导向靠 rAF 逐帧退火，不加这两个画布是空的
            "--run-all-compositor-stages-before-draw",
            "--disable-new-content-rendering-timeout",
            "--force-device-scale-factor=1",
            "--window-size=%d,%d" % (width, height),
            "--virtual-time-budget=%d" % budget_ms,
            "--screenshot=" + png, url]
    if hide_sb:
        args.insert(3, "--hide-scrollbars")
    old_mtime = os.path.getmtime(png) if os.path.exists(png) else 0
    p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    size, stable, last = 0, 0, time.time()
    while time.time() - last < wait:
        time.sleep(0.4)
        if not os.path.exists(png) or os.path.getmtime(png) <= old_mtime:
            continue
        cur = os.path.getsize(png)
        if cur and cur == size:
            stable += 1
            if stable >= 2:
                break
        else:
            size, stable, last = cur, 0, time.time()
    try:
        p.kill()
        p.wait(5)
    except Exception:                                          # noqa: BLE001
        pass
    return os.path.getsize(png) if os.path.exists(png) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="http://127.0.0.1:5173")
    ap.add_argument("--pages", default="login")
    ap.add_argument("--tag", default="now")
    ap.add_argument("--width", type=int, default=1440)
    ap.add_argument("--height", type=int, default=900)
    ap.add_argument("--budget", type=int, default=14000)
    ap.add_argument("--wait", type=float, default=30.0)
    ap.add_argument("--scrollbars", action="store_true")
    a = ap.parse_args()

    for spec in [x.strip() for x in a.pages.split(",") if x.strip()]:
        name, target = spec.split("=", 1) if "=" in spec else (spec, spec)
        # login 是免登录页；其余页要先过种子页换 token
        url = (a.base + "/login" if target == "login"
               else "%s/_seed.html?to=/%s" % (a.base, target))
        # 名字里的斜杠必须换掉：'admin/system' 直接拼进路径会变成
        # _shot/tag-admin/system.png —— 那个子目录不存在，chrome 写不进去，
        # 表现是"这几页永远 MISSING"，看着像页面坏了，其实是文件名。
        safe = name.replace("/", "_").replace("\\", "_")
        png = os.path.join(SHOT, "%s-%s.png" % (a.tag, safe))
        profile = os.path.join(PROF_ROOT, "%s-%s-%d" % (a.tag, safe, int(time.time())))
        n = shoot(url, png, profile, a.width, a.height, a.budget, a.wait,
                  hide_sb=not a.scrollbars)
        print("  %-12s %8dB  %s" % (name, n, os.path.basename(png) if n else "MISSING"))


if __name__ == "__main__":
    sys.exit(main())
