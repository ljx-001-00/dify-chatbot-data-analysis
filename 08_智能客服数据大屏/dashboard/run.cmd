@echo off
chcp 65001 > nul
title 热水器客服 · 聊天数据可视化大屏
cd /d "%~dp0"

echo ==============================================================
echo   热水器客服 -^> 聊天数据智能分析大屏
echo ==============================================================
echo.

where python >nul 2>nul
if errorlevel 1 (
    echo [错误] 没找到 python，请先安装 Python 3.9+ 并勾选 Add to PATH
    pause
    exit /b 1
)

python -c "import flask" >nul 2>nul
if errorlevel 1 (
    echo [提示] 检测到缺少 Flask，正在安装...
    python -m pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
    if errorlevel 1 (
        echo [错误] Flask 安装失败，请手动执行：
        echo        python -m pip install flask
        pause
        exit /b 1
    )
)

echo [启动] 浏览器将自动打开 http://127.0.0.1:5001
echo [停止] 按 Ctrl+C
echo.
start "" http://127.0.0.1:5001
python app.py

echo.
echo 服务已退出。
pause