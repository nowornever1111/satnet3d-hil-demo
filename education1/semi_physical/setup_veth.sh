#!/bin/sh
# 案例二半实物：准备"真实主机"侧的地址环境
#
#   真实发送端 192.168.100.2 (vethA-peer)  -->  发往 192.168.100.1:5000
#   192.168.100.1 配在 vethA 上，由仿真里的 gatewayA 桥接应用监听
#
#   仿真 gatewayB 把数据发往 192.168.101.2:5000
#   192.168.101.2 配在 vethB-peer 上，由真实接收端监听
#
# 两台"电脑"用同一台 Linux 的两个网段模拟；veth 保证地址真实存在、可用 tcpdump 抓包。
# 用法：sudo sh setup_veth.sh

set -e

echo "== 清理旧设备 =="
ip link del vethA 2>/dev/null || true
ip link del vethB 2>/dev/null || true

echo "== 创建 veth 对 =="
ip link add vethA type veth peer name vethA-peer
ip link add vethB type veth peer name vethB-peer

echo "== 配置地址 =="
ip addr add 192.168.100.1/24 dev vethA
ip addr add 192.168.100.2/24 dev vethA-peer
ip addr add 192.168.101.2/24 dev vethB-peer

echo "== 启用接口 =="
ip link set vethA up
ip link set vethA-peer up
ip link set vethB up
ip link set vethB-peer up

echo
echo "== 完成 =="
ip -brief addr show vethA | cat
ip -brief addr show vethA-peer | cat
ip -brief addr show vethB-peer | cat

cat <<'EOF'

接下来：
  1. 启动仿真（实时调度器）： cd .. && sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini
  2. 等 5 秒（DHCP 完成后），另开终端跑：
       python3 semi_physical/video_receiver.py --bind 192.168.101.2
       python3 semi_physical/video_sender.py --src 192.168.100.2 --dst 192.168.100.1 --synthetic
  3. 抓包看流量是否真的进出仿真：
       sudo tcpdump -i vethA -n udp port 5000
EOF
