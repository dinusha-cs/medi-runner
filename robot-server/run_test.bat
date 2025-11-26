@echo off
cd /d "d:\DIPS-AS\Workbench\medi-runner\robot-server"
start /B python main.py
timeout /t 3 /nobreak > nul
python test_pid.py