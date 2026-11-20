#include <cerrno>
#include <cstring>
#include <vector>

#include <arpa/inet.h>
#include <fcntl.h>
#include <sys/socket.h>
#include <unistd.h>

#include "ExternalUdpBridge.h"

#include "inet/common/ModuleAccess.h"
#include "inet/common/TimeTag_m.h"
#include "inet/common/packet/chunk/BytesChunk.h"
#include "inet/networklayer/common/L3AddressResolver.h"

namespace satnet3d {

Define_Module(ExternalUdpBridge);

ExternalUdpBridge::~ExternalUdpBridge()
{
    cancelAndDelete(pollTimer);
    closeRealSocket();
}

void ExternalUdpBridge::initialize(int stage)
{
    ApplicationBase::initialize(stage);
    if (stage == INITSTAGE_LOCAL) {
        realLocalPort = par("realLocalPort");
        realLocalAddressStr = par("realLocalAddress").stringValue();
        realDestAddressStr = par("realDestAddress").stringValue();
        realDestPort = par("realDestPort");
        simLocalPort = par("simLocalPort");
        simDestPort = par("simDestPort");
        simDestAddressStr = par("simDestAddress").stringValue();
        pollInterval = par("pollInterval").doubleValue();
        pollTimer = new cMessage("external-poll");
        WATCH(pktsFromReal);
        WATCH(pktsToReal);
    }
}

void ExternalUdpBridge::finish()
{
    recordScalar("pktsFromReal", pktsFromReal);
    recordScalar("pktsToReal", pktsToReal);
    recordScalar("bytesFromReal", bytesFromReal);
    recordScalar("bytesToReal", bytesToReal);
    recordScalar("droppedUnresolved", droppedUnresolved);
    closeRealSocket();
}

void ExternalUdpBridge::handleStartOperation(LifecycleOperation *operation)
{
    openRealSocket();

    socket.setOutputGate(gate("socketOut"));
    socket.setCallback(this);
    socket.bind(simLocalPort);

    if (!simDestAddressStr.empty()) {
        // 目的地址可能由 DHCP 动态分配，此刻未必可用；在 drainRealSocket() 里重试解析
        L3Address resolved;
        if (L3AddressResolver().tryResolve(simDestAddressStr.c_str(), resolved))
            simDestAddress = resolved;
    }

    scheduleAfter(pollInterval, pollTimer);
    EV_INFO << "ExternalUdpBridge started: real :" << realLocalPort
            << " -> sim " << simDestAddress << ":" << simDestPort
            << " ; sim -> real " << realDestAddressStr << ":" << realDestPort << "\n";
}

void ExternalUdpBridge::handleStopOperation(LifecycleOperation *operation)
{
    cancelEvent(pollTimer);
    socket.close();
    closeRealSocket();
}

void ExternalUdpBridge::handleCrashOperation(LifecycleOperation *operation)
{
    cancelEvent(pollTimer);
    socket.destroy();
    closeRealSocket();
}

void ExternalUdpBridge::handleMessageWhenUp(cMessage *msg)
{
    if (msg == pollTimer) {
        drainRealSocket();
        scheduleAfter(pollInterval, pollTimer);
    }
    else
        socket.processMessage(msg);
}

void ExternalUdpBridge::openRealSocket()
{
    realFd = ::socket(AF_INET, SOCK_DGRAM, 0);
    if (realFd < 0)
        throw cRuntimeError("Cannot create real UDP socket: %s", strerror(errno));

    int one = 1;
    setsockopt(realFd, SOL_SOCKET, SO_REUSEADDR, &one, sizeof(one));
    int rcvbuf = 8 * 1024 * 1024;
    setsockopt(realFd, SOL_SOCKET, SO_RCVBUF, &rcvbuf, sizeof(rcvbuf));
    int sndbuf = 8 * 1024 * 1024;
    setsockopt(realFd, SOL_SOCKET, SO_SNDBUF, &sndbuf, sizeof(sndbuf));

    struct sockaddr_in local;
    memset(&local, 0, sizeof(local));
    local.sin_family = AF_INET;
    local.sin_addr.s_addr = htonl(INADDR_ANY);
    if (!realLocalAddressStr.empty() && realLocalAddressStr != "0.0.0.0")
        inet_pton(AF_INET, realLocalAddressStr.c_str(), &local.sin_addr);
    local.sin_port = htons(realLocalPort);
    if (::bind(realFd, (struct sockaddr *)&local, sizeof(local)) < 0)
        throw cRuntimeError("Cannot bind real UDP port %d: %s", realLocalPort, strerror(errno));

    int flags = fcntl(realFd, F_GETFL, 0);
    fcntl(realFd, F_SETFL, flags | O_NONBLOCK);

    memset(&realDestAddr, 0, sizeof(realDestAddr));
    realDestAddr.sin_family = AF_INET;
    realDestAddr.sin_port = htons(realDestPort);
    if (!realDestAddressStr.empty()) {
        if (inet_pton(AF_INET, realDestAddressStr.c_str(), &realDestAddr.sin_addr) != 1)
            throw cRuntimeError("Invalid realDestAddress '%s' (dotted IPv4 expected)",
                                realDestAddressStr.c_str());
    }
}

void ExternalUdpBridge::closeRealSocket()
{
    if (realFd >= 0) {
        ::close(realFd);
        realFd = -1;
    }
}

void ExternalUdpBridge::drainRealSocket()
{
    if (realFd < 0)
        return;

    static thread_local uint8_t buffer[1 << 16];
    for (int i = 0; i < 1024; i++) {
        struct sockaddr_in from;
        socklen_t fromLen = sizeof(from);
        ssize_t n = ::recvfrom(realFd, buffer, sizeof(buffer), 0,
                               (struct sockaddr *)&from, &fromLen);
        if (n <= 0)
            break;  // EAGAIN：真实侧暂时没有数据

        // 目的地址尚未解析成功（DHCP 还没分配），先尝试再决定
        if (!simDestAddressStr.empty() && simDestAddress.isUnspecified()) {
            L3Address resolved;
            if (L3AddressResolver().tryResolve(simDestAddressStr.c_str(), resolved)) {
                simDestAddress = resolved;
                EV_INFO << "Resolved simDestAddress '" << simDestAddressStr
                        << "' -> " << simDestAddress << "\n";
            }
            else {
                droppedUnresolved++;
                continue;
            }
        }

        auto data = makeShared<BytesChunk>(buffer, static_cast<size_t>(n));
        auto packet = new Packet("RealToSim", data);
        packet->addTag<CreationTimeTag>()->setCreationTime(simTime());

        pktsFromReal++;
        bytesFromReal += n;
        socket.sendTo(packet, simDestAddress, simDestPort);
    }
}

void ExternalUdpBridge::forwardToReal(const std::vector<uint8_t>& data)
{
    if (realFd < 0 || realDestPort == 0)
        return;
    ssize_t sent = ::sendto(realFd, data.data(), data.size(), 0,
                            (struct sockaddr *)&realDestAddr, sizeof(realDestAddr));
    if (sent < 0)
        EV_WARN << "sendto to real side failed: " << strerror(errno) << "\n";
}

void ExternalUdpBridge::socketDataArrived(UdpSocket *socket, Packet *packet)
{
    auto bytes = packet->peekDataAsBytes();
    const std::vector<uint8_t>& raw = bytes->getBytes();
    std::vector<uint8_t> buffer(raw.begin(), raw.end());

    forwardToReal(buffer);
    pktsToReal++;
    bytesToReal += buffer.size();
    delete packet;
}

void ExternalUdpBridge::socketErrorArrived(UdpSocket *socket, Indication *indication)
{
    EV_WARN << "Ignoring UDP error report " << indication->getName() << "\n";
    delete indication;
}

void ExternalUdpBridge::socketClosed(UdpSocket *socket)
{
    if (operationalState == State::STOPPING_OPERATION)
        startActiveOperationExtraTimeOrFinish(par("stopOperationExtraTime"));
}

} // namespace satnet3d
