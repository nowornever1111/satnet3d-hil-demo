//
// 案例二半实物接入：真实 UDP 套接字 <-> 仿真 UDP 应用
//
// 本模块解决一个问题：预编译的 INET 库没有编译 emulation（pcap）模块，
// 无法用 ExtLowerEthernetInterface 在二层挂 veth。因此在应用层做桥接——
// 仍然让真实进程产生/接收视频流，传输路径依旧完整穿过仿真星座。
//
// 典型部署（两台网关各一个实例）：
//   网关A: ExternalUdpBridge  realLocalPort=5000  ->  simDestAddress=gatewayB  simDestPort=5001
//          真实视频发送端(192.168.100.2) 发往 192.168.100.1:5000（该地址配在 vethA 上）
//   网关B: ExternalUdpBridge  realLocalPort=5001  ->  realDestAddress=192.168.101.2:5000
//          仿真包到达后，用真实 UDP 套接字发给真实视频接收端
//
// 注意：真实时间与仿真时间要同步，运行时必须使用实时调度器：
//   opp_run ... --scheduler=inet::RealTimeScheduler
//

#ifndef SATNET3D_APP_EXTERNALUDPBRIDGE_H_
#define SATNET3D_APP_EXTERNALUDPBRIDGE_H_

#include <vector>

#ifdef __linux__
#include <netinet/in.h>
#endif

#include "inet/applications/base/ApplicationBase.h"
#include "inet/transportlayer/contract/udp/UdpSocket.h"

namespace satnet3d {

using namespace inet;

class ExternalUdpBridge : public ApplicationBase, public UdpSocket::ICallback
{
  protected:
    UdpSocket socket;
    cMessage *pollTimer = nullptr;

    // 真实侧
    int realFd = -1;
    int realLocalPort = 5000;
    std::string realLocalAddressStr;
    std::string realDestAddressStr;
    int realDestPort = 0;
    struct sockaddr_in realDestAddr;

    // 仿真侧
    int simLocalPort = -1;
    int simDestPort = 5000;
    std::string simDestAddressStr;
    L3Address simDestAddress;

    double pollInterval = 0.001;

    long pktsFromReal = 0;
    long pktsToReal = 0;
    long bytesFromReal = 0;
    long bytesToReal = 0;
    long droppedUnresolved = 0;

    void openRealSocket();
    void closeRealSocket();
    void drainRealSocket();
    void forwardToReal(const std::vector<uint8_t>& data);

  protected:
    virtual int numInitStages() const override { return NUM_INIT_STAGES; }
    virtual void initialize(int stage) override;
    virtual void finish() override;
    virtual void handleMessageWhenUp(cMessage *msg) override;

    virtual void handleStartOperation(LifecycleOperation *operation) override;
    virtual void handleStopOperation(LifecycleOperation *operation) override;
    virtual void handleCrashOperation(LifecycleOperation *operation) override;

    virtual void socketDataArrived(UdpSocket *socket, Packet *packet) override;
    virtual void socketErrorArrived(UdpSocket *socket, Indication *indication) override;
    virtual void socketClosed(UdpSocket *socket) override;

  public:
    ExternalUdpBridge() {}
    virtual ~ExternalUdpBridge();
};

} // namespace satnet3d

#endif
