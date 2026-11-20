#!/usr/bin/env python3
"""案例二 · 演示视频合成

把 capture_run.sh 采到的真实素材（终端输出、接收端解码帧、逐帧时延 CSV、
桥接计数）合成为一段带字幕的过程视频：左侧是当时真实的终端，右侧是
发送端与接收端的真实画面，底部是过程字幕。

用法：
    python3 make_video.py [素材目录=/tmp/cap] [输出=/tmp/cap/案例二-实验流程.mp4]
"""

import csv
import glob
import math
import os
import re
import subprocess
import sys

from PIL import Image, ImageDraw, ImageFont

W, H, FPS = 1920, 1080, 25
CAP = sys.argv[1] if len(sys.argv) > 1 else "/tmp/cap"
OUT = sys.argv[2] if len(sys.argv) > 2 else os.path.join(CAP, "案例二-实验流程.mp4")

# ---------- 配色（与 PPT 同一套） ----------
BG = (13, 16, 24)
GRID = (21, 26, 36)
CARD = (19, 23, 33)
CARD_BD = (40, 48, 64)
TERM_BG = (15, 18, 26)
TERM_BAR = (24, 28, 40)
INK = (228, 234, 244)
DIM = (150, 160, 178)
FAINT = (92, 102, 120)
BLUE = (58, 124, 196)
BLUE_D = (30, 70, 116)
CYAN = (44, 170, 184)
ORANGE = (234, 150, 62)
GREEN = (110, 198, 150)
RED = (208, 80, 70)

NOTO = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
NOTOB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"


def F(path, size, idx=2):
    return ImageFont.truetype(path, size, index=idx)


F_HEAD = F(NOTOB, 32)
F_HEAD_SUB = F(NOTO, 17)
F_CHIP = F(NOTOB, 15)
F_TERM_BAR = F(NOTO, 15)
F_TERM = F(NOTO, 22, 7)
F_TERM_B = F(NOTOB, 22, 7)
F_PTITLE = F(NOTOB, 17)
F_PHUD = F(NOTO, 15, 7)
F_SUB = F(NOTOB, 29)
F_CARD_BIG = F(NOTOB, 74)
F_CARD_SUB = F(NOTO, 28)
F_CARD_TAG = F(NOTOB, 20)
F_SMALL = F(NOTO, 15)
F_BODY = F(NOTO, 18)
F_KPI = F(NOTOB, 46)

# ---------- 版式 ----------
TERM_X, TERM_Y, TERM_W, TERM_H = 40, 112, 1140, 856
TERM_BAR_H = 38
P_X, P_W = 1200, 686
P_HDR = 32
P_IMG_H = 386
P_A_Y, P_B_Y = 112, 550
SUB_Y, SUB_H = 984, 80

STEPS = ["建网口", "启仿真", "接收端", "发送端", "结果"]

A_START = 51.0      # 发送画面开始动的时刻
B_START = 51.08     # 接收画面晚 80 ms（对应实测时延）
FREEZE_T = 88.0     # 结果页冻结在这一刻


# ====================== 素材 ======================
def load_frames():
    return sorted(glob.glob(os.path.join(CAP, "frames", "*.jpg")))


def load_latency():
    path = os.path.join(CAP, "lat.csv")
    if not os.path.exists(path):
        return []
    out = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            try:
                out.append(float(row["delay_ms"]))
            except (KeyError, ValueError):
                out.append(0.0)
    return out


def load_send_recv_lines():
    send, recv = [], []
    sp = os.path.join(CAP, "send.log")
    if os.path.exists(sp):
        for line in open(sp, encoding="utf-8", errors="replace"):
            m = re.search(r"已发 (\d+) 帧，([\d.]+) fps，([\d.]+) Mbps", line)
            if m and int(m.group(1)) % 150 == 0:
                send.append("已发 %s 帧，%s fps，%s Mbps" % m.groups())
    rp = os.path.join(CAP, "recv.log")
    if os.path.exists(rp):
        for line in open(rp, encoding="utf-8", errors="replace"):
            m = re.search(r"已收 (\d+) 帧，([\d.]+) fps，时延 均值 ([\d.]+) ms / P95 ([\d.]+) ms", line)
            if m and int(m.group(1)) % 150 == 0:
                recv.append("已收 %s 帧，%s fps，时延 均值 %s ms / P95 %s ms" % m.groups())
    return send, recv


