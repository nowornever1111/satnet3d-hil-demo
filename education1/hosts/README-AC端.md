# A / C 两端程序（真机演示随身包）

这个目录放的是**演示时跑在 A、C 两台电脑上的东西**，跟 B 上的仿真工程放在一起，
整包拷到 U 盘就能走。A、C 两边各一个自包含子目录，互不依赖：

```
hosts/
├── README-AC端.md        ← 本文件（地址表 + 部署 + 让 B 上 agent 怎么改）
├── pack_ac.sh            ← 打成 A端.tgz / C端.tgz，分别拷给两台机
├── A/                    ← 拷到电脑 A（发送端）
│   ├── video_sender.py       摄像头 → JPEG 分包 → UDP
│   ├── run_a.sh              Linux 一键起
│   ├── run_a.bat             Windows 双击起
│   ├── requirements.txt      opencv-python、numpy
│   └── 说明.md               配地址、自检、故障速查
└── C/                    ← 拷到电脑 C（接收端）
    ├── video_receiver.py     收分片 → 重组 → 显示 + 统计时延
    ├── run_c.sh
    ├── run_c.bat
    ├── requirements.txt
    └── 说明.md
```

## 一、地址表（三机两段，A、C 二层不通）

| 机器 | 地址 | 网关 | 谁往哪发 |
|---|---|---|---|
| A | `192.168.100.2/24` | 不配 | 发到 `192.168.100.1:5000` |
| B 网卡1 | `192.168.100.1/24` | 不配 | 仿真 gatewayA 绑这里 |
| B 网卡2 | `192.168.101.1/24` | 不配 | 仿真 gatewayB 绑这里 |
| C | `192.168.101.2/24` | 不配 | 监听 `192.168.101.2:5000` |

**最容易错的一点**：A 的目的地址是 `192.168.100.1`（B 网卡1），**不是 C**。
A 的包里根本没有 C 的地址，是 B 上的仿真域把帧取出来、过完星座、再以 `192.168.101.1` 的源地址发给 C。
脚本默认值已经按这个写好了。

## 二、部署（每端 1 分钟）

**A、C 是 Windows**，直接用 `A-发送-Windows.zip` / `C-接收-Windows.zip`：
解压后先读 `先看这个-Windows.md`（装 Python → 配 IP → 双击 bat，防火墙放行），
里面把每一步和报错对照都写全了。

在 Linux 机型上跑才需要下面的 shell 方式：

```bash
# 打包（在 B 上做，或在本机做）
bash pack_ac.sh                  # 生成 dist/A端.tgz、dist/C端.tgz

# A、C 各自解包后
bash run_a.sh       # 或 run_a.bat（Windows 双击）
bash run_c.sh       # 或 run_c.bat
```

依赖脚本会自己装（`pip install -r requirements.txt`）。离线环境请提前把
`opencv-python`、`numpy` 的 whl 拷过去，或 Ubuntu 上用 `sudo apt install python3-opencv`。

## 三、到时候用 B 上的 agent 改哪里

这份包里**能不改就不改**，因为脚本是 2026-11-19 实测跑通、PPT 里截图出自同一份代码。
真出现现场网段冲突（比如 100.x / 101.x 已被占用），只需要动 4 个值，其余一律不碰：

| # | 文件 | 变量 / 参数 | 默认 | 什么时候要改 |
|---|---|---|---|---|
| 1 | `A/run_a.sh`、`A/run_a.bat` | `ADDR` | `192.168.100.2` | A 的网段变了 |
| 2 | `A/run_a.sh`、`A/run_a.bat` | `GW` | `192.168.100.1` | B 网卡1 换地址了（**必须跟 `omnetpp-semi-real.ini` 的 `gatewayA.app[1].realLocalAddress` 一致**） |
| 3 | `C/run_c.sh`、`C/run_c.bat` | `BIND` | `192.168.101.2` | C 的网段变了 |
| 4 | `semi_physical/omnetpp-semi-real.ini`（B 侧） | `gatewayA/gatewayB.app[1].realLocalAddress`<br>`gatewayB.app[1].realDestAddress` | `192.168.100.1`<br>`192.168.101.1` / `192.168.101.2` | 同上，改一端就要成对改 |

改完必须成对自检：A `ping 100.1` 通、A `ping 101.2` 不通、C `ping 101.1` 通。
三条同时满足才说明包确实是从仿真域过的。

**可直接粘给 B 上 agent 的话：**

> 工程在 `~/omnetpp-6.3.0/workspace/satnet3d/simulations/education1`。
> 里面 `hosts/A` 是电脑 A 的发送端，`hosts/C` 是电脑 C 的接收端。
> 现在现场网段改成了 A=`<新地址>`、B 网卡1=`<新地址>`、B 网卡2=`<新地址>`、C=`<新地址>`。
> 请只改这几处：`hosts/A/run_a.sh` 与 `run_a.bat` 的 ADDR/GW、
> `hosts/C/run_c.sh` 与 `run_c.bat` 的 BIND、
> `semi_physical/omnetpp-semi-real.ini` 里 `gatewayA.app[1].realLocalAddress`、
> `gatewayB.app[1].realLocalAddress` / `realDestAddress`。
> 不要改两个 py 的任何逻辑，也不要动 IP 头、包长、端口号。
> 改完把 `grep -n "192.168" hosts/A/run_a.* hosts/C/run_c.* semi_physical/omnetpp-semi-real.ini` 的结果给我看。

## 四、真机拍不到时的退路

A、C 合并到 B 上跑单机版：`semi_physical/setup_veth.sh` 起一对 veth，
A 用 `--src 192.168.100.2 --dst 192.168.100.1`、C 用 `--bind 192.168.101.2`，
两端照常起，只是同机。讲解时说"三个角色的逻辑分离"，画面效果一致。
