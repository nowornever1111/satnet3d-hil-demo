#!/bin/bash
# 把本仓库的 education1 安装到 OMNeT++ 工作区的 simulations/ 下
#
# 用法：
#   bash 安装到B.sh                    # 默认 ~/omnetpp-6.3.0/workspace/satnet3d/simulations
#   bash 安装到B.sh /自定义/simulations
set -e

DEST="${1:-$HOME/omnetpp-6.3.0/workspace/satnet3d/simulations}"
SRC="$(cd "$(dirname "$0")" && pwd)/education1"

[ -d "$SRC" ] || { echo "[错误] 找不到 $SRC"; exit 1; }
[ -d "$DEST" ] || { echo "[错误] 目标目录不存在：$DEST"; exit 1; }

# 依赖检查（只提醒，不阻断）
[ -f "$DEST/../../src/libsatnet3d.so" ] || \
    echo "[提醒] 没找到 $DEST/../../src/libsatnet3d.so —— satnet3d 可能还没编译"
[ -f "$DEST/../../../inet4.6/src/libINET.so" ] || \
    echo "[提醒] 没找到 $DEST/../../../inet4.6/src/libINET.so —— INET 路径可能不对"

if [ -d "$DEST/education1" ]; then
    echo "旧的 education1 将被替换：$DEST/education1"
    rm -rf "$DEST/education1"
fi

cp -r "$SRC" "$DEST/education1"
chmod +x "$DEST/education1/run" \
         "$DEST/education1"/semi_physical/*.sh \
         "$DEST/education1"/hosts/pack_ac.sh 2>/dev/null || true
find "$DEST/education1/hosts" -name '*.sh' -exec chmod +x {} + 2>/dev/null || true

echo
echo "已安装到：$DEST/education1"
echo "文件数：$(find "$DEST/education1" -type f | wc -l)"
echo
echo "启动："
echo "  cd ~/omnetpp-6.3.0 && source setenv"
echo "  cd $DEST/education1"
echo "  sh ./run -u Cmdenv -f semi_physical/omnetpp-semi-real.ini"
echo
echo "给 A、C 的包在：$DEST/education1/hosts/dist/"