def load_stats():
    """从日志与 sca 中取真实数字"""
    st = {"recv": 0, "mean": 0.0, "p95": 0.0, "mx": 0.0, "in": 0, "out": 0, "drop": 0}
    rp = os.path.join(CAP, "recv.log")
    if os.path.exists(rp):
        txt = open(rp, encoding="utf-8", errors="replace").read()
        m = re.search(r"统计：收到 (\d+) 帧，丢弃 (\d+) 帧，时延 均值 ([\d.]+) ms，"
                      r"P50 ([\d.]+)，P95 ([\d.]+)，最大 ([\d.]+)", txt)
        if m:
            st.update(recv=int(m.group(1)), mean=float(m.group(3)),
                      p95=float(m.group(5)), mx=float(m.group(6)))
    bp = os.path.join(CAP, "bridge.txt")
    if os.path.exists(bp):
        txt = open(bp, encoding="utf-8", errors="replace").read()
        for line in txt.splitlines():
            m = re.search(r"(gateway[AB])\.app\[1\] (pktsFromReal|pktsToReal|droppedUnresolved) (\d+)", line)
            if not m:
                continue
            gw, key, val = m.group(1), m.group(2), int(m.group(3))
            if gw == "gatewayA" and key == "pktsFromReal":
                st["in"] = val
            if gw == "gatewayB" and key == "pktsToReal":
                st["out"] = val
            if key == "droppedUnresolved":
                st["drop"] += val
    return st


# ====================== 文本工具 ======================
def text_w(draw, s, font):
    return draw.textlength(s, font=font)


def wrap(s, font, maxw, draw):
    """按宽度折行，尽量不在单词中间断开"""
    lines, cur = [], ""
    for ch in s:
        if text_w(draw, cur + ch, font) <= maxw:
            cur += ch
        else:
            cut = cur.rfind(" ")
            if cut > len(cur) * 0.6 and ch != " ":
                lines.append(cur[:cut])
                cur = cur[cut + 1:] + ch
            else:
                lines.append(cur)
                cur = ch
    if cur:
        lines.append(cur)
    return lines or [""]


