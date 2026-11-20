@echo off
chcp 65001 >nul
cd /d "%~dp0"

if "%~1"=="" (
    echo 用法：把仓库地址作为参数传进来，例如
    echo    推送.bat https://github.com/你的账号/satnet3d-hil-demo.git
    echo.
    echo 也可以在 Git Bash 里执行：bash 推送.sh 仓库地址
    pause
    exit /b 1
)

bash 推送.sh %1
echo.
pause
