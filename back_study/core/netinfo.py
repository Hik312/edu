# -*- coding: utf-8 -*-
"""本机地址探测。后端（FastAPI 的 app/）用这一份，
免得「手机连不上」的排查经验要修两遍。

**为什么不能只靠 UDP 出口 IP。**
早先的做法是「`socket.connect(('8.8.8.8', 80))` 拿到出口 IP，排最前」—— 这在干净
机器上是准的，但装了代理软件（Clash 之类）开 TUN 模式、或者装了 VirtualBox / Hyper-V
之后就不成立了：默认路由会被虚拟网卡劫持，出口 IP 变成 `198.18.0.1`（代理的 fake-ip 段）
或 `192.168.56.1`（VirtualBox Host-Only）。按出口 IP 排最前，恰好会把最不可能连上的
那个排到第一位 —— 本机实测踩到过，所以现在改成**打分排序**：

- 出口 IP 小幅加分（它仍然是「内核实际会走的那张网卡」，有信息量）
- 真正的内网段（10/8、192.168/16、172.16/12）加分
- 已知的虚拟/特殊段（代理 fake-ip、Host-Only、link-local、CGNAT、Docker 网桥）重扣分

这样 `10.71.215.180` 这类真实校园网/家用网地址会稳定排在最前，虚拟网卡沉底但仍列出
—— 不删掉它们，因为万一有人就是要在虚拟网络里用。
"""
import ipaddress
import socket

# 加分：这些是「手机大概率连得上」的段
_BONUS = (
    ('10.0.0.0/8', 30),
    ('192.168.0.0/16', 20),
    ('172.16.0.0/12', 10),
)

# 扣分：这些段基本不可能是手机该连的那个
_PENALTY = (
    ('198.18.0.0/15', 100),     # 代理 TUN 的 fake-ip（Clash 默认就吃这段）
    ('192.168.56.0/24', 90),    # VirtualBox Host-Only
    ('169.254.0.0/16', 90),     # link-local，没拿到 DHCP 时的自配地址
    ('100.64.0.0/10', 80),      # CGNAT，Tailscale 之类也在这段
    ('172.17.0.0/16', 60),      # Docker 默认网桥
)


def _score(ip, outbound):
    try:
        a = ipaddress.ip_address(ip)
    except ValueError:
        return -999
    s = 50 if ip == outbound else 0
    for net, w in _BONUS:
        if a in ipaddress.ip_network(net):
            s += w
    for net, w in _PENALTY:
        if a in ipaddress.ip_network(net):
            s -= w
    return s


def lan_ips():
    """列出本机可能的局域网 IPv4，**最可能是「手机该访问的那个」排最前**。"""
    out, outbound = [], ''

    try:                              # 出口 IP：UDP 不真发包，只是让内核挑默认网卡
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            outbound = s.getsockname()[0]
        finally:
            s.close()
    except Exception:
        pass

    if outbound:
        out.append(outbound)

    try:                              # 再补上其它网卡（可能同时插了网线又开着 WiFi）
        for info in socket.getaddrinfo(socket.gethostname(), None, socket.AF_INET):
            ip = info[4][0]
            if ip not in out and not ip.startswith('127.'):
                out.append(ip)
    except Exception:
        pass

    # 稳定排序：同分的保持原始顺序（出口 IP 天然在最前）
    return sorted(out, key=lambda ip: -_score(ip, outbound))


def banner(port, lan):
    """手机访问那几行提示。格式要稳定：用户是照着这行 URL 手敲到手机浏览器里的。"""
    if not lan:
        return ['要让手机连进来请加 --lan（会绑到 0.0.0.0，注意网络安全）']
    ips = lan_ips()
    if not ips:
        return ['已绑到 0.0.0.0（手机同 WiFi 用本机局域网 IP 访问，注意网络安全）']
    lines = ['手机同 WiFi: http://%s:%d/' % (ip, port) for ip in ips]
    lines.append('           若连不上：确认同一 WiFi + 放行防火墙 %d 端口（第一个通常是对的）' % port)
    return lines
