// 案例二 · 半实物版本网络（应用层桥接方案）
//
//   真实 Python 发送端 --(真实UDP)--> gatewayA(仿真) ==(48星星座)==> gatewayB(仿真) --(真实UDP)--> 真实 Python 接收端
//
// 说明：预编译的 INET 库未包含 emulation(pcap) 模块，无法在二层挂 veth，
// 因此改用 satnet3d.app.ExternalUdpBridge 在应用层做收发桥接：
//   - 真实视频包进入 gatewayA 的桥接应用 -> 变成仿真 UDP 包，经星座转发到 gatewayB
//   - gatewayB 的桥接应用收到仿真包 -> 用真实 UDP 套接字发给真实接收端
// 传输路径依然完整穿过仿真星座，时延统计由仿真侧给出。
//
// 两台网关用与纯仿真一致的 EarthStandardHost + 卫星 DHCP 地址，网络层无需任何额外配置。

package satnet3d.simulations.education1;

import inet.visualizer.common.IntegratedVisualizer;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import satnet3d.common.AdaptiveGeographicCoordinateSystem;
import satnet3d.node.EarthStandardHost;
import satnet3d.node.SatelliteRouter;
import satnet3d.scenario.TopologyManager;
import satnet3d.scenario.WalkerDeltaScenarioManager;

network SatNet3DEducationSemiPhysicalNetwork
{
    submodules:
        visualizer: IntegratedVisualizer {
            parameters:
                @display("p=100,60");
        }
        coordinateSystem: AdaptiveGeographicCoordinateSystem {
            parameters:
                @display("p=100,160");
        }
        walkerDeltaScenarioManager: WalkerDeltaScenarioManager {
            parameters:
                @display("p=420,60");
                targetNetworkModule = "^";
                satelliteModuleType = "satnet3d.node.SatelliteRouter";
        }
        groundToSatTopologyManager: TopologyManager {
            parameters:
                @display("p=420,160");
                primaryLayerModule = "^";
                primaryNodeTypePattern = "satnet3d.node.EarthStandardHost";
                primaryNodeNamePattern = "*";
                peerLayerModule = "^";
                peerNodeTypePattern = "satnet3d.node.SatelliteRouter";
                peerNodeNamePattern = "*";
                maxLinksPerPrimaryNode = 1;
                initialUpdateOffset = 0s;
        }
        configurator: Ipv4NetworkConfigurator {
            parameters:
                @display("p=100,260;is=s");
        }
        // 真实主机 A 侧接入点（视频发送端所在机器）
        gatewayA: EarthStandardHost {
            parameters:
                @display("p=760,80");
        }
        // 真实主机 B 侧接入点（视频接收端所在机器）
        gatewayB: EarthStandardHost {
            parameters:
                @display("p=760,180");
        }
    connections allowunconnected:
}
