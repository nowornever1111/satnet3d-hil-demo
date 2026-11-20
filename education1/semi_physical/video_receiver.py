#!/usr/bin/env python3
"""案例二半实物 · 视频接收端（对应"电脑 B"：vethB → UDP → 解码显示）

监听 vethB-peer 上的 UDP 端口，重组 JPEG 帧并显示，同时统计端到端时延。

依赖：opencv-python、numpy
    sudo apt install python3-opencv        # 或 pip install opencv-python numpy

用法：
    python3 video_receiver.py
    python3 video_receiver.py --bind 192.168.101.2 --port 5000 --save-csv recv_latency.csv

时延 = 本机收到该帧的墙钟时间 - 发送端写入的时间戳（同机测试时可直接对比）
"""
import argparse
import csv
import os
import signal
import socket
import struct
import sys
import time

import cv2
import numpy as np

HEADER = struct.Struct("!IHHI")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--bind", default="192.168.101.2", help="接收端绑定地址（vethB-peer）")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--save-csv", default="", help="把逐帧时延写入该 CSV 文件")
    ap.add_argument("--no-display", action="store_true", help="不弹窗，只统计")
    ap.add_argument("--win-size", default="", help="窗口尺寸，形如 960x540（录制排版用）")
    ap.add_argument("--win-pos", default="", help="窗口左上角坐标，形如 1010,40（录制排版用）")
    ap.add_argument("--dump-dir", default="", help="把解码后的帧另存到该目录（做演示视频用）")
    ap.add_argument("--dump-every", type=int, default=1, help="每隔多少帧存一张")
    args = ap.parse_args()

    # 被 kill / timeout 终止时也走正常收尾，保证 CSV 与统计落盘
    def _on_term(signum, frame):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, _on_term)
    signal.signal(signal.SIGINT, _on_term)

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 8 * 1024 * 1024)
    sock.bind((args.bind, args.port))
    sock.settimeout(1.0)
    print("接收端：监听 %s:%d" % (args.bind, args.port))

    csv_f = None
    csv_w = None
    if args.save_csv:
        csv_f = open(args.save_csv, "w", newline="", encoding="utf-8")
        csv_w = csv.writer(csv_f)
        csv_w.writerow(["wall_time_s", "frame_id", "delay_ms", "frame_bytes"])

    frames = {}          # frame_id -> {idx: chunk}
    meta = {}            # frame_id -> (total, ts_ms)
    latencies = []
    got = 0
    dropped = 0
    t0 = time.time()

    win_name = "Receiver - decoded"
    if not args.no_display and (args.win_size or args.win_pos):
        cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
        if args.win_size:
            ww, wh = [int(v) for v in args.win_size.lower().split("x")]
            cv2.resizeWindow(win_name, ww, wh)
        if args.win_pos:
            wx, wy = [int(v) for v in args.win_pos.split(",")]
            cv2.moveWindow(win_name, wx, wy)
        cv2.waitKey(50)

    try:
        while True:
            try:
                pkt, _ = sock.recvfrom(65535)
            except socket.timeout:
                continue
            if len(pkt) <= HEADER.size:
                continue
            fid, idx, total, ts_ms = HEADER.unpack(pkt[:HEADER.size])
            payload = pkt[HEADER.size:]

            buf = frames.setdefault(fid, {})
            buf[idx] = payload
            meta[fid] = (total, ts_ms)

            if len(buf) < total:
                continue

            data = b"".join(buf[i] for i in range(total))
            frames.pop(fid, None)
            total_n, ts = meta.pop(fid, (total, ts_ms))

            got += 1
            now_ms = int(time.time() * 1000)
            delay = (now_ms - ts) & 0xFFFFFFFF
            if delay > 60000:      # 时间戳跨位或异常，忽略
                delay = -1
            if delay >= 0:
                latencies.append(delay)
                if csv_w:
                    csv_w.writerow(["%.3f" % (time.time() - t0), fid, delay, len(data)])
                    csv_f.flush()

            if (not args.no_display) or args.dump_dir:
                arr = np.frombuffer(data, dtype=np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue
                if args.dump_dir and got % max(args.dump_every, 1) == 0:
                    cv2.imwrite(os.path.join(args.dump_dir, "f%05d.jpg" % got), frame,
                                [int(cv2.IMWRITE_JPEG_QUALITY), 85])
                if not args.no_display:
                    txt = "Receiver  frame %d  %.1f KB  delay %d ms" % (fid, len(data) / 1024.0, delay)
                    cv2.putText(frame, txt, (10, 24), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (0, 255, 255), 2)
                    cv2.imshow(win_name, frame)
                    if cv2.waitKey(1) & 0xFF == ord("q"):
                        break

            if got % 50 == 0:
                dur = max(time.time() - t0, 1e-6)
                arr_l = np.array(latencies) if latencies else np.array([0])
                print("已收 %d 帧，%.1f fps，时延 均值 %.1f ms / P95 %.1f ms"
                      % (got, got / dur, arr_l.mean(), np.percentile(arr_l, 95)))

            # 丢弃残留超过 2 秒的不完整帧
            for k in [k for k, v in meta.items() if (int(time.time() * 1000) - v[1]) & 0xFFFFFFFF > 2000]:
                frames.pop(k, None)
                meta.pop(k, None)
                dropped += 1
    except KeyboardInterrupt:
        pass
    finally:
        sock.close()
        if csv_f:
            csv_f.close()
        if not args.no_display:
            cv2.destroyAllWindows()
        if latencies:
            a = np.array(latencies)
            print("统计：收到 %d 帧，丢弃 %d 帧，时延 均值 %.1f ms，P50 %.1f，P95 %.1f，最大 %.1f"
                  % (got, dropped, a.mean(), np.percentile(a, 50),
                     np.percentile(a, 95), a.max()))
        else:
            print("统计：未收到完整帧（检查 veth 配置、仿真是否在跑、目标地址是否正确）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
