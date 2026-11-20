#!/bin/bash
# 电脑 A · 一键启动视频发送端（Linux / macOS）
#
# 用法：
#   bash run_a.sh                  正常发摄像头
#   bash run_a.sh --synthetic      没摄像头，用合成动态画面联调通路
#   bash run_a.sh --list-cameras   先确认摄像头序号
#   bash run_a.sh --camera 1       用第 2 个摄像头
#   ADDR=192.168.100.3 bash run_a.sh   临时换本机地址（网段不同时用）
set -u
cd "$(dirname "$0")"

ADDR="${ADDR:-192.168.100.2}"   # A 自己的网卡地址
GW="${GW:-192.168.100.1}"       # B 网卡1 = 仿真入口（不是 C 的地址！）
PORT="${PORT:-5000}"
FPS="${FPS:-25}"
W="${W:-960}"
H="${H:-540}"

echo "== 电脑 A 发送端 =="
echo "   本机地址 : $ADDR"
echo "   目的地址 : $GW:$PORT   (B 网卡1，经仿真域转发到 C)"
echo "   画幅帧率 : ${W}x${H} @ ${FPS}fps"

if ! ip -4 addr 2>/dev/null | grep -q "$ADDR"; then
    echo "   [提醒] 本机没有 $ADDR，先配地址：sudo ip addr add $ADDR/24 dev <网卡名>"
fi

if ! python3 -c "import cv2, numpy" 2>/dev/null; then
    echo "== 缺 opencv/numpy，安装依赖 =="
    python3 -m pip install -r requirements.txt
fi

exec python3 video_sender.py \
    --src "$ADDR" --dst "$GW" --port "$PORT" \
    --fps "$FPS" --width "$W" --height "$H" \
    --win-size 960x540 "$@"