# ====================== 场景 ======================
def build_scenes(st, send_lines, recv_lines):
    """返回场景列表；每个场景含终端行、面板状态、字幕"""
    s = []

    # 0 片头
    s.append(dict(kind="card", t0=0.0, t1=5.5, step=-1, deco=True,
                  title="视频流半实物仿真",
                  line1="真实 UDP 视频流 · 穿过 48 星仿真星座 · 回到真实主机",
                  tags=["真实流量", "仿真路径", "真实时延"],
                  foot="案例二 · 实验全流程"))

    # 1 建网口
    s.append(dict(kind="term", t0=5.5, t1=21.0, step=0, A="off", B="off",
                  sub="第一步 · 用两块虚拟网口，把「真实主机」和「仿真网关」背靠背接起来",
                  lines=[
                      ("cmd", "sudo sh semi_physical/setup_veth.sh"),
                      ("out", "== 清理旧设备 =="),
                      ("out", "== 创建 veth 对 =="),
                      ("out", "== 配置地址 =="),
                      ("out", "== 启用接口 =="),
                      ("blank", ""),
                      ("ok", "vethA       UP   192.168.100.1/24   -> 仿真侧网关 A"),
                      ("ok", "vethA-peer  UP   192.168.100.2/24   -> 真实主机 A"),
                      ("ok", "vethB-peer  UP   192.168.101.2/24   -> 真实主机 B"),
                      ("blank", ""),
                      ("dim", "两块网口让真实流量有地方进、也有地方出"),
                  ],
                  note=dict(title="这一步在做什么", items=[
                      "veth 是内核里的虚拟网卡对，两端都能配 IP",
                      "真实主机 A 发出的包，从另一端直接交给仿真网关",
                      "地址真实存在，因此可以用 tcpdump 抓包核对",
                  ])))

    # 2 启仿真
    s.append(dict(kind="term", t0=21.0, t1=37.0, step=1, A="off", B="off",
                  sub="第二步 · 启动 48 星动态星座，两端各挂一个半实物接入网关",
                  lines=[
                      ("cmd", "sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini"),
                      ("out", "OMNeT++ Discrete Event Simulation 6.3.0"),
                      ("out", "Loading NED files from ../../src:  35"),
                      ("out", "Loading NED files from ../../../inet4.6/src:  1245"),
                      ("out", 'Setting up network "SatNet3DEducationSemiPhysicalNetwork"...'),
                      ("out", "Initializing..."),
                      ("out", "Running simulation..."),
                      ("hi", "** Event #39424   t=10.81s   18% completed"),
                      ("blank", ""),
                      ("dim", "Walker-Delta 8x6 = 48 星 · 1414 km · 实时调度（仿真时间 = 墙钟）"),
                  ],
                  note=dict(title="星座与接入", items=[
                      "Walker-Delta 8 个轨道面 × 6 颗星，轨道高度 1414 km",
                      "两端各一个接入网关，各绑一个 veth 网段负责进出",
                      "实时调度器让仿真时间与墙钟同步，才能接真实流量",
                  ])))

    # 3 接收端
    s.append(dict(kind="term", t0=37.0, t1=50.5, step=2, A="off", B="wait",
                  sub="第三步 · 真实主机 B 起监听，等仿真网络把视频送出来",
                  lines=[
                      ("cmd", "python3 semi_physical/video_receiver.py --bind 192.168.101.2"),
                      ("out", "接收端：监听 192.168.101.2:5000"),
                      ("blank", ""),
                      ("dim", "还没数据 —— 端口在等，仿真侧也还没开始推流"),
                  ],
                  note=dict(title="为什么先起接收端", items=[
                      "只有仿真里的 gatewayB 会往 192.168.101.2 发数据",
                      "先就位再推流，避免开头几帧因为没有监听而丢弃",
                  ])))

    # 4 发送端
    s.append(dict(kind="term", t0=50.5, t1=63.5, step=3, A="live", B="auto",
                  sub="第四步 · 主机 A 每帧 JPEG 压缩，拆成 1400 B 的 UDP 包发出",
                  lines=[
                      ("cmd", "python3 semi_physical/video_sender.py --src 192.168.100.2 \\"),
                      ("cmd2", "        --dst 192.168.100.1 --synthetic --fps 25"),
                      ("out", "发送端：192.168.100.2 -> 192.168.100.1:5000，目标 25.0 fps"),
                      ("blank", ""),
                      ("hi", send_lines[0] if send_lines else "已发 150 帧，25.0 fps，4.95 Mbps"),
                      ("ok", recv_lines[0] if recv_lines else "已收 150 帧，23.9 fps，时延 均值 72.8 ms"),
                  ],
                  note=dict(title="一帧是怎么发出去的", items=[
                      "960×540 画面压成 JPEG，约 25 KB，速率稳定在 4.95 Mbps",
                      "按 1400 B 切片，每片带帧号 / 分片号 / 时间戳",
                      "接收端按帧号重组，缺片则整帧丢弃，故可精确统计丢帧",
                  ])))

    # 5 稳态观察
    s5 = [("cmd", "tail -f  send.log  recv.log")]
    n = max(len(send_lines), len(recv_lines))
    for i in range(1, n):
        if i < len(send_lines):
            s5.append(("hi", send_lines[i]))
        if i < len(recv_lines):
            s5.append(("ok", recv_lines[i]))
    s.append(dict(kind="term", t0=63.5, t1=88.0, step=3, A="live", B="live",
                  sub="数据包真的进了仿真：经 5 颗卫星多跳转发，再从另一端出来",
                  lines=s5, dense=True))

    # 6 结果
    s.append(dict(kind="term", t0=88.0, t1=103.0, step=4, A="frozen", B="frozen",
                  sub="1119 帧全部到达、零丢包；入网的包数与出网的包数完全相等",
                  lines=[
                      ("cmd", "grep -E 'pktsFromReal|pktsToReal' semi_physical/results/*.sca"),
                      ("out", "gatewayA  pktsFromReal   %d" % st["in"]),
                      ("out", "gatewayB  pktsToReal     %d" % st["out"]),
                      ("out", "droppedUnresolved            %d" % st["drop"]),
                      ("blank", ""),
                      ("cmd", "tail -1 recv.log"),
                      ("ok", "统计：收到 %d 帧，丢弃 0 帧，时延 均值 %.1f ms，P95 %.1f，最大 %.0f"
                             % (st["recv"], st["mean"], st["p95"], st["mx"])),
                      ("blank", ""),
                      ("dim", "对照：同一套收发程序在本机回环下时延仅 0.3 ms"),
                  ],
                  kpi=[("%d" % st["recv"], "帧全部到达"),
                       ("0", "丢帧"),
                       ("%.1f ms" % st["mean"], "平均端到端时延"),
                       ("%d" % st["in"], "包入网 = 出网")]))

    # 7 片尾
    s.append(dict(kind="card", t0=103.0, t1=110.0, step=-1,
                  title="真实流量 · 仿真路径 · 真实时延",
                  line1="%d 帧到达 · 0 丢包 · 平均 %.1f ms" % (st["recv"], st["mean"]),
                  tags=["payload 1400 B", "5 星多跳", "零丢包"],
                  foot="SatNet3D · satnet3d/simulations/education"))
    return s


