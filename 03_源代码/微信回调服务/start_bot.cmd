@echo off
chcp 65001 >nul
title WeChat Bot - Flask :80
cd /d "C:\Users\HP\Documents\deepseek-harness\default-workspace"
"C:\Users\HP\AppData\Local\Programs\Python\Python310\python.exe" -u "wechat_public_bot.py"
echo.
echo [service exited] press any key to close
pause >nul