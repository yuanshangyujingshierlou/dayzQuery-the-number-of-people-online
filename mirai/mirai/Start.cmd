@echo off
cd /D %~dp0%
echo.Run dir: %cd%
".\java\bin\java.exe" -cp ./libs/* net.mamoe.mirai.console.terminal.MiraiConsoleTerminalLoader
pause