# 卫星星座半实物演示 · 真机工程

案例二（48 星 Walker 星座 · 半实物链路）真机演示用的 OMNeT++ 工程，一台 Ubuntu 机器（下文称 **B**）+ 两台 Windows（A 发送 / C 接收）。

只放演示要用的东西，**不含** PPT、视频、仿真结果。

## 一、拿到 B 上（三行）

```bash
git clone https://github.com/nowornever1111/satnet3d-hil-demo.git ~/hil-demo
cd ~/hil-demo
bash 安装到B.sh                       # 自动拷到 ~/omnetpp-6.3.0/workspace/satnet3d/simulations/education1
```

如果 OMNeT++ 装在别处，把路径传进去：

```bash
bash 安装到B.sh /path/to/satnet3d/simulations
```

装完启动：

```bash
cd ~/omnetpp-6.3.0 && source setenv
cd workspace/satnet3d/simulations/education1
sh ./run -u Cmdenv -f semi_physical/omnetpp-semi-real.ini
```

看到 `2029 modules`、`simsec/sec ≈ 1.000` 就算起来了。

> `education1` 必须落在 `satnet3d/simulations/` 下一层。`run` 里写的是
> `../../src`（satnet3d/src）和 `../../../inet4.6/src`（INET），层级错一层就找不到库。

## 二、目录

```
.
├── 安装到B.sh                    一键装到 simulations/（会先删旧的 education1）
└── education1/
    ├── run                       启动脚本（相对路径，勿改）
    ├── package.ned               包声明 satnet3d.simulations.education1
    ├── SatNet3D*.ned             纯仿真拓扑 / 半实物拓扑 / 地面网关
    ├── omnetpp.ini               纯仿真参数
    ├── omnetpp_qtenv.ini         图形版参数（OSG 起不来时别用）
    ├── semi_physical/
    │   ├── omnetpp-semi-real.ini ★ 真机三机版，演示用这份
    │   ├── omnetpp-semi.ini      单机 veth 版（Plan B 兜底）
    │   └── setup_veth.sh / teardown_veth.sh
    ├── hosts/                    ★ A、C 两端的随身包
    │   ├── A/                    video_sender.py + run_a.bat（Windows 双击）
    │   ├── C/                    video_receiver.py + run_c.bat
    │   ├── README-AC端.md        地址表 + 现场要改的 4 个值
    │   ├── pack_ac.sh            重新打 A/C 的 zip
    │   └── dist/                 ★ A-发送-Windows.zip、C-接收-Windows.zip
    ├── src_app/                  桥接模块源码备份（重编 satnet3d 时用）
    ├── README-真机部署.md        目录说明、依赖检查、Plan B
    └── 现场执行单.md             打印版：地址表、起停 9 步、故障速查
```

## 三、A、C 两台的包

就在 `education1/hosts/dist/`：

| 文件 | 给谁 | 怎么用 |
|---|---|---|
| `A-发送-Windows.zip` | 电脑 A | 解压后读 `先看这个-Windows.md`：装 Python → 配 `192.168.100.2` → 双击 `run_a.bat` |
| `C-接收-Windows.zip` | 电脑 C | 解压后读 `先看这个-Windows.md`：装 Python → 配 `192.168.101.2` → 双击 `run_c.bat` |

克隆之后直接拷这两个 zip 给 A、C 就行，不用另找。

## 四、地址与顺序（摘要）

| 机器 | 地址 | 说明 |
|---|---|---|
| A | `192.168.100.2/24` | 发到 `192.168.100.1:5000`（B 网卡1，**不是 C**） |
| B 网卡1 | `192.168.100.1/24` | 仿真 gatewayA 绑这里 |
| B 网卡2 | `192.168.101.1/24` | 仿真 gatewayB 绑这里 |
| C | `192.168.101.2/24` | 监听 `:5000` |

- 四台（三段网段里）都**不配网关**；B 的 `net.ipv4.ip_forward` 必须为 **0**；
- 起停顺序：**B 仿真 → C 接收 → A 发送**；停的时候反过来；
- 关键证据：A `ping 192.168.101.2` **必须不通**，画面却出现在 C 上——唯一的通路是那 48 颗星。

详见 `education1/现场执行单.md`。

## 五、依赖

B 上需要预先装好，本仓库不含：

- OMNeT++ 6.3.0（`~/omnetpp-6.3.0`）
- INET 4.6（`workspace/inet4.6/src/libINET.so`）
- satnet3d（`workspace/satnet3d/src/libsatnet3d.so`，含 `ExternalUdpBridge`）

A、C 只需 Python 3.9+，首次运行会自动 `pip install opencv-python numpy`。

## 六、重新生成分发物

改过 `hosts/` 之后，在源工程根目录执行：

```bash
python 04-代码/本机工具/_mk_packages.py
```

会重打 B 整包与 A/C 两个 zip；本仓库的 `education1/` 直接从 B 包里解出来即可。
