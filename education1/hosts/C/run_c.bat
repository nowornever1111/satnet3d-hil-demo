@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set BIND=192.168.101.2
set PORT=5000

echo ============================================================
echo   电脑 C  视频接收端
echo   监听 %BIND%:%PORT%   （从 B 网卡2 进来的帧）
echo ============================================================
echo   窗口先黑屏是正常的，等 B 的仿真和 A 的发送都起来
echo ============================================================
echo.

python --version >nul 2>nul
if errorlevel 1 goto NOPY

python -c "import cv2, numpy" >nul 2>nul
if errorlevel 1 (
    echo [1/2] 首次运行，安装依赖 opencv-python / numpy ...
    python -m pip install -r requirements.txt
    if errorlevel 1 goto PIPFAIL
)
echo [2/2] 启动接收端：窗口出现后按 q 退出
echo.
python video_receiver.py --bind %BIND% --port %PORT% --save-csv recv_latency.csv --win-size 1000x560 %*
goto END

:NOPY
echo [错误] 找不到 python。
echo        请先装 Python 3.9+，安装时勾选 "Add python.exe to PATH"。
pause
exit /b 1

:PIPFAIL
echo [错误] 依赖安装失败。离线环境请先把 opencv_python / numpy 的 whl 拷来，
echo        然后执行： python -m pip install --no-index --find-links . -r requirements.txt
pause
exit /b 1

:END
echo.
echo 接收端已退出
pause
