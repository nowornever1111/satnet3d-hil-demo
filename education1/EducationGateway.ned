// 半实物接入网关：2 个以太网口
//   eth[0]：面向真实主机（extLower + veth），由 omnetpp-semi.ini 替换为 ExtLowerEthernetInterface
//   eth[1]：面向卫星星座（由 TopologyManager 动态建链，primaryFirstGateIndex=1）
//
// 采用 Router 而非 StandardHost，是为了开启 IP 转发——半实物需要仿真侧当网关，
// 把真实网段的流量转发进星座，再把星座出来的流量转发回真实主机。

package satnet3d.simulations.education1;

import inet.node.inet.Router;

module EducationGateway extends Router
{
    parameters:
        numEthInterfaces = default(2);
        @display("i=block/switch");

        mobility.typename = default("EarthFixedMobility");
        mobility.coordinateSystemModule = default("coordinateSystem");
        mobility.updateInterval = default(0.1s);
        mobility.latitude = default(0deg);
        mobility.longitude = default(0deg);
        mobility.altitude = default(0m);
        mobility.earthRotationSpeed = default(7.2921159e-5radps);
        mobility.initialEarthRotation = default(0deg);
}
