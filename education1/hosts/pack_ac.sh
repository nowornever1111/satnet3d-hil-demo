#!/bin/bash
# 把 A、C 两端分别打包，各生成一个可单独拷走的 tgz
# 用法：bash pack_ac.sh
# 产物：dist/A端-发送.tgz   → 解包得到 A端-发送/，拷到电脑 A
#       dist/C端-接收.tgz   → 解包得到 C端-接收/，拷到电脑 C
set -e
cd "$(dirname "$0")"
mkdir -p dist

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

cp -r A "$tmp/A端-发送"
cp -r C "$tmp/C端-接收"
cp README-AC端.md "$tmp/"
rm -rf "$tmp"/*/__pycache__ "$tmp"/*/dist /tmp/nohup.out

# --owner/--group 归零，避免拷到别人机器上出现奇怪属主
tar czf "dist/A端-发送.tgz" --owner=0 --group=0 --mode='u+rwX,go+rX' \
    -C "$tmp" "A端-发送" README-AC端.md
tar czf "dist/C端-接收.tgz" --owner=0 --group=0 --mode='u+rwX,go+rX' \
    -C "$tmp" "C端-接收" README-AC端.md

echo "=== 产物 ==="
ls -lh dist/*.tgz
echo
echo "=== A 端内容 ==="
tar tzf "dist/A端-发送.tgz"
echo
echo "=== C 端内容 ==="
tar tzf "dist/C端-接收.tgz"
