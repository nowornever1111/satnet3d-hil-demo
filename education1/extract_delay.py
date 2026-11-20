#!/usr/bin/env python3
"""从 OMNeT++ 结果文件 .vec 中提取视频客户端逐包端到端时延，输出 CSV。

用法：
    python3 extract_delay.py results/General-#0.vec results/delay_e2e.csv

输出列：sim_time_s, delay_s
"""
import re
import sys


def find_vector_id(vec_path, suffix):
    """按向量名后缀（如 endToEndDelay:vector）查找向量 id。"""
    with open(vec_path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if line.startswith("vector "):
                parts = line.split()
                # vector <id> <module> <name> <attrs>
                if len(parts) >= 4 and parts[3].startswith(suffix):
                    if "videoClient" in parts[2] or "videoServer" in parts[2]:
                        return int(parts[1]), parts[2] + " " + parts[3]
    return None, None


def main():
    vec_path = sys.argv[1] if len(sys.argv) > 1 else "results/General-#0.vec"
    out_path = sys.argv[2] if len(sys.argv) > 2 else "results/delay_e2e.csv"

    vid, name = find_vector_id(vec_path, "endToEndDelay")
    if vid is None:
        print("未找到 endToEndDelay 向量，请确认 ini 中已开启 record=vector")
        sys.exit(1)
    print("向量 id = %d  名称 = %s" % (vid, name))

    n = 0
    with open(vec_path, "r", encoding="utf-8", errors="replace") as fin, \
            open(out_path, "w", encoding="utf-8") as fout:
        fout.write("sim_time_s,delay_s\n")
        for line in fin:
            if not line or line[0] not in "0123456789":
                continue
            parts = line.split()
            if len(parts) != 4:
                continue
            try:
                if int(parts[0]) != vid:
                    continue
                t = float(parts[2])
                v = float(parts[3])
            except ValueError:
                continue
            fout.write("%.3f,%.6f\n" % (t, v))
            n += 1
    print("已导出 %d 个样本 -> %s" % (n, out_path))


if __name__ == "__main__":
    main()
