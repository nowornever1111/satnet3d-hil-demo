# 案例二 · 卫星网络视频流传输（教学实验）

本目录是 SatNet3D 教学版实验工程，对应"案例二：视频流半实物仿真"。
核心目标：**视频流（UDP）经低轨卫星星座从一端传到另一端，并能测量端到端时延与吞吐。**

---

## 1. 目录结构

```
simulations/education/
├── package.ned                      # NED 包声明（satnet3d.simulations.education）
├── SatNet3DEducationNetwork.ned     # 纯仿真拓扑：48 星 + 两个地面站
├── SatNet3DEducationSemiPhysicalNetwork.ned  # 半实物拓扑：两个接入网关
├── omnetpp.ini                      # 仿真参数（星座、地址、视频业务、统计）
├── run                              # 启动脚本（已修正 NED 搜索路径）
├── extract_delay.py                 # 从 .vec 结果中提取逐包时延 → CSV
├── plot_delay.py                    # 由 CSV 生成时延曲线/分布图（可直接进 PPT）
├── semi_physical/                   # 半实物套件（桥接 ini + veth 脚本 + Python 端点）
│   ├── omnetpp-semi.ini             # 半实物配置（实时调度器）
│   ├── setup_veth.sh                # 建 veth 与地址
│   ├── video_sender.py              # 真实发送端（支持 --synthetic）
│   └── video_receiver.py            # 真实接收端（统计时延）
├── results/                         # 仿真输出（.sca/.vec/.csv/.png）
└── README.md
```

## 2. 前置条件

- OMNeT++ 6.3.0，环境变量需先加载：
  ```bash
  cd ~/omnetpp-6.3.0 && source setenv
  ```
- INET 4.6（`workspace/inet4.6`，已编译出 `src/libINET.so`）
- SatNet3D 模型库（`satnet3d/src/libsatnet3d.so`，若改动 C++ 源码需先 `make`）

> 本工程只使用已有模型库，**无需重新编译**。

## 3. 运行

```bash
cd ~/omnetpp-6.3.0 && source setenv
cd workspace/satnet3d/simulations/education

sh ./run -u Cmdenv                 # 命令行运行，结果写入 results/
sh ./run -u Cmdenv --sim-time-limit=60s   # 缩短时长快速验证
sh ./run -u Qtenv                  # 图形界面，可看三维星座（需把 ini 中 osgVisualizer 那行注释掉）
```

> `run` 脚本内的 NED 搜索路径为 `../../src:..:../../../inet4.6/src`。
> 注意 `..`（即 `satnet3d/`）不能省，否则 NED 包名 `satnet3d.simulations.*` 无法解析——
> 原有 `layer2/layer3/run` 用的是 `.`，命令行直接跑会报 "Declared package does not match expected package"。

## 4. 组网与业务参数

| 项目 | 取值 | 说明 |
|------|------|------|
| 星座 | Walker-Delta，8 面 × 6 星 = **48 星** | `walkerDeltaScenarioManager` 动态创建 |
| 轨道高度 | 1414 km | LEO |
| 轨道倾角 | 52° | |
| 星间链路 | `oneStarFourLinks`，1 Gbps | 每星与同轨前后 + 异轨相邻建链 |
| 地面站 | videoServer 北京（39.9°N, 116.4°E）<br>videoClient 伦敦（51.5°N, 0.1°W） | 对应案例中的"两台电脑" |
| 星地链路 | 卫星 eth4 作 DHCP 服务器，地面站 eth0 作客户端 | 地址动态分配 |
| 视频业务 | `UdpVideoStreamServer` / `UdpVideoStreamClient` | INET 自带模型 |
| 包长 | 1400 B | 接近以太网 MTU，不触发 IP 分片 |
| 发送间隔 | `uniform(4ms, 7ms)` | 平均码率 ≈ **2.2 Mbps**，含帧间抖动 |
| 视频总量 | 30 MB | 约 120 s 的流 |
| 请求时刻 | t = 20 s | 等 DHCP 与拓扑收敛完成 |
| 仿真时长 | 180 s | |

