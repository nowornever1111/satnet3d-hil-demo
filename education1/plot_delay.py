#!/usr/bin/env python3
"""由 delay_e2e.csv 生成案例二实验结果图（时延曲线 + 时延分布/CDF）。

用法：python plot_delay.py results/delay_e2e.csv results/
"""
import csv
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

csv_path = sys.argv[1] if len(sys.argv) > 1 else "results/delay_e2e.csv"
out_dir = sys.argv[2] if len(sys.argv) > 2 else "results"
os.makedirs(out_dir, exist_ok=True)

t, d = [], []
with open(csv_path, newline="", encoding="utf-8") as f:
    for row in csv.DictReader(f):
        t.append(float(row["sim_time_s"]))
        d.append(float(row["delay_s"]) * 1000.0)  # ms

t = np.array(t)
d = np.array(d)
order = np.argsort(t)
t, d = t[order], d[order]

mean, std = d.mean(), d.std()
p50, p95, p99 = np.percentile(d, [50, 95, 99])

# ---------- 图1：逐包端到端时延曲线（全量 + 细节放大） ----------
fig, (ax0, ax) = plt.subplots(2, 1, figsize=(11, 6.4), dpi=200,
                              sharex=True, gridspec_kw={"height_ratios": [1, 1.15]})

for a in (ax0, ax):
    a.plot(t, d, lw=0.5, color="#2a6ebb", alpha=0.8, label="逐包端到端时延")
    a.axhline(mean, color="#d9534f", ls="--", lw=1.3, label=f"均值 {mean:.1f} ms")
    a.grid(alpha=0.25, ls="--", lw=0.6)

ax0.set_ylim(0, d.max() * 1.08)
ax0.set_ylabel("时延 (ms)")
ax0.set_title("案例二 · 视频流经 48 星 Walker-Delta 星座的逐包端到端时延")
ax0.legend(loc="upper right", fontsize=8, frameon=True, ncol=2)

# 放大稳态区间（去掉 <1 ms 以外的尖峰）
lo = np.percentile(d, 1) - 0.6
hi = np.percentile(d, 99) + 0.4
ax.set_ylim(lo, hi)
ax.set_xlabel("仿真时间 (s)")
ax.set_ylabel("时延 (ms)")
ax.set_title(f"稳态区间放大（{lo:.1f}–{hi:.1f} ms）：抖动主要来自星地链路切换", fontsize=10)

fig.tight_layout()
f1 = os.path.join(out_dir, "delay_timeseries.png")
fig.savefig(f1)
print("saved", f1)

# ---------- 图2：时延分布 + CDF ----------
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4.6), dpi=200)

ax1.hist(d, bins=80, color="#2a6ebb", alpha=0.85, edgecolor="white", lw=0.3)
ax1.axvline(mean, color="#d9534f", ls="--", lw=1.4, label=f"均值 {mean:.1f} ms")
ax1.set_xlabel("端到端时延 (ms)")
ax1.set_ylabel("包数量")
ax1.set_title("时延分布直方图")
ax1.legend()
ax1.grid(alpha=0.25, ls="--", lw=0.6)

ds = np.sort(d)
cdf = np.arange(1, len(ds) + 1) / len(ds)
ax2.plot(ds, cdf * 100, color="#2a6ebb", lw=1.6)
for p, c in [(p50, "#5cb85c"), (p95, "#f0ad4e"), (p99, "#d9534f")]:
    ax2.axvline(p, color=c, ls="--", lw=1.2)
    ax2.text(p, 5, f" {p:.1f}", color=c, fontsize=8, rotation=90)
ax2.set_xlabel("端到端时延 (ms)")
ax2.set_ylabel("累积概率 (%)")
ax2.set_title("时延 CDF")
ax2.grid(alpha=0.25, ls="--", lw=0.6)

fig.tight_layout()
f2 = os.path.join(out_dir, "delay_distribution.png")
fig.savefig(f2)
print("saved", f2)

print("统计：样本 %d，均值 %.2f ms，标准差 %.2f ms，P50 %.2f，P95 %.2f，P99 %.2f，最大 %.2f"
      % (len(d), mean, std, p50, p95, p99, d.max()))
