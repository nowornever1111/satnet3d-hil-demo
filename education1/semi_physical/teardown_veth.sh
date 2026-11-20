#!/bin/sh
# 删除 setup_veth.sh 创建的 veth 设备与路由
# 用法：sudo sh teardown_veth.sh

ip link del vethA 2>/dev/null || true
ip link del vethB 2>/dev/null || true
ip route del 192.168.101.0/24 2>/dev/null || true
echo "已清理 vethA / vethB"