## 5. 实验步骤（建议按此顺序做）

1. **跑通基线**：`sh ./run -u Cmdenv`，确认最后输出 `Simulation time limit reached`。
2. **看业务是否通**：结果里 `videoServer.app[1] packetSent:count` 与
   `videoClient.app[1] packetReceived:count` 应基本相等（差值为在途/丢弃）。
3. **看时延**：`videoClient.app[1] endToEndDelay:histogram` 给出 count/mean/min/max/stddev。
4. **导出逐包时延**：`python3 extract_delay.py results/General-#0.vec results/delay_e2e.csv`
5. **出图**：把 `results/delay_e2e.csv` 拷回本机，`python plot_delay.py results/delay_e2e.csv results/`
   得到 `delay_timeseries.png` 与 `delay_distribution.png`。
6. **（可选）改参数做对照实验**：改星座规模（`numPlanes`/`satsPerPlane`）、
   改视频码率（`sendInterval`）、改地面站位置，观察时延与丢包变化。

## 6. 本次实测结果（180 s，48 星）

| 指标 | 数值 |
|------|------|
| 服务端发出 | 21 429 个包 / 30.0 MB |
| 客户端收到 | 21 428 个包 / 29.999 MB（丢包率 ≈ 0.005%） |
| 端到端时延 均值 | **65.40 ms**（标准差 2.40 ms） |
| P50 / P95 / P99 | 65.70 / 65.87 / 65.89 ms |
| 最大时延 | 185.65 ms（星地链路切换瞬间） |
| 转发路径 | 5 颗卫星参与：sat19（星地）→ ISL → sat31 → sat25 → sat26（星地） |
| 星间链路总流量 | 2.75 Mbps（业务码率 2.2 Mbps，双向叠加） |

可解释的现象：时延曲线呈**分段台阶状**——每段内缓慢变化（卫星相对地面站移动，
路径长度连续变化），在段边界处**跳变**（星地链路切换、重新选路）。
这正是案例二希望学生观察到的低轨星座动态特性，也是与地面固定网络最大的差别。

## 7. 半实物（真机接入）——已打通

真实 Python 视频端 → 仿真星座 → 真实接收端。详见 `semi_physical/README.md`。

| 指标 | 数值 |
|------|------|
| 真实包入网 / 出网 | 1 972 / 1 972（零丢失） |
| 视频帧 | 297 帧，15 fps 发送 |
| 端到端时延 | 均值 76.4 ms（纯本机 UDP 为 0.3 ms） |

实现方式：新增 `satnet3d/src/app/ExternalUdpBridge.{h,cc,ned}`（应用层桥接）。
原计划的 `ExtLowerEthernetInterface + veth`（二层挂接）不可用——预编译的 `libINET.so`
没有编译 emulation(pcap) 模块，启用需重编 INET。桥接方案保留了"真实流量 + 仿真路径 + 真实时延"，
只是不模拟链路层细节。

运行方式（三条命令）：

```bash
sudo sh semi_physical/setup_veth.sh
sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini
/usr/bin/python3 semi_physical/video_receiver.py --bind 192.168.101.2
```

## 8. 常见问题

| 现象 | 原因与处理 |
|------|-----------|
| `Declared package ... does not match expected package` | 用了旧的 `run` 脚本或 `-n` 路径少了 `..`，用本目录的 `run` |
| `Enter parameter ... sceneLatitude (unassigned)` | `coordinateSystem` 参数缺失，`omnetpp.ini` 里已给出，勿删 |
| 客户端收不到包、`packetReceived:count = 0` | 请求时刻太早（DHCP 未完成），把 `startTime` 调到 20 s 以后 |
| `results/*.vec` 很大（~90 MB） | 记录了全星座的矢量；用 `extract_delay.py` 导出后可直接删除 `.vec` |
| 想更快跑完 | `--sim-time-limit=60s` 即可看到前 40 s 的流（业务 20 s 起） |
