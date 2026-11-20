#!/bin/bash
# 案例二 · 演示视频素材采集
#
# 跑一遍真实的半实物流程，把每一步的真实输出与接收端解码帧留下来，
# 供 make_video.py 合成带字幕的演示视频（虚拟机图形界面不可用时仍可出行车记录）。
#
# 用法：bash capture_run.sh [采集时长秒，默认 45]

set +u
DUR=${1:-45}
EDU=/home/user/omnetpp-6.3.0/workspace/satnet3d/simulations/education
CAP=/tmp/cap

cd /home/user/omnetpp-6.3.0 && source setenv -q >/dev/null 2>&1
cd "$EDU" || exit 1

rm -rf "$CAP" && mkdir -p "$CAP/frames"

echo "[1/5] 建立虚拟网口"
echo 123 | sudo -S -p '' sh semi_physical/setup_veth.sh > "$CAP/step1.log" 2>&1

echo "[2/5] 启动仿真"
nohup sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini > "$CAP/sim.log" 2>&1 &
sleep 8

echo "[3/5] 启动接收端"
nohup /usr/bin/python3 -u semi_physical/video_receiver.py \
    --bind 192.168.101.2 --no-display \
    --dump-dir "$CAP/frames" --dump-every 1 \
    --save-csv "$CAP/lat.csv" > "$CAP/recv.log" 2>&1 &
RECV=$!
sleep 2

echo "[4/5] 启动发送端（$DUR 秒）"
timeout "$DUR" /usr/bin/python3 -u semi_physical/video_sender.py \
    --synthetic --width 960 --height 540 \
    --src 192.168.100.2 --dst 192.168.100.1 \
    --no-preview --fps 25 --quality 60 > "$CAP/send.log" 2>&1

sleep 1
echo "[5/5] 收尾并留证据"
kill "$RECV" 2>/dev/null
sleep 1

SCA=$(ls -t results/*.sca 2>/dev/null | head -1)
[ -n "$SCA" ] && cp "$SCA" "$CAP/General.sca"

echo "帧数：$(ls "$CAP/frames" | wc -l)"
echo "素材目录：$CAP"
