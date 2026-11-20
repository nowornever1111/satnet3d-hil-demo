@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ============================================
echo   同步 education1 -^> 提交 -^> 推送到 GitHub
echo ============================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 没找到 python，请先安装 Python 并勾选 Add python.exe to PATH
    echo        下载：https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)

python 同步并推送.py %*

echo.
echo ============================================
pause
