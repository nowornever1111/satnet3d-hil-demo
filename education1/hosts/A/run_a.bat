@echo off
chcp 65001 >nul
setlocal
cd /d "%~dp0"

set ADDR=192.168.100.2
set GW=192.168.100.1
set PORT=5000
set FPS=25
set W=960
set H=540

echo ============================================================
echo   电脑 A  视频发送端
echo   本机地址 %ADDR%   --^>   目的 %GW%:%PORT%  （B 网卡1，仿真入口）
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
echo [2/2] 启动发送端：窗口出现后按 q 退出
echo.
python video_sender.py --src %ADDR% --dst %GW% --port %PORT% --fps %FPS% --width %W% --height %H% --win-size 960x540 %*
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
echo 发送端已退出
pause
