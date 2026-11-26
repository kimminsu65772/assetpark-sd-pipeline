@echo off
chcp 65001 >nul
rem 가마우지 제작 페이지 켜기: 두 번 누르면 서버가 켜지고 브라우저가 열린다. 이 창을 닫으면 꺼진다.
cd /d "%~dp0"
python "%~dp0제작페이지.py" --폴더 "%~dp0.." %*
if errorlevel 1 pause
