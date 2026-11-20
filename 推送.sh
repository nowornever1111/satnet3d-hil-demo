#!/bin/bash
# 一键把本仓库推到 GitHub
#
# 用法：
#   bash 推送.sh https://github.com/<你的账号>/<仓库名>.git
#   bash 推送.sh git@github.com:<你的账号>/<仓库名>.git          # 用 SSH key 的话
#
# 会自动处理两种情况：
#   1) 远端是空仓库          → 直接推
#   2) 远端已有提交（建仓库时勾了 README）→ 提示后强制覆盖
set -u
URL="${1:-}"
if [ -z "$URL" ]; then
    echo "用法：bash 推送.sh https://github.com/<你的账号>/<仓库名>.git"
    exit 1
fi

cd "$(dirname "$0")" || exit 1
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || {
    echo "[错误] 这里不是 git 仓库：$(pwd)"; exit 1; }

git branch -M main

if git remote get-url origin >/dev/null 2>&1; then
    git remote set-url origin "$URL"
else
    git remote add origin "$URL"
fi

echo "仓库目录：$(pwd)"
echo "远端地址：$(git remote get-url origin)"
echo "本次会推的提交："
git log --oneline -3 | sed 's/^/  /'
echo "跟踪文件数：$(git ls-files | wc -l)"
echo

echo "== 尝试推送 =="
out=$(git push -u origin main 2>&1)
rc=$?
echo "$out"

if [ $rc -eq 0 ]; then
    echo
    echo "✅ 推送成功"
    echo "   网页确认：$(echo "$URL" | sed 's/\.git$//')"
    exit 0
fi

case "$out" in
    *rejected*|*non-fast-forward*|*"fetch first"*|*"Updates were rejected"*)
        echo
        echo "== 远端已有提交（多半是建仓库时勾了 README）=="
        echo "   将用 --force 覆盖远端，内容以本仓库为准（本仓库的 README 更完整）"
        echo
        if git push -u --force origin main; then
            echo
            echo "✅ 已强制推送，远端现在与本仓库一致"
            exit 0
        fi
        echo "❌ 强制推送也失败，往上翻报错"
        exit 1
        ;;
    *)
        echo
        echo "❌ 推送失败，最常见的原因是认证："
        echo "   - 密码位置要填 Personal Access Token（勾 repo），不是 GitHub 登录密码"
        echo "   - 或改用本机已配好的 SSH：bash 推送.sh git@github.com:<账号>/<仓库>.git"
        exit 1
        ;;
esac
