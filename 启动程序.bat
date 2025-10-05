@echo off
chcp 65001 >nul
echo ====================================
echo     批量注册账号管理工具启动器
echo ====================================
echo.

REM 检查Python是否安装
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [错误] 未检测到Python，请先安装Python 3.x
    echo 下载地址: https://www.python.org/downloads/
    pause
    exit /b 1
)

echo [信息] 检查依赖包...
python -c "import customtkinter" >nul 2>&1
if %errorlevel% neq 0 (
    echo [警告] 缺少依赖包，正在安装...
    pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo [成功] 请重启程序
        pause
        exit /b 1
    )
)

echo [信息] 启动程序...
echo.
python main.py

if %errorlevel% neq 0 (
    echo.
    echo [成功] 请重启程序
    pause
)

