#!/usr/bin/env python3
"""案例二半实物 · 视频发送端（对应"电脑 A"：摄像头 → UDP → vethA）

把本机摄像头画面按 JPEG 压缩、分包，经 vethA-peer 发往仿真侧，
由 OMNeT++ 中的卫星星座转发到接收端。

依赖：opencv-python、numpy
    sudo apt install python3-opencv        # 或 pip install opencv-python numpy

用法：
    python3 video_sender.py                     # 默认 192.168.100.2 -> 192.168.101.2:5000
    python3 video_sender.py --dst 192.168.101.2 --port 5000 --fps 25
    python3 video_sender.py --list-cameras      # 查看可用摄像头序号

包格式（12 字节头 + 负载）：
    uint32 frame_id | uint16 chunk_idx | uint16 chunk_total | uint32 timestamp_ms
    big-endian（网络字节序）
"""
import argparse
import socket
import struct
import sys
import time

import cv2
import numpy as np

HEADER = struct.Struct("!IHHI")   # 12 字节
MAX_PAYLOAD = 1400 - HEADER.size  # 与仿真中 1400B 包长对齐


def draw_synthetic(fid, w, h, fps):
    """无摄像头时的合成"监看画面"：网格底 + 滚动波形 + 运动目标 + HUD

    目的是让画面持续在动、帧号可读，便于演示"实时传输"而不是静态图片。
    """
    t = fid / max(fps, 1.0)
    frame = np.zeros((h, w, 3), dtype=np.uint8)

    # 纵向渐变底（BGR：深靛蓝 -> 略亮的蓝灰）
    grad = np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None, None]
    frame[:] = (np.array([34, 22, 18], np.float32) * (1 - grad)
                + np.array([58, 40, 30], np.float32) * grad).astype(np.uint8)

    # 网格
    for x in range(0, w, 60):
        cv2.line(frame, (x, 0), (x, h), (52, 42, 36), 1)
    for y in range(0, h, 60):
        cv2.line(frame, (0, y), (w, y), (52, 42, 36), 1)

    # 滚动波形（模拟业务流）
    pts = []
    for x in range(0, w + 4, 4):
        amp = 0.62 + 0.38 * np.sin(t * 0.8)
        y = int(h * 0.68 + 44 * amp * np.sin(x / 56.0 + t * 2.6))
        pts.append((x, y))
    cv2.polylines(frame, [np.array(pts, np.int32)], False, (235, 200, 70), 2, cv2.LINE_AA)

    # 运动目标（带十字准星）
    cx = int(w * 0.5 + w * 0.34 * np.sin(t * 1.1))
    cy = int(h * 0.36 + 46 * np.cos(t * 1.7))
    cv2.circle(frame, (cx, cy), 36, (250, 160, 60), 2, cv2.LINE_AA)
    cv2.circle(frame, (cx, cy), 5, (250, 160, 60), -1, cv2.LINE_AA)
    cv2.line(frame, (cx - 52, cy), (cx + 52, cy), (250, 160, 60), 1, cv2.LINE_AA)
    cv2.line(frame, (cx, cy - 52), (cx, cy + 52), (250, 160, 60), 1, cv2.LINE_AA)

    # HUD
    cv2.putText(frame, "LIVE  %dx%d  %dfps" % (w, h, int(fps)),
                (24, 44), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (210, 210, 210), 2, cv2.LINE_AA)
    cv2.putText(frame, "FRAME %06d" % fid,
                (24, h - 62), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (80, 220, 250), 2, cv2.LINE_AA)
    cv2.putText(frame, time.strftime("%H:%M:%S"),
                (24, h - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (225, 225, 225), 2, cv2.LINE_AA)

    # REC 指示（闪烁）
    if (fid // 12) % 2 == 0:
        cv2.circle(frame, (w - 96, 34), 10, (60, 60, 230), -1, cv2.LINE_AA)
        cv2.putText(frame, "REC", (w - 76, 42), cv2.FONT_HERSHEY_SIMPLEX,
                    0.62, (60, 60, 230), 2, cv2.LINE_AA)
    return frame


def list_cameras(max_index=6):
    print("可用的摄像头序号：")
    for i in range(max_index):
        cap = cv2.VideoCapture(i)
        ok = cap.isOpened()
        cap.release()
        print("  %d: %s" % (i, "可用" if ok else "不可用"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--src", default="192.168.100.2", help="发送端绑定地址（vethA-peer）")
    ap.add_argument("--dst", default="192.168.101.2", help="接收端地址（vethB-peer）")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--camera", type=int, default=0)
    ap.add_argument("--fps", type=float, default=25.0)
    ap.add_argument("--width", type=int, default=640)
    ap.add_argument("--height", type=int, default=480)
    ap.add_argument("--quality", type=int, default=60, help="JPEG 质量 10-95")
    ap.add_argument("--no-preview", action="store_true")
    ap.add_argument("--synthetic", action="store_true",
                    help="不用摄像头，生成合成画面（无摄像头环境联调通路用）")
    ap.add_argument("--win-size", default="", help="预览窗口尺寸，形如 960x540（录制排版用）")
    ap.add_argument("--win-pos", default="", help="预览窗口左上角坐标，形如 1010,620（录制排版用）")
    ap.add_argument("--list-cameras", action="store_true")
    args = ap.parse_args()

    if args.list_cameras:
        list_cameras()
        return 0

    cv2.setNumThreads(1)
    cap = None
    if not args.synthetic:
        cap = cv2.VideoCapture(args.camera)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, args.width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, args.height)
        if not cap.isOpened():
            print("打不开摄像头 %d。用 --list-cameras 看可用序号，"
                  "或加 --synthetic 先用合成画面联调通路。" % args.camera)
            return 1

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 4 * 1024 * 1024)
    sock.bind((args.src, 0))
    sock.settimeout(1.0)
    print("发送端：%s -> %s:%d，目标 %.1f fps，包长 %d B"
          % (args.src, args.dst, args.port, args.fps, 1400))

    frame_id = 0
    sent_frames = 0
    sent_bytes = 0
    t_start = time.time()
    interval = 1.0 / args.fps

    win_name = "Sender - camera"
    if not args.no_preview and (args.win_size or args.win_pos):
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
            if args.synthetic:
                frame = draw_synthetic(frame_id, args.width, args.height, args.fps)
            else:
                ok, frame = cap.read()
                if not ok:
                    print("读帧失败，退出")
                    break

            ok, jpg = cv2.imencode(".jpg", frame,
                                   [int(cv2.IMWRITE_JPEG_QUALITY), args.quality])
            if not ok:
                continue
            data = jpg.tobytes()
            total = (len(data) + MAX_PAYLOAD - 1) // MAX_PAYLOAD
            ts_ms = int(time.time() * 1000) & 0xFFFFFFFF

            for idx in range(total):
                chunk = data[idx * MAX_PAYLOAD:(idx + 1) * MAX_PAYLOAD]
                pkt = HEADER.pack(frame_id, idx, total, ts_ms) + chunk
                try:
                    sock.sendto(pkt, (args.dst, args.port))
                except OSError as e:
                    print("发送失败：%s（检查 vethA-peer 地址与路由）" % e)
                    return 2

            frame_id += 1
            sent_frames += 1
            sent_bytes += len(data)

            if not args.no_preview:
                cv2.putText(frame, "Sender  frame %d  %d pkts  %.1f KB"
                            % (frame_id, total, len(data) / 1024.0),
                            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                cv2.imshow(win_name, frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break

            if frame_id % 50 == 0:
                dur = time.time() - t_start
                print("已发 %d 帧，%.1f fps，%.2f Mbps"
                      % (sent_frames, sent_frames / dur, sent_bytes * 8 / dur / 1e6))

            # 控制帧率
            sleep = interval - (time.time() - (t_start + (sent_frames - 1) * interval))
            if sleep > 0:
                time.sleep(sleep)
    finally:
        if cap is not None:
            cap.release()
        sock.close()
        if not args.no_preview:
            cv2.destroyAllWindows()
        dur = max(time.time() - t_start, 1e-6)
        print("结束：%d 帧，%.1f fps，%.2f Mbps"
              % (sent_frames, sent_frames / dur, sent_bytes * 8 / dur / 1e6))
    return 0


if __name__ == "__main__":
    sys.exit(main())