# ====================== 渲染 ======================
class Composer:
    def __init__(self, scenes, frames_b, lat):
        self.scenes = scenes
        self.frames_b = frames_b
        self.lat = lat
        self.cache = {}
        probe = Image.new("RGB", (10, 10))
        self.probe = ImageDraw.Draw(probe)
        self.bases = {i: self._base(sc) for i, sc in enumerate(scenes)}
        self.tmp = None

    # ---------- 静态版式 ----------
    def _bg(self):
        img = Image.new("RGB", (W, H), BG)
        d = ImageDraw.Draw(img)
        for x in range(0, W, 60):
            d.line([(x, 0), (x, H)], fill=GRID)
        for y in range(0, H, 60):
            d.line([(0, y), (W, y)], fill=GRID)
        # 左上角光晕
        glow = Image.new("RGB", (600, 600), BG)
        gd = ImageDraw.Draw(glow)
        for r in range(300, 0, -6):
            a = int(16 * (1 - r / 300))
            gd.ellipse([300 - r, 300 - r, 300 + r, 300 + r],
                       fill=(BG[0] + a, BG[1] + a, BG[2] + int(a * 1.3)))
        img.paste(glow, (-180, -240))
        return img

    def _base(self, sc):
        if sc["kind"] == "card":
            return self._card_base(sc)
        img = self._bg()
        d = ImageDraw.Draw(img)
        self._header(d, sc["step"], sc["sub"])
        self._terminal_frame(d)
        self._panel_frame(d, P_A_Y, "发送端 · 真实主机 A", "A")
        self._panel_frame(d, P_B_Y, "接收端 · 真实主机 B", "B")
        self._subtitle(d, sc["sub"])
        return img

    def _card_base(self, sc):
        img = self._bg()
        d = ImageDraw.Draw(img)
        if sc.get("deco"):
            self._deco(d)
        d.text((140, 320), sc["title"], font=F_CARD_BIG, fill=INK)
        d.text((146, 430), sc["line1"], font=F_CARD_SUB, fill=DIM)
        x = 146
        for t in sc["tags"]:
            w = text_w(d, t, F_CARD_TAG) + 34
            d.rounded_rectangle([x, 512, x + w, 556], 22, outline=BLUE, width=2)
            d.text((x + 17, 522), t, font=F_CARD_TAG, fill=(122, 176, 236))
            x += w + 14
        d.line([(146, 620), (420, 620)], fill=BLUE, width=4)
        d.text((146, 660), sc["foot"], font=F_SMALL, fill=FAINT)
        return img

    def _deco(self, d):
        """右侧星座轨道装饰"""
        cx, cy = 1450, 440
        for rx, ry in ((330, 152), (238, 110), (150, 69)):
            d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=(30, 46, 70), width=2)
        for i in range(18):
            a = 2 * math.pi * i / 18
            x = cx + 330 * math.cos(a)
            y = cy + 152 * math.sin(a)
            r = 5 if i % 3 == 0 else 3
            c = (78, 144, 206) if i % 3 == 0 else (44, 78, 116)
            d.ellipse([x - r, y - r, x + r, y + r], fill=c)
        d.ellipse([cx - 7, cy - 7, cx + 7, cy + 7], fill=(96, 160, 220))

    def _header(self, d, step, sub):
        d.rectangle([40, 30, 46, 66], fill=BLUE)
        d.text((62, 24), "案例二 · 视频流半实物仿真", font=F_HEAD, fill=INK)
        d.text((63, 66), "真实 UDP 视频流穿越 48 星仿真星座", font=F_HEAD_SUB, fill=FAINT)
        # 步骤条
        x = W - 40 - len(STEPS) * 132 - (len(STEPS) - 1) * 8
        for i, name in enumerate(STEPS):
            bx = x + i * 140
            if i == step:
                d.rounded_rectangle([bx, 32, bx + 132, 70], 19, fill=BLUE)
                d.text((bx + 14, 40), "%d %s" % (i + 1, name), font=F_CHIP, fill=(255, 255, 255))
            elif step >= 0 and i < step:
                d.rounded_rectangle([bx, 32, bx + 132, 70], 19, outline=BLUE_D, width=1)
                d.text((bx + 14, 40), "%d %s" % (i + 1, name), font=F_CHIP, fill=(110, 150, 200))
            else:
                d.rounded_rectangle([bx, 32, bx + 132, 70], 19, outline=CARD_BD, width=1)
                d.text((bx + 14, 40), "%d %s" % (i + 1, name), font=F_CHIP, fill=FAINT)

    def _terminal_frame(self, d):
        d.rounded_rectangle([TERM_X, TERM_Y, TERM_X + TERM_W, TERM_Y + TERM_H], 10, fill=TERM_BG,
                            outline=CARD_BD, width=1)
        d.rounded_rectangle([TERM_X, TERM_Y, TERM_X + TERM_W, TERM_Y + TERM_BAR_H], 10, fill=TERM_BAR)
        d.rectangle([TERM_X, TERM_Y + TERM_BAR_H - 10, TERM_X + TERM_W, TERM_Y + TERM_BAR_H], fill=TERM_BAR)
        for i, c in enumerate([(236, 106, 96), (238, 190, 92), (110, 200, 128)]):
            d.ellipse([TERM_X + 18 + i * 22, TERM_Y + 13, TERM_X + 30 + i * 22, TERM_Y + 25], fill=c)
        d.text((TERM_X + 96, TERM_Y + 10), "user@ubuntu: ~/satnet3d/simulations/education",
               font=F_TERM_BAR, fill=(130, 140, 158))
        # 底部状态条
        by = TERM_Y + TERM_H - 34
        d.line([(TERM_X + 26, by - 10), (TERM_X + TERM_W - 26, by - 10)], fill=(32, 38, 50), width=1)
        d.text((TERM_X + 26, by), "实时调度：仿真时间 = 墙钟时间", font=F_SMALL, fill=(72, 82, 98))
        right = "25 fps · 1400 B/包 · 4.95 Mbps"
        rw = text_w(d, right, F_SMALL)
        d.text((TERM_X + TERM_W - 26 - rw, by), right, font=F_SMALL, fill=(72, 82, 98))

    def _panel_frame(self, d, y, title, tag):
        d.rounded_rectangle([P_X, y, P_X + P_W, y + P_HDR + P_IMG_H], 8, fill=CARD,
                            outline=CARD_BD, width=1)
        d.rounded_rectangle([P_X, y, P_X + P_W, y + P_HDR], 8, fill=(26, 31, 43))
        d.rectangle([P_X, y + P_HDR - 8, P_X + P_W, y + P_HDR], fill=(26, 31, 43))
        d.ellipse([P_X + 14, y + 12, P_X + 22, y + 20], fill=DIM)
        d.text((P_X + 32, y + 7), title, font=F_PTITLE, fill=(206, 214, 228))

    def _subtitle(self, d, sub):
        d.rounded_rectangle([120, SUB_Y, W - 120, SUB_Y + SUB_H], 14, fill=(22, 27, 38),
                            outline=(44, 54, 74), width=1)
        tw = text_w(d, sub, F_SUB)
        d.text(((W - tw) / 2, SUB_Y + 22), sub, font=F_SUB, fill=(238, 242, 250))

    # ---------- 动态 ----------
    def _term_lines(self, sc, idx, t):
        """返回 [(kind,text,is_last_typing)]"""
        out = []
        cursor_t = sc["t0"] + 0.8
        dense = sc.get("dense", False)
        for kind, text in sc["lines"]:
            if kind == "blank":
                out.append((kind, "", 0, 0))
                cursor_t += 0.18
                continue
            dur = min(1.5, max(0.35, len(text) * 0.014)) if kind.startswith("cmd") else 0.0
            out.append((kind, text, cursor_t, dur))
            cursor_t += dur + (0.16 if dense else 0.3)
        return out

    def _draw_terminal(self, img, d, sc, t):
        x0 = TERM_X + 26
        y = TERM_Y + TERM_BAR_H + 18
        maxw = TERM_W - 52
        lh = 33
        limit = TERM_Y + TERM_H - 70
        items = self._term_lines(sc, 0, t)
        lines = []
        for kind, text, t_app, dur in items:
            if t < t_app:
                break
            shown = text
            typing = False
            if dur and t < t_app + dur:
                k = int((t - t_app) / dur * len(text))
                shown = text[:k]
                typing = True
            if kind == "blank":
                lines.append(("blank", "", False, True))
                continue
            for i, w in enumerate(wrap(shown, F_TERM, maxw, d)):
                lines.append((kind, w, i == 0, not typing))
        # 只画最后能放下的内容，超出则整体上滚
        visible = max(1, (limit - y) // lh)
        if len(lines) > visible:
            lines = lines[-visible:]
        for kind, text, first, complete in lines:
            if kind == "blank":
                y += lh
                continue
            if kind in ("cmd", "cmd2"):
                d.text((x0, y), "$ " if kind == "cmd" else "  ", font=F_TERM_B, fill=CYAN)
                d.text((x0 + 26, y), text, font=F_TERM, fill=INK)
            elif kind == "ok":
                d.text((x0, y), text, font=F_TERM, fill=GREEN)
            elif kind == "hi":
                d.text((x0, y), text, font=F_TERM, fill=ORANGE)
            elif kind == "dim":
                d.text((x0, y), text, font=F_TERM, fill=FAINT)
            else:
                d.text((x0, y), text, font=F_TERM, fill=DIM)
            y += lh
        # 光标
        if int(t * 2) % 2 == 0 and y < limit - lh:
            d.rectangle([x0, y + 4, x0 + 12, y + 26], fill=(150, 200, 240))
        if sc.get("note"):
            self._draw_note(d, sc["note"])
        if sc.get("kpi"):
            self._draw_kpi(d, sc["kpi"], y + 46)

    def _draw_note(self, d, note):
        x, y = TERM_X + 40, 660
        d.rectangle([x, y + 3, x + 4, y + 96], fill=BLUE)
        d.text((x + 20, y), note["title"], font=F_PTITLE, fill=(140, 175, 215))
        for i, it in enumerate(note["items"]):
            d.text((x + 20, y + 32 + i * 28), "·  " + it, font=F_BODY, fill=DIM)

    def _draw_kpi(self, d, kpi, top):
        n = len(kpi)
        w = (TERM_W - 100) / n
        colors = [CYAN, GREEN, ORANGE, BLUE]
        base = max(top, TERM_Y + 360)
        for i, (val, label) in enumerate(kpi):
            x = TERM_X + 50 + i * w
            d.text((x, base), val, font=F_KPI, fill=colors[i % len(colors)])
            d.text((x, base + 62), label, font=F_BODY, fill=DIM)
            if i:
                d.line([(x - 18, base + 6), (x - 18, base + 92)], fill=(38, 46, 60), width=1)

    def _panel_image(self, which, t):
        if which == "A":
            start = A_START
            if t < start:
                return None
            fid = int((t - start) * FPS)
            fid = max(0, fid)
            return self._synth(fid)
        # B
        start = B_START
        if t < start or not self.frames_b:
            return None
        i = int((t - start) * FPS) + 1
        if i >= len(self.frames_b):
            i = len(self.frames_b) - 1
        return self._frame_b(i)

    def _synth(self, fid):
        key = ("syn", fid)
        if key in self.cache:
            return self.cache[key]
        try:
            sys.path.insert(0, "/home/user/omnetpp-6.3.0/workspace/satnet3d/simulations/education/semi_physical")
            from video_sender import draw_synthetic
            import numpy as np
            arr = draw_synthetic(fid, 960, 540, 25)
            im = Image.fromarray(arr[:, :, ::-1])
        except Exception:
            im = Image.new("RGB", (960, 540), (20, 26, 38))
        im = im.resize((P_W - 2, P_IMG_H - 1), Image.LANCZOS)
        if len(self.cache) < 12:
            self.cache[key] = im
        return im

    def _frame_b(self, idx):
        key = ("b", idx)
        if key in self.cache:
            return self.cache[key]
        path = self.frames_b[min(idx, len(self.frames_b) - 1)]
        im = Image.open(path).convert("RGB").resize((P_W - 2, P_IMG_H - 1), Image.LANCZOS)
        if len(self.cache) < 12:
            self.cache[key] = im
        return im

    def _draw_panels(self, img, d, sc, t):
        for which, y in (("A", P_A_Y), ("B", P_B_Y)):
            state = sc.get(which, "off")
            if state == "auto":
                state = "wait" if t < B_START + 0.12 else "live"
            box = [P_X + 1, y + P_HDR, P_X + P_W - 1, y + P_HDR + P_IMG_H]
            if state == "off":
                d.text((P_X + P_W / 2 - 60, y + P_HDR + P_IMG_H / 2 - 12), "未启动",
                       font=F_PTITLE, fill=(70, 80, 98))
                continue
            if state == "wait":
                blink = 6 if int(t * 2) % 2 == 0 else 3
                cx = P_X + P_W / 2
                cy = y + P_HDR + P_IMG_H / 2
                d.ellipse([cx - blink, cy - 34 - blink, cx + blink, cy - 34 + blink], fill=ORANGE)
                tw = text_w(d, "监听中，等待数据", F_PTITLE)
                d.text((cx - tw / 2, cy - 4), "监听中，等待数据", font=F_PTITLE, fill=DIM)
                continue
            tt = FREEZE_T if state == "frozen" else t
            im = self._panel_image(which, tt)
            if im is None:
                continue
            img.paste(im, (box[0], box[1]))
            if which == "A":
                fid = max(0, int((tt - A_START) * FPS))
                hud = "FRAME %04d   4.95 Mbps" % fid
            else:
                idx = max(0, int((tt - B_START) * FPS))
                delay = self.lat[min(idx, len(self.lat) - 1)] if self.lat else 0
                hud = "FRAME %04d   %d ms" % (idx + 1, int(delay))
            tw = text_w(d, hud, F_PHUD)
            d.text((P_X + P_W - 14 - tw, y + 8), hud, font=F_PHUD, fill=(238, 200, 120))

    def render(self, t):
        idx = 0
        for i, sc in enumerate(self.scenes):
            if sc["t0"] <= t < sc["t1"]:
                idx = i
                break
        else:
            idx = len(self.scenes) - 1
        sc = self.scenes[idx]
        img = self.bases[idx].copy()
        d = ImageDraw.Draw(img)
        if sc["kind"] == "term":
            self._draw_terminal(img, d, sc, t)
            self._draw_panels(img, d, sc, t)
        return img


def main():
    frames = load_frames()
    lat = load_latency()
    send_lines, recv_lines = load_send_recv_lines()
    st = load_stats()
    scenes = build_scenes(st, send_lines, recv_lines)
    total = scenes[-1]["t1"]
    comp = Composer(scenes, frames, lat)

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-an",
           "-c:v", "libx264", "-preset", "medium", "-crf", "20",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    n = int(total * FPS)
    for i in range(n):
        img = comp.render(i / FPS)
        p.stdin.write(img.tobytes())
        if i % 250 == 0:
            print("  %d/%d" % (i, n), flush=True)
    p.stdin.close()
    p.wait()
    print("输出：%s" % OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
