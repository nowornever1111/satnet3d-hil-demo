// 案例二：卫星网络视频流传输（教学版）
//
// 网络由三部分组成：
//   1. Walker-Delta 低轨星座（由 WalkerDeltaScenarioManager 在初始化时动态创建）
//   2. 两个地面站：videoServer（视频发送端）、videoClient（视频接收端）
//   3. 地面站-卫星动态拓扑维护（TopologyManager）与 IPv4 自动配置
//
// 与 simulations/layer3 的区别：layer3 用 UdpSendApp 发固定大小探测包，
// 本网络用 INET 自带的 UdpVideoStreamServer / UdpVideoStreamClient 模拟视频流，
// 便于统计端到端时延、吞吐与时延抖动（案例二的核心观测指标）。

package satnet3d.simulations.education1;

import inet.visualizer.common.IntegratedVisualizer;
import inet.networklayer.configurator.ipv4.Ipv4NetworkConfigurator;
import satnet3d.common.AdaptiveGeographicCoordinateSystem;
import satnet3d.node.EarthStandardHost;
import satnet3d.node.SatelliteRouter;
import satnet3d.scenario.TopologyManager;
import satnet3d.scenario.WalkerDeltaScenarioManager;

network SatNet3DEducationNetwork
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
        // 视频发送端（服务端）
        videoServer: EarthStandardHost {
            parameters:
                @display("p=760,80");
        }
        // 视频接收端（客户端）
        videoClient: EarthStandardHost {
            parameters:
                @display("p=760,180");
        }
    connections allowunconnected:
}
