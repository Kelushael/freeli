@echo off
echo Starting Sovereign Dashboard...
start /min python "C:\Users\Axcitement\.freeli\bin\dashboard.py"
timeout /t 2 >nul
start http://localhost:8888
echo Dashboard launched! 
echo Press any key to close launcher (server will stop if this window closes)...
pause
