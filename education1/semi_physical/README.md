# 半实物接入（案例二 · Stage B）——已打通

真实 Python 视频端 → 仿真星座 → 真实 Python 接收端，**每条真实 UDP 包都穿过 48 星星座**。

## 实测结果（2026-11-17，虚拟机内实时运行 60 s）

| 指标 | 数值 |
|------|------|
| 真实包入网（gatewayA.pktsFromReal） | 1 972 |
| 出网送达真实端（gatewayB.pktsToReal） | 1 972（**零丢失**） |
| 视频帧 | 297 帧（15 fps 发送，13.4 fps 接收） |
| 端到端时延 | 均值 **76.4 ms**，P95 78 ms，最大 190 ms |
| 对照：纯本机 UDP | 0.3 ms |

时延从 0.3 ms 抬到 76 ms，说明流量确实走完了星座，没有被本机环路"短路"。

## 1. 为什么不用 veth + pcap（原方案）

原计划是 `ExtLowerEthernetInterface` 绑定 veth，在二层把真实网卡接进仿真。实测该方案不可行：

```
<!> Error: Class "inet::ExtInterface" not found
```

预编译的 `libINET.so` 没有编译 emulation 模块（`nm -D libINET.so | grep ExtInterface` 为 0），
要启用需装 libpcap-dev 并整体重编译 INET（数十分钟，且会动到现有环境）。

## 2. 实际方案：应用层桥接（ExternalUdpBridge）

新增自研模块 `satnet3d/src/app/ExternalUdpBridge.{h,cc,ned}`：

- 在仿真里开一个**真实 UDP 套接字**（可指定绑定地址与端口）
- 收到真实数据 → 包成仿真 UDP 包，发给仿真侧目的地址（如 `gatewayB`）
- 收到仿真数据 → 用真实套接字发出去（如 `192.168.101.2:5000`）
- 目的地址支持延迟解析：DHCP 分配完地址后才生效，之前到达的包计入 `droppedUnresolved`

数据通路：

```
Python 发送端 192.168.100.2
   │  真实 UDP → 192.168.100.1:5000
gatewayA.app[1]  (ExternalUdpBridge)
   │  仿真 UDP → gatewayB:5001
   ├── 48 星 Walker-Delta（星地 + 星间多跳）──
gatewayB.app[1]  (ExternalUdpBridge)
   │  真实 UDP → 192.168.101.2:5000
Python 接收端（解码显示 + 时延统计）
```

代价与收益：链路层细节（MAC、ARP、pcap 抓包）没有进入仿真，但**传输路径、多跳转发、时延特性完全是仿真的**，
足以支撑"多台电脑 + 仿真网络"的教学演示；需要验证二层行为时再走 pcap 重编译路线。

## 3. 编译（改了 C++ 才需要）

```bash
cd ~/omnetpp-6.3.0 && source setenv
cd workspace/satnet3d/src
opp_makemake --make-so -f --deep -KINET4_6_PROJ=../../inet4.6 -DINET_IMPORT \
             -I'$(INET4_6_PROJ)/src' -L'$(INET4_6_PROJ)/src' -lINET'$(D)'
make MODE=release -j8
```

> 新增 .cc 后必须重新 `opp_makemake` 生成 Makefile，否则新文件不会进编译列表。

## 4. 运行

```bash
# 0) 准备真实侧地址（每次重启虚拟机后都要做）
sudo sh semi_physical/setup_veth.sh

# 1) 启动仿真（在 education 目录下，实时调度器在 ini 里已指定）
cd ~/omnetpp-6.3.0 && source setenv
cd workspace/satnet3d/simulations/education
sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini

# 2) 等约 5 秒（DHCP 完成），另开终端跑接收端
#    注意：source setenv 会把 OMNeT 自带 venv 放到 PATH 最前，那里没有 cv2，
#    所以这里必须用 /usr/bin/python3
/usr/bin/python3 semi_physical/video_receiver.py --bind 192.168.101.2 \
        --save-csv results/semi/latency.csv

# 3) 再开终端跑发送端（有摄像头就去掉 --synthetic）
/usr/bin/python3 semi_physical/video_sender.py --src 192.168.100.2 \
        --dst 192.168.100.1 --synthetic
```

`--synthetic` 是合成画面模式，用于无摄像头环境先验证通路。

## 5. 抓包与验证

```bash
# 真实侧收发（两端地址都在本机，流量走 lo）
sudo tcpdump -i lo -n udp port 5000
#  14:56:54 IP 192.168.100.2.49938 > 192.168.100.1.5000: UDP, length 1400
#  14:56:54 IP 192.168.100.2.49938 > 192.168.100.1.5000: UDP, length 897

# 仿真侧桥接计数（仿真结束后）
grep -E 'pktsFromReal|pktsToReal' semi_physical/results/General-*.sca
```

判据：`pktsFromReal ≈ pktsToReal ≈ tcpdump 包数`，且端到端时延在 70 ms 量级（而不是 0.x ms）。

## 6. 踩过的坑

| 现象 | 原因 | 处理 |
|------|------|------|
| `ExtInterface not found` | INET 未编译 emulation | 改用应用层桥接 |
| `Cannot resolve address 'gatewayB'` | 初始化时 DHCP 还没分配 | 改用 `tryResolve` + 延迟解析 |
| `Cannot serialize Ipv4 header without checksum` | `peekAllAsBytes()` 连头部一起序列化 | 改用 `peekDataAsBytes()` 只取负载 |
| `Address already in use` | 桥接绑 `0.0.0.0:5000` 与接收端冲突 | 增加 `realLocalAddress`，绑到 192.168.100.1 |
| `ModuleNotFoundError: cv2` | `source setenv` 把 venv 放到 PATH 首位 | 用 `/usr/bin/python3` |
| 收端一直等不到包 | 仿真 60 s 到点自动结束 | 先起仿真，5 s 内起收发端 |
