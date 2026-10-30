@echo off
chcp 65001 >nul
title 智能客服数据大屏
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 goto NOPY

echo ==============================================
echo   智能客服数据大屏
echo   访问地址: http://127.0.0.1:5001
echo   停止服务: 关闭本窗口或按 Ctrl+C
echo ==============================================
start "dash-browser" cmd /c "timeout /t 3 >nul && start http://127.0.0.1:5001"
python dashboard\app.py
echo.
echo 服务已停止。
pause
exit /b 0

:NOPY
echo [错误] 未找到 python 命令。
echo 请安装 Python 3.8+ 并在安装时勾选 "Add Python to PATH"，
echo 或编辑本文件，把 python 改成完整路径，例如:
echo   C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe dashboard\app.py
pause
exit /b 1
