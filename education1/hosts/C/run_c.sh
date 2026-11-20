#!/bin/bash
# 电脑 C · 一键启动视频接收端（Linux / macOS）
#
# 用法：
#   bash run_c.sh                              正常收流并显示
#   bash run_c.sh --no-display                 只统计不弹窗
#   BIND=192.168.101.3 bash run_c.sh           临时换本机地址
set -u
cd "$(dirname "$0")"

BIND="${BIND:-192.168.101.2}"   # C 自己的网卡地址
PORT="${PORT:-5000}"
CSV="${CSV:-recv_latency.csv}"

echo "== 电脑 C 接收端 =="
echo "   监听 : $BIND:$PORT"
echo "   时延 : 写入 $CSV"

if ! ip -4 addr 2>/dev/null | grep -q "$BIND"; then
    echo "   [提醒] 本机没有 $BIND，先配地址：sudo ip addr add $BIND/24 dev <网卡名>"
fi

if ! python3 -c "import cv2, numpy" 2>/dev/null; then
    echo "== 缺 opencv/numpy，安装依赖 =="
    python3 -m pip install -r requirements.txt
fi

exec python3 video_receiver.py \
    --bind "$BIND" --port "$PORT" \
    --save-csv "$CSV" --win-size 1000x560 "$@"
