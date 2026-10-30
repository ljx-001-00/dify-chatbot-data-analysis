@echo off
chcp 65001 >nul
title frp tunnel
cd /d "C:\frp"
"C:\frp\frpc.exe" -c "C:\frp\frpc.toml"
echo.
echo [tunnel exited] press any key to close
pause >nul