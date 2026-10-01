#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""卷宗主题浏览器冒烟（Python 版，自包含）。

为什么不继续用 bash 版本：
  Git Bash 在这台机器上踩了三个互不相干的坑，叠在一起会给出**假信号**：
    1. `curl -o /dev/null` → 退出码 23（/dev/null 被 MSYS 转成非法 Windows 路径），
       请求其实成功、服务端回了 200，但探活判定成"服务没起来"。
    2. 中文路径下 `wc -c < file`、`grep file` 偶发 "No such file or directory"，
       日志明明写了却读不到，会让人误判成服务没启动。
    3. 后台进程与服务日志的时序在轮次边界上会被回收。
  Python 里 os.getcwd()/open()/subprocess 都是确定的，不会出这些鬼。

做的事：起 run.py（FastAPI）→ 探活 → 逐页抓图 → 收服务，全在一个进程树内。
用法：python back_study/scripts/smoke_paper.py [--pages login,dashboard,...]
"""
import argparse
import json
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))            # back_study/scripts
BACK = os.path.dirname(HERE)                                  # back_study
ROOT = os.path.dirname(BACK)                                  # study
OUT = os.path.join(BACK, "_shot")

CHROME_CANDIDATES = [
    r"C:\Users\wangh\AppData\Local\ms-playwright\chromium_headless_shell-1208\chrome-headless-shell-win64\chrome-headless-shell.exe",
]
PY_CANDIDATES = [
    os.path.join(BACK, ".venv", "Scripts", "python.exe"),
    r"C:\Users\wangh\.workbuddy\binaries\python\versions\3.13.12\python.exe",
]

# 页面清单：名字 → 访问路径。需要登录的走 _seed.html（它先写 localStorage 再跳）。
PAGES = {
    "login":     "/login",
    "dashboard": "/_seed.html?to=/dashboard",
    "cards":     "/_seed.html?to=/cards",
    "graph":     "/_seed.html?to=/graph",
    "review":    "/_seed.html?to=/review",
    "path":      "/_seed.html?to=/path",
    "docs":      "/_seed.html?to=/docs",
    "notes":     "/_seed.html?to=/notes",
    "generate":  "/_seed.html?to=/generate",
    "sys":       "/_seed.html?to=/admin/system",
    "users":     "/_seed.html?to=/admin/users",
}


def pick(paths):
    for p in paths:
        if os.path.exists(p):
            return p
    return None


class Server:
    """把 run.py（FastAPI 版）拉起来，退出时保证收干净。

    零依赖版 server.py 已于 2026-09-26 移除 —— 现在只有 FastAPI 这一条线，
    所以**必须**用装了 fastapi / uvicorn / PyJWT 的解释器（首选 back_study/.venv）。
    候选里那个托管 Python 没有这些包，只有 .venv 不存在时才会被选中，
    那种情况下服务起不来，报错是「进程已退出 rc=1」，别当成页面坏了。
    """

    def __init__(self, port, py):
        self.port = port
        self.py = py
        self.proc = None
        self.log_path = os.path.join(BACK, "_srv.log")
        self.log = None

    def __enter__(self):
        # 关键：日志走真实文件句柄，不要 PIPE。PIPE 不读会写满缓冲区，
        # 把服务卡死在一次 print 上，表现成"页面一直转圈"。
        self.log = open(self.log_path, "w", encoding="utf-8", errors="replace")
        self.proc = subprocess.Popen(
            [self.py, "run.py", str(self.port)],
            cwd=BACK, stdout=self.log, stderr=subprocess.STDOUT,
        )
        return self

    def wait_ready(self, timeout=25.0):
        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.proc.poll() is not None:
                return False, "进程已退出 rc=%s" % self.proc.returncode
            try:
                with socket.create_connection(("127.0.0.1", self.port), 0.4):
                    pass
            except OSError:
                time.sleep(0.3)
                continue
            code, _ = self.get("/api/health")
            if code == 200:
                return True, "ok"
            time.sleep(0.3)
        return False, "超时"

    def get(self, path, timeout=10):
        """裸 urllib 请求。显式清空代理——本机 TUN 代理会劫持 127.0.0.1。"""
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(url, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:                                # noqa: BLE001
            return None, str(e).encode()

    def post(self, path, payload, timeout=10):
        """POST JSON。返回 (状态码, 原始字节)。"""
        url = "http://127.0.0.1:%d%s" % (self.port, path)
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = urllib.request.Request(
            url, data=data, headers={"Content-Type": "application/json"}, method="POST"
        )
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        try:
            with opener.open(req, timeout=timeout) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()
        except Exception as e:                                # noqa: BLE001
            return None, str(e).encode()

    def __exit__(self, *exc):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            try:
                self.proc.wait(5)
            except subprocess.TimeoutExpired:
                pass
        if self.log:
            self.log.close()
        return False

    def tail(self, n=25):
        try:
            with open(self.log_path, encoding="utf-8", errors="replace") as f:
                return "".join(f.readlines()[-n:])
        except OSError as e:
            return "读日志失败: %s" % e


# 冒烟账号：跟 check.js 的契约测试用同一组。第一次跑会注册，之后就只是登录。
# 走真实登录接口而不是自己签 token —— 顺手把 auth 往返也验了一遍。
SEED_USER = "zz_check_probe"
SEED_PASS = "zz_check_123456"


def ensure_seed(srv):
    """生成 web/dist/_seed.html。返回是否成功。

    **为什么必须每次重新生成**：dist/ 是 vite 的构建产物目录，`vite build`
    会把它整个清空。手工放进去的种子页活不过一次构建 —— 表现为"上一轮还能
    截图，重新构建之后所有需要登录的页面都打不开"，最容易被误判成路由写坏了。

    **为什么需要种子页**：headless chrome 没有"执行页面脚本之前先往
    localStorage 里塞东西"的命令行能力（--user-data-dir 只带 cookie/profile）。
    所以借一个真实页面来写：它把 token 写进 localStorage 后立刻
    location.replace 到目标页，用户感知不到它存在。
    """
    dist = os.path.join(ROOT, "web", "dist")
    if not os.path.isdir(dist):
        print("!! web/dist 不存在，先跑 `npx vite build`")
        return False

    # 已注册会返回 409/400，无所谓，继续登录就好
    srv.post("/api/auth/register", {"username": SEED_USER, "password": SEED_PASS})
    code, body = srv.post("/api/auth/login", {"username": SEED_USER, "password": SEED_PASS})
    if code != 200:
        print("!! 登录失败 %s %s" % (code, body[:140]))
        return False
    try:
        token = json.loads(body).get("token") or ""
    except ValueError:
        print("!! 登录返回不是 JSON：%s" % body[:140])
        return False
    if not token:
        print("!! 登录成功但返回体里没有 token")
        return False

    html = (
        '<!DOCTYPE html><html lang="zh-CN"><head><meta charset="utf-8">'
        "<title>seed</title></head><body><script>\n"
        "/* 冒烟专用：写 token 再跳目标页，?to=/graph 控制去哪。 */\n"
        "var p = new URLSearchParams(location.search);\n"
        "localStorage.setItem('edupath.token', %s);\n"
        "location.replace(p.get('to') || '/dashboard');\n"
        "</script></body></html>\n"
    ) % json.dumps(token)
    with open(os.path.join(dist, "_seed.html"), "w", encoding="utf-8", newline="\n") as f:
        f.write(html)
    print("种子页  : dist/_seed.html（token %d 字符）" % len(token))
    return True


def shoot(chrome, port, name, path, png, budget_ms=9000, timeout=32.0):
    """抓一张图。chrome-headless-shell 写完 PNG 不退出，靠文件出现+稳定来收。

    ⚠️ 坑一：`--force-prefers-reduced-motion` 不能省。
    站内的入场动画是 `.rise { animation: rise .44s ... both }`，`both` 意味着
    **动画开始前元素就停在 opacity:0**。headless 的 virtual-time 只快进计时器、
    不推进 CSS 动画的合成帧，于是截图永远停在起始态 —— 侧栏菜单整片消失、
    卡片区只剩半透明的白块。看起来像"页面坏了"，其实是截图环境的假象。
    tokens.css 里对 prefers-reduced-motion 已做降级（duration/delay→0），
    这个参数把它打开，动画即刻落到终态，截出来的才是用户真看到的样子。

    ⚠️ 坑二：**每次必须给独立的 --user-data-dir**。
    这是最难查的一个：不指定时所有实例共用默认 profile。只要有一个
    chrome-headless-shell 还活在内存里（上一次 kill 没干净、或它在等你
    看不见的什么），新的 `--screenshot` 进程就会**把 URL 转交给老实例然后
    自己退出** —— 命令返回 0、没有报错、PNG 永远不会出现。
    现象是"截图这一步无声无息地什么都不做"，很容易被误判成页面打不开。
    独立 profile 目录后每个实例都是新的，转交行为消失。

    ⚠️ 坑三：等待循环必须用**绝对 deadline**。
    第一版写的是 `while time.time() - last < 25`，其中 `last` 在"文件还没
    出现"的分支里被刷新 —— 于是 PNG 一直不出现时 `time.time()-last` 恒等于
    一个 sleep 周期，条件永远成立，循环永不退出。实测卡了 7 分半，还得手动杀。
    超时判断只能跟"开始时刻"比，不能跟"上次变化时刻"比。
    """
    # 每张图一个全新 profile，用完不复用 —— 复用一个目录的话，上一轮
    # chrome 异常退出留下的 SingletonLock 会让下一轮卡在启动阶段
    profile = tempfile.mkdtemp(prefix="shot-%s-" % name)
    args = [
        chrome, "--disable-gpu", "--no-sandbox", "--hide-scrollbars",
        "--user-data-dir=%s" % profile,
        # 代理必须显式绕开：本机 TUN 开着时 chrome 会把 127.0.0.1 也送去代理，
        # 拿回来的是代理的 502 或直接连接被拒 —— 截出来是一张纯白图
        "--no-proxy-server", "--proxy-bypass-list=<-loopback>",
        "--force-prefers-reduced-motion",
        "--run-all-compositor-stages-before-draw",
        "--disable-new-content-rendering-timeout",
        "--force-device-scale-factor=1", "--window-size=1440,900",
        "--virtual-time-budget=%d" % budget_ms,
        "--screenshot=%s" % png,
        "http://127.0.0.1:%d%s" % (port, path),
    ]
    if os.path.exists(png):
        os.remove(png)
    errlog = os.path.join(OUT, "_chrome.log")
    with open(errlog, "ab") as err:
        err.write(("\n=== %s %s ===\n" % (name, path)).encode())
        err.flush()
        p = subprocess.Popen(args, stdout=subprocess.DEVNULL, stderr=err)
        deadline = time.time() + timeout
        size, stable = 0, 0
        while time.time() < deadline:
            time.sleep(0.4)
            cur = os.path.getsize(png) if os.path.exists(png) else 0
            if cur and cur == size:
                stable += 1
                if stable >= 2:        # 连续两次字节数不变 = 已写完
                    break
            else:
                size, stable = cur, 0
        if p.poll() is None:
            p.kill()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                pass
    shutil.rmtree(profile, ignore_errors=True)
    return os.path.getsize(png) if os.path.exists(png) else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8799)
    ap.add_argument("--pages", default="login,dashboard,cards,graph")
    args = ap.parse_args()

    chrome = pick(CHROME_CANDIDATES)
    py = pick(PY_CANDIDATES)
    if not chrome:
        print("!! 找不到 chrome-headless-shell")
        return 2
    if not py:
        print("!! 找不到可用的 python")
        return 2
    os.makedirs(OUT, exist_ok=True)

    print("chrome : %s" % chrome)
    print("python : %s" % py)

    with Server(args.port, py) as srv:
        ok, why = srv.wait_ready()
        print("服务    : %s (%s)" % ("就绪" if ok else "未就绪", why))
        if not ok:
            print(srv.tail())
            return 1

        # 种子页必须在自检**之前**生成 —— 自检清单里就有它。
        # 顺序反了的话，每一轮都会多出一条 `/_seed.html 404` 的假警报，
        # 而它其实只是"还没轮到生成"。
        print("\n-- 种子页 --")
        if not ensure_seed(srv):
            print("!! 种子页没建成 —— 下面需要登录的页面会全停在登录页")

        # 静态自检：登录页与首屏必须拿到真内容，空 body 会让截图全白
        print("\n-- 静态路径自检 --")
        for u in ["/login", "/", "/_seed.html?to=/dashboard",
                  "/assets/", "/nonexist.zip"]:
            code, body = srv.get(u)
            print("  %-34s %-5s %7dB" % (u, code, len(body) if body else 0))

        print("\n-- 抓图 --")
        wanted = [p.strip() for p in args.pages.split(",") if p.strip()]
        for name in wanted:
            path = PAGES.get(name)
            if not path:
                print("  %-12s (未知页面，跳过)" % name)
                continue
            png = os.path.join(OUT, "paper-%s.png" % name)
            n = shoot(chrome, args.port, name, path, png)
            print("  %-12s %-9s %s" % (name, "%dB" % n if n else "MISSING", png))

        print("\n-- 后端收到的请求 --")
        for line in srv.tail(20).splitlines():
            if "GET " in line or "POST " in line:
                print("  " + line.strip())
    return 0


if __name__ == "__main__":
    sys.exit(main())
