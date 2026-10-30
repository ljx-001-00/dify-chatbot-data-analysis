@echo off
rem frp tunnel keeper - double click. closes? no. keep it minimized.
if "%~1"=="--worker" goto worker
start "frp tunnel" /min cmd /c "%~f0" --worker
exit /b
:worker
cd /d C:\frp
:loop
echo [%date% %time%] starting frpc ...
frpc.exe -c frpc.toml
echo [%date% %time%] frpc exited, restart in 5s
timeout /t 5 /nobreak >nul
goto loop
