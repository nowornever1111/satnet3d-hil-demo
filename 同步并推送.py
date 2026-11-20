#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把本机的 education1 工程同步到本仓库，然后提交并推送到 GitHub。

日常用法（在这个目录下双击 同步并推送.bat 效果相同）：

    python 同步并推送.py                      # 自动生成提交说明
    python 同步并推送.py -m "改了什么"         # 自己写提交说明
    python 同步并推送.py --dry-run            # 只报告会改哪些文件，不动手
    python 同步并推送.py --no-push            # 只提交到本地，先不推

同步来源：../04-代码/仿真模型/education1
同步目标：本脚本所在目录下的 education1/

规则：
  * 源里有、仓库里没有或内容不同  -> 覆盖过去
  * 仓库里有、源里没有            -> 删除（但 hosts/dist/ 下的 zip 保留）
  * __pycache__ / results / *.pyc / 仿真结果文件 一律忽略
  * .bat 写出时统一用 CRLF 行尾，其余用 LF
"""

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE
DST = REPO / "education1"
SRC = REPO.parent / "04-代码" / "仿真模型" / "education1"

SKIP_DIRS = {"__pycache__", "results", ".git", ".ipynb_checkpoints"}
SKIP_SUFFIX = {".pyc", ".pyo", ".vci", ".vec", ".sca", ".elog", ".tmp"}
KEEP_IN_DST = ("hosts/dist/",)


def collect(root: Path):
    """返回 {相对路径: 绝对路径}，跳过忽略项。"""
    out = {}
    if not root.is_dir():
        return out
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel = p.relative_to(root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if p.suffix.lower() in SKIP_SUFFIX:
            continue
        out[rel.as_posix()] = p
    return out


def read_text_normalized(path: Path) -> bytes:
    """统一换行后再比较，避免 CRLF/LF 造成假差异。"""
    data = path.read_bytes()
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def write_file(src: Path, dst: Path):
    dst.parent.mkdir(parents=True, exist_ok=True)
    data = src.read_bytes()
    if dst.suffix.lower() in (".bat", ".cmd"):
        # 批处理必须是 CRLF，否则 Windows 上 goto 会出问题
        data = data.replace(b"\r\n", b"\n").replace(b"\r", b"\n").replace(b"\n", b"\r\n")
    dst.write_bytes(data)
    try:
        shutil.copymode(str(src), str(dst))
    except Exception:
        pass
    if src.suffix.lower() in (".sh", ".py") or src.name == "run":
        try:
            os.chmod(str(dst), 0o755)
        except Exception:
            pass


def run_git(args, check=True, env=None):
    r = subprocess.run(
        ["git"] + args, cwd=str(REPO), capture_output=True, text=True,
        encoding="utf-8", errors="replace", env=env,
    )
    if check and r.returncode != 0:
        print((r.stdout or "") + (r.stderr or ""), end="")
        raise SystemExit("[失败] git " + " ".join(args))
    return r


def main():
    ap = argparse.ArgumentParser(add_help=True)
    ap.add_argument("-m", "--msg", default="", help="提交说明，留空则自动生成")
    ap.add_argument("--dry-run", action="store_true", help="只报告差异，不改文件")
    ap.add_argument("--no-push", action="store_true", help="只提交，不推送")
    args = ap.parse_args()

    if not SRC.is_dir():
        print("[错误] 找不到源工程：%s" % SRC)
        print("       如果你就是想直接改本仓库里的文件，那不用这个脚本，")
        print("       直接 git add -A && git commit -m '...' && git push 即可。")
        raise SystemExit(1)

    print("源工程：%s" % SRC)
    print("目标  ：%s" % DST)
    print()

    src_files = collect(SRC)
    dst_files = collect(DST)

    added, updated, removed = [], [], []
    for rel, sp in sorted(src_files.items()):
        dp = DST / rel
        if not dp.exists():
            added.append(rel)
        elif read_text_normalized(sp) != read_text_normalized(dp):
            updated.append(rel)

    for rel in sorted(dst_files):
        if rel in src_files:
            continue
        if any(rel.startswith(k) for k in KEEP_IN_DST):
            continue
        removed.append(rel)

    print("新增 %d  修改 %d  删除 %d   （源 %d 个文件）"
          % (len(added), len(updated), len(removed), len(src_files)))
    for tag, items in (("+", added), ("~", updated), ("-", removed)):
        for rel in items:
            print("  %s %s" % (tag, rel))
    if not (added or updated or removed):
        print("  内容与仓库一致，无需同步")
    print()

    if args.dry_run:
        print("[dry-run] 没有改动任何文件，也没有提交。")
        return

    for rel in added + updated:
        write_file(SRC / rel, DST / rel)
    for rel in removed:
        try:
            (DST / rel).unlink()
        except OSError:
            pass

    run_git(["add", "-A"])

    status = run_git(["status", "--porcelain"], check=False)
    if not status.stdout.strip():
        print("暂存区没有变化，跳过提交。")
    else:
        msg = args.msg.strip()
        if not msg:
            parts = []
            if updated:
                parts.append("改 %d" % len(updated))
            if added:
                parts.append("增 %d" % len(added))
            if removed:
                parts.append("删 %d" % len(removed))
            msg = ("sync: %s（education1）" % "，".join(parts)) if parts else "sync: education1"
        run_git(["commit", "-m", msg])
        print("[已提交] %s" % msg)

    if args.no_push:
        print("[--no-push] 已停在本地，检查无误后再执行 git push origin main")
        return

    print()
    print("== 推送到 GitHub ==")
    r = run_git(["push", "origin", "HEAD"], check=False)
    out = (r.stdout or "") + (r.stderr or "")
    print(out.strip() or "(无输出)")

    if r.returncode == 0:
        print()
        print("[完成] 已推送。网页查看：https://github.com/nowornever1111/satnet3d-hil-demo")
        return

    # HTTPS 走代理失败时，临时摘掉 insteadOf 规则改走 SSH 再试一次
    if "502" in out or "CONNECT" in out or "schannel" in out or "unable to access" in out:
        print()
        print("[提示] HTTPS 通道失败，改用 SSH 重试……")
        old = subprocess.run(
            ["git", "config", "--global", "--get", "url.https://github.com/.insteadof"],
            capture_output=True, text=True,
        ).stdout.strip()
        if old:
            subprocess.run(["git", "config", "--global", "--unset",
                            "url.https://github.com/.insteadof"], capture_output=True)
        try:
            env = dict(os.environ)
            env["GIT_SSH_COMMAND"] = "ssh -o StrictHostKeyChecking=no"
            r2 = subprocess.run(
                ["git", "push", "git@github.com:nowornever1111/satnet3d-hil-demo.git", "HEAD:main"],
                cwd=str(REPO), capture_output=True, text=True, encoding="utf-8",
                errors="replace", env=env,
            )
            print(((r2.stdout or "") + (r2.stderr or "")).strip() or "(无输出)")
            if r2.returncode == 0:
                print()
                print("[完成] 已通过 SSH 推送成功。")
                return
        finally:
            if old:
                subprocess.run(["git", "config", "--global",
                                "url.https://github.com/.insteadof", old], capture_output=True)
        print()
        print("[失败] SSH 也没推上去。先试：ssh -T git@github.com")
        raise SystemExit(1)

    print()
    print("[失败] 上面是 git 的原始报错。常见原因：")
    print("  - 32 位端口/代理不通：试 ssh -T git@github.com")
    print("  - 远端有别人新提交：先 git pull --rebase origin main 再推")
    raise SystemExit(1)


if __name__ == "__main__":
    main()
