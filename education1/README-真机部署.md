# education1 —— 真机演示专用工程目录

与 `education` 平级、可整目录拷走的**干净版**工程，只保留真机（三机两段）演示要用的文件。
包名已改为 `satnet3d.simulations.education1`，与 `education` 互不干扰，两者可共存于同一台机。

---

## 1. 目录内容

```
education1/
├── package.ned                         包声明：satnet3d.simulations.education1
├── SatNet3DEducationNetwork.ned         纯仿真拓扑（48 星 + 2 地面站）
├── SatNet3DEducationSemiPhysicalNetwork.ned  半实物拓扑（gatewayA / gatewayB）
├── EducationGateway.ned                 地面网关
├── omnetpp.ini                          纯仿真参数
├── omnetpp_qtenv.ini                    图形版参数
├── run                                  启动脚本（相对路径，勿改）
├── extract_delay.py / plot_delay.py     结果提取与画图
├── README.md                            原工程说明
├── README-真机部署.md                   本文件
├── 现场执行单.md                        打印版：地址表、起停 9 步、故障速查
├── semi_physical/
│   ├── omnetpp-semi-real.ini            ★ 真机演示用这份
│   ├── omnetpp-semi.ini                 单机 veth 版（Plan B 用）
│   ├── setup_veth.sh / teardown_veth.sh 建/拆 veth（Plan B 用）
│   ├── video_sender.py / video_receiver.py  单机版收发（Plan B 用）
│   └── README.md
├── hosts/                               ★ 电脑 A、C 两端的随身包
│   ├── README-AC端.md                   地址表 + 现场给 B 上 agent 的修改指令
│   ├── pack_ac.sh                       打 dist/A端-发送.tgz、dist/C端-接收.tgz
│   ├── A/                               video_sender.py + run_a.sh/.bat + 说明.md
│   └── C/                               video_receiver.py + run_c.sh/.bat + 说明.md
├── src_app/                             桥接源码备份（重编 satnet3d 时用）
│   ├── ExternalUdpBridge.h / .cc
│   └── ExternalUdpBridge.ned.bak        改后缀，避免被 NED 扫描
└── video/                               录屏编排与合成脚本（可选）
```

---

## 2. 部署前提（B 上必须已有）

| 依赖 | 位置 | 缺失后果 |
|---|---|---|
| OMNeT++ 6.3.0 | `~/omnetpp-6.3.0`（`bin/opp_run`、`setenv`） | `run` 报 opp_run 找不到 |
| INET 4.6 库 | `workspace/inet4.6/src/libINET.so` | 加载失败 |
| satnet3d 库 | `workspace/satnet3d/src/libsatnet3d.so`（含 `ExternalUdpBridge`） | 网络构建失败，提示未知模块 |

`run` 里的路径是相对 `simulations/` 的：`../../src` → `satnet3d/src`，`../../../inet4.6/src` → `inet4.6/src`。
**本目录必须放在 `satnet3d/simulations/` 下**，层级错一层就跑不起来。

检查依赖：

```bash
cd ~/omnetpp-6.3.0/workspace/satnet3d/simulations
ls ../../src/libsatnet3d.so ../../../inet4.6/src/libINET.so
nm -C ../../src/libsatnet3d.so | grep -c 'ExternalUdpBridge::initialize'   # 应 ≥1
```

---

## 3. 拷到目标 B

> **现成的三个包在 `分发包/`**：`B-仿真-Ubuntu.tar.gz` 拷给 B，
> `A-发送-Windows.zip`、`C-接收-Windows.zip` 分别拷给 A、C（两台都是 Windows）。
> 逐台步骤见 `分发包/分发说明.md`。下面的命令是从零自己打的情况。

```bash
# 源机
tar czf education1.tgz --exclude='*/results' --exclude='*/dist' --exclude='*/__pycache__' \
    -C ~/omnetpp-6.3.0/workspace/satnet3d/simulations education1

# 目标 B
tar xzf education1.tgz -C ~/omnetpp-6.3.0/workspace/satnet3d/simulations/
```

若目标 B 上已有 `satnet3d` 工程（含 `src/libsatnet3d.so`），只需这一步，不必再拷 `src`。

整包拷过去之后，A、C 两端的程序就在 `education1/hosts/` 里，不用另外找：

```bash
cd ~/omnetpp-6.3.0/workspace/satnet3d/simulations/education1/hosts
bash pack_ac.sh            # 生成 dist/A端-发送.tgz、dist/C端-接收.tgz，分别拷给 A、C
```

现场要改的地址只有 4 个值（A 的 `ADDR`、`GW`，C 的 `BIND`，以及 B 上 ini 里的
`realLocalAddress`），清单与可直接粘贴的提示词见 `hosts/README-AC端.md` 第三节。

---

## 4. 启动（真机演示）

```bash
cd ~/omnetpp-6.3.0 && source setenv
cd workspace/satnet3d/simulations/education1

# 真机：三机两段
sh ./run -u Cmdenv -f semi_physical/omnetpp-semi-real.ini

# 单机回退（Plan B）
sudo sh semi_physical/setup_veth.sh
sh ./run -u Cmdenv -f semi_physical/omnetpp-semi.ini --sim-time-limit=900s
```

真机版的关键差异：`gatewayB.app[1].realLocalAddress = "192.168.101.1"`。
绑 `127.0.0.1` 时，源地址为回环的包发不上物理网卡，C 端收不到任何帧。

---

## 5. 与 education 的关系

| | `education` | `education1` |
|---|---|---|
| 包名 | `satnet3d.simulations.education` | `satnet3d.simulations.education1` |
| 用途 | 开发与单机实测 | 真机演示交付 |
| 含 `results/`、`layer2_hil/` | 有 | 无（已清理） |
| 真机版 ini | 有 | 有 |

两者可同时存在，`run` 的 `-n ..` 会把两个包一起载入，包名不同、无冲突。
本目录是独立副本，改这里不会影响 `education`。

---

## 6. 从零重建

若需在另一台 B 上重建本目录，把 `mk_education1.sh` 与本文档一起上传后执行：

```bash
scp mk_education1.sh README-真机部署.md user@B:/tmp/
ssh user@B 'bash /tmp/mk_education1.sh'
```

脚本会自动完成包名迁移、源码备份、清理试跑残留、打包与试加载。
三处必须改的地方已在脚本里处理：`package.ned`、每个 `.ned` 的 `package` 行、ini 里的全限定网络名；
`src_app/ExternalUdpBridge.ned` 改名为 `.ned.bak`，否则 `-n ..` 会把它当成本包 NED 扫描并报 package mismatch。
